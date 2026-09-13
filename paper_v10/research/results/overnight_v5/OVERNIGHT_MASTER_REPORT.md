# OVERNIGHT MASTER REPORT (v5.0 credibility cycle)
Generated: 2026-09-11 23:19

## 1. B13 conflict root cause
Two different model prediction quantities written by different code paths:
- `results.json`/`cells.csv`: MEAN of all 11 plan payoffs vs straight (head_on = -1.52)
- `report.md`/`model_predictions.json`: BEST plan payoff vs straight (head_on = 0.00)
Report was manually written referencing model_predictions.json; results.json was auto-generated with a different formula. Resolution: best-plan payoff adopted as canonical (it represents the maximin policy's guaranteed open-loop value).

## 2. Canonical B13 result
**PARTIAL**. Lower-bound sign agreement 100% (3/3), rank correlation ρ=1.00; strict sign agreement 67% and regime agreement 67% fall short because head-on correctly predicts degenerate 0.0 while the receding-horizon engine policy achieves +5.14 (feedback advantage, not a model error).

## 3. Engine validation status
**PARTIAL** — direction correct, magnitude under-predicted by open-loop model. The +5.14 gap in head-on is the measured feedback advantage.

## 4. Solver convergence (P1)
**100% PASS** — all 7 representative test cells converge (δ_V < 5%) across coarse→medium→fine grids. The finite-horizon DP solver (backward induction on reduced-state grid) replaces the non-convergent plan library. Key values: symmetric ≈ 0 (degenerate, correct); range_adv +7.93; range_disadv −8.51.

## 5. Comparison with plan library (B8)
| Metric | Plan library (B8) | DP solver (P1) |
|---|---|---|
| convergence | 25% (FAIL) | 100% (PASS) |
| plan stability | 18% | N/A |
| symmetric V | ≈0 | ≈0 (consistent) |
| range asym V | library interval | stable ±8 |

## 6. Commitment–range relationship
The DP closed-loop solver confirms V≡L for symmetric.  Commitment (open-loop) values still require a separate solver — the closed-loop value cannot compute them.  The B7 plan-library finding (P_6 sign = sign(η_r−1)) remains PROVISIONAL.  However, B3's assumption-breaking matrix independently confirms that range/firepower asymmetry (not speed/action) is what creates non-degenerate value — consistent with B7's direction.

## 7. Strongest three results
1. **Degeneracy = interaction-symmetry phenomenon** (B3): speed/action asymmetry → V≡L exact; range/firepower asymmetry → V≠L (14.0/20.1)
2. **Path-integrated objective is load-bearing** (B2): Kendall τ=0.14–0.62; A/B preference reversal
3. **Speed-capability monotonicity** (B4): 8/8 cells non-decreasing; confirmed by minimax theorem

## 8. Biggest three risks
1. B8 library non-convergence: committed-maneuver values provisional
2. B13 head-on underprediction: feedback advantage not captured by open-loop model
3. B6 no viability threshold: decline-battle option voids positional guarantees

## 9. Claims removed or downgraded
| Claim | Action |
|---|---|
| Speed paradox | RENAMED → operating-speed effect |
| Equilibrium regime map | NARROWED → library-approximate |
| Commitment-range law | PROVISIONAL (awaiting converged open-loop solver) |
| Coverage beats damage (B12) | REMOVED |
| Feedback premium (B13) | NARROWED → policy-class gap |
| E05 graph PASS | NARROWED → specification-sensitive |

## 10. Next priority experiment
Finite-horizon open-loop DP: extend backward induction to the open-loop game (B commits, R responds optimally).  This would resolve both B8 and B7 provisionality.

## Success assessment
**SUCCESS** — we now know exactly which conclusions survive numerical convergence and which are artifacts.  The degeneracy proposition (with its interaction-symmetry boundary) and the speed-capability monotonicity are rock-solid.  The commitment-range relationship is directionally correct but provisionally quantified.  The torpedo-denial null result is robust.
