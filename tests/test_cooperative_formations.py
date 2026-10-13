"""Behavior gates for the realistic-mode cooperative AI population."""
from __future__ import annotations

from types import SimpleNamespace
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from iron_bottom_sound.engine import IronBottomEngine, ORDER_PHASES
from iron_bottom_sound.formation_tactics import (
    CooperativeFormationPlanner, crossing_t_value, friendly_conflicts,
    torpedo_contacts, visible_torpedo_forecast,
)
from iron_bottom_sound.match import run_match
from iron_bottom_sound.models import (
    FormationMovementOrder, FormationSpeedDecision, FormationState, GameOptions, HexCoord, OrderBatch,
    MovementOrder, Phase, Side, TorpedoTrack,
)
from iron_bottom_sound.realistic_command import RealisticCommander, expand_movement_orders, rebuild_guide_trail, _withdrawal_order, _withdrawal_order_reference
from iron_bottom_sound.tactical import PROFILES
from iron_bottom_sound.torpedo_tactics import _safe_step


NEW_PROFILES = [name for name in PROFILES if name.startswith("rc_")]


@pytest.mark.parametrize("scenario", [f"IBS-S-{number:02d}" for number in range(1, 15)] + ["IBS-S-EM-01", "IBS-S-FM-01"])
def test_latest_scenarios_accept_cooperative_setup_without_overlapping_columns(scenario):
    engine = IronBottomEngine()
    state = engine.reset(scenario, 91, GameOptions(realistic_command=True, battle_report=False))
    before = {ship.id: ship.position for ship in state.ships.values()}
    for side in Side:
        batch = RealisticCommander(PROFILES["rc_coordinated"]).choose_orders(engine, state.game_id, side)
        assert engine.submit_orders(state.game_id, batch).valid
    assert before == {ship.id: ship.position for ship in state.ships.values()}
    engine.advance(state.game_id)
    assert state.phase != Phase.FORMATION_SETUP
    positions = [ship.position for ship in state.ships.values() if ship.position and not ship.sunk]
    assert len(positions) == len(set(positions))


def drive_to(engine, state, phase):
    commander = RealisticCommander()
    for _ in range(60):
        if state.phase == phase:
            return
        if state.phase in ORDER_PHASES:
            for side in Side:
                result = engine.submit_orders(state.game_id, commander.choose_orders(engine, state.game_id, side))
                assert result.valid, result.errors
        engine.advance(state.game_id)
    raise AssertionError(f"Did not reach {phase}")


def fleet_fixture():
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-EM-01", 81, GameOptions(realistic_command=True))
    heavy = [ship for ship in state.ships.values() if ship.side == Side.AXIS and ship.ship_type == "BB"][:2]
    light = [ship for ship in state.ships.values() if ship.side == Side.AXIS and ship.ship_type == "DD"][:4]
    enemies = [ship for ship in state.ships.values() if ship.side == Side.ALLIES][:2]
    state.ships = {ship.id: ship for ship in heavy + light + enemies}
    state.phase = Phase.MOVEMENT_PLANNING
    state.land_hexes.clear()
    state.coast_hexes.clear()
    state.visibility = {side.value: 50 for side in Side}
    state.formations.clear()
    for index, members in enumerate((heavy, light[:2], light[2:])):
        fid = f"axis-task-{index}"
        leader = HexCoord(q=12 + index * 3, r=10 + index * 2)
        for member_index, ship in enumerate(members):
            ship.position = leader if member_index == 0 else leader.neighbor(5)
            ship.heading = 2
            ship.previous_speed = ship.current_speed = 3
            ship.formation_id = fid
        state.formations[fid] = FormationState(
            id=fid, name=fid, side=Side.AXIS, ship_ids=[ship.id for ship in members],
            leader_id=members[0].id, flagship_id=members[0].id,
            reserve_flagship_id=members[1].id, heading=2, speed=3,
            guide_trail=[members[1].position, members[0].position],
        )
    for index, ship in enumerate(enemies):
        ship.position = HexCoord(q=22, r=16 + index)
        ship.heading = 5
        ship.previous_speed = ship.current_speed = 3
    baseline = OrderBatch(
        side=Side.AXIS, phase=Phase.MOVEMENT_PLANNING,
        formation_movement=[FormationMovementOrder(formation_id=fid, leader_plan="3") for fid in state.formations],
    )
    assert engine.validate_orders(state.game_id, baseline).valid
    return engine, state, baseline


def paths_for(engine, state, batch):
    prepared, errors, _ = expand_movement_orders(engine, state, batch)
    assert not errors, errors
    return CooperativeFormationPlanner._paths(engine, state, prepared)[0]


def test_cooperation_assigns_light_wings_to_opposite_flanks_and_main_partner():
    engine, state, baseline = fleet_fixture()
    planner = CooperativeFormationPlanner(PROFILES["rc_coordinated"])
    missions = planner.missions(engine, state, Side.AXIS, engine.observe(state.game_id, Side.AXIS), baseline)
    wings = [item for item in missions if item.role == "torpedo_wing"]
    assert len(wings) == 2
    assert {item.flank for item in wings} == {-1, 1}
    assert {item.partner_id for item in wings} == {"axis-task-0"}
    assert len({item.target_id for item in missions}) == 1
    assert wings[0].station != wings[1].station


def test_southern_battle_line_engages_local_enemy_and_has_local_partner():
    engine, state, baseline = fleet_fixture()
    northern = next(ship for ship in state.ships.values() if ship.side == Side.ALLIES)
    southern = [ship for ship in state.ships.values() if ship.side == Side.ALLIES][1]
    northern.position = HexCoord.from_label("T10")
    southern.position = HexCoord.from_label("T29")
    formation = state.formations["axis-task-2"]
    for index, sid in enumerate(formation.ship_ids):
        state.ships[sid].position = HexCoord.from_label(f"N{27-index}")
    missions = CooperativeFormationPlanner(PROFILES["rc_coordinated"]).missions(
        engine, state, Side.AXIS, engine.observe(state.game_id, Side.AXIS), baseline,
    )
    local = next(item for item in missions if item.formation_id == formation.id)
    assert local.target_id == southern.id


def test_column_with_sunk_leader_and_last_survivor_detaching_can_be_planned():
    engine, state, _baseline = fleet_fixture()
    formation = state.formations["axis-task-1"]
    dead, survivor = [state.ships[sid] for sid in formation.ship_ids]
    dead.sunk = True
    dead.hull = 0
    survivor.forced_circle_turns = 2
    survivor.forced_turn_side = "port"
    baseline = RealisticCommander(PROFILES["adaptive"]).choose_orders(engine, state.game_id, Side.AXIS)
    assert engine.validate_orders(state.game_id, baseline).valid
    batch, _intents, audit = CooperativeFormationPlanner(PROFILES["rc_coordinated"]).optimize(
        engine, state, Side.AXIS, baseline,
    )
    assert engine.validate_orders(state.game_id, batch).valid
    assert any(row["formation_id"] == formation.id and row["state"] == "withdraw" for row in audit["formations"])


def test_search_without_published_zones_uses_only_map_geometry(monkeypatch):
    engine, state, baseline = fleet_fixture()
    state.visibility = {side.value: 0 for side in Side}
    monkeypatch.setattr("iron_bottom_sound.formation_tactics.public_search_target", lambda *_: None)
    planner = CooperativeFormationPlanner(PROFILES["rc_coordinated"])
    first = planner.missions(engine, state, Side.AXIS, engine.observe(state.game_id, Side.AXIS), baseline)
    assert all(row.state == "search" and row.station is not None and row.target_id is None for row in first)
    for enemy in state.ships.values():
        if enemy.side != Side.AXIS:
            enemy.position = HexCoord.from_label("AA30")
    second = planner.missions(engine, state, Side.AXIS, engine.observe(state.game_id, Side.AXIS), baseline)
    assert first == second


def test_fleet_gunnery_assignments_are_engine_generated_and_read_only():
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 81, GameOptions(realistic_command=True))
    drive_to(engine, state, Phase.GUNNERY)
    before = state.model_dump(mode="json")
    recommendations = engine.gunnery_assist(state, Side.AXIS)["recommendations"]
    orders = RealisticCommander(PROFILES["rc_coordinated"]).choose_orders(engine, state.game_id, Side.AXIS)
    assert [(order.ship_id, order.primary_target, [item.mount_id for item in order.mounts]) for order in orders.gunnery] == [
        (item["ship_id"], item["target_id"], item["mount_ids"]) for item in recommendations
    ]
    assert engine.validate_orders(state.game_id, orders).valid
    assert state.model_dump(mode="json") == before


def test_engine_gun_pressure_speed_parameter_preserves_legacy_default():
    engine, state, _baseline = fleet_fixture()
    ship = next(item for item in state.ships.values() if item.side == Side.AXIS)
    target = ship.position.neighbor(1).neighbor(1)
    legacy = engine.ship_gun_pressure(state, ship, target_hexes=[target])
    assert legacy == engine.ship_gun_pressure(state, ship, target_hexes=[target], target_speed=4)
    stopped = engine.ship_gun_pressure(state, ship, target_hexes=[target], target_speed=0)
    assert stopped >= legacy > 0


@pytest.mark.parametrize("speed,heading", [(0, 1), (1, 3), (2, 5)])
def test_fast_autonomous_withdrawal_matches_the_old_controller_exactly(speed, heading):
    engine, state, _baseline = fleet_fixture()
    ship = state.ships[state.formations["axis-task-1"].leader_id]
    ship.command_status = "retreating"
    ship.withdrawal_edge = "west"
    ship.current_speed = ship.previous_speed = speed
    ship.heading = heading
    before = state.model_dump(mode="json")
    assert _withdrawal_order(engine, state, ship) == _withdrawal_order_reference(engine, state, ship)
    assert state.model_dump(mode="json") == before


def test_final_command_repair_does_not_cycle_between_detach_and_reduce(monkeypatch):
    """Two same-pass errors used to overwrite a detach decision with reduce."""
    import iron_bottom_sound.realistic_command as command
    engine, state, _baseline = fleet_fixture()
    formation = state.formations["axis-task-1"]
    offender = formation.ship_ids[-1]
    original_expand = command.expand_movement_orders
    def interacting_errors(engine_arg, state_arg, batch):
        prepared, errors, detached = original_expand(engine_arg, state_arg, batch)
        order = next((item for item in batch.formation_movement if item.formation_id == formation.id), None)
        forced = set(order.speed_decision.detach_ship_ids) if order and order.speed_decision and order.speed_decision.action == "detach" else set()
        if offender not in forced:
            errors = [f"{formation.id}: {offender} follower speed 6 outside 0-4",
                      f"{formation.id}: reduced speed is not legal for every member"]
        return prepared, errors, detached
    monkeypatch.setattr(command, "expand_movement_orders", interacting_errors)
    batch = RealisticCommander(PROFILES["adaptive"]).choose_orders(engine, state.game_id, Side.AXIS)
    order = next(item for item in batch.formation_movement if item.formation_id == formation.id)
    assert order.speed_decision.action == "detach"
    assert offender in order.speed_decision.detach_ship_ids
    assert engine.validate_orders(state.game_id, batch).valid


def test_rebuilt_wake_and_partial_planner_both_exclude_sunk_old_leader():
    engine, state, _baseline = fleet_fixture()
    formation = state.formations["axis-task-0"]
    dead, survivor = [state.ships[sid] for sid in formation.ship_ids]
    dead.sunk, dead.hull = True, 0
    dead.position = HexCoord.from_label("X10")
    borrowed = state.formations["axis-task-1"]
    formation.ship_ids += borrowed.ship_ids
    del state.formations[borrowed.id]
    previous = survivor.position
    for sid in formation.ship_ids[2:]:
        ship = state.ships[sid]
        ship.formation_id = formation.id
        ship.heading = survivor.heading
        previous = previous.neighbor(5)
        ship.position = previous
    formation.guide_trail = []
    trail = rebuild_guide_trail(state, formation)
    assert trail[-1] == survivor.position
    assert dead.position not in trail
    baseline = RealisticCommander(PROFILES["adaptive"]).choose_orders(engine, state.game_id, Side.AXIS)
    assert engine.validate_orders(state.game_id, baseline).valid
    batch, _intents, _audit = CooperativeFormationPlanner(PROFILES["rc_coordinated"]).optimize(engine, state, Side.AXIS, baseline)
    assert engine.validate_orders(state.game_id, batch).valid


@pytest.mark.parametrize("detach_index", [0, 1])
def test_partial_candidates_preserve_rebuilt_wake_when_a_member_detaches(detach_index, monkeypatch):
    engine, state, baseline = fleet_fixture()
    formation = state.formations["axis-task-0"]
    borrowed = state.formations["axis-task-1"]
    extra = borrowed.ship_ids.pop()
    formation.ship_ids.append(extra)
    ship = state.ships[extra]
    ship.formation_id = formation.id
    ship.heading = state.ships[formation.leader_id].heading
    ship.position = state.ships[formation.ship_ids[1]].position.neighbor(5)
    formation.guide_trail = []
    baseline.formation_movement[0].speed_decision = FormationSpeedDecision(
        formation_id=formation.id, action="detach",
        detach_ship_ids=[formation.ship_ids[detach_index]],
    )
    assert engine.validate_orders(state.game_id, baseline).valid
    before = state.model_dump(mode="json")
    original = CooperativeFormationPlanner._route
    compared = []

    def checked(self, engine_arg, state_arg, baseline_arg, order, mission, enemies):
        route = original(self, engine_arg, state_arg, baseline_arg, order, mission, enemies)
        full_batch = baseline_arg.model_copy(deep=True)
        full_batch.formation_movement = [order if item.formation_id == order.formation_id else item
                                         for item in full_batch.formation_movement]
        prepared, errors, _ = expand_movement_orders(engine_arg, state_arg, full_batch)
        valid = not errors and engine_arg.validate_orders(state_arg.game_id, prepared, _prepared=True).valid
        assert (route is not None) == valid
        if route:
            paths = CooperativeFormationPlanner._paths(engine_arg, state_arg, prepared)[0]
            assert route.paths == {sid: paths[sid] for sid in state_arg.formations[order.formation_id].ship_ids}
            compared.append(order.formation_id)
        return route

    monkeypatch.setattr(CooperativeFormationPlanner, "_route", checked)
    batch, _intents, _audit = CooperativeFormationPlanner(PROFILES["rc_coordinated"]).optimize(
        engine, state, Side.AXIS, baseline,
    )
    assert compared.count(formation.id) > 3
    assert engine.validate_orders(state.game_id, batch).valid
    assert state.model_dump(mode="json") == before


def overlapping_stop_fixture():
    engine, state, _baseline = fleet_fixture()
    ships = [ship for ship in state.ships.values() if ship.side == Side.AXIS][:3]
    state.ships = {ship.id: ship for ship in ships}
    state.formations = {}
    start = HexCoord.from_label("N18")
    for index, ship in enumerate(ships):
        ship.position = start
        ship.heading = 2 if index == 0 else 5
        ship.current_speed = ship.previous_speed = 1
        ship.formation_id = None
        start = start.neighbor(2)
    state.phase = Phase.MOVEMENT_RESOLUTION
    state.sealed_orders = {f"{state.turn}:{Phase.MOVEMENT_PLANNING.value}": {Side.AXIS.value: OrderBatch(
        side=Side.AXIS, phase=Phase.MOVEMENT_PLANNING,
        movement=[MovementOrder(ship_id=ship.id, plan="1" if index < 2 else "2") for index, ship in enumerate(ships)],
    )}}
    return engine, state


def test_overlapping_friendly_swap_and_same_hex_groups_stop_all_participants():
    engine, state = overlapping_stop_fixture()
    before = {ship.id: ship.position for ship in state.ships.values()}
    engine._resolve_movement(state)
    assert {ship.id: ship.position for ship in state.ships.values()} == before
    stopped = {sid for event in state.events if event.type == "formation_emergency_stop"
               for sid in event.payload.get("ship_ids", [])}
    assert stopped == set(before)


def test_overlapping_emergency_stop_trace_is_identical_across_python_hash_seeds():
    script = '''
import json, sys
sys.path.insert(0, 'tests')
from test_cooperative_formations import overlapping_stop_fixture
engine, state = overlapping_stop_fixture()
engine._resolve_movement(state)
print(json.dumps({'positions': {ship.id: ship.position.label for ship in state.ships.values()},
                  'stops': [event.payload for event in state.events if event.type == 'formation_emergency_stop'],
                  'rng_counter': state.rng_counter}, sort_keys=True))
'''
    results = []
    for seed in ("1", "77", "999"):
        result = subprocess.run([sys.executable, "-c", script], cwd=Path(__file__).resolve().parents[1],
                                env=dict(os.environ, PYTHONHASHSEED=seed), text=True, capture_output=True, timeout=30)
        assert result.returncode == 0, result.stderr
        results.append(result.stdout)
    assert results[0] == results[1] == results[2]


def test_crossing_t_rewards_broadside_across_bow_not_stern_or_bow_on():
    target = SimpleNamespace(position=HexCoord(q=15, r=15), heading=6)
    ahead = HexCoord(q=15, r=8)
    behind = HexCoord(q=15, r=22)
    assert crossing_t_value(ahead, 2, target, 7) > crossing_t_value(ahead, 6, target, 7)
    assert crossing_t_value(ahead, 2, target, 7) > crossing_t_value(behind, 2, target, 7)


def test_reservations_include_stationary_follower_and_hex_swaps():
    a, b, c = HexCoord(q=9, r=9), HexCoord(q=10, r=9), HexCoord(q=11, r=9)
    assert friendly_conflicts({"leader": [a, b], "follower": [b, a]})
    assert friendly_conflicts({"leader": [a, b, c], "follower": [c]}) == [("follower", "leader", 2)]
    assert not friendly_conflicts({"leader": [a, b, c], "follower": [b, c, c.neighbor(2)]})


def test_two_columns_yield_before_their_planned_intersection():
    engine, state, baseline = fleet_fixture()
    intersection = HexCoord(q=17, r=16)
    for fid, heading in (("axis-task-1", 1), ("axis-task-2", 5)):
        formation = state.formations[fid]
        reverse = ((heading + 2) % 6) + 1
        leader = intersection.neighbor(reverse).neighbor(reverse)
        members = [state.ships[item] for item in formation.ship_ids]
        members[0].position, members[1].position = leader, leader.neighbor(reverse)
        for ship in members:
            ship.heading = heading
        formation.heading = heading
        formation.guide_trail = [members[1].position, members[0].position]
    assert friendly_conflicts(paths_for(engine, state, baseline))
    batch, _intents, audit = CooperativeFormationPlanner(PROFILES["rc_coordinated"]).optimize(engine, state, Side.AXIS, baseline)
    assert engine.validate_orders(state.game_id, batch).valid
    assert not friendly_conflicts(paths_for(engine, state, batch))
    assert audit["predicted_friendly_conflicts"] == 0
    assert not any(item.speed_decision and item.speed_decision.emergency_stop for item in batch.formation_movement)


@pytest.mark.parametrize("track_side", list(Side))
def test_dodges_visible_enemy_and_friendly_torpedo_along_route(track_side):
    engine, state, baseline = fleet_fixture()
    leader = state.ships[state.formations["axis-task-1"].leader_id]
    hit_hex = leader.position.neighbor(leader.heading).neighbor(leader.heading)
    track = TorpedoTrack(
        id="crossing-torpedo", side=track_side,
        launcher_ship_id=leader.id if track_side == Side.AXIS else next(ship.id for ship in state.ships.values() if ship.side == Side.ALLIES),
        torpedo_type="test", position=hit_hex.neighbor(6).neighbor(6), heading=3,
        speed_cycle=(2, 2, 2), range_remaining=10, launched_turn=state.turn,
    )
    state.torpedo_tracks.append(track)
    threats = visible_torpedo_forecast(engine, state, engine.observe(state.game_id, Side.AXIS))
    assert torpedo_contacts(paths_for(engine, state, baseline), threats) > 0
    batch, _intents, audit = CooperativeFormationPlanner(PROFILES["rc_coordinated"]).optimize(engine, state, Side.AXIS, baseline)
    assert torpedo_contacts(paths_for(engine, state, batch), threats) == 0
    assert audit["predicted_torpedo_contacts"] == 0
    assert any(row["state"] == "evade" for row in audit["formations"])


def test_hidden_torpedo_and_enemy_orders_do_not_change_decisions():
    engine, state, _baseline = fleet_fixture()
    commander = RealisticCommander(PROFILES["rc_coordinated"])
    state.options.optional_rules.blind_torpedoes = True
    before_state = state.model_dump_json()
    first_plan, first, _ = commander.choose_plan(engine, state.game_id, Side.AXIS)
    assert state.model_dump_json() == before_state
    enemy = next(ship for ship in state.ships.values() if ship.side == Side.ALLIES)
    state.torpedo_tracks.append(TorpedoTrack(
        id="private-torpedo", side=Side.ALLIES, launcher_ship_id=enemy.id,
        torpedo_type="test", position=HexCoord(q=14, r=14), heading=5,
        speed_cycle=(5, 5, 5), range_remaining=12, launched_turn=state.turn, hidden=True,
    ))
    state.submitted_orders[Side.ALLIES.value] = OrderBatch(side=Side.ALLIES, phase=state.phase)
    next_plan, next_batch, _ = RealisticCommander(PROFILES["rc_coordinated"]).choose_plan(engine, state.game_id, Side.AXIS)
    assert first == next_batch
    assert first_plan.tactical_analysis == next_plan.tactical_analysis
    assert "private-torpedo" not in str(next_plan.model_dump())


def test_withdrawing_ship_does_not_use_hidden_enemy_positions():
    engine, state, _baseline = fleet_fixture()
    formation = state.formations["axis-task-1"]
    ship = state.ships[formation.ship_ids.pop()]
    ship.command_status, ship.withdrawal_edge = "retreating", "west"
    state.visibility = {side.value: 1 for side in Side}
    for enemy in state.ships.values():
        if enemy.side == Side.ALLIES:
            enemy.position = HexCoord(q=30, r=20)
    commander = RealisticCommander(PROFILES["rc_coordinated"])
    first = commander.choose_orders(engine, state.game_id, Side.AXIS)
    for enemy in state.ships.values():
        if enemy.side == Side.ALLIES:
            enemy.position = HexCoord(q=33, r=22)
    second = commander.choose_orders(engine, state.game_id, Side.AXIS)
    assert first == second


def test_t_hunter_actually_improves_crossing_t_station():
    engine, state, baseline = fleet_fixture()
    _batch, _intents, audit = CooperativeFormationPlanner(PROFILES["rc_t_hunter"]).optimize(engine, state, Side.AXIS, baseline)
    assert any(row["role"] == "battle_line" and row["crossing_t_after"] > row["crossing_t_before"] + 0.01
               for row in audit["formations"])


def test_search_caches_withdrawal_controller_instead_of_recomputing_for_each_candidate(monkeypatch):
    from iron_bottom_sound import realistic_command
    engine, state, baseline = fleet_fixture()
    formation = state.formations["axis-task-1"]
    ship = state.ships[formation.ship_ids.pop()]
    ship.command_status, ship.withdrawal_edge = "retreating", "west"
    original = realistic_command._withdrawal_order
    calls = []

    def counted(*args):
        calls.append(args[2].id)
        return original(*args)

    monkeypatch.setattr(realistic_command, "_withdrawal_order", counted)
    _batch, _intents, audit = CooperativeFormationPlanner(PROFILES["rc_coordinated"]).optimize(engine, state, Side.AXIS, baseline)
    assert max(row["legal_candidates"] for row in audit["formations"]) > 10
    assert len(calls) <= 3


def test_whole_formation_detachment_keeps_forced_withdrawal_paths():
    engine, state, baseline = fleet_fixture()
    formation = state.formations["axis-task-0"]
    for ship_id in formation.ship_ids:
        state.ships[ship_id].forced_circle_turns = 1
        state.ships[ship_id].forced_turn_side = "port"
    baseline.formation_movement[0].speed_decision = FormationSpeedDecision(
        formation_id=formation.id, action="detach", detach_ship_ids=formation.ship_ids,
    )
    assert engine.validate_orders(state.game_id, baseline).valid
    old_paths = paths_for(engine, state, baseline)
    batch, _intents, _audit = CooperativeFormationPlanner(PROFILES["rc_coordinated"]).optimize(engine, state, Side.AXIS, baseline)
    new_paths = paths_for(engine, state, batch)
    assert all(old_paths[item] == new_paths[item] for item in formation.ship_ids)
    assert engine.validate_orders(state.game_id, batch).valid


@pytest.mark.parametrize("profile", NEW_PROFILES)
def test_new_population_fires_safe_torpedoes_in_realistic_mode(profile):
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 44, GameOptions(realistic_command=True))
    drive_to(engine, state, Phase.TORPEDO_PLANNING)
    plan, batch, _ = RealisticCommander(PROFILES[profile]).choose_plan(engine, state.game_id, Side.AXIS)
    assert batch.torpedoes, "AI must fire when the engine offers worthwhile, friendly-safe shots"
    assert engine.validate_orders(state.game_id, batch).valid
    assert plan.tactical_analysis["selected_option_ids"]
    assert len({(order.ship_id, order.launcher_id) for order in batch.torpedoes}) == len(batch.torpedoes)
    expected_salvos = {}
    for order in batch.torpedoes:
        launcher = next(item for item in state.ships[order.ship_id].torpedo_launchers if item.id == order.launcher_id)
        assert order.count == launcher.loaded
        expected_salvos[(order.ship_id, order.launcher_id)] = launcher.loaded
    state.submitted_orders.clear()
    assert engine.submit_orders(state.game_id, batch).valid
    assert engine.submit_orders(state.game_id, OrderBatch(side=Side.ALLIES, phase=state.phase)).valid
    engine.advance(state.game_id)
    engine.advance(state.game_id)
    launched = [event for event in state.events if event.type == "torpedo_launched"]
    assert launched
    for event in launched:
        key = (event.payload["ship_id"], event.payload["launcher_id"])
        assert event.payload["salvo_size"] == expected_salvos[key]
        launcher = next(item for item in state.ships[key[0]].torpedo_launchers if item.id == key[1])
        assert launcher.loaded == 0


def test_torpedo_prediction_uses_large_map_and_terrain_boundaries():
    state = SimpleNamespace(map_columns=92, map_rows=78, land_hexes=set())
    position = HexCoord(q=70, r=10)
    assert _safe_step(state, position, 2) == position.neighbor(2, columns=92, rows=78)
    state.land_hexes.add(position.neighbor(2, columns=92, rows=78).label)
    assert _safe_step(state, position, 2) is None


def test_command_disruption_and_forced_damage_keep_engine_authority():
    engine, state, baseline = fleet_fixture()
    formation = state.formations["axis-task-0"]
    formation.disruption_turn = state.turn
    formation.locked_speed, formation.locked_heading = 3, formation.heading
    batch, _intents, audit = CooperativeFormationPlanner(PROFILES["rc_t_hunter"]).optimize(engine, state, Side.AXIS, baseline)
    disrupted = next(row for row in audit["formations"] if row["formation_id"] == formation.id)
    assert disrupted["state"] == "disrupted"
    assert disrupted["leader_plan"] == "3"
    assert engine.validate_orders(state.game_id, batch).valid


@pytest.mark.parametrize("profile", NEW_PROFILES)
def test_new_profiles_work_through_player_api_without_revealing_opponent_orders(profile, monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from iron_bottom_sound import api
    from iron_bottom_sound.storage import GameRepository
    monkeypatch.setattr(api, "engine", IronBottomEngine())
    monkeypatch.setattr(api, "repository", GameRepository(tmp_path / "cooperative.sqlite3"))
    client = TestClient(api.app)
    response = client.post("/games", json={
        "scenario_id": "IBS-S-03", "seed": 44,
        "options": {"mode": "vs_ai", "realistic_command": True, "ai_profile": profile, "battle_report": False},
    })
    assert response.status_code == 201
    game_id = response.json()["game_id"]
    own = RealisticCommander(PROFILES[profile]).choose_orders(api.engine, game_id, Side.AXIS)
    assert client.post(f"/games/{game_id}/orders", headers={"X-Player-Side": "axis"}, json=own.model_dump(mode="json")).status_code == 200
    submitted = client.post(f"/games/{game_id}/ai-opponent", headers={"X-Player-Side": "axis"}, json={"profile": profile})
    assert submitted.status_code == 200
    assert submitted.json() == {"valid": True, "ai_submitted": True}
    assert "formation_setup" not in submitted.text
    seen = set()
    for _ in range(16):
        state = api.engine.get(game_id)
        if state.turn > 1 or state.phase == Phase.COMPLETE:
            break
        if state.phase in ORDER_PHASES and state.phase != Phase.FORMATION_SETUP:
            seen.add(state.phase)
            own = RealisticCommander(PROFILES[profile]).choose_orders(api.engine, game_id, Side.AXIS)
            response = client.post(f"/games/{game_id}/orders", headers={"X-Player-Side": "axis"}, json=own.model_dump(mode="json"))
            assert response.status_code == 200, response.text
            submitted = client.post(f"/games/{game_id}/ai-opponent", headers={"X-Player-Side": "axis"}, json={"profile": profile})
            assert submitted.status_code == 200, submitted.text
            assert submitted.json() == {"valid": True, "ai_submitted": True}
        advanced = client.post(f"/games/{game_id}/advance", headers={"X-Player-Side": "axis"})
        assert advanced.status_code == 200, advanced.text
    assert {Phase.MOVEMENT_PLANNING, Phase.TORPEDO_PLANNING, Phase.GUNNERY} <= seen


@pytest.mark.parametrize("profile", NEW_PROFILES)
def test_new_population_finishes_and_replays_realistic_match(profile):
    report, engine, _sessions = run_match(
        "IBS-S-03", axis="tactical", allies="tactical", axis_profile=profile,
        allies_profile="rc_coordinated", seed=83, options=GameOptions(realistic_command=True), request_limit=200,
    )
    assert report.passed, report.failure_reason
    assert report.fallback_count == report.manual_state_changes == 0
    state = engine.get(report.game_id)
    assert not any(event.type == "collision_check" and len(event.payload.get("ships", [])) == 2
                   and len({state.ships[item].side for item in event.payload["ships"]}) == 1
                   for event in state.events)
    assert engine.replay(state.game_id).model_dump(mode="json") == state.model_dump(mode="json")
