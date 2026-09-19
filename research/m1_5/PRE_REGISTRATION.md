# PRE_REGISTRATION.md — M1.5 Stage-1 thresholds, fixed before any Stage-1 number was computed

Written before E1-T1 / E2-T1 produce any aggregate (histogram, CDF, rate).
Where prior M1 knowledge exists it is declared explicitly rather than hidden.

## E1-T1 (rho distribution over the M1 G1 pair population)

**Data**: `research/m1/g1/g1_analysis15.json` — the 15-replicate primary
analysis of M1 G1: 200 main pairs, 120 evaluable (≥2 shared candidates),
each pair = one information state `s` with two consistent hidden commitments
`C(s) = {A, B}`; `rho(s) = min_a max_x [V_x − Q_x(a)]` is exactly the G1
shared-action regret R recomputed from the stored Q tables.

**Population scope (declared up front)**: this population conditions on an
existing hidden-commitment difference (near-ship variants). The unconditional
base rate of rho over all IBS states is trivially lower (most states have no
live commitment difference). E1-T1 therefore measures the *conditional*
distribution — the one that matters for "when a commitment difference exists,
does it force an action change".

**Definitions, fixed now**:

| quantity | definition |
|---|---|
| `rho_abs` (outcome) | `min_a max_x [V_x − Q_x(a)]` in win units (±1) |
| `rho_abs` (damage) | same on the damage_diff value function (fraction of combined hull) |
| `rho_norm` | `rho_abs / stake`, `stake = max_x (V_x − min_a Q_x(a))` |
| low-rho | `rho_norm < 0.05` OR `rho_abs < stake floor` |
| high-rho (meaningful) | `rho_norm ≥ 0.10` AND `rho_abs ≥ stake floor` |

**Stake floors (pre-registered, with rationale)**:

- damage value function: **0.02** — two percent of combined fleet hull,
  ≈ one destroyer's hull worth of material swing; below this the difference
  cannot alter tactical behavior materially.
- outcome value function: **0.10** — ten percentage points of win
  probability.

**Prior-knowledge disclosure**: during M1 I reported the G1 stake
distribution (median 0.036, max 0.235 on damage). The 0.02 floor sits below
that median with the domain rationale above; it was fixed before computing
any E1-T1 aggregate (no histogram/CDF/rate was computed or looked at before
this file was written).

**E1-T1 gate (pre-declared)**:

PASS requires ALL of, on the CI-passing subset (full evaluable set reported
alongside as secondary):

1. ≥ 50% of states low-rho;
2. ≥ 10% of states high-rho (meaningful, i.e. passing both the normalized
   and the absolute floor);
3. among high-rho states, median `stake` ≥ the floor (high-rho is not a
   tiny-stake normalization artifact).

FAIL (`E1_FAIL_DISTRIBUTION`) if any of: nearly all rho low; nearly all high;
high-rho concentrated at sub-floor stakes.

## E2-T1 (influence ranking disagreement)

**Data**: fresh sampling of reachable TORPEDO_PLANNING states (no rollout
Q-values — Stage 1 is heuristic-level only): ≥200 states, ≥2 scenarios
(IBS-S-01, IBS-S-03), profiles sampled from the repo's own PROFILES
(balanced, torpedo, cautious, line, adaptive — fixed list now).

**Scorers (fixed now)**:

- `Direct-only`: rank candidates by `expected_hits` (engine-expected immediate
  hits; ties by salvo size). No influence term.
- `Influence-only`: rank by the influence composite below; direct hits ignored.
- `Hybrid`: `expected_hits + lambda * influence_composite` with `lambda = 1.0`
  fixed now (no tuning later).

**Influence composite (pre-declared)**: whatever subset of the following
fields the current-HEAD `AdaptiveTorpedoPlanner` actually exposes per
candidate, each normalised to [0,1] across the state's candidates and averaged
with equal weights: `forced_deviation`, `speed_loss`, `fire_position_loss`,
`crossing_t_loss`, `formation_split`, `local_force_ratio_gain`,
`route_changed`. If a field does not exist at HEAD it is dropped and the
dropped list is reported (no field is invented).

**Top-1 disagreement**: share of states where Influence-only's top candidate
differs from Direct-only's top candidate (primary), and where Hybrid's top
differs from Direct-only's (secondary).

**E2-T1 gate (pre-declared)**: PASS requires ≥20% of states with a Hybrid-vs-
Direct top-1 change AND ≥30 strong interpretable cases (candidates, both
scores, and the influence fields of the changed decision dumped for manual
reading). FAIL (`E2_FAIL_NO_SIGNAL`) if the rate is below 20%.

**Rollout ledger**: E2-T1 state sampling consumes matches-to-TORPEDO_PLANNING
only (no continuations); every match started is counted.


## AMENDMENT E2-T1-PROFILES (before any E2-T1 result was produced)

The pre-registered profile list (balanced, torpedo, cautious, line, adaptive)
is unworkable at HEAD: profiles with `torpedo_doctrine="legacy"` never invoke
`AdaptiveTorpedoPlanner` at all (the commander branches to the legacy assist
path), so they produce no counterfactual influence fields — precisely the
"verify fields at current HEAD, do not trust old documents" case the plan
calls out. Amended list = the five doctrine-bearing profiles that do exercise
the counterfactual machinery: **adaptive, direct_attack, area_denial,
break_crossing_t, crossfire**. No E2-T1 aggregate had been computed when this
amendment was written.
