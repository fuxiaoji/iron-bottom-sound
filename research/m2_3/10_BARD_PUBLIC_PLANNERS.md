# 10_BARD_PUBLIC_PLANNERS.md

Every planner is chosen **on the matched public set** and scored **on the true
hidden set** (identical convention for all, so none can exceed the full-state
ceiling); `CURRENT_ADAPTIVE` and `SIMPLE_PUBLIC_PROXY` are scored the same way.

| scenario | CURRENT_ADAPTIVE | SIMPLE_PUBLIC_PROXY | PUBLIC_SET_COVER_ROBUST | PUBLIC_BELIEF_EXPECTED | FULL_STATE_CEILING | best public / ceiling |
|---|---|---|---|---|---|---|
| IBS-S-01 | 0.000 | 0.002 | 0.000 | **0.080** | 0.130 | **0.611** |
| IBS-S-03 | 0.000 | 0.000 | 0.000 | 0.045 | 0.197 | 0.226 |
| IBS-S-EM-01 | 0.000 | 0.022 | 0.000 | 0.004 | 0.050 | 0.086 |

```
BARD_PUBLIC_RECOVERY = FAIL   (0.611 / 0.226 / 0.086 — one scenario clears 50%)
```

## Reading

- The deployed adaptive planner recovers **0.000** of the true hidden structure in
  every scenario: it fires (or abstains) without constraining the hidden routes.
- The naive straight-line proxy is also ≈0.
- A belief-aware planner that at least *represents* the matched hypothesis set
  recovers 61 % of the ceiling in S-01 and 23 % / 9 % elsewhere. So the ceiling is
  partly approachable, but not consistently and not in the scenarios where the
  effect is weakest.
- The ceiling itself is small (0.050–0.197 mean route reduction), because a single
  salvo can only cover so much of a 40-route set: this is the same ceiling
  limitation B1E recorded.

Note the first implementation of `PUBLIC_BELIEF_EXPECTED` reported its value **on
the matched set**, which made it appear to exceed the ceiling (0.336 vs 0.124) —
an impossible comparison that revealed the inconsistency (M23-F4). Both planners
now use the same convention.
