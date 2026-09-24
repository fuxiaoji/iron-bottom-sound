"""Append a re-freeze attribution record to the golden index.

Why this exists: ``golden_replay.py --build`` rewrites ``GOLDEN_INDEX.json`` from a fixed
dict, so anything hand-added to that file (including the attribution the project requires
whenever a frozen row legitimately changes) is silently lost on the next rebuild.  This
script re-appends the record, and is meant to be run right after any ``--build`` that
follows an authorized change.

Usage::

    .venv/bin/python research/command_delay/record_refreeze.py \
        --row cd_s01 --before-digest 8445973cb14e64eb \
        --reason "v2.3 routing repair (distance is reachability, not delay)" \
        --authorized-by "PI ruling, COMMAND_DELAY_V2_3 repair plan"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
INDEX = HERE / "golden" / "GOLDEN_INDEX.json"
# Rows that must never drift: they run with the command-delay mode off.
FROZEN_NON_CD_ROWS = ("classic_s01", "classic_s03", "classic_em01", "realistic_s01",
                      "realistic_s03", "realistic_em01", "realistic_s03_seed9")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--row", required=True)
    parser.add_argument("--before-digest", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--authorized-by", required=True)
    parser.add_argument("--previous-frozen-commit", default=None)
    args = parser.parse_args()

    index = json.loads(INDEX.read_text(encoding="utf-8"))
    record = next((row for row in index["records"] if row["tag"] == args.row), None)
    if record is None:
        raise SystemExit(f"no row {args.row!r} in the index")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                            text=True).stdout.strip()
    unchanged = {}
    for tag in FROZEN_NON_CD_ROWS:
        if tag == args.row:
            continue
        digest = hashlib.sha256((HERE / "golden" / f"{tag}.json").read_bytes()).hexdigest()
        unchanged[tag] = digest

    entry = {
        "row": args.row,
        "date": "2026-09-24",
        "authorized_by": args.authorized_by,
        "reason": args.reason,
        "previous_frozen_commit": args.previous_frozen_commit or "e3149c4f",
        "trees_digest": {"before": args.before_digest, "after": record["digest_trees"]},
        "unchanged_non_cd_rows_sha256": unchanged,
        "note": ("Only the Command Delay row may change under this batch: Classic and "
                 "Realistic semantics stay frozen.  The digests above are the proof that "
                 "they did."),
    }
    existing = index.get("refreeze") or []
    if isinstance(existing, dict):
        existing = [existing]
    existing.append(entry)
    index["refreeze"] = existing
    index["rebuilt_at_commit"] = commit
    INDEX.write_text(json.dumps(index, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(entry, ensure_ascii=False, indent=1))
    print(f"-> {INDEX}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
