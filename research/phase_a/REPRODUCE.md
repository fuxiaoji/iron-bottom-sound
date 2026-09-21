# REPRODUCE.md — Phase A.2

```
cd iron-bottom-sound && export PYTHONPATH=backend/src
.venv_phase_a/bin/python research/phase_a/scripts/a2_oracle_audit.py        # ~30 s, no new sims
.venv_phase_a/bin/python research/phase_a/scripts/a2_track_b.py           # ~50 min (labels cached on rerun)
.venv_phase_a/bin/python research/phase_a/scripts/a2_track_c.py --per-task 50 --attempts 1000
```

Deterministic: frozen seed lists (60 000+ for Track B, 70 000+ for Track C), 30
frozen acquisition repetitions, all episodes seeded. Track B reuses cached labels,
so re-running the acquisition comparison is minutes, not hours.

## Phase A.3
```
.venv_phase_a/bin/python research/phase_a/scripts/a3_track_b.py    # ~10 min, labels cached
.venv_phase_a/bin/python research/phase_a/scripts/a3_track_c.py --stage C0   # ~15 min
```
Deterministic: frozen synthetic-pool seeds, calibration seeds 80 000+, acquisition
repetitions seeded per (rep, K). Vectorised paired episodes share initial states by
construction (same reset seed per arm).
