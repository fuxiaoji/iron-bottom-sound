# 03_MG4_SPACETIME_CORRIDOR — PASS (RouteReduction 0.966)

## Frozen search (PRE_REGISTRATION_R21), executed

Scanning S-01/S-03/EM-01, seeds ascending. The engine's own
`torpedo_tactical_combos` offers only intercept-aimed options (2 identical
combos in the S-01 states), so the legal configuration space was enumerated
directly (launcher x launch MF x side x angle x setting = **288 configurations**
at the chosen state), each projected with the engine's own
`_project_torpedo_path`. Precondition 4 was evaluated **geometrically only**.

## Chosen case

- scenario/seed: IBS-S-01 seed 1, victim IBS-U-IJN-AOBA
- setting 2 (long-range, range 25) — the
  pre-registration's preferred multi-turn setting
- launched track: `TT-2-IBS-U-USN-FARENHOLT-TT1-1`, at T9,
  heading 6, range_remaining 21
- order validated by the engine: `valid = True`

## Result

| metric | value |
|---|---|
| total legal victim routes at T+1 | 29 |
| routes with space-time torpedo contact | **28** |
| safe routes | 1 |
| contact fraction | **0.966** (gate >= 0.25) |
| engine cross-validation | **29/29 agreement** |

Classification is **torpedo-only**: a route is unsafe iff the victim's
(MF, hex) trajectory meets the track's (MF, hex) trajectory at the same MF —
never hull damage. The engine's own `torpedo_contact` events agree with the
prediction on every single route.

## Two-arm RouteReduction

| arm | legal routes | torpedo-safe routes |
|---|---|---|
| torpedo corridor | 29 | **1** |
| no launch | 29 | 29 |

`RouteReduction = 0.966` (gate >= 0.25) — **PASS**.
Best-response identity also changes: in the torpedo arm the only safe route is
`['0']` (hold), against 29/29 free routes
without the launch.

**MG4-R = PASS.** A real, legal, long-range torpedo corridor collapses the
victim's safe route space from 29 routes to 1. The earlier "torpedoes cannot
force displacement" reading was a measurement artifact, exactly as the PI
suspected.
