# VALUE_SEMANTICS.md — value panel definitions (frozen before any leverage number)

All four panel values are computed at a common evaluation point P (end of the
current turn for H0; see horizon audit for later points).

## U0 — authoritative scenario value
Directly `state.score` / `state.winner` / `victory_reason` as produced by
`scenario_rules.resolve_victory` / `refresh_score`. Never reimplemented.
S-03's coarse threshold outcome is always reported alongside U1 (plan §15).

## U1 — normalized material value (PRIMARY leverage scale)

```
M = ( Σ_enemy VP_i · damageFrac_i − Σ_own VP_i · damageFrac_i ) / Σ_all VP_i
damageFrac_i = 1 if sunk else 1 − hull_i / max_hull_i
```

- VP weights come from the scenario ship table (engine data, not invented).
- No extra weights for mounts/MFC/radar (plan §3 U1).
- Range [−1, 1]; 0 = material balance.

## U2 — gunnery opportunity diagnostic (read-only engine semantics)

At P (post-movement, pre-gunnery), per side:

```
OPP_side = Σ_ships expected_hits(ship → best legal target)
         computed with engine.gunnery_assist / expected_gunnery_hits
U2_margin = OPP_focal − OPP_enemy
```

This is a *diagnostic* of tactical geometry, never a value, and is computed
from public state only.

## U3 — physical state divergence (non-value)

Between two branches at P: position distance (mean hex distance over common
ships), heading mismatch count, speed mismatch count, alive-set difference,
legal-action count difference, visibility-set Jaccard distance. Reported as
`U3_pos`, `U3_hull` (material |ΔM|), `U3_actions`.

## Evaluator values (Q_E)

`Q_E(s, a)` is ALWAYS written as **empirical evaluator value** — the mean of U
over R matched-seed continuations under evaluator policy E. The symbol Q* is
banned (no exact solver exists for IBS).

## Variance policy

R = 5 replicates per (state, action, evaluator) unless a pilot shows
intolerable noise (then up to 20, pre-declared). Every Lambda carries a
bootstrap CI (1000 resamples over replicates); a leverage comparison is
"resolvable" iff the 90-10 Lambda's CI lower bound > 0.
