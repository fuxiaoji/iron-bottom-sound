# FAILURES_AND_COUNTEREXAMPLES.md — M2.2-R / B1E

## M22R-F1 — a frozen verdict rule referenced a mechanism row the design cannot produce

`PRE_REGISTRATION_B1E.md` §7 froze `NATURAL_COMPILER_GAP` as requiring "≥2
mechanisms in ≥2 scenarios", but the census arm set contains no range-directed
arm: every arm is a broadside/joint-manoeuvre arm, so the census has exactly
**one** local mechanism row (focal-pair legal visible-fire EH). Range's
executable status is established by MG3-E, not by a second census row. The rule
is therefore reported in its single-mechanism form with
`mechanism_rows_in_census = 1` written next to the verdict, and the unsatisfiable
clause is disclosed rather than silently relaxed. Fix for a future census:
either add a range-directed arm (frozen before measurement) or drop the
2-mechanism clause.

## M22R-F2 — the first per-route payoff made the identifiability formula degenerate

`D_bin(c,a) = 1[route c in contact with action a]` produced `R_shared = 1.000`
in three states whose full-state ceilings were 0.071–0.316. With 14–40 compatible
routes and one launch per turn, no action can touch every route, so `R_shared`
saturates at 1 whenever route count exceeds one action's reach: it measured
action-space coverage, not belief conflict, and would have produced a false
`TORPEDO_PARTIAL_OBSERVABILITY`. Repaired to `D_grad` (blocked fraction of the
route's own trajectory), which keeps `V_c` per-route achievable as the formula
presupposes. Both forms are kept in the record; the binary form is the
counterexample. Caught by noticing an exact 1.000 across states whose ceilings
differed by 4x — an exact saturated value is a bug signature, not a finding.

## M22R-F3 — bucket labels silently discarded mid-game states

The first bucket definition was a first-match chain (`early` ≤ turn 3, then
`contact`, `damaged`, `late`), in which `early` shadowed `contact` and any state
at turns 4–7 with no damage and no label was **silently dropped** from the
pool. Replaced before any measurement by multi-label assignment (a state carries
every label it satisfies; the picker never takes a state twice). A residual
defect remains and is reported, not hidden: with only four labels and no `mid`
bucket, S-01 and S-03 cannot fill their 20-state quota from their short games,
and the census's `damaged`/`late` strata are thin or empty (see
`05_B1E_MOVEMENT_CENSUS.md` for the achieved distribution). A future census
should add a `mid` bucket.

## M22R-F4 — map-edge `neighbor()` raises instead of returning None

`HexCoord.neighbor` raises `ValueError("Movement leaves the map")` rather than
returning `None`, so a public-hypothesis walk off the map crashed the first
torpedo census run. Fixed with an explicit `safe_neighbor` that ends the walk,
which is the correct domain semantics: an off-map step is not a legal
hypothesis. The same pattern is handled around `torpedo_step_positions`, whose
edge error is captured per state rather than masked (no bare `except` that
swallows it; the error text is recorded in `current_meta`).

## M22R-F5 — a vacuous assertion where a real leak guard was needed

The first version of the `PUBLIC_SET_COVER` sealed-data guard was
`assert not any("submitted" in str(k) for k in pub_h[0])` — true by construction,
so it protected nothing. Replaced by a **real** invariant: every hypothesis cell
must lie within `speed + 1` hexes of the victim's observed position and its MF
index must not exceed the observed speed. A hypothesis derived from the sealed
batch would violate both and now raises.

## Counterexample of record — the test I over-specified and then demoted

The intent-compiler unit test first asserted that the repaired plan recovers the
gold arm's mount count (3). It recovers 2 (pre-fix 1). I demoted that assertion
to a reported diagnostic rather than weakening it after seeing the number, and
kept the diagnostic in the record
(`metrics/intent_compiler_unit_test.json`): heading 1 carries the maximum 3
mounts at the observed geometry, so the compiled heading is right and the loss is
F18 (simultaneous movement invalidates the pre-movement bearing). Kept as a
standing example of the difference between "the test was wrong" and "the result
was inconvenient".

## Counterexample of record — a rank correlation that would have misled (carried from M2.2)

`Spearman(public proxy overlap, true route reduction) = +0.676` across 288
configurations, yet the proxy's argmax contained no informative configuration.
Rank correlations on tie-dominated spaces are not evidence; the tie-set
decomposition is. Carried forward from `research/m2_2/` because the torpedo
census is where the temptation recurs.

## M22R-F6 (found in M2.3, corrected here) — the `damaged` predicate never fired

`_hull_frac` read `getattr(s, "hull_max", s.hull)`; the model field is
**`max_hull`**, so the fallback silently made `start == now` and the fraction
identically 1.0. The `damaged` label could therefore never be assigned, and the
B1E census reported an empty `damaged` stratum and attributed it to the scripted
commanders not producing hull loss. That attribution was **wrong**, and it was
wrong because of a silently-defaulting attribute read — the same failure shape as
a bare `except` that swallows an error.

Measured after the fix (3 seeds per scenario, all movement-planning states from
turn 2): S-01 18/18, S-03 9/9, EM-01 24/33 states satisfy "≥1 surviving ship with
`hull < max_hull`". So the stratum was never empty; the predicate was dead.

**Impact on the old numbers: none.** `_hull_frac` was used only to assign the
`damaged` label, and the picker selects states by the labels a state carries. A
dead label changes no selection, so the 52-state / 104-state-side census, its
per-arm rates and the MIXED verdict are unaffected. What was wrong is the
*explanation* of the coverage gap, and that is corrected in the M2.1... see the
ERRATUM block in `05_B1E_MOVEMENT_CENSUS.md`.

**Second finding, independent of my bug:** with the predicate fixed it fires at
almost every state, because ships are not at full health to begin with. The PI's
literal damaged rule ("≥1 surviving ship with hull < max_hull, or a key system
down") is therefore not discriminative. M2.3's supplemental panel reports the
literal rule as specified and, beside it, the fraction of states satisfying a
stricter `hull ≤ 0.75·max_hull` threshold, so the conditional probability can be
read against a predicate that actually separates states.
