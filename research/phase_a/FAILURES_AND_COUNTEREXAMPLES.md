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

## Phase A.3 — the honest kills

- **Track B (valid kill):** with a competent instrument proven at 61x/46x over
  random on synthetic geometry, the real universes contain only 3 (balance) and 20
  (sampling) true adjacent-severity transitions across 1260 lines each. The gate
  needs >= 20 % of lines to contain a transition; the measured share is 0.42 % and
  2.08 % even restricted to the 720 multi-severity lines that can in principle
  transition. The pre-registered boundary does not exist in these cooperative tasks
  under the frozen grid.
- **Track C (generator infeasibility):** under the 8-step locality cap the best
  reachable yields are 6.9 % (balance) and 0.0 % (sampling) against a 10 % floor —
  with faults verified applied via mean-shift diagnostics (−38.7 and −2.8 return).
  The pre-cap v3.1 evidence (20-step windows: 2.7 % / 0.1 %) shows removing the cap
  does not rescue sampling, and does not reach the band on balance either.

## Carried disclosure
The Phase A v3.1 23-case balance matrix (78.3 % unique minimal repair) is cited as
an indication only; per the PI it is not A.3 evidence.
