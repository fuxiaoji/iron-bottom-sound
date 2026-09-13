# v13.1 confirmatory design — frozen before held-out evaluation

Date: 2026-09-13. Local prospective freeze, not an external preregistration. Git baseline fc77a65e970e92cca429e6c87498b0c68a70bf1e; experimental branch codex/v13-1-mobility-flexibility. Uncommitted experimental source and input hashes are recorded in FREEZE.json. Discovery has completed and is explicitly exploratory. No held-out value or mechanism field has been evaluated when this document is frozen.

## Hypotheses and estimands

H1: for a fixed Red policy class kappa and fixed Red operating speed, increasing Blue's operating speed increases Blue's own adaptation value. F_B^F(v)=V_FF(v)-V_CF(v); F_B^C(v)=V_FC(v)-V_CC(v). M^kappa=F_B^kappa(v_H)-F_B^kappa(v_L). H2's mobility-premium identity is a restatement of H1 and supplies no additional endpoint. The primary numerical model uses forced operating speed and cannot by itself establish a capability theorem.

Every high/low pair fixes opponent speed ratio 1.0 (model speed 6), opponent policy class, both range ratios 1.0, initial geometry, T=6, LF representation, three vessels/spacing 2, six substeps, action grid {-1,0,1} multiplied by 60 degrees, fixed kernel target-speed channel, undiscounted causal trapezoid payoff, and the public executed-history/hidden-current-and-suffix observation law.

## Exact twelve primary comparisons

| IDs | Geometry | Low/high ratios | Fixed opponent classes |
|---|---|---|---|
| H-outer-F, H-outer-C | head_on | .75 / 1.25 | F, C separately |
| H-inner-F, H-inner-C | head_on | .90 / 1.10 | F, C separately |
| P-outer-F, P-outer-C | parallel | .75 / 1.25 | F, C separately |
| P-inner-F, P-inner-C | parallel | .90 / 1.10 | F, C separately |
| X-outer-F, X-outer-C | crossing | .75 / 1.25 | F, C separately |
| X-inner-F, X-inner-C | crossing | .90 / 1.10 | F, C separately |

There are twelve endpoints built from twelve physical parameter cells and two policy contrasts per speed pair. Opponent-class endpoints share physical games; the twelve are not iid population samples. Independent Red-focal mirrors validate exchange but are not extra primary endpoints. No optional speed/range stress grid is used.

## Solver, uncertainty, exclusions and reversals

FF: complete finite backward induction. CC: complete normal-form matrix LP. FC/CF: full perfect-recall sequence-form LP and independent full realization best responses. Grid-3, T=6 has 531441 terminal history pairs per physical cell. Require full saddle gap <=1e-6 and feasibility residual <=1e-6; allow mirrored payoff discrepancy <=1e-8 and value discrepancies <= summed numerical budgets +1e-7. Record every status, bound and failure. Never use an old pose cache or a receding-open-loop bound for an extensive-form value.

For value intervals [L_X,U_X], construct F and M intervals by interval subtraction, retaining dependence conservatively without pretending these are confidence intervals. A positive endpoint requires M_LB>1e-5 and |M|>100 times its numerical interval width. A resolved reversal requires M_UB < -1e-5 with the same separation rule. A strong reversal additionally has M_UB < -.1 in the fixed payoff units. Values within the numerical threshold are unresolved and do not count as support. All twelve stay in the denominator; failed cells remain missing with reasons and block a successful gate. No outlier removal, missing-cell imputation, alternate contrast choice, or post hoc sign relabeling is permitted.

## Mechanism endpoints

Use MECHANISM_PROTOCOL.md unchanged: alpha=.9 primary, .8 sensitivity; the same bounded relative-state domain, fixed periodic distance and 32 paired standardized probe episodes. The primary comparison is DeltaTheta=Theta(v_H)-Theta(v_L) paired with the same M. Report Spearman separately by fixed opponent class and pooled, stratified plots and geometry/class/contrast fixed-effects least squares. Because two M endpoints share each DeltaTheta, pooled correlations are descriptive and do not imply twelve independent mechanism replicates or causal mediation.

Strong mechanism support: pooled rho(M,DeltaTheta)>.6; neither class-specific rho is negative; >=95% of probe epochs have defined favorable sets. Conditional mechanism support requires pooled rho>0, neither class-specific rho negative, and the same coverage. Also report the fraction with DeltaTheta>0: a positive M/DeltaTheta correlation when both decrease does not establish the proposed speed -> higher tracking -> higher adaptation chain. The chain additionally requires DeltaTheta>0 in at least five of the six physical speed-pair comparisons. Failure of this directional condition means the stated tracking mechanism is unsupported even if the correlation is positive.

## Gate and dependent experiments

Q1-STRONG candidate requires >=10/12 positive endpoints, <=1 strong reversal, positive support in all three geometries, at least one opponent class strongly consistent and the other not systematically reversed (>=4/6 resolved negative counts as systematic), strong mechanism support including the directional chain, passing regressions, and numerical error much smaller than effects. It is not a final Q1-STRONG gate until required refinement checks pass.

Q1-CONDITIONAL candidate requires 8-9/12 positives, fewer than two strong reversals, conditional mechanism support including the directional chain, and no systematic reversal within an opponent class. Geometry concentration is reported; it does not override the hard <=7/12 failure rule.

FAIL: <=7/12 support, >=2 strong reversals, unsupported tracking mechanism, unresolved solver validity, or failed subsequent refinement. On FAIL, stop experiment expansion and preserve negative evidence. Do not rescue the result using the optional T=4 capability experiment, which is a separately scoped six-interaction diagnostic with a genuinely nested speed menu.

Only eligible candidates advance to Grid-5 all twelve comparisons; then Grid-7 six anchors (three geometries × the outer contrast × each opponent class); the SAME six anchors at turn-bound ratios {.8,1,1.2}, T={4,6,8}, and rigid formation. No anchor is selected by observed effect magnitude. Refinement values require extensive-form exploitability/duality bounds, not fixed-iteration heuristics. Multiple resolved sign reversals or solver uncertainty comparable to the effect fails refinement. Optional capability results cannot be pooled with the primary count and do not make a T=6 forced-speed result into a general capability theorem.

The gate names describe this project's research decision, not certification of CAS journal rank or acceptance. The user's latest request stops before manuscript writing even if a candidate ultimately passes. No title, abstract, contribution list, manuscript narrative, submission or external message is authorized in this phase.
