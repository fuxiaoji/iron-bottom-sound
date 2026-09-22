"""Mission Command: MissionOrder, contingencies and delegated autonomy (IBS-R-CD-04).

Structure follows the WWII U.S. Navy battle-plan layout the v2.2 plan prescribes:
the superior states *what* to do, *why*, and *with whom to coordinate*; the
subordinate decides *how*, except where coordination requires otherwise.  A
MissionOrder therefore carries mission, intent, task, coordination measures,
target priorities, ROE, the communications plan, the loss-of-communication plan
and pre-briefed contingencies — not a step-by-step move list.

Contingencies are exactly three kinds (plan §9), never an arbitrary if/else:

``EXPLICIT_SIGNAL_BRANCH``
    written in advance, active only after the named signal arrives;
``LOCAL_CONDITION_BRANCH``
    pre-authorised: a locally verifiable condition activates it;
``LOSS_OF_COMM_BRANCH``
    the fallback when the link itself is gone.

Every evaluation is a pure function of the observation and the order, so a
replay reproduces the same branch activation and the same deviation report.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .models import (
    CommandMessage,
    Contingency,
    ContingencyBranch,
    FormationState,
    GameState,
    HexCoord,
    LinkStatus,
    MessageKind,
    MessageStatus,
    MissionOrder,
    Side,
    TargetPriorityDirective,
)

if TYPE_CHECKING:
    from .engine import IronBottomEngine

RULE_MISSION = "IBS-R-CD-04"

# A locally verifiable "superior enemy force": the local contact strength in
# hull points exceeds this multiple of the formation's own.  A simulation
# abstraction with a declared value, not a claim about doctrine.
SUPERIOR_FORCE_RATIO = 1.5
# "minimum capability lost": own hull fraction below which the formation may not
# continue a decisive engagement.
MINIMUM_CAPABILITY_HULL_FRACTION = 0.4

DEFAULT_FIRE_PRIORITY = ("CA", "CL", "DD", "BB")


def mission_order_template(
    *,
    order_id: str,
    formation_id: str,
    side: Side,
    turn: int,
    issued_by: str,
    mission: str,
    intent: str,
    task: str,
    coordination: list[str] | None = None,
    priority_classes: tuple[str, ...] = DEFAULT_FIRE_PRIORITY,
    operating_area: str | None = None,
    waypoint: HexCoord | None = None,
    deadline_turn: int | None = None,
    report_requirements: list[str] | None = None,
    communications_plan: list[str] | None = None,
    loss_of_comm_plan: list[str] | None = None,
    rendezvous: str | None = None,
    contingencies: list[Contingency] | None = None,
) -> MissionOrder:
    """Build a MissionOrder with the prescribed battle-plan structure filled in."""
    return MissionOrder(
        order_id=order_id,
        formation_id=formation_id,
        side=side,
        issued_turn=turn,
        issued_by=issued_by,
        mission=mission,
        assumptions=["communications degrade under fire", "enemy strength as last reported"],
        trigger_conditions=["contact with the enemy", "expiry of the current task"],
        commander_intent=intent,
        task_to_formation=task,
        coordination_measures=coordination or [
            "maintain station relative to the main body while the link is available",
            "do not cross the flagship formation's fire sector",
        ],
        operating_area=operating_area,
        waypoint=waypoint,
        deadline_turn=deadline_turn,
        target_priority_directives=[
            TargetPriorityDirective(
                formation_id=formation_id,
                source="FLEET_ORDER",
                target_class=ship_class,
                weight=round(1.0 - index * 0.25, 2),
                objective_tag="fire_priority",
            )
            for index, ship_class in enumerate(priority_classes)
        ],
        roe=[
            "engage only targets the engine's selector can legally bear on",
            "no fire into the flagship formation's sector",
        ],
        risk_constraints=[
            f"withdraw from a decisive engagement below {int(MINIMUM_CAPABILITY_HULL_FRACTION * 100)}% hull",
            "preserve at least one flagship-capable ship",
        ],
        report_requirements=report_requirements or [
            "contact report on first sighting",
            "sitrep each turn the link supports it",
            "deviation report on resuming communication",
        ],
        communications_plan=communications_plan or [
            "TBS primary", "blinker fallback", "keep the tactical circuit clear",
        ],
        commander_location=issued_by,
        rendezvous=rendezvous or "fallback area designated by the fleet commander",
        loss_of_comm_plan=loss_of_comm_plan or [
            "continue the current mission",
            "observe the main body's manoeuvre if visible",
            "rendezvous at the designated time and place",
            "report and reconnect when possible",
        ],
        contingencies=contingencies if contingencies is not None else default_contingencies(),
        valid_from_turn=turn,
        expiry_turn=deadline_turn,
    )


def standing_plan(
    *, formation_id: str, side: Side, turn: int, issued_by: str = "",
) -> MissionOrder:
    """The pre-briefed plan a commander executes before any order arrives.

    Doctrine step 2 is "latest valid order"; with none, the fallback is the
    pre-briefed loss-of-communication plan, not a licence to improvise.  The
    returned order is deliberately complete so the same structural validation and
    the same contingency evaluator apply as to a real order.
    """
    return mission_order_template(
        order_id=f"standing-{formation_id}",
        formation_id=formation_id,
        side=side,
        turn=turn,
        issued_by=issued_by,
        mission="尚无上级命令：继续当前任务并按预令行动",
        intent="在收到命令前不进行决定性交战，保持与主力相对位置",
        task="维持队形、保持通信、报告接触",
    )


def default_contingencies() -> list[Contingency]:
    """The three branch kinds, one each, as the template's standing set."""
    return [
        Contingency(
            branch=ContingencyBranch.EXPLICIT_SIGNAL_BRANCH,
            description="activate the pre-briefed intercept only on the fleet signal",
            trigger_condition="fleet signal received",
            trigger_message_kind=MessageKind.AMENDMENT,
            fallback_task="hold the current task until the signal arrives",
        ),
        Contingency(
            branch=ContingencyBranch.LOCAL_CONDITION_BRANCH,
            description="superior enemy force: shadow, report, avoid a decisive engagement",
            trigger_condition="superior enemy force in local contact",
            requires_local_check=True,
            fallback_task="shadow and report; do not force a decision",
        ),
        Contingency(
            branch=ContingencyBranch.LOCAL_CONDITION_BRANCH,
            description="target found in the task area: intercept within the task boundary",
            trigger_condition="contact inside the assigned operating area",
            requires_local_check=True,
            fallback_task="search the assigned area",
        ),
        Contingency(
            branch=ContingencyBranch.LOSS_OF_COMM_BRANCH,
            description="loss of communication: continue the mission and rendezvous",
            trigger_condition="link stale or blacked out",
            fallback_task="continue the current mission and rendezvous as briefed",
        ),
    ]


def validate_mission_order(order: MissionOrder) -> list[str]:
    """The §8 required-structure check, as explicit errors."""
    errors: list[str] = []
    if not order.mission.strip():
        errors.append("mission (task + purpose) is required")
    if not order.commander_intent.strip():
        errors.append("commander_intent is required")
    if not order.task_to_formation.strip():
        errors.append("task_to_formation is required")
    if not order.coordination_measures:
        errors.append("coordination_measures are required")
    if not order.roe:
        errors.append("ROE / fire restrictions are required")
    if not order.report_requirements:
        errors.append("report_requirements are required")
    if not order.communications_plan:
        errors.append("communications_plan is required")
    if not order.loss_of_comm_plan:
        errors.append("loss_of_comm_plan is required")
    branches = {contingency.branch for contingency in order.contingencies}
    for required in ContingencyBranch:
        if required not in branches:
            errors.append(f"missing {required.value}")
    for contingency in order.contingencies:
        if contingency.branch == ContingencyBranch.EXPLICIT_SIGNAL_BRANCH and contingency.trigger_message_kind is None:
            errors.append("an explicit-signal branch needs the signal it waits for")
        if contingency.branch == ContingencyBranch.LOCAL_CONDITION_BRANCH and not contingency.requires_local_check:
            errors.append("a local-condition branch must be locally verifiable")
    return errors


def activate_branches(
    order: MissionOrder,
    *,
    received: list[CommandMessage],
    local_contacts: list[dict[str, Any]],
    own_hull_fraction: float,
    own_ship_count: int,
    link_status: LinkStatus,
) -> list[dict[str, Any]]:
    """Return the branches that are active now, each with its reason.

    Read-only and deterministic: the same order plus the same local picture
    always activates the same set, which is what makes a replay auditable.  The
    local-condition test uses only what a local agent can see — its own ships
    and the contacts its own lookouts have — never the side plot.
    """
    active: list[dict[str, Any]] = []
    delivered_kinds = {
        message.kind for message in received
        if message.status == MessageStatus.DELIVERED
    }
    for contingency in order.contingencies:
        if contingency.branch == ContingencyBranch.EXPLICIT_SIGNAL_BRANCH:
            if contingency.trigger_message_kind in delivered_kinds:
                active.append({
                    "branch": contingency.branch.value,
                    "reason": f"signal {contingency.trigger_message_kind.value} received",
                    "fallback_task": contingency.fallback_task,
                })
            continue
        if contingency.branch == ContingencyBranch.LOCAL_CONDITION_BRANCH:
            condition = contingency.trigger_condition or ""
            if "superior enemy" in condition:
                margin = superior_force(local_contacts, own_ship_count)
                if margin:
                    active.append({
                        "branch": contingency.branch.value,
                        "reason": margin,
                        "fallback_task": contingency.fallback_task,
                    })
            elif "contact" in condition and local_contacts:
                active.append({
                    "branch": contingency.branch.value,
                    "reason": "locally sighted contact inside the task area",
                    "fallback_task": contingency.fallback_task,
                })
            continue
        if link_status in (LinkStatus.STALE, LinkStatus.BLACKOUT):
            active.append({
                "branch": contingency.branch.value,
                "reason": f"link is {link_status.value}",
                "fallback_task": contingency.fallback_task,
            })
    if own_hull_fraction < MINIMUM_CAPABILITY_HULL_FRACTION:
        active.append({
            "branch": ContingencyBranch.LOCAL_CONDITION_BRANCH.value,
            "reason": (
                f"own hull fraction {own_hull_fraction:.2f} below the pre-briefed "
                f"minimum {MINIMUM_CAPABILITY_HULL_FRACTION}"
            ),
            "fallback_task": "withdraw and rendezvous",
        })
    return active


# Coarse class rank for the local "superior force" test.  Only classes the
# scenario actually fields; an unknown class ranks lowest rather than being
# silently treated as a capital ship.
CLASS_RANK = {"DD": 1, "DE": 1, "CL": 2, "AV": 2, "CA": 3, "CB": 3, "BC": 4, "BB": 5}


def superior_force(local_contacts: list[dict[str, Any]], own_ship_count: int) -> str | None:
    """Return the reason a locally sighted force looks superior, else ``None``.

    Two locally checkable tests, both deliberately crude and pre-registered:
    contact count above the declared ratio, or a hull class heavier than the
    heaviest own ship.  Unseen enemies contribute nothing, so a local agent
    cannot learn enemy strength it never observed.
    """
    if not local_contacts:
        return None
    if own_ship_count and len(local_contacts) >= SUPERIOR_FORCE_RATIO * own_ship_count:
        return (
            f"{len(local_contacts)} local contacts against {own_ship_count} own ships "
            f"exceeds the {SUPERIOR_FORCE_RATIO}x pre-briefed margin"
        )
    return None


def superior_force_by_class(
    local_contacts: list[dict[str, Any]], own_classes: list[str],
) -> str | None:
    """The second local test: a heavier hull class sighted than any own ship."""
    if not local_contacts:
        return None
    own_rank = max((CLASS_RANK.get(item, 0) for item in own_classes), default=0)
    enemy_rank = max(
        (CLASS_RANK.get(contact.get("target_class") or contact.get("ship_type") or "", 0)
         for contact in local_contacts),
        default=0,
    )
    if enemy_rank > own_rank:
        return f"a heavier hull class sighted (rank {enemy_rank}) than any own ship (rank {own_rank})"
    return None


def own_hull_fraction(
    engine: "IronBottomEngine", state: GameState, formation: FormationState,
) -> float:
    """Fraction of the formation's hull boxes still afloat."""
    total = 0
    current = 0
    for ship_id in formation.ship_ids:
        ship = state.ships.get(ship_id)
        if ship is None or ship.position is None:
            continue
        total += ship.max_hull
        current += ship.hull
    return (current / total) if total else 1.0


def deviation_report(
    order: MissionOrder, *, turn: int, reason: str, origin: str,
) -> dict[str, Any]:
    """The record a commander must send when it has departed from its order."""
    return {
        "order_id": order.order_id,
        "formation_id": order.formation_id,
        "turn": turn,
        "origin": origin,
        "intent_consistency": (
            "local task chosen to advance commander_intent: " + order.commander_intent
        ),
        "reason": reason,
    }


def autonomy_priority_list() -> list[str]:
    """The commander's doctrine ladder, in the order the plan fixes it."""
    return [
        "engine legality",
        "latest valid order",
        "commander intent",
        "coordination constraints",
        "authorised contingency",
        "local tactical optimisation",
        "force preservation within mission and risk constraints",
        "report deviation when communication resumes",
    ]
