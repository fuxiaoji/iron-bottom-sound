# 04_EQUAL_BUDGET_BASELINES.md

Every method draws from the **same candidate pool object** (≤6 plans per ship:
production plan, hold, faster, slower, port extreme, starboard extreme) and is
capped at **the same 24 engine-exact joint evaluations** per state.

| method | exact evals used (mean per state, Gate II) | note |
|---|---|---|
| `CURRENT_PRODUCTION` | 1 | the production batch |
| `PER_SHIP_GREEDY_ADDITIVE` | 1 | each ship's surrogate-best |
| `SEQUENTIAL_TEAM_BEST_RESPONSE` | ≤ 2·n (one sweep, top-2 per ship) | coordinate ascent on the **exact** metric |
| `INTERACTION_AWARE_BEAM` | 15 (1 baseline + up to 12 `q_i` probes + up to 10 pairwise probes + 1 final) | model = `U(a0) + Σ q_i + Σ phi_ij`, all terms exact |
| `RANDOM_MATCHED_BUDGET` | 24 | random joints, best kept |

Mean total exact evaluations per state ≈ **44**; per-method counts are recorded per
state (`evals` in `metrics/m24_gate2_coordination.json`).

## Data recorded for every evaluated state

`batch_valid` (the materialised gunnery batch passes `validate_orders` — true for
every reported state), collision events, legal and visible pair counts, aspect mix,
mean engagement range, split-fire ship count and maximum concentration. Across
Gate II: **0 collision events**, all batches valid.

**One more disclosure**: `SEQUENTIAL_TEAM_BEST_RESPONSE` evaluates on the exact
metric while `PER_SHIP_GREEDY_ADDITIVE` does not, so the two differ in *information*
as well as in structure. That is by design — the additive baseline is precisely
"what a per-ship surrogate-only planner does" — but the gap between them should be
read as "exact evaluation helps", not only "coordination helps".
