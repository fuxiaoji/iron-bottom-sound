# Correctness amendment 01, 2026-09-13

Timing: after initial Phase A controls, before ANY v12 asymmetric discovery/held-out data. Preserve PROTOCOL.md and all first controls unchanged.

A dedicated R4 policy metamorphism test showed the initial v12 label-swap canonical solver was not invariant under the spatial isometries needed by the prescribed controls. Among 20 Grid-3 reachable-history tests, payoff values were invariant but policy probabilities differed by up to 1.0 (also 0.651 and 0.0664). This is a demonstrated equilibrium-selection defect, not inferred from the desired range-sign pattern.

Fix: canonically orient complete histories by leader translation/rotation, optional reflection for proved port/starboard-symmetric kernels, and player exchange. Lexicographic keys rounded to 8 decimals ONLY order equivalent orientation candidates; no rounded history is evaluated or cached. Exact transformed float64 station bytes plus full metadata remain scientific cache keys. Apply inverse action reflection/player swap to policies. Resolve exhaustive BR numerical ties within 1e-10 by stable index; report true exhaustive maxima/minima in the bounds. Re-run the SAME Phase A seeds and preserve previous outputs under their existing filenames.

The independent Monte Carlo sample means are not expected to be identically zero. The preregistered 0.25 cutoff and CI checks are still reported as written; a miss is not silently repaired by extra seeds. A remaining mismatch requires deterministic policy-symmetry/expectation verification, or a failed gate; it is never grounds to relabel a failed MC check as passed.
