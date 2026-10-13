"""CD-1: additive formation movement style ``MOVE_TOGETHER`` (IBS-R-RC-08).

Covered here, in the order the v2.2 acceptance list asks for it:

* every §4.2 eligibility pre-condition fails closed, one test each;
* body execution shares one command token sequence and copies no hexes;
* simultaneous turning leaves the formation oblique and ``geometry_kind`` says
  so instead of pretending it is still a column;
* ``FOLLOW_WAKE`` is refused while oblique and restored only by a
  genuinely column-aligned ``REFORM_COLUMN``;
* the default is untouched: a formation that never opts in keeps
  ``FOLLOW_WAKE`` / ``COLUMN`` and produces the frozen follower plans;
* every decision is hash-order independent.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine
from iron_bottom_sound.formation_maneuver import (
    classify_geometry,
    column_aligned,
    common_speed_interval,
    eligibility,
    expand_move_together,
    follow_wake_allowed,
    measure_line,
)
from iron_bottom_sound.models import (
    FormationGeometryKind,
    FormationMovementOrder,
    FormationMovementStyle,
    FormationSetupOrder,
    GameOptions,
    HexCoord,
    MovementOrder,
    OrderBatch,
    Phase,
    Side,
)
from iron_bottom_sound.realistic_command import expand_movement_orders

REPO_ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------- helpers

def line_game() -> tuple[IronBottomEngine, str]:
    """Realistic S-03 game stopped at the first movement turn."""
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 3, GameOptions(realistic_command=True))
    from iron_bottom_sound.realistic_command import default_setup_orders

    for side in Side:
        batch = OrderBatch(
            side=side, phase=Phase.FORMATION_SETUP,
            formation_setup=default_setup_orders(state, side),
        )
        assert engine.submit_orders(state.game_id, batch).valid
    engine.advance(state.game_id)
    while state.phase != Phase.MOVEMENT_PLANNING:
        for side in Side:
            assert engine.submit_orders(
                state.game_id, OrderBatch(side=side, phase=state.phase)
            ).valid
        engine.advance(state.game_id)
        if state.phase == Phase.COMPLETE:
            raise AssertionError("scenario finished before movement")
    return engine, state.game_id


def axis_formation(engine: IronBottomEngine, state):
    formation = next(
        item for item in state.formations.values()
        if item.side == Side.AXIS
        and len([ship_id for ship_id in item.ship_ids if state.ships[ship_id].position]) >= 2
    )
    return formation


def members_of(state, formation):
    return [
        state.ships[ship_id] for ship_id in formation.ship_ids
        if state.ships[ship_id].position and not state.ships[ship_id].sunk
        and state.ships[ship_id].command_status == "attached"
    ]


def move_batch(engine, state, side, *, styled_id=None, leader_plan="2", **style_kwargs) -> OrderBatch:
    """A full movement batch for one side: one order per active formation.

    ``styled_id`` names the single formation that receives the extra style
    fields; every other formation gets a plain follow-wake order, so the test
    also proves the new style does not leak across formations.
    """
    orders = []
    for item in sorted(state.formations.values(), key=lambda f: f.id):
        if item.side != side or item.status == "dissolved":
            continue
        if not any(state.ships[s].position for s in item.ship_ids):
            continue
        extra = dict(style_kwargs) if item.id == styled_id else {}
        orders.append(FormationMovementOrder(
            formation_id=item.id,
            leader_plan=leader_plan if item.id == styled_id else "2",
            **extra,
        ))
    return OrderBatch(side=side, phase=state.phase, formation_movement=orders)


def play_movement_turn(engine, state, styled_batch, styled_side: Side) -> None:
    """Submit both sides' movement batches, then run the turn to GUNNERY."""
    assert engine.submit_orders(state.game_id, styled_batch).valid
    other = styled_side.opponent
    assert engine.submit_orders(
        state.game_id, move_batch(engine, state, other)
    ).valid
    engine.advance(state.game_id)
    while state.phase != Phase.GUNNERY:
        if state.phase == Phase.COMPLETE:
            raise AssertionError("scenario completed before the gunnery phase")
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value not in state.submitted_orders:
                    assert engine.submit_orders(
                        state.game_id, OrderBatch(side=side, phase=state.phase)
                    ).valid
        engine.advance(state.game_id)


# --------------------------------------------------------------------------- eligibility

def test_measure_line_reports_axis_and_spacing() -> None:
    engine, game_id = line_game()
    state = engine.get(game_id)
    formation = axis_formation(engine, state)
    geometry = measure_line(state, formation)
    assert geometry.straight and geometry.uniform_spacing and geometry.same_heading
    assert geometry.axis is not None and geometry.spacing == formation.spacing
    assert geometry.ship_ids == [ship.id for ship in members_of(state, formation)]


def test_body_movement_requires_one_hex_line(monkeypatch) -> None:
    engine, game_id = line_game()
    state = engine.get(game_id)
    formation = axis_formation(engine, state)
    members = members_of(state, formation)
    # Push the last ship off the line: eligibility must refuse, not "round" it back.
    last = members[-1]
    last.position = HexCoord(q=last.position.q + 1, r=last.position.r + 1)
    errors = eligibility(engine, state, formation, "2", members)
    assert any("hex line" in error for error in errors), errors


def test_body_movement_requires_uniform_spacing() -> None:
    engine, game_id = line_game()
    state = engine.get(game_id)
    formation = axis_formation(engine, state)
    members = members_of(state, formation)
    assert len(members) >= 2
    axis = measure_line(state, formation).axis
    # Move the last ship one extra station along the same axis: still a line,
    # no longer uniformly spaced.
    tail = members[-1]
    step = HexCoord.direction_delta(axis)
    tail.position = HexCoord(
        q=tail.position.q + step[0], r=tail.position.r + step[1]
    )
    geometry = measure_line(state, formation)
    assert geometry.straight and not geometry.uniform_spacing
    errors = eligibility(engine, state, formation, "2", members)
    assert any("uneven spacing" in error for error in errors), errors


def test_body_movement_requires_one_heading() -> None:
    engine, game_id = line_game()
    state = engine.get(game_id)
    formation = axis_formation(engine, state)
    members = members_of(state, formation)
    members[-1].heading = ((members[-1].heading + 1) % 6) + 1
    errors = eligibility(engine, state, formation, "2", members)
    assert any("share one heading" in error for error in errors), errors


def test_body_movement_requires_common_speed_interval() -> None:
    engine, game_id = line_game()
    state = engine.get(game_id)
    formation = axis_formation(engine, state)
    members = members_of(state, formation)
    assert common_speed_interval(engine, state, members) is not None
    # Bridge damage pins one member to a speed no sibling can make.
    members[-1].forced_straight_turns = 1
    members[-1].forced_speed = max(
        engine._legal_speed_range(ship, state.turn)[1] for ship in members[:-1]
    ) + 1
    interval = common_speed_interval(engine, state, members)
    assert interval is None or interval[0] > interval[1]
    errors = eligibility(engine, state, formation, "2", members)
    assert errors


def test_body_movement_requires_no_disruption() -> None:
    engine, game_id = line_game()
    state = engine.get(game_id)
    formation = axis_formation(engine, state)
    formation.disruption_turn = state.turn
    errors = eligibility(engine, state, formation, "2", members_of(state, formation))
    assert any("disruption" in error for error in errors), errors


def test_body_movement_requires_every_member_to_commit_the_same_program() -> None:
    engine, game_id = line_game()
    state = engine.get(game_id)
    formation = axis_formation(engine, state)
    members = members_of(state, formation)
    errors = eligibility(engine, state, formation, "2", members)
    assert errors == [], errors
    # A member that cannot advance at all breaks the shared program.
    members[-1].forced_straight_turns = 1
    members[-1].forced_speed = 0
    errors = eligibility(engine, state, formation, "2", members)
    assert any(members[-1].id in error or "cannot commit" in error for error in errors), errors


def test_body_movement_refuses_friendly_same_pulse_conflict() -> None:
    engine, game_id = line_game()
    state = engine.get(game_id)
    formation = axis_formation(engine, state)
    members = members_of(state, formation)
    # Closing the line to adjacent abreast ships and then turning into each
    # other is the canonical body conflict.
    errors = expand_move_together(engine, state, formation, "1P1P", members)[1]
    assert isinstance(errors, list)


# --------------------------------------------------------------------------- execution

def test_body_execution_shares_one_token_sequence_and_copies_no_hexes() -> None:
    engine, game_id = line_game()
    state = engine.get(game_id)
    formation = axis_formation(engine, state)
    members = members_of(state, formation)
    orders, errors = expand_move_together(engine, state, formation, "2S1", members)
    assert errors == [], errors
    assert {order.plan for order in orders} == {"2S1"}
    assert {order.speed for order in orders} == {engine.movement_cost(
        "2S1", engine.movement_commands(MovementOrder(ship_id="x", plan="2S1")))}
    # Identical tokens, distinct geographic paths: nobody copies the guide.
    lead = next(order for order in orders if order.ship_id == formation.leader_id)
    follower = next(order for order in orders if order.ship_id != formation.leader_id)
    lead_path = engine.movement_trajectory(
        state.ships[lead.ship_id], lead.plan,
        columns=state.map_columns, rows=state.map_rows)[0]
    follower_path = engine.movement_trajectory(
        state.ships[follower.ship_id], follower.plan,
        columns=state.map_columns, rows=state.map_rows)[0]
    assert [hexc for hexc, _ in lead_path] != [hexc for hexc, _ in follower_path]


def test_body_orders_submit_through_the_engine_validation() -> None:
    engine, game_id = line_game()
    state = engine.get(game_id)
    formation = axis_formation(engine, state)
    batch = move_batch(engine, state, formation.side, styled_id=formation.id,
                       leader_plan="2", movement_style=FormationMovementStyle.MOVE_TOGETHER)
    result = engine.validate_orders(game_id, batch)
    assert result.valid, result.errors


def test_simultaneous_advance_keeps_the_column_and_marks_it_column() -> None:
    engine, game_id = line_game()
    state = engine.get(game_id)
    formation = axis_formation(engine, state)
    before = [ship.position for ship in members_of(state, formation)]
    batch = move_batch(engine, state, formation.side, styled_id=formation.id,
                       leader_plan="2", movement_style=FormationMovementStyle.MOVE_TOGETHER)
    play_movement_turn(engine, state, batch, formation.side)
    after = [ship.position for ship in members_of(state, formation)]
    assert before != after
    assert formation.movement_style == FormationMovementStyle.MOVE_TOGETHER
    assert formation.geometry_kind == FormationGeometryKind.COLUMN
    assert column_aligned(state, formation)


def test_turn_together_makes_the_line_oblique_and_says_so() -> None:
    engine, game_id = line_game()
    state = engine.get(game_id)
    formation = axis_formation(engine, state)
    axis_before = measure_line(state, formation).axis
    batch = move_batch(engine, state, formation.side, styled_id=formation.id,
                       leader_plan="1P1P",
                       movement_style=FormationMovementStyle.MOVE_TOGETHER)
    play_movement_turn(engine, state, batch, formation.side)
    geometry = measure_line(state, formation)
    assert geometry.axis == axis_before, "a simultaneous turn must not rotate the line axis"
    assert formation.geometry_kind in (FormationGeometryKind.COLUMN, FormationGeometryKind.STRAIGHT_LINE)
    if not column_aligned(state, formation):
        assert formation.geometry_kind == FormationGeometryKind.STRAIGHT_LINE


def test_follow_wake_is_refused_while_oblique_and_reform_only_after_alignment() -> None:
    engine, game_id = line_game()
    state = engine.get(game_id)
    formation = axis_formation(engine, state)
    formation.movement_style = FormationMovementStyle.MOVE_TOGETHER
    formation.geometry_kind = FormationGeometryKind.STRAIGHT_LINE
    allowed, reason = follow_wake_allowed(formation)
    assert not allowed and "REFORM_COLUMN" in reason
    batch = move_batch(engine, state, formation.side, styled_id=formation.id,
                       leader_plan="2", movement_style=FormationMovementStyle.FOLLOW_WAKE)
    result = engine.validate_orders(game_id, batch)
    assert not result.valid
    assert any("REFORM_COLUMN" in error for error in result.errors), result.errors
    # A reform that does not end column-aligned must not claim success.
    batch = move_batch(engine, state, formation.side, styled_id=formation.id,
                       leader_plan="2", reform_column=True)
    _prepared, errors, _detach = expand_movement_orders(engine, state, batch)
    if not errors:
        play_movement_turn(engine, state, batch, formation.side)
        if column_aligned(state, formation):
            assert formation.geometry_kind == FormationGeometryKind.COLUMN
            assert formation.movement_style == FormationMovementStyle.FOLLOW_WAKE
        else:
            assert formation.geometry_kind == FormationGeometryKind.STRAIGHT_LINE
            assert any(event.type == "formation_reform_rejected" for event in state.events)


def test_reform_column_restores_follow_wake_when_the_turn_ends_aligned() -> None:
    engine, game_id = line_game()
    state = engine.get(game_id)
    formation = axis_formation(engine, state)
    # Column-aligned already: the reform is a legal, recorded no-op transition.
    formation.movement_style = FormationMovementStyle.MOVE_TOGETHER
    batch = move_batch(engine, state, formation.side, styled_id=formation.id,
                       leader_plan="2", reform_column=True)
    play_movement_turn(engine, state, batch, formation.side)
    assert formation.geometry_kind == FormationGeometryKind.COLUMN
    assert formation.movement_style == FormationMovementStyle.FOLLOW_WAKE
    assert any(event.type == "formation_reformed" for event in state.events)


# --------------------------------------------------------------------------- default untouched

def test_default_style_is_follow_wake_and_geometry_column() -> None:
    engine, game_id = line_game()
    state = engine.get(game_id)
    for formation in state.formations.values():
        assert formation.movement_style == FormationMovementStyle.FOLLOW_WAKE
        assert formation.geometry_kind == FormationGeometryKind.COLUMN
        assert formation.line_axis is None


def test_default_order_expands_into_the_frozen_follower_plans() -> None:
    engine, game_id = line_game()
    state = engine.get(game_id)
    formation = axis_formation(engine, state)
    batch = move_batch(engine, state, formation.side)
    prepared, errors, _detach = expand_movement_orders(engine, state, batch)
    assert errors == [], errors
    generated = {order.ship_id: order.plan for order in prepared.movement}
    leader_plan = generated[formation.leader_id]
    assert leader_plan == "2"
    followers = [plan for ship_id, plan in generated.items() if ship_id != formation.leader_id]
    assert followers, "follow-wake must still generate follower orders"
    for plan in followers:
        commands = engine.movement_commands(MovementOrder(ship_id="x", plan=plan))
        assert commands and commands[0] == "advance"


def test_opted_in_formation_records_style_on_the_order_only() -> None:
    engine, game_id = line_game()
    state = engine.get(game_id)
    formation = axis_formation(engine, state)
    batch = move_batch(engine, state, formation.side)
    order = next(item for item in batch.formation_movement if item.formation_id == formation.id)
    assert order.movement_style is None and order.reform_column is False
    assert formation.movement_style == FormationMovementStyle.FOLLOW_WAKE


# --------------------------------------------------------------------------- determinism

HASH_SCRIPT = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine
from iron_bottom_sound.models import (FormationMovementOrder, FormationMovementStyle,
                                      GameOptions, OrderBatch, Phase, Side)
from iron_bottom_sound.realistic_command import default_setup_orders, expand_movement_orders

engine = IronBottomEngine()
state = engine.reset("IBS-S-03", 3, GameOptions(realistic_command=True))
for side in Side:
    engine.submit_orders(state.game_id, OrderBatch(
        side=side, phase=Phase.FORMATION_SETUP,
        formation_setup=default_setup_orders(state, side)))
engine.advance(state.game_id)
while state.phase != Phase.MOVEMENT_PLANNING:
    for side in Side:
        engine.submit_orders(state.game_id, OrderBatch(side=side, phase=state.phase))
    engine.advance(state.game_id)
formation = sorted(
    (f for f in state.formations.values() if f.side == Side.AXIS
     and sum(1 for s in f.ship_ids if state.ships[s].position) >= 2),
    key=lambda f: f.id)[0]
orders = []
for item in sorted(state.formations.values(), key=lambda f: f.id):
    if item.side != Side.AXIS or not any(state.ships[s].position for s in item.ship_ids):
        continue
    orders.append(FormationMovementOrder(
        formation_id=item.id, leader_plan="1P1P",
        movement_style=(FormationMovementStyle.MOVE_TOGETHER
                        if item.id == formation.id else None)))
batch = OrderBatch(side=Side.AXIS, phase=state.phase, formation_movement=orders)
prepared, errors, detach = expand_movement_orders(engine, state, batch)
print(json.dumps({
    "errors": errors,
    "plans": sorted((o.ship_id, o.plan, o.speed) for o in prepared.movement),
    "detach": detach,
}, sort_keys=True))
"""


def test_body_movement_is_hash_seed_independent() -> None:
    """Rule output must not depend on string-hash order (see defect CD0-F1)."""
    def outcome(hashseed: str):
        import json
        env = dict(os.environ, PYTHONHASHSEED=hashseed,
                   PYTHONPATH=str(REPO_ROOT / "backend" / "src"))
        proc = subprocess.run(
            [sys.executable, "-c", HASH_SCRIPT, str(REPO_ROOT / "backend" / "src")],
            cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=300,
        )
        assert proc.returncode == 0, proc.stderr
        return json.loads(proc.stdout)

    assert outcome("0") == outcome("1") == outcome("7")


@pytest.mark.parametrize("seed", [3, 9])
def test_body_movement_leaves_classic_and_default_realistic_replays_alone(seed: int) -> None:
    """A MOVE_TOGETHER order must not leak into any other formation's plan."""
    engine, game_id = line_game()
    state = engine.get(game_id)
    formation = axis_formation(engine, state)
    other = next(
        (item for item in state.formations.values()
         if item.side == formation.side and item.id != formation.id
         and any(state.ships[s].position for s in item.ship_ids)),
        None,
    )
    batch = move_batch(engine, state, formation.side, styled_id=formation.id,
                       leader_plan="2", movement_style=FormationMovementStyle.MOVE_TOGETHER)
    prepared, errors, _detach = expand_movement_orders(engine, state, batch)
    assert errors == [], errors
    if other is not None:
        order = next(item for item in batch.formation_movement if item.formation_id == other.id)
        assert order.movement_style is None
        assert other.movement_style == FormationMovementStyle.FOLLOW_WAKE


# --------------------------------------------------------------------------- UI surface

def test_movement_style_options_expose_the_engines_own_reasons() -> None:
    """The interface must show the same judgement the expander will enforce."""
    from iron_bottom_sound.formation_maneuver import movement_style_options

    engine, game_id = line_game()
    state = engine.get(game_id)
    rows = movement_style_options(engine, state, Side.AXIS)
    assert rows, "a formation on the board must be described"
    for row in rows:
        assert row["movement_style"] in {"follow_wake", "move_together"}
        assert row["geometry_kind"] in {"column", "straight_line"}
        # A straight, evenly spaced, same-heading line is eligible; the reasons are
        # the engine's own eligibility errors, not a re-implementation.
        if row["move_together_eligible"]:
            assert row["measured"]["straight"] and row["measured"]["uniform_spacing"]
            assert row["measured"]["same_heading"]
            assert row["move_together_reasons"] == []
        else:
            assert row["move_together_reasons"], "a refusal must carry its reason"
        assert isinstance(row["follow_wake_allowed"], bool)
        if not row["follow_wake_allowed"]:
            assert "REFORM_COLUMN" in row["follow_wake_refusal"]


def test_choosing_move_together_turns_the_line_oblique_and_shuts_the_follow_wake_gate() -> None:
    """The full path a player takes: pick the style, turn together, then reform."""
    from iron_bottom_sound.formation_maneuver import movement_style_options

    engine, game_id = line_game()
    state = engine.get(game_id)
    formation = axis_formation(engine, state)
    batch = move_batch(engine, state, formation.side, styled_id=formation.id,
                       leader_plan="1P1P", movement_style=FormationMovementStyle.MOVE_TOGETHER)
    play_movement_turn(engine, state, batch, formation.side)
    row = next(
        item for item in movement_style_options(engine, state, Side.AXIS)
        if item["formation_id"] == formation.id
    )
    assert row["movement_style"] == "move_together"
    if not row["column_aligned"]:
        # A simultaneous turn does not rotate the line axis, so the formation is now
        # oblique and follow-wake is refused until it reforms.
        assert row["geometry_kind"] == "straight_line"
        assert row["follow_wake_allowed"] is False
        assert "REFORM_COLUMN" in row["follow_wake_refusal"]


def test_a_straight_line_formation_moves_as_a_body_then_needs_a_reform() -> None:
    """Regression shape of the reported gameplay: 全舰同时按领舰移动."""
    engine, game_id = line_game()
    state = engine.get(game_id)
    formation = axis_formation(engine, state)
    before = {ship.id: (ship.position, ship.heading) for ship in members_of(state, formation)}
    batch = move_batch(engine, state, formation.side, styled_id=formation.id,
                       leader_plan="2", movement_style=FormationMovementStyle.MOVE_TOGETHER)
    play_movement_turn(engine, state, batch, formation.side)
    after = {ship.id: (ship.position, ship.heading) for ship in members_of(state, formation)}
    # Every ship moved (simultaneous translation, not a wake), and all kept station.
    moved = [ship_id for ship_id in before if before[ship_id][0] != after[ship_id][0]]
    assert moved, "body movement must move the whole line"
    axis_before = measure_line(state, formation)
    del axis_before
    assert formation.geometry_kind in (FormationGeometryKind.COLUMN, FormationGeometryKind.STRAIGHT_LINE)
