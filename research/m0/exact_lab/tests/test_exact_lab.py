"""Correctness tests for the Exact Strategic Lab.

The lab is the truth source for Tracks A, B and D.  If any of these fail, no
downstream number from the lab may be used.

Run:
    PYTHONPATH=backend/src:research/m0 .venv/bin/python -m pytest \
        research/m0/exact_lab/tests -q
"""

from __future__ import annotations

import pytest

from exact_lab import (ExactLab, GameSpec, alias_stats, snapshot_of,
                       brute_force_best_open_loop,
                       brute_force_fixed_policy_value, case1_markov_control,
                       case3_negative_control, case4_path_dependent,
                       enumerate_reachable, find_witness, initial_belief,
                       reference_optimum)


# --------------------------------------------------------------------------
# 1. Two independent solvers must agree
# --------------------------------------------------------------------------

TINY = [
    GameSpec(name="t_c1", T=2, b=2, K=2, m=2, L=1, family="coordination", alpha=1),
    GameSpec(name="t_c2", T=2, b=2, K=2, m=2, L=2, family="coordination", alpha=1),
    GameSpec(name="t_a1", T=2, b=2, K=3, m=2, L=1, family="anticor", alpha=1),
    GameSpec(name="t_a2", T=2, b=2, K=3, m=2, L=2, family="anticor", alpha=1),
    GameSpec(name="t_d1", T=2, b=2, K=2, m=2, L=1, family="delayed", alpha=1),
    GameSpec(name="t_d2", T=2, b=2, K=2, m=2, L=2, family="delayed", alpha=1),
    GameSpec(name="t_p1", T=2, b=2, K=2, m=2, L=2, family="pathdep", alpha=1),
    GameSpec(name="t_n0", T=3, b=2, K=1, m=2, L=2, family="null", alpha=1),
    GameSpec(name="t_nc", T=3, b=2, K=2, m=2, L=1, family="coordination", alpha=1),
]


@pytest.mark.parametrize("spec", TINY, ids=[s.name for s in TINY])
def test_dp_matches_independent_policy_enumeration(spec):
    lab = ExactLab(spec)
    dp = lab.V(0, 0, 0, initial_belief(spec))
    ref = reference_optimum(spec)
    assert dp == pytest.approx(ref, abs=1e-12), f"{spec.name}: DP={dp} REF={ref}"


# --------------------------------------------------------------------------
# 2. Dynamics: forcing "continue" forever must reproduce the fixed-sequence value
# --------------------------------------------------------------------------


def test_forced_policy_matches_brute_force_sequence():
    """A policy that replans to `a` at t=0 and then *continues forever* must be
    worth exactly the direct trajectory sum of the constant sequence (a,...,a).

    This is the dynamics check: it pins the payoff accumulation, the opponent
    update and the public-signal branching against a from-scratch simulation.
    """
    from exact_lab.reference import _evaluate_policy, _reachable_nodes

    spec = GameSpec(name="forced", T=4, b=2, K=2, m=2, L=4, family="coordination", alpha=1)
    beliefs = _reachable_nodes(spec)
    for a in spec.actions:
        policy = {}
        for node in beliefs:
            t, af, rf, obs = node
            if t == 0:
                policy[node] = ("replan", a)
            elif rf > 0:
                policy[node] = ("continue", -1)
            else:
                policy[node] = ("replan", a)
        got = _evaluate_policy(spec, policy, (0, 0, 0, ()), beliefs)
        expected = sum(brute_force_fixed_policy_value(spec, (a,) * spec.T, th)
                       for th in range(spec.K)) / spec.K
        assert got == pytest.approx(expected, abs=1e-12), f"a={a}: {got} vs {expected}"


def test_continue_is_never_better_than_replan():
    """Delta_t = V_replan - V_continue must be >= 0 wherever a commitment exists,
    by construction (replanning is optional)."""
    from exact_lab.generator import grid

    for spec in grid("discovery")[:12]:
        lab = ExactLab(spec)
        for h in enumerate_reachable(spec, lab):
            if h.rf <= 0:
                continue
            vc = lab.W(h.t, h.af, h.rf, h.belief, "continue", -1)
            vr = lab.V_replan(h.t, h.af, h.rf, h.belief)
            assert vr >= vc - 1e-12, (spec.name, h.snapshot, vr, vc)


def test_adaptive_beats_or_ties_open_loop():
    """A player that may re-decide can never do worse than a fixed sequence."""
    for spec in TINY:
        lab = ExactLab(spec)
        dp = lab.V(0, 0, 0, initial_belief(spec))
        assert dp >= brute_force_best_open_loop(spec) - 1e-12, spec.name


def test_value_is_bounded_by_payoff_range():
    for spec in TINY:
        lab = ExactLab(spec)
        v = lab.V(0, 0, 0, initial_belief(spec))
        assert -spec.T - 1e-9 <= v <= spec.T + 1e-9, spec.name


# --------------------------------------------------------------------------
# 3. The four required cases
# --------------------------------------------------------------------------


def _alias_gap(spec, min_group=2):
    """Node-level alias gap: max optimal-value / delta difference between two
    same-snapshot nodes with different beliefs."""
    st = alias_stats(spec)
    return max(st["max_v_gap"], st["max_delta_gap"]), st["n_mixed_cells"], st["n_nodes"]


def test_case1_markov_control_has_no_aliasing():
    """No hidden variable and an opponent-blind payoff: the snapshot suffices."""
    gap, _n, n_hist = _alias_gap(case1_markov_control())
    assert n_hist > 0
    assert gap == pytest.approx(0.0, abs=1e-12), f"gap={gap}"


def test_case3_negative_control_has_no_aliasing():
    """A hidden doctrine exists but provably cannot matter, so the gap is zero.
    This is the control that keeps Case 2 from being a tautology."""
    gap, _n, n_hist = _alias_gap(case3_negative_control())
    assert n_hist > 0
    assert gap == pytest.approx(0.0, abs=1e-12), f"gap={gap}"


def test_case4_path_dependence_creates_aliasing():
    """Identical snapshot, different past path, different terminal payoff."""
    gap, _n, _h = _alias_gap(case4_path_dependent())
    assert gap > 0.0, "path-dependent payoff produced no aliasing"


def test_case2_sealed_commitment_witness_exists():
    """There must exist two histories with the SAME public snapshot whose optimal
    continuations differ.  This is the minimal witness the plan requires."""
    res = find_witness()
    best_gap = res["best_gap"]
    assert best_gap is not None, "no sealed-commitment witness found in the search grid"
    assert best_gap["gap"] > 0.0
    assert best_gap["v_gap"] > 0.0 or best_gap["d_gap"] > 0.0

    dis = res["best_disagreeing"]
    assert dis is not None, ("aliasing exists but no witness was found where the "
                             "optimal actions themselves disagree")
    assert dis["actions_disagree"]
    assert dis["a"] != dis["b"]
