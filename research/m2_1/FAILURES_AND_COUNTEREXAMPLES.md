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

## F8. USER-RAISED DESIGN RISK: the candidate generator may not contain "skilled" moves (P2 coverage)

The user (game expert) objected to low measured leverage: master-level play is
about MOVEMENT — unmasking full broadsides while forcing bow/stern-only fire,
crossing the T, torpedo corridors that force the enemy to displace and create
local superiority — not gunnery target choice. Three masking mechanisms were
identified and their tests pre-registered:

1. Candidate homogeneity: the generator's movement candidates are mostly
   per-ship perturbations of the balanced plan; coordinated tactical plans
   (all-ships turn to unmask broadsides, range-control speed moves, torpedo
   -lane denial turns) are ABSENT. If movement leverage is flat, re-run with
   the tactical-pattern candidates before any platform verdict
   (ACTION_COVERAGE gate).
2. Scripted-flattening: E0 scripts BOTH sides with the same heuristic after
   the candidate — the opponent never "responds" to a positional threat, and
   the focal side's own script may sail back out of the advantage. Evidence
   pattern to test with E2 (local minimax) / E3 (adversarial profiles):
   U3 divergence high + E0 leverage low + E2/E3 leverage high.
3. Horizon: torpedo/positional value realizes in 2-3 turns; horizon audit
   H0/H1/H2/terminal covers this.

Gunnery's low leverage is NOT evidence against the platform: the auto
gunnery-assignment is common to all profiles, and per-target hit differences
are small relative to hull*VP. The open question is movement/torpedo only.

Also recorded: all five profiles produce IDENTICAL gunnery batches (checked
at S-01 turn-1), so policy_* gunnery candidates are duplicates by
construction; gunnery candidate diversity must come from target-assignment
variants (concentrate/finish/hold/random), which the generator does build.
