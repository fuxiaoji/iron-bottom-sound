"""大地图（92×78）剧本 50 局自走统计（本地 Headless）。

双 RealisticCommander（tactical 风格包真实现）跑 `match.run_match`，引擎真实规则；
胜利 = 引擎既有通用分支「回合到点 VP 多者胜」；margin=score[axis]-score[allies]。

用法：
  python -m iron_bottom_sound.sim_bigmap --games 3 --quick   # 先冒烟 3 局
  python -m iron_bottom_sound.sim_bigmap --games 50 --workers 4
产物：
  sim-bigmap-raw.jsonl        逐局一行（随完成实时追加，可中途复现）
  sim-bigmap-report.json      汇总
  sim-bigmap-report.md        人类可读汇总（UTF-8 BOM 防中文乱码）

G 标定旋钮不在本文件：先以不同 --gap 调 bigmap_builder 重建副本、各跑少量试局，
用首接敌回合分布选 G；本文件专注「在所选副本上跑 N 局 + 汇总」。
"""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .data import register_custom_scenario
from .match import run_match
from .models import GameOptions, Side
from .storage import GameRepository

# 首轮炮/雷真正打中敌舰的回合 = 首次跨侧交火（gunnery_result / torpedo_result）。
_CONTACT_TYPES = {"gunnery_result", "torpedo_result"}


def _load_registry(db_path: str) -> None:
    repo = GameRepository(db_path)
    for definition in repo.custom_scenarios():
        register_custom_scenario(definition)


def _sunk_side(state: Any, ship_id: str) -> str | None:
    ship = state.ships.get(ship_id)
    return ship.side.value if ship else None


def play_one(scenario_id: str, seed: int, profile: str, db_path: str) -> dict[str, Any]:
    _load_registry(db_path)
    options = GameOptions(mode="llm", realistic_command=True)
    started = time.perf_counter()
    try:
        report, engine, _sessions = run_match(
            scenario_id,
            axis="tactical", allies="tactical",
            axis_profile=profile, allies_profile=profile,
            seed=seed, options=options,
            # RealisticCommander 也经 LLMPlayerSession 记 audit（每次点单 +1），
            # 与真 LLM 调用数无关；30 回合局会超过 128，必须放大否则中途被误裁。
            request_limit=100_000,
        )
        state = engine.get(report.game_id) if engine else None
    except Exception as exc:  # noqa: BLE001 —— 单局失败也要留档，汇总里计为 failure
        return {
            "seed": seed, "completed": False, "passed": False,
            "failure": f"{type(exc).__name__}: {exc}",
            "elapsed_s": round(time.perf_counter() - started, 1),
        }
    events = state.events if state else []
    sunk: dict[str, int] = {"axis": 0, "allies": 0}
    emergency_stop: dict[str, int] = {"axis": 0, "allies": 0}
    detach: dict[str, int] = {"axis": 0, "allies": 0}
    first_contact: int | None = None
    for event in events:
        if event.type == "ship_sunk":
            side = _sunk_side(state, event.payload.get("ship_id") or "")
            if side:
                sunk[side] += 1
        elif event.type == "formation_emergency_stop":
            side = _sunk_side(state, event.payload.get("ship_id") or "")
            if side in emergency_stop:
                emergency_stop[side] += 1
        elif event.type == "ship_detached":
            side = _sunk_side(state, event.payload.get("ship_id") or "")
            if side in detach:
                detach[side] += 1
        elif event.type in _CONTACT_TYPES:
            if first_contact is None or event.turn < first_contact:
                first_contact = event.turn
    score = state.score if state else {"axis": 0, "allies": 0}
    winner = report.winner.value if report.winner else None
    if state and state.winner and not winner:
        winner = state.winner.value
    return {
        "seed": seed,
        "game_id": report.game_id,
        "completed": report.completed,
        "passed": report.passed,
        "failure": report.failure_reason,
        "winner": winner,  # "axis" | "allies" | None(平局)
        "final_turn": state.turn if state else report.failure_reason,
        "score_axis": score.get("axis", 0),
        "score_allies": score.get("allies", 0),
        "margin": score.get("axis", 0) - score.get("allies", 0),
        "victory_reason": report.victory_reason,
        "sunk_axis": sunk["allies"],   # 同盟被轴心击沉数 = axis 造成
        "sunk_allies": sunk["axis"],   # 轴心被同盟击沉数 = allies 造成
        "emergency_stop_axis": emergency_stop["axis"],
        "emergency_stop_allies": emergency_stop["allies"],
        "detach_axis": detach["axis"],
        "detach_allies": detach["allies"],
        "first_contact_turn": first_contact,
        "elapsed_s": round(time.perf_counter() - started, 1),
    }


def _fmt(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}"


def aggregate(games: list[dict[str, Any]]) -> dict[str, Any]:
    finished = [game for game in games if game.get("completed") and game.get("passed")]
    crashed = [game for game in games if not game.get("completed") or not game.get("passed")]
    draws = [game for game in finished if not game.get("winner")]
    axis_wins = [game for game in finished if game.get("winner") == "axis"]
    allies_wins = [game for game in finished if game.get("winner") == "allies"]
    mean = lambda items: (sum(items) / len(items)) if items else 0.0  # noqa: E731
    first_contacts = [game["first_contact_turn"] for game in finished if game.get("first_contact_turn")]
    return {
        "total": len(games),
        "completed": len(finished),
        "crashed_or_incomplete": len(crashed),
        "axis_wins": len(axis_wins),
        "allies_wins": len(allies_wins),
        "draws": len(draws),
        "axis_win_rate": len(axis_wins) / len(finished) if finished else None,
        "allies_win_rate": len(allies_wins) / len(finished) if finished else None,
        "avg_margin": mean([game["margin"] for game in finished]),
        "min_margin": min((game["margin"] for game in finished), default=None),
        "max_margin": max((game["margin"] for game in finished), default=None),
        "avg_axis_score": mean([game["score_axis"] for game in finished]),
        "avg_allies_score": mean([game["score_allies"] for game in finished]),
        "avg_final_turn": mean([game["final_turn"] for game in finished]),
        "avg_sunk_axis": mean([game["sunk_axis"] for game in finished]),
        "avg_sunk_allies": mean([game["sunk_allies"] for game in finished]),
        "total_sunk_axis": sum(game["sunk_axis"] for game in finished),
        "total_sunk_allies": sum(game["sunk_allies"] for game in finished),
        "avg_first_contact_turn": mean(first_contacts),
        "first_contact_min": min(first_contacts, default=None),
        "first_contact_max": max(first_contacts, default=None),
        "emergency_stop_axis": sum(game["emergency_stop_axis"] for game in finished),
        "emergency_stop_allies": sum(game["emergency_stop_allies"] for game in finished),
        "detach_axis": sum(game["detach_axis"] for game in finished),
        "detach_allies": sum(game["detach_allies"] for game in finished),
        "avg_elapsed_s": mean([game["elapsed_s"] for game in games]),
        "crash_reasons": sorted(set(str(game.get("failure"))[:160] for game in crashed)),
    }


def build_markdown(stats: dict[str, Any], scenario_id: str, gap: int | None) -> str:
    l = []  # noqa: E741
    l.append(f"# 大战场（{scenario_id}）自走统计\n")
    meta = [f"副本 G(正面间距)={gap}" if gap is not None else ""]
    l.append(f"- 完成 {stats['completed']}/{stats['total']} 局 · 崩溃/未完成 {stats['crashed_or_incomplete']}")
    if stats["crashed_or_incomplete"]:
        l.append(f"- 失败原因：{stats['crash_reasons']}")
    l.append("")
    l.append("## 胜负")
    l.append(f"- 轴心 {stats['axis_wins']}（{_fmt((stats['axis_win_rate'] or 0) * 100)}%）· 同盟 {stats['allies_wins']}（{_fmt((stats['allies_win_rate'] or 0) * 100)}%）· 平局 {stats['draws']}")
    l.append(f"- 平均净分 margin=轴-盟：{_fmt(stats['avg_margin'])}（min {stats['min_margin']} / max {stats['max_margin']}）")
    l.append(f"- 平均终盘 VP：轴 {_fmt(stats['avg_axis_score'])} / 盟 {_fmt(stats['avg_allies_score'])}")
    l.append("")
    l.append("## 对局进程")
    l.append(f"- 平均结束回合：{_fmt(stats['avg_final_turn'])}")
    l.append(f"- 平均单局耗时：{_fmt(stats['avg_elapsed_s'])} s")
    l.append("")
    l.append("## 交火与击沉")
    l.append(f"- 首接敌回合：均 {_fmt(stats['avg_first_contact_turn'])}（min {stats['first_contact_min']} / max {stats['first_contact_max']}）")
    l.append(f"- 平均击沉：轴 {_fmt(stats['avg_sunk_axis'])} 舰（共 {stats['total_sunk_axis']}）· 盟 {_fmt(stats['avg_sunk_allies'])} 舰（共 {stats['total_sunk_allies']}）")
    l.append("")
    l.append("## 编队纪律")
    l.append(f"- 紧急停车：轴 {stats['emergency_stop_axis']} / 盟 {stats['emergency_stop_allies']}")
    l.append(f"- 脱队撤退：轴 {stats['detach_axis']} / 盟 {stats['detach_allies']}")
    return "\n".join(l) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run N realistic dual-tactical games on the big-map scenario and aggregate")
    parser.add_argument("--scenario", default="IBS-CUSTOM-BIG-GRAND", help="大战场副本 id")
    parser.add_argument("--games", type=int, default=1, help="总局数（seed = start..start+games-1）")
    parser.add_argument("--start", type=int, default=1, help="首个 seed")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--profile", default="balanced", help="双方 RealisticCommander 的战术风格")
    parser.add_argument("--quick", action="store_true", help="冒烟：1 worker 顺序跑，便于尽早看产物")
    parser.add_argument("--gap", type=int, default=None, help="若有则写进报告元信息（仅注释）")
    parser.add_argument("--db", default=r"backend\iron-bottom-sound.sqlite3", help="仓库 DB（相对仓库根或绝对）")
    parser.add_argument("--out", default="backend", help="产物目录（raw.jsonl / report.json / report.md）")
    args = parser.parse_args()
    # --db/--out 的默认值是仓库根相对路径；无论从仓库根还是 backend/ 下调用都要指向同一份 DB。
    repo_root = Path(__file__).resolve().parents[3]
    db_path = Path(args.db)
    if not db_path.is_absolute():
        rooted = repo_root / args.db
        if rooted.exists() or not db_path.exists():
            db_path = rooted
    args.db = str(db_path)
    output = Path(args.out)
    if not output.is_absolute():
        output = repo_root / output
    output.mkdir(parents=True, exist_ok=True)
    raw_path = output / "sim-bigmap-raw.jsonl"
    games: list[dict[str, Any]] = []

    def append_raw(game: dict[str, Any]) -> None:
        with open(raw_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(game, ensure_ascii=False) + "\n")
        games.append(game)

    seeds = range(args.start, args.start + args.games)
    if args.quick:
        for seed in seeds:
            append_raw(play_one(args.scenario, seed, args.profile, args.db))
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(play_one, args.scenario, seed, args.profile, args.db): seed
                for seed in seeds
            }
            for future in as_completed(futures):
                seed = futures[future]
                try:
                    game = future.result()
                except Exception as exc:  # noqa: BLE001
                    game = {"seed": seed, "completed": False, "passed": False,
                            "failure": f"{type(exc).__name__}: {exc}", "elapsed_s": 0}
                append_raw(game)

    stats = aggregate(games)
    stats["scenario_id"] = args.scenario
    stats["profile"] = args.profile
    stats["gap_front_columns"] = args.gap
    (output / "sim-bigmap-report.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # utf-8-sig：带 BOM，中文 Windows 编辑器/VS Code 才不会误判成 GBK。
    (output / "sim-bigmap-report.md").write_text(
        build_markdown(stats, args.scenario, args.gap), encoding="utf-8-sig"
    )
    print(json.dumps(stats, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
