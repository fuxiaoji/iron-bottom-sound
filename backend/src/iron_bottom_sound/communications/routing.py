"""Medium selection (IBS-R-CD-03): distance decides *which* medium, never a delay.

The v2.2 rule is that a direct TBS call is possible only while the formation is
inside the fleet's tactical range; past that the signal must go by visual repeat,
coded W/T, or a relay.  Distance is therefore a **selector**, not a multiplier:
delays come from ``processing.MEDIUM_PROFILES`` only.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..models import CommunicationMedium, MessageKind, MessagePrecedence


@dataclass(frozen=True)
class RouteDecision:
    medium: CommunicationMedium
    relay_hops: int
    reason: str

    @property
    def is_blackout(self) -> bool:
        return self.medium == CommunicationMedium.BLACKOUT


def select_medium(
    *,
    distance: int | None,
    tactical_range: int,
    line_of_sight: bool,
    coded_available: bool,
    relay_available: bool,
    precedence: MessagePrecedence = MessagePrecedence.OPERATIONAL,
    kind: MessageKind = MessageKind.SITREP,
) -> RouteDecision:
    """Choose a medium deterministically from the link picture.

    Ordered rules, each with the reason recorded, so a replay can be audited
    line by line:

    1. no line of sight and no coded set -> blackout;
    2. inside tactical range with line of sight -> TBS short;
    3. line of sight but beyond tactical range -> blinker, repeated down the
       formation, one relay stage per repeat;
    4. no line of sight but a coded set -> coded W/T, or a re-enciphered relay
       when the two ends sit under different cipher systems (``relay_available``);
    5. otherwise blackout.
    """
    del kind, precedence  # reserved: precedence reorders the queue, it never picks a medium
    if not line_of_sight and not coded_available:
        return RouteDecision(CommunicationMedium.BLACKOUT, 0, "no line of sight and no coded set")
    if line_of_sight and distance is not None and distance <= tactical_range:
        return RouteDecision(CommunicationMedium.TBS_SHORT, 0, "within tactical range with line of sight")
    if line_of_sight:
        hops = 1 if relay_available else 0
        return RouteDecision(CommunicationMedium.BLINKER, hops, "visual signal repeated down the formation")
    if relay_available:
        return RouteDecision(
            CommunicationMedium.WT_REENCIPHER_RELAY, 1, "coded set but the ends are under different ciphers"
        )
    if coded_available:
        return RouteDecision(CommunicationMedium.WT_CODED, 0, "coded W/T through the message centre")
    return RouteDecision(CommunicationMedium.BLACKOUT, 0, "no route available")
