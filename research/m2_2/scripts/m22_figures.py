"""M2.2 figures — from the frozen metrics JSONs only (no re-measurement).

    PYTHONPATH=backend/src:research/m2_2/scripts:research/m2_1/scripts \
        .venv/bin/python research/m2_2/scripts/m22_figures.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
M = ROOT / "metrics"
F = ROOT / "figures"
F.mkdir(exist_ok=True)

plt.rcParams.update({"figure.dpi": 140, "font.size": 9, "axes.grid": True,
                     "grid.alpha": 0.25, "axes.axisbelow": True})
B0 = json.loads((M / "b0_gold_compiler_fidelity.json").read_text())


def bar_labels(ax, bars, fmt="{:.2f}"):
    for b in bars:
        h = b.get_height()
        ax.annotate(fmt.format(h), (b.get_x() + b.get_width() / 2, h),
                    ha="center", va="bottom" if h >= 0 else "top", fontsize=7)


# ---------------------------------------------------------------- fig 01
def fig01():
    mechs = ["MG1", "MG3", "MG4"]
    methods = ["CURRENT_POLICY", "CURRENT_INTENT_COMPILER", "BEAM_SEARCH_COMPILER"]
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.6), sharey=True)
    for ax, m in zip(axes, mechs):
        r = B0[m]
        pan = r.get("primary", {})
        fid = pan.get("fidelity", {})
        vals = []
        for k in methods:
            v = fid.get(k)
            if v is None and k == "BEAM_SEARCH_COMPILER":
                v = fid.get("PUBLIC_CORRIDOR_SEARCH")
            vals.append(v)
        status = pan.get("status")
        if status != "COMPUTABLE":
            ax.text(0.5, 0.5, f"excluded:\n{status}\n(gold gap = "
                              f"{pan.get('gold_gap'):+.3f})",
                    transform=ax.transAxes, ha="center", va="center", fontsize=9,
                    bbox=dict(boxstyle="round", fc="#fff2cc", ec="#bf9000"))
            ax.set_xticks([])
        else:
            bars = ax.bar(range(3), vals,
                          color=["#c00000", "#ed7d31", "#2e75b6"])
            bar_labels(ax, bars)
            ax.axhline(0.70, ls="--", c="#2e75b6", lw=1)
            ax.axhline(0.40, ls=":", c="#c00000", lw=1)
            ax.set_xticks(range(3))
            ax.set_xticklabels(["CURRENT\nPOLICY", "INTENT\nCOMPILER",
                                "SEARCH"], fontsize=8)
        label = r.get("primary_metric") or (
            "route reduction" if m == "MG4" else "")
        ax.set_title(f"{m} — {label[:34]}", fontsize=8)
        ax.set_ylim(-1.6, 1.6)
    axes[0].set_ylabel("fidelity  F = (M − M_random)/(M_gold − M_random)")
    fig.suptitle("B0 gold-compiler fidelity, primary (frozen) metric — "
                 "dashes: SEARCH ≥ 0.70, dotted: CURRENT ≤ 0.40", fontsize=9)
    fig.tight_layout()
    fig.savefig(F / "fig01_b0_fidelity_primary.png", bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- fig 02
def fig02():
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    r1 = B0["MG1"]
    for ax, pan, title in ((axes[0], r1["primary"], "MG1 fleet EH margin"),
                           (axes[1], r1["supplementary"], "MG1 pair margin (focal↔target)")):
        mv = pan["mechanism_value"]
        keys = ["MANUAL_GOLD", "REGISTERED_COUNTER_ARM", "RANDOM_LEGAL_MEAN",
                "CURRENT_POLICY", "CURRENT_INTENT_COMPILER", "BEAM_SEARCH_COMPILER"]
        vals = [mv.get(k) or 0 for k in keys]
        cols = ["#548235", "#a9d18e", "#bfbfbf", "#c00000", "#ed7d31", "#2e75b6"]
        bars = ax.bar(range(len(keys)), vals, color=cols)
        bar_labels(ax, bars)
        ax.set_xticks(range(len(keys)))
        ax.set_xticklabels(["GOLD", "COUNTER", "RANDOM\nmean", "CURRENT", "INTENT",
                            "SEARCH"], fontsize=7)
        ax.axhline(0, c="k", lw=0.8)
        ax.set_title(f"{title}\nstatus={pan['status']}, gap={pan['gold_gap']:+.3f}",
                     fontsize=8)
    ax = axes[2]
    mv = B0["MG4"]["primary"]["mechanism_value"]
    keys = ["MANUAL_GOLD", "RANDOM_LEGAL_MEAN", "CURRENT_POLICY",
            "CURRENT_INTENT_COMPILER", "PUBLIC_CORRIDOR_SEARCH",
            "FULL_STATE_CORRIDOR_CEILING"]
    vals = [mv.get(k) or 0 for k in keys]
    bars = ax.bar(range(len(keys)), vals,
                  color=["#548235", "#bfbfbf", "#c00000", "#ed7d31", "#2e75b6", "#1f3864"])
    bar_labels(ax, bars, "{:.2f}")
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels(["GOLD", "RANDOM\nmean", "CURRENT", "INTENT", "PUBLIC\nSEARCH",
                        "FULL-STATE\nCEILING"], fontsize=7)
    ax.set_title("MG4 route reduction\nstatus=COMPUTABLE, gap=+0.966", fontsize=8)
    fig.suptitle("Mechanism values by method (M2.2 naming discipline: SEARCH, never optimal)",
                 fontsize=9)
    fig.tight_layout()
    fig.savefig(F / "fig02_mechanism_values.png", bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- fig 03
def fig03():
    """MG4 public-signal diagnostic, both facets, recomputed from the frozen case
    with the engine's own projection.

    Panel A (CORRIDOR_BLOB): the objective's argmax contains NO informative
    configuration.  Panel B (LEAD_TURN_ALLOWED): the argmax set contains the best
    configuration and 64 uninformative ones — the public signal identifies a set
    but cannot rank inside it.  Both statements are reported; neither alone is
    the finding.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from m22_b0 import public_corridor  # noqa: E402
    from mg.mg4r import launch_and_advance, route_trajectory, victim_routes  # noqa: E402
    from mg.mg4r_corridor import enumerate_configs, t1_segment  # noqa: E402
    from mg.micro import reach  # noqa: E402
    from iron_bottom_sound.models import Phase, Side  # noqa: E402

    base = launch_and_advance("IBS-S-01", 1)
    victim, shooter = base["victim"], base["shooter"]
    routes = victim_routes(base["eng"], base["state"], victim)
    trajs = {e["plan"]: set(route_trajectory(base["eng"], base["state"], victim, e["plan"]))
             for e in routes}
    engT, stT, _ = reach("IBS-S-01", 1, Phase.TORPEDO_PLANNING, 2)
    cfgs = [c for c in enumerate_configs(engT, stT, Side.ALLIES, stT.ships[shooter])]
    for c in cfgs:
        c["seg"] = set(t1_segment(c))
    cfgs = [c for c in cfgs if c["seg"]]
    for c in cfgs:
        c["rr"] = 1 - sum(1 for t in trajs.values() if not (t & c["seg"])) / len(trajs)

    vic = stT.ships[victim]
    sp = max(1, min(int(vic.current_speed or 2), 6))
    lead = set()
    for t in (-1, 0, 1):
        h0 = ((vic.heading - 1 + t) % 6) + 1
        for a0 in range(0, sp + 1):
            end, good = vic.position, True
            for _ in range(a0):
                n = end.neighbor(h0, columns=stT.map_columns, rows=stT.map_rows)
                if n is None:
                    good = False
                    break
                end = n
            if not good:
                break
            p = end
            for mf in range(1, sp + 1):
                n = p.neighbor(h0, columns=stT.map_columns, rows=stT.map_rows)
                if n is None:
                    break
                p = n
                lead.add((mf, p.label))
    blob = public_corridor(stT, victim)
    best = max(cfgs, key=lambda c: c["rr"])

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.2), sharey=True)
    diag = {"n_configs": len(cfgs), "n_routes": len(routes),
            "full_state_best": {"overlap_blob": len(best["seg"] & blob),
                               "overlap_lead": len(best["seg"] & lead),
                               "rr": best["rr"]},
            "objectives": {}}
    for ax, (name, cells, claim) in zip(axes, (
            ("CORRIDOR_BLOB", blob,
             "argmax contains NO informative config"),
            ("LEAD_TURN_ALLOWED", lead,
             "argmax contains the best AND 64 uninformative ones"))):
        for c in cfgs:
            c["_ov"] = len(c["seg"] & cells)
        ov = [c["_ov"] for c in cfgs]
        rr = [c["rr"] for c in cfgs]
        mx = max(ov)
        tied = [c for c in cfgs if c["_ov"] == mx]
        ax.scatter(ov, rr, s=16, c="#8ea9db", edgecolors="none", label="288 legal configs")
        ax.scatter([c["_ov"] for c in tied], [c["rr"] for c in tied], s=54,
                   facecolors="none", edgecolors="#c00000", linewidths=1.2,
                   label=f"public argmax ties (n={len(tied)})")
        ax.scatter([len(best["seg"] & cells)], [best["rr"]], marker="*", s=200,
                   c="#548235", label=f"full-state best (RR {best['rr']:.2f})")
        ax.set_xlabel(f"public objective score — {name}\n(overlap with forecast corridor, "
                      f"{len(cells)} cells)")
        ax.set_title(f"{name}: {claim}", fontsize=9)
        ax.legend(fontsize=7, loc="center right")
        ax.set_ylim(-0.06, 1.06)
        ax.set_xlim(-0.35, mx + 0.5)
        ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
        diag["objectives"][name] = {
            "objective_cells": len(cells), "max_overlap": mx, "n_ties": len(tied),
            "tie_rr_min": min(c["rr"] for c in tied),
            "tie_rr_max": max(c["rr"] for c in tied),
            "n_ties_informative_ge_050": sum(1 for c in tied if c["rr"] >= 0.50),
            "n_configs_overlap_positive": sum(1 for c in cfgs if c["_ov"] > 0)}
    axes[0].set_ylabel("true route reduction")
    fig.suptitle("MG4 public-information gap: the observation-only objective cannot rank "
                 "configurations", fontsize=10)
    fig.tight_layout()
    fig.savefig(F / "fig03_mg4_public_signal.png", bbox_inches="tight")
    plt.close(fig)
    diag["per_config"] = [{"overlap_blob": len(c["seg"] & blob),
                           "overlap_lead": len(c["seg"] & lead), "rr": c["rr"],
                           "setting_index": c["setting_index"],
                           "launch_angle": c["launch_angle"]} for c in cfgs]
    (M / "mg4_public_signal_diagnostic.json").write_text(json.dumps(diag, indent=1))


# ---------------------------------------------------------------- fig 04
def fig04():
    r = B0["MG3"]
    rep = r["verification"]["arms"]
    fig, ax = plt.subplots(figsize=(5.6, 3.6))
    arms = ["CLOSE", "OPEN"]
    d = [rep[a]["distance"] for a in arms]
    eh = [rep[a]["expected_hits"] for a in arms]
    bars = ax.bar(arms, eh, color=["#2e75b6", "#8ea9db"], width=0.5)
    for b, dist, e in zip(bars, d, eh):
        ax.annotate(f"{e:.2f} EH\n@ {dist} hex", (b.get_x() + b.get_width() / 2, e),
                    ha="center", va="bottom", fontsize=8)
    vis = 13
    ax.axhline(0, c="k", lw=0.8)
    ax.set_ylim(0, 3.2)
    ax.set_ylabel("registered MG3 metric: BB expected hits")
    ax.set_title("MG3 registered arms vs the visibility horizon\n"
                 f"both arms ({d[0]}/{d[1]} hex) lie beyond allied visibility "
                 f"({vis} hex), radar rule OFF → can_see = False", fontsize=8)
    ax.annotate("engageable envelope (≤ 13 hex)", xy=(0.02, 0.06),
                xycoords="axes fraction", fontsize=8, color="#548235")
    fig.tight_layout()
    fig.savefig(F / "fig04_mg3_visibility_horizon.png", bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- fig 05
def fig05():
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    mechs = ["MG1 (pair)", "MG1 (fleet)", "MG3 (fleet)", "MG4 (RR)"]
    cur = [B0["MG1"]["supplementary"]["mechanism_value"]["CURRENT_POLICY"],
           B0["MG1"]["primary"]["mechanism_value"]["CURRENT_POLICY"],
           B0["MG3"]["primary"]["mechanism_value"]["CURRENT_POLICY"],
           B0["MG4"]["primary"]["mechanism_value"]["CURRENT_POLICY"]]
    sch = [B0["MG1"]["supplementary"]["mechanism_value"]["BEAM_SEARCH_COMPILER"],
           B0["MG1"]["primary"]["mechanism_value"]["BEAM_SEARCH_COMPILER"],
           B0["MG3"]["primary"]["mechanism_value"]["BEAM_SEARCH_COMPILER"],
           B0["MG4"]["primary"]["mechanism_value"]["FULL_STATE_CORRIDOR_CEILING"]]
    x = range(len(mechs))
    b1 = ax.bar([i - 0.19 for i in x], cur, width=0.36, color="#c00000",
                label="CURRENT_POLICY")
    b2 = ax.bar([i + 0.19 for i in x], sch, width=0.36, color="#2e75b6",
                label="SEARCH (fleet: BEAM; MG4: full-state ceiling*)")
    bar_labels(ax, b1)
    bar_labels(ax, b2)
    ax.axhline(0, c="k", lw=0.8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(mechs, fontsize=8)
    ax.set_ylabel("mechanism value (mixed units, panel-local)")
    ax.set_title("CURRENT_POLICY vs SEARCH per case\n"
                 "* MG4's ceiling is not deployable; its public search scores 0.10",
                 fontsize=8)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(F / "fig05_current_vs_search.png", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    fig01(); fig02(); fig03(); fig04(); fig05()
    print("figures written:")
    for p in sorted(F.glob("*.png")):
        print(" ", p.name, p.stat().st_size, "bytes")
