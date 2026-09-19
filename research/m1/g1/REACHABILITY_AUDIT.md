# REACHABILITY_AUDIT.md — how G1 pairs are constructed and why they are legal

## What counts as "naturally reachable" in this gate

A pair is accepted only if BOTH branches are produced by the game's own legal
pipeline from a single shared pre-state. No board coordinate, ship attribute,
sealed order, phase, or score field is ever hand-edited. The full chain:

```
IronBottomEngine.reset(scenario, seed, GameOptions(mode="llm"))
  ↓  (both sides = TacticalCommander("balanced"), the game's own AI)
loop: commander choose_plan → engine.submit_orders (engine validates; invalid
      ⇒ run aborted and recorded) → engine.advance
  ↓  at MOVEMENT_PLANNING of a target turn:
X_A = axis commander's own movement batch        (what actually happened)
Y   = allies commander's own movement batch
pre_state = deepcopy(state)                      (shared ancestor)
  ↓
X_B = X_A with ONE axis ship's plan replaced by an alternative plan string
      taken from engine.movement_candidates(state, ship, include_plans=True)
      — the engine's own enumeration of legal plans for that ship at that state
      (formation/forced-constraint aware). Nothing else in the batch changes.
  ↓
branch A: clone(pre) → validate(X_A) ✓ → submit → validate(Y) ✓ → submit → advance
branch B: clone(pre) → validate(X_B) ✓ → submit → validate(Y) ✓ → submit → advance
  ↓
assert phase == TORPEDO_PLANNING in both branches
```

Every `validate_orders` result along the chain must be `valid=True`; a failure
aborts the pair and is recorded in `logs/gen_failures.json`.

## The five pair conditions and how each is verified

| condition | verification |
|---|---|
| public observation identical | `sha256(engine.observe(game_id, ALLIES).model_dump())` equal across branches — this is the game's own fog-of-war-filtered observation (ships, visible events, score, markers), not a custom projection |
| own current state identical | the two branches are clones of the same pre-state; additionally the allies' own sealed movement batches hash equal (`own_sealed_hash`) |
| own pending orders identical | at TORPEDO_PLANNING neither side has submitted torpedo plans yet in either branch (both were cleared by `_seal_orders`); the allies' torpedo candidate set is generated from own state only |
| legal action set identical | `sha256(engine.legal_actions(game_id, ALLIES))` equal across branches. Note: `legal_actions` at TORPEDO_PLANNING returns the schema + `torpedo_candidates`, which depend on the ship's OWN sealed movement only (verified in source: `_torpedo_candidates` reads `_sealed_batches(MOVEMENT_PLANNING)` filtered to the ship itself; `torpedo_assist` is documented "不读敌方封存计划") |
| opponent hidden pending commitment different | X_A ≠ X_B on exactly one axis ship's plan; the axis-side observation hash DIFFERS across branches (recorded as `axis_view_differs`, sanity check that the intervention actually changed the hidden state and nothing else) |

`axis_view_differs=True` plus `public_obs_equal=True` together prove the
difference is confined to information the allies cannot see.

## Why the intervention itself is legitimate

The replaced plan is not invented: it is one of the exact plan strings the
engine's `movement_candidates` offers for that ship at that state (the same
source the commander and the LLM prompt path use). It is then re-validated by
`engine.validate_orders` on the branch state before submission. The branch-B
world is therefore a match the axis player could legally have played from the
identical information set — the definition of a natural alternative commitment.

## What is recorded per pair

`scenario, seed, turn, phase, public_observation_hash, own_state_hash,
legal_action_hash, hidden_commitment_A (full axis plan map),
hidden_commitment_B, candidate list (per-branch validity), c0 (dice-stream
position), variant metadata (ship, from_plan, to_plan, distance to allies),
axis_view_differs, errors`. Branch states are persisted gzipped
(`states/{pair_id}_{A,B}.json.gz`) so any pair can be re-simulated byte-for-byte.

## Known limits

1. Only the ALLIES-as-focal / axis-movement-as-commitment window is exercised.
2. Variants replace one ship's plan at a time; multi-ship joint alternatives
   are not enumerated (a deliberate restriction to keep the intervention
   minimal and auditable).
3. The pre-state ancestor is produced by `balanced` commanders; pair density
   under other profiles is not sampled in this checkpoint.
