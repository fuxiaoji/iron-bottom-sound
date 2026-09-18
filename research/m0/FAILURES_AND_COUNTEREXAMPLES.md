# FAILURES_AND_COUNTEREXAMPLES.md

Everything here is a negative result, a modelling trap, or a mistake that was
made and then found. Under the plan's discipline these are the most valuable
artefacts in the checkpoint, because each one is a place where a less careful run
would have produced a confident wrong answer.

---

## F1. The lab was degenerate, twice, and both degeneracies look like a clean "no aliasing" result

**What happened.** The first version of the exact lab modelled the public signal as
`q_t = sum(ao_hist) mod m` with the opponent's action `ao_t = (theta + sum(ao_hist)) % b`
and a uniform prior over `theta`. The B0 census then reported:

```
coordination  K=3  snapshot cells w/ mixed beliefs = 0   maxgap = 0.0000
anticor       K=3  snapshot cells w/ mixed beliefs = 1   maxgap = 0.0000
delayed       K=3  snapshot cells w/ mixed beliefs = 3   maxgap = 0.0000
pathdep       K=3  snapshot cells w/ mixed beliefs = 3   maxgap = 0.0000
```

Read naively that is "public-state aliasing does not exist → `B_FAIL`".

**Why it was wrong.** `q` was independent of `theta`, and `theta` uniform, so the
posterior over the *next opponent action* was **uniform no matter what was
observed**. No policy can be better informed by a signal that carries no
information: the belief never became informative, so nothing could be aliased.
The lab was measuring its own assumption.

**Second, subtler degeneracy.** After making the signal informative
(`q = (alpha*theta + sum) mod m`), a second trap appeared: with `K = 2, m = 2` one
has `ao_0 = theta` and `q_1 = theta`, so **the signal identifies the doctrine
outright at the first observation**. Ambiguity then cannot persist, and again
there is no aliasing. The working configuration requires `K > m` (or equivalent
non-injectivity) *and* `alpha != 0`.

**Consequence that is now enforced in code**: `GameSpec.snapshot_lossy` returns
`False` whenever `alpha == 0`, and the witness search skips non-lossy specs. Any
future run that silently drops `alpha` will produce a vacuous "no aliasing"
result — this is the single most dangerous failure mode in Track B.

## F2. The plan's own aliasing metric gives a false negative

**What happened.** The plan defines
`AliasGap(z) = max_{phi(h)=phi(h')} max_a |Q*(h,a) - Q*(h',a)|`. Measuring the
value spread `max |V(h) - V(h')|` across the discovery grid returned:

```
max_v_gap = 0.0   in ALL 72 sealed-commitment games
```

Read literally, that kills Track B (`B_WEAK`) — and it would have been wrong.

**Why it was wrong.** In these games every node inside a snapshot cell can
*reach* the same optimal value, but by a **different action**. The value is not
lost; the *policy* is ill-defined. Example from the minimal witness
(`witness_T3_b3_K3_L2_coordination`, snapshot `(t=3, q=1, af=1, rf=1)`):

| node | observation history | optimal option | `V` | `V_continue` | `Delta` |
|---|---|---|---|---|---|
| A | `(0, 0, 1)` | `replan(2)` | 0.0 | −1.0 | **2.0** |
| B | `(0, 1, 1)` | `continue` | 0.0 | +1.0 | **0.0** |

Same snapshot. Opposite decision. `V` identical. `Delta` differs by 2.0.

**The correct quantity** is the snapshot-policy regret
`min_a max_h [ V(h) - Q(h,a) ]` — the worst-case loss of the best single option a
stateless policy may commit to. Under that metric the same grid reports:

```
18/72 sealed games with strictly positive snapshot regret
max 2.0, mean 0.361, action-disagreement rate 0.291
controls (Markov K=1, negative control): 0.0 on every metric
```

**Lesson carried forward**: for Track B, never report a value-spread metric
alone. A value-spread of zero is compatible with a completely aliased state.

## F3. A hypothesis that was written into a test before it was checked

`test_forced_continue_equals_brute_force_sequence` asserted that forcing
`continue` forever reproduces the fixed-sequence value. It **failed immediately**
(`3.0 vs -3.0`). The test was wrong, not the solver: `W(..., "replan", a)` means
"take `a` now, then play **optimally**", which is strictly better than repeating
`a` forever whenever a later replan helps. It was replaced with a genuine
forced-policy evaluation (`reference._evaluate_policy` with a hand-built policy).

This is recorded because the first instinct on a red test is to suspect the code
under test; here the *expectation* was the bug.

## F4. A dominance artefact in the action model

In the lab, `replan` to an action `a` resets the commitment to `L-1` remaining
turns, while `continue` decrements it. Replanning to the *same* action is
therefore weakly better than continuing (more future freedom for free). As a
result `V_replan >= V_continue` always, `Delta >= 0` by construction, and the
`continue` option is never strictly optimal at the moment of decision.

**This is a modelling choice, not a discovered fact**, and it means the lab's
`Delta` is an *upper* bound on the value of replanning in a setting where
replanning has no cost. A real CARP needs an explicit planning *cost*; the lab has
none. Any Track A claim that depends on replanning being expensive does **not**
follow from these numbers.

## F5. "Hidden information that cannot matter" is behaviourally identical to "no hidden information"

The negative control (`family="null"`, `K=3`, doctrine present but payoff-blind)
scores **0.0 on every aliasing metric**, exactly like the Markov control. This is
the intended behaviour of a control, but it carries a warning for **Track D**: a
test-selection method that only separates "there is hidden state" from "there is
not" will pass every sanity check while being useless for identifying *mechanism*.
Track D must be validated against mechanism-level confusions, not difficulty.

## F6. The repository test suite did not finish, and one test fails

`pytest tests/ -q` over 53 files was still running when this checkpoint closed;
one failure (`F`) appeared in the first 13%. The failing test's name was **not
captured**, because pytest had not printed its summary.

This is recorded as an **open item**. It does not invalidate the cheap kill tests
(they live in `research/m0/` and do not import the engine's test fixtures), but
**the repository's own regression status at commit `7ab8ac4` is not
established**, and nobody should claim it is.

## F7. `M0_RESEARCH_PLAN.md` was not where the task said it was

The task states the plan is in the repository root. It is not present at the
audited commit; it was supplied as an external attachment. It has been copied
into the repo verbatim (1611 lines) so the evidence package is self-contained.
No other statement in the task was found to be wrong.

## F8. Only 3 of 15 scenarios are playable

`engine.scenarios()` returns 15 ids; `engine.reset()` raises
`KeyError: "Scenario IBS-S-XX is catalogued but not playable"` for 12 of them
(`IBS-S-02`, `IBS-S-04` … `IBS-S-14`). This contradicts a natural reading of the
plan's "current repository scenarios" and it caps Track C's scenario breadth at
three. It is a repository fact, not a bug introduced by this work, and it was
**not** "fixed" — the plan forbids touching production semantics.

## F9. A digest that looks stable but is not

The P0 baseline fingerprints matches with `hash(repr(events))`. Python salts
`hash()` per process, so the digest **is not comparable across invocations**;
within one process the determinism comparison is exact and it did match. The
digest was reported in `BASELINE_STATUS.md` with this caveat attached. A future
version should use `hashlib.sha256` on the serialised events instead.


---

## F10. Two bugs in the Track C sampling code, both found by running the experiment

**Bug 1 — half-matrix round-robin.** `select_cell("uniform")` keyed its
round-robin on the *total sample count*; under batched sampling (batch = 25)
only every other cell was ever visited, so half the matrix stayed at the full
interval and the certificate never tightened. Symptom: width stuck near the
maximum. Fix: key the round-robin on the batch number.

**Bug 2 — unsampled-cell deadlock in the candidate.** `cert_sensitivity`
evaluates each cell by "halve its interval and recompute the certificate". For
an *unsampled* cell the trial used pseudo-counts `[2, 0, 2]`; under
Hoeffding with 36 cells the resulting half-width is still ≈ 1.9, the interval
clamps to (−1, 1), the trial shows **no improvement**, and the unsampled cell is
never chosen — so the certificate pinned at width 2.0 forever. Symptom: S-03
`cert_sensitivity` seeds reporting `width=2.000` after 90k matches. Fix:
unsampled cells are taken first (resolving a full interval is the largest
possible width reduction by definition).

Both were fixed **before any number from the fixed code entered the report**, and
the unit tests were re-run green after the fixes. They are recorded here because
"the first implementation of the clever policy was broken in a way that made it
look hopeless, twice" is exactly the failure mode a cheap kill test exists to
catch — and because the *symptoms* (stuck width) are indistinguishable from
"the method doesn't work" unless you read the logs.

## F11. A property I believed that is false: certificate width is not trajectory-monotone

An early unit test asserted that the certificate width decreases monotonically
along a sampling trajectory. It failed with a tiny widening
(1.1210 → 1.1256). The cause is structural, not a bug: **Hoeffding intervals are
not nested** — as n grows the half-width shrinks but the centre (the sample
mean) moves, so a later interval need not contain an earlier one, and the LP
bracket can briefly widen. Confidence *sequences* (anytime-valid) would restore
monotonicity; they were deliberately out of scope for this checkpoint. The test
was replaced by the properties that do hold (per-cell half-width monotone in n
at fixed mean; widening a cell never shrinks the certificate; coverage).

## F12. A verdict-gate discrepancy, left in place and escalated

The pre-declared *textual* gate for Track C ("saving 10–40% **or inconsistent
across scenarios** → `C_SMALL_EFFECT`") and the *coded* branch ("candidate never
reached → `FAIL`", evaluated before the inconsistency clause) disagree on the
S-01 outcome: the candidate saved 71% on S-03 but never reached the target on
S-01. Re-coding the gate after seeing results would be exactly the post-hoc
manipulation the plan forbids, so the recorded verdict is the coded one
(`FAIL`), and the discrepancy is flagged in the report and registry for the PI.
This entry exists so nobody later "fixes" the verdict silently.

## F13. The support-weighted baseline does not produce certificates at all

`support_weighted` — sample cells proportionally to the current meta-strategy
support × best-response — never reached the certificate target on **either**
scenario (width 0.77–1.40 after 90k matches). It starves off-support cells, and
the certificate bracket is dominated by exactly those cells (the adversary's
best response can exploit any unresolved cell). Not a bug: a genuine negative
result, and a warning for the common EGTA intuition that "sampling the
equilibrium support is enough". It is not enough when the deliverable is an
*exploitability/value certificate*.
