"""Exact Team-Abstraction Lab: a tiny cooperative team game with exact
V*_flat(s), V*_Pi(s) and L*(s, Pi) = V*_flat(s) - V*_Pi(s).

Environment (deterministic, fully observable, cooperative; horizon T):

  * N agents; agent i has capability vector; at each turn every decision entity
    picks one of b actions;
  * state = (t, task_state, damage_flags); task_state in {0..S-1} rotates under
    a known transition driven jointly by all executed actions;
  * per-turn reward = task_reward(task_state, joint action) minus
    coordination_penalty if two agents in DIFFERENT groups must act
    inconsistently (kept 0 — the loss of a partition comes solely from
    constrained action sets, not from extra penalties);
  * a partition Pi constrains each group to one shared action; agents in a
    group execute that action;
  * optional damage: a damaged agent's action set shrinks (models IBS
    damage-induced speed incompatibility).

Two independent solvers:
  1. flat/enumeration DP over joint action sets (V*_flat, and V*_Pi via the
     restricted action sets);
  2. a separate recursive memoised evaluator written against the explicit game
     tree (no shared DP code).

The four required cases are unit-tested.
"""

from __future__ import annotations

from functools import lru_cache
from itertools import product


class TeamGame:
    def __init__(self, *, n_agents: int, b: int, T: int, n_tasks: int,
                 capabilities: tuple[tuple[int, ...], ...] | None = None,
                 damaged: tuple[int, ...] = (),
                 transition=None, reward=None):
        self.n = n_agents
        self.b = b
        self.T = T
        self.S = n_tasks
        self.capabilities = capabilities or tuple(tuple(range(b)) for _ in range(n_agents))
        self.damaged = set(damaged)          # damaged agents lose their last action
        self.actions_of = tuple(
            tuple(a for a in self.capabilities[i] if not (i in self.damaged and a == self.b - 1))
            for i in range(self.n))
        self._transition = transition        # (task, joint) -> task'
        self._reward = reward                # (task, joint) -> float

    def transition(self, task: int, joint: tuple[int, ...]) -> int:
        if self._transition:
            return self._transition(task, joint)
        return (task + sum(joint)) % self.S

    def reward(self, task: int, joint: tuple[int, ...]) -> float:
        if self._reward:
            return self._reward(task, joint)
        return 1.0 if sum(joint) % self.S == task else -0.25

    # -- partition-restricted joint action enumeration --------------------
    def group_joint_actions(self, partition: tuple[tuple[int, ...], ...]):
        """All executed joint action tuples achievable under the partition."""
        per_group = []
        for group in partition:
            allowed = set(self.actions_of[group[0]])
            for i in group[1:]:
                allowed &= set(self.actions_of[i])
            per_group.append(sorted(allowed))
        for picks in product(*per_group):
            executed = [None] * self.n
            for group, a in zip(partition, picks):
                for i in group:
                    executed[i] = a
            yield tuple(executed)


def V_flat(g: TeamGame, t: int, task: int) -> float:
    if t >= g.T:
        return 0.0
    return max(g.reward(task, joint) + V_flat(g, t + 1, g.transition(task, joint))
               for joint in product(*(g.actions_of[i] for i in range(g.n))))


def V_partition(g: TeamGame, t: int, task: int,
                partition: tuple[tuple[int, ...], ...]) -> float:
    if t >= g.T:
        return 0.0
    return max(g.reward(task, joint) + V_partition(g, t + 1, g.transition(task, joint), partition)
               for joint in g.group_joint_actions(partition))


def L_star(g: TeamGame, task: int, partition) -> float:
    return V_flat(g, 0, task) - V_partition(g, 0, task, partition)


# --------------------------------------------------------------------------
# Independent second implementation: explicit-tree recursion, no shared DP
# --------------------------------------------------------------------------


def tree_value_flat(g: TeamGame, t: int, task: int) -> float:
    if t >= g.T:
        return 0.0
    best = None
    stack = [()]
    while stack:
        partial = stack.pop()
        i = len(partial)
        if i < g.n:
            for a in g.actions_of[i]:
                stack.append(partial + (a,))
        else:
            v = g.reward(task, partial) + tree_value_flat(g, t + 1, g.transition(task, partial))
            if best is None or v > best:
                best = v
    return best


def tree_value_partition(g: TeamGame, t: int, task: int, partition) -> float:
    if t >= g.T:
        return 0.0
    best = None
    for joint in g.group_joint_actions(partition):
        v = g.reward(task, joint) + tree_value_partition(g, t + 1, g.transition(task, joint), partition)
        if best is None or v > best:
            best = v
    return best
