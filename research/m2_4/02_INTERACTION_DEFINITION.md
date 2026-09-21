# 02_INTERACTION_DEFINITION.md

Around the production baseline joint `a0`, with every `U` engine-exact:

```
q_i(a_i)        = U(a_i, a_-i^0) − U(a0)
phi_ij(a_i,a_j) = U(a_i,a_j,a_-ij^0) − U(a_i,a_-i^0) − U(a_j,a_-j^0) + U(a0)
```

## Operationalisation (frozen in PRE_REGISTRATION_M24 §2)

`a_i` is ship i's **additive-surrogate-best** candidate and `a_j` likewise, so
`phi_ij` measures the interaction between each ship's individually-best choice —
precisely the quantity that decides whether per-ship greedy suffices.
`PRACTICAL_FLOOR_PHI = |phi| >= 0.05` EH units.

The additive model the interaction-aware arm fits is

```
U ≈ U(a0) + Σ_i q_i(a_i) + Σ_{i<j} phi_ij(a_i,a_j)
```

with `q_i` and `phi_ij` taken from **exact** evaluations only. If the pairwise
terms are negligible, this model collapses to the additive one and the arm has
nothing to exploit — which is what Gate I tests.

## Why the definition is second-order

The PI's question is whether `U(a_1,…,a_N) ≠ Σ_i u_i(a_i)`. The first-order
deviation is captured by `q_i` (single-ship effect), and the residual after the
best additive model is exactly the pairwise term above, up to higher-order terms
that are unmeasurable at this budget and are not claimed.
