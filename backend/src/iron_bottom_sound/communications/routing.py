"""Medium selection (IBS-R-CD-03, v2.3): reachability decides the medium; delay never
comes from distance.

The v2.2 rule had two defects, both found by auditing the CD-13 battle (see
``v2_3/01_COMM_ROUTE_AUDIT.md``):

* it passed the scenario's **optical** horizon as the TBS range, so "direct TBS" ended
  where eyesight ended (measured 13-15 hex on a board whose TBS range is 73), and
* it treated **every cross-formation message** as a cryptographic-domain transition
  (``relay_available = not same_command``), sending 55 messages down the re-enciphered
  relay branch at +2 turns with the reason "the ends are under different ciphers" - a
  claim the mode has no model for.

The v2.3 order, applied in this sequence and recorded with the reason that decided it:

1. same command location      -> FACE_TO_FACE
2. inside direct TBS range    -> TBS_DIRECT      (no line-of-sight requirement, no delay)
3. direct visual possible     -> BLINKER         (one relay stage only if repeated)
4. coded set available        -> WT_CODED        (encode/decode: +1 abstraction)
5. explicit relay path exists -> MULTI_HOP / WT_REENCIPHER_RELAY, and only with a node
                                 list plus a stated reason; re-encipherment additionally
                                 requires an actual cryptographic-domain transition
6. otherwise                  -> NO_PATH         (BLACKOUT)
"""
from __future__ import annotations

from dataclasses import dataclass

from ..models import CommunicationMedium, MessageKind, MessagePrecedence

FACE_TO_FACE_REASON = "同一指挥位置：当面交办，非无线电事件"
TBS_REASON = "在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟）"
BLINKER_REASON = "直连 TBS 不可用，但有直视信号条件"
CODED_REASON = "直连与视觉均不可用，改由编码电报"
NO_PATH_REASON = "无可用通路"


@dataclass(frozen=True)
class RouteDecision:
    medium: CommunicationMedium
    relay_hops: int
    reason: str
    # v2.3 provenance: a relayed or re-enciphered route is only legal with these.
    route_nodes: tuple[str, ...] = ()
    why_relay_required: str | None = None
    why_reencipher_required: str | None = None
    blockers: tuple[str, ...] = ()
    direct_tbs_available: bool = False
    direct_visual_available: bool = False

    @property
    def is_blackout(self) -> bool:
        return self.medium == CommunicationMedium.BLACKOUT

    @property
    def route_is_valid(self) -> bool:
        """True when a relayed/re-enciphered route carries the provenance it must have."""
        if self.medium in (CommunicationMedium.WT_REENCIPHER_RELAY,
                           CommunicationMedium.MULTI_HOP):
            if not self.route_nodes:
                return False
            if not self.why_relay_required:
                return False
            if (self.medium == CommunicationMedium.WT_REENCIPHER_RELAY
                    and not self.why_reencipher_required):
                return False
        return True


def select_medium(
    *,
    distance: int | None,
    tbs_range_hex: int | None = None,
    direct_visual: bool | None = None,
    coded_available: bool,
    same_command_location: bool = False,
    relay_path: tuple[str, ...] | None = None,
    crypto_domain_transition: bool = False,
    tbs_blockers: tuple[str, ...] = (),
    precedence: MessagePrecedence = MessagePrecedence.OPERATIONAL,
    kind: MessageKind = MessageKind.SITREP,
    # legacy keyword names from v2.2, kept so an old call site still reads correctly
    tactical_range: int | None = None,
    line_of_sight: bool | None = None,
    relay_available: bool = False,
) -> RouteDecision:
    """Choose a medium deterministically, in the v2.3 order, with the reason recorded."""
    del kind, precedence  # precedence reorders the queue; length is priced as slot cost
    if tbs_range_hex is None:
        tbs_range_hex = tactical_range if tactical_range is not None else 0
    if direct_visual is None:
        direct_visual = bool(line_of_sight)
    if relay_available and relay_path is None:
        # v2.2 read "a different formation" as "a relay".  A relay path must name its
        # nodes; without them no relay route may be selected.
        relay_path = None

    if same_command_location:
        return RouteDecision(
            medium=CommunicationMedium.FACE_TO_FACE, relay_hops=0,
            reason=FACE_TO_FACE_REASON, direct_tbs_available=True,
            direct_visual_available=True,
        )

    tbs_available = (
        not tbs_blockers
        and distance is not None
        and tbs_range_hex > 0
        and distance <= tbs_range_hex
    )
    if tbs_available:
        return RouteDecision(
            medium=CommunicationMedium.TBS_SHORT, relay_hops=0, reason=TBS_REASON,
            direct_tbs_available=True, direct_visual_available=bool(direct_visual),
        )
    if direct_visual:
        return RouteDecision(
            medium=CommunicationMedium.BLINKER, relay_hops=0, reason=BLINKER_REASON,
            direct_visual_available=True,
        )
    if coded_available:
        if relay_path:
            nodes = tuple(relay_path)
            return RouteDecision(
                medium=(
                    CommunicationMedium.WT_REENCIPHER_RELAY if crypto_domain_transition
                    else CommunicationMedium.MULTI_HOP
                ),
                relay_hops=len(nodes),
                reason=(
                    "编码电报经明确中继路径，且路径上存在密码体系转换"
                    if crypto_domain_transition
                    else "编码电报经明确中继路径"
                ),
                route_nodes=nodes,
                why_relay_required="直连 TBS 与视觉均不可用，必须经指定节点转发",
                why_reencipher_required=(
                    "路径两端属于不同密码体系（由想定/档案显式给出）"
                    if crypto_domain_transition else None
                ),
                blockers=tuple(tbs_blockers),
            )
        return RouteDecision(
            medium=CommunicationMedium.WT_CODED, relay_hops=0, reason=CODED_REASON,
            blockers=tuple(tbs_blockers),
        )
    return RouteDecision(
        medium=CommunicationMedium.BLACKOUT, relay_hops=0, reason=NO_PATH_REASON,
        blockers=tuple(tbs_blockers),
    )
