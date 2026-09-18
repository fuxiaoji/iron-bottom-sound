"""P0.3 minimal baseline: determinism, auto-termination, timing, throughput.

Read-only with respect to the engine: it never writes into the repository's
production paths (artifact_dir=None, battle_report=False).

Run:
    PYTHONPATH=backend/src .venv/bin/python research/m0/p0_baseline.py --out research/m0/logs
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))

from iron_bottom_sound.models import GameOptions  # noqa: E402
from iron_bottom_sound.match import run_match  # noqa: E402


def _fingerprint(report, state) -> dict:
    """A stable signature of a finished match, for determinism comparison."""
    events = getattr(state, "events", []) or []
    ev_sig = [
        (e.turn, str(getattr(e, "kind", "")), str(getattr(e, "message", ""))[:80])
        for e in events
    ]
    return {
        "turns": getattr(state, "turn", None),
        "phase": str(getattr(state, "phase", None)),
        "score": dict(getattr(state, "score", {}) or {}),
        "n_events": len(events),
        "winner": str(getattr(report, "winner", None)),
        "completed": bool(getattr(report, "completed", False)),
        "passed": bool(getattr(report, "passed", False)),
        "axis_plans": int(getattr(report, "axis_plan_count", 0)),
        "allies_plans": int(getattr(report, "allies_plan_count", 0)),
        "events_digest": abs(hash(repr(ev_sig))) % (10**12),
    }


def one_match(scenario_id: str, seed: int, axis_profile: str, allies_profile: str,
              realistic: bool = False) -> dict:
    t0 = time.perf_counter()
    options = GameOptions(mode="llm")
    if realistic:
        options = GameOptions(mode="llm", realistic_command=True)
    err = None
    fp: dict = {}
    try:
        report, engine, _sessions = run_match(
            scenario_id,
            axis="tactical", allies="tactical",
            axis_profile=axis_profile, allies_profile=allies_profile,
            seed=seed, options=options,
            artifact_dir=None, battle_report=False,
        )
        state = engine.get(report.game_id)
        fp = _fingerprint(report, state)
    except Exception as exc:  # noqa: BLE001 - we must record, not hide, failures
        err = f"{type(exc).__name__}: {exc}"
    dt = time.perf_counter() - t0
    return {"scenario_id": scenario_id, "seed": seed,
            "axis_profile": axis_profile, "allies_profile": allies_profile,
            "realistic": realistic, "seconds": dt, "error": err, **fp}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="research/m0/logs")
    ap.add_argument("--throughput-scenario", default="IBS-S-01")
    ap.add_argument("--throughput-n", type=int, default=20)
    ap.add_argument("--throughput-workers", type=int, default=20)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    log_lines: list[str] = []
    result: dict = {"env": {}, "determinism": [], "termination": [],
                    "timing": {}, "throughput": {}, "failures": []}

    def log(msg: str) -> None:
        print(msg, flush=True)
        log_lines.append(msg)

    import os
    result["env"] = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version.split()[0],
        "cpu_count": os.cpu_count(),
        "executable": sys.executable,
    }
    log(f"ENV {json.dumps(result['env'])}")

    # ---- 1. determinism: identical config twice -----------------------------
    log("\n=== 1. DETERMINISM (same seed + same policy, repeated) ===")
    det_cases = [
        ("IBS-S-01", 1, "balanced", "balanced"),
        ("IBS-S-01", 1, "torpedo", "cautious"),
        ("IBS-S-03", 7, "adaptive", "line"),
        ("IBS-S-03", 7, "adaptive", "line"),
    ]
    det_runs = []
    for scenario, seed, ap_, lp in det_cases:
        r = one_match(scenario, seed, ap_, lp)
        det_runs.append(r)
        log(f"  {scenario} seed={seed} {ap_} vs {lp}: turns={r.get('turns')} "
            f"score={r.get('score')} n_events={r.get('n_events')} "
            f"digest={r.get('events_digest')} err={r.get('error')} "
            f"({r['seconds']:.2f}s)")
    result["determinism"] = det_runs

    # pair (0,1) differs by profiles -> should DIFFER; pair (2,3) identical -> must MATCH
    def same(a, b):
        keys = ("turns", "score", "n_events", "events_digest", "winner", "completed")
        return all(a.get(k) == b.get(k) for k in keys)

    pair_same = same(det_runs[2], det_runs[3]) if len(det_runs) == 4 else None
    log(f"  -> identical-config repeat matched: {pair_same}")
    result["determinism_identical_repeat_matched"] = pair_same

    # ---- 2. auto-termination across representative scenarios ----------------
    log("\n=== 2. AUTO-TERMINATION ===")
    scen = ["IBS-S-01", "IBS-S-02", "IBS-S-03", "IBS-S-EM-01", "IBS-S-14"]
    for s in scen:
        r = one_match(s, 1, "balanced", "balanced")
        result["termination"].append(r)
        status = "COMPLETE" if r.get("phase") == "complete" and not r.get("error") else "NOT_COMPLETE"
        log(f"  {s}: {status} turns={r.get('turns')} winner={r.get('winner')} "
            f"n_events={r.get('n_events')} ({r['seconds']:.2f}s) err={r.get('error')}")
        if r.get("error"):
            result["failures"].append({"stage": "termination", **r})

    # ---- 3. realistic-command mode -----------------------------------------
    log("\n=== 3. REALISTIC-COMMAND MODE ===")
    for s in ["IBS-S-01", "IBS-S-03"]:
        r = one_match(s, 1, "balanced", "balanced", realistic=True)
        result["termination"].append(r)
        log(f"  {s} (realistic): turns={r.get('turns')} winner={r.get('winner')} "
            f"phase={r.get('phase')} ({r['seconds']:.2f}s) err={r.get('error')}")
        if r.get("error"):
            result["failures"].append({"stage": "realistic", **r})

    # ---- 4. timing ----------------------------------------------------------
    log("\n=== 4. TIMING (per match, seconds) ===")
    times = [r["seconds"] for r in result["termination"] if not r.get("error")]
    if times:
        result["timing"] = {
            "n": len(times), "mean": statistics.mean(times),
            "median": statistics.median(times), "min": min(times), "max": max(times),
        }
        log(f"  n={len(times)} mean={statistics.mean(times):.2f}s "
            f"median={statistics.median(times):.2f}s max={max(times):.2f}s")

    # ---- 5. throughput ------------------------------------------------------
    log(f"\n=== 5. THROUGHPUT ({args.throughput_workers} workers, {args.throughput_scenario}) ===")
    try:
        jobs = [(args.throughput_scenario, 1000 + i, "balanced", "balanced") for i in range(args.throughput_n)]
        t0 = time.perf_counter()
        with ProcessPoolExecutor(max_workers=args.throughput_workers) as ex:
            rows = list(ex.map(_throughput_worker, jobs))
        wall = time.perf_counter() - t0
        errs = [r for r in rows if r.get("error")]
        result["throughput"] = {
            "n": len(rows), "wall_seconds": wall,
            "matches_per_second": len(rows) / wall if wall > 0 else None,
            "workers": args.throughput_workers,
            "errors": len(errs),
        }
        log(f"  {len(rows)} matches in {wall:.1f}s -> {len(rows)/wall:.2f} matches/s, errors={len(errs)}")
        if errs:
            result["failures"].append({"stage": "throughput", "errors": errs[:5]})
    except Exception as exc:  # noqa: BLE001
        log(f"  THROUGHPUT FAILED: {type(exc).__name__}: {exc}")
        result["failures"].append({"stage": "throughput", "error": str(exc)})

    (out / "p0_baseline.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
    log(f"\nwrote {out/'p0_baseline.json'}")
    (out / "p0_baseline.txt").write_text("\n".join(log_lines))
    return 0


def _throughput_worker(job):
    scenario, seed, ap_, lp = job
    return one_match(scenario, seed, ap_, lp)


if __name__ == "__main__":
    raise SystemExit(main())
