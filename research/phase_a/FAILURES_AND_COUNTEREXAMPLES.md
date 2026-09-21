# FAILURES_AND_COUNTEREXAMPLES.md — Phase A

## PA-F1 — the pre-registered native oracle was unusable on this VMAS build

`final_rew` / `all_goal_reached` do not track the scenario's own `done()`. Verified
directly: at the terminal step of a navigation episode all four agents were inside
their goal radius (0.043/0.026/0.067/0.084 vs radius 0.1) and `done()` fired, while
`all_goal_reached` stayed `False` and `final_rew` stayed `0.0`. Had the
pre-registered fields been used, a policy that completes the task would have been
reported at **0 % success** — and every downstream failure-fraction gate (Track B's
5–50 % band, Track C's failure set) would have been measured on a broken oracle.
Corrected to the scenarios' own `done()` before any Track number existed.

## PA-F2 — a saturated task would have silently voided two tracks

`vmas/navigation` reaches **100 %** clean success. With a saturated policy, Track A
measures planning gains on states where nothing can improve, and Track B's
perturbation grid would need extreme severities to leave the 0 % failure region.
The frozen A0.2 switch rule caught this *before* any Track result; the task was
replaced by `vmas/sampling` and the reason recorded in `logs/task_switch.log`.

## PA-F3 — my own efficiency assumption was wrong

I assumed MPS would accelerate training. Measured: **2.1x slower** than CPU
(navigation pilot, 100k frames: 4m26s on mps vs 2m03s on cpu). CPU was frozen
before the real runs, so the frozen budget is unaffected — but an MPS default would
have doubled the training cost of the whole phase.

## PA-F4 — three defective instruments, all preserved

Two positive-control toys and the training-registry status check were defective on
first use; every defective artefact is kept as `INVALID_*` with the fix in
`BUG_AND_RERUN_LOG.md` (B1: a budget total that made the allocation gate
unreachable by construction; B1 again: a structured probe that was *worse* than
random because it stopped refining columns; B2: a checkpoint path that reported six
successful runs as rejected; B5: an unintended duplicate training batch). The
counterexample of record is B1's first version — a toy that could not pass no
matter how good the method was, which is exactly the failure mode a positive
control exists to catch.

## PA-F5 — a tautological control that had to be redesigned

Positive control C v1 asserted that repairing a non-fault cell changes nothing,
which is true by definition and tests no repair machinery. It was redesigned as a
2-cell time-window fault so that single-cell repairs genuinely fail and the minimal
restoring set must be recovered — the version that now passes is the one that
actually constrains the Track C instrument.
