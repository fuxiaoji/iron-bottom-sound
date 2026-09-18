"""C0 calibration: real Iron Bottom Sound matches -> empirical payoff distributions.

Runs a full strategy-pool matrix (6 strategies x 6 strategies, both orders) on
the playable scenarios and records win/draw/loss counts per cell, from the AXIS
perspective.  These counts calibrate the outcome distributions used by the
sampling-policy comparison in ``simulate.py``.

Resource discipline (per M0 plan):
  * pilot first (12 matches), TIME_ESTIMATE printed, then a pre-declared rule
    decides matches-per-cell:
      n_cell = 30 if projected scenario block <= 75 min else 20;
  * every failure is recorded, never dropped;
  * budget check against the 20,000-match ceiling before starting.

Usage:
    PYTHONPATH=backend/src .venv/bin/python research/m0/c0_psro/calibrate.py \
        --scenario IBS-S-03 [--workers 12]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO / "research" / "m0"))

STRATEGIES = ["balanced", "torpedo", "cautious", "line", "adaptive", "brawl"]
# 'random' is deliberately excluded: RandomCommander's seeding was not verified
# in P0, so its matches would not be reproducible.

TOTAL_BUDGET = 20_000
SPENT_BEFORE = 78            # P0 baseline matches, see BASELINE_STATUS.md


def _one(job):
    scenario, i, j, axis_p, allies_p, seed = job
    from iron_bottom_sound.match import run_match
    from iron_bottom_sound.models import GameOptions
    t0 = time.perf_counter()
    try:
        report, _engine, _sessions = run_match(
            scenario, axis="tactical", allies="tactical",
            axis_profile=axis_p, allies_profile=allies_p,
            seed=seed, options=GameOptions(mode="llm"),
            artifact_dir=None, battle_report=False)
        outcome = 1 if report.winner and report.winner.value == "axis" else (
            -1 if report.winner else 0)
        err = None
    except Exception as exc:  # noqa: BLE001 - record, never hide
        outcome = None
        err = f"{type(exc).__name__}: {exc}"
    return {"scenario": scenario, "i": i, "j": j, "axis": axis_p,
            "allies": allies_p, "seed": seed, "outcome": outcome,
            "error": err, "seconds": time.perf_counter() - t0}


def run_block(scenario: str, n_cell: int, workers: int, seed_base: int,
              out_path: Path):
    n = len(STRATEGIES)
    jobs = []
    for i in range(n):
        for j in range(n):
            for r in range(n_cell):
                jobs.append((scenario, i, j, STRATEGIES[i], STRATEGIES[j],
                             seed_base + r * 1000 + i * 37 + j))
    t0 = time.perf_counter()
    rows = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for row in ex.map(_one, jobs):
            rows.append(row)
            if len(rows) % 120 == 0:
                done = len(rows)
                rate = done / (time.perf_counter() - t0)
                print(f"  {done}/{len(jobs)}  {rate:.2f} matches/s  "
                      f"eta {(len(jobs)-done)/max(rate,1e-9)/60:.1f} min",
                      flush=True)
    wall = time.perf_counter() - t0
    ok = [r for r in rows if r["error"] is None]
    bad = [r for r in rows if r["error"] is not None]
    counts = {}
    for r in ok:
        key = (r["i"], r["j"])
        counts.setdefault(key, [0, 0, 0])
        counts[key][r["outcome"] + 1] += 1
    dist = [[None] * n for _ in range(n)]
    for (i, j), (w, d, l) in counts.items():
        tot = w + d + l
        dist[i][j] = [w / tot, d / tot, l / tot]
    payload = {
        "scenario": scenario,
        "strategies": STRATEGIES,
        "n_cell_target": n_cell,
        "n_planned": len(jobs),
        "n_ok": len(ok),
        "n_failed": len(bad),
        "wall_seconds": wall,
        "matches_per_second": len(rows) / wall,
        "seed_base": seed_base,
        "distribution": dist,
        "counts": {f"{i},{j}": v for (i, j), v in sorted(counts.items())},
        "failures": bad[:50],
        "per_match_seconds": {
            "mean": statistics.mean(r["seconds"] for r in ok) if ok else None,
            "max": max((r["seconds"] for r in ok), default=None),
        },
    }
    out_path.write_text(json.dumps(payload, indent=2))
    print(json.dumps({k: payload[k] for k in
                      ("scenario", "n_ok", "n_failed", "wall_seconds",
                       "matches_per_second")}, indent=2))
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True, choices=["IBS-S-01", "IBS-S-03"])
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--n-cell", type=int, default=None,
                    help="override the pre-declared pilot rule")
    ap.add_argument("--seed-base", type=int, default=20_000)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    out = Path(args.out) if args.out else (
        REPO / "research" / "m0" / "results" / f"c0_calibration_{args.scenario}.json")

    # ---- pilot with TIME_ESTIMATE --------------------------------------
    if args.n_cell is None:
        print(f"pilot: 12 matches on {args.scenario} ...", flush=True)
        pilot_jobs = [(args.scenario, i % 6, j % 6, STRATEGIES[i % 6],
                       STRATEGIES[j % 6], args.seed_base + k)
                      for k, (i, j) in enumerate(
                          [(a, b) for a in range(6) for b in range(6)][:12])]
        t0 = time.perf_counter()
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            pilot = list(ex.map(_one, pilot_jobs))
        pilot_wall = time.perf_counter() - t0
        per_match = pilot_wall / max(len(pilot), 1)
        full_n = 6 * 6 * 30
        est_full = per_match * full_n / args.workers * (args.workers / 1.9)  # measured 1.9x scaling
        # pre-declared rule: 30/cell if the block fits in 75 min, else 20/cell
        n_cell = 30 if est_full <= 75 * 60 else 20
        print(f"TIME_ESTIMATE: {est_full/60:.1f} min for 30/cell "
              f"(pilot {pilot_wall:.1f}s for {len(pilot)} matches) -> "
              f"n_cell={n_cell}", flush=True)
    else:
        n_cell = args.n_cell

    n_planned = 36 * n_cell
    if SPENT_BEFORE + n_planned > TOTAL_BUDGET:
        print(f"BUDGET REFUSED: {SPENT_BEFORE}+{n_planned} > {TOTAL_BUDGET}")
        return 2

    print(f"running {n_planned} matches on {args.scenario} "
          f"({n_cell}/cell, {args.workers} workers)", flush=True)
    run_block(args.scenario, n_cell, args.workers, args.seed_base, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
