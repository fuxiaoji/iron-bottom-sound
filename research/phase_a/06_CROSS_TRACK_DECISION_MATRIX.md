# 06_CROSS_TRACK_DECISION_MATRIX.md

| Track | Problem exists? | Simple positive scheme works? | Cross-task? | External family? | Closest-prior risk | Engineering risk | Status |
|---|---|---|---|---|---|---|---|
| A adaptive compute | not measured | not measured | — | not attempted | medium (test-time compute allocation is active) | low — instrument validated, policy certified | **BLOCKED** |
| B failure boundary | not measured | toy-validated only (3.4x/2.7x at K=50/100) | — | not attempted | medium (active boundary discovery exists in RL) | low — instrument validated | **BLOCKED** |
| C counterfactual attribution | not measured | toy-validated only (unique minimal repair set recovered) | — | not attempted | **high** (crowded; needs the query-efficiency angle) | medium — exhaustive matrix is compute-heavy | **BLOCKED** |
| D resilience | not measured | — | — | — | low | low | NOT_ACTIVATED |

No row carries a scientific verdict, and the local AI does not select a mainline.
`SELECTED_MAINLINE` is deliberately absent from `metrics/phase_a_verdict.json`.

## What the PI can act on today

- **Certified infrastructure**: environment lock, native-oracle correction, three
  passing positive controls, six verified checkpoints, a 500-episode clean
  baseline with a documented task switch. A rerun of Tracks A–C needs no new setup.
- **Two design corrections already baked in**: the native oracle must be the
  scenario's own `done()`, and the Track A allocation total must admit a
  non-uniform optimum (the toy proved that a total of 32 does not).
- **One open risk**: the surviving task's 87.6 % clean success may leave little
  room for planning gains; the replacement task's clean baseline is not yet
  measured.
