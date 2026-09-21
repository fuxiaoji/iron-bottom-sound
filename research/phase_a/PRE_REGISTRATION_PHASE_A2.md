# PRE_REGISTRATION_PHASE_A2.md

The binding directive is `PHASE_A2_DECISIVE_VALIDATION_PLAN.md` (PI). This file
records the concrete numbers chosen **before** the Phase A.2 measurements, so no
threshold moved after results.

## Track A (audit only — no new simulation)

- Exact oracle = multiple-choice knapsack over increments 0→4→16→64 (costs 4/12/48),
  solved by DP over states × capacity; total budget 16·N.
- Mandatory checks: all-16 feasible; both allocations spend exactly 16·N; identical
  held-out matrix; allocation counts recorded; raw and normalised objectives.
- Gate (unchanged from the PI plan): corrected oracle gain ≥ 0.08 normalised on
  **both** tasks with paired bootstrap CI > 0.

## Track B (valid rerun)

- G = 165 (original grid). M = ceil(2500/G) clipped to [12, 24] = **16**.
- Frozen seed list: `60000 … 60000+M−1`. Universe = seed × grid = **2700**/task.
- K ∈ {25, 50, 100, 200}, admissible because all K ≤ 10 % of 2700.
- **30** acquisition repetitions per task × method × K, `random.Random(1000*rep + K)`.
- GENERIC_ACTIVE: ExtraTreesClassifier(40 trees) on flattened config + initial-state
  descriptor, acquisition = vote entropy, first ¼ of the budget seeded randomly.
- STRUCTURED_ACTIVE: per severity line query mid/min/max, then fill (this is the
  implementation whose weakness the results expose).
- Boundary = adjacent-severity label change inside a fixed
  (seed, agent/subset, window, modality) line; recall = fraction of true edges
  localised within one severity interval.

## Track C (decisive calibration)

- Fault generator **frozen as of Phase A v3.1** (duration 20, severities 0.5/0.8/1.0,
  starts 20/40/60) and not changed after any attribution outcome.
- 50 valid causal failures per task, ≤1000 attempts; <30 valid ⇒
  `C_LOW_YIELD_BLOCKED` for that task.
- Ground truth = minimal successful repair set from the exhaustive 3 agents × 5
  windows matrix; injection metadata stored separately and never read by probes.
- Budgets 10/20/25 % of each case's exhaustive query count; every replay a query.
- Gates unchanged from the PI plan (identifiable, ≥80 % top-k at ≤25 % queries,
  ≥15 pp over RANDOM_CELL and ≥10 pp over AGENT_THEN_TIME_GROUP_TEST on both tasks).

## Red lines carried

No silent drops · no `except: pass` · no threshold changes after results · no task
shopping · no fault-strength change after C outcomes · no fake generic baseline · no
K cherry-picking · no one-task promotion · all numbers script-generated · invalid
runs preserved · stop after packaging.
