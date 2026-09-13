"""v9 figure rebuild (v9 sections 31-37).

Fig3  degeneracy boundary: axis narrative corrected (x = speed asymmetry,
      y = range/interaction-envelope asymmetry) and the claim narrowed to
      "in the tested perturbations ...".
Fig4  commitment certification rebuilt ENTIRELY from the v9 exact
      discretized finite-game results, with an explicit certification
      encoding separate from the magnitude colour:
        solid blue border  = exact sign-certified positive
        solid red border   = exact sign-certified negative
        grey hatch         = interval crosses zero (uncertified)
        black X            = Grid-5 / Grid-7 sign disagreement
        small open circle  = Grid-7 not run
Fig5  delayed threat: thickness sweep labelled as unmatched-lethality, with
      the matched-lethality counterexample (21/28) added as a panel.
Fig6  engine transfer: two panels (full range / near-zero zoom) so a single
      outlier no longer stretches the axis; zero reference lines kept.

Every figure is written as vector PDF + >=300 dpi PNG.
Style: colourblind-safe, uniform fonts/linewidths, certification never
encoded by colour alone.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

FIG = REPO / "paper_v8" / "figures"
EXACT = REPO / "research" / "final_v9" / "commitment_exact"

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
    "legend.fontsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "figure.dpi": 300, "savefig.dpi": 300, "axes.spines.top": False,
    "axes.spines.right": False, "lines.linewidth": 1.2, "lines.markersize": 5,
})
BLUE, RED, GREY = "#2166ac", "#b2182b", "#777777"
GEOM_TITLE = {"head_on": "head-on", "parallel": "parallel chase", "crossing": "crossing"}


def save(fig, name: str) -> None:
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG / f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"{name}: pdf + png(300dpi) written")


def load_exact() -> tuple[list[dict], list[dict]]:
    rows = []
    for g in ("5", "7"):
        f = EXACT / f"exact_grid{g}_results.csv"
        if f.exists():
            rows += list(csv.DictReader(open(f)))
    return [r for r in rows if r["grid"] == "5"], [r for r in rows if r["grid"] == "7"]


def fig3() -> None:
    d = json.load(open(REPO / "research" / "final_v8" / "figures" / "fig3_grid.json"))
    ev, er = np.array(d["eta_v"]), np.array(d["eta_r"])
    Z = np.array(d["V_minus_L"])
    fig, ax = plt.subplots(figsize=(4.8, 3.7))
    vmax = float(np.nanmax(np.abs(Z)))
    im = ax.pcolormesh(ev, er, Z.T, cmap="RdBu_r", vmin=-vmax, vmax=vmax,
                       shading="nearest")
    cb = fig.colorbar(im, ax=ax)
    cb.set_label(r"$\max_s |V(s)-L(s)|$")
    ax.axvline(1.0, color="k", lw=0.8, ls=":")
    ax.axhline(1.0, color="k", lw=0.8, ls=":")
    ax.set_xlabel(r"speed ratio $\eta_v$")
    ax.set_ylabel(r"range ratio $\eta_r$")
    ax.set_title("Where the degeneracy breaks", fontsize=9)
    fig.tight_layout()
    save(fig, "fig3_degeneracy_boundary")


def fig4() -> None:
    g5, g7 = load_exact()
    if not g5:
        print("fig4: exact Grid-5 results missing -- skipping")
        return
    idx5 = {(r["geometry"], float(r["eta_r"]), float(r["eta_v"])): r for r in g5}
    idx7 = {(r["geometry"], float(r["eta_r"]), float(r["eta_v"])): r for r in g7}
    eta_vs = sorted({float(r["eta_v"]) for r in g5})
    eta_rs = sorted({float(r["eta_r"]) for r in g5 if float(r["eta_r"]) != 1.0})
    fig, axes = plt.subplots(1, 3, figsize=(10.2, 3.4), sharey=True)
    for ax, g in zip(axes, ("head_on", "parallel", "crossing")):
        for er in eta_rs:
            for ev in eta_vs:
                r5 = idx5.get((g, er, ev))
                if r5 is None:
                    continue
                s5 = int(r5["certified_sign"])
                mid = float(r5["point_estimate"])
                face = ("#dbe7f3" if mid > 0 else "#f6dede") if abs(mid) > 0.05 else "#f2f2f2"
                ax.add_patch(Rectangle((ev - 0.11, er - 0.07), 0.22, 0.14,
                                       facecolor=face, edgecolor="none"))
                if s5 > 0:
                    ax.add_patch(Rectangle((ev - 0.11, er - 0.07), 0.22, 0.14,
                                           facecolor="none", edgecolor=BLUE, lw=2.2))
                elif s5 < 0:
                    ax.add_patch(Rectangle((ev - 0.11, er - 0.07), 0.22, 0.14,
                                           facecolor="none", edgecolor=RED, lw=2.2))
                else:
                    ax.add_patch(Rectangle((ev - 0.11, er - 0.07), 0.22, 0.14,
                                           facecolor="none", edgecolor=GREY,
                                           hatch="///", lw=1.2))
                ax.text(ev, er, f"{mid:+.1f}", ha="center", va="center", fontsize=7)
                r7 = idx7.get((g, er, ev))
                if r7 is not None and int(r7["certified_sign"]) != s5 and s5 != 0:
                    ax.plot(ev, er, "x", color="k", ms=7, mew=1.6)
                elif r7 is None:
                    ax.plot(ev + 0.075, er - 0.052, "o", mfc="none", mec=GREY,
                            ms=4, mew=0.9)
        ax.set_xticks(eta_vs); ax.set_yticks(eta_rs)
        ax.set_xlabel(r"speed ratio $\eta_v$")
        ax.set_title(GEOM_TITLE[g])
        ax.set_xlim(min(eta_vs) - 0.22, max(eta_vs) + 0.22)
        ax.set_ylim(min(eta_rs) - 0.14, max(eta_rs) + 0.14)
    axes[0].set_ylabel(r"range ratio $\eta_r$")
    import matplotlib.patches as mpatches
    handles = [
        mpatches.Patch(fc="none", ec=BLUE, lw=2.2, label="certified $P_6>0$ (exact)"),
        mpatches.Patch(fc="none", ec=RED, lw=2.2, label="certified $P_6<0$ (exact)"),
        mpatches.Patch(fc="none", ec=GREY, hatch="///", label="interval crosses 0"),
        plt.Line2D([], [], ls="none", marker="x", color="k", label="grid-5/7 sign differs"),
        plt.Line2D([], [], ls="none", marker="o", mfc="none", mec=GREY,
                   label="grid-7 not run"),
    ]
    axes[-1].legend(handles=handles, loc="center left", bbox_to_anchor=(1.02, 0.5),
                    fontsize=7.5, frameon=False)
    fig.suptitle("Exact finite-game certification of the value of a 6-turn commitment "
                 "(numbers: interval midpoint)", fontsize=10)
    fig.tight_layout(rect=(0, 0, 0.845, 0.92))
    save(fig, "fig4_commitment_certification")


def fig5() -> None:
    stats = list(csv.DictReader(open(REPO / "research" / "results" / "b10"
                                     / "field_stats.csv")))
    td = json.load(open(REPO / "research" / "results" / "b10"
                        / "time_dependence.json"))
    contr = list(csv.DictReader(open(REPO / "research" / "results" / "b11"
                                     / "contraction.csv")))
    ks = sorted({int(float(r["k"])) for r in contr})
    mean = {k: float(np.mean([float(r["c_resp"]) for r in contr
                              if int(float(r["k"])) == k])) for k in ks}
    q1 = {k: float(np.percentile([float(r["c_resp"]) for r in contr
                                  if int(float(r["k"])) == k], 25)) for k in ks}
    q3 = {k: float(np.percentile([float(r["c_resp"]) for r in contr
                                  if int(float(r["k"])) == k], 75)) for k in ks}
    # matched-lethality counterexample (b12 acceptance block)
    b12 = json.load(open(REPO / "research" / "results" / "b12" / "results.json"))
    acc = b12["acceptance"]
    n_pairs = int(acc["n_matched_pairs"])
    thin_wins = int(acc["paired_comparisons_thin_wins_5pct"])
    disp_wins = n_pairs - thin_wins
    fig, axes = plt.subplots(1, 4, figsize=(12.2, 2.9))
    frac = sorted(float(r["future_turn_threat_mass_fraction"]) for r in stats)
    axes[0].bar(range(len(frac)), [100 * f for f in frac], color=RED, alpha=0.75)
    axes[0].set_xlabel("tested engagement cells")
    axes[0].set_ylabel("% threat mass in later turns")
    axes[0].set_title("(a) Threat mass lies in the future")
    axes[0].set_ylim(0, 50)
    axes[0].annotate(f"{100*min(frac):.0f}--{100*max(frac):.0f}% of the\n"
                     "field's mass acts after\nthe launch turn",
                     xy=(0.03, 0.97), xycoords="axes fraction", fontsize=7.5,
                     va="top", bbox=dict(boxstyle="round", fc="white", ec="none",
                                         alpha=0.9))
    cell = td["cells"]["chase:1v1"]["time_dependence"]
    dist = cell["hot_pulse_count_distribution"]
    xs = [int(k) for k in dist]
    axes[1].bar(xs, [dist[str(x)] for x in xs], color=GREY)
    axes[1].set_xlabel("impulses with the hex hot")
    axes[1].set_ylabel("hot hexes")
    axes[1].set_title("(b) Same hex, different impulses")
    axes[1].annotate(f"single-pulse hot share "
                     f"{100*cell['single_pulse_hot_share']:.0f}%",
                     xy=(0.3, 0.78), xycoords="axes fraction", fontsize=7.5)
    axes[2].errorbar(ks, [mean[k] for k in ks],
                     yerr=[[abs(mean[k] - q1[k]) for k in ks],
                           [abs(q3[k] - mean[k]) for k in ks]],
                     fmt="o-", color=BLUE, capsize=3)
    axes[2].set_xlabel("torpedo salvo thickness $k$")
    axes[2].set_ylabel(r"contraction $C_{\rm resp}$")
    axes[2].set_title("(c) Unmatched-lethality sweep")
    axes[2].set_ylim(-0.02, 0.45)
    axes[3].bar([0, 1], [thin_wins / n_pairs, disp_wins / n_pairs],
                color=[RED, GREY], hatch=["", "//"])
    axes[3].set_xticks([0, 1])
    axes[3].set_xticklabels(["concentrated\nthreat wins", "dispersed\nwins"])
    axes[3].set_ylabel("share of matched pairs")
    axes[3].set_ylim(0, 1)
    axes[3].set_title("(d) Matched lethality")
    axes[3].annotate(f"{thin_wins}/{n_pairs} matched pairs:\n"
                     "concentrated contracts more",
                     xy=(0.03, 0.75), xycoords="axes fraction", fontsize=7.5)
    fig.tight_layout()
    save(fig, "fig5_delayed_threat")


def fig6() -> None:
    res = json.load(open(REPO / "research" / "results" / "final_v7"
                         / "must2_results.json"))
    cells = res["per_cell"]
    marks = {"head_on": "o", "parallel": "s", "crossing": "^"}
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.8),
                             gridspec_kw={"width_ratios": [1, 1]})
    for ax, (xlim, ylim, title) in zip(axes, [
            (None, None, "(a) full range"),
            ((-3, 3), (-8, 8), "(b) near-zero region")]):
        for c in cells:
            x, y = c["V_surrogate"], c["F-F"]["axis_adv"]
            err = (c["F-F"]["ci"][1] - c["F-F"]["ci"][0]) / 2
            ax.errorbar(x, y, yerr=err, fmt=marks[c["geometry"]],
                        color=BLUE if c["speed"] == 4 else RED,
                        ms=6, capsize=2.5, markeredgecolor="k", markeredgewidth=0.5)
        ax.axhline(0, color="k", lw=0.8); ax.axvline(0, color="k", lw=0.8)
        if xlim:
            ax.set_xlim(*xlim)
        if ylim:
            ax.set_ylim(*ylim)
        ax.set_xlabel(r"model: formation surrogate value $\Delta J_{\rm model}$")
        ax.set_title(title)
    axes[0].set_ylabel(r"engine: axis advantage $\Delta J_{\rm engine}$")
    g = res["gates"]
    axes[0].annotate(f"sign agreement {g['sign_agreement']:.0%} (gate $\\geq$80%)\n"
                     f"Spearman $\\rho$={g['spearman_rho']:.2f} (gate $\\geq$0.60)\n"
                     f"pairwise ordering {g['pairwise_ordering']:.0%} (gate $\\geq$75%)\n"
                     f"verdict: {res['verdict']}",
                     xy=(0.02, 0.02), xycoords="axes fraction", fontsize=7.5,
                     bbox=dict(boxstyle="round", fc="white", ec=GREY, alpha=0.9))
    for geom, mk in marks.items():
        axes[1].scatter([], [], marker=mk, color="k", label=geom.replace("_", "-"))
    axes[1].scatter([], [], marker="s", color=BLUE, label=r"$v_0=4$")
    axes[1].scatter([], [], marker="s", color=RED, label=r"$v_0=6$")
    axes[1].legend(fontsize=7, loc="upper right", frameon=False)
    fig.suptitle("Transfer of reduced-model comparative statics to the rules engine",
                 fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    save(fig, "fig6_engine_transfer")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("figs", nargs="*", default=["3", "4", "5", "6"])
    a = ap.parse_args()
    table = {"3": fig3, "4": fig4, "5": fig5, "6": fig6}
    for f in a.figs:
        table[f]()
