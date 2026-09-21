# 05_POSITIVE_RESULT_CONTRACT_CANDIDATES.md

No candidate passes its strong-baseline gate in Phase A.2, so **no positive-result
contract is issued**. Per the plan, a contract accompanies only a selected mainline
and the PI owns that decision. For the record, the contract each track would need:

| track | primary estimand | must beat | both tasks | falsifier | must NOT be claimed |
|---|---|---|---|---|---|
| A adaptive compute | normalised team return at fixed total planning budget | Uniform-16, RandomAllocation, uncertainty heuristic | yes | oracle gain < 0.08 NR | "more planning"; unequal totals; oracle-only |
| B boundary discovery | transition-edge recall at fixed K | RANDOM **and** a real label-based generic active learner | yes | structured ≤ random or ≤ generic | "multi-agent structure helps" unless ≥15 % over the generic learner |
| C attribution | top-k hit against the minimal repair set at ≤25 % of the exhaustive budget | RANDOM_CELL **and** AGENT_THEN_TIME_GROUP_TEST | yes | < 80 % of exhaustive accuracy, or <10 pp over group testing | "first"; injection metadata; correlation as attribution |

Track A's contract is now moot (killed on corrected evidence). Track B's and Track
C's are untested rather than refuted: B has never had a bisecting acquisition, and C
has never reached its minimum sample under the frozen generator.
