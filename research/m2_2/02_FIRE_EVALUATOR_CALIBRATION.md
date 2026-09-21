# 02_FIRE_EVALUATOR_CALIBRATION.md — LEGAL_FIRE_HEURISTIC vs FIRE_SEARCH

Purpose (pre-registration): decide whether the cheap `LEGAL_FIRE_HEURISTIC` may
carry the large-sample mechanism metrics, or whether `FIRE_SEARCH` is needed.

20 movement states (the M2.1 snapshot pool), both evaluators, engine-real
post-movement/pre-gunnery geometry.

| statistic | value |
|---|---|
| Spearman(net EH) | **0.908** |
| mean absolute net-EH difference | 2.61 EH |
| max absolute net-EH difference | 4.89 EH |
| same-target fraction | **0.888** |
| mean relative own-EH difference | 0.191 |
| verdict | `HEURISTIC_PARTIAL (rank corr >= 0.7) - report both` |

Decision: the mechanism metrics are computed with `LEGAL_FIRE_HEURISTIC` and the
`FIRE_SEARCH` panel is reported beside them where it was computed (MG1 gold vs
current policy). Neither is ever called optimal.

## M22-F2 — the first calibration run was a bug, not a result

The first run produced Spearman(net EH) per side = **-0.333** and a 49-mount
entry for a 5-mount ship. Cause: `fire_search` stored one and the same mount
list under every mount id of the "all mounts on one target" option and then
extended its per-target bucket by that list once per key, multiplying that
ship's firepower by its mount count. A search whose option set contains the
heuristic's own style of allocation cannot be strictly worse than it; the
negative correlation was the tell. After the repair (option representation
`{target_id: [mounts]}`, one `_group_eh` call per target and mount kind, each
mount counted once) the correlation is +0.908 and the 49-mount entry is gone.
All downstream MG1/MG3/MG4 numbers in this bundle were produced after the fix.
