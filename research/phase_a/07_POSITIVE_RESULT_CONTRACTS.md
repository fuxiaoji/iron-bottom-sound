# 07_POSITIVE_RESULT_CONTRACTS.md

No track passed, so no contract is issued. Per plan §0 a contract accompanies only
a `SELECTED_MAINLINE != NONE`, and the PI owns that decision.

For reference, the *candidate* contracts the pre-registration implies, so the PI can
see what would have to hold before any of them is claimed:

| track | primary estimand | equal-budget baselines it must beat | independent tasks/seeds | falsifier | must NOT be claimed yet |
|---|---|---|---|---|---|
| A | normalised team return at a fixed total planning budget | Uniform-4/16/64, RandomAllocation, UncertaintyHeuristic | 2 VMAS tasks + 1 external family, 3 seeds | oracle-vs-best-fixed gap ≤ 8 % with CI covering 0 | "adaptive compute helps"; any comparison with unequal totals; hindsight-oracle-only results |
| B | boundary recall at fixed K queries | Random, Latin/stratified, generic uncertainty sampling | 2 tasks + external family, ≥2 query seeds | structured/random ≤ 1.8x with CI covering 1 | "multi-agent structure helps" unless structured beats the *generic active* baseline by ≥15 % |
| C | top-1/top-k attribution accuracy at ≤25 % of the exhaustive budget | Random, temporal binary search, agent-first | 2 tasks, held-out failures | best probe < 80 % of exhaustive accuracy at 25 % | "first" claims; using injection metadata; correlation/saliency as attribution |

Every row is conditional on data that do not yet exist in this execution window.
