"""Per-recipient causal information (IBS-R-CD-10, v2.3).

The rule, stated once and enforced in one place:

    a formation may know an enemy fact only if it observed it, or a message carrying it
    was delivered **to that formation** at or before the current turn.

Why this module exists: the v2.2 mode gave every formation its siblings' last reported
positions (``_external_reports`` read the fleet's copy of those reports).  Nothing had
been delivered to the formation in question - the fleet simply held the report - so a
formation could act on a sibling's sighting before any traffic reached it.  That is the
"per-formation causal information boundary" the PI marked FAIL.

The ledger here is the replacement: every fact carries who observed it, when it was true,
who holds it, and (for anything learned rather than seen) the message that carried it.
``knowledge_for`` is the only reader, and it never consults another formation's memory or
the fleet's picture.
"""
from __future__ import annotations

from .models import KnowledgeItem

MAX_ITEMS_PER_FORMATION = 400
ENEMY_FIELDS = ("POSITION", "HEADING", "SPEED", "SHIP_TYPE")


def knowledge_for(state, formation_id: str) -> list[KnowledgeItem]:
    """This formation's knowledge, and nothing else's."""
    mode = state.command_delay
    if mode is None:
        return []
    return list(mode.knowledge.get(formation_id, []))


def record_local_observation(state, formation_id: str, side, contacts: list[dict],
                             turn: int) -> list[KnowledgeItem]:
    """Facts this formation's own lookouts produced this turn."""
    if not contacts:
        return []
    mode = state.command_delay
    recorded: list[KnowledgeItem] = []
    bucket = mode.knowledge.setdefault(formation_id, [])
    for contact in contacts:
        ship_id = contact.get("ship_id")
        if not ship_id:
            continue
        pairs = (
            ("POSITION", contact.get("position")),
            ("HEADING", contact.get("heading")),
            ("SPEED", contact.get("speed")),
            ("SHIP_TYPE", contact.get("ship_type")),
        )
        for field, value in pairs:
            if value is None:
                continue
            item = KnowledgeItem(
                subject_id=ship_id, field=field, value=value, observed_turn=turn,
                received_turn=turn, source_kind="LOCAL_OBSERVATION",
                source_id=formation_id, confidence="CONFIRMED",
            )
            recorded.append(item)
            bucket.append(item)
    if len(bucket) > MAX_ITEMS_PER_FORMATION:
        del bucket[:-MAX_ITEMS_PER_FORMATION]
    return recorded


def record_delivered_report(state, message) -> list[KnowledgeItem]:
    """Facts carried by a report that has just been delivered to its addressee.

    Only the addressee learns anything, and only what the report actually carries: the
    reporting formation's own position/heading/speed/ship count (structured), and a
    ``REPORTED``-confidence pointer to the report's prose for anything else.  A formation
    that was not addressed learns nothing - which is the point.
    """
    payload = message.payload or {}
    snapshot = payload.get("report") or {}
    reporter = snapshot.get("reporting_formation_id") or message.destination
    if not reporter:
        return []
    mode = state.command_delay
    holder = message.destination
    bucket = mode.knowledge.setdefault(holder, [])
    guided = (
        (snapshot.get("guide_position") or {}).get("label")
        if isinstance(snapshot.get("guide_position"), dict)
        else snapshot.get("guide_position")
    )
    recorded: list[KnowledgeItem] = []
    for field, value in (
        ("POSITION", guided),
        ("HEADING", snapshot.get("guide_heading")),
        ("SPEED", snapshot.get("guide_speed")),
        ("SHIP_COUNT", snapshot.get("ship_count")),
    ):
        if value is None:
            continue
        item = KnowledgeItem(
            subject_id=reporter, field=field, value=value,
            observed_turn=int(message.issued_turn), received_turn=message.delivered_turn,
            source_kind="DELIVERED_MESSAGE", source_id=reporter,
            message_id=message.message_id, confidence="REPORTED",
        )
        recorded.append(item)
        bucket.append(item)
    text = str(payload.get("report_text") or "").strip()
    if text:
        item = KnowledgeItem(
            subject_id=reporter, field="REPORT_TEXT", value=text[:600],
            observed_turn=int(message.issued_turn), received_turn=message.delivered_turn,
            source_kind="DELIVERED_MESSAGE", source_id=reporter,
            message_id=message.message_id, confidence="REPORTED",
        )
        recorded.append(item)
        bucket.append(item)
    if len(bucket) > MAX_ITEMS_PER_FORMATION:
        del bucket[:-MAX_ITEMS_PER_FORMATION]
    return recorded


def knowledge_payload(state, formation_id: str, *, limit: int = 40) -> list[dict]:
    """JSON view for the observation and the debug surface (most recent first)."""
    items = knowledge_for(state, formation_id)
    return [
        {
            "subject_id": item.subject_id, "field": item.field, "value": item.value,
            "observed_turn": item.observed_turn, "received_turn": item.received_turn,
            "age_turns": item.age_turns, "source_kind": item.source_kind,
            "source_id": item.source_id, "message_id": item.message_id,
            "confidence": item.confidence,
        }
        for item in items[-limit:][::-1]
    ]
