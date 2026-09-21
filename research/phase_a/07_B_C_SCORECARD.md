# 07_B_C_SCORECARD.md

| criterion | Track B | Track C |
|---|---|---|
| valid scientific run? | **yes** — positive control PASS (61x/46x over random), immutable 2700-cell tables, 30 reps, traces saved | **yes** — 28 frozen settings x 100 paired vectorised episodes, dedicated seeds, faults verified applied (mean shifts to −38.7) |
| cross-task effect? | boundary absent on BOTH tasks (0.24 % / 2.08 % of lines vs >= 20 %) | infeasible on BOTH tasks (max yield 6.9 % / 0.0 % vs >= 10 % band) |
| strong-baseline gap? | structured beats random 5x and generic 7.6x at K=100 on sampling — but on balance there is nothing to find | not reachable |
| equal-resource comparison? | yes (identical query counts, 30 reps) | yes (every pair counted; zero swallowed errors) |
| engineering cost? | ~10 min compute (labels cached) | ~15 min compute (vectorised calibration) |
| closest-prior risk? | medium (active boundary discovery exists; our result is a negative existence result on cooperative VMAS) | high (crowded attribution field; never reached testing) |
| **final status** | **B_KILL_FOR_MAINLINE** | **C_GENERATOR_FEASIBILITY_FAIL** |

## PI selection rule applied

- Select B only if `B_PROVISIONAL_PASS` → not met.
- Select C only if `C_PROVISIONAL_PASS` → not met.
- If neither passes → `MAINLINE_CANDIDATE = NONE`.

The local AI does not choose; the scorecard is the PI's input.
