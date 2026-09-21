# 03_TRACK_C_DECISIVE_CALIBRATION.md

```
TRACK_C = C_LOW_YIELD_BLOCKED  (BOTH tasks)
```

## Generator frozen, and the yield it produces

The strengthened Phase A v3.1 generator is frozen and unchanged after any
attribution outcome: duration 20 steps, severities 0.5/0.8/1.0, window starts
20/40/60, modalities act_drop / obs_corrupt / act_delay. Injection metadata lives in
`raw/track_c_a2/injection_metadata.csv` and is **never read by the attribution
code**.

| task | valid causal failures | attempts (cap 1000) | yield | status |
|---|---|---|---|---|
| balance | **27** | 1000 | ~2.7 % | `C_LOW_YIELD_BLOCKED` (needs ≥30) |
| sampling | **1** | ~800 when last checked; cap reached | ~0.1 % | `C_LOW_YIELD_BLOCKED` |

Because both tasks fall below the 30-valid threshold, **no repair matrix was built
in Phase A.2 and no C gate is evaluated**: `C_IDENTIFIABLE`, `C_QUERY_EFFICIENT` and
`C_NONTRIVIAL` all remain unevaluated as gates.

## Correction to an earlier statement in this bundle

An earlier draft of this file (and the accompanying summary) described the balance
calibration as "computed", quoting 15 replays per case at ~26 s. Those numbers come
from the **Phase A v3.1 run** (23 valid cases collected under the pre-A.2 loop),
**not** from Phase A.2. In A.2 the frozen generator reached only 27 valid failures
on balance inside the 1000-attempt cap, so the matrices were never built here. The
two runs agree on the underlying property — yield ≈2.5 % — and that is the finding:

**The frozen instrument cannot deliver the required 30-minimum sample inside 1000
attempts on either task.** Reaching 50 valid failures per task would need ≈2 000
attempts (balance) and ≈50 000 (sampling) at the frozen yield. Per the plan the
fault strength must not be changed after attribution outcomes, so this is reported
as `C_LOW_YIELD_BLOCKED` rather than fixed.

## What remains valid from the pre-A.2 balance calibration

Phase A v3.1's 23-case balance matrix (15 cells each, ~26 s per case) is still on
record in `raw/track_c_balance.json` and shows sparse, mostly unique causal
structure (78.3 % single-cell, 95.7 % ≤3 cells, mean 1.13). It is a **prior-run
observation**, not an A.2 gate input, and it is cited only as an indication.
