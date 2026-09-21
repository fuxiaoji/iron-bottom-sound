# 09_BARD_ACTION_CONFLICT.md — full payoff matrices

The complete hidden-state × torpedo-action payoff matrix `D(c,a)` is stored for
every information set, for both the true hidden set and the matched control
(`payoff_matrix`, `payoff_matrix_matched` in `metrics/m23_bard.json`), with
`figures/fig04_bard_conflict_matrix.png` showing the decisive set (true vs
matched) as heatmaps.

Per set the record carries: `V_c = max_a D(c,a)`, the argmax action per hidden
state, the number of distinct best actions (crossover), `R_shared`, `R_bayes`
(uniform prior), and whether an ε-good shared action exists
(`D(c,a) ≥ V_c − 0.25` for every `c`).

| quantity (true hidden set, 14 sets) | value |
|---|---|
| sets with crossover (distinct best actions) | 11 of 14 |
| sets with **no** ε-good shared action | 5 of 14 |
| scenarios at ≥20 % no-ε-good | S-01, S-03 → `BARD_ACTION_CONFLICT = PASS` |
| median `R_shared` (true) | 0.975 · 0.966 · 0.875 · 0.775 · 0.450 · … (see JSON) |

So on the true hidden set the conflict is exactly the shape the PI specified:
multiple hidden sealed routes for one public history require different torpedo
actions and no single action is ε-good. **The matched control is what decides
whether that survives** (`08_BARD_MATCHED_CONTROL.md`) — and it does so in one
scenario only.
