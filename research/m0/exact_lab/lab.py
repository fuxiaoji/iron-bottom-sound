"""Reachable-history enumeration and the four required lab cases.

A *history* here is a concrete true state of the world at a focal decision
point: the turn, the focal's commitment, the observation sequence so far, the
focal's posterior, and the true hypothesis ``(theta, ao_hist)``.  Two histories
that share a ``snapshot`` are indistinguishable to a stateless representation
but may differ in truth — that difference is what Tracks A and B measure.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .core import (Belief, ExactLab, GameSpec, Hypothesis, _normalise,
                   initial_belief, opponent_action, payoff, public_signal)


@dataclass
class History:
    t: int
    af: int
    rf: int
    obs_hist: tuple          # public signal sequence observed so far
    belief: Belief
    truth: Hypothesis
    cum_ao: int
    # filled by the census
    snapshot: tuple = field(default=())

    def __post_init__(self) -> None:
        self.snapshot = self.make_snapshot()

    def make_snapshot(self) -> tuple:
        """The stateless public representation: current turn, current public
        signal, the focal's own commitment.  This is what an R0-style
        snapshot model is allowed to see."""
        q = self.obs_hist[-1] if self.obs_hist else 0
        return (self.t, q, self.af, self.rf)

    @property
    def hist_id(self) -> str:
        theta, ao = self.truth
        return f"h:t{self.t}:obs{','.join(map(str, self.obs_hist))}:af{self.af}:rf{self.rf}:th{theta}:ao{','.join(map(str, ao))}"

    @property
    def public_state(self) -> str:
        return f"z:t{self.t}:q{self.obs_hist[-1] if self.obs_hist else 0}"

    @property
    def hidden_commitment(self) -> str:
        theta, ao = self.truth
        return f"th{theta}:aohist{','.join(map(str, ao))}"

    @property
    def commitment_len(self) -> int:
        return self.rf


def enumerate_reachable(spec: GameSpec, lab: ExactLab, max_histories: int = 200_000) -> list[History]:
    """Enumerate the histories reachable when the focal plays optimally.

    The tree branches only on the public signal, so this is the set of situations
    an optimal player actually meets — which is the set over which "is replanning
    worth it" has an operational meaning.
    """
    out: list[History] = []
    stack: list[tuple[int, int, int, tuple, Belief]] = [(0, 0, 0, (), initial_belief(spec))]
    while stack:
        t, af, rf, obs, belief = stack.pop()
        for (theta, ao_hist), _w in belief:
            out.append(History(t=t, af=af, rf=rf, obs_hist=obs, belief=belief,
                               truth=(theta, ao_hist), cum_ao=sum(ao_hist)))
            if len(out) > max_histories:
                raise RuntimeError("history enumeration exceeded budget")
        if t >= spec.T:
            continue
        # descend along the optimal action, branching on the realised public signal
        kind, a = lab.best_action(t, af, rf, belief)
        af_exec, rf_next = (af, rf - 1) if kind == "continue" else (a, spec.L - 1)
        branches: dict[int, list] = {}
        for (theta, ao_hist), w in belief:
            ao = opponent_action(theta, sum(ao_hist), spec.b)
            ao2 = ao_hist + (ao,)
            branches.setdefault((spec.alpha * theta + sum(ao2)) % spec.m, []).append(((theta, ao2), w))
        for q, pairs in sorted(branches.items()):
            stack.append((t + 1, af_exec, rf_next, obs + (q,), _normalise(pairs)))
    return out


# --------------------------------------------------------------------------
# The four cases the plan requires
# --------------------------------------------------------------------------


def case1_markov_control() -> GameSpec:
    """Markov control: no hidden doctrine, and the payoff ignores the opponent,
    so the snapshot is genuinely sufficient."""
    return GameSpec(name="case1_markov_control", T=4, b=2, K=1, m=2, L=2,
                    family="null", seed=1, alpha=1)


def case3_negative_control() -> GameSpec:
    """Negative control: a hidden doctrine exists and is unobservable, but it
    provably cannot affect the continuation, because the payoff ignores the
    opponent."""
    return GameSpec(name="case3_negative_control", T=4, b=2, K=3, m=2, L=2,
                    family="null", seed=3, alpha=1)


def case4_path_dependent() -> GameSpec:
    """Path-dependent payoff: identical snapshot, different past path, and the
    past path changes the terminal payoff."""
    # K=3 (not K=2) is required: with K=2 and m=2 the public signal identifies the
    # doctrine outright, so no ambiguity survives and no aliasing can appear.
    return GameSpec(name="case4_path_dependent", T=4, b=3, K=3, m=2, L=2,
                    family="pathdep", seed=4, alpha=1)


def case2_candidates():
    """Yield small specs to search for a sealed-commitment witness.

    ``b=3, m=2`` is required for the public signal to be genuinely lossy: with
    ``b=2, m=2`` one has ``ao_t = (theta + q_t) % 2`` and ``q_0 = theta``, so the
    signal reveals the doctrine outright and no aliasing can exist.
    """
    for T in (3, 4, 5):
        for b in (3,):
            for K in (2, 3):
                for m in (2,):
                    for L in (2, 3):
                        if L > T:
                            continue
                        for fam in ("coordination", "anticor", "delayed", "pathdep"):
                            yield GameSpec(name=f"witness_T{T}_b{b}_K{K}_L{L}_{fam}",
                                           T=T, b=b, K=K, m=m, L=L, family=fam, seed=7, alpha=1)


# --------------------------------------------------------------------------
# Full information-set tree enumeration
# --------------------------------------------------------------------------


def _options(spec: GameSpec, rf: int) -> list[tuple[str, int]]:
    opts: list[tuple[str, int]] = []
    if rf > 0:
        opts.append(("continue", -1))
    for a in spec.actions:
        opts.append(("replan", a))
    return opts


def enumerate_all_nodes(spec: GameSpec, max_nodes: int = 200_000) -> list[tuple]:
    """Enumerate the full information-set tree: every reachable focal decision
    node ``(t, af, rf, obs_hist)`` together with the belief there, under **all**
    focal options — not just the optimal one.

    The optimal-play-only enumeration in ``enumerate_reachable`` is far too
    narrow for an aliasing census: it yields roughly one node per observation and
    therefore hides exactly the cross-history comparisons the census needs.
    """
    start = (0, 0, 0, ())
    beliefs: dict[tuple, Belief] = {start: initial_belief(spec)}
    frontier = [start]
    while frontier:
        nxt = []
        for node in frontier:
            t, af, rf, obs = node
            if t >= spec.T:
                continue
            belief = beliefs[node]
            for kind, a in _options(spec, rf):
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
                        if len(beliefs) > max_nodes:
                            raise RuntimeError("node enumeration exceeded budget")
        frontier = nxt
    return sorted(beliefs.items())  # [(node, belief), ...]


def snapshot_of(t: int, af: int, rf: int, obs: tuple) -> tuple:
    """The stateless public representation an R0-style snapshot model may use."""
    return (t, obs[-1] if obs else 0, af, rf)


def history_rows(spec: GameSpec, lab: ExactLab) -> list[dict]:
    """One flat row per reachable *history* (node x hypothesis in its support).

    This is the table Tracks A and B both work from.  ``V`` is the optimal
    value given the history's true information set (the belief), so a gap in
    ``V`` between two histories sharing a ``snapshot`` is exactly the value
    that any snapshot-based representation cannot recover.
    """
    rows: list[dict] = []
    for (t, af, rf, obs), belief in enumerate_all_nodes(spec):
        v = lab.V(t, af, rf, belief)
        v_replan = lab.V_replan(t, af, rf, belief)
        v_cont = lab.W(t, af, rf, belief, "continue", -1) if rf > 0 else None
        best = lab.best_action(t, af, rf, belief)
        for (theta, ao_hist), w in belief:
            rows.append({
                "game_id": spec.name,
                "t": t,
                "af": af,
                "rf": rf,
                "obs_hist": obs,
                "public_state": f"z:t{t}:q{obs[-1] if obs else 0}",
                "snapshot": snapshot_of(t, af, rf, obs),
                "theta": theta,
                "ao_hist": ao_hist,
                "hidden_commitment": f"th{theta}:ao{','.join(map(str, ao_hist))}",
                "belief_weight": w,
                "belief_n": len(belief),
                "horizon_left": spec.T - t,
                "commitment_left": rf,
                "V": v,
                "V_replan": v_replan,
                "V_continue": v_cont,
                "delta": (v_replan - v_cont) if v_cont is not None else None,
                "best_kind": best[0],
                "best_action": best[1],
                "family": spec.family,
                "T": spec.T,
                "b": spec.b,
                "K": spec.K,
                "m": spec.m,
                "L": spec.L,
            })
    return rows
