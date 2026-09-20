# 00_EXECUTIVE_SUMMARY.md — M2.1-R measurement repair + gold-case gate

**Stage stopped per PI stop rule: GOLD_EVALUATOR_GATE = FAIL.**

```
RULE_ENGINE_CONFORMANCE = PASS   (unchanged from M2.1; re-verified)
RNG_PAIRING_STATUS = MATCHED_INITIAL_SEEDS_ONLY
    (replicate scheme REPAIRED: each replicate now uses an independent
     sha256-derived state.seed; all arms of a replicate share it; branch-point
     rng_counter untouched. Matched-seed at seed level.)

ACTION_COVERAGE_MOVEMENT = REBUILT
    intent-based generator (UNMASK_BROADSIDE / CROSS_T / CLOSE / OPEN /
    MAINTAIN / CONCENTRATE / BREAK_CONTACT...), candidates verified to differ
    on 9/9 ships. ORACLE/PUBLIC split designed but only PUBLIC built this round.

MOVEMENT_LEVERAGE = NOT_MEASURED (gate failed before census)
TORPEDO_LEVERAGE = NOT_MEASURED
REALISTIC_COMMAND_LEVERAGE = NOT_MEASURED
GUNNERY_LEVERAGE = INVALID_PENDING_RERUN (PI ruling upheld: the original
    branch never submitted the opponent batch; repaired pipeline verified to
    measure hold-vs-fire correctly: P0 U1 0.0 vs 0.0978)

SCRIPTED_CONTINUATION_ATTENUATION = PARTIAL EVIDENCE
    G1 unmasking wins at E0 (+0.011 T0) but LOSES under adversarial
    opponent (-0.015): positional value exists but is response-dependent.
    G2/G3/G4/G5: E3 compresses E0 spreads by 2-4x.
HORIZON_MASKING = AMBIGUOUS (T0 favors cautious arms, T2 favors tactical
    arms in G3/G4/G5 — a crossover, magnitudes 0.004-0.032)
VICTORY_METRIC_MASKING = UNTESTED

PLATFORM_DIAGNOSIS = UNRESOLVED
IBS_FUTURE_ROLE = NO VERDICT (gate failed before the evidence existed)
B_COMMAND_ORGANIZATION = KEEP_SUSPENDED
NEXT_PI_DECISION_NEEDED =
    1. the gate failed with PUBLIC tactical candidates compiled by a greedy
       per-ship plan matcher (60-degree hex quantization). Options: invest in
       a real intent-to-plan compiler (path-level maneuvers, multi-turn
       shapes) and retry the gate; or
    2. accept that the evaluator family (scripted + profile pool + local
       minimax) cannot price positional value, and demote IBS to an
       application benchmark; or
    3. build the frozen Research Evaluation Policy first (E2/E3-grade), then
       re-run the gate.
```

## What the repair accomplished (all PI items)

1. U1 repaired to the frozen definition (damage VP / constant snapshot VP
   total; sunk = full value); 4/4 unit tests pass (zero/no-damage, enemy
   sunk > 0, own sunk < 0, symmetric = 0).
2. Replicates re-keyed by sha256(snapshot, replicate) seeds; branch-point
   counter untouched; no overlapping-stream offsets.
3. Gunnery branch: opponent batch is now SUBMITTED (not just generated)
   before seal; verified: hold P0 = 0.0 vs fire P0 = 0.0978 in the repaired
   pipeline.
4. Checkpoints redefined to P0/T0/T1/T2/Terminal with phase-machine-exact
   boundaries.
5. Baseline removed as a separate path; POLICY_BALANCED is the scripted
   baseline arm through the identical pipeline.

Plus two self-found harness bugs fixed en route: F9 (gold-case geometry
sampled one advance too early), F10 (heading off-by-one collapsing all
tactical intents into one batch — 9/9 ships identical plans).

## Gold gate (the PI's accept/reject test)

5/5 cases built and evaluated; **0/5 separated at T2 >= 0.05**:

| case | tactical vs cautious (T2, E0) | E3 (adversarial) |
|---|---|---|
| G1 broadside unmasking | +0.003 | **flips negative (-0.015)** |
| G2 crossing the T | +0.012 | wiped (0.074 vs 0.072) |
| G3 range control | spread 0.033 | compressed to 0.009 |
| G4 torpedo corridor (movement proxy) | +0.004 | wiped |
| G5 local force concentration | +0.004 | wiped |

The direction is consistently pro-tactical at T2 in 4 of 5 cases and G3's
range-control spread (0.033) is the largest measured — but everything sits
3-10x below the gate, and E3 either compresses or flips the sign. Under the
plan's own vocabulary: the platform question remains UNRESOLVED between
"scripted/adversarial evaluators flatten real positional value" and "the
candidate compiler cannot express the tactics". The repaired harness is now
good enough to tell them apart — that next measurement is the PI's call.
