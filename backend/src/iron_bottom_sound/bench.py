"""风格状态机对战基准（训练/评估框架）：多进程并行跑满轮次，聚合各风格胜率。

设计要点（与治理约束一致）：
- 每一局都走 `match.run_match` —— 引擎是唯一裁决者，本模块只收集 `MatchReport`，
  不碰状态、不改裁决、不复制规则常量。
- 对局之间零共享状态（每局独立 `IronBottomEngine` + 独立 seed 派生的 AI RNG），
  因此可以放心并行；CPU 密集的纯 Python 模拟受 GIL 限制，多**进程**才有真加速
  （`--workers` 默认 min(8, cpu_count)，`--workers 0` 串行）。
- 胜率按"风格作为轴心 / 作为盟军"分开统计：想定的轴/盟船表与 VP 目标不对称，
  单看合计会掩盖阵营优势。
- 默认 `--games 50` 局按轮转分布到全部有序非镜像组合（6 风格 × 5 = 30 组），
  每组内 seed 连续取 `seed_base+1..`，控制开局方差、便于复现。
- `--per-pair N`：每对有序组合精确跑 N 局（而非轮转均摊），seed 取 seed_base+1..N，
  用于"每两个对战打 30 局"式密集对照。`--profiles` 可含 `random`（乱打 AI，
  在所有合法选择里均匀随机，见 randomai.py）。
"""

from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from .match import run_match
from .models import Side
from .tactical import PROFILES

# 基准参赛者 = 6 种战术风格 + 乱打 AI；random 走 run_match 的 "random" 玩家。
DEFAULT_PROFILES = [*PROFILES, "random"]
_KNOWN_PROFILES = set(PROFILES) | {"random"}


def ordered_matchups(profiles: list[str]) -> list[tuple[str, str]]:
    """有序非镜像组合：(axis 风格, allies 风格)，A≠B。"""
    return [(a, b) for a in profiles for b in profiles if a != b]


def build_games(
    scenario: str,
    profiles: list[str],
    total_games: int,
    seed_base: int = 1,
    per_pair: int | None = None,
) -> list[tuple[str, int, str, str]]:
    """把 total_games 局轮转分布到全部有序组合；同组合内 seed 依次取
    seed_base+1..seed_base+k（同组合共享同一套开局 seed，控制风格间方差）。
    余数给靠前组合 → 各组合局数差 ≤ 1。

    `per_pair` 给定时忽略 total_games 的均摊，改为每对有序组合精确 N 局
    （seed_base+1..seed_base+N），用于"每两个对战打 N 局"的密集对照。"""
    pairs = ordered_matchups(profiles)
    if per_pair is not None:
        per = [per_pair] * len(pairs)
    else:
        base, extra = divmod(total_games, len(pairs))
        per = [base] * len(pairs)
        for i in range(extra):
            per[i] += 1
    games: list[tuple[str, int, str, str]] = []
    for (axis_p, allies_p), k in zip(pairs, per):
        for g in range(k):
            games.append((scenario, seed_base + g, axis_p, allies_p))
    return games


def _run_one(args: tuple[str, int, str, str]) -> dict[str, Any]:
    """单个进程里跑一局；只返回可序列化的结果（report 公开字段 + 终局回合数）。

    profile == "random" 时改走 run_match 的 "random" 玩家（乱打 AI），
    其余走 tactical + profile。若想定声明了增援，附带记录检定/入场结果
    （供"增援是否出现/几回合出场"观察）。"""
    scenario, seed, axis_p, allies_p = args
    try:
        report, engine, _ = run_match(
            scenario,
            axis="random" if axis_p == "random" else "tactical",
            allies="random" if allies_p == "random" else "tactical",
            axis_profile=None if axis_p == "random" else axis_p,
            allies_profile=None if allies_p == "random" else allies_p,
            seed=seed,
        )
        state = engine.get(report.game_id) if report.game_id else None
        final_turn = state.turn if state else None
        reinforcement: dict[str, Any] | None = None
        if state is not None and state.reinforcement_trigger_turn is not None:
            reinforcement = {
                "trigger_turn": state.reinforcement_trigger_turn,
                "arrival_turn": state.reinforcement_arrival_turn,
                "roll_done": state.reinforcement_roll_done,
                "available": state.reinforcement_available,
                "entered": sum(
                    1 for ship in state.ships.values()
                    if ship.reinforcement_turn is not None and ship.position is not None
                ),
            }
        return {
            "scenario": scenario,
            "seed": seed,
            "axis_profile": axis_p,
            "allies_profile": allies_p,
            "winner": report.winner.value if report.winner else None,
            "completed": report.completed,
            "passed": report.passed,
            "final_turn": final_turn,
            "victory_reason": report.victory_reason,
            "elapsed_ms": report.elapsed_ms,
            "failure_reason": report.failure_reason,
            "reinforcement": reinforcement,
        }
    except Exception as error:  # 一局失败不影响整批；如实记录
        return {
            "scenario": scenario,
            "seed": seed,
            "axis_profile": axis_p,
            "allies_profile": allies_p,
            "error": f"{type(error).__name__}: {error}",
        }


def _empty_stats() -> dict[str, Any]:
    return {
        "axis_games": 0, "axis_wins": 0,
        "allies_games": 0, "allies_wins": 0,
        "draws": 0, "errors": 0,
    }


def aggregate(results: list[dict[str, Any]], profiles: list[str]) -> dict[str, Any]:
    """把逐局结果聚合为：风格胜率（按阵营分列 + 合计）、组合矩阵、结局分布、增援观察。"""
    stats: dict[str, dict[str, Any]] = {p: _empty_stats() for p in profiles}
    matrix: dict[str, Counter] = {}
    victory_reasons: Counter[str] = Counter()
    failed: list[dict[str, Any]] = []
    reinforcements: Counter[str] = Counter()
    entered_total = 0
    reinforcement_games = 0

    for r in results:
        if "error" in r:
            failed.append(r)
            stats[r["axis_profile"]]["errors"] += 1
            stats[r["allies_profile"]]["errors"] += 1
            continue
        pair = f"{r['axis_profile']} vs {r['allies_profile']}"
        cell = matrix.setdefault(pair, Counter())
        winner = r["winner"]
        # 每局双方各计 1 场（该方视角）；胜者方记 win，无胜者记 draw。
        stats[r["axis_profile"]]["axis_games"] += 1
        stats[r["allies_profile"]]["allies_games"] += 1
        if winner == Side.AXIS.value:
            stats[r["axis_profile"]]["axis_wins"] += 1
            cell["axis"] += 1
        elif winner == Side.ALLIES.value:
            stats[r["allies_profile"]]["allies_wins"] += 1
            cell["allies"] += 1
        else:
            stats[r["axis_profile"]]["draws"] += 1
            stats[r["allies_profile"]]["draws"] += 1
            cell["draw"] += 1
        if r.get("victory_reason"):
            victory_reasons[r["victory_reason"]] += 1
        ref = r.get("reinforcement")
        if ref is not None:
            reinforcement_games += 1
            entered_total += ref["entered"]
            reinforcements["roll_done"] += 1 if ref["roll_done"] else 0
            reinforcements["available"] += 1 if ref["available"] else 0
            reinforcements["entered>0"] += 1 if ref["entered"] > 0 else 0
            reinforcements["all_entered"] += 1 if ref["entered"] == 8 else 0

    for p, s in stats.items():
        s["total_games"] = s["axis_games"] + s["allies_games"]
        s["axis_win_rate"] = (s["axis_wins"] / s["axis_games"]) if s["axis_games"] else None
        s["allies_win_rate"] = (s["allies_wins"] / s["allies_games"]) if s["allies_games"] else None
        s["overall_win_rate"] = (
            (s["axis_wins"] + s["allies_wins"]) / s["total_games"] if s["total_games"] else None
        )

    reinforcement_stats: dict[str, Any] | None = None
    if reinforcement_games:
        reinforcement_stats = {
            "games": reinforcement_games,
            **dict(reinforcements),
            "avg_entered": round(entered_total / reinforcement_games, 2),
        }

    return {
        "profiles": profiles,
        "stats": stats,
        "matrix": {pair: dict(cell) for pair, cell in sorted(matrix.items())},
        "victory_reasons": dict(victory_reasons.most_common()),
        "reinforcement": reinforcement_stats,
        "failed": failed,
        "summary": {
            "games_attempted": len(results),
            "games_completed": sum(1 for r in results if r.get("passed")),
            "games_failed": len(failed),
        },
    }


def run_benchmark(
    scenario: str,
    profiles: list[str] | None = None,
    total_games: int = 50,
    workers: int = 0,
    seed_base: int = 1,
    out: str | Path | None = None,
    progress: bool = True,
    per_pair: int | None = None,
) -> dict[str, Any]:
    """多进程（或串行 workers=0）跑基准并聚合。

    `per_pair` 给定时每对有序组合精确跑 N 局（覆盖 total_games 均摊）。
    `progress=True` 且并行时每完成 1/20 局打一行进度（观察过程）。
    out 非空时写 `bench-report.json`（全量逐局 + 聚合）、`bench-report.md`（人类可读表）
    与 `raw-games.jsonl`（逐局存档，供事后重放/交叉观察）。
    返回聚合 dict（含 raw=逐局结果）。
    """
    profiles = list(profiles or DEFAULT_PROFILES)
    games = build_games(scenario, profiles, total_games, seed_base, per_pair)
    started = time.perf_counter()
    total = len(games)

    if workers == 0 or total == 1:
        results = [_run_one(g) for g in games]
    else:
        results = []
        with ProcessPoolExecutor(max_workers=workers) as pool:
            step = max(1, total // 20)
            for index, result in enumerate(pool.map(_run_one, games, chunksize=4)):
                results.append(result)
                if progress and (index + 1) % step == 0:
                    print(f"  进度 {index + 1}/{total}", flush=True)
    wall = time.perf_counter() - started

    data = aggregate(results, profiles)
    data["meta"] = {
        "scenario": scenario,
        "total_games": total,
        "per_pair": per_pair,
        "profiles": profiles,
        "workers": workers,
        "seed_base": seed_base,
        "wall_seconds": round(wall, 2),
    }
    data["raw"] = results

    if out is not None:
        directory = Path(out)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "bench-report.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (directory / "bench-report.md").write_text(
            _markdown_report(data), encoding="utf-8"
        )
        (directory / "raw-games.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in results) + "\n",
            encoding="utf-8",
        )
    return data


def _markdown_report(data: dict[str, Any]) -> str:
    meta = data["meta"]
    lines = [
        f"# 风格状态机对战基准 · {meta['scenario']}",
        "",
        f"- 局数：{meta['total_games']}（并行 workers={meta['workers']}，"
        f"墙钟 {meta['wall_seconds']}s）",
        f"- 参赛者：{', '.join(meta['profiles'])}"
        + (f"；每对 {meta['per_pair']} 局" if meta.get("per_pair") else ""),
        f"- 完成 {data['summary']['games_completed']}/{data['summary']['games_attempted']}，"
        f"失败 {data['summary']['games_failed']}",
        "",
        "## 各风格胜率（按阵营分列；合计 = 该风格任一阵营取胜的局数占比）",
        "",
        "| 风格 | 作轴心 局 | 轴心胜率 | 作盟军 局 | 盟军胜率 | 合计 局 | 合计胜率 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for p, s in data["stats"].items():
        lines.append(
            f"| {p} | {s['axis_games']} | {_fmt(s['axis_win_rate'])} | "
            f"{s['allies_games']} | {_fmt(s['allies_win_rate'])} | "
            f"{s['total_games']} | {_fmt(s['overall_win_rate'])} |"
        )
    lines += ["", "## 组合矩阵（行=轴心风格，列=盟军风格：轴胜/盟胜/平）", "",
              "| 轴\\盟 | " + " | ".join(data["profiles"]) + " |",
              "|---" + "|---" * len(data["profiles"]) + "|"]
    for a in data["profiles"]:
        row = [f"**{a}**"]
        for b in data["profiles"]:
            if a == b:
                row.append("—")
            else:
                cell = data["matrix"].get(f"{a} vs {b}", {})
                row.append(f"{cell.get('axis', 0)}/{cell.get('allies', 0)}/{cell.get('draw', 0)}")
        lines.append("| " + " | ".join(row) + " |")
    ref = data.get("reinforcement")
    if ref is not None:
        lines += [
            "",
            "## 增援观察（想定增援：检定成功才入场）",
            "",
            f"- 计入局数：{ref['games']}",
            f"- 检定已掷：{ref['roll_done']}/{ref['games']}",
            f"- 检定成功（可用）：{ref['available']}/{ref['games']}"
            f"（{ref['available'] / ref['games']:.1%}）",
            f"- 有舰入场：{ref['entered>0']}/{ref['games']}",
            f"- 八舰全部入场：{ref['all_entered']}/{ref['games']}",
            f"- 平均入场舰数：{ref['avg_entered']}",
            "",
        ]
    lines += ["## 结局类型分布", ""]
    for reason, count in data["victory_reasons"].items():
        lines.append(f"- {reason}：{count}")
    if data["failed"]:
        lines += ["", "## 失败局", ""]
        for r in data["failed"]:
            lines.append(f"- seed {r['seed']} {r['axis_profile']} vs {r['allies_profile']}: {r['error']}")
    return "\n".join(lines) + "\n"


def _fmt(rate: float | None) -> str:
    return "—" if rate is None else f"{rate:.1%}"


def _print_summary(data: dict[str, Any]) -> None:
    meta = data["meta"]
    s = data["summary"]
    print(f"场景 {meta['scenario']} · {meta['total_games']} 局 · workers={meta['workers']} · "
          f"墙钟 {meta['wall_seconds']}s · 完成 {s['games_completed']}/{s['games_attempted']} "
          f"失败 {s['games_failed']}")
    ref = data.get("reinforcement")
    if ref is not None:
        print(f"增援：检定成功 {ref['available']}/{ref['games']}"
              f"（{ref['available'] / ref['games']:.1%}）· 有舰入场 {ref['entered>0']} 局 · "
              f"平均入场 {ref['avg_entered']} 舰")
    print()
    print(f"{'风格':<10}{'轴心':>10}{'盟军':>10}{'合计':>10}")
    for p, st in data["stats"].items():
        print(f"{p:<10}"
              f"{_fmt(st['axis_win_rate']):>10}"
              f"{_fmt(st['allies_win_rate']):>10}"
              f"{_fmt(st['overall_win_rate']):>10}")
    print()
    print("组合矩阵（行=轴心，列=盟军；轴胜/盟胜/平）:")
    header = "        " + "".join(f"{p:>12}" for p in data["profiles"])
    print(header)
    for a in data["profiles"]:
        cells = []
        for b in data["profiles"]:
            if a == b:
                cells.append(f"{'—':>12}")
            else:
                cell = data["matrix"].get(f"{a} vs {b}", {})
                cells.append(f"{cell.get('axis', 0)}/{cell.get('allies', 0)}/{cell.get('draw', 0)}".rjust(12))
        print(f"{a:<8}" + "".join(cells))


def main() -> int:
    parser = argparse.ArgumentParser(description="风格状态机对战基准（多进程并行 + 胜率聚合）")
    parser.add_argument("--scenario", default="IBS-S-03", choices=("IBS-S-01", "IBS-S-03"))
    parser.add_argument("--games", type=int, default=50, help="总局数，按轮转分布到全部风格组合")
    parser.add_argument("--per-pair", type=int, default=None,
                        help="每对有序组合精确跑 N 局（覆盖 --games 均摊；如 30）")
    parser.add_argument("--profiles", default=None,
                        help="逗号分隔的风格子集（默认全部 6 种 + random）")
    parser.add_argument("--workers", type=int, default=0,
                        help="进程数；0 = min(8, cpu_count)，-1 = 串行")
    parser.add_argument("--seed-base", type=int, default=1)
    parser.add_argument("--out", type=Path, default=None, help="写 bench-report.json/.md/raw-games.jsonl 的目录")
    args = parser.parse_args()

    profiles = [p.strip() for p in args.profiles.split(",")] if args.profiles else None
    if profiles:
        unknown = set(profiles) - _KNOWN_PROFILES
        if unknown:
            raise SystemExit(f"未知风格 {sorted(unknown)}；可用 {sorted(_KNOWN_PROFILES)}")
    workers = args.workers
    if workers == 0:
        workers = min(8, os.cpu_count() or 1)
    if workers == -1:
        workers = 0

    data = run_benchmark(
        args.scenario, profiles=profiles, total_games=args.games,
        workers=workers, seed_base=args.seed_base, out=args.out,
        per_pair=args.per_pair,
    )
    _print_summary(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
