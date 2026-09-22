"""Deterministic per-turn channel capacity, precedence order and TTL (IBS-R-CD-05).

The congestion rule is deliberately bandwidth-shaped and explainable rather than
statistical: every channel has a fixed number of message slots per turn, urgent
traffic is transmitted before operational and operational before routine, ties
break on issue order, and anything still queued past its time-to-live is dropped
with a recorded reason.  No probability enters the model.

Ordering is total and stable — ``(precedence_rank, issued_turn, issued_phase_rank,
message_id)`` — so the queue cannot depend on dictionary or set iteration order
(see defect CD0-F1).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..models import (
    CommandMessage,
    CommunicationMedium,
    MessagePrecedence,
    MessageStatus,
    Phase,
)

# Slots per turn, per channel.  A simulation abstraction: the game models a
# single tactical circuit plus a message-centre channel, not a real radio room.
DEFAULT_CHANNEL_CAPACITY = 4
CHANNEL_CAPACITY: dict[CommunicationMedium, int] = {
    CommunicationMedium.TBS_SHORT: 4,
    CommunicationMedium.BLINKER: 3,
    CommunicationMedium.WT_CODED: 2,
    CommunicationMedium.WT_REENCIPHER_RELAY: 1,
    CommunicationMedium.MULTI_HOP: 1,
    CommunicationMedium.BLACKOUT: 0,
}

# Turns a queued message may wait before it is dropped as stale.
DEFAULT_TTL_TURNS = 3

PRECEDENCE_RANK = {
    MessagePrecedence.URGENT: 0,
    MessagePrecedence.OPERATIONAL: 1,
    MessagePrecedence.ROUTINE: 2,
}

PHASE_RANK = {phase: index for index, phase in enumerate(Phase)}


@dataclass
class ChannelQueue:
    """One channel's slots for one turn."""

    medium: CommunicationMedium
    capacity: int
    slots_used: int = 0

    @property
    def free(self) -> int:
        return max(0, self.capacity - self.slots_used)


@dataclass
class QueueOutcome:
    delivered: list[CommandMessage] = field(default_factory=list)
    waiting: list[CommandMessage] = field(default_factory=list)
    dropped: list[CommandMessage] = field(default_factory=list)


def sort_key(message: CommandMessage) -> tuple[int, int, int, str]:
    return (
        PRECEDENCE_RANK[message.precedence],
        message.issued_turn,
        PHASE_RANK.get(message.issued_phase, 0),
        message.message_id,
    )


def schedule(medium: CommunicationMedium) -> ChannelQueue:
    return ChannelQueue(medium=medium, capacity=CHANNEL_CAPACITY.get(medium, DEFAULT_CHANNEL_CAPACITY))


def due(message: CommandMessage, turn: int, phase: Phase) -> bool:
    """True when this message's abstracted handling delay has elapsed."""
    if message.handling_delay <= 0:
        return True
    elapsed = turn - message.issued_turn
    if elapsed > message.handling_delay:
        return True
    if elapsed == message.handling_delay:
        # Same turn as issue: only a phase strictly later than the issuing phase
        # can be reached, so a +1 message issued during GUNNERY waits for the
        # next turn rather than arriving "earlier" in the same one.
        return PHASE_RANK.get(phase, 0) > PHASE_RANK.get(message.issued_phase, 0) or turn > message.issued_turn
    return False


def drain(
    messages: list[CommandMessage],
    *,
    turn: int,
    phase: Phase,
    queues: dict[CommunicationMedium, ChannelQueue],
    ttl_turns: int = DEFAULT_TTL_TURNS,
) -> QueueOutcome:
    """Deliver what the channels can carry, in precedence order; drop what expired.

    Mutates the passed ``CommandMessage`` objects (status/turn fields) because
    they are the game's own ledger; returns the three buckets so the caller can
    emit events without re-deriving them.
    """
    outcome = QueueOutcome()
    pending = [
        message for message in messages
        if message.status == MessageStatus.QUEUED
        and message.medium != CommunicationMedium.BLACKOUT
    ]
    for message in sorted(pending, key=sort_key):
        if turn - message.issued_turn >= ttl_turns:
            message.status = MessageStatus.DROPPED
            message.reason = f"exceeded TTL of {ttl_turns} turns"
            outcome.dropped.append(message)
            continue
        if not due(message, turn, phase):
            outcome.waiting.append(message)
            continue
        queue = queues.get(message.medium)
        if queue is None or queue.free <= 0:
            outcome.waiting.append(message)
            continue
        queue.slots_used += 1
        message.status = MessageStatus.DELIVERED
        message.delivered_turn = turn
        message.delivered_phase = phase
        message.observed_turn = turn
        outcome.delivered.append(message)
    return outcome
