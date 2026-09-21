"""A0.3 clean baseline + frozen-checkpoint selection.

Step 1: 100 clean episodes per seed (0,1,2) per task -> pick the MEDIAN seed by mean
        return (never the best; plan §11.4).
Step 2: 500 clean episodes on the median seed per task -> clean distribution,
        native success rate, and the fallback return threshold if needed.
Self-check: my reconstructed actor vs the training run's own evaluation series.

    .venv_phase_a/bin/python research/phase_a/scripts/eval_clean.py
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path

import torch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase_a_common import (MAX_STEPS, N_AGENTS, PA, TASKS, FrozenActor,  # noqa: E402
                            checkpoint_for, make_task_env, native_success)

RAW = PA / "raw" / "track_common"
RAW.mkdir(parents=True, exist_ok=True)
FIELDS = ["task", "checkpoint", "checkpoint_seed", "episode_idx", "episode_seed",
          "return", "success", "length", "status", "error"]


def env_done_success(task: str, env, terminated: bool) -> bool:
    """Native success from the SCENARIO'S OWN done() definition.

    navigation: done() fires when every agent is within `agent.shape.radius` of its
                goal -> that IS task completion.  This VMAS build does not credit
                `final_rew`/`all_goal_reached` in that case (verified: at t=44 all
                four distances 0.043/0.026/0.067/0.084 < radius 0.1 while
                all_goal_reached was False), so the engine's own termination is used.
    balance:    done() = on_the_ground + overlap(package, goal) -> success requires
                termination WITHOUT the package on the ground.
    """
    if not terminated:
        return False
    if task == "navigation":
        return True
    if task == "balance":
        og = env.scenario.on_the_ground
        return not bool(torch.as_tensor(og).any())
    raise ValueError(task)


def run_episode(actor: FrozenActor, task: str, episode_seed: int, max_steps=MAX_STEPS):
    env = make_task_env(task, num_envs=1, seed=episode_seed)
    obs = env.reset(seed=episode_seed)
    total = 0.0
    steps = 0
    terminated = False
    while steps < max_steps:
        actions = actor.act(obs)
        obs, rew, dones, infos = env.step(actions)
        total += float(sum(float(r.sum()) for r in rew))
        steps += 1
        if bool(torch.as_tensor(dones).any()):
            terminated = not bool(torch.as_tensor(env.terminated_truncated).any())
            break
    return {"return": total, "steps": steps,
            "success": env_done_success(task, env, terminated)}


def main() -> int:
    rows, sel, wall0 = [], {}, time.time()
    for task in TASKS:
        per_seed = {}
        for seed in (0, 1, 2):
            try:
                ck = checkpoint_for(task, seed)
                actor = FrozenActor(ck)
            except Exception as exc:
                rows.append({"task": task, "checkpoint": "", "checkpoint_seed": seed,
                             "episode_idx": -1, "episode_seed": -1, "return": "",
                             "success": "", "length": "", "status": "REJECTED_NO_CHECKPOINT",
                             "error": f"{type(exc).__name__}: {exc}"})
                continue
            rets, succ, t0 = [], 0, time.time()
            for e in range(100):
                try:
                    r = run_episode(actor, task, episode_seed=1000 * seed + e)
                    rets.append(r["return"]); succ += int(r["success"])
                except Exception as exc:
                    rows.append({"task": task, "checkpoint": ck.name,
                                 "checkpoint_seed": seed, "episode_idx": e,
                                 "episode_seed": 1000 * seed + e, "return": "",
                                 "success": "", "length": "", "status": "ERROR_WITH_TRACE",
                                 "error": f"{type(exc).__name__}: {exc}"})
            per_seed[seed] = {"mean_return": sum(rets) / max(1, len(rets)),
                              "success_rate": succ / max(1, len(rets)),
                              "n": len(rets), "wall_seconds": round(time.time() - t0, 1),
                              "checkpoint": str(ck)}
            print(f"  {task} s{seed}: mean_return={per_seed[seed]['mean_return']:.3f} "
                  f"success={per_seed[seed]['success_rate']:.2f} n={len(rets)}", flush=True)
        order = sorted(per_seed, key=lambda s: per_seed[s]["mean_return"])
        median_seed = order[len(order) // 2]
        sel[task] = {"per_seed": per_seed, "median_seed": median_seed,
                     "selection_rule": "median mean_return across seeds 0,1,2"}

        # Step 2: 500 clean episodes on the median seed
        ck = Path(per_seed[median_seed]["checkpoint"])
        actor = FrozenActor(ck)
        for e in range(500):
            eseed = 5000 + e
            try:
                r = run_episode(actor, task, episode_seed=eseed)
                rows.append({"task": task, "checkpoint": ck.name,
                             "checkpoint_seed": median_seed, "episode_idx": e,
                             "episode_seed": eseed, "return": r["return"],
                             "success": int(r["success"]), "length": r["steps"],
                             "status": "SUCCESS", "error": ""})
            except Exception as exc:
                rows.append({"task": task, "checkpoint": ck.name,
                             "checkpoint_seed": median_seed, "episode_idx": e,
                             "episode_seed": eseed, "return": "", "success": "",
                             "length": "", "status": "ERROR_WITH_TRACE",
                             "error": f"{type(exc).__name__}: {exc}"})
            if (e + 1) % 100 == 0:
                print(f"  {task} clean {e+1}/500", flush=True)

    with open(RAW / "clean_baseline.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    summary = {}
    for task in TASKS:
        rr = [float(r["return"]) for r in rows
              if r["task"] == task and r["status"] == "SUCCESS" and r["episode_idx"] >= 0
              and r["checkpoint_seed"] == sel[task]["median_seed"]]
        ss = [int(r["success"]) for r in rows
              if r["task"] == task and r["status"] == "SUCCESS" and r["episode_idx"] >= 0
              and r["checkpoint_seed"] == sel[task]["median_seed"]]
        rr_sorted = sorted(rr)
        q25 = rr_sorted[int(0.25 * (len(rr_sorted) - 1))] if rr_sorted else None
        summary[task] = {
            "n_clean_episodes": len(rr),
            "mean_return": (sum(rr) / len(rr)) if rr else None,
            "std_return": (torch.tensor(rr).std(unbiased=True).item() if len(rr) > 1 else None),
            "success_rate": (sum(ss) / len(ss)) if ss else None,
            "return_p25": q25,
            "errors": sum(1 for r in rows if r["task"] == task and r["status"] == "ERROR_WITH_TRACE"),
            "rejected": sum(1 for r in rows if r["task"] == task and r["status"].startswith("REJECTED")),
            "median_seed": sel[task]["median_seed"],
        }
        s = summary[task]
        if s["success_rate"] is not None and s["success_rate"] >= 0.95:
            summary[task]["saturation_flag"] = "SATURATED_GE_95PCT"
        elif s["success_rate"] is not None and s["success_rate"] <= 0.05:
            summary[task]["saturation_flag"] = "USELESS_LE_5PCT"
        else:
            summary[task]["saturation_flag"] = "OK"
    (RAW / "checkpoint_selection.json").write_text(json.dumps(
        {"selection": sel, "clean_summary": summary,
         "wall_seconds": round(time.time() - wall0, 1)}, indent=1, default=str))
    print(json.dumps(summary, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
