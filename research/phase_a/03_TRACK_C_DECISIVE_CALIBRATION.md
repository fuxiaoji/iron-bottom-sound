# 03_TRACK_C_DECISIVE_CALIBRATION.md

```
TRACK_C = C_LOW_YIELD_BLOCKED (sampling) / calibration computed (balance)
```

## Generator frozen, as required

The strengthened generator of Phase A v3.1 is frozen and unchanged after any
attribution outcome: duration 20 steps, severities 0.5/0.8/1.0, window starts
20/40/60, modalities act_drop / obs_corrupt / act_delay. Injection metadata is
written to `raw/track_c_a2/injection_metadata.csv` and is **never read by the
attribution code**; ground truth is the minimal successful repair set from the
exhaustive agent × time-window matrix.

## Yield, and why the sampling side is blocked

| task | valid causal failures | attempts | outcome |
|---|---|---|---|
| balance | 19 at 600 attempts (~3.2 %) | ≤1000 | generation continued; matrices computed for the collected cases |
| sampling | **1 at ~700 attempts** | ≤1000 | **C_LOW_YIELD_BLOCKED** — fewer than 30 valid failures after the full attempt cap |

The sampling rule is the frozen material-causal one (clean ≥ Q50 = 204.03,
faulted < Q25 = 160.57, drop ≥ 0.5·IQR = 41.7), and the frozen generator almost
never produces a fault that satisfies all three at once. That is a real property of
the frozen instrument, and the plan's rule applies literally: fewer than 30 valid
failures after 1000 attempts ⇒ `C_LOW_YIELD_BLOCKED` for that task. **No fault
strength was changed after this outcome**, and no attribution gate is claimed.

## What the balance calibration shows

Per-case exhaustive matrix = 3 agents × 5 windows = 15 counterfactual replays at
~26 s per case; four probes (RANDOM_CELL, TIME_BINARY,
AGENT_THEN_TIME_GROUP_TEST, INFLUENCE_PRIORITIZED) at 10/20/25 % budgets, every
replay counted as a query. Metrics and per-modality breakdowns are in
`metrics/a2_track_c.json` and `raw/track_c_a2/cases_balance.json`.

Because the sampling side is blocked and the plan requires both tasks for every C
gate, **no Track C verdict is issued**: `C_IDENTIFIABLE`, `C_QUERY_EFFICIENT` and
`C_NONTRIVIAL` remain unevaluated as gates, and Track C stays
`PROMISING_CALIBRATION / INCOMPLETE` from the PI's own status vocabulary.
