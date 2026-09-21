# 12_MAINLINE_SCORECARD.md

| criterion | JTC (Joint Tactical Compilation) | BARD (Belief-Aware Route Denial) |
|---|---|---|
| multi-intent / multi-scenario | 3 intents × 3 scenarios measured | 14 information sets × 3 scenarios |
| frozen PASS bar | ≥2 intents × ≥2 scenarios ≥20 % **and** joint ≫ greedy/random | matched control **and** action conflict **and** public recovery, ≥2 scenarios |
| what passed | conditions 1, 2, 4, 7 (coverage, stable positive joint gain, bug-independence) | action conflict on the true set (11/14 crossover, 5/14 no ε-good action) |
| what failed | condition 3 (only I1) and conditions 5–6 (joint **worse** than greedy 1.428 and random 1.831) | matched control (1 of 3 scenarios) and public recovery (1 of 3 scenarios ≥50 %) |
| measured effect size | joint mean ΔU +1.048 vs greedy +1.428 vs random +1.831 on the same 35 states | `R_shared` true 0.357 material → matched 0.214; ceiling 0.050–0.197 |
| fatal confound, disclosed | the frozen joint arm's surrogate is separable, so greedy is its exact optimizer (M23-F3) — the arm cannot test coordination | the matched control's conclusion hinges on an anchor detail (M23-F1), fixed and both runs kept |
| deployable value | none demonstrated | current planner 0.000, best public 61 % of a small ceiling in one scenario |
| **verdict** | **FAIL** | **FAIL** |
| residual value to the project | the local-vs-team externality is confirmed at census scale (again); a JTC re-test needs an interaction-aware surrogate | the hidden-commitment conflict is now known to be mostly a hypothesis-construction effect, with one surviving scenario named |

```
MAINLINE_CANDIDATE = NONE
```

Neither candidate clears its frozen cheap-kill bar. Per the PI's instruction, a
tie or a double failure is not resolved by this stage; the honest output is NONE,
and the two named follow-ups (interaction-aware joint surrogate; the S-01
surviving information set) are what a future stage would have to attack.
