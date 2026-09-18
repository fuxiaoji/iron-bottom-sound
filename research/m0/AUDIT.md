# AUDIT.md — P0 repository audit

**Auditor role**: research execution engineer (not PI). This document reports what
the repository *actually* is at the audited commit. Where it contradicts the M0
plan's expectations, the contradiction is stated rather than smoothed over.

| Item | Value |
|---|---|
| Repo | `fuxiaoji/iron-bottom-sound` (origin verified) |
| Branch at audit start | `codex/v14-budgeted-replanning` |
| HEAD at audit start | `7ab8ac4acdf029e6ea14346d568c3f509abd9390` |
| Working tree at audit start | **clean** (`git status --short` empty) |
| Research branch | `research/m0-validation` (created from HEAD; original branch left untouched) |
| Platform | macOS 26.3, arm64, 10 CPUs |
| Python | 3.14.6 (`.venv`) |
| Research code | `research/m0/` only; no production module modified |

`git reset --hard`, `git clean -fd` and any write to the user's working tree were
not used, per the plan's hard constraints.

---

## 0. Discrepancy with the task statement (reported, not silently fixed)

The task states that `M0_RESEARCH_PLAN.md` is in the repository root. **It is not
present at the audited commit.** The plan was supplied as an external attachment
(`~/Downloads/M0_多主线科研验证执行计划 (1).md`). It has been copied verbatim into
the repository root as `M0_RESEARCH_PLAN.md` (1611 lines) so that the plan is
version-controlled alongside the evidence it governs.

Nothing else in the task statement was found to contradict the repository.

---

## 1. Does Iron Bottom Sound actually have sealed, unexecuted, hidden commitments?

**Yes. This is real, first-class structure, not documentation aspiration.** It is
the single most important prerequisite for Tracks A and B, so it was verified in
the code rather than inferred.

### 1.1 Storage

`backend/src/iron_bottom_sound/models.py:617`

```python
sealed_orders: dict[str, dict[str, OrderBatch]] = Field(default_factory=dict)
```

Keyed by `f"{turn}:{phase}"`, written by:

`backend/src/iron_bottom_sound/engine.py:1712`

```python
@staticmethod
def _seal_orders(state: GameState) -> None:
    key = f"{state.turn}:{state.phase.value}"
    state.sealed_orders[key] = deepcopy(state.submitted_orders)
    state.submitted_orders.clear()
```

**`sealed_orders` is never purged.** A `grep` for `sealed_orders` across the
package returns exactly two sites: the write above (1714) and the read at 1719.
So the full history of every sealed batch persists in state for the whole game —
a research-friendly property (full commitment history is available) that also
means memory grows with turn count.

### 1.2 Hiding is real

`engine.observe()` (engine.py:249) builds `PlayerObservation` from `state.ships`
filtered by visibility, and filters events by `payload["secret_side"]`. It **does
not** include `sealed_orders` in any form. `api.py` is explicit: saved-game
metadata "never include units or sealed orders", and enemy sealed trajectories are
returned only when `debug=true`.

### 1.3 The phase machine creates a genuine pending-commitment window

`engine.advance()` (engine.py:1721) implements:

```
MOVEMENT_PLANNING  --both sides submit-->  _seal_orders()  -->  TORPEDO_PLANNING
TORPEDO_PLANNING   --both sides submit-->  _seal_orders()  -->  MOVEMENT_RESOLUTION
MOVEMENT_RESOLUTION -- executes movement, then--> GUNNERY
```

So at `TORPEDO_PLANNING` **both sides choose their torpedo plans while both
sides' movement orders are already sealed, unexecuted, and invisible to the
opponent.** The torpedo plan must anticipate where the enemy will move, and that
movement is exactly the hidden pending commitment. This is the structure Tracks A
and B are premised on, and it exists in production code today.

### 1.4 Ready-made counterfactual interface

`engine.sealed_movement_trajectories(state, side, debug=False)` (engine.py:966):
"Own side always; enemy plans only when `debug=true`." Exposed over HTTP at
`/games/{id}/sealed-trajectories`, gated to `TORPEDO_PLANNING`. This is a
read-only, side-filtered view of sealed plans — a usable basis for research
counterfactual clones without touching the engine.

---

## 2. Capability inventory actually present at HEAD

| Capability | Status | Location |
|---|---|---|
| `run_match` | present | `match.py:72` |
| `bench.py` parallel benchmark | present (`_run_one` / `ProcessPoolExecutor`) | `bench.py:71`, `207` |
| `replay` from event log | present | `engine.py:1851` |
| snapshots / event log | present (`state.events`, `GameEvent`), `event_visible_to` filter | `engine.py:444` |
| `observe` | present, fog-of-war respected | `engine.py:249` |
| `legal_actions` | present, returns `advance` only when both sides submitted | `engine.py:520` |
| sealed / pending orders | **present as described in §1** | `engine.py:966,1712,1718` |
| `TacticalCommander` | present (`DeterministicCommander` subclass) | `tactical.py:151` |
| `AdaptiveTorpedoPlanner` | present, with `EnemyRouteHypothesis`, `CounterfactualResponse`, `TorpedoDecisionAudit` | `torpedo_tactics.py:107` |
| `rl/psro.py` | present; `--smoke`, `--workers`, `regret_matching` | `rl/psro.py:172,609` |
| `rl/evolve.py` | present (GA + novelty) | `rl/evolve.py:408` |
| strategy / profile pool | `PROFILES` (13), `CHAMPIONS` (1: `evolved`) | `tactical.py:82`, `champions.py:20` |
| scenario list | 15 catalogued | `engine.scenarios()` |
| realistic-command | present, incl. `expand_movement_orders`, `resolve_setup`, `refresh_command_chain` | `realistic_command.py` |
| custom scenario | present (`custom_scenarios.py`, `IBS-CUSTOM-*` ids) | `custom_scenarios.py` |
| state export | present (`export_frame`, `render_board`) | `state_export.py:73,231` |
| deterministic seeds | present (`state.rng_counter`, `seed` on reset) | `models.py` |
| `RandomCommander` | present | `randomai.py:50` |

**Profile names come from the repository, not from memory**: `balanced, fleet,
line, brawl, torpedo, cautious, adaptive, direct_attack, area_denial,
break_crossing_t, formation_split, crossfire, cover_withdrawal` (13), plus
champion `evolved`.

---

## 3. Findings that constrain the M0 plan

### 3.1 Only 3 of 15 catalogued scenarios are playable

```
PLAYABLE: IBS-S-01, IBS-S-03, IBS-S-EM-01
NOT PLAYABLE (12): IBS-S-02, IBS-S-04 ... IBS-S-14
  -> KeyError: "Scenario IBS-S-XX is catalogued but not playable"
```

`engine.scenarios()` returns 15 entries, but `engine.reset()` raises for 12 of
them. **Consequence for Track C**: the plan asks for "at least two scenarios, a
third if realistic performance allows". Three exist, so Track C is feasible but
has no slack — and any claim of breadth across scenarios is limited to three.

### 3.2 Throughput is low, and does not scale with worker count

Measured (see `BASELINE_STATUS.md`): 20 matches of `IBS-S-01` with
`ProcessPoolExecutor(max_workers=20)` took 53.7 s → **0.37 matches/s**, while a
single match takes ~5.2 s on one core. That is a **1.9× speed-up on 10 CPU
cores** — the pool is oversubscribed (20 workers on 10 cores) and does not scale
linearly. Extrapolating naively, the plan's ≤20,000-match budget is ~15 h of wall
clock at this rate, which is inside the plan's limits but leaves little room.

### 3.3 Scenario-independent RNG streams are not obviously separated

`run_match` seeds the engine from `seed`, but the per-side commanders
(`TacticalCommander`, `RandomCommander`) are constructed without a seed argument.
Repeated runs with identical configuration were still bit-identical (see
`BASELINE_STATUS.md` §1), so determinism holds in practice for the deterministic
commanders. It does **not** follow that `RandomCommander` is seed-controlled; that
was not tested and must not be assumed for Track C/D, which need reproducible
opponent randomness.

### 3.4 Not verified

The following were **not** exercised in P0 and are marked unresolved rather than
assumed healthy: LLM-backed players (`deepseek`, `zhipu` — out of scope, M0
forbids paid API), `frontend/` behaviour, `rl/evolve.py` end-to-end runs, custom
scenario creation, and the full pytest suite (still running at report time; see
`BASELINE_STATUS.md` §6 for the partial result).

---

## 4. What this means for the four tracks

| Track | Prerequisite from the repo | Audit verdict |
|---|---|---|
| A (CARP) | an expensive planner that can be called or skipped, over states with a hidden commitment | **available**: `AdaptiveTorpedoPlanner` + sealed movement window; no planner-cost model exists yet |
| B (CAIS) | public observation that is genuinely insufficient | **available**: sealed movement plans are hidden at `TORPEDO_PLANNING` while visible positions are identical |
| C (CD-PSRO) | a strategy pool and a payoff-matrix generator | **available** but only 3 scenarios and 0.37 matches/s |
| D (DiagGame) | agents with distinguishable reasoning defects | **partially**: the profile pool gives behavioural variety, but the profiles are not documented as *mechanism* defects; a defect zoo must be constructed (the exact lab is the cheaper route) |

The audit found **no blocker that invalidates P1**, so P1 proceeded.
