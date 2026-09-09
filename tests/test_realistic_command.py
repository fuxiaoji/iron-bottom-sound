from copy import deepcopy

import pytest

from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine
from iron_bottom_sound.match import run_match
from iron_bottom_sound.models import (
    FormationMovementOrder,
    FormationSpeedDecision,
    GameOptions,
    HexCoord,
    MovementOrder,
    OrderBatch,
    Phase,
    Side,
)
from iron_bottom_sound.realistic_command import (
    MAX_FORMATIONS_PER_SIDE,
    RealisticCommander,
    _best_formation_cohort,
    _withdrawal_order,
    default_setup_orders,
    expand_movement_orders,
    refresh_command_chain,
)
from iron_bottom_sound.scenario_guidance import public_search_target


def realistic_game(seed: int = 3) -> tuple[IronBottomEngine, str]:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed, GameOptions(realistic_command=True))
    assert state.phase == Phase.FORMATION_SETUP
    for side in Side:
        batch = OrderBatch(
            side=side,
            phase=Phase.FORMATION_SETUP,
            formation_setup=default_setup_orders(state, side),
        )
        assert engine.submit_orders(state.game_id, batch).valid
    engine.advance(state.game_id)
    return engine, state.game_id


def advance_empty_orders(engine: IronBottomEngine, game_id: str) -> None:
    state = engine.get(game_id)
    for side in Side:
        assert engine.submit_orders(
            game_id, OrderBatch(side=side, phase=state.phase)
        ).valid
    engine.advance(game_id)


def test_best_formation_cohort_recomputes_speed_after_forced_detach(monkeypatch) -> None:
    engine, game_id = realistic_game()
    state = engine.get(game_id)
    formation = next(item for item in state.formations.values() if item.side == Side.AXIS)
    members = [state.ships[ship_id] for ship_id in formation.ship_ids if state.ships[ship_id].position]
    assert len(members) >= 3
    ranges = {
        members[0].id: (4, 6),
        members[1].id: (0, 3),
        members[2].id: (2, 5),
    }
    for member in members[3:]:
        ranges[member.id] = (2, 5)
    monkeypatch.setattr(
        engine, "_legal_speed_range", lambda ship, _turn: ranges[ship.id],
    )
    speed, detach = _best_formation_cohort(
        engine, state, formation, members, {members[0].id},
    )
    assert speed == 3
    assert members[0].id in detach
    assert members[1].id not in detach
    assert members[2].id not in detach


def test_realistic_mode_is_opt_in_and_classic_phase_is_unchanged() -> None:
    classic = IronBottomEngine().reset("IBS-S-03", 1)
    assert not classic.options.realistic_command
    assert classic.phase == Phase.REINFORCEMENT
    realistic = IronBottomEngine().reset(
        "IBS-S-03", 1, GameOptions(realistic_command=True)
    )
    assert realistic.phase == Phase.FORMATION_SETUP
    assert realistic.formation_resume_phase == Phase.REINFORCEMENT


def test_default_setup_assigns_every_ship_once_and_is_private() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 1, GameOptions(realistic_command=True))
    for side in Side:
        orders = default_setup_orders(state, side)
        owned = {ship.id for ship in state.ships.values() if ship.side == side}
        listed = [ship_id for order in orders for ship_id in order.ship_ids]
        assert 1 <= len(orders) <= MAX_FORMATIONS_PER_SIDE
        assert set(listed) == owned
        assert len(listed) == len(set(listed))
        assert all(len(order.ship_ids) >= 2 for order in orders)
        assert all(order.flagship_id != order.reserve_flagship_id for order in orders)
    engine, game_id = realistic_game()
    axis = engine.observe(game_id, Side.AXIS)
    allies = engine.observe(game_id, Side.ALLIES)
    assert axis.formations and all(item.side == Side.AXIS for item in axis.formations)
    assert allies.formations and all(item.side == Side.ALLIES for item in allies.formations)


def test_setup_rejects_formation_count_beyond_cap_and_duplicate_membership() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 1, GameOptions(realistic_command=True))
    orders = default_setup_orders(state, Side.ALLIES)
    duplicate = deepcopy(orders[0])
    duplicate.formation_id = "duplicate"
    duplicate.name = "重复编队"
    batch = OrderBatch(
        side=Side.ALLIES,
        phase=Phase.FORMATION_SETUP,
        formation_setup=orders + [duplicate] * MAX_FORMATIONS_PER_SIDE,  # pushes len > cap
    )
    result = engine.validate_orders(state.game_id, batch)
    assert not result.valid
    assert any(f"one to {MAX_FORMATIONS_PER_SIDE}" in error for error in result.errors)


def test_leader_order_expands_to_every_attached_member() -> None:
    engine, game_id = realistic_game()
    advance_empty_orders(engine, game_id)
    state = engine.get(game_id)
    assert state.phase == Phase.MOVEMENT_PLANNING
    side = Side.AXIS
    formation = next(item for item in state.formations.values() if item.side == side)
    batch = OrderBatch(
        side=side,
        phase=state.phase,
        formation_movement=[FormationMovementOrder(
            formation_id=formation.id,
            leader_plan="1",
            spacing=formation.spacing,
        )],
    )
    prepared, errors, detached = expand_movement_orders(engine, state, batch)
    assert not errors
    assert not detached
    assert {order.ship_id for order in prepared.movement} == {
        ship_id for ship_id in formation.ship_ids if state.ships[ship_id].position
    }


def test_detached_ship_gets_atomic_withdrawal_order_and_no_torpedoes() -> None:
    engine, game_id = realistic_game()
    advance_empty_orders(engine, game_id)
    state = engine.get(game_id)
    formation = next(item for item in state.formations.values() if item.side == Side.AXIS)
    detached_id = formation.ship_ids[-1]
    batch = OrderBatch(
        side=Side.AXIS,
        phase=state.phase,
        formation_movement=[FormationMovementOrder(
            formation_id=formation.id,
            leader_plan="1",
            spacing=formation.spacing,
            speed_decision=FormationSpeedDecision(
                formation_id=formation.id,
                action="detach",
                detach_ship_ids=[detached_id],
            ),
        )],
    )
    prepared, errors, detached = expand_movement_orders(engine, state, batch)
    assert not errors
    assert detached == [detached_id]
    assert detached_id in {order.ship_id for order in prepared.movement}


def test_detaching_forced_old_leader_uses_replacement_leader_plan() -> None:
    engine, game_id = realistic_game()
    advance_empty_orders(engine, game_id)
    state = engine.get(game_id)
    formation = next(item for item in state.formations.values() if item.side == Side.AXIS)
    old_leader = state.ships[formation.leader_id]
    old_leader.forced_straight_turns = 1
    old_leader.forced_speed = 6
    survivor_id = next(ship_id for ship_id in formation.ship_ids if ship_id != old_leader.id)
    detached = [ship_id for ship_id in formation.ship_ids if ship_id != survivor_id]
    batch = OrderBatch(
        side=Side.AXIS,
        phase=state.phase,
        formation_movement=[FormationMovementOrder(
            formation_id=formation.id,
            leader_plan="2",
            spacing=formation.spacing,
            speed_decision=FormationSpeedDecision(
                formation_id=formation.id,
                action="detach",
                detach_ship_ids=detached,
            ),
        )],
    )
    prepared, errors, detach_ids = expand_movement_orders(engine, state, batch)
    assert not errors
    assert set(detach_ids) == set(detached)
    replacement = next(order for order in prepared.movement if order.ship_id == survivor_id)
    assert replacement.plan == "2"
    assert replacement.speed == 2


def test_realistic_boundary_emergency_stop_overrides_forced_damage_order() -> None:
    engine, game_id = realistic_game()
    advance_empty_orders(engine, game_id)
    state = engine.get(game_id)
    owned = [ship for ship in state.ships.values() if ship.side == Side.AXIS and ship.position]
    target = owned[0]
    target.forced_straight_turns = 1
    target.forced_circle_turns = 2
    target.turn_limit_degrees = 60
    target.forced_speed = 5
    batch = OrderBatch(
        side=Side.AXIS,
        phase=state.phase,
        movement=[MovementOrder(
            ship_id=ship.id,
            plan="0",
            speed=0,
            formation_emergency_stop=ship.id == target.id,
        ) for ship in owned],
    )
    result = engine.validate_orders(game_id, batch, _prepared=True)
    assert result.valid, result.errors


def test_withdrawal_at_map_rim_probes_legal_forced_circle_program(monkeypatch) -> None:
    engine, game_id = realistic_game()
    advance_empty_orders(engine, game_id)
    state = engine.get(game_id)
    ship = next(ship for ship in state.ships.values() if ship.side == Side.AXIS and ship.position)
    ship.position = HexCoord.from_label("O2")
    ship.heading = 6
    ship.current_speed = 4
    ship.previous_speed = 4
    ship.withdrawal_edge = "east"
    ship.forced_circle_turns = 2
    ship.turn_limit_degrees = 60
    monkeypatch.setattr(engine, "movement_candidates", lambda *_args, **_kwargs: {"reachable": []})
    monkeypatch.setattr(engine, "_legal_speed_range", lambda *_args: (2, 4))

    order = _withdrawal_order(engine, state, ship)
    preview = engine.movement_preview(state, ship, plan=order.plan)

    assert preview["commitable"], preview["errors"]
    assert order.plan.startswith("1")
    assert all(not command.endswith("120") for command in engine.movement_commands(order))


def test_disrupted_formation_clamps_locked_speed_to_damage_floor(monkeypatch) -> None:
    engine, game_id = realistic_game()
    advance_empty_orders(engine, game_id)
    state = engine.get(game_id)
    formation = next(item for item in state.formations.values() if item.side == Side.AXIS)
    formation.disruption_turn = state.turn
    formation.locked_speed = 0
    leader_id = formation.leader_id
    monkeypatch.setattr(
        engine,
        "_legal_speed_range",
        lambda ship, _turn: (0, 2) if ship.id == leader_id else (1, 1),
    )
    batch = OrderBatch(
        side=Side.AXIS,
        phase=state.phase,
        formation_movement=[FormationMovementOrder(
            formation_id=formation.id,
            leader_plan="0",
            spacing=formation.spacing,
        )],
    )

    prepared, errors, _detached = expand_movement_orders(engine, state, batch)

    assert not any("reduced speed is not legal" in error for error in errors)
    leader_order = next(order for order in prepared.movement if order.ship_id == leader_id)
    assert leader_order.speed == 1


def test_flagship_death_uses_reserve_and_locks_next_turn() -> None:
    engine, game_id = realistic_game()
    state = engine.get(game_id)
    formation = next(item for item in state.formations.values() if item.side == Side.AXIS)
    previous = formation.flagship_id
    expected = formation.reserve_flagship_id
    formation.speed = 5
    formation.heading = 4
    state.ships[previous].captain_status = "killed"
    refresh_command_chain(engine, state)
    assert formation.flagship_id == expected
    assert formation.disruption_turn == state.turn + 1
    assert formation.locked_speed == 5
    assert formation.locked_heading == state.ships[formation.leader_id].heading
    assert state.command_successions[-1].previous_flagship_id == previous


def test_flagship_transfer_locks_surviving_leader_actual_speed_not_stale_cache() -> None:
    engine, game_id = realistic_game()
    state = engine.get(game_id)
    formation = next(item for item in state.formations.values() if item.side == Side.AXIS)
    stale_leader = state.ships[formation.leader_id]
    stale_leader.position = None
    survivor = next(state.ships[item] for item in formation.ship_ids if item != stale_leader.id)
    survivor.current_speed = 4
    formation.speed = 0
    state.ships[formation.flagship_id].captain_status = "killed"
    refresh_command_chain(engine, state)
    assert formation.leader_id == survivor.id
    assert formation.locked_speed == 4
    assert formation.locked_heading == survivor.heading


def test_realistic_state_machine_completes_scenario_three_without_fallback() -> None:
    for seed in (3, 9):
        report, engine, _sessions = run_match(
            "IBS-S-03",
            axis="tactical",
            allies="tactical",
            seed=seed,
            options=GameOptions(realistic_command=True),
            request_limit=128,
        )
        state = engine.get(report.game_id)
        assert report.passed, report.failure_reason
        assert state.phase == Phase.COMPLETE
        assert not any(event.type == "collision" and event.payload.get("friendly") for event in state.events)
        assert not any(
            event.type == "torpedo_hit"
            and event.payload.get("attacker_side") == event.payload.get("target_side")
            for event in state.events
        )


def test_realistic_commander_emits_only_formation_movement_orders() -> None:
    engine, game_id = realistic_game()
    advance_empty_orders(engine, game_id)
    plan, batch, _audits = RealisticCommander().choose_plan(engine, game_id, Side.AXIS)
    assert plan.phase == Phase.MOVEMENT_PLANNING
    assert batch.formation_movement
    assert batch.movement == []


def test_erma_commander_searches_public_enemy_zone_before_contact() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-EM-01", 28, GameOptions(realistic_command=True))
    commander = RealisticCommander()
    for side in Side:
        setup = commander.choose_orders(engine, state.game_id, side)
        assert engine.submit_orders(state.game_id, setup).valid
    engine.advance(state.game_id)
    while state.phase != Phase.MOVEMENT_PLANNING:
        if state.phase in ORDER_PHASES:
            advance_empty_orders(engine, state.game_id)
        else:
            engine.advance(state.game_id)
    for side in Side:
        target = public_search_target(state, side)
        assert target is not None
        before = {
            formation.id: state.ships[formation.leader_id].position.distance(target)
            for formation in state.formations.values() if formation.side == side
        }
        batch = commander.choose_orders(engine, state.game_id, side)
        prepared, errors, _ = expand_movement_orders(engine, state, batch)
        assert not errors
        for order in prepared.movement:
            ship = state.ships[order.ship_id]
            formation = state.formations[ship.formation_id]
            if ship.id != formation.leader_id:
                continue
            preview = engine.movement_preview(state, ship, plan=order.plan)
            end = HexCoord(**preview["current_hex"])
            assert end.distance(target) < before[formation.id]


def test_realistic_tactical_planner_leaves_retreating_ship_to_withdrawal_controller() -> None:
    engine, game_id = realistic_game()
    advance_empty_orders(engine, game_id)
    state = engine.get(game_id)
    ship = next(ship for ship in state.ships.values() if ship.side == Side.AXIS)
    ship.command_status = "retreating"
    commander = RealisticCommander()
    movement, _contacts, _intents = commander.tactical._plan_movement(
        engine, state, Side.AXIS, commander.tactical._ai_rng(state, Side.AXIS)
    )
    assert ship.id not in {order.ship_id for order in movement}


def test_realistic_legal_actions_include_valid_editable_formation_starting_orders() -> None:
    engine, game_id = realistic_game()
    advance_empty_orders(engine, game_id)
    state = engine.get(game_id)
    action = engine.legal_actions(game_id, Side.AXIS)[0]
    suggested = action.schema_hint["suggested_formation_movement"]
    assert suggested
    batch = OrderBatch(
        side=Side.AXIS,
        phase=Phase.MOVEMENT_PLANNING,
        formation_movement=suggested,
    )
    assert engine.validate_orders(game_id, batch).valid


def test_friendly_collision_never_damages_when_enemy_shares_the_hex() -> None:
    """混战同格既含友军对、又含敌舰时，友军对必须仍被紧急停车，不得掷友军碰撞。

    回归：engine._resolve_movement 的友军保护原先按“整组是否全同侧”生效，
    同一脉冲同落一格的组里混进一艘敌舰即整体跳过保护，随后伤害循环把组内
    友军×友军也照常掷 collision_check/collision_result。
    """
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 1, GameOptions(realistic_command=True))
    axis_ships = [ship for ship in state.ships.values() if ship.side == Side.AXIS and ship.position]
    ally_ships = [ship for ship in state.ships.values() if ship.side == Side.ALLIES and ship.position]
    a_ship, b_ship = axis_ships[0], axis_ships[1]
    enemy = ally_ships[0]

    occupied = {ship.position for ship in state.ships.values() if ship.position}
    target = next(
        HexCoord(q=q, r=r)
        for q in range(3, 43) for r in range(2, 36)
        if HexCoord(q=q, r=r) not in occupied
        and all(HexCoord(q=q, r=r).neighbor(h) not in occupied for h in range(1, 7))
    )

    def opposite(heading: int) -> int:
        return ((heading + 2) % 6) + 1

    starts: dict[str, HexCoord] = {}
    for ship, heading in ((a_ship, 1), (b_ship, 3), (enemy, 5)):
        ship.position = target.neighbor(opposite(heading))
        ship.heading = heading
        ship.current_speed = 3
        ship.previous_speed = 3
        ship.command_status = "attached"
        starts[ship.id] = ship.position

    state.sealed_orders[f"{state.turn}:{Phase.MOVEMENT_PLANNING.value}"] = {
        Side.AXIS.value: OrderBatch(
            side=Side.AXIS,
            phase=Phase.MOVEMENT_PLANNING,
            movement=[MovementOrder(ship_id=ship.id, plan="1") for ship in (a_ship, b_ship)],
        ),
        Side.ALLIES.value: OrderBatch(
            side=Side.ALLIES,
            phase=Phase.MOVEMENT_PLANNING,
            movement=[MovementOrder(ship_id=enemy.id, plan="1")],
        ),
    }
    before = len(state.events)
    engine._resolve_movement(state)
    events = state.events[before:]

    friendly_events = [
        event for event in events
        if event.type in {"collision_check", "collision_result"}
        and event.payload.get("ships")
        and state.ships[event.payload["ships"][0]].side
        == state.ships[event.payload["ships"][1]].side
    ]
    assert not friendly_events, [event.message for event in friendly_events]
    assert a_ship.position == starts[a_ship.id]  # 友军对双双急停在起点
    assert b_ship.position == starts[b_ship.id]
    assert enemy.position == target  # 敌舰单独进入争议格


@pytest.mark.parametrize(("axis_profile", "allies_profile", "seed"), [
    ("balanced", "balanced", 20280829),
    ("balanced", "torpedo", 20280830),
    ("balanced", "balanced", 20280831),
    ("balanced", "brawl", 20280832),
    ("balanced", "direct_attack", 20280832),
    ("torpedo", "area_denial", 20280830),
    ("torpedo", "crossfire", 20280830),
    ("brawl", "balanced", 20280829),
    ("brawl", "torpedo", 20280829),
    ("brawl", "balanced", 20280832),
    ("evolved", "area_denial", 20280831),
    ("evolved", "break_crossing_t", 20280831),
    ("evolved", "formation_split", 20280830),
    ("evolved", "crossfire", 20280829),
])
def test_realistic_erma_training_regression_seeds_complete_legally(
    axis_profile: str, allies_profile: str, seed: int,
) -> None:
    report, engine, _sessions = run_match(
        "IBS-S-EM-01",
        axis="tactical",
        allies="tactical",
        axis_profile=axis_profile,
        allies_profile=allies_profile,
        seed=seed,
        options=GameOptions(realistic_command=True),
        request_limit=180,
    )
    assert report.passed, report.failure_reason
    state = engine.get(report.game_id)
    assert state.phase == Phase.COMPLETE and state.turn == 12
    assert not any(
        event.type in {"collision", "collision_check"} and event.payload.get("friendly")
        for event in state.events
    )
    assert not any(
        event.type == "torpedo_hit"
        and event.payload.get("attacker_side") == event.payload.get("target_side")
        for event in state.events
    )


@pytest.mark.parametrize(("allies_profile", "seed"), [
    ("line", 20270830),
    ("brawl", 20270829),
    ("evolved", 20270829),
])
def test_realistic_s01_reinforcement_formations_remain_commanded(
    allies_profile: str, seed: int,
) -> None:
    report, engine, _sessions = run_match(
        "IBS-S-01",
        axis="tactical",
        allies="tactical",
        axis_profile="balanced",
        allies_profile=allies_profile,
        seed=seed,
        options=GameOptions(realistic_command=True),
        request_limit=180,
    )
    assert report.passed, report.failure_reason
    state = engine.get(report.game_id)
    assert state.phase == Phase.COMPLETE
    assert not any(
        event.type in {"collision", "collision_check"} and event.payload.get("friendly")
        for event in state.events
    )
    assert not any(
        event.type == "torpedo_hit"
        and event.payload.get("attacker_side") == event.payload.get("target_side")
        for event in state.events
    )
