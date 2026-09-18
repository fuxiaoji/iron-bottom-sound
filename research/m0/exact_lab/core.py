"""Exact Strategic Lab — a tiny, fully enumerable sealed-commitment game family.

Purpose
-------
Tracks A (CARP), B (CAIS) and D (DiagGame) must not be validated directly on
Iron Bottom Sound.  They are validated here first, on games small enough that
*every* quantity is exact: no sampling, no learning, no estimates.

Modelled structure (mirrors the Iron Bottom Sound turn machine)
--------------------------------------------------------------
IBS seals both sides' movement orders at ``MOVEMENT_PLANNING`` and then hands
the turn to ``TORPEDO_PLANNING``, where both sides decide again while the
already-sealed movement orders remain *committed but unexecuted and invisible*.
This lab keeps exactly that structure:

* turns ``t = 0..T-1``;
* the focal player holds an explicit **commitment**: an action bound for ``L``
  consecutive turns, which it may break at a cost of "replanning";
* the opponent holds a **hidden commitment** whose executed action is
  ``ao_t = (theta + cum_ao) % b`` — driven by a hidden doctrine ``theta`` and by
  the opponent's own (hidden) accumulation ``cum_ao``;
* executed actions become publicly visible only through a **lossy public
  signal** ``q = cum_ao mod m``: the analogue of "you can see where the ships
  are, not where they were ordered to go";
* terminal payoff may be immediate, delayed, historical, or opponent-blind.

Two levels of information exist, and the gap between them is the object of
study:

``snapshot``  what a stateless representation sees: ``(t, q, af, rf)``.
``belief``    the true information set: the full observed ``q`` sequence, which
              pins down a posterior over hypotheses ``(theta, ao_history)``.

Scope limit — read before citing any number produced by this lab
---------------------------------------------------------------
The opponent is a **fixed, known, deterministic policy of its hidden state**,
not an equilibrium player.  ``V`` and ``Q`` are therefore exact *best responses
against a known opponent policy*, obtained by belief-space dynamic programming.
They are **not** Nash values, and no claim about equilibrium play follows.
"""

from __future__ import annotations

from dataclasses import dataclass

FAMILIES = ("coordination", "anticor", "delayed", "pathdep", "null")


@dataclass(frozen=True)
class GameSpec:
    """A tiny finite-horizon sealed-commitment game."""

    name: str
    T: int = 4          # turns
    b: int = 2          # actions per turn per player
    K: int = 2          # hidden opponent doctrines, theta in 0..K-1
    m: int = 2          # public-signal modulus (how lossy the board is)
    L: int = 2          # commitment block length
    family: str = "coordination"
    seed: int = 0
    alpha: int = 0      # how much of the hidden doctrine leaks into the signal

    def __post_init__(self) -> None:
        assert 2 <= self.T <= 6, "T must be in 2..6"
        assert 2 <= self.b <= 3, "b must be in 2..3"
        assert self.K >= 1
        assert 1 <= self.m <= max(2, self.b)
        assert 1 <= self.L <= self.T
        assert self.family in FAMILIES

    @property
    def actions(self) -> tuple[int, ...]:
        return tuple(range(self.b))

    @property
    def snapshot_lossy(self) -> bool:
        """True when the public signal cannot pin down the opponent's next action.

        With ``alpha = 0`` the signal is ``sum(ao) mod m``, which is independent
        of the uniform doctrine; the posterior over the next action is then
        uniform no matter what is observed, and *no* aliasing is possible.  A
        lossy-but-informative signal needs ``alpha != 0``.
        """
        return self.family != "null" and self.K > 1 and self.alpha != 0


# --------------------------------------------------------------------------
# Dynamics
# --------------------------------------------------------------------------


def opponent_action(theta: int, cum_ao: int, b: int) -> int:
    """Opponent's executed action: a function of hidden doctrine and hidden history."""
    return (theta + cum_ao) % b


def payoff(spec: GameSpec, af: int, ao: int, t: int, cum_ao_next: int) -> float:
    """Per-turn payoff contribution."""
    T, b, fam = spec.T, spec.b, spec.family
    if fam == "coordination":
        return 1.0 if af == ao else -1.0
    if fam == "anticor":
        return 1.0 if af != ao else -1.0
    if fam == "delayed":
        return 0.0 if t < T - 1 else (1.0 if af == ao else -1.0)
    if fam == "pathdep":
        # pays only at the end, and pays on the opponent's *accumulated* action
        # over the whole game — a quantity the lossy signal q does not reveal.
        if t < T - 1:
            return 0.0
        return 1.0 if af == (cum_ao_next % b) else -1.0
    if fam == "null":
        # opponent-irrelevant: the hidden commitment exists but cannot matter.
        return 1.0 if af == (t % b) else -1.0
    raise ValueError(fam)


# --------------------------------------------------------------------------
# Belief state
# --------------------------------------------------------------------------
# Hypothesis = (theta, ao_history).  cum_ao and the projected next action are
# both derivable from it, so this is a sufficient hypothesis space.
# The belief is a deterministic function of the observed q sequence, so using it
# as the DP state automatically merges observationally equivalent histories.

Hypothesis = tuple  # (theta:int, ao_hist:tuple[int,...])
Belief = tuple      # tuple[tuple[Hypothesis, float], ...]


def _normalise(pairs) -> Belief:
    merged: dict[Hypothesis, float] = {}
    for key, w in pairs:
        merged[key] = merged.get(key, 0.0) + w
    total = sum(merged.values())
    if total <= 0:
        return ()
    return tuple(sorted((k, v / total) for k, v in merged.items() if v > 0))


def initial_belief(spec: GameSpec) -> Belief:
    return _normalise([((theta, ()), 1.0 / spec.K) for theta in range(spec.K)])


def public_signal(theta: int, ao_hist: tuple[int, ...], m: int, alpha: int) -> int:
    """The lossy public signal the focal observes about the opponent's commitment.

    ``alpha`` controls how much of the hidden doctrine leaks through.  With
    ``alpha = 0`` the signal is uninformative about the next action (the
    posterior stays uniform); with ``alpha != 0`` it partially reveals it, which
    is what makes the representation question non-trivial.
    """
    return (alpha * theta + sum(ao_hist)) % m


# --------------------------------------------------------------------------
# Solvers
# --------------------------------------------------------------------------


class ExactLab:
    """Exact best-response solver for one GameSpec.

    ``V``  optimal belief-averaged continuation value (what an optimal player
           with this information set can guarantee in expectation).
    ``Q``  realised value at a concrete true history: take action ``a`` now at
           the *true* hypothesis, then play the optimal policy.  This is the
           quantity the aliasing census needs, because two histories sharing a
           snapshot but differing in truth have different realised values.
    """

    def __init__(self, spec: GameSpec) -> None:
        self.spec = spec
        self._v: dict = {}
        self._w: dict = {}
        self.nodes = 0

    # -- focal option set -------------------------------------------------
    def options(self, rf: int) -> list[tuple[str, int]]:
        opts: list[tuple[str, int]] = []
        if rf > 0:
            opts.append(("continue", -1))
            for a in self.spec.actions:
                opts.append(("replan", a))
        else:
            for a in self.spec.actions:
                opts.append(("replan", a))
        return opts

    def _exec(self, af: int, rf: int, kind: str, a: int) -> tuple[int, int]:
        if kind == "continue":
            return af, rf - 1
        return a, self.spec.L - 1

    # -- belief-averaged DP ----------------------------------------------
    def V(self, t: int, af: int, rf: int, belief: Belief) -> float:
        if t >= self.spec.T:
            return 0.0
        key = (t, af, rf, belief)
        hit = self._v.get(key)
        if hit is not None:
            return hit
        self.nodes += 1
        best = max(self.W(t, af, rf, belief, kind, a) for kind, a in self.options(rf))
        self._v[key] = best
        return best

    def W(self, t: int, af: int, rf: int, belief: Belief, kind: str, a: int) -> float:
        key = (t, af, rf, belief, kind, a)
        hit = self._w.get(key)
        if hit is not None:
            return hit
        s = self.spec
        af_exec, rf_next = self._exec(af, rf, kind, a)
        immediate = 0.0
        branches: dict[int, list] = {}
        for (theta, ao_hist), w in belief:
            ao = opponent_action(theta, sum(ao_hist), s.b)
            ao2 = ao_hist + (ao,)
            cum_next = sum(ao2)
            immediate += w * payoff(s, af_exec, ao, t, cum_next)
            q_next = (s.alpha * theta + cum_next) % s.m
            branches.setdefault(q_next, []).append(((theta, ao2), w))
        total = immediate
        if t + 1 < s.T:
            for _q, pairs in branches.items():
                p = sum(w for _, w in pairs)
                total += p * self.V(t + 1, af_exec, rf_next, _normalise(pairs))
        self._w[key] = total
        return total

    def V_continue(self, t: int, af: int, rf: int, belief: Belief) -> float | None:
        if rf <= 0:
            return None
        return self.W(t, af, rf, belief, "continue", -1)

    def V_replan(self, t: int, af: int, rf: int, belief: Belief) -> float:
        return max(self.W(t, af, rf, belief, "replan", a) for a in self.spec.actions)

    def best_action(self, t: int, af: int, rf: int, belief: Belief) -> tuple[str, int]:
        return max(self.options(rf),
                   key=lambda ka: self.W(t, af, rf, belief, ka[0], ka[1]))

    # -- realised Q at a concrete true history ----------------------------
    def Q_realised(self, t: int, af: int, rf: int, belief: Belief,
                   truth: Hypothesis, kind: str, a: int) -> float:
        """Value of taking (kind, a) now at the true hypothesis, then playing
        the optimal policy."""
        s = self.spec
        af_exec, rf_next = self._exec(af, rf, kind, a)
        theta, ao_hist = truth
        ao = opponent_action(theta, sum(ao_hist), s.b)
        ao2 = ao_hist + (ao,)
        cum_next = sum(ao2)
        val = payoff(s, af_exec, ao, t, cum_next)
        if t + 1 < s.T:
            q_next = (s.alpha * theta + cum_next) % s.m
            # the focal observes q_next, so the posterior is restricted to that branch
            pairs = [((th, ah + ((th + sum(ah)) % s.b,)), w)
                     for (th, ah), w in belief
                     if (s.alpha * th + sum(ah) + ((th + sum(ah)) % s.b)) % s.m == q_next]
            val += self.V(t + 1, af_exec, rf_next, _normalise(pairs))
        return val

    def Q_optimal_realised(self, t: int, af: int, rf: int, belief: Belief,
                           truth: Hypothesis) -> float:
        kind, a = self.best_action(t, af, rf, belief)
        return self.Q_realised(t, af, rf, belief, truth, kind, a)


# --------------------------------------------------------------------------
# Brute force — an independent second implementation, for cross-validation
# --------------------------------------------------------------------------


def brute_force_fixed_policy_value(spec: GameSpec, focal_actions: tuple[int, ...],
                                   theta: int) -> float:
    """Value of a *fixed* open-loop focal action sequence against doctrine theta.

    This is deliberately naive: it walks the trajectory directly and sums the
    per-turn payoff.  It shares no code with the DP above, so agreement between
    the two is real evidence that the DP is correct.
    """
    cum = 0
    total = 0.0
    for t, af in enumerate(focal_actions):
        ao = (theta + cum) % spec.b
        cum += ao
        total += payoff(spec, af, ao, t, cum)
    return total


def brute_force_best_open_loop(spec: GameSpec) -> float:
    """Best *open-loop* (non-adaptive) focal sequence, averaged over doctrines.
    An upper bound that any policy with less information must fall short of;
    used only as a sanity reference."""
    best = None
    for seq in _sequences(spec.b, spec.T):
        v = sum(brute_force_fixed_policy_value(spec, seq, th) for th in range(spec.K)) / spec.K
        if best is None or v > best:
            best = v
    return best


def _sequences(b: int, T: int):
    if T == 0:
        yield ()
        return
    for head in range(b):
        for tail in _sequences(b, T - 1):
            yield (head,) + tail
