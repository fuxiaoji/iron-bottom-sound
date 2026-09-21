# 05_JOINT_VS_GREEDY.md — Gate II main comparison

```
Delta_joint_greedy = U_exact(INTERACTION_AWARE_BEAM) − U_exact(PER_SHIP_GREEDY_ADDITIVE)
```

## Main panel (M2.3 census state-sides)

| quantity | value |
|---|---|
| n | **19** |
| win / tie / loss | **6 / 9 / 4** |
| pooled win rate | **0.316** |
| pooled median | **+0.000** |
| pooled mean | −0.389 |
| paired bootstrap 95 % CI of the median | **[+0.000, +0.111]** |
| per-scenario median | S-01 0.000 (n=10) · S-03 **+0.222** (n=6) · EM-01 **−4.194** (n=3) |
| median after dropping the two largest \|Δ\| states | **+0.000** |

## Supplementary panel (deterministic supplemental states)

| quantity | value |
|---|---|
| n | **11** |
| win / tie / loss | 5 / 4 / 2 |
| pooled win rate | 0.455 |
| pooled median | +0.000 |
| per-scenario median | S-01 **+0.722** (n=5) · S-03 0.000 (n=5) · EM-01 −4.194 (n=1) |

## Reading

**Nine of nineteen main states are exact ties.** The interaction-aware beam and
per-ship greedy frequently produce *the same joint* — the interaction terms guide
it to the same place greedy already reaches — and where they differ the sign is not
consistent: S-03 favours the beam (+0.222 median), EM-01 punishes it (−4.194), S-01
ties exactly. The mean is negative because the EM-01 losses are large.

The two extremes are not the story either: dropping the two largest-gain states
leaves the median at 0.000, so condition 6 fails on its own terms.

State loss, disclosed (M24-F2): 53 main state-sides were attempted and 34 were
dropped when an exact evaluation failed and the `RuntimeError` guard skipped the
state silently; the supplemental scan produced 11 evaluable states of ~30 scanned.
The recorded n is therefore 19 and 11, not the 35/30 the pre-registration named,
and the dropped-state pattern is unknown. Every failing condition fails by a wide
margin, so the verdict is not sensitive to the loss — but the loss is real and is
recorded rather than smoothed over.
