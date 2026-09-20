# 02_RNG_BRANCHING_AUDIT.md — P1

## Mechanism (source-verified)

Every die roll is an **independent** `random.Random(seed * 1_000_003 +
state.rng_counter)` draw; `state.rng_counter` increments by 1 per roll
(engine.py:4369-4385, `_roll_d66` / `_roll_2d6` / `_roll_d6`). There is no
persistent RNG stream object — the counter position IS the stream state.

## Probes (this session)

| probe | result |
|---|---|
| P1.1 same snapshot + same scripted policy + same seed, two runs | bit-identical dice sequences and rng_counter (deterministic: **PASS**) |
| P1.2 same snapshot, `rng_counter` offset by 1 | sequences diverge from the first roll (**offset-sensitive: PASS**) |
| P1.3 branch at turn-2 GUNNERY (S-01, full `advance()` resolution): axis HOLD vs axis FIRE | hold = 45 draws / 18 dice events; fire = **63 draws / 36 dice events**; first dice-sequence divergence at event index 2 |

## Consequence for branching

When two action branches produce a different number of gunnery salvoes,
torpedo checks, collision checks or fire rolls — which is the *normal* case
for genuinely different actions — their `rng_counter` positions diverge and
**every subsequent roll compares different random numbers**. Same initial seed
guarantees identical continuation only while the branch draw counts happen to
match.

```
RNG_PAIRING_STATUS = MATCHED_INITIAL_SEEDS_ONLY
```

Not `TRUE_EVENT_ALIGNED_CRN` (pairing breaks after the first unequal draw
count) and not `UNSAFE` in the sense of non-reproducibility — every
evaluation is exactly reproducible; it is pairing that is not guaranteed.

## Binding consequences for this audit (enforced in VALUE_SEMANTICS)

1. The word "CRN" is banned from all leverage reports; the correct description
   is **matched-seed continuations**.
2. Per-(state, action) value estimates still average over R dice streams
   (`rng_counter` offsets 0..R-1): the offset shifts the whole draw schedule,
   which is a legitimate variance-reduction trick ACROSS replicates of the
   same arm, but cross-arm differences are NOT variance-paired.
3. Because cross-arm noise is unpaired, every leverage statistic must carry
   its bootstrap CI and the plan's "CI 可分辨" requirements apply per state.
