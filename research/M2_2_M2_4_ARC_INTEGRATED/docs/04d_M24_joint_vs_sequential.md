# 06_JOINT_VS_SEQUENTIAL.md

```
Delta_joint_seq = U_exact(INTERACTION_AWARE_BEAM) − U_exact(SEQUENTIAL_TEAM_BR)
```

| panel | median | paired bootstrap 95 % CI | reading |
|---|---|---|---|
| main (n=19) | **+0.000** | **[−0.722, +0.000]** | the interaction beam is **not** better than sequential coordinate ascent, and the CI's lower bound is far below the −0.05 tolerance |
| supplemental (n=11) | +0.000 | [−0.694, +0.000] | the same shape |

`SEQUENTIAL_TEAM_BEST_RESPONSE` moves one ship at a time and accepts a change only
when the **engine-exact** team utility improves. It is cheap (≤2n evaluations) and
it is at least as good as the pairwise-model beam in both panels.

This is the most informative single comparison in the stage: it says that whatever
coordination gain exists is already captured by **sequential exact hill-climbing**,
and that modelling `phi_ij` explicitly and searching over the model does not add
value at this budget. Condition 4 of the frozen gate is therefore false, and it
would remain false even if condition 3 had passed.
