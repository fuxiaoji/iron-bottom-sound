# MORNING_README.md

OVERNIGHT STATUS: **SUCCESS** (v5.0 credibility cycle complete)

Most important result:
**Finite-horizon DP solver converges 100% (7/7 cells) where the plan library failed (25%).**  The DP solver confirms: symmetric closed-loop V≡L exactly (degenerate), range asymmetry breaks degeneracy (V=±8), speed asymmetry does NOT break it.  B8's failure was a plan-library discretization artifact, not a model error.

What changed in the paper:
- v4 paper (`paper_v4/main.pdf`, 11 pages) is the current main submission
- B13 resolved to canonical **PARTIAL** (lower-bound sign 100% PASS, rank ρ=1.00 PASS; strict sign 67% and regime 67% reflect model conservative head-on prediction)
- Speed paradox renamed to **operating-speed effect** (B0 audit + B4.1 confirms capability monotonicity)
- B8 FAIL documented with root cause (library discretization) and DP solver as replacement

Best current paper direction:
**Operations Research + Applied Mathematics / Dynamic Games** per v4.0 plan.  Primary: degeneracy boundary (B3) + path-integrated load-bearing proof (B2) + speed monotonicity (B4).  Secondary: commitment-range law (B7, provisional pending open-loop solver) + engine validation (B13, PARTIAL).

Biggest problem:
Committed-maneuver open-loop values remain library-dependent.  The finite-horizon DP solver solves the closed loop but not the open loop.  Next: extend backward induction to the open-loop game.

v5 credibility fixes applied:
- B13 canonical results established (PARTIAL: lower-bound 100% PASS, strict 67%, ρ=1.00)
- Root cause identified: two scripts wrote different model prediction formulas (best vs mean plan)
- P1 DP solver: 100% convergence (7/7 cells, replaces B8's 25% plan library)
- v4 paper Section 5 replaced: plan library → DP solver, with convergence table

Next command to run:
```
cd paper_v4 && pdflatex main.tex && pdflatex main.tex
```
All experiment scripts: `research/experiments/p1_solver_convergence.py`, etc.
Full overnight log: `research/audit_v4/OVERNIGHT_MASTER_LOG.md`
Detailed report: `OVERNIGHT_FINAL_REPORT.md`
v5 detailed report: `research/results/overnight_v5/OVERNIGHT_MASTER_REPORT.md`
