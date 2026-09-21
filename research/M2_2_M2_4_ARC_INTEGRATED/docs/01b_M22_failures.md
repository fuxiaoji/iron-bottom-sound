# FAILURES_AND_COUNTEREXAMPLES.md — M2.2

## M22-F1 — mixed-side rank statistic is artifactual

`AXIS net_eh = -(ALLIES net_eh)` holds identically on a fixed state (the two
sides' legal-EH margins are negatives of each other), so pooling both sides in a
single rank correlation manufactures a spurious anti-correlation. The first fire
calibration reported per-side Spearman -0.333 for exactly this reason. All
reported correlations are now computed per side or on a single side's states.

## M22-F2 — FIRE_SEARCH multiplied firepower by the mount count

`fire_search` stored one mount list under every mount id of the
"all-mounts-on-one-target" option and then extended its per-target bucket with
that list once per key, so a 5-mount ship was scored with 25 mount entries. The
tell was that the search scored **worse** than the heuristic although its option
set contains the heuristic's own allocations, and a 49-mount detail row for a
9-mount ship. Fixed by representing an option as `{target_id: [mounts]}` with one
`_group_eh` call per (target, mount kind) and each mount counted once. The
negative correlation disappeared (Spearman(net EH) 0.908).

## M22-F3 — `movement_candidates` is a subset of the legal plan space

The deployed commander emits legal plans that never appear in
`movement_candidates(...)["reachable"]` (e.g. `1P1P1P1P`), so looking a plan up
in that table to obtain its cost both false-rejects legal plans and cannot be
used as an oracle for "is this plan legal". Two further consequences found while
fixing it:

- `MovementOrder.speed` must be the engine's own **movement cost** (advances +
  120-degree turns; a 60-degree turn is free), not the count of hexes advanced
  and not the number of MF commands. `engine.movement_cost(plan, commands)` is
  the authority; computing it by hand rejected legal batches
  (`KINUGASA: declared speed 4 does not match 5 MF plan`).
- End-of-plan position and heading must come from
  `engine.movement_trajectory(ship, plan)`, not from the candidate table, for the
  beam's cheap-geometry ordering to cover the deployed policy's own plans.

Every arm remains validated by `engine.validate_orders` before submission; this
entry concerns lookup helpers only, and no state is ever mutated outside the
engine's own submit/advance path.

## M22-F4 — MG3's registered meter has no visibility gate

See `04_MG3_RANGE_FIDELITY.md`. The frozen PASS compares expected hits at 15 and
17 hexes in a state whose allied visibility is 13 hexes with the radar optional
rule off, so `_can_see` is `False` for both arms and the engine would reject the
fire. MG3 was frozen during the R2.1 repair and never received the visibility
fix applied to MG2/MG4. Historical verdict preserved; diagnosis added.

## M22-F5 — MG4's MANUAL_GOLD is the full-state argmax

The R2.1 gold was itself obtained by searching the full-state corridor
objective, so `F(FULL_STATE_CORRIDOR_CEILING) = 1.000` is an identity rather
than an independent confirmation, and the gold gap is defined by gold vs random
only. The deployable number is `F(PUBLIC) = 0.107`. Disclosed in every artifact
that quotes the MG4 panel.

## Counterexample of record: a rank correlation that would have been misleading

`Spearman(CORRIDOR_BLOB overlap, true route reduction) = +0.676` over the 288
configurations, yet the blob objective's argmax (overlap 5) contains no
informative configuration and the true best configuration scores overlap 1.
Reporting the correlation alone would have implied the public proxy carries
signal usable for ranking. The tie-set decomposition is the evidence; the
correlation is not. Kept as a standing counterexample for the project's use of
rank statistics on tie-dominated spaces.

## M22-F6 — a figure carried the wrong objective's conclusion

The first `fig03` computed the `LEAD_TURN_ALLOWED` objective (max overlap 1, 68
ties) while displaying the conclusion established for `CORRIDOR_BLOB` (max
overlap 5, 4 ties, all uninformative). For `LEAD_TURN_ALLOWED` the statement "the
argmax contains no informative configuration" is **false** — that tie set does
contain the best configuration. The figure now shows both objectives side by
side, each with its own tie set and its own claim: the blob objective's argmax is
uninformative, and the lead objective's argmax is informative-but-unrankable
(4 informative of 68). Recorded because the two facets are easily conflated and
only together support the `PUBLIC_INFORMATION_GAP` diagnosis.
