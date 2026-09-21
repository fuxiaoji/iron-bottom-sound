# REPRODUCE.md

## 0. Environment

```
python3.9 -m venv .venv_phase_a
.venv_phase_a/bin/python -m pip install torch==2.8.0 vmas==1.5.2 benchmarl==1.5.2 scikit-learn
```

Versions and platform are frozen in `ENVIRONMENT_LOCK.json` (setup took 112 s from
a clean venv). Device is CPU; MPS is available but 2.1x slower on this workload.

## 1. Base policies (A0.2) — ~15 min per seed on 10 cores

```
.venv_phase_a/bin/python -u research/phase_a/scripts/train_base.py
```

Runs `benchmarl/run.py algorithm=mappo task=vmas/{navigation,balance} seed={0,1,2}`
with `experiment.max_n_frames=600000`, csv logger, checkpoint interval 120k and
checkpoint-at-end, three runs in parallel. A row is written per attempt into
`raw/training_registry.csv`. The dedicated launcher is `scripts/train_base.py`;
the replacement task currently training was started with the same hydra arguments
and `task=vmas/sampling` (see `logs/task_switch.log`).

## 2. Clean baseline + median-seed selection (A0.3) — ~4 min

```
.venv_phase_a/bin/python -u research/phase_a/scripts/eval_clean.py
```

Writes `raw/track_common/clean_baseline.csv` (500 episodes/task) and
`raw/track_common/checkpoint_selection.json` (median-seed rule applied).

## 3. Positive controls (A0.4) — ~1 min

```
.venv_phase_a/bin/python research/phase_a/scripts/positive_controls.py
```

## 4. Tracks A/B/C — NOT RUN in this window

The frozen designs are in `PRE_REGISTRATION_PHASE_A.md` §5–§7 and the shared
plumbing they build on is `scripts/phase_a_common.py` (frozen-policy loader,
perturbation hooks, native-success predicate, registry helpers). A rerun needs no
new setup; it needs the track runners, which do not exist yet.

## Determinism

Every episode is seeded explicitly (`make_task_env(..., seed=...)` and
`env.reset(seed=...)`); selection and evaluation RNG streams in the planning
operator use disjoint seeds by construction. The actor is deterministic
(`tanh(mean)`), so repeated runs of the eval scripts reproduce the same numbers.
