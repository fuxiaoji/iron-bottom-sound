# 08_FINAL_JTC_DECISION.md

```
INTERACTION_STRUCTURE = PRESENT
JTC_INTERACTION_GATE  = FAIL
JTC_FINAL_STATUS      = PERMANENTLY_KILL
BARD_FINAL_STATUS     = ARCHIVED
IBS_NEXT_ROLE         = APPLICATION_BENCHMARK_ONLY
```

## The gate, condition by condition (frozen in PRE_REGISTRATION_M24 §7)

| # | condition | measured | result |
|---|---|---|---|
| 1 | median Δ_joint_greedy > 0 in ≥2 scenarios | S-01 0.000 · S-03 +0.222 · EM-01 −4.194 | **FAIL** (one scenario) |
| 2 | pooled win rate ≥ 0.60 | 0.316 (main), 0.455 (supplemental) | **FAIL** |
| 3 | pooled median gain ≥ 0.05 EH | +0.000 | **FAIL** |
| 4 | not significantly worse than sequential BR | median 0.000, CI [−0.722, +0.000] | **FAIL** |
| 5 | random clearly worse than the interaction beam | beam − random median −0.083 | **FAIL** |
| 6 | not driven by 1–2 extreme states | median after dropping the two largest \|Δ\| = 0.000 | **FAIL** |

## What this last chance established

1. **Interaction structure is real** (Gate I): 28 % of ship pairs carry
   |φ| ≥ 0.05, p90 0.556, max 4.139, and the exact additive model predicts the
   exact joint value poorly (agreement 0.037). The M2.3 diagnosis that per-ship
   greedy is not *structurally* sufficient was correct.
2. **But exploiting it does not pay at this budget** (Gate II): the interaction
   beam ties per-ship greedy in 9 of 19 states, wins 6 and loses 4, with a pooled
   median of exactly 0 and a bootstrap CI of [+0.000, +0.111]. It does not beat
   sequential exact coordinate ascent, and it is not even clearly better than a
   matched-budget random search.
3. Therefore the failure is **not** a surrogate artifact this time. The arm had
   real interaction terms measured by the engine, the same candidate set as every
   other method, and the same exact-evaluation budget. It still could not turn
   interaction structure into a systematic team gain.

Per the PI's rule this is the **last** surrogate revision: there is no third
attempt, and `JTC_FINAL_STATUS = PERMANENTLY_KILL`. The interaction definition,
the Gate I measurements and the equal-budget protocol remain in the record as the
reason the kill is informed rather than assumed.
