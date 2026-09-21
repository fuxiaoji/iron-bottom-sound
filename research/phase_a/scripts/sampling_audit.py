"""Sampling policy audit (directive §"Sampling quality gate").

Completes the frozen protocol for the replacement task: median validation
checkpoint, 500 clean episodes, 500 random-action episodes, frozen quantiles
written into ENVIRONMENT_LOCK.json, and the four-condition quality gate.

    .venv_phase_a/bin/python research/phase_a/scripts/sampling_audit.py
"""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hardened import Registry, bootstrap_ci_mean, cohens_d, quantiles  # noqa: E402
from phase_a_common import FrozenActor, make_task_env  # noqa: E402

PA = Path(__file__).resolve().parents[1]
TASK = "sampling"
MAX_STEPS = 100
OUT = PA / "raw" / "track_common" / "sampling_audit.csv"
FIELDS = ["task", "mode", "checkpoint_seed", "episode_idx", "episode_seed",
          "return", "length", "status"]


def run_episode(actor, task, seed, random_actions=False, max_steps=MAX_STEPS):
    env = make_task_env(task, 1, seed=seed)
    obs = env.reset(seed=seed)
    total, steps = 0.0, 0
    while steps < max_steps:
        if random_actions:
            acts = env.get_random_actions()
        else:
            acts = actor.act(obs)
        obs, rew, dones, infos = env.step(acts)
        total += float(sum(float(r.sum()) for r in rew))
        steps += 1
        if bool(torch.as_tensor(dones).any()):
            break
    return {"return": total, "steps": steps}


def main() -> int:
    t0 = time.time()
    reg = Registry()
    rows = []
    sel_path = PA / "raw" / "track_common" / "checkpoint_selection.json"
    sel = json.loads(sel_path.read_text()) if sel_path.exists() else {"selection": {}}

    # 1. validation pass over the three seeds (100 episodes each) -> median seed
    per_seed = {}
    for seed in (0, 1, 2):
        ck = sorted((PA / "runs" / f"mappo_{TASK}_s{seed}").rglob("checkpoint_600000.pt"))
        if not ck:
            with reg.unit(f"sampling_val_s{seed}", "A0", TASK, "frozen_policy") as u:
                u.reject("checkpoint_600000.pt missing")
            continue
        actor = FrozenActor(ck[-1])
        rets = []
        for e in range(100):
            with reg.unit(f"sampling_val_s{seed}_e{e}", "A0", TASK, "frozen_policy") as u:
                r = run_episode(actor, TASK, 1000 * seed + e)
                rets.append(r["return"])
                u.success({"return": r["return"], "length": r["steps"]},
                          sim_steps=r["steps"])
        per_seed[seed] = {"mean_return": sum(rets) / len(rets), "n": len(rets),
                          "checkpoint": str(ck[-1])}
        print(f"  sampling s{seed}: mean_return={per_seed[seed]['mean_return']:.3f}", flush=True)
    order = sorted(per_seed, key=lambda s: per_seed[s]["mean_return"])
    median_seed = order[len(order) // 2]
    actor = FrozenActor(Path(per_seed[median_seed]["checkpoint"]))
    print(f"  median seed = {median_seed}")

    # 2. 500 clean + 500 random episodes on the median checkpoint
    for mode, random_actions in (("clean", False), ("random", True)):
        for e in range(500):
            seed = 5000 + e
            with reg.unit(f"sampling_{mode}_e{e}", "A0", TASK,
                          "frozen_policy" if mode == "clean" else "random_policy") as u:
                r = run_episode(actor, TASK, seed, random_actions=random_actions)
                rows.append({"task": TASK, "mode": mode, "checkpoint_seed": median_seed,
                             "episode_idx": e, "episode_seed": seed,
                             "return": r["return"], "length": r["steps"],
                             "status": "SUCCESS"})
                u.success({"return": r["return"]}, sim_steps=r["steps"])
        print(f"  {mode} done", flush=True)

    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    clean = [r["return"] for r in rows if r["mode"] == "clean"]
    rand = [r["return"] for r in rows if r["mode"] == "random"]
    q = quantiles(clean)
    ci = bootstrap_ci_mean([c - r for c, r in zip(clean, rand)])
    d = cohens_d(clean, rand)
    err = sum(1 for r in rows if r["status"] != "SUCCESS")
    err_rate = err / max(1, len(rows))
    gate = {
        "1_trained_gt_random": q["mean"] > (sum(rand) / len(rand)),
        "2_bootstrap_ci_excludes_0": ci is not None and ci[0] > 0,
        "3_standardised_effect_ge_0.5": d is not None and d >= 0.5,
        "4_error_rate_le_1pct": err_rate <= 0.01,
    }
    verdict = "PASS" if all(gate.values()) else "FAIL"
    block = {"task": TASK, "median_seed": median_seed,
             "per_seed": per_seed, "clean": q,
             "random_mean_return": sum(rand) / len(rand),
             "mean_difference": q["mean"] - sum(rand) / len(rand),
             "bootstrap_ci_mean_diff": ci, "cohens_d": d,
             "n_episodes": len(rows), "error_rate": err_rate,
             "quality_gate": gate, "status": verdict}
    (PA / "raw" / "track_common" / "sampling_quality_gate.json").write_text(
        json.dumps(block, indent=1))

    # 3. freeze the quantiles into ENVIRONMENT_LOCK.json
    lock_path = PA / "ENVIRONMENT_LOCK.json"
    lock = json.loads(lock_path.read_text())
    lock.setdefault("sampling_semantics", {})
    lock["sampling_semantics"] = {
        "quantiles_from": "500 clean episodes, median validation checkpoint",
        "clean_Q25": q["Q25"], "clean_Q50": q["Q50"], "clean_Q75": q["Q75"],
        "clean_IQR": q["IQR"], "clean_mean": q["mean"],
        "random_mean": sum(rand) / len(rand),
        "track_b_failure_definition": "episode_return < clean_Q25",
        "track_c_valid_failure_definition":
            "paired identical initial seed: clean_return >= clean_Q50 AND "
            "faulted_return < clean_Q25 AND clean_return - faulted_return >= 0.5*clean_IQR",
        "no_native_binary_success": True,
    }
    sel.setdefault("selection", {})[TASK] = {"per_seed": per_seed,
                                            "median_seed": median_seed,
                                            "selection_rule": "median mean_return across seeds 0,1,2"}
    sel_path.write_text(json.dumps(sel, indent=1, default=str))
    lock_path.write_text(json.dumps(lock, indent=1))

    rec = reg.reconcile()
    print(json.dumps({"quality_gate": gate, "status": verdict,
                      "clean": q, "random_mean": sum(rand) / len(rand),
                      "cohens_d": d, "reconcile_ok": rec["ok"],
                      "wall_seconds": round(time.time() - t0, 1)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
