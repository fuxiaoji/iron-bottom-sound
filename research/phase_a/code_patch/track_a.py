"""Track A — Adaptive Test-Time Planning under a global compute budget.

Frozen protocol (Phase A v3.1 directive):
  200 natural decision states per task, stratified 50 per episode-progress
  quartile, never selected by future planning benefit; candidates sampled from the
  frozen stochastic MAPPO action distribution with the deterministic mean always
  included; frozen base-policy continuation; H=5; disjoint search/evaluation RNG;
  budgets B = {0,4,16,64}; equal total planning budget = 16*N_states for the
  primary comparison (UNIFORM_16, RANDOM_ALLOCATION, UNCERTAINTY_HEURISTIC,
  HINDSIGHT_ORACLE); UNIFORM_4/64 are frontier references only.

    .venv_phase_a/bin/python research/phase_a/scripts/track_a.py [--states 200] [--pilot 3]
"""

from __future__ import annotations

import copy
import json
import math
import random
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hardened import (Registry, bootstrap_ci_mean, bootstrap_ci_paired,  # noqa: E402
                      quantiles)
from phase_a_common import MAX_STEPS, PA, FrozenActor, make_task_env  # noqa: E402

TASKS = ("balance", "sampling")
BUDGETS = (0, 4, 16, 64)
H = 5
N_STATES = 200
TOTAL_PER_STATE = 16
SEED_SEARCH = 2000
SEED_EVAL = 3000
RNG_SEED = 20260921


# ---------------------------------------------------------------- policy
def load_actor(task):
    sel = json.loads((PA / "raw" / "track_common" / "checkpoint_selection.json").read_text())
    seed = sel["selection"][task]["median_seed"]
    ck = sorted((PA / f"runs" / f"mappo_{task}_s{seed}").rglob("checkpoint_600000.pt"))[-1]
    return FrozenActor(ck), seed


class StochasticActor(FrozenActor):
    """Frozen MAPPO actor with the stochastic branch reconstructed.

    BenchMARL config for MAPPO: use_tanh_normal=True, scale_mapping=
    biased_softplus_1.0 -> std = softplus(log_std_raw + 1.0); a ~ N(0,1);
    action = tanh(mean + std * a).
    """

    @torch.no_grad()
    def sample_action(self, obs, rng):
        """obs is a per-agent list (VMAS) — sample a joint action."""
        if isinstance(obs, (list, tuple)):
            return [self.sample_action(o, rng) for o in obs]
        h = torch.tanh(obs @ self.W0.T + self.b0)
        h = torch.tanh(h @ self.W2.T + self.b2)
        out = h @ self.W4.T + self.b4
        mean, raw = out.chunk(2, dim=-1)
        std = torch.nn.functional.softplus(raw + 1.0)
        g = torch.Generator().manual_seed(rng.randrange(2 ** 31))
        eps = torch.randn(mean.shape, generator=g)
        return torch.tanh(mean + std * eps)


# ---------------------------------------------------------------- environment
def clone(env):
    return copy.deepcopy(env)


def rollout_return(env_snapshot, obs0, actor, first_actions, horizon=H, rng=None,
                   stochastic=False):
    """Roll H steps from a cloned snapshot; step 0 uses `first_actions`, the rest
    the frozen base policy. `obs0` is the observation captured at the snapshot
    point (this VMAS build exposes observations only through reset/step returns)."""
    env = clone(env_snapshot)
    obs = obs0
    total = 0.0
    for t in range(horizon):
        acts = first_actions if t == 0 else (actor.act(obs) if not stochastic
                                            else actor.sample_action(obs, rng))
        obs, rew, dones, infos = env.step(acts)
        total += float(sum(float(r.sum()) for r in rew))
        if bool(torch.as_tensor(dones).any()):
            break
    return total


def candidate_set(actor_stoch, obs, n_candidates, rng):
    """Deterministic mean action first, then sampled joint actions from the frozen
    stochastic policy (distinct RNG stream from the held-out evaluation)."""
    base = actor_stoch.act(obs)
    cands = [base]
    while len(cands) < n_candidates:
        cands.append(actor_stoch.sample_action(obs, rng))
    return cands[:n_candidates]


# ---------------------------------------------------------------- state collection
def replay_episode(env, actor, step_index, seed):
    """Deterministic replay of a clean episode to `step_index`; returns the state
    snapshot and the observation at that instant."""
    obs = env.reset(seed=seed)
    for t in range(step_index):
        obs, rew, dones, infos = env.step(actor.act(obs))
    return clone(env), obs


def collect_states(task, actor, n_states=N_STATES, seed0=7000):
    """Natural decision states stratified by episode-progress quartile.

    A state is identified by (episode_seed, step_index); it is reconstructed by
    replaying the deterministic frozen policy, so no selection uses planning value.
    """
    per_q = n_states // 4
    states = []
    ep = 0
    while len(states) < n_states:
        seed = seed0 + ep
        ep += 1
        env = make_task_env(task, 1, seed=seed)
        obs = env.reset(seed=seed)
        taken = {0: 0, 1: 0, 2: 0, 3: 0}
        for t in range(MAX_STEPS):
            q = min(3, int(t / (MAX_STEPS / 4)))
            if taken[q] < per_q and (t % 3 == 0):
                states.append({"task": task, "episode_seed": seed, "step_index": t,
                               "quartile": q})
                taken[q] += 1
            obs, _rew, dones, _infos = env.step(actor.act(obs))
            if bool(torch.as_tensor(dones).any()):
                break
        if len(states) >= n_states:
            break
    states = states[:n_states]
    return states


def replay_to(env, actor, step_index):
    """Advance a fresh env to `step_index` deterministically; returns (snapshot, obs)."""
    obs = env.reset(seed=env.seed if hasattr(env, "seed") else None) if False else None
    obs = env.reset(seed=SEED_REPLAY + step_index * 0) if False else None
    return None, None


# ---------------------------------------------------------------- planning
def measure_state(task, actor_stoch, snapshot, obs, rng_search, rng_eval):
    """Delta(s,B) for every frozen budget at one state."""
    rng = random.Random(rng_search)
    cands = candidate_set(actor_stoch, obs, max(BUDGETS), rng)
    out = {}
    search_returns = {}
    for b in BUDGETS:
        if b == 0:
            sel = 0
        else:
            vals = [rollout_return(snapshot, obs, actor_stoch, cands[i], rng=rng)
                    for i in range(b)]
            search_returns[b] = vals
            sel = max(range(b), key=lambda i: (vals[i], -i))
        ev = rollout_return(snapshot, obs, actor_stoch, cands[sel],
                            rng=random.Random(rng_eval))
        out[b] = {"selected": sel, "search_return": search_returns.get(b, [None])[sel],
                  "eval_return": ev}
    d = {b: out[b]["eval_return"] - out[0]["eval_return"] for b in BUDGETS}
    return out, d


# ---------------------------------------------------------------- allocation
def allocate_uniform(deltas, b, n):
    return {i: b for i in range(n)}


def allocate_random(deltas, total, n, rng):
    """Random budget in {0,4,16,64} with exactly `total` total (greedy fill)."""
    budgets = {i: 0 for i in range(n)}
    remaining = total
    order = list(range(n))
    rng.shuffle(order)
    for i in order:
        if remaining <= 0:
            break
        choice = rng.choice([b for b in BUDGETS if b <= remaining])
        budgets[i] = choice
        remaining -= choice
    spent = sum(budgets.values())
    if spent < total and order:
        for i in order:
            for b in (64, 16, 4):
                if spent + b <= total:
                    budgets[i] = b
                    spent += b
                    break
            if spent == total:
                break
    return budgets


def allocate_uncertainty(deltas, total, n, entropy_by_state, rng):
    """Uncertainty heuristic frozen BEFORE results: allocate greedily to the
    highest policy-action entropy states first (entropy = mean per-agent std of
    the frozen stochastic actor at that state), 64/16/4/0 in that order."""
    order = sorted(range(n), key=lambda i: -entropy_by_state[i])
    budgets = {i: 0 for i in range(n)}
    remaining = total
    for i in order:
        if remaining <= 0:
            break
        for b in (64, 16, 4):
            if b <= remaining:
                budgets[i] = b
                remaining -= b
                break
    return budgets


def allocate_oracle(deltas, total, n):
    """Hindsight oracle: choose per-state budgets maximising the measured held-out
    value subject to the same total. Analysis-only; never a deployable baseline."""
    # value of giving budget b to state i, measured on the margin over budget 0
    order = sorted(range(n), key=lambda i: -max(deltas[i][b] for b in BUDGETS))
    budgets = {i: 0 for i in range(n)}
    remaining = total
    for i in order:
        if remaining <= 0:
            break
        best_b, best_gain = 0, 0.0
        for b in BUDGETS:
            if b > 0 and b <= remaining:
                gain = deltas[i][b] / b          # gain per unit budget
                if gain > best_gain:
                    best_gain, best_b = gain, b
        budgets[i] = best_b
        remaining -= best_b
    return budgets


def value_of(deltas, budgets, i):
    return deltas[i][budgets[i]]


def main() -> int:
    args = sys.argv[1:]
    n_states = N_STATES
    if "--states" in args:
        n_states = int(args[args.index("--states") + 1])
    pilot = int(args[args.index("--pilot") + 1]) if "--pilot" in args else 0
    t0 = time.time()
    reg = Registry()
    results = {"n_states_per_task": n_states, "budgets": list(BUDGETS), "H": H,
               "total_per_state": TOTAL_PER_STATE, "tasks": {}}
    for task in TASKS:
        actor, mseed = load_actor(task)
        stoch = StochasticActor(Path(actor.source))
        states = collect_states(task, actor, n_states=n_states)
        if pilot:
            states = states[:pilot]
        print(f"[{task}] {len(states)} states (median seed {mseed})", flush=True)
        rows, entropies = [], {}
        for si, s in enumerate(states):
            with reg.unit(f"A_state_{task}_{si}", "A", task, "planning_operator") as u:
                env = make_task_env(task, 1, seed=s["episode_seed"])
                snap, obs = replay_episode(env, actor, s["step_index"], s["episode_seed"])
                per_budget, d = measure_state(task, stoch, snap, obs, SEED_SEARCH + si,
                                              SEED_EVAL + si)
                with torch.no_grad():
                    _h = torch.tanh(obs[0] @ stoch.W0.T + stoch.b0)
                    _h = torch.tanh(_h @ stoch.W2.T + stoch.b2)
                    _out = _h @ stoch.W4.T + stoch.b4
                    _raw = _out.chunk(2, dim=-1)[1]
                    ent = float(torch.nn.functional.softplus(_raw + 1.0).mean())
                entropies[si] = ent
                rows.append({"task": task, "state_idx": si, "episode_seed": s["episode_seed"],
                             "step_index": s["step_index"], "quartile": s["quartile"],
                             "delta": {str(b): d[b] for b in BUDGETS},
                             "eval": {str(b): per_budget[b]["eval_return"] for b in BUDGETS},
                             "search": {str(b): per_budget[b]["search_return"] for b in BUDGETS},
                             "entropy": ent})
                u.success({"delta": {str(b): d[b] for b in BUDGETS}}, sim_steps=(sum(BUDGETS) + len(BUDGETS)) * H)
            if (si + 1) % 10 == 0:
                print(f"  {task} {si+1}/{len(states)}  {time.time()-t0:.0f}s", flush=True)
        deltas = [{b: r["delta"][str(b)] for b in BUDGETS} for r in rows]
        n = len(rows)
        total = TOTAL_PER_STATE * n
        rng = random.Random(RNG_SEED)
        allocs = {
            "UNIFORM_16": allocate_uniform(deltas, TOTAL_PER_STATE, n),
            "UNIFORM_4": allocate_uniform(deltas, 4, n),
            "UNIFORM_64": allocate_uniform(deltas, 64, n),
            "RANDOM_ALLOCATION": allocate_random(deltas, total, n, rng),
            "UNCERTAINTY_HEURISTIC": allocate_uncertainty(deltas, total, n, entropies, rng),
            "HINDSIGHT_ORACLE": allocate_oracle(deltas, total, n),
        }
        means = {k: sum(value_of(deltas, v, i) for i in range(n)) / n
                 for k, v in allocs.items()}
        totals_spent = {k: sum(v.values()) for k, v in allocs.items()}
        pos = [max(0.0, deltas[i][b]) for i in range(n) for b in BUDGETS]
        gain_vals = sorted((max(deltas[i][b] for b in BUDGETS), i) for i in range(n))[::-1]
        tot_gain = sum(g for g, _ in gain_vals if g > 0)
        top25 = gain_vals[:max(1, n // 4)]
        conc = (sum(g for g, _ in top25 if g > 0) / tot_gain) if tot_gain > 0 else 0.0
        results["tasks"][task] = {"n_states": n, "median_seed": mseed,
                                  "allocation_means": means, "allocation_totals": totals_spent,
                                  "gain_concentration_top25": conc,
                                  "per_state_delta": {str(i): rows[i]["delta"] for i in range(n)},
                                  "quartile_means": {q: sum(rows[i]["delta"]["64"] for i in range(n)
                                                            if rows[i]["quartile"] == q) /
                                                        max(1, sum(1 for i in range(n)
                                                                   if rows[i]["quartile"] == q))
                                                     for q in range(4)}}
        print(f"[{task}] means={ {k: round(v,3) for k,v in means.items()} } conc={conc:.3f}", flush=True)
    results["wall_seconds"] = round(time.time() - t0, 1)
    results["registry"] = reg.reconcile()
    out = PA / "metrics" / ("track_a_pilot.json" if pilot else "track_a.json")
    out.write_text(json.dumps(results, indent=1))
    print(f"wrote {out} ({results['wall_seconds']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
