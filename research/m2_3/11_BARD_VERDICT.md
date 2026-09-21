# 11_BARD_VERDICT.md

```
BARD_MATCHED_CONTROL  = FAIL   (21.4% pooled clears the bar; only 1 of 3 scenarios does)
BARD_ACTION_CONFLICT  = PASS   (S-01 and S-03 at >=20% with no eps-good shared action)
BARD_PUBLIC_RECOVERY  = FAIL   (0.611 / 0.226 / 0.086 of the ceiling; one scenario clears 50%)

BARD = FAIL
```

Frozen rule mapping (§7):

| required | status |
|---|---|
| material shared/Bayes regret ≥20 % of information sets | met on the true set (35.7 %), attenuated to 21.4 % by matching |
| ≥2 scenarios | **not met after matching** (S-01 only; S-03 16.7 %, EM-01 0 %) |
| survives the size/diversity-matched control | **partially** — one scenario, two sets |
| best-action crossover present | met (11 of 14 sets) |
| public planner clearly better than simple proxy / current | met in S-01 only |
| not dominated by a single S-01 scene | **failed** — the surviving effect is exactly the S-01 scene |

Why not `ARTIFACT`: the ARTIFACT branch is defined as "the matched control removes
the effect (<20 % after matching)", and the pooled matched rate is 21.4 %, above
that line. Why not `INFORMATION_LIMIT_ONLY`: that branch requires the conflict to
survive matching at ≥20 % **in ≥2 scenarios**, and only one survives.

The most useful statement of the outcome, in the PI's vocabulary:

> The hidden-commitment conflict is real on the true hidden set and is
> **substantially a hypothesis-set construction effect**: once the public
> hypothesis set is matched to the true set in cardinality, length, spread and
> trajectory-distance distribution, the conflict halves in rate and is eliminated
> in two of three scenarios. What survives is one scenario, where a belief-aware
> planner recovers 61 % of the ceiling.

BARD therefore stays `STRONG_RESEARCH_SEED` and is **not** a mainline candidate.
