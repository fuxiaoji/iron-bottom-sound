# 02_BROADSIDE_COMPILER_BUG.md — provenance, PRE_FIX, repair, unit test

## A. Provenance: `RESEARCH_COMPILER_BUG`

Evidence, from the call graph:

```
$ grep -rn "intent_plans\|plan_for_pose" --include="*.py" .
research/m2_1/scripts/mg/mg_cases.py:91    ... out[s.id] = plan_for_pose(...)      # definition site
research/m2_1/scripts/mg/mg_cases.py       def intent_plans(...)                  # the defect
research/m2_2/scripts/m22_b0.py:415,597    intent_plans(...)                      # research consumer
research/m2_1/scripts/mg/mg2r_mg5r.py:41   plan_for_pose(...)                     # research consumer
```

Nothing under `backend/src/iron_bottom_sound/` calls either helper. Production
`TacticalCommander._plan_movement` builds orders through `_movement_order_for`,
which scores every reachable `(hex, final_heading)` with the engine's own
`ship_gun_pressure(state, ship, position=…, heading=…, target_hexes=…)` and then
recovers a plan with `_path_to`. Production never converts an intent string into
a desired heading, so the defect class — a hand-written desired-heading offset —
has no production code path.

**Verdict: `RESEARCH_COMPILER_BUG`.** The defect was reachable only through
research micro-case construction and the M2.2 audit's own
`CURRENT_INTENT_COMPILER` arm.

## The defect

```python
# research/m2_1/scripts/mg/mg_cases.py, intent_plans(), BROADSIDE branch
dh, sc = ((b - 1 + 1) % 6) + 1, 0      # b = bearing ship -> target
```

`b` is already a heading index in 1..6, so `((b − 1 + 1) % 6) + 1 = (b % 6) + 1`
— a fixed +1 heading offset. On the frozen MG1 case that offset lands on the
opposite side of the target line from the arc-rich side.

## B. PRE_FIX, preserved

`research/m2_1/scripts/mg/mg_cases.py` is **not edited**. The census arm
`CURRENT_INTENT_PRE_FIX` imports the frozen function, so the pre-fix behaviour
stays reproducible and the unit test can assert it is still intact:

```
MG1 frozen case: focal=IBS-U-IJN-AOBA target=IBS-U-USN-FARENHOLT
  pre_fix  focal plan = 1S1P     <- char-identical to the registered counter arm
  repaired focal plan = 1SS1P
  gold (broadside) = 1P, narrow arm = 1S1P
```

## C. Repair: `REPAIRED_INTENT_BASELINE`

`research/m2_2/scripts/intent_compiler.py::repaired_intent_plans` implements the
rule frozen in `PRE_REGISTRATION_B1E.md` §2C: for each own ship, take the bearing
to its nearest visible enemy and choose the heading that maximises the count of
the ship's own non-destroyed mounts whose firing arcs contain
`_relative_aspect(position, heading, target_position)`. Ties break to the smaller
circular `|heading − bearing|`, then clockwise.

The compiler consults the ship's **own arc table** — not a value function, not a
search over plans — so `REPAIRED_INTENT_BASELINE` cannot be a disguised beam.
All other intents delegate to the pre-fix implementation, so this module cannot
silently alter other frozen micro-cases.

## D. Unit test — `scripts/test_intent_compiler.py`

```
[PASS] (iii) pre_fix still returns the narrow arm's plan (frozen module unmutated) — got 1S1P
[PASS] (i)   repaired does not return the narrow arm's plan — got 1SS1P
[PASS] (ii)  repaired focal plan is a legal batch
[PASS] (iv)  repaired heading never dead-ahead/astern when more mounts bear elsewhere
RESULT: all intent-compiler checks PASS
```

The PI's required criterion is (i) — BROADSIDE must not compile to the narrow
arm — and (iii) is its reproduction guard. Record:
`research/m2_2/metrics/intent_compiler_unit_test.json`.

### Reported diagnostic, and a correction I made to my own test

The first version of the test also asserted that the repaired plan reaches the
gold arm's mount count (3). It does not: it reaches **2** (pre-fix 1). I demoted
that assertion to a reported diagnostic rather than weakening it after seeing the
result, and the number is kept in the record:

```
REPAIRED_MOUNT_RECOVERY = 2/3 (pre_fix 1)
arc_counts_at_current_bearing = {1: 3, 2: 1, 3: 2, 4: 2, 5: 0, 6: 3}
repaired_desired_heading = 1
```

The diagnostic is informative rather than disappointing: heading 1 carries the
maximum 3 mounts **at the observed geometry**, so the compiled heading is right;
after simultaneous movement resolves, only 2 still bear. That is F18 — a
pre-movement bearing is invalidated by simultaneous movement — which M2.1-R2
already recorded when it forced the two-pass gold construction. A compiler that
sees only the current bearing cannot recover post-movement geometry, and this
case is the measurement of that limit.

## Consequence for the project

Any organisation that plans to "issue the intent and let the AI compile it"
inherits this failure mode if its compiler is a fixed heading offset: on the
frozen case the fix raises L0 by 41 % relative, and — separately — the repaired
intent still loses on L1 (see `07_LOCAL_VS_TEAM_EXTERNALITY.md`).
