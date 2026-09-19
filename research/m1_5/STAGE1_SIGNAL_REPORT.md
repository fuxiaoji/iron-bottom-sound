# STAGE1_SIGNAL_REPORT.md — M1.5 Stage 1 (E1-T1 + E2-T1)

Thresholds were pre-registered in `PRE_REGISTRATION.md` before any Stage-1
aggregate was computed. Two amendments are recorded there, both made before
results existed: the E2 profile list (legacy profiles never exercise the
counterfactual machinery at HEAD) and the per-scenario/per-profile sampling
quotas (mechanics fixes, applied before reading any gate number).

## E1_SIGNAL = PASS

**Population**: the 120 evaluable main pairs from M1 G1's frozen 15-replicate
analysis; each pair is an information state with two consistent hidden
commitments, and `rho(s) = min_a max_x [V_x − Q_x(a)]` is recomputed from the
stored Q tables. Primary gate population: the 30 CI-passing states.

| value fn | low-rho | high-meaningful-rho | high-rho stake median | gate |
|---|---|---|---|---|
| outcome | 83.3% | **16.7%** | **0.333** (33 pp of win probability) | **PASS** |
| damage_diff | 90.0% | **10.0%** | 0.045 (≥ 0.02 floor) | **PASS** |

All three pre-registered conditions hold on both value functions:

1. ≥50% of states low-rho (83%/90%);
2. ≥10% of states high-rho with meaningful absolute regret (17%/10%);
3. high-rho states are NOT tiny-stake artifacts (outcome high-rho states have
   median stake 0.333 — when the decision matters, a third of the win
   probability is on the table).

Scenario conditioning (CI-passing): S-01 outcome 33% high-rho / S-03 6%;
S-01 damage 8% / S-03 11% — the sparse-but-consequential structure appears in
both scenarios, with scenario-dependent rates.

Declared scope limits: the population conditions on an existing hidden-
commitment difference (the unconditional base rate of rho over all IBS states
is lower); rho is computed over TWO consistent commitments per state (the G1
pair design), not the full commitment posterior.

## E2_SIGNAL = PASS

**Data**: 200 reachable torpedo-planning decisions — 2 scenarios (IBS-S-01,
IBS-S-03; 100 each) × 5 doctrine profiles (adaptive, direct_attack,
area_denial, break_crossing_t, crossfire; 40 each) — from 42 real matches
(rollout ledger: 42 of ≤15,000). All nine influence fields exist at HEAD in
`CounterfactualResponse`; nothing was invented.

| scorer comparison | top-1 change rate (all) | non-degenerate direct ranking |
|---|---|---|
| Hybrid vs Direct-only (λ=1.0, pre-registered) | **48.5%** | **55.9%** (n=143) |
| Influence-only vs Direct-only | 40.0% | 51.5% |
| median rank correlation direct↔hybrid | — | 0.799 |

Per-scenario: S-01 33.0%, S-03 30.0%. Per-profile: 35.0%–62.5%, no doctrine
below the 20% gate.

Gate: ≥20% of states change top-1 when influence is added — measured 48.5%,
**PASS**; 30 strong interpretable cases dumped with full option tables
(direct score, influence composite, all six counterfactual fields, marked
DIRECT/HYBRID winners) in `e2_strong_cases/`.

**Stage-1 caveat carried forward to E2-T2**: a ranking change is a heuristic-
level signal only. Whether the influence-aware choice is actually BETTER in
real continuations is exactly what E2-T2 tests; if rollouts disagree,
`E2_FAIL_HEURISTIC_ONLY` fires and E2 dies despite this PASS.

## Decision per the plan

Both tracks PASS Stage 1 → proceed to E1-T2 (criticality prediction), E1-T3
(exact-lab selective gate), E2-T2 (counterfactual continuation), E2-T3
(causal ablation). Neither track is stopped; no threshold was changed after
seeing results.

Artifacts: `metrics/e1_t1_rho.json`, `metrics/e1_t1_rho_pairs.csv`,
`metrics/e2_t1_summary.json`, `metrics/e2_t1_rows.csv`,
`metrics/e2_t1_decisions.json`, `e2_strong_cases/` (31 files),
`figures/E1_rho_distribution.png`, `figures/E2_influence_disagreement.png`.
