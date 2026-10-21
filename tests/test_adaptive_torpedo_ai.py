"""Adaptive torpedo tactics, with realistic-mode Erma as the primary gate."""

from iron_bottom_sound.engine import IronBottomEngine, ORDER_PHASES
from iron_bottom_sound.llm import LLMPlayerSession
from iron_bottom_sound.match import run_match
from iron_bottom_sound.models import GameOptions, HexCoord, Phase, Side, TorpedoTrack
from iron_bottom_sound.realistic_command import RealisticCommander
from iron_bottom_sound.tactical import PROFILES, TacticalCommander
from iron_bottom_sound.torpedo_tactics import AdaptiveTorpedoPlanner, TorpedoDoctrine, CounterfactualResponse, _route_key
import pytest


def _uncached_counterfactual(routes, lane):
    """Pre-optimization algorithm, retained as an exact old-policy oracle."""
    baseline = max(routes, key=lambda route: (route.base_utility, _route_key(route)))
    def threat(route):
        hits = len(lane.intersection(route.path))
        near = 0
        if not hits:
            lane_hexes = [HexCoord.from_label(label) for label in lane]
            near = sum(1 for label in route.path if lane_hexes and
                       min(HexCoord.from_label(label).distance(cell) for cell in lane_hexes) <= 1)
        return hits * 4.0 + near * .75
    response = max(routes, key=lambda route: (route.base_utility - threat(route), _route_key(route)))
    changed = _route_key(baseline) != _route_key(response)
    return CounterfactualResponse(
        ship_id=baseline.ship_id, baseline_route=_route_key(baseline), threatened_route=_route_key(response),
        forced_deviation=HexCoord.from_label(baseline.final_hex).distance(HexCoord.from_label(response.final_hex)),
        speed_loss=max(0, baseline.speed - response.speed),
        fire_position_loss=max(0., baseline.base_utility - response.base_utility),
        crossing_t_loss=max(0., baseline.crossing_t_value - response.crossing_t_value),
        formation_split=max(0., baseline.formation_cohesion - response.formation_cohesion),
        local_force_ratio_gain=.5 if changed and threat(baseline) > 0 else 0., route_changed=changed,
    )


def test_torpedo_performance_optimization_preserves_entire_legacy_decision(monkeypatch):
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=41, movement_timing="legacy-mf-v1")
    _drive_to(engine, state.game_id, Phase.TORPEDO_PLANNING)
    planner = AdaptiveTorpedoPlanner(PROFILES["adaptive"])
    optimized = planner.analyze(engine, state, Side.AXIS)
    monkeypatch.setattr(AdaptiveTorpedoPlanner, "_counterfactual", staticmethod(_uncached_counterfactual))
    reference = AdaptiveTorpedoPlanner(PROFILES["adaptive"]).analyze(engine, state, Side.AXIS)
    assert optimized == reference


def test_lane_neighbourhood_is_exact_for_empty_hit_near_and_distant_lanes():
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=41)
    planner = AdaptiveTorpedoPlanner(PROFILES["adaptive"])
    routes = planner.enemy_routes(engine, state, Side.AXIS)
    targets = sorted({route.ship_id for route in routes})
    for target in targets:
        choices = [route for route in routes if route.ship_id == target]
        for lane in (set(), {choices[0].path[0]}, {"A1", "B1"}, set(choices[-1].path)):
            assert planner._counterfactual(choices, lane) == _uncached_counterfactual(choices, lane)


def test_torpedo_geometry_reuse_preserves_every_legacy_engine_candidate():
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=41)
    _drive_to(engine, state.game_id, Phase.TORPEDO_PLANNING)
    actual = engine.torpedo_tactical_combos(state, Side.AXIS)
    visible = sorted(ship.id for ship in engine.observe(state.game_id, Side.AXIS).ships
                     if ship.side != Side.AXIS and not ship.sunk and ship.position)
    friendly = {ship.id: {ship.position.label} for ship in state.ships.values()
                if ship.side == Side.AXIS and not ship.sunk and ship.position}
    for trajectory in engine.sealed_movement_trajectories(state, Side.AXIS)["trajectories"]:
        friendly.setdefault(trajectory["ship_id"], set()).update(item["label"] for item in trajectory["trajectory"])
    reference = []
    for target_id in visible:
        for combo in engine._assist_launch_combos(state, Side.AXIS):
            evaluated = engine._assist_evaluate(state, state.ships[target_id], combo, friendly)
            if evaluated.get("blocked_reason") or evaluated.get("friendly_risk"):
                continue
            evaluated["target_id"] = target_id
            evaluated["target_name"] = state.ships[target_id].name
            for count in range(1, evaluated["salvo_size"] + 1):
                row = dict(evaluated, salvo_size=count)
                if row.get("aspect") and row.get("modifier") is not None:
                    row["expected_hits"] = engine.expected_torpedo_hits(row["aspect"], row["modifier"], count)
                reference.append(row)
    reference.sort(key=lambda row: tuple(row[key] for key in (
        "ship_id", "launcher_id", "launch_at_mf", "launch_side", "launch_angle", "setting_index", "target_id", "salvo_size")))
    assert actual == reference


def _drive_to(engine: IronBottomEngine, game_id: str, phase: Phase, realistic: bool = False):
    sessions = {
        side: LLMPlayerSession(
            side,
            RealisticCommander(profile=PROFILES["adaptive"])
            if realistic else TacticalCommander(profile=PROFILES["balanced"]),
        ) for side in Side
    }
    state = engine.get(game_id)
    for _ in range(60):
        if state.phase == phase:
            return state
        if state.phase in ORDER_PHASES:
            for side in Side:
                result = engine.submit_orders(game_id, sessions[side].choose_orders(engine, game_id))
                assert result.valid, result.errors
        engine.advance(game_id)
    raise AssertionError(f"did not reach {phase}")


def test_engine_keeps_partial_salvos_but_adaptive_orders_are_full_legal_and_deterministic() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=41, game_id="adaptive-partial")
    state = _drive_to(engine, state.game_id, Phase.TORPEDO_PLANNING)
    rows = engine.torpedo_tactical_combos(state, Side.AXIS)
    counts = {}
    for row in rows:
        counts.setdefault((row["ship_id"], row["launcher_id"]), set()).add(row["salvo_size"])
    assert any({1, 2}.issubset(values) for values in counts.values())

    commander = TacticalCommander(profile=PROFILES["adaptive"])
    first_plan, first, _ = commander.choose_plan(engine, state.game_id, Side.AXIS)
    second_plan, second, _ = TacticalCommander(profile=PROFILES["adaptive"]).choose_plan(
        engine, state.game_id, Side.AXIS
    )
    assert first == second
    assert first_plan.tactical_analysis == second_plan.tactical_analysis
    assert engine.validate_orders(state.game_id, first).valid
    assert first.torpedoes
    for order in first.torpedoes:
        launcher = next(item for item in state.ships[order.ship_id].torpedo_launchers if item.id == order.launcher_id)
        assert order.count == launcher.loaded
    assert first_plan.tactical_analysis["doctrine"] in {item.value for item in TorpedoDoctrine}
    assert len(first_plan.tactical_analysis["top_candidates"]) <= 3


def test_blind_unobserved_enemy_torpedo_never_enters_movement_pressure() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=42, game_id="adaptive-hidden-track")
    state = _drive_to(engine, state.game_id, Phase.MOVEMENT_PLANNING)
    state.options.optional_rules.blind_torpedoes = True
    enemy = next(ship for ship in state.ships.values() if ship.side == Side.ALLIES and ship.position)
    state.torpedo_tracks.append(TorpedoTrack(
        id="hidden-track", side=Side.ALLIES, launcher_ship_id=enemy.id,
        torpedo_type=enemy.torpedo_type or "test", position=HexCoord(q=10, r=10),
        heading=1, speed_cycle=(2, 2, 2), range_remaining=10, launched_turn=state.turn,
        hidden=True,
    ))
    assert TacticalCommander._visible_torpedo_threat(engine, state, Side.AXIS) == {}
    state.torpedo_tracks[-1].contact_ship_ids.append(
        next(ship.id for ship in state.ships.values() if ship.side == Side.AXIS)
    )
    assert TacticalCommander._visible_torpedo_threat(engine, state, Side.AXIS)


def test_route_hypotheses_are_public_deterministic_and_bounded() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=43, game_id="adaptive-routes")
    planner = AdaptiveTorpedoPlanner(PROFILES["adaptive"])
    first = planner.enemy_routes(engine, state, Side.AXIS)
    second = planner.enemy_routes(engine, state, Side.AXIS)
    assert first == second
    per_ship = {}
    for route in first:
        per_ship[route.ship_id] = per_ship.get(route.ship_id, 0) + 1
    assert per_ship and max(per_ship.values()) <= 24


@pytest.mark.parametrize("profile_name", [
    "direct_attack", "area_denial", "break_crossing_t", "formation_split",
    "crossfire", "cover_withdrawal",
])
def test_each_torpedo_specialist_records_its_explainable_doctrine(profile_name: str) -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=44, game_id=f"specialist-{profile_name}")
    state = _drive_to(engine, state.game_id, Phase.TORPEDO_PLANNING)
    plan, batch, _ = TacticalCommander(profile=PROFILES[profile_name]).choose_plan(
        engine, state.game_id, Side.AXIS
    )
    assert plan.tactical_analysis["doctrine"] in {profile_name, "reserve"}
    assert engine.validate_orders(state.game_id, batch).valid


def test_realistic_erma_adaptive_match_completes_without_friendly_incidents() -> None:
    report, engine, _sessions = run_match(
        "IBS-S-EM-01", axis="tactical", allies="tactical",
        axis_profile="adaptive", allies_profile="adaptive", seed=47,
        options=GameOptions(realistic_command=True), request_limit=160,
    )
    assert report.passed, report.failure_reason
    assert report.completed and report.fallback_count == 0
    state = engine.get(report.game_id)
    assert state.turn == state.max_turns == 12
    assert not any(
        event.type in {"collision", "collision_check"} and event.payload.get("friendly")
        for event in state.events
    )
    assert not any(
        event.type == "torpedo_hit"
        and event.payload.get("attacker_side") == event.payload.get("target_side")
        for event in state.events
    )
    assert engine.replay(report.game_id).model_dump(mode="json") == state.model_dump(mode="json")
