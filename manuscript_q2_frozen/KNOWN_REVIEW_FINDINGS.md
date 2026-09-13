# Author-facing developmental review: major findings before v12 results

Working draft, AI-assisted; not an independent journal review or an editorial decision.

## M1 — Invalid all-state degeneracy proof
Location: paper_v11/main.tex, Proposition labelled prop:deg and proof.
Observation: equivariance at swapped state is replaced by equality at the same state. The conclusion V(s)=ell(s) at every state does not follow.
Evidence: THEORY_AUDIT.md, section 6; two absorbing exchange-related states provide a counterexample satisfying the stated premises.
Why it matters: the abstract, contribution list, degeneracy figure interpretation, discussion and conclusion depend on the stronger statement.
Requested action: replace the theorem with exchange oddness and zero only at exchange-fixed states. Remove all-state and kinematic-asymmetry-invariance claims. A descriptive result from one discretized model is not a general theorem.

## M2 — Historical LF numerical results do not use a single causal payoff
Location: matched_horizon.py scalar_interval_payoff, batch_interval_payoff, state_key, run_cadence.
Observation: history time origin differs in scalar/vector paths; vector endpoint heading can depend on future sealed suffix; cache reads the wrong buffer index and omits history.
Evidence: v12 100-state audit and cache-collision witness.
Why it matters: existing confidence intervals reflect sampling from a contaminated/inconsistent implementation, not uncertainty about the intended game.
Requested action: keep v11 outputs archived, classify them as unreliable for the intended estimand, rerun only the authorized repair branch, and avoid treating them as evidence that the scientific hypothesis was falsified.

## M3 — The proposed flexibility sign hypothesis repeats the old bilateral sign
Location: requested v12 plan sections 15, 18 and 25.
Observation: with its definitions, Delta_F=sign(eta_r-1)*(V_CC-V_FF).
Evidence: exact algebra in THEORY_AUDIT.md sections 3-4.
Why it matters: new notation and monotonic component values do not create independent evidence or mathematical novelty. Individual component values also depend on the comparison path through FC or CF.
Requested action: report all four values and the attribution path; do not present an algebraic identity as an empirical mechanism test or established Q1 novelty.

## M4 — Local open-loop gaps do not bound feedback performance
Location: requested v12 plan section 3; v11 control discussion.
Observation: each LB/UB bounds a different remaining-horizon open-loop game. Its continuation does not equal the feedback continuation.
Evidence: solver definitions and THEORY_AUDIT.md section 7.
Why it matters: summing these gaps and enlarging a Monte Carlo CI does not create a valid feedback-equilibrium confidence bound.
Requested action: label sums as diagnostics; use complete finite-game DP/sequence-form values for equilibrium claims.

## M5 — Additional legacy closed-loop implementation issue
Location: differential_game.py _build_L calls _classify with radians, although _classify uses degree thresholds; Bellman recursion is pure max-min rather than mixed minimax.
Evidence: a 90-degree aspect is classified bow_stern in the legacy path and broadside when units are corrected. A targeted 576-state audit changes stage values by up to 0.8971. The observed V2=L equality persists in that small audit, so the unit bug is NOT claimed as the demonstrated cause of degeneracy.
Why it matters: the experiment does not implement the fully stated general model or mixed Bellman solver, even where some outputs happen to coincide.
Requested action: narrow historical DP evidence to its actual implementation; do not reuse those tables as verification of the corrected general theorem.

## M6 — Claims of completion in v11 do not match its manuscript
Location: FINAL_V11_ADVISOR_REPORT.md versus paper_v11/main.tex, negative results and abstract.
Observation: the report says the phrase about one third of rank information was deleted, but the manuscript retains it. The abstract also asserts unchanged comparative statics across formation representations while the robustness section explicitly declines that claim.
Evidence: direct manuscript inspection. Neither a rank correlation change nor a graph count implies a fraction of information.
Why it matters: a completed checkbox cannot establish cross-section consistency or submission readiness.
Requested action: audit the delivered manuscript itself, remove unsupported interpretations, and bind each retained quantitative claim to a source.

## Review limitations

The requesting author owns the scientific decisions. Final mathematical novelty, current target-journal fit, licensing of original wargame material and any author declarations require human review. No current CAS quartile is certified here. No external submission or communication is authorized or performed.
