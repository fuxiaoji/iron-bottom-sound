"""Unit tests for the Exact Team-Abstraction Lab (the four required cases +
two-solver cross-validation)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from exact_team_lab.core import (L_star, TeamGame, V_flat, V_partition,
                                 tree_value_flat, tree_value_partition)


def test_two_solvers_agree_flat_and_partitions():
    g = TeamGame(n_agents=4, b=3, T=3, n_tasks=3)
    assert V_flat(g, 0, 0) == pytest.approx(tree_value_flat(g, 0, 0), abs=1e-12)
    for partition in (((0, 1), (2, 3)), ((0,), (1,), (2,), (3,)), ((0, 2), (1, 3)),
                      ((0, 1, 2, 3),)):
        assert V_partition(g, 0, 0, partition) == pytest.approx(
            tree_value_partition(g, 0, 0, partition), abs=1e-12)


def test_singleton_partition_equals_flat():
    g = TeamGame(n_agents=3, b=2, T=4, n_tasks=2)
    flat = V_flat(g, 0, 0)
    singleton = V_partition(g, 0, 0, ((0,), (1,), (2,)))
    assert flat == pytest.approx(singleton, abs=1e-12)
    assert L_star(g, 0, ((0,), (1,), (2,))) == pytest.approx(0.0, abs=1e-12)


def test_case1_grouping_lossless():
    """Two agents whose payoffs depend only on the SUM of their actions:
    merging them into one decision entity with b actions each → the group can
    only emit one shared action, but because only the sum matters the shared
    action can reproduce every reachable sum profile? NO in general — so this
    case constructs the regime where it is provably lossless: actions of the
    two agents are identical-reward (payoff ignores agent-1 entirely)."""
    reward = lambda task, joint: 1.0 if joint[0] == task else -0.25
    g = TeamGame(n_agents=3, b=2, T=3, n_tasks=2, reward=reward)
    # agent 1 is irrelevant → grouping (1, 2) is lossless
    assert L_star(g, 0, ((0,), (1, 2))) == pytest.approx(0.0, abs=1e-12)


def test_case2_grouping_harmful():
    """Two agents need opposite actions: reward is 1 iff a0 != a1. Under the
    merged partition both execute the same action → always -1."""
    reward = lambda task, joint: 1.0 if joint[0] != joint[1] else -1.0
    g = TeamGame(n_agents=2, b=2, T=3, n_tasks=1, reward=reward)
    flat = V_flat(g, 0, 0)
    merged = V_partition(g, 0, 0, ((0, 1),))
    # T=3: flat plays (0,1) every turn -> +3; merged must play identical actions -> -3
    assert flat == pytest.approx(3.0, abs=1e-12)
    assert merged == pytest.approx(-3.0, abs=1e-12)
    assert L_star(g, 0, ((0, 1),)) == pytest.approx(6.0, abs=1e-12)


def test_case3_state_dependent_split():
    """State-dependent split (minimal formal object): with the two group
    members' preferences ALIGNED, merging is lossless; with them OPPOSED, the
    same merge is strictly harmful. Two game states, same partition, same
    solver — the abstraction decision genuinely depends on the state."""
    merged = ((0,), (1, 2))
    split = ((0,), (1,), (2,))
    aligned = TeamGame(n_agents=3, b=2, T=1, n_tasks=2,
                       reward=lambda t, j: (1.0 if j[1] == t else -0.5)
                                           + (1.0 if j[2] == t else -0.5))
    opposed = TeamGame(n_agents=3, b=2, T=1, n_tasks=2,
                       reward=lambda t, j: (1.0 if j[1] == t else -0.5)
                                           + (1.0 if j[2] == 1 - t else -0.5))
    assert L_star(aligned, 0, merged) == pytest.approx(0.0, abs=1e-12)
    assert L_star(opposed, 0, merged) == pytest.approx(1.5, abs=1e-12)
    assert L_star(opposed, 0, split) == pytest.approx(0.0, abs=1e-12)


def test_case4_failure_sensitive_organization():
    """Two organizations of the same 4 agents: org A groups the fragile pair
    (0,1); org B keeps 0 split. Reward needs agent 0 and agent 1 to be able to
    disagree (a0 != a1) AND needs the pair's sum to be controllable. After
    agent 0 is damaged (loses its biggest action), the merged group's shared
    action set is the intersection, which can no longer satisfy a0 != a1 while
    org B still can for agent 1's side by compensating."""
    reward = lambda task, joint: (1.0 if joint[0] != joint[1] else -1.0) + (
        1.0 if joint[2] == task else -0.25)
    damaged = TeamGame(n_agents=4, b=3, T=3, n_tasks=3, reward=reward,
                       damaged=(0,))
    orgA = ((0, 1), (2, 3))
    orgB = ((0,), (1,), (2, 3))
    va = V_partition(damaged, 0, 0, orgA)
    vb = V_partition(damaged, 0, 0, orgB)
    assert vb > va, (vb, va)
