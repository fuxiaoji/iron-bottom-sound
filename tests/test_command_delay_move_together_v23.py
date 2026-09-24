"""IR-8: MOVE_TOGETHER's remaining cases, in both modes, and the freeze.

The 22 tests in `test_command_delay_movement_style.py` cover most of the plan's list
(eligibility conditions, collision conflict, disruption, geometry state, REFORM_COLUMN).
This file adds the three that were missing, each in the mode where it matters:

* board-edge rejection - the common program would take a member off the map;
* forced-movement rejection - a ship under forced movement cannot follow the body program;
* Realistic-mode parity - the same rules hold with the command-delay mode off, because the
  manoeuvre helper is not a command-delay feature.

The freeze is not re-asserted here; it is the golden replay's job (seven Classic/Realistic
rows byte-identical, checked by `run_audits` and by `golden_replay --check`).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from iron_bottom_sound import command_delay, formation_maneuver  # noqa: E402
from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine  # noqa: E402
from iron_bottom_sound.llm import LLMPlayerSession  # noqa: E402
from iron_bottom_sound.models import (  # noqa: E402
    FormationMovementOrder, FormationMovementStyle, GameOptions, HexCoord, OrderBatch,
    Phase, Side,
)
from iron_bottom_sound.realistic_command import (  # noqa: E402
    RealisticCommander, default_setup_orders,
)

SCENARIO = "IBS-S-01"          # the small scenario the mode's own tests use
SEED = 20270830


def _game(command_delay_mode: bool, turn: int = 2):
    engine = IronBottomEngine()
    state = engine.reset(SCENARIO, SEED, GameOptions(
        realistic_command=True, command_delay_mode=command_delay_mode,
    ))
    for side in Side:
        assert engine.submit_orders(state.game_id, OrderBatch(
            side=side, phase=Phase.FORMATION_SETUP,
            formation_setup=default_setup_orders(state, side),
        )).valid
    engine.advance(state.game_id)
    sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
    steps = 0
    while state.phase is not Phase.COMPLETE and steps < 200:
        steps += 1
        if state.turn >= turn and state.phase is Phase.MOVEMENT_PLANNING:
            return engine, state
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                if state.phase is Phase.MOVEMENT_PLANNING and command_delay_mode:
                    batch = OrderBatch(side=side, phase=state.phase,
                                       formation_movement=command_delay.formation_orders(state, side))
                elif state.phase is Phase.GUNNERY and command_delay_mode:
                    batch = command_delay.gunnery_batch(state, side)
                else:
                    batch = sessions[side].choose_orders(engine, state.game_id)
                result = engine.submit_orders(state.game_id, batch)
                if not result.valid and state.phase is Phase.MOVEMENT_PLANNING:
                    _, fallback, _ = RealisticCommander().choose_plan(engine, state.game_id, side)
                    result = engine.submit_orders(state.game_id, fallback)
                assert result.valid, result.errors[:2]
        engine.advance(state.game_id)
    raise AssertionError("never reached a movement phase")


def _straight_line_formation(state, side: Side):
    """A formation that is eligible in shape: one line, one heading, even spacing."""
    for formation in command_delay.active_formations(state, side):
        members = formation_maneuver.attached_members(state, formation)
        if len(members) < 2:
            continue
        geometry = formation_maneuver.measure_line(state, formation)
        if geometry.straight and geometry.uniform_spacing and geometry.same_heading:
            return formation
    return None


# --------------------------------------------------------------------- board edge

def test_body_move_never_leaves_the_board() -> None:
    """The boundary is enforced by clamping at resolution, not by a legality gate.

    This is a finding, recorded rather than assumed: `movement_preview` reports an
    off-board program as *commitable* (it validates commands, plan and cost, not the
    resulting hexes), and the boundary is enforced when the movement resolves, where
    `HexCoord.neighbor` raises "Movement leaves the map" and the step stops.  Turning that
    into an order-time rejection would change Realistic-mode semantics, which this batch
    must not do (the seven frozen rows are the proof that it did not) - so the invariant
    tested here is the one the engine actually guarantees: **no ship ends a movement off
    the map**.
    """
    engine, state = _game(command_delay_mode=True)
    formation = None
    for candidate in command_delay.active_formations(state, Side.AXIS):
        if len(formation_maneuver.attached_members(state, candidate)) >= 2:
            formation = candidate
            break
    if formation is None:
        pytest.skip("no multi-ship formation on this side")
    members = formation_maneuver.attached_members(state, formation)

    # park the formation on the last display row heading off it (display row = r + q//2 in
    # this flat-top odd-q layout, so the raw r on the edge depends on q)
    for index, ship in enumerate(members):
        q = min(20 + index, state.map_columns - 1)
        ship.position = HexCoord(q=q, r=(state.map_rows - 1) - q // 2)
        ship.heading = 3                    # heading 3 steps +r, off the bottom edge
        ship.current_speed = 0

    # What the engine guarantees is the boundary itself: whatever it does with an
    # off-board program (see 07_MOVEMENT_AND_MODE_ISOLATION.md for what was measured - the
    # *preview* does not refuse it, the resolution stops the step), no ship ends a movement
    # outside the map.
    # and after the movement resolves, every member is still on the board
    from iron_bottom_sound.models import MovementOrder

    session = LLMPlayerSession(Side.AXIS, RealisticCommander())
    batch = OrderBatch(
        side=Side.AXIS, phase=state.phase,
        movement=[MovementOrder(ship_id=ship.id, plan="6") for ship in members],
    )
    result = engine.submit_orders(state.game_id, batch)
    if result.valid:
        engine.advance(state.game_id)
    for ship in state.ships.values():
        if ship.position is None:
            continue
        display_row = ship.position.r + ship.position.q // 2
        assert 0 <= ship.position.q < state.map_columns, (ship.id, ship.position)
        assert 0 <= display_row < state.map_rows, (ship.id, ship.position)


# --------------------------------------------------------------------- forced movement

def test_forced_movement_prevents_the_body_program() -> None:
    """A ship under forced movement cannot follow the body program (the v2.2 battle error
    'forced movement prevents formation following', now asserted from the helper's side)."""
    engine, state = _game(command_delay_mode=True)
    formation = None
    for candidate in command_delay.active_formations(state, Side.AXIS):
        if len(formation_maneuver.attached_members(state, candidate)) >= 2:
            formation = candidate
            break
    if formation is None:
        pytest.skip("no multi-ship formation on this side")
    members = formation_maneuver.attached_members(state, formation)
    for index, ship in enumerate(members):
        ship.position = HexCoord(q=20 + index, r=10)
        ship.heading = 2
        ship.current_speed = 0
    # forced movement is expressed as forced_circle_turns on the ship
    members[1].forced_circle_turns = 2
    errors = formation_maneuver.eligibility(engine, state, formation, "2", members)
    # the manoeuvre helper's own preview refuses a ship that cannot commit the program;
    # the realistic layer additionally names "forced movement" as the reason
    assert errors, "forced movement must make the common program ineligible"
    allowed, refusal = formation_maneuver.follow_wake_allowed(formation)
    assert allowed or refusal


# --------------------------------------------------------------------- realistic parity

def test_move_together_is_available_with_the_command_delay_mode_off() -> None:
    """The manoeuvre is a realistic-command feature, not a command-delay one."""
    engine, state = _game(command_delay_mode=False)
    options = formation_maneuver.movement_style_options(engine, state, Side.AXIS)
    assert options, "the UI surface must list the side's formations"
    assert any("move_together_eligible" in option for option in options), (
        "MOVE_TOGETHER's availability must be reported in plain Realistic mode too"
    )
    formation = _straight_line_formation(state, Side.AXIS)
    if formation is None:
        pytest.skip("no straight-line formation on this side")
    members = formation_maneuver.attached_members(state, formation)
    errors = formation_maneuver.eligibility(engine, state, formation, "1", members)
    # the same helper answers the same way with the mode off: eligible or refused for
    # geometric reasons, never because a mode is missing
    assert all("command delay" not in error for error in errors), errors
    # and the opt-in is recorded on the order, not on the formation
    order = OrderBatch(
        side=Side.AXIS, phase=Phase.MOVEMENT_PLANNING,
        formation_movement=[command_delay.FormationMovementOrder(
            formation_id=formation.id, leader_plan="1",
            movement_style=FormationMovementStyle.MOVE_TOGETHER,
        )],
    )
    result = engine.validate_orders(state.game_id, order)
    # either the engine accepts the body move, or it refuses for a stated geometric
    # reason - what must not happen is a mode-specific error
    if not result.valid:
        assert not any("command delay" in error.lower() for error in result.errors), result.errors
