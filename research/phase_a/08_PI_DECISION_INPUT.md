# 08_PI_DECISION_INPUT.md

## Where Phase A ends

Every candidate has now been killed or blocked **on valid, corrected evidence**:

| track | first answer | what was wrong | final answer after repair |
|---|---|---|---|
| A adaptive compute | A_KILL (v3.1) | "oracle" was a greedy heuristic scoring below a feasible allocation | **A_KILL_CONFIRMED** (exact knapsack; gap 0.01-0.13 % vs 8 %) |
| B boundary discovery | B_KILL (v3.1: universe < K, fake generic) | invalid design run | **B_KILL_FOR_MAINLINE** (valid run; positive control 61x/46x; boundary absent: 0.42 % / 2.08 % of multi-level lines vs >= 20 %) |
| C attribution | blocked (v3.1) | low yield, no matrices | **C_GENERATOR_FEASIBILITY_FAIL** (28-setting calibration, both tasks, under the locality cap) |

## What is solid

- Track B's kill is the project's first *clean* kill of this track: the instrument
  is proven on synthetic geometry, the universe is valid, the labels are immutable,
  and the gate that fails (nontrivial boundary) fails by **two orders of magnitude**
  (0.4 % / 2.1 % vs 20 %). The residual caveat is grid coarseness (1-4 severity
  levels per modality), which bounds what any within-line method could detect.
- Track C's failure is a property of the frozen materiality semantics (sampling:
  0.5·IQR = 41.7 return) versus what any ≤8-step local fault can do (~1-3 points).
  The pre-cap evidence (20-step windows: 2.7 % / 0.1 %) shows the cap is not the
  binding constraint.

## Options that remain lawful (and their cost)

1. **Accept NONE and stop Phase A** — the default; all evidence is packaged.
2. **B revival path** — a new perturbation design with a denser severity axis
   (e.g. 8-16 levels) and multi-agent *coupled* faults. That is a new pre-registered
   phase, not a rescue of this one (plan: "No further rescue run").
3. **C revival path** — either relax the locality cap or redefine sampling
   materiality; both are semantic changes only the PI can authorise.

## Machine-readable

`metrics/phase_a3_verdict.json` — statuses, gates, per-task numbers; no
`SELECTED_MAINLINE` value is filled.
