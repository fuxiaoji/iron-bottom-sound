# 07_COMPILER_FIDELITY.md — NOT TESTED (Stage B gated on Mechanistic Gold PASS)

Stage B would test whether the intent-to-plan compiler can reproduce the five
MG geometries. It is gated on a >= 4/5 Mechanistic Gold PASS, which did not
occur (3/5). Recorded so the next round starts here:

- Targets are now CONCRETE: the MG geometries (6/9 ships broadside in the
  cross-T arm; 3 mounts bearing vs 1; expected-hit deltas per ship) are the
  compiler's acceptance criteria, per intent:
  CROSS_T_PORT, CROSS_T_STARBOARD, UNMASK_BROADSIDE, RANGE_CONTROL,
  CONCENTRATE_LOCAL_FORCE, TORPEDO_SCREEN.
- Known compiler weaknesses to fix first: 60-degree quantization of desired
  headings; greedy per-ship plan matching (no fleet-shape objective); intent
  vocabulary aliasing (CLOSE/PRESS/CONCENTRATE compiled to one batch — F14).
