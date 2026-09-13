# Audit execution clarification 02, 2026-09-13

No asymmetric discovery or held-out outcome has been run.

The cache audit targets reuse ACROSS LF histories/epochs/seeds, as described in requested plan section 1.1. `cache_mode=off` now means the shared payoff cache is neither read nor written; each immutable remaining-horizon matrix is assembled locally during a single DO solve. Locally materialized matrix columns/rows may be reused by that SAME solve, then discarded. This is explicitly not a claim of disabling every temporary matrix allocation or every numerical reuse. `exact_history` and `old_pose_key` additionally permit shared reuse. Full-state policy memoization is independently safe and separately declared in the controls harness.

Two literal no-reuse profiling processes were stopped before producing a complete episode: they recomputed unchanged matrix columns at every iteration and used several CPU-minutes without an output. Their logs are retained with aborted-profile filenames. This scheduling change does not change a payoff, policy, tolerance, sample, or gate. A direct no-cache scalar/vector history audit (100 actual histories, including independently recomputed payoffs) already verifies evaluator equivalence. New off-mode control runs compare full same-seed outputs to exact-history mode, and the test suite checks that the shared cache remains untouched.

Convergence sweep uses N=8 paired seeds for diagnostic C6 versus gap, all prescribed 4 tolerances x 5 caps x 3 geometries. Main symmetry inference retains N=200 and original seed/CI choices. A configuration with any failed epoch has no scientific C6 estimate; this missingness is explicit, not replaced by a partial-case mean.
