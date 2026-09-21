# 07_INTENT_CONDITIONAL.md — conditional only, no prevalence gate

Per the PI: intent is a **label** in this stage, not a gate.

| label | n | P(Delta_joint_greedy > 0) |
|---|---|---|
| `I1_BROADSIDE` (main panel) | 19 | **6/19 = 0.316** |
| `SUPPLEMENTAL` | 11 | **5/11 = 0.455** |

**Disclosure (M24-F3):** the main-panel intent labels came out degenerate — all 19
recorded main states carry `I1_BROADSIDE`, because the main-set builder takes the
first M2.3 row per state-side and M2.3 ordered the intents with I1 first. So a
genuine `P(Δ>0 | RANGE)` or `P(Δ>0 | RAKING)` cannot be computed from this run, and
none is reported. The conditional rates above are the only ones the data supports.

The supplemental panel's dominant-local-change labelling was not applied either:
those states are reported under a single `SUPPLEMENTAL` label. Both gaps are
recorded rather than filled with a post-hoc labelling pass that could be tuned to
the result.

What the label does show: on the one intent family with n > 0, the interaction
beam wins in under a third of states — consistent with the pooled panel and with
the tie-heavy distribution in `05_JOINT_VS_GREEDY.md`.
