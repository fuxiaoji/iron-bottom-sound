# 00_EXECUTIVE_SUMMARY.md — M2.2 Tactical Compiler Fidelity Audit

## Frozen historical record (unchanged, quoted as recorded)

```
M21R21_GOLD_GATE          = FAIL_3_OF_5
MG1_BROADSIDE             = VALID PASS   (rule leverage CONFIRMED)
MG2_CROSSING_THE_T        = FAIL         (registered arm)
MG3_RANGE_CONTROL         = VALID PASS   (rule leverage CONFIRMED)
MG4_REAL_TORPEDO_CORRIDOR = VALID PASS   (rule leverage CONFIRMED)
MG5_LOCAL_FORCE           = FAIL         (registered arm)
```

M2.2 does not re-run, re-tune or re-score any of them. MG2/MG5 stay out of scope.

## M2.2 verdicts

```
GOLD_COMPILER_GAP = FAIL   (0 of 3 cases; 1 of 3 computable under the frozen metric)
    MG1  GOLD_GAP_NONPOSITIVE   fleet margin: gold is WORSE than random
         supplementary (pair margin, same formula on the case pair): COMPUTABLE,
         SEARCH fid = +0.876, CURRENT fid = -0.178  -> this case WOULD be GAP
    MG3  GOLD_GAP_NONPOSITIVE   both panels identically zero
    MG4  NO_GAP                 COMPUTABLE: gold gap +0.966, SEARCH fid = +0.107
B1_NATURAL_CENSUS = NOT RUN   (gated on B0 PASS; pre-registration forbids it)
NATURAL_OPPORTUNITY_RATE  = NOT_MEASURED
SEARCH_RECOVERABILITY     = METRIC_DEPENDENT
CURRENT_AI_FIDELITY       = CURRENT_POLICY 0.00 (MG4) / -0.18 (MG1 pair) / n.c. (MG3)
                            CURRENT_INTENT_COMPILER -2.53 (MG1 pair) / +0.04 (MG4) / n.c. (MG3)
PUBLIC_INFORMATION_GAP    = CONFIRMED (MG4)
STAGE_B_DIAGNOSIS         = NOT_MEASURABLE_AT_B0 (its thresholds need the census)
```

## What this round actually found

The compiler question cannot be answered before the metric question. Three
independent results, each engine-real and reproduced against the frozen M2.1-R2.1
artifacts:

1. **The same frozen formula gives opposite answers at two scales (MG1).**
   Fleet-wide `M_broad = EH_own_legal - EH_enemy_legal` scores the hand-built
   broadside **-12.17**, worse than the mean random legal plan **-6.32** (gap
   -5.84, non-positive denominator, so the pre-registered ratio is not
   computable). Restricted to the case's own pair, the same formula scores gold
   **+1.89** vs random **+1.44** (gap +0.45) and the verdict flips to GAP
   (SEARCH 0.876, CURRENT -0.178). Unmasking a broadside is a real gain in the
   pair exchange and a real loss in the fleet exchange — the lever is consumed
   by fleet-level accounting, exactly the "exposure is symmetric" effect M2.1-R
   recorded, now isolated to one ship.

2. **The deployed intent compiler turns the ship the wrong way (MG1).** Told
   intent `BROADSIDE`, the repository's own compiler
   (`mg_cases.intent_plans`, unmodified) emits for the focal ship `1S1P` — the
   *counter arm's* plan — producing post-movement relative bearing 5 with 1
   mount bearing instead of the gold's bearing 1 with 3 mounts. Pair fidelity
   **-2.53**. This is a compiler defect with a one-line reproduction, not a
   research ambiguity.

3. **The registered MG3 meter is outside the engageable envelope (MG3).** The
   frozen PASS compares the BB's expected hits at 15 and 17 hexes
   (2.56 vs 0.94, reproduced exactly). Allied visibility in that state is **13
   hexes** and the radar optional rule is **OFF**, so `engine._can_see` is
   `False` for both arms: the engine would reject those gunnery orders
   (`gunnery_rejected`). Under the engine-real meter both arms are **0.000** and
   the gold gap is 0. MG3's registered meter checks `_mount_can_bear` but not
   `_can_see`; MG3 was frozen during the R2.1 repair, so it never received the
   visibility fix that MG2/MG4 received. Recorded as M22-F4.

4. **The torpedo corridor is a full-state phenomenon (MG4).** The gold corridor
   is reproduced exactly (route reduction **0.966**, 12/12 engine agreement on
   the space-time contact test, predicted segment `[(1,T8),(2,T7),(3,T6),(4,T5)]`
   identical to R2.1). The deployable public-information search scores **0.107**
   and the deployed AI scores **0.000** (it submits no torpedo order at all in
   that state). The public objective is **tie-dominated**: its argmax sets
   contain configurations spanning route reduction 0.00 -> 0.97, and the best
   configuration scores *low* on it (overlap 1 of a maximum 5). The corridor is
   real, and not identifiable from observation-grade information in this case.

5. **The two legal-fire evaluators agree well enough to proceed** (fire
   calibration, 20 states): Spearman(net EH) = **0.908**, same-target fraction
   0.888, mean relative own-EH difference 0.191 -> `HEURISTIC_PARTIAL`, both are
   reported side by side, and the movement mechanisms are evaluated with
   `LEGAL_FIRE_HEURISTIC` per the pre-registration. A first version of
   `FIRE_SEARCH` multiplied firepower by the mount count (M22-F2); after the fix
   the negative correlation that motivated the check disappeared.

## What this round does not claim

- No value-realisation claim, no RL, no rule change, no production edit.
- No claim that M2.1-R2.1's historical verdicts were wrong. MG3's PASS stands as
  recorded; M2.2 shows *which meter* produced it and that the meter omits
  visibility. That is a case-validity finding, not a re-verdict.
- No claim that the beam search is optimal. It is `BEAM_SEARCH_COMPILER`, width
  64, <=8 legal plans per ship, every surviving joint played through real
  simultaneous movement — never "oracle".

## NEXT_PI_DECISION (four items, PI only)

1. **Which mechanism value is the research object** — fleet margin or pair
   margin? Under the frozen fleet margin, MG1's gold loses to random and the
   question of the compiler cannot be asked of that case at all.
2. **MG3** — accept the M22-F4 finding (the registered mechanism value is not
   realizable) and decide whether the frozen MG3 verdict is re-scoped, or
   whether a new range-control case is built inside the visibility horizon.
3. **MG4** — whether "the corridor needs full state" is promoted from
   side-result to a research object of its own (it is currently the strongest
   single negative in the project).
4. **B1 census** — the pre-registration forbids it while B0 is not PASS. If the
   PI wants the natural-opportunity numbers, the metric (item 1) must be
   re-specified first, in a new pre-registration.
