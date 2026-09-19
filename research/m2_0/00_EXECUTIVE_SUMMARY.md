# 00_EXECUTIVE_SUMMARY.md — M2-0 organizational intelligence validation

```
P0_MODE_AUDIT        = PASS   (classic/realistic semantics verified at HEAD; doc/code
                               formation-cap mismatch recorded, not fixed; <=4 used)
D0_MACRO_EXECUTOR    = PASS   (5 tests + 1 declared skip; validator-passed expansion;
                               no-silent-repair verified by constructive counterexample)

A_ORACLE_SIGNAL      = FAIL   (flat is the tied-best partition on 25/35 = 71% of usable
                               snapshots; L=0 on 68% of partition evaluations)
A_STATE_DEPENDENCE   = PASS   (48.6% >= 30%: minimal-safe partition differs from fixed)
A_COMPRESSION_VALUE  = PASS   (median saving 60%/77.5% with retention ~100%)
A_LEARNABILITY       = NOT_RUN (moot — oracle gap absent; A2 skipped per plan §31.6)
A_NOVELTY            = NOT_REVIEWED (moot)
A_VERDICT            = A_FAIL_ORACLE

B_NATURALITY           = PASS (65% of 150 realistic matches have transfer/disruption;
                                226 independent cases across 58 scenario x profile cells)
B_HIERARCHY_SENSITIVITY= PASS (25% of 12 valid natural shock cases have sensitivity
                                >= 0.05; max 0.767; both scenarios)
B_ROBUST_ORGANIZATION  = B_ORACLE_ONLY (the only non-degenerate improver,
                                flagship_low_exposure, is scenario-opposed:
                                EM-01 +0.252 / S-01 -0.083; flagship_max_vp is
                                degenerate == default (31/31 ties); random arms
                                noise-level)
B_NOVELTY              = NOT_REVIEWED (moot)
B_VERDICT              = B_ORACLE_ONLY

C_PHASE_DIFFERENCE = FAIL (granularity is scenario-dominated, not phase-dominated:
                           S-03 min-safe K=1 in both phases; S-01 K=2 both phases)
C_VERDICT          = C_MODULE (movement compression exists; no cross-phase lever at HEAD)

BEST_EVIDENCE_TRACK = NONE
SECOND_BEST_TRACK   = NONE
TRACKS_TO_KILL      = Track A (oracle), Track C (module-only), Track B (org design
                      effect not robust across scenarios)
BIGGEST_UNRESOLVED_RISK = every candidate signal (compression, hierarchy
                      sensitivity, robust org) is real but none survives its
                      own next gate: compression has no loss to reduce (flat
                      already optimal), sensitivity does not convert into a
                      design advantage that generalizes across scenarios.
```

## The phase in one paragraph

All infrastructure the plan demanded was built and passed: a mode-semantics
audit with the documented 4-vs-8 formation-cap mismatch recorded (not fixed),
an exact team-abstraction lab with two independent solvers and all four
required cases (6/6 tests), and a rule-constrained ResearchGroupExecutor on
classic semantics (validator-passed, deterministic, no-silent-repair). On top
of it, the Track A oracle measured 60 movement snapshots across 2 scenarios x
3 profile pairs with CRN replicates under three pre-registered mechanics
amendments. The result is unambiguous in the direction the plan feared:
**flat per-ship control is already the ceiling** — grouping is nearly
lossless (68% of evaluations have exactly zero loss) but flat beats or ties
every partition in 71% of snapshots, so there is no compression-value trade-off
to learn; "minimal-safe K" is small everywhere and structure does not beat
random grouping. Track B found the strongest natural phenomenon of the round
(65% disruption incidence; hierarchy changes worth up to 0.77 of normalized
value after a natural shock) but the only simple robust-organization rule that
beats default does so in one scenario and loses in the other, which is
`B_ORACLE_ONLY` by the plan's own definition. Per the plan's §31 discipline —
oracle first, never train without a gap — nothing was trained, and the honest
verdict is that Organizational Intelligence, like the four M0 tracks and the
M1 hidden-commitment line before it, does not currently present a CCF-A
mainline on this platform.

## What a future attempt would need (evidence-based, not speculation)

1. A regime where grouping actually costs something (the current snapshots'
   scripted-play continuation is too forgiving: HOLD-everything is near-optimal
   from most states — the same regime-killer that killed M1 G1).
2. An opponent/policy mix that punishes static formations (B0 shows EM-01 at
   94% disruption incidence — the failure machinery exists; the *value lever*
   for exploiting it does not, under self-play scripted policies).
3. Cross-scenario stability of any organizational design effect before
   blueprinting (B2's scenario-opposed sign is the cautionary tale).
