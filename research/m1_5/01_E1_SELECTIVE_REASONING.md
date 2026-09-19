# 01 — E1: Selective Opponent Reasoning / Strategic Irrelevance

## Question
Can an agent decide cheaply whether the opponent's hidden state deserves
expensive reasoning at this step? Formal object: rho(s) = min_a max_c [V_c −
Q_c(a)] over the commitments consistent with the agent's information.

## T1 — rho distribution: PASS

Recomputed from the frozen 15-replicate M1 G1 Q tables (120 evaluable main
pairs; each pair is an information state with two consistent commitments).

| value fn | low-rho | high-meaningful | high-rho stake median |
|---|---|---|---|
| outcome (±1 win) | 83.3% | 16.7% | **0.333** |
| damage_diff (hull fraction) | 90.0% | 10.0% | 0.045 |

Thresholds (rho_norm >= 0.10 AND rho_abs >= floor; floors 0.10 outcome /
0.02 damage) were pre-registered before any aggregate. The desired
"sparse but consequential" structure holds on both value functions and in
both scenarios. Scope: conditional on a live commitment difference; rho
computed over the pair's two commitments.

## T2 — criticality prediction: FAIL (kill)

Features: agent-visible only (enemy count/distances/spread, bearing, own
torpedo readiness, own damage, score margin, turn, hull totals, visible VP) —
no hidden commitment, no rollouts, no rho. Labels: high-meaningful rho
(13/120 positives; label noise on non-CI-passing pairs acknowledged).

5-fold CV, three model families:

| model | AUROC | AUPRC | recall@20% | recall@30% | FN regret mass@20% |
|---|---|---|---|---|---|
| Logistic regression | 0.459 | 0.145 | 15.4% | 30.8% | 88.1% |
| Gradient boosting | 0.367 | 0.123 | 0.0% | 23.1% | 100.0% |
| Small MLP | 0.469 | 0.170 | 15.4% | 15.4% | 87.6% |

Gate required AUROC >= 0.75 and budget-recall >= 70%. Measured: at/below
chance on every family, and the false negatives hold 76-100% of the total
regret mass — the exact catastrophic mode the plan flagged.

**Interpretation.** In IBS's torpedo window, whether a hidden-commitment
difference forces an action change is not readable from the public board: it
lives in the geometry between the (hidden) enemy route and the torpedo launch
lanes. Criticality is real but epistemically hidden. E1_FAIL_PREDICTABILITY
fires; per the plan's kill rules the track stops (T3's selective agent needs
a predictable gate to exist).

## T3 — not run (moot). Novelty — moot; structural concerns recorded in 03.
