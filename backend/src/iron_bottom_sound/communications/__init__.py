"""Command Delay communications package (CD-2 shell, CD-3 pipeline).

Modules
-------
``models``   the wire vocabulary (re-exported from the central data model)
``processing`` medium profiles and the documented simulation abstractions
``routing``  medium selection from distance / relay availability / addressee
``queue``    deterministic per-turn channel capacity, precedence and TTL
``integrity`` a deliberate no-op seam: no invented loss/garble probabilities

What this package deliberately does **not** model
------------------------------------------------
Radio propagation.  At a three-minute game turn, electromagnetic travel time is
zero at any map distance; the delay that matters is human and procedural.
``processing`` therefore prices handling, encoding, relay, queue and
clarification, and every number in it is labelled as a simulation abstraction.
"""
from .models import CommunicationMedium, CommandMessage, MessageKind, MessagePrecedence, MessageStatus
from .processing import (MEDIUM_PROFILES, MediumProfile, abstraction_note, delay_for,
                         profile_for)
from .queue import ChannelQueue, drain, schedule
from .routing import RouteDecision, select_medium
from .integrity import IntegrityPolicy, apply_integrity

__all__ = [
    "CommunicationMedium",
    "CommandMessage",
    "MessageKind",
    "MessagePrecedence",
    "MessageStatus",
    "MEDIUM_PROFILES",
    "MediumProfile",
    "profile_for",
    "abstraction_note",
    "delay_for",
    "ChannelQueue",
    "drain",
    "schedule",
    "RouteDecision",
    "select_medium",
    "IntegrityPolicy",
    "apply_integrity",
]
