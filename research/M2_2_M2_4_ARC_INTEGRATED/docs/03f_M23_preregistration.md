# PRE_REGISTRATION_M23.md — Mainline Disambiguation cheap-kill

```
STAGE      = M2.3  (cheap-kill between two candidates; no final model is trained)
FROZEN     = every threshold, arm, state rule and control below is fixed BEFORE measurement
HISTORY    = frozen and never overwritten (see 01_HISTORICAL_STATUS.md)
```

## 0. Candidates

**A. JTC — Joint Tactical Compilation.** Given a high-level intent `z`, compile a
legal joint action `a_{1:N} = C(s,z)` such that the local mechanism fires
(`M_z ≥ τ_z`) *without* damaging `U_team`. The object is the conflict between
local intent fidelity and team utility under hard constraints and simultaneous
movement — not single-ship intent generation.

**B. BARD — Belief-Aware Route Denial under Hidden Commitments.** The same public
history admits several legal hidden sealed routes that call for different torpedo
actions, and no single action is ε-good for all of them.

Exactly one of `JOINT_TACTICAL_COMPILATION / BELIEF_AWARE_ROUTE_DENIAL / NONE` is
returned. "Both" is not an allowed answer.

## 1. Frozen metrics

```
L0 (intent fidelity)  intent-specific, per §3
L1 (team utility)     U_team = FIRE_SEARCH own EH − FIRE_SEARCH enemy EH
ΔM = M(method) − M(CURRENT_PRODUCTION_POLICY)      per intent
ΔU = U_team(method) − U_team(current)
Externality = ΔU − ΔM
```

Every arm is a **complete side batch**: full validator, simultaneous movement,
measured at the post-movement / pre-gunnery instant.

## 2. JTC state sets (supplemental only — the old prevalence is never rewritten)

```
B1E-S_SUPPLEMENTAL
  MID      deterministic windows: S-01 turns 3–5 · S-03 turns 2–3 · EM-01 turns 4–8
           target 10–15 state-sides per scenario
  DAMAGED  event-conditioned: per scenario, in (seed, turn) order, take the first
           state-sides where ≥1 surviving own ship has hull < max_hull or a key
           system down; max 10–15 per scenario
```

`MID` and `DAMAGED` are reported **separately**; `P(opportunity | damaged)` is a
conditional probability and is never mixed into a natural prevalence. The old 52
state / 104 state-side census and its rates stay exactly as recorded in
`research/m2_2r/`.

## 3. JTC intent families (≥3, frozen)

| id | intent | L0 (local mechanism) | research compiler rule (per-ship, no value search) |
|---|---|---|---|
| **I1** | Broadside / firepower unmask | focal legal bearing mounts + focal→target legal visible EH | arc-count rule: choose the heading whose `_relative_aspect` is in the most own mount arcs (`REPAIRED_INTENT_BASELINE`) |
| **I2** | Executable range control | focal→target legal **visible** EH, both arms visible with ≥1 bearing mount (the MG3-E definition) | heading toward the target (CLOSE) or 180° off it (OPEN); the arm reports the better direction and records both |
| **I3** | Raking / crossing-T geometry | selected-target **bow/stern fraction** among own legal firing pairs | choose the reachable (hex, heading) maximising the count of legally engageable enemies presenting bow/stern to us via the engine's `_target_aspect`; ties by fewer turns |

I3 is a new compiler target and does **not** touch the old MG2 verdict. A state
counts as an I3 opportunity only if the search finds one.

## 4. JTC methods (5, frozen)

| method | definition |
|---|---|
| `CURRENT_PRODUCTION_POLICY` | the deployed `TacticalCommander(profile="balanced")` batch — the baseline for ΔM/ΔU |
| `REPAIRED_RESEARCH_INTENT` | the intent compiler of §3, per-ship, research baseline. `CURRENT_INTENT_PRE_FIX` is carried **only** for bug provenance and is not a baseline; the research-only bug is never charged to production |
| `PER_SHIP_GREEDY` | each ship independently maximises its own contribution to the cheap geometry surrogate; the concatenation is played. This is the "stitch local optima" control |
| `JOINT_BEAM_SEARCH` | beam width 64 over per-ship plan pools (≤8 plans/ship); partial ordering by the additive cheap surrogate; the **top 8 survivors** are played through the real engine and scored by the real metrics |
| `RANDOM_MATCHED_BUDGET` | 8 joint plans drawn uniformly from the same per-ship pools, played through the real engine |

**Budget matching (frozen):** beam and random both receive **8 real engine plays**
per (state, intent). This is deliberately conservative for JTC — B1E's beam
real-scored all 64 survivors, so JTC is evaluated with a weaker beam than the one
that produced the B1E numbers.

**Intent constraint (frozen):** the beam's final selection is lexicographic —
among the 8 real-scored joints whose real `M_z` ≥ `M_z(CURRENT)`, take the largest
real `U_team`; if none qualifies, take the joint with the largest `M_z`, then
`U_team`. The surrogate prunes, the real engine decides.

### 4.1 Per-intent opportunity floors (clarification fixed before measurement)

`MECHANISM_OPPORTUNITY` is evaluated in each intent's **own units**, so the
generic "≥0.05 absolute and ≥25 % relative" is instantiated as:

| intent | local M | opportunity floor |
|---|---|---|
| I1 | focal→target legal visible EH | ΔM ≥ 0.05 EH and ≥25 % relative |
| I2 | signed range change `d(current) − d(arm)` in hexes | \|ΔM\| ≥ 2 hex AND both arms executable (visible and ≥1 bearing mount) AND relative team gain ≥25 % and ≥0.05 absolute |
| I3 | bow/stern fraction among own legal firing pairs | Δfraction ≥ 0.05 and ≥1 legal raking pair in the arm |

`TEAM_BENEFICIAL_OPPORTUNITY` = opportunity AND ΔU > 0, for every intent.

### 4.3 Admission rule (fixed before measurement)

A state-side enters the JTC panel only if the focal pair **survives movement
resolution under the `CURRENT_PRODUCTION_POLICY` arm** (both ships alive with a
position at the post-movement instant). Enemy movement is byte-identical across
arms, so the filter is arm-independent and cannot favour a method. Rationale: a
pair that dies during movement makes `M(current) = 0`, against which every arm
looks like a large positive `ΔM` — a manufactured opportunity, observed on the
first smoke-test state where a hull-2 target sank during movement resolution.
Rejected state-sides are **counted and reported** by reason and by
panel/scenario; they are never silently dropped.

### 4.2 Joint-vs-greedy comparison (fixed before measurement)

Because a mean can be negative, "≥25 % relative" is frozen as

```
mean ΔU(JOINT) >= mean ΔU(X) + 0.25 * max(0.05, |mean ΔU(X)|)      X in {GREEDY, RANDOM}
```

evaluated on the same opportunity-state set.

## 5. JTC outputs and PASS

Reported per (intent, state): `mechanism opportunity`, `team-beneficial
opportunity`, `conditional median team gain` (median ΔU **conditioned on
opportunity states**), `negative-externality rate`, `joint-vs-greedy gap`,
`search-vs-random gap`, per-scenario consistency.

```
JTC_MULTI_INTENT            = PASS iff >=2 intent families reach a team-beneficial
                              opportunity rate >= 20% in >= 2 scenarios
JTC_JOINT_COORDINATION_EFFECT = PASS iff on opportunity states JOINT_BEAM's mean ΔU
                              is positive AND exceeds PER_SHIP_GREEDY's by >= 25%
                              relative AND exceeds RANDOM_MATCHED's by >= 25 %
JTC_VERDICT = PASS iff both of the above AND the result is not carried by the
              research BROADSIDE bug (i.e. it holds for the intents whose compiler
              is not the fixed one, I2/I3) AND no single scenario owns it
JTC_VERDICT = FAIL otherwise
```

## 6. BARD information sets

An information set `h` is a `TORPEDO_PLANNING` state at turn T. Hidden commitments
are the opponent's **sealed movement plans** for turn T, which are unresolved at
that instant, so every variant of `h` has:
- an identical public observation hash (`eng.observe`) and
- an identical focal legal torpedo action set,

by construction; only the sealed route differs. Verification is enforced in code
and recorded per set.

```
K = up to 6 legal victim movement plans per information set, taken in the
    engine's own deterministic candidate order (never chosen by outcome)
```

## 7. BARD payoffs, risks, control

```
D(c,a)          route reduction of action a over the route set that sealed plan c
                produces at T+1  (= fraction of c's legal routes blocked)
V_c             = max_a D(c,a)
R_shared(h)     = min_a max_c [ V_c − D(c,a) ]
R_Bayes_UNIFORM = min_a mean_c [ V_c − D(c,a) ]     (uniform; no legal prior exists)
CROSSOVER(h)    = the per-state argmax action is not the same for all c
EPS_GOOD(h)     = exists a legal a with D(c,a) >= V_c − 0.25 for every c
material(h)     = R_shared >= 0.25 AND CROSSOVER
```

**Matched size/diversity control (the decisive test).** `C_match(h)` is built from
the true hidden set by a **matched-kinematics straight-line surrogate**: each true
route is replaced by the straight-line walk from the observed start that achieves
the same net displacement and the same MF length. This matches, by construction,
cardinality, route-length distribution, endpoint spread and the pairwise
trajectory-distance distribution, while being constructible by a public actor.
Subsets are **never** chosen by regret. `R_shared` is computed on the true set,
the matched set, and the naive straight-line set.

```
BARD_MATCHED_CONTROL = PASS iff R_shared(C_match) >= 0.25 and material(h) holds
                       on the matched set for >= 20% of information sets
BARD_ACTION_CONFLICT = PASS iff crossover is present in >= 20% of information
                       sets and no ε-good shared action exists in >= 20 %
```

Public planners (never reading the sealed batch):

| planner | objective |
|---|---|
| `CURRENT_ADAPTIVE` | the deployed commander's torpedo batch |
| `SIMPLE_PUBLIC_PROXY` | lead pursuit on the observed course (the naive hypothesis) |
| `PUBLIC_SET_COVER_ROBUST` | `max_a min_{c ∈ C_match} D(c,a)` |
| `PUBLIC_BELIEF_EXPECTED` | `max_a mean_{c ∈ C_match} D(c,a)` |
| `FULL_STATE_CEILING` | `max_a max_c D(c,a)` — not deployable |

```
BARD_PUBLIC_RECOVERY = PASS iff the best public planner's mean D over the true
                       hidden set is >= 50 % of the full-state ceiling's AND
                       exceeds CURRENT_ADAPTIVE and SIMPLE_PUBLIC_PROXY by >= 25 %
BARD_VERDICT = PASS                 iff BARD_MATCHED_CONTROL and BARD_ACTION_CONFLICT
                                    and BARD_PUBLIC_RECOVERY, across >= 2 scenarios,
                                    not carried by S-01
BARD_VERDICT = INFORMATION_LIMIT_ONLY  iff the conflict survives the matched
                                    control (>= 20 %, >= 2 scenarios) but the
                                    public planners cannot recover >= 50 %
BARD_VERDICT = ARTIFACT             iff the matched control removes the effect
                                    (< 20 % after matching)
BARD_VERDICT = FAIL                 otherwise
```

## 8. Mainline selection rule (frozen)

```
MAINLINE_CANDIDATE = JOINT_TACTICAL_COMPILATION   if JTC = PASS and BARD != PASS
                     BELIEF_AWARE_ROUTE_DENIAL    if BARD = PASS and JTC != PASS
                     NONE                         if neither passes, or if both pass
                                                  (a tie is not resolved here; the
                                                  PI decides, and "both" is not an
                                                  allowed answer from this stage)
```

## 9. Budget and integrity

- Engine entry points only, as in `research/m2_2r/`: no state surgery beyond the
  engine's own submit/advance path, no RNG manipulation, no production edit, no
  rule change, no training, no paid LLM.
- Expected wall clock: JTC ≈ 50–70 min (66 supplemental states × 3 intents ×
  ~19 real plays), BARD ≈ 5 min, verdict/figures ≈ 2 min.
- Everything reproducible from recorded seeds; every number traces to a JSON in
  `metrics/`.
