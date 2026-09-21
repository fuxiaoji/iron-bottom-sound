# 04_TRACK_C_COUNTERFACTUAL_ATTRIBUTION.md

```
TRACK_C = BLOCKED (not run in this execution window)   attempted=0 valid=0 rejected=0 error=0
```

No fault was injected, no counterfactual repair was run, no probe was budgeted.
`C_IDENTIFIABLE`, `C_QUERY_EFFICIENT` and `C_NONTRIVIAL` are all empty.

## Frozen design (unchanged, ready to run)

- ≥200 failed trajectories per task, exactly one injected fault from a frozen
  distribution (action replacement/drop, observation corruption, one-step delay),
  injection time uniform over the middle 80 % of the episode, injected agent
  uniform; the attribution method never sees injection metadata.
- A failure is kept only if a clean counterfactual rerun confirms the injected
  event materially caused it; rejected cases are counted.
- Exhaustive agent × time-window repair matrix on a 50-trajectory calibration
  subset; repair threshold = clean-baseline return p25 = **115.73** (balance).
- Probe budgets 10 % / 20 % / 25 % of the exhaustive matrix; four strategies as
  pre-registered; gates per `PRE_REGISTRATION_PHASE_A.md` §7.

## Calibration available for the rerun

Positive control C already exercises the exhaustiveness machinery on a case with a
**known unique minimal 2-cell repair set**, including the check that single-cell
repairs do *not* restore success. The toy's fault is deliberately a window rather
than a single cell so that minimality and uniqueness are actually tested — the
first version of that toy was a tautology and was discarded (`INVALID_*`).
