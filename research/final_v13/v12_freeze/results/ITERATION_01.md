# COMMITMENT REVIVAL ITERATION 01

1. Current phase: R0-R6, Phase A correctness audit.
2. Question: do payoff semantics, LF histories, and solver certificates support the v11 interpretation?
3. Fixed: existing kernel, geometries, action grids, horizon, spacing, ship count; old artifacts frozen by hashes.
4. Changes: independent causal scalar/vector endpoints; complete-history fingerprints; actual rigid-mode dispatch; fail-closed LP/DO; common exchange-mapped supports; exact player-swap canonicalization.
5. Correctness basis: old key uses stations[head] rather than stations[M+head]; old scalar uses turn 0 on nonzero-head histories; old vector reads outgoing leader heading at endpoints from unexecuted suffix. All alter the computed game rather than merely reducing variance.
6. Tests: 100/100 old scalar/vector comparisons fail; corrected max error 8.17e-14. Prefix invariance max error 0.0. A concrete old cache-key collision changes payoff by 33.12.
7. Symmetry: all three prescribed initial geometries admit an exchange isometry. Head-on/crossing use a half-turn; parallel uses reflection and action-sign reversal. Random history swap error max 3.55e-15.
8. Gap: head-on Grid-5 initial requires 144 DO iterations at frozen strict tolerance, final gap 2.35e-10. Parallel requires 109, final gap 2.83e-14. Remaining audits underway.
9. Exact/approximate: current DO bounds certify only finite open-loop games; no feedback value or receding-policy episode bound is asserted.
10. Results: at least three implementation defects established, all new primary results still pending.
11. Negative cases: all 100 legacy history comparisons retained, no removal of inconvenient cells.
12. Revival: not yet; solver audit is necessary, not evidence of the range-sign hypothesis.
13. Flexibility: A-C follow from nested mixed policy classes and algebra. Delta_F defined in the plan is exactly sign(eta_r-1)*(V_CC-V_FF), so its proposed sign is not an independent new hypothesis.
14. Claim status: Commitment INCONCLUSIVE/REMOVE pending gates. A separate critical proof error found in v11 Proposition 2: equivariance relates F(s,u,v) to S F(Ss,v,u), not S F(s,v,u). Therefore V(s)=L(s) for every state is not proved. A correct exchange-oddness theorem is required.
15. Next allowed step: finish Phase A, repair the theorem statement and provide a counterexample to the stronger false claim; implement (but do not run discovery before the hard gate) independent exact finite-game algorithms.
