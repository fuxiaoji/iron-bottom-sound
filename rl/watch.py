"""GA 实时面板：追读 games.jsonl（流式），实时显示每个个体（风格）的双想定胜率。

evolve.py 用 imap_unordered 每局完成即落盘 + flush，本工具每 N 秒重扫一次目录：
  * games.jsonl           流式逐局结果 → 按 ind_id 聚合实时胜率
  * config.json           想定/对手/种群/局数/代数（进度与 ETA）
  * population-gen-N.json 最近一代的基因 → 映射到最近内置风格（个体"风格"列）

用法（在任意终端跑，实时刷新；Ctrl-C 退出）：
    PYTHONPATH=backend/src python -X utf8 -m rl.watch --out rl/results/ga-dual-med-v1

    --once   只打印一帧快照（脚本/日志用）
    --interval 5   刷新间隔秒（默认 5）
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

from .evolve import PROFILES, Config, _init_population, encode_profile, genome_distance


def _load_cfg(out: Path) -> Config:
    return Config(**json.loads((out / "config.json").read_text(encoding="utf-8")))


def _style_map(out: Path, cfg: Config, current_gen: int, rng_seed: int):
    """个体 id → 风格标签。gen 0 用确定性重建（同 _init_population）；gen≥1 读最近一代落盘。"""
    builtin = {name: list(encode_profile(PROFILES[name])) for name in PROFILES}
    genes_by_id: dict[int, list[float]] = {}
    source = None
    if current_gen == 0:
        source = "init(重建)"
        for ind in _init_population(cfg, random.Random(cfg.seed)):
            genes_by_id[ind["id"]] = list(ind["genes"])
    else:
        pf = out / f"population-gen-{current_gen - 1}.json"
        if pf.exists():
            source = f"gen{current_gen - 1}(落盘)"
            for entry in json.loads(pf.read_text(encoding="utf-8")):
                genes_by_id[entry["id"]] = list(entry["genes"])
    labels: dict[int, str] = {}
    for ind_id, genes in genes_by_id.items():
        best, best_d = None, None
        for name, bg in builtin.items():
            d = genome_distance(genes, bg)
            if best_d is None or d < best_d:
                best, best_d = name, d
        labels[ind_id] = f"{best}{'*' if best_d > 0.15 else ''}"
    return labels, source


def _render(out: Path, cfg: Config) -> str:
    games_f = out / "games.jsonl"
    rows: list[dict] = []
    if games_f.exists():
        for line in games_f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    per_gen = len(cfg.scenarios) * len(cfg.opponents) * 2 * cfg.games_per_opp * cfg.pop_size
    total = per_gen * cfg.gens
    current_gen = min(len(rows) // per_gen, cfg.gens - 1) if per_gen else 0
    gen_rows = rows[current_gen * per_gen:] if per_gen else rows
    elapsed_s = time.time() - (out / "config.json").stat().st_mtime  # GA 自身墙钟
    done = len(rows)
    pct = 100.0 * done / total if total else 0.0
    eta = elapsed_s / max(1, done) * max(1, total - done) if done else float("nan")

    labels, label_source = _style_map(out, cfg, current_gen, cfg.seed)

    # 按 (ind_id, scenario) 聚合 —— 真实胜率 = 胜局 / 总局数（0~1）
    stat: dict[tuple[int, str], list[float]] = defaultdict(list)
    errors = 0
    for r in gen_rows:
        if r.get("error"):
            errors += 1
            continue
        stat[(r["ind_id"], r["scenario"])].append(
            1.0 if r["winner"] == r["side"] else 0.0)  # 胜=1 负/平=0
    ind_ids = sorted({i for i, _ in stat})
    table = []
    for ind_id in ind_ids:
        s03 = stat.get((ind_id, cfg.scenarios[0]), [])
        s01 = stat.get((ind_id, cfg.scenarios[1]), [])
        wr03 = (sum(s03) / len(s03)) if s03 else float("nan")
        wr01 = (sum(s01) / len(s01)) if s01 else float("nan")
        combined = (wr03 + wr01) / 2 if (s03 and s01) else (wr03 if s03 else wr01)
        table.append((ind_id, labels.get(ind_id, "?"), wr03, wr01, combined,
                      len(s03) + len(s01)))
    table.sort(key=lambda t: t[4], reverse=True)

    # 逐代 best 历史
    history = []
    gen_f = out / "gen-summary.csv"
    if gen_f.exists():
        for line in list(gen_f.read_text(encoding="utf-8").splitlines())[1:]:
            if line.strip():
                cols = line.split(",")
                history.append(f"g{cols[0]} {float(cols[1]):+.2f}")

    L = []
    L.append(f"铁底湾 GA 实时面板  →  {out}")
    L.append(f"想定 {'+'.join(cfg.scenarios)} · 对手 {','.join(cfg.opponents)} · "
             f"种群 {cfg.pop_size} · games/opp {cfg.games_per_opp} · 进程 {cfg.workers} · {cfg.gens} 代")
    eta_s = f"{eta / 60:.0f}m" if eta == eta else "-"
    L.append(f"gen {current_gen}/{cfg.gens} · 本代 {len(gen_rows)}/{per_gen} 局 · "
             f"总 {done}/{total} ({pct:.1f}%) · 墙钟 {elapsed_s / 60:.0f}m · ETA ~{eta_s}  · "
             f"风格源 {label_source}")
    if errors:
        L.append(f"  ⚠ 本代 {errors} 局出错（不计入胜率）")
    L.append("")
    L.append(f"  ID  风格                   S-03       S-01       合计       局数")
    for ind_id, label, wr03, wr01, combined, n in table:
        f03 = f"{wr03:.3f}" if wr03 == wr03 else "  -   "
        f01 = f"{wr01:.3f}" if wr01 == wr01 else "  -   "
        L.append(f"  {ind_id:>2}  {label:<20} {f03:>9} {f01:>9} {combined:>9.3f} {n:>6}")
    if history:
        L.append("")
        L.append("  逐代 best（fitness = 胜−负差分，GA 排序用，非胜率）： "
                 + " | ".join(history))
    if not _once:
        L.append("")
        L.append(f"  刷新中（每 {_interval}s）… Ctrl-C 退出")
    return "\n".join(L)


def main() -> int:
    global _started, _interval, _once
    parser = argparse.ArgumentParser(description="GA 实时面板（追读流式 games.jsonl）")
    parser.add_argument("--out", required=True, help="GA 输出目录（--out）")
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--once", action="store_true", help="只打印一帧快照")
    args = parser.parse_args()
    _interval = args.interval
    _once = args.once
    _started = time.time()

    out = Path(args.out)
    while not (out / "config.json").exists():
        print(f"等待 {out}/config.json …")
        if args.once:
            return 0
        time.sleep(2)

    cfg = _load_cfg(out)
    if args.once:
        print(_render(out, cfg))
        return 0

    # 终端实时刷新（ANSI）；stdout 非 tty 时退化为逐帧打印
    is_tty = sys.stdout.isatty()
    try:
        while True:
            frame = _render(out, cfg)
            if is_tty:
                sys.stdout.write("\033[H\033[2J\033[?25l" + frame)
                sys.stdout.flush()
            else:
                sys.stdout.write("\n" + "=" * 78 + "\n" + frame + "\n")
                sys.stdout.flush()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        if is_tty:
            sys.stdout.write("\033[?25h")
        return 0


_started = 0.0
_interval = 5.0
_once = False

if __name__ == "__main__":
    raise SystemExit(main())
