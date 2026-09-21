# 09_BARD_ARCHIVE_NOTE.md

```
BARD_FINAL_STATUS = ARCHIVED
```

No BARD run, no S-01 deep dive, no further BARD metric work in this stage. BARD
was not disproven; it was **retired by PI decision** on four grounds recorded in
`M2_4_JTC_Interaction_Last_Gate.md` §9:

1. after the size/diversity-matched control only a single scenario remained stable
   (`R_shared` 0.357 material on the true hidden set → 0.214 matched, S-01 only);
2. public-planner recovery was weak across scenarios (0.611 / 0.226 / 0.086 of the
   full-state ceiling);
3. continuing on S-01 would be case overfitting;
4. the direction overlaps heavily with existing sealed-commitment /
   public-state-insufficiency research axes.

## What is retained

As an appendix / future project seed only, without further runs in this stage:

- the **MG4 route-denial mechanism** (`research/m2_1/03_MG4_SPACETIME_CORRIDOR.md`,
  RouteReduction 0.966, 29/29 engine agreement) and the executable MG3-E case;
- the **BARD metrics**: `R_shared`, `R_Bayes` (uniform-prior label preserved),
  best-action crossover, ε-good shared-action existence, the matched-kinematics
  control, and the full hidden-state × action payoff matrices in
  `research/m2_3/metrics/m23_bard.json`;
- the recorded caution that the binary per-route payoff is degenerate (M22R-F2)
  and that the first matched control was mis-anchored (M23-F1) — both are the
  reasons these metrics should be reused carefully rather than rediscovered.
