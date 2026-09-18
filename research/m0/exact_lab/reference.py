"""Independent reference solver: exhaustive policy enumeration, no dynamic programming.

The main solver in ``core.py`` is a belief-space DP with memoisation.  Any bug in
its recursion, its belief update, or its option set would silently produce wrong
"exact" numbers, so this lab is only usable if a second, structurally different
implementation agrees with it.

This module enumerates **every deterministic policy** over the reachable
(t, af, rf, observation-history) nodes and evaluates each one by direct forward
recursion over hypotheses.  It shares the dynamics primitives but neither the
recursion shape nor the memoisation of ``core.py``.  It is exponential, so it is
only usable on the smallest specs — which is exactly what a correctness check
needs.
"""

from __future__ import annotations

from itertools import product

from .core import GameSpec, _normalise, initial_belief, opponent_action, payoff


def _reachable_nodes(spec: GameSpec) -> dict[tuple, object]:
    """BFS over nodes (t, af, rf, obs_hist) annotated with the belief there.

    The belief is carried through the BFS, so only genuinely reachable
    observation histories are produced (no free-floating accumulators).
    """
    start = (0, 0, 0, ())
    beliefs = {start: initial_belief(spec)}
    frontier = [start]
    while frontier:
        nxt = []
        for node in frontier:
            t, af, rf, obs = node
            if t >= spec.T:
                continue
            belief = beliefs[node]
            opts = [("continue", -1)] if rf > 0 else []
            opts += [("replan", a) for a in spec.actions]
            for kind, a in opts:
                af_exec, rf_next = (af, rf - 1) if kind == "continue" else (a, spec.L - 1)
                branches: dict[int, list] = {}
                for (theta, ao_hist), w in belief:
                    ao = opponent_action(theta, sum(ao_hist), spec.b)
                    ao2 = ao_hist + (ao,)
                    branches.setdefault((spec.alpha * theta + sum(ao2)) % spec.m, []).append(((theta, ao2), w))
                for q, pairs in branches.items():
                    child = (t + 1, af_exec, rf_next, obs + (q,))
                    if child not in beliefs:
                        beliefs[child] = _normalise(pairs)
                        nxt.append(child)
        frontier = nxt
    return beliefs


def _options(spec: GameSpec, rf: int) -> list[tuple[str, int]]:
    opts = [("continue", -1)] if rf > 0 else []
    opts += [("replan", a) for a in spec.actions]
    return opts


def _evaluate_policy(spec: GameSpec, policy: dict, node: tuple,
                     beliefs: dict) -> float:
    """Forward evaluation of a fixed policy: no memoisation, direct recursion."""
    t, af, rf, obs = node
    if t >= spec.T:
        return 0.0
    kind, a = policy[node]
    af_exec, rf_next = (af, rf - 1) if kind == "continue" else (a, spec.L - 1)
    belief = beliefs[node]
    immediate = 0.0
    total = 0.0
    branches: dict[int, list] = {}
    for (theta, ao_hist), w in belief:
        ao = opponent_action(theta, sum(ao_hist), spec.b)
        ao2 = ao_hist + (ao,)
        immediate += w * payoff(spec, af_exec, ao, t, sum(ao2))
        branches.setdefault((spec.alpha * theta + sum(ao2)) % spec.m, []).append(((theta, ao2), w))
    total += immediate
    if t + 1 < spec.T:
        for q, pairs in branches.items():
            p = sum(w for _, w in pairs)
            total += p * _evaluate_policy(spec, policy, (t + 1, af_exec, rf_next, obs + (q,)),
                                          beliefs)
    return total


def reference_optimum(spec: GameSpec, budget: int = 3_000_000) -> float:
    """Exact optimum by brute-force enumeration over all deterministic policies."""
    beliefs = _reachable_nodes(spec)
    nodes = sorted(beliefs)
    option_lists = [_options(spec, n[2]) for n in nodes]
    total = 1
    for opts in option_lists:
        total *= len(opts)
    if total > budget:
        raise ValueError(f"reference_optimum too large: {total} policies")
    best = None
    for combo in product(*option_lists):
        policy = dict(zip(nodes, combo))
        v = _evaluate_policy(spec, policy, (0, 0, 0, ()), beliefs)
        if best is None or v > best:
            best = v
    return best
