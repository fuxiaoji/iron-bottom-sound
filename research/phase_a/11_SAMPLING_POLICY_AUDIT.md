# 11_SAMPLING_POLICY_AUDIT.md

```
status: RUNNING at the end of this execution window (frozen protocol, no shortcut)
task:   vmas/sampling     median-seed rule: same as balance (median validation return)
```

## Frozen protocol being executed (`scripts/sampling_audit.py`)

1. 100 validation episodes on **each** of the three 600k-frame checkpoints
   (seeds 0,1,2) → median seed by mean return (never the best seed).
2. 500 clean episodes and 500 random-action episodes on the median checkpoint,
   one registry row per episode through the hardened registry.
3. Frozen quantiles written into `ENVIRONMENT_LOCK.json`
   (`sampling_semantics.clean_Q25/Q50/Q75/IQR`), plus the two derived rules:
   - Track B failure = `episode_return < clean_Q25`
   - Track C valid causal failure = paired identical initial seed with
     `clean >= Q50` AND `faulted < Q25` AND `clean − faulted >= 0.5 · IQR`
   Sampling has **no native binary success**, and none is invented.
4. Quality gate (all four required):
   `trained mean > random mean` · paired bootstrap 95 % CI excludes 0 ·
   standardised effect size (Cohen's d) >= 0.5 · error rate <= 1 %.

## Partial results available at the end of this window

| checkpoint seed | validation mean return (100 episodes) |
|---|---|
| 0 | 172.66 |
| 1 | 196.96 |
| 2 | *in progress* |

Training itself finished 100/100 iterations for all three seeds with end
checkpoints present (`raw/training_registry.csv`). The clean/random episode counts,
the frozen quantiles and the gate verdict **do not exist yet** and are deliberately
not guessed here: the script writes them when it completes, and no Track B/C rule
may be applied before they exist.

## What follows automatically

When the audit completes it writes
`raw/track_common/sampling_audit.csv` (1000 episode rows),
`raw/track_common/sampling_quality_gate.json`, and the quantiles into
`ENVIRONMENT_LOCK.json`. If the gate fails, the single frozen fallback is
`VMAS/WIND_FLOCKING`, which would need the same three-seed training and the same
audit before any Track row; if that also fails, `PHASE_A_TASK_PAIR = BLOCKED`.
