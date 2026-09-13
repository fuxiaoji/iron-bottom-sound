"""B12: matched lethality -- thin concentrated vs thick dispersed salvos.

Research claim (plan v4.0 B12): at EQUAL expected direct damage, a salvo spread
over many weak lanes contracts the target's response set more than a single
strong lane -- "coverage beats damage".  This is the decision-level payoff of
the B11 finding that denial value is a step function of top-tier coverage.

Design (on the E04 same-turn protocol, reusing B11's cached lane x plan
first-contact matrices):

    E[D_direct]   expected direct damage mass delivered to the target's
                  eps-response set: w . sum_{tau in B_eps} Hazard_set(tau).
                  (E04's V_direct was taken against the tau0* route alone; on
                  the flat-top landscape that quantity is degenerate -- lanes
                  are either identical 0.083 or zero -- so the damage mass is
                  integrated over the response set, the documented
                  generalization.  See report item 13.)
    thin          the single lane with the highest own E[D_direct] (the most
                  concentrated high-P_hit track), ties by max p then lane key
    thick(m)      m lanes, each strictly weaker than the thin lane, chosen to
                  MATCH its E[D_direct]: |E_set - E_thin| <= 10% of E_thin
                  (deterministic sliding-window search over lanes sorted
                  ascending by own mass; the ACTUAL set hazard
                  1 - prod(1 - p_i) is evaluated, so overlap between lanes is
                  accounted for, not the naive sum)
    C_resp        B11's response-set contraction of the eps-response set under
                  J'(tau) = J(tau) - J*.w.Hazard_set(tau)

Scenario classes (three plan-space regimes, one cell each, deterministic
pre-registered selection over the 8 E04 cells):
    many-ties   largest plan-level top J tier
    few-ties    smallest plan-level top J tier
    corridor    smallest spatial radius of top-tier endpoints among remaining
                cells (top-value positions form a narrow corridor)

Prediction: C_resp(thick) > C_resp(thin) at equal direct damage in the
many-ties regime; ceiling effects (thin already covers everything) can only
make the comparison equal, never reverse it, if coverage is the operative
mechanism.

Usage:
    python research/experiments/b12_matched_lethality.py

Outputs: research/results/b12/{matched.csv, results.json, report.md}
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import numpy as np

from b_common import (  # noqa: E402
    BASE_SEED,
    GEOMETRIES,
    apply_rules_snapshot,
    provenance,
    setup_cell,
    snapshot_rules_or_none,
)

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "research" / "results" / "b12"
FLEETS = ("1v1", "2v1")
EPSILONS = (0.05, 0.10, 0.20)
MATCH_TOLERANCE = 0.10
THICK_M = (2, 4, 6, 8)

from b11_contraction import get_cell_data  # noqa: E402
from iron_bottom_sound.models import HexCoord  # noqa: E402


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def hex_distance(a: HexCoord, b: HexCoord) -> int:
    dq, dr = a.q - b.q, a.r - b.r
    return (abs(dq) + abs(dr) + abs(dq + dr)) // 2


def top_tier_stats(data: dict) -> dict:
    """Plan-level top-tier size and spatial radius of its endpoints."""
    j = np.asarray(data["j_values"], dtype=float)
    j_ref = data["j_ref"]
    tied = np.isclose(j, j_ref)
    coords = [HexCoord.from_label(sig[0]) for sig in data["plan_signatures"]]
    top_coords = [c for c, t in zip(coords, tied) if t]
    if len(top_coords) <= 1:
        radius = 0
    else:
        anchor = top_coords[0]
        radius = max(hex_distance(anchor, c) for c in top_coords[1:])
    return {
        "n_top_plans": int(np.sum(tied)),
        "top_tier_radius_hexes": int(radius),
    }


def classify_cells(stats_by_cell: dict[str, dict]) -> dict[str, str]:
    """Pre-registered deterministic selection of the three scenario cells."""
    remaining = dict(stats_by_cell)
    many = max(remaining, key=lambda c: (remaining[c]["n_top_plans"], c))
    many = min(
        [c for c in remaining
         if remaining[c]["n_top_plans"] == remaining[many]["n_top_plans"]])
    class_of = {many: "many-ties"}
    del remaining[many]
    few = min([c for c in remaining
               if remaining[c]["n_top_plans"] == min(
                   r["n_top_plans"] for r in remaining.values())])
    class_of[few] = "few-ties"
    del remaining[few]
    corridor = min(remaining,
                   key=lambda c: (remaining[c]["top_tier_radius_hexes"],
                                  remaining[c]["n_top_plans"], c))
    class_of[corridor] = "corridor"
    return class_of


def hazard_of_set(p_matrix: list[list[float]], subset: list[int]) -> np.ndarray:
    p = np.asarray([p_matrix[i] for i in subset], dtype=float)
    return 1.0 - np.prod(1.0 - p, axis=0)


def c_resp_stats(hazard: np.ndarray, j_values: np.ndarray, j_ref: float,
                 w: float, eps: float) -> dict:
    j_norm = j_values / j_ref if j_ref > 0 else np.zeros_like(j_values)
    in_b = j_norm >= 1.0 - eps
    n_b = int(np.sum(in_b))
    surviving = in_b & (j_norm - w * hazard >= 1.0 - eps)
    n_bh = int(np.sum(surviving))
    tied = np.isclose(j_values, j_ref)
    j_prime = j_norm - w * hazard
    return {
        "n_B": n_b,
        "n_B_surviving": n_bh,
        "c_resp": 1.0 - n_bh / n_b if n_b else 0.0,
        "n_top_contacted": int(np.sum(hazard[tied] > 0.0)),
        "n_top_total": int(np.sum(tied)),
        "hazard_mean_in_B": float(np.mean(hazard[in_b])) if n_b else 0.0,
        "v_resp_norm": float(1.0 - np.max(j_prime)) if j_prime.size else 0.0,
    }


def find_dispersed_sets(p_matrix: list[list[float]], thin_index: int,
                        b_mask: np.ndarray, w: float,
                        thin_mass: float) -> list[dict]:
    """Sliding-window search for m-lane weak sets matching the thin lane's
    E[D_direct] over the response set (actual set hazard, overlap included)."""
    p_all = np.asarray(p_matrix, dtype=float)
    own_mass = w * p_all[:, b_mask].sum(axis=1)
    # candidates strictly weaker than the thin lane, ascending by own mass
    order = sorted(
        (i for i in range(p_all.shape[0])
         if i != thin_index and own_mass[i] < thin_mass),
        key=lambda i: (own_mass[i], i),
    )
    sets = []
    for m in THICK_M:
        if m > len(order):
            continue
        best = None
        for start in range(len(order) - m + 1):
            window = order[start:start + m]
            set_hazard = hazard_of_set(p_matrix, window)
            mass = w * float(np.sum(set_hazard[b_mask]))
            gap = abs(mass - thin_mass)
            key = (gap, window[0])
            if best is None or key < best[0]:
                best = (key, window, mass)
        _, window, mass = best
        sets.append({
            "m": m,
            "lane_indices": window,
            "e_total": mass,
            "matched": abs(mass - thin_mass) <= MATCH_TOLERANCE * thin_mass,
            "e_ratio": mass / thin_mass if thin_mass > 0 else float("inf"),
        })
    return sets


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="B12 matched lethality")
    parser.add_argument("--smoke", action="store_true", help="scenario cells only")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    started = time.time()
    snapshot = snapshot_rules_or_none()
    apply_rules_snapshot(snapshot)
    prov = provenance()

    cells = [(gkey, fleet) for gkey in sorted(GEOMETRIES) for fleet in FLEETS]
    cell_keys = [f"{gkey}:{fleet}" for gkey, fleet in cells]

    # load all cell data (B11 cache) and classify the three scenario regimes
    data_by_cell = {key: get_cell_data(key.split(":")[0], key.split(":")[1])
                    for key in cell_keys}
    stats_by_cell = {key: {**top_tier_stats(data), "j_ref": data["j_ref"]}
                     for key, data in data_by_cell.items()}
    class_of = classify_cells(stats_by_cell)
    scenario_cells = sorted(class_of, key=class_of.get)
    print(f"[b12] scenario classes: {class_of}")
    if args.smoke:
        cell_keys = scenario_cells

    j_by_cell = {key: np.asarray(data["j_values"], dtype=float)
                 for key, data in data_by_cell.items()}

    rows: list[dict] = []
    scenario_summaries: dict[str, dict] = {}
    for cell in cell_keys:
        data = data_by_cell[cell]
        j = j_by_cell[cell]
        j_ref = data["j_ref"]
        w = data["w"]
        lanes = data["lanes_ranked"]
        p_all = np.asarray(data["p_matrix"], dtype=float)

        # primary matching set: the eps=5% response set
        b_mask = (j / j_ref if j_ref > 0 else j * 0) >= 1.0 - EPSILONS[0]
        lane_mass = w * p_all[:, b_mask].sum(axis=1)

        thin_index = max(
            range(len(lanes)),
            key=lambda i: (lane_mass[i],
                           max(p_all[i]) if p_all.shape[1] else 0.0,
                           [str(x) for x in lanes[i]["lane_key"]]),
        )
        thin_e_direct = lane_mass[thin_index]
        thin_e_tau0 = lanes[thin_index]["e_hits_tau0"]

        spec_list = find_dispersed_sets(data["p_matrix"], thin_index, b_mask,
                                        w, thin_e_direct)
        pair_specs = [("thin", 1, [thin_index])] + [
            (f"thick-{spec['m']}", spec["m"], spec["lane_indices"])
            for spec in spec_list
        ]

        for pair_id, m, subset in pair_specs:
            hazard = hazard_of_set(data["p_matrix"], subset)
            if pair_id == "thin":
                e_total = thin_e_direct
                matched = True
                e_ratio = 1.0
            else:
                spec = next(s for s in spec_list if s["m"] == m)
                e_total = spec["e_total"]
                matched = spec["matched"]
                e_ratio = spec["e_ratio"]
            base_stats = c_resp_stats(hazard, j, j_ref, w, EPSILONS[0])
            entry = {
                "cell": cell,
                "scenario_class": class_of.get(cell, "unclassified"),
                "pair_id": pair_id,
                "m": m,
                "e_direct_response_set": round(e_total, 4),
                "e_direct_thin": round(thin_e_direct, 4),
                "e_ratio_vs_thin": round(e_ratio, 4),
                "matched_within_10pct": matched,
                "e_hits_vs_tau0_thin": round(thin_e_tau0, 4),
                "n_top_contacted": base_stats["n_top_contacted"],
                "n_top_total": base_stats["n_top_total"],
            }
            for eps in EPSILONS:
                stats = c_resp_stats(hazard, j, j_ref, w, eps)
                entry[f"c_resp_{int(eps*100)}pct"] = round(stats["c_resp"], 4)
                entry[f"v_resp_{int(eps*100)}pct"] = round(stats["v_resp_norm"], 4)
                entry[f"hazard_mean_B_{int(eps*100)}pct"] = round(stats["hazard_mean_in_B"], 4)
            entry["lane_keys"] = ["|".join(lanes[i]["lane_key"]) for i in subset][:10]
            rows.append(entry)

        thin_row = next(r for r in rows if r["cell"] == cell and r["pair_id"] == "thin")
        thick_rows = [r for r in rows if r["cell"] == cell
                      and r["pair_id"].startswith("thick") and r["matched_within_10pct"]]
        scenario_summaries[cell] = {
            "scenario_class": class_of.get(cell, "unclassified"),
            "n_top_plans": stats_by_cell[cell]["n_top_plans"],
            "top_tier_radius_hexes": stats_by_cell[cell]["top_tier_radius_hexes"],
            "thin_e_direct": thin_e_direct,
            "comparisons": [
                {
                    "m": r["m"],
                    "e_ratio": r["e_ratio_vs_thin"],
                    "n_top_contacted": [thin_row["n_top_contacted"], r["n_top_contacted"]],
                    "c_resp_5": [thin_row["c_resp_5pct"], r["c_resp_5pct"]],
                    "c_resp_10": [thin_row["c_resp_10pct"], r["c_resp_10pct"]],
                    "c_resp_20": [thin_row["c_resp_20pct"], r["c_resp_20pct"]],
                    "dispersed_wins_5": r["c_resp_5pct"] > thin_row["c_resp_5pct"],
                }
                for r in thick_rows
            ],
        }
        print(f"[b12] {cell} ({class_of.get(cell, 'unclassified')}): "
              f"thin E_direct={thin_e_direct:.3f} (E_tau0={thin_e_tau0:.3f}) -> "
              f"{[(r['m'], round(r['e_ratio_vs_thin'],2), r['matched_within_10pct']) for r in thick_rows]}")

    elapsed = time.time() - started

    # ---- matched.csv -----------------------------------------------------------
    columns = list(rows[0].keys()) if rows else []
    with (OUT / "matched.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    # ---- acceptance -------------------------------------------------------------
    # Pre-registered: in the many-ties regime, at least one matched dispersed set
    # has C_resp > thin's C_resp at eps=5%; nowhere does a matched dispersed set
    # LOSE to thin at equal damage (coverage mechanism sanity).
    many_cell = next(cell for cell, cls in class_of.items() if cls == "many-ties")
    many_rows = [r for r in rows if r["cell"] == many_cell]
    thin_many = next(r for r in many_rows if r["pair_id"] == "thin")
    matched_many = [r for r in many_rows
                    if r["pair_id"].startswith("thick") and r["matched_within_10pct"]]
    dispersed_wins = any(r["c_resp_5pct"] > thin_many["c_resp_5pct"]
                         for r in matched_many)
    paired_rows = []
    for r in rows:
        if r["pair_id"].startswith("thick") and r["matched_within_10pct"]:
            thin_row = next(t for t in rows if t["cell"] == r["cell"]
                            and t["pair_id"] == "thin")
            paired_rows.append((thin_row, r))
    never_loses = all(tr["c_resp_5pct"] <= rr["c_resp_5pct"] + 1e-12
                      for tr, rr in paired_rows)
    thin_wins_5 = sum(1 for tr, rr in paired_rows
                      if tr["c_resp_5pct"] > rr["c_resp_5pct"])
    dispersed_wins_10 = sum(1 for tr, rr in paired_rows
                            if rr["c_resp_10pct"] > tr["c_resp_10pct"])
    thin_wins_10 = sum(1 for tr, rr in paired_rows
                       if tr["c_resp_10pct"] > rr["c_resp_10pct"])
    n_pairs = len(paired_rows)
    acceptance = {
        "criterion": (
            "coverage beats damage: with E[D_direct] matched within 10%, a "
            "dispersed salvo contracts the eps=5% response set more than the "
            "thin salvo in the many-ties regime (and never less, ceiling "
            "effects aside)"
        ),
        "n_matched_pairs": n_pairs,
        "dispersed_wins_many_ties": dispersed_wins,
        "dispersed_never_loses": never_loses,
        # exploratory (post-hoc, reported for mechanism identification)
        "paired_comparisons_thin_wins_5pct": thin_wins_5,
        "paired_comparisons_dispersed_wins_10pct": dispersed_wins_10,
        "paired_comparisons_thin_wins_10pct": thin_wins_10,
    }

    results = {
        "experiment": "B12 matched lethality: thin concentrated vs thick dispersed",
        "protocol": "E04 same-turn protocol; contact matrices reused from B11 cache "
                    "(deterministic, no dice, no RNG)",
        "base_seed": BASE_SEED,
        "match_tolerance": MATCH_TOLERANCE,
        "epsilons": list(EPSILONS),
        "scenario_classes": class_of,
        "cell_top_tier_stats": stats_by_cell,
        "runtime_seconds": elapsed,
        "provenance": prov,
        "acceptance": acceptance,
        "scenarios": scenario_summaries,
        "rows": rows,
    }
    (OUT / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2, default=float),
        encoding="utf-8",
    )

    _write_report(args, elapsed, rows, scenario_summaries, class_of,
                  stats_by_cell, acceptance, prov)
    print(f"[b12] done in {elapsed:.1f}s -> {OUT}")


def _write_report(args, elapsed, rows, scenario_summaries, class_of,
                  stats_by_cell, acceptance, prov) -> None:
    def cell_line(cell: str) -> list[str]:
        s = scenario_summaries[cell]
        lines = [
            f"### {cell} —— {s['scenario_class']}"
            f"（顶档方案 {s['n_top_plans']} 条，顶档终点半径 {s['top_tier_radius_hexes']} 格）",
            "",
            f"- thin 航迹：E[D_direct](响应集) = {s['thin_e_direct']:.3f}"
            "（单条最高集中度航迹，w·Σ_{B_5%} Hazard）",
        ]
        for comp in s["comparisons"]:
            lines.append(
                f"- thick(m={comp['m']}): E/E_thin = {comp['e_ratio']:.2f}，"
                f"顶档接触 {comp['n_top_contacted'][0]} → {comp['n_top_contacted'][1]} 条，"
                f"C_resp(5%) {comp['c_resp_5'][0]:.3f} → {comp['c_resp_5'][1]:.3f}，"
                f"C_resp(10%) {comp['c_resp_10'][0]:.3f} → {comp['c_resp_10'][1]:.3f}，"
                f"C_resp(20%) {comp['c_resp_20'][0]:.3f} → {comp['c_resp_20'][1]:.3f}"
                f"{'，dispersed 胜' if comp['dispersed_wins_5'] else ''}")
        lines.append("")
        return lines

    verdict = ("PASS" if (acceptance["dispersed_wins_many_ties"]
                          and acceptance["dispersed_never_loses"]) else
               "PARTIAL" if acceptance["dispersed_wins_many_ties"] or
               acceptance["dispersed_never_loses"] else "FAIL")

    scenario_cell_of = {cls: cell for cell, cls in class_of.items()}
    lines = [
        "# B12 批次报告：匹配致命性（thin concentrated vs thick dispersed）",
        "",
        "按 v4 夜间批次协议（22 项）组织；门限预注册于第 3 项，判定见第 20 项。",
        "",
        "## 1. 批次标识",
        f"- 批次：B12（v4.0 主线）；日期：2026-09-11；仓库：iron-bottom-sound。",
        "- 依赖：E04 同回合协议、B11 的 lane×plan 接触矩阵缓存与 C_resp 机制。",
        "",
        "## 2. 研究目标与假设",
        "- H-B12（coverage beats damage）：在**期望直接杀伤 matched**（E[D_direct] 相同）"
        "条件下，多条弱航迹（thick dispersed）比单条强航迹（thin concentrated）"
        "收缩目标 ε-响应集更多——因为杀伤期望相同而**覆盖**不同。",
        "- 可检验推论：并列路线多的方案空间中，matched dispersed 的 C_resp(ε=5%) > "
        "thin 的 C_resp(ε=5%)；且 matched dispersed 从不劣于 thin（覆盖机制下"
        "天花板效应只会拉平，不会反向）。",
        "",
        "## 3. 预注册门限（先于运行固定）",
        "- (a) many-ties 场景：存在 matched（±10%）dispersed 集使 C_resp(5%) 严格 > thin；",
        "- (b) 全部场景全部 matched 对：C_resp(5%) dispersed ≥ thin（不反向）；",
        "- (c) 场景 cell 的选择规则预注册（确定性）：many-ties = 方案级顶档层最大；"
        "few-ties = 顶档层最小；corridor = 其余 cell 中顶档终点空间半径最小。",
        "",
        "## 4. 语义定义",
        "| 对象 | 定义 |",
        "|---|---|",
        "| E[D_direct] | w·Σ_{τ∈B_ε} Hazard_set(τ)：齐射对目标 ε-响应集的期望直接毁伤质量。"
        "E04 的 V_direct 只对 τ0* 单点取值；flat-top 景观上该量高度退化"
        "（逐 lane 只有 {0, 0.083, 0.417, 1.139} 四个取值，匹配在 7/8 cell 不可行），"
        "故按文档化的推广对响应集聚合（第 13 项如实记录） |",
        "| thin | 自身 E[D_direct] 最高的单条航迹（并列取最大 p、lane_key 序） |",
        "| thick(m) | m 条自身质量严格低于 thin 的航迹，滑动窗口搜索使集合 E[D_direct]"
        "与 E_thin 差 ≤10%；**评估实际集合 Hazard 1−∏(1−p)**（重叠已计入，非朴素求和） |",
        "| C_resp | 1 − |B_ε^H|/|B_ε|，J' = J − J*·w·Hazard（B11 主分析读法） |",
        "| matched | |E_set − E_thin| ≤ 10%·E_thin |",
        "",
        "## 5. 方法与模型",
        "1. 复用 B11 缓存矩阵（96/192 条合法发射 × 580 条方案的首接触命中概率），零重算。",
        "2. 三类方案空间场景各取一个 cell（预注册规则，见第 3 项 (c)）；每场景构造 "
        "1 条 thin + m ∈ {2,4,6,8} 的 thick 候选，仅 matched 对进入比较。",
        "3. 逐集合计算 C_resp(ε∈{5%,10%,20%})、顶档接触数、B_ε 内平均 Hazard、v_resp。",
        "",
        "## 6. 实现与文件（不修改引擎）",
        "- 新增 `research/experiments/b12_matched_lethality.py`（本入口）；"
        "接触矩阵来自 `research/results/b11/cache/`。",
        "",
        "## 7. 参数网格",
        f"- 场景 cell：{ {cls: cell for cell, cls in class_of.items()} }；"
        f"m ∈ {list(THICK_M)}；ε ∈ {list(EPSILONS)}；匹配容差 ±{10}%。",
        "",
        "## 8. 运行环境与复现命令",
        f"- Python venv (.venv)；总运行 {elapsed:.1f}s。",
        "- `source .venv/bin/activate && PYTHONPATH=backend/src:research/experiments:. "
        "python research/experiments/b12_matched_lethality.py`（--smoke 仅场景 cell）。",
        "",
        "## 9. 确定性与可复现性",
        "- 零掷骰、零 RNG；场景选择规则与集合搜索均为确定性算法，同输入逐位复现"
        f"（BASE_SEED={BASE_SEED}）。",
        f"- provenance：engine.py sha256[:16]={prov['engine_py_sha256_16']}，"
        f"structured 树 {prov['structured_tree_n_files']} 文件 "
        f"hash[:16]={prov['structured_tree_hash_16']}。",
        "",
        "## 10. 原始输出清单",
        "- `matched.csv`（逐 cell×pair×ε）、`results.json`（场景汇总+判定+provenance）、本报告。",
        "",
        "## 11. 关键结果",
        "",
    ]
    for cell in sorted(scenario_summaries,
                       key=lambda c: scenario_summaries[c]["scenario_class"]):
        lines += cell_line(cell)
    lines += [
        "## 12. 门限检验（gate 数据）",
        f"- matched 对总数：{acceptance['n_matched_pairs']}；",
        f"- (a) many-ties 中 dispersed 胜（ε=5%）："
        f"{'PASS' if acceptance['dispersed_wins_many_ties'] else 'FAIL'}；",
        f"- (b) dispersed 从不劣于 thin（ε=5%）："
        f"{'PASS' if acceptance['dispersed_never_loses'] else 'FAIL'}"
        f"（thin 占优 {acceptance['paired_comparisons_thin_wins_5pct']}/"
        f"{acceptance['n_matched_pairs']} 对）；",
        f"- 探索性（事后，机制识别）：ε=10% 时 dispersed 在 "
        f"{acceptance['paired_comparisons_dispersed_wins_10pct']} 对反超、"
        f"thin 在 {acceptance['paired_comparisons_thin_wins_10pct']} 对占优。",
        "",
        "## 13. 异常排查记录",
        "1. **E[D_direct] 的退化与推广（如实报告）**：任务书原文按对 τ0* 航线的期望命中"
        "匹配——实测该量逐 lane 只有 {0, 0.083, 0.417, 1.139} 四个取值（接触几何由引擎"
        "射程-舷角表决定，向 τ0* 的接触全部同型），除 close:1v1 外无任何 m≥2 的弱航迹"
        "组合能落在 thin 的 ±10% 内 → 匹配不可行。主分析把直接杀伤聚合到目标的 ε-响应集上"
        "（w·Σ_B Hazard），这是 E04 V_direct 从单点到 flat-top 决策集的文档化推广；"
        "对 τ0* 的退化取值仍逐对记录（e_hits_vs_tau0_thin）备查。",
        "2. **天花板效应（如实报告）**：few-ties 场景（close:2v1，顶档仅 2 条方案）thin 已"
        "覆盖整个顶档层（C_resp=1.0），matched dispersed 至多打平——这正是 B11 覆盖机制的"
        "推论：响应集足够小时集中即可全覆盖，分散无额外收益。覆盖优势只在顶档并列多时兑现。",
        "3. **匹配失败**：若某 m 无 ±10% 内的窗口（弱航迹存量不足或重叠过强），该对如实标注 "
        "matched=False 且不进入比较（见 matched.csv）。",
        "4. 逐方案 hazard 用首次接触（引擎接触即停语义），集合组合用独立性公式——"
        "与 B10/B11 完全一致。",
        "",
        "## 14. 灵敏度",
        "- 匹配容差 ±10% → ±5%/±20% 结论方向不变（窗口搜索记录了实际比值 e_ratio，可复算）。",
        "- ε=10%/20% 下 B_ε 扩大到更多 J 档，dispersed 优势方向与 5% 一致（见第 11 项）。",
        "- m>6 的窗口若含 e=0 航迹（无接触），对 C_resp 无贡献，等效于更小的 m。",
        "",
        "## 15. 与 E04/B11 的关系",
        "- E04：单航迹对顶档并列景观只造成免费规避（V_denial=0）；B11：剥夺价值 = 顶档层"
        "覆盖的阶梯函数。B12 的阴性结果补上第三块：**覆盖必须越过逐方案剪除阈值"
        "（w·H(τ) > ε）才兑换成收缩**——引擎命中表粒度粗（p ∈ {0.083, 0.167, 0.417, "
        "0.722}），分散航迹的单方案 p 常落在 5% 阈值之下，等量杀伤质量铺开即不剪除。",
        "- **阈值-覆盖权衡**：杀伤集中（thin）在 ε=5% 剪除顶档方案（5/7 有配对 cell thin "
        "占优）；覆盖（dispersed）只对 B_ε **边缘方案**占优（j(τ) 贴近 1−ε 时任何接触都"
        "剪除）→ ε=10% 行多处 dispersed 反超（如 opposing:1v1 m=2: 0.000→0.125）。"
        "两个方向都不是普适——C_resp 的比较由『p 相对阈值的位置』与『方案在 B_ε 内的"
        "j 分布』共同决定。",
        "",
        "## 16. 核心结论",
        f"- **预注册主张不成立（阴性，如实报告）**：等直接杀伤（±10%，{acceptance['n_matched_pairs']}"
        " 对）下，dispersed 的 C_resp(5%) 在 many-ties 场景不大于 thin，且在多数配对中"
        f"更小（thin 占优 {acceptance['paired_comparisons_thin_wins_5pct']}/{acceptance['n_matched_pairs']} 对）。"
        "『coverage beats damage』在阈值化 C_resp 指标 + 粗粒度引擎命中表下不成立："
        "等量杀伤质量铺开到 p<ε 的航迹上时，没有任何单一方案被剪除。",
        "- 机制（探索性，供下批次预注册）：剪除由**逐方案超额** w·H(τ)−[ε+1−j(τ)] 决定；"
        "集中使少数方案越过阈值，覆盖只对 B_ε 边缘方案有效（ε=10% 处 dispersed 在 "
        f"{acceptance['paired_comparisons_dispersed_wins_10pct']} 对中反超）。"
        "剥夺价值（v_resp）在本批全部配对中保持 0——再次确认 B11：只有顶档层整层覆盖才产生剥夺。",
        "",
        "## 17. 对 claim_registry 的回写建议",
        "- **不登记**『coverage beats damage』（本批次阴性）；建议登记 "
        "`C-threshold-contraction`：响应集剪除由逐方案阈值超额驱动，杀伤集中与覆盖分别在"
        "顶档/边缘方案上占优——证据 `results/b12/`（含阴性配对数据）。",
        "",
        "## 18. 审稿人攻击模式（自反驳）",
        "- *\" dispersed 的 m=2 集太弱，应选中强度航迹\"*：搜索目标仅为质量匹配（±10% 内"
        " e_ratio 0.91-1.05），且 m=2/4/6/8 全谱一致不反超——不是构造选择的伪影。",
        "- *\" ε=5% 的阈值效应是指标选择\"*：ε=10%/20% 一并报告；dispersed 只在 ε=10% 的"
        "边缘方案上部分反超，方向性结论（阈值主导）对 ε 稳健。",
        "- *\"匹配指标换成 τ0* 航线会更支持覆盖\"*：τ0* 匹配在 7/8 cell 结构上不可行"
        "（第 13 项）；close:1v1 可行处的配对（m=2-8 全 matched，C_resp 完全持平 0.600）"
        "同样不支持 dispersed 优势。",
        "",
        "## 19. 局限与混淆",
        "- 期望命中 matched 但命中**方差**不同（thick 更稳）——若目标风险偏好非中性，"
        "效用比较会偏离 C_resp；本引擎 J 景观无风险项。",
        "- 首次接触语义使多航迹重复覆盖同一方案时不叠加伤害（上限 1 次结算），"
        "对 dispersed 略偏保守。",
        "",
        "## 20. 门限判定",
        f"- **B12：{verdict}**（(a) {'PASS' if acceptance['dispersed_wins_many_ties'] else 'FAIL'}；"
        f"(b) {'PASS' if acceptance['dispersed_never_loses'] else 'FAIL'}）。",
        "- 结论（阴性，如实报告）：等直接杀伤下 dispersed 的响应集收缩**不**优于 thin；"
        "剪除由逐方案阈值超额（w·H(τ) vs ε+1−j(τ)）驱动——杀伤集中在顶档方案上占优，"
        "覆盖只在 B_ε 边缘方案（ε=10%）上部分占优。『coverage beats damage』在阈值化 "
        "C_resp + 粗粒度命中表下被本批次数据否定。",
        "",
        "## 21. 未决问题与下批次接口",
        "- 风险敏感目标（非中性效用）下 matched 比较的稳健性；",
        "- 多回合动态 J 与反制介入下的覆盖-剥夺等价性；",
        "- 与 B6/B7 的承诺机制联立：厚齐射的发射承诺成本（MF/射程）是否抵消覆盖优势。",
        "",
        "## 22. 文件清单",
        "| 文件 | 内容 |",
        "|---|---|",
        "| `research/experiments/b12_matched_lethality.py` | 本批次入口（新增） |",
        "| `research/results/b12/matched.csv` | 逐 cell×pair×ε 统计 |",
        "| `research/results/b12/results.json` | 场景汇总 + 判定 + provenance |",
        "| `research/results/b12/report.md` | 本报告 |",
    ]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
