"""遗传算法训练状态机 AI（TacticalCommander 的 TacticalProfile 权重）。

背景：做 BC（行为克隆）之前，先把要被克隆的状态机 AI 训练出来。TacticalProfile
（tactical.py:29-73）是一组启发式权重/阈值，目前是手调默认值（balanced）。本模块用
遗传算法进化这组权重，得到比手调更强的策略，BC 再用它产监督数据。

- 基因组 = 16 个连续基因（逼近/规避/编队/鱼雷/目标价值/温度等，见 GENE_SPECS），
  解码回 TacticalProfile 交给引擎对局评估。**引擎唯一裁决**：评估只走 `run_match`，
  本模块不碰状态、不改裁决、不复制规则常量。
- 适应度 = 对「对手池」多局（个体同时作轴心与盟军，抵消阵营不对称）的胜率 + VP 差。
- 策略多样性（用户要求）：
  * 新奇度奖励：行为描述子（对各对手、各阵营的胜率向量）到 k 近邻的 L2 距离，
    适应度 = 原始胜率 + λ·新奇度 → 选择直接奖励"打法不同"的个体。
  * BLX-α 交叉（α=0.5）向父母区间之外外推 → 自然产生区间外新基因。
  * 变异：高斯逐基因（概率随代数自适应 0.4→0.15）+ 3% 整基因重置（跳回均匀区间）。
  * 精英保留 + 名人堂（跨代全局最优基因组，防退化/防丢失）。
- 并行加速：`ProcessPoolExecutor` 多进程。纯 Python 引擎受 GIL 限制，多线程无加速，
  多进程才有真并行（bench 实测 8 进程 ~0.23s/局墙钟）。GPU 对状态机 GA 无收益——
  它留给后续 BC/PPO 神经网络训练，本模块不涉及。
- 实验记录（保留关键数据）：--out 目录每代落盘
  * population-gen-N.json   全群体基因组 + 适应度 + 新奇度
  * gen-summary.csv         每代 best/mean/worst/多样性指标
  * games.jsonl             逐局原始结果（seed/胜方/VP/耗时）
  * best-genome.json / best-profile.json / hall-of-fame.json
  * config.json             全部超参与种子 → 可复现

运行（需 PYTHONPATH=backend/src）：
    python -m rl.evolve --scenario IBS-S-03 --gens 10 --pop 16 \
        --opponents balanced --games-per-opp 4 --workers 8 \
        --out rl/results/ga-s03-small-v1 --seed 20260826
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from iron_bottom_sound.match import run_match
from iron_bottom_sound.tactical import PROFILES, TacticalProfile

# --------------------------------------------------------------------------- 基因组

# (基因名, 下界, 上界, 是否整数, 默认值)。只进化连续权重/阈值；结构性字段
# （formation_spacing / top_k_candidates / rng_seed_off）保持默认。
GENE_SPECS: list[tuple[str, float, float, bool, float]] = [
    ("w_enemy_heat", 0.0, 4.0, False, 1.0),
    ("w_fire_pressure", 0.0, 4.0, False, 1.0),
    ("w_approach", -2.0, 3.0, False, 0.5),
    ("w_formation", -2.0, 4.0, False, 0.0),
    ("line_ahead", -2.0, 4.0, False, 0.0),
    ("w_predict_opponent", 0.0, 2.0, False, 1.0),
    ("w_retreat", 0.0, 3.0, False, 1.0),
    ("w_protect_own", 0.0, 3.0, False, 0.5),
    ("w_vp", 0.0, 3.0, False, 0.3),
    ("w_finish", 0.0, 3.0, False, 0.5),
    ("w_self_status", 0.0, 3.0, False, 0.3),
    ("torpedo_min_expected", 0.0, 0.8, False, 0.30),
    ("retreat_hull_threshold", 0.1, 0.7, False, 0.35),
    ("temperature", 0.0, 1.5, False, 0.5),
    ("approach_range", 6.0, 24.0, True, 12.0),
    ("torpedo_max_range", 6.0, 20.0, True, 10.0),
]
GENE_NAMES = [g[0] for g in GENE_SPECS]
GENE_LO = [g[1] for g in GENE_SPECS]
GENE_HI = [g[2] for g in GENE_SPECS]
GENE_INT = [g[3] for g in GENE_SPECS]
GENE_DEF = [g[4] for g in GENE_SPECS]
_GENE_RANGES = [hi - lo for lo, hi in zip(GENE_LO, GENE_HI)]


def encode_profile(profile: TacticalProfile) -> list[float]:
    return [getattr(profile, name) for name in GENE_NAMES]


def decode_genes(genes: list[float]) -> TacticalProfile:
    """基因 → TacticalProfile，逐基因 clamp 到界内、整数基因取整。"""
    values: dict[str, Any] = {}
    for name, lo, hi, is_int, g in zip(GENE_NAMES, GENE_LO, GENE_HI, GENE_INT, genes):
        v = max(lo, min(hi, float(g)))
        values[name] = int(round(v)) if is_int else float(v)
    return TacticalProfile(**values)


def default_genome() -> list[float]:
    return list(GENE_DEF)


def random_genome(rng: random.Random) -> list[float]:
    return [rng.uniform(lo, hi) for lo, hi in zip(GENE_LO, GENE_HI)]


def jitter_genome(base: list[float], rng: random.Random, frac: float) -> list[float]:
    """围绕 base 加高斯噪声；frac 为相对基因区间宽度的 σ。"""
    return [
        max(lo, min(hi, g + rng.gauss(0.0, span * frac)))
        for g, lo, hi, span in zip(base, GENE_LO, GENE_HI, _GENE_RANGES)
    ]


def genome_distance(a: list[float], b: list[float]) -> float:
    """基因空间的归一化 L2 距离（每维按区间宽度归一，量纲 [0,1]）。"""
    return math.sqrt(
        sum(((x - y) / span) ** 2 for x, y, span in zip(a, b, _GENE_RANGES))
    )


# --------------------------------------------------------------------------- 单局评估 worker

def _run_one_game(args: tuple[str, int, list[float], list[float], int, str, str]) -> dict[str, Any]:
    """单进程单局：axis 用 axis_genes，allies 用 allies_genes。只返回可序列化结果。

    Windows spawn 要求：顶层函数 + 普通可 pickle 元组（基因是 float 列表，OK）。
    一局失败不炸批：转成 error 记录。args 后三项（ind_id/ind_side/opp_name）供
    主进程聚合，worker 不用。"""
    scenario, seed, axis_genes, allies_genes, _, _, _ = args
    try:
        report, engine, _ = run_match(
            scenario,
            axis="tactical",
            allies="tactical",
            axis_profile=decode_genes(axis_genes),
            allies_profile=decode_genes(allies_genes),
            seed=seed,
        )
        state = engine.get(report.game_id)
        score = dict(state.score) if state else {}
        return {
            "seed": seed,
            "winner": report.winner.value if report.winner else None,
            "victory_reason": report.victory_reason,  # 引擎裁决的胜负原因（绝对锚点）
            "axis_score": score.get("axis", 0),
            "allies_score": score.get("allies", 0),
            "completed": report.completed,
            "elapsed_ms": report.elapsed_ms,
            "error": None,
        }
    except Exception as error:
        return {
            "seed": seed,
            "winner": None,
            "axis_score": 0,
            "allies_score": 0,
            "completed": False,
            "elapsed_ms": 0,
            "error": f"{type(error).__name__}: {error}",
        }


# --------------------------------------------------------------------------- 配置

@dataclass
class Config:
    # 双想定都打：S-03（4 回合 8 舰）与 S-01（7 回合 14~22 舰）共用同一主图
    # IBS-M-MAIN（34×27），同一套权重必须对两个想定都成立（跨想定复用验证）。
    scenarios: list[str] = field(default_factory=lambda: ["IBS-S-03", "IBS-S-01"])
    gens: int = 10
    pop_size: int = 16
    opponents: list[str] = field(default_factory=lambda: ["balanced"])
    games_per_opp: int = 4
    workers: int = 8
    seed: int = 20260826
    out: str = "rl/results/ga-run"

    # GA 参数
    tournament_k: int = 3
    elite_fraction: float = 0.15
    hall_of_fame: int = 4
    recombine_prob: float = 0.8
    uniform_crossover_prob: float = 0.3
    blx_alpha: float = 0.5
    mutation_prob_hi: float = 0.4
    mutation_prob_lo: float = 0.15
    sigma_frac_hi: float = 0.2
    sigma_frac_lo: float = 0.05
    reset_prob: float = 0.03
    novelty_lambda: float = 0.5
    novelty_k: int = 3
    vp_weight: float = 0.01
    seed_base: int = 1000

    # 冠军复评：主循环的逐代适应度局数少、噪声大（伯努利对局方差高），
    # 最后一轮对名人堂候选用大量局数重评，选出真正稳健的最优。
    champion_candidates: int = 4
    champion_games: int = 24
    champion_seed_base: int = 70000   # 与训练/verify seed 不相交

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


# --------------------------------------------------------------------------- 评估

def _build_jobs(population: list[dict[str, Any]], cfg: Config) -> list[tuple]:
    """每代固定工作清单：个体 × 想定 × 对手 × 双阵营 × games_per_opp 个 seed。

    seed 按 (想定 idx, 个体 id, 对手 idx, 第 k 局) 确定性派生：同一代里每个个体
    看到的开局集固定（比较噪声小）；不同个体开局不同，避免全群过拟合同一批开局。
    每代全员重新评估（含精英），下一代个体重编号 → seed 也随之变动。"""
    jobs: list[tuple] = []
    for ind in population:
        for scen_idx, scenario in enumerate(cfg.scenarios):
            for opp_idx, opp_name in enumerate(cfg.opponents):
                opp_genes = encode_profile(PROFILES[opp_name])
                for side in ("axis", "allies"):
                    for k in range(cfg.games_per_opp):
                        seed = cfg.seed_base + scen_idx * 7 + ind["id"] * 1009 + opp_idx * 101 + k
                        if side == "axis":
                            jobs.append((scenario, seed, ind["genes"], opp_genes,
                                         ind["id"], side, opp_name))
                        else:
                            jobs.append((scenario, seed, opp_genes, ind["genes"],
                                         ind["id"], side, opp_name))
    return jobs


def _champion_jobs(genes_list: list[list[float]], cfg: Config) -> list[tuple]:
    """冠军复评工作清单：候选 × 想定 × 对手 × 双阵营 × champion_games 个 fresh seed。

    seed 从 champion_seed_base 派生（与训练 seed_base、verify seed_base 全不相交），
    候选之间共享同批开局 → 相互比较的噪声更小（对局本身的伯努利方差仍存在，
    靠局数摊平）。"""
    jobs: list[tuple] = []
    for cand_id, genes in enumerate(genes_list):
        for scen_idx, scenario in enumerate(cfg.scenarios):
            for opp_idx, opp_name in enumerate(cfg.opponents):
                opp_genes = encode_profile(PROFILES[opp_name])
                for side in ("axis", "allies"):
                    for k in range(cfg.champion_games):
                        seed = (cfg.champion_seed_base + scen_idx * 7
                                + cand_id * 1009 + opp_idx * 101 + k)
                        if side == "axis":
                            jobs.append((scenario, seed, genes, opp_genes,
                                         cand_id, side, opp_name))
                        else:
                            jobs.append((scenario, seed, opp_genes, genes,
                                         cand_id, side, opp_name))
    return jobs


def _aggregate(
    population: list[dict[str, Any]], cfg: Config,
    job_meta: list[tuple[str, int, str, str]], results: list[dict],
) -> dict[int, dict[str, Any]]:
    """按个体聚合：wins/losses/draws、score_sum（胜+1/负-1/平0）、VP 差、各槽位胜率。

    job_meta 为 (scenario, ind_id, ind_side, opp_name)；槽位键 = scenario:opp:side。"""
    acc: dict[int, dict[str, Any]] = {
        ind["id"]: {"wins": 0, "losses": 0, "draws": 0, "errors": 0,
                    "score_sum": 0, "margin_sum": 0, "slots": {}}
        for ind in population
    }
    for (scenario, ind_id, ind_side, opp_name), res in zip(job_meta, results):
        a = acc[ind_id]
        if res["error"]:
            a["errors"] += 1
            continue
        winner = res["winner"]
        if winner is None:
            a["draws"] += 1
        elif winner == ind_side:
            a["wins"] += 1
            a["score_sum"] += 1
        else:
            a["losses"] += 1
            a["score_sum"] -= 1
        margin = (res["axis_score"] - res["allies_score"]) * (1 if ind_side == "axis" else -1)
        a["margin_sum"] += margin
        slot = a["slots"].setdefault(f"{scenario}:{opp_name}:{ind_side}", {"n": 0, "score": 0})
        slot["n"] += 1
        slot["score"] += 1 if winner == ind_side else (0 if winner is None else -1)
    return acc


def _slot_keys(cfg: Config) -> list[str]:
    return [f"{scen}:{opp}:{side}"
            for scen in cfg.scenarios for opp in cfg.opponents for side in ("axis", "allies")]


def _descriptor(ind: dict[str, Any], cfg: Config) -> list[float]:
    """行为描述子 = 对每个想定、每个对手、每个阵营的胜率向量。

    长度 = len(scenarios)×len(opponents)×2；双想定都打 → 行为差异在双想定上都体现。"""
    return [round(r, 4) for r in ind["wr_by_slot"]]


def _novelty(ind: dict[str, Any], population: list[dict[str, Any]], cfg: Config) -> float:
    """行为描述子到 k 近邻的 L2 距离（新奇度；个体越"另类"越高）。"""
    target = ind["descriptor"]
    others = [o["descriptor"] for o in population if o["id"] != ind["id"]]
    if not others:
        return 0.0
    dists = sorted(
        math.sqrt(sum((x - y) ** 2 for x, y in zip(target, o))) for o in others
    )
    k = min(cfg.novelty_k, len(dists))
    return sum(dists[:k]) / k


# --------------------------------------------------------------------------- 种群初始化

def _init_population(cfg: Config, rng: random.Random) -> list[dict[str, Any]]:
    """初始种群：全部内置风格（保证起点多样性）+ balanced 抖动变体 + 少量随机。"""
    pop: list[dict[str, Any]] = []
    builtin = [encode_profile(PROFILES[name]) for name in PROFILES]
    seen: set[tuple] = set()
    for genes in builtin:
        if len(pop) >= cfg.pop_size:
            break
        pop.append({"id": len(pop), "genes": list(genes)})
        seen.add(tuple(genes))
    while len(pop) < cfg.pop_size:
        if rng.random() < 0.3:
            genes = random_genome(rng)
        else:
            base = builtin[rng.randrange(len(builtin))]
            genes = jitter_genome(base, rng, frac=rng.uniform(0.05, 0.25))
        if tuple(genes) not in seen:
            pop.append({"id": len(pop), "genes": genes})
            seen.add(tuple(genes))
    for ind in pop:
        ind["fitness"] = float("-inf")
        ind["descriptor"] = []
        ind["novelty"] = 0.0
    return pop


# --------------------------------------------------------------------------- 选择 / 交叉 / 变异

def _tournament(population: list[dict[str, Any]], cfg: Config, rng: random.Random) -> dict[str, Any]:
    best = None
    for _ in range(cfg.tournament_k):
        candidate = population[rng.randrange(len(population))]
        if best is None or candidate["adjusted_fitness"] > best["adjusted_fitness"]:
            best = candidate
    return best


def _crossover(a: list[float], b: list[float], cfg: Config, rng: random.Random) -> list[float]:
    if rng.random() < cfg.uniform_crossover_prob:
        return [x if rng.random() < 0.5 else y for x, y in zip(a, b)]
    # BLX-α：向父母区间外外推，保持区间外多样性
    child = []
    for x, y, lo, hi, span in zip(a, b, GENE_LO, GENE_HI, _GENE_RANGES):
        low, high = min(x, y), max(x, y)
        d = high - low
        child.append(max(lo, min(hi, rng.uniform(low - cfg.blx_alpha * d, high + cfg.blx_alpha * d))))
    return child


def _mutate(genes: list[float], gen: int, cfg: Config, rng: random.Random) -> list[float]:
    progress = gen / max(1, cfg.gens - 1)
    prob = cfg.mutation_prob_hi + (cfg.mutation_prob_lo - cfg.mutation_prob_hi) * progress
    sigma = cfg.sigma_frac_hi + (cfg.sigma_frac_lo - cfg.sigma_frac_hi) * progress
    out = []
    for g, lo, hi, span in zip(genes, GENE_LO, GENE_HI, _GENE_RANGES):
        if rng.random() < cfg.reset_prob:
            out.append(rng.uniform(lo, hi))          # 整基因重置 → 多样性注入
        elif rng.random() < prob:
            out.append(max(lo, min(hi, g + rng.gauss(0.0, span * sigma))))
        else:
            out.append(g)
    return out


def _evaluate(
    jobs: list[tuple], cfg: Config, pool: ProcessPoolExecutor | None = None,
    on_result: Callable[[tuple, dict], None] | None = None,
) -> list[dict[str, Any]]:
    """评估全部工作，返回与 jobs **顺序对齐**的 results（供聚合）。

    on_result(job, res)：每局完成立即回调（实时流式落盘 → watch.py 面板）。
    pool 非空时 submit + as_completed，按完成顺序回调；results 用 idx 回填保持对齐。
    _run_one_game 内部兜底异常 → result() 不会抛。
    pool=None → 串行（冒烟/调试）。
    """
    if pool is None:
        results: list[dict[str, Any]] = []
        for job in jobs:
            res = _run_one_game(job)
            if on_result is not None:
                on_result(job, res)
            results.append(res)
        return results
    results: list[dict[str, Any] | None] = [None] * len(jobs)
    fut_to_idxjob = {
        pool.submit(_run_one_game, job): (idx, job) for idx, job in enumerate(jobs)
    }
    for fut in as_completed(fut_to_idxjob):
        idx, job = fut_to_idxjob[fut]
        res = fut.result()
        results[idx] = res
        if on_result is not None:
            on_result(job, res)
    return results


# --------------------------------------------------------------------------- 主进化循环

def evolve(cfg: Config) -> dict[str, Any]:
    rng = random.Random(cfg.seed)
    out_dir = Path(cfg.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "config.json").write_text(
        json.dumps(cfg.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    games_fh = (out_dir / "games.jsonl").open("w", encoding="utf-8")
    summary_rows: list[dict[str, Any]] = []
    slot_keys = _slot_keys(cfg)

    population = _init_population(cfg, rng)
    hall: dict[tuple, dict[str, Any]] = {}
    best_overall: dict[str, Any] | None = None
    pool = ProcessPoolExecutor(max_workers=cfg.workers) if cfg.workers > 0 else None

    for gen in range(cfg.gens):
        t0 = time.perf_counter()
        jobs = _build_jobs(population, cfg)
        job_meta = [(j[0], j[4], j[5], j[6]) for j in jobs]  # (scenario, ind_id, ind_side, opp_name)

        # 逐局原始数据（保留关键数据）——每局完成即落盘 + flush，watch.py 实时追读
        def on_game(job, res):
            scenario, seed, _, _, ind_id, ind_side, opp_name = job
            games_fh.write(json.dumps(
                {"gen": gen, "scenario": scenario, "ind_id": ind_id, "side": ind_side,
                 "opponent": opp_name, "seed": seed, **res},
                ensure_ascii=False) + "\n")
            games_fh.flush()

        results = _evaluate(jobs, cfg, pool, on_game)
        agg = _aggregate(population, cfg, job_meta, results)

        # 适应度 + 行为描述子 + 新奇度
        for ind in population:
            a = agg[ind["id"]]
            games = max(1, a["wins"] + a["losses"] + a["draws"])
            win_rate = a["score_sum"] / games
            avg_margin = a["margin_sum"] / games
            ind["wr_by_slot"] = [
                (a["slots"].get(k) or {"n": 0, "score": 0})["score"]
                / max(1, (a["slots"].get(k) or {"n": 0, "score": 0})["n"])
                for k in slot_keys
            ]
            ind["descriptor"] = _descriptor(ind, cfg)
            ind["fitness"] = win_rate + cfg.vp_weight * avg_margin
        for ind in population:
            ind["novelty"] = _novelty(ind, population, cfg)
            ind["adjusted_fitness"] = ind["fitness"] + cfg.novelty_lambda * ind["novelty"]

        # 精英 + 名人堂（跨代全局最优基因组）
        ranked = sorted(population, key=lambda i: i["fitness"], reverse=True)
        elite_count = max(1, int(math.ceil(cfg.elite_fraction * len(population))))
        elites = [dict(i) for i in ranked[:elite_count]]
        for ind in ranked:
            key = tuple(ind["genes"])
            if key not in hall or ind["fitness"] > hall[key]["fitness"]:
                hall[key] = dict(ind)
        hall_sorted = sorted(hall.values(), key=lambda i: i["fitness"], reverse=True)[:cfg.hall_of_fame]
        best_overall = max(ranked[0], best_overall or ranked[0], key=lambda i: i["fitness"])

        # 本代群体日志
        (out_dir / f"population-gen-{gen}.json").write_text(json.dumps(
            [{"id": i["id"], "genes": i["genes"], "fitness": i["fitness"],
              "novelty": i["novelty"], "adjusted_fitness": i["adjusted_fitness"],
              "descriptor": i["descriptor"]} for i in population],
            ensure_ascii=False, indent=2), encoding="utf-8")

        # 多样性指标
        genomes = [i["genes"] for i in population]
        pair_dists = [genome_distance(a, b)
                      for idx, a in enumerate(genomes) for b in genomes[idx + 1:]]
        fitnesses = [i["fitness"] for i in population]
        mean_f = sum(fitnesses) / len(fitnesses)
        summary_rows.append({
            "gen": gen,
            "best_fitness": round(max(fitnesses), 4),
            "mean_fitness": round(mean_f, 4),
            "worst_fitness": round(min(fitnesses), 4),
            "best_novelty": round(max(i["novelty"] for i in population), 4),
            "mean_pairwise_genome_dist": round(sum(pair_dists) / len(pair_dists), 4) if pair_dists else 0.0,
            "fitness_std": round((sum((f - mean_f) ** 2 for f in fitnesses) / len(fitnesses)) ** 0.5, 4),
            "unique_genomes": len({tuple(g) for g in genomes}),
            "hall_best_fitness": round(hall_sorted[0]["fitness"], 4) if hall_sorted else None,
            "errors": sum(a["errors"] for a in agg.values()),
            "wall_s": round(time.perf_counter() - t0, 2),
        })

        # 繁殖下一代：精英 + 名人堂（未在精英中）+ 锦标赛选择的后代
        next_pop = [dict(e) for e in elites]
        elite_genes = {tuple(e["genes"]) for e in elites}
        for h in hall_sorted:
            if len(next_pop) >= cfg.pop_size:
                break
            if tuple(h["genes"]) not in elite_genes:
                next_pop.append(dict(h))
        while len(next_pop) < cfg.pop_size:
            parent_a = _tournament(population, cfg, rng)
            parent_b = _tournament(population, cfg, rng)
            if rng.random() < cfg.recombine_prob:
                genes = _crossover(parent_a["genes"], parent_b["genes"], cfg, rng)
            else:
                genes = list(parent_a["genes"])
            genes = _mutate(genes, gen, cfg, rng)
            next_pop.append({"id": -1, "genes": genes})
        for idx, ind in enumerate(next_pop):
            ind["id"] = idx
            ind.setdefault("fitness", float("-inf"))
            ind.setdefault("descriptor", [])
            ind.setdefault("novelty", 0.0)
        population = next_pop

        row = summary_rows[-1]
        print(f"gen {gen:>2} | best {row['best_fitness']:+.3f} "
              f"mean {row['mean_fitness']:+.3f} | 基因距离 {row['mean_pairwise_genome_dist']:.3f} "
              f"新奇度 {row['best_novelty']:.3f} | {row['wall_s']}s")

    games_fh.close()

    # ---- 冠军复评：逐代适应度局数少、伯努利对局噪声大（此前小规模 best 8/8
    #      全胜但 fresh seed 验证发现并不优于 balanced 即此原因）。最后一轮对
    #      名人堂候选用大量局数重评，选出真正稳健的最优作为交付 profile。 ----
    champion: dict[str, Any] | None = None
    champion_rows: list[dict[str, Any]] = []
    if hall_sorted:
        candidates = [dict(h) for h in hall_sorted[:cfg.champion_candidates]]
        cand_genes = [c["genes"] for c in candidates]
        cjobs = _champion_jobs(cand_genes, cfg)
        cmeta = [(j[0], j[4], j[5], j[6]) for j in cjobs]  # (scenario, cand_id, ind_side, opp_name)
        # 复评逐局原始数据（保留关键数据）——同样实时落盘
        champ_games_fh = (out_dir / "champion-games.jsonl").open("w", encoding="utf-8")

        def on_champ_game(job, res):
            scenario, seed, _, _, cand_id, ind_side, opp_name = job
            champ_games_fh.write(json.dumps(
                {"cand_id": cand_id, "scenario": scenario, "side": ind_side,
                 "opponent": opp_name, "seed": seed, **res},
                ensure_ascii=False) + "\n")
            champ_games_fh.flush()

        cresults = _evaluate(cjobs, cfg, pool, on_champ_game)
        champ_games_fh.close()
        fake_pop = [{"id": i, "genes": g} for i, g in enumerate(cand_genes)]
        cagg = _aggregate(fake_pop, cfg, cmeta, cresults)
        for idx, cand in enumerate(candidates):
            a = cagg[idx]
            games = max(1, a["wins"] + a["losses"] + a["draws"])
            win_rate = a["score_sum"] / games
            avg_margin = a["margin_sum"] / games
            champion_rows.append({
                "cand_id": idx,
                "win_rate": round(win_rate, 4),
                "avg_margin": round(avg_margin, 2),
                "robust_fitness": round(win_rate + cfg.vp_weight * avg_margin, 4),
                "games": games,
                "genes": cand["genes"],
            })
        champion_rows.sort(key=lambda r: r["robust_fitness"], reverse=True)
        for rank, row in enumerate(champion_rows, start=1):
            row["rank"] = rank
        champion = champion_rows[0]
        (out_dir / "champion-genome.json").write_text(json.dumps(
            champion, ensure_ascii=False, indent=2), encoding="utf-8")
        (out_dir / "champion-profile.json").write_text(
            decode_genes(champion["genes"]).model_dump_json(indent=2), encoding="utf-8")
        (out_dir / "champion-summary.json").write_text(json.dumps(
            champion_rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print("\n冠军复评（名人堂候选 × 大量局数）:")
        for row in champion_rows:
            print(f"  #{row['rank']} cand {row['cand_id']} | 胜率 {row['win_rate']:+.3f} "
                  f"均VP差 {row['avg_margin']:+.2f} | robust {row['robust_fitness']:+.3f} "
                  f"| {row['games']} 局")
    if pool is not None:
        pool.shutdown()

    with (out_dir / "gen-summary.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    # 终局产物
    assert best_overall is not None
    best_genes = best_overall["genes"]
    (out_dir / "best-genome.json").write_text(json.dumps(
        {"genes": best_genes, "fitness": best_overall["fitness"],
         "descriptor": best_overall["descriptor"]}, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "best-profile.json").write_text(
        decode_genes(best_genes).model_dump_json(indent=2), encoding="utf-8")
    (out_dir / "hall-of-fame.json").write_text(json.dumps(
        [{"genes": h["genes"], "fitness": h["fitness"], "descriptor": h["descriptor"]}
         for h in hall_sorted], ensure_ascii=False, indent=2), encoding="utf-8")

    return {"config": cfg.to_dict(), "summary": summary_rows, "best": best_overall,
            "champion": champion, "champion_rows": champion_rows}


# --------------------------------------------------------------------------- CLI

def main() -> int:
    parser = argparse.ArgumentParser(description="遗传算法训练 TacticalCommander 的 TacticalProfile 权重")
    parser.add_argument("--scenario", default="IBS-S-03,IBS-S-01",
                        help="想定（逗号分隔，两个都打默认；同主图 34×27，权重须双想定成立）")
    parser.add_argument("--gens", type=int, default=10, help="迭代代数（用户要求 10）")
    parser.add_argument("--pop", type=int, default=16, help="种群规模")
    parser.add_argument("--opponents", default="balanced",
                        help="对手池：逗号分隔风格名（默认 balanced；可 fleet,brawl,...）")
    parser.add_argument("--games-per-opp", type=int, default=4,
                        help="每个 (个体,对手,阵营) 打几局（不同 seed）")
    parser.add_argument("--workers", type=int, default=0,
                        help="进程数；0 = min(8, cpu_count)，-1 = 串行")
    parser.add_argument("--champion-candidates", type=int, default=4,
                        help="冠军复评候选数（名人堂 top-N，大量局数重评去噪）")
    parser.add_argument("--champion-games", type=int, default=24,
                        help="冠军复评每 (候选,对手,阵营) 局数")
    parser.add_argument("--out", default="rl/results/ga-run")
    parser.add_argument("--seed", type=int, default=20260826, help="GA 随机种子（评估开局 seed 按槽位另派生）")
    args = parser.parse_args()

    opponents = [p.strip() for p in args.opponents.split(",")]
    unknown = set(opponents) - set(PROFILES)
    if unknown:
        raise SystemExit(f"未知对手风格 {sorted(unknown)}；可用 {sorted(PROFILES)}")
    known_scenarios = ("IBS-S-01", "IBS-S-03")
    scenarios = [s.strip() for s in args.scenario.split(",")]
    unknown_s = set(scenarios) - set(known_scenarios)
    if unknown_s:
        raise SystemExit(f"未知想定 {sorted(unknown_s)}；可用 {sorted(known_scenarios)}")
    workers = args.workers
    if workers == 0:
        workers = min(8, os.cpu_count() or 1)
    if workers == -1:
        workers = 0

    cfg = Config(
        scenarios=scenarios, gens=args.gens, pop_size=args.pop,
        opponents=opponents, games_per_opp=args.games_per_opp,
        workers=workers, seed=args.seed, out=args.out,
        champion_candidates=args.champion_candidates,
        champion_games=args.champion_games,
    )
    print(f"[GA] 想定 {'+'.join(cfg.scenarios)} · {cfg.gens} 代 · 种群 {cfg.pop_size} · "
          f"对手 {','.join(cfg.opponents)} · games/opp/想定/阵营 {cfg.games_per_opp} · "
          f"workers {cfg.workers} → {cfg.out}")
    t0 = time.perf_counter()
    result = evolve(cfg)
    wall = time.perf_counter() - t0

    champion = result["champion"]
    champ_profile = decode_genes(champion["genes"]) if champion else None
    defaults = dict(zip(GENE_NAMES, GENE_DEF))
    print("\n===== 结果 =====")
    print(f"总墙钟 {wall:.1f}s")
    print(f"逐代最优 fitness {result['best']['fitness']:+.4f}  "
          f"descriptor {[round(x, 3) for x in result['best']['descriptor']]}")
    if champ_profile is not None:
        print(f"\n冠军（大量局数复评的稳健最优）robust {champion['robust_fitness']:+.4f}  "
              f"胜率 {champion['win_rate']:+.3f}  均VP差 {champion['avg_margin']:+.2f}")
        print("冠军基因（* = 已偏离手调默认）：")
        for name, v in zip(GENE_NAMES, champion["genes"]):
            mark = " *" if abs(v - defaults[name]) > 1e-9 else ""
            print(f"  {name:<24} {v:>8.3f}{mark}")
    print(f"\n交付 profile 已写 {Path(args.out) / 'champion-profile.json'}"
          f"（逐代最优另存 best-profile.json 供对照）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
