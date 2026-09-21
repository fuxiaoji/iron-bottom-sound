# FAILURES_AND_COUNTEREXAMPLES.md — Phase A.2

## The counterexample of record: an "oracle" that scored below a feasible point

A greedy heuristic was named `HINDSIGHT_ORACLE` and used to kill Track A. It scored
**below** Uniform-16 on sampling, which no oracle can do because all-16 is feasible
under the same total budget. The impossibility of that number was the only tell; the
gate itself failed quietly in the direction the run "wanted". This is now the
project's canonical example of why oracle baselines need a feasibility assertion
(implemented: `checks["all_16_feasible"]`, exact-total assertions, allocation counts).

## Second counterexample: a baseline too weak to be a baseline

Phase A v3.1's "generic uncertainty" baseline was frozen-policy action entropy — a
signal with no relation to the *label*. It was replaced (A.2) by a real ExtraTrees
vote-entropy learner. The replacement turned out to be similarly weak (0.022–0.078
recall on balance), which is itself informative: on this universe, model-based
active learning does not find severity transitions either.

## Third: recollection of the acquisition-design failure mode

Track B has now failed three times for three different instrument reasons (universe
< K; mid/min/max rather than bisection; and in the toys, a discovery metric that
rewarded coverage). No run to date has given the multi-agent-structure hypothesis a
competent acquisition strategy, and the record says so instead of presenting three
failures as one verdict.
