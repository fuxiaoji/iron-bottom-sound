# code_patch — Phase A.3

## Added (research only)
- `scripts/a3_track_b.py` — §2.4 acquisition positive control + §2.5 valid
  tournament (corrected STRUCTURED_ACTIVE with endpoint probes and true bisection;
  real ExtraTrees generic learner; full query traces)
- `scripts/a3_track_c.py` — C0 generator-feasibility calibration (vectorised paired
  episodes, ordered frozen settings, first-in-band rule, mean-shift sanity
  diagnostic); C1/C2/C3 stages implemented behind `--stage` but gated off by the
  C0 verdict
- `scripts/hardened.py` (from v3.1) — append-only registry with per-unit final
  status, JSONL checkpoints, reconciliation; used by every A.3 runner

## Not changed
- `backend/src/iron_bottom_sound/**`, production engine, BenchMARL/VMAS installs
- the immutable A.2 label tables (`raw/track_b_a2/labels_*.csv`)
- C material-causality semantics; the fault-strength grid after outcomes
