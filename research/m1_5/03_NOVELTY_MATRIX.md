# 03_NOVELTY_MATRIX.md — scope-limited novelty assessment

**Scope declaration**: the plan gates the full novelty review on experimental
pass ("只有实验信号通过才做完整 novelty review"). Neither track survived, so what
follows is the structural assessment needed for the executive summary, NOT a
complete closest-prior literature review. Entries marked `not deep-reviewed`.

## E1 — Selective Opponent Reasoning

| prior family | relation to rho-gating | status |
|---|---|---|
| Learning When to Plan (arXiv:2509.03581) | test-time compute allocation for LLM agents; same *shape* (when to invoke expensive reasoning), different object (tool-use planning vs opponent hidden state) | not deep-reviewed |
| Value of Information / metareasoning (Russell-Wefald lineage) | rho(s) is a worst-case regret VOI variant; "is rho just VOI rewritten?" — the defensive answer is that rho is computed over an opponent's *hidden commitments* (a game-theoretic information set), not over observations to buy | structural overlap acknowledged |
| Selective search / adaptive test-time compute | same gating pattern | not deep-reviewed |
| Safe opponent exploitation / opponent modeling gates | closest if prior work gates opponent modeling by action-sensitivity | the plan's own kill condition; not established either way |

Honest assessment: even if E1 had survived T2, its novelty case would have
hinged on (a) the hidden-commitment formal object and (b) a "shared safe
action exists" certificate. The measured T2 failure makes the question moot:
a gate that cannot be learned does not need a novelty defense. `E1_NOVELTY =
AMBIGUOUS` is recorded rather than PASS/FAIL because the review was not run
to the plan's depth on a dead track.

## E2 — Strategic Influence Planning

| prior family | relation | status |
|---|---|---|
| Opponent shaping (learning-time, e.g. LOLA-style) | different: shaping alters the opponent's *learning*, not its current physical feasible set | not deep-reviewed |
| Opponent-aware MCTS / Stackelberg planning | embeds opponent best-response into search; E2's IV(a) is a single-decision physical-influence term | structural overlap acknowledged |
| Area denial / deception / feint | domain cousins; E2's claim would have been a planner-level counterfactual influence objective | not deep-reviewed |

Honest assessment: E2 died before novelty mattered — there is no causal
long-horizon effect in the measured window to attribute to influence. Any
future revival would first need an effect, then must clear the
learning-time-shaping vs physical-BR-set distinction the plan demands.
`E2_NOVELTY = AMBIGUOUS` recorded for the same reason as above.
