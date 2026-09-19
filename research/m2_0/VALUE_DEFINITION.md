# VALUE_DEFINITION.md — the value function used by every Track A/C number

**Single source of truth for value.** The pre-registration duplicates it; if
they ever diverge, this file wins and the divergence is a bug.

(Original pre-registration header follows; the value section is the binding
part, the gate thresholds live in PRE_REGISTRATION_A.md.)

Written before any partition value was evaluated in this repository. If a
number in the Track A report disagrees with anything here, the discrepancy is a
protocol violation and must be reported as such.

## Value definition (also in VALUE_DEFINITION.md; single source of truth there)

- **Primary**: `V_H^{eval}` = H-turn horizon continuation value from the
  deciding side's perspective, **scripted continuation**:
  replay the deterministic match to the snapshot; apply the partition's macro
  decisions for the deciding side at this turn; then let **both** sides play
  their normal TacticalCommander policy until `H` further turns elapse or the
  game ends.
- `utility(terminal)` = +1 win / 0 draw / −1 loss (deciding side).
- `utility(terminated-at-h)` = normalized VP swing over the horizon:
  `(myVP_gained − oppVP_gained) / 10`, clipped to [−1, 1] — VP awards in IBS
  are of order tens, this scaling puts typical swings near ±0.1–0.6.
- If the game completes within the horizon, terminal utility wins (the two are
  on the same normalized scale by construction of the clip).
- **Value is a simulator continuation. Heuristic planner scores are never a
  value.**

## Frozen knobs

| knob | value |
|---|---|
| H (discovery) | 1 turn (this turn's macro decisions + 1 scripted turn) |
| H (spot-check) | 2 turns on a fixed 20% subset (same states every time: hash(pair_id) % 5 == 0) |
| rollout reps | 5 dice-stream replicates, common random numbers across partitions (offsets 0..4 added to `state.rng_counter`) |
| opponent policy | scripted TacticalCommander, same profile pair as the source match |
| candidate macro budget | ≤ 7 macro actions per group (HOLD, STRAIGHT_SLOW, STRAIGHT_FAST, TURN_PORT_60, TURN_STARBOARD_60, plus ≤2 leader-proposal plans), identical budget for every partition size |
| candidate partitions | P0 flat, P1 fixed, P2 type, P3 speed, P4 spatial, P5 damage-split, P6 threat-split, P7 one-step neighbors of P1 (≤16), P8 random matched-K (3 draws per K), per plan §9.1 |
| epsilon (safe) | **0.05 normalized value** |
| tie tolerance | 1e-9 |
| snapshots | every MOVEMENT_PLANNING snapshot of the deciding side from discovery matches, capped at 60 per scenario taken in (seed, turn) order — the cap is outcome-blind (applied before evaluation) |
| scenarios | IBS-S-01, IBS-S-03 (EM-01 reserved for spot-check H=2 due to 12-turn length) |
| profiles | balanced vs balanced, fleet vs line, brawl vs cautious (3 pairs × seeds) |
| minimal-safe partition | argmin K over candidates with `L_H ≤ epsilon`, ties → the structured candidate with more membership agreement with P1; L_H = mean over reps of V_flat − V_Pi, per-state CRN pairing |

## A1 gates (verbatim from the plan, §10.1)

1. **State dependence**: ≥30% of movement snapshots have a minimal-safe
   partition whose K or membership differs from the fixed (P1) partition.
2. **Compression**: in ≥2 scenarios, median decision-entity reduction of the
   dynamic candidate-oracle ≥30% with value retention ≥95% (retention =
   V_best-allowed / V_flat at the chosen partition, ≥ 1 − 0.05 by the epsilon
   definition; reported directly).
3. **Need for adaptation**: fixed (P1) grouping has `L_H > 0.05` on ≥20% of
   snapshots, and dynamic candidates recover (bring to ≤ epsilon) at least half
   of those.
4. **Structure beats random**: at equal K, structured partitions beat random
   matched-K (mean L over matched pairs, sign test across states).

`A_FAIL_ORACLE` if flat is always best, fixed is always sufficient, best K is
essentially constant, or random matches structured.

## Compute budget estimate (frozen before measuring)

60 snapshots × ~10 candidate partitions × (1 flat + groups' macro sweeps ≤7
each ≈ ≤20 batch evaluations) × 5 reps ≈ ≤6,000 continuations per scenario —
inside the plan's 50,000 continuation budget. If the measured per-continuation
time makes this exceed ~2.5 h, the snapshot cap drops to 30 per scenario
**before** any result is inspected (mechanics amendment, pre-declared here).
