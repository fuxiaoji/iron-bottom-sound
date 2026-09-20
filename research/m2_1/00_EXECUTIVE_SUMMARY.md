# 00_EXECUTIVE_SUMMARY.md — M2.1-R2 Mechanistic Gold Decomposition

**Stage A (Mechanistic Gold) complete. GATE = FAIL (3 of 5). Stage B/C NOT RUN
(gated). Stopped per PI instruction.**

```
MECHANISTIC_GOLD_GATE = FAIL (3/5: MG1 PASS, MG2 PASS, MG3 PASS,
                              MG4 FAIL[CASE_CONSTRUCTION_FAIL],
                              MG5 FAIL[TACTICAL_ASSUMPTION_NOT_SUPPORTED])
COMPILER_FIDELITY = NOT_TESTED (Stage B gated)
VALUE_REALIZATION = NOT_TESTED (Stage C gated)
PLATFORM_DIAGNOSIS = NO_VERDICT (but see "the new fact" below)
```

## The decomposition worked — and located the problem

This round separated what every previous round conflated. The rule engine was
measured directly, with no compiler, no neural net, no scripted continuation
between the tactic and the meter:

| mechanism | rule-native measurement | verdict |
|---|---|---|
| broadside vs narrow aspect | +92.9% expected hits at common distance (3 vs 1 mounts bearing) | **priced steeply** |
| crossing the T | own GF 651 vs enemy 486; net exchange 1.68x parallel; 64 longitudinal pairs | **priced steeply** |
| range control (2 hexes for a BB) | 2.56 vs 0.94 expected hits | **priced steeply** |
| torpedo corridor denial | turn-T launches had ZERO effect on T+1 routes (arms identical to 13 decimals) | case construction failed |
| local force superiority | concentrate margin WORSE than disperse (56.6 vs 82.7) — gun range exceeds fleet spacing | assumption unsupported at this scale |

**The rule engine is not the problem.** Heading, aspect and range carry
2-3x consequences inside the rules. This kills the "LOW_LEVERAGE_PLATFORM"
reading at its root: a platform whose rules price a 60-degree turn at +93%
expected hits is not a low-leverage game.

The earlier rounds' flat E0 numbers must therefore come from one or both of:

1. **COMPILER_FIDELITY**: the intent-to-plan compiler (60-degree hex
   quantization + greedy per-ship plan matching) cannot steer fleets into the
   geometries the rules reward. Stage B was built to test exactly this and
   now has sharp per-case targets to test against (the MG geometries).
2. **VALUE_REALIZATION**: the evaluator family (scripted continuation,
   profile pool, local minimax) does not cash in positional advantages that
   the rules would eventually pay out. The G1 adversarial flip (unmasking
   wins at E0, loses at E3) already shows value realization is
   response-dependent.

Stage B and Stage C — now unblurred — are the next two experiments, in that
order, each with a crisp PASS/FAIL against the MG geometries recorded here.

## Integrity notes

- All 5 cases are RESEARCH_MICRO_SANITY_CASEs built from reachable replay
  states; every order passed the full validator; zero state surgery.
- Three new harness failures found and fixed during construction (F16
  opponent torpedo submission, F17 same-launcher duplicate orders, F18
  post-movement bearing staleness) plus one metric gap (F19 D66 vs 2d6
  expectation — expectation must integrate the 36-outcome D66 table).
- Budget: ~2,500 route/continuation evaluations; 0 paid LLM; engine untouched.
