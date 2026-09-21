# 01_TRACK_B_SAMPLING_COMPLETION.md

Per plan §2.1: the already-running Sampling labeling job was allowed to finish; no
second job was started; Balance was not relabeled.

- `raw/track_b_a2/labels_sampling.csv`: **2700 rows** = 16 frozen initial seeds
  (60000+i) x 165-cell grid. The A.2 acquisition stage also completed before this
  phase began (`metrics/a2_track_b.json`), so both label tables were already closed.
- Reconciliation over the hardened registry for track=B, task=sampling,
  method=universe_label: attempted = success + rejected + error holds (see
  `metrics/registry_reconciliation_a3.json`).
- The two label tables are declared **immutable evaluation tables** for A.3; no row
  was added, removed or relabeled (file hashes in `DATA_MANIFEST.md`).
