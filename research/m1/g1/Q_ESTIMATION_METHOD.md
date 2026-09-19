# Q_ESTIMATION_METHOD.md — how Q values are estimated in G1

## Estimand

For a valid pair `(h_A, h_B)` (identical public observation, identical own
state, identical legal actions, different hidden axis movement commitment) and
a shared candidate torpedo batch `a`, we estimate

```
Q_x(a) = value of: submit a for ALLIES at TORPEDO_PLANNING in world x,
         then let both sides play the scripted TacticalCommander("balanced")
         until the game ends.
```

`Q*` (optimal continuation) is not computable in IBS; the plan's allowed
estimation hierarchy is exact local enumeration → deterministic continuation →
simulator rollouts. **We use deterministic scripted continuation**: the engine
is deterministic given (state, dice stream), so each rollout is an exact value
of a well-defined quantity — the *policy-continuation value* under scripted
play. It is not `Q*`; the gap between scripted-play continuation and optimal
continuation is a scope limit that travels with every number in this gate.

## Value functions (pre-declared before evaluation)

| key | definition | role |
|---|---|---|
| `outcome` | +1 allies win / 0 draw / −1 axis win at game end | **primary** (the true game value) |
| `damage_diff` | (axis hull lost − allies hull lost during the continuation) / (total hull at branch), in [−1, 1] | secondary (granularity; the outcome is coarse in short scenarios) |

The reason for two value functions: IBS-S-03 ends with axis winning from most
reachable states, so `outcome` is nearly constant there (observed: all −1 at
turn-2 branches) and regret on it is degenerate; `damage_diff` is continuous.
The G1 gate is evaluated on the **primary** value; `damage_diff` results are
reported alongside as diagnostics.

## Candidate actions (shared across branches, identical set)

Per pair, up to 6 candidate torpedo batches, from the game's own proposal
machinery only:

1. the empty torpedo batch (hold fire);
2. the allies TacticalCommander's own chosen batch in branch A;
3. the allies commander's own chosen batch in branch B (if different);
4. the top-2 `engine.torpedo_assist` combos for the top-2 own torpedo-capable
   ships (assist is documented engine-side as visible-info-only: it does not
   read enemy sealed plans).

A candidate is in the shared set iff it validates in BOTH branches. The count
of shared candidates is known before any Q evaluation (outcome-blind); pairs
with <2 shared candidates are recorded but excluded from the primary analysis
and do not consume the pre-declared pair cap.

`AdaptiveTorpedoPlanner` / heuristic scores are **never** used as Q values —
only as candidate generators, per the plan.

## Dice-stream replicates (CRN)

The engine's dice are `random.Random(seed * 1_000_003 + rng_counter)`.
The strategic state (ships, sealed orders, observations) is untouched; before a
continuation we set `state.rng_counter = c0 + j`, `j = 0..R−1` (R = 5,
pre-declared). Both branches use the SAME offsets, so branch A and B share
dice-stream realisations up to the point where the differing commitment causes
genuine divergence (common random numbers).

Per (branch, candidate): mean over replicates, standard error of the mean.
A pair is `q_ranking_confident` iff, in BOTH branches,
`max_a Q − min_a Q > 2 × max_a SE` (signal exceeds noise).

## Regret quantities

```
V_x        = max_a Q_x(a)
R          = min_a max(V_A − Q_A(a), V_B − Q_B(a))     (shared-action regret)
stake      = max(V_A − min_a Q_A(a), V_B − min_a Q_B(a))
normalized = R / stake  (0 if stake ≤ 1e-9)
```

`normalized` is the fraction of the avoidable loss that NO single shared action
can recover — 1.0 means every candidate is bad in one of the two worlds.

## Scope limits

1. Scripted-play continuation, not optimal continuation (both sides
   `balanced`; the game's own AI is commitment-blind by design —
   `torpedo_assist` reads only visible information).
2. 5 dice-stream replicates: means carry Monte Carlo noise (SEs reported;
   ranking-confidence flag gates interpretation per pair).
3. Candidate set is the game's own proposals (≤6): R is a LOWER bound on the
   regret over all legal torpedo batches; a richer candidate set can only
   shrink R, never inflate it — this bias is conservative for the gate
   (it works AGAINST finding aliasing).
4. Focal side = ALLIES, hidden commitment = axis sealed movement. The symmetric
   window (axis decides gunnery under sealed torpedo plans) is priority 3 and
   not exercised in this checkpoint.


## Amendment G1-POWER-002 (pre-registered before its results were inspected)

The 5-replicate pilot could not satisfy the task's CI rule for 104/120
evaluable pairs (power wall, FAILURES F2). Replicates were increased uniformly
and outcome-blind to 15 for every evaluable pair (main and control-B); pairs,
candidate sets, value functions, and the CI rule were frozen. The 15-replicate
run is the PRIMARY analysis; the 5-replicate run is retained as the pilot.
One analysis bug (a falsy-zero test that discarded `control_a_max_diff == 0.0`,
i.e. exactly the passing value) was found and fixed before the final 15-rep
numbers were read; its only effect was to stop discarding every pair.
