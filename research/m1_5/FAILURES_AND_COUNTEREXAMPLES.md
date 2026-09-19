# FAILURES_AND_COUNTEREXAMPLES — M1.5

## F1. The pre-registered E2 profile list cannot exercise the machinery at HEAD
`balanced` (and every `torpedo_doctrine="legacy"` profile) branches to the
legacy assist path and never calls `AdaptiveTorpedoPlanner` — no counterfactual
influence fields exist for it. Amended to the five doctrine-bearing profiles
BEFORE any E2-T1 aggregate existed (PRE_REGISTRATION.md, Amendment
E2-T1-PROFILES). This is the plan's own "以当前 HEAD 为准" case.

## F2. Two sampling-quota bugs in the E2-T1 sampler
(a) The total target (200) was consumed entirely by the first scenario, then
entirely by the first profile — the first "complete" run was 208 decisions
from 1 scenario / 1 profile. Both quota structures were fixed (per-scenario,
then per-profile) and re-run; the reported 200 = 2 scenarios × 5 profiles ×
40. All fixes happened before any gate number was read; the intermediate runs'
outputs were overwritten and never used as evidence.

## F3. Missing persistence of the option `order` field
The first E2-T1 sample did not persist `TorpedoTacticalOption.order`, which
E2-T2 needs to reconstruct the torpedo batch. Sampler fixed and re-run (cheap:
state capture only). Recorded because it silently blocks the downstream test.

## F4. `Side.other()` does not exist at HEAD
E2-T2's first rollout run crashed with AttributeError inside every rollout
(meaning all arms returned errors); the summary then crashed on
`statistics.mean([])`. Two fixes: an explicit other-side computation, and the
summary now persists per-state results BEFORE aggregating so incomplete runs
stay visible. After the fix: 40/40 states complete.

## F5. numpy bool_ is not JSON serialisable
E1-T2's gate dict crashed on dump; cast to Python bool. Cosmetic, recorded for
completeness.

## F6. The "mean relative improvement +19%" artifact
`mean(d / |direct|)` over paired states produced +0.19 for hybrid-vs-direct
purely from tiny-denominator states (|direct outcome| ≈ 0 with 5 replicates of
a ±1 variable). The honest paired summary is mean +0.02 with 24/40 exact ties.
Reported both, gate evaluated on the raw diffs.

## F7. E1-T2 label noise (declared, not fixable post-hoc)
rho labels on non-CI-passing pairs are measured but ranking-uncertain (M1's
power wall). The classifier therefore trains on 13 noisy positives / 120. This
can only have made T2 look BETTER or worse than truth; the observed <=0.47
AUROC across three families is far from the 0.75 gate either way, so the FAIL
stands under any noise model. A clean-label run on the 30 CI-passing states
would be statistically meaningless (6 positives, 6-state folds) — noted rather
than run.

## F8. Selection bias in the E1-T1 population (declared scope)
The pair population conditions on a live hidden-commitment difference; the
unconditional rho distribution over all IBS states is trivially lower. E1-T1
is a conditional measurement, which is the operationally relevant one for
"when a difference exists, does it force an action change" — declared in
PRE_REGISTRATION before computing.
