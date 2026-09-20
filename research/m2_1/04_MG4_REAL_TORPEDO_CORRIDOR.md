# 04_MG4_REAL_TORPEDO_CORRIDOR — FAIL (CASE_CONSTRUCTION_FAIL)

RESEARCH_MICRO_SANITY_CASE (S-01 s1 t2 torpedo planning; victim IJN-AOBA at 6
hexes; shooter USN-FARENHOLT, TT1 loaded).

Three aiming schemes, all with REAL validated TorpedoOrders:

| scheme | result |
|---|---|
| current-intercept combos (top-3 by target match) | both arms IDENTICAL to 13 decimals at T+1 |
| corridor coverage of T+1 route hexes | identical again |
| launcher-deduped spread (F17 fix) | 29 routes; safe 19/29 in BOTH arms; mean damage 1.172 both |

**RouteReduction = 0.0** — the turn-T torpedo launches did not constrain the
victim's T+1 route set at all.

Classification: **CASE_CONSTRUCTION_FAIL**. Two candidate mechanisms (not
separated this round): (a) torpedoes launched at turn T expire or exit before
the T+1 routes at this range/geometry; (b) the corridor coverage metric
(pattern hexes of predicted paths) does not correspond to where the tracks
actually travel. Distinguishing them requires reading the torpedo persistence
semantics in `_resolve_torpedoes` — engine source study, not this stage.

The plan's requirement "G4 必须继续至少 2 个回合，并允许 opponent 重新规划"
is satisfiable only if multi-turn torpedo tracks persist; that premise failed
here.
