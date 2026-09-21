# 00_EXECUTIVE_SUMMARY.md — Phase A v3.0 (CCF-A mainline selection)

```
PHASE_A_COMPLETE = NO            (A0 complete and certified; Tracks A–C not executed)
TRACK_A = BLOCKED   (not run)
TRACK_B = BLOCKED   (not run)
TRACK_C = BLOCKED   (not run)
TRACK_D = NOT_ACTIVATED
PI_DECISION_REQUIRED = YES
```

## What this execution window delivered

A0 — environment, policy and instrument certification — is **done and auditable**,
and it produced four findings that change what the tracks should be run against:

1. **Environment locked and reproducible.** BenchMARL 1.5.2 + VMAS 1.5.2 + torch
   2.8.0 on Python 3.9.6, CPU (MPS measured 2.1x slower). Installation 112 s.
   `ENVIRONMENT_LOCK.json`.
2. **Base policies trained and verified.** MAPPO, 3 seeds × 2 tasks × 600 000
   frames, 6/6 SUCCESS with end-of-training checkpoints present
   (`raw/training_registry.csv`). Median-seed selection rule applied, never the
   best seed.
3. **The native success signal is NOT what the pre-registration assumed.** On this
   VMAS build `final_rew` / `all_goal_reached` disagree with the scenario's own
   `done()`: an episode terminated with all four agents inside their goal radius
   (distances 0.043/0.026/0.067/0.084 vs radius 0.1) while `all_goal_reached`
   stayed False. The pre-registered oracle would have reported **0 % success for a
   policy that completes the task**. The oracle now uses each scenario's own
   `done()`; the correction was made before any Track number existed and is logged
   in `BUG_AND_RERUN_LOG.md` (B3).
4. **One task is saturated and was replaced before any Track result.**
   `vmas/navigation` reaches **100 %** clean success (500 episodes) — no room for
   planning or perturbation effects — so per the frozen A0.2 rule it is replaced
   by `vmas/sampling` (coverage/spread coordination). `vmas/balance` survives at
   **87.6 %** clean success (mean return 121.2 ± 25.7, n=500). The switch is
   recorded in `logs/task_switch.log` with `vmas/sampling` training under way.

## Instruments validated (A0.4)

All three positive controls **PASS**, so no track carries a measurement blocker:

- **A** budget allocation: the oracle spends 16 on the planning-sensitive state
  and 4 on the insensitive one (+8.9 vs 0.000 reward at b=16).
- **B** known boundary: structure-aware/random boundary recall = **3.36x** (K=50),
  **2.71x** (K=100), 1.11x (K=200) — strictly better at 2 of 4 budgets.
- **C** injected fault: exhaustive repair returns exactly the injected 2-cell
  window, with no single-cell repair restoring success (unique minimal set).

Two control instruments and the training registry check were themselves defective
on first use; every defective version is preserved as `INVALID_*` and the fixes are
in `BUG_AND_RERUN_LOG.md` (B1, B2, B3, B5).

## Why the tracks are BLOCKED rather than FAIL

No Track measurement was taken, so no scientific verdict exists — reporting
`A_KILL`/`B_KILL`/`C_*` now would be fabrication. Per plan §10 the honest status
for an execution window that ends inside A0 is `BLOCKED` with the reason recorded,
and the pre-registration, frozen thresholds, validated instruments and certified
policies remain in place for an immediate rerun (`REPRODUCE.md`).

## The largest unresolved risk for the PI

`vmas/balance` succeeds in 87.6 % of clean episodes: the policy is strong enough
that perturbations must be severe to reach the pre-registered 5–50 % failure band,
and Track A's planning headroom may be correspondingly small. The replacement task
`vmas/sampling` is still training, so its clean success rate is unknown, and the
frozen two-task set will only be complete once it is measured.
