"""Reinforcement-candidate helper: turn-4 entry corridor, pending ships, and the
roll result surfaced to the planning UI (read-only, never placed)."""

import pytest
from fastapi.testclient import TestClient

from iron_bottom_sound.api import app, engine as api_engine
from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import (
    HexCoord,
    MovementOrder,
    OrderBatch,
    Phase,
    Side,
)


def per_side_batch(state, side: Side) -> OrderBatch:
    own = [
        ship for ship in state.ships.values()
        if ship.side == side and ship.position is not None and not ship.sunk
    ]
    return OrderBatch(
        side=side,
        phase=state.phase,
        movement=[MovementOrder(ship_id=ship.id, plan="0") for ship in own],
    )


def play_to_reinforcement_turn4(engine: IronBottomEngine, seed: int) -> tuple[object, str]:
    """Drive IBS-S-01 to the turn-4 REINFORCEMENT phase (roll already resolved)."""
    state = engine.reset("IBS-S-01", seed=seed, game_id=f"reinf-{seed}")
    guard = 0
    while state.phase != Phase.COMPLETE and guard < 100:
        guard += 1
        if state.phase == Phase.REINFORCEMENT and state.turn == 4:
            return state, state.game_id
        if state.phase in (Phase.MOVEMENT_RESOLUTION, Phase.TORPEDO_EFFECTS, Phase.FIRE_END):
            engine.advance(state.game_id)
            continue
        engine.step(state.game_id, {side: per_side_batch(state, side) for side in Side})
    raise AssertionError(f"seed {seed} never reached turn-4 reinforcement")


def corridor_hexes(state) -> list[HexCoord]:
    start, end = state.reinforcement_entry_start, state.reinforcement_entry_end
    return [
        HexCoord(q=q, r=r)
        for q in range(1, 34)
        for r in range(1, 28)
        if IronBottomEngine._reinforcement_entry_legal(state, HexCoord(q=q, r=r))
    ]


def test_candidates_success_seed_surfaces_group_and_corridor() -> None:
    engine = IronBottomEngine()
    state, _ = play_to_reinforcement_turn4(engine, seed=3)
    candidates = engine._reinforcement_candidates(state, Side.AXIS)

    assert candidates["group_available"] is True
    assert candidates["roll_result"] == {"roll": 1, "available": True}
    assert candidates["trigger_turn"] == 3
    assert candidates["arrival_turn"] == 4
    assert candidates["succeeds_on"] == [1]
    assert candidates["entry_range"] == ["E17", "U27"]

    corridor = corridor_hexes(state)
    assert len(candidates["entry_hexes"]) == len(corridor)
    assert set(candidates["entry_hexes"]) == {hexcoord.label for hexcoord in corridor}
    assert len(corridor) == 51

    pending = [
        ship for ship in state.ships.values()
        if ship.side == Side.AXIS and ship.position is None and ship.reinforcement_turn == 4
    ]
    assert len(pending) == 8
    assert [ship["ship_id"] for ship in candidates["ships"]] == sorted(ship.id for ship in pending)
    assert all(
        (ship["name"], ship["asset"], ship["max_speed"])
        for ship in candidates["ships"]
    )


def test_candidates_failure_seed_marks_group_unavailable() -> None:
    engine = IronBottomEngine()
    state, _ = play_to_reinforcement_turn4(engine, seed=1)
    candidates = engine._reinforcement_candidates(state, Side.AXIS)
    assert candidates["group_available"] is False
    assert candidates["roll_result"]["available"] is False
    # ships still surface so the UI can explain why they did not arrive
    assert len(candidates["ships"]) == 8


def test_candidates_empty_before_trigger_turn() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-01", seed=3, game_id="reinf-turn1")
    assert state.turn == 1
    candidates = engine._reinforcement_candidates(state, Side.AXIS)
    assert candidates["ships"] == []
    assert candidates["roll_result"] is None
    assert candidates["group_available"] is False


def test_candidates_only_lists_own_side() -> None:
    engine = IronBottomEngine()
    state, _ = play_to_reinforcement_turn4(engine, seed=3)
    allies = engine._reinforcement_candidates(state, Side.ALLIES)
    axis = engine._reinforcement_candidates(state, Side.AXIS)
    assert allies["ships"] == []          # no allied ships are reinforcements
    assert len(axis["ships"]) == 8


def test_legal_actions_embeds_reinforcement_candidates() -> None:
    engine = IronBottomEngine()
    state, game_id = play_to_reinforcement_turn4(engine, seed=3)
    actions = engine.legal_actions(game_id, Side.AXIS)
    assert len(actions) == 1 and actions[0].kind == "submit_phase_orders"
    hint = actions[0].schema_hint
    assert "reinforcement_candidates" in hint
    assert hint["reinforcement_candidates"]["group_available"] is True
    assert len(hint["reinforcement_candidates"]["entry_hexes"]) == 51


def test_reinforcement_candidates_api_reads_current_state() -> None:
    client = TestClient(app)
    _, game_id = play_to_reinforcement_turn4(api_engine, seed=3)
    actions = client.get(
        f"/games/{game_id}/legal-actions", headers={"X-Player-Side": "axis"}
    ).json()
    assert len(actions) == 1 and actions[0]["kind"] == "submit_phase_orders"
    hint = actions[0]["schema_hint"]
    assert hint["reinforcement_candidates"]["group_available"] is True
    assert hint["reinforcement_candidates"]["roll_result"] == {"roll": 1, "available": True}
    assert len(hint["reinforcement_candidates"]["ships"]) == 8
    assert len(hint["reinforcement_candidates"]["entry_hexes"]) == 51
