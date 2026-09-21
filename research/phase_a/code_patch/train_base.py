"""Phase A base-policy training launcher (A0.2).

Frozen: MAPPO via BenchMARL, 3 seeds per task, identical frame budget, CPU device.
Emits one registry row per attempt (red line 1: no silent drops; red line 2: no
swallowed exceptions — an error row carries the traceback tail).

    .venv_phase_a/bin/python research/phase_a/scripts/train_base.py
"""

from __future__ import annotations

import csv
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PA = REPO / "research" / "phase_a"
RUNNER = REPO / ".venv_phase_a" / "lib" / "python3.9" / "site-packages" / "benchmarl" / "run.py"
PY = REPO / ".venv_phase_a" / "bin" / "python"

TASKS = ("navigation", "balance")
SEEDS = (0, 1, 2)
FRAMES = 600_000                    # frozen budget (see PRE_REGISTRATION_PHASE_A.md)
CHECKPOINT_INTERVAL = 120_000
MAX_PARALLEL = 3

REGISTRY = PA / "raw" / "training_registry.csv"
FIELDS = ["run_id", "task", "seed", "frames", "status", "returncode",
          "wall_seconds", "log_path", "run_dir", "trace_tail"]


def run_one(task: str, seed: int) -> dict:
    run_id = f"mappo_{task}_s{seed}"
    run_dir = PA / "runs" / run_id
    log_path = PA / "logs" / f"{run_id}.log"
    run_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(PY), str(RUNNER),
        "algorithm=mappo", f"task=vmas/{task}", f"seed={seed}",
        f"experiment.max_n_frames={FRAMES}",
        "experiment.loggers=[csv]",
        "experiment.train_device=cpu",
        "experiment.sampling_device=cpu",
        "experiment.render=False",
        f"experiment.checkpoint_interval={CHECKPOINT_INTERVAL}",
        "experiment.checkpoint_at_end=True",
        f"hydra.run.dir={run_dir}",
    ]
    env = dict(os.environ)
    env["OMP_NUM_THREADS"] = "3"
    env["MKL_NUM_THREADS"] = "3"
    t0 = time.time()
    with open(log_path, "w") as fh:
        proc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, env=env, cwd=REPO)
    wall = time.time() - t0
    trace = ""
    status = "SUCCESS" if proc.returncode == 0 else "ERROR_WITH_TRACE"
    if proc.returncode != 0:
        tail = log_path.read_text(errors="replace").splitlines()[-20:]
        trace = " | ".join(tail)
    # bug fix (BUG_AND_RERUN_LOG v1): the checkpoints live under
    # run_dir/<config-hash-dir>/checkpoints/, not run_dir/<run_id>/, so the first
    # version reported REJECTED_NO_CHECKPOINT for successful runs.
    has_ckpt = any(run_dir.rglob("checkpoint_*.pt"))
    if status == "SUCCESS" and not has_ckpt:
        status = "REJECTED_NO_CHECKPOINT"
    return {"run_id": run_id, "task": task, "seed": seed, "frames": FRAMES,
            "status": status, "returncode": proc.returncode,
            "wall_seconds": round(wall, 1), "log_path": str(log_path.relative_to(REPO)),
            "run_dir": str(run_dir.relative_to(REPO)), "trace_tail": trace}


def main() -> int:
    rows: list[dict] = []
    with open(REGISTRY, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        fh.flush()
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
            futures = [pool.submit(run_one, t, s) for t in TASKS for s in SEEDS]
            for fut in futures:
                row = fut.result()
                writer.writerow(row)
                fh.flush()
                rows.append(row)
                print(f"  {row['run_id']}: {row['status']} rc={row['returncode']} "
                      f"{row['wall_seconds']}s", flush=True)
    ok = sum(1 for r in rows if r["status"] == "SUCCESS")
    print(f"training registry: {len(rows)} attempted, {ok} SUCCESS -> {REGISTRY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
