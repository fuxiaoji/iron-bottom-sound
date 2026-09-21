# 02_TRACK_B_ACQUISITION_RERUN.md

## Positive control first (plan §2.4) — PASS

Synthetic pool with the same line/severity geometry (4-level / 2-level / 1-level
lines, monotone latent thresholds, 30 % of multi-level lines transitioning). The
corrected STRUCTURED_ACTIVE — endpoint probes per line, then true bisection that
strictly shrinks a candidate transition interval, round-robin over unresolved lines
in a frozen order — beats RANDOM at both preregistered budgets:

| K | random recall | structured recall | ratio |
|---|---|---|---|
| 25 | 0.0000 | 0.0075 | — (structured > 0) |
| 50 | 0.0002 | 0.0143 | **61.5x** |
| 100 | 0.0006 | 0.0267 | **46.0x** |
| 200 | 0.0027 | 0.0541 | 20.3x |

`B_MEASUREMENT_BLOCKER` is therefore not triggered; the acquisition stage ran on the
real tables.

## Valid tournament (plan §2.5)

4 methods x 4 K x 30 repetitions per task, identical pool metadata and query counts,
full query traces saved (`raw/track_b_a3/trace_*.json`).

Boundary recall (primary: both severity levels of the true adjacent pair queried
in-line):

| task | method | K=25 | K=50 | K=100 | K=200 |
|---|---|---|---|---|---|
| balance | RANDOM | 0.000 | 0.000 | 0.011 | 0.000 |
| balance | GENERIC_ACTIVE | 0.000 | 0.000 | 0.011 | 0.011 |
| balance | STRUCTURED_ACTIVE | 0.000 | 0.000 | 0.000 | 0.000 |
| sampling | RANDOM | 0.000 | 0.000 | 0.005 | 0.003 |
| sampling | GENERIC_ACTIVE | 0.000 | 0.000 | 0.003 | 0.008 |
| sampling | STRUCTURED_ACTIVE | 0.005 | 0.007 | **0.025** | 0.023 |

## Gates

```
B_NONTRIVIAL_BOUNDARY  = FAIL  (transition-line fraction 0.0024 / 0.0120 vs >= 0.20;
                                failure fractions 0.223 / 0.409 are in band)
B_ACTIVE_EFFICIENCY    = FAIL  (>=1.8x on BOTH tasks not met; balance has 3 true
                                edges so the ratio is undefined/zero)
B_MULTIAGENT_STRUCTURE = FAIL  (>=15% over GENERIC on BOTH tasks not met; on
                                sampling it is +658% at K=100, on balance negative)
TRACK_B = B_KILL_FOR_MAINLINE  (valid run, gates fail; no further rescue run)
```

## What the failure means

The world, not the instrument, is the constraint this time. Under the frozen
perturbation grid a severity line is almost always uniformly failed or uniformly
clean — failure is decided by (initial seed, window, modality) context, not by a
within-line severity threshold. The corrected structured acquisition behaves exactly
as the positive control predicts wherever there is something to find (sampling,
5x random, 7.6x generic at K=100), but 3 edges (balance) and 20 edges (sampling)
across 1260 lines each is a boundary that essentially does not exist. Reviving B
would require a denser severity axis — a new perturbation design, which this phase
forbids.
