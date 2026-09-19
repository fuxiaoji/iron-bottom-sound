"""D0 — ResearchGroupExecutor: partition-constrained macro decisions expanded
to ordinary per-ship MovementOrders under CLASSIC engine semantics.

Why this exists (plan §8): comparing classic vs realistic modes confounds
control granularity with rule changes (shared speed, detach, disruption,
withdrawal). This wrapper holds the engine semantics fixed at classic and
varies ONLY the number of decision entities.

Design
------
* ``macro_for_group(state, engine, group) -> plan str`` — the group's single
  macro decision (a plan string for the group's lead ship).
* Expansion: the group's executed joint plan = the lead ship's plan; every
  other member receives the leader's plan **copied through the engine's own
  path machinery** (``movement_candidates`` per member), so every order is an
  ordinary legal classic order. No realistic-mode rule is triggered.
* Macro vocabulary (first version, plan §8.3):
    HOLD              everyone stays (plan "0" where legal, else each ship's
                      minimal plan — surfaced, never silently altered)
    STRAIGHT_SLOW     lead advances at min legal speed along current heading
    STRAIGHT_FAST     lead advances at max legal speed along current heading
    TURN_PORT_60      lead turns left 60 then advances
    TURN_STARBOARD_60 lead turns right 60 then advances
    LEADER_PROPOSAL   the TacticalCommander's own chosen plan for the lead ship,
                      copied to members (classic-legal follower mimicry)
* No silent repair: if a member cannot legally execute the copied plan, the
  executor raises ``MacroInvalid`` — callers see the failure (the A oracle
  treats it as -inf value for that macro), it is never swapped for another
  action.

Membership note: a partition groups the ships ALIVE at the snapshot. Orders
are only produced for ships with a position; a dead ship in a partition is
skipped (it produces no order in classic either).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend" / "src"))

MACROS = ("HOLD", "STRAIGHT_SLOW", "STRAIGHT_FAST",
          "TURN_PORT_60", "TURN_STARBOARD_60", "LEADER_PROPOSAL")


class MacroInvalid(Exception):
    """A macro action cannot be executed legally by some member. Never silently
    repaired."""


@dataclass
class GroupOrder:
    group: tuple[str, ...]
    macro: str
    lead_plan: str
    member_plans: dict[str, str]   # ship_id -> plan (lead included)
    invalid_members: list[str]


def _plans_for(engine, state, ship_id: str) -> dict[str, str]:
    """Legal plan strings for one ship: candidate plans from the engine."""
    ship = state.ships[ship_id]
    if ship.sunk or not ship.position:
        return {}
    info = engine.movement_candidates(state, ship, include_plans=True)
    plans = {}
    for entry in info.get("reachable", []):
        plan = entry.get("plan")
        if plan is not None:
            plans[plan] = entry.get("cost", 0)
    # hold: the engine does not list the current hex (no cost-0 entry); a
    # stationary order in classic is plan "0" only when the ship is required to
    # move — the candidate table tells us: empty reachable means forced move.
    if info.get("reachable"):
        plans.setdefault("0", 0)  # candidate only when holding is possible
    return plans


def plan_for_macro(engine, state, ship_id: str, macro: str,
                   leader_proposal: str | None = None) -> str:
    """Resolve a macro to a concrete plan for the lead ship, from its OWN legal
    plan table. Raises MacroInvalid if impossible."""
    plans = _plans_for(engine, state, ship_id)
    ship = state.ships[ship_id]
    heading = ship.heading
    if macro == "LEADER_PROPOSAL":
        if leader_proposal is None or leader_proposal not in plans:
            raise MacroInvalid(f"{ship_id}: leader proposal {leader_proposal!r} not legal")
        return leader_proposal
    if macro == "HOLD":
        if "0" not in plans:
            raise MacroInvalid(f"{ship_id}: HOLD not legal (ship must move)")
        return "0"
    # directional macros: filter the plan table by executed displacement &
    # final heading. Plan strings are sequences of P/S/<digits>.
    best = None
    for plan, cost in plans.items():
        if plan == "0":
            continue
        turns = plan.count("P") - plan.count("S")
        advance = sum(int(ch) for ch in plan if ch.isdigit())
        final_heading = ((heading - 1 + turns) % 6) + 1
        if macro == "STRAIGHT_SLOW" and turns == 0 and advance > 0:
            score = (advance, -cost)
        elif macro == "STRAIGHT_FAST" and turns == 0 and advance > 0:
            score = (-advance, -cost)
        elif macro == "TURN_PORT_60" and turns < 0 and advance > 0:
            score = (advance, -cost)
        elif macro == "TURN_STARBOARD_60" and turns > 0 and advance > 0:
            score = (advance, -cost)
        else:
            continue
        if best is None or score > best[0]:
            best = (score, plan)
    if best is None:
        raise MacroInvalid(f"{ship_id}: no legal plan for macro {macro}")
    return best[1]


def execute_partition(engine, state, side, partition,
                      macro_choices: dict[str, str],
                      leader_proposals: dict[str, str] | None = None,
                      commander=None) -> list[GroupOrder]:
    """Expand one macro decision per group into per-ship plans.

    ``macro_choices`` maps group-tuple -> macro name.  For every non-lead
    member we copy the lead plan IF the member can legally execute it; members
    that cannot raise MacroInvalid (no silent repair).  Returns GroupOrder list.
    """
    orders: list[GroupOrder] = []
    for group in partition:
        members = []
        for ship_id in group:
            ship = state.ships.get(ship_id)
            if ship is None or ship.sunk or not ship.position:
                continue
            members.append(ship_id)
        if not members:
            continue
        macro = macro_choices.get(group)
        if macro is None:
            raise ValueError(f"no macro for group {group}")
        proposal = (leader_proposals or {}).get(group)
        lead_plan = plan_for_macro(engine, state, members[0], macro, proposal)
        member_plans = {members[0]: lead_plan}
        invalid: list[str] = []
        for member in members[1:]:
            plans = _plans_for(engine, state, member)
            if lead_plan in plans:
                member_plans[member] = lead_plan
            else:
                # copying is impossible: NOT silently repaired
                raise MacroInvalid(
                    f"member {member} cannot execute lead plan {lead_plan!r} "
                    f"(macro {macro}); candidates={sorted(plans)[:5]}")
        orders.append(GroupOrder(group=tuple(members), macro=macro,
                                 lead_plan=lead_plan, member_plans=member_plans,
                                 invalid_members=invalid))
    return orders


def orders_to_batch(engine, state, side, group_orders) -> "object":
    """Wrap expanded plans into an OrderBatch for validation."""
    from iron_bottom_sound.models import MovementOrder, OrderBatch, Phase
    batch = OrderBatch(side=side, phase=Phase.MOVEMENT_PLANNING)
    for go in group_orders:
        for ship_id, plan in go.member_plans.items():
            cost = None
            info = engine.movement_candidates(state, state.ships[ship_id],
                                              include_plans=True)
            for entry in info.get("reachable", []):
                if entry.get("plan") == plan:
                    cost = entry.get("cost", entry.get("speed", 0))
                    break
            batch.movement.append(MovementOrder(ship_id=ship_id, plan=plan,
                                                speed=cost))
    return batch
