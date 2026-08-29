from copy import deepcopy

import pytest

from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine
from iron_bottom_sound.match import run_match
from iron_bottom_sound.models import (
    FormationMovementOrder,
    FormationSpeedDecision,
    GameOptions,
    HexCoord,
    OrderBatch,
    Phase,
    Side,
)
from iron_bottom_sound.realistic_command import (
    RealisticCommander,
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
        assert 1 <= len(orders) <= 4
        assert set(listed) == owned
        assert len(listed) == len(set(listed))
        assert all(len(order.ship_ids) >= 2 for order in orders)
        assert all(order.flagship_id != order.reserve_flagship_id for order in orders)
    engine, game_id = realistic_game()
    axis = engine.observe(game_id, Side.AXIS)
    allies = engine.observe(game_id, Side.ALLIES)
    assert axis.formations and all(item.side == Side.AXIS for item in axis.formations)
    assert allies.formations and all(item.side == Side.ALLIES for item in allies.formations)


def test_setup_rejects_fifth_formation_and_duplicate_membership() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 1, GameOptions(realistic_command=True))
    orders = default_setup_orders(state, Side.ALLIES)
    duplicate = deepcopy(orders[0])
    duplicate.formation_id = "duplicate"
    duplicate.name = "重复编队"
    batch = OrderBatch(
        side=Side.ALLIES,
        phase=Phase.FORMATION_SETUP,
        formation_setup=orders + [duplicate, deepcopy(duplicate), deepcopy(duplicate), deepcopy(duplicate)],
    )
    result = engine.validate_orders(state.game_id, batch)
    assert not result.valid
    assert any("one to four" in error for error in result.errors)


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


@pytest.mark.parametrize(("axis_profile", "allies_profile", "seed"), [
    ("balanced", "balanced", 20280829),
    ("balanced", "torpedo", 20280830),
    ("balanced", "balanced", 20280831),
    ("balanced", "brawl", 20280832),
    ("balanced", "direct_attack", 20280832),
    ("torpedo", "area_denial", 20280830),
    ("torpedo", "crossfire", 20280830),
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
