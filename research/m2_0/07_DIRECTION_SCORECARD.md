# 07 — Direction scorecard (evidence only, no subjective ranking)

| Criterion | Track A (dynamic partitions) | Track B (command org) | Track C (phase granularity) |
|---|---|---|---|
| Exact-lab signal | PASS (lab can express L*>0; lossless/harmful/state-split/failure cases all constructible) | n/a (rule machinery only) | PASS (same lab) |
| IBS natural signal | FAIL (flat tied-best 71%; L=0 68%) | PASS (65% disruption; sensitivity 25%>=0.05, max 0.767) | PARTIAL (compression yes; phase-dependence no) |
| State dependence | PASS (48.6%) | yes (shock-conditional) | no (scenario-dominated) |
| Effect size | none to reduce | sparse (median sens 0) but max 0.767 | saving 38-80%, lossless |
| Strong-baseline gap | negative (flat IS the baseline and wins) | negative (no simple rule robust cross-scenario) | negative (fixed K=1-2 suffices) |
| Learnability | NOT_RUN (moot) | NOT_RUN (moot) | NOT_RUN (moot) |
| Cross-scenario | yes (2 scenarios, both compress) | FAIL (low-exposure sign flips) | scenario factor dominates |
| Benchmark portability | plausible but unneeded | unproven | unproven |
| Engineering cost | D0 executor built & cheap | setup-variant pipeline built & cheap | reused A |
| Closest-prior overlap | not reviewed (moot) | not reviewed (moot) | not reviewed (moot) |
| Strongest counterevidence | 25/35 flat tied-best; struct vs random 18.4% | low-exposure scenario-opposed (S-01 -0.083) | K stable within scenario across phases |
| Verdict | **A_FAIL_ORACLE** | **B_ORACLE_ONLY** | **C_MODULE** |
