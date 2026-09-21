# DATA_MANIFEST.md — Phase A.2

| path | content |
|---|---|
| `raw/track_a_audit/oracle_audit_{task}.json` | exact-knapsack audit: checks, allocation counts, V_oracle/V_uniform16, gap, CI |
| `raw/track_b_a2/labels_{task}.csv` | complete labeled universe (16 seeds × 165 grid = 2700 rows/task) |
| `raw/track_b_a2/truth_{task}.json` | severity lines, true transition edges, failure fraction |
| `raw/track_b_a2/acquisition_{task}.json` | per method × K × 30 repetitions recall (raw arrays kept) |
| `raw/track_c_a2/cases_{task}.json` | per-case repair matrix, causal cells, probe outcomes |
| `raw/track_c_a2/injection_metadata.csv` | **separate** file; never read by attribution |
| `metrics/phase_a2_verdict.json` | machine-readable verdicts |
| `metrics/a2_oracle_audit.json`, `a2_track_b.json` | stage aggregates |
| `code_patch/a2_*.py` | the three Phase A.2 runners |
| `logs/a2_*.log` | run logs |

Not included: model checkpoints (see `checkpoints_manifest/` for SHA256 + path) and
`runs/` scratch directories.
