# FAILURES_AND_COUNTEREXAMPLES.md — M2.4

## M24-F1 — main-set deviation from the pre-registration

`PRE_REGISTRATION_M24` §7 named the M2.3 frozen 35 opportunity combos as the main
set. The run used **all unique state-sides of the M2.3 census** (53 attempted),
which is a superset of that set. A superset is not cherry-picking, but it is a
deviation and is recorded as one. The intent labels that came with it are
degenerate (M24-F3), so the deviation also cost the conditional analysis.

## M24-F2 — silent state loss, the exact failure shape the red lines name

`run_methods` raises `RuntimeError` when an engine-exact evaluation fails, and
`evaluate_state` catches it and returns `None`; the driver then `continue`s without
incrementing any counter. Result: **53 main state-sides attempted, 19 recorded**
(34 lost) and ~30 supplemental scanned, 11 recorded. The pre-registered sample
sizes (35/30) were therefore not reached, and nothing in the partial record shows
the loss — it had to be derived by comparing the log's progress line with the final
row count.

The verdict does not depend on it (all six conditions fail by wide margins), but
the mechanism is recorded verbatim because "a per-state exception that silently
drops the state" is precisely the pattern the project's R3 forbids. The counts are
printed in every panel table in this bundle, and the fix for a future run is to
count and report rejections by reason, as `m23_jtc.py` already does for its
admission rule.

## M24-F3 — degenerate intent labels

All 19 recorded main states carry `I1_BROADSIDE`, because the main-set builder
takes the first M2.3 row per state-side and M2.3 ordered intents with I1 first. The
PI asked for `P(Δ>0 | intent)`; only `I1_BROADSIDE` (6/19) and `SUPPLEMENTAL`
(5/11) are computable, and both are reported as such. No post-hoc relabelling pass
was run, because a labelling chosen after seeing Δ could be tuned to it.

## M24-F4 — two real bugs inside the interaction arm, found by re-reading it

After Gate I passed I re-read the arm before trusting Gate II:

1. the `phi` construction set `u_i = a0U = …` and then used that mutated `a0U` as
   the base for `u_j`, so `u_j` was overstated by `q_i` and every `phi` was
   therefore understated by `q_i`;
2. the model-guided selection added a pair term only when the assignment matched
   the **first** probe's plans, for every pair, instead of matching each pair's own
   probed plans — so at most one interaction term could ever enter the score.

Both were fixed and Gate II re-run from scratch. Gate I's numbers are unaffected:
its `phi` block used the correct base term (`u_ij − a0U − q_i − q_j`), which is why
Gate I's distribution is trustworthy while the arm's own phi values were not.

## Counterexample of record — the kill was not foregone

The first single-state sanity check after the fix showed beam − greedy = **+0.972**
with pair interactions of 3.25 and 2.61 EH, and the S-03 median in the full panel
is **+0.222**. The sign was genuinely open until the panel ran; the FAIL comes from
the ties (9 of 19), the EM-01 losses (−4.194 median) and the inability to beat
sequential exact coordinate ascent — not from an arm that could not work.
