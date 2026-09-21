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
