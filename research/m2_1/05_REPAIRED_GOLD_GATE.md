# 05_REPAIRED_GOLD_GATE.md

```
MG1_BROADSIDE            = VALID_PASS (frozen; not re-run, not re-tuned)
MG2_CROSSING_THE_T       = FAIL  (repaired meter; 3 of 4 conditions;
                                  raking fraction 0.44 < 0.50)
MG3_RANGE_CONTROL        = VALID_PASS (frozen)
MG4_REAL_TORPEDO_CORRIDOR= PASS  (repaired: persistence PASS,
                                  RouteReduction 0.966, engine agreement 29/29)
MG5_LOCAL_FORCE          = FAIL  (repaired meter; DISPERSE beats CONCENTRATE)

MECHANISTIC_GOLD_GATE = FAIL  (3 of 5; requires >= 4)
```

Stage B (compiler fidelity) and Stage C (value realization) remain NOT RUN.

## What the repair changed, and what it did not

| case | M2.1-R2 | after repair | cause |
|---|---|---|---|
| MG2 | PASS (1.68x, no legal allocation) | **FAIL** | F21 double counting inflated the exchange; also the arm does not produce raking geometry |
| MG4 | FAIL (CASE_CONSTRUCTION_FAIL) | **PASS** | F22 space-time off-by-one + intercept-only aiming + hull-damage safety metric; correct corridor covers 28/29 routes |
| MG5 | FAIL | **FAIL** (confirmed) | the illegal meter did not cause this one; the assumption itself fails at this engagement scale |

## Science the repair settled

1. **A long-range torpedo setting creates a real, engine-verified
   time x space corridor**: 28 of the victim's 29 legal next-turn routes pass
   through the track's path; only "hold" is safe. The prediction and the
   engine's `torpedo_contact` agree on 29/29 routes. Torpedo area denial is
   therefore a measurable, rule-level phenomenon in this platform — the
   M2.1-R2 negative was a construction artifact, as the PI judged.
2. **Crossing the T remains unconfirmed** — not because the rules fail to
   price aspect (MG1 shows they do), but because the current arm cannot
   occupy the raking position. This is now a *positioning/compiler* question,
   not a rules question.
3. **Local force superiority does not exist at this platform's engagement
   scale** (gun range >= fleet spacing), confirmed with a legal meter in the
   original M2.1-R2 state.

## Budget and integrity

- All thresholds in PRE_REGISTRATION_R21 before any repaired measurement;
  MG2/MG5 states and MG1/MG3 verdicts frozen, not re-searched.
- New failures recorded: F21 (mount multi-target double counting),
  F22 (space-time segment off-by-one), plus the two fidelity defects found
  while repairing (modifier grouping, visibility) — all in
  FAILURES_AND_COUNTEREXAMPLES.md.
- ~1,200 engine evaluations; 0 paid LLM; production engine untouched.
