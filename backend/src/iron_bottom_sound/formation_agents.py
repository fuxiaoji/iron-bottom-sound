"""Formation agents: one protocol for deterministic, LLM and future ML policies.

Authority boundary (the part that must never drift)
---------------------------------------------------
A formation agent **cannot** issue a ``GunneryOrder``: no mounts, no firing
solution, no hit modifier, no expected-hit calculation.  It emits a movement
action chosen from the engine's own enumerated list, a contingency branch, and
**bounded** target-priority adjustments.  ``target_priority.validate_agent_decision_shape``
is the structural guard, and the engine generates every final gunnery order.

Local observation only
----------------------
The input is a ``FormationObservation`` (``command_observation``): this
formation's own state, its own ships' contacts, its received messages and its
stale external reports.  There is no field carrying side-global truth, so an
agent cannot read the world it is not entitled to — the guarantee is a property
of the data, not of agent good behaviour.

Determinism
-----------
``DeterministicFormationAgent`` is a pure function of its inputs.  Every ordering
is by explicit sort keys; no set iteration order reaches a decision (see defect
CD0-F1).  The same observation always yields the same decision, which is what
makes a local-agent decision replayable and auditable (acceptance criterion 10).
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from . import delegation
from .command_observation import (
    LOCAL_PRIORITY_WEIGHT_LIMIT,
    REPORT_ACTIONS,
    FormationObservation,
)
from .models import (
    ContingencyBranch,
    FormationMovementOrder,
    MissionOrder,
    Phase,
)

# The doctrine's default movement weight set.  Declared constants, not learned
# parameters: this agent is the inert baseline the LLM and future ML policies are
# compared against.
OBJECTIVE_WEIGHT = 1.0
STATION_KEEPING_WEIGHT = 1.5
ENGAGEMENT_RANGE = 6
CONTACT_CLOSING_WEIGHT = 2.0
# Bounded local adjustment, well inside the observation's declared limit.
LOCAL_ADJUSTMENT = 0.2


class TargetPriorityAdjustment(BaseModel):
    """A bounded preference weight.  It cannot carry gunnery machinery."""

    target_id: str | None = None
    target_class: str | None = None
    weight: float = Field(default=0.0, ge=-LOCAL_PRIORITY_WEIGHT_LIMIT,
                          le=LOCAL_PRIORITY_WEIGHT_LIMIT)
    reason: str = ""

    def as_directive(self, formation_id: str, expires_turn: int | None = None):
        from .models import TargetPriorityDirective

        return TargetPriorityDirective(
            formation_id=formation_id,
            source="LOCAL_AGENT",
            target_id=self.target_id,
            target_class=self.target_class,
            weight=self.weight,
            expires_turn=expires_turn,
        )


class FormationDecision(BaseModel):
    """What a formation agent may decide.  Note the absence of gunnery fields."""

    formation_id: str
    turn: int
    phase: Phase
    selected_movement_action_id: str | None = None
    # Copied from the enumerated action, never synthesised by the agent.
    selected_movement_plan: str | None = None
    selected_contingency_branch: str | None = None
    target_priority_adjustments: list[TargetPriorityAdjustment] = Field(default_factory=list)
    report_actions: list[str] = Field(default_factory=list)
    acknowledgement: bool = False
    rationale_summary: str = ""
    # The agent's message to its own next turn, stored verbatim in its memory.
    memory_note: str = ""
    # Audit only: what was rejected and why.
    audit: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class FormationPolicy(Protocol):
    """The common protocol for deterministic, LLM and future ML agents."""

    name: str

    def act(
        self,
        local_observation: FormationObservation,
        mission_order: MissionOrder | None,
        comm_state: dict[str, Any],
        legal_action_mask: list[dict[str, Any]],
        target_priority_space: list[dict[str, Any]],
        contract_state: dict[str, Any] | None = None,
        *,
        memory_text: str | None = None,
        order_text: str | None = None,
    ) -> FormationDecision:
        ...


class DeterministicFormationAgent:
    """The baseline local agent: doctrine ladder, no learning, no randomness."""

    name = "deterministic-formation-v1"

    def act(
        self,
        local_observation: FormationObservation,
        mission_order: MissionOrder | None = None,
        comm_state: dict[str, Any] | None = None,
        legal_action_mask: list[dict[str, Any]] | None = None,
        target_priority_space: list[dict[str, Any]] | None = None,
        contract_state: dict[str, Any] | None = None,
        *,
        memory_text: str | None = None,
        order_text: str | None = None,
    ) -> FormationDecision:
        del contract_state, memory_text  # CD-6 hook and memory: unused by the baseline policy
        legal = list(legal_action_mask if legal_action_mask is not None
                     else local_observation.legal_formation_actions)
        space = list(target_priority_space if target_priority_space is not None
                     else local_observation.legal_target_priority_options)
        comm = dict(comm_state if comm_state is not None else local_observation.comm_state)
        contacts = list(local_observation.local_contacts)
        hull_fraction = _hull_fraction(local_observation)
        order_received = mission_order is not None
        if mission_order is None:
            # No order has been confirmed yet: the pre-briefed standing plan
            # applies, so the agent still runs the same doctrine ladder instead of
            # improvising a task of its own.
            mission_order = delegation.standing_plan(
                formation_id=local_observation.formation_id,
                side=local_observation.side,
                turn=local_observation.turn,
            )
        active = delegation.activate_branches(
            mission_order,
            received=local_observation.received_messages,
            local_contacts=contacts,
            own_hull_fraction=hull_fraction,
            own_ship_count=len(local_observation.formation_state.get("ships", [])),
            link_status=local_observation.link_status,
        )
        branch = _select_branch(active)
        withdraw = any(
            "withdraw" in item.get("fallback_task", "") for item in active
        )
        objective = _objective(local_observation, mission_order, contacts, branch)
        chosen, audit = _choose_action(
            legal, objective, contacts, local_observation.formation_state, withdraw,
        )
        adjustments = _adjustments(space, mission_order, contacts)
        reports, acknowledgement = _reports(
            local_observation, mission_order, contacts, branch, active,
        )
        return FormationDecision(
            formation_id=local_observation.formation_id,
            turn=local_observation.turn,
            phase=local_observation.phase,
            selected_movement_action_id=chosen.get("action_id") if chosen else None,
            selected_movement_plan=chosen.get("plan") if chosen else None,
            selected_contingency_branch=branch,
            target_priority_adjustments=adjustments,
            report_actions=reports,
            acknowledgement=acknowledgement,
            rationale_summary=(
                _rationale(local_observation, branch, chosen, contacts, comm)
                + (f" | 上级命令：{order_text}" if order_text else " | 未收到上级命令")
            ),
            audit={**audit, "active_branches": active,
                   "hull_fraction": round(hull_fraction, 3), "withdraw": withdraw,
                   "order_received": order_received},
        )


# --------------------------------------------------------------------------- internals

def _hull_fraction(observation: FormationObservation) -> float:
    ships = observation.formation_state.get("ships", [])
    total = sum(int(ship.get("max_hull") or 0) for ship in ships)
    current = sum(int(ship.get("hull") or 0) for ship in ships)
    return (current / total) if total else 1.0


def _select_branch(active: list[dict[str, Any]]) -> str | None:
    """The branch the doctrine ladder puts first.

    Order is the plan's: an authorised contingency outranks local optimisation,
    and among branches the loss-of-communication fallback is the most binding
    because it is the one that says the fleet can no longer be asked.
    """
    order = (
        ContingencyBranch.LOSS_OF_COMM_BRANCH.value,
        ContingencyBranch.EXPLICIT_SIGNAL_BRANCH.value,
        ContingencyBranch.LOCAL_CONDITION_BRANCH.value,
    )
    present = {item["branch"] for item in active}
    return next((name for name in order if name in present), None)


def _objective(
    observation: FormationObservation,
    mission_order: MissionOrder | None,
    contacts: list[dict[str, Any]],
    branch: str | None,
) -> tuple[int, int] | None:
    """The hex the formation is trying to reach, as ``(q, r)``.

    An explicit waypoint wins; otherwise, under a local-condition branch, the
    nearest local contact becomes the objective (intercept inside the task
    boundary).  With neither, ``None`` means keep station — the agent has no
    authority to invent a destination.
    """
    if mission_order is not None and mission_order.waypoint is not None:
        return (mission_order.waypoint.q, mission_order.waypoint.r)
    if branch == ContingencyBranch.LOCAL_CONDITION_BRANCH.value and contacts:
        nearest = min(
            contacts,
            key=lambda item: (
                item.get("range") if item.get("range") is not None else 99,
                item["ship_id"],
            ),
        )
        return _contact_axial(observation, nearest)
    return None


def _contact_axial(
    observation: FormationObservation, contact: dict[str, Any],
) -> tuple[int, int] | None:
    """Axial coordinates of a contact, resolved through the local map.

    A local agent knows a contact as a hex *label* exactly as its lookouts report
    it; the local map is the only place the label-to-axial mapping is available to
    it, which is why the resolution goes through ``local_map`` and not through
    engine state.
    """
    label = contact.get("position")
    if not label:
        return None
    for cell in observation.local_map:
        if cell["hex"] == label:
            return (int(cell["q"]), int(cell["r"]))
    return None


def _choose_action(
    legal: list[dict[str, Any]],
    objective: tuple[int, int] | None,
    contacts: list[dict[str, Any]],
    formation_state: dict[str, Any],
    withdraw: bool,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Pick one enumerated action; the plan is copied, never invented."""
    audit: dict[str, Any] = {"legal_actions": len(legal)}
    if not legal:
        audit["rejected"] = "no legal action"
        return None, audit
    speed = int(formation_state.get("speed") or 0)
    ranges = [item["range"] for item in contacts if item.get("range") is not None]
    nearest = min(ranges) if ranges else None
    scored: list[tuple[tuple[float, float, str, str], dict[str, Any]]] = []
    for action in legal:
        cell = _action_axial(action)
        progress = 0.0
        if objective is not None and cell is not None:
            distance = _axial_distance(cell, objective)
            # Withdrawing inverts the objective: the sanest reading of "withdraw
            # and rendezvous" for a local agent is to open the range.
            progress = float(distance if withdraw else -distance) * OBJECTIVE_WEIGHT
        closing = 0.0
        if cell is not None and objective is not None and nearest is not None:
            approach = float(_axial_distance(cell, objective))
            if withdraw:
                closing = approach * CONTACT_CLOSING_WEIGHT
            else:
                closing = -abs(approach - ENGAGEMENT_RANGE) * CONTACT_CLOSING_WEIGHT
        station = -abs(int(action.get("cost") or 0) - speed) * STATION_KEEPING_WEIGHT
        key = (
            progress + closing + station,
            float(-(int(action.get("cost") or 0))),
            str(action.get("label") or ""),
            str(action.get("plan") or ""),
        )
        scored.append((key, action))
    best_key, best = max(scored, key=lambda item: item[0])
    audit["score_key"] = list(best_key)
    return best, audit


def _action_axial(action: dict[str, Any]) -> tuple[int, int] | None:
    hexc = action.get("hex")
    if isinstance(hexc, dict) and "q" in hexc and "r" in hexc:
        return (int(hexc["q"]), int(hexc["r"]))
    return None


def _axial_distance(left: tuple[int, int], right: tuple[int, int]) -> int:
    dq = left[0] - right[0]
    dr = left[1] - right[1]
    return (abs(dq) + abs(dr) + abs((-dq) - (-dr))) // 2


def _adjustments(
    space: list[dict[str, Any]],
    mission_order: MissionOrder | None,
    contacts: list[dict[str, Any]],
) -> list[TargetPriorityAdjustment]:
    """Weight the locally visible contact that best matches the fleet priority."""
    if not contacts:
        return []
    preferred: list[str] = []
    if mission_order is not None:
        preferred = [
            directive.target_class
            for directive in sorted(
                mission_order.target_priority_directives,
                key=lambda item: (-item.weight, item.target_class or ""),
            )
            if directive.target_class
        ]
    adjustments: list[TargetPriorityAdjustment] = []
    for contact in sorted(contacts, key=lambda item: item["ship_id"]):
        target_class = contact.get("target_class") or contact.get("ship_type")
        if preferred and target_class in preferred:
            rank = preferred.index(target_class)
            weight = max(0.05, LOCAL_ADJUSTMENT - 0.05 * rank)
            adjustments.append(TargetPriorityAdjustment(
                target_id=contact["ship_id"],
                target_class=target_class,
                weight=round(weight, 3),
                reason=f"locally sighted {target_class} matching the fleet priority list",
            ))
        else:
            adjustments.append(TargetPriorityAdjustment(
                target_id=contact["ship_id"],
                target_class=target_class,
                weight=-round(LOCAL_ADJUSTMENT / 2, 3),
                reason="locally sighted but outside the fleet priority list",
            ))
    return adjustments


def _reports(
    observation: FormationObservation,
    mission_order: MissionOrder | None,
    contacts: list[dict[str, Any]],
    branch: str | None,
    active: list[dict[str, Any]],
) -> tuple[list[str], bool]:
    reports: list[str] = []
    unacknowledged = (
        mission_order is not None
        and not any(
            message.kind.value == "acknowledgement"
            for message in observation.received_messages
        )
    )
    if unacknowledged:
        reports.append("ACKNOWLEDGEMENT")
    if contacts:
        reports.append("CONTACT_REPORT")
    else:
        reports.append("SITREP")
    if branch is not None and branch != ContingencyBranch.LOSS_OF_COMM_BRANCH.value:
        reports.append("DEVIATION_REPORT")
    if not reports:
        reports.append("NONE")
    reports = [name for name in reports if name in REPORT_ACTIONS]
    return sorted(set(reports)), unacknowledged


def _rationale(
    observation: FormationObservation,
    branch: str | None,
    chosen: dict[str, Any] | None,
    contacts: list[dict[str, Any]],
    comm: dict[str, Any],
) -> str:
    return (
        f"{observation.formation_name}: link={observation.link_status.value}, "
        f"authority={observation.authority.value}, contacts={len(contacts)}, "
        f"branch={branch or 'none'}, action={chosen.get('action_id') if chosen else 'hold'}"
    )


# --------------------------------------------------------------------------- application

def decision_orders(
    decision: FormationDecision, formation_id: str,
) -> list[FormationMovementOrder]:
    """Translate a decision into the only order type an agent may produce."""
    if decision.selected_movement_plan is None:
        return []
    return [FormationMovementOrder(
        formation_id=formation_id,
        leader_plan=decision.selected_movement_plan,
        movement_style=None,
    )]


def decision_to_priority_directives(decision: FormationDecision):
    """Fleet-visible form of the agent's bounded adjustments."""
    return [
        adjustment.as_directive(decision.formation_id)
        for adjustment in decision.target_priority_adjustments
    ]


def plan_from_decision(decision: FormationDecision) -> str | None:
    """The plan the commander may submit, or ``None`` to keep the tactical plan."""
    return decision.selected_movement_plan
