# 02_JTC_SUPPLEMENTAL_CENSUS.md — supplemental panels (old prevalence untouched)

```
B1E-S_SUPPLEMENTAL — reported separately; never merged into the old 52-state /
104-state-side census, whose rates stay exactly as recorded in research/m2_2r/
```

## MID panel

Deterministic windows S-01 turns 3–5 · S-03 turns 2–3 · EM-01 turns 4–8, first
state-sides in `(seed, turn, side)` order. **105 (state, intent) rows** = 35
state-sides × 3 intents. Rejections: `pair_lost_during_movement` 2 (the frozen
admission rule of `PRE_REGISTRATION_M23` §4.3).

## DAMAGED panel (event-conditioned)

The PI's literal rule — "≥1 surviving own ship with `hull < max_hull`, or a key
system down" — applied in `(seed, turn, side)` order, first 12 per scenario:
**105 (state, intent) rows**, 0 rejections.

**The literal predicate is not discriminative**, and the panel says so with
numbers: over the scanned pools, the rule selects

| scenario | pool state-sides | strict `hull ≤ 0.75·max_hull` |
|---|---|---|
| IBS-S-01 | 86 | 82 |
| IBS-S-03 | 39 | 34 |
| IBS-S-EM-01 | 109 | 101 |

i.e. 234 of 234 pool state-sides satisfy it, and 217 of 234 satisfy the stricter
threshold as well, because ships are not at full health from the outset. Every
state-side in this panel is therefore a *conditioned* sample of essentially all
states, and `P(opportunity | damaged)` is reported only as that conditioned rate —
it is **not** a contrast against undamaged states, and no claim of the form
"damage changes opportunity" is made anywhere in this bundle.

Because `MID` and `DAMAGED` are separate panels, neither modifies the old
prevalence. `damaged_pool_diagnostics` is recorded in
`metrics/m23_jtc_census.json`.
