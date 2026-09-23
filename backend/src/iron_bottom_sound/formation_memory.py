"""Per-formation memory for Command Delay agents (IBS-R-CD-08).

Why memory is a first-class object here
---------------------------------------
A formation commander that cannot remember anything is not a commander: every turn
it would re-derive its situation from scratch, re-read the same order as if it were
new, and report the same contact forever.  The mode's whole point is that a
subordinate acts on what it *last knew* while the link is slow — which is only
possible if "what it knew" is stored.

Two properties the memory must have
-----------------------------------
**Local.**  A formation's memory holds only what that formation observed, was told,
or decided.  It is written from the same side-filtered material the local agent
already receives (``command_observation.formation_observation``), never from the
side plot, so memory cannot become a back-channel around the information boundary.
The leakage audit checks this by construction: the writer's inputs are the
observation and the agent's own decision.

**Bounded.**  A long scenario must not grow the state without limit, so every list
is capped and the cap is applied deterministically (oldest first).  The caps are
declared constants, not tuned values.

The scratchpad is the agent's own note area: an LLM may write a short reminder
("keep the light division between the enemy and the transports"), it is stored
verbatim and shown back to it next turn.  That is what makes a long game read as a
continuous command rather than a series of independent calls.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# Bounds.  Declared, not tuned.
#
# Doubled in CD-13 (2026-09-23) after measuring the recorded battles: ``contact_seen``
# was **saturating at 24 entries for both formations** in both runs of a 7-turn
# battle, i.e. the earliest sightings were already being evicted while the rendered
# block stayed at 1.3-2.0 KB against a 4000-char budget.  The cap that was binding
# was the wrong one, so the per-kind cap doubled and the render budget tripled.
MAX_ENTRIES_PER_KIND = 48
MAX_SCRATCHPAD_NOTES = 24
MAX_NOTE_CHARS = 400
MAX_TEXT_CHARS = 600
MAX_PROMPT_CHARS = 12000

# Memory kinds.  Fixed vocabulary so a consumer can filter without guessing.
MEMORY_KINDS = (
    "order_received",
    "report_sent",
    "contact_seen",
    "decision",
    "contingency",
    "note",
)


class MemoryEntry(BaseModel):
    """One remembered fact, with the turn it was learned."""

    turn: int
    phase: str
    kind: str
    text: str
    meta: dict[str, Any] = Field(default_factory=dict)


class FormationMemory(BaseModel):
    """What one formation remembers.  Local to that formation; bounded."""

    formation_id: str
    entries: list[MemoryEntry] = Field(default_factory=list)
    scratchpad: list[str] = Field(default_factory=list)
    # The order text currently in force, as the formation last understood it.  Kept
    # separately from the entry log because the agent needs the *current* order
    # verbatim, while the log is history.
    active_order_text: str | None = None
    active_order_turn: int | None = None
    # The last turn this formation successfully reported, so it can tell whether a
    # report is due (rather than repeating one every phase).
    last_report_turn: int | None = None
    last_contact_signature: str | None = None

    def of_kind(self, kind: str) -> list[MemoryEntry]:
        return [entry for entry in self.entries if entry.kind == kind]


def memory_for(state, formation_id: str) -> FormationMemory:
    """Get or create one formation's memory (never shared between formations)."""
    mode = state.command_delay
    if mode is None:
        raise ValueError("memory exists only in command delay mode")
    memory = mode.memories.get(formation_id)
    if memory is None:
        memory = FormationMemory(formation_id=formation_id)
        mode.memories[formation_id] = memory
    return memory


def remember(
    state, formation_id: str, *, kind: str, text: str, turn: int, phase: str,
    meta: dict[str, Any] | None = None,
) -> MemoryEntry:
    """Append one remembered fact, trimming that kind to its cap."""
    if kind not in MEMORY_KINDS:
        raise ValueError(f"unknown memory kind {kind!r}; choose from {MEMORY_KINDS}")
    memory = memory_for(state, formation_id)
    entry = MemoryEntry(
        turn=turn,
        phase=phase,
        kind=kind,
        text=text[:MAX_TEXT_CHARS],
        meta=dict(meta or {}),
    )
    memory.entries.append(entry)
    same = [item for item in memory.entries if item.kind == kind]
    if len(same) > MAX_ENTRIES_PER_KIND:
        # Drop the oldest of this kind; other kinds keep their own budget.
        drop = same[0]
        memory.entries = [item for item in memory.entries if item is not drop]
    if len(memory.entries) > MAX_ENTRIES_PER_KIND * len(MEMORY_KINDS):
        memory.entries = memory.entries[-MAX_ENTRIES_PER_KIND * len(MEMORY_KINDS):]
    return entry


def write_note(state, formation_id: str, *, text: str, turn: int) -> str | None:
    """Store one scratchpad note; returns the stored text or ``None`` if empty."""
    cleaned = " ".join((text or "").split())[:MAX_NOTE_CHARS]
    if not cleaned:
        return None
    memory = memory_for(state, formation_id)
    memory.scratchpad.append(cleaned)
    if len(memory.scratchpad) > MAX_SCRATCHPAD_NOTES:
        memory.scratchpad = memory.scratchpad[-MAX_SCRATCHPAD_NOTES:]
    remember(
        state, formation_id, kind="note", text=cleaned, turn=turn, phase="",
    )
    return cleaned


def set_active_order(
    state, formation_id: str, *, text: str, turn: int, order_id: str | None = None,
) -> None:
    """Record the order text now in force for this formation."""
    memory = memory_for(state, formation_id)
    memory.active_order_text = text[:MAX_TEXT_CHARS]
    memory.active_order_turn = turn
    remember(
        state, formation_id, kind="order_received", text=text, turn=turn,
        phase="", meta={"order_id": order_id} if order_id else {},
    )


def render_for_prompt(memory: FormationMemory, *, max_chars: int = MAX_PROMPT_CHARS) -> str:
    """The memory block shown to an agent, oldest material trimmed first.

    Rendered as plain text rather than JSON because it is read as a narrative:
    newest first within each section, with the current order quoted verbatim.

    Trimming keeps the **head**, because the head is what the agent must not lose:
    the order in force, then its own notes, then the newest entries of each section.
    (Until CD-13 this sliced ``text[-max_chars:]``, which on an over-budget memory
    dropped exactly the current order and the scratchpad and kept the oldest history -
    the opposite of what the docstring, the comment and the test all claimed.  The
    test passed only because its fixture never exceeded ``max_chars``.)
    """
    lines: list[str] = []
    if memory.active_order_text:
        lines.append(f"【当前生效命令（第 {memory.active_order_turn} 回合收到）】")
        lines.append(memory.active_order_text)
        lines.append("")
    if memory.scratchpad:
        lines.append("【你自己的备忘】")
        lines.extend(f"- {note}" for note in reversed(memory.scratchpad))
        lines.append("")
    for kind, title in (
        ("contact_seen", "【你见过的接触（最近在前）】"),
        ("decision", "【你之前的决策（最近在前）】"),
        ("report_sent", "【你发出的报告（最近在前）】"),
    ):
        entries = memory.of_kind(kind)
        if not entries:
            continue
        lines.append(title)
        for entry in reversed(entries):
            lines.append(f"- T{entry.turn} {entry.text}")
        lines.append("")
    text = "\n".join(lines).strip()
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "\n…（较早的记忆已省略）"
    return text


def memory_payload(memory: FormationMemory) -> dict[str, Any]:
    """JSON form for the debug view and the episode export."""
    return {
        "formation_id": memory.formation_id,
        "active_order_text": memory.active_order_text,
        "active_order_turn": memory.active_order_turn,
        "scratchpad": list(memory.scratchpad),
        "counts": {
            kind: len(memory.of_kind(kind)) for kind in MEMORY_KINDS
        },
        "entries": [
            entry.model_dump(mode="json") for entry in memory.entries[-40:]
        ],
    }
