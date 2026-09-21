# PRE_REGISTRATION_M24.md — JTC Interaction-Aware Last-Chance Gate

```
STAGE   = M2.4, the LAST mechanism re-test for JTC. No third surrogate revision.
HISTORY = frozen, never rewritten (see §0).
FROZEN  = every floor, budget, selection rule and PASS condition below is fixed
          BEFORE any measurement.
```

## 0. Frozen history

```
M2.1-R2.1 MECHANISTIC_GOLD_GATE = FAIL_3_OF_5
M2.2      GOLD_COMPILER_GAP     = FAIL / BLOCKED_BY_METRIC_VALIDITY
M2.2-R    B1E                   = TORPEDO_PARTIAL_OBSERVABILITY · movement MIXED
M2.3      JTC = FAIL (separable-surrogate confound M23-F3) · BARD = FAIL
MG3       HISTORICAL_PROXY_PASS / EXECUTABLE_INVALID · SUPERSEDED_BY_MG3E
```

`BARD_MAINLINE = ARCHIVED` (PI decision): no further BARD runs, no S-01 deep dive;
the MG4 route-denial mechanism and the BARD metrics are retained as a future seed
only.

## 1. The question

Does `U(a_1,…,a_N) ≠ Σ_i u_i(a_i)` hold in this game, and can a search that
**explicitly uses agent–agent interaction** beat per-ship greedy at the same
candidate set and the same exact-evaluation budget?

## 2. Interaction definition (frozen)

Around the production baseline joint `a0`:

```
q_i(a_i)      = U_exact(a_i, a_-i^0) − U_exact(a0)
phi_ij(a_i,a_j) = U_exact(a_i,a_j,a_-ij^0) − U_exact(a_i,a_-i^0)
                − U_exact(a_j,a_-j^0) + U_exact(a0)
```

Operationalisation, fixed here: `a_i` is ship i's **additive-surrogate-best**
candidate and `a_j` likewise, so `phi_ij` is the interaction between each ship's
individually-best choice — the quantity that decides whether per-ship greedy is
sufficient. Every `U_exact` call is engine-exact (§4).

```
PRACTICAL_FLOOR_PHI = 0.05   (EH units, the project's absolute floor convention)
PRACTICAL_NONZERO_PAIR  iff |phi_ij| >= 0.05
FLOOR_GAIN          = 0.05   (EH units, for the coordination gain)
```

## 3. Interaction Existence Gate (Gate I)

Ten **pilot states**, selected deterministically: the first ten of the M2.3 frozen
35 common opportunity states in `(scenario, seed, turn, side, intent)` order. No
outcome-based selection, no hand-picking.

On each pilot, all pairs `(i,j)` of the side's ships are scored:

```
report  median |phi| · p90 |phi| · max |phi| · practical-nonzero pair fraction
        positive vs negative interaction counts
        |phi| against inter-ship distance, shared-target indicator,
        obstruction (land between the two), and post-movement concentration count
ADDITIVE_RANK_AGREEMENT = Spearman between the additive-surrogate ranking and the
        exact U ranking over the SAME sampled joint set on that pilot
```

```
INTERACTION_STRUCTURE = ABSENT  iff  > 90 % of pairs have |phi| < 0.05
                                    AND median ADDITIVE_RANK_AGREEMENT >= 0.95
INTERACTION_STRUCTURE = PRESENT otherwise
```

If ABSENT: **stop immediately**, `JTC_INTERACTION_GATE = NOT_RUN`,
`JTC_FINAL_STATUS = PERMANENTLY_KILL`. No further work in this stage.

## 4. Exact evaluation (frozen)

```
U_exact = FIRE_SEARCH own EH − FIRE_SEARCH enemy EH
```

`FIRE_SEARCH` (the repaired M22-F2 version) already enforces: visibility
(`_can_see`), each mount used at most once, engine-exact modifiers, the
attackers/concentration bonus and the target_count/split-fire penalty, primary vs
secondary grouping, and a **validated complete gunnery batch** per side. For every
state reported in this stage the materialised gunnery batch is validated through
`validate_orders` and the result is recorded (`batch_valid`). Additionally
recorded per state-side: collision count during movement resolution, obstruction
(land) between engaged pairs, selected-target concentration, aspect mix, range
distribution and the visibility graph summary.

**The cheap surrogate is used only to guide search; it never decides a verdict.**
Every number in the gates is engine-exact.

## 5. Candidate set (frozen, identical for every method)

Per ship, at most **K = 6** legal movement plans:
current production plan · hold (if legal) · faster · slower · port extreme ·
starboard extreme (falling back to the additive-surrogate-best plan when one of
those is illegal). The identical pool object is passed to every method, and every
joint batch is validated by the full side-level validator before it is played.

## 6. Methods, equal budget (frozen)

```
EXACT_BUDGET = 24 engine-exact joint evaluations per method per state
```

| method | allocation of the budget |
|---|---|
| `CURRENT_PRODUCTION` | 1 (evaluate `a0`) |
| `PER_SHIP_GREEDY_ADDITIVE` | 1: each ship's additive-surrogate-best, played once |
| `SEQUENTIAL_TEAM_BEST_RESPONSE` | greedy sweeps in fixed ship order: for each ship, exactly evaluate its top-2 alternatives (by additive surrogate) with the others at the current best, keep the better, then move on; one sweep (cost ≤ 2n ≤ 24) |
| `INTERACTION_AWARE_BEAM` | 1 for `a0`; up to 12 single-ship probes `(a_i, a_-i^0)` chosen by the additive surrogate, giving exact `q_i`; up to 10 **pairwise probes** `(a_i,a_j,a_-ij^0)` chosen to maximise surrogate rank plus pair diversity, giving exact interactions; the final joint is the argmax of the fitted additive+pairwise model over the additive beam's top survivors and is itself exactly evaluated; remaining budget evaluates more probes |
| `RANDOM_MATCHED_BUDGET` | 24 random joints from the identical candidate set, all exactly evaluated, best kept |

Actual exact-evaluation counts are reported per method and per state; no method may
exceed 24. `INTERACTION_AWARE_BEAM`'s model is `U ≈ U(a0) + Σ_i q_i(a_i) +
Σ_{i<j} phi_ij(a_i,a_j)` with the `q_i` and `phi_ij` it measured, i.e. its
guidance contains real interaction terms, unlike M2.3's additive surrogate.

## 7. Coordination Effect Gate (Gate II)

Main set: the M2.3 frozen 35 common opportunity states, original locators.
Supplemental set (separate, never merged with the main set's prevalence): per
scenario, in `(seed, turn, side)` order, the first 10 state-sides satisfying
(a) ≥2 own ships with ≥2 legal movement alternatives each, and (b) ≥1 legal
visible gunnery pair post-movement; ≤30 states total.

```
Delta_joint_greedy = U_exact(INTERACTION_AWARE_BEAM) − U_exact(PER_SHIP_GREEDY_ADDITIVE)
Delta_joint_seq    = U_exact(INTERACTION_AWARE_BEAM) − U_exact(SEQUENTIAL_TEAM_BR)
```

Reported: mean, median, win/tie/loss, **paired bootstrap 95 % CI** (10 000
resamples over states, seeded), per-scenario split, exact-evaluation counts, wall
time.

```
JTC_INTERACTION_GATE = PASS iff ALL of:
  1. median Delta_joint_greedy > 0 in at least 2 scenarios
  2. pooled win rate >= 0.60
  3. pooled median gain >= FLOOR_GAIN (0.05 EH)
  4. the interaction beam is not significantly worse than sequential team BR
     (paired bootstrap CI of Delta_joint_seq has lower bound > -FLOOR_GAIN)
  5. RANDOM_MATCHED_BUDGET is clearly worse than the interaction beam
     (pooled median of beam − random >= FLOOR_GAIN)
  6. the result is not driven by 1–2 extreme states: after removing the top two
     |Delta_joint_greedy| states, pooled median gain still >= FLOOR_GAIN
JTC_INTERACTION_GATE = FAIL otherwise
```

## 8. Intent: conditional analysis only (frozen)

States are labelled `BROADSIDE / RANGE / RAKING / OTHER` by the intent that the
M2.3 pipeline attached to them (main set) or by the state's own dominant local
change for the supplemental set. Reported: `P(Delta_joint_greedy > 0 | intent)`.
**No intent prevalence gate is applied in this stage.**

## 9. Final outputs (frozen)

```
INTERACTION_STRUCTURE   = PRESENT / ABSENT
JTC_INTERACTION_GATE    = PASS / FAIL / NOT_RUN
JTC_FINAL_STATUS        = SURVIVES_FOR_NOVELTY_REVIEW / PERMANENTLY_KILL
BARD_FINAL_STATUS       = ARCHIVED
IBS_NEXT_ROLE           = METHOD_DISCOVERY_CONTINUES / APPLICATION_BENCHMARK_ONLY
```

Rules: PASS → `SURVIVES_FOR_NOVELTY_REVIEW` and
`METHOD_DISCOVERY_CONTINUES`; FAIL → `PERMANENTLY_KILL` and this is the last
surrogate revision the project will attempt; ABSENT at Gate I → `NOT_RUN` +
`PERMANENTLY_KILL`.

## 10. Integrity

Engine entry points only; no production edit; no rule change; no training; no paid
LLM; no RL/GNN/paper work. Deterministic seeds. Expected budget: Gate I ≈ 450 exact
evaluations, Gate II ≈ 4 500 exact evaluations ≈ 40–60 min.
