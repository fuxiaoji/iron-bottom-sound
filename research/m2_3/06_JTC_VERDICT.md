# 06_JTC_VERDICT.md

```
JTC_MULTI_INTENT              = FAIL   (only I1 reaches >=20% in >=2 scenarios)
JTC_JOINT_COORDINATION_EFFECT = FAIL   (joint 1.048 < greedy 1.428 < random 1.831 on the
                                        common opportunity set, n=35)
JTC                           = FAIL
```

Frozen PASS conditions and their status:

| # | condition | status |
|---|---|---|
| 1 | ≥2 intent families | met (I1, I2, I3 all measured) |
| 2 | ≥2 scenarios | met (3) |
| 3 | team-beneficial opportunity ≥20 % in ≥2 scenarios | **FAIL** (I1 only) |
| 4 | JOINT team gain stably positive on opportunity states | met (mean +1.048) |
| 5 | JOINT clearly better than PER_SHIP_GREEDY | **FAIL** (worse: 1.048 vs 1.428) |
| 6 | JOINT clearly better than RANDOM_MATCHED | **FAIL** (worse: 1.048 vs 1.831) |
| 7 | result not dependent on the research BROADSIDE bug | met (failures are not carried by I1 alone) |

**Confound, stated in the verdict rather than after it:** condition 5 and 6 fail
partly because the frozen joint arm is structurally unable to beat greedy (M23-F3,
separable surrogate). The FAIL is reported as the frozen rule requires, and the
confound is attached so the PI can decide whether JTC deserves a re-test with an
interaction-aware surrogate before being killed for good.
