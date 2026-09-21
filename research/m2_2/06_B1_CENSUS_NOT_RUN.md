# 06_B1_CENSUS_NOT_RUN.md

The pre-registration gates the natural census on B0 PASS:

> If SEARCH < 0.70 on every case while the gold gap is above the floor:
> `SEARCH_COMPILER_FAIL` -> fix the search, do **not** run the natural census.

B0 = FAIL with 0 of 3 cases satisfying the gate. The pre-registered trigger for
`SEARCH_COMPILER_FAIL` is not met (MG1's computable panel has SEARCH = 0.876),
but the census is gated on PASS and B0 is not PASS, so **the census was not
run**.

```
NATURAL_OPPORTUNITY_RATE = NOT_MEASURED
B1 = NOT RUN
```

Consequently these requested artifacts are `N/A — B1 not run`, and no figure or
table in this bundle reports a natural opportunity rate, a per-scenario
opportunity distribution, or a fidelity-by-scenario breakdown:

- natural mechanism-gain CDF
- current vs search scatter over natural states
- fidelity by scenario
- opportunity rates
- route-reduction distribution over natural states
- raking-geometry scatter over natural states

Producing them would require a new pre-registration, because item 1 of
`NEXT_PI_DECISION` (fleet margin vs pair margin) changes what B1 would even be
measuring. Running the census under the frozen fleet-margin metric is knowable in
advance to be uninformative for MG1 (that metric's gold loses to random).
