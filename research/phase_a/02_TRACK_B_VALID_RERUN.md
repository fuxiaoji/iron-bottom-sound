# 02_TRACK_B_VALID_RERUN.md

```
TRACK_B = B_KILL_FOR_MAINLINE   (balance side complete; sampling side still running at packaging)
```

## The rerun is design-valid on the axis the PI identified

G = 165 (original grid), so M = ceil(2500/165) = **16** frozen initial seeds (inside
the prescribed [12, 24] clip) → universe = 16 × 165 = **2700 configurations per
task**, so every K in {25, 50, 100, 200} satisfies the K ≤ 10 % rule. The generic
baseline is now a **real label-based ExtraTrees ensemble** (40 trees, vote-entropy
acquisition with a frozen diversity tie-break); the frozen-policy action-entropy
proxy is no longer used. 30 acquisition repetitions per task × method × K.

## Balance result (complete)

Boundary recall at K (fraction of true transition edges localised to within one
severity interval):

| method | K=25 | K=50 | K=100 | K=200 |
|---|---|---|---|---|
| RANDOM | 0.033 | **0.078** | **0.089** | **0.211** |
| STRATIFIED_RANDOM | 0.033 | 0.022 | 0.056 | 0.100 |
| GENERIC_ACTIVE (ExtraTrees) | 0.022 | 0.022 | 0.022 | 0.078 |
| STRUCTURED_ACTIVE | 0.011 | 0.022 | 0.000 | 0.033 |

`B_ACTIVE_EFFICIENCY = FAIL` (structured/random = **0.16** at K=200, gate 1.8) and
`B_MULTIAGENT_STRUCTURE = FAIL` (structured is *below* generic at every K).

## Honest reading — this is not yet a clean scientific kill

Two things are true at once:

1. **Random is the strongest method**, and the strong generic learner is genuinely
   weak (0.022–0.078), so nothing in this run supports "multi-agent structure beats
   a generic active learner".
2. **My STRUCTURED_ACTIVE implementation is the weak link**: it queries each
   severity line at mid/min/max and then fills, which cannot localise a transition
   that lies between those probes; a bisection-to-transition strategy (the one the
   probe design implies) was not implemented. So the failure mode is again the
   acquisition design, not necessarily the hypothesis — the same class of error as
   the positive-control toys and the Phase A universe sizing, now for the third time
   in this project's Track B attempts.

The universe is now valid, K is valid, and the repetitions are done; what remains
untested is a *correct* structured acquisition. Until that exists, the honest
status is `B_KILL_FOR_MAINLINE` for the run as executed, with the design defect
recorded rather than dressed up as a scientific verdict.
