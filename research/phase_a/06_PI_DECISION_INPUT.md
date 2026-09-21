# 06_PI_DECISION_INPUT.md

## What Phase A.2 changed relative to Phase A v3.1

1. **Track A's killing aggregate was invalid and is now corrected** (exact
   multiple-choice knapsack instead of a greedy heuristic; the heuristic scored
   *below* the feasible all-16 allocation on sampling). The corrected verdict is
   still `A_KILL_CONFIRMED`, so the *direction* of the earlier conclusion survives —
   but the earlier evidence did not support it, and would have been indefensible
   under review.
2. **Track B's universe defect is fixed** (16 frozen seeds × 165 grid = 2700 cells,
   K ≤ 10 % satisfied) and the generic baseline is now a real label-based
   ExtraTrees learner. The result is still a failure, and the remaining defect is
   **my structured-acquisition implementation**, not the sizing.
3. **Track C's sampling side is low-yield blocked** by the frozen generator: ~1
   valid causal failure per 700 injections against the frozen
   Q50/Q25/0.5·IQR rule. The balance calibration is complete and shows sparse,
   mostly unique causal structure.

## Repeated failure mode worth the PI's attention

Three times in this Phase A effort, a "scientific kill" turned out to be an
instrument defect of mine rather than a property of the world:

| where | defect | how it presented |
|---|---|---|
| Track A v3.1 | greedy heuristic labelled "oracle" | oracle below the feasible uniform allocation (impossible) |
| Track B v3.1 | universe (165) smaller than max K (200) | recall ratio exactly 1.0 at the top of the sweep |
| Track B A.2 | structured acquisition queries mid/min/max, no bisection | structured below random at every K |

In each case the tell was an **impossible or suspiciously exact shape** in the
numbers, not a failing gate. That is a process signal: Track B's hypothesis has
never actually been tested by a competent acquisition strategy in this project, and
Track A was killed by a corrected measurement rather than by a faulty one.

## What a decision can rest on today

- **Track A: killed on corrected evidence.** Safe to treat as dead for this
  environment family; the oracle gap is 0.01–0.13 % of the normalised scale.
- **Track B: not decided.** The hypothesis has not had a fair test. The honest
  options are (i) implement bisection-to-transition and re-run on the existing 2700
  cell universes (labels are already cached, so it is cheap), or (ii) retire B.
- **Track C: incomplete, and blocked by the frozen instrument rather than by
  evidence.** Reaching a verdict needs either a higher-yield fault generator on
  sampling (a change the plan forbids after outcomes) or a redesigned sampling
  semantic for causal materiality, both of which need your ruling.
