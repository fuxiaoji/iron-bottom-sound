# 00_EXECUTIVE_SUMMARY.md — M2.3 Mainline Disambiguation

```
HISTORICAL_GATES_PRESERVED = YES

MG3_STATUS =
SUPERSEDED_BY_MG3E_EXECUTABLE_PASS

JTC_MULTI_INTENT              = FAIL
JTC_JOINT_COORDINATION_EFFECT = FAIL
JTC_VERDICT                   = FAIL

BARD_MATCHED_CONTROL = FAIL
BARD_ACTION_CONFLICT = PASS
BARD_PUBLIC_RECOVERY = FAIL
BARD_VERDICT         = FAIL

MAINLINE_CANDIDATE   = NONE

BIGGEST_REMAINING_RISK =
  the JTC cheap-kill is confounded by my own search arm: the frozen joint
  beam's objective is additively separable, so PER_SHIP_GREEDY is its exact
  optimizer and the joint arm could not win by construction (M23-F3). The
  FAIL is reported as frozen, but a re-test with an interaction-aware
  surrogate is the first thing to run before treating JTC as dead.
```

## What the stage established

1. **Neither candidate passes.** JTC fails its multi-intent bar (only I1 reaches
   ≥20 % in ≥2 scenarios) and its coordination bar on the same 35 opportunity
   states: joint +1.048 < greedy +1.428 < random +1.831. BARD's conflict is real
   on the true hidden set (11/14 sets with best-action crossover, 5/14 with no
   ε-good shared action) but halves under a size/diversity-matched control
   (0.357 → 0.214) and survives in **one** scenario, where the best public planner
   recovers 61 % of a small ceiling.
2. **The local-vs-team externality is now a census-scale fact**, not a single-case
   observation: every arm that optimises the local mechanism pays in team utility,
   and the arm that drops the intent constraint (greedy) does better on team
   utility while achieving the mechanism *more* often in 5 of 8 scenario×intent
   cells. The constraint, not the search, is what costs.
3. **MG3 is annotated, not defeated**: `SUPERSEDED_BY_MG3E_EXECUTABLE_PASS`.
4. **Two of my own measurements had to be repaired mid-stage**, both found by
   looking at shapes that could not be right: a degenerate all-zero matched
   control (M23-F1, wrong anchor) and a comparison across different state sets
   (M23-F2). The first would have produced `ARTIFACT` for BARD; both bad and good
   runs are kept in `metrics/`.
5. **The damaged-panel predicate is non-discriminative** (M22R-F6 carried forward
   and quantified): 234 of 234 scanned state-sides satisfy the PI's literal
   "damaged" rule, and 217 of 234 the stricter 0.75·max_hull threshold. The panel
   is reported as a conditioned sample and no damage-contrast claim is made.

## What was not done

No RL, no GNN, no Transformer, no paper method design, no literature review, no
rule changes, no production edits, no paid LLM calls. The old census, the old
gates and the old verdicts are untouched; `research/m2_2r/` gained only the M22R-F6
erratum and the predicate fix, both disclosed.
