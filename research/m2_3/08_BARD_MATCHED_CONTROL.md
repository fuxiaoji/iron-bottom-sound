# 08_BARD_MATCHED_CONTROL.md — the decisive control

## Construction

`C_match(h)` is a **matched-kinematics straight-line surrogate**: each true route
is replaced by the straight-line walk from *that variant's own T+1 start position*
that achieves the same net displacement and the same MF length. This matches, by
construction, cardinality, route-length distribution, endpoint spread and the
pairwise trajectory-distance distribution, while remaining constructible by a
public actor. Subsets are never chosen by regret, and the planner choices are made
on the matched set and scored on the true set.

## The anchor defect that had to be fixed first (M23-F1)

The first implementation anchored every surrogate at the **pre-movement** victim
position. That displaces the whole matched set by the victim's own turn-T move,
which makes it disjoint from every corridor and reports `R_shared = 0` for a
reason that has nothing to do with the hypothesis set. The symptom was 12 of 14
sets at exactly `0.000` and 3 degenerate (all-zero) matched payoff matrices; with
the anchor corrected, 3 of 14 remain degenerate and those have all-zero *true*
matrices too. Both runs are kept: `metrics/m23_bard_badanchor.json` (the
bad-anchor run, which would have returned `ARTIFACT`) and `metrics/m23_bard.json`.

## Result

```
material on the true hidden set      : 0.357  (5 of 14)
material after the matched control   : 0.214  (3 of 14)
material on the naive single hypothesis: 0.000 (0 of 14, by construction)
```

| scenario | n | material (true) | material (matched) | median R_shared true → matched |
|---|---|---|---|---|
| IBS-S-01 | 4 | 0.50 | **0.50** | 0.483 → 0.087 |
| IBS-S-03 | 6 | 0.50 | **0.17** | 0.262 → 0.000 |
| IBS-S-EM-01 | 4 | 0.00 | 0.00 | 0.000 → 0.000 |

The control **attenuates** the conflict by roughly half and removes it entirely in
two of the three scenarios; one scenario (S-01) survives matching with
`R_shared = 0.586` and `0.655` and no ε-good shared action. `BARD_MATCHED_CONTROL
= FAIL` because the frozen rule requires ≥20 % after matching **in ≥2 scenarios**
and only S-01 qualifies (the pooled rate, 21.4 %, does clear 20 % — the two
readings disagree at n=14 and both are reported).

The naive single-hypothesis public actor perceives **zero** regret in every set:
with one hypothesis the minimax regret is 0 by construction. That is not a bug, it
is the calibration point — a naive public planner cannot even *represent* the
conflict.
