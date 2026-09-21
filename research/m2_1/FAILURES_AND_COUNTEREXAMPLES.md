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


---

# M2.1-R measurement-repair failures (F9-F12)

## F9. Gold-case geometry sampled one phase too early
`gunnery_geometry` advanced the state only ONCE from movement_planning, which
steps to TORPEDO_PLANNING — ships had not moved, so every candidate produced
identical geometry. Fix: advance until phase == torpedo_effects (movement
resolved, gunnery not yet fired).

## F10. Heading arithmetic off-by-one collapsed tactical intents
`((bearing - 1) % 6) + 1` is the identity on bearing, so UNMASK_BROADSIDE
computed the same desired heading as KEEP_NARROW_CLOSE and all intent
candidates collapsed to one joint batch (9/9 ships identical). Corrected wrap:
`_hdg(bearing, k) = ((bearing - 1 + k) % 6) + 1`. After the fix the intent
pairs select different plans for 9/9 ships. The collapse also silently
invalidated the first gold-case run (0/5 with two cases comparing identical
arms).

## F11. Geometry sample point after scripted gunnery
Even post-F9 the geometry sampler advanced through gunnery resolution, so
`expected_hits` read 0 (mounts fired) and the "geometry" mixed movement
posture with scripted-combat damage. Sample point for posture claims must be
phase == GUNNERY (post-movement, pre-fire); the shipped gold cases report
post-gunnery geometry instead, and G1's geometry proof is therefore weaker
than the plan requires (value-path evidence used instead).

## F12. Stale G1/G2 json entries across intent fix
The G1/G2 entries in gold_cases.json predated the F10 fix; a re-run
(gold_g12.py) replaced them before the gate verdict. Any earlier copy of the
json (22:31 version) is obsolete.

## F13. Opponent gunnery batch never submitted in the original E0
(The PI-identified bug, confirmed and fixed.) The original e0_scripted.py
gunnery branch called `choose_plan` for the opponent but never
`submit_orders`, so only the focal side's batch was sealed and `_resolve_gunnery`
resolved an empty opponent set. The gunnery-layer LOW-leverage numbers in the
M2.1 checkpoint are therefore INVALID_PENDING_RERUN, exactly as the PI ruled.
The repaired evaluator (repair/evaluator.py) scripts AND submits the opponent
batch through the standard advance() machine, verified by the repaired
gunnery probe (hold vs fire now differ at P0: 0.0 vs 0.0978).

## F14. G2/G3/G4/G5 arm-value collapse explained (movement-intent aliasing)
CLOSE_RANGE (G3), PRESS_CORRIDOR (G4) and CONCENTRATE (G5) all compile to the
same fleet-level steering ("head at the enemy, fast"), so their arm values are
identical by construction; OPEN/REFUSE/DISPERSE likewise alias to "head away,
fast". The intent vocabulary is thus effectively 2 movement plans per case in
these states, and the 90-10 spread over them cannot exceed the CLOSE-vs-OPEN
gap. A future gate needs intents that compile to DIFFERENT geometry (e.g.
unmask vs narrow are the only pair that diverges on all 9 ships).

## F15. E3 definition subtlety in the gold run
Gold E3 re-keys the seed by the arm-independent (snapshot|replicate) string,
so adversarial and scripted arms share streams until divergence — but because
the opponent profile differs, its order stream diverges immediately at its
first choice; matched-seed holds only up to that point. Reported as
matched-seed, per the standing RNG audit.

---

# M2.1-R2 failures (mechanistic gold decomposition)

## F16. Opponent torpedo batch never submitted in MG4's turn rollover
Same family as the original E0 bug: resolving from TORPEDO_PLANNING requires
BOTH sides' torpedo batches; the loop advanced without submitting the
opponent's. Fixed by scripting+submitting both sides before each advance.

## F17. Same launcher twice = invalid torpedo batch
A "spread" assembled from multiple combos of the SAME launcher fails
validation. Fixed with a (ship, launcher) dedupe.

## F18. Pre-turn bearing is stale under simultaneous movement
MG1's first design chose broadside/narrow plans against the PRE-movement
bearing; the target moves in the same resolution, so the realized aspect was
uncorrelated with the chosen one (arms produced identical post states despite
"opposite" intents). Fix: a two-pass design — a probe run learns the target's
deterministic post-movement position, then the plans are chosen against the
POST bearing. This is the correct pattern for any simultaneous-movement
mechanistic case.

## F19. D66 expectation, not 2d6
Gunnery hits are looked up on a D66 table (11-66) with base-six step
modifiers; an expectation integral over 2d6 sums (2-12) crashes with KeyError
and is simply the wrong distribution. Fixed by integrating the 36 uniform D66
outcomes through d66_adjust.

## F20. MG3 relative-gap formula divided by an artificial epsilon
`eh_diff / (min(a, b, 1e-9) + 1e-9)` produced 8e8. The raw numbers (2.56 vs
0.94, a 2.72x ratio) are the honest report; formula recorded as a bug, gate
unaffected.

---

# M2.1-R2.1 repair failures (F21-F23)

## F21_GUN_MOUNT_MULTI_TARGET_DOUBLE_COUNT  (PI-identified)
`measure_side()` iterated (ship -> target -> mount) and added a mount's
firepower and expected hits once per *visible target* it could bear on. One
mount covering three targets counted three times. Consequence: MG2's usable
GF and both sides' expected hits in M2.1-R2 were not legal gunnery
allocations; MG2's 1.68x ratio and MG5's 56.6-vs-82.7 margin are void.

Repair: `scripts/mg/legal_fire2.py` — each mount allocated at most once, one
target per ship, greedy best-response iteration for the coupled
concentration/splitting choice, engine-exact `_gunnery_modifiers`, and the
resulting batch submitted through `validate_orders(_prepared=True)`.

Two further fidelity defects found while repairing:
- **modifier grouping**: the engine passes
  `attackers = len(attacking_ships[target])` and
  `target_count = len(targets_per_attacker[attacker])`; the first repair pass
  assumed both were 1.
- **per-kind hit tables**: the engine groups attacks by
  `(attacker, target, mount.kind)`, so primary and secondary batteries are
  separate lookups; the first repair pass summed all bearing mounts into one
  firepower total.
- **visibility**: `_mount_can_bear` passing does not imply the validator
  accepts the order — `_can_see` is required too (one arm produced an invalid
  batch until this was added).

## F22_SPACETIME_SEGMENT_OFF_BY_ONE
`t1_segment()` returned `path[allowance : allowance + cycle[1]]`, but
`path[allowance]` is the hex the track already occupies when the turn begins;
the turn's first landing is `path[allowance + 1]`. Verified against a real
launched track (search predicted `[T8,T7,T6,T5,T4,T3]`, the engine track
moved `[T7,T6,T5,T4,T3,T2]`). After the fix the geometric preselection and the
engine's own contact verdict agree on 29/29 routes.

## F23_TORPEDO_AIMING_CONFINED_TO_INTERCEPT_COMBOS
`eng.torpedo_tactical_combos` returned only 2 identical intercept-aimed
configurations for the S-01 shooter, so no corridor could be built from that
API. The legal configuration space (launcher x launch MF x side x angle x
setting, 288 configurations) had to be enumerated directly, with each
candidate projected through the engine's own `_project_torpedo_path` and only
the final choice submitted as a real validated `TorpedoOrder`. This is the
first concrete instance of the *compiler* limitation the M2.2 line is meant to
study: the platform's own candidate generator does not expose the aiming
freedom the rules permit.
