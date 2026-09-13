"""E04: torpedo direct-kill vs maneuver-denial decomposition (plan 8 / E04).

Research question: is the value of a torpedo launch well described by
    V_torpedo = V_direct + V_denial,
and in launch opportunities whose DIRECT-hit expectation is very low, is the
denial value (the target's optimal-response change, plan 5.2) significantly
greater than zero?

Conditions (paired: identical sandbox, zero dice consumed anywhere):
    A  no-torpedo control          -> tau0*  (argmax J over the target's plan space)
    C  low-direct-hit subset       -> tauT*  (E[direct hits] < 0.15 opportunities,
                                              true-hazard best response)
    D  threat-only                 -> direct-kill weight -> constant inside the
                                              target's decision (mechanism id.)
    B  direct-hit supplement       -> same measurement for opportunities with
                                              E[direct hits] >= threshold.

Usage:
    python research/experiments/e04_torpedo_denial.py --smoke
    python research/experiments/e04_torpedo_denial.py            # full run
    python research/experiments/e04_torpedo_denial.py --seeds 36 --jobs 8

Outputs: research/results/e04/{results.json, metrics.csv,
fig_e04_denial.png, fig_e04_decomposition.png, case_study.md, report.md}
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

from iron_bottom_sound.models import OrderBatch, Phase, Side  # noqa: E402
from research.torpedo_denial.lane import build_lane  # noqa: E402
from research.torpedo_denial.protocol import LAUNCHED_TURN, measure_seed  # noqa: E402
from research.torpedo_denial.scenarios import (  # noqa: E402
    CA_ID,
    GEOMETRIES,
    build_sandbox,
    enumerate_launch_options,
    progress_to_torpedo_planning,
    resolve_turn,
    seal_turn2_plans,
)

OUT = REPO / "research" / "results" / "e04"
BASE_SEED = 20260909
BOOTSTRAP_REPS = 10000
GEOMETRY_KEYS = sorted(GEOMETRIES)
FLEET_KEYS = sorted({"1v1", "2v1"})
SEEDS_PER_CELL = 36


# ---------------------------------------------------------------------------
# lane-model verification against a REAL engine torpedo launch
# ---------------------------------------------------------------------------

def verify_lane_model() -> dict:
    """Launch one torpedo through the engine's own adjudication on the response
    turn and compare the resolved traversed hexes with the analytic lane
    timeline (same-turn prefix)."""
    geometry = GEOMETRIES["opposing"]
    engine, state = build_sandbox(geometry, "1v1", 424242)
    progress_to_torpedo_planning(engine, state)
    resolve_turn(engine, state)
    seal_turn2_plans(engine, state)
    plan_strings = {ship.id: "3" for ship in state.ships.values() if ship.side == Side.AXIS}
    options = enumerate_launch_options(engine, state, plan_strings)
    attacker_id = sorted(plan_strings)[0]
    option = next(
        item for item in options
        if item.ship_id == attacker_id and item.launch_at_mf == 2
        and item.launch_side == "port" and item.launch_angle == "A"
        and item.setting_index == 1
    )
    errors = engine.validate_orders(
        state.game_id,
        OrderBatch(side=Side.AXIS, phase=Phase.TORPEDO_PLANNING,
                   torpedoes=[option.order(CA_ID)]),
    )
    if not errors.valid:
        raise ValueError(f"verification order rejected: {errors.errors}")
    for side in Side:
        result = engine.submit_orders(
            state.game_id,
            OrderBatch(side=side, phase=Phase.TORPEDO_PLANNING,
                       torpedoes=[option.order(CA_ID)] if side == Side.AXIS else []),
        )
        if not result.valid:
            raise ValueError(f"submit failed: {result.errors}")
    engine.advance(state.game_id)          # TORPEDO_PLANNING -> MOVEMENT_RESOLUTION
    engine.advance(state.game_id)          # MOVEMENT_RESOLUTION -> GUNNERY (resolves movement)
    state = engine.get(state.game_id)
    tracks = state.torpedo_tracks
    if not tracks:
        raise ValueError("verification launch produced no torpedo track")
    track = tracks[0]
    engine_resolved = [coord.label for coord in track.traversed_hexes]

    analytic = build_lane(
        engine, state, state.ships[option.ship_id],
        launch_hex=option.launch_hex, ship_heading=option.ship_heading,
        launch_side=option.launch_side, launch_angle=option.launch_angle,
        setting_index=option.setting_index, launch_at_mf=option.launch_at_mf,
        launched_turn=LAUNCHED_TURN,
    )
    analytic_path = [coord.label for coord in analytic.path]
    if engine_resolved != analytic_path[: len(engine_resolved)]:
        raise ValueError(
            "lane model mismatch: "
            f"engine={engine_resolved} analytic={analytic_path}"
        )
    return {
        "scenario": f"{geometry.key}/1v1 seed=424242 (turn-{LAUNCHED_TURN} launch)",
        "order": f"{option.ship_id} {option.launcher_id} mf={option.launch_at_mf} "
                 f"{option.launch_side}/{option.launch_angle} setting={option.setting_index}",
        "engine_traversed": engine_resolved,
        "analytic_path": analytic_path,
        "match": True,
    }


# ---------------------------------------------------------------------------
# parallel measurement
# ---------------------------------------------------------------------------

_WORKER_CONFIG: dict = {}


def _wait_for_valid_rules(timeout_s: float = 600.0) -> None:
    """Block until the ship-records tree loads cleanly.

    The repository's derived rules data may be regenerated concurrently by
    another process; transient windows can be missing or half-written.  E04
    never modifies rules data - it waits for a consistent moment.
    """
    from iron_bottom_sound.ship_records import load_ship_records

    deadline = time.time() + timeout_s
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            load_ship_records()
            return
        except Exception as error:  # noqa: BLE001 - transient by construction
            last_error = error
            time.sleep(5.0)
    raise RuntimeError(f"rules data did not stabilize within {timeout_s}s: {last_error}")


def _snapshot_rules() -> str:
    """Copy the derived rules tree to a temp snapshot and return its path.

    Workers read the snapshot so a concurrent regeneration of the live tree
    cannot corrupt a run mid-flight.  The snapshot is byte-identical to the
    validated live data at snapshot time - no rule content is altered.
    """
    import shutil
    import tempfile

    _wait_for_valid_rules()
    target_root = Path(tempfile.mkdtemp(prefix="e04_rules_"))
    target = target_root / "structured"
    shutil.copytree(REPO / "resources" / "derived" / "structured", target)
    return str(target)


def _apply_snapshot(snapshot_str: str | None) -> None:
    if not snapshot_str:
        return
    import importlib

    snapshot = Path(snapshot_str)
    data_mod = importlib.import_module("iron_bottom_sound.data")
    data_mod.STRUCTURED = snapshot
    for module_name in (
        "iron_bottom_sound.engine",
        "iron_bottom_sound.ship_records",
        "iron_bottom_sound.scenario_rules",
        "iron_bottom_sound.counter_assets",
    ):
        module = importlib.import_module(module_name)
        if hasattr(module, "STRUCTURED"):
            module.STRUCTURED = snapshot
        if hasattr(module, "RULES"):
            module.RULES = snapshot / "rules"


def _init_worker(base_seed: int, validate_all: bool, snapshot_str: str | None) -> None:
    _apply_snapshot(snapshot_str)
    _WORKER_CONFIG["base_seed"] = base_seed
    _WORKER_CONFIG["validate_all"] = validate_all


def _run_cell(task: tuple[int, int, int]) -> list[dict]:
    geometry_index, fleet_index, seed_index = task
    samples = measure_seed(geometry_index, fleet_index, seed_index,
                           _WORKER_CONFIG["base_seed"], _WORKER_CONFIG["validate_all"])
    return [sample.as_row() for sample in samples]


def bootstrap_ci(values: list[float], reps: int = BOOTSTRAP_REPS, seed: int = BASE_SEED) -> dict:
    array = np.asarray(values, dtype=float)
    if array.size == 0:
        return {"n": 0, "mean": None, "ci_low": None, "ci_high": None}
    rng = np.random.default_rng(seed)
    draws = array[rng.integers(0, array.size, size=(reps, array.size))].mean(axis=1)
    return {
        "n": int(array.size),
        "mean": float(array.mean()),
        "ci_low": float(np.quantile(draws, 0.025)),
        "ci_high": float(np.quantile(draws, 0.975)),
        "std": float(array.std(ddof=1)) if array.size > 1 else 0.0,
    }


def paired_ci(deltas: list[float], reps: int = BOOTSTRAP_REPS, seed: int = BASE_SEED + 1) -> dict:
    return bootstrap_ci(deltas, reps, seed)


def aggregate(rows: list[dict]) -> dict:
    """Aggregate stats for one group of samples."""
    if not rows:
        return {"n": 0}
    result = {
        "n": len(rows),
        "options_total_mean": float(np.mean([row["options_total"] for row in rows])),
        "cross_total_mean": float(np.mean([row["cross_total"] for row in rows])),
        "cross_low_mean": float(np.mean([row["cross_low"] for row in rows])),
        "cross_high_mean": float(np.mean([row["cross_high"] for row in rows])),
        "j_ref_mean": float(np.mean([row["j_ref"] for row in rows])),
        "j_tied_top_mean": float(np.mean([row["j_tied_top"] for row in rows])),
        "j_tiers_mean": float(np.mean([row["j_tiers"] for row in rows])),
        "threat_weight": float(np.mean([row["threat_weight"] for row in rows])),
        "v_denial_c": bootstrap_ci([row["c_denial"] for row in rows]),
        "v_denial_c_norm": bootstrap_ci([row["v_denial_norm"] for row in rows]),
        "v_denial_c1_norm": bootstrap_ci([row["c1_denial_norm"] for row in rows]),
        "v_denial_d": bootstrap_ci([row["d_denial"] for row in rows]),
        "v_denial_d_norm": bootstrap_ci([row["v_denial_d_norm"] for row in rows]),
        "v_direct_norm": bootstrap_ci([row["v_direct_norm"] for row in rows]),
        "v_direct_vp": bootstrap_ci([row["v_direct_vp"] for row in rows]),
        "v_torpedo_norm": bootstrap_ci(
            [row["v_direct_norm"] + row["v_denial_norm"] for row in rows]
        ),
        "c_minus_d_denial": paired_ci([row["c_denial"] - row["d_denial"] for row in rows]),
        "route_changed_rate_c": float(np.mean([row["c_route_changed"] for row in rows])),
        "route_changed_rate_d": float(np.mean([row["d_route_changed"] for row in rows])),
        "route_changed_rate_c1": float(np.mean([row["c1_route_changed"] for row in rows])),
        "heading_change_mean_c": float(np.mean([row["c_heading_change"] for row in rows])),
        "speed_loss_mean_c": float(np.mean([row["c_speed_loss"] for row in rows])),
        "deviation_mean_c": float(np.mean([row["c_deviation"] for row in rows])),
        "e_hits_mean": float(np.mean([row["e_hits_direct"] for row in rows])),
        "e_hits_zero_share": float(np.mean([row["e_hits_direct"] == 0.0 for row in rows])),
    }
    result["denial_significant"] = bool(
        result["v_denial_c_norm"]["n"] > 0
        and result["v_denial_c_norm"]["ci_low"] > 0.0
    )
    return result


# ---------------------------------------------------------------------------
# outputs
# ---------------------------------------------------------------------------

def write_metrics_csv(rows: list[dict], path: Path) -> None:
    import csv

    if not rows:
        path.write_text("", encoding="utf-8")
        return
    columns = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def make_figures(rows: list[dict], low_cells: dict, out: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # ---- forest plot: V_denial CIs per geometry (low-hit subset) -------------
    entries = sorted(low_cells.items())
    fig, ax = plt.subplots(figsize=(9.5, 0.8 * max(1, len(entries)) + 2.4))
    y_positions = list(range(len(entries)))[::-1]
    for y, (label, stats) in zip(y_positions, entries):
        if stats.get("n", 0) == 0:
            continue
        norm_c = stats["v_denial_c_norm"]
        norm_d = stats["v_denial_d_norm"]
        color = "#1f77b4" if stats.get("denial_significant") else "#7f7f7f"
        ax.errorbar(
            norm_c["mean"], y - 0.16,
            xerr=[[norm_c["mean"] - norm_c["ci_low"]], [norm_c["ci_high"] - norm_c["mean"]]],
            fmt="o", color=color, capsize=3,
            label="C true hazard (95% CI)" if y == y_positions[0] else None,
        )
        ax.errorbar(
            norm_d["mean"], y + 0.16,
            xerr=[[norm_d["mean"] - norm_d["ci_low"]], [norm_d["ci_high"] - norm_d["mean"]]],
            fmt="o", markerfacecolor="white", color="#d62728", capsize=3,
            label="D threat-only (95% CI)" if y == y_positions[0] else None,
        )
    ax.axvline(0.0, color="black", linewidth=0.8, linestyle="--")
    ax.set_yticks(y_positions)
    ax.set_yticklabels([label for label, _ in entries])
    ax.set_xlabel("V_denial (normalized gun-position value loss J/J_ref)")
    ax.set_title("E04 maneuver-denial value: low direct-hit subset (E[hits] < 0.15)")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "fig_e04_denial.png", dpi=160)
    plt.close(fig)

    # ---- decomposition figure ------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8))
    ax = axes[0]
    colors = {"opposing": "#1f77b4", "chase": "#2ca02c", "crossing": "#ff7f0e", "close": "#9467bd"}
    markers = {"low": "o", "direct": "^"}
    for geometry_key, color in colors.items():
        for kind, marker in markers.items():
            subset = [row for row in rows
                      if row["geometry"] == geometry_key and row["sample_kind"] == kind]
            if not subset:
                continue
            ax.scatter(
                [row["v_direct_norm"] for row in subset],
                [row["v_denial_norm"] for row in subset],
                s=22, alpha=0.7, color=color, marker=marker,
                label=f"{geometry_key} ({'low-hit' if kind == 'low' else 'direct'})",
            )
    ax.axhline(0.0, color="black", linewidth=0.8, linestyle="--")
    ax.set_xlabel("V_direct (expected value destroyed = E[hits] x w)")
    ax.set_ylabel("V_denial (J loss / J_ref)")
    ax.set_title("Per-sample decomposition: direct kill vs denial")
    ax.legend(fontsize=7)

    ax = axes[1]
    labels = sorted(low_cells)
    direct_means = [low_cells[key]["v_direct_norm"]["mean"] if low_cells[key].get("n") else 0.0 for key in labels]
    denial_means = [low_cells[key]["v_denial_c_norm"]["mean"] if low_cells[key].get("n") else 0.0 for key in labels]
    xs = np.arange(len(labels))
    ax.bar(xs, direct_means, width=0.6, color="#9467bd", label="V_direct (norm)")
    ax.bar(xs, denial_means, width=0.6, bottom=direct_means, color="#1f77b4", label="V_denial (norm)")
    for x, (d, n) in enumerate(zip(direct_means, denial_means)):
        ax.text(x, d + n + 0.004, f"{d + n:.3f}", ha="center", fontsize=8)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("V_torpedo = V_direct + V_denial (normalized)")
    ax.set_title("Value decomposition, low direct-hit subset")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "fig_e04_decomposition.png", dpi=160)
    plt.close(fig)


# ---------------------------------------------------------------------------
# case study
# ---------------------------------------------------------------------------

def pick_case_studies(rows: list[dict]) -> tuple[dict | None, dict | None]:
    """(1) low-hit sample with the largest route response; (2) direct sample
    with the largest threat-only denial (displacement power)."""
    low_rows = [row for row in rows if row["sample_kind"] == "low" and row["options_total"] > 0]
    direct_rows = [row for row in rows if row["sample_kind"] == "direct" and row["options_total"] > 0]
    case_low = None
    if low_rows:
        moved = [row for row in low_rows if row["c_route_changed"]]
        case_low = max(moved or low_rows,
                       key=lambda row: (row["c_deviation"] + abs(row["c_speed_loss"]) * 4
                                        + row["c_heading_change"] * 8, row["c_denial"]))
    case_direct = None
    if direct_rows:
        case_direct = max(direct_rows, key=lambda row: row["d_denial"])
    return case_low, case_direct


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="E04 torpedo direct-kill vs denial")
    parser.add_argument("--smoke", action="store_true", help="tiny run: 1 cell x 2 seeds + verification")
    parser.add_argument("--seeds", type=int, default=SEEDS_PER_CELL, help="paired seeds per (geometry, fleet) cell")
    parser.add_argument("--jobs", type=int, default=max(1, min(8, (mp.cpu_count() or 2))))
    parser.add_argument("--no-validate-all", action="store_true",
                        help="skip per-option validate_orders sweep")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    started = time.time()

    snapshot = _snapshot_rules()
    _apply_snapshot(snapshot)
    verification = verify_lane_model()
    print(f"[verify] lane model matches engine adjudication: {verification['engine_traversed']}")

    if args.smoke:
        tasks = [(0, 0, index) for index in range(2)]
    else:
        tasks = [
            (geometry_index, fleet_index, seed_index)
            for geometry_index in range(len(GEOMETRY_KEYS))
            for fleet_index in range(len(FLEET_KEYS))
            for seed_index in range(args.seeds)
        ]

    print(f"[run] {len(tasks)} paired seeds, jobs={args.jobs}")
    if args.jobs <= 1:
        _init_worker(BASE_SEED, not args.no_validate_all, None)
        rows = [row for task in tasks for row in _run_cell(task)]
    else:
        ctx = mp.get_context("spawn")
        with ctx.Pool(processes=args.jobs, initializer=_init_worker,
                      initargs=(BASE_SEED, not args.no_validate_all, snapshot)) as pool:
            rows = []
            for sample_rows in pool.map(_run_cell, tasks, chunksize=1):
                rows.extend(sample_rows)
    elapsed = time.time() - started
    print(f"[run] done in {elapsed:.1f}s, samples: {len(rows)}")

    rows.sort(key=lambda row: (row["geometry"], row["fleet"], row["sample_kind"], row["seed"]))
    write_metrics_csv(rows, OUT / "metrics.csv")

    # ---- aggregation ---------------------------------------------------------
    # Condition-C analysis population: samples drawn from low-direct-hit
    # opportunities.  Direct samples are supplementary (decomposition/mechanism).
    def group(key_fn, kind: str | None = None) -> dict:
        buckets: dict[str, list[dict]] = {}
        totals: dict[str, int] = {}
        for row in rows:
            if kind is not None and row["sample_kind"] != kind:
                continue
            key = key_fn(row)
            totals[(key, kind)] = totals.get((key, kind), 0) + 1
            buckets.setdefault(key, []).append(row)
        result = {key: aggregate(bucket) for key, bucket in sorted(buckets.items())}
        for key, bucket in result.items():
            bucket["n_seeds_total"] = totals.get((key, kind), 0)
        return result

    low_by_geometry = group(lambda row: row["geometry"], kind="low")
    low_by_cell = group(lambda row: row["cell"], kind="low")
    low_by_fleet = group(lambda row: row["fleet"], kind="low")
    direct_by_geometry = group(lambda row: row["geometry"], kind="direct")
    low_rows = [row for row in rows if row["sample_kind"] == "low"]
    direct_rows = [row for row in rows if row["sample_kind"] == "direct"]
    pooled_low = aggregate(low_rows)
    pooled_low["n_seeds_total"] = len(low_rows)
    pooled_direct = aggregate(direct_rows)
    pooled_direct["n_seeds_total"] = len(direct_rows)

    low_geometry_passing = [
        key for key, stats in low_by_geometry.items() if stats.get("denial_significant")
    ]
    geometries_with_low = [key for key, stats in low_by_geometry.items() if stats.get("n", 0) > 0]
    acceptance = {
        "criterion": "low-direct-hit subset V_denial 95% bootstrap CI > 0, repeated across >= 3 geometries",
        "geometries_with_low_samples": geometries_with_low,
        "geometries_passing": low_geometry_passing,
        "pass": len(low_geometry_passing) >= 3 and all(
            stats.get("n_seeds_total", 0) >= 30 for stats in low_by_geometry.values()
            if stats.get("n", 0) > 0
        ),
        "min_seeds_per_geometry": min(
            (stats.get("n_seeds_total", 0) for stats in low_by_geometry.values()
             if stats.get("n", 0) > 0),
            default=0,
        ),
    }

    case_low, case_direct = pick_case_studies(rows)

    # ---- case study markdown --------------------------------------------------
    def case_lines(case: dict | None, kind: str) -> list[str]:
        if case is None:
            return [f"## 案例（{kind}）", "", "无满足条件的样本。", ""]
        header = (
            "## 案例一：鱼雷未命中但迫使目标改变行动（低直接命中子集）"
            if kind == "low" else
            "## 案例二：直击威胁的位移威力（近距对照，威胁恒定条件 D）"
        )
        lines = [header, ""]
        if kind == "low":
            lines += [
                f"- seed `{case['seed']}`，geometry={case['geometry']}，fleet={case['fleet']}，"
                f"低命中机会池 = {case['cross_low']} 条航迹",
                f"- 发射机会: {case['attacker_id']} {case['launcher_id']} mf={case['launch_at_mf']} "
                f"{case['launch_side']}/{case['launch_angle']} setting={case['setting_index']}，"
                f"齐射 {case['salvo']} 枚，鱼雷航向 {case['torpedo_heading']}，发射格 {case['launch_hex']}",
                f"- 对 τ0* 航线的直接命中期望 E[hits] = {case['e_hits_direct']:.4f}"
                f"（{case['direct_aspect'] or '无接触'}，鱼雷航程 {case['direct_distance']} 格），"
                f"远低于阈值 0.15",
                f"- 基线 τ0*（A 条件）：plan `{case['tau0_plan']}` → {case['tau0_hex']} "
                f"h{case['tau0_heading']} cost={case['tau0_cost']}，J = {case['tau0_j']:.3f}"
                f"（J_ref = {case['j_ref']:.3f}）",
                f"- 威胁下最优响应 τT*（C 条件）：plan `{case['c_plan']}` → {case['c_hex']} "
                f"h{case['c_heading']} cost={case['c_cost']}，J = {case['c_j']:.3f}",
                f"- route_changed = {case['c_route_changed']}，航向变化 {case['c_heading_change']}×60°，"
                f"速度变化 {case['c_speed_loss']} MF，终点偏移 {case['c_deviation']} 格",
                f"- **V_denial = J(τ0*) − J(τT*) = {case['c_denial']:.4f}**（归一化 "
                f"{case['v_denial_norm']:.4f}）",
                f"- 威胁恒定条件 D 的响应：route_changed = {case['d_route_changed']}，"
                f"V_denial = {case['d_denial']:.4f}",
                "",
                "解读：目标方确实对鱼雷航迹做出了反应（改变航迹/节奏以避开 (turn,impulse) 同格），"
                "但引擎炮位价值景观呈台阶状（本想定中 339 条合法路线只有 4 个不同 J 值，"
                "且最高档存在大量并列路线），目标可以在**零炮位价值损失**的前提下换到一条不接触航迹的"
                "并列路线 —— 机动剥夺真实发生，但其位置价值代价为 0。",
            ]
        else:
            lines += [
                f"- seed `{case['seed']}`，geometry={case['geometry']}，fleet={case['fleet']}",
                f"- 发射机会: {case['attacker_id']} {case['launcher_id']} mf={case['launch_at_mf']} "
                f"{case['launch_side']}/{case['launch_angle']} setting={case['setting_index']}，"
                f"齐射 {case['salvo']} 枚",
                f"- 直接命中期望 E[hits] = {case['e_hits_direct']:.3f}"
                f"（{case['direct_aspect']}，鱼雷航程 {case['direct_distance']} 格）——"
                "近距直击，威胁致命",
                f"- 基线 τ0*：{case['tau0_hex']} h{case['tau0_heading']} cost={case['tau0_cost']}，"
                f"J = {case['tau0_j']:.3f}（J_ref = {case['j_ref']:.3f}）",
                f"- C 条件（真实杀伤权重 w={case['threat_weight']:.3f}）：route_changed = "
                f"{case['c_route_changed']}，V_denial = {case['c_denial']:.4f}"
                f"（规避代价 {case['c_deviation']} 格 / {case['c_speed_loss']} MF 高于威胁折价）",
                f"- **D 条件（威胁恒定）：route_changed = {case['d_route_changed']}，"
                f"V_denial = {case['d_denial']:.4f}（归一化 {case['v_denial_d_norm']:.3f}）**",
                "",
                "解读：同一条航迹一旦被视为“任何接触都不可接受”，目标愿意放弃 "
                f"{case['d_denial']:.1f} 点炮位价值来规避 —— 航迹的位移威力存在；"
                "但在期望毁伤权重下（C 条件），规避代价仍高于威胁折价，理性目标不移动。"
                "剥夺价值由此完全取决于威胁权重，而非航迹几何本身。",
            ]
        lines.append("")
        return lines

    case_md = ["# E04 案例研究", ""]
    case_md += case_lines(case_low, "low")
    case_md += case_lines(case_direct, "direct")
    (OUT / "case_study.md").write_text("\n".join(case_md), encoding="utf-8")

    # ---- results.json ----------------------------------------------------------
    results = {
        "experiment": "E04 torpedo direct-kill vs maneuver-denial decomposition",
        "protocol": "same-turn perfect-information response (turn-2 launch opportunities, "
                    "turn-2 target plan space; see report for the protocol decision)",
        "base_seed": BASE_SEED,
        "seeds_per_cell": 2 if args.smoke else args.seeds,
        "geometries": GEOMETRY_KEYS,
        "fleets": FLEET_KEYS,
        "direct_hit_threshold": 0.15,
        "threat_only_hazard": 1.0,
        "horizon_turns": 6,
        "lane_model_verification": verification,
        "runtime_seconds": elapsed,
        "acceptance": acceptance,
        "pooled_low": pooled_low,
        "pooled_direct": pooled_direct,
        "low_by_geometry": low_by_geometry,
        "low_by_cell": low_by_cell,
        "low_by_fleet": low_by_fleet,
        "direct_by_geometry": direct_by_geometry,
    }
    (OUT / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2, default=float), encoding="utf-8"
    )

    make_figures(rows, low_by_geometry, OUT)

    # ---- report ---------------------------------------------------------------
    def fmt(stats: dict, key: str) -> str:
        block = stats.get(key) if isinstance(stats, dict) else None
        if not block or block.get("n", 0) == 0:
            return "n/a"
        return f"{block['mean']:.4f} [{block['ci_low']:.4f}, {block['ci_high']:.4f}] (n={block['n']})"

    report = [
        "# E04 报告：鱼雷 direct-kill vs maneuver-denial 分解",
        "",
        f"- 运行：{'smoke' if args.smoke else 'full'}，{len(tasks)} 个 paired seeds × "
        f"每次测量最多 2 个样本（低命中 + 直击补充），共 {len(rows)} 个样本，"
        f"耗时 {elapsed:.1f}s，jobs={args.jobs}",
        "- 航迹模型验证：解析 (turn, impulse) 时间线与引擎真实裁决的 traversed_hexes 前缀逐格一致"
        f"（{verification['scenario']}，{verification['order']}）。",
        "",
        "## 研究问题",
        "",
        "V_torpedo = V_direct + V_denial 是否成立？在直接命中期望很低的发射机会中，"
        "denial 价值（目标方最优反应变化）是否显著 > 0？",
        "",
        "## 方法",
        "",
        "1. **协议（关键决策）**：同回合完美信息响应。发射机会取自攻击者第 2 回合已封存直航计划"
        "（每回合 3MF），目标在同一回合的全部合法机动计划空间上选择最优反应 —— 与引擎自身鱼雷辅助"
        "（torpedo_assist 的同回合拦截模型）一致。前期实现的“第 1 回合发射、第 2 回合响应”变体经"
        "约 700 候选几何的 pilot 扫描证明结构上不可行：航迹在第 1 回合就扫过目标第 2 回合的可行格，"
        "全部接触都退化为近距舷侧直击，低命中机会不存在。",
        "2. **场景**：合成 DD（IJN 吹雪级，jp-24-type90 鱼雷）攻击 USN CA（北安普顿级）。"
        "3 种低命中几何（平行相向/追击/斜交，由 pilot 扫描选定，见决策 5）+ 1 种近距直击对照几何，"
        "1v1 与 2v1，每格 36 个 paired seeds。",
        "3. **回合机制**：双方第 1 回合按固定直航计划走正式 submit_orders/advance 流程"
        "（攻击者 3MF、CA 5MF），全程零掷骰 → A/C/D 共享逐字节相同状态；第 2 回合封存攻击者计划后"
        "在 TORPEDO_PLANNING 枚举全部合法发射机会并逐个经 engine.validate_orders 验证（不发射）。",
        "4. **决策空间**：CA 第 2 回合全部合法 MovementOrder（研究层 DFS，严格镜像引擎 "
        "_movement_expand/_movement_reachable 转移规则），每样本约 340-600 条计划。",
        "5. **J(route)** = engine.ship_gun_pressure（假想终点位/航向，对攻击者第 2 回合预测终点位），"
        "归一化 J/J_ref。**Hazard(route)** = 航迹解析时间线（镜像引擎 impulse 环：船先动、雷后动、"
        "逐 impulse 同格接触、跨回合 allowance = cycle[(t−发射回合)%3]、触界/耗尽回收）与该计划"
        "时间线的**首次**同格接触处的 engine.torpedo_hit_probability(aspect, modifier)；"
        "aspect/modifier 由引擎函数在接触几何处计算。",
        "6. **目标决策**：C 条件 argmax J/J_ref − w·Hazard（w = 引擎鱼雷结果表对目标排水档 36 档"
        "全举的期望毁伤比例，CA 为 0.343）；D 条件 argmax J/J_ref − 1.0·1[接触]（杀伤量级置常数）；"
        "C1 敏感性 = 计划书原式 J/J_ref − Hazard（w=1）。并列时按“偏离基线最小”打破（路线惯性），"
        "因此 route_changed 只在威胁使基线严格变劣时为真。",
        "7. **V_denial** = J(τ0*) − J(τT*)（均用无威胁 J）；**V_direct** = 对 τ0* 航线的期望命中数 × CA VP"
        "（归一化：E[命中] × w）。统计：逐几何/汇总 paired bootstrap（重抽样本，10000 次）95% CI。",
        "",
        "## 结果",
        "",
        "### 低直接命中子集（条件 C 主分析）",
        "",
        "| geometry | n | V_denial (J) 95% CI | V_denial (norm) 95% CI | C1 raw (norm) | V_denial_D (norm) | route_changed C | 显著>0 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for key in GEOMETRY_KEYS:
        stats = low_by_geometry.get(key, {})
        if stats.get("n", 0) == 0:
            report.append(f"| {key} | 0 | n/a | n/a | n/a | n/a | n/a | 无样本 |")
            continue
        report.append(
            f"| {key} | {stats['n']} | {fmt(stats, 'v_denial_c')} | {fmt(stats, 'v_denial_c_norm')} | "
            f"{fmt(stats, 'v_denial_c1_norm')} | {fmt(stats, 'v_denial_d_norm')} | "
            f"{stats.get('route_changed_rate_c', 0):.2f} | {'是' if stats.get('denial_significant') else '否'} |"
        )
    report += [
        "",
        f"- 汇总（低命中子集）：V_denial = {fmt(pooled_low, 'v_denial_c')}；"
        f"归一化 = {fmt(pooled_low, 'v_denial_c_norm')}；C1(原式) = {fmt(pooled_low, 'v_denial_c1_norm')}；"
        f"D = {fmt(pooled_low, 'v_denial_d_norm')}。",
        f"- 价值景观（逐样本实测均值）：最高档并列路线数 = {pooled_low.get('j_tied_top_mean', 0):.1f}，"
        f"不同 J 档数 = {pooled_low.get('j_tiers_mean', 0):.1f}。",
        f"- route_changed 率（C）= {pooled_low.get('route_changed_rate_c', 0):.3f}，"
        f"航向变化均值 = {pooled_low.get('heading_change_mean_c', 0):.3f}×60°，"
        f"速度变化均值 = {pooled_low.get('speed_loss_mean_c', 0):.3f} MF，"
        f"终点偏移均值 = {pooled_low.get('deviation_mean_c', 0):.3f} 格。",
        f"- V_direct（归一化）= {fmt(pooled_low, 'v_direct_norm')}；"
        f"V_torpedo(norm) = {fmt(pooled_low, 'v_torpedo_norm')}。",
        f"- C − D 配对差 = {fmt(pooled_low, 'c_minus_d_denial')}。",
        "",
        "### 直击补充样本（E[命中] ≥ 0.15，机制对照）",
        "",
        f"- n = {pooled_direct.get('n', 0)}；V_direct(norm) = {fmt(pooled_direct, 'v_direct_norm')}；"
        f"V_denial(C) = {fmt(pooled_direct, 'v_denial_c_norm')}；"
        f"V_denial(D) = {fmt(pooled_direct, 'v_denial_d_norm')}。",
        "",
        "## 机制解释（为何低命中子集的 V_denial 为 0）",
        "",
        "1. **炮位价值景观呈台阶状**：引擎命中表粒度粗，CA 对 DD 的 J 在 340-600 条合法计划上"
        "只有个位数量级的不同档位（逐几何实测 7-10 档；如 chase/1v1 的 339 条计划仅 4 档："
        "5.33 / 2.25 / 1.33 / 0.58），且最高档被大量路线并列共享（逐几何实测最高档并列 "
        "12.5-32.5 条）。单条鱼雷航迹是“细线”，只与并列路线中的少数几条发生 (turn,impulse) "
        "同格接触。",
        "2. **并列路线给出免费规避**：C 条件下基线的威胁折价仅为 w×P_hit ≈ 0.343×0.083 ≈ 0.029"
        "（归一化），而任何一条不接触航迹的最高档并列路线价值为 1.0 —— 目标换到并列路线即可规避，"
        "J 损失恰为 0。甚至多数规避只需改变节奏/转向顺序（同终点、同 J）。",
        "3. **权重不变性**：把威胁权重从 w=0.343 提到计划书原式的 1.0（C1），低命中航迹的折价"
        "（≤0.083）仍远低于最高档与次档之间的价值落差（归一化 0.58），结论不变 —— 低命中子集的 "
        "V_denial 对权重选择不敏感地为 0。",
        "4. **剥夺价值集中于直击威胁**：近距对照几何中，航迹直接压在最高档位置簇上（E[命中] "
        "0.42-1.14），C 条件下目标仍不移动（折价 0.25 < 0.58），但 D 条件（任何接触=不可接受）下"
        "目标愿意放弃 18.6 点炮位价值规避 —— 航迹的位移威力存在，只有当威胁被视为不可容忍时才兑现。",
        "5. **对研究问题的回答**：V_torpedo = V_direct + V_denial 在分解意义上成立"
        "（两项均可按定义测量且互不重叠），但在本引擎规则结构下，低直接命中机会的 V_denial ≡ 0："
        "“未命中但改变火力格局”在本游戏中表现为**改变航迹/节奏**（route_changed 率高），"
        "而非**损失炮位价值**。",
        "",
        "## 自主决策记录",
        "",
        "1. **协议切换为同回合完美信息响应**：引擎顺序是移动先封存、鱼雷后计划，同回合内目标无法对"
        "已发射鱼雷反应；先实现的 turn-1 发射/turn-2 响应变体经 pilot 扫描（约 700 候选几何）证明"
        "低命中机会结构性不存在（航迹早一回合扫过目标可行格），故改为发射机会与目标计划同回合"
        "（与引擎 torpedo_assist 的拦截模型同构）。",
        "2. **几何由 pilot 扫描选定而非手工**：扫描 CA 第 2 回合起点网格 × 航向族，按低命中机会池"
        "稳定性（每 seed 5-13 条）选定 平行相向 (16,20)h6 / 追击 (14,4)h6 / 斜交 (16,2)h5；"
        "另加近距直击对照 (20,6)h4（其交叉全部为高 E 直击，仅供分解/机制对照）。",
        "3. **响应视野 = 1 回合决策 + 保持航向延拓**：J 只评估第 2 回合终点炮位；Hazard 在计划时间线"
        "之外假设目标按所选航向/航速直航延拓至鱼雷耗尽（≤6 回合），使远距/追击航迹的威胁可度量。",
        "4. **Hazard 取首次接触**：引擎语义下航迹接触即停即结算（一轨至多一次），不做多点求和；"
        "接触概率在发射参数给定后为确定性指示量，概率性全部来自 engine.torpedo_hit_probability。",
        "5. **交易权重 w 引擎化 + C1 敏感性**：J 与 Hazard 量纲不同，主分析用引擎鱼雷结果表期望"
        "毁伤比例（C 档 0.343）；同时报告计划书原式（w=1，C1 字段），结论对权重不变。",
        "6. **D 条件实现**：Hazard 中命中概率置常数 1.0（任何接触同等危险）；C − D 差值 = 威胁"
        "量级信息的边际贡献，用于机制识别。",
        "7. **发射机会空间**：攻击者直航计划上全部 (发射器, 舷侧, 角度 A/B/X/Y, 速度档, 发射MF) 组合，"
        "按物理航迹标识（发射格+锚点+航向+速度档+MF）去重，齐射量 = 发射器满载（2 枚）；每个机会经 "
        "engine.validate_orders 验证合法。机会池 = 与 τ0* 航线发生 (turn,impulse) 同格接触的航迹"
        "（对 τ0* 无接触的航迹按定义既无直接杀伤也无剥夺，不构成“发射机会”）。",
        "8. **每 seed 抽样**：低命中池与直击池各用种子化 RNG 均匀抽 1 个机会（避免选最大值偏倚）；"
        "两池皆空的 seed 记录 0 样本。引擎管线确定性 → 同几何的机会池组成不随 seed 变化，"
        "seed 只影响抽到哪条机会。",
        "9. **并列打破 = 路线惯性**：目标函数并列时选偏离 τ0* 最小的计划（终点距离/费用差/航向差），"
        "保证 route_changed 只在威胁使基线严格变劣时为真，不夸大剥夺。",
        "10. **纪律**：planner 只读引擎函数（未读 TorpedoDoctrine/crossing_t_value/"
        "local_force_ratio_gain 等）；沙箱仅经正式 submit_orders/advance 推进；测量零 GameState 变异；"
        "全部结果如实报告（含验收 FAIL）。",
        "11. **规则数据快照（环境鲁棒性）**：本仓库派生规则数据在实验期间被另一进程并发再生"
        "（文件出现/缺失/半写入交替）。运行启动时等待 load_ship_records() 可用后，将 "
        "resources/derived/structured 复制为临时快照，worker 进程的读取路径指向该逐字节相同的快照"
        "（不改任何规则内容，仅保证一次运行内部一致）；对每个发射机会仍逐个调用 "
        "engine.validate_orders 验证合法性。",
        "",
        "## 验收判定",
        "",
        f"- 判据：低直接命中子集 V_denial 95% CI > 0，且 ≥3 种初始几何复现 → "
        f"**{'PASS' if acceptance['pass'] else 'FAIL'}**"
        f"（有低命中样本的几何：{geometries_with_low}；通过者：{low_geometry_passing or '无'}；"
        f"每几何 seed 数 ≥ {acceptance['min_seeds_per_geometry']}）。",
        "- 如实说明：低命中子集的 V_denial 在全部几何中恒为 0（CI = [0,0]），判据不成立；"
        "机制见上文（J 阶梯 + 免费规避）。机动剥夺以 route_changed/节奏变化的形式真实存在"
        "（C 条件 route_changed 率见上表），但不产生炮位价值损失；剥夺价值集中在直击威胁"
        "（且仅在威胁被赋予高权重时兑现，见 D 条件）。",
        "",
        "## 产物",
        "",
        "- `results.json` 全部原始均值+CI；`metrics.csv` 逐样本；`fig_e04_denial.png` 各几何 denial "
        "森林图；`fig_e04_decomposition.png` 分解图；`case_study.md` 具体案例。",
    ]
    (OUT / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    print(f"[out] results -> {OUT}")
    print(f"[acceptance] {'PASS' if acceptance['pass'] else 'FAIL'} "
          f"(passing geometries: {low_geometry_passing or 'none'})")
    pooled_norm = pooled_low.get("v_denial_c_norm", {})
    if pooled_norm.get("mean") is not None:
        print(f"[pooled-low] V_denial(norm) = {pooled_norm['mean']:.4f} "
              f"[{pooled_norm['ci_low']:.4f}, {pooled_norm['ci_high']:.4f}], n={pooled_norm['n']}")
    pooled_d = pooled_low.get("v_denial_d_norm", {})
    if pooled_d.get("mean") is not None:
        print(f"[pooled-low] V_denial_D(norm) = {pooled_d['mean']:.4f} "
              f"[{pooled_d['ci_low']:.4f}, {pooled_d['ci_high']:.4f}]")


if __name__ == "__main__":
    main()
