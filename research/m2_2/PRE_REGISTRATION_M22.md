# PRE_REGISTRATION_M22.md — M2.2 compiler-fidelity thresholds, frozen before measurement

Historical verdicts are **not** modified:
`MECHANISTIC_GOLD_GATE = FAIL (3/5)`; `MG1/MG3/MG4 = VALID PASS`;
`MG2/MG5 = FAIL in their registered arms`.

## Naming discipline (binding on every M2.2 artifact)

- `LEGAL_FIRE_HEURISTIC` — the repaired `team_legal_fire_v2` (one target per
  ship, each mount once, engine-exact modifiers, validated batch). **Never**
  called optimal.
- `FIRE_SEARCH` — research-only allocation search over per-mount targets
  (each mount once, engine-exact modifiers, validated batch), used only to
  calibrate the heuristic on 10-20 states. Named SEARCH; not optimal.
- `BEAM_SEARCH_COMPILER` — joint movement beam search. Not "oracle".
- `PUBLIC_CORRIDOR_SEARCH` / `FULL_STATE_CORRIDOR_CEILING` — torpedo corridor
  search from observation-only vs research full state. The ceiling is **not**
  a deployable method.

## Mechanism values (frozen)

| mechanism | value |
|---|---|
| M_broad (MG1) | `EH_own_legal(s') − λ·EH_enemy_legal(s')`, λ = 1, at post-movement pre-gunnery |
| M_range (MG3) | `NetEH(s')` (same formula) — **never** "closer is better"; report weighted engagement distance, penetration feasibility, torpedo-threat proximity alongside |
| M_corr (MG4) | `RR(s,τ) = 1 − |R_safe_τ(s)| / |R(s)|` over the victim's next-decision legal routes, torpedo-only contact |

## Fidelity (frozen)

`F(method) = (M(method) − M(random)) / (M(manual_gold) − M(random))`

Computed **only** when the denominator is positive and the gold gap exceeds
the floor. Floors (pre-registered): **absolute mechanism floor = 0.05** in the
mechanism's own units (EH margin for broadside/range; route-reduction
fraction for torpedo). Below the floor the case is reported as
`GOLD_TOO_SMALL` and excluded from the ratio.

Bands: `F ≥ 0.8` full realisation · `0.4–0.8` partial · `F < 0.4` compiler gap.

## B0 gate (Gold Compiler Fidelity) — frozen

For the three confirmed mechanisms (MG1 broadside, MG3 range, MG4 torpedo
corridor):

```
GOLD_COMPILER_GAP = PASS iff  >= 2 of 3 cases satisfy
    SEARCH fidelity >= 0.70
    AND CURRENT_POLICY fidelity <= 0.40
```

- If SEARCH < 0.70 on every case while the gold gap is above the floor:
  `SEARCH_COMPILER_FAIL` → fix the search, do **not** run the natural census.
- If CURRENT_POLICY ≥ 0.8 anywhere: record `CURRENT_AI_ALREADY_STRONG` for
  that mechanism.

## B0 search budget (frozen)

- Movement: per ship ≤ **8** legal plans (current-policy, hold if legal,
  fastest, slowest, port-extreme, starboard-extreme, + top-2 by the single-ship
  mechanism score). Joint **beam width 64**; EM-01 may drop to **32**
  (pre-registered here). Partial ordering by cheap geometry; the final full
  joint batch must be played through real simultaneous movement to the
  pre-gunnery state and scored there.
- Torpedo: enumerate launcher × launch MF × side × angle × setting × salvo,
  projected with `_project_torpedo_path`, every candidate validated. Objective
  is **route reduction**, not expected hits. Search capped at the first 400
  valid configurations per state (emitted in deterministic order).

## B1 census (only on B0 PASS) — frozen

States: per scenario movement 20 / torpedo ≤10, stratified early / contact /
damaged / late, both sides, taken from the M2.1 snapshot pool plus new
replays in (scenario, seed, turn) order — no hand-picking.

`OPPORTUNITY_PRESENT(s)` iff `SEARCH` beats `CURRENT_POLICY` by
**≥ 25% relative mechanism gain AND ≥ the absolute floor (0.05)**.

Stage-B diagnosis thresholds (frozen):

- `COMPILER_GAP_CONFIRMED`: ≥2 mechanisms in ≥2 scenarios with opportunity
  rate ≥ 20%, AND (median fidelity gain ≥ 0.30 or CURRENT < 0.40×realisable
  with SEARCH ≥ 0.70), AND random matched-budget clearly worse, AND not driven
  by one scenario.
- `MECHANISM_RARE`: opportunity rate < 10%.
- `SEARCH_LIMITED`: natural signal present but SEARCH cannot recover.
- `CURRENT_AI_ALREADY_STRONG`: CURRENT fidelity ≥ 0.8 and near SEARCH.

## Explicitly out of scope

MG2/MG5 are not re-run as gates; crossing-the-T becomes a supplementary
compiler target (maximise net EH + bow/stern fraction); local force becomes a
diagnostic only. No training, no rule changes, no value-realisation claims.
