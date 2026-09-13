"""Parallel dispatcher for the frozen v14 solver jobs.

The frozen design fixes the jobs; this script only changes *how many* of them
run at once.  Every job is the identical entry point the serial runner uses
(``python -m research.experiments.v14_run --worker solve ...`` with the same
``--limit``), results are written to the same deterministic per-job paths, and
the dispatcher skips any job whose result file already exists.  It therefore
cooperates with the official serial pipeline instead of replacing it: the
serial runner re-reads existing results, so whichever process gets there first
is irrelevant to the science.

Usage:
  python -m research.experiments.v14_dispatch --phase development --workers 6
  python -m research.experiments.v14_dispatch --phase test --workers 6

Safety: each solver process peaks near 0.55 GB, so the default worker count is
bounded by a memory budget rather than by core count, and the script refuses to
exceed it.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "backend" / "src"))

from research.experiments.v14_setup import ROOT, save  # noqa: E402
from research.experiments.v14_run import (  # noqa: E402
    directory, result_path, stamp,
)


MEM_PER_WORKER_GB = 1.2          # measured peak ~0.55 GB, with headroom


def missing_jobs(phase: str) -> list[tuple[dict, str, str, int]]:
    design = json.loads((ROOT / "DESIGN.json").read_text())
    cells = [c for c in design["cells"] if phase in c["phases"]]
    jobs: list[tuple[dict, str, str, int]] = []
    for c in cells:
        full = 2 ** (c["T"] - 1) - 1
        masks = [full, 0] + [m for m in range(1, full)]
        sides = ["blue"] + (["red"] if c.get("mirror_solve_all") else [])
        for side in sides:
            for k in c["opponents"]:
                for mask in masks:
                    if not result_path(c, side, k, mask).exists():
                        jobs.append((c, side, k, mask))
    return jobs


def ensure_payoff(cell: dict, env: dict) -> None:
    out = directory(cell)
    out.mkdir(parents=True, exist_ok=True)
    if (out / "payoff.json").exists():
        return
    log = out / "worker.log"
    subprocess.run([sys.executable, "-u", "-m", "research.experiments.v14_run",
                    "--worker", "payoff", "--cell", cell["id"]],
                   cwd=str(REPO), env=env,
                   stdout=open(log, "a"), stderr=subprocess.STDOUT, check=False)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True,
                    choices=["development", "test", "robustness", "ablation"])
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--memory-gb", type=float, default=12.0)
    ap.add_argument("--max-jobs", type=int, default=0,
                    help="stop after this many jobs (0 = all missing)")
    a = ap.parse_args()

    max_workers = max(1, int(a.memory_gb // MEM_PER_WORKER_GB))
    workers = min(a.workers, max_workers)
    print(f"[dispatch] phase={a.phase} workers={workers} "
          f"(memory cap {a.memory_gb} GB / {MEM_PER_WORKER_GB} GB per worker)",
          flush=True)

    env = os.environ.copy()
    env.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1",
               VECLIB_MAXIMUM_THREADS="1")

    jobs = missing_jobs(a.phase)
    if a.max_jobs:
        jobs = jobs[:a.max_jobs]
    print(f"[dispatch] {len(jobs)} missing jobs", flush=True)
    if not jobs:
        return

    # payoff precomputation is per cell and shared by many solves
    seen: set[str] = set()
    for c, *_ in jobs:
        if c["id"] not in seen:
            seen.add(c["id"])
            ensure_payoff(c, env)
    print(f"[dispatch] payoff ready for {len(seen)} cells", flush=True)

    t0 = time.time()
    done = 0
    running: list[tuple[subprocess.Popen, tuple]] = []
    queue = list(jobs)
    while queue or running:
        while queue and len(running) < workers:
            c, side, k, mask = queue.pop(0)
            log = directory(c) / "worker.log"
            p = subprocess.Popen(
                [sys.executable, "-u", "-m", "research.experiments.v14_run",
                 "--worker", "solve", "--cell", c["id"], "--side", side,
                 "--opponent", k, "--mask", str(mask), "--limit", "1200"],
                cwd=str(REPO), env=env, stdout=open(log, "a"),
                stderr=subprocess.STDOUT, start_new_session=True)
            running.append((p, (c, side, k, mask)))
        time.sleep(1.0)
        still = []
        for p, job in running:
            if p.poll() is None:
                still.append((p, job))
                continue
            c, side, k, mask = job
            ok = result_path(c, side, k, mask).exists()
            done += 1
            if not ok:
                print(f"[dispatch] worker produced no result: {c['id']} "
                      f"{side} {k} mask={mask} rc={p.returncode}", flush=True)
            if done % 20 == 0 or done == len(jobs):
                el = time.time() - t0
                eta = el * (len(jobs) - done) / max(done, 1)
                print(f"[dispatch] {done}/{len(jobs)} "
                      f"elapsed={time.strftime('%H:%M:%S', time.gmtime(el))} "
                      f"eta={time.strftime('%H:%M:%S', time.gmtime(eta))}",
                      flush=True)
                save(ROOT / "DISPATCH_PROGRESS.json",
                     {"phase": a.phase, "done": done, "total": len(jobs),
                      "workers": workers, "updated_utc": stamp()})
        running = still
    print(f"[dispatch] complete: {done} jobs in "
          f"{time.strftime('%H:%M:%S', time.gmtime(time.time() - t0))}", flush=True)


if __name__ == "__main__":
    main()
