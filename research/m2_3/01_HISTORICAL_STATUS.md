# 01_HISTORICAL_STATUS.md — frozen history, as carried into M2.3

```
HISTORICAL_GATES_PRESERVED = YES

M2.1-R2.1  MECHANISTIC_GOLD_GATE = FAIL_3_OF_5                     (unchanged)
M2.2       GOLD_COMPILER_GAP     = FAIL / BLOCKED_BY_METRIC_VALIDITY (unchanged)
M2.2-R     B1E                   = TORPEDO_PARTIAL_OBSERVABILITY    (unchanged)
           movement branch       = MIXED                           (unchanged)

MG3_HISTORICAL = HISTORICAL_PROXY_PASS / EXECUTABLE_INVALID
MG3-E          = EXECUTABLE_PASS · SUPERSEDES_MG3_FOR_FUTURE_SCIENTIFIC_CLAIMS
```

No prior gate, number or verdict is overwritten anywhere in this stage. The MG3
relabelling is an annotation, not a re-verdict: the original PASS and its meter
(`_mount_can_bear` without `_can_see`) remain recorded in `research/m2_2/04_...`,
and MG3-E (`research/m2_2r/metrics/mg3e.json`) is the case future claims must use.

## Erratum carried forward from M2.2-R

M22R-F6: the B1E `damaged` stratum was empty because its predicate read
`hull_max` instead of the model's `max_hull` — dead code, not commander
behaviour. Fixed here; M2.3's damaged panel uses the corrected field, and its
pool diagnostics (§`02_JTC_SUPPLEMENTAL_CENSUS.md`) show how non-discriminative
the literal predicate turns out to be.
