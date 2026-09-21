# M2.2-R / B1E DATA MANIFEST

Branch: `research/m2-2-compiler-fidelity` (continues the M2.2 branch; the M2.2
bundle is untouched and still recorded under `research/m2_2/`).

## Frozen inputs, never modified

| artifact | status |
|---|---|
| `research/m2_1/scripts/mg/mg_cases.py` (holds the defective `intent_plans`) | **not edited** — `CURRENT_INTENT_PRE_FIX` must stay reproducible |
| `research/m2_1/*` (MG1..MG5 cases, verdicts) | read-only; gates `FAIL_3_OF_5` unchanged |
| `research/m2_2/*` (B0 gates, metrics) | read-only; `GOLD_COMPILER_GAP = FAIL/BLOCKED_BY_METRIC_VALIDITY` unchanged |
| `backend/src/iron_bottom_sound/**` | production engine untouched; no rule edits |

## New code

| file | role |
|---|---|
| `scripts/intent_compiler.py` | `REPAIRED_INTENT_BASELINE` (frozen arc-table rule) + re-export of the frozen pre-fix function |
| `scripts/test_intent_compiler.py` | unit test: (i) repaired ≠ narrow arm, (iii) pre-fix == narrow arm, (iv) no dead-ahead/astern; (ii) reported diagnostic |
| `scripts/b1e.py` | state scan, five movement arms, six torpedo arms, MG3-E, identifiability risks |
| `scripts/mg1_dual.py` | MG1 L0/L1/externality freeze |
| `scripts/b1e_verdict.py` | frozen verdict mapping + figures (reads frozen JSONs only) |

## Metrics

| file | content |
|---|---|
| `metrics/intent_compiler_unit_test.json` | unit-test criteria, pass/fail, reported diagnostic |
| `metrics/mg1_dual_scale.json` | MG1 arms on L0 and L1 with externality |
| `metrics/mg3e.json` | MG3-E scan (162 state-checks, rejection reasons) + chosen case + gate |
| `metrics/b1e_movement_census.json` | 52 natural movement states (104 state-sides), five arms, L0/L1/externality, summary |
| `metrics/b1e_movement_states.jsonl` | append-only per-state rows written as they are produced (crash safety) |
| `metrics/b1e_torpedo_census.json` | 15 torpedo states, six arms, graded+binary risk panels, public-hypothesis control |
| `metrics/b1e_verdicts.json` | the frozen §7 mapping, its inputs, and per-scenario rates |

## Figures

| file | content |
|---|---|
| `figures/fig01_b1e_movement_local_team_ext.png` | distribution of ΔL0, ΔL1 and externality by arm |
| `figures/fig02_b1e_opportunity_rates.png` | MECHANISM_OPPORTUNITY rate by scenario against the frozen 20 % line |
| `figures/fig03_b1e_strata.png` | which strata were actually filled (shortfalls visible, not back-filled) |
| `figures/fig04_b1e_torpedo.png` | route reduction by arm, shared vs Bayes regret, public-vs-full-state gap |

## Logs

`logs/b1e_movement.log`, `logs/b1e_torpedo.log` (both run with `-u` so progress
is unbuffered), plus the console record of the MG3-E and MG1-dual runs.

## Reproduction

```
cd iron-bottom-sound
export PYTHONPATH=backend/src:research/m2_2r/scripts:research/m2_2/scripts:research/m2_1/scripts
.venv/bin/python research/m2_2/scripts/test_intent_compiler.py
.venv/bin/python research/m2_2r/scripts/mg1_dual.py
.venv/bin/python research/m2_2r/scripts/b1e.py mg3e
.venv/bin/python research/m2_2r/scripts/b1e.py movement     # ~35 min
.venv/bin/python research/m2_2r/scripts/b1e.py torpedo      # ~2 min
.venv/bin/python research/m2_2r/scripts/b1e_verdict.py
```

Deterministic seeds throughout; the only RNG use is `random.Random(20260921)`
for the matched-budget random arm. No paid LLM calls. Budget: ~5,000 engine
evaluations (movement census ~4,000; torpedo ~30 real launches plus 15 route
sets; MG3-E 162 state-checks; MG1 dual ~25).
