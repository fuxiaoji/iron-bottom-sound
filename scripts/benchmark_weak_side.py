"""Frozen weak-side comparisons, without API imports or player-save access.

The favored side always uses balanced. Replace ONLY the preregistered weak
side with rc_coordinated; compare to balanced/balanced with the same seed.
Draws are non-wins for the primary endpoint. Invalid games exclude their
entire matched pair. All preregistered scenarios remain in the Holm family.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
import time
import traceback

from iron_bottom_sound.data import load_scenario
from iron_bottom_sound.models import Side
from iron_bottom_sound.tactical import PROFILES

from evaluate_realistic_ai import evaluate


ROOT = Path(__file__).resolve().parents[1]
NEW_PROFILE = "rc_coordinated"
BASELINE = "balanced"
# This order also fixes the disjoint seed blocks. Never reselect from results.
WEAK_SIDES = (
    ("IBS-S-01", "axis"), ("IBS-S-02", "allies"),
    ("IBS-S-03", "allies"), ("IBS-S-04", "axis"),
    ("IBS-S-05", "axis"), ("IBS-S-06", "axis"),
    ("IBS-S-10", "allies"), ("IBS-S-11", "axis"),
    ("IBS-S-12", "axis"), ("IBS-S-14", "axis"),
    ("IBS-S-EM-01", "allies"), ("IBS-S-FM-01", "axis"),
)


def exact_improvement_p(improved: int, worsened: int) -> float:
    """One-sided exact McNemar/binomial test on discordant binary wins."""
    n = improved + worsened
    return sum(math.comb(n, k) for k in range(improved, n + 1)) / 2 ** n if n else 1.0


def holm_adjust(pvalues: dict[str, float]) -> dict[str, float]:
    ordered = sorted(pvalues, key=lambda key: (pvalues[key], key))
    adjusted, previous = {}, 0.0
    for index, key in enumerate(ordered):
        previous = max(previous, min(1.0, (len(ordered) - index) * pvalues[key]))
        adjusted[key] = previous
    return adjusted


def valid(row: dict) -> bool:
    return bool(row["completed"] and row["replay_equal"] and not row["failure"])


def arm_stats(rows: list[dict], weak_side: str) -> dict:
    wins = sum(row["winner"] == weak_side for row in rows)
    draws = sum(row["winner"] is None for row in rows)
    count = len(rows)
    behavior = {name: sum(row.get("behavior", {}).get(name, 0) for row in rows) for name in
                ("torpedo_launches", "friendly_collisions", "friendly_torpedo_hits", "emergency_stops")}
    return {
        "wins": wins, "losses": count - wins - draws, "draws": draws,
        "win_rate": wins / count if count else None,
        "points_rate": (wins + .5 * draws) / count if count else None,
        "behavior": behavior,
    }


def summarize(rows: list[dict], cases: list[dict], minimum_pairs: int = 30) -> dict:
    by_id = {case["id"]: case for case in cases}
    if len(by_id) != len(cases):
        raise ValueError("Duplicate preregistered scenario")
    pairs = {}
    for row in rows:
        case = by_id.get(row["scenario"])
        if not case or row["seed"] not in case["seeds"] or row["side"] != case["weak_side"]:
            raise ValueError("Unregistered scenario, seed or weak side")
        if row["arm"] not in {"new", "baseline"}:
            raise ValueError("Unknown comparison arm")
        expected = NEW_PROFILE if row["arm"] == "new" else BASELINE
        if row["profile"] != expected or row["opponent"] != BASELINE:
            raise ValueError("Comparison profile changed")
        pair = pairs.setdefault((row["scenario"], row["seed"]), {})
        if row["arm"] in pair:
            raise ValueError("Duplicate game would duplicate a statistical sample")
        pair[row["arm"]] = row
    layers = {}
    for case in cases:
        baseline_rows, new_rows, invalid_games = [], [], []
        improved = worsened = invalid_pairs = missing_pairs = 0
        for seed in case["seeds"]:
            pair = pairs.get((case["id"], seed), {})
            invalid_games.extend({"seed": seed, "arm": row["arm"], "failure": row["failure"],
                                  "completed": row["completed"], "replay_equal": row["replay_equal"],
                                  "failure_side": row.get("failure_side")}
                                 for row in pair.values() if not valid(row))
            if len(pair) != 2:
                missing_pairs += 1
                continue
            if not all(valid(row) for row in pair.values()):
                invalid_pairs += 1
                continue
            old, new = pair["baseline"], pair["new"]
            old_win, new_win = old["winner"] == case["weak_side"], new["winner"] == case["weak_side"]
            improved += int(new_win and not old_win)
            worsened += int(old_win and not new_win)
            baseline_rows.append(old)
            new_rows.append(new)
        old_stats, new_stats = arm_stats(baseline_rows, case["weak_side"]), arm_stats(new_rows, case["weak_side"])
        count = len(baseline_rows)
        layers[case["id"]] = {
            "title": case.get("title", case["id"]), "weak_side": case["weak_side"],
            "planned_pairs": len(case["seeds"]), "valid_pairs": count,
            "missing_pairs": missing_pairs, "invalid_pairs": invalid_pairs, "invalid_games": invalid_games,
            "baseline": old_stats, "new": new_stats,
            "win_rate_change": (new_stats["win_rate"] - old_stats["win_rate"]) if count else None,
            "improved_pairs": improved, "worsened_pairs": worsened,
            "unchanged_pairs": count - improved - worsened,
            "paired_one_sided_p": exact_improvement_p(improved, worsened),
        }
    adjusted = holm_adjust({key: layer["paired_one_sided_p"] for key, layer in layers.items()})
    for key, layer in layers.items():
        layer["holm_p"] = adjusted[key]
        layer["significant_improvement"] = (
            layer["valid_pairs"] >= minimum_pairs
            and not layer["missing_pairs"] and not layer["invalid_games"]
            and layer["win_rate_change"] > 0 and layer["holm_p"] < .05
        )
    return {
        "planned_games": 2 * sum(len(case["seeds"]) for case in cases),
        "attempted_games": len(rows), "valid_pairs": sum(layer["valid_pairs"] for layer in layers.values()),
        "invalid_games": sum(len(layer["invalid_games"]) for layer in layers.values()),
        "completed_attempts": len(rows) == 2 * sum(len(case["seeds"]) for case in cases),
        "significantly_improved_scenarios": [key for key, layer in layers.items() if layer["significant_improvement"]],
        "by_scenario": layers,
    }


def frozen_inputs() -> dict[str, str]:
    paths = list((ROOT / "backend/src/iron_bottom_sound").rglob("*.py"))
    paths += [path for path in (ROOT / "resources/derived/structured").rglob("*")
              if path.is_file() and path.suffix in {".yaml", ".yml", ".csv", ".json"}]
    paths += [Path(__file__), ROOT / "scripts/evaluate_realistic_ai.py"]
    return {path.relative_to(ROOT).as_posix(): sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}


def play(task: tuple) -> dict:
    scenario, weak_side, seed, arm, hashes = task
    actual = {path: sha256((ROOT / path).read_bytes()).hexdigest() for path in hashes}
    if actual != hashes:
        raise RuntimeError("Frozen engine, AI, rules or benchmark changed; stop and register a new experiment")
    profile = NEW_PROFILE if arm == "new" else BASELINE
    started = time.perf_counter()
    try:
        row = evaluate(scenario, profile, BASELINE, seed, Side(weak_side))
    except Exception as error:
        # Initialization/replay errors, too, are INVALID attempts, not defeats.
        row = {"scenario": scenario, "profile": profile, "opponent": BASELINE, "seed": seed,
               "side": weak_side, "completed": False, "replay_equal": False, "winner": None,
               "failure": f"{type(error).__name__}: {error}", "failure_traceback": traceback.format_exc(),
               "failure_side": None, "elapsed_seconds": round(time.perf_counter() - started, 3)}
    row["arm"] = arm
    return row


def preregister(pairs: int = 30) -> list[dict]:
    cases = []
    for index, (scenario, side) in enumerate(WEAK_SIDES):
        definition = load_scenario(scenario)
        legacy = scenario in {"IBS-S-03", "IBS-S-FM-01"}
        cases.append({
            "id": scenario, "title": definition["title"], "weak_side": side,
            "seeds": list(range(1001 + 100 * index, 1001 + 100 * index + pairs)),
            "reference_ai_stats": definition.get("ai_stats"),
            "selection_source": "havedone.md 2026-09-10/11 old 10:0 record" if legacy else "current YAML 10-game balanced reference",
            "selection_caution": "S-03 current YAML is only axis 6:4; recheck old anecdote" if scenario == "IBS-S-03" else
                                 "Reference sample selects a side, not proof of structural imbalance",
            "definition": definition,
        })
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--pairs", type=int, default=30, help="Preregistered samples per scenario, not result-dependent")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.pairs <= 100 or args.workers < 1:
        parser.error("pairs must be 1..100 and workers positive")
    if args.output.exists() or args.output.with_suffix(".jsonl").exists():
        parser.error("Use a fresh output; never overwrite or mix experimental batches")
    cases = preregister(args.pairs)
    metadata = {
        "registered_at_utc": datetime.now(timezone.utc).isoformat(), "cases": cases,
        "new_profile": NEW_PROFILE, "baseline_profile": BASELINE, "strong_side_profile": BASELINE,
        "profile_parameters": {key: PROFILES[key].model_dump() for key in (NEW_PROFILE, BASELINE)},
        "source_hashes": frozen_inputs(),
        "statistical_unit": "same preregistered scenario, fixed weak side, seed; two arms",
        "primary_endpoint": "engine-adjudicated weak-side win; draw is non-win",
        "primary_test": "one-sided exact paired McNemar; Holm over all 12 preregistered scenarios",
        "minimum_valid_pairs": 30, "maximum_adjusted_p_exclusive": .05,
        "invalid_policy": "exclude entire same-seed pair, report all failures, no compatibility pass",
        "seed_caution": "same initial seed, not identical dice streams after tactical choices diverge",
        "scope": "no AI changes, scenario balancing, API import, player DB or external calls",
    }
    rows = []
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def save() -> None:
        args.output.write_text(json.dumps({"metadata": metadata, "summary": summarize(rows, cases), "games": rows},
                                         ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    save()  # Freeze sides, seeds, parameters and evidence before any result.
    # Interleave scenarios to avoid a whole stratum waiting behind slow cases.
    tasks = [(case["id"], case["weak_side"], case["seeds"][index], arm, metadata["source_hashes"])
             for index in range(args.pairs) for case in cases for arm in ("baseline", "new")]
    with args.output.with_suffix(".jsonl").open("x", encoding="utf-8") as stream:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(play, task): task for task in tasks}
            for future in as_completed(futures):
                row = future.result()
                rows.append(row)
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                stream.flush()
                print(json.dumps({"done": len(rows), "total": len(tasks), "scenario": row["scenario"],
                                  "seed": row["seed"], "arm": row["arm"], "winner": row["winner"],
                                  "failure": row["failure"], "seconds": row["elapsed_seconds"]}), flush=True)
                if len(rows) % 12 == 0:
                    save()
    rows.sort(key=lambda row: (row["scenario"], row["seed"], row["arm"]))
    save()
    print(json.dumps(summarize(rows, cases)), flush=True)
    return int(any(not valid(row) for row in rows))


if __name__ == "__main__":
    sys.exit(main())
