# 01_MG2_LEGAL_FIRE_REPAIR — FAIL (3 of 4 conditions)

## F21 repaired: three fidelity defects in the fire meter

1. **mount double-counting** (the PI's F21): the old `measure_side()` summed
   over every (ship, target, mount) triple, so one mount bearing on three
   targets counted three times. Replaced by a legal allocation: each mount
   allocated at most once, one target per ship.
2. **modifier grouping**: the engine computes
   `attackers = #distinct ships firing at the target` (a concentration bonus)
   and `target_count = #distinct targets the attacker fires at` (a splitting
   penalty). The old meter assumed both were 1. Now resolved by greedy
   best-response iteration and the engine's exact `_gunnery_modifiers`.
3. **hit-table grouping**: the engine groups attacks by
   `(attacker, target, mount.kind)` — primary and secondary batteries are
   separate table lookups. The old meter summed all bearing mounts into one
   firepower total. Now grouped by kind.
4. **visibility**: `_mount_can_bear` alone is not sufficient; the validator
   also requires `_can_see`. Added (it had produced an invalid batch).

Every arm's batch now passes `validate_orders(_prepared=True)`.

## Repaired result (IBS-S-01 s1 t2)

| arm | own GF | own legal EH | enemy GF | enemy legal EH | net EH | longitudinal frac | batch |
|---|---|---|---|---|---|---|---|
| CROSS_T | 165 | 22.42 | 61 | 9.97 | **+12.44** | 0.44 | valid |
| PARALLEL | 165 | 16.17 | 61 | 8.19 | +7.97 | 0.89 | valid |

| condition (unchanged) | value | pass |
|---|---|---|
| CROSS own legal GF > enemy | 165 > 61 | yes |
| CROSS net legal EH > 0 | +12.44 | yes |
| enemy bow/stern fraction >= 50% | 0.44 | **no** |
| CROSS net >= 1.25x PARALLEL net | 12.44 / 7.97 = 1.56x | yes |

**MG2-R = FAIL**, on the raking-fire condition only.

## Diagnostic (not a rescue)

The CROSS_T arm steers each ship beam-on to its *own* bearing to the nearest
enemy; that posture does not place our ships **ahead of** the enemy column, so
the enemy presents its bow/stern to us in only 44% of pairs. The PARALLEL arm
(chase geometry) shows 0.89 — matching an enemy's course is what produces a
stern rake in this engine. A true T-cross needs our ships to reach a position
ahead of the enemy line, which is a *positioning* problem the current arm does
not solve. Per the PI's instruction the verdict stands at FAIL; the arm's
inability to occupy the raking position is itself evidence for the compiler
question (Stage B), not for the value question.
