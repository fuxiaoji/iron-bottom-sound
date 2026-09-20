# STRATEGIC_GOLD_CASES.md — M2.1-R gold-case gate results

**GOLD_EVALUATOR_GATE = FAIL** (0 of 5 cases produce tactical separation
>= 0.05 at T2; gate requires >= 4 of 5)

All five cases were built from reachable replay states (no synthetic boards),
all candidate batches passed the full side-level validator, all values come
from the REPAIRED evaluator (derived-seed replicates; both sides submit+seal
in gunnery branches; P0/T0/T1/T2 checkpoints; explicit baseline excluded from
the action set per PI fix #5 — the scripted-baseline comparison is the
POLICY_BALANCED arm, which is itself one of the intent candidates).

## Case data (E0 = scripted both sides; E3 = adversarial worst-of-pool; U1 scale)

### G1 BROADSIDE_UNMASKING (S-01 s1 t2, allies, 9 own ships)

| arm | geometry (post-gunnery) | P0 | T0 | T1 | T2 | E3 |
|---|---|---|---|---|---|---|
| UNMASK_BROADSIDE | aspect mix unchanged post-script | 0.045 | **0.060** | 0.077 | **0.090** | **0.057** |
| KEEP_NARROW | (see note) | 0.045 | 0.049 | 0.075 | 0.087 | 0.072 |

- E0: unmasking ahead +0.011 at T0, +0.003 at T2 — direction right, magnitude
  1/5 of the gate.
- E3 (opponent plays worst-of-pool): unmasking is **worse** (0.057 vs 0.072).
  Exposed broadside cuts both ways — against an adversary that punishes
  exposure, the "good" tactic flips sign. This is the single most informative
  negative in the round.

### G2 CROSSING_THE_T (S-01 s1 t2)

| arm | geometry (P0) | P0 | T0 | T1 | T2 | E3 |
|---|---|---|---|---|---|---|
| CROSS_T | **6/9 broadside**, 3 narrow | 0.045 | **0.062** | 0.074 | **0.099** | 0.074 |
| KEEP_NARROW | 4/9 broadside, 5 narrow | 0.045 | 0.049 | 0.075 | 0.087 | 0.072 |

- Geometry DOES separate (6 vs 4 broadside ships) — the tactics produce the
  intended postures. E0 converts it to only +0.013 at T0, +0.012 at T2.
  E3 wipes it (0.074 vs 0.072).

### G3 RANGE_CONTROL (S-01 s1 t2) — no pre-declared good/bad direction

| arm | P0 | T0 | T1 | T2 | E3 |
|---|---|---|---|---|---|
| CLOSE | 0.045 | 0.055 | 0.068 | **0.103** | 0.089 |
| OPEN | 0.045 | **0.073** | 0.077 | 0.099 | **0.090** |
| MAINTAIN | 0.045 | 0.067 | 0.081 | 0.104 | 0.081 |

Range-control spread at T2: **0.033** (0.071-0.104) — the largest of the
round, still under the 0.05 gate; E3 compresses it to 0.009.

### G4 TORPEDO_CORRIDOR_DENIAL (S-01 s1 t2)

Identical arm values to G3 (PRESS uses the same CLOSE movement intent;
torpedo FIRE vs HOLD was not separable at movement layer — torpedo candidates
are a separate layer and were not evaluated in the movement-layer harness).

| arm | P0 | T0 | T1 | T2 | E3 |
|---|---|---|---|---|---|
| PRESS_CORRIDOR | 0.045 | 0.055 | 0.068 | 0.103 | 0.089 |
| REFUSE | 0.045 | 0.073 | 0.077 | 0.099 | 0.090 |

### G5 LOCAL_FORCE_SUPERIORITY (S-01 s1 t2)

Same movement batches as G3/G4 (concentrate == close-range steering;
disperse == open-range steering): CONCENTRATE T2 0.103 vs DISPERSE 0.099;
E3 0.089 vs 0.090.

## Case-construction notes

- G4's intended separation (torpedo corridor denial value) was NOT
  implemented at the movement layer: corridor denial value would come from
  the torpedo-fire arm, which lives in the torpedo layer. The movement-only
  proxy (press vs refuse) measures range pressure instead. Recorded as a
  case-design gap.
- G1 geometry sampling: post-script-gunnery aspects are identical across
  arms even though post-movement headings differ, because the scripted
  gunnery exchange dominates the next aspect state. The G1 separation
  evidence must come from the E0/E3 value paths (above), not the P0 geometry
  snapshot — a weaker proof than the plan's G1 requirement.
- E2 (local minimax) was implemented in the repair evaluator design but the
  gold-case run reports E0/E3 only; E2 was not run for the gold cases
  (scope: E2 was scheduled for the post-gate census).

## Verdict

`GOLD_EVALUATOR_GATE = FAIL`

Per the PI's stop rule: no mass census. The measurement-harness repair
(U1 formula, derived-seed replicates, dual-side gunnery sealing, checkpoint
redefinition, explicit baseline) is verified by unit/probe tests, but the
five tactical patterns the game expert named produce only 0.003-0.033 T2
separation under scripted and adversarial continuations — below the 0.05
gate everywhere, and the one case where a "good" tactic clearly wins at E0
(unmasking) **loses** under an adversarial opponent.

Two readings are open to the PI and are NOT decided here:
(a) the scripted+profile-pool evaluator family cannot price positional value
    (movement geometry only pays when someone exploits it over several turns
    with intent), i.e. the SCRIPTED_FLATTENING hypothesis stands unrefuted;
(b) the intent-to-plan compiler is still too coarse (60°-hex perpendicular,
    greedy per-ship plan matching) to encode the expert's tactics.
Both require more engineering before the platform question can be answered.
