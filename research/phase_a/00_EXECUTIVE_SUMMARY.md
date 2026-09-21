# 00_EXECUTIVE_SUMMARY.md — Phase A.3 (B/C decisive correction)

```
PHASE_A3_COMPLETE = YES
TRACK_B = B_KILL_FOR_MAINLINE        (valid run; acquisition instrument finally competent)
TRACK_C = C_GENERATOR_FEASIBILITY_FAIL (both tasks, under the frozen locality cap)
MAINLINE_CANDIDATE per selection rule = NONE   (PI confirms)
```

## Track B — the hypothesis finally got its fair test, and failed

For the first time in this project, Track B's instrument is demonstrably competent:
the mandatory acquisition positive control **PASS** (corrected endpoint-probe +
bisection strategy beats random **61x at K=50 and 46x at K=100** on a synthetic pool
with the same line/severity geometry and known monotone transitions). The rerun then
executed on the immutable 2700-cell label tables (16 seeds x 165 grid) with 30
repetitions per task x method x K and full query traces.

Result: the pre-registered severity-line boundary **does not exist** in these tasks.

| | balance | sampling |
|---|---|---|
| failure fraction (gate 5-50 %) | 0.223 PASS | 0.409 PASS |
| transition-line fraction (gate >= 20 %) | **0.0024 FAIL** | **0.0120 FAIL** |
| true transition edges | **3** in 1260 lines | **20** in 1260 lines |
| STRUCTURED/RANDOM recall at K=100 | 0.0 / 0.0 (no edge findable) | **5.0x** (0.0250 vs 0.0050) |
| STRUCTURED vs GENERIC at K=100 | 0.0 vs 0.0111 | +658 % relative |

`B_NONTRIVIAL_BOUNDARY = FAIL` — the kill. The failure response of these cooperative
tasks is determined by **(initial seed, window, modality) context**, not by a
within-line severity threshold: under the frozen grid, a perturbation line is almost
always either entirely failed or entirely clean. Even restricted to the 720
multi-severity lines per task that can in principle contain a transition, the share
is 0.42 % (balance) and 2.08 % (sampling) against the 20 % gate.

The one positive signal: on sampling, the corrected structured acquisition achieves
**5x random** boundary recall at K=100 (and beats the generic learner 7.6x) — with a
competent instrument the multi-agent structure effect appears, but there is almost
no boundary for it to find. Per the PI rule this does not select a mainline.

## Track C — generator infeasible under the locality cap

C0 ran exactly as frozen: 14 ordered settings per task x family grid, 100 paired
vectorised episodes per setting (dedicated seeds 80 000+), no repair matrices, no
attribution outcomes. All **28 settings** across 3 families x 2 tasks landed below
the 10 % band floor:

- balance: best = obs_corrupt sigma 1.2, window 8 → yield **6.9 %** (LCB 3.4 %),
  with the fault demonstrably applied (mean return shift −38.7);
- sampling: best mean shift **−2.8 return** against a required drop of 41.7
  (0.5·IQR) — 8-step local faults physically cannot cross the materiality rule;
  every yield = 0.000.

```
C0 = C_GENERATOR_FEASIBILITY_FAIL on both tasks
=> C_IDENTIFIABLE / C_QUERY_EFFICIENT / C_NONTRIVIAL: NOT_EVALUATED (gates need
   the generator; per plan §4.4 no family reached the band under the locality cap)
```

Context that makes this closure solid rather than premature: the pre-cap evidence
(the v3.1 generator with 20-step windows, i.e. *violating* the locality cap) reached
only 2.7 % (balance) and 0.1 % (sampling) — so the cap is not the binding constraint
for sampling at all, and removing it on balance still does not reach the band at
these strengths.

## Cross-track

| | A | B | C |
|---|---|---|---|
| final | A_KILL_CONFIRMED (A.2, corrected oracle) | **B_KILL_FOR_MAINLINE** | **C_GENERATOR_FEASIBILITY_FAIL** |
| on corrected/valid evidence | yes | yes (competent instrument, first time) | yes (28-setting calibration, faults verified applied) |

```
MAINLINE_CANDIDATE = NONE
```
