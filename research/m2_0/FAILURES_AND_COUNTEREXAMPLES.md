# FAILURES_AND_COUNTEREXAMPLES.md — M2-0

## F1. GameEvent has `.type`, not `.kind`
P0 pilot crashed on `e.kind`; the field is `GameEvent.type` (models.py). Fixed
in the pilot; recorded because earlier M-phase scripts used `.kind` on other
event-like objects and the vocabulary differs across models.

## F2. `command_disrupted` is not an event type at HEAD
Command disruption exists only as the state flag `formation.disruption_turn`
plus a next-turn movement restriction (realistic_command.py:475/734). Any
census that greps the event log for `command_disrupted` finds nothing. The
pilot now counts disruption from state, once per (formation, disruption_turn).
NOTE: `disruption_turn = state.turn + 1` is set during GUNNERY/TORPEDO_EFFECTS
*before* `advance()` increments `state.turn` at FIRE_END — a census that checks
`disruption_turn == state.turn` after the phase transition sees nothing (this
was my second bug on the same feature).

## F3. Transfer/disruption counts must dedupe by event sequence
The pilot initially rescanned `state.events[-8:]` every loop iteration,
double-counting events. Fixed by deduping on `event.sequence`. After the fix,
each `formation_command_transferred` corresponds to exactly one disruption
turn (verified 4/4 on S-01, 4/4 S-03, 13/13 EM-01 in the pilot).

## F4. The classic movement validator requires full-fleet coverage
`validate_orders` rejects a movement batch that omits any active ship of the
side ("Movement plans must cover every active ship"). A partition experiment
must therefore emit orders for ALL alive own ships every turn — partitions are
partitions of the full alive set, never a subset. My first D0 test grouped 4
of 5 ships and the validator correctly rejected it. This is a real constraint
on Track A's candidate generation, not a test artifact.

## F5. Whole-fleet plan tables can be identical, so "copying must fail" is not
guaranteed
The no-silent-repair test initially assumed a whole-fleet TURN_PORT_60 macro
would be impossible; in the S-03 snapshot all 5 allied DDs share heading and
plan table, so full-fleet copying succeeded. The test now uses constructive
counterexamples (an illegal proposal; a mixed-heading pair with genuinely
divergent plan tables) and skips (declared) when the snapshot has no divergent
pair.
