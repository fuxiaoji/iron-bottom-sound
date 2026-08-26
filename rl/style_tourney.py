"""风格混战赛（meta-game）：全部内置风格（+可选冠军）在指定想定上循环互殴。

目的：回答「想定 X 上，每个风格自己怎么样、两边（轴心/盟军）胜率如何、赢是怎么赢的」。
与 verify.py 的区别：verify 是「一个 profile 打一组固定对手」，本工具是**全互联互通**——
每种风格既当主角也当对手，输出逐风格（轴心/盟军）聚合 + 两两对阵矩阵 + 胜负原因分布。

对每对 (风格A, 风格B)，A 作轴心打 B 作盟军 + A 作盟军打 B 作轴心，各 games 局
（seed 按 (想定, A idx, B idx, 阵营, k) 确定性派生）。支持多想定（--scenario 逗号分隔），
S-01 想定尤其重要：它的胜率被「平局（胜利点差<4）」主导，只看胜率会漏掉「谁把平局局
转化为决定性胜利」。

运行（PYTHONPATH=backend/src）：
    python -X utf8 -m rl.style_tourney --scenario IBS-S-03,IBS-S-01 \
        --champion rl/results/ga-dual-med-v1/champion-genome.json \
        --games 12 --workers 16 --out rl/results/style-tourney-final
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from iron_bottom_sound.tactical import PROFILES

from .evolve import Config, encode_profile, _evaluate
from .verify import _load_genes


@dataclass
class _SideStats:
    games: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    score_sum: int = 0
    margin_sum: int = 0
    reasons: Counter[str] = field(default_factory=Counter)


def _build_jobs(scenarios: list[str], roster: list[tuple[str, list[float]]],
                games: int, seed_base: int) -> tuple[list[tuple], list[tuple]]:
    """返回 (jobs, job_meta)；job_meta 为 (scen_idx, style_idx, opp_idx, side)。

    每个 (风格A, 风格B) 有序对在每个想定上打两个阵营块：A 轴心 vs B 盟军、A 盟军 vs B 轴心。"""
    jobs: list[tuple] = []
    meta: list[tuple] = []
    for sci, scenario in enumerate(scenarios):
        for si, (sname, sgenes) in enumerate(roster):
            for oi, (oname, ogenes) in enumerate(roster):
                if si == oi:
                    continue
                for side in ("axis", "allies"):
                    for k in range(games):
                        seed = seed_base + sci * 7 + si * 1009 + oi * 101 \
                            + (0 if side == "axis" else 1) * 5 + k
                        if side == "axis":
                            jobs.append((scenario, seed, sgenes, ogenes, si, side, oname))
                        else:
                            jobs.append((scenario, seed, ogenes, sgenes, si, side, oname))
                        meta.append((sci, si, oi, side))
    return jobs, meta


def _aggregate(job_meta: list[tuple], results: list[dict],
               n_styles: int) -> tuple[dict[str, _SideStats], dict[str, dict[str, dict[str, float]]], dict[str, dict[str, float]]]:
    """按 (想定, 风格, 阵营) 聚合；另出两两对阵矩阵（按想定 + 跨想定合成）combined 差分。"""
    by_side: dict[tuple[str, str, str], _SideStats] = {}
    pair: dict[tuple[str, str, str], list[int]] = {}  # (scen, style, opp) -> score 列表
    for (sci, si, oi, side), res in zip(job_meta, results):
        if res["error"]:
            continue
        st = by_side.setdefault((sci, si, side), _SideStats())
        st.games += 1
        winner = res["winner"]
        if winner is None:
            st.draws += 1
        elif winner == side:
            st.wins += 1
            st.score_sum += 1
        else:
            st.losses += 1
            st.score_sum -= 1
        st.margin_sum += (res["axis_score"] - res["allies_score"]) * (1 if side == "axis" else -1)
        st.reasons[res.get("victory_reason") or "(平局/未标)"] += 1
        pair.setdefault((sci, si, oi), []).append(1 if winner == side else (0 if winner is None else -1))
    matrix_by_scen: dict[str, dict[str, dict[str, float]]] = {}
    pooled: dict[str, dict[str, list[int]]] = {}
    for (sci, si, oi), scores in pair.items():
        matrix_by_scen.setdefault(sci, {}).setdefault(si, {})[oi] = round(sum(scores) / len(scores), 3)
        pooled.setdefault(si, {}).setdefault(oi, []).extend(scores)
    matrix = {si: {oi: round(sum(v) / len(v), 3) for oi, v in row.items()}
              for si, row in pooled.items()}
    return by_side, matrix_by_scen, matrix


def _side_row(st: _SideStats) -> dict[str, Any]:
    n = max(1, st.games)
    return {
        "games": st.games, "wins": st.wins, "draws": st.draws, "losses": st.losses,
        "score_diff": round(st.score_sum / n, 3),
        "true_win_rate": round(st.wins / n, 3),
        "decisive_rate": round((st.wins + st.losses) / n, 3),
        "avg_margin": round(st.margin_sum / n, 2),
        "victory_reasons": dict(st.reasons.most_common()),
    }


def style_tourney(scenarios: list[str], roster: list[tuple[str, list[float]]],
                  games: int, workers: int, seed_base: int,
                  out: str | Path) -> dict[str, Any]:
    jobs, meta = _build_jobs(scenarios, roster, games, seed_base)
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    games_fh = (out_dir / "games.jsonl").open("w", encoding="utf-8")

    def on_game(job, res):
        _, seed, _, _, si, side, oname = job
        sname = roster[si][0]
        games_fh.write(json.dumps(
            {"style": sname, "opponent": oname, "side": side, "seed": seed, **res},
            ensure_ascii=False) + "\n")
        games_fh.flush()

    pool = ProcessPoolExecutor(max_workers=workers) if workers > 0 else None
    results = _evaluate(jobs, Config(), pool, on_game)
    if pool is not None:
        pool.shutdown()
    games_fh.close()

    by_side, matrix_by_scen, matrix = _aggregate(meta, results, len(roster))

    summary: dict[str, Any] = {
        "scenarios": list(scenarios), "games_per_slot": games, "seed_base": seed_base,
        "roster": [n for n, _ in roster], "styles": {},
    }
    for si, (sname, _) in enumerate(roster):
        per_scen: dict[str, Any] = {}
        scen_combined: list[float] = []
        for sci, scen in enumerate(scenarios):
            ax = _side_row(by_side.get((sci, si, "axis"), _SideStats()))
            al = _side_row(by_side.get((sci, si, "allies"), _SideStats()))
            combined = round((ax["score_diff"] + al["score_diff"]) / 2, 3)
            per_scen[scen] = {"axis": ax, "allies": al, "combined": combined}
            scen_combined.append(combined)
        summary["styles"][sname] = {
            "scenarios": per_scen,
            "combined": round(sum(scen_combined) / len(scen_combined), 3),
            "matrix": {roster[oi][0]: v for oi, v in matrix.get(si, {}).items()},
            "matrix_by_scenario": {
                scenarios[sci]: {roster[oi][0]: v for oi, v in matrix_by_scen.get(sci, {}).get(si, {}).items()}
                for sci in range(len(scenarios))
            },
        }

    (out_dir / "style-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="风格混战赛：内置风格（+冠军）互殴")
    parser.add_argument("--scenario", default="IBS-S-01", help="想定（逗号分隔，多个都打）")
    parser.add_argument("--styles", default=",".join(PROFILES),
                        help="内置风格名单（默认全部 6 个）")
    parser.add_argument("--champion", default=None,
                        help="冠军 genome/profile 路径（加入混战，默认不带）")
    parser.add_argument("--games", type=int, default=12, help="每 (风格,对手,阵营,想定) 局数")
    parser.add_argument("--workers", type=int, default=0, help="0 = min(8, cpu)")
    parser.add_argument("--seed-base", type=int, default=60000)
    parser.add_argument("--out", default="rl/results/style-tourney")
    args = parser.parse_args()

    import os
    workers = args.workers
    if workers == 0:
        workers = min(8, os.cpu_count() or 1)

    roster: list[tuple[str, list[float]]] = [
        (name, encode_profile(PROFILES[name])) for name in args.styles.split(",")
    ]
    if args.champion:
        roster.append(("champion", _load_genes(args.champion)))
    scenarios = [s.strip() for s in args.scenario.split(",")]

    print(f"[style_tourney] {'+'.join(scenarios)} · {len(roster)} 风格（"
          f"{','.join(n for n, _ in roster)}）· {args.games} 局/槽 · workers {workers}")
    summary = style_tourney(scenarios, roster, args.games, workers,
                            args.seed_base, args.out)
    st = summary["styles"]

    for sci, scen in enumerate(scenarios):
        print(f"\n== {scen} ==")
        print(f"{'风格':<10}{'阵营':>6}{'局数':>5}{'胜':>4}{'平':>4}{'负':>4}"
              f"{'胜率差分':>8}{'真实胜率':>8}{'决定性率':>8}{'均VP差':>8}")
        for name in summary["roster"]:
            for side in ("axis", "allies"):
                r = st[name]["scenarios"][scen][side]
                print(f"{name:<10}{side:>6}{r['games']:>5}{r['wins']:>4}{r['draws']:>4}"
                      f"{r['losses']:>4}{r['score_diff']:>+8.3f}{r['true_win_rate']:>8.3f}"
                      f"{r['decisive_rate']:>8.3f}{r['avg_margin']:>+8.2f}")
            print(f"  {name} {scen} combined {st[name]['scenarios'][scen]['combined']:+.3f}")

    print("\n两两对阵（行风格作轴心的胜率差分，跨想定合成；正=行吃列）：")
    names = summary["roster"]
    print(f"{'':<10}" + "".join(f"{n:>10}" for n in names))
    for rname in names:
        row = st[rname]["matrix"]
        cells = []
        for cname in names:
            v = row.get(cname)
            cells.append(f"{v:>+10.3f}" if v is not None else f"{'-':>10}")
        print(f"{rname:<10}" + "".join(cells))

    print(f"\n跨想定综合（标注用）：")
    for name in summary["roster"]:
        print(f"  {name:<10} {st[name]['combined']:+.3f}")
    print(f"\n产物 → {Path(args.out) / 'style-summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
