# E05 — dynamic engagement graph vs aggregate-force damage prediction

- matches: 120 ok / 0 failed (S-03 x80, S-01 x40); snapshots 600; samples 5862
- event crosscheck: 600/600 damage windows fully matched by event payloads (2535 vs 2535 hull points)
- samples with damage>0: 0.170; mean damage 0.432; max 13

## Main result (80/20 grouped-by-match split)

| model | OOS R2 | OOS MAE | AUC(damaged) |
|---|---|---|---|
| baseline (totals) | 0.0891 | 0.6380 | 0.8508 |
| full (baseline + graph) | 0.1221 | 0.6452 | 0.8794 |

- delta R2 (full - baseline): **+0.0330**  95% CI [+0.0069, +0.0561]
- relative MAE reduction: **-0.0114**  95% CI [-0.0365, +0.0145]
- delta AUC (damaged): **+0.0286**  95% CI [+0.0119, +0.0459]

- acceptance (delta R2 >= +0.05 OR MAE reduction >= 10%): **FAIL**
- Interpretation: the graph shape metrics add no material out-of-sample explanatory power beyond aggregate totals on this data — reported verbatim as a null result (plan permits downgrading to appendix).

## OOD transfer

| direction | model | R2 | MAE |
|---|---|---|---|
| train_s01_test_s03 | baseline | 0.0303 | 0.6316 |
| train_s01_test_s03 | full | -0.2163 | 0.4984 |
| train_s03_test_s01 | baseline | 0.0612 | 0.6929 |
| train_s03_test_s01 | full | -1.1145 | 1.6645 |

## Method

- Matches driven exclusively through legal TacticalCommander order batches adjudicated by the engine (profiles cycled over balanced/balanced, line/brawl, cautious/balanced).
- Snapshot at gunnery-freeze time (after MOVEMENT_RESOLUTION; S-01 turn 1 starts in GUNNERY per scenario rule, snapshot = setup layout).
- Directed edge i->j = sum over gun kinds of expected_gunnery_hits(summed can-bear firepower, distance, target speed), gated by _can_see.
- Node features: P_attack, P_reply, LFR=(P_attack+eps)/(P_reply+eps), Herfindahl concentration, attacker count, formation lambda2 (distance<=3, heading diff<=1), plus baseline totals (hull_frac, force_ratio, avg_enemy_dist).
- Outcome: hull points lost in the following GUNNERY + TORPEDO_EFFECTS phases. OLS (numpy lstsq), logistic ridge IRLS, Mann-Whitney AUC, paired bootstrap 95% CIs.

## Decisions

- D1 graph edges are gated by engine._can_see: gunnery validation rejects orders at unseen targets (night-battle visibility), so ungated expected fire could never convert into adjudicated shots.
- D2 per-kind firepower aggregation mirrors research/geometry/firepower_kernel.expected_hits_exact: sum can-bear, non-destroyed mount firepower per kind, then one engine.expected_gunnery_hits lookup per (kind, distance, target_speed).
- D3 baseline force_ratio = enemy-side remaining total hull points / own-side remaining total hull points (aggregate 'total strength'); avg_enemy_dist = mean distance to alive enemies.
- D4 Herfindahl H_j = sum_i (w_ij / P_attack)^2 with H=0 when P_attack=0 and H=1 with a single attacker (degenerate maximum concentration); 'at least 2 attackers' structure is carried by attacker_count.
- D5 lambda2 = second-smallest eigenvalue of the side's formation-graph Laplacian (adjacency: distance <= 3 AND circular heading difference <= 1 on the 6-direction compass); 0.0 for sides with fewer than 2 alive ships or a disconnected graph.
- D6 outcome window = hull points lost between the GUNNERY snapshot and the entry to FIRE_END (i.e. _resolve_gunnery + _resolve_torpedoes only); movement-phase damage (collision / torpedo contact) precedes the snapshot and is excluded by design.
- D7 P_attack is excluded from the full regression (collinear with LFR = P_attack / P_reply); it is kept in dataset.csv for reference.
- D8 statsmodels/sklearn are not installed: OLS uses numpy lstsq, logistic uses ridge IRLS (lambda=1e-6, 50 Newton steps), AUC uses the Mann-Whitney rank statistic.
- D9 train/test split is grouped by match (no samples of the same match on both sides), stratified per scenario at 80/20.
- D10 S-01 special rules (allies firepower halved, axis turn-1 gunnery ban) act through adjudication only; w_ij uses the raw engine hit-table function per plan, so S-01 realised damage is systematically scaled relative to its graph weights — a known, documented mismatch that also affects the OOD transfer numbers.
- D11 reinforcement / contact-setup phases are answered by TacticalCommander.choose_plan itself (inherits DeterministicCommander._reinforcements); no special-casing needed. S-03 has no reinforcement group; S-01 turn-4 axis reinforcements enter through the same legal path when the turn-3 roll triggers.
- D12 LFR smoothing constant eps = 0.05 (scale of a fraction of one expected hit) and LFR clipped to [0, 50]: ships whose side has no can-bear gun on any visible enemy give P_reply = 0 and an unclipped ratio would explode (observed max > 3e5 with eps = 1e-6 in S-01) and destabilise OLS standardisation. Clip affects 8.4% of smoke samples.
