# DATA_MANIFEST.md — M1 G1 checkpoint

Artifacts NOT included in M1_G1_CHECKPOINT.zip:

| Path | What | Size | Regenerate | Must keep? |
|---|---|---|---|---|
| `research/m1/g1/states/` | 546 gzipped branch states (full GameState JSON) | ~15 MB | reproduce via `g1_driver.py gen` (seeds/turns pre-declared in `g1_lab.py`) | no — regenerable byte-for-byte; the 8 strong cases' states ARE included |
| `research/m1/g1/pairs_gen.jsonl` | pre-eval pair specs (superseded by IBS_ALIAS_PAIRS.jsonl) | ~1.5 MB | `g1_driver.py gen` | no |
| `research/m1/g1/g1_power15.json` | raw 15-rep Q tables (aggregated into g1_analysis15.json / jsonl) | ~4 MB | `g1_power15.py` (~3 h) | no |

Regeneration entry points (from repo root):
- pairs + pilot eval: `PYTHONPATH=backend/src:research/m1/g1/scripts .venv/bin/python research/m1/g1/scripts/g1_driver.py all`
- power extension: `... research/m1/g1/scripts/g1_power15.py`
- final analysis: `... research/m1/g1/scripts/g1_final_analysis.py`
- strong cases: `... research/m1/g1/scripts/strong_cases.py --top 8`
- figures: `... research/m1/g1/scripts/make_g1_figures.py` + the 15-rep figure block in session log

Budget ledger: ~35,000 continuation rollouts of the 50,000 budget; 0 paid LLM
calls; engine source files modified 0.
