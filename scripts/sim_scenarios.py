#!/usr/bin/env python3
"""全部内置想定 × N 局双 AI 自战统计，把胜率写回各想定 YAML 的 ai_stats 字段。

复用 match.run_match 的双 RealisticCommander（tactical 风格）管线；想定全部在
SUPPORTED_SCENARIOS 白名单内并带 engine_default_formations 编队提案。

用法：
  .venv/bin/python scripts/sim_scenarios.py --games 10 --workers 8
产物：
  backend/sim-scenarios-raw.jsonl  逐局一行
  各 scenario-*.yaml 的 ai_stats:  局数/轴心胜/同盟胜/平局/平均回合/平均击沉
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
SCENARIO_DIR = REPO / "resources" / "derived" / "structured" / "scenarios"
SCENARIOS = [f"IBS-S-{n:02d}" for n in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14)] + ["IBS-S-EM-01", "IBS-S-FM-01"]


def play_one(scenario_id: str, seed: int) -> dict:
    from iron_bottom_sound.match import run_match
    from iron_bottom_sound.models import GameOptions

    started = time.perf_counter()
    options = GameOptions(mode="llm", realistic_command=True)
    try:
        report, engine, _sessions = run_match(
            scenario_id,
            axis="tactical", allies="tactical",
            axis_profile="balanced", allies_profile="balanced",
            seed=seed, options=options,
            request_limit=100_000,
        )
        state = engine.get(report.game_id) if engine else None
        if state is None:
            raise RuntimeError("no state returned")
        sunk = {"axis": 0, "allies": 0}
        for event in state.events:
            if event.type == "ship_sunk":
                ship = state.ships.get(event.payload.get("ship_id") or "")
                if ship is not None:
                    sunk[ship.side.value] += 1
        return {
            "scenario": scenario_id, "seed": seed, "completed": True,
            "winner": state.winner.value if state.winner else "draw",
            "reason": state.victory_reason,
            "turns": state.turn, "sunk": sunk,
            "elapsed_s": round(time.perf_counter() - started, 1),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "scenario": scenario_id, "seed": seed, "completed": False,
            "failure": f"{type(exc).__name__}: {exc}",
            "elapsed_s": round(time.perf_counter() - started, 1),
        }


def write_stats(results: list[dict]) -> None:
    by_scenario: dict[str, list[dict]] = {}
    for row in results:
        by_scenario.setdefault(row["scenario"], []).append(row)
    for scenario_id, rows in by_scenario.items():
        number = scenario_id.replace("IBS-S-", "").lower()
        path = SCENARIO_DIR / f"scenario-{number}.yaml"
        if not path.exists():
            continue
        completed = [r for r in rows if r.get("completed")]
        wins = {"axis": 0, "allies": 0, "draw": 0}
        turns = [r["turns"] for r in completed]
        sunk = {"axis": 0, "allies": 0}
        for r in completed:
            wins[r["winner"]] = wins.get(r["winner"], 0) + 1
            for side in ("axis", "allies"):
                sunk[side] += r["sunk"].get(side, 0)
        games = len(completed)
        stats = {
            "games": games,
            "axis_wins": wins["axis"],
            "allies_wins": wins["allies"],
            "draws": wins.get("draw", 0),
            "avg_turns": round(statistics.mean(turns), 1) if turns else None,
            "avg_sunk": {"axis": round(sunk["axis"] / games, 1) if games else None,
                         "allies": round(sunk["allies"] / games, 1) if games else None},
            "failures": len(rows) - games,
            "note": "双 tactical RealisticCommander 自战（balanced 风格，seeds 1..N）；仅供剧本平衡参考，非官方胜率。",
        }
        text = path.read_text(encoding="utf-8")
        block = yaml.safe_dump({"ai_stats": stats}, allow_unicode=True, sort_keys=False, width=120).rstrip("\n")
        if "ai_stats:" in text:
            # ai_stats 块始终追加在文件末尾：重跑时按行裁掉旧块再追加，绝不整文件重dump（保注释）
            lines = text.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("ai_stats:"):
                    lines = lines[:i]
                    break
            text = "\n".join(lines).rstrip("\n") + "\n"
        else:
            text = text.rstrip("\n") + "\n"
        text += block + "\n"
        path.write_text(text, encoding="utf-8")
        print(f"ai_stats written: {path.name} axis={wins['axis']} allies={wins['allies']} draw={wins.get('draw', 0)} failures={stats['failures']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Play N AI-vs-AI games for every builtin scenario and write ai_stats")
    parser.add_argument("--games", type=int, default=10)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--only", nargs="*", default=None, help="只跑指定想定 id")
    parser.add_argument("--skip-fm", action="store_true", help="跳过 91 舰的 FM-01（太慢）")
    args = parser.parse_args()

    scenarios = list(args.only) if args.only else list(SCENARIOS)
    if args.skip_fm:
        scenarios = [s for s in scenarios if s != "IBS-S-FM-01"]
    jobs = [(sid, args.start + i) for sid in scenarios for i in range(args.games)]
    raw_path = REPO / "backend" / "sim-scenarios-raw.jsonl"
    raw_path.parent.mkdir(exist_ok=True)
    results: list[dict] = []
    with raw_path.open("w", encoding="utf-8") as raw:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(play_one, sid, seed): (sid, seed) for sid, seed in jobs}
            for done, future in enumerate(as_completed(futures), 1):
                row = future.result()
                results.append(row)
                raw.write(json.dumps(row, ensure_ascii=False) + "\n")
                raw.flush()
                print(f"[{done}/{len(jobs)}] {row['scenario']} seed={row['seed']} "
                      f"{'OK ' + str(row.get('winner')) if row.get('completed') else 'FAIL ' + row.get('failure', '')[:80]} "
                      f"{row['elapsed_s']}s", flush=True)
    write_stats(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
