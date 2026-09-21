# 01_ENVIRONMENT_POLICY_AUDIT.md

## A0.1 Environment lock — DONE

`ENVIRONMENT_LOCK.json` records platform, package versions and the frozen configs:

```
python 3.9.6 · torch 2.8.0 · vmas 1.5.2 · benchmarl 1.5.2 · torchrl 0.10.1
tensordict 0.10.0 · hydra-core 1.3.7 · numpy 2.0.2 · scikit-learn 1.6.1 · device CPU
```

Installation completed in **112 s** (well inside the 25 % setup budget). MPS is
available but was measured **2.1x slower** than CPU (navigation pilot, 100k
frames: 4m26s mps vs 2m03s cpu), so CPU is frozen. Official sources only
(BenchMARL / VMAS PyPI releases corresponding to the official repositories).

## A0.2 Base policy — DONE, with one documented task switch

MAPPO through BenchMARL, 3 seeds, **600 000 frames** each, `share_policy_params=True`,
csv logger, checkpoint every 120k + at end. All six runs completed
(`raw/training_registry.csv`, 6/6 SUCCESS, two checkpoints per run present).

| task | seed 0 | seed 1 | seed 2 | median seed | clean success (500 ep) |
|---|---|---|---|---|---|
| `vmas/balance` | 0.90 | 0.90 | 0.91 | **1** | **0.876** |
| `vmas/navigation` | 1.00 | 1.00 | 1.00 | 0 | **1.000 → SATURATED** |

**Task switch (A0.2, executed before any Track result):** `navigation` reaches
100 % success on the 500-episode clean baseline, i.e. no measurable room for
planning or perturbation interventions. Per the frozen rule it is replaced by
`vmas/sampling` (3 agents, coverage/spread coordination — structurally distinct
from balance's shared-rigid-body coupling). Recorded in `logs/task_switch.log`
before any Track measurement; the switch is not made after results.

## A0.3 Clean baseline and failure oracle — DONE, with a corrected native signal

500 clean episodes per task on the median seed (1000 rows in
`raw/track_common/clean_baseline.csv`, 0 errors, 0 rejected):

| task | n | mean return | std | success rate | return p25 |
|---|---|---|---|---|---|
| navigation (retired) | 500 | 16.07 | 3.55 | 1.000 | 13.65 |
| balance | 500 | 121.23 | 25.69 | **0.876** | 115.73 |

**Corrigendum to the pre-registered oracle.** The pre-registration named
`final_rew`/`ground_rew`-style fields as the native success signal. Direct
inspection of this VMAS build showed that they do **not** track the engine's own
termination: at the terminal step of a navigation episode all four agents were
inside their goal radius (0.043/0.026/0.067/0.084 vs radius 0.1) and `done()`
fired, while `all_goal_reached` and `final_rew` stayed False. Using the fields as
written would have reported 0 % success for a policy that actually completes the
task — a pure instrument error. The oracle used from here on is therefore each
scenario's **own** `done()` criterion:

```
navigation: episode ends with done() = all agents within their goal radius  -> success
balance   : done() = on_the_ground OR overlap(package, goal);
            success = done() AND NOT on_the_ground
```

The change is a correction of a broken instrument, not a threshold change: no
Track number existed when it was made, and the pre-registration's fallback
(clean-distribution return threshold, p25 = 115.73 for balance) remains available
and is used as the Track C repair threshold.

## A0.4 Positive controls — ALL PASS (no measurement blocker)

| control | status | evidence |
|---|---|---|
| A (budget allocation) | **PASS** | oracle splits the frozen total 20 as 4 (insensitive) / 16 (sensitive); sensitive gain at b=16 = +8.9 reward, insensitive gain = 0.000 |
| B (known boundary) | **PASS** | structure-aware / random boundary recall = 3.36x (K=50) and 2.71x (K=100), 1.11x at K=200; strictly better at 2 of 4 budgets |
| C (single injected fault) | **PASS** | exhaustive repair over all cells/windows returns exactly the injected 2-cell window `[(2,3),(2,4)]`; no single-cell repair restores success; unique minimal set |

Two control instruments were themselves defective on first run and were fixed
before any scientific use; both defective versions are preserved as `INVALID_*`
(see `BUG_AND_RERUN_LOG.md`).

## Track readiness

The frozen pre-registration is in place, the environment is locked, the base
policy is certified on the surviving task, the native oracle is corrected, and
all three positive controls pass. Tracks A/B/C have **not** been executed in this
execution window; their status is `BLOCKED` with the reason recorded in
`metrics/phase_a_verdict.json`, and no Track number exists yet.
