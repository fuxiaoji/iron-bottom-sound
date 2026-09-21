# 01_TRACK_A_ORACLE_AUDIT.md

```
TRACK_A_AUDITED = A_KILL_CONFIRMED
Phase A v3.1 aggregate = INVALID
```

## What was wrong

The Phase A v3.1 "HINDSIGHT_ORACLE" was a **greedy gain-per-unit-budget heuristic**,
not an oracle, and it also left states at budget 0 before filling the total. On
sampling it scored **1.2193** while plain Uniform-16 scored **1.2947** — impossible
for a true oracle, because assigning 16 to every state is feasible under a total of
16·N. The PI's suspicion was correct: the aggregate that killed Track A was invalid.

## Audit (exact multiple-choice knapsack, increments 0→4→16→64 with costs 4/12/48)

All five mandatory checks:

| check | balance | sampling |
|---|---|---|
| all-16 feasible | True | True |
| Uniform-16 spends exactly 16·N | True | True |
| oracle spends exactly 16·N | True | True |
| same held-out matrix for both | True (raw R[state,budget]) | True |
| allocation counts (0/4/16/64) | 12 / 60 / 109 / 19 | 45 / 60 / 65 / 30 |

| quantity | balance | sampling |
|---|---|---|
| V_oracle (raw) | **0.082146** | **1.514451** |
| V_uniform16 (raw) | 0.066388 | 1.294673 |
| gap (raw) | +0.015758 | +0.219778 |
| gap (normalised, ÷ (µ_base − µ_random)) | **+0.000106** | **+0.001278** |
| paired bootstrap 95 % CI of the gap | [+0.0043, +0.0349] | [+0.1366, +0.3096] |
| Phase A heuristic vs Uniform-16 | 0.064753 **< 0.066388** | 1.219337 **< 1.294673** |

No new held-out evaluations were needed: every allocation is scored on the same
measured matrix, so the comparison is exactly paired.

## Verdict

`A_KILL_CONFIRMED`: the corrected oracle gain is **+0.011 %** (balance) and
**+0.13 %** (sampling) of the normalised scale, against a **8 %** gate. The CIs
exclude zero, so reallocation has a *real* but negligible effect: at this compute
scale a state-wise budget allocator has essentially nothing to win. The small
learnability probe is therefore not run (it is gated on the oracle gate passing on
both tasks), and no new Track A method is introduced.
