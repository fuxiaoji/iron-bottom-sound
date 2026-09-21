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

## A2-C2 — a draft of this bundle overstated Track C (corrected)

An earlier draft of `03_TRACK_C_DECISIVE_CALIBRATION.md`, `00_EXECUTIVE_SUMMARY.md`
and the accompanying chat report said the balance calibration was "computed" and
quoted 15 replays/case at ~26 s. Those numbers come from the **Phase A v3.1** run
(23 valid cases), not from Phase A.2: A.2's frozen generator reached only **27**
valid failures on balance inside the 1000-attempt cap, so status was
`C_LOW_YIELD_BLOCKED` and no matrices were built. The claim was caught by re-reading
the A.2 log (`[balance] valid=27/1000 C_LOW_YIELD_BLOCKED`) and is corrected in the
three documents listed above. Recorded here because an unsupported "calibration
computed" would have been exactly the kind of overstatement the red lines forbid.

## A3-B1 — a3_track_b ran headless in the background (no defect)
The whole Track B rerun (positive control + 2 tasks x 4 methods x 4 K x 30 reps =
960 acquisition runs) executed deterministically from cached labels; reconcile ok.

## A3-C1 — CSV schema crash in the first C0 attempt (fixed, rerun from zero)
Per-episode rows and per-setting summary rows were written through one DictWriter
with the fieldnames of whichever rows came first → `ValueError: dict contains fields
not in fieldnames`. The run crashed after the act_drop settings had completed. Fixed
with a fixed superset schema + `extrasaction="ignore"`; the calibration seeds are
dedicated and deterministic, so the rerun-from-zero reproduced identical numbers.

## A3-C2 — an impossible all-zero yield triggered a machinery sanity check
The first C0 attempt showed yield = 0.000 for every setting. Because "exactly zero
everywhere" has been a bug signature in this project three times before, a mean-shift
diagnostic (faulted mean − clean mean) was added before accepting any verdict: the
shifts are large and correctly signed (balance obs_corrupt σ1.2 w8: −38.7; sampling
max −2.8), proving the faults are applied and the zeros are real. The verdict
`C_GENERATOR_FEASIBILITY_FAIL` therefore stands on verified-applied faults.
