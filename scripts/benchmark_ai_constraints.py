"""Isolated continuation batches: former failures, development or fresh holdout.

Never imports the API or player storage. Keep old reports immutable. Failed
games remain invalid attempts and exclude their whole matched pair.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from iron_bottom_sound.data import load_scenario
from iron_bottom_sound.tactical import PROFILES
from benchmark_weak_side import ROOT, frozen_inputs, play, summarize, valid


def register(mode, pairs):
    if mode == "development":
        sides, start = [("IBS-S-05", "axis")], 2401
    else:
        sides, start = [("IBS-S-02", "allies"), ("IBS-S-05", "axis"), ("IBS-S-10", "allies")], 3001
    return [{"id": scenario, "title": load_scenario(scenario)["title"], "weak_side": side,
             "seeds": list(range(start + index * 100, start + index * 100 + pairs)),
             "definition": load_scenario(scenario)} for index, (scenario, side) in enumerate(sides)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["former-failures", "development", "holdout"], required=True)
    parser.add_argument("--pairs", type=int, default=30)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--old-report", type=Path, default=Path("artifacts/realistic-ai/weak-side-frozen-720.json"))
    args = parser.parse_args()
    if args.output.exists() or args.output.with_suffix(".jsonl").exists():
        parser.error("Fresh output required; existing evidence cannot be overwritten")
    if not 1 <= args.pairs <= 100 or args.workers < 1:
        parser.error("pairs must be 1..100; workers must be positive")
    hashes = frozen_inputs()
    hashes[Path(__file__).relative_to(ROOT).as_posix()] = sha256(Path(__file__).read_bytes()).hexdigest()
    cases = register(args.mode, args.pairs)
    if args.mode == "former-failures":
        old = json.loads(args.old_report.read_text(encoding="utf-8"))
        tasks = [(row["scenario"], row["side"], row["seed"], row["arm"], hashes)
                 for row in old["games"] if not valid(row)]
        old_hash = sha256(args.old_report.read_bytes()).hexdigest()
    else:
        tasks = [(case["id"], case["weak_side"], seed, arm, hashes)
                 for case in cases for seed in case["seeds"] for arm in ("baseline", "new")]
        old_hash = None
    metadata = {
        "registered_at_utc": datetime.now(timezone.utc).isoformat(), "mode": args.mode,
        "cases": cases if args.mode != "former-failures" else [],
        "registered_jobs": [{"scenario": scenario, "side": side, "seed": seed, "arm": arm}
                            for scenario, side, seed, arm, _ in tasks],
        "source_hashes": hashes, "old_report_sha256": old_hash,
        "profile_parameters": {key: PROFILES[key].model_dump() for key in ("balanced", "rc_coordinated")},
        "scope": "Shared legality repairs; no scenario values, victory conditions or player saves changed",
        "statistical_unit": "same scenario, fixed weak side, same initial seed; paired binary wins",
        "gate": "30 valid pairs, no invalid games, positive wins, Holm p<0.05 over this fixed three-case family",
        "caution": "Development/former-failures are not holdout strength evidence; S-02 source adjacency remains partial",
    }
    rows = []
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        summary = summarize(rows, cases) if args.mode != "former-failures" else {
            "planned_games": len(tasks), "attempted_games": len(rows),
            "valid_complete_replays": sum(valid(row) for row in rows),
            "invalid_games": [row for row in rows if not valid(row)],
        }
        args.output.write_text(json.dumps({"metadata": metadata, "summary": summary, "games": rows},
                                         ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    save()
    with args.output.with_suffix(".jsonl").open("x", encoding="utf-8") as journal:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(play, task) for task in tasks]
            for future in as_completed(futures):
                row = future.result()
                rows.append(row)
                journal.write(json.dumps(row, ensure_ascii=False) + "\n")
                journal.flush()
                save()
                print(json.dumps({"done": len(rows), "total": len(tasks), "scenario": row["scenario"],
                                  "arm": row["arm"], "seed": row["seed"], "failure": row["failure"]}), flush=True)
    return int(any(not valid(row) for row in rows))


if __name__ == "__main__":
    raise SystemExit(main())
