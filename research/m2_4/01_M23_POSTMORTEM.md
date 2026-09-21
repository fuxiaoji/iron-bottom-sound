# 01_M23_POSTMORTEM.md — why a last chance was given

`M2.3 JTC = FAIL` is preserved exactly as recorded. This document states what the
FAIL did and did not establish, because the PI's grant of one more test rests on
it.

## What M2.3 measured

On the same 35 opportunity states: `JOINT_BEAM_SEARCH` +1.048 < `PER_SHIP_GREEDY`
+1.428 < `RANDOM_MATCHED_BUDGET` +1.831 (mean Δ team utility). Mechanism-opportunity
rates likewise favoured greedy in 5 of 8 scenario×intent cells.

## What it could not establish

The M2.3 joint arm searched with a cheap geometry surrogate that is **additively
separable** once the enemy's predicted geometry is fixed:

```
S(a_1..a_N) = Σ_i contribution_i(a_i)
```

The per-ship argmax is therefore the surrogate's **exact optimizer**, so
`PER_SHIP_GREEDY_ADDITIVE` and `JOINT_BEAM_SEARCH` optimised the same function, and
the only remaining lever was the lexicographic intent constraint — which costs
team utility. The arm could not, by construction, test whether *coordination*
helps. That is M23-F3, recorded in `research/m2_3/FAILURES_AND_COUNTEREXAMPLES.md`.

## What M2.4 changes, and what it does not

Changed: (i) the candidate set is fixed and shared by every method; (ii) every
method is capped at the same number of **engine-exact** joint evaluations; (iii)
the interaction-aware arm fits `q_i` and `phi_ij` from *exact* measurements and
uses those terms to choose which joints to evaluate and which to submit, so its
guidance contains real interaction; (iv) the verdict keys on engine-exact
`U_exact` only, with the cheap surrogate confined to guiding search.

Unchanged: the frozen history, the old census, the intent families as *conditional*
labels only, and the rule that a FAIL here ends JTC permanently.
