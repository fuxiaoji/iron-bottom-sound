# 09_NEXT_RESEARCH_DECISION.md

What B1E establishes, what it does not, and the decisions that are now the PI's.
No item below is started; the stage stopped here by instruction.

## Established

1. **The BROADSIDE defect is research-only and is now quantified on both scales.**
   Pre-fix: −0.056 L0 (usable mounts 2 → 1) and −11.361 L1 — worse than doing
   nothing. Repaired: +0.667 L0 (41 % relative) and −5.833 L1, i.e.
   `MECHANISM_SUCCESS_BUT_NEGATIVE_EXTERNALITY`. Only the joint beam is positive
   on both (+0.472 L0, +7.417 L1).
2. **Range control has an executable gold** (MG3-E, 9 vs 12 hex inside the 13-hex
   envelope, 39 % own-EH gap, both arms visible with 8 primary mounts bearing), so
   the old MG3's `EXECUTABLE_GOLD_INVALID` diagnosis is now backed by a
   replacement case rather than only by a critique.
3. **The deployed torpedo planner achieves exactly zero mean route reduction**
   over 15 natural torpedo states while firing in 40 % of them, and two
   observation-only arms land within 0.03 of `HOLD`. The full-state ceiling
   ranges 0.020–0.316 by scenario.
4. **Material per-route commitment regret exists in 4 of 15 torpedo states across
   2 scenarios** (`R_shared` 0.500 / 0.667 / 0.333 / 0.333), so the frozen rule
   returns `TORPEDO_PARTIAL_OBSERVABILITY` — with the caveat that the effect size
   is single-scenario-dominant (S-01 carries ceilings 0.97 and 0.30; EM-01's two
   material states carry 0.07 and 0.17; S-03 contributes none).

## Not established

- **No L2 claim.** Nothing here says a better compiler wins games; long-horizon
  game value is deferred to M2.3 by the pre-registration.
- **Hypothesis B is not separated.** Whether the commitment conflict is
  *observational* or a property of route diversity under a one-launch action
  space cannot be decided by the control that was run: the public hypothesis set
  moved the metric in **both** directions relative to the true route set, and it
  differs from it in size and diversity. A size/diversity-matched subset control
  over `C(h)` is the first thing to add and is **not** in this design.
- **The movement census's stratum coverage is incomplete** (see
  `05_B1E_MOVEMENT_CENSUS.md`): `damaged` and `late` are thin or empty in S-01
  and S-03 because those scenarios end at turns 7 and 4 (M22R-F3).
- **`NATURAL_COMPILER_GAP`'s two-mechanism clause is unsatisfiable** by this
  census design (M22R-F1); the verdict is reported in single-mechanism form.

## Decisions for the PI

1. **Promote torpedo partial observability to a main line?** The PI's own gate
   for that was "≥20 % of torpedo decision states show material shared/Bayes
   regret, across scenarios" — met by the frozen rule, but with a
   single-scenario-dominant effect size. Recommendation: run the matched-subset
   control first (cheap, one script), and only then take it to an independent
   CCF-A novelty review.
2. **MG3-E's role.** It passes, so Range may enter future censuses. Does the PI
   want MG3 re-issued as `HISTORICAL_PROXY_PASS (superseded by MG3-E)` in a later
   pre-registration, or left exactly as recorded with MG3-E cited alongside?
3. **The externality result.** `REPAIRED_INTENT_BASELINE` gains locally and loses
   team utility; the beam gains both. If the project wants a compiler target, it
   is "compile the *line*, not the ship" — which is a different object from an
   intent compiler and would need its own pre-registration.
4. **Census design repairs before any further census**: add a `mid` bucket and
   either add a range-directed arm or drop the two-mechanism clause (M22R-F1,
   M22R-F3). Both are cheap and both were discovered here.

## Discipline notes carried forward

- `REPAIRED_INTENT_BASELINE` is a baseline, never a candidate method; it loses to
  `RANDOM_LEGAL` on both scales in the frozen MG1 case.
- The binary per-route payoff is a recorded counterexample (M22R-F2), not a
  result.
- No value-realisation, RL, GNN or paper-method work was performed or designed
  in this stage.
