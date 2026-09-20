# PRE_REGISTRATION.md — M2.1-R2 Mechanistic Gold gates (frozen before any measurement)

All thresholds below were fixed before any MG case was constructed or
measured. Micro cases are labelled RESEARCH_MICRO_SANITY_CASE: they validate
the measurement chain and rule mechanics, and are never paper evidence.

## Case construction rules (all cases)

- Every action order passes the full engine validator. No state surgery.
- States come from real matches (replay-derived) at deterministic
  (scenario, seed, turn); the search is by declared precondition only.
- Measurements at phase == GUNNERY (post-movement, pre-fire) unless the case
  needs another exact point (MG4 route resolution).
- All engine-native APIs: `_mount_can_bear`, `_target_aspect`,
  `expected_gunnery_hits`, `_gunnery_modifiers`, `gunnery_assist`,
  `_legal_speed_range`. No heuristic scores as ground truth.

## Gates (rule-local metrics, fixed now)

| case | pre-registered gate |
|---|---|
| MG1 BROADSIDE | broadside arm has ≥ +25% own available main-GF that can bear, or ≥ +25% expected hits, vs narrow arm (same position, same distance — pure-turn plans, cost 0) |
| MG2 CROSSING_T | in CROSS arm: own usable GF > enemy usable GF AND net exchange (own EH − enemy EH) > 0 AND enemy-bow_stern-fraction ≥ 50%; AND CROSS net exchange ≥ 1.25× PARALLEL net exchange |
| MG3 RANGE_CONTROL | long-GF ship's expected hits at favorable range ≥ +25% vs unfavorable; report penetration and torpedo-reach flips alongside |
| MG4 REAL_TORPEDO_CORRIDOR | RouteReduction = 1 − safe_routes(torpedo)/safe_routes(no-torpedo) ≥ 0.25 AND (best-response route identity differs between arms OR BR-route torpedo damage > 0 in torpedo arm) |
| MG5 LOCAL_FORCE | expected-hit margin (own EH − enemy EH) in good geometry ≥ +25% better than bad geometry, OR own active-firing-ship count strictly higher in good geometry |

## Mechanistic Gold Gate

PASS requires ≥ 4 of 5 cases showing the pre-registered direction with the
stated margin. On FAIL: stop, and classify each failing case as
CASE_CONSTRUCTION_FAIL / RULE_IMPLEMENTATION_ISSUE /
TACTICAL_ASSUMPTION_NOT_SUPPORTED. No compiler work, no value work.

## Stage B (only on PASS): compiler fidelity

Intent compiler must reproduce, for each of CROSS_T_PORT /
CROSS_T_STARBOARD / UNMASK_BROADSIDE / RANGE_CONTROL /
CONCENTRATE_LOCAL_FORCE / TORPEDO_SCREEN, geometry within the case's
separation margin: % ships whose plan changed, available-GF delta,
expected-hit delta, longitudinal-target count, local-force ratio,
route-denial metric. Gate: compiler achieves ≥ 50% of the gold-case
mechanistic effect per intent (median over its ships). Compiler FAIL with
Mechanistic PASS ⇒ PLATFORM_OK / COMPILER_FAIL (evaluator is not blamed).

## Stage C (only on A+B PASS): value realization

Mechanistically-good and bad arms evaluated under E0 (scripted), E2 (local
tactical minimax), E3 (adversarial profile) to P0/T0/T1/T2 (+terminal
subset). Readings:
- mechanistic strong + E0 flat + E2 strong → SCRIPTED_FLATTENING
- mechanistic strong + all evaluators flat → LOCAL_TACTIC_NOT_LONG_HORIZON_VALUABLE
- mechanistic strong + all evaluators strong → PLATFORM_LEVERAGE_CONFIRMED
"""
