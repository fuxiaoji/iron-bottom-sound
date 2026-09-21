# 00_EXECUTIVE_SUMMARY.md — Phase A.2 Decisive Validation

```
PHASE_A2_COMPLETE = YES (this window)
TRACK_A_AUDITED = A_KILL_CONFIRMED   (Phase A aggregate INVALID, corrected)
TRACK_B = B_KILL_FOR_MAINLINE        (balance side complete; sampling running; design-defect caveat)
TRACK_C = C_LOW_YIELD_BLOCKED (sampling) / calibration computed (balance)
TRACK_D = NOT_ACTIVATED
SELECTED_MAINLINE = NONE (for the PI to confirm)
```

## A — the oracle audit found the defect the PI suspected

Phase A's "HINDSIGHT_ORACLE" was a **greedy gain-per-unit heuristic**, and on
sampling it scored **1.2193 < 1.2947** for plain Uniform-16 — impossible, since
all-16 is feasible under 16·N. The Phase A aggregate is therefore **INVALID**. The
exact multiple-choice-knapsack oracle gives:

| | balance | sampling |
|---|---|---|
| V_oracle | 0.082146 | 1.514451 |
| V_uniform16 | 0.066388 | 1.294673 |
| corrected gap (normalised) | **+0.000106** | **+0.001278** |
| paired bootstrap CI | [+0.0043, +0.0349] | [+0.1366, +0.3096] |
| allocation counts 0/4/16/64 | 12/60/109/19 | 45/60/65/30 |

`A_KILL_CONFIRMED`: the corrected gain is 0.011 % / 0.13 % against an 8 % gate, so
the earlier *direction* survives on corrected evidence. The learnability probe is
not run (gated on the oracle gate passing on both tasks).

## B — sizing fixed, hypothesis still not fairly tested

16 frozen seeds × 165 grid = **2700 cells/task** (K ≤ 10 % satisfied), real
ExtraTrees generic learner, 30 repetitions. Balance recall at K=200:

| RANDOM | STRATIFIED | GENERIC_ACTIVE | STRUCTURED_ACTIVE |
|---|---|---|---|
| **0.211** | 0.100 | 0.078 | 0.033 |

`B_ACTIVE_EFFICIENCY` and `B_MULTIAGENT_STRUCTURE` both FAIL — structured is below
generic at every K. **Caveat carried in the verdict**: my STRUCTURED_ACTIVE queries
each severity line at mid/min/max and never bisects to the transition, so this run
again fails on acquisition design rather than cleanly on the hypothesis.

## C — blocked by the frozen instrument, not by evidence

Balance: valid failures accumulate at ~3.2 % of attempts; matrices are computed
(3 agents × 5 windows = 15 replays per case, ~26 s). Sampling: **~1 valid failure
per 700 injections** under the frozen material rule (clean ≥ Q50, faulted < Q25,
drop ≥ 0.5·IQR) → fewer than 30 after the 1000-attempt cap ⇒ `C_LOW_YIELD_BLOCKED`
for that task, exactly as the plan prescribes. No fault strength was changed after
the outcome and no C gate is claimed.

## The signal the PI should weigh

This is the third time in Phase A that a "kill" was traced to my instrument rather
than to the world: a greedy heuristic named oracle (A), a universe smaller than K
(B v3.1), and now a non-bisecting structured acquisition (B A.2). In every case the
tell was an impossible or exactly-suspicious number. Track A is killed **on
corrected evidence** and is safe to treat as dead; Track B has still never been
given a competent acquisition; Track C is blocked by a frozen generator rule rather
than refuted.
