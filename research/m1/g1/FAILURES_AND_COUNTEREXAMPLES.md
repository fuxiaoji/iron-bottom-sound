# FAILURES_AND_COUNTEREXAMPLES.md — G1

## F1. The pre-declared primary value function is degenerate in IBS-S-03

S-03 ends with an axis win from most reachable branch states regardless of the
allies' torpedo decision (pilot: 56 of 213 branch-A candidate means sit at
exactly −1; the rest spread over {−0.6..+1.0} but with outcome regret ≥ 0.10 in
only 1/60 evaluable pairs). A value function that barely moves cannot carry a
regret gate. This was anticipated as a risk in `Q_ESTIMATION_METHOD.md`
(secondary `damage_diff` added for exactly this reason), and the pilot numbers
are reported on both value functions. It is a property of the scenario +
scripted continuation, not a bug.

## F2. The task's CI rule and a 5-replicate budget are incompatible (power wall)

The task pre-declares: "action ranking CI 大量重叠的 pair 不进入主分析". With 5
dice-stream replicates, action-ranking signal exceeds 2×SE in only 16/120
evaluable pairs (either value function) — a power wall, not a pipelining bug
(Control A confirms the pipeline is exactly deterministic; the noise is genuine
outcome variance). Consequence: only 8 pairs are valid for the primary
analysis against the task's own rule, far below the ≥25 the gate requires. A
power-extension probe (15 replicates, 4 pairs) was run to decide whether a
2.3-hour re-run could repair this; see F4 for its result.

## F3. Normalized regret inflates when the decision stake is tiny

`normalized_regret = R / stake` with `stake = max_x (V_x − min_a Q_x(a))`.
When all candidates are nearly equally (in)effective, stake is tiny (pilot
median 0.036 of total hull on `damage_diff`, max 0.235) and normalized regret
can approach 1.0 while the ABSOLUTE regret is a fraction of a percent of the
fleet's hull — strategically meaningless. The biggest control-B case
(`IBS-S-01_s3_t2_..._KINUGASA_1P1S1S-0`) reaches normalized 0.777 with an
absolute damage-regret of ~0.02–0.04. Any future gate on this metric needs an
absolute-stake floor; adding one post-hoc here would be result-dependent
gerrymandering, so the pilot reports raw and normalized side by side and the
gate is evaluated as pre-declared.

## F4. Confidence and regret are anti-correlated in this window (the central negative finding)

Across the 120 evaluable pilot pairs, the pairs whose action rankings are
statistically resolvable (signal > 2×SE) are exactly the pairs where one
action is clearly fine in BOTH worlds — so their shared-action regret is ~0
(median 0.000, max 0.081 on `damage_diff`; 0.000 on `outcome`). Conversely,
pairs with large normalized regret (28/120 ≥ 0.10 on `damage_diff`) have
close, noisy rankings — precisely the ones the CI rule excludes. The power
probe (F2) tests whether 15 replicates break this anti-correlation; its
outcome is recorded in `logs/probe_15rep.json` and reflected in the executive
summary. Mechanistically: the game's own candidate sets always contain robust
actions (notably "hold fire"), and torpedo hits under scripted play are rare
enough that candidate choice rarely reorders between worlds. Hidden-commitment
VALUE divergence is common (65/120 pairs show outcome divergence ≥ 0.2 — the
worlds genuinely differ), but it rarely propagates into DECISION incompatibility
over the game's own candidate sets.

## F5. "Distant ship ⇒ irrelevant commitment" is false in IBS

Control B was constructed as "change the farthest ship's movement; predict no
decision effect". Measured: control-B pairs reach normalized damage-regret up
to 0.777 (absolute ~0.02–0.04) — distant ships interact through long-range
gunnery and the victory condition over the remaining turns. The control's
design assumption was wrong; it still functions as a control in the honest
sense (its regret distribution is reported against the main pairs), but it
does NOT provide the clean "≈0" baseline the plan hoped for. Lesson: in IBS,
essentially every hidden movement difference is potentially decision-relevant
somewhere down the line; the question is only how much, how soon.

## F6. Candidate-set dependence of R (conservative bias, documented)

R is computed over the game's own candidate proposals (≤6 per pair, including
"hold fire"). A richer candidate set can only DECREASE R — so R is a lower
bound over all legal torpedo batches, which biases the gate AGAINST finding
aliasing. This is the conservative direction and was pre-declared in
`Q_ESTIMATION_METHOD.md`; it means the observed FAIL is not an artifact of a
starved candidate set — a starved set would have inflated R, not deflated it.

## F7. Pilot vs power-extension discipline

The 5-replicate run is labelled a PILOT. The 15-replicate run (if executed)
uses the SAME frozen pairs, value functions, candidate sets and CI rule, with
replicates increased uniformly and outcome-blind — an amendment recorded in
`EXPERIMENT_REGISTRY.csv` before its results were inspected. No pair, value
function, or threshold was changed after seeing results.
