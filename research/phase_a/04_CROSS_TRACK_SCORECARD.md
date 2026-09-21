# 04_CROSS_TRACK_SCORECARD.md

| | Track A | Track B | Track C |
|---|---|---|---|
| valid scientific run? | **yes** (200 states × 2 tasks, paired matrix, exact knapsack oracle) | **partially** — universe/K now valid, but the structured acquisition is my own weak implementation | **no** — sampling side low-yield blocked; balance calibration computed |
| cross-task effect? | no (fails on both) | balance only so far | balance only |
| strong-baseline gap? | oracle over Uniform-16: +0.011 % / +0.13 % (gate 8 %) | RANDOM is strongest; structured below generic at every K | not evaluated (gates require both tasks) |
| equal-resource comparison? | yes (total 16·N for all allocators) | yes (identical query counts, 30 reps) | yes (all replays counted) |
| engineering cost? | 21 min (measured) | labeling 2700 × 2 tasks ≈ 25 min + acquisition | ~26 s per case per task; sampling yield blocks |
| closest-prior risk? | medium | medium | high (crowded attribution literature) |
| **final status** | **A_KILL_CONFIRMED** | **B_KILL_FOR_MAINLINE** (design-defect caveat) | **C_LOW_YIELD_BLOCKED / INCOMPLETE** |

## PI rule applied

1. *A survives only if the oracle audit resurrects it* → the audit corrected the
   aggregate (Phase A's oracle was a greedy heuristic and scored below the feasible
   all-16 point) but the corrected oracle gain is still two orders of magnitude
   below the gate ⇒ **A does not survive**.
2. *C can win only if it beats strong group-testing baselines on both tasks* → the
   sampling side is low-yield blocked, so C cannot be evaluated ⇒ **C does not win**.
3. *B can win only if it beats a real generic active learner on both tasks* → on
   balance, structured is below generic at every K ⇒ **B does not win**.
4. *Weak one-task positives never select a mainline* → no one-task result is
   promoted.
5. *If neither B nor C passes the strong-baseline gate, selected mainline = NONE.*

```
SELECTED_MAINLINE = NONE   (left for the PI to confirm; the local AI does not choose)
```
