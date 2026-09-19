# G1_EXECUTIVE_SUMMARY.md — Iron Bottom Sound natural commitment-induced decision aliasing

**G1_IBS_NATURALITY = FAIL**

**FINAL_M1_STATUS = B_TOY_ONLY** (per the task's stop rule; execution halts here)

| | |
|---|---|
| Branch | `research/m1-decision-state` (from `7f9ed4a`) |
| Data | 273 candidate pairs (200 main + 73 control-B) over the pre-declared grid: {S-01, S-03} × 12 seeds × turns {1..4} × ≤3 near-ship variants (+1 far-ship control variant per node) |
| Q estimation | deterministic scripted continuation (both sides TacticalCommander "balanced"), CRN dice-stream replicates: 5 (pilot) → 15 (pre-registered power extension) |
| Rollout ledger | ≈ 35,000 continuations of the ≈50,000 budget; 0 paid LLM calls; 0 engine modifications |

## Mandated answers

```
Number of valid pairs            = 20 (primary value fn "outcome"; CI-passing)
                                   22 (secondary "damage_diff"; CI-passing)
                                   120 evaluable before the CI rule
Number of scenarios              = 2 (IBS-S-03, IBS-S-01)
Number with normalized regret>=0.10 = 4 (outcome) / 8 (damage_diff) among CI-passing pairs
Fraction with regret>=0.10       = 20% (outcome) / 36% (damage_diff)
Median regret                    = 0.000 (both value fns, CI-passing pairs)
Max regret                       = 0.400 (outcome) / 0.840 (damage_diff)
Controls median regret           = 0.000 (both value fns; control-B CI-passing n=9/10)
Controls fraction >=0.10         = 22% (outcome; n=9) / 10% (damage_diff; n=10)

Public observations truly identical?   YES (sha256 of engine.observe(ALLIES) equal in both branches)
Legal action sets truly identical?     YES (sha256 of engine.legal_actions(ALLIES) equal)
Naturally reachable?                   YES (every branch produced by validate→submit→advance
                                       through the real pipeline; alternative plans drawn from
                                       engine.movement_candidates; no state surgery)
Q estimates reliable?                  YES for ranking within CI-passing pairs (signal > 2×SE
                                       at 15 CRN replicates); NO for 98/120 evaluable pairs,
                                       which fail the task's CI rule at any budget tested
```

## Gate criteria, scored

| criterion | required | measured | verdict |
|---|---|---|---|
| ≥25 nontrivial valid pairs | 25 | **6** (outcome) / **11** (damage_diff) | **FAIL** |
| valid pairs (any reading) | 25 | 20 / 22 | **FAIL** |
| ≥2 scenarios | 2 | 2 | PASS |
| all pairs naturally reachable | yes | yes (REACHABILITY_AUDIT.md) | PASS |
| public/legal/own identical | yes | yes, hashed | PASS |
| hidden commitment only difference | yes | axis-view hash differs, allies-view equal | PASS |
| ≥20% of pairs normalized regret ≥ 0.10 | 20% | 20% (outcome) / 36% (damage) | PASS (boundary on primary) |
| ≥5 strong manually auditable cases | 5 | 8 (strong_cases/) | PASS |
| controls clearly lower | yes | damage: 10% vs 36% — lower; **outcome: 22% vs 20% — NOT lower** | **FAIL** |

Three conjunctive criteria fail → **G1 = FAIL**.

## What the evidence actually says (for the PI)

1. **The phenomenon exists and is auditable.** 10 strong cases where two
   naturally-reachable worlds with byte-identical public observations value the
   shared torpedo candidates so differently that no single action is good in
   both (up to normalized regret 0.84 on material outcome, 0.40 on game
   outcome, both CI-passing). The pipeline is airtight: Control A (same world
   twice) reproduces bit-identically; public/legal/own hashes equal;
   axis-view-only difference.

2. **But its natural density is far below the gate.** Over the full
   pre-declared grid (120 evaluable pairs), only 6–11 pairs are simultaneously
   (a) CI-passing at 15 replicates and (b) nontrivial. The gate's ≥25 is a
   frequency claim, and the measured frequency is ~1 per 11–20 evaluable
   pairs. Running more grid rounds would be threshold-chasing, not evidence.

3. **Confidence and regret anti-correlate at feasible budgets.** Pairs whose
   action rankings are statistically resolvable are mostly pairs where one
   robust action (typically "hold fire") is near-optimal in BOTH worlds →
   regret ≈ 0. High-regret pairs have close, noisy rankings. This is
   structural (scripted-play continuation + the game's own candidate sets),
   documented in FAILURES F2/F4, and it is why the pilot's 5-replicate run
   produced only 8 CI-passing pairs and the 15-replicate extension only 20–22.

4. **Value divergence ≠ decision aliasing.** 65/120 evaluable pairs show
   outcome divergence ≥ 0.2 between worlds — hidden commitments genuinely
   change what will happen. But in most of them the shared candidate set still
   contains an action that is fine in both worlds. The gap between "the hidden
   information matters" and "the hidden information changes the best decision"
   is exactly the gap this gate was designed to measure, and in IBS's torpedo
   window it is large.

5. **The control result is a warning, not a technicality.** On the primary
   value function, distant-ship commitment differences (control B) produce
   ≥0.10 normalized regret as often as near-ship differences (22% vs 20%).
   Outcome-level regret in this window is not specific to commitment proximity
   — essentially any hidden movement difference can propagate to
   decision-relevance through long-run interactions. The rule "G1 requires the
   regret to come from the hidden pending commitment" is satisfied by
   construction in all pairs (that is the only difference), but the stronger
   implicit claim — that decision-relevant aliasing concentrates where
   strategic intuition says it should — did not survive.

## Why this is not a pipeline artifact (checked, not assumed)

- Control A: same world evaluated twice → bit-identical (max diff 0.0 across all 273 pairs).
- The candidate set bias is conservative: R over the game's own proposals (incl. "hold fire") is a LOWER bound over all legal batches; a richer set could only shrink R further (FAILURES F6).
- The 5→15 replicate extension was pre-registered as an outcome-blind amendment (REGISTRY G1-POWER-002) after the pilot hit the power wall; pairs, value functions, candidate sets and the CI rule were frozen throughout.
- One analysis bug (falsy-zero test on `control_a_max_diff`) was found and fixed before the final numbers were read; the fix's only effect was to stop discarding all pairs.

## What would have to be true for this mainline to live (PI decisions, not executed)

- Q from optimal (or search-based) continuation at combat-contact moments instead of scripted-play tails — the scripted tails are the dominant regime-killer.
- Candidate sets covering all legal torpedo batches, not the game's own shortlist.
- A value function tied to the scenario victory margin (S-03's outcome is nearly constant under scripted play).
- If any of these is pursued, it is M2-scale work; per the task's stop rule, nothing further was run.

## Stop

Per the task: G1 FAIL → `FINAL_M1_STATUS = B_TOY_ONLY` → no G2, no OpenSpiel,
no neural training, no DSRL, no PPO, no PSRO expansion. Everything is packaged
in `M1_G1_CHECKPOINT.zip` for PI review.
