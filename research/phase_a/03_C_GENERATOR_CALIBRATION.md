# 03_C_GENERATOR_CALIBRATION.md — C0

```
C0 = C_GENERATOR_FEASIBILITY_FAIL (both tasks)
```

Protocol as frozen: 3 families x ordered settings, 100 paired vectorised episodes
per setting (clean twin + faulted twin on identical initial states), dedicated
calibration seeds 80 000+ (never reused later), locality cap window <= 8 steps,
one affected agent rotating deterministically, **no repair matrices and no
attribution outcomes inspected**.

## Balance (all 14 settings below the 10 % band)

| family | best setting | yield | LCB | mean shift (fault - clean) |
|---|---|---|---|---|
| act_drop | p=1.0, w=8 | 0.029 | 0.010 | −25.3 |
| obs_corrupt | sigma=1.2, w=8 | **0.069** | 0.034 | −38.7 |
| act_delay | delay=4, w=4 | 0.010 | 0.002 | −2.0 |

The faults are unambiguously applied (a 8-step sensory blackout at sigma 1.2 moves
the mean episode return by −38.7), yet even the best setting tops out at 6.9 %
against the 10 % band floor.

## Sampling (all 14 settings at 0.000)

The material rule needs a paired drop of >= 41.7 return with clean >= 204.03. The
largest mean shift any permitted fault produces is **−2.8**. 8-step local faults
physically cannot cross the materiality threshold on this task; every setting
yielded 0 valid causal failures in 100 pairs.

## Verdict and context

```
balance  : C_GENERATOR_FEASIBILITY_FAIL (0 families in band)
sampling : C_GENERATOR_FEASIBILITY_FAIL (0 families in band)
```

The plan's own escape clause says: *if useful yield requires violating the locality
cap, C fails generator feasibility.* The pre-cap evidence shows the cap is not the
binding constraint anyway — the v3.1 generator with 20-step windows (a violation)
reached only 2.7 % (balance) and 0.1 % (sampling), still under the band at those
strengths. Reaching 10-30 % yield with these semantics would require materially
stronger faults than any setting inside the frozen grid, which is exactly the
change this phase forbids after outcomes.
