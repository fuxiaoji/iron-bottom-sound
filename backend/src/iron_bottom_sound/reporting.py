"""Event-driven reporting and radio policy (IBS-R-CD-05/11, v2.3 IR-5).

The v2.2 mode had every formation report every phase: 68 reports in a 7-turn battle on one
occasion and 40 in another, most of them saying "no change".  Traffic that carries no
information still occupies channel slots, still queues, and still buries the reports that
matter - and, worse, it makes a commander's picture look fresher than it is.

v2.3 drafts a report when something happened, and when the radio policy allows it:

    NEW_CONTACT          -> CONTACT_REPORT
    MAJOR_DAMAGE         -> DAMAGE_REPORT
    MISSION_DEVIATION    -> DEVIATION_REPORT   (the formation agent asks for it)
    MISSION_COMPLETE     -> MISSION_STATUS
    FLAGSHIP_LOSS        -> URGENT REPORT
    CLARIFICATION_NEEDED -> CLARIFICATION_REQUEST
    PERIODIC_DUE         -> SITREP, only if the standing order asked for it

Radio policy is a per-formation setting:

    NORMAL            everything may transmit
    CONTACT_ONLY      contact and urgent traffic only; no routine sitrep
    SCHEDULED_WINDOW  routine traffic only while the window is open
    STRICT_SILENCE    no routine traffic at all; only the emergencies a formation cannot
                      choose to withhold (it is under attack, or its flagship is gone)

The policy is checked *before* a message is drafted, and the suppression is recorded, so
an agent can never be made to say "maintaining radio silence" in the same turn as a
routine transmission - the transmission does not happen.
"""
from __future__ import annotations

from dataclasses import dataclass

from .command_observation import formation_members
from .models import MessageKind, MessagePrecedence, RadioPolicy

MAJOR_DAMAGE_DROP = 0.2          # a fifth of the formation's hull, in one phase
URGENT_KINDS = (MessageKind.CONTACT_REPORT, MessageKind.DEVIATION_REPORT)
ROUTINE_KINDS = (MessageKind.SITREP,)


@dataclass(frozen=True)
class Trigger:
    """Why a report is being drafted (recorded on the message)."""

    kind: str                    # NEW_CONTACT | MAJOR_DAMAGE | FLAGSHIP_LOSS | ...
    message_kind: MessageKind
    precedence: MessagePrecedence
    detail: str

    @property
    def is_routine(self) -> bool:
        return self.message_kind in ROUTINE_KINDS


def hull_fraction(state, formation) -> float:
    from . import delegation

    return float(delegation.own_hull_fraction(state, formation))


def detect_triggers(state, formation, *, contacts: int, last_hull: float | None,
                    last_contacts: int | None, order) -> list[Trigger]:
    """What has happened to this formation since the last time it spoke."""
    triggers: list[Trigger] = []
    flagship = state.ships.get(formation.flagship_id)
    if flagship is not None and flagship.sunk:
        triggers.append(Trigger(
            "FLAGSHIP_LOSS", MessageKind.CONTACT_REPORT, MessagePrecedence.URGENT,
            f"旗舰 {formation.flagship_id} 已沉没",
        ))
        return triggers          # nothing else matters while the flagship is gone
    hull = hull_fraction(state, formation)
    if last_hull is not None and hull <= last_hull - MAJOR_DAMAGE_DROP:
        triggers.append(Trigger(
            "MAJOR_DAMAGE", MessageKind.CONTACT_REPORT, MessagePrecedence.URGENT,
            f"编队损伤 {round(last_hull, 2)} → {round(hull, 2)}",
        ))
    if contacts and (last_contacts is None or contacts > last_contacts):
        triggers.append(Trigger(
            "NEW_CONTACT", MessageKind.CONTACT_REPORT, MessagePrecedence.URGENT,
            f"接触数 {last_contacts or 0} → {contacts}",
        ))
    if not triggers and order is not None and order.deadline_turn is not None \
            and state.turn >= order.deadline_turn:
        triggers.append(Trigger(
            "MISSION_COMPLETE", MessageKind.SITREP, MessagePrecedence.ROUTINE,
            f"命令期限 T{order.deadline_turn} 已到",
        ))
    if not triggers and periodic_due(state, order):
        triggers.append(Trigger(
            "PERIODIC_DUE", MessageKind.SITREP, MessagePrecedence.ROUTINE,
            "现行命令要求定期报告",
        ))
    return triggers


def periodic_due(state, order) -> bool:
    """A periodic sitrep is due only because the standing order asked for one."""
    if order is None:
        return False
    requirements = [str(item).upper() for item in (order.report_requirements or [])]
    # Explicit markers only: the v2.2 default text "sitrep each turn the link supports it"
    # is exactly the doctrine IR-5 removes, so a bare mention of a sitrep must not
    # resurrect it.
    if not any("PERIODIC" in item or "定期" in item or "SCHEDULED" in item
               or "EACH TURN" in item
               for item in requirements):
        return False
    window = getattr(order, "report_window_turns", None) or []
    if window:
        return state.turn in window
    return state.turn % 3 == 0      # a three-turn staff cycle, stated as an abstraction


def policy_allows(policy: str, trigger: Trigger, *, window_open: bool,
                  under_attack: bool) -> tuple[bool, str]:
    """May this report be transmitted under the current radio policy?"""
    policy = (policy or RadioPolicy.NORMAL.value).upper()
    if policy in (RadioPolicy.NORMAL.value.upper(), "NORMAL"):
        return True, ""
    if policy == "CONTACT_ONLY":
        if trigger.is_routine:
            return False, "CONTACT_ONLY：禁止例行态势报告"
        return True, ""
    if policy == "SCHEDULED_WINDOW":
        if trigger.is_routine and not window_open:
            return False, "SCHEDULED_WINDOW：例行报告只在窗口内发送"
        return True, ""
    if policy == "STRICT_SILENCE":
        # silence is a choice a commander makes - except when it is not: a formation
        # taking damage or losing its flagship cannot withhold that.
        if under_attack:
            return True, "STRICT_SILENCE：遇袭例外"
        if trigger.is_routine:
            return False, "STRICT_SILENCE：禁止例行通报"
        return False, "STRICT_SILENCE：非紧急事项一律不发"
    return True, ""


def policy_note(policy: str) -> str:
    """One line for the agent's prompt, so it does not claim silence while transmitting."""
    return {
        "NORMAL": "通信政策：正常，可发例行与紧急报告。",
        "CONTACT_ONLY": "通信政策：仅限接触与紧急报告，不要发例行态势。",
        "SCHEDULED_WINDOW": "通信政策：例行报告只在指定窗口发送。",
        "STRICT_SILENCE": "通信政策：严格静默；除遇袭或旗舰损失外不得发报。",
    }.get((policy or "NORMAL").upper(), "通信政策：正常。")
