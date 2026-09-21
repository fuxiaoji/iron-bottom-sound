# 01_METRIC_HIERARCHY.md — PI Decision 1, as executed

Two scales, two different questions. They are never merged, and a divergence
between them is a result, not an error.

| level | question | quantity | where computed |
|---|---|---|---|
| **L0** intent / mechanism fidelity | was the intent correctly compiled? | focal ship → its recorded target: legal **visible**-fire EH and usable mount count | `b1e.local_metric`, `m22_b0.pair_net` |
| **L1** team tactical utility | is this local tactic good for the fleet? | `U_team = FIRE_SEARCH own EH − FIRE_SEARCH enemy EH` | `b1e.team_metric` |
| **L2** long-horizon game value | deferred | — | not measured in M2.2-R |

```
ExternalityGain = delta_L1 − delta_L0          (both vs the CURRENT_POLICY arm)
MECHANISM_SUCCESS_BUT_NEGATIVE_EXTERNALITY  iff  delta_L0 > 0 and delta_L1 < 0
```

Per the PI, that flag is **not** a compiler failure.

## Why this replaces the M2.2 primary/supplementary split

M2.2 measured the frozen `M_broad` fleet-wide and found the hand-built broadside
*loses* to random (−12.17 vs −6.32), while the pair-restricted version of the
same formula makes the same case a compiler gap. That was reported as a
metric-validity blocker. Decision 1 resolves it by giving each scale a role
instead of asking one number to answer both questions — and it changes one
input: **L1 uses `FIRE_SEARCH`**, where the M2.2 fleet panel used
`LEGAL_FIRE_HEURISTIC`. B1E therefore recomputes L1 from scratch; the M2.2 panel
stays in the record unchanged and is not comparable to L1 without noting the
evaluator difference.

## The two scales disagree, and the disagreement is the finding

MG1 frozen case (`metrics/mg1_dual_scale.json`, reproduction re-verified:
`reproduced = true`, all seven M2.1-R2.1 invariants exact):

| arm | L0 EH | L0 mounts | ΔL0 | L1 U_team | ΔL1 | externality |
|---|---|---|---|---|---|---|
| CURRENT_POLICY | 1.611 | 2 | — | −6.722 | — | — |
| CURRENT_INTENT_PRE_FIX | 1.556 | **1** | −0.056 | −18.083 | **−11.361** | −11.306 |
| REPAIRED_INTENT_BASELINE | 2.278 | 2 | **+0.667** | −12.556 | **−5.833** | −6.500 |
| RANDOM_LEGAL (mean of 8) | 2.194 | 2.75 | +0.583 | −8.694 | −1.972 | −2.556 |
| BEAM_SEARCH_COMPILER | 2.083 | **3** | +0.472 | **+0.694** | **+7.417** | **+6.944** |

Three readings, all of which matter:

1. **The pre-fix intent compiler is worse than doing nothing on both scales** —
   L0 −0.056 (mounts 2 → 1) and L1 −11.361. The inverted turn does not merely
   fail to help; it removes a mount and costs 11.4 EH of team margin.
2. **The repaired compiler wins L0 and loses L1** (+0.667 local, −5.833 team,
   externality −6.500) — a textbook
   `MECHANISM_SUCCESS_BUT_NEGATIVE_EXTERNALITY`. The intent is now compiled
   correctly and the fleet is worse off. Under the M2.2 framing this would have
   read as a compiler shortfall; under Decision 1 it is a **finding about the
   tactic**, not about the compiler.
3. **Only the joint search improves both** (ΔL0 +0.472, ΔL1 +7.417,
   externality +6.944). The mechanism value is joint and symmetry-aware: it is
   realised by coordinating the whole line, not by turning each ship into the
   broadside arc.

Note the ordering collision worth recording: `RANDOM_LEGAL` beats
`REPAIRED_INTENT_BASELINE` on both L0 and L1 here. A single intent applied per
ship is not a tactic; a random single-ship perturbation that happens to improve
fleet geometry can beat it. This is why `REPAIRED_INTENT` is a baseline and
never a candidate method.

## Evaluator provenance

`FIRE_SEARCH` is the repaired per-mount allocation search (M22-F2 fix;
calibration Spearman 0.908 against `LEGAL_FIRE_HEURISTIC`). It is named SEARCH
and is never called optimal or an oracle. The beam's *selection objective*
inside `beam_search_movement` is still `LEGAL_FIRE_HEURISTIC` net EH — frozen in
the M2.2 pre-registration and unchanged here — while its *reported* L1 uses
`FIRE_SEARCH`; the two are recorded side by side rather than conflated.
