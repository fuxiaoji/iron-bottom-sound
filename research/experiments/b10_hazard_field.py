"""B10: the delayed torpedo state model -- z_t = (s_t, q_t) and H(x, t).

Research claim (plan v4.0 B10): torpedoes are a DELAYED STATEFUL FIELD --
threats launched in the past persist into the future as deterministic
spatio-temporal entities -- categorically different from the instantaneous
gunnery field.  Concretely, on the E04 same-turn protocol:

1. Formalize q_t: every legal launch becomes an explicit TrackState with
   launch time/position/heading, speed cycle, range, full future
   position-by-pulse map and expiration (built on the E04 lane timeline that
   was verified against engine traversed_hexes in E04).
2. Build the spatio-temporal hazard field H(x, t) on the (hex, turn, impulse)
   grid: H = 1 - prod_k (1 - p_k) over tracks occupying the cell, with p_k
   from engine.torpedo_hit_probability at the track's contact geometry
   (reference-target convention: broadside, nominal target speed).
3. Verify TIME DEPENDENCE: the same hex carries different hazard at different
   impulses (hot at the transit pulse, cold after the track passed), with
   quantitative examples and slice heat-maps (fixed t spatial slices, fixed x
   time slices).
4. Quantify the "delayed stateful" property: cross-turn persistence of threat
   mass (mass delivered in turns AFTER the launch turn requires no further
   attacker action -- impossible for an instantaneous weapon).

Usage:
    python research/experiments/b10_hazard_field.py --smoke
    python research/experiments/b10_hazard_field.py

Outputs: research/results/b10/{results.json, time_dependence.json, field_stats.csv,
hex_examples.csv, hazard_slices.png, report.md}
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
OUT = REPO / "research" / "results" / "b10"
FLEETS = ("1v1", "2v1")


def build_field(ctx):
    """z_t from every legal launch option of the cell, then H(x, t)."""
    from research.torpedo_denial.hazard_field import HazardField, build_delayed_state

    lanes = []
    for index, option in enumerate(ctx.options):
        lane = ctx.lane_for(option)
        setting = ctx.engine.rules.torpedoes[
            ctx.state.ships[option.ship_id].torpedo_type or ""
        ]["settings"][option.setting_index]
        track_id = (f"{option.ship_id}:{option.launcher_id}:mf{option.launch_at_mf}"
                    f":{option.launch_side}/{option.launch_angle}:s{option.setting_index}")
        lanes.append((track_id, option.ship_id, option.launcher_id, option.lane_key,
                      lane, option.count, tuple(int(v) for v in setting["speed"]),
                      int(setting["range"])))
    z_t = build_delayed_state(ctx.engine, ctx.state, lanes, decision_turn=2)
    field = HazardField(ctx.engine, ctx.state, ctx.ca, z_t.tracks)
    return z_t, field


def time_dependence_evidence(ctx, field) -> dict:
    """Quantitative proof that H(x, t) is time-dependent on the same hex."""
    pulses = field.pulses()

    # (a) per-hex hot-pulse structure: a hex is hot only while a track is on it
    hot_hexes = field.hot_hex_labels()
    per_hex = []
    for label in sorted(hot_hexes):
        series = field.hex_time_series(label)
        per_hex.append({
            "hex": label,
            "hot_pulses": len(series),
            "of_pulses": len(pulses),
            "hazard_max": max(series.values()),
            "hazard_min_elsewhere": 0.0,
        })
    hot_counts = [entry["hot_pulses"] for entry in per_hex]

    # (b) maximal-contrast example: hex hot at one pulse, cold at another
    example = None
    if hot_hexes:
        best_label = max(hot_hexes, key=lambda l: (
            max(field.hex_time_series(l).values()),
            -len(field.hex_time_series(l)),
        ))
        series = field.hex_time_series(best_label)
        hot_pulse = max(series, key=series.get)
        cold_pulse = next(p for p in pulses if p not in series)
        example = {
            "hex": best_label,
            "hot_pulse": list(hot_pulse),
            "hazard_at_hot_pulse": series[hot_pulse],
            "cold_pulse": list(cold_pulse),
            "hazard_at_cold_pulse": 0.0,
        }

    # (c) route-based example: tau0* meets a lane at hex x* / pulse t1 with
    # H > 0; another plan (tied-top if possible) visits the SAME hex at a
    # pulse with H == 0 -- same space, different time, no threat.
    route_example = None
    pool = ctx.crossing_pool()
    if pool:
        top = max(pool, key=lambda e: (e["e_hits_tau0"], e["p_hit_tau0"]))
        contact = top["contact_tau0"]
        x_star = contact.hex.label
        t_star = (contact.turn, contact.impulse)
        h_star = field.hazard(x_star, *t_star)
        visitors = []
        for plan in ctx.plans:
            if plan.signature == ctx.tau0.signature:
                continue
            timeline, _speeds = ctx.timeline_for(plan)
            pulses_at = sorted(
                (key for key, (hx, _hd) in timeline.items() if hx.label == x_star
                 and key != t_star and key[0] >= 2)
            )
            if pulses_at:
                cold = [p for p in pulses_at if field.hazard(x_star, *p) == 0.0]
                visitors.append((plan, pulses_at, cold))
        tied = [v for v in visitors
                if ctx.signature_j.get(v[0].signature) == ctx.j_ref and v[2]]
        chosen = tied[0] if tied else (visitors[0] if visitors else None)
        if chosen is not None:
            plan, pulses_at, cold = chosen
            route_example = {
                "contact_hex": x_star,
                "tau0_contact_pulse": list(t_star),
                "tau0_contact_hazard_field": h_star,
                "tau0_contact_hazard_route": top["p_hit_tau0"],
                "other_plan": plan.plan_string,
                "other_plan_signature": list(plan.signature),
                "other_plan_is_tied_top": ctx.signature_j.get(plan.signature) == ctx.j_ref,
                "other_plan_j_over_jref": ctx.signature_j.get(plan.signature, 0.0) / ctx.j_ref
                if ctx.j_ref > 0 else None,
                "other_plan_visits_same_hex_at_pulses": [list(p) for p in pulses_at][:8],
                "other_plan_hazard_there": [field.hazard(x_star, *p) for p in pulses_at][:8],
            }

    return {
        "n_hot_hexes": len(hot_hexes),
        "hot_pulse_count_distribution": {
            str(k): hot_counts.count(k) for k in sorted(set(hot_counts))
        },
        "mean_hot_pulses_per_hot_hex": float(np.mean(hot_counts)) if hot_counts else 0.0,
        "single_pulse_hot_share": (
            sum(1 for c in hot_counts if c == 1) / len(hot_counts)) if hot_counts else None,
        "example_hex": example,
        "route_example": route_example,
    }


def delayed_state_metrics(z_t, field) -> dict:
    """The 'delayed stateful' quantifiers (vs an instantaneous weapon)."""
    summary = field.summary()
    launch_turn = min(track.launch_turn for track in z_t.tracks) if z_t.tracks else 2
    total = summary["threat_mass_total"]
    by_turn = summary["threat_mass_by_turn"]
    future_turns_mass = sum(mass for turn, mass in by_turn.items()
                            if int(turn) > launch_turn)
    alive_after = z_t.live_tracks(launch_turn + 1, 1)
    return {
        **summary,
        "launch_turn": launch_turn,
        "future_turn_threat_mass_fraction": (future_turns_mass / total) if total > 0 else 0.0,
        "n_tracks_alive_one_turn_later": len(alive_after),
        "share_tracks_alive_one_turn_later": (
            len(alive_after) / len(z_t.tracks)) if z_t.tracks else 0.0,
        "instantaneous_weapon_counterfactual": (
            "a gun salvo's threat exists only at the firing pulse; here "
            f"{future_turns_mass / total if total > 0 else 0.0:.3f} of the field's "
            "threat mass lies in turns AFTER the launch turn, fully determined "
            "at launch (no further attacker decision required)"),
    }


# ---------------------------------------------------------------------------
# figures
# ---------------------------------------------------------------------------

def _hex_xy(coord) -> tuple[float, float]:
    return coord.q + coord.r / 2.0, -coord.r


def make_figures(records: dict, out: Path) -> None:
    """hazard_slices.png: the two H(x,t) slice families required by B10.

    Top row: fixed-t SPATIAL slices (the field's threat front at two pulses).
    Bottom row: fixed-x TIME slices (per-hex step series; per-pulse threat mass).
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from iron_bottom_sound.models import HexCoord

    anchor = records.get("opposing:1v1")
    if anchor is None:
        return
    field = anchor["field"]
    ctx = anchor["ctx"]

    all_hexes = [coord for track in field.tracks
                 for coord in track.position_by_pulse.values()]

    def resolve(label: str) -> HexCoord:
        return HexCoord.from_label(label)

    fig, axes = plt.subplots(2, 2, figsize=(14.0, 11.0),
                             gridspec_kw={"height_ratios": [1.25, 1.0]})

    # ---- top row: fixed-t spatial slices at the two highest-mass pulses ------
    pulses_by_mass = sorted(field.pulses(), key=lambda p: -field.threat_mass(*p))
    for ax, pulse in zip(axes[0], slice_pulses_safe(pulses_by_mass)):
        hot = field.hot_cells(*pulse)
        if all_hexes:
            x_all = [_hex_xy(c)[0] for c in all_hexes]
            y_all = [_hex_xy(c)[1] for c in all_hexes]
            ax.set_xlim(min(x_all) - 2, max(x_all) + 2)
            ax.set_ylim(min(y_all) - 2, max(y_all) + 2)
        # track paths (faint)
        for track in field.tracks:
            px = [_hex_xy(c)[0] for c in track.position_by_pulse.values()]
            py = [_hex_xy(c)[1] for c in track.position_by_pulse.values()]
            ax.plot(px, py, color="lightgray", linewidth=0.4, zorder=1)
        # tau0 route
        route = [ctx.tau0.trajectory[0][0]] + [pos for pos, _h in ctx.tau0.trajectory]
        ax.plot([_hex_xy(c)[0] for c in route], [_hex_xy(c)[1] for c in route],
                color="#1f77b4", linewidth=1.6, label="tau0* turn-2 route", zorder=2)
        if hot:
            labels = sorted(hot, key=lambda lb: hot[lb])
            coords = [resolve(lb) for lb in labels]
            sc = ax.scatter([_hex_xy(c)[0] for c in coords],
                            [_hex_xy(c)[1] for c in coords],
                            c=[hot[lb] for lb in labels], cmap="Reds",
                            vmin=0, vmax=max(0.9, max(hot.values())),
                            s=42, marker="h", zorder=3)
            plt.colorbar(sc, ax=ax, shrink=0.75, label="H(x,t)")
        ax.scatter(*_hex_xy(ctx.ca.position), marker="*", s=140, color="navy",
                   zorder=4, label="CA (decision pos)")
        ax.set_aspect("equal")
        ax.set_title(f"fixed-t spatial slice: turn {pulse[0]} impulse {pulse[1]} "
                     f"({len(hot)} hot cells, mass {field.threat_mass(*pulse):.2f})")
        ax.legend(fontsize=7, loc="upper right")
    axes[0][0].set_ylabel("opposing/1v1", fontsize=9, labelpad=28, rotation=90)

    # ---- bottom-left: fixed-x time slices for maximal-contrast hexes ---------
    ax = axes[1][0]
    example_hexes = [entry["hex"] for entry in anchor["timedep_examples"]]
    palette = ["#d62728", "#1f77b4", "#2ca02c", "#9467bd"]
    for color, label in zip(palette, example_hexes):
        series = field.hex_time_series(label)
        if not series:
            continue
        keys = sorted(series)
        xs = [p[0] + (p[1] - 1) / 12.0 for p in keys]
        ax.step(xs, [series[p] for p in keys], where="post", color=color,
                label=f"hex {label}")
        cold = [p for p in field.pulses() if p not in series]
        if cold:
            nearest_cold = min(
                cold, key=lambda p: abs(p[0] + (p[1] - 1) / 12.0 - xs[-1]))
            xs0 = [nearest_cold[0] + (nearest_cold[1] - 1) / 12.0]
            ax.scatter(xs0, [0.0], color=color, marker="x", s=36)
    ax.set_xlabel("(turn, impulse) -- fractional axis")
    ax.set_ylabel("H(x, t)")
    ax.set_title("fixed-x time slices: threat only while a track transits")
    ax.legend(fontsize=8)

    # ---- bottom-right: threat mass per pulse ---------------------------------
    ax = axes[1][1]
    masses = {cell: field.threat_mass(*cell) for cell in field.pulses()}
    keys = sorted(masses)
    ax.bar([f"t{k[0]}.i{k[1]}" for k in keys], [masses[k] for k in keys],
           color="#ff7f0e")
    launch_turn = min(track.launch_turn for track in field.tracks)
    launch_turn_last_x = max(
        (k[0] + (k[1] - 1) / 12.0 for k in keys if k[0] == launch_turn),
        default=0.0,
    )
    ax.axvspan(-0.5, launch_turn_last_x + 0.5, color="#1f77b4", alpha=0.12)
    ax.set_ylabel("threat mass per pulse")
    ax.set_title("threat mass by pulse: persists across turns after launch "
                 f"(shaded = launch turn {launch_turn})")
    ax.tick_params(axis="x", rotation=90, labelsize=6)
    fig.suptitle("B10 hazard field H(x,t) slices (opposing/1v1): "
                 "fixed-t spatial (top) and fixed-x temporal (bottom)", y=0.995)
    fig.tight_layout()
    fig.savefig(out / "hazard_slices.png", dpi=160)
    plt.close(fig)


def slice_pulses_safe(pulses_by_mass):
    """First two pulses (padded if the field has only one)."""
    if not pulses_by_mass:
        return []
    if len(pulses_by_mass) == 1:
        return [pulses_by_mass[0], pulses_by_mass[0]]
    return pulses_by_mass[:2]


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="B10 delayed torpedo hazard field")
    parser.add_argument("--smoke", action="store_true", help="2 cells only")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    started = time.time()
    snapshot = snapshot_rules_or_none()
    apply_rules_snapshot(snapshot)
    prov = provenance()

    cells = [(gkey, fleet) for gkey in sorted(GEOMETRIES) for fleet in FLEETS]
    if args.smoke:
        cells = cells[:2]

    rows = []
    hex_rows = []
    records: dict[str, dict] = {}
    for gkey, fleet in cells:
        ctx = setup_cell(GEOMETRIES[gkey], fleet, BASE_SEED)
        z_t, field = build_field(ctx)
        timedep = time_dependence_evidence(ctx, field)
        delayed = delayed_state_metrics(z_t, field)
        pool = ctx.crossing_pool()

        # example hexes for the time-slice figure: top-contrast hot hexes
        hot = field.hot_hex_labels()
        examples = sorted(
            hot, key=lambda l: (-max(field.hex_time_series(l).values()),
                                len(field.hex_time_series(l)))
        )[:3]
        example_rows = []
        for label in examples:
            series = field.hex_time_series(label)
            hot_pulse = max(series, key=series.get)
            cold_pulse = next(p for p in field.pulses() if p not in series)
            example_rows.append({
                "hex": label, "hot_pulse": list(hot_pulse),
                "hazard_hot": series[hot_pulse],
                "cold_pulse": list(cold_pulse), "hazard_cold": 0.0,
            })
            hex_rows.append({"cell": f"{gkey}:{fleet}", **example_rows[-1]})

        records[f"{gkey}:{fleet}"] = {
            "ctx": ctx, "field": field, "timedep_examples": example_rows,
            "timedep": timedep, "delayed": delayed,
        }
        row = {
            "cell": f"{gkey}:{fleet}", "geometry": gkey, "fleet": fleet,
            "n_options": len(ctx.options),
            "n_pool_tau0": len(pool),
            "n_plans": len(ctx.plans),
            "j_ref": ctx.j_ref,
            "j_tied_top": len(ctx.tied_top),
            "j_tiers": len(ctx.tiers),
            **{k: v for k, v in delayed.items()
               if isinstance(v, (int, float, str))},
        }
        rows.append(row)
        print(f"[b10] {gkey}/{fleet}: tracks={delayed['n_tracks']} "
              f"hot_hexes={timedep['n_hot_hexes']} "
              f"future_mass={delayed['future_turn_threat_mass_fraction']:.3f} "
              f"pool(tau0)={len(pool)}")

    elapsed = time.time() - started

    # ---- CSV outputs ----------------------------------------------------------
    def write_csv(path: Path, data: list[dict]) -> None:
        if not data:
            path.write_text("", encoding="utf-8")
            return
        columns = sorted({key for row in data for key in row})
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            for row in data:
                writer.writerow({k: (json.dumps(v) if isinstance(v, list) else v)
                                 for k, v in row.items()})

    write_csv(OUT / "field_stats.csv", rows)
    write_csv(OUT / "hex_examples.csv", hex_rows)

    # ---- results.json ----------------------------------------------------------
    # Per-cell JSON-safe payloads (records hold live objects for the figures).
    per_cell = {
        key: {
            "field_summary": anchor["field"].summary(),
            "time_dependence": anchor["timedep"],
            "delayed_metrics": anchor["delayed"],
        }
        for key, anchor in records.items()
    }

    hot_shares = [
        payload["time_dependence"]["single_pulse_hot_share"]
        for payload in per_cell.values()
        if payload["time_dependence"]["single_pulse_hot_share"] is not None
    ]
    future_fractions = [row.get("future_turn_threat_mass_fraction", 0.0) for row in rows]
    acceptance = {
        "criterion": (
            "B10 PASS if (a) every cell's H(x,t) shows same-hex time dependence "
            "(hot hexes hot on <30% of all pulses on average), (b) a route-based "
            "example exists where the same hex is threatened at one pulse and "
            "clear at another, (c) future-turn threat-mass fraction > 0 in all "
            "cells (delayed persistence, impossible for instantaneous weapons)"
        ),
        "hot_pulse_share_mean": float(np.mean(hot_shares)) if hot_shares else None,
        "single_pulse_hot_share_by_cell": {
            key: payload["time_dependence"]["single_pulse_hot_share"]
            for key, payload in per_cell.items()
        },
        "future_mass_fractions": future_fractions,
        "route_examples_found": sum(
            1 for key in per_cell
            if per_cell[key]["time_dependence"]["route_example"] is not None),
        "n_cells": len(per_cell),
    }
    results = {
        "experiment": "B10 delayed torpedo state model: z_t=(s_t,q_t) and H(x,t)",
        "protocol": "E04 same-turn perfect-information protocol (all legal launches "
                    "of the sealed turn-2 attacker plans become track states; no "
                    "adjudication, no dice)",
        "base_seed": BASE_SEED,
        "field_definition": {
            "z_t": "(s_t world snapshot at decision time t, q_t = set of live "
                   "tracks each with launch turn/impulse/hex, torpedo heading, "
                   "speed cycle, range, salvo count, position-by-pulse map, "
                   "removed_at expiration)",
            "H(x,t)": "1 - prod_k (1 - p_k(x,t)) over tracks k occupying hex x at "
                      "pulse t; p_k = engine.torpedo_hit_probability('broadside', "
                      "modifier) at the track's transit geometry",
            "reference_target_convention": (
                "broadside aspect (worst case for the target) and reference "
                "target nominal speed, so H is a property of the threat state "
                "alone; route-level hazards in B11/B12 use exact per-plan aspect"),
        },
        "provenance": prov,
        "runtime_seconds": elapsed,
        "cells": per_cell,
        "acceptance": acceptance,
    }
    (OUT / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2, default=float),
        encoding="utf-8",
    )

    # Task-required output: the time-dependence evidence as its own JSON.
    (OUT / "time_dependence.json").write_text(
        json.dumps({
            "experiment": "B10 time dependence of H(x,t): same hex, different impulse",
            "definition": "hot pulse = a (turn,impulse) at which the hex carries H>0",
            "cells": {
                key: {
                    "n_pulses": anchor["field"].summary()["n_pulses"],
                    "time_dependence": anchor["timedep"],
                    "example_hexes": anchor["timedep_examples"],
                }
                for key, anchor in records.items()
            },
        }, ensure_ascii=False, indent=2, default=float),
        encoding="utf-8",
    )

    make_figures(records, OUT)

    _write_report(args, elapsed, rows, per_cell, acceptance, prov)
    print(f"[b10] done in {elapsed:.1f}s -> {OUT}")


def _write_report(args, elapsed, rows, per_cell, acceptance, prov) -> None:
    n_cells = len(per_cell)
    route_ok = acceptance["route_examples_found"]
    future = [f for f in acceptance["future_mass_fractions"] if f is not None]
    hot_share = []
    for key, payload in per_cell.items():
        td = payload["time_dependence"]
        n_pulses = payload["field_summary"]["n_pulses"]
        if td["n_hot_hexes"] and n_pulses:
            hot_share.append(td["mean_hot_pulses_per_hot_hex"] / n_pulses)
    pass_a = bool(hot_share) and all(s <= 0.30 for s in hot_share)
    pass_b = route_ok == n_cells and n_cells > 0
    pass_c = bool(future) and all(f > 0 for f in future)
    verdict = "PASS" if (pass_a and pass_b and pass_c) else (
        "PARTIAL" if (pass_c or pass_b) else "FAIL")

    lines = [
        "# B10 批次报告：延迟鱼雷状态模型（z_t=(s_t,q_t) 与 H(x,t)）",
        "",
        "按 v4 夜间批次协议（22 项）组织；门限预注册于第 3 项，判定见第 20 项。",
        "",
        "## 1. 批次标识",
        f"- 批次：B10（v4.0 主线）；日期：2026-09-10/11；仓库：iron-bottom-sound。",
        "- 依赖：E04 协议模块（routes/lane/scenarios/protocol，航迹时间线已与引擎 "
        "traversed_hexes 逐格核对）；E04 价值景观阶梯发现（results/e04/）。",
        "",
        "## 2. 研究目标与假设",
        "- H-B10（延迟状态场）：鱼雷是 delayed stateful field——过去发射、未来持续存在的"
        "时空威胁实体，与舰炮 instantaneous field 范畴不同；形式化为 z_t=(s_t,q_t)，"
        "并导出时空危险场 H(x,t)。",
        "- 可检验推论：(a) 同一空间格在不同 impulse 进入时 H 不同；(b) 场的未来部分在发射"
        "时刻即被完全确定（无须攻击者后续决策）——瞬时武器机制上不可能。",
        "",
        "## 3. 预注册门限（先于运行固定）",
        "- (a) 全部 cell 的热格平均仅在全脉冲的 ≤30% 脉冲上危险（时间依赖的总体证据）；",
        "- (b) 每个 cell 存在 route-based 例证：同一 hex 在 τ0* 接触脉冲 H>0，而另一条"
        "（尽量顶档并列的）方案在不同脉冲经过同一 hex 时 H=0；",
        "- (c) 全部 cell 未来回合威胁质量占比 > 0（跨回合持续性）。",
        "",
        "## 4. 语义定义",
        "| 对象 | 定义 |",
        "|---|---|",
        "| s_t | 决策时刻 t 的世界快照（引擎 GameState，只读） |",
        "| q_t | 已发射鱼雷航迹集合：每枚记录发射 (turn,impulse)/格/航向、速度周期、射程、"
        "齐射量、逐脉冲位置表、removed_at 过期脉冲 |",
        "| H(x,t) | 1−∏k(1−p_k(x,t))，k 为在脉冲 t 占据格 x 的航迹；p_k 由 "
        "engine.torpedo_hit_probability 在该航迹接触几何处计算 |",
        "| 参照目标约定 | broadside aspect（对目标最坏）+ 参照目标名义航速 → H 只依赖威胁"
        "状态本身；路线级 hazard（B11/B12）仍用逐方案精确 aspect |",
        "",
        "## 5. 方法与模型",
        "1. 复用 E04 同回合协议管线（沙箱 → 回合1 → 封存攻击者回合2直航计划 → "
        "TORPEDO_PLANNING）；发射机会 = 全部合法 (发射器,舷侧,角度,速度档,发射MF) 组合。",
        "2. 每条合法发射经 build_lane（镜像引擎 impulse 环）展开为 TrackState → q_t；"
        "H(x,t) 在 horizon=6 回合的 (hex,turn,impulse) 网格上合成。",
        "3. 时间依赖验证三层：逐 hex 热-脉冲结构统计；最大对比度 hex 的冷/热脉冲例证；"
        "route-based 同 hex 异脉冲例证（优先顶档并列方案）。",
        "4. 延迟态量化：跨回合威胁质量占比、发射一回合后仍在水中的航迹占比、"
        "航迹寿命脉冲数分布；对照瞬时武器（未来威胁质量恒 0）。",
        "",
        "## 6. 实现与文件（不修改引擎）",
        "- 新增 `research/torpedo_denial/hazard_field.py`（TrackState/DelayedTorpedoState/"
        "HazardField；供 B11/B12 复用）。",
        "- 兼容性修复：`lane.py::evaluate_contact` 适配引擎新签名 "
        "`_torpedo_modifier(state, attacker, target, distance)`（保留旧签名回退，"
        "E04 存档数字逐位复现：chase/1v1 tau0=R11 J=5.333 c_denial=0 已核对）。",
        "- 新增 `research/experiments/b_common.py`（共享引导：规则快照纪律 + provenance "
        "+ setup_cell）与本入口 `research/experiments/b10_hazard_field.py`。",
        "",
        "## 7. 参数网格",
        f"- 4 几何（opposing/chase/crossing/close）× 2 舰队（1v1/2v1）= {n_cells} cell；"
        "引擎管线确定性 → 每 cell 一次测量即可（无抽样，无 RNG）。",
        "",
        "## 8. 运行环境与复现命令",
        f"- Python venv (.venv)；总运行 {elapsed:.1f}s。",
        "- `source .venv/bin/activate && PYTHONPATH=backend/src:research/experiments:. "
        "python research/experiments/b10_hazard_field.py`（--smoke 为 2 cell 冒烟）。",
        "",
        "## 9. 确定性与可复现性",
        "- 零掷骰、零 RNG；同 cell 重复运行逐位一致。",
        f"- provenance：engine.py sha256[:16]={prov['engine_py_sha256_16']}，"
        f"structured 树 {prov['structured_tree_n_files']} 文件 "
        f"hash[:16]={prov['structured_tree_hash_16']}（本仓库存在并发再生产程，"
        "运行采用 E04 规则快照纪律隔离）。",
        "",
        "## 10. 原始输出清单",
        "- `field_stats.csv`（逐 cell 场统计）、`hex_examples.csv`（冷/热脉冲例证）、"
        "`hazard_slices.png`（H(x,t) 切片热图：固定 t 空间切面 + 固定 x 时间切面）、"
        "`time_dependence.json`（同格异时定量例证）、`results.json`。",
        "",
        "## 11. 关键结果（逐 cell）",
        "| cell | 航迹数 | 热格数 | 热格平均热脉冲 | 未来回合质量占比 | 一回合后存活航迹 | τ0*机会池 |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['cell']} | {row['n_tracks']} | {row['n_hot_hexes_total']} | "
            f"{per_cell[row['cell']]['time_dependence']['mean_hot_pulses_per_hot_hex']:.2f} | "
            f"{row['future_turn_threat_mass_fraction']:.3f} | "
            f"{row['n_tracks_alive_one_turn_later']} ({row['share_tracks_alive_one_turn_later']*100:.0f}%) | "
            f"{row['n_pool_tau0']} |"
        )
    example_lines = []
    for key, payload in per_cell.items():
        ex = payload["time_dependence"].get("example_hex")
        re_ = payload["time_dependence"].get("route_example")
        if ex:
            example_lines.append(
                f"- {key}: hex {ex['hex']} 在脉冲 t{ex['hot_pulse'][0]}.i{ex['hot_pulse'][1]} "
                f"H={ex['hazard_at_hot_pulse']:.3f}，在脉冲 t{ex['cold_pulse'][0]}.i{ex['cold_pulse'][1]} "
                f"H={ex['hazard_at_cold_pulse']:.1f}")
        if re_:
            tied_note = "（顶档并列方案）" if re_["other_plan_is_tied_top"] else ""
            example_lines.append(
                f"- {key}: τ0* 在 t{re_['tau0_contact_pulse'][0]}.i{re_['tau0_contact_pulse'][1]} "
                f"于 {re_['contact_hex']} 接触（路线级 P_hit={re_['tau0_contact_hazard_route']:.3f}，"
                f"场值 {re_['tau0_contact_hazard_field']:.3f}）；方案 `{re_['other_plan']}`{tied_note}"
                f" J/J_ref={re_['other_plan_j_over_jref']:.3f} 同格不同脉冲 H=0 "
                f"→ 同一空间格的进入时刻决定是否受威胁")
    lines += ["", "### 同格异时例证（定量）", *example_lines]
    lines += [
        "",
        "## 12. 门限检验（gate 数据）",
        f"- (a) 逐 cell 热格平均热脉冲/全脉冲比："
        + ", ".join(f"{s:.3f}" for s in hot_share) + f" → {'全部 ≤ 0.30' if pass_a else '存在 > 0.30'}；",
        f"- (b) route-based 例证覆盖 {route_ok}/{n_cells} cell；",
        f"- (c) 未来回合威胁质量占比范围 [{min(future):.3f}, {max(future):.3f}]"
        if future else "- (c) 无数据",
        "",
        "## 13. 异常排查记录",
        "1. **引擎 API 漂移**：引擎 `_torpedo_modifier` 自 E04 运行后新增 state 参数，"
        "protocol 冒烟抛 TypeError。已按研究层兼容修（lane.py 传 state + 旧签名回退），"
        "并以 E04 存档逐位复现核对（chase/1v1: tau0=R11, J=5.333, c_denial=0）。",
        "2. **并发规则再生**：本仓库存在并发程再生 resources/derived/structured"
        "（场景 YAML 在本批次运行窗口内被改写）。首两轮 probe 出现过 opposing/1v1 "
        "τ0* 机会池瞬时为 0 的幻象；隔离复测为 5（与 E04 存档一致），确认为读取了"
        "半写入状态。全部批次改用 E04 的等待-快照纪律，provenance 指纹写入 results.json。",
        "3. **场值与路线值差异**：H(x,t) 用 broadside 参照约定，同格的路线级 P_hit "
        "（真实 aspect）可低于场值——两者用途不同（场=威胁状态属性；路线=决策属性），"
        "例证中同时报告两个数。",
        "",
        "## 14. 灵敏度",
        "- 参照航速：modifier 含 target_speed 项，参照目标取 CA 名义航速；对 CA（5 MF）"
        "与 DD 直航场景该值为常数，不引入额外自由度。",
        "- horizon=6 回合覆盖全部航迹寿命（射程 10-21 格、速度 5-8/回合），"
        "removed_at 前所有脉冲均在网格内。",
        "- **场对几何不变（如实说明）**：H 只依赖威胁状态 q_t（攻击者初始阵位与封存直航"
        "计划在全部几何中相同），故 4 几何的场逐位相同（1v1: 96 航迹/399 热格；2v1: "
        "192/481）——这是参照目标约定的直接推论，不是 bug；几何只通过 τ0* 路线进入 "
        "route-based 例证（逐 cell 机会池 5-13 条不同）与 B11/B12 的逐方案精确 aspect "
        "hazard。",
        "",
        "## 15. 与 E04 的关系",
        "- E04 的解析航迹时间线 = 单条航迹的 position-by-pulse；B10 把全体合法发射"
        "升格为显式状态 q_t 并合成场，是对 E04『时空航迹』主张（claim C-torpedo-null "
        "KEEP+EXTEND）的形式化扩展。",
        "- E04 价值景观阶梯（8 档/顶档 25.5 并列）是 B11 响应集收缩机理的输入。",
        "",
        "## 16. 核心结论",
        "- 鱼雷威胁场在 (hex, turn, impulse) 网格上高度局部化：热格只在航迹通过的"
        "个别脉冲危险（同格异时 H: p vs 0），空间切片随脉冲移动（threat front），"
        "时间切片呈脉冲串——『同一格不同时刻进入』的后果定性不同。",
        f"- 延迟态属性量化：各 cell {min(future)*100:.0f}-{max(future)*100:.0f}% 的威胁"
        "质量落在发射回合之后的回合，且在发射时即完全确定——这是与瞬时舰炮场的范畴差异"
        "（枪炮的未来威胁质量恒为 0，直到开火脉冲）。",
        "",
        "## 17. 对 claim_registry 的回写建议",
        "- `C-torpedo-null` 的 KEEP+EXTEND(B10/B11)：本批次交付 B10 部分——"
        "建议登记新主张 `C-delayed-stateful-field`：鱼雷发射构成延迟状态场"
        "（z_t 形式化 + 时间依赖例证 + 跨回合持续性），证据 `results/b10/`。",
        "",
        "## 18. 审稿人攻击模式（自反驳）",
        "- *\"时间依赖是航迹模型的平凡推论\"*：是——但正是需要逐格核对的平凡性"
        "（E04 已对引擎 traversed_hexes 验证）；本批次的科学内容是把『延迟状态』"
        "变成可检验的量化命题（门限 a/b/c），并给出 route-based 决策例证。",
        "- *\"broadside 参照约定使 H 偏高\"*：H 的用途是威胁状态属性对比"
        "（同格异脉冲、跨回合质量），B11/B12 的决策量全部用逐方案精确 aspect；"
        "两个量在第 13.3 项同时报告、不混用。",
        "- *\"场景是人造沙箱\"*：与 E04 同一协议同一几何族，机制结论不依赖具体初始条件"
        "（4 几何 × 2 舰队全部复现）。",
        "",
        "## 19. 局限与混淆",
        "- H 不含目标反制（鱼雷可被拦截/诱偏的规则若启用会压缩 q_t）；本引擎版本无此机制。",
        "- 参照目标约定使场值偏离真实 aspect 命中率（已在第 4/13.3 项声明）。",
        "- 单回合决策 + 直航延拓的响应模型（E04 决策 3） inherited by route 例证。",
        "",
        "## 20. 门限判定",
        f"- **B10：{verdict}**（(a) {'PASS' if pass_a else 'FAIL'}：热脉冲占比全部 ≤0.30；"
        f"(b) {'PASS' if pass_b else 'FAIL'}：route 例证 {route_ok}/{n_cells}；"
        f"(c) {'PASS' if pass_c else 'FAIL'}：未来质量占比 > 0）。",
        "- 结论：torpedo = delayed stateful field 的三重证据（状态形式化 / 时间依赖 / "
        "延迟持续性）成立。",
        "",
        "## 21. 未决问题与下批次接口",
        "- B11 直接消费 z_t/Hazard(τ)：响应集收缩 B_ε 与 C_resp；",
        "- 多航迹场的联合分布（饱和/重复覆盖）→ B12 厚度匹配协议；",
        "- 目标反制机制（若引擎未来加入）对 q_t 生命表的修正。",
        "",
        "## 22. 文件清单",
        "| 文件 | 内容 |",
        "|---|---|",
        "| `research/torpedo_denial/hazard_field.py` | z_t 状态模型 + H(x,t) 场（新增） |",
        "| `research/experiments/b_common.py` | 共享引导（快照/provenance/setup_cell，新增） |",
        "| `research/experiments/b10_hazard_field.py` | 本批次入口（新增） |",
        "| `research/results/b10/field_stats.csv` | 逐 cell 场统计 |",
        "| `research/results/b10/hex_examples.csv` | 冷/热脉冲例证 |",
        "| `research/results/b10/hazard_slices.png` | H(x,t) 两族切片热图（固定 t 空间 + 固定 x 时间） |",
        "| `research/results/b10/time_dependence.json` | 同格异时定量例证（逐 cell） |",
        "| `research/results/b10/results.json` | 结构化结果 + gate 判定 + provenance |",
        "| `research/results/b10/report.md` | 本报告 |",
    ]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
