"""对训练出的 TacticalProfile 做全新 seed 的稳健性验证（防过拟合评估 seed）。

进化时评估 seed 按 (想定, 个体, 对手, 第k局) 派生（seed_base+…）。本工具用
**不相交的 fresh seed**（默认 seed_base=50000）重测：best 对每个**想定**、每个对手、
每个阵营打 N 局，输出胜率 + 平均 VP 差；同时可跑 balanced-vs-balanced 基线做语境。

产物（保留关键数据）：--out 下
  * verify-summary.json   逐想定×对手×阵营 胜率/VP 差/局数 + 跨想定 combined
  * verify-games.jsonl    逐局原始结果

运行（PYTHONPATH=backend/src）：
    python -X utf8 -m rl.verify --profile rl/results/ga-s03-small-v1/best-genome.json \
        --opponents balanced,fleet,line,brawl,torpedo,cautious --games 12 --workers 8 \
        --out rl/results/ga-s03-small-v1/verify-best
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from iron_bottom_sound.tactical import PROFILES, Side

from .evolve import GENE_NAMES, decode_genes, encode_profile, _run_one_game


@dataclass
class _Slot:
    opp: str
    side: str
    games: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    score_sum: int = 0
    margin_sum: int = 0
    goal_games: int = 0          # 达成剧本目标的局数（绝对锚点，见 _goal_achieved）
    reasons: Counter[str] = field(default_factory=Counter)  # 引擎裁决的胜负原因分布


def _goal_achieved(scenario: str, side: str, reason: str | None) -> bool:
    """S-03 想定的剧本目标达成判定（绝对标准，锚在游戏规则而非对手）。

    S-03 德军战术胜利是**默认兜底**（对方没达成目标就判德军胜，不等于德军干成了事）。
    只有"德军小型战略胜利"（击沉≥2英舰）才算轴心达成剧本目标；盟军任何胜利都要求
    击沉/减速德舰（英军战略/战术胜利）。S-01 用胜利点差，无兜底，不在此判定。"""
    if not reason:
        return False
    if scenario == "IBS-S-03":
        if side == "allies":
            return reason.startswith("英军")
        return reason == "德军小型战略胜利"
    return False


def _elo_delta(wins: int, draws: int, losses: int) -> float:
    """对锚点对手的 Elo 差：S = (胜 + 0.5平) / 局数；ΔElo = 400·log10(S/(1−S))。

    伪半局防除零：S' = (胜 + 0.5平 + 0.5) / (局数 + 1)。正 = 比锚点强。"""
    games = wins + draws + losses
    if games == 0:
        return 0.0
    s = (wins + 0.5 * draws + 0.5) / (games + 1)
    s = max(1e-6, min(1 - 1e-6, s))
    return 400.0 * math.log10(s / (1 - s))


def _load_genes(path: str | Path) -> list[float]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if "genes" in data:
        return list(data["genes"])
    return encode_profile(decode_genes_proxy(data))


def decode_genes_proxy(data: dict[str, Any]):
    """best-profile.json（TacticalProfile 序列化）→ TacticalProfile。"""
    from iron_bottom_sound.tactical import TacticalProfile
    return TacticalProfile(**data)


def verify(
    scenarios: list[str],
    genes: list[float],
    opponents: list[str],
    games: int,
    workers: int,
    seed_base: int,
    out: str | Path,
) -> dict[str, Any]:
    jobs: list[tuple] = []
    for scen_idx, scenario in enumerate(scenarios):
        for opp_idx, opp in enumerate(opponents):
            opp_genes = encode_profile(PROFILES[opp])
            for side in ("axis", "allies"):
                for k in range(games):
                    seed = seed_base + scen_idx * 7 + opp_idx * 1009 + (0 if side == "axis" else 1) * 101 + k
                    if side == "axis":
                        jobs.append((scenario, seed, genes, opp_genes, -1, side, opp))
                    else:
                        jobs.append((scenario, seed, opp_genes, genes, -1, side, opp))

    if workers <= 0:
        results = [_run_one_game(j) for j in jobs]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(_run_one_game, jobs, chunksize=8))

    slots: dict[tuple[str, str, str], _Slot] = {
        (scen, opp, side): _Slot(opp, side)
        for scen in scenarios for opp in opponents for side in ("axis", "allies")
    }
    raw_lines: list[dict[str, Any]] = []
    for (scenario, seed, _, _, _, ind_side, opp_name), res in zip(jobs, results):
        slot = slots[(scenario, opp_name, ind_side)]
        raw_lines.append({"scenario": scenario, "opponent": opp_name,
                          "side": ind_side, "seed": seed, **res})
        if res["error"]:
            continue
        slot.games += 1
        winner = res["winner"]
        if winner is None:
            slot.draws += 1
        elif winner == ind_side:
            slot.wins += 1
            slot.score_sum += 1
        else:
            slot.losses += 1
            slot.score_sum -= 1
        slot.margin_sum += (res["axis_score"] - res["allies_score"]) * (1 if ind_side == "axis" else -1)
        reason = res.get("victory_reason")
        slot.reasons[reason or "(平局/未标)"] += 1
        if _goal_achieved(scenario, ind_side, reason):
            slot.goal_games += 1

    summary: dict[str, Any] = {
        "scenarios": list(scenarios),
        "genes": genes,
        "per_scenario": {},
    }
    per_scen_combined: dict[str, float] = {}
    for scen in scenarios:
        summary["per_scenario"][scen] = {"opponents": {}}
        scen_wr: list[float] = []
        for opp in opponents:
            summary["per_scenario"][scen]["opponents"][opp] = {}
            for side in ("axis", "allies"):
                s = slots[(scen, opp, side)]
                n = max(1, s.games)
                summary["per_scenario"][scen]["opponents"][opp][side] = {
                    "games": s.games,
                    "win_rate": round(s.score_sum / n, 4),
                    "avg_margin": round(s.margin_sum / n, 2),
                    "goal_rate": round(s.goal_games / n, 4),  # 剧本目标达成率（绝对锚点）
                    "wins": s.wins, "draws": s.draws, "losses": s.losses,
                    "victory_reasons": dict(s.reasons.most_common()),
                }
            ax = summary["per_scenario"][scen]["opponents"][opp]["axis"]
            al = summary["per_scenario"][scen]["opponents"][opp]["allies"]
            combined = (ax["win_rate"] + al["win_rate"]) / 2
            summary["per_scenario"][scen]["opponents"][opp]["combined_win_rate"] = round(combined, 4)
            scen_wr.append(combined)
        # 想定级：各阵营的目标达成率（跨对手合并）
        scen_goal: dict[str, float] = {}
        for side in ("axis", "allies"):
            g, t = 0, 0
            for opp in opponents:
                s = slots[(scen, opp, side)]
                g += s.goal_games
                t += s.games
            scen_goal[side] = round(g / max(1, t), 4)
        summary["per_scenario"][scen]["goal_rate_by_side"] = scen_goal
        per_scen_combined[scen] = round(sum(scen_wr) / len(scen_wr), 4)
    summary["combined_win_rate"] = round(sum(per_scen_combined.values()) / len(per_scen_combined), 4)
    summary["per_scenario_combined"] = per_scen_combined

    # 绝对刻度：对 balanced 锚点的 Elo（锚=1500；分数=胜+0.5平，伪半局防 0/1 除零）
    if "balanced" in opponents:
        elo_delta = _elo_delta(
            sum(slots[(scen, "balanced", side)].wins for scen in scenarios for side in ("axis", "allies")),
            sum(slots[(scen, "balanced", side)].draws for scen in scenarios for side in ("axis", "allies")),
            sum(slots[(scen, "balanced", side)].losses for scen in scenarios for side in ("axis", "allies")),
        )
        summary["elo_vs_balanced_anchor"] = round(elo_delta, 1)

    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "verify-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "verify-games.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in raw_lines) + "\n",
        encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="全新 seed 稳健性验证（防过拟合）")
    parser.add_argument("--scenario", default="IBS-S-03,IBS-S-01",
                        help="想定（逗号分隔，默认两个都验）")
    parser.add_argument("--profile", required=True,
                        help="best-genome.json / champion-genome.json 或 *-profile.json 路径")
    parser.add_argument("--opponents", default="balanced,fleet,line,brawl,torpedo,cautious")
    parser.add_argument("--games", type=int, default=12, help="每个 (想定,对手,阵营) 打几局")
    parser.add_argument("--workers", type=int, default=0, help="0 = min(8, cpu)，-1 = 串行")
    parser.add_argument("--seed-base", type=int, default=50000,
                        help="fresh seed 基（与训练 seed 不相交）")
    parser.add_argument("--baseline", action="store_true",
                        help="额外跑 balanced-vs-balanced 同 seed 基线做语境")
    parser.add_argument("--out", default="rl/results/verify")
    args = parser.parse_args()

    import os
    workers = args.workers
    if workers == 0:
        workers = min(8, os.cpu_count() or 1)
    if workers == -1:
        workers = 0

    scenarios = [s.strip() for s in args.scenario.split(",")]
    genes = _load_genes(args.profile)
    opponents = [p.strip() for p in args.opponents.split(",")]
    print(f"[verify] {Path(args.profile).name} on {'+'.join(scenarios)} vs "
          f"{','.join(opponents)} · {args.games} 局/槽 · fresh seed {args.seed_base}+")
    summary = verify(scenarios, genes, opponents, args.games, workers,
                     args.seed_base, args.out)

    if args.baseline:
        base = encode_profile(PROFILES["balanced"])
        base_out = Path(args.out) / "baseline"
        baseline = verify(scenarios, base, ["balanced"], args.games, workers,
                          args.seed_base + 50000, base_out)
        print("\n基线 balanced vs balanced（同 seed 偏移）："
              f"combined {baseline['combined_win_rate']:+.3f}")

    print(f"\n{'想定':<10}{'对手':<10}{'阵营':>6}{'局数':>5}{'胜率':>8}{'均VP差':>8}{'目标达成率':>10}")
    for scen in scenarios:
        for opp in opponents:
            for side in ("axis", "allies"):
                r = summary["per_scenario"][scen]["opponents"][opp][side]
                print(f"{scen:<10}{opp:<10}{side:>6}{r['games']:>5}"
                      f"{r['win_rate']:>+8.3f}{r['avg_margin']:>+8.2f}"
                      f"{r['goal_rate']:>10.2%}")
        g = summary["per_scenario"][scen]["goal_rate_by_side"]
        print(f"  {scen} combined {summary['per_scenario_combined'][scen]:+.3f}  "
              f"｜ 目标达成率 轴心 {g['axis']:.2%} · 盟军 {g['allies']:.2%}")
    print(f"跨想定 combined {summary['combined_win_rate']:+.3f}")
    if "elo_vs_balanced_anchor" in summary:
        print(f"绝对刻度：Elo vs balanced 锚点 = "
              f"{summary['elo_vs_balanced_anchor']:+.0f}（锚=1500，正=比手调均衡强）")
    print(f"\n产物 → {Path(args.out) / 'verify-summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
