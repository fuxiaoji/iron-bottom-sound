# DATA_MANIFEST.md — M2-0

Excluded from the bundle (regenerable):
- `research/m2_0/snapshots/` (60 gzipped GameStates, ~10 MB) — regenerate:
  `PYTHONPATH=backend/src:research/m2_0/scripts .venv/bin/python research/m2_0/scripts/track_a_oracle.py capture`
- `research/m1_5`-era caches: none.

Budget ledger (M2-0): ~150 (B0) + 30 (P0 pilot) + ~250 (B1/B2 arms incl.
re-runs after F6) + ~35x20x6+35x5x20 continuation batches (A oracle) ≈ within
the plan's 1,500-match / 50,000-continuation ceilings. 0 paid LLM calls.
Engine files modified: 0. New packages: none this phase (sklearn from M1.5
reused for nothing here).
