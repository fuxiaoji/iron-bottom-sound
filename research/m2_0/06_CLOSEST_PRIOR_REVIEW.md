# 06 — Closest-prior review

**Scope**: per the plan (§16), the full closest-prior matrix is only mandatory
after experimental signal passes. Track A failed its oracle gate and Track B
landed at B_ORACLE_ONLY, so the required reading (GRDC/APS/CD3T/DECOR/VO-MASD/
NeurIPS-2025 robustness study) was NOT performed at paper-review depth. The
matrix below records the structural overlap questions the plan pre-set, with
their status; it exists so a future revival starts from the right questions
rather than from scratch.

| plan question | status | note |
|---|---|---|
| Has any paper directly done state-dependent partition + one macro action per group + fewer decision entities + performance/complexity tradeoff? | NOT ESTABLISHED (review skipped — Track A oracle failed first) | the plan's fatal-collision test; must be answered before any revival |
| Is Track B just generic agent-dropout robustness? | PARTIALLY ANSWERED by measurement | B0/B1 show the failure model is structurally richer (endogenous, adversarial, command-state-changing, next-turn control constraints) — the differentiator EXISTS in the platform; what failed is the robust-design effect, not the failure model |
| "别人没做海战" counts as novelty? | NO (plan §16) | recorded |

Keyword searches (multi-agent action abstraction / agent abstraction RL /
dynamic team partition MARL / group macro action / decision entity abstraction /
dynamic coalition control / state-dependent grouping macro-action / hierarchical
control granularity / leader failure MARL / organizational resilience MARL) were
NOT run to the plan's depth for the same gate-order reason. No novelty verdict is
offered for any track; the scorecard marks novelty as not-reviewed-everywhere.
