# v10 freeze (v11 section 0)

Frozen at 2026-09-12 19:50:20

| artefact | sha256-16 |
|---|---|
| manuscript_tex | 56e14493fb1d7a28 |
| manuscript_pdf | 259cfec6ee8f85f8 |
| claim_registry | 964f4a62fc564f4f |
| lf_grid5 | 56035877f90cc89a |
| lf_grid7 | 9b972cbbd197aa71 |
| rigid_vs_lf | 26fa88571b19fb9c |
| bridge | 3c300be3a3cc55dd |
| torpedo | 46704b9f753fcf7b |
| reposition | 038c04fa3b0d98af |
| unit_tests | 665fd7d6dfcf5330 |
| advisor_report | fd5ca4a7b8d7cd9b |
| lf_module | 5a7491150662c71c |

## v10 commitment definition (to be superseded)

    P_H = V_H - V_1

with V_H = sum_{t<H} gamma^t L(s_t).  **Known problem**: this changes the plan
length AND the evaluation horizon simultaneously, so it does not isolate the
value of commitment/flexibility.

## Claim renames required by v11

| v10 wording | v11 allowed wording |
|---|---|
| commitment premium / value of commitment | **open-loop engagement-horizon effect** |
| feedback premium / value of replanning | horizon-dependent cumulative value |
| 18/18 certified (as commitment) | open-loop horizon experiment: all 18 signs certified |

## v10 results retained unchanged

- LF certified signs (open-loop horizon metric): 18/18, 0 reversals, Grid-7 all 18 cells.
- rigid vs LF sign match 18/18 on that metric.
- 8/8 formation unit tests, 9-cell bridge ROBUST, sensitivity checks.

v11 must not silently overwrite these files.
