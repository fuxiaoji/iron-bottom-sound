"""Adaptive torpedo tactics, with realistic-mode Erma as the primary gate."""

from iron_bottom_sound.engine import IronBottomEngine, ORDER_PHASES
from iron_bottom_sound.llm import LLMPlayerSession
from iron_bottom_sound.match import run_match
from iron_bottom_sound.models import GameOptions, HexCoord, Phase, Side, TorpedoTrack
from iron_bottom_sound.realistic_command import RealisticCommander
from iron_bottom_sound.tactical import PROFILES, TacticalCommander
from iron_bottom_sound.torpedo_tactics import AdaptiveTorpedoPlanner, TorpedoDoctrine
import pytest


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


def test_adaptive_orders_are_partial_salvo_capable_legal_and_deterministic() -> None:
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
