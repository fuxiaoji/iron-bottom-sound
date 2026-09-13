# Prospective v13.1 discovery implementation protocol

Fixed before v13 numerical outcomes are read. Discovery is exploratory; the separate confirmatory design will be frozen after discovery and before new held-out parameter runs. The two supplied documents are archived as requested study plans; mathematical definitions are checked rather than treated as facts.

## Estimand and numerical model

Use the v12 causal, undiscounted endpoint-trapezoid payoff, complete LF histories, three vessels at arc offsets 0/2/4, six substeps/turn, initial leader separation 16, CA-labelled frozen kernel and fixed kernel target-speed channel. T=6; normalized turns {-1,0,1} multiplied by 60 degrees. Opponent operating-speed ratio=1 (physical model speed 6); both range ratios=1. Focal ratios {.70,.85,1,1.15,1.30}, all three inherited geometries. This is forced operating speed, not selectable mobility capability.

For fixed opponent class kappa=F or C, F_B^F=V_FF-V_CF and F_B^C=V_FC-V_CC. All four values are calculated by complete finite backward induction (FF), complete matrix LP (CC), and perfect-recall sequence form (FC/CF). Full realization best responses supply numerical bounds; scientific cells require gap <=1e-6, feasibility <=1e-6 and flexibility non-negativity within 1e-6. Failures stop dependent conclusions, with no silent fallback.

Mirrors independently build the swapped physical-speed payoff matrix and solve the four structures, permuting turn signs for the parallel reflection. Verify A_mirror=-P A^T P^T within 1e-8 and V_XY=-V_mirror_YX within combined numerical bounds plus 1e-7. Mirrors do not add independent cases. Cache mode is complete terminal-matrix persistence indexed by full configuration and source hashes; no old-pose cache or receding DO is used.

Discovery curves retain all five speeds and all four adjacent-speed contrasts per geometry and fixed opponent class. No confirmatory pass is declared from these curves. The intended held-out contrasts are the outer (.75,1.25) and inner (.90,1.10) pairs, each with kappa F/C in each geometry: 12 endpoints. Their exact rules must still be frozen in CONFIRMATORY_DESIGN.md before evaluation.

## Required mathematical clarifications

1. Forced positive speed can make raw reachable correction R=d_before-min_reachable(d_after) negative: the current state need not be reachable at the next epoch. The requested R/(R+D+eps) is then not necessarily in [0,1]. Preserve signed R and its negative frequency, and define the bounded proxy using R_plus=max(R,0): Theta=R_plus/(R_plus+D+eps). This change is a disclosed correctness amendment, not an exclusion or positive-result adjustment.
2. A finite speed menu {.75*vmax,vmax} is generally NOT nested as vmax increases. A genuine capability check must use fixed absolute speed levels with lower-ceiling actions retained at higher ceilings. A small-horizon speed-control experiment will use this rule and label its scope separately from the forced-speed main grid.
3. Alpha*L_star can create an empty superlevel set if L_star<0. Preserve undefined/empty-set cases, report coverage, and never replace the threshold after inspecting outcomes.
4. Focal-versus-opponent policy labels stay fixed within every speed contrast. H2's payoff-premium identity is algebraically H1, not independent corroboration.

No v12 Monte Carlo audit is rerun. Only regressions required by the new experiment and any new speed-control/metric implementation are allowed. All v13 figures are DRAFT. Manuscript writing is outside the latest request, even if an experimental gate passes.
