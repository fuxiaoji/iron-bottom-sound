# Frozen diagnostic mechanism protocol — DRAFT, not a mediation identification design

Fixed before any v13 mechanism field or tracking result is calculated. All choices below apply unchanged to discovery and held-out speeds.

## Probes and conditioning

For each geometry and focal operating speed, execute 32 deterministic seeded probe episodes, T=6. A NumPy PCG64 generator seeded 2026091300+probe_id supplies independent uniform turn indices from {-60,0,60} for the two players. The SAME focal and opponent action sequences are used across all focal speeds and geometries. The opponent remains at operating-speed ratio 1. These are standardized kinematic probes, not sampled equilibrium policies; no causal mediation of equilibrium value is claimed. Mechanism scores are shared across the two opponent-policy classes and cannot be counted twice as independent replicates.

## Relative-state domain and distance

The kernel's fixed effective range ceiling is 24 grid-length units. Use D={(x,y,psi): x,y in {-24,-22,...,24}, 1 <= sqrt(x²+y²) <=24, psi in {0,30,...,330} degrees}. Domain and resolution are not outcome-tuned. The coordinate frame translates with the opponent leader but keeps world-axis orientation fixed. Drift therefore measures changes due to opponent heading/formation shape, not its translational motion. Actual distances before and after correction are both evaluated relative to the NEXT opponent leader location.

Embed z as (x,y,4*cos(psi),4*sin(psi)); use Euclidean distance in this embedding. The angular length scale 4 is the fixed three-ship formation length. This is a periodic chord metric with explicit length units. Report out-of-domain actual states; do not exclude them. Its interpretation is a reduced relative-state proxy, not a metric over the full LF history.

## Favorable sets

At each epoch t, freeze the focal formation's actual current shape and all its heading offsets relative to its leader. Translate and rotate this entire shape to every z in D, retaining its bending. Evaluate the unchanged pairwise directional kernel against the actual opponent shape at t and t+1, in the corresponding translated frames. Keeping the focal template fixed within this two-field comparison isolates opponent shape/heading changes in the field drift. Across focal speeds the actual focal shape can differ; report this limitation.

G_alpha={z:L(z)>=alpha*max_D L}. Primary alpha=.90, robustness alpha=.80. Empty sets or nonpositive maxima are flagged and remain missing for drift/Theta summaries, with all counts reported. No replacement threshold, argmax selection, smoothing, or outcome-driven domain adjustment is allowed.

Compute directed median nearest-set drift, embedded-centroid drift, symmetric Hausdorff distance, and absolute wrapped opponent leader heading change. A representative field illustration always uses head_on, probe 0, epoch 0 (unless undefined, in which case display the missing field); it is not selected for visual strength.

## Reachability and tracking

Extend the current complete focal LF state by each of the three legal one-turn controls at its prescribed speed, while using the same already specified next opponent state. R_raw=d(current state,G_next)-min_a d(next focal state under a,G_next). Store d_before, d_after_min and all R_raw, including negative values. Define R_plus=max(R_raw,0) and Theta=R_plus/(R_plus+D+1e-9). Also report the raw ratio R_raw/(D+1e-9), the nonnegative ratio R_plus/(D+1e-9), centroid/Hausdorff versions, zero-drift frequency, negative-correction frequency and alpha=.80 sensitivity. Theta is a bounded correction-opportunity score; a zero raw correction with zero drift has Theta=0 by definition and must not be described as poor realized tracking.

Per-episode score is the median over its defined epochs; per-cell score is the median of the 32 episode scores. Undefined counts and between-probe distributions are retained. This aggregation is frozen and is not a Monte Carlo equilibrium estimate.

## Analyses

Discovery: F^F and F^C versus median Theta, separately and pooled, plus all adjacent-speed M and DeltaTheta. Held-out: outer (.75,1.25) and inner (.90,1.10) pairs in all three geometries and both fixed opponent classes. Report Spearman(M,DeltaTheta), stratified scatter, and least squares M ~ intercept + DeltaTheta + geometry indicators + opponent-class indicator + contrast indicator. Report coefficient, design rank, residuals and descriptive R²; no ML, causal mediation claim, or population p-value. Also report each opponent class separately because pooled scores share probe outcomes. The planned strong mechanism criterion is pooled rho>0.6, with no negative association in either fixed opponent class, and >=95% defined probe epochs. A failed mechanism blocks a strong Q1 classification and is not repaired by trying other metrics.

## Optional true-capability scope fixed prospectively

Implement a small-horizon check with per-turn absolute speed menus: low ceiling 1.0 permits {.75,1.0}, high ceiling 1.3 permits {.75,1.0,1.3}; normalized turn menu remains {-1,0,1}. Opponent speed stays fixed at 1.0, both ranges=1, T=4, three geometries and both opponent classes. Initial prehistory uses baseline speed for BOTH ceilings, so initial physical state is identical and low-ceiling policies embed exactly. This six-interaction check is a separate limited-horizon diagnostic, not a substitute for the T=6 forced-speed confirmatory set and not six extra confirmatory successes.
