"""Track C — Budgeted Counterfactual Failure Attribution.

Frozen design (v3.1 directive + PRE_REGISTRATION_PHASE_A §7):
  exactly ONE injected fault per failed trajectory (action replacement/drop,
  observation corruption, one-step delay), injection distribution frozen; the
  attribution method never sees injection metadata; ground truth is the
  EXHAUSTIVE counterfactual repair matrix over agent x time-window cells, not the
  injection log. Valid failures: balance = same-initial-state clean twin succeeds
  and faulted twin fails; sampling = clean >= Q50, faulted < Q25, drop >= 0.5*IQR.

Cost rule (v3.1): estimate the exhaustive-matrix cost BEFORE the large run. If it
exceeds the remaining Phase A budget, complete the 50-case calibration and report
C_ENGINEERING_BLOCKED rather than shrinking the design after seeing results.

    .venv_phase_a/bin/python research/phase_a/scripts/track_c.py [--failures 50] [--pilot 2]
"""

from __future__ import annotations

import copy
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

TASKS = ("balance", "sampling")
FAULT_MODALITIES = ("act_drop", "obs_corrupt", "act_delay")
WINDOW = 5          # repair grid: 5 evenly spaced time windows
N_AGENTS = {"balance": 3, "sampling": 3}
PROBE_FRACTIONS = (0.10, 0.20, 0.25)
SEED_BASE = 40_000


def semantics(task):
    if task == "sampling":
        lock = json.loads((PA / "ENVIRONMENT_LOCK.json").read_text())["sampling_semantics"]
        return {"Q25": lock["clean_Q25"], "Q50": lock["clean_Q50"], "IQR": lock["clean_IQR"]}
    return None


def load_actor(task):
    sel = json.loads((PA / "raw" / "track_common" / "checkpoint_selection.json").read_text())
    seed = sel["selection"][task]["median_seed"]
    ck = sorted((PA / "runs" / f"mappo_{task}_s{seed}").rglob("checkpoint_600000.pt"))[-1]
    return FrozenActor(ck)


def episode(actor, task, seed, fault=None, repair=None, snapshot_at=None):
    """Run one episode, optionally injecting `fault` (a Perturbation) over a window,
    and optionally undoing it inside the cell `repair` = (agent, window_index).

    Returns (return, success_or_None, steps, snapshot, obs_at_snapshot).
    """
    env = make_task_env(task, 1, seed=seed)
    obs = env.reset(seed=seed)
    rng = random.Random(seed * 7919 + 17)
    memory, total, steps = {}, 0.0, 0
    snap = obs_snap = None
    while steps < 100:
        active_fault = fault is not None and fault.active(steps)
        if active_fault and repair is not None:
            wi = steps // max(1, (100 // WINDOW))
            if repair[1] == wi and repair[0] in fault.agents:
                active_fault = False                     # this cell is repaired
        if active_fault:
            if fault.modality == "obs_corrupt":
                obs = apply_observation_noise(obs, fault, rng)
                acts = actor.act(obs)
            else:
                acts = apply_action_perturbation(actor.act(obs), fault, rng, memory)
        else:
            acts = actor.act(obs)
        if snapshot_at is not None and steps == snapshot_at:
            snap, obs_snap = copy.deepcopy(env), obs
        obs, rew, dones, infos = env.step(acts)
        total += float(sum(float(r.sum()) for r in rew))
        steps += 1
        if bool(torch.as_tensor(dones).any()):
            break
    if task == "balance":
        terminated = bool(torch.as_tensor(dones).any())
        success = terminated and not bool(torch.as_tensor(env.scenario.on_the_ground).any())
    else:
        success = None
    return total, success, steps, snap, obs_snap


def valid_failure(task, clean_ret, clean_succ, fault_ret, fault_succ, sem):
    if task == "balance":
        return bool(clean_succ) and not bool(fault_succ)
    return bool(clean_ret >= sem["Q50"] and fault_ret < sem["Q25"]
                and clean_ret - fault_ret >= 0.5 * sem["IQR"])


def repair_matrix(actor, task, seed, fault, sem):
    """Exhaustive agent x time-window repair. Returns (cells, causal_cells, queries)."""
    cells, causal, queries = [], [], 0
    for a in range(N_AGENTS[task]):
        for w in range(WINDOW):
            ret, succ, steps, _s, _o = episode(actor, task, seed, fault=fault, repair=(a, w))
            queries += 1
            cells.append({"agent": a, "window": w, "return": ret, "success": succ})
            ok = (bool(succ) if task == "balance"
                  else bool(ret >= sem["Q50"] if sem else False))
            if ok:
                causal.append((a, w))
    return cells, causal, queries


def main() -> int:
    n_fail = 50
    pilot = 0
    for flag, cast in (("--failures", int), ("--pilot", int)):
        if flag in sys.argv:
            v = cast(sys.argv[sys.argv.index(flag) + 1])
            if flag == "--failures":
                n_fail = v
            else:
                pilot = v
    t0 = time.time()
    reg = Registry()
    out = {"targets": {"failures": n_fail, "window": WINDOW,
                       "probe_fractions": list(PROBE_FRACTIONS),
                       "fault_modalities": list(FAULT_MODALITIES)},
           "tasks": {}, "pilot": pilot}
    for task in TASKS:
        actor = load_actor(task)
        sem = semantics(task)
        rng = random.Random(20260921)
        made, attempted = [], 0
        t_task = time.time()
        while len(made) < (pilot or n_fail) and attempted < (pilot or n_fail) * 20:
            attempted += 1
            seed = SEED_BASE + attempted
            modality = rng.choice(FAULT_MODALITIES)
            agent = rng.randrange(N_AGENTS[task])
            # Fault strength calibrated BEFORE any attribution result: the first
            # (weaker) grid produced 0/8 valid failures on balance, whose clean
            # success is 87.6%, so severity/duration were widened and frozen here:
            # duration 20 steps, severities 0.5/0.8/1.0, window starts 20/40/60.
            sev = rng.choice([0.5, 0.8, 1.0])
            start = rng.choice([20, 40, 60])
            fault = Perturbation(modality, (agent,), start, start + 20, sev)
            with reg.unit(f"C_gen_{task}_{attempted}", "C", task, "fault_generation") as u:
                clean_ret, clean_succ, _s1, _a, _b = episode(actor, task, seed)
                f_ret, f_succ, _s2, _a2, _b2 = episode(actor, task, seed, fault=fault)
                ok = valid_failure(task, clean_ret, clean_succ, f_ret, f_succ, sem)
                if ok:
                    made.append({"seed": seed, "fault": fault.to_dict(),
                                 "clean_return": clean_ret, "fault_return": f_ret})
                    u.success({"valid": True}, sim_queries=2)
                else:
                    u.reject("not_a_valid_causal_failure", {"clean_return": clean_ret,
                                                            "fault_return": f_ret},
                             sim_queries=2)
        print(f"[{task}] valid failures collected: {len(made)} (attempted {attempted}) "
              f"{time.time()-t_task:.0f}s", flush=True)
        cases = []
        for i, f in enumerate(made):
            pert = Perturbation(f["fault"]["modality"], tuple(f["fault"]["agents"]),
                                f["fault"]["t_start"], f["fault"]["t_end"],
                                f["fault"]["severity"])
            with reg.unit(f"C_matrix_{task}_{i}", "C", task, "exhaustive_repair") as u:
                cells, causal, q = repair_matrix(actor, task, f["seed"], pert, sem)
                mind = min((abs(c["agent"] - causal[0][0]) + abs(c["window"] - causal[0][1])
                            for c in cells) for _ in [0]) if causal else None
                minimal = None
                if causal:
                    best = None
                    for a in range(N_AGENTS[task]):
                        for w in range(WINDOW):
                            if (a, w) in causal:
                                best = (a, w) if best is None else best
                    minimal = best
                cases.append({"seed": f["seed"], "fault": f["fault"], "cells": cells,
                              "causal_cells": [list(c) for c in causal],
                              "n_causal": len(causal), "minimal_repair": list(minimal) if minimal else None,
                              "repair_queries": q})
                u.success({"n_causal": len(causal)}, sim_queries=q)
            if (i + 1) % 5 == 0:
                print(f"  {task} matrix {i+1}/{len(made)} {time.time()-t_task:.0f}s", flush=True)
        # identifiable / ambiguity / sparsity
        if cases:
            ident = sum(1 for c in cases if 0 < c["n_causal"] <= 3) / len(cases)
            uniq = sum(1 for c in cases if c["n_causal"] == 1) / len(cases)
            mean_cell = sum(c["n_causal"] for c in cases) / len(cases)
        else:
            ident = uniq = mean_cell = None
        # budgeted probes on the matrix (queries reuse measured cells: no new episodes)
        probe_res = {}
        for frac in PROBE_FRACTIONS:
            for name, order_fn in (("RANDOM", lambda cells, r: sorted(
                                        cells, key=lambda c: r.random())),
                                   ("TEMPORAL_BINARY", lambda cells, r: sorted(
                                        cells, key=lambda c: (c["window"] != WINDOW // 2, c["window"]))),
                                   ("AGENT_FIRST", lambda cells, r: sorted(
                                        cells, key=lambda c: (c["agent"], c["window"]))),
                                   ("INFLUENCE", lambda cells, r: sorted(
                                        cells, key=lambda c: c["return"]))):
                hit, tot = 0, 0
                for ci, c in enumerate(cases):
                    r = random.Random(ci)
                    k = max(1, int(frac * len(c["cells"])))
                    q = order_fn(c["cells"], r)[:k]
                    tot += 1
                    if any((q2["agent"], q2["window"]) in [tuple(x) for x in c["causal_cells"]]
                           for q2 in q):
                        hit += 1
                probe_res[f"{name}@{int(frac*100)}pct"] = {"top1_hit_rate": hit / max(1, tot),
                                                           "n": tot}
        out["tasks"][task] = {"valid_failures": len(made), "attempted": attempted,
                              "identifiable_fraction_le3cells": ident,
                              "unique_fraction": uniq,
                              "mean_causal_cells": mean_cell,
                              "probes": probe_res, "cases": cases}
        (PA / "raw" / f"track_c_{task}.json").write_text(
            json.dumps(out["tasks"][task], indent=1, default=str))
        # --- cost estimate for the large run (v3.1 cost rule)
        per_case_s = (time.time() - t_task) / max(1, len(made))
        targets = {"calibration_50": 50, "large_run_200": 200}
        out["cost_estimate_per_task_seconds"] = {k: round(v * per_case_s) for k, v in targets.items()}
        print(f"[{task}] ident={ident} unique={uniq} mean_cells={mean_cell} "
              f"per_case={per_case_s:.1f}s", flush=True)
    rec = reg.reconcile()
    out["registry"] = rec
    out["wall_seconds"] = round(time.time() - t0, 1)
    out["large_run_estimate_seconds_both_tasks"] = (
        2 * out.get("cost_estimate_per_task_seconds", {}).get("large_run_200", 0))
    (PA / "metrics" / "track_c.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({t: {k: v for k, v in d.items() if k in
                          ("valid_failures", "identifiable_fraction_le3cells",
                           "unique_fraction", "mean_causal_cells")}
                      for t, d in out["tasks"].items()}, indent=1))
    print(f"large-run estimate (both tasks): {out['large_run_estimate_seconds_both_tasks']}s; "
          f"reconcile ok={rec['ok']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
