# DATA_MANIFEST.md

## Root documents
`00_EXECUTIVE_SUMMARY.md` · `01_ENVIRONMENT_POLICY_AUDIT.md` · `02..05` track
documents · `06_CROSS_TRACK_DECISION_MATRIX.md` · `07_POSITIVE_RESULT_CONTRACTS.md`
· `08_CLOSEST_PRIOR_COLLISION_NOTES.md` · `09_IBS_COMPATIBILITY_NOTE.md` ·
`PRE_REGISTRATION_PHASE_A.md` · `EXPERIMENT_REGISTRY.csv` · `MISSINGNESS_AUDIT.csv`
· `FAILURES_AND_COUNTEREXAMPLES.md` · `BUG_AND_RERUN_LOG.md` · `ENVIRONMENT_LOCK.json`

## raw/
| file | content |
|---|---|
| `vmas_task_probe.json` | official VMAS task enumeration + throughput probe (10 tasks) |
| `training_registry.csv` | one row per (task, seed) training attempt with status, log and run dir |
| `INVALID_training_registry_v1.csv` | the defective registry (wrong checkpoint path) preserved per red line 6 |
| `positive_controls_registry.csv` | per-control PASS/FAIL rows with attempted/valid/rejected/error counts |
| `positive_controls.json` | control results with full detail (curves, recalls, repair sets) |
| `INVALID_positive_controls_v1.json`, `..._v2.json` | defective control instruments, preserved |
| `track_common/clean_baseline.csv` | 1000 clean episodes (500/task) with return, success, length, status |
| `track_common/checkpoint_selection.json` | per-seed validation returns, median-seed rule, clean summary |
| `track_a/`, `track_b/`, `track_c/`, `track_d/` | empty by design: those tracks were not run |

## metrics/
`phase_a_verdict.json` — the machine-readable summary, with **no** `SELECTED_MAINLINE`
field populated (the PI decides).

## checkpoints_manifest/
`checkpoints_manifest.csv` — path, task, seed, frame step and SHA256 for every
checkpoint, so the bundle stays small and the checkpoints stay reproducible.

## Not included
No multi-hundred-MB checkpoint is zipped; the manifest carries SHA256 + source path
+ the exact training command instead (`REPRODUCE.md`).
