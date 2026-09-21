# 03_INTERACTION_EXISTENCE.md — Gate I

Ten pilot states = the first ten of the M2.3 frozen common-opportunity locators in
`(scenario, seed, turn, side, intent)` order. 150 ship pairs scored, every `U`
engine-exact.

```
median |phi|                   0.000
p90 |phi|                      0.556
max |phi|                      4.139
practical-nonzero fraction     0.280   (|phi| >= 0.05)
INTERACTION_STRUCTURE          = PRESENT
```

**The interaction structure exists and is sparse and heavy-tailed**: the median
pair has no measurable interaction while 28 % of pairs exceed the practical floor
and the largest single pair interaction (4.14 EH) is comparable to the whole team
utility scale. Aggregated per pilot, the nonzero pairs are the minority; per state
the number of interacting pairs ranges from 6 to 28.

## The two agreement readings, and why both are reported

`PRE_REGISTRATION_M24` §3 froze `ADDITIVE_RANK_AGREEMENT` as the Spearman
correlation between the **cheap surrogate** ranking and the exact `U` ranking over
a sampled joint set, with `ABSENT` requiring >90 % of pairs below the floor *and*
that agreement ≥ 0.95.

Measured: surrogate-vs-exact median agreement **0.175**; but the honest reading is
that this statistic conflates two different things — the quality of the cheap
guide, and the presence of interaction. A guide can be crude while the additive
*model fitted from exact measurements* still predicts exactly.

So a second, interaction-specific measure was added: the agreement between the
**exact additive model** (`U(a0) + Σ_i q_i(a_i)` with `q_i` from exact single-ship
probes) and exact `U`. Measured median **0.037** — the exact additive model is a
poor predictor of the exact joint value. That is interaction structure, not guide
crudeness.

Both readings agree on the verdict (`PRESENT`), and the frozen rule's own
combination is also `PRESENT` — because the nonzero-pair fraction (28 %) is well
above the 10 % line, the ">90 % below floor" half of the ABSENT condition fails
outright, independently of any agreement statistic.

## Relations recorded

Per pair the record keeps the two ships' distance and the interaction value; the
state-level context keeps collision count (0 across all evaluated states),
legal/visible pair counts, aspect mix, range mean, split-fire ship count and
maximum concentration. The full per-pilot `phi` tables are in
`metrics/m24_gate1_interaction.json`.
