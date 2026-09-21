# 06_B1E_TORPEDO_CENSUS.md

15 legal torpedo-planning states were found in total (S-01 4, S-03 5, EM-01 6)
against a quota of ≤10 per scenario; every scenario's shortfall is therefore due
to the legal-state supply, not to sampling. All thresholds and arms were frozen
in `PRE_REGISTRATION_B1E.md` §5 before any state was measured.

## Arm means of route reduction

| arm | S-01 | S-03 | EM-01 |
|---|---|---|---|
| HOLD | 0.000 | 0.000 | 0.000 |
| CURRENT_ADAPTIVE (deployed) | **0.000** | **0.000** | **0.000** |
| INTERCEPT_ASSIST (engine combos) | 0.009 | 0.000 | 0.004 |
| PUBLIC_SET_COVER (worst-case) | 0.000 | 0.000 | 0.029 |
| PUBLIC_BELIEF_AWARE (uniform prior) | 0.000 | 0.000 | 0.029 |
| FULL_STATE_CEILING | 0.316 | 0.020 | 0.203 |

## Reading

1. **The deployed adaptive torpedo planner achieves a pooled mean route
   reduction of exactly 0.000** across all 15 states, while firing in 40 % of
   them (6 of 15 states had ≥1 order). It fires; it does not constrain.
2. **Both public arms are also ≈0** (pooled means 0.010 worst-case, 0.010
   uniform-prior). With the corrected per-route payoff they land within 0.03 of
   `HOLD` on average.
3. **The full-state ceiling is 0.02–0.32 depending on scenario**, so the gap
   between what is achievable with full knowledge and what any observable method
   achieves is one to two orders of magnitude. That gap is the census's main
   torpedo finding, and it is what `TORPEDO_PARTIAL_OBSERVABILITY` names.
4. `PUBLIC_BELIEF_AWARE` equals `PUBLIC_SET_COVER` in mean because the uniform
   prior I could justify is flat over three straight-line hypotheses; no legal
   prior narrows it. It is reported as `R_Bayes_UNIFORM` and is never called a
   Bayesian value.

## The `PUBLIC_SET_COVER` sealed-data rule

The arm is required not to read the sealed movement batch. Its route hypotheses
come only from the victim's observed position, heading and speed plus map bounds,
and a **real** leak guard is enforced in code: every hypothesis cell must lie
within `speed + 1` hexes of the observed position and its MF index must not
exceed the observed speed, so a hypothesis built from sealed data raises instead
of passing silently. The inputs used are recorded per state as `public_inputs`.

Note that the leak guard is a guard on the *hypotheses*; the *evaluation* of
every arm's route reduction uses the true route set, which is the correct
experimental design — the arms differ in what they may use to choose, not in how
they are scored.

## Per-state record

`metrics/b1e_torpedo_census.json` carries, for every state: shooter, victim,
route counts, all six arm values, the graded and binary risk panels, the public
hypothesis panel, the per-route best-action count, the public and full-state
chosen configurations, the deployed commander's order count, and the public
inputs. `figures/fig04_b1e_torpedo.png` shows the distributions.
