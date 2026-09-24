"""Handling / encoding / relay / queue latency per medium (IBS-R-CD-03).

The historical process
----------------------
The v2.2 plan is explicit that same-navy tactical communication is not
translation, and that the correct model is procedural:

    command decision -> drafting / standard signal formulation ->
    authentication / encipherment -> transmission -> relay / repeat /
    re-encipherment -> reception / transcription -> decipherment ->
    message-centre / CIC / bridge routing -> acknowledgement -> execution

TBS short voice traffic can bypass most of the cipher and message-centre path,
so a short tactical signal can be delivered and acknowledged inside the same
three-minute turn.  Coded W/T, a cross-cipher relay, a visual signal repeated
ship by ship, and post-receipt decipherment all add real handling time.

Provenance discipline
---------------------
Every number below is a **simulation abstraction**, not a measured historical
average, and :func:`abstraction_note` says so in the same words wherever the
values are surfaced.  No packet-loss or garble probability is defined anywhere
in this module: inventing one would violate the project's rule against
unsourced numbers, so the integrity seam (``integrity.py``) is a documented
no-op with a bounded, explicitly-configured alternative.

Delay accounting
----------------
``propagation_turns`` is fixed at 0 with the reason attached, so the omission is
a stated decision rather than an oversight.  Distance never enters as a delay;
it only decides *which medium is available* (``routing.select_medium``).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..models import CommunicationMedium, MessageKind

ABSTRACTION_LABEL = "SIMULATION_ABSTRACTION"

_SOURCE_HANDLING = (
    "history: same-navy tactical traffic is a handling/encoding/relay/queue "
    "problem, not propagation; TBS short signals can complete inside one turn "
    "while coded W/T through a message centre takes materially longer"
)


@dataclass(frozen=True)
class MediumProfile:
    """One communication medium's abstracted cost and availability."""

    medium: CommunicationMedium
    base_delay_turns: int
    per_relay_stage_turns: int
    max_relay_hops: int
    requires_encipherment: bool
    description: str
    source: str = _SOURCE_HANDLING
    label: str = ABSTRACTION_LABEL
    # Zero at game scale, stated explicitly rather than left implicit.
    propagation_turns: float = 0.0

    def delay_for(self, relay_hops: int) -> int:
        """Total abstracted delivery delay for a given number of relay stages."""
        hops = max(0, min(int(relay_hops), self.max_relay_hops))
        return self.base_delay_turns + self.per_relay_stage_turns * hops


# The turn values are the plan's §6 abstraction table, transcribed as data.
MEDIUM_PROFILES: dict[CommunicationMedium, MediumProfile] = {
    CommunicationMedium.FACE_TO_FACE: MediumProfile(
        medium=CommunicationMedium.FACE_TO_FACE,
        base_delay_turns=0,
        per_relay_stage_turns=0,
        max_relay_hops=0,
        requires_encipherment=False,
        description="same command location: spoken, no radio event and no channel slot",
    ),
    CommunicationMedium.TBS_SHORT: MediumProfile(
        medium=CommunicationMedium.TBS_SHORT,
        base_delay_turns=0,
        per_relay_stage_turns=1,
        max_relay_hops=2,
        requires_encipherment=False,
        description="short tactical signal; same turn if the channel is free",
    ),
    CommunicationMedium.BLINKER: MediumProfile(
        medium=CommunicationMedium.BLINKER,
        base_delay_turns=0,
        per_relay_stage_turns=1,
        max_relay_hops=4,
        requires_encipherment=False,
        description="direct visual; same or +1 turn, +1 per repeated-down stage",
    ),
    CommunicationMedium.WT_CODED: MediumProfile(
        medium=CommunicationMedium.WT_CODED,
        base_delay_turns=1,
        per_relay_stage_turns=1,
        max_relay_hops=2,
        requires_encipherment=True,
        description="encode/transmit/decode/routing; base +1 turn",
    ),
    CommunicationMedium.WT_REENCIPHER_RELAY: MediumProfile(
        medium=CommunicationMedium.WT_REENCIPHER_RELAY,
        base_delay_turns=1,
        per_relay_stage_turns=1,
        max_relay_hops=3,
        requires_encipherment=True,
        description="relay or re-encipherment; +1 further turn",
    ),
    CommunicationMedium.MULTI_HOP: MediumProfile(
        medium=CommunicationMedium.MULTI_HOP,
        base_delay_turns=1,
        per_relay_stage_turns=1,
        max_relay_hops=4,
        requires_encipherment=True,
        description="compound route; the total may reach t+2",
    ),
    CommunicationMedium.BLACKOUT: MediumProfile(
        medium=CommunicationMedium.BLACKOUT,
        base_delay_turns=0,
        per_relay_stage_turns=0,
        max_relay_hops=0,
        requires_encipherment=False,
        description="no delivery is possible; the message is never sent",
    ),
}

# v2.3 deleted the "a long order on TBS costs +1" rule.  Length is not a delay: a long
# order costs more *channel slots*, and if the channel cannot take it this turn the
# message waits - a queue delay, visible as ``queue_delay`` on the message rather than
# hidden in a kind-based constant.  (Measured on the v2.2 battle: 63 mission orders paid
# the deleted +1 while every one of them was inside direct TBS range.)
# Direct TBS reachability, in hexes.  Historically grounded: U.S. Navy TBS was VHF
# tactical voice, roughly line-of-sight, commonly described as ~25 statute miles; at
# 600 yd/hex that is ~73 hex.  It is a *reachability* threshold - it never converts into
# a delay.  Measured caveat (v2.3, recorded rather than assumed): the standard 46x39
# board's maximum legal hex distance is 83 hex, so the pathological corner-to-corner case
# is outside TBS range; every message in the CD-13 battle ran 0-42 hex.
TBS_DIRECT_RANGE_HEX = 73
HEX_YARDS = 600
YARDS_PER_NMI = 2025.37


def range_units(distance_hex: int | None) -> dict[str, float | int | None]:
    """The same distance in hex, yards and nautical miles - computed here, never by a model.

    The engine owns the unit conversion so an LLM never has to: the v2.2 battle produced a
    report claiming "12-15 海里" for what was actually 12-15 *hex*, which this function
    exists to make impossible (the prose is rendered from these numbers).
    """
    if distance_hex is None:
        return {"range_hex": None, "range_yards": None, "range_nmi": None}
    yards = distance_hex * HEX_YARDS
    return {
        "range_hex": distance_hex,
        "range_yards": yards,
        "range_nmi": round(yards / YARDS_PER_NMI, 2),
    }


SLOT_COST_LONG_CHARS = 240      # above this, an order is a multi-part signal
SLOT_COST_VERY_LONG_CHARS = 600


def slot_cost(kind: MessageKind, text_length: int = 0) -> int:
    """How many channel slots this message occupies on its medium.

    Only orders and amendments are priced by length: they are the messages that are
    genuinely long.  Reports are short by construction and cost one slot.
    """
    if kind not in (MessageKind.MISSION_ORDER, MessageKind.AMENDMENT):
        return 1
    if text_length > SLOT_COST_VERY_LONG_CHARS:
        return 3
    if text_length > SLOT_COST_LONG_CHARS:
        return 2
    return 1


def profile_for(medium: CommunicationMedium) -> MediumProfile:
    return MEDIUM_PROFILES[medium]


def delay_for(
    medium: CommunicationMedium, kind: MessageKind, relay_hops: int = 0,
) -> int:
    """Abstracted delivery delay in turns for one message.

    v2.3: this is exactly the medium profile's cost - no kind-based surcharge and no
    distance term.  Delay beyond it can only come from the queue, which the caller
    records as the ``queue`` component when the message is actually delivered.
    """
    del kind  # length/cost lives in ``slot_cost``, not in the delay
    profile = profile_for(medium)
    if medium in (CommunicationMedium.BLACKOUT, CommunicationMedium.FACE_TO_FACE):
        return profile.base_delay_turns
    return profile.delay_for(relay_hops)


def breakdown_for(
    medium: CommunicationMedium, relay_hops: int = 0, *,
    reencipher_stages: int = 0,
) -> "DelayBreakdown":
    """The delay components a medium contributes before the queue is involved."""
    from ..models import DelayBreakdown

    profile = profile_for(medium)
    if medium == CommunicationMedium.BLACKOUT:
        return DelayBreakdown()
    if medium == CommunicationMedium.FACE_TO_FACE:
        return DelayBreakdown()
    handling = 0
    encoding = 0
    relay = 0
    reencipher = 0
    if medium == CommunicationMedium.TBS_SHORT:
        handling = profile.base_delay_turns
    elif medium == CommunicationMedium.BLINKER:
        handling = profile.base_delay_turns
        relay = profile.per_relay_stage_turns * max(0, min(relay_hops, profile.max_relay_hops))
    else:
        # coded and relayed traffic pays encoding once, then one stage per hop.
        encoding = profile.base_delay_turns
        relay = profile.per_relay_stage_turns * max(0, min(relay_hops, profile.max_relay_hops))
        reencipher = reencipher_stages
    return DelayBreakdown(handling=handling, encoding=encoding, relay=relay,
                          reencipher=reencipher)


def abstraction_note() -> dict[str, str]:
    """The provenance banner that must accompany these values wherever shown."""
    return {
        "label": ABSTRACTION_LABEL,
        "source": _SOURCE_HANDLING,
        "explicitly_not": "no measured historical mean is claimed for any turn value",
        "propagation": "modeled as zero at game scale; distance only selects the medium",
        "loss_probabilities": "none defined; see integrity.apply_integrity",
    }
