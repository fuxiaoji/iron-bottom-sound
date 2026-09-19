# 00_EXECUTIVE_SUMMARY.md — M1.5 new-mainline cheap-kill

```
E1_SIGNAL         = PASS   (rho sparse-but-consequential: 83-90% low, 10-17% high-meaningful,
                            high-rho stake median 0.333 win-probability)
E1_PREDICTABILITY = FAIL   (best of 3 model families AUROC 0.37-0.47 at/below chance;
                            recall@20-30% budget 0-31% vs required >=70%;
                            false negatives hold 76-100% of total regret mass)
E1_COMPUTE_VALUE  = NOT_RUN (moot: no predictable gate exists to build the selective agent on;
                            killed by E1_FAIL_PREDICTABILITY per plan §15)
E1_NOVELTY        = AMBIGUOUS (structural concerns recorded; full review moot — track dead)

E2_SIGNAL             = PASS (48.5% of 200 reachable torpedo decisions change top-1 when
                              influence is added; consistent across 2 scenarios x 5 doctrines)
E2_LONG_HORIZON_VALUE = FAIL (real CRN continuations, 40 changed states x 5 reps:
                              hybrid vs direct mean diff +0.02, 10W/6L/24T;
                              S-01 exactly 0.000; no scenario reaches ~10% improvement)
E2_CAUSALITY          = FAIL (true influence ≈ shuffled influence: -0.01 mean diff, 5W/5L/30T;
                              shuffled-vs-direct +0.03 — ANY different action "helps" as much
                              as the influence-aware one)
E2_NOVELTY            = AMBIGUOUS (moot: no causal effect to write a paper about)

BEST_SUPPORTED_TRACK = NONE
SECONDARY_TRACK      = NONE
```

No banned vocabulary is needed: both tracks are dead on measured evidence.

## One-paragraph verdict for the PI

E1 found the exact phenomenon it needed (decision-criticality is sparse and
huge when present) and then died on the step that makes it an *agent*
method: nothing on the public board predicts which states are critical — the
best of logistic regression, gradient boosting and a small MLP is at or below
coin-flip, and the mistakes concentrate exactly the regret mass a selective
reasoner must not miss. E2 found that the planner's counterfactual influence
features change the chosen action in half the reachable torpedo decisions, and
then died on reality: in true simulator continuations the influence-aware
choice is worth +0.02 outcome over direct (10W/6L/24T, zero in S-01), and
shuffling the influence labels across candidates changes nothing (−0.01) — the
ranking disagreement was a heuristic artifact, not strategy. Per the plan's
stop rules this ends the hidden-commitment research line: **E1 = FAIL, E2 =
FAIL, BEST_SUPPORTED_TRACK = NONE**, and the recommended next step is the
plan's own §21 fallback — a fresh topic scan over the whole Iron Bottom Sound
system, not another excavation of torpedo/commitment mechanics.

## What was run (evidence map)

| test | data | result artifact |
|---|---|---|
| E1-T1 rho distribution | M1 G1 frozen 15-rep Q tables, 120 evaluable pairs (30 CI-passing) | `metrics/e1_t1_rho.json`, `figures/E1_rho_distribution.png` |
| E1-T2 criticality prediction | same pairs; features from allies' own observation only | `metrics/e1_t2_predict.json` |
| E2-T1 influence disagreement | 200 reachable torpedo decisions, 2 scenarios × 5 doctrine profiles, 42+34+42 real matches | `metrics/e2_t1_summary.json`, `e2_strong_cases/` (30) |
| E2-T2/T3 continuation + causality | 40 changed states × 3 arms × 5 CRN replicates | `metrics/e2_t2_rollout.json`, `metrics/e2_t2_states_rollout.csv` |

Budget: ≈ 800 match-equivalents of the ≤15,000 new-rollout budget; 0 paid LLM
calls; production engine untouched; all thresholds pre-registered in
`PRE_REGISTRATION.md` before any Stage-1 aggregate existed; both amendments
(E2 profile list, sampling quotas) recorded there pre-results.

## The three load-bearing numbers

1. **E1's cruel irony**: `rho` is real (16.7% of commitment-differing states
   carry a median 0.333 win-probability stake) but *invisible from the
   outside* — AUROC 0.47 means the public state and the critical states are
   indistinguishable to every cheap model tried. A selective-reasoning paper
   needs the gate to be learnable; here it is not, and the false negatives
   hold 76-100% of the regret.
2. **E2's null is symmetric**: true influence beats direct by +0.02; shuffled
   influence beats direct by +0.03. If the label carries no information
   beyond "pick a different torpedo plan sometimes", there is no causal
   strategic-influence effect in this window under scripted play.
3. **Both failures are regime-flavoured, not pipelining bugs** (controls and
   determinism checks all pass; see FAILURES doc). The M0/M1 pattern repeats:
   in scripted-play IBS, torpedo decisions are rarely pivotal and the game's
   own scoring machinery does not encode a exploitable long-horizon influence
   signal.
