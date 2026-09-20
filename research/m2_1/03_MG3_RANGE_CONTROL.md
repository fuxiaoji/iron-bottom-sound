# 03_MG3_RANGE_CONTROL — PASS (2.72x range effect)

RESEARCH_MICRO_SANITY_CASE (EM-01 s1 t2, allied BB).

| arm | post distance | expected hits (own, vs nearest enemy) | penetration@D | enemy torpedo max range |
|---|---|---|---|---|
| CLOSE | 15 | **2.56** | 8.0 | 71* |
| OPEN | 17 | 0.94 | 8.0 | 71* |

Gate: >= +25% expected-hits difference — **PASS** (2.72x). The range-modifier
table is very steep at long range. *torpedo range 71 is the raw table value
read from the DD's settings and is not hex-turns; the torpedo-threat flip was
therefore not decidable from this number (recorded as a metric gap, F19).
