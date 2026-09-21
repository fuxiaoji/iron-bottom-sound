# 05_MG4_TORPEDO_FIDELITY.md

Case: `IBS-S-01` seed 1, TORPEDO_PLANNING turn 2; shooter
`IBS-U-USN-FARENHOLT` (TT1), victim `IBS-U-IJN-AOBA`; 288 legal configurations
enumerated (identical count to M2.1-R2.1), 29 victim routes at T+1.

**Reproduction of the frozen case: exact.** Full-state argmax = setting 2
(long-range), route reduction **0.9655** (28 of 29 routes in contact), gold
order accepted by the engine (`valid = True`), predicted T+1 segment
`[(1,T8),(2,T7),(3,T6),(4,T5)]` identical to the recorded `t1_predicted`, and
**12/12** agreement between the geometric space-time contact test and the
engine's own `torpedo_contact` events on the cross-validated routes.

| method | route reduction | fidelity |
|---|---|---|
| MANUAL_GOLD | 0.9655 | — (reference) |
| RANDOM_LEGAL mean (8 draws) | **0.0000** | denominator |
| CURRENT_POLICY | **0.0000** | 0.000 |
| CURRENT_INTENT_COMPILER | 0.0345 | 0.036 |
| PUBLIC_CORRIDOR_SEARCH | **0.1034** | **0.107** |
| FULL_STATE_CORRIDOR_CEILING | 0.9655 | 1.000 (trivial, see below) |

Gold gap +0.966 -> COMPUTABLE -> **NO_GAP** (search 0.107 < 0.70).

M22-F5, disclosed: MG4's MANUAL_GOLD *is* the full-state argmax, because the
R2.1 gold was constructed by that search. `F(FULL_STATE) = 1.000` is therefore
an identity, not a finding; the deployable number is `F(PUBLIC) = 0.107`.

## CURRENT_POLICY = 0 by abstention

At that state the deployed `TacticalCommander(profile="balanced")` submits **no
torpedo order at all** for the allies (0 orders), so it cannot create a corridor.
This is state-specific, not a global claim: over 15 turn-2 TORPEDO_PLANNING
states (`metrics/torpedo_usage_census.json`) the allies side fires in 7 states
and the axis side in 1, with 0 for both sides in the remaining 7.

## PUBLIC_INFORMATION_GAP: confirmed

Three observation-only objectives were scored over the same 288 configurations,
each with a deterministic tie-break that cannot consult the full state
(config tuple order):

| public objective | objective cells | max overlap | configs tied | route reduction within the tie set | chosen |
|---|---|---|---|---|---|
| LEAD_HOLD_COURSE | 30 | 1 | 12 | 0.000 .. 0.103 | 0.103 |
| LEAD_TURN_ALLOWED | 90 | 1 | **68** | **0.000 .. 0.966** | 0.000 |
| CORRIDOR_BLOB | 240 | 5 | 4 | **0.000 .. 0.000** | 0.000 |

The `CORRIDOR_BLOB` argmax has **no informative configuration among its four
ties**, while the true best configuration scores *low* on every public objective
(overlap 1 against a maximum of 5). `LEAD_TURN_ALLOWED` shows the general shape:
the public signal identifies a set containing the corridor but cannot rank inside
it — 4 informative configurations against 64 non-informative ones, expected value
of a uniform pick from the tie set ~0.04, which is what the deployed AI's own
candidate generator plus the intent objective achieves (0.0345, 225 engine
combos, best setting 0, angle A).

Rank correlation between blob overlap and true route reduction is +0.676 across
all 288 configurations, which is exactly why a rank-correlation summary alone
would have been misleading here: the correlation is produced by the large mass
of zero-overlap/zero-reduction configurations, while the *argmax* region is
anti-informative. The numbers above, not the correlation, are the evidence.

## Reading

Torpedo area denial is real, engine-verified, and a **full-state** phenomenon in
this case. An actor restricted to observation-grade information cannot identify
the corridor: not with the engine's own candidate generator, not with lead
pursuit on the target's course, not by maximising forecast-corridor coverage.
