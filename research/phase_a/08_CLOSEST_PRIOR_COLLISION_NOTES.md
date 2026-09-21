# 08_CLOSEST_PRIOR_COLLISION_NOTES.md

The plan names the closest priors and forbids expanding Phase A into a literature
survey; this note only records, per track, what would have to be shown and against
which baseline, and it makes **no novelty claim**.

- **Adaptive compute / planning** — *Optimizing Test-Time Compute via Meta
  Reinforcement Finetuning* (ICML 2025); *MALinZero* (NeurIPS 2025). Implication
  held: test-time compute allocation and efficient multi-agent planning are both
  active. A Track A contract therefore has to compare allocations at equal *total*
  budget and beat a strong fixed allocation, not demonstrate that planning helps.
- **Robustness / failure boundary** — *Empirical Study on Robustness and
  Resilience in Cooperative MARL* (NeurIPS 2025); *DEPLOY-RL* (IJCAI 2026).
  Implication held: active boundary discovery exists in RL, so Track B only stays
  interesting if *multi-agent combinatorial structure* beats a **generic** active
  baseline — which is exactly the frozen `B_MULTIAGENT_STRUCTURE` gate, and why the
  plan's weaker outcome is named `B_GENERIC_ACTIVE_LEARNING_ONLY`.
- **Failure attribution** — *Which Agent Causes Task Failures and When?* (ICML
  2025); *Counterfactual Effect Decomposition in Multi-Agent Sequential Decision
  Making* (ICML 2025); *Counterfactual Reasoning for Responsibility Attribution in
  Probabilistic Multi-Agent Systems* (IJCAI 2026). Implication held: attribution is
  crowded, so Track C carries the strictest gate (query efficiency at ≤25 % of the
  exhaustive budget plus ≥15 pp over random and binary search) and is the track most
  likely to end as `C_TOO_EXPENSIVE` or `C_TRIVIAL`.
- **Adjacent artefacts consulted for definitions only** — AMB/Trustworthy-MARL
  uncertainty taxonomy; Who&When task/metric definitions. No reported aggregate was
  copied as data, and no paid LLM API was used.

No "first" claim is made anywhere in Phase A.
