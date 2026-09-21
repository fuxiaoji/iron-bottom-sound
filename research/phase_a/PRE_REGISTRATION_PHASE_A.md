# PRE_REGISTRATION_PHASE_A.md

```
FREEZE POINT: this file is written BEFORE any Track A/B/C/D measurement is
inspected.  Every threshold, budget, metric and stop rule below is fixed here.
No threshold may be changed after seeing Track results (plan §11.3).
```

## 0. Scope and role split

Local AI executes, audits and packages; the PI decides the mainline. This stage
outputs `PASS/FAIL/BLOCKED` per track and never `SELECTED_MAINLINE`.

## 1. Frozen environment (see `ENVIRONMENT_LOCK.json`)

```
python 3.9.6 · torch 2.8.0 · vmas 1.5.2 · benchmarl 1.5.2 · torchrl 0.10.1
tensordict 0.10.0 · hydra-core 1.3.7 · numpy 2.0.2 · device = CPU
```

CPU is frozen because MPS measured **2.1x slower** on the navigation pilot
(100k frames: 4m26s on mps vs 2m03s on cpu). BenchMARL's own defaults are kept
except where noted (frame budget, loggers, checkpointing).

## 2. Frozen tasks (two, different coordination structure)

| task | agents | obs/agent | act | coordination structure |
|---|---|---|---|---|
| `vmas/navigation` | 4 | 18 | 2 | per-agent goals + collision avoidance (spread / role assignment) |
| `vmas/balance` | 3 | 16 | 2 | tight continuous coupling on one shared rigid body |

Both are official VMAS cooperative tasks exposed through BenchMARL
(`conf/task/vmas/{navigation,balance}.yaml`); their configs are used unchanged.

## 3. Frozen base policy (A0.2)

```
MAPPO through BenchMARL, share_policy_params=True, BenchMARL defaults otherwise.
3 seeds: 0, 1, 2.  Frame budget: 600,000 per seed (identical across seeds).
Checkpoint interval 120,000 and checkpoint at end; csv logger only; render off.
Selection: the MEDIAN seed by final validation return at the frozen budget —
never the best seed (plan §11.4).
```

There is no public VMAS checkpoint with a matching config, so the training branch
of the A0.2 order of preference applies; this is recorded rather than silently
skipped. A 100k-frame pilot showed navigation reaching mean return ≈0.92 and a
200k-frame pilot showed balance reaching ≈47, i.e. the budget is above the
learning threshold for both tasks while keeping training inside the local budget.

**Saturation rule (A0.2).** If the frozen policy turns out saturated (clean
success ≥95 %) or useless (clean success ≤5 %) on a task, that task is replaced
BEFORE any Track result is inspected, and the replacement and its reason are
written into `BUG_AND_RERUN_LOG.md`. Task switching after Track results is
prohibited.

## 4. Frozen success / failure oracle (A0.3)

Native VMAS signals, checked before perturbation work:

```
navigation: success  iff every agent's final_rew > 0 at episode end
            (native per-agent goal-reached signal)
balance:    success  iff every agent's ground_rew > 0 AND every agent's pos_rew > 0
            at episode end (package held above ground and inside the goal region)
```

If a native predicate turns out unavailable or degenerate (all-success or
all-failure on the 500-episode clean baseline), the fallback is a **pre-registered
return threshold** = the 25th percentile of the clean episode-return distribution
of that task, computed on the clean baseline only. Either way the chosen oracle
is written to `01_ENVIRONMENT_POLICY_AUDIT.md` before perturbations run.

**Clean baseline:** 500 clean evaluation episodes per task per frozen checkpoint
seed (the single median seed), storing per-episode return, success, length,
episode seed. No perturbed episode enters this distribution.

## 5. Track A — adaptive test-time planning

**State collection.** 200 decision states per task, taken from clean episodes of
the median checkpoint, stratified by episode-progress quartile (50 per quartile),
states sampled at fixed stride within each quartile. **No state is selected by its
future planning benefit.**

**Planning operator (measurement tool, not a proposed method).**

```
candidate set      : base joint action + up to 63 sampled/perturbed joint actions
                     drawn from the frozen policy's action distribution
selection rollouts : RNG stream seed_SC = 2000 + state_index
evaluation rollouts: RNG stream seed_EV = 3000 + state_index  (disjoint)
horizon H          : 5 environment steps for both tasks (frozen)
continuation       : the frozen base policy
budgets            : B = {0, 4, 16, 64} candidate evaluations
```

Every state × budget row records: `state_id, task, seed, episode_t, budget,
selected_action_id, search_return, independent_eval_return, simulator_steps,
wall_time, status`.

**Primary quantity:** `Delta(s,B) = EvalReturn(s,B) − EvalReturn(s,0)`.

**Equal-total-compute comparison.** All allocators receive the same total number
of evaluation rollouts across the dataset, i.e. the same mean budget
`B̄ = 16` per state (total = 16 × 200 per task):

```
Uniform-4, Uniform-16, Uniform-64      (fixed per-state budgets; 4 and 64 get the
                                         same TOTAL by scaling the state subset)
RandomAllocation                        (random budget from {0,4,16,64}, same total)
UncertaintyHeuristic                    (allocate by policy action entropy, avail-
                                         ability recorded; if unavailable, reported
                                         as NOT_RUN, never silently dropped)
HindsightOracle                         (per-state budgets chosen with full
                                         knowledge of Δ, same total; analysis only,
                                         never a deployable baseline)
```

**Gates (all three required for the VMAS pre-gate):**

```
A_HETEROGENEITY  = PASS iff the top 25 % of states by positive Δ account for
                   >= 50 % of total positive planning gain, on BOTH tasks
A_ORACLE_ALLOCATION = PASS iff HindsightOracle >= 8 % relative normalised return
                   above the best equal-compute fixed allocation on BOTH tasks,
                   with a paired bootstrap 95 % CI excluding 0
                   (10 000 resamples, seeded)
A_LEARNABILITY   = PASS iff a small held-out predictor (logistic regression or
                   2-layer MLP, inputs available BEFORE planning, split by episode)
                   recovers >= 35 % of the oracle-vs-best-fixed gap AND beats
                   RandomAllocation on BOTH tasks
```

Status: 3 gates + external family → `A_STRONG_PASS`; VMAS pass, external blocked →
`A_PROVISIONAL_PASS`; oracle pass, learnability fail → `A_HEADROOM_NOT_PREDICTABLE`;
oracle fail → `A_KILL`.

**External confirmation:** one independent environment family (SMACv2 preferred).
Time-boxed: if setup is not working within **2 hours**, record `SMACV2_BLOCKED`
and do not substitute a task after seeing results.

## 6. Track B — active coordination-failure boundary discovery

**Perturbation space** `x = (agent, time-window, modality, severity)`, frozen
modalities (no new modality may be added later):

```
M1 observation Gaussian noise   : sigma ∈ {0.05, 0.10, 0.20, 0.40} × obs scale
M2 action perturbation          : {gaussian noise 0.05/0.20, drop prob 0.1/0.3,
                                   one-step delay}
M3 agent dropout                : agent's action replaced by zero-hold for a
                                   window of 1/3/5 steps
```

Axis grids: agent ∈ all agents (and pairs for M3), time-window start ∈ 5 evenly
spaced steps, severity ∈ the frozen sets above. **Hidden evaluation pool target
2 000–5 000 configurations per task** (dense grid, evaluated once, analysis-only).
Un-queried rows are hidden from every active algorithm.

**Boundary point (pre-registered):** a configuration whose local neighbourhood
(±1 agent, ±1 time-window step, ±1 severity step; modality neighbours) contains
both success and failure outcomes.

**Discovery metric (validated in positive control Toy B):** a boundary cell is
DISCOVERED at K queries iff (a) it was queried and at least one neighbour was
queried with the opposite label, or (b) two of its neighbours were queried with
opposite labels. A diffuse "any queried neighbour" definition was rejected in the
toy because it rewards uniform coverage rather than transition localisation.

**Budgets:** `K = {25, 50, 100, 200}`. **Baselines:** Random · Latin/stratified
random · generic black-box uncertainty sampling (action-entropy surrogate) ·
structure-aware acquisition (per-column bisection on the ordered axes,
round-robin; validated by Toy B).

**Gates:**

```
B_NONTRIVIAL_BOUNDARY = PASS iff failure fraction ∈ [5 %, 50 %] over the
                        pre-registered severity range on >= 2 tasks
B_ACTIVE_EFFICIENCY   = PASS iff structure-aware / random boundary recall
                        >= 1.8x at the same K on BOTH tasks, bootstrap CI > 1
B_MULTIAGENT_STRUCTURE= PASS iff structure-aware beats the generic active baseline
                        by >= 15 % relative boundary recall on >= 2 tasks/seeds
```

Status: all + external → `B_STRONG_PASS`; VMAS all → `B_PROVISIONAL_PASS`;
active-vs-random passes but structured-vs-generic fails →
`B_GENERIC_ACTIVE_LEARNING_ONLY`; non-trivial boundary fails → `B_KILL`.

## 7. Track C — budgeted counterfactual failure attribution

**Failure generation.** ≥ 200 failed trajectories per task from the same frozen
policy, each with **exactly one** injected fault from the frozen distribution:

```
action replacement/drop (probability 1/3) · observation corruption (1/3) ·
one-step delay (1/3)
injection time: uniform over the middle 80 % of the episode
injected agent: uniform over agents
```

The attribution method **never** sees injection metadata. A failure is kept only
if a clean counterfactual rerun confirms the injected event materially caused it
(the episode would otherwise have succeeded). Rejected cases are counted.

**Exhaustive attribution matrix** on a 50-trajectory calibration subset:
counterfactual repair over every plausible agent × time-window cell; a cell is
causal iff repairing it restores native success (or raises return above the
pre-registered repair threshold = the clean-baseline 25th percentile). Reported:
causal cells per failure, minimal repair-set size, uniqueness/ambiguity, sparsity.

**Budgeted probes** at 10 %, 20 %, 25 % of the exhaustive matrix: Random ·
temporal binary-search · agent-first-then-time · influence-prioritised probe from
observable trajectory features (no injection metadata).

**Gates:**

```
C_IDENTIFIABLE     = PASS iff >= 70 % of valid failures have a unique or <= 3-cell
                     minimal repair set
C_QUERY_EFFICIENT  = PASS iff the best non-exhaustive strategy reaches >= 80 % of
                     exhaustive top-1/top-k accuracy using <= 25 % of the queries,
                     on BOTH tasks
C_NONTRIVIAL       = PASS iff Random and temporal binary search are each
                     >= 15 percentage points worse than the best structured probe
                     on held-out trajectories
```

Status: all pass → `C_PROVISIONAL_PASS`; only exhaustive works →
`C_TOO_EXPENSIVE`; binary search solves it → `C_TRIVIAL`; diffuse causes →
`C_KILL`.

## 8. Track D — conditional, reuses Track B data only

Activated only if, on Track B episodes: ≥ 30 % of perturbed episodes recover
(return to within 10 % of the clean return before episode end) AND recovery time
has meaningful variance (IQR > 0). Then compare no-intervention · always-on
fallback · hindsight-best intervention time, and compute recoverable headroom.
`D_KILL` if the oracle timing headroom is < 10 % on either task. No learned
recovery controller is designed in Phase A.

## 9. Resource accounting and stop rules

- Equal budget means equal budget: rollouts, simulator steps, counterfactual
  queries and wall time are counted per method (plan §11.6).
- Every attempted row gets one registry row: `SUCCESS / REJECTED_WITH_REASON /
  ERROR_WITH_TRACE` (plan §11.1, §11.2). No `except: pass` anywhere.
- Missingness audit by task/seed/method is mandatory (plan §11.9).
- A bug run is preserved as `INVALID` and the fixed experiment reruns from zero
  (plan §11.5).
- Hindsight/oracle labels never feed a deployable baseline (plan §11.7).
- All summary numbers are generated from the raw CSV/JSONL by script (plan §11.8).
- Budget: 0 paid LLM; local CPU only; training ≤ 20 h; ≤ 100 000 additional
  simulator episodes/rollout branches for the tracks; a track stops immediately
  after a hard kill gate (plan §10).

## 10. Status vocabulary (frozen)

```
Track A: A_STRONG_PASS | A_PROVISIONAL_PASS | A_HEADROOM_NOT_PREDICTABLE | A_KILL | BLOCKED
Track B: B_STRONG_PASS | B_PROVISIONAL_PASS | B_GENERIC_ACTIVE_LEARNING_ONLY | B_KILL | BLOCKED
Track C: C_PROVISIONAL_PASS | C_TOO_EXPENSIVE | C_TRIVIAL | C_KILL | BLOCKED
Track D: D_PROVISIONAL_PASS | D_KILL | NOT_ACTIVATED | BLOCKED
```
