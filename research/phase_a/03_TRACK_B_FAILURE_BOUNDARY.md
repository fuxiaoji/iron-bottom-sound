# 03_TRACK_B_FAILURE_BOUNDARY.md

```
TRACK_B = BLOCKED (not run in this execution window)   attempted=0 valid=0 rejected=0 error=0
```

No perturbation was evaluated, so `B_NONTRIVIAL_BOUNDARY`, `B_ACTIVE_EFFICIENCY`
and `B_MULTIAGENT_STRUCTURE` are all empty. Nothing here is evidence either way.

## Frozen design (unchanged, ready to run)

- Perturbation space `x = (agent, time-window, modality, severity)` with three
  frozen modalities (observation Gaussian noise; action noise/drop/one-step delay;
  agent dropout) — no modality may be added after results.
- Hidden evaluation pool of 2 000–5 000 configurations per task, evaluated once,
  analysis-only; un-queried rows hidden from every active algorithm.
- Boundary point = a configuration whose local neighbourhood contains both
  outcomes (pre-registered).
- **Discovery metric validated in Toy B**: a boundary cell is discovered iff it was
  queried together with an opposite-labelled neighbour, or two of its neighbours
  were queried with opposite labels. The diffuse "any queried neighbour" variant
  was rejected because it rewards uniform coverage — in the toy it let random beat
  bisection.
- Budgets K = {25, 50, 100, 200}; baselines Random, Latin/stratified, generic
  uncertainty sampling, structure-aware per-column bisection.
- Gates per `PRE_REGISTRATION_PHASE_A.md` §6.

## Calibration available for the rerun

The toy already measured the shape this track should expect: structure-aware
querying is **3.4x / 2.7x** better than random at K=50/100 and only **1.1x** at
K=200, and at K=25 random was *better*. A K-sweep that only reports K=25 or K=200
would therefore misrepresent the effect — the sweep is part of the frozen design.
