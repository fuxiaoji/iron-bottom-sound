"""Track D defect zoo: five agent types with distinct, hand-defined mechanisms.

Every agent answers the same query — "which option do you take at this decision
node?" — and every agent is *exactly computable*.  The point of the zoo is that
the defects are MECHANISM differences, not strength differences.

Zoo members
-----------
OPT  Bayesian DP over the belief (the lab's optimal policy).
MYO  One-step greedy: maximises the immediate expected payoff, belief-aware.
     Never uses lookahead.  Mechanism defect: myopia.
NOM  One-step greedy against an assumed UNIFORM opponent action distribution:
     it ignores the evidence in the belief.  Mechanism defect: no opponent
     model.  (Differs from MYO whenever the belief is informative.)
NBU  Full DP lookahead, but computed under the ROOT prior belief frozen at every
     node — i.e. it plans correctly but never updates its information state.
     Mechanism defect: no belief update.  (Differs from NOM by lookahead.)
AMB  Maximin over the hypotheses in the current support: it evaluates each
     option by its WORST-case continuation over consistent doctrines and picks
     the best worst case.  Mechanism defect: ambiguity/risk distortion.

Dropped, with reason
--------------------
COMMITMENT-FORGETFUL ("ignores its own sealed orders") is NOT expressible in
this lab: replanning is weakly dominant (see FAILURES F4), so an agent that
ignores its own commitments coincides with OPT everywhere and is unidentifiable
by construction.  A commitment-forgetting defect needs a lab where breaking a
seal has a cost — a design change, not a parameter, and out of scope for the
cheap kill test.
"""

from __future__ import annotations

from exact_lab import ExactLab, GameSpec, opponent_action, payoff

ZOO = ("OPT", "MYO", "NOM", "NBU", "AMB")


def _immediate_expected(spec: GameSpec, lab: ExactLab, belief, kind: str, a: int,
                        af: int, t: int, uniform_ao: bool) -> float:
    af_exec = af if kind == "continue" else a
    total = 0.0
    if uniform_ao:
        for ao in spec.actions:
            total += payoff(spec, af_exec, ao, t, 0) / spec.b
    else:
        for (theta, ao_hist), w in belief:
            ao = opponent_action(theta, sum(ao_hist), spec.b)
            total += w * payoff(spec, af_exec, ao, t, 0)
    return total


def _nbu_dp(spec: GameSpec):
    """DP under the wrong 'stationary uniform opponent' model (frozen prior)."""
    cache: dict = {}

    def V(t: int, af: int, rf: int) -> float:
        if t >= spec.T:
            return 0.0
        key = (t, af, rf)
        if key in cache:
            return cache[key]
        opts = [("continue", -1)] if rf > 0 else []
        opts += [("replan", a) for a in spec.actions]
        best = None
        for kind, a in opts:
            af_exec = af if kind == "continue" else a
            rf_next = rf - 1 if kind == "continue" else spec.L - 1
            imm = sum(payoff(spec, af_exec, ao, t, 0) for ao in spec.actions) / spec.b
            v = imm + (V(t + 1, af_exec, max(rf_next, 0)) if t + 1 < spec.T else 0.0)
            if best is None or v > best:
                best = v
        cache[key] = best
        return best

    def best(t: int, af: int, rf: int):
        opts = [("continue", -1)] if rf > 0 else []
        opts += [("replan", a) for a in spec.actions]
        return max(opts, key=lambda ka: (
            sum(payoff(spec, af if ka[0] == "continue" else ka[1], ao, t, 0)
                for ao in spec.actions) / spec.b
            + (V(t + 1, af if ka[0] == "continue" else ka[1],
                 (rf - 1) if ka[0] == "continue" else spec.L - 1)
               if t + 1 < spec.T else 0.0)))

    return best


def agent_answer(agent: str, spec: GameSpec, lab: ExactLab, node, belief):
    """The option (kind, action) the agent takes at the given decision node."""
    t, af, rf, _obs = node
    opts = [("continue", -1)] if rf > 0 else []
    opts += [("replan", a) for a in spec.actions]

    if agent == "OPT":
        return lab.best_action(t, af, rf, belief)

    if agent == "MYO":
        return max(opts, key=lambda ka: _immediate_expected(
            spec, lab, belief, ka[0], ka[1], af, t, uniform_ao=False))

    if agent == "NOM":
        return max(opts, key=lambda ka: _immediate_expected(
            spec, lab, belief, ka[0], ka[1], af, t, uniform_ao=True))

    if agent == "NBU":
        return _nbu_dp(spec)(t, af, rf)

    if agent == "AMB":
        # maximin over the hypotheses in the belief support, using the
        # Bayes-optimal continuation value at each single hypothesis
        def worst(kind: str, a: int) -> float:
            vals = []
            for (theta, ao_hist), _w in belief:
                vals.append(lab.Q_realised(t, af, rf, belief, (theta, ao_hist),
                                           kind, a))
            return min(vals) if vals else 0.0
        return max(opts, key=lambda ka: worst(ka[0], ka[1]))

    raise ValueError(agent)


def regret_of(spec: GameSpec, lab: ExactLab, node, belief, option) -> float:
    t, af, rf, _obs = node
    v_star = lab.V(t, af, rf, belief)
    return v_star - lab.W(t, af, rf, belief, option[0], option[1])
