# 02_MG4_TORPEDO_PERSISTENCE — PASS (the PI's hypothesis confirmed)

The PI's read of the engine was correct: `TorpedoTrack` carries
`speed_cycle / range_remaining / distance_travelled / launched_turn`, a track
persists across turns, and `blind_torpedoes=False` by default means the
victim *sees* it at the T+1 decision — so a forcing claim is legitimate.

## Probe (6 independent launches, S-01 seeds 1-8, first torpedo-capable ship)

| seed | track | position | heading | range_remaining | distance_travelled | speed_cycle | T+1 allowance | visible to victim |
|---|---|---|---|---|---|---|---|---|
| 1 | TT-2-IBS-U-USN-FARENHOLT-TT1-1 | N8 | 5 | 2 | 8 | [8, 8, 2] | 8 | True |
| 2 | TT-2-IBS-U-USN-FARENHOLT-TT1-1 | N8 | 5 | 2 | 8 | [8, 8, 2] | 8 | True |
| 3 | TT-2-IBS-U-USN-FARENHOLT-TT1-1 | T6 | 6 | 3 | 7 | [8, 8, 2] | 8 | True |
| 4 | TT-2-IBS-U-USN-FARENHOLT-TT1-1 | V4 | 6 | 2 | 8 | [8, 8, 2] | 8 | True |
| 5 | TT-2-IBS-U-USN-FARENHOLT-TT1-1 | N8 | 5 | 2 | 8 | [8, 8, 2] | 8 | True |
| 6 | TT-2-IBS-U-USN-FARENHOLT-TT1-1 | N10 | 5 | 4 | 6 | [8, 8, 2] | 8 | True |

All 6 tracks survive to T+1 with `range_remaining > 0` and
`distance_travelled > 0`, and all 6 are visible to the victim side.

**Persistence probe = PASS.** The earlier M2.1-R2 conclusion ("torpedoes do
not constrain T+1 routes") was an artifact of aiming at the current-turn
intercept and of a hull-damage-based safety metric — the repair shows below
that a long-range setting produces a corridor covering 28 of 29 routes.
