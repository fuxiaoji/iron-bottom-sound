"""Recover only missing preregistered games from an interrupted weak-side run.

The append-only journal is authoritative. Existing games are never rerun or
discarded, and the original runner verifies all frozen code/data hashes.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil

from benchmark_weak_side import play, summarize


def missing_tasks(rows, metadata):
    summarize(rows, metadata["cases"])  # Reject duplicate/unregistered results.
    seen = {(row["scenario"], row["seed"], row["arm"]) for row in rows}
    return [(case["id"], case["weak_side"], seed, arm, metadata["source_hashes"])
            for case in metadata["cases"] for seed in case["seeds"] for arm in ("baseline", "new")
            if (case["id"], seed, arm) not in seen]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    document = json.loads(args.input.read_text(encoding="utf-8"))
    metadata = document["metadata"]
    journal = args.input.with_suffix(".jsonl")
    rows = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
    tasks = missing_tasks(rows, metadata)
    snapshot = args.input.with_name(args.input.stem + ".pre-resume.json")
    if snapshot.exists():
        parser.error("Recovery snapshot already exists; inspect state before another recovery")
    shutil.copyfile(args.input, snapshot)
    metadata.setdefault("resumptions", []).append({
        "utc": datetime.now(timezone.utc).isoformat(), "journal_games_before": len(rows),
        "missing_games": [{"scenario": task[0], "side": task[1], "seed": task[2], "arm": task[3]} for task in tasks],
        "resumer_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "policy": "same registered seed/side/arm and verified frozen source; no completed games rerun",
    })

    def save():
        rows.sort(key=lambda row: (row["scenario"], row["seed"], row["arm"]))
        args.input.write_text(json.dumps({"metadata": metadata, "summary": summarize(rows, metadata["cases"]),
                                         "games": rows}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    save()
    print(json.dumps({"recovered": len(rows), "missing": len(tasks)}), flush=True)
    with journal.open("a", encoding="utf-8") as stream, ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(play, task) for task in tasks]
        for future in as_completed(futures):
            row = future.result()
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            stream.flush()
            rows.append(row)
            save()
            print(json.dumps({"done": len(rows), "scenario": row["scenario"], "seed": row["seed"],
                              "arm": row["arm"], "failure": row["failure"]}), flush=True)
    print(json.dumps(summarize(rows, metadata["cases"])), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
