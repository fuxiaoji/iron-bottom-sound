# PRE_REGISTRATION_PHASE_A3.md

```
FREEZE POINT: written before any Phase A.3 measurement. The binding plan is
PHASE_A3_BC_DECISIVE_PLAN.md (PI); this file fixes the concrete numbers,
orders and implementations. Nothing may change after results are seen.
```

## 0. Scope

- Track A: finished (`A_KILL_CONFIRMED`); no further compute.
- Track B: acquisition-only rerun on the **existing immutable label tables**
  (balance + sampling, 2700 labelled configurations each). No relabeling.
- Track C: generator feasibility calibration (C0) → fresh collection (C1) →
  exhaustive matrices (C2) → query tournament (C3). The material-causality
  semantics are **frozen** (balance native; sampling clean ≥ Q50 = 204.03,
  faulted < Q25 = 160.57, drop ≥ 0.5·IQR = 41.685).

## 1. Track B — frozen protocol

### 1.1 Label tables (immutable)
`raw/track_b_a2/labels_{balance,sampling}.csv` — 2700 rows each = 16 frozen
initial seeds (60000+i) × 165-cell perturbation grid. Reconciliation
(attempted = success + rejected + error) is re-verified from the registry
before use. These files become the evaluation universe; no row is added.

### 1.2 Boundary definition (per plan §2.3)
Within a fixed `(initial_seed, agent/subset, time_window, modality)` line, sort by
severity. A **true transition edge** is an adjacent severity pair with different
labels. Primary metric `boundary_recall@K` = fraction of true edges localised to
within one severity interval, i.e. both severity levels of the true adjacent pair
were queried in that line. Also reported: failure fraction, transition-line
fraction, multi-transition and non-monotone line fractions, failure discovery rate.

### 1.3 Acquisition positive control (§2.4, must run first)
Synthetic pool mirroring the real line geometry (mix of 4-level, 2-level and
1-level severity lines; monotone latent thresholds; a frozen fraction of lines
transition-free). The **corrected STRUCTURED_ACTIVE** — endpoint probes then
bisection that strictly shrinks a candidate transition interval — must beat RANDOM
at K=50 **and** K=100. Otherwise `B_MEASUREMENT_BLOCKER`.

### 1.4 Methods and budgets (§2.5)
K = {25, 50, 100, 200} (all ≤ 10 % of 2700). 30 repetitions per
task × method × K. Identical pool metadata for every method. Full query traces
saved per repetition.

- `RANDOM` — uniform over the pool.
- `STRATIFIED_RANDOM` — stratified by (modality, affected agents), no labels.
- `GENERIC_ACTIVE` — ExtraTreesClassifier(40 trees) trained **only on queried
  labels**, acquisition = vote entropy, frozen diversity tie-break, first quarter
  of the budget seeded randomly.
- `STRUCTURED_ACTIVE` — corrected implementation: frozen line order (sorted by
  line key); unprobed lines receive endpoint probes; disagreeing endpoints open a
  candidate interval that is **bisected** until the adjacent flip is localised;
  cross-line allocation is round-robin over unresolved lines, using only queried
  evidence and pre-query metadata.

### 1.5 Gates (§2.6, unchanged)

```
B_NONTRIVIAL_BOUNDARY  both tasks failure fraction 5–50 % AND >= 20 % of severity
                       lines contain >= 1 transition
B_ACTIVE_EFFICIENCY    STRUCTURED/RANDOM boundary recall >= 1.8 on both tasks at the
                       same preregistered K <= 100, bootstrap ratio CI > 1
B_MULTIAGENT_STRUCTURE STRUCTURED >= 15 % relative gain over GENERIC_ACTIVE on both
                       tasks at the same K <= 100, CI of difference > 0 on both,
                       not driven by one modality
```

Verdicts: all pass → `B_PROVISIONAL_PASS`; beats random but not generic →
`B_GENERIC_ACTIVE_ONLY`; valid run but fails → `B_KILL_FOR_MAINLINE`; cannot
complete → `B_BLOCKED`. **No further rescue run.**

## 2. Track C — frozen semantics, calibrated generator

### 2.1 What may not change
Valid-failure requirement (first 50 per task, ≥30 minimum), balance native
semantics, sampling Q50/Q25/0.5·IQR semantics, fault families (action drop,
observation corruption, delay), one affected agent, contiguous window, no
terminal-state manipulation. The v3.1 23-case matrix is **not** A.3 evidence.

### 2.2 C0 grid (frozen before calibration)
Locality cap: window ≤ min(8 steps, 10 % of the 100-step horizon) = 8; one agent.
Base strength 1× refers to the largest previously used severity (act_drop p = 0.5,
obs_corrupt σ = 0.3); multipliers scale it (probabilities clipped at 1.0). Windows
start at step 40. The affected agent rotates deterministically
(`agent = episode_index mod n_agents`) so the estimate is not agent-specific.

Ordered settings (first-in-band wins; band = 10 % ≤ yield ≤ 30 %):

```
act_drop     : (p=0.5, w=8) → (p=1.0, w=8) → (p=1.0, w=4) → (p=1.0, w=2) → (p=1.0, w=1)
obs_corrupt  : (σ=0.3, w=8) → (σ=0.6, w=8) → (σ=1.2, w=8) → (σ=1.2, w=4) → (σ=1.2, w=2) → (σ=1.2, w=1)
act_delay    : (delay=2, w=8) → (delay=4, w=8) → (delay=4, w=4)
```

### 2.3 C0 protocol
Dedicated calibration seeds (80 000+; never reused later). Per setting: **100
paired episodes** (clean twin + faulted twin on identical initial states, batched
vectorised). Yield = valid-causal-failure fraction under the frozen semantics.
Accept a setting iff yield ∈ [10 %, 30 %], lower 95 % confidence bound > 5 %,
runner error rate ≤ 1 %. **No repair matrix and no attribution outcome is
inspected during C0.**

### 2.4 C0 verdict
Per task: ≥2 families accepted → `PASS`; exactly 1 → `C_GENERATOR_NARROW`;
0 → `C_GENERATOR_FEASIBILITY_FAIL`. Mainline eligibility: both tasks ≥ NARROW and
at least one task with ≥2 accepted families. If sampling needs whole-agent or
whole-episode failure, C is killed.

### 2.5 C1 (only after C0 passes)
Frozen accepted settings; **fresh** evaluation seeds (90 000+); ≤1000 attempts per
task; collect the first 50 valid causal failures in deterministic seed order; every
attempted row kept; <30 valid ⇒ `C_GENERATOR_GENERALIZATION_FAIL`. Injection
metadata sealed separately, hidden from attribution.

### 2.6 C2 / C3
Exhaustive repair matrix per accepted failure: 3 agents × 5 window slots = 15
counterfactual replays; ground truth = minimal successful repair set. Tournament:
`RANDOM_CELL`, `TIME_BINARY`, `AGENT_THEN_TIME_GROUP_TEST` (mandatory),
`INFLUENCE_PRIORITIZED` at 10/20/25 % budgets, bootstrap by episode. Gates
`C_IDENTIFIABLE` (≥70 % minimal set ≤3 cells on both tasks), `C_QUERY_EFFICIENT`
(≥80 % top-k within ≤25 % on both tasks), `C_NONTRIVIAL` (≥15 pp over RANDOM_CELL
and ≥10 pp over AGENT_THEN_TIME_GROUP_TEST, CI > 0, both tasks). Verdicts per plan
§7. **No third rescue round.**

## 3. Selection rule (PI)

`B_PROVISIONAL_PASS` → ACTIVE_FAILURE_BOUNDARY eligible; `C_PROVISIONAL_PASS` →
BUDGETED_COUNTERFACTUAL_ATTRIBUTION eligible; neither → `NONE`. The local AI does
not choose.

## 4. Red lines carried
No silent drops · no `except: pass` · C semantics unchanged · no attempt-cap
inflation · no attribution outcome in calibration · no new tasks/fault families ·
no fake generic baseline · no favourable-K cherry-picking · no one-task promotion ·
invalid runs preserved · all aggregates script-generated · stop after packaging.
