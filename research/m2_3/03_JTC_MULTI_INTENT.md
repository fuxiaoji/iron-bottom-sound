# 03_JTC_MULTI_INTENT.md — three intent families

| id | intent | L0 | compiler |
|---|---|---|---|
| I1 | Broadside / firepower unmask | focal→target legal visible EH | arc-count rule |
| I2 | Executable range control | signed range change (hexes) + executability | toward/away via `plan_for_pose`; better direction reported |
| I3 | Raking / crossing-T geometry | bow/stern fraction among own legal firing pairs | reachable station maximising bow/stern-presenting enemies |

I3 is new and does not touch the old MG2 verdict. In this engine the longitudinal
modifier is a property of the *target's* heading relative to the bearing to us, so
the I3 compiler selects a **station**, not a turn — a fact worth recording.

## JOINT_BEAM team-beneficial opportunity rates (frozen 20 % line)

| scenario | I1 | I2 | I3 |
|---|---|---|---|
| IBS-S-01 | 0.222 | 0.167 | 0.333 |
| IBS-S-03 | 0.182 | 0.000 | 0.136 |
| IBS-S-EM-01 | 0.200 | 0.000 | 0.100 |

`JTC_MULTI_INTENT = FAIL`: only **I1** reaches ≥20 % in ≥2 scenarios (S-01 0.222,
EM-01 0.200). I2 is near-dead in the supplemental panels (0.000–0.167): the
executable-range condition (both arms visible *and* a ≥2-hex change *and* a ≥25 %
relative team gain) is rarely met jointly in these states — the MG3-E case that
passes it was found by scanning 162 states, so its rarity here is consistent.
I3 passes 20 % only in S-01.
