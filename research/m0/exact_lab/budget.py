"""Budgeted replanning: how much value survives when only K replans are allowed?

This is the operational core of Track A.  ``Vb`` adds a replan-budget dimension
to the belief-space DP, so that the *Oracle top-K* (spend K replans where they
are worth most) can be compared against fixed schedules computed exactly:

* **Always**  — unlimited budget;
* **Never**   — budget 0;
* **Periodic**— may replan only at ``t % P == 0``;
* **Random-K**— replans at a uniformly random K-subset of turns, averaged over
  *all* subsets exactly (no sampling).

All four are exact; none is estimated.
"""

from __future__ import annotations

from itertools import combinations

from .core import Belief, GameSpec, _normalise, opponent_action, payoff


def _branch(spec: GameSpec, belief: Belief, af_exec: int, t: int):
    """Split the belief by the public signal that will be observed."""
    immediate = 0.0
    branches: dict[int, list] = {}
    for (theta, ao_hist), w in belief:
        ao = opponent_action(theta, sum(ao_hist), spec.b)
        ao2 = ao_hist + (ao,)
        cum_next = sum(ao2)
        immediate += w * payoff(spec, af_exec, ao, t, cum_next)
        branches.setdefault((spec.alpha * theta + cum_next) % spec.m, []).append(((theta, ao2), w))
    return immediate, branches


class BudgetedLab:
    """Exact value with a finite replanning budget, plus exact fixed schedules."""

    def __init__(self, spec: GameSpec) -> None:
        self.spec = spec
        self._cache: dict = {}

    # -- oracle: optimal placement of K replans ---------------------------
    def Vb(self, t: int, af: int, rf: int, belief: Belief, k: int) -> float:
        s = self.spec
        if t >= s.T:
            return 0.0
        key = (t, af, rf, belief, k)
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        best = self._forced(t, af, rf, belief,
                            kind="continue", a=-1, k=k)
        if k > 0:
            for a in s.actions:
                best = max(best, self._forced(t, af, rf, belief,
                                              kind="replan", a=a, k=k - 1))
        self._cache[key] = best
        return best

    def _forced(self, t: int, af: int, rf: int, belief: Belief,
                kind: str, a: int, k: int) -> float:
        s = self.spec
        af_exec, rf_next = (af, max(rf - 1, 0)) if kind == "continue" else (a, s.L - 1)
        immediate, branches = _branch(s, belief, af_exec, t)
        total = immediate
        if t + 1 < s.T:
            for _q, pairs in branches.items():
                p = sum(w for _, w in pairs)
                total += p * self.Vb(t + 1, af_exec, rf_next, _normalise(pairs), k)
        return total

    # -- fixed schedules, evaluated exactly under belief branching --------
    def V_schedule(self, t: int, af: int, rf: int, belief: Belief,
                   replan_at: frozenset) -> float:
        """Value of the schedule "replan only at turns in ``replan_at``".

        Continuation is always available, so the schedule is well defined even at
        turns outside the set.
        """
        s = self.spec
        if t >= s.T:
            return 0.0
        key = (t, af, rf, belief, replan_at)
        hit = self._cache.get(("sched",) + key)
        if hit is not None:
            return hit
        if t in replan_at:
            best = max(self._sched_step(t, af, rf, belief, "replan", a, replan_at)
                       for a in s.actions)
        else:
            best = self._sched_step(t, af, rf, belief, "continue", -1, replan_at)
        self._cache[("sched",) + key] = best
        return best

    def _sched_step(self, t: int, af: int, rf: int, belief: Belief,
                    kind: str, a: int, replan_at: frozenset) -> float:
        s = self.spec
        af_exec, rf_next = (af, max(rf - 1, 0)) if kind == "continue" else (a, s.L - 1)
        immediate, branches = _branch(s, belief, af_exec, t)
        total = immediate
        if t + 1 < s.T:
            for _q, pairs in branches.items():
                p = sum(w for _, w in pairs)
                total += p * self.V_schedule(t + 1, af_exec, rf_next,
                                             _normalise(pairs), replan_at)
        return total

    def periodic(self, P: int, belief: Belief) -> float:
        turns = frozenset(t for t in range(self.spec.T) if t % P == 0)
        return self.V_schedule(0, 0, 0, belief, turns)

    def random_k_mean(self, k: int, belief: Belief) -> tuple[float, float, int]:
        """Mean and std of the Random-K baseline, averaged over *all* K-subsets."""
        if k <= 0:
            v = self.V_schedule(0, 0, 0, belief, frozenset())
            return v, 0.0, 1
        if k >= self.spec.T:
            turns = frozenset(range(self.spec.T))
            return self.V_schedule(0, 0, 0, belief, turns), 0.0, 1
        vals = [self.V_schedule(0, 0, 0, belief, frozenset(c))
                for c in combinations(range(self.spec.T), k)]
        mean = sum(vals) / len(vals)
        var = sum((v - mean) ** 2 for v in vals) / len(vals)
        return mean, var ** 0.5, len(vals)

    def oracle_k(self, k: int, belief: Belief) -> float:
        return self.Vb(0, 0, 0, belief, k)
