# 05_E0_SCRIPTED_LEVERAGE.md — E0 results (PARTIAL: interrupted by PI)

**Status**: gunnery layer COMPLETE (30 snapshots x 3 scenarios x ~10 candidates
x 5 matched-seed replicates). Movement and torpedo layers were mid-evaluation
when the run was stopped (80/93; movement-layer results from the fixed
pipeline were in-process only and were lost — raw JSON writes at completion).
Movement/torpedo numbers below are therefore NOT MEASURED, and the user-raised
candidate-coverage risk (F8) means movement would need candidate enrichment +
re-run before any verdict anyway.

## Gunnery layer (complete; instant-material + H0/H1/H2 panels)

| scenario | n state-horizons | median λ9010 (U1) | p75 | p90 | frac ≥0.05 | ≥0.10 | ≥0.20 |
|---|---|---|---|---|---|---|---|
| IBS-S-01 | 30 | 0.018 | 0.027 | 0.034 | 0% | 0% | 0% |
| IBS-S-03 | 30 | 0.012 | 0.021 | 0.047 | 3% | 0% | 0% |
| IBS-S-EM-01 | 30 | **0.000** | 0.000 | 0.000 | 0% | 0% | 0% |

**Diagnostic ground truth (manual resolution, F7-fixed)**: hold-fire vs any
fire batch differs materially and immediately (U1_now 0.2374 hold vs
0.2014-0.2251 fire; 0 vs 11 gunnery checks) — the pipeline MEASURES gunnery
effects correctly. What is nearly flat is "good vs another good": concentrating
on max-VP / finishing damaged / splitting fire produce indistinguishable
outcome distributions, because (a) all five profiles emit IDENTICAL gunnery
batches (auto-assignment already consensus), and (b) the hit table is a wide
low-magnitude distribution. EM-01's zero is the sharpest warning: even in the
dense-scoring scenario, target ALLOCATION has no measured leverage under
scripted continuation.

**GUNNERY_LEVERAGE = LOW** (hold-vs-fire exists; allocation-level leverage ~0).

## Movement / Torpedo layers — NOT MEASURED (interrupted)

Prerequisites for any future movement verdict, from the user-raised analysis
(FAILURES F8):

1. the candidate generator must add coordinated tactical plans (all-ships
   60° unmasking turns, range-control speed moves, torpedo-lane denial) —
   current candidates are per-ship perturbations of balanced and would
   understate movement leverage (candidate-homogeneity risk);
2. evaluation must include E2/E3: a scripted balanced opponent does not
   respond to positional threats, so scripted continuation structurally
   flattens movement value (SCRIPTED_FLATTENING test);
3. horizon: torpedo/positional value realizes over 2-3 turns (H2/terminal).
