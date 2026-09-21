# 02_TRACK_A_ADAPTIVE_COMPUTE.md

```
TRACK_A = A_KILL
  A_HETEROGENEITY      = PASS  (top-25% concentration 0.523 balance / 0.562 sampling, gate >= 0.50)
  A_ORACLE_ALLOCATION  = FAIL  (oracle - Uniform16 = +0.0002 balance / +0.0022 sampling normalised return; gate >= 0.08)
  A_LEARNABILITY       = NOT_RUN (gated on the oracle gate)
```

200 natural states per task (50 per progress quartile, no selection by planning
value), budgets 0/4/16/64, H=5, frozen continuation policy, disjoint
search/evaluation RNG, total planning budget 16 per state for every allocator.

## Allocation comparison (raw return delta over budget 0)

| allocator | balance | sampling |
|---|---|---|
| UNIFORM_16 (primary) | **0.0664** | **1.2947** |
| RANDOM_ALLOCATION | 0.0331 | 0.6958 |
| UNCERTAINTY_HEURISTIC | 0.0415 | 0.2807 |
| HINDSIGHT_ORACLE | 0.0648 | 1.2193 |
| UNIFORM_4 (frontier) | 0.0301 | 0.7102 |
| UNIFORM_64 (frontier) | 0.0981 | 1.6736 |

Denominators are healthy (balance mu_base 121.2 / mu_random -27.7;
sampling 198.1 / 26.0), so the kill is not a denominator
artefact: the oracle's normalised gain over Uniform-16 is **+0.0002** (balance) and
**+0.0022** (sampling), with paired bootstrap CIs [0.02, 0.051] and
[0.298, 0.466] — non-zero but two orders of magnitude below the 8 % gate.

**Heterogeneity is real but not exploitable at this scale**: the top 25 % of states
carry >50 % of positive planning gain on both tasks, yet reallocating the *same*
total budget is worth ≈0.2 %. On sampling the oracle lands *below* uniform-16.

## Frontier note (opposite of the hypothesis)

UNIFORM_64 (0.098 / 1.674) beats UNIFORM_16 on both tasks: *more* planning helps,
*allocating* a fixed total does not.
