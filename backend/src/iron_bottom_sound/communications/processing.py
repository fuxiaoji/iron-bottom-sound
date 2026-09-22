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

# A complex mission amendment on TBS may need an extra turn of formulation and
# clarification, which is why it is not simply base 0.
TBS_COMPLEX_KINDS = frozenset({
    MessageKind.MISSION_ORDER,
    MessageKind.AMENDMENT,
    MessageKind.CLARIFICATION,
})


def profile_for(medium: CommunicationMedium) -> MediumProfile:
    return MEDIUM_PROFILES[medium]


def delay_for(
    medium: CommunicationMedium, kind: MessageKind, relay_hops: int = 0,
) -> int:
    """Abstracted delivery delay in turns for one message."""
    profile = profile_for(medium)
    if medium == CommunicationMedium.BLACKOUT:
        return profile.base_delay_turns
    delay = profile.delay_for(relay_hops)
    if medium == CommunicationMedium.TBS_SHORT and kind in TBS_COMPLEX_KINDS:
        delay += 1
    return delay


def abstraction_note() -> dict[str, str]:
    """The provenance banner that must accompany these values wherever shown."""
    return {
        "label": ABSTRACTION_LABEL,
        "source": _SOURCE_HANDLING,
        "explicitly_not": "no measured historical mean is claimed for any turn value",
        "propagation": "modeled as zero at game scale; distance only selects the medium",
        "loss_probabilities": "none defined; see integrity.apply_integrity",
    }
