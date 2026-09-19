# 03 — Track A: Dynamic Decision-Entity Abstraction

## Infrastructure (D0)
`ResearchGroupExecutor` on classic semantics: partition (of ALL alive own
ships — the validator requires full-fleet coverage, F4) + one macro per group
from {HOLD, STRAIGHT_SLOW, STRAIGHT_FAST, TURN_PORT_60, TURN_STARBOARD_60,
LEADER_PROPOSAL} -> per-ship MovementOrders -> engine validator. No-silent-
repair verified; deterministic; 5/6 tests pass (1 declared skip: no divergent
plan-table pair in the test snapshot; the illegal-proposal counterexample
covers the same contract).

## Mechanics amendments (all pre-result, in PRE_REGISTRATION_A.md)
A-MECH-01: per-partition greedy macro search in full context was infeasible
(>75 min/snapshot); groups now choose macros independently (others at HOLD).
A-MECH-02: macro selection uses rep=0 only; reported partition values keep the
5-replicate CRN. A-MECH-03: the pre-declared snapshot-cap fallback fired
(60 -> 30/scenario). The independence approximation biases partition values
DOWN, i.e. it makes the A1 gates harder — conservative direction for a kill.

## Oracle results (60 snapshots captured; 35 usable with flat + >=1 partition
evaluated; 25 dropped by validator/continuation failures — recorded in
metrics/a_partition_eval.json)

| gate | required | measured | verdict |
|---|---|---|---|
| State dependence (minimal-safe != fixed) | >=30% | **48.6%** (17/35) | PASS |
| Compression, median saving | >=30% in >=2 scenarios | **60%** (S-01) / **77.5%** (S-03) | PASS |
| Value retention | >=95% | ~100% (epsilon-capped by definition) | PASS |
| Fixed grouping has loss > 0.05 | >=20% | **11.4%** (4/35) | **FAIL** |
| Dynamic candidates recover >= half of those | yes | 4/4 (all of them) | PASS |
| Structure beats random matched-K | clear | 18.4% win-rate (7/7/24) | **FAIL** |
| Flat not always best | required | flat tied-best on **71%** (25/35) | **FAIL** |

## Why A_FAIL_ORACLE despite two PASS gates

The compression numbers are real but empty: grouping is nearly always
lossless, so of course one can "save 60-77% of decision entities" — but flat
control is the tied-best partition on 71% of snapshots and the L=0 mass is
68% of all partition evaluations. The oracle's minimal-safe K is 1-2 almost
everywhere (min-safe-K distribution: {1:16, 2:14, 3:4, 5:1}); structure does
not beat random grouping at equal K (18.4% win-rate, 62% ties). The plan's own
kill condition — "flat 永远最好 / best K 基本恒定 / random grouping 一样好" —
is met on all three clauses. Under scripted-play continuation, HOLD-biased
group behaviour is near-optimal from almost every movement state; there is no
value left on the table for a dynamic partition to recover. A2 learnability is
moot (nothing to learn toward) and was skipped per the oracle-first discipline.
