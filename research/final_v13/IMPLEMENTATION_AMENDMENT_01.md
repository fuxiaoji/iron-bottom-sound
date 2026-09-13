# Implementation amendment 01: directional-sector boundary precision

Date: 2026-09-13. Trigger: a pre-specified mirror regression failed during the first confirmatory run, parallel geometry with focal speed ratio .75. The main run returned an explicit failure and did not produce a complete confirmatory gate.

## Evidence and diagnosis

The original and reflected independent payoff matrices differed in 9/531441 entries, with maximum difference 2.499809686895558. One CF value differed from its mirrored FC value by approximately .00469743, even though each LP's residual was small. Thus the fault was in the evaluated payoff matrix, not a justification to relax the LP or mirror tolerance.

Witness: original Blue plan [-60,0,60,60,-60,60], Red plan [-60,0,60,-60,-60,60], at epoch 5, leader/leader pair. Distance is .0196161860206, not zero. The exact reflection changes coordinates only at about 4e-14, but near-contact bearing evaluation amplifies that difference. One relative angle becomes -150.0000000001 degrees while the reflected angle is 150.0 degrees. The previous 10-decimal rounding was insufficient to make these mathematically boundary-equivalent cases select corresponding sectors. Stage contributions then jump at the piecewise directional boundary.

## Correctness change

The new v13-only payoff module snaps relative angles within 1e-8 degrees of the fixed sector/aspect boundaries {-150,-30,30,150} to that boundary, in BOTH scalar and vector code. Interior angles keep the prior treatment. This numerical completion of discontinuous boundaries is explicit; no skew projection, payoff symmetrization, result sign adjustment or averaged equilibrium is used. Mirror matrices are still built independently from the physical swapped game.

All pre-fix v13 numerical outputs, figures, analysis and changed source snapshots are archived under pre_boundary_amendment/. Recompute every v13 discovery, confirmation, capability and mechanism result with the corrected boundary rule. Compare old/new outcome changes in an audit table; the old outputs are not final scientific evidence. v12 source, results and frozen conclusions remain unchanged, with their previously stated tested-scope qualification.

## Protocol status

The primary contrasts, parameters, hypotheses, exclusions and gate thresholds in the already frozen design are unchanged. The original design file is not edited. This is a post-freeze implementation amendment triggered by an observed validation failure, so final reports must not call the study an untouched preregistered confirmation. Recomputations can run concurrently because the entire confirmatory design is already frozen and cannot adapt to recomputed discovery outcomes. The rerun source/hash manifest records this amendment before any amended numerical result is read.

Acceptance requires the exact offending trajectory to fail the old implementation and pass the corrected scalar/vector/reflection checks, all existing/new regressions to pass, and independently rebuilt complete mirrors for every scientific cell to meet the original tolerance. If these fail, stop and diagnose; do not enlarge tolerances again to accommodate outcome differences.
