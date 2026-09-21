# PRE_REGISTRATION_R21.md — M2.1-R2.1 repair thresholds and search rules

Frozen before any repaired measurement. Frozen cases (not re-run, not
re-tuned): **MG1_BROADSIDE = VALID_PASS**, **MG3_RANGE_CONTROL = VALID_PASS**.

Total gate unchanged: `MECHANISTIC_GOLD_GATE = PASS iff passes >= 4 of 5`.

## F21 (the defect being repaired)

`measure_side()` accumulated `usable_gf` and `expected_hits` over every
(ship, target, mount) triple, so one mount bearing on three visible targets
was counted three times. Neither side's numbers were legal gunnery
allocations. MG2 and MG5 results from M2.1-R2 are void.

## Repaired fire measurement (MG2-R, MG5-R)

Rule: **each mount is allocated at most once per turn.**

Per shooter, enumerate legal per-ship allocations over its gun mounts:
each mount → at most one target it can bear on (engine `_mount_can_bear`),
mounts not fired/destroyed. For each allocation compute the engine-native
expected hits (D66 expectation through `d66_adjust` + `hit_count` with
`_gunnery_modifiers` at the arm's post-movement geometry).

```
BestAllocation(ship)  = argmax over legal allocations of expected_hits
TeamEH(side)          = sum over ships of max(0, BestAllocation(ship).eh)
UsableGF(side)        = sum of firepower of mounts used in BestAllocation
```

Then materialize the chosen allocations as a real `GunneryOrder` batch
(one order per shooter, `mounts=[GunMountOrder(mount_id, target_id)…]`),
submit it, and require `validate_orders(..., _prepared=True)` to pass.

Reported per case: selected target per ship, selected mounts, usable GF
counted once, expected hits, target aspect, bow/stern selected-target
fraction, batch validation result.

**MG2-R gate (unchanged):** CROSS own legal UsableGF > enemy legal
UsableGF; CROSS net legal expected exchange > 0; enemy bow/stern
selected-target fraction >= 50%; CROSS net exchange >= 1.25 x PARALLEL net
exchange. If repaired FAIL → MG2 = FAIL, no case hunting.

**MG5-R gate (unchanged):** CONCENTRATE hit margin >= 1.25 x DISPERSE, or
CONCENTRATE own active firing ships > DISPERSE. If DISPERSE >= CONCENTRATE
after repair → accept MG5 = TACTICAL_ASSUMPTION_NOT_SUPPORTED, no scenario
hunting.

Both re-use their M2.1-R2 states (S-01 s1 t2 for MG2; EM-01 s1 t3 for MG5) —
no new state search, so no selection freedom enters.

## MG4-R: torpedo persistence probe (must pass first)

From a real TORPEDO_PLANNING state, launch one real validated `TorpedoOrder`,
advance to the next `MOVEMENT_PLANNING`, and assert on the surviving track:

- `track` still in `state.torpedo_tracks`
- `range_remaining > 0`
- `distance_travelled` increased since launch
- record: id, position, heading, `range_remaining`, `speed_cycle`,
  next-turn allowance `speed_cycle[(turn − launched_turn) % 3]`,
  and visibility to the victim side (`observe(victim).torpedo_tracks` —
  standard rules have `blind_torpedoes=False`, so tracks are public).

If persistence fails, MG4-R stops with `CASE_CONSTRUCTION_FAIL`.

## MG4-R: state search rule (frozen BEFORE looking at any RouteReduction)

Scan replay-derived TORPEDO_PLANNING states in a fixed order
(scenarios S-01, S-03, EM-01; seeds 1..8 ascending; the first
torpedo-capable own ship in roster order; the nearest enemy as victim).
Select the FIRST state satisfying ALL preconditions:

1. a real legal torpedo launch validates (launcher loaded, not blocked);
2. after advancing one turn, >= 1 track survives with `range_remaining > 0`;
3. the victim has >= 10 legal movement routes at T+1;
4. at least one legal launch setting/angle yields a track whose space-time
   path can intercept >= 2 of the victim's T+1 routes.

Precondition 4 is evaluated **geometrically only** (space-time intersection),
never on RouteReduction. Ties within a state are broken by the engine's own
combo ordering (deterministic).

## MG4-R: corridor measurement

At T+1 `MOVEMENT_PLANNING`, for each victim legal route (movement plan):

- **Space-time prediction**: victim trajectory = [(MF, hex)…] from
  `engine.movement_trajectory`; torpedo trajectory = [(MF, hex)…] for the
  T+1 allowance from the same rule machinery. A route is
  **TORPEDO_UNSAFE** iff some MF has the same hex in both trajectories.
- **Engine cross-validation**: apply the route, resolve T+1 movement, and
  read `torpedo_contact` events / `track.contact_ship_ids` for the test
  track. Classification uses **torpedo contact only** — never hull damage.
- The two classifications must agree on every sampled route (>= 12 routes
  cross-validated); any disagreement is reported as a metric bug, and the
  engine's verdict wins.

Reported: total legal routes, contact routes, safe routes, contact fraction,
`route_id → first contact MF`, and per-route `BR` (the engine's own
best-route choice is not defined, so "best response" is reported as the
route minimizing torpedo risk then maximizing gun opportunity).

**MG4-R gate (unchanged):**
`RouteReduction = 1 − safe_routes(torpedo) / safe_routes(no-torpedo) >= 0.25`
AND (the best-response route identity changes between arms OR the
best-response route has positive torpedo contact in the torpedo arm).

If correctly constructed and still FAIL → MG4 = FAIL, no rescue.
