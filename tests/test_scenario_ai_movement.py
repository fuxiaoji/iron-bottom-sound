"""Scenario planning interfaces must agree with the authoritative validator.

S-02 deliberately tests the existing endpoint implementation, not a claim that
the source's continuous adjacency requirement has been fully adjudicated.
"""
from __future__ import annotations

import pytest

from iron_bottom_sound.engine import IronBottomEngine, ORDER_PHASES
from iron_bottom_sound.models import GameOptions, MovementOrder, Phase, Side
from iron_bottom_sound.realistic_command import RealisticCommander, _withdrawal_order
from iron_bottom_sound.tactical import PROFILES


def savo_fixture():
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-10", 3, GameOptions(realistic_command=True, battle_report=False))
    state.phase = Phase.MOVEMENT_PLANNING
    state.turn = 2
    return engine, state


def test_savo_speed_cap_is_visible_to_owned_planning_interfaces():
    engine, state = savo_fixture()
    ship = state.ships["IBS-U-RAN-CANBERRA"]
    assert ship.current_speed == 2
    assert engine._legal_speed_range(ship, state.turn)[1] == 4
    assert engine.movement_speed_range(state, ship) == (0, 3)
    public = next(item for item in engine.observe(state.game_id, Side.ALLIES).ships if item.id == ship.id)
    assert public.max_legal_speed == 3
    assert not engine.movement_preview(state, ship, plan="4")["commitable"]
    candidates = engine.movement_candidates(state, ship)
    assert candidates["max_cost"] == 3
    assert candidates["reachable"]
    assert all(engine.movement_preview(state, ship, plan=item["plan"])["commitable"]
               for item in candidates["reachable"])


def test_unalerted_ship_candidates_keep_original_heading_and_speed():
    engine, state = savo_fixture()
    ship = state.ships["IBS-U-USN-VINCENNES"]
    assert ship.id not in state.scenario_state["alerted"]
    candidates = engine.movement_candidates(state, ship)
    assert candidates["min_cost"] == candidates["max_cost"] == ship.current_speed
    assert len(candidates["reachable"]) == 1
    assert candidates["reachable"][0]["plan"] == str(ship.current_speed)
    assert not engine.movement_preview(state, ship, plan=f"1P{ship.current_speed-1}")["commitable"]


def test_damage_lock_does_not_override_scenario_speed_cap():
    engine, state = savo_fixture()
    ship = state.ships["IBS-U-RAN-CANBERRA"]
    ship.forced_straight_turns = 1
    ship.forced_speed = 4
    assert engine.movement_speed_range(state, ship) == (4, 3)
    assert not engine.movement_candidates(state, ship)["reachable"]
    assert not engine.movement_preview(state, ship, plan="4")["commitable"]


@pytest.mark.parametrize("realistic,profile", [(False, "balanced"), (True, "balanced"), (True, "rc_coordinated")])
def test_s05_guaranteed_reinforcements_are_available_before_entry_orders(realistic, profile):
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-05", 2401, GameOptions(realistic_command=realistic, battle_report=False))
    commanders = {side: RealisticCommander(PROFILES[profile]) for side in Side}
    for _ in range(40):
        if state.turn == 2 and state.phase == Phase.REINFORCEMENT:
            break
        if state.phase in ORDER_PHASES:
            for side in Side:
                assert engine.submit_orders(state.game_id, commanders[side].choose_orders(engine, state.game_id, side)).valid
        engine.advance(state.game_id)
    assert state.turn == 2 and state.phase == Phase.REINFORCEMENT
    assert state.reinforcement_available and state.reinforcement_roll_done
    event = next(item for item in state.events if item.type == "reinforcement_available")
    assert event.rule.rule_id == "IBS-S-05-R4" and event.rule.pdf_page == 5
    assert event.dice is None and event.payload["automatic"]
    assert not any(item.type == "reinforcement_roll" for item in state.events)
    batches = {side: commanders[side].choose_orders(engine, state.game_id, side) for side in Side}
    assert len(batches[Side.AXIS].reinforcements) == 3
    pending = {order.ship_id for order in batches[Side.AXIS].reinforcements}
    for side in Side:
        result = engine.submit_orders(state.game_id, batches[side])
        assert result.valid, result.errors
    engine.advance(state.game_id)
    assert all(state.ships[ship_id].position for ship_id in pending)
    assert sum(item.type == "reinforcement_entered" for item in state.events) == 3


def test_s05_disabled_guns_do_not_encourage_an_unavailable_opening_salvo():
    from iron_bottom_sound.formation_tactics import CooperativeFormationPlanner
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-05", 2401, GameOptions(realistic_command=True, battle_report=False))
    commander = RealisticCommander(PROFILES["balanced"])
    while state.phase != Phase.MOVEMENT_PLANNING:
        for side in Side:
            assert engine.submit_orders(state.game_id, commander.choose_orders(engine, state.game_id, side)).valid
        engine.advance(state.game_id)
    baseline = commander.choose_orders(engine, state.game_id, Side.AXIS)
    planner = CooperativeFormationPlanner(PROFILES["rc_coordinated"])
    observation = engine.observe(state.game_id, Side.AXIS)
    missions = planner.missions(engine, state, Side.AXIS, observation, baseline)
    assert missions and all(item.state == "cover" for item in missions)
    for mission in missions:
        leader = state.ships[state.formations[mission.formation_id].leader_id]
        target = next(item for item in observation.ships if item.id == mission.target_id)
        assert mission.station.distance(target.position) > leader.position.distance(target.position)


@pytest.mark.parametrize("profile", ["balanced", "rc_coordinated", "rc_t_hunter", "rc_torpedo_wings", "rc_screen", "rc_pincer"])
def test_whole_savo_column_respects_unalerted_and_capped_followers(profile):
    engine, state = savo_fixture()
    # Setup through the real setup orders, without changing the deployment.
    state.phase = Phase.FORMATION_SETUP
    state.formation_resume_phase = Phase.MOVEMENT_PLANNING
    for side in Side:
        assert engine.submit_orders(state.game_id, RealisticCommander(PROFILES[profile]).choose_orders(
            engine, state.game_id, side,
        )).valid
    engine.advance(state.game_id)
    batch = RealisticCommander(PROFILES[profile]).choose_orders(engine, state.game_id, Side.ALLIES)
    result = engine.validate_orders(state.game_id, batch)
    assert result.valid, result.errors


def test_kula_candidates_and_autonomous_retreat_obey_current_endpoint_guard():
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-02", 3, GameOptions(battle_report=False))
    ship = state.ships["IBS-U-USN-NICHOLAS"]
    assert not engine.movement_preview(state, ship, plan="4")["commitable"]
    anchors = [item.position for item in state.ships.values()
               if item.side == Side.ALLIES and item.ship_type == "CL"]
    candidates = engine.movement_candidates(state, ship)
    assert candidates["reachable"]
    for entry in candidates["reachable"]:
        order = MovementOrder(ship_id=ship.id, plan=entry["plan"])
        trajectory, _ = engine.movement_trajectory(ship, order.plan)
        end = trajectory[-1][0] if trajectory else ship.position
        assert min(end.distance(anchor) for anchor in anchors) <= 2
        assert engine.movement_preview(state, ship, plan=order.plan)["commitable"]
    ship.command_status = "retreating"
    ship.withdrawal_edge = "north"
    order = _withdrawal_order(engine, state, ship)
    assert engine.movement_preview(state, ship, plan=order.plan)["commitable"]


def test_kula_impossible_withdrawal_is_blocked_not_disguised_as_emergency_stop():
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-02", 3, GameOptions(battle_report=False))
    ship = state.ships["IBS-U-USN-NICHOLAS"]
    # Boundary fixture for IBS-Q-022: all anchor ships are too far away to
    # satisfy the existing guard within this ship's entire legal speed range.
    from iron_bottom_sound.models import HexCoord
    ship.position = HexCoord.from_label("A1")
    ship.command_status = "retreating"
    ship.withdrawal_edge = "east"
    assert not engine.movement_candidates(state, ship)["reachable"]
    with pytest.raises(ValueError, match="withdrawal controller has no legal movement"):
        _withdrawal_order(engine, state, ship)


@pytest.mark.parametrize("scenario,seed,profile", [
    ("IBS-S-02", 1107, "balanced"), ("IBS-S-02", 1107, "rc_coordinated"),
    ("IBS-S-10", 1604, "balanced"), ("IBS-S-10", 1602, "rc_coordinated"),
])
def test_old_failure_seeds_finish_legally_and_replay(scenario, seed, profile):
    engine = IronBottomEngine()
    state = engine.reset(scenario, seed, GameOptions(realistic_command=True, battle_report=False))
    commanders = {side: RealisticCommander(PROFILES[profile if side == Side.ALLIES else "balanced"])
                  for side in Side}
    for _ in range(1500):
        if state.phase == Phase.COMPLETE:
            break
        if state.phase in ORDER_PHASES:
            for side in Side:
                result = engine.submit_orders(state.game_id, commanders[side].choose_orders(engine, state.game_id, side))
                assert result.valid, result.errors
        engine.advance(state.game_id)
    assert state.phase == Phase.COMPLETE
    assert engine.replay(state.game_id).model_dump(mode="json") == state.model_dump(mode="json")
