# M2.3 DATA MANIFEST

## Metrics

| file | content |
|---|---|
| `metrics/m23_jtc_census.json` | 210 (state,intent) rows over the MID + DAMAGED supplemental panels, five arms each, all rejections and pool diagnostics |
| `metrics/m23_jtc_partial.json` | crash-safe partial record written during the run |
| `metrics/m23_bard.json` | 14 information sets: hidden plans, route counts, identity checks, full payoff matrices (true and matched), risks, planners |
| `metrics/m23_bard_n4_firstrun.json` | the n=4 pipeline smoke run (kept for the record) |
| `metrics/m23_bard_badanchor.json` | the bad-anchor matched control (M23-F1) — would have returned ARTIFACT |
| `metrics/m23_verdicts.json` | the frozen §5/§7 mapping, its inputs, and per-scenario×intent tables |

## Figures

| file | content |
|---|---|
| `figures/fig01_jtc_team_by_arm.png` | Δ team utility by arm for each intent |
| `figures/fig02_jtc_opportunity_rates.png` | JOINT mechanism vs team-beneficial rates against the frozen 20 % line |
| `figures/fig03_joint_vs_greedy.png` | joint vs greedy ΔU on opportunity states |
| `figures/fig04_bard_conflict_matrix.png` | hidden-state × action heatmap, true vs matched (the decisive set) |
| `figures/fig05_bard_matched_control.png` | R_shared true vs matched per information set |

## Logs

`logs/m23_jtc.log`, `logs/m23_bard.log`.

## Reproduction

```
cd iron-bottom-sound
export PYTHONPATH=backend/src:research/m2_3/scripts:research/m2_2r/scripts:research/m2_2/scripts:research/m2_1/scripts
.venv/bin/python research/m2_3/scripts/m23_jtc.py all     # ~24 min
.venv/bin/python research/m2_3/scripts/m23_bard.py        # ~4 min
.venv/bin/python research/m2_3/scripts/m23_verdict.py     # ~1 min
```

Deterministic seeds; the only RNG is `random.Random(20260921 + …)` for the
matched-budget random arm. No paid LLM calls. Budget ≈ 3,000 engine evaluations
(JTC ≈ 2,900; BARD ≈ 170 advances + 5 launches). Production engine untouched.
