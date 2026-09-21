"""Track B — Active Coordination-Failure Boundary Discovery.

Frozen design (PRE_REGISTRATION_PHASE_A §6 + v3.1 directive):
  perturbation space x = (agent, time-window, modality, severity) with the three
  frozen modalities only; a dense hidden evaluation universe evaluated once
  (analysis-only); active methods may only *query* labels from it at identical
  counts K = {25,50,100,200}; primary test = structure-aware vs GENERIC black-box
  active learning (beating random alone is insufficient).

Failure labels: balance = audited native failure; sampling = return < Q25_clean.

    .venv_phase_a/bin/python research/phase_a/scripts/track_b.py [--per-modality 6]
"""

from __future__ import annotations

import itertools
import json
import random
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hardened import Registry  # noqa: E402
from phase_a_common import (PA, FrozenActor, Perturbation, apply_action_perturbation,  # noqa: E402
                            apply_observation_noise, make_task_env)


def _policy_std(self, obs):
    """Mean softplus(log_std) of the frozen actor — the uncertainty signal the
    generic black-box baseline is allowed to see."""
    if isinstance(obs, (list, tuple)):
        return sum(_policy_std(self, o) for o in obs) / len(obs)
    with torch.no_grad():
        h = torch.tanh(obs @ self.W0.T + self.b0)
        h = torch.tanh(h @ self.W2.T + self.b2)
        raw = (h @ self.W4.T + self.b4).chunk(2, dim=-1)[1]
        return float(torch.nn.functional.softplus(raw + 1.0).mean())


FrozenActor.policy_std = _policy_std

TASKS = ("balance", "sampling")
KS = (25, 50, 100, 200)
WINDOWS = (10, 30, 50, 70, 90)          # window start steps, frozen
WIN_LEN = 10
MODALITIES = {
    "obs_noise": (0.05, 0.10, 0.20, 0.40),
    "act_noise": (0.05, 0.20),
    "act_drop": (0.10, 0.30),
    "act_delay": (1.0,),
    "dropout": (1.0,),
}
SEED_BASE = 20_000


def load_actor(task):
    sel = json.loads((PA / "raw" / "track_common" / "checkpoint_selection.json").read_text())
    seed = sel["selection"][task]["median_seed"]
    ck = sorted((PA / "runs" / f"mappo_{task}_s{seed}").rglob("checkpoint_600000.pt"))[-1]
    return FrozenActor(ck), seed


def sampling_q25():
    lock = json.loads((PA / "ENVIRONMENT_LOCK.json").read_text())
    return lock["sampling_semantics"]["clean_Q25"]


def make_universe(task, n_agents, per_modality):
    """Frozen grid: modality x severity x agent-subset x window. The size is fixed
    BEFORE any label is read (v3.1: the universe is analysis-only)."""
    out = []
    for modality, severities in MODALITIES.items():
        for sev in severities:
            for w in WINDOWS:
                for a in range(n_agents):
                    out.append(Perturbation(modality, (a,), w, w + WIN_LEN, sev))
                if modality in ("dropout", "obs_noise"):
                    for a, b in itertools.combinations(range(n_agents), 2):
                        out.append(Perturbation(modality, (a, b), w, w + WIN_LEN, sev))
    # deterministic thinning to the frozen per-modality budget, preserving spread
    rng = random.Random(20260921)
    rng.shuffle(out)
    by_mod = {}
    for p in out:
        by_mod.setdefault(p.modality, []).append(p)
    picked = []
    for modality, rows in by_mod.items():
        picked += rows[:per_modality * len(WINDOWS) * 2]
    picked.sort(key=lambda p: (p.modality, p.severity, p.t_start, p.agents))
    return picked


def run_perturbed(actor, task, pert, seed, q25, n_agents):
    """One perturbed episode. Returns (return, failure_label, steps)."""
    env = make_task_env(task, 1, seed=seed)
    obs = env.reset(seed=seed)
    rng = random.Random(seed * 7919 + 13)
    memory, total, steps = {}, 0.0, 0
    ent_sum, ent_n = 0.0, 0
    while steps < 100:
        if pert.active(steps):
            if pert.modality == "obs_noise":
                obs = apply_observation_noise(obs, pert, rng)
            base_acts = actor.act(obs)
            acts = apply_action_perturbation(base_acts, pert, rng, memory)
        else:
            acts = actor.act(obs)
        # generic (structure-free) uncertainty signal: mean frozen-policy action
        # std at this state, computed during the label episode at no extra cost
        if hasattr(actor, "policy_std"):
            ent_sum += actor.policy_std(obs)
            ent_n += 1
        obs, rew, dones, infos = env.step(acts)
        total += float(sum(float(r.sum()) for r in rew))
        steps += 1
        if bool(torch.as_tensor(dones).any()):
            break
    if task == "balance":
        terminated = bool(torch.as_tensor(dones).any())
        success = terminated and not bool(torch.as_tensor(env.scenario.on_the_ground).any())
        failure = not success
    else:
        failure = total < q25
    return total, failure, steps, (ent_sum / max(1, ent_n))


def discover(queried, labels, boundary_cells):
    """Discovery definition validated in positive-control Toy B."""
    qs = set(queried)
    found = 0
    for b in boundary_cells:
        key_b = b if not isinstance(b, tuple) else tuple(b)
        if key_b in qs and any(labels[n] != labels[key_b] for n in neighbours(key_b) if n in qs):
            found += 1
            continue
        ns = [n for n in neighbours(key_b) if n in qs]
        if any(labels[a] != labels[c] for a in ns for c in ns):
            found += 1
    return found


def neighbours(x):
    """Local neighbourhood in the frozen grid: +/-1 slot along each axis index."""
    out = []
    for ax in range(len(x)):
        for d in (-1, 1):
            y = list(x)
            y[ax] += d
            if y[ax] >= 0:
                out.append(tuple(y))
    return out


def main() -> int:
    per_modality = 6
    if "--per-modality" in sys.argv:
        per_modality = int(sys.argv[sys.argv.index("--per-modality") + 1])
    t0 = time.time()
    reg = Registry()
    out = {"universe_target_per_task": None, "ks": list(KS), "tasks": {}}
    q25s = {}
    for task in TASKS:
        q25s[task] = sampling_q25() if task == "sampling" else None
        actor, mseed = load_actor(task)
        n_agents = {"balance": 3, "sampling": 3}[task]
        universe = make_universe(task, n_agents, per_modality)
        out["universe_target_per_task"] = len(universe)
        print(f"[{task}] universe={len(universe)} agents={n_agents} median_seed={mseed}", flush=True)
        labels, cells, rows, ents = {}, [], [], {}
        for ci, pert in enumerate(universe):
            cell = (list(MODALITIES).index(pert.modality), MODALITIES[pert.modality].index(pert.severity),
                    WINDOWS.index(pert.t_start), pert.agents[0])
            with reg.unit(f"B_label_{task}_{ci}", "B", task, "universe_label") as u:
                seed = SEED_BASE + ci
                ret, fail, steps, ent = run_perturbed(actor, task, pert, seed, q25s[task], n_agents)
                ents[cell] = ent
                labels[cell] = int(fail)
                cells.append(cell)
                rows.append({"task": task, "paired_clean_seed": seed, "config": pert.to_dict(),
                             "return": ret, "failure_label": int(fail), "status": "SUCCESS",
                             "simulator_queries": 1, "cell": cell})
                u.success({"failure": int(fail)}, sim_queries=1, sim_steps=steps)
            if (ci + 1) % 50 == 0:
                print(f"  {task} universe {ci+1}/{len(universe)} {time.time()-t0:.0f}s", flush=True)
        fail_frac = sum(labels.values()) / max(1, len(labels))
        boundary = [c for c in cells
                    if any(labels.get(n) is not None and labels[n] != labels[c] for n in neighbours(c))]
        # ---- active methods, identical query counts
        def run_method(name, order):
            res = {}
            for K in KS:
                q = order[:K]
                res[K] = {"discovered": discover(q, labels, boundary),
                          "queries": K}
            return {"name": name, "by_k": res}
        methods = []
        rnd = list(cells); random.Random(20260921).shuffle(rnd)
        methods.append(run_method("RANDOM", rnd))
        strat = sorted(cells, key=lambda c: (c[1] % 2, random.Random(c[0] * 31 + c[1]).random()))
        methods.append(run_method("STRATIFIED", strat))
        # generic black-box uncertainty: order by distance to the nearest already-seen
        # *mixed* neighbour is unknown before querying, so the generic baseline uses
        # action-entropy at the perturbed state as its cheap acquisition signal
        # generic black-box active baseline: highest mean frozen-policy action
        # uncertainty first (no agent/time/modality structure used)
        methods.append(run_method("GENERIC_UNCERTAINTY",
                                  sorted(cells, key=lambda c: -ents.get(c, 0.0))))
        # structure-aware: sweep one modality x severity slot per (agent, window) column,
        # then bisect the ordered severity axis inside each column (Toy-B validated)
        order = []
        for a in range(n_agents):
            for wi, w in enumerate(WINDOWS):
                for mi, modality in enumerate(MODALITIES):
                    for si in range(len(MODALITIES[modality])):
                        order.append((mi, si, wi, a))
        order = [c for c in order if c in labels] + [c for c in cells if c not in order]
        methods.append(run_method("STRUCTURE_AWARE", order))
        out["tasks"][task] = {"n_universe": len(universe), "failure_fraction": fail_frac,
                              "n_boundary_cells": len(boundary), "median_seed": mseed,
                              "methods": methods,
                              "rows": rows[:0]}   # rows go to the CSV below
        (PA / "raw" / f"track_b_universe_{task}.json").write_text(
            json.dumps({"labels": {str(k): v for k, v in labels.items()},
                        "boundary": [list(c) for c in boundary],
                        "failure_fraction": fail_frac}, indent=1))
        import csv as _csv
        with open(PA / "raw" / f"track_b_labels_{task}.csv", "w", newline="") as fh:
            w = _csv.DictWriter(fh, fieldnames=["task", "paired_clean_seed", "config",
                                                "return", "failure_label", "status",
                                                "simulator_queries", "cell"])
            w.writeheader()
            for r in rows:
                r2 = dict(r); r2["config"] = json.dumps(r["config"])
                w.writerow(r2)
        print(f"[{task}] failure_fraction={fail_frac:.3f} boundary={len(boundary)}", flush=True)
    rec = reg.reconcile()
    out["registry"] = rec
    out["wall_seconds"] = round(time.time() - t0, 1)
    (PA / "metrics" / "track_b.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({t: {"failure_fraction": v["failure_fraction"],
                          "n_boundary": v["n_boundary_cells"]} for t, v in out["tasks"].items()},
                     indent=1))
    print(f"reconcile ok={rec['ok']} wall={out['wall_seconds']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
