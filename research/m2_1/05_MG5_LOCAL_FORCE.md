# 05_MG5_LOCAL_FORCE — FAIL (TACTICAL_ASSUMPTION_NOT_SUPPORTED)

RESEARCH_MICRO_SANITY_CASE (EM-01 s1 t3; 9 allied vs >=4 axis ships; split
enemy cluster >= 6 hexes).

| arm | own active ships | own GF | own EH | enemy EH | margin |
|---|---|---|---|---|---|
| CONCENTRATE (all steer at isolated ship) | 9 | 527 | 96.6 | 40.0 | 56.6 |
| DISPERSE (split toward both clusters) | 9 | 593 | 121.0 | 38.3 | **82.7** |

Margin ratio 0.68 — DISPERSE is BETTER. Root cause: IBS gun ranges (8+ hexes
effective) exceed the 6-hex cluster separation, so in BOTH arms every own
ship is active and every enemy is under fire; "3v2 local superiority" cannot
manifest because the distant group remains fully in the fight, and the
concentrate steering actually degrades arcs for the other ships.

Classification: **TACTICAL_ASSUMPTION_NOT_SUPPORTED** at this engagement
scale — the tactic is real in naval doctrine but this platform's range scale
erases it under expected-hit measurement.
