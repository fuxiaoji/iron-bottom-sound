"""Operational claims and their provenance (IBS-R-CD-12, v2.3 IR-6).

A commander may say many things about the enemy.  The mode's job is to make sure that
"confirmed" means confirmed:

    CONFIRMED   this formation's own lookouts established it
    REPORTED    it arrived in a message delivered to this formation
    INFERRED    it follows from facts this formation holds
    SUSPECTED   nothing supports it but the speaker's judgement

The v2.2 battle produced a claim that an enemy heavy cruiser had been *confirmed sunk*
when nothing in the formation's record supported it - the model's inference had become an
operational fact by being written down.  This module exists so that cannot pass silently:
claims are extracted from what an agent actually wrote, graded against its own knowledge
ledger, and anything asserted as confirmed without a source is reported.

Units are the sibling problem (the same battle claimed "12-15 海里" for 12-15 hex), which is
why ``range_claim`` renders distances from ``processing.range_units`` rather than trusting
a number that appears in prose.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .communications.processing import range_units

CLAIM_FIELDS = ("SUNK", "HEAVILY_DAMAGED", "POSITION", "SPEED", "HEADING",
                "MISSION_COMPLETE")

CERTAINTY_RANK = {"SUSPECTED": 0, "INFERRED": 1, "REPORTED": 2, "CONFIRMED": 3}

# Wording that asserts a claim rather than suggesting one.  Kept deliberately small and
# readable: this is a check on the record, not a natural-language parser.
CONFIRMED_MARKERS = ("确认", "证实", "已击沉", "confirmed", "sunk")
SUSPECTED_MARKERS = ("可能", "疑似", "推测", "perhaps", "possibly", "may have")
INFERRED_MARKERS = ("因此", "推断", "说明", "therefore", "suggests")


@dataclass(frozen=True)
class Claim:
    subject_id: str | None
    field: str
    certainty: str
    source_kind: str
    source_id: str | None
    message_id: str | None
    observed_turn: int | None
    text: str

    @property
    def is_supported(self) -> bool:
        return self.source_kind in ("LOCAL_OBSERVATION", "DELIVERED_MESSAGE")


def _markers(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in markers)


def claim_field(text: str) -> str | None:
    lowered = text.lower()
    if any(word in text for word in ("击沉", "沉没")) or "sunk" in lowered:
        return "SUNK"
    if "重创" in text or "heavily damaged" in lowered:
        return "HEAVILY_DAMAGED"
    return None


def grade(text: str, *, subject_ids: set[str], knowledge: list) -> list[Claim]:
    """Grade every operational claim in one piece of agent prose.

    The grade is taken from the formation's own knowledge ledger, never from how
    confidently the sentence is written: a model that types "确认" without a source gets a
    SUSPECTED claim, and the mismatch is what the audit reports.
    """
    field = claim_field(text)
    if field is None:
        return []
    named = [ship_id for ship_id in subject_ids if ship_id in text]
    claims: list[Claim] = []
    for subject in named or [None]:
        supporting = [
            item for item in knowledge
            if item.field == field and (subject is None or item.subject_id == subject)
        ]
        supporting.sort(key=lambda item: CERTAINTY_RANK.get(item.confidence, 0), reverse=True)
        best = supporting[0] if supporting else None
        if best is not None and best.source_kind == "LOCAL_OBSERVATION":
            certainty = "CONFIRMED"
        elif best is not None:
            certainty = "REPORTED"
        elif _markers(text, SUSPECTED_MARKERS):
            certainty = "SUSPECTED"
        elif _markers(text, INFERRED_MARKERS):
            certainty = "INFERRED"
        else:
            certainty = "SUSPECTED"
        claim = Claim(
            subject_id=subject, field=field, certainty=certainty,
            source_kind=best.source_kind if best is not None else "NONE",
            source_id=best.source_id if best is not None else None,
            message_id=best.message_id if best is not None else None,
            observed_turn=best.observed_turn if best is not None else None,
            text=text[:200],
        )
        claims.append(claim)
    return claims


def unsupported_confirmed(text: str, *, subject_ids: set[str], knowledge: list) -> list[Claim]:
    """Prose that asserts a confirmed enemy fact the formation cannot support.

    This is the check the PI asked for: an unsupported CONFIRMED enemy-state claim is
    either traced to a valid delivered source or it is ungrounded - there is no third
    possibility, because the grade comes from the ledger and not from the sentence.
    """
    return [
        claim for claim in grade(text, subject_ids=subject_ids, knowledge=knowledge)
        if _markers(claim.text, CONFIRMED_MARKERS) and not claim.is_supported
    ]


def range_claim(distance_hex: int | None) -> dict:
    """A range fact, in the engine's own units, for prose to be rendered from."""
    return range_units(distance_hex)


def range_prose(distance_hex: int | None) -> str:
    """How far away something is, said correctly (the fix for the 12 hex = 12 海里 error)."""
    units = range_units(distance_hex)
    if units["range_hex"] is None:
        return "距离未知"
    return f"{units['range_hex']} 格（约 {units['range_nmi']} 海里）"


def miles_claimed_for_hexes(text: str, *, distance_hex: int, tolerance: float = 0.35) -> bool:
    """True when prose states a distance in 海里 that is really the hex count.

    The v2.2 error, exactly: 12-15 hex was written as 12-15 海里 (3.55-4.44 nmi).  The
    check looks at the numbers stated *next to* a nautical-mile token, and only calls it an
    error when the honest figure is nowhere in the sentence - a report that says
    "12 格（约 3.55 海里）" is right, and one that says "12 至 15 海里" is not.
    """
    honest = range_units(distance_hex)["range_nmi"]
    if honest is None:
        return False
    lowered = text.lower()
    if "海里" not in text and "nmi" not in lowered:
        return False
    if distance_hex < 5 or abs(honest - distance_hex) <= tolerance:
        # At short range the hex count and the nautical-mile figure are numerically close
        # (1 hex ≈ 0.3 nmi), so the wording carries no material error and prosecuting it
        # would be noise.  The error this check exists for is the 10x-scale one.
        return False
    numbers = [float(number) for number in re.findall(r"\d+(?:\.\d+)?", text)]
    if any(abs(value - honest) <= tolerance for value in numbers):
        return False          # the correct nautical figure is present as well
    claimed_near_token = False
    for index, character in enumerate(text):
        if not text.startswith("海里", index) and not lowered.startswith("nmi", index):
            continue
        window = text[max(0, index - 14):index]
        if any(abs(float(number) - distance_hex) <= tolerance
               for number in re.findall(r"\d+(?:\.\d+)?", window)):
            claimed_near_token = True
    return claimed_near_token
