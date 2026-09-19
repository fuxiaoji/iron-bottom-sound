# DATA_MANIFEST.md — M1.5 checkpoint

Not included in the zip (regenerable, large):

| Path | What | Size | Regenerate |
|---|---|---|---|
| `research/m1_5/metrics/e2_t2_states.json` | cached TORPEDO_PLANNING state JSON for the 40 rollout states | ~130 MB | automatic: `e2_t2_rollout.py` rebuilds it deterministically from (scenario, seed, profile) on first run |
| `research/m1_5/metrics/e2_t1_decisions.json` | full decision records incl. per-candidate order dicts (zip carries the .gz, 124 MB -> compressed) | 124 MB | `e2_t1_influence.py` (deterministic) |
| `research/m1_g1/states/` (upstream) | M1 G1 branch states | ~15 MB | `research/m1/g1/scripts/g1_driver.py gen` |

Everything else (metrics JSON/CSV, decisions, figures, scripts, logs, strong
cases) is included. Rollout ledger for M1.5: ~118 sampling matches + ~40 state
rebuilds + 600 rollout continuations ≈ 760 match-equivalents of the ≤15,000
budget; 0 paid LLM calls; engine untouched; sklearn 1.9.1 added to the project
.venv (reversible).
