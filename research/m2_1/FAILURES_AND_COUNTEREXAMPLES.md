# FAILURES_AND_COUNTEREXAMPLES.md — M2.1

## F1. GameEvent.dice field is `.dice`, not `.rolls`
`DiceRoll.dice: list[int]` (models.py). First P1 probe crashed on `.rolls`.

## F2. `MovementOrder` (not str) is the argument of `movement_commands`
`engine.movement_commands(order: MovementOrder)`; passing a plan string
crashes. Static-typed, found immediately.

## F3. GunneryOrder uses `primary_target`/`mounts`, not `targets`
First B-branch probe assumed a `targets` list. Checked models.py and rewrote.

## F4. Phase-gated submit: batches submitted outside their phase are rejected
(`Order phase movement_planning does not match current phase reinforcement`).
All probes must walk the real phase machine.

## F5. There is no `command_disrupted` event; disruption is a state flag
(Carried from M2-0 F2; relevant to the realistic strata definitions here.)

## F6. Dice-sequence comparison must use post-branch slices
The deterministic probe initially compared whole-game event slices including
pre-branch events, which masked nothing but is the wrong slice for branch
audits; the audit compares events after the branch point only.
