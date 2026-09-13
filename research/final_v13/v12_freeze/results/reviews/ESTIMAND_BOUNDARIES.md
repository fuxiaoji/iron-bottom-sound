# Quantities that must not be conflated

1. v10 V_H-V_1: evaluation horizon changes with sealed-plan horizon. This is not commitment.
2. v11 C_h: Monte Carlo payoff of an algorithm that repeatedly solves a remaining open-loop game and executes h steps. It is not a feedback equilibrium value, even when each local open-loop game is solved exactly.
3. v12 exact block value: complete backward induction with equilibrium continuation at future observation epochs. This is a different decision rule from (2), and Grid-3 differs from Grid-5.
4. v12 FC/CF: perfect-recall extensive-form values with a hidden opponent plan suffix. Revealing the suffix defines a different game.
5. External-engine F/R arms: translated rule-legal heuristics, a different payoff scale/dynamics/observation model. Neither equality with (2) nor transfer of (3) is guaranteed.

Consequences: even if exact Grid-3 recovers the desired bilateral sign, it does not by itself show that solver bias caused the v11 reversals. Payoff bugs, action resolution and the equilibrium-versus-receding distinction all changed. A cell can receive a causal artifact label only under a matched ablation; otherwise mark UNRESOLVED or a narrower descriptive comparison.

The intended Grid-5/7 robustness statement must name the object actually computed. Open-loop DO bounds cannot certify an extensive-form feedback value. An approximation needs full extensive-form exploitability/duality bounds or remains a policy-level diagnostic. Likewise h=1 versus h=6 Monte Carlo results may be reported as a planner-cadence effect with numerical convergence checks, not relabeled a controlled error bound on V_CC-V_FF.
