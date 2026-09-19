# 02 — Dataset and Exact Team Lab

## Shared snapshot dataset
- 60 movement-planning snapshots (30/scenario: IBS-S-01, IBS-S-03), from
  3 profile pairs (balanced/balanced, fleet/line, brawl/cautious) x 10 seeds x
  both sides, taken in (pair, seed, turn) order with the pre-declared 30-cap
  (A-MECH-03).
- Every snapshot stores the full GameState (research-only) plus per-ship rows
  (public fields: type/hp/pos/heading/speed/vp); public/research split is by
  field, both derived from the same engine state. Replayable byte-for-byte via
  the stored state JSON + seed.
- Realistic-mode census data (Track B): 150 completed matches (50/scenario) in
  `metrics/b0_census.json`, plus 36x7 B2 organization arms.

## Exact Team-Abstraction Lab (research/m2_0/exact_team_lab/)
- Tiny cooperative game: N agents, b actions each, horizon T, state-dependent
  tasks, damage-shrunk action sets; exact V*_flat, V*_Pi, L*.
- Two independent solvers (DP over joint actions; explicit-tree recursion with
  no shared DP code) agree to 1e-12 on flat values and all tested partitions.
- Required cases all present as unit tests (6/6 pass):
  Case 1 grouping-lossless (irrelevant-agent merge), Case 2 grouping-harmful
  (a0 != a1 payoff; merged = -3 vs flat +3, L*=6), Case 3 state-dependent split
  (aligned preferences merge losslessly, opposed preferences L*=1.5), Case 4
  failure-sensitive organization (damaged fragile pair: split org strictly
  beats merged).
- Note: my first three case-tests encoded wrong hand-computed expectations
  (T=3 totals; sum-reward degeneracy where merge and split reach identical
  executed sums). The failures were fixed by choosing reward structures where
  the case property is provable, with the reasoning recorded in the test docstrings.
