# CHEAP_KILL_REPORT.md — M0 cheap kill tests

**Status: CHECKPOINT. This is the milestone the plan asks to stop at.** No
discovery, no confirmatory, no large-scale runs were started.

| | |
|---|---|
| Branch | `research/m0-validation` |
| Baseline commit | `7ab8ac4acdf029e6ea14346d568c3f509abd9390` |
| Repo | `fuxiaoji/iron-bottom-sound` |
| Exact lab | `research/m0/exact_lab/` — 17/17 tests pass |
| Discovery grid | 74 games, 1573 decision nodes, all values exact |
| IBS matches consumed | **2,238** of 20,000 (78 P0 + 2,160 C0 calibration) |
| Paid LLM API calls | **0** |
| Engine files modified | **0** |

## Verdicts at a glance

| Track | Verdict | One-line reason |
|---|---|---|
| A — CARP | **`WEAK`** | signal exists and has the right shape, but 38% of games have zero replanning value and a fixed calendar already meets the bar on 24% of evaluable points |
| B — CAIS | **`PASS_TO_DISCOVERY`** | 18/72 sealed games have strictly positive snapshot regret (max 2.0) while both controls are 0.0 — but only under a lossy-*informative* signal, exact lab only |
| C — CD-PSRO | **`FAIL`** (borderline, PI to adjudicate) | 71% saving on the close game, total failure (0/5) on the lopsided one; coded gate says FAIL, textual gate would allow SMALL_EFFECT |
| D — DiagGame | **`FAIL`** | MYO≡OPT and NBU≡NOM on all 684 tests — 4/5 defect types unidentifiable in principle on this generator |

---

# Track A — CARP (Certified Adaptive Replanning)

**hypothesis**: in games with a strategic opponent holding sealed commitments,
`always replan` is not necessary; an adaptive gate can cut planning calls
substantially while retaining strategic value, and the resulting loss admits a
non-vacuous certificate.

**result**: `A_WEAK`

**strongest evidence**

- Replanning value is *not* uniformly zero: over 1573 exact decision nodes the
  mean `Delta = V_replan - V_continue` is **0.849**, std **0.963**, max **2.0**.
- Replanning value decays with the remaining horizon — mean `Delta` by
  `remaining_horizon` 4/3/2/1/0 is **0.367 / 0.475 / 0.568 / 1.007 / 1.087** —
  i.e. the signal is not noise, it has the expected shape.
- Within a *single public state*, `Delta` spreads by **1.365 on average** (max
  2.0) over 189 snapshot groups. "How much is a replan worth here" is genuinely
  state-dependent, which is the precondition the CARP story needs.

**strongest counterevidence** (this is what produces `WEAK`)

- **28 of 74 games (38%) have zero compute-value span**: `never plan` is worth
  exactly as much as `always plan`. In these games there is no compute/value
  trade-off to learn at all.
- **55% of all `Delta` values are below 0.1** — the median `Delta` is exactly
  **0.0**. The signal is concentrated in a minority of nodes.
- A **trivial fixed schedule** (periodic `t % P == 0`, or random-K) already meets
  the pre-declared bar (saving >= 30% **and** retention >= 95%) at
  **64 of 268 evaluable points (24%)**. A learned gate would have to beat a
  calendar, and on a quarter of the evaluable points the calendar already wins.
- Commitment length does **not** modulate `Delta` as the story predicts: mean
  `Delta` is 0.864 at `rf = 1` and 0.822 at `rf = 2` — essentially flat.

**estimated effect**: if the zero-span games are excluded, the remaining games do
show a frontier; the gate verdict on the full grid is a **38% dead-weight
fraction**.

**engineering risk**: low. Everything measured is exact and fast.

**current verdict**: **`WEAK`**

**why not `FAIL`**: a real state-dependent replanning signal exists with the
right shape (monotone in horizon), and it is large in the games where it exists.
**why not `PASS_TO_DISCOVERY`**: on 38% of games there is no trade-off to learn,
and on 24% of evaluable points a fixed calendar already satisfies the acceptance
bar, so "learn when to replan" is not yet separated from "replan on a schedule".
Proceeding needs a *reason* why the fixed calendar fails — that has not been
demonstrated.

---

# Track B — CAIS (Commitment-Aware Information State)

**hypothesis**: hidden pending commitments make the public state aliased —
`o(h) = o(h')` while `Q*(h, .) != Q*(h', .)` — and a commitment-aware
representation recovers a continuation-sufficient state.

**result**: `PASS_TO_DISCOVERY` — **but the plan's literal H-B1 is only
half-confirmed, and the metric matters more than the result**

**strongest evidence**

- **18 of 72 sealed-commitment games show strictly positive snapshot regret**
  (worst-case loss of the best single cell-wide action), max **2.0**, mean
  **0.361**. Concretely: no stateless policy can act well on every situation the
  snapshot conflates.
- **24 of 72 games show outright optimal-action disagreement** within a snapshot
  cell (mean disagreement rate **0.291**).
- The **controls are clean**: the Markov control and the negative control
  (hidden doctrine present but payoff-blind to it) both score **0.0** on every
  aliasing metric. So the effect is specific to the hidden-commitment mechanism,
  not an artefact of the lab.
- Minimal witness (Case 2, `witness_T3_b3_K3_L2_coordination`, snapshot
  `(t=3, q=1, af=1, rf=1)`):
  - node A `obs=(0,0,1)` → best option `replan(2)`, `V_continue = -1`, `Delta = 2`
  - node B `obs=(0,1,1)` → best option `continue`, `V_continue = +1`, `Delta = 0`
  - **same snapshot, opposite decision, `Delta` differs by 2.0.**

**strongest counterevidence — and it is a measurement finding, not a nuisance**

- **`max_v_gap = 0.0` in all 72 sealed games.** If "aliasing" is measured the
  literal way the plan writes it — the spread of optimal values `V = max_a Q`
  inside a cell — the answer is *always zero*, and Track B would have been killed
  as `B_WEAK` on a metric artefact.
- The reason is structural: in these games every node in a cell can *reach* the
  same optimal value, but by a **different action**. A value-spread metric is
  therefore blind to it. The correct quantity is the **snapshot-policy regret**
  `min_a max_h [ V(h) - Q(h,a) ]`, which is positive exactly when the value is
  reachable but not by one shared action.
- Model-side caveats that bound what may be claimed: with `alpha = 0` (the signal
  carries no information about the doctrine) the lab is **provably degenerate —
  no aliasing is possible at all**; and with `K = 2, m = 2` the signal identifies
  the doctrine outright at the first observation, again killing aliasing. Both
  degeneracies were found by measurement and are documented in
  `FAILURES_AND_COUNTEREXAMPLES.md`. **The observed aliasing is therefore
  conditional on a lossy-but-informative public signal**, which is a modelling
  assumption, not a fact about Iron Bottom Sound.

**estimated effect**: 25% of sealed games have a strictly positive snapshot
regret, none of the controls do.

**engineering risk**: low for the census; the representation study (`R0..R4`) and
CEGIS refinement are **not started**.

**current verdict**: **`PASS_TO_DISCOVERY`**

**why**: the mechanism-specific effect survives a clean control, and it is
expressible as a sharp minimal witness. **Scope limit that must travel with this
verdict**: it is an *exact synthetic-lab* result under a fixed, known opponent
policy. The plan's own `B_TOY_ONLY` label applies unless an Iron Bottom Sound
natural counterexample is found — **that IBS probe was not run in this
checkpoint.**

---

# Track C — CD-PSRO (Certificate-Directed Sampling)

**hypothesis**: PSRO/EGTA simulation budget is dominated by a few payoff cells;
sampling directed by certificate sensitivity should reach a fixed meta-game
certificate width with far fewer simulator matches than uniform.

**result**: `FAIL` (per the coded pre-declared gate) — **with an explicit
borderline that the PI must adjudicate**, see below.

**what was run**

1. **Certificate machinery, unit-tested first** (`c0_psro/certs.py`, 6/6 tests):
   Hoeffding + union simultaneous CIs per cell; zero-sum game value by LP;
   `v_L = value(L) <= v* <= value(U) = v_U`; verified against analytic game
   values, 300/300-seed coverage Monte Carlo, and the property that widening a
   cell can never shrink the certificate. One documented subtlety: the
   certificate width is **not** monotone along a sampling trajectory (Hoeffding
   intervals are not nested) — an initial test asserting monotonicity was wrong
   and was corrected (recorded in FAILURES F11).
2. **Real IBS calibration** (2,160 fresh matches, both scenarios, 6 strategies
   read from the repo, 30/cell by the pre-declared pilot rule, 0 failures):
   - `IBS-S-03`: 1,080 matches, 13.8 min, **draw rate 0.000** (always a
     winner), cell means spread −0.93..+0.73, true meta-value **+0.067** — a
     close game.
   - `IBS-S-01`: 1,080 matches, 31.9 min, **draw rate 0.419**, every cell mean
     positive (+0.27..+0.73), true meta-value **+0.543** — a structurally
     axis-favoured game.
3. **Sampling-policy comparison** on the calibrated meta-games (each simulated
   match = one draw from the cell's calibrated outcome distribution; the
   certificate sees only counts). Target width 0.20, α = 0.05, batch 25, 5
   seeds, budget 90k matches.

**results** (median matches to certificate width ≤ 0.20):

| policy | S-03 (close game) | saving | S-01 (lopsided game) | saving |
|---|---|---|---|---|
| uniform | 53,025 (5/5) | — | 52,750 (5/5) | — |
| largest_width | 51,500 (5/5) | +2.9% | 52,775 (5/5) | −0.0% |
| variance_aware | 43,150 (5/5) | **+18.6%** | 47,025 (5/5) | +10.9% |
| support_weighted | **never** (0/5) | — | **never** (0/5) | — |
| cert_sensitivity | **15,350 (4/5)** | **+71.1%** | **never** (0/5) | — |

**strongest evidence FOR the idea**: on the close game (S-03) the candidate hit
the certificate target at **15.4k vs 53.0k matches — a 71% reduction**, far
beyond the 40% discovery gate, with 4/5 seeds (the fifth needed 78k — the
behaviour is bimodal, not uniformly good).

**strongest evidence AGAINST (what produces the kill)**

- On S-01 the candidate **never reached the target in any of 5 seeds** (width
  stuck at 0.70–0.80 at 90k) while uniform finished at ~53k. The greedy
  certificate-sensitivity rule is not merely slower there — it fails outright:
  in a game where all rows are near-tied (+0.4..+0.7), resolving any single cell
  barely moves the certificate, and the greedy assignment oscillates instead of
  converging.
- `support_weighted` (the natural "sample the equilibrium support" heuristic)
  **never reached on either scenario** — it starves off-support cells, and the
  certificate is dominated by exactly those cells. A cautionary result for
  anyone assuming support-sampling suffices for *certificates* (it does not —
  exploitability bounds need the BR cells too).
- `largest_width` ≈ uniform (within 3%): with Hoeffding widths depending only
  on n, "widest cell" degenerates to round-robin.

**the borderline the PI must adjudicate**: the pre-declared *textual* gate in
`simulate.py`'s header says "saving 10–40% **or inconsistent across scenarios**
→ C_SMALL_EFFECT"; the *coded* branch treats "candidate never reached" as FAIL
before the inconsistency clause applies. On S-03 the effect (71%) exceeds the
PASS bar; on S-01 the candidate fails to finish. I did **not** re-code the
verdict after seeing results — the recorded verdict is the coded one (`FAIL`),
and this discrepancy is flagged rather than resolved. Under the textual gate
`C_SMALL_EFFECT` would also be defensible.

**engineering risk**: two implementation bugs were found and fixed *before any
result was used* (an unsampled-cell deadlock that pinned the certificate at
width 2.0, and a batch-indexed round-robin that sampled only half the matrix);
both are documented in FAILURES. The remaining engineering is cheap; the risk is
conceptual — the candidate needs a regime discriminator (close game vs blowout)
that currently does not exist.

**current verdict**: **`FAIL`** (coded gate) — scenario-conditional 71% effect
recorded as the strongest counter-evidence to the kill. If the PI wants Track C
alive, the first discovery task is precisely characterising *when* greedy
certificate sensitivity stalls (near-tied rows), because that is also the regime
where PSRO actually needs certificates.

**novelty**: not checked (plan §C6); even a positive experimental result would
still face the C_LITERATURE_MATRIX question before any PASS could be upgraded.

---

# Track D — DiagGame (Identifiable Strategic Test Synthesis)

**hypothesis**: an automatic test-selection system can identify an agent's
specific reasoning defect (mechanism), not just its strength, with far fewer
queries than random testing.

**result**: `D_FAIL`

**what was run**

A five-type defect zoo — all exactly computable, all answering the same query
("which option at this decision node"):

| type | mechanism defect |
|---|---|
| `OPT` | none (Bayesian DP optimum) |
| `MYO` | myopia (one-step greedy, belief-aware) |
| `NOM` | no opponent model (one-step greedy, opponent assumed uniform) |
| `NBU` | no belief update (full DP under the frozen root prior) |
| `AMB` | risk/ambiguity distortion (maximin over consistent doctrines) |

`COMMITMENT-FORGETFUL` was **dropped before the run, with reason**: in this lab
replanning is weakly dominant (see FAILURES F4), so an agent that ignores its own
commitments coincides with `OPT` by construction and is unidentifiable — the
defect needs a lab where breaking a seal costs something, which is a design
change, not a parameter.

Test pool: 684 exact decision nodes over the 74 discovery games. Four selection
methods (random ×5 seeds, hardest, static disagreement, adaptive info-gain);
identification = posterior mass ≥ 0.90 on the true type; cap 60 queries.

**strongest evidence (the kill itself)**

- **`MYO` and `OPT` answered identically on every one of the 684 tests.**
- **`NBU` and `NOM` answered identically on every one of the 684 tests.**
- Consequence: for 4 of 5 types, mechanism identification is **impossible in
  principle** on this generator — no test can ever separate them, so no
  selection method, however clever, can help. Pre-declared gate requires ≥4
  defect types identifiable; measured: **1 of 4** (only `AMB`).
- `AMB` was identifiable (random median 23–27 tests; static disagreement median
  11 — a real 2.3× selection effect, but on one type only).
- **Adaptive info-gain identified nobody (0/5 types)** and is a useful negative:
  greedy entropy minimisation prefers tests that resolve the *resolvable*
  `OPT`-vs-`NOM` ambiguity, lands on an inseparable pair
  (`{OPT,MYO}` or `{NBU,NOM}`), and dead-ends at two consistent types for the
  full 60-query budget. On a pool with inseparable pairs, greedy Bayesian
  selection is *worse* than random.

**why the inseparability happens (mechanism, not bug)**

In this lab's game families, per-turn payoffs make one-step greedy optimal or
tie everywhere: the coordination/anticor families are stationary (tomorrow looks
like today, so lookahead adds nothing); the delayed/pathdep families pay only on
the final turn, so early-turn greed sees all zeros and ties. The defects as
defined therefore **do not change observable behaviour** on these games.

**POST_HOC rescue probe (labelled, does not count toward the gate).** One new
payoff family ("setup": final-turn payoff on the opponent's *accumulated* action,
so only lookahead can steer an early commitment toward the target) was added
after seeing the failure and re-measured: the family turned out **fully
degenerate — all five types answered identically on all 60 probe tests**, so the
rescue failed outright (`results/D0_posthoc_probe.json`). The inseparability was
not broken by the most obvious structural fix available cheaply.

**estimated effect**: identification of mechanism defects: 1/4 types; the one
strong-selection datapoint (2.3× on `AMB`) does not satisfy the mechanism gate.

**engineering risk**: a working DiagGame needs a game generator in which myopia,
missing opponent models and missing belief updates each *change behaviour* —
i.e. non-stationary, replanning-costly games. That is a redesign of the
generator, not a parameter sweep; it is discovery-scale work, contradicting the
"cheap kill" premise.

**current verdict**: **`D_FAIL`** — the premise (defects are identifiable from
behaviour) fails on this lab. Rescue requires a redesigned generator whose
payoffs punish short horizons; whether such a generator would keep the defects
*humanly interpretable* is unknown.

---

# What the cheap kill tests actually settled

1. **The premise of A and B exists in the repository.** Sealed, unexecuted,
   hidden orders are real production structure (`AUDIT.md` §1), not aspiration.
2. **A is weak, for a specific and actionable reason**: in 38% of games there is
   no compute/value trade-off at all, and a fixed calendar already meets the
   retention bar on 24% of evaluable points. The story needs a regime where the
   calendar demonstrably fails.
3. **B has a mechanism-specific signal** — but only under a metric that measures
   *acting* regret, and only under a lossy-but-informative signal. A naive
   value-spread metric would have produced a false negative.
4. **C is scenario-conditional in a way that matters**: certificate-directed
   sampling cuts 71% of matches on the close game and fails outright on the
   lopsided one; support-weighted sampling never produces a certificate at all.
5. **D's premise fails structurally**: on this lab's games, myopia and missing
   opponent/belief modelling do not change behaviour, so mechanism-level
   identification is impossible in principle for 4 of 5 defect types.

# What was deliberately not done

- No discovery sweep, no confirmatory run, no freeze document.
- No Iron Bottom Sound transfer experiment (Track A5 / B4 in the plan) — the
  2,160 C0 calibration matches are outcome calibration, not a Track A/B
  transfer experiment.
- IBS match budget consumed: 78 (P0) + 2,160 (C0 calibration) = **2,238 of
  20,000**.
- No certificate search (A2/A4). Note the plan's own warning: **"certificate 弱
  或无效应报 A_PASS_NO_CERT，不允许继续使用 Certified 作为标题核心"** — nothing
  here supports the word "Certified", and after `A_WEAK` it is premature even to
  discuss it.
- No literature comparison for the surviving track. **`B_PASS_TO_DISCOVERY` must
  not be read as a novelty claim**: NOVELTY IS NOT ESTABLISHED. The plan's
  closest-work check (Learning When to Plan, LAMIR, NashDreamer, IIG embedding
  work, PSRO/EGTA progressive sampling, GENSTRAT, Level-k distinguishability) has
  **not** been run.
