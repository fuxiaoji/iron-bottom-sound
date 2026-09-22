"""Target priority / ROE adapter into the engine fire selector (IBS-R-CD-06).

Authority boundary
------------------
A formation agent never issues a ``GunneryOrder``, never chooses a mount, never
computes a firing solution or a hit modifier, and never re-implements the hit
rule.  It may only attach a **bounded priority weight** to a target, a target
class or an objective tag.  The engine's own selection path does the rest:

* ``engine._gunnery_candidates`` decides what is legal — visibility, arcs, mount
  availability, ammunition, scenario restrictions;
* ``engine.expected_gunnery_hits`` supplies the base objective for each legal
  target;
* this module only re-ranks those legal options by
  ``base_fire_objective + lambda_priority * priority_bonus`` and asks the engine
  for the mount list it already computed.

So a directive can change *which* legal target is preferred, and can never make
an illegal shot legal, change a modifier, or invent a mount.  If the named
priority target is not visible or cannot be borne, the selector falls back to the
remaining legal targets — there is no error path that produces an illegal order.

Weight composition is the plan's formula::

    priority_bonus(target) = fleet_priority + bounded_local_priority + doctrine_priority

with the local term clamped to ``local_priority_weight_limit``, so no agent can
outvote the fleet order.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable

from .models import (
    GunneryOrder,
    GunMountOrder,
    GameState,
    Side,
    TargetPriorityDirective,
)

if TYPE_CHECKING:
    from .engine import IronBottomEngine

RULE_PRIORITY = "IBS-R-CD-06"

# How much one unit of priority weight is worth in expected hits.  A declared
# simulation parameter, not a rule constant: it sets how strongly a directive can
# pull the selector away from the raw expected-hit optimum.
LAMBDA_PRIORITY = 0.35

# Doctrine priorities are engine-side defaults, so a game with no directives at
# all still selects by the standard objective hierarchy.
DOCTRINE_CLASS_PRIORITY: dict[str, float] = {
    "BB": 0.30,
    "BC": 0.25,
    "CB": 0.22,
    "CA": 0.20,
    "CL": 0.12,
    "AV": 0.05,
    "DD": 0.0,
}


def clamp_local(weight: float, limit: float) -> float:
    return max(-limit, min(limit, weight))


def priority_bonus(
    target_id: str,
    target_class: str | None,
    directives: Iterable[TargetPriorityDirective],
    *,
    turn: int,
    local_limit: float | None = None,
) -> float:
    """Compose the bonus for one target from fleet, local and doctrine terms.

    An empty directive set composes to exactly ``0.0``, so "no directive" means
    "the raw expected-hit objective decides" — doctrine only ever adds on top of
    a declared preference.
    """
    total = 0.0
    for directive in directives:
        if directive.expires_turn is not None and directive.expires_turn < turn:
            continue
        matches = (
            (directive.target_id is not None and directive.target_id == target_id)
            or (directive.target_id is None
                and directive.target_class is not None
                and target_class is not None
                and directive.target_class == target_class)
        )
        if not matches:
            continue
        weight = directive.weight
        if directive.source == "FLEET_ORDER":
            total += max(-1.0, min(1.0, weight))
        elif directive.source == "DOCTRINE":
            total += weight
        else:
            limit = local_limit if local_limit is not None else 1.0
            total += clamp_local(weight, limit)
    return total


def doctrine_bonus(target_class: str | None) -> float:
    return DOCTRINE_CLASS_PRIORITY.get(target_class or "", 0.0)


def selection_trace(
    engine: "IronBottomEngine", state: GameState, side: Side,
    directives: list[TargetPriorityDirective] | None = None,
    *,
    local_limit: float | None = None,
    side_directives: list[TargetPriorityDirective] | None = None,
) -> list[dict[str, Any]]:
    """Every legal (ship, target) pair with its base objective and bonus.

    Read-only: this is the audit surface that proves a directive only re-ranks
    legal options.  ``legal`` is decided entirely by the engine.
    """
    directives = list(directives or [])
    side_directives = list(side_directives or [])
    trace: list[dict[str, Any]] = []
    for candidate in engine._gunnery_candidates(state, side):
        ship_id = candidate["ship_id"]
        if candidate["blocked_reason"]:
            trace.append({
                "ship_id": ship_id,
                "target_id": None,
                "legal": False,
                "blocked_reason": candidate["blocked_reason"],
                "base_fire_objective": 0.0,
                "priority_bonus": 0.0,
                "score": 0.0,
            })
            continue
        for target in candidate["targets"]:
            target_ship = state.ships.get(target["target_id"])
            target_class = target_ship.ship_type if target_ship else None
            bonus = priority_bonus(
                target["target_id"], target_class, directives,
                turn=state.turn, local_limit=local_limit,
            )
            bonus += priority_bonus(
                target["target_id"], target_class, side_directives,
                turn=state.turn, local_limit=local_limit,
            )
            bonus += doctrine_bonus(target_class)
            base = float(target["expected_hits"])
            trace.append({
                "ship_id": ship_id,
                "target_id": target["target_id"],
                "target_class": target_class,
                "mount_ids": list(target["mount_ids"]),
                "range": target["range"],
                "modifier": target["modifier"],
                "legal": True,
                "base_fire_objective": base,
                "priority_bonus": round(bonus, 6),
                "score": round(base + LAMBDA_PRIORITY * bonus, 6),
            })
    return sorted(trace, key=lambda row: (row["ship_id"], str(row["target_id"])))


def select_gunnery_orders(
    engine: "IronBottomEngine", state: GameState, side: Side,
    directives: list[TargetPriorityDirective] | None = None,
    *,
    local_limit: float | None = None,
) -> list[GunneryOrder]:
    """Generate the final gunnery orders from legal candidates + priority weights.

    Deterministic: each ship takes its highest-scoring legal target, ties break on
    the engine's own expected hits, then range, then target id.  Mounts come
    straight from the engine's candidate record, so the order is legal by
    construction.
    """
    directives = list(directives or [])
    rows = selection_trace(
        engine, state, side, directives, local_limit=local_limit,
    )
    by_ship: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not row["legal"] or row["target_id"] is None:
            continue
        current = by_ship.get(row["ship_id"])
        key = (
            row["score"],
            row["base_fire_objective"],
            -row["range"],
            str(row["target_id"]),
        )
        if current is None or key > current["_key"]:
            by_ship[row["ship_id"]] = {**row, "_key": key}
    orders: list[GunneryOrder] = []
    for ship_id in sorted(by_ship):
        row = by_ship[ship_id]
        orders.append(GunneryOrder(
            ship_id=ship_id,
            primary_target=row["target_id"],
            mounts=[
                GunMountOrder(mount_id=mount_id, target_id=row["target_id"])
                for mount_id in row["mount_ids"]
            ],
        ))
    return orders


def auto_gunnery(
    engine: "IronBottomEngine", state: GameState, side: Side,
) -> list[GunneryOrder]:
    """Selector input assembled from the game's own directive book.

    Fleet mission orders carry the fleet directives; formation agents contribute
    bounded local adjustments; doctrine supplies the fallback hierarchy.  All
    three are read-only here.
    """
    fleet: list[TargetPriorityDirective] = []
    local: list[TargetPriorityDirective] = []
    mode = getattr(state, "command_delay", None)
    if mode is not None:
        for order in mode.mission_orders:
            if order.side is not side or order.confirmed_turn is None:
                continue
            fleet.extend(order.target_priority_directives)
        for directive in mode.local_directives:
            local.append(directive)
    return select_gunnery_orders(engine, state, side, fleet + local)


def validate_agent_decision_shape(decision: Any) -> list[str]:
    """Structural guard: an agent decision may carry priority weights, nothing else.

    Any object that reaches this function carrying gunnery machinery is refused,
    which is what acceptance criterion 6 checks.
    """
    errors: list[str] = []
    payload = decision.model_dump() if hasattr(decision, "model_dump") else dict(decision)
    forbidden = {
        "gunnery", "gunnery_orders", "mounts", "mount_allocation", "mount_ids",
        "firing_solution", "hit_modifier", "expected_hits", "target_id",
    }
    present = sorted(forbidden & set(payload))
    if present:
        errors.append(
            "a formation agent may not emit gunnery machinery: " + ", ".join(present)
        )
    for adjustment in payload.get("target_priority_adjustments", []) or []:
        keys = set(adjustment if isinstance(adjustment, dict) else adjustment.model_dump())
        banned = {"mount_ids", "mounts", "firing_solution", "hit_modifier"} & keys
        if banned:
            errors.append("an adjustment may not carry " + ", ".join(sorted(banned)))
    return errors
