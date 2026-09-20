# 00_EXECUTIVE_SUMMARY.md — M2.1 platform & strategic-leverage audit (PARTIAL)

**Stage stopped early by PI**: the E0 census was interrupted at 80/93 snapshots
(movement-layer results lost, see 05). Everything below is what the completed
data supports. Honesty first: the flagship question of this audit — movement
and torpedo leverage — is NOT answered by measurement yet.

```
RULE_ENGINE_CONFORMANCE = PASS
    (0 BUG / 0 UNKNOWN / 0 NOT_IMPLEMENTED; illegal-move fallback =
     INTENTIONAL_INTERFACE_STRICTER; formation cap 8-vs-4 = PROJECT_EXTENSION,
     recorded, <=4 used)

RNG_PAIRING_STATUS = MATCHED_INITIAL_SEEDS_ONLY
    (engine rolls = independent Random(seed*1e6+counter); branch probe:
     HOLD 45 draws vs FIRE 63 draws, first dice divergence at event 2.
     "CRN" language banned throughout.)

ACTION_COVERAGE = FAIL (movement; gunnery PASS-with-caveat)
    movement candidates were per-ship perturbations of balanced plans;
    coordinated tactical plans (broadside unmasking, T-crossing,
    torpedo-corridor denial) are absent (user-raised, FAILURES F8).
    gunnery: hold/fire/allocation variants all distinct and valid.

MOVEMENT_LEVERAGE = NOT_MEASURED (interrupted; would need candidate
                    enrichment + re-run regardless)
GUNNERY_LEVERAGE = LOW
    (median lambda 0.000-0.018; no state >= 0.05 in any scenario;
    hold-vs-fire gap real but allocation-level differences ~0)
TORPEDO_LEVERAGE = NOT_MEASURED (interrupted)
REALISTIC_COMMAND_LEVERAGE = NOT_MEASURED (interrupted; M2-0 B0/B1 evidence
    of frequent natural disruptions remains valid)

SCRIPTED_CONTINUATION_ATTENUATION = UNTESTED (E2/E3 not reached)
HORIZON_MASKING = UNTESTED (horizon audit not reached)
VICTORY_METRIC_MASKING = UNTESTED for S-01/EM-01;
    for S-03 the coarse threshold is confirmed by construction (4 discrete
    outcomes) and material diagnostic was wired but not evaluated.

PLATFORM_DIAGNOSIS = INCOMPLETE (only the gunnery layer measured; that layer
    reads LOW, which is consistent with - but not sufficient for - any
    platform-level verdict)

IBS_FUTURE_ROLE = NO VERDICT (movement/torpedo unmeasured + candidate-
    coverage fix outstanding; per the plan's own decision tree, a
    platform-level demotion cannot be decided on the gunnery layer alone)

B_COMMAND_ORGANIZATION = KEEP_SUSPENDED
    (M2-0's B_ORACLE_ONLY stands: no new evidence was produced that meets
    the reassessment gate; the realistic-mode leverage strata were not run)

NEXT_PI_DECISION_NEEDED =
    1. approve movement candidate enrichment (add coordinated tactical plans:
       broadside unmasking turns, range-control speed moves, torpedo-corridor
       denial) + re-run E0 movement layer;
    2. approve E2/E3 evaluators to test the scripted-flattening hypothesis
       (the game-expert's objection: master-level movement value only exists
       when the opponent responds);
    3. or accept the gunnery-layer reading and demote IBS now.
