# Round 1 revision response

This is the author's workspace implementation log of the assistant's developmental self-audit. It is not an independent review exchange.

|Comment|Action and evidence|State|
|---|---|---|
|M1|Closest-work table now compares the expanded JAIR2014 theorem/experiments and NeurIPS2018 lifting/decomposition theorems. Main text credits standard components. Novelty and useful increments remain to be judged from the frozen experiment.|Theory wording revised; empirical assessment pending|
|M2|Exact behavioral product formula, normalization, zero-reach rule and legal-menu assumption added in proof supplement S4. policy_v14.py and tests/test_policy_v14.py verify complete-response values and full-calendar identity.|Revised and small-game verified|
|M3|Main common-update proof and supplement S1 explicitly define completed private blocks, information-set IDs, parent sequences and payoff mapping. Frozen solver cuts only at intersections. Independent enumeration/decomposition checks pass.|Revised and verified|
|M4|Supplement S7 (renumbered after the interval-bound addition) states Cartesian-product policy spaces before deriving modularity from product equilibria; no formation applicability claim.|Revised with proof|
|M5|Supplement S5/S9 and the main algorithm separate finite termination, floating intervals and budget ambiguity. v14_resume.py preserves ordinary attempts and uses the same tolerance; continuation implementation still requires actual resource-run records.|Revised; run records pending|
|M6|recovery_v14.py now recovers full and coarse policies and checks complete responses. Independent sequence-form recovery tests pass. v14_certificates.py records the complete adversarial leaf law and selects its most probable leaf for illustration.|Implemented; full experiment pending|
|M7|v14_foundations.py reproduced all archived class metrics. CALIBRATION_REPLAY.json records the missing-class reconstruction and correct metric labels. Main/supplement explicitly avoid interpreting calibration as physical validation.|Arithmetic correction completed|
|m1|The main theorem title now names the complete permitted policy class.|Revised|
|m2|HISTORICAL_OVERLAP_AUDIT.json identifies known development exposure and new paired frozen-test distances; methods state the deterministic algorithm-test unit.|Revised|

No experimental result has been changed to resolve a review comment. The remaining empirical checks are explicit tasks in the execution ledger and will be revisited in the final round.
