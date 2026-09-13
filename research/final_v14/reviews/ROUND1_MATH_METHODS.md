# Round 1: author-workspace mathematical and methods review

Date: 2026-09-13. Materials: THEORY.md, main sections model/theory/algorithm/methods, the proof supplement, the frozen solver, auxiliary recovery and policy code, tiny-game tests, DESIGN.json and the closest-work audit. Review capacity: developmental self-audit by the implementing assistant, requested by the author. This is not independent peer review. No journal editorial recommendation is made. Local review artifacts remain in the author's workspace; no unpublished manuscript text was submitted to an external review service.

# Comments to authors

## Evidence-bounded summary

The target is the minimum public revision budget needed to retain a specified amount of minimax adaptation value in a finite history-payoff game. The opponent calendar is held fixed. Calendar inclusion, exact response pricing and feasible-strategy bounds support a finite calendar search. Development experiments are in progress; the frozen-test results, final figures and completed paper are unavailable at this review stage.

## Strengths

Information sets explicitly exclude unexecuted commands. Independent reduced normal-form comparisons test the representation, separately from LP residuals. Player mirrors rebuild physical payoffs. The paper distinguishes forced speed, selectable ability, policy-class inclusion and changes in the opposing class. The protocol retains negative and unresolved results and distinguishes trace cost accounting from cold wall time.

## Major comments

### Major comment M1

**generality of the method contribution**

- Location: Theory and algorithm sections; LITERATURE_POSITIONING.md.
- Observation: Policy inclusion, double-oracle stopping, feasible-strategy lower bounds and branch-and-bound are established; combining their names is not a new general theorem.
- Evidence or criterion: Bošanský et al.2014 Theorem5.5; Kroer–Sandholm2018 Theorems1–2; the actual proofs in the draft.
- Why it matters: A mathematical/OR contribution must distinguish a specialized constructive result and useful decision consequences from standard foundations.
- Requested action: Credit the established components and base any contribution claim on calendar-specific certificates, structure and measured computational or decision increments; retain an explicit novelty limitation if those increments are weak.

### Major comment M2

**coarsening a mixed policy versus its behavioral representation**

- Location: Constructive deletion certificate and policy_v14.py.
- Observation: A realization-plan source must be extended at zero-reach histories; after deleting updates, its behavioral coarsening need not preserve the original root mixture.
- Evidence or criterion: Perfect recall justifies the pre-coarsening conversion, but it does not make two different coarsening operations identical.
- Why it matters: Confusing these constructions would invalidate the claim about the actual returned strategy.
- Requested action: Give the exact product-kernel construction, fix legal zero-reach behavior, identify the state-independent menu assumption, and evaluate its complete worst response.

### Major comment M3

**common-update cuts and hidden suffixes**

- Location: Common-update theorem; sequence-form appendix.
- Observation: A focal update alone is not necessarily a proper subgame if the opponent retains a private suffix.
- Evidence or criterion: Information-set closure at a subgame boundary; independent tiny normal-form and full sequence-form comparisons.
- Why it matters: An unrestricted Bellman recursion would give the focal player unavailable information.
- Requested action: Restrict decomposition to common boundaries, spell out the incoming sequence and terminal-payoff mapping, and keep full history in every subgame address.

### Major comment M4

**sufficient submodularity conditions**

- Location: Reset-game paragraph following the counterexample.
- Observation: The short phrase independent reset games does not by itself define the required strategy-space factorization.
- Evidence or criterion: Cross-component information or a shared opponent budget can destroy additivity despite additive rewards.
- Why it matters: A claimed sufficient condition must be checkable without assuming the desired modular value formula.
- Requested action: State Cartesian-product pure-policy sets and component-local payoffs, and prove matching product-strategy bounds; do not claim the formation model meets these assumptions.

### Major comment M5

**numerical certification and convergence language**

- Location: Solver outputs; algorithm termination; performance-retention rules.
- Observation: Feasible strategy repair and full responses support useful floating-point intervals, but fixed padding is not directed-rounding verification. Finite search may finish while its numerical gap remains unresolved.
- Evidence or criterion: The solver reports its actual gap; frontier tests include a threshold-straddling interval.
- Why it matters: Mathematical exactness and numerical certainty must not be conflated, especially when deciding a minimum budget.
- Requested action: State the interval scope everywhere, retain terminal upper bounds, separate possible/certified minimum budgets, and preserve timed-out attempts and remaining bounds under the fixed resource cap.

### Major comment M6

**interpretable replays must implement the selected policy**

- Location: Planned decision experiment and Figure8.
- Observation: A favorable single path cannot stand in for a mixed-strategy guarantee, and value-only decompositions do not provide a deployable policy by themselves.
- Evidence or criterion: A strategy must obey its calendar and its guarantee must be tested against the complete permitted opponent class.
- Why it matters: The final operational interpretation otherwise exceeds the numerical value computation.
- Requested action: Recover calendar-feasible policies, check their complete-response value, retain the complete replay probability law and use a payoff-independent rule for the displayed representative path.

### Major comment M7

**model foundation and historical calibration labels**

- Location: Directional-kernel foundation and archived calibration statement.
- Observation: The archived pooled metrics are arithmetic means of per-class metrics; the exported truth table also omits its class column.
- Evidence or criterion: The original exporter iterates DD/CL/CA/BB and concatenates blocks; arithmetic replay of20304 rows reproduces all class train/test metrics.
- Why it matters: Reusing the old label would misstate the validation target and the data's provenance.
- Requested action: Report the CA class actually used, document exporter-order reconstruction, distinguish rule-grid calibration from physical observations, and avoid global smoothness assumptions at angular boundaries.

## Minor comments

### Minor comment m1

**response theorem title**

- Location: Main response theorem title.
- Observation: Full-calendar response could be mistaken to refer only to the F calendar.
- Evidence or criterion: The theorem and implementation apply to every permitted fixed own calendar.
- Why it matters: The title should match its quantifier.
- Requested action: Rename it Response over the complete permitted policy class.

### Minor comment m2

**experimental units and historical exposure**

- Location: Methods table and design provenance.
- Observation: Some development endpoints were already inspected in v13, and frozen-test speed/distance are paired.
- Evidence or criterion: HISTORICAL_OVERLAP_AUDIT.json and DESIGN.json.
- Why it matters: Neither mirrors nor deterministic paired settings create independent samples for causal inference.
- Requested action: Mark known development exposure, retain the new frozen configuration pairs and state that they test algorithms rather than identify a speed effect.

## Limitations of this review

The reviewer is also the implementing assistant. Specialist verification of mathematical novelty remains necessary. This round does not assess unrun experiments, the final manuscript's overall argument, final citation consistency or page layout. Those are the second round's remit. The local skill validators check declared record structure rather than truth or publication merit.

# Confidential comments to editor

No editor channel is applicable to this author-workspace review. No report has been sent to a journal or another person.
