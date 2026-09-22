"""Integrity seam: no invented loss or garble probabilities (IBS-R-CD-06).

The v2.2 plan says the deterministic congestion model comes first and only a
later research mode may add ``p_drop`` / ``p_garble``.  It also forbids inventing
historical packet-loss probabilities.  Both constraints are satisfied by making
this module an explicit, configured no-op:

* ``IntegrityPolicy()`` (the default, and the only policy any mode uses today)
  has no probabilities at all and returns every message unchanged;
* a future research mode can set ``p_drop`` / ``p_garble`` **and** must supply a
  ``source`` string naming where the number came from; :func:`apply_integrity`
  refuses to run a policy whose source is empty, so an unsourced probability
  cannot enter a replay even by accident.

The function is deterministic given the message id and the seed, so enabling a
sourced policy later stays replayable.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from ..models import CommandMessage, MessageStatus

UNSOURCED_REASON = "unsourced probability refused"


@dataclass(frozen=True)
class IntegrityPolicy:
    """Corruption model.  Defaults are the documented no-op."""

    p_drop: float = 0.0
    p_garble: float = 0.0
    source: str = ""
    enabled: bool = False

    @property
    def is_noop(self) -> bool:
        return not self.enabled or (self.p_drop <= 0.0 and self.p_garble <= 0.0)


def apply_integrity(
    message: CommandMessage, policy: IntegrityPolicy, *, seed: int,
) -> CommandMessage:
    """Apply the policy to one message; a no-op policy returns it untouched."""
    if policy.is_noop:
        return message
    if not policy.source.strip():
        # Fail closed: a probability without provenance is not allowed to act.
        message.reason = UNSOURCED_REASON
        return message
    generator = random.Random(f"{seed}:{message.message_id}")
    if generator.random() < policy.p_drop:
        message.status = MessageStatus.DROPPED
        message.reason = f"dropped by sourced integrity policy ({policy.source})"
        return message
    if generator.random() < policy.p_garble:
        message.payload = {**message.payload, "garbled": True}
        message.reason = f"garbled by sourced integrity policy ({policy.source})"
    return message
