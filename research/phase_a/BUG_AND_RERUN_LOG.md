# BUG_AND_RERUN_LOG.md — Phase A.2

Preserved per red line "preserve invalid runs"; no run was deleted.

## A2-B1 — Track B `true_edges` serialization crash (fixed, rerun)

`json.dump({"true_edges": [[list(k[0]), list(k[1]), ...]}` indexed the line key
instead of using it, raising `TypeError: 'int' object is not iterable` after the
balance labels had been written. Fixed to serialize the key directly. Because labels
are cached in `raw/track_b_a2/labels_*.csv`, the rerun skipped labeling entirely and
went straight to the truth/acquisition stages — no measurements were lost or
duplicated.

## A2-A1 — the Phase A "oracle" was not an oracle (audited, invalidated)

Detailed in `01_TRACK_A_ORACLE_AUDIT.md`. The old aggregate is marked INVALID; the
corrected computation reuses the same held-out matrix, so no new evaluations were
required and the comparison stays paired.

## A2-B2 — structured acquisition does not bisect (recorded, not "fixed")

The STRUCTURED_ACTIVE order queries mid/min/max severity per line and then fills.
It cannot localise a transition between those probes, which is why it scores below
random. This is left in place and reported as a design defect of the run rather than
silently replaced, because replacing it after seeing the comparison would be exactly
the post-hoc method-shopping the plan forbids.

## A2-C1 — sampling fault yield (instrument property, no change made)

The frozen generator produces ~1 valid causal failure per 700 injections on
sampling. Per the plan the fault strength is **not** changed after attribution
outcomes, so the task is reported `C_LOW_YIELD_BLOCKED`.
