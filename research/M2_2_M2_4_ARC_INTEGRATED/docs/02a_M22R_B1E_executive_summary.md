# 00_EXECUTIVE_SUMMARY.md — M2.2-R / B1E Exploratory Natural Opportunity Census

```
STAGE = B1E   EXPLORATORY / NOT USED TO OVERRIDE PRIOR GATES
```

## Frozen history (quoted, unchanged)

```
M2.1-R2.1 MECHANISTIC_GOLD_GATE = FAIL_3_OF_5
M2.2      GOLD_COMPILER_GAP     = FAIL / BLOCKED_BY_METRIC_VALIDITY
```

No prior gate is overwritten by anything below.

## PI decisions, as executed

| decision | outcome |
|---|---|
| 1 — L0 intent fidelity and L1 team utility, two roles | L0/L1 frozen; `U_team = FIRE_SEARCH own − enemy EH`; externality defined and reported |
| A — provenance of the BROADSIDE defect first | **`RESEARCH_COMPILER_BUG`** (call-graph evidence; production never converts an intent to a heading) |
| B — save PRE_FIX, repair, unit-test | frozen module untouched; `REPAIRED_INTENT_BASELINE` in a new module; test PASS on (i)/(iii)/(iv), (ii) demoted to a reported diagnostic |
| C — MG1 frozen at both scales | done: `metrics/mg1_dual_scale.json`, reproduction exact |
| 2 — MG3 downgraded, MG3-E added | MG3 = `HISTORICAL_PROXY_PASS / EXECUTABLE_GOLD_INVALID`; **MG3-E = PASS** (9 vs 12 hex, 39 % gap, both arms executable) |
| 3 — MG4 vocabulary | `PUBLIC_PROXY_AMBIGUITY` was the entry state; `PUBLIC_INFORMATION_GAP` is never used; three-way A/B/C split implemented |
| 4 — B1E, not B1 | run; old B1 not restored, old B0 not overwritten |

## B1E verdicts

```
B1E_VERDICT (frozen §7 first-match order) = TORPEDO_PARTIAL_OBSERVABILITY
  movement branch                        = MIXED
  torpedo branch                         = TORPEDO_PARTIAL_OBSERVABILITY
```

### Movement census — MIXED

52 natural states / 104 state-sides (S-01 32, S-03 32, EM-01 40); beam on 49
state-sides by index parity. Quota shortfalls S-01 −4, S-03 −4, EM-01 0; the
`damaged` stratum is **empty** and `late` thin — reported, not back-filled.

> **ERRATUM (M2.3, M22R-F6).** The `damaged` stratum is empty because the
> predicate was dead code (`hull_max` vs the model's `max_hull`), **not** because
> the commanders avoid damage: after the fix, S-01 18/18, S-03 9/9 and EM-01
> 24/33 scanned states qualify. State selection and all rates below are
> unaffected. See `05_B1E_MOVEMENT_CENSUS.md`.

| arm | n | mechanism-opportunity rate | usable-tactical rate | negative-externality rate | median ΔL1 |
|---|---|---|---|---|---|
| BEAM_SEARCH_COMPILER | 49 | 0.245 | **0.694** | **0.020** | **+0.972** |
| REPAIRED_INTENT_BASELINE | 103 | 0.301 | 0.388 | 0.165 | 0.000 |
| CURRENT_INTENT_PRE_FIX | 101 | 0.297 | 0.416 | 0.129 | 0.000 |
| RANDOM_LEGAL | 104 | 0.298 | 0.404 | 0.154 | 0.000 |

What blocks `NATURAL_COMPILER_GAP` is the frozen median relative-gain clause
(0.000 < 0.30); the opportunity *rates* (S-01 0.375, EM-01 0.235, S-03 0.125) and
the externality structure both point the other way, and the median is 0 because
half the states carry no opportunity at all. Both facts are reported; the rule is
applied as frozen. `LOCAL_ONLY_MECHANISM` is explicitly **not** the case: the
beam's team utility rises with its local gain (usable 0.694 vs the branch's <0.10
requirement, median externality +0.861 vs the branch's ≤0 requirement).

### Torpedo census — TORPEDO_PARTIAL_OBSERVABILITY

15 legal torpedo states (S-01 4, S-03 5, EM-01 6; shortfalls 0 because the legal
supply ends there). Six arms.

| arm | pooled mean route reduction |
|---|---|
| HOLD | 0.000 |
| **CURRENT_ADAPTIVE (deployed)** | **0.000** |
| INTERCEPT_ASSIST | 0.004 |
| PUBLIC_SET_COVER | 0.010 |
| PUBLIC_BELIEF_AWARE (uniform prior) | 0.010 |
| FULL_STATE_CEILING | 0.020–0.316 by scenario |

Material per-route commitment regret (`R_shared ≥ 0.25` with distinct best
actions) in **4 of 15 states across 2 scenarios** (S-01 50 %, EM-01 33 %), which
meets the frozen rule. Caveat carried as part of the result: the effect size is
**single-scenario-dominant** — S-01's material states carry full-state ceilings
0.97 and 0.30, EM-01's carry 0.07 and 0.17, S-03 contributes none.

## The four things a reader should take away

1. **The deployed torpedo planner fires and constrains nothing**: 0.000 mean
   route reduction over 15 natural states while submitting ≥1 order in 40 % of
   them. Both observation-only arms land within 0.03 of doing nothing.
2. **The intent compiler's error is fully priced now**: pre-fix −0.056 L0
   (usable mounts 2 → 1) and −11.361 L1; repaired +0.667 L0 (41 % relative) and
   −5.833 L1. The repaired arm is a textbook
   `MECHANISM_SUCCESS_BUT_NEGATIVE_EXTERNALITY`, and in the census the intent
   arms carry 12.9–16.5 % negative-externality states against the beam's 2.0 %.
3. **Only the joint search gains on both scales** (MG1 dual: +0.472 L0 and
   +7.417 L1; census: usable-tactical rate 0.694 with a 2 % negative-externality
   rate). Single-ship compilers, repaired or not, do not reproduce it.
4. **Public proxies are not substitutes for the hidden set.** The straight-line
   public hypothesis set moved `R_shared` in *both* directions relative to the
   true route set (0.200 vs 0.500 in one state, 0.167 vs 0.000 in another), so
   the observational component (hypothesis B) is **not** separated.

## Not established / not measured

- No L2 (long-horizon game value) claim anywhere; deferred to M2.3 by the
  pre-registration.
- Hypothesis B unseparated; a size/diversity-matched subset control over `C(h)`
  is the required next step and is not in this design.
- `damaged`-fleet behaviour has no evidence behind it (empty stratum).
- The `NATURAL_COMPILER_GAP` two-mechanism clause is unsatisfiable by this design
  (M22R-F1); reported in single-mechanism form.

## Failures recorded

M22R-F1 unsatisfiable verdict clause · M22R-F2 degenerate binary per-route payoff
(would have produced a false positive) · M22R-F3 bucket labels dropping mid-game
states · M22R-F4 map-edge `neighbor()` raising · M22R-F5 vacuous leak guard
replaced by a real invariant · plus two counterexamples of record (an
over-specified test demoted to a diagnostic, and the rank-correlation trap).

## Deliverables

`M2_2R_B1E_NATURAL_OPPORTUNITY_BUNDLE.zip` — this file, 01 metric hierarchy, 02
broadside bug, 03 MG3-E, 04 MG4-P, 05 movement census, 06 torpedo census, 07
local-vs-team, 08 public-vs-full-state, 09 next decision, the pre-registration,
registry, claims, failures, manifest, `metrics/`, `figures/`, `logs/`, `cases/`,
`code_patch/`.

Stopped here by instruction. No RL, no GNN, no paper-method design.
