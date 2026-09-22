"""Command Delay CD-1: the additive formation movement style ``MOVE_TOGETHER``.

Why a separate module
---------------------
``realistic_command.py`` is frozen at tag ``realistic-command-v1-frozen`` and
owns the follow-wake column.  This module adds the second movement method
alongside it and is reached through a single dispatch line in that file, so the
frozen module keeps exactly one reference to the new behaviour instead of
growing the feature.

What the rule is
----------------
``FOLLOW_WAKE`` (unchanged) is successive movement: the guide goes first and each
follower reaches the guide's turning point before turning.

``MOVE_TOGETHER`` is the historical alternative: every attached member executes
the *same movement command token* in each global MF pulse, from its own position
and its own heading.  No ship copies the guide's geographic hexes.  Consequently
the formation turns as a body, and the line axis does **not** rotate with the
heading: a line-ahead column becomes oblique or line-abreast as it turns.  That
is real, not a rendering detail, so :class:`~.models.FormationGeometryKind`
tracks it and ``FOLLOW_WAKE`` is refused until the formation is column-aligned
again through an explicit ``REFORM_COLUMN``.

All ordering in this module is over lists sorted by ship id or over
``formation.ship_ids``; no set iteration order reaches a decision (see defect
CD0-F1 in ``research/command_delay/cd0/CD0_FREEZE_EVIDENCE.md``).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .models import (
    FormationGeometryKind,
    FormationMovementStyle,
    FormationState,
    GameState,
    HexCoord,
    MovementOrder,
    Phase,
    ShipState,
)

if TYPE_CHECKING:
    from .engine import IronBottomEngine

# Rule identity for the audit trail.
RULE_STYLE = "IBS-R-RC-08"

# The full rule allows turning as a body ("turn-together").  Setting this to
# False restricts MOVE_TOGETHER to simultaneous translation, which is the
# low-risk variant the v2.2 plan explicitly permits as an interim step.  It is a
# constant rather than a per-order flag so a replay cannot silently change
# meaning between two orders of the same profile.
ALLOW_TURN_TOGETHER = True

# Turn tokens, and the ones that also consume an MF pulse.
_TURNS = {
    "turn_port_60": 0,
    "turn_starboard_60": 0,
    "turn_port_120": 1,
    "turn_starboard_120": 1,
}


@dataclass
class LineGeometry:
    """Measured geometry of a formation's attached ships, in column order."""

    ship_ids: list[str] = field(default_factory=list)
    axis: int | None = None
    spacing: int | None = None
    straight: bool = False
    uniform_spacing: bool = False
    same_heading: bool = True
    heading: int | None = None
    reasons: list[str] = field(default_factory=list)

    @property
    def is_line(self) -> bool:
        return self.straight and self.uniform_spacing and self.same_heading

    def as_payload(self) -> dict:
        return {
            "ship_ids": list(self.ship_ids),
            "axis": self.axis,
            "spacing": self.spacing,
            "straight": self.straight,
            "uniform_spacing": self.uniform_spacing,
            "same_heading": self.same_heading,
            "heading": self.heading,
            "reasons": list(self.reasons),
        }


def attached_members(state: GameState, formation: FormationState) -> list[ShipState]:
    """Attached, positioned, unsunk members in the formation's declared order."""
    return [
        state.ships[ship_id]
        for ship_id in formation.ship_ids
        if ship_id in state.ships
        and state.ships[ship_id].position is not None
        and not state.ships[ship_id].sunk
        and state.ships[ship_id].command_status == "attached"
    ]


def _exact_axis(origin: HexCoord, target: HexCoord) -> tuple[int, int] | None:
    """Return ``(heading, steps)`` when ``target`` lies on a hex direction line.

    Uses axial ``direction_delta`` arithmetic, i.e. the same lattice the engine
    moves on, rather than the screen-space ``_bearing_between`` approximation
    that firing arcs intentionally use.
    """
    dq = target.q - origin.q
    dr = target.r - origin.r
    if (dq, dr) == (0, 0):
        return None
    for heading, (step_q, step_r) in (
        (index, HexCoord.direction_delta(index)) for index in range(1, 7)
    ):
        for steps in (1, 2, 3, 4, 5, 6, 7, 8):
            if (step_q * steps, step_r * steps) == (dq, dr):
                return heading, steps
            if (step_q * -steps, step_r * -steps) == (dq, dr):
                return ((heading + 2) % 6) + 1, steps
    return None


def _opposite(heading: int) -> int:
    return ((heading + 2) % 6) + 1


def measure_line(state: GameState, formation: FormationState) -> LineGeometry:
    """Measure whether the attached members sit on one uniformly spaced line."""
    geometry = LineGeometry()
    members = attached_members(state, formation)
    geometry.ship_ids = [ship.id for ship in members]
    if len(members) < 2:
        geometry.reasons.append("fewer than two attached, positioned members")
        return geometry
    geometry.heading = members[0].heading
    geometry.same_heading = all(ship.heading == members[0].heading for ship in members)
    if not geometry.same_heading:
        geometry.reasons.append("members do not share one heading")
    axes: list[int] = []
    steps: list[int] = []
    for left, right in zip(members, members[1:]):
        resolved = _exact_axis(left.position, right.position)  # type: ignore[arg-type]
        if resolved is None:
            geometry.reasons.append(f"{left.id}->{right.id} is not on a hex line")
            return geometry
        axis, count = resolved
        axes.append(axis)
        steps.append(count)
    geometry.straight = len(set(axes)) == 1
    if not geometry.straight:
        geometry.reasons.append("consecutive members do not lie on one axis")
        return geometry
    geometry.axis = axes[0]
    geometry.uniform_spacing = len(set(steps)) == 1
    if not geometry.uniform_spacing:
        geometry.reasons.append("member spacing is not uniform")
        return geometry
    geometry.spacing = steps[0]
    return geometry


def classify_geometry(state: GameState, formation: FormationState) -> tuple[FormationGeometryKind, int | None]:
    """Declared geometry kind implied by the measured line, if it is a line."""
    geometry = measure_line(state, formation)
    if not geometry.is_line or geometry.axis is None:
        return FormationGeometryKind.STRAIGHT_LINE, geometry.axis
    leader = state.ships.get(formation.leader_id)
    heading = leader.heading if leader is not None and leader.position else geometry.heading
    if heading is not None and geometry.axis == _opposite(heading):
        return FormationGeometryKind.COLUMN, geometry.axis
    return FormationGeometryKind.STRAIGHT_LINE, geometry.axis


def column_aligned(state: GameState, formation: FormationState) -> bool:
    """True when the measured line is a genuine line-ahead column."""
    geometry = measure_line(state, formation)
    leader = state.ships.get(formation.leader_id)
    if not geometry.is_line or geometry.axis is None or leader is None or not leader.position:
        return False
    return geometry.axis == _opposite(leader.heading)


def common_speed_interval(
    engine: "IronBottomEngine", state: GameState, members: list[ShipState],
) -> tuple[int, int] | None:
    """Intersection of the members' legal speed ranges, or ``None`` if empty."""
    if not members:
        return None
    minimum = max(engine._legal_speed_range(ship, state.turn)[0] for ship in members)
    maximum = min(engine._legal_speed_range(ship, state.turn)[1] for ship in members)
    return (minimum, maximum) if minimum <= maximum else None


def _tokens(engine: "IronBottomEngine", leader_id: str, plan: str) -> list[str]:
    return engine.movement_commands(MovementOrder(ship_id=leader_id, plan=plan))


def eligibility(
    engine: "IronBottomEngine", state: GameState, formation: FormationState,
    leader_plan: str, members: list[ShipState],
) -> list[str]:
    """Every pre-condition of IBS-R-RC-08 §4.2, as explicit error strings."""
    errors: list[str] = []
    if formation.disruption_turn == state.turn:
        errors.append("command disruption forbids body movement this turn")
    geometry = measure_line(state, formation)
    if len(members) < 2:
        errors.append("MOVE_TOGETHER needs at least two attached members")
        return errors
    if not geometry.straight:
        errors.append("members are not on one hex line: " + "; ".join(geometry.reasons))
    elif not geometry.uniform_spacing:
        errors.append(f"uneven spacing along the line axis ({geometry.reasons})")
    elif not geometry.same_heading:
        errors.append("members do not share one heading")
    interval = common_speed_interval(engine, state, members)
    if interval is None:
        errors.append("no common speed satisfies every member's legal range")
    try:
        tokens = _tokens(engine, formation.leader_id, leader_plan)
    except ValueError as error:
        errors.append(f"leader plan is not a movement program: {error}")
        return errors
    if tokens and not ALLOW_TURN_TOGETHER and any(token in _TURNS for token in tokens):
        errors.append("turn-together is disabled in this build")
    if tokens:
        engine.validate_movement_commands(tokens)
    cost = engine.movement_cost(leader_plan, tokens)
    if interval is not None and not interval[0] <= cost <= interval[1]:
        errors.append(f"common speed {cost} is outside the formation interval {interval[0]}-{interval[1]}")
    # "the same leader plan applied to each ship's own current position is legal"
    plan = engine.commands_to_plan(tokens)
    for ship in members:
        preview = engine.movement_preview(state, ship, plan=plan)
        if not preview["commitable"]:
            detail = "; ".join(preview["errors"]) or "not commitable"
            errors.append(f"{ship.id} cannot commit the common program ({detail})")
    return errors


def simultaneous_conflicts(
    engine: "IronBottomEngine", state: GameState, orders: list[MovementOrder],
) -> list[str]:
    """Whole-batch same-impulse same-hex / hex-swap check, per side.

    Mirrors the batch legality property the frozen expander applies to a
    follow-wake column: a body movement that would make two same-side ships
    occupy one hex in one pulse (or trade hexes) is not a legal body movement and
    must be refused rather than silently absorbed by the resolver's emergency
    stop.
    """
    errors: list[str] = []
    paths: dict[str, list[HexCoord]] = {}
    for order in sorted(orders, key=lambda item: item.ship_id):
        ship = state.ships[order.ship_id]
        if not ship.position:
            continue
        try:
            trajectory, _heading = engine.movement_trajectory(
                ship, order.plan, columns=state.map_columns, rows=state.map_rows,
            )
        except ValueError as error:
            errors.append(f"{ship.id}: {error}")
            continue
        paths[ship.id] = [ship.position] + [position for position, _ in trajectory]
    ids = sorted(paths)
    for left_index, left_id in enumerate(ids):
        for right_id in ids[left_index + 1:]:
            if state.ships[left_id].side != state.ships[right_id].side:
                continue
            left, right = paths[left_id], paths[right_id]
            for impulse in range(max(len(left), len(right)) - 1):
                lb = left[min(impulse, len(left) - 1)]
                rb = right[min(impulse, len(right) - 1)]
                la = left[min(impulse + 1, len(left) - 1)]
                ra = right[min(impulse + 1, len(right) - 1)]
                if la == ra or (la == rb and ra == lb):
                    errors.append(
                        f"friendly body-movement conflict at MF {impulse + 1}: {left_id} / {right_id}"
                    )
                    break
    return errors


def expand_move_together(
    engine: "IronBottomEngine", state: GameState, formation: FormationState,
    leader_plan: str, members: list[ShipState],
) -> tuple[list[MovementOrder], list[str]]:
    """Expand one body-movement order into per-ship orders carrying identical tokens."""
    errors = eligibility(engine, state, formation, leader_plan, members)
    if errors:
        return [], errors
    tokens = _tokens(engine, formation.leader_id, leader_plan)
    plan = engine.commands_to_plan(tokens)
    cost = engine.movement_cost(plan, tokens)
    orders = [
        MovementOrder(ship_id=ship.id, plan=plan, speed=cost)
        for ship in sorted(members, key=lambda item: item.id)
    ]
    errors = simultaneous_conflicts(engine, state, orders)
    if errors:
        return [], errors
    return orders, []


def commit_sealed_style_transitions(engine: "IronBottomEngine", state: GameState) -> None:
    """Commit declared style/geometry from the movement batch sealed this turn.

    Called after ``_resolve_movement``, so it only ever sees orders that already
    passed ``validate_orders``: a rejected body movement is never sealed and can
    therefore never move the declared geometry.

    Wholly inert for the frozen default: if no sealed order asks for body
    movement, this returns before touching any state, so a Realistic
    ``FOLLOW_WAKE`` turn is bit-identical to the frozen implementation.
    """
    requests: dict[str, tuple[FormationMovementStyle | None, bool]] = {}
    for batch in engine._sealed_batches(state, Phase.MOVEMENT_PLANNING):
        for order in batch.formation_movement:
            formation = state.formations.get(order.formation_id)
            if formation is None:
                continue
            body = (
                order.movement_style == FormationMovementStyle.MOVE_TOGETHER
                or order.reform_column
                or (
                    order.movement_style is None
                    and formation.movement_style == FormationMovementStyle.MOVE_TOGETHER
                )
            )
            if body:
                requests[order.formation_id] = (order.movement_style, order.reform_column)
    if not requests:
        return
    for formation_id in sorted(requests):
        style, reform = requests[formation_id]
        formation = state.formations.get(formation_id)
        if formation is None or formation.status == "dissolved":
            continue
        if reform:
            if column_aligned(state, formation):
                geometry = measure_line(state, formation)
                formation.geometry_kind = FormationGeometryKind.COLUMN
                formation.line_axis = geometry.axis
                formation.movement_style = FormationMovementStyle.FOLLOW_WAKE
                engine._event(
                    state, "formation_reformed",
                    f"{formation.name} 恢复纵队队形，可继续尾随领舰",
                    payload={
                        # One side's formation geometry: private, exactly like
                        # formation_created.  Without this the neutral battle report
                        # would carry it.
                        "secret_side": formation.side.value,
                        "formation_id": formation.id,
                        "line_axis": formation.line_axis,
                        "spacing": geometry.spacing,
                    },
                    rule=engine._rule(RULE_STYLE, None, "命令延迟：重整纵队"),
                )
            else:
                engine._event(
                    state, "formation_reform_rejected",
                    f"{formation.name} 尚未与纵队轴线对齐，整队机动继续",
                    payload={
                        "secret_side": formation.side.value,
                        "formation_id": formation.id,
                        **measure_line(state, formation).as_payload(),
                    },
                    rule=engine._rule(RULE_STYLE, None, "命令延迟：重整纵队"),
                )
            continue
        formation.movement_style = FormationMovementStyle.MOVE_TOGETHER
        kind, axis = classify_geometry(state, formation)
        formation.geometry_kind = kind
        formation.line_axis = axis


def follow_wake_allowed(formation: FormationState) -> tuple[bool, str]:
    """Declared-geometry gate for switching back to ``FOLLOW_WAKE``."""
    if formation.geometry_kind == FormationGeometryKind.COLUMN:
        return True, ""
    return False, (
        "formation is not column-aligned after MOVE_TOGETHER; "
        "issue REFORM_COLUMN before FOLLOW_WAKE"
    )
