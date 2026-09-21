# 01_B0_GOLD_COMPILER_FIDELITY.md

Gate, exactly as frozen in `PRE_REGISTRATION_M22.md`:

```
GOLD_COMPILER_GAP = PASS iff >= 2 of 3 cases satisfy
    SEARCH fidelity >= 0.70 AND CURRENT_POLICY fidelity <= 0.40
```

Result: **FAIL — 0 of 3**, with only 1 of 3 computable under the frozen metric.

| case | primary status | gold gap | F(SEARCH) | F(CURRENT) | F(INTENT) | verdict |
|---|---|---|---|---|---|---|
| MG1 broadside | GOLD_GAP_NONPOSITIVE | -5.844 | n/c | n/c | n/c | excluded |
| MG1 pair panel (supplementary) | COMPUTABLE | +0.448 | **+0.876** | **-0.178** | **-2.535** | would be GAP |
| MG3 range | GOLD_GAP_NONPOSITIVE | 0.000 | n/c | n/c | n/c | excluded |
| MG4 torpedo | COMPUTABLE | +0.966 | **+0.107** | **0.000** | **+0.036** | NO_GAP |

`n/c` = not computable: the pre-registration computes fidelity "only when the
denominator is positive", and the denominator `M(gold) - M(random)` is not.

Pre-registered interpretation clauses applied literally:

- "If SEARCH < 0.70 on **every** case while the gold gap is above the floor:
  `SEARCH_COMPILER_FAIL`" — **does not apply**: on the one computable search
  panel (MG1 pair) SEARCH = +0.876 >= 0.70. The failure is not the search.
- "If CURRENT_POLICY >= 0.8 anywhere: `CURRENT_AI_ALREADY_STRONG`" — does not
  apply either; the measured current-policy fidelities are 0.00, -0.18.
- "If SEARCH < 0.70 ... do not run the natural census" — B1 is not run.

Method definitions as executed (naming discipline per pre-registration):
MANUAL_GOLD = the arm recorded by M2.1-R2.1; RANDOM_LEGAL = mean of 8 seeded
uniform draws from the legal space; CURRENT_POLICY = the deployed
`TacticalCommander(profile="balanced")`; CURRENT_INTENT_COMPILER = the repo's
existing `mg_cases.intent_plans`, unmodified, given the mechanism's intent;
BEAM_SEARCH_COMPILER = joint movement beam, width 64, <=8 legal plans per ship,
cheap geometry for partial ordering, all 64 surviving joints played through real
simultaneous movement; PUBLIC_CORRIDOR_SEARCH / FULL_STATE_CORRIDOR_CEILING =
torpedo enumeration under an observation-only vs a full-state objective.

Budget actually consumed: MG1 beam played 64 joints (5 AXIS ships, pool 8 each);
MG3 beam played 64 joints (12 ALLIES ships, pool 8 each); MG4 enumerated 288
legal configurations (the R2.1 count) and cross-validated 12 routes against the
engine. Wall clock 127 s for all three cases. 0 paid LLM calls. Production
engine untouched.
