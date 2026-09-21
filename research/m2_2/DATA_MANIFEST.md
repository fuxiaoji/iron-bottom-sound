# M2.2 DATA_MANIFEST

Branch `research/m2-2-compiler-fidelity`. Production engine untouched: all
measurement goes through `engine.validate_orders` / `submit_orders` / `advance`,
`engine._gunnery_modifiers`, `engine._mount_can_bear`, `engine._can_see`,
`engine.movement_candidates`, `engine.movement_trajectory`,
`engine.movement_cost`, `engine.torpedo_tactical_combos` and
`engine._project_torpedo_path`. No state surgery, no sealed-order inspection for
arm construction, no RNG manipulation — every engine call is the engine's own.

## Metrics

| file | content |
|---|---|
| `metrics/fire_calibration.json` | 20-state LEGAL_FIRE_HEURISTIC vs FIRE_SEARCH panel, per state and summary |
| `metrics/b0_gold_compiler_fidelity.json` | the B0 record: per-mechanism case reproduction, both metric panels, all method values, fidelity, GATE |
| `metrics/mg4_public_signal_diagnostic.json` | all 288 configurations with public-objective overlap and true route reduction |
| `metrics/torpedo_usage_census.json` | deployed commander torpedo-order counts, 15 states x 2 sides |

## Figures

| file | content |
|---|---|
| `figures/fig01_b0_fidelity_primary.png` | fidelity by method per mechanism under the frozen metric, gate lines, exclusions marked |
| `figures/fig02_mechanism_values.png` | mechanism values by method: MG1 fleet, MG1 pair, MG4 route reduction |
| `figures/fig03_mg4_public_signal.png` | public objective vs true route reduction, tie sets marked (the public-information gap) |
| `figures/fig04_mg3_visibility_horizon.png` | MG3 registered arms against the 13-hex visibility horizon |
| `figures/fig05_current_vs_search.png` | CURRENT_POLICY vs SEARCH per case |

Figures for the natural census are `N/A — B1 not run` (see
`06_B1_CENSUS_NOT_RUN.md`).

## Scripts

| file | role |
|---|---|
| `scripts/m22_core.py` | fire evaluators (LEGAL_FIRE_HEURISTIC, FIRE_SEARCH), NetEH panel, movement application, plan pools |
| `scripts/fire_calibration.py` | the 20-state evaluator calibration |
| `scripts/m22_b0.py` | case reproduction + the five methods + the gate |
| `scripts/m22_figures.py` | figures from the frozen metrics only |

## Reproduction

```
PYTHONPATH=backend/src:research/m2_2/scripts:research/m2_1/scripts \
  .venv/bin/python research/m2_2/scripts/fire_calibration.py
PYTHONPATH=backend/src:research/m2_2/scripts:research/m2_1/scripts \
  .venv/bin/python research/m2_2/scripts/m22_b0.py ALL
PYTHONPATH=backend/src:research/m2_2/scripts:research/m2_1/scripts \
  .venv/bin/python research/m2_2/scripts/m22_figures.py
```

Wall clock: calibration 86 s, B0 127 s, figures 55 s. Deterministic seeds
throughout (random draws use `random.Random(20260921)`).
