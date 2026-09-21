# FAILURES_AND_COUNTEREXAMPLES.md — M2.3

## M23-F1 — the decisive control was anchored at the wrong position

The matched-kinematics surrogate was anchored at the victim's **pre-movement**
position, while the true routes start from its T+1 position. The displacement made
the surrogate disjoint from every action corridor, so `R_shared` collapsed to
exactly 0.000 in 12 of 14 sets and 3 matched payoff matrices were all-zero. The
tell was the exactness: an all-zero control removes any effect for a reason that
has nothing to do with the hypothesis set. Corrected to each variant's own T+1
start; 3 of 14 matrices remain degenerate and those have all-zero *true* matrices
too. Both runs are kept (`metrics/m23_bard_badanchor.json` is the bad-anchor run,
which would have returned `ARTIFACT`), because a control that decides a verdict
must be auditable against its own failure.

## M23-F2 — joint-vs-greedy compared across different state sets

`PRE_REGISTRATION_M23` §4.2 requires the *same* opportunity-state set for every
arm. The first implementation averaged each arm over its **own** opportunity set,
which compares different states and let greedy look better on a friendlier subset.
Corrected to the common set defined by the intent-constrained arm's successes
(n=35); the corrected numbers are the ones reported (joint 1.048, greedy 1.428,
random 1.831).

## M23-F3 — my joint arm cannot represent coordination (the verdict's confound)

The cheap geometry surrogate is **additively separable** once the enemy's
predicted geometry is fixed: total = `Σ_ship contribution(ship, own plan)`. The
per-ship argmax is therefore the surrogate's **exact** optimizer, so
`PER_SHIP_GREEDY` and `JOINT_BEAM_SEARCH` optimise the same function and the joint
arm cannot win except through real-scored survivors and the intent constraint.
The interaction structure the game actually has — the concentration bonus and
multi-target penalty of `_gunnery_modifiers`, which depend on how many attackers
share a target — is absent from the surrogate and present in the real metric.

Consequence: `JTC = FAIL` is the correct frozen output, but it is **not** evidence
that joint compilation is worthless; it is evidence that this arm cannot test it.
A fair re-test needs a surrogate with interaction terms or direct optimisation of
the real team metric at a small budget, under a new pre-registration.

## M23-F4 — a planner scored on a different set than its competitor

`PUBLIC_BELIEF_EXPECTED` first reported its value **on the matched set** while
`PUBLIC_SET_COVER_ROBUST` was scored on the true set, producing an impossible
comparison (0.336 > full-state ceiling 0.124). Both planners now choose on the
matched set and are scored on the true set.

## M23-F5 — three pipeline repairs needed before BARD could run at all

1. The first construction forked the hidden plan at `TORPEDO_PLANNING`, where the
   victim's movement is **already sealed** — the fork is impossible there by
   definition. Hidden commitments must be forked at `MOVEMENT_PLANNING` and
   carried forward to the torpedo decision instant.
2. `play_movement` advances to GUNNERY; BARD needs to stop at `TORPEDO_PLANNING`.
   A custom advance loop was required, and the first run rejected every variant
   because of it.
3. JTC's first smoke test measured a **degenerate baseline**: a hull-2 target sank
   during movement resolution, so `M(current) = 0` and every arm appeared to gain
   massively. Frozen fix: the admission rule of §4.3 (the focal pair must survive
   the current arm), with rejections counted per panel and scenario.

## Counterexample of record — the killed narrative

`05_JTC_EXTERNALITY.md` was first written with the M2.2 pattern in mind (the
repaired intent as the worst externality offender). The measured pooled rates are
the opposite: repaired intent 0.067, random 0.090, joint 0.107, **greedy 0.161**.
The narrative was rewritten to the numbers and the non-stability of the arm
ranking across state sets is now stated rather than papered over.

## Carried forward from M2.2-R (recorded there, quantified here)

M22R-F6: the B1E `damaged` stratum was empty because the predicate read
`hull_max` instead of `max_hull`. Fixed in `research/m2_2r/scripts/b1e.py`; the
M2.3 damaged panel uses the corrected field and additionally reports that the
literal predicate is non-discriminative (234/234 pool state-sides satisfy it,
217/234 the stricter 0.75·max_hull threshold), so `P(opportunity | damaged)` is
reported as a conditioned rate and never as a damage contrast.
