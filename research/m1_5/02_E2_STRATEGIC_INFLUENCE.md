# 02 — E2: Strategic Influence Planning

## Question
Do torpedo actions have value beyond immediate damage — forcing route changes,
speed loss, formation splits, loss of firing position — that a direct-only
planner misses?

## Field audit (current HEAD)
All nine fields exist in `CounterfactualResponse` (baseline_route,
threatened_route, forced_deviation, speed_loss, fire_position_loss,
crossing_t_loss, formation_split, local_force_ratio_gain, route_changed) per
`TorpedoTacticalOption`. The legacy profiles never exercise this machinery;
the sampled profiles are the five doctrine-bearing ones (pre-registered
amendment).

## T1 — ranking disagreement: PASS

200 reachable torpedo decisions (2 scenarios × 5 doctrines × 40), 42+34+42
matches for the three sampler runs. With the pre-registered Hybrid =
expected_hits + 1.0·influence-composite:

- Hybrid vs Direct top-1 change: **48.5%** (55.9% on non-degenerate direct
  rankings); per scenario 33%/30%; per doctrine 35-62.5%.
- Influence-only vs Direct: 40.0% (51.5% non-degenerate).
- 30 strong interpretable cases dumped (`e2_strong_cases/`).

## T2 — real continuation: FAIL

For 40 states where Hybrid != Direct (spread over scenarios/doctrines), the
deterministic match was replayed to the same state and each arm rolled out
with CRN (5 dice-stream replicates), scripted play after:

| comparison | mean outcome diff | W/L/T |
|---|---|---|
| Hybrid vs Direct | **+0.02** | 10/6/**24** |
| — IBS-S-01 | 0.000 (exactly) | 3 wins |
| — IBS-S-03 | +0.04 | 7 wins |
| Hybrid vs Shuffled | −0.01 | 5/5/30 |
| Shuffled vs Direct | +0.03 | 5/1/34 |

The gate (Hybrid > Direct in both scenarios at ~>=10% relative improvement)
fails in both. The +0.19 "relative improvement" ratio sometimes quoted for
hybrid-vs-direct is a small-denominator artifact; the raw paired diffs and
the 60% tie rate are the honest summary.

## T3 — causality: FAIL (kill)

True influence ≈ shuffled influence (−0.01, 5W/5L/30T), and shuffled-vs-direct
(+0.03) is as large as true-vs-direct (+0.02). The influence labels carry no
information beyond "sometimes pick a different torpedo plan": the T1
disagreement was a heuristic artifact. E2_FAIL_HEURISTIC_ONLY and
E2_FAIL_CAUSALITY both fire; the track stops.
