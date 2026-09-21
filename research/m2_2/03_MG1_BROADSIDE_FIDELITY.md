# 03_MG1_BROADSIDE_FIDELITY.md

Case: `IBS-S-01` seed 5, turn 2, MOVEMENT_PLANNING, side AXIS, focal ship
selected exactly as in M2.1-R2.1 (first ship by VP with distinct
broadside/narrow plans against the post-movement bearing to its nearest enemy).
Gold plan `1P`, counter arm `1S1P`, deployed policy plan `1P1P1P1P`.

**Reproduction of the frozen case: 7 of 7 invariants exact** (post_rel 1 vs 5,
distance 4 vs 3, bearing mounts 3 vs 1, common-distance expected hits +92.9 %,
against `research/m2_1/metrics/mg1_broadside.json`).

## Primary metric (frozen): fleet margin — excluded

`M_broad = EH_own_legal(s') - EH_enemy_legal(s')`, LEGAL_FIRE_HEURISTIC.

| method | M (EH) |
|---|---|
| MANUAL_GOLD | **-12.167** |
| registered counter arm | -12.361 |
| RANDOM_LEGAL mean (8 draws) | **-6.323** |
| RANDOM_LEGAL max | -3.583 |
| CURRENT_POLICY | -5.472 |
| CURRENT_INTENT_COMPILER | -14.361 |
| BEAM_SEARCH_COMPILER | **+5.472** |

Gold gap = **-5.844** -> non-positive denominator -> `GOLD_GAP_NONPOSITIVE`,
excluded from the ratio by the pre-registration's own sentence. The hand-built
broadside is worse than the *mean* random legal plan at fleet scale, while the
beam's joint plan is 10.94 EH better than the deployed policy.

## Supplementary panel: pair margin — COMPUTABLE, and the verdict flips

Same frozen formula, restricted to the case's own pair (focal vs its recorded
target), lambda = 1.

| method | M (pair EH margin) | fidelity |
|---|---|---|
| MANUAL_GOLD | +1.889 | — (reference) |
| registered counter arm | +0.306 | — |
| RANDOM_LEGAL mean | +1.441 | denominator |
| RANDOM_LEGAL max | +2.167 | — |
| CURRENT_POLICY | +1.361 | **-0.178** |
| CURRENT_INTENT_COMPILER | +0.306 | **-2.535** |
| BEAM_SEARCH_COMPILER | +1.833 | **+0.876** |

`SEARCH >= 0.70 AND CURRENT_POLICY <= 0.40` holds on this panel, i.e. the MG1
case **would be a compiler gap** if the mechanism value were pair-scoped.

## The intent compiler inverts the intent

Told `BROADSIDE`, `mg_cases.intent_plans` emits for the focal ship `1S1P` —
character-identical to the *counter arm's* plan — producing post-movement
relative bearing 5 with 1 mount bearing (gold: bearing 1, 3 mounts). The
offending expression is the intent's desired heading, `((b - 1 + 1) % 6) + 1`,
which offsets from the target bearing by +1 heading and lands on the narrow side
for this geometry. Consequence: any organisation built on "issue the intent, let
the AI compile it" inherits a systematically inverted turn direction. This is
the round's most directly actionable defect.

## Reading

Unmasking a broadside wins the pair exchange and loses the fleet exchange. The
lever is real and it is consumed by fleet-level accounting — consistent with the
M2.1-R "unmasking flips negative against an adversary" result, now isolated to a
single ship with an exact reproduction.
