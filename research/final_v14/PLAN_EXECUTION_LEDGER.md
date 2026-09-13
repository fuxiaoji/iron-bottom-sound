# v14 execution ledger

Last material update: 2026-09-13, development running. DONE means the work and stated verification actually happened; it does not mean a publication-quality gate passed.

|ID|Approved requirement|Status|Evidence / completion condition|
|---|---|---|---|
|P01|Approved plan, design and historical freeze|DONE|MASTER_PLAN.md; DESIGN.json; HISTORICAL_FREEZE.json,1371 files|
|P02|Old-plan mapping and unchanged conclusions|DONE|OLD_PLAN_MAPPING.csv,103 numbered items; OLD_PLAN_SOURCE_MANIFEST.json; HISTORICAL_V12_ANSWERS.md|
|P03|Theory corrections and complete derivations|DRAFT/ROUND1 REVISED|THEORY.md; paper_v14 main and proofs; F-only interval theorem; final consistency/review pending|
|P04|Arbitrary sealed-block calendar solver|DONE|schedule_v14.py; micro normal-form, endpoints, physical mirrors|
|P05|Pricing, coarsening, response transfer|IMPLEMENTED/VERIFIED SMALL|pricing_v14.py; policy_v14.py; independent complete-response comparisons|
|P06|Calendar branch-and-bound|IMPLEMENTED/VERIFIED SMALL|frontier_v14.py; complementarity test and interval-budget ambiguity test|
|P07|Closest-work/novelty audit|THEOREM COMPARISON COMPLETE / EMPIRICAL ASSESSMENT PENDING|LITERATURE_POSITIONING.md; primary full-text theorem, algorithm and scale comparisons; novelty not yet established by experiments|
|P08|Development,9physical/18conditions plus mirrors|RUNNING|runs/; development.log; PROGRESS.json|
|P09|Frozen test,12physical/24conditions|PENDING|Configurations frozen before outputs in DESIGN.json|
|P10|Horizon/action-grid robustness|PENDING|Predeclared configurations; T6 baseline shared with development|
|P11|Three one-factor ablations|PENDING|T4 Grid3, three geometries, both opponent classes|
|P12|Certified retention budgets and policy replay|PENDING|90/95/99%, possible versus certified K, no ratio when adaptation unresolved|
|P13|Fair algorithm comparison and losses|PENDING|Cold timings versus trace accounting labeled; all model/precision costs included|
|P14|Eight figures/four tables|PENDING|Data-linked PDF/PNG and visual inspection|
|P15|Full English paper/proof/supplement/Chinese explanation|PARTIAL DRAFT|paper_v14/ model,theory,algorithm,methods,proof appendix; results/full prose/final PDF pending|
|P16|Two review/revision rounds|ROUND1 REVISED / ROUND2 PENDING|reviews/ROUND1_MATH_METHODS.md,ROUND1_RESPONSE.md,ROUND1_INTERVAL_ADDENDUM.md; author-workspace developmental self-audit|
|P17|Reproduction,manifests,environment and verification log|IN PROGRESS|Environment/freeze present; final runner and reproduced results pending|
|P18|CAS journal positioning and candid final quality assessment|PENDING|Official scope/policies and verifiable rankings, no invented certification|

## Historical plan mapping

The controlling v13 ledger has sections0–42 and the mapping of master items1–15. It remains immutable at ../final_v13/PLAN_EXECUTION_LEDGER.md. v12 history remains under ../final_v12/. The new user instruction authorizes a new complete paper; it does not turn the old hypothesis into a supported result.

|Old sections|Disposition in v14|
|---|---|
|v13 0–13,22–25|Historical completed factorial design/results stay frozen; the 5/12 support and7 strong reversals are not changed|
|v13 14–21|Historical tracking metrics remain exploratory/unsupported as a causal mechanism; no relabeling as new held-out evidence|
|v13 26–30|Old failed-branch extensions remain untriggered. New horizon/grid/rigid tests address budgeted calendars under a separately frozen protocol; not retrospective passes of v13|
|v13 31–34|Valid inclusion and algebra retained as foundations; general complementarity rejected, counterexample retained; old global degeneracy theorem corrected|
|v13 35–38|Old Q1 rewrite gate failed. New author-approved direction independently permits paper_v14; fallback remains unendorsed|
|v13 39–42|Old eight DRAFT figures, literature, advisor report and stopping record stay unchanged; new displays/reviews do not overwrite them|
|v12 range claims|Falsified results stay archived and are disclosed where relevant; no new range-success claim|
|v12/v13 numerical audit|Targeted regressions only; no unnecessary rerun of full Monte Carlo audit|

No final quality assessment has been passed. Completion of a draft theorem or a software test does not certify novelty or CAS journal suitability.
