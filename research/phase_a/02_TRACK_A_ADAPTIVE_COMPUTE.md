# 02_TRACK_A_ADAPTIVE_COMPUTE.md

```
TRACK_A = BLOCKED (not run in this execution window)   attempted=0 valid=0 rejected=0 error=0
```

No state was collected, no planning budget was spent, no gate was evaluated, so
neither `A_HETEROGENEITY`, `A_ORACLE_ALLOCATION` nor `A_LEARNABILITY` has a value.
Nothing here should be read as evidence for or against Track A.

## Frozen design (unchanged, ready to run)

- 200 decision states per task, stratified 50 per episode-progress quartile, from
  clean episodes of the median checkpoint, **never selected by future planning
  benefit**.
- Planning operator: base joint action + ≤63 policy-sampled/perturbed candidates;
  cloned short rollouts with H=5; frozen continuation policy; disjoint selection
  (`seed_SC = 2000 + i`) and evaluation (`seed_EV = 3000 + i`) RNG streams;
  budgets B = {0, 4, 16, 64}.
- Equal total compute: mean budget 16 per state for every allocator, with
  Uniform-4/16/64, RandomAllocation, UncertaintyHeuristic (or `NOT_RUN` if
  unavailable — never silently dropped) and the HindsightOracle compared; the
  oracle is analysis-only and never feeds a deployable baseline.
- Gates and statuses exactly as pre-registered (`PRE_REGISTRATION_PHASE_A.md` §5).

## Calibration available for the rerun

The positive control already fixes the arithmetic of the allocation test: with the
frozen budget set, a total of 20 admits the informative splits (4,16)/(16,4) while a
total of 32 admits only (16,16) — the toy proved the latter makes the gate
unreachable. The real Track A total must therefore be chosen from a set that
permits a non-uniform optimum (this is recorded before running the track).
