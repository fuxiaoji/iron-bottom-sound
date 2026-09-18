# DATA_MANIFEST.md — M0 cheap kill checkpoint

Artifacts NOT included in M0_CHEAP_KILL_CHECKPOINT.zip, with regeneration commands.

| Path | What | Size | Regenerate | Must keep? |
|---|---|---|---|---|
| `/tmp/m0_psro/smoke/` | PSRO smoke checkpoint (outside repo by design) | ~10 KB | `PYTHONPATH=backend/src .venv/bin/python rl/psro.py --smoke --out /tmp/m0_psro/smoke` | no (summary extracted into `logs/p0_psro_smoke.txt`) |
| `research/m0/results/A0_*.csv/json` | A0 census metrics | ~230 KB | `PYTHONPATH=backend/src:research/m0 .venv/bin/python research/m0/a0b0_census.py` | included in zip (small) |
| IBS calibration raw matches | 2,160 individual match trajectories | not stored (per-match results aggregated at generation time into counts) | `PYTHONPATH=backend/src:research/m0 .venv/bin/python research/m0/c0_psro/calibrate.py --scenario {IBS-S-03,IBS-S-01}` | aggregated distributions kept (`results/c0_calibration_*.json`); raw trajectories regenerable from recorded seeds |
| `research/m0/figures/*.png` | 7 figures | ~500 KB | `PYTHONPATH=backend/src:research/m0 .venv/bin/python research/m0/make_figures.py` | included |

Budget ledger: IBS matches consumed 2,238 of 20,000 (78 P0 baseline + 2,160 C0
calibration); paid LLM API calls 0; engine source files modified 0.
