# BUG_AND_RERUN_LOG.md

Every entry preserves the buggy artefact and states whether a rerun was needed.
Red line 6: buggy runs are kept as INVALID and the fixed experiment reruns from
zero.

## B1 — positive-control instruments (Track-level, fixed, rerun)

- **Toy A v1** (`INVALID_positive_controls_v1.json`): the frozen budget set
  {0,4,16,64} admits only the split 16+16 at total 32, so "the oracle spends more
  on the planning-sensitive state" was **structurally impossible**. Fixed by
  setting the toy total to 20 (splits 4+16 / 16+4). Rerun from zero → PASS.
- **Toy B v1/v2** (`INVALID_positive_controls_v1.json`, `..._v2.json`): v1 used a
  first-match `mid`-severity refinement that stopped refining columns whose
  transition lay above mid-severity; v2 kept that flaw behind a bigger space; both
  made the "structured" probe *worse* than random. Fixed by replacing the probe
  with per-column bisection on the ordered axis **and** by adopting the standard
  discovery definition (a boundary cell is discovered iff it or two of its
  neighbours were queried with opposite labels). The diffuse "any queried
  neighbour" definition was rejected explicitly because it rewards uniform coverage
  rather than transition localisation. Rerun from zero → PASS.
- **Toy C v1** (`INVALID_positive_controls_v1.json`): the first version was a
  tautology (repairing a non-fault cell changed nothing) and its arithmetic had
  the clean total already above the failure threshold. Redesigned as a 2-cell
  time-window fault so that single-cell repairs fail and the minimal restoring set
  is the window → PASS, and the control now actually tests minimality/uniqueness.

## B2 — training registry status check (registry only, no retraining)

`train_base.py` v1 looked for checkpoints under `run_dir/<run_id>/`, but BenchMARL
writes them under `run_dir/<config-hash-dir>/checkpoints/`. All six successful
runs were therefore recorded as `REJECTED_NO_CHECKPOINT`. The buggy registry is
preserved as `raw/INVALID_training_registry_v1.csv`; the corrected registry was
regenerated from ground truth (log present, no traceback, `checkpoint_600000.pt`
present) and the training runs themselves needed no rerun — they completed with
returncode 0 and two checkpoints each.

## B3 — native success oracle (instrument, corrected before any Track number)

The pre-registered oracle used VMAS's `final_rew`/`ground_rew` fields; on this
build they disagree with the scenario's own `done()` (verified: done() fires with
all agents inside their goal radius while `all_goal_reached` is False). The
reported success rate would have been 0 % for a policy that completes the task.
Oracle replaced by the scenarios' own `done()` criteria (see
`01_ENVIRONMENT_POLICY_AUDIT.md`), corrected **before** any Track measurement.

## B4 — task saturation and the A0.2 switch (not a bug, recorded for audit)

`vmas/navigation` reached 100 % clean success → `SATURATED_GE_95PCT` → replaced by
`vmas/sampling` strictly before Track results, per the frozen A0.2 rule. The
switch and its reason are in `logs/task_switch.log`.

## B5 — operator error: a second training batch was launched unintentionally

While the replacement task (`vmas/sampling`) was training, `train_base.py` was
launched again in the same call without arguments. Its task list is frozen to
`navigation,balance`, so it began a **second, unwanted** batch of those six runs,
competing for CPU with the sampling runs and rewriting `raw/training_registry.csv`.
The batch was killed within ~2 minutes; the corrected registry is regenerated from
ground truth below and the navigation/balance checkpoints from the first batch are
the ones used everywhere. Recorded here because an unaudited second batch is
exactly the kind of silent duplication the red lines forbid, even though no
scientific number was produced by it.
