# 10_A0_ERRATA_AND_TASK_SWITCH.md

All A0 errata are kept, not cleaned up. `A0_STATUS = ACCEPTED_WITH_ERRATA`.

## E1 — the pre-registered native success predicate was unusable (PA-F1)

`final_rew` / `all_goal_reached` do not track the scenario's own `done()` on this
VMAS build. Verified: at the terminal step of a navigation episode all four agents
were inside their goal radius (0.043 / 0.026 / 0.067 / 0.084 vs radius 0.1) and
`done()` fired, while `all_goal_reached` stayed `False` and `final_rew` stayed
`0.0`. The pre-registered oracle would have reported **0 % success for a policy
that completes the task**, and every downstream failure-fraction gate would have
been measured on a broken signal.
**Correction:** the oracle is each scenario's own `done()` criterion; balance
failure = terminated with the package on the ground, success = terminated without.

## E2 — training-registry checkpoint path (PA-F4/B2)

The first launcher looked for checkpoints under `run_dir/<run_id>/`; BenchMARL
writes them under `run_dir/<config-hash-dir>/checkpoints/`, so six successful runs
were recorded as `REJECTED_NO_CHECKPOINT`. The buggy registry is preserved as
`raw/INVALID_training_registry_v1.csv`; the corrected registry is regenerated from
ground truth (log present, no traceback, `checkpoint_600000.pt` present) and **no
training was rerun** — the runs themselves were valid.

## E3 — three defective instruments, all preserved as INVALID

`raw/INVALID_positive_controls_v1.json` / `_v2.json`: toy A's budget total (32) made
the allocation gate unreachable by construction (only 16+16 fits); toy B's first
two structured probes were *worse* than random, first because they stopped refining
columns whose transition lay above mid-severity and then because the discovery
metric rewarded uniform coverage — that diffuse definition was explicitly rejected;
toy C v1 was a tautology (repairing a non-fault cell changes nothing). Every fix
and rerun is in `BUG_AND_RERUN_LOG.md` (B1).

## E4 — an accidental duplicate training batch (PA-F4/B5)

A second `train_base.py` invocation was launched in the same call as the sampling
runs. Its frozen task list is `navigation,balance`, so it began re-training those
six runs, competing for CPU and rewriting the registry. Killed within ~2 minutes;
the checkpoints used everywhere are from the first batch. Recorded because an
unaudited second batch is exactly the silent duplication the red lines forbid,
even though no scientific number came from it.

## E5 — navigation saturation and the task switch (A0.2, pre-Track)

`vmas/navigation` produced **100 %** clean success over 500 episodes
(`SATURATED_GE_95PCT`): with the task solved, Track A has no planning headroom to
measure and Track B would need extreme severities to leave the 0 %-failure region.
Per the frozen A0.2 rule the task was replaced **before any Track result**, with the
reason written to `logs/task_switch.log`. Per the v3.1 directive the replacement is
`vmas/sampling`, and the pair is now:

```
PRIMARY_PHASE_A_PAIR = VMAS/BALANCE + VMAS/SAMPLING      (locked, no further shopping)
```

The one frozen fallback if sampling fails its policy gate is `VMAS/WIND_FLOCKING`;
if that also fails, `PHASE_A_TASK_PAIR = BLOCKED` and no further task shopping.

## A0 artefacts

`ENVIRONMENT_LOCK.json` (platform, packages, device decision incl. the measured
2.1x MPS slowdown, task configs, `sampling_semantics` once frozen),
`raw/training_registry.csv` (9 rows: 6 SUCCESS, 3 IN_PROGRESS at the time of
writing), `raw/positive_controls.json` (A/B/C PASS), `raw/track_common/`
(balance clean baseline 500 episodes, checkpoint selection), `history/
A0_PARTIAL_CHECKPOINT/` (the accepted v3.0 package).
