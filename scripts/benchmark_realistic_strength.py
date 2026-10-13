"""Paired, isolated fleet AI tournament. Does not import API or touch player saves.

Development and held-out deployments/seeds are distinct. Each seed is played
with the new AI on BOTH sides; a natural faction advantage is not an AI win.
Only complete, valid, replay-identical pairs enter the strength statistics.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
import sqlite3
import sys

from iron_bottom_sound.custom_scenarios import validate_definition, with_engine_default_formations
from iron_bottom_sound.data import load_scenario, register_custom_scenario
from iron_bottom_sound.models import HexCoord, Side
from iron_bottom_sound.ship_records import load_ship_records
from iron_bottom_sound.tactical import PROFILES

from evaluate_realistic_ai import evaluate


ROOT = Path(__file__).resolve().parents[1]


def fleet_scenario(layout: int, development: bool = False) -> dict:
    """Author legal custom bodies from actual catalog records, never edit ships.

    24--48 ships, 6--8 formations per side, varied visibility, separation and
    heading. Real national equipment asymmetries are retained and side-swapped.
    The authored groups are the same editable format as the scenario workshop.
    """
    records = load_ship_records()
    sources = load_scenario("IBS-S-FM-01")["ships"] + load_scenario("IBS-S-EM-01")["ships"]
    pools = {}
    for entry in sources:
        key = (entry["side"], records[entry["id"]].ship_type)
        if entry["id"] not in [item["id"] for item in pools.get(key, [])]:
            pools.setdefault(key, []).append(entry)
    kinds = ["BB", "CA", "CL", "DD", "DD", "BB"]
    if layout == 5:
        kinds = ["BB", "BB", "CA", "CA", "CL", "CL", "DD", "DD"]
    count = 3 if layout == 5 else 2
    gap = [12, 10, 16, 14, 11, 14][layout]
    headings = [(2, 5), (3, 6), (1, 4), (2, 5), (3, 3), (2, 5)][layout]
    # A separate deployment, not just a different dice seed, for development.
    shift = 4 if development else 0
    ships, formations = [], {side.value: [] for side in Side}
    for side in Side:
        used = set()
        heading = headings[0 if side == Side.AXIS else 1]
        for group_index, kind in enumerate(kinds):
            available = [entry for entry in pools[(side.value, kind)] if entry["id"] not in used]
            members = available[:count]
            if len(members) < 2:
                raise ValueError(f"Not enough catalog {side} {kind}")
            used.update(entry["id"] for entry in members)
            q = 26 + (gap if side == Side.ALLIES else 0) + shift
            # Widely separated columns, with flanking/screen forces forward.
            q += (2 if kind == "DD" else 0) * (1 if side == Side.AXIS else -1)
            row = 28 + group_index * 5 + ((group_index % 2) * 2 if layout in (2, 3) else 0)
            if side == Side.ALLIES and layout in (1, 3):
                row += 3
            cursor = HexCoord(q=q, r=row - (q - (q & 1)) // 2)
            fid = f"{side.value}-group-{group_index}"
            for entry in members:
                ships.append({
                    "id": entry["id"], "side": side.value, "position": cursor.label,
                    "heading": heading, "speed": 3, "asset": entry["asset"],
                })
                cursor = cursor.neighbor(((heading + 2) % 6) + 1, columns=80, rows=80)
            formations[side.value].append({
                "formation_id": fid, "name": f"{kind} {group_index + 1}",
                "ship_ids": [entry["id"] for entry in members], "leader_id": members[0]["id"],
                "flagship_id": members[0]["id"], "reserve_flagship_id": members[1]["id"],
                "spacing": 1, "heading": heading,
            })
    return {
        "id": f"IBS-CUSTOM-AI-{'DEV' if development else 'HOLDOUT'}-{layout}",
        "title": f"AI fleet {'development' if development else 'held-out'} deployment {layout}",
        "description": "Offline strength fixture; no historical or adjudication rules modified.",
        "turns": 12 if layout != 5 else 14,
        # The published penetration table stops at 25 hexes. Do not invent a
        # beyond-table adjudication in an AI experiment; keep sight <= 20.
        "visibility": {"axis": 12 if layout == 3 else 20, "allies": 12 if layout == 3 else 20},
        "optional_rules": [], "map_columns": 80, "map_rows": 80,
        "printed_columns": 80, "printed_rows": 80,
        "ships": ships, "formations": formations,
    }


def prepare(definition):
    definition = deepcopy(definition)
    errors = validate_definition(definition["id"], definition)
    if errors:
        raise ValueError(errors)
    definition = with_engine_default_formations(definition)
    register_custom_scenario(definition)
    return definition


def play(task):
    definition, scenario, profile, opponent, seed, side, revision, progress, expected_hashes = task
    actual_hashes = {path: sha256((ROOT / "backend/src/iron_bottom_sound" / path).read_bytes()).hexdigest() for path in expected_hashes}
    if actual_hashes != expected_hashes:
        raise RuntimeError("AI source changed after tournament registration; use a new output for the new revision")
    if definition:
        prepare(definition)
    if revision is not None:
        PROFILES[profile] = PROFILES[profile].model_copy(update={"fleet_tactics_version": revision})
    return evaluate(scenario, profile, opponent, seed, Side(side), progress=progress)


def summarize(rows, minimum_pairs=30):
    groups = {}
    invalid = []
    for row in rows:
        key = (row["scenario"], row["profile"], row["opponent"], row["seed"])
        if row["failure"] or not row["completed"] or not row["replay_equal"]:
            invalid.append({"key": key, "side": row["side"], "failure": row["failure"]})
        groups.setdefault(key, {})[row["side"]] = row
    points, signs, by_scenario = [], [], {}
    wins = losses = draws = 0
    for key, pair in sorted(groups.items()):
        if set(pair) != {"axis", "allies"} or any(
            row["failure"] or not row["completed"] or not row["replay_equal"] for row in pair.values()
        ):
            continue
        score = 0
        for row in pair.values():
            if row["winner"] is None:
                draws += 1
                score += 0.5
            elif row["winner"] == row["side"]:
                wins += 1
                score += 1
            else:
                losses += 1
        points.append(score)
        signs.append(1 if score > 1 else -1 if score < 1 else 0)
        layer = by_scenario.setdefault(key[0], {"pairs": 0, "points": 0})
        layer["pairs"] += 1
        layer["points"] += score
    positive, negative = signs.count(1), signs.count(-1)
    n = positive + negative
    p = sum(math.comb(n, k) for k in range(positive, n + 1)) / 2 ** n if n else 1.0
    rate = sum(points) / (2 * len(points)) if points else None
    return {
        "complete_pairs": len(points), "wins": wins, "losses": losses, "draws": draws,
        "points_rate": rate, "positive_pairs": positive, "negative_pairs": negative,
        "neutral_pairs": signs.count(0), "paired_one_sided_sign_p": p,
        "invalid_games": invalid, "unpaired_games": len(rows) - 2 * len(points),
        "by_scenario": by_scenario,
        "strength_gate_pass": len(points) >= minimum_pairs and rate is not None and rate >= .60 and p < .05
        and not invalid and len(rows) == 2 * len(points),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=["dev", "holdout", "historical", "custom"], default="dev")
    parser.add_argument("--profile", choices=PROFILES, default="rc_coordinated")
    parser.add_argument("--opponent", choices=PROFILES, default="adaptive")
    parser.add_argument("--seeds", type=int, nargs="+")
    parser.add_argument("--layouts", type=int, nargs="+", default=list(range(6)))
    parser.add_argument("--scenarios", nargs="+")
    parser.add_argument("--custom-db", type=Path, help="Read-only source of workshop scenarios; no games or events read")
    parser.add_argument("--custom-ids", nargs="+")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--revision", type=int, choices=[2, 3, 4], help="Reproduce the pre-strength cooperative policy (2)")
    parser.add_argument("--progress", action="store_true", help="Print completed-turn checkpoints, not strength samples")
    parser.add_argument("--minimum-pairs", type=int, default=30)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.revision is not None:
        PROFILES[args.profile] = PROFILES[args.profile].model_copy(update={"fleet_tactics_version": args.revision})
    if args.profile == args.opponent:
        parser.error("Comparison must use different profiles")
    seeds = args.seeds or ([11, 29] if args.suite == "dev" else [101, 107, 113, 127, 139])
    definitions = [prepare(fleet_scenario(layout, args.suite == "dev")) for layout in args.layouts] if args.suite in {"dev", "holdout"} else []
    if args.suite == "custom":
        if not args.custom_db or not args.custom_ids or not args.custom_db.is_file():
            parser.error("custom suite requires an existing --custom-db and explicit --custom-ids")
        with sqlite3.connect(args.custom_db.resolve().as_uri() + "?mode=ro", uri=True) as connection:
            for scenario_id in args.custom_ids:
                result = connection.execute("SELECT definition_json FROM custom_scenarios WHERE scenario_id = ?", (scenario_id,)).fetchone()
                if not result:
                    parser.error(f"Missing custom scenario {scenario_id}")
                definition = json.loads(result[0])
                definition["id"] = scenario_id
                definitions.append(prepare(definition))
    scenarios = args.scenarios or ([f"IBS-S-{i:02d}" for i in range(1, 15)] + ["IBS-S-EM-01", "IBS-S-FM-01"])
    scenarios = [(item, item["id"]) for item in definitions] if definitions else [(None, item) for item in scenarios]
    source_paths = ["engine.py", "realistic_command.py", "tactical.py", "formation_tactics.py", "torpedo_tactics.py"]
    metadata = {
        "suite": args.suite, "profile": args.profile, "opponent": args.opponent, "seeds": seeds,
        "definitions": definitions,
        "profile_parameters": PROFILES[args.profile].model_dump(),
        "opponent_parameters": PROFILES[args.opponent].model_dump(),
        "source_hashes": {path: sha256((ROOT / "backend/src/iron_bottom_sound" / path).read_bytes()).hexdigest() for path in source_paths},
        "statistical_unit": "same scenario and seed, both sides; exact one-sided sign test of pair points versus 1",
        "primary_gate": {"minimum_pairs": args.minimum_pairs, "minimum_points_rate": .60, "maximum_p_exclusive": .05},
    }
    tasks = [(definition, scenario, args.profile, args.opponent, seed, side.value, args.revision, args.progress, metadata["source_hashes"])
             for definition, scenario in scenarios for seed in seeds for side in Side]
    if len(set(seeds)) != len(seeds) or len(set(args.layouts)) != len(args.layouts):
        parser.error("Duplicate seeds or layouts would duplicate statistical samples")
    rows = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    def save():
        args.output.write_text(json.dumps({"metadata": metadata, "summary": summarize(rows, args.minimum_pairs), "games": rows},
                                         ensure_ascii=False, indent=2), encoding="utf-8")
    save()  # Freeze specification before seeing any result.
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(play, task): task for task in tasks}
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            rows.sort(key=lambda item: (item["scenario"], item["seed"], item["side"]))
            save()
            print(json.dumps({"done": len(rows), "total": len(tasks), "scenario": row["scenario"],
                              "seed": row["seed"], "side": row["side"], "winner": row["winner"],
                              "score": row["score"], "failure": row["failure"], "seconds": row["elapsed_seconds"]}), flush=True)
    print(json.dumps(summarize(rows, args.minimum_pairs)), flush=True)
    return int(any(row["failure"] or not row["completed"] or not row["replay_equal"] for row in rows))


if __name__ == "__main__":
    sys.exit(main())
