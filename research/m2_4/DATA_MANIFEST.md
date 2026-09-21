# M2.4 DATA MANIFEST

## Metrics

| file | content |
|---|---|
| `metrics/m24_gate1_interaction.json` | 10 pilots, 150 ship pairs, every `phi_ij`, per-pilot `q_i`, both agreement readings, pilot locators |
| `metrics/m24_gate2_coordination.json` | every evaluated state: five methods' `U` and eval counts, Δ vs each baseline, pair probes, and the recorded context (collisions, legal/visible pairs, aspects, ranges, concentration) |
| `metrics/m24_gate2_partial.json` | crash-safe partial record written during the run |
| `metrics/m24_final.json` | the frozen mapping result |

## Figures

| file | content |
|---|---|
| `figures/fig01_interaction_distribution.png` | `phi_ij` distribution with the 0.05 floor |
| `figures/fig02_gate2_scatter.png` | beam vs greedy against beam vs sequential / random, per panel, with W/T/L |
| `figures/fig03_per_scenario.png` | per-scenario median Δ against the frozen floor |

## Logs

`logs/m24_gate1.log`, `logs/m24_gate2.log` (both `-u`).

## Reproduction

```
cd iron-bottom-sound
export PYTHONPATH=backend/src:research/m2_4/scripts:research/m2_3/scripts:research/m2_2r/scripts:research/m2_2/scripts:research/m2_1/scripts
.venv/bin/python research/m2_4/scripts/m24_jtc.py gate1   # ~4 min
.venv/bin/python research/m2_4/scripts/m24_jtc.py gate2   # ~33 min
```

Deterministic seeds (`random.Random(20260921 + …)`) for the matched-budget random
arm and the bootstrap. Budget: Gate I ≈ 450 exact evaluations, Gate II ≈ 1,300
recorded (≈ 44 per state × 30 evaluated states), wall clock 1973 s for Gate II.
No paid LLM calls. Production engine untouched.
