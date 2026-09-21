# PRE_REGISTRATION_B1E.md — Exploratory Natural Opportunity Census

```
STAGE      = B1E  (Exploratory Natural Opportunity Census, M2.2-R)
STATUS     = EXPLORATORY / NOT USED TO OVERRIDE PRIOR GATES
FREEZENESS = every threshold, arm and decision rule below is fixed BEFORE any
             B1E measurement is taken.  Nothing here is tuned after seeing data.
```

## 0. Frozen history (quoted, never overwritten)

```
M2.1-R2.1  MECHANISTIC_GOLD_GATE = FAIL_3_OF_5
M2.2       GOLD_COMPILER_GAP     = FAIL / BLOCKED_BY_METRIC_VALIDITY
MG3        HISTORICAL_PROXY_PASS / EXECUTABLE_GOLD_INVALID
MG4        PUBLIC_PROXY_AMBIGUITY = CONFIRMED
```

The old B1 census is **not** restored and the old B0 is **not** overwritten.
B1E results are exploratory and may not be cited as a prior gate's outcome.

## 1. Metric hierarchy (PI Decision 1)

| level | question | definition |
|---|---|---|
| **L0 intent / mechanism fidelity** | "was the intent correctly compiled?" | focal ship → its recorded target: legal visible-fire EH, usable mount count. Broadside: mounts + focal→target EH. Range: focal→target legal visible EH. Torpedo: RouteReduction / safe-route contraction. |
| **L1 team tactical utility** | "is this local tactic good for the fleet?" | `U_team = FIRE_SEARCH own EH − FIRE_SEARCH enemy EH` at the post-movement / pre-fire state |
| **L2 long-horizon game value** | deferred to M2.3 | **no L2 claim is made in B1E** |

`ExternalityGain = delta_team − delta_local` (both against the state's
CURRENT_POLICY arm). A state is flagged
`MECHANISM_SUCCESS_BUT_NEGATIVE_EXTERNALITY` iff `delta_local > 0` and
`delta_team < 0`. Per the PI: this flag is **not** a compiler failure.

Note the deliberate asymmetry, frozen here: **L1 uses `FIRE_SEARCH`**, not
`LEGAL_FIRE_HEURISTIC`. B1E therefore recomputes L1 rather than reusing the M2.2
fleet panel (which used the heuristic). Both evaluators remain in the record.

## 2. BROADSIDE intent bug (PI Decision — provenance first)

`A. PROVENANCE` is decided before any fix, from call-graph evidence, and recorded
in `02_BROADSIDE_COMPILER_BUG.md`:

- `mg_cases.intent_plans` is defined in `research/m2_1/scripts/mg/mg_cases.py` and
  called only from research scripts (`m22_b0.py`, and `mg_cases.py`'s own
  micro-cases). Production `TacticalCommander` does not call it, does not accept
  an intent string as a planning input, and scores each reachable
  `(hex, final_heading)` with the engine's own `ship_gun_pressure` — so the
  defect class (a hand-written desired-heading offset) has no production path.
  Verdict: **`RESEARCH_COMPILER_BUG`**.

`B. PRE_FIX` — the unmodified frozen function is preserved verbatim at
`research/m2_1/scripts/mg/mg_cases.py` (**not edited**, because
`CURRENT_INTENT_PRE_FIX` must stay reproducible) and its outputs on the frozen
MG1 case and on every census state are saved under `cases/` (arm
`CURRENT_INTENT_PRE_FIX`).

`C. FIX` — the repair lives in a new module
`research/m2_2/scripts/intent_compiler.py` as `repaired_intent_plans`, named
`REPAIRED_INTENT_BASELINE` in every table. Its translation rule is frozen here:

> For each own ship, take the bearing `b` to its nearest visible enemy. Among the
> six candidate headings, choose the heading `h` that maximises the number of the
> ship's own non-destroyed mounts whose firing arcs contain
> `_relative_aspect(position, h, target_position)` — i.e. the intent is compiled
> by consulting the ship's own arc table, not a value function and not a search
> over plans. Ties break to the smaller `|h − b|`, then to the clockwise heading.

`D. UNIT TEST` — `research/m2_2/scripts/test_intent_compiler.py` must assert, on
the frozen MG1 case: (i) `repaired` never returns the narrow arm's plan for the
focal ship; (ii) `repaired`'s focal plan yields usable mount count equal to the
gold arm's; (iii) `pre_fix` still returns the narrow arm's plan (the reproduction
guard that proves the frozen module was not mutated); (iv) on a synthetic
target-bearing sweep over all six bearings, the repaired plan's relative aspect
is never dead-ahead/dead-astern when an abeam heading is legal.

## 3. MG3-E — Executable Range-Control Gold (PI Decision 2)

New case. The old MG3 stays recorded as
`HISTORICAL_PROXY_PASS / EXECUTABLE_GOLD_INVALID` and is **not** a confirmed
executable mechanism.

Selection rules, applied in this order, with **no** look at EH magnitude:

1. same focal shooter / same focal target within the state;
2. two legal movement arms for the focal ship, both validated by the engine;
3. both arms' post states have `_can_see(focal → target) = True`;
4. ≥1 mount bears on the target in **both** arms;
5. the two arms' post distances differ by ≥2 hex **or** straddle a real
   breakpoint of the range-modifier table (`rules.range_modifier("gunnery", d)`);
6. identical radar / optional rules across arms (same state, same turn);
7. **states are scanned in (scenario, seed) order and the first state satisfying
   1–6 is taken** — never selected on observed EH size.

Measured with `FIRE_SEARCH` + engine-validated batches; reported per arm: legal
own EH, legal enemy return EH, net EH, distance, visibility, selected mounts and
targets.

**MG3-E PASS gate (frozen):** executable (rules 3–4 hold in both arms) **and**
`local_gap = |EH_pair(CLOSE) − EH_pair(OPEN)|` satisfies `≥ 0.05` absolute
**and** `≥ 25%` relative to the larger arm. Otherwise `MG3E = FAIL` and Range is
excluded from the census entirely (no Range row is reported).

## 4. MG4-P — Public Identifiability Test (PI Decision 3)

Current status may only be written `PUBLIC_PROXY_AMBIGUITY = CONFIRMED`. The
phrase `PUBLIC_INFORMATION_GAP` is **not** used. Three distinct hypotheses are
kept apart: **A** representation/objective gap, **B** belief gap, **C**
irreducible public insufficiency.

Test on a public history `h` (the shooter's observation at TORPEDO_PLANNING) with
compatible hidden sealed routes `c ∈ C(h)` and legal torpedo actions `a`:

```
D(c,a) = route reduction of action a against hidden route c
V_c    = max_a D(c,a)
R_shared(h) = min_a  max_c [ V_c − D(c,a) ]      # minimax shared-action regret
R_Bayes(h)  = min_a  E_c [ V_c − D(c,a) ]        # UNIFORM prior unless a legal
                                                 # public prior is justified
DIFFERENT_BEST(h) = argmax_a D(c,a) differs across c ∈ C(h)
```

Frozen implementation choices:

- `C(h)` = the victim's engine-legal next-turn route set, derived only from
  states the shooter can actually observe plus the public rules — **and** the
  full-state route set, reported as `C_FULLSTATE`. Because
  `C_observed ⊆ C_FULLSTATE`, any regret computed on `C_FULLSTATE` is a **lower
  bound** on what a public actor faces; the bound direction is recorded in every
  table so the sign of the approximation is never ambiguous.
- `R_Bayes` is reported only as `R_Bayes_UNIFORM_PRIOR`; it is not claimed to be
  a Bayesian value under a legitimate prior.
- **Material** iff `R_shared ≥ 0.25` **and** `DIFFERENT_BEST`.

Decision rule (frozen): `TORPEDO_PARTIAL_OBSERVABILITY` requires material regret
in **≥ 20% of torpedo decision states, in ≥ 2 scenarios**. Below that, the MG4
finding stays `PUBLIC_PROXY_AMBIGUITY` and MG4 remains `STRONG_RESEARCH_SEED`,
not a main line.

## 5. B1E census design

Scenarios: `IBS-S-01`, `IBS-S-03`, `IBS-S-EM-01`.

**State ordering (no hand-picking):** states are enumerated in
`(scenario, seed, turn)` order, seeds ascending from 1, and taken until the quota
is filled; stratification is by turn phase bucket only (`early` = turn ≤ 3,
`contact` = first turn with ≥ 3 legal engagements per side, `damaged` = a side
lost ≥ 25% hull, `late` = turn ≥ 8). A state carries **every** label it
satisfies and is never picked twice; the picker round-robins the four labels in
the fixed order early, contact, damaged, late, taking the first unused matching
state in scan order. If a bucket cannot be filled within the scanned seeds,
the shortfall is reported as a number, never back-filled.

- **Movement: 20 states / scenario** (60 total), both sides, post-movement
  pre-fire instant.
- **Torpedo: ≤ 10 legal torpedo-planning states / scenario** (≤ 30 total).

**Movement arms:**
`CURRENT_POLICY` · `CURRENT_INTENT_PRE_FIX` (bug provenance only, **not** a
candidate method) · `REPAIRED_INTENT` · `BEAM_SEARCH_COMPILER` ·
`RANDOM_LEGAL matched-budget`.

Budgets (frozen): per ship ≤ 8 legal plans; beam width 64; every surviving joint
batch played through real simultaneous movement to the pre-gunnery state; enemy
plans byte-identical across arms on the same state; RANDOM_LEGAL = 8 seeded
draws per state for the mechanism's lever ship, mean reported, draw count matched
across arms.

Budget scoping (fixed before measurement): the four cheap movement arms run on
**both** sides of every state; `BEAM_SEARCH_COMPILER` runs on one side per state
chosen by the state's index parity — a rule that consults no arm's output, so
the expensive arm's side cannot be picked to favour a method.

**Torpedo arms:** `HOLD` · `CURRENT_ADAPTIVE` · `INTERCEPT_ASSIST` ·
`PUBLIC_SET_COVER` · `PUBLIC_BELIEF_AWARE` (only if a legal prior is justified;
otherwise reported `NOT_RUN_NO_LEGAL_PRIOR`) · `FULL_STATE_CEILING`.

`PUBLIC_SET_COVER` **must not** read the sealed movement batch: its objective is
expected/worst-case spacetime coverage over route hypotheses compatible with the
public history only. Violation of this rule voids the arm (asserted in code).

Torpedo report per state: RouteReduction, SharedActionRegret, BayesRegret (if
defined), Current-vs-Public, Public-vs-FullState.


### 5.1 Lever-pair definition (added before any B1E measurement; a definition, not a threshold)

The L0 subject of a state is fixed from the **pre-movement** geometry only:
among the focal side's ships and the opposing ships, take the pair with the
largest number of the ship's non-destroyed mounts bearing on the enemy at the
current geometry; ties break by ship id, then enemy id. No arm's output and no
EH value enters this choice, so L0 is comparable across arms and cannot be
selected to favour a method.

## 6. Opportunity definitions and thresholds (frozen)

Per state and per mechanism, with `delta_X = M_X(arm) − M_X(CURRENT_POLICY)`:

```
MECHANISM_OPPORTUNITY(s)      : best-arm delta_local  ≥ 0.05 absolute AND ≥ 25% relative
USABLE_TACTICAL_OPPORTUNITY(s): best-arm delta_team   ≥ 0.05 absolute AND ≥ 25% relative
TEAM_BENEFICIAL_OPPORTUNITY(s): MECHANISM_OPPORTUNITY(s) AND delta_team > 0
```

Rates are reported per scenario and pooled; the median relative gain of
`BEAM_SEARCH_COMPILER` over `CURRENT_POLICY` is reported beside them.

## 7. Final verdict rules (frozen, mutually exclusive, first match wins)

```
TORPEDO_PARTIAL_OBSERVABILITY : material regret in ≥20% of torpedo states in ≥2 scenarios
NATURAL_COMPILER_GAP          : ≥2 mechanisms in ≥2 scenarios with
                                MECHANISM_OPPORTUNITY rate ≥20%, AND median
                                SEARCH-over-CURRENT local gain ≥0.30 relative,
                                AND RANDOM clearly worse (median random local gain
                                ≤0.5 × median SEARCH local gain on those states),
                                AND not driven by one scenario
LOCAL_ONLY_MECHANISM          : MECHANISM_OPPORTUNITY rate ≥20% in ≥2 scenarios
                                while USABLE_TACTICAL_OPPORTUNITY rate <10% and
                                median externality ≤ 0
MECHANISM_RARE                : every mechanism's MECHANISM_OPPORTUNITY rate <10%
NO_NATURAL_GAP               : MECHANISM_OPPORTUNITY <10% for all mechanisms AND
                                no material torpedo regret AND median SEARCH-over-
                                CURRENT relative gain <0.10
MIXED                         : anything else
```

Range rows exist only if `MG3E = PASS`. Broadside rows always exist. The
verdict's inputs (`rates`, `medians`, `scenario coverage`) are all printed
alongside it, so the mapping can be re-checked by hand.

## 8. Budget and integrity

- Engine-only measurement: `validate_orders` / `submit_orders` / `advance`,
  `_gunnery_modifiers`, `_mount_can_bear`, `_can_see`, `movement_candidates`,
  `movement_trajectory`, `movement_cost`, `torpedo_tactical_combos`,
  `_project_torpedo_path`, `ship_gun_pressure`. No state surgery, no RNG
  manipulation, no production edit.
- No paid LLM calls. No training. No L2 claims. No rule changes.
- Expected wall clock: movement census ~45-75 min (60 states × ~5 arms + 60 beam
  searches at width 64); torpedo census ~30-50 min; MG3-E and MG4-P < 15 min.
- Everything reproducible from the recorded seeds; every number in the bundle
  traces to a JSON in `metrics/`.
