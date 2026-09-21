# 08_PUBLIC_VS_FULLSTATE.md

The PI's required torpedo comparisons, side by side. All numbers come from
`metrics/b1e_torpedo_census.json` (15 states).

## Current vs Public

| quantity | S-01 | S-03 | EM-01 | pooled |
|---|---|---|---|---|
| CURRENT_ADAPTIVE mean RR | 0.000 | 0.000 | 0.000 | **0.000** |
| PUBLIC_SET_COVER mean RR | 0.000 | 0.000 | 0.029 | 0.010 |
| PUBLIC_BELIEF_AWARE mean RR | 0.000 | 0.000 | 0.029 | 0.010 |
| states where CURRENT fired ≥1 order | 1/4 | 3/5 | 1/6 | 6/15 |

The public arms are marginally better than the deployed planner and both are
practically indistinguishable from `HOLD`. A public method exists, runs, is
legal, and buys nothing measurable at this scale.

## Public vs FullState

| quantity | S-01 | S-03 | EM-01 |
|---|---|---|---|
| FULL_STATE_CEILING mean RR | 0.316 | 0.020 | 0.203 |
| best public arm mean RR | 0.000 | 0.000 | 0.029 |
| ratio (ceiling / public) | 316x | 20x | 7x |

The full-state ceiling is not a deployable method and is never called one: it is
the value of choosing the single action that maximises coverage of the *true*
route set. The ratio is the size of the deployment gap on this census.

## The regret comparison, and its confound

| state | R_shared on true routes | R_shared on public hypotheses |
|---|---|---|
| S-01 s1 t2 | 0.500 | 0.200 |
| S-03 s2 t2 | 0.000 | 0.167 |
| EM-01 s1 t4 | n/a | 0.200 |
| EM-01 s1 t10 | n/a | 0.333 |

The two directions of movement are the honest result: a straight-line public
proxy is not a faithful stand-in for the true hidden set, in either direction.
`R_shared` responds to the size and diversity of the compatible set, and the
public hypothesis set differs from the true route set in both. Isolating the
observational component requires a size/diversity-matched subset control, which
is not in the frozen design; it is the first follow-up in
`09_NEXT_RESEARCH_DECISION.md`.

## What the deployment gap does and does not imply

- It does **not** imply the rules are wrong, nor that a better torpedo planner
  would win games — no long-horizon (L2) claim is made anywhere in this stage.
- It **does** show that the torpedo mechanism is present in the rules (M2.1-R2.1
  established a 28/29-route corridor) and that nothing observable in the current
  design harvests it: not the deployed planner, not the engine's intercept
  combos, not the public set-cover arms.
