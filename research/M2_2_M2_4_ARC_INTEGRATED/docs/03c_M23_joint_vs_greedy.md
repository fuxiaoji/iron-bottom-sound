# 04_JTC_JOINT_VS_GREEDY.md — the decisive comparison, and why it is confounded

Common opportunity set (the states where the intent-constrained beam achieves the
mechanism): **35 (state, intent) rows**, frozen rule §4.2.

| arm | mean Δ team utility on the common opportunity set |
|---|---|
| `JOINT_BEAM_SEARCH` | **1.048** |
| `PER_SHIP_GREEDY` | **1.428** |
| `RANDOM_MATCHED_BUDGET` | **1.831** |

Mechanism-opportunity rates agree: greedy ≥ joint in **5 of 8** scenario×intent
cells (e.g. S-01 I1 0.350 vs 0.222, EM-01 I3 0.455 vs 0.100), with joint ahead in
S-01 I3 (0.556 vs 0.400) and EM-01 I1 (0.500 vs 0.409).

```
JTC_JOINT_COORDINATION_EFFECT = FAIL
```

## M23-F3 — my own search arm cannot express coordination

The cheap geometry surrogate is **additively separable**: with the enemy's
predicted post-movement geometry fixed (it is — enemy plans are byte-identical
across arms), the total score is `Σ_ship contribution(ship, its own plan)`. The
per-ship argmax is therefore the **exact** optimizer of that surrogate, and the
beam — searching over the same separable objective — cannot beat it except
through the real-scored survivors and the lexicographic intent constraint.

So the JTC FAIL has two components and they must not be conflated:

1. **A genuine finding**: the intent constraint (reach the local mechanism first)
   costs team utility, and the arm that keeps the constraint is dominated by arms
   that drop it. That is the JTC *phenomenon* showing up as the JTC *experiment's*
   failure.
2. **A defect in the arm**: `JOINT_BEAM_SEARCH` as frozen cannot represent joint
   coordination, because its objective contains no interaction terms. The
   interaction structure the game actually has — concentration bonus and
   multi-target penalty in `_gunnery_modifiers`, which depend on how many
   attackers share a target — is absent from the surrogate and present in the real
   metric.

A fair joint-compiler test needs a surrogate with interaction terms (or direct
optimisation of the real team metric at a small budget). That is a new arm and
requires a new pre-registration; it is **not** run here, and the JTC verdict below
is reported as frozen, with this confound attached.
