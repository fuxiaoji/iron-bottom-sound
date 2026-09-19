# 05 — Track C: Phase-Adaptive Granularity

Census over the frozen Track A movement evaluations, split by phase proxy
(early turn<=2 vs contact turn>=3):

| cell | n | median minimal-safe K | median saving | K distribution |
|---|---|---|---|---|
| S-01/early | 6 | 2.0 | 63% | {2:5, 3:1} |
| S-01/contact | 13 | 2 | 38% | {2:9, 3:3, 5:1} |
| S-03/early | 7 | 1 | 80% | {1:7} |
| S-03/contact | 9 | 1 | 75% | {1:9} |

**Verdict: C_MODULE.** The dominant factor is SCENARIO (S-03 tolerates K=1
everywhere; S-01 wants K=2 everywhere), not PHASE — within a scenario the
phase split barely moves the distribution. Gunnery and torpedo granularity are
ship-level by rule at HEAD (no grouping lever exists without new machinery, a
fact from the mode audit), so a phase-ADAPTIVE claim cannot even be exercised
across phases in the current engine. Movement compression itself (the real
finding) is a Track A module — and Track A failed its own oracle gate.
