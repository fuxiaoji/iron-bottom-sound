"""v10 figure updates (plan sections 38-41).

Fig1   schematic redrawn with a BENDING line-ahead column: the leader track,
       followers at fixed arc-length offsets, per-vessel local headings, the
       directional fire field and the delayed hazard corridor.
Fig4   commitment certification heatmap rebuilt from the leader-follower
       exact results (the rigid map moved to a comparison panel).
Fig7   formation-representation robustness: (a) rigid vs leader-follower
       positions on the same leader trajectory, (b) chi_F vs |delta J|,
       (c) P6 rigid vs P6 leader-follower with the y = x line.
All figures are written as vector PDF and >=300 dpi PNG.
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

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

from research.geometry.firepower_kernel import KernelFit  # noqa: E402
from research.formation.path_following import (  # noqa: E402
    LeaderPath, line_ahead_offsets, make_lf_game,
)

FIG = REPO / "paper_v10" / "figures"
EXACT = REPO / "research" / "final_v10" / "commitment_lf_exact"
BRIDGE = REPO / "research" / "final_v10" / "bridge"
KD = json.load(open(REPO / "research" / "results" / "e01" / "kernel_fits.json"))["CA"]

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
    "legend.fontsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "figure.dpi": 300, "savefig.dpi": 300, "axes.spines.top": False,
    "axes.spines.right": False, "lines.linewidth": 1.2, "lines.markersize": 5,
})
BLUE, RED, GREY, ORANGE = "#2166ac", "#b2182b", "#777777", "#e08214"
GEOM_TITLE = {"head_on": "head-on", "parallel": "parallel chase", "crossing": "crossing"}


def save(fig, name):
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG / f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"{name}: pdf + png written")


def fire_vec(kw, r, delta, aspect):
    from research.experiments.t1_exact_discrete_certification import fire_vec as fv
    return fv(kw, r, delta, aspect)


def fig1():
    """Schematic with a bending column."""
    g = make_lf_game(KD, "head_on", 1.2, 1.0, 6)
    fit = KernelFit.from_dict(KD)
    from research.geometry.committed_game import KernelWrap
    kw = KernelWrap(fit, 1.0)
    seq = np.array([40.0, 40.0, 0.0, 0.0, 0.0, 0.0])
    p = LeaderPath.from_sequence(g, "B", seq, 6, g.n_sub)
    t = 3
    pos, psi = p.vessel_states(t, g.offsets)
    xs = np.linspace(-25, 45, 170)
    ys = np.linspace(-25, 45, 170)
    XX, YY = np.meshgrid(xs, ys)
    F = np.zeros_like(XX)
    for k in range(g.n_ships):
        dx = XX - pos[k, 0]; dy = YY - pos[k, 1]
        r = np.maximum(np.hypot(dx, dy), 0.5)
        d = np.degrees(np.arctan2(dy, dx)) - psi[k]
        a = np.abs((d + 180.0) % 360.0 - 180.0)
        asp = np.where((a <= 30.0) | (a >= 150.0), "bow_stern", "broadside")
        F += fire_vec(kw, r, d, asp)
    fig, ax = plt.subplots(figsize=(6.6, 4.6))
    Fc = np.ma.masked_less(F, 0.02)
    im = ax.pcolormesh(XX, YY, Fc, cmap="Blues", shading="auto", alpha=0.8,
                       rasterized=True)
    cb = fig.colorbar(im, ax=ax, shrink=0.82, pad=0.01)
    cb.set_label("directional fire field $F_B(x,t)$ (expected hits/pulse)")
    # leader track
    st = p.stations[p.M:]
    ax.plot(st[:, 0], st[:, 1], "-", color="#333333", lw=1.4, zorder=4,
            label="leader track $\\gamma(s)$")
    # vessels with local headings
    for k in range(g.n_ships):
        h = math.radians(psi[k])
        ax.plot([pos[k, 0] - 1.1 * math.cos(h), pos[k, 0] + 1.4 * math.cos(h)],
                [pos[k, 1] - 1.1 * math.sin(h), pos[k, 1] + 1.4 * math.sin(h)],
                color=BLUE, lw=2.4, solid_capstyle="round", zorder=6)
        off = line_ahead_offsets(g.spacing, g.n_ships)[k]
        q = t * g.vB / p.seg - off / p.seg
        pv, _ = p.sample(q)
        ax.plot(pv[0], pv[1], "o", color=ORANGE, ms=3.5, zorder=5)
    ax.annotate("lead vessel", xy=pos[0], xytext=(pos[0, 0] + 3, pos[0, 1] + 7),
                arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=8)
    ax.annotate("trailing vessels follow the same track\nat fixed arc-length "
                "offsets $\\ell_k$:\nthe column BENDS (headings differ)",
                xy=pos[2], xytext=(-24, 34),
                arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=8)
    ax.set_xlim(-24, 44); ax.set_ylim(-22, 44)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    ax.set_title("A line-ahead formation bends along the leader's track;\n"
                 "the payoff integrates exposure over whole trajectories",
                 fontsize=10)
    save(fig, "fig1_schematic")


def fig4():
    """Commitment certification from the leader-follower exact results."""
    def load(model, grid):
        f = EXACT / f"{model}_grid{grid}_results.csv"
        return list(csv.DictReader(open(f))) if f.exists() else []
    lf5, lf7 = load("lf", "5"), load("lf", "7")
    rg5 = {(r["geometry"], float(r["eta_r"]), float(r["eta_v"])): r
           for r in load("rigid", "5")}
    idx7 = {(r["geometry"], float(r["eta_r"]), float(r["eta_v"])): r for r in lf7}
    rows = [r for r in lf5 if float(r["eta_r"]) != 1.0]
    eta_vs = sorted({float(r["eta_v"]) for r in rows})
    eta_rs = sorted({float(r["eta_r"]) for r in rows})
    fig, axes = plt.subplots(1, 3, figsize=(10.4, 3.4), sharey=True)
    for ax, g in zip(axes, ("head_on", "parallel", "crossing")):
        for r in rows:
            if r["geometry"] != g:
                continue
            ev, er = float(r["eta_v"]), float(r["eta_r"])
            sign = int(r["certified_sign"]); mid = float(r["point_estimate"])
            face = ("#dbe7f3" if mid > 0 else "#f6dede") if abs(mid) > 0.05 else "#f2f2f2"
            ax.add_patch(Rectangle((ev - 0.11, er - 0.07), 0.22, 0.14,
                                   facecolor=face, edgecolor="none"))
            ec, lw = (BLUE, 2.2) if sign > 0 else ((RED, 2.2) if sign < 0 else (GREY, 1.2))
            ax.add_patch(Rectangle((ev - 0.11, er - 0.07), 0.22, 0.14,
                                   facecolor="none", edgecolor=ec, lw=lw,
                                   hatch=None if sign != 0 else "///"))
            ax.text(ev, er, f"{mid:+.1f}", ha="center", va="center", fontsize=7)
            r7 = idx7.get((g, er, ev))
            if r7 is not None and int(r7["certified_sign"]) != sign and sign != 0:
                ax.plot(ev, er, "x", color="k", ms=7, mew=1.6)
            elif r7 is None:
                ax.plot(ev + 0.075, er - 0.052, "o", mfc="none", mec=GREY,
                        ms=4, mew=0.9)
            rr = rg5.get((g, er, ev))
            if rr is not None and int(rr["certified_sign"]) != sign:
                ax.plot(ev - 0.075, er + 0.052, "+", color="k", ms=7, mew=1.4)
        ax.set_xticks(eta_vs); ax.set_yticks(eta_rs)
        ax.set_xlabel(r"speed ratio $\eta_v$"); ax.set_title(GEOM_TITLE[g])
        ax.set_xlim(min(eta_vs) - 0.22, max(eta_vs) + 0.22)
        ax.set_ylim(min(eta_rs) - 0.14, max(eta_rs) + 0.14)
    axes[0].set_ylabel(r"range ratio $\eta_r$")
    import matplotlib.patches as mpatches
    handles = [mpatches.Patch(fc="none", ec=BLUE, lw=2.2,
                              label="certified $P_6>0$ (leader--follower)"),
               mpatches.Patch(fc="none", ec=RED, lw=2.2, label="certified $P_6<0$"),
               mpatches.Patch(fc="none", ec=GREY, hatch="///", label="uncertified"),
               plt.Line2D([], [], ls="none", marker="x", color="k",
                          label="grid-5/7 sign differs"),
               plt.Line2D([], [], ls="none", marker="+", color="k",
                          label="rigid vs leader--follower differs")]
    axes[-1].legend(handles=handles, loc="center left", bbox_to_anchor=(1.02, 0.5),
                    fontsize=7.2, frameon=False)
    fig.suptitle("Exact finite-game certification of the value of a six-turn "
                 "commitment (leader--follower instantiation; numbers: interval "
                 "midpoints)", fontsize=9.5)
    fig.tight_layout(rect=(0, 0, 0.845, 0.9))
    save(fig, "fig4_commitment_certification")


def fig7():
    """Formation-representation robustness (geometry and curvature scaling).

    v11: the former commitment panel was removed together with that claim; the
    figure now documents only the geometric divergence between the rigid
    baseline and the leader-follower model.
    """
    rows = list(csv.DictReader(open(BRIDGE / "bridge_cells.csv")))
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.4))
    from research.formation.path_following import vessel_states_rigid_line_ahead
    ax = axes[0]
    g = make_lf_game(KD, "crossing", 1.2, 1.0, 6)
    seq = np.array([45.0, 45.0, 0.0, 0.0, 0.0, 0.0])
    p = LeaderPath.from_sequence(g, "B", seq, 6, g.n_sub)
    st = p.stations[p.M:]
    ax.plot(st[:, 0], st[:, 1], "-", color="#333333", lw=1.2, label="leader track")
    t3 = 3
    posLF, _ = p.vessel_states(t3, g.offsets)
    posRG, _ = vessel_states_rigid_line_ahead(g, seq, "B", t3)
    for k in range(g.n_ships):
        ax.plot([posLF[k, 0], posRG[k, 0]], [posLF[k, 1], posRG[k, 1]], ":",
                color=GREY, lw=0.8)
    ax.plot(posLF[:, 0], posLF[:, 1], "o-", color=BLUE, ms=5, label="leader--follower")
    ax.plot(posRG[:, 0], posRG[:, 1], "s--", color=ORANGE, ms=5, label="rigid baseline")
    ax.set_aspect("equal"); ax.set_xlabel("$x$ (hex)"); ax.set_ylabel("$y$ (hex)")
    ax.set_title("(a) same leader track, different column shape")
    ax.legend(loc="upper left", fontsize=7)
    ax = axes[1]
    chi = [float(r["kappa_L_F"]) for r in rows]
    shape = [float(r["max_shape_error"]) for r in rows]
    field = [100.0 * float(r["field_deviation"]) for r in rows]
    ax.plot(chi, shape, "o", color=BLUE, ms=7, mec="k", mew=0.5,
            label="vessel-position error (hex)")
    ax.plot(chi, [f / 2.0 for f in field], "^", color=ORANGE, ms=7, mec="k",
            mew=0.5, label="field deviation (%, rescaled)")
    ax.set_xlabel(r"$\chi_F$ (curvature $\times$ formation length)")
    ax.set_ylabel("measured divergence")
    ax.set_title("(b) curvature scale versus measured divergence")
    ax.legend(loc="center right", fontsize=7, framealpha=0.95)
    ax.set_ylim(0, 11)
    ax.annotate(f"$\chi_F$ range {min(chi):.2f}--{max(chi):.2f};\n"
                "divergence does not follow\na monotone trend in these cells",
                xy=(0.03, 0.97), xycoords="axes fraction", fontsize=7, va="top",
                bbox=dict(boxstyle="round", fc="white", ec="none", alpha=0.9))
    fig.suptitle("Formation-representation robustness: the rigid baseline versus "
                 "path following", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    save(fig, "fig7_formation_robustness")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("figs", nargs="*", default=["1", "4", "7"])
    a = ap.parse_args()
    table = {"1": fig1, "4": fig4, "7": fig7}
    for f in a.figs:
        table[f]()
