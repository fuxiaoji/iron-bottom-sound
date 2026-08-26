"""Batch A: movement step-by-step backend — reachable overlay, per-step preview,
plan/commands round-trips, path-to-commands, and the read-only preview API."""

import pytest
from fastapi.testclient import TestClient

from iron_bottom_sound.api import app, engine as api_engine
from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import (
    MovementOrder,
    OrderBatch,
    Phase,
    Side,
)


def axis_ship(engine: IronBottomEngine, game_id: str):
    return next(
        ship
        for ship in engine.get(game_id).ships.values()
        if ship.side.value == "axis" and ship.position is not None
    )


def game_in_movement_planning(client, seed: int = 5):
    created = client.post("/games", json={"scenario_id": "IBS-S-03", "seed": seed}).json()
    game_id = created["game_id"]
    # REINFORCEMENT has no mandatory entries for the opening group; empty batches advance.
    api_engine.submit_orders(game_id, OrderBatch(side=Side.AXIS, phase=Phase.REINFORCEMENT))
    api_engine.submit_orders(game_id, OrderBatch(side=Side.ALLIES, phase=Phase.REINFORCEMENT))
    api_engine.advance(game_id)
    assert api_engine.get(game_id).phase == Phase.MOVEMENT_PLANNING
    return game_id


def full_movement_batch(game_id: str, side: Side) -> OrderBatch:
    own = [
        ship for ship in api_engine.get(game_id).ships.values()
        if ship.side == side and ship.position is not None
    ]
    return OrderBatch(
        side=side,
        phase=Phase.MOVEMENT_PLANNING,
        movement=[MovementOrder(ship_id=ship.id, plan="0") for ship in own],
    )


def test_commands_to_plan_compresses_and_round_trips() -> None:
    engine = IronBottomEngine()
    assert engine.commands_to_plan([]) == "0"
    assert engine.commands_to_plan(["advance", "advance", "advance"]) == "3"
    assert engine.commands_to_plan(["advance", "turn_starboard_60", "advance", "turn_port_120"]) == "1S1PP"
    assert engine.commands_to_plan(["turn_port_120", "advance"]) == "PP1"
    assert engine.commands_to_plan(["turn_starboard_60"]) == "S"


def test_commands_to_plan_is_inverse_of_movement_commands() -> None:
    engine = IronBottomEngine()
    plans = ["0", "1", "1S", "2P1", "1PP1", "1S1P", "3SS1"]
    for plan in plans:
        order = MovementOrder(ship_id="s", plan=plan)
        assert engine.commands_to_plan(engine.movement_commands(order)) == plan


def test_path_to_commands_straight_and_turns() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=7, game_id="path-straight")
    ship = axis_ship(engine, state.game_id)
    heading = ship.heading
    straight = ship.position.neighbor(heading)
    assert engine.path_to_commands(ship, [straight]) == ["advance"]
    port60 = ship.position.neighbor(6 if heading == 1 else heading - 1)
    assert engine.path_to_commands(ship, [port60]) == ["turn_port_60", "advance"]
    starboard60 = ship.position.neighbor(1 if heading == 6 else heading + 1)
    assert engine.path_to_commands(ship, [starboard60]) == ["turn_starboard_60", "advance"]


def test_path_to_commands_rejects_reversal_and_non_adjacency() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=7, game_id="path-errors")
    ship = axis_ship(engine, state.game_id)
    reverse = ship.position.neighbor(((ship.heading + 2) % 6) + 1)
    with pytest.raises(ValueError, match="180"):
        engine.path_to_commands(ship, [reverse])
    far = HexCoord_from_label_stepping(ship.position, ship.heading, 2)
    with pytest.raises(ValueError, match="not adjacent"):
        engine.path_to_commands(ship, [far])


def HexCoord_from_label_stepping(position, heading, steps):
    from iron_bottom_sound.models import HexCoord
    for _ in range(steps):
        position = position.neighbor(heading)
    return HexCoord(q=position.q, r=position.r)


def test_path_to_commands_trajectory_ends_on_dragged_hex() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=7, game_id="path-roundtrip")
    ship = axis_ship(engine, state.game_id)
    path = [ship.position.neighbor(ship.heading)]
    path.append(path[0].neighbor(((ship.heading + 1) % 6) + 1))
    commands = engine.path_to_commands(ship, path)
    trajectory, _ = engine.movement_trajectory(ship, "", commands)
    assert trajectory[-1][0] == path[-1]
    # exactly one turn between two advances; which turn depends on hex geometry
    assert engine.commands_to_plan(commands) in {"1S1", "1P1", "1SS1", "1PP1"}


def test_movement_candidates_overlay_bounds_and_dedup() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=7, game_id="candidates")
    ship = axis_ship(engine, state.game_id)
    candidates = engine.movement_candidates(state, ship)
    minimum, maximum = candidates["min_cost"], candidates["max_cost"]
    assert minimum <= maximum
    labels = [entry["label"] for entry in candidates["reachable"]]
    assert len(labels) == len(set(labels))
    assert ship.position.label in labels  # the stationary "0" plan is a final state
    for entry in candidates["reachable"]:
        assert minimum <= entry["cost"] <= maximum
        assert entry["cost"] <= 8
        for final_heading in entry["final_headings"]:
            assert 1 <= final_heading <= 6
    # the straight-ahead hex is reachable at cost 1
    ahead = ship.position.neighbor(ship.heading)
    ahead_entry = next(entry for entry in candidates["reachable"] if entry["label"] == ahead.label)
    assert ahead_entry["cost"] == 1


def test_movement_candidates_stationary_plan_is_min_cost() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=7, game_id="candidates-stationary")
    ship = axis_ship(engine, state.game_id)
    candidates = engine.movement_candidates(state, ship)
    start = next(entry for entry in candidates["reachable"] if entry["label"] == ship.position.label)
    assert start["cost"] == 0
    assert candidates["min_cost"] == 0


def test_movement_preview_empty_and_simple_plans() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=7, game_id="preview-simple")
    ship = axis_ship(engine, state.game_id)
    empty = engine.movement_preview(state, ship)
    assert empty["valid"] is True
    assert empty["commitable"] is True
    assert empty["plan"] == "0"
    assert empty["cost"] == 0
    assert empty["current_label"] == ship.position.label
    assert empty["trajectory"] == []
    one = engine.movement_preview(state, ship, plan="1")
    assert one["cost"] == 1
    assert one["current_label"] == ship.position.neighbor(ship.heading).label
    assert one["current_heading"] == ship.heading
    assert len(one["trajectory"]) == 1
    assert one["trajectory"][0]["mf"] == 1
    turn = engine.movement_preview(state, ship, plan="1S")
    assert turn["current_heading"] == (1 if ship.heading == 6 else ship.heading + 1)
    assert turn["commitable"] is True


def test_movement_preview_twenty_degree_costs_one_mf() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=7, game_id="preview-120")
    ship = axis_ship(engine, state.game_id)
    preview = engine.movement_preview(state, ship, plan="1SS1")
    assert preview["cost"] == 3
    assert preview["valid"] is True
    assert preview["commitable"] is True
    assert len(preview["trajectory"]) == 3  # advance, 120 (same hex), advance


def test_movement_preview_drag_continues_from_prefix_end_state() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=7, game_id="preview-drag-continue")
    ship = axis_ship(engine, state.game_id)
    heading = ship.heading
    new_heading = 1 if heading == 6 else heading + 1
    first = ship.position.neighbor(heading)
    target = first.neighbor(new_heading)
    # advance one MF, turn starboard, then drag forward: the drag must continue
    # from the planned position/heading, not the ship's real one
    continued = engine.movement_preview(
        state, ship, commands=["advance", "turn_starboard_60"], hexes=[target]
    )
    assert continued["valid"] is True
    assert continued["commands"] == ["advance", "turn_starboard_60", "advance"]
    assert continued["plan"] == "1S1"
    assert continued["current_label"] == target.label


def test_movement_preview_rejects_illegal_plans() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=7, game_id="preview-illegal")
    ship = axis_ship(engine, state.game_id)
    # first command must be advance
    starts_with_turn = engine.movement_preview(state, ship, plan="S1")
    assert starts_with_turn["valid"] is False
    assert starts_with_turn["commitable"] is False
    assert starts_with_turn["errors"]
    # a 120-degree turn may not end the plan
    ends_with_120 = engine.movement_preview(state, ship, plan="1SS")
    assert ends_with_120["valid"] is False
    assert ends_with_120["errors"]


def test_movement_preview_next_options_follows_rules() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=7, game_id="preview-next")
    ship = axis_ship(engine, state.game_id)
    preview = engine.movement_preview(state, ship, plan="1")
    assert preview["next_options"]["advance"][0]["label"] == (
        ship.position.neighbor(ship.heading).neighbor(ship.heading).label
    )
    turns = {turn["action"]: turn for turn in preview["next_options"]["turns"]}
    assert set(turns) == {
        "turn_port_60",
        "turn_starboard_60",
        "turn_port_120",
        "turn_starboard_120",
    }
    assert turns["turn_port_60"]["legal"] is True
    assert turns["turn_port_60"]["cost_delta"] == 0
    assert turns["turn_port_120"]["legal"] is True
    assert turns["turn_port_120"]["cost_delta"] == 1
    # after the final free turn no further turns are offered (must advance next)
    after_turn = engine.movement_preview(state, ship, plan="1S")
    assert after_turn["next_options"]["turns"] == []
    assert after_turn["next_options"]["advance"]


def test_movement_preview_commits_through_submit_orders() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=7, game_id="preview-commit")
    engine.submit_orders(state.game_id, OrderBatch(side=Side.AXIS, phase=Phase.REINFORCEMENT))
    engine.submit_orders(state.game_id, OrderBatch(side=Side.ALLIES, phase=Phase.REINFORCEMENT))
    engine.advance(state.game_id)
    assert engine.get(state.game_id).phase == Phase.MOVEMENT_PLANNING
    ship = axis_ship(engine, state.game_id)
    preview = engine.movement_preview(state, ship, plan="1S1")
    assert preview["valid"] is True
    orders = [
        MovementOrder(ship_id=owned.id, plan="0")
        for owned in state.ships.values()
        if owned.side == Side.AXIS and owned.position is not None
    ]
    orders = [
        MovementOrder(ship_id=ship.id, plan=preview["plan"], speed=preview["cost"])
        if order.ship_id == ship.id
        else order
        for order in orders
    ]
    result = engine.validate_orders(state.game_id, OrderBatch(side=Side.AXIS, movement=orders))
    assert result.valid, result.errors


def test_movement_candidates_respects_forced_straight_speed_lock() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=7, game_id="candidates-straight")
    ship = axis_ship(engine, state.game_id)
    ship.forced_straight_turns = 1
    ship.forced_speed = 2
    candidates = engine.movement_candidates(state, ship)
    assert (candidates["min_cost"], candidates["max_cost"]) == (2, 2)
    ahead = ship.position
    for _ in range(2):
        ahead = ahead.neighbor(ship.heading)
    assert [entry["label"] for entry in candidates["reachable"]] == [ahead.label]
    assert candidates["reachable"][0]["final_headings"] == [ship.heading]


def test_movement_preview_honors_forced_circle_side() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=7, game_id="preview-circle")
    ship = axis_ship(engine, state.game_id)
    ship.forced_circle_turns = 1
    ship.forced_turn_side = "port"
    preview = engine.movement_preview(state, ship, plan="1")
    turns = {turn["action"]: turn for turn in preview["next_options"]["turns"]}
    assert turns["turn_port_60"]["legal"] is True
    assert turns["turn_starboard_60"]["legal"] is False
    assert turns["turn_starboard_120"]["legal"] is False
    assert turns["turn_port_120"]["legal"] is False
    # the straight-ahead hex cannot be a final stop facing the original heading
    # (that would require no turn); "1P" is legal, so it is reachable at cost 1
    # but only facing the post-port-turn heading
    candidates = engine.movement_candidates(state, ship)
    ahead = ship.position.neighbor(ship.heading).label
    ahead_entry = next(entry for entry in candidates["reachable"] if entry["label"] == ahead)
    assert ahead_entry["cost"] == 1
    assert ship.heading not in ahead_entry["final_headings"]


def test_immobile_forced_circle_ship_can_legally_stay() -> None:
    """最大航速归零（引擎失效）+ 圆周强制：舰无法移动、圆周指令无法执行，
    引擎须放行「原地停留」（plan "0"），否则该舰不存在任何合法订单
    （IBS-U-USN-DUNCAN 死锁回归：legal_range [0,0] 但强制圆周要求转一次）。"""
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=7, game_id="circle-immobile")
    ship = axis_ship(engine, state.game_id)
    ship.speed_damage_track = ((0,), (0,), (0,))
    ship.speed_damage_crossed = (0, 0, 0)
    ship.forced_circle_turns = 1
    ship.forced_turn_side = "port"
    assert ship.max_speed_for_turn(state.turn) == 0
    candidates = engine.movement_candidates(state, ship, include_plans=False)
    assert (candidates["min_cost"], candidates["max_cost"]) == (0, 0)
    assert any(
        entry["label"] == ship.position.label and entry["cost"] == 0
        for entry in candidates["reachable"]
    ), "原地停留必须是可达状态"
    preview = engine.movement_preview(state, ship, plan="0")
    assert preview["commitable"], preview["errors"]
    # 完整 MOVEMENT_PLANNING 批次复核：该舰 plan "0" 必须被 validate_orders 放行。
    engine.submit_orders(state.game_id, OrderBatch(side=Side.ALLIES, phase=Phase.REINFORCEMENT))
    engine.submit_orders(state.game_id, OrderBatch(side=Side.AXIS, phase=Phase.REINFORCEMENT))
    engine.advance(state.game_id)
    assert engine.get(state.game_id).phase == Phase.MOVEMENT_PLANNING
    active = [s for s in engine.get(state.game_id).ships.values() if s.side == Side.AXIS and s.position]
    movement = []
    for s in active:
        if s.id == ship.id:
            movement.append(MovementOrder(ship_id=s.id, plan="0"))
            continue
        reachable = engine.movement_candidates(engine.get(state.game_id), s)["reachable"]
        movement.append(MovementOrder(ship_id=s.id, plan=reachable[0]["plan"] if reachable else "0"))
    result = engine.validate_orders(
        engine.get(state.game_id).game_id,
        OrderBatch(side=Side.AXIS, phase=Phase.MOVEMENT_PLANNING, movement=movement),
    )
    assert result.valid, result.errors


def test_cornered_forced_circle_ship_can_legally_stay() -> None:
    """舰首动 advance 不可进（贴地图边朝场外）+ 圆周强制：无法执行圆周指令，
    引擎须放行「原地停留」（plan "0"），否则该舰不存在任何合法订单
    （IBS-U-USN-DUNCAN M1/heading5 贴边圆周死锁回归）。"""
    from iron_bottom_sound.models import HexCoord

    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=7, game_id="circle-corner")
    ship = axis_ship(engine, state.game_id)
    # 找一个正前方在场外（neighbor 抛 ValueError → 首动 advance 不可进）且自身非陆的贴边格。
    corner: HexCoord | None = None
    corner_heading = 1
    for q in range(34):
        for row in range(27):
            pos = HexCoord(q=q, r=row - (q - (q & 1)) // 2)
            if pos.label in state.land_hexes:
                continue
            for heading in range(1, 7):
                try:
                    pos.neighbor(heading)
                except ValueError:
                    corner, corner_heading = pos, heading
                    break
            if corner:
                break
        if corner:
            break
    assert corner is not None, "地图应存在贴边格"
    ship.position = corner
    ship.heading = corner_heading
    ship.forced_circle_turns = 1
    ship.forced_turn_side = "port"
    assert engine._advance_impossible(state, ship)
    candidates = engine.movement_candidates(state, ship, include_plans=False)
    assert candidates["min_cost"] == 0
    assert any(
        entry["label"] == ship.position.label and entry["cost"] == 0
        for entry in candidates["reachable"]
    ), "原地停留必须是可达状态"
    preview = engine.movement_preview(state, ship, plan="0")
    assert preview["commitable"], preview["errors"]


def test_legal_actions_embeds_movement_candidates() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=7, game_id="legal-actions")
    engine.submit_orders(state.game_id, OrderBatch(side=Side.AXIS, phase=Phase.REINFORCEMENT))
    engine.submit_orders(state.game_id, OrderBatch(side=Side.ALLIES, phase=Phase.REINFORCEMENT))
    engine.advance(state.game_id)
    assert engine.get(state.game_id).phase == Phase.MOVEMENT_PLANNING
    ship = axis_ship(engine, state.game_id)
    actions = engine.legal_actions(state.game_id, Side.AXIS)
    assert actions
    hint = actions[0].schema_hint
    assert "movement_candidates" in hint
    candidates = hint["movement_candidates"]
    assert any(entry["ship_id"] == ship.id for entry in candidates)
    enemy_ids = {ship.id for ship in state.ships.values() if ship.side == Side.ALLIES}
    assert not ({entry["ship_id"] for entry in candidates} & enemy_ids)


def test_observation_exposes_own_forced_fields_only() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=7, game_id="observe-forced")
    ship = axis_ship(engine, state.game_id)
    ship.turn_limit_degrees = 60
    ship.forced_speed = 4
    ship.forced_circle_turns = 1
    ship.forced_turn_side = "port"
    axis_observation = engine.observe(state.game_id, Side.AXIS)
    allies_observation = engine.observe(state.game_id, Side.ALLIES)
    axis_public = next(entry for entry in axis_observation.ships if entry.id == ship.id)
    assert axis_public.turn_limit_degrees == 60
    assert axis_public.forced_circle_turns == 1
    assert axis_public.forced_turn_side == "port"
    assert axis_public.forced_speed == 4
    allies_public = next(entry for entry in allies_observation.ships if entry.id == ship.id)
    assert allies_public.turn_limit_degrees is None
    assert allies_public.forced_circle_turns == 0
    assert allies_public.forced_turn_side is None
    assert allies_public.forced_speed is None


def test_movement_preview_api_shape_and_side_checks() -> None:
    client = TestClient(app)
    game_id = game_in_movement_planning(client)
    ship = axis_ship(api_engine, game_id)
    response = client.post(
        f"/games/{game_id}/movement-preview",
        headers={"X-Player-Side": "axis"},
        json={"ship_id": ship.id, "plan": "1S"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ship_id"] == ship.id
    assert body["valid"] is True
    assert body["commitable"] is True
    assert body["plan"] == "1S"
    assert "trajectory" in body and "next_options" in body and "reachable" in body
    # enemy ships are off-limits
    enemy = next(
        ship for ship in api_engine.get(game_id).ships.values()
        if ship.side.value == "allies" and ship.position is not None
    )
    forbidden = client.post(
        f"/games/{game_id}/movement-preview",
        headers={"X-Player-Side": "axis"},
        json={"ship_id": enemy.id, "plan": "1"},
    )
    assert forbidden.status_code == 403


def test_movement_preview_api_read_only_and_wrong_phase() -> None:
    client = TestClient(app)
    game_id = game_in_movement_planning(client)
    before = len(api_engine.get(game_id).events)
    ship = axis_ship(api_engine, game_id)
    client.post(
        f"/games/{game_id}/movement-preview",
        headers={"X-Player-Side": "axis"},
        json={"ship_id": ship.id, "commands": ["advance"]},
    )
    assert len(api_engine.get(game_id).events) == before  # nothing was recorded
    # wrong phase (after moving on to torpedo planning) is rejected
    api_engine.submit_orders(game_id, full_movement_batch(game_id, Side.AXIS))
    api_engine.submit_orders(game_id, full_movement_batch(game_id, Side.ALLIES))
    api_engine.advance(game_id)
    assert api_engine.get(game_id).phase == Phase.TORPEDO_PLANNING
    wrong_phase = client.post(
        f"/games/{game_id}/movement-preview",
        headers={"X-Player-Side": "axis"},
        json={"ship_id": ship.id, "plan": "1"},
    )
    assert wrong_phase.status_code == 409
