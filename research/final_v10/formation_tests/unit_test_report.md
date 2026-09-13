# v10 Phase 1: leader-follower formation unit tests

**8/8 passed**

| # | test | result | metric |
|---|---|---|---|
| 1 | straight-line equivalence | PASS | max|LF - rigid_line_ahead| = 0.00e+00 (positions and headings) |
| 2 | arc-length spacing | PASS | max |chord - d| = 0.0034 hex (d = 2.0) |
| 3 | constant-curvature arc | PASS | chord 1.9966 vs 1.9955 hex (R = 8.59); heading spread 26.7 vs 26.7 deg, monotone = True |
| 4 | no lateral teleportation | PASS | max per-turn step = 7.200 hex <= v = 7.20 hex |
| 5 | heading-tangent consistency | PASS | max heading error = 0.00e+00 deg |
| 6 | rotation / translation equivariance | PASS | |dJ| rotation = 8.88e-16, translation-invariance = 0.00e+00 |
| 7 | formation order preserved | PASS | min arc-length gap = 2.000 hex > 0 |
| 8 | sub-step refinement | PASS | |dJ|/max(1,|J|) = 1.5% between n_sub = 6 and 12 (J = 21.591 vs 21.918) |