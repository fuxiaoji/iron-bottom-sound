# 00_EXECUTIVE_SUMMARY.md — M2.4 JTC Interaction-Aware Last-Chance Gate

```
HISTORICAL_GATES_PRESERVED = YES          (M2.1-R2.1 · M2.2 · M2.2-R · M2.3 all unchanged)

INTERACTION_STRUCTURE = PRESENT
JTC_INTERACTION_GATE  = FAIL
JTC_FINAL_STATUS      = PERMANENTLY_KILL
BARD_FINAL_STATUS     = ARCHIVED
IBS_NEXT_ROLE         = APPLICATION_BENCHMARK_ONLY

BIGGEST_REMAINING_RISK = state loss in Gate II (M24-F2): 53 main state-sides were
  attempted, 34 were dropped by a guard when an exact evaluation failed, leaving
  n=19 (and 11 of ~30 supplemental). Every failing condition fails by a wide
  margin, so the verdict is not sensitive to the loss, but the pre-registered
  35/30 sample sizes were not reached and the dropped-state pattern is unknown.
```

## Gate I — interaction structure exists

Ten pre-registered pilots, 150 ship pairs, all `U` engine-exact:
median |φ| 0.000, **p90 0.556**, max **4.139**, **28 % of pairs ≥ 0.05**. Sparse,
heavy-tailed, and real: the exact additive model (sum of exactly measured
single-ship deltas) predicts the exact joint value with median agreement **0.037**,
so the additive description is genuinely insufficient.

## Gate II — coordination still does not pay

| | main (n=19) | supplemental (n=11) |
|---|---|---|
| win / tie / loss | **6 / 9 / 4** | 5 / 4 / 2 |
| pooled win rate | 0.316 | 0.455 |
| pooled median Δ (beam − greedy) | **+0.000** | +0.000 |
| bootstrap CI of the median | [+0.000, +0.111] | [+0.000, +0.86] |
| per-scenario median | S-01 0.000 · S-03 +0.222 · EM-01 **−4.194** | S-01 +0.722 · S-03 0.000 · EM-01 −4.194 |
| vs sequential team BR | median 0.000, CI [**−0.722**, 0.000] | same shape |
| vs matched-budget random | median −0.083 | 0.000 |

All six pre-registered PASS conditions are false. The arm had real interaction
terms, the same candidate set as every other method, and the same exact-evaluation
budget — and the most informative comparison is that **sequential exact
coordinate ascent matches it**, i.e. whatever coordination gain exists is already
captured by moving one ship at a time and accepting only exact improvements.

## Why this kill is informed

M2.3's FAIL was confounded (separable surrogate ⇒ greedy is its exact optimizer).
This stage removed that confound: interaction terms were measured by the engine and
used in the model that guided search, and the verdict used `U_exact` only. The kill
therefore rests on a test that could have gone the other way — the first state
sanity check showed beam − greedy = **+0.972**, and S-03's median is **+0.222**, so
the sign was genuinely uncertain until the whole panel ran.

## Recorded defects (all disclosed, none smoothed over)

- **M24-F1** main-set deviation: the pre-registration named the M2.3 35 opportunity
  combos; the run used all unique census state-sides (53 attempted) — a superset,
  so not cherry-picked, and recorded here.
- **M24-F2** silent state loss: a `RuntimeError` guard skipped states whose exact
  evaluation failed (53 → 19, ~30 → 11), which is exactly the failure shape the
  project's red lines warn about; it is reported with counts in every panel table
  instead of being hidden behind the pre-registered sample sizes.
- **M24-F3** degenerate intent labels in the main panel (all `I1_BROADSIDE`), so
  `P(Δ>0 | RANGE/RAKING)` could not be computed and is not reported.
- **M24-F4** two real bugs inside the interaction arm, found by re-reading the code
  after Gate I: the `phi` construction used the wrong base term for `u_j`, and the
  model added a pair term only when the assignment matched the *first* probe. Both
  fixed and Gate II re-run from scratch; Gate I's numbers are unaffected (its `phi`
  block was correct).

## What was not done

No BARD runs (archived), no S-01 deep dive, no RL, no GNN, no Transformer, no
paper method design, no rule or production change, no paid LLM calls. No third
surrogate revision — per the PI, this was the last chance.
