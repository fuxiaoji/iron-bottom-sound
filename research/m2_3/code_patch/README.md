# code_patch — M2.3

## Added (research only, no production change)

- `scripts/m23_jtc.py` — supplemental MID/DAMAGED panels, three intent families,
  five methods, admission rule, rejection accounting
- `scripts/m23_bard.py` — same-public-history information sets with hash and
  action-set identity verification, matched-kinematics control, full payoff
  matrices, public planners
- `scripts/m23_verdict.py` — frozen §5/§7 mapping, scorecard, figures

## Changed in the M2.2-R tree (disclosed)

- `research/m2_2r/scripts/b1e.py`: `_hull_frac` now reads `max_hull` (M22R-F6 — the
  old attribute name made the damaged predicate dead code)
- `research/m2_2r/FAILURES_AND_COUNTEREXAMPLES.md`: M22R-F6 appended
- `research/m2_2r/05_B1E_MOVEMENT_CENSUS.md` and `00_EXECUTIVE_SUMMARY.md`: an
  ERRATUM block appended; the original claims are preserved, not rewritten, and
  the old numbers are unchanged (a dead label changed no state selection)

## Deliberately not changed

- `backend/src/iron_bottom_sound/**` — production untouched
- the old census state sets, gates, verdicts and rates
- `research/m2_1/scripts/mg/mg_cases.py` (the frozen pre-fix intent compiler)
