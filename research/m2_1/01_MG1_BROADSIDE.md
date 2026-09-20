# 01_MG1_BROADSIDE — PASS (+92.9%)

RESEARCH_MICRO_SANITY_CASE. Focal: IBS-U-IJN-AOBA, target IBS-U-USN-FARENHOLT
(S-01 s1 t2, post-movement/post-bearing design with a probe pass that learns
the target's deterministic post position first — simultaneous movement makes
the pre-turn bearing stale, F18).

| arm | plan | post rel | mounts bearing | main GF | EH @ common distance 4 |
|---|---|---|---|---|---|
| BROADSIDE | "0" (hold) | 1 | 3 | 5 | **3.00** |
| NARROW | "1S1P..." (turn toward, closes to d=3) | 5* | 1 | 5 | 1.56 |

*post_rel 5 with only 1 mount bearing: the post-movement bearing rotated so
the target sits on the stern arc — engine-native result.

Gate: +92.9% expected hits at common distance (>= +25%) — **PASS**.
First-MF-straight forbids pure turns (no cost-0 turn plans exist); the pair
hold-vs-turn is the exact same-position comparator.
