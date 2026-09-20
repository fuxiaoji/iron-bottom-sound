# 06_MECHANISTIC_GOLD_GATE.md

```
MECHANISTIC_GOLD_GATE = FAIL   (3 of 5; required >= 4)
MG1 BROADSIDE        = PASS  (+93% common-distance expected hits)
MG2 CROSSING_THE_T   = PASS  (net exchange 1.68x the parallel arm; 64 longitudinal pairs)
MG3 RANGE_CONTROL    = PASS  (2.56 vs 0.94 expected hits across 2 hexes of range)
MG4 REAL_TORPEDO_CORRIDOR = FAIL (CASE_CONSTRUCTION_FAIL)
MG5 LOCAL_FORCE      = FAIL (TACTICAL_ASSUMPTION_NOT_SUPPORTED)

COMPILER_FIDELITY = NOT_TESTED (Stage B gated on >=4/5)
VALUE_REALIZATION = NOT_TESTED (Stage C gated on >=4/5)
PLATFORM_DIAGNOSIS = STILL NO_VERDICT, but see "the new fact" below
```

## The new fact this round establishes

The rule engine **does** price movement geometry steeply — three independent
rule-local measurements, each using only engine-native APIs at the
post-movement/pre-fire instant:

1. **MG1** (pure hold vs 60° oblique turn, same fleet): 3 mounts / 3.00
   expected hits broadside vs 1 mount / 1.56 narrow at common distance
   (**+92.9%**).
2. **MG2** (cross-T vs parallel): own usable GF 651 vs enemy 486, net
   expected exchange **+41.6 vs +24.7 (1.68x)**, 64 longitudinal-fire pairs
   against the bow-presenting column.
3. **MG3** (2-hex range difference for a BB): expected hits **2.56 vs
   0.94** — the range-modifier table is extremely steep.

So the original M2.1 question — "does the game itself have low leverage" —
is now answered **NO at rule level**: the rules create large, exact,
engine-native consequences for heading, aspect and range. The leverage
collapse measured in earlier rounds happens **after** the rules layer: in the
compiler, the continuation, or the value function. That is precisely the
decomposition this round was built to produce.

## Why MG4/MG5 failed

- **MG4 = CASE_CONSTRUCTION_FAIL.** Real TorpedoOrders were submitted and
  validated (launcher dedupe fixed, F17), but three different aiming schemes
  (current-intercept combos, corridor coverage of T+1 route hexes, deduped
  launcher spread) all produced arms IDENTICAL to 13 decimal places at T+1:
  the torpedoes launched at turn T do not constrain the victim's T+1 route
  set in this geometry — they either expire at turn end or their tracks miss
  every sampled route. Either the engine's torpedo persistence cannot express
  a multi-turn corridor from this range, or the corridor must be built from
  the T+1 tracks themselves. Not resolvable without deeper engine study;
  classified as construction failure of THIS case, not a rule bug.
- **MG5 = TACTICAL_ASSUMPTION_NOT_SUPPORTED.** "Local force superiority"
  requires the un-engaged enemy group to be OUT of the fight. At IBS gun
  ranges (8+ hexes effective) and the 6-hex cluster split, every own ship
  bears on SOMETHING in both arms: the concentrate arm actually scored WORSE
  expected-hit margin (56.6 vs 82.7) because steering toward one cluster
  degrades the other ships' arcs. The platform's engagement scale erases
  local superiority at this fleet spacing.

## What the PI should read together

- MG1/MG2/MG3 PASS: heading, aspect, and range have steep rule-native value.
- M2.1-R gold gate (previous round): those same geometries, converted to
  E0/E3 values, moved only 0.003-0.033 at T2 — and unmasking FLIPPED NEGATIVE
  against an adversarial opponent (exposure is symmetric).
- Conclusion the evidence supports: **rules rich, value realization poor.**
  If a future round wants to revive movement-leverage research, the target is
  the value-realization step (an evaluator that plays out the *consequences*
  of geometry over multiple turns), not the rule engine and not the
  platform's victory arithmetic.
