"""T5 (v8): main-figure rebuild.  One figure, one scientific question.

Fig 1  Formation-level problem schematic (schematic + calibrated kernel field).
Fig 2  Peak position vs integrated trajectory (real B2 rollouts).
Fig 3  Closed-loop degeneracy boundary heatmap (DP grid; needs fig3 data run).
Fig 4  Commitment comparative statics + sign certification (needs T1 results).
Fig 5  Delayed torpedo spacetime hazard + response-set contraction (real data).
Fig 6  Transfer of reduced-model comparative statics to the rules engine.

Style: colorblind-safe diverging/sequential maps, grayscale-printable,
uniform fonts, English labels.  Internal experiment codes never appear in
figure titles.  Output: paper_v8/figures/figN_*.png (200 dpi).
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
from matplotlib.patches import FancyArrow, RegularPolygon, Rectangle

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

from research.geometry.firepower_kernel import KernelFit  # noqa: E402

FIG = REPO / "paper_v8" / "figures"
FIG.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
    "legend.fontsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "figure.dpi": 200, "savefig.dpi": 200, "axes.spines.top": False,
    "axes.spines.right": False,
})
BLUE, RED, GREY = "#2c6fbb", "#c0392b", "#666666"


def kernel_field(fit: KernelFit, heading_deg: float, origin=(0.0, 0.0),
                 r_max=24.0, n=240, eta_r=1.0):
    """Directional fire field of a 3-vessel line-ahead formation (screen space)."""
    xs = np.linspace(-r_max, r_max, n)
    ys = np.linspace(-r_max, r_max, n)
    XX, YY = np.meshgrid(xs, ys)
    F = np.zeros_like(XX)
    h = math.radians(heading_deg)
    for k in range(3):
        sx = origin[0] - 2.0 * k * math.cos(h)   # vessels astern of the lead
        sy = origin[1] - 2.0 * k * math.sin(h)
        dx, dy = XX - sx, YY - sy
        r = np.hypot(dx, dy)
        delta = np.degrees(np.arctan2(dy, dx)) - heading_deg
        # broadside/bow-stern aspect of the hypothetical target at (x,y):
        d_back = delta + 180.0
        a_back = np.abs((d_back + 180.0) % 360.0 - 180.0)
        aspect = np.where((a_back <= 30.0) | (a_back >= 150.0),
                          "bow_stern", "broadside")
        r_eff = np.clip(r / eta_r, 1.0, 24.0)
        acc = np.zeros_like(r)
        for asp in ("bow_stern", "broadside"):
            m = aspect == asp
            if m.any():
                acc[m] += _interp_subset(r_eff[m], delta[m], fit, asp)
        F += acc
    return XX, YY, F


def _interp_subset(r, delta, fit, asp):
    out = np.empty_like(r)
    for i, (re, de) in enumerate(zip(r, delta)):
        out[i] = fit.expected_hits(re, de, 6, asp)
    return out


def ship_glyph(ax, x, y, heading_deg, color, s=14):
    h = math.radians(heading_deg)
    ax.plot([x - 0.9 * math.cos(h), x + 0.9 * math.cos(h)],
            [y - 0.9 * math.sin(h), y + 0.9 * math.sin(h)],
            color=color, lw=2.2, solid_capstyle="round", zorder=6)


def fig1():
    fits = json.load(open(REPO / "research" / "results" / "e01" / "kernel_fits.json"))
    fit = KernelFit.from_dict(fits["CA"])
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    # field of the BLUE formation heading 30 deg
    XX, YY, F = kernel_field(fit, 30.0)
    Fc = np.ma.masked_less(F, 0.02)
    im = ax.pcolormesh(XX, YY, Fc, cmap="Blues", shading="auto", alpha=0.85,
                       rasterized=True)
    cb = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.01)
    cb.set_label(r"directional fire field $F_B(x,t)$  (expected hits / pulse)")
    # formations
    hb = 30.0
    hr = 210.0
    xr, yr = 16.0 * math.cos(math.radians(30)), 16.0 * math.sin(math.radians(30))
    for k in range(3):
        ship_glyph(ax, -2.0 * k * math.cos(math.radians(hb)),
                   -2.0 * k * math.sin(math.radians(hb)), hb, BLUE)
        ship_glyph(ax, xr - 2.0 * k * math.cos(math.radians(hr)),
                   yr - 2.0 * k * math.sin(math.radians(hr)), hr, RED)
    ax.annotate("formation centre $c_B$, heading $\\psi_B$",
                xy=(0, 0), xytext=(-22, 6),
                arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=8)
    ax.annotate("red line-ahead formation",
                xy=(xr, yr), xytext=(4, 20),
                arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=8)
    # candidate trajectories (open-loop plans)
    t = np.linspace(0, 1, 60)
    for turn, ls in ((+90, "--"), (0, "-"), (-60, ":")):
        xs, ys = [0.0], [0.0]
        hdeg = hb
        for _ in range(8):
            hdeg += turn / 3.0 / 8 * 3
            xs.append(xs[-1] + 4.8 * math.cos(math.radians(hdeg)) / 8 * 3)
            ys.append(ys[-1] + 4.8 * math.sin(math.radians(hdeg)) / 8 * 3)
        xs, ys = np.array(xs), np.array(ys)
        ax.plot(xs, ys, ls, color=BLUE, lw=1.1, alpha=0.75)
    ax.annotate("candidate trajectories\n(open-loop plans)",
                xy=(6, 6), xytext=(10, -20),
                arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=8)
    # delayed torpedo corridor from the red formation
    th = math.atan2(0 - yr, 0 - xr)
    for w in (-0.35, 0.35):
        ax.plot([xr, xr + 26 * math.cos(th + w)], [yr, yr + 26 * math.sin(th + w)],
                color=RED, lw=0.9, alpha=0.5)
    wedge_x = [xr, xr + 26 * math.cos(th - 0.35), xr + 26 * math.cos(th + 0.35)]
    wedge_y = [yr, yr + 26 * math.sin(th - 0.35), yr + 26 * math.sin(th + 0.35)]
    ax.fill(wedge_x, wedge_y, color=RED, alpha=0.12)
    tt = np.linspace(0, 1, 30)
    tx = xr + tt * 20 * math.cos(th)
    ty = yr + tt * 20 * math.sin(th)
    ax.scatter(tx[3::6], ty[3::6], s=6, color=RED, alpha=0.7, marker="*", zorder=5)
    ax.annotate("delayed torpedo hazard $H(x,t;q_t)$",
                xy=(tx[-1], ty[-1]), xytext=(-20, -22),
                arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=8)
    ax.set_xlim(-24, 24); ax.set_ylim(-24, 24)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle("Two formations compete over future trajectories in anisotropic and delayed fields",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "fig1_schematic.png", bbox_inches="tight")
    plt.close(fig)
    print("fig1 done")


def fig2():
    ex = json.load(open(REPO / "research" / "results" / "b2" / "example_AB.json"))["example"]
    LA = np.array(ex["A"]["L_series"]); LB = np.array(ex["B"]["L_series"])
    JA = np.cumsum(LA); JB = np.cumsum(LB)
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.0))
    # panel a: trajectories (schematic, from plan kinematics)
    ax = axes[0]
    for plan, col, lab in (("A", BLUE, "trajectory $A$ (turn $+180^\\circ$)"),
                           ("B", "#e08214", "trajectory $B$ (turn $+30^\\circ$)")):
        p = ex[plan]
        hdeg = 30.0
        xs, ys = [0.0], [0.0]
        rate = {"turn+180": 60.0, "turn+30": 10.0}[p["plan_B"]]
        for t in range(12):
            if t < 3:
                hdeg += rate
            xs.append(xs[-1] + 4.8 * math.cos(math.radians(hdeg)))
            ys.append(ys[-1] + 4.8 * math.sin(math.radians(hdeg)))
        ax.plot(xs, ys, "-", color=col, lw=1.4, label=lab)
    ax.set_xlabel("$x$ (hex)"); ax.set_ylabel("$y$ (hex)")
    ax.set_title("(a) Two committed trajectories")
    ax.legend(loc="lower right")
    ax = axes[1]
    t = np.arange(len(LA))
    ax.step(t, LA, where="post", color=BLUE, lw=1.4,
            label=fr"$L_A$: peak {ex['A']['peak']:.2f}")
    ax.step(t, LB, where="post", color="#e08214", lw=1.4,
            label=fr"$L_B$: peak {ex['B']['peak']:.2f}")
    ax.set_xlabel("turn $t$"); ax.set_ylabel("instantaneous advantage $L(t)$")
    ax.set_title("(b) Instantaneous payoff")
    ax.legend()
    ax = axes[2]
    ax.plot(t, JA, "-", color=BLUE, lw=1.6,
            label=fr"$J_A(T)={ex['A']['integral']:.2f}$")
    ax.plot(t, JB, "-", color="#e08214", lw=1.6,
            label=fr"$J_B(T)={ex['B']['integral']:.2f}$")
    ax.set_xlabel("turn $t$"); ax.set_ylabel(r"cumulative $J(t)=\int_0^t L\,dt$")
    ax.set_title("(c) Path-integrated payoff")
    ax.annotate("peak criterion prefers $A$,\nintegral prefers $B$",
                xy=(0.42, 0.06), xycoords="axes fraction", fontsize=8)
    ax.legend(loc="upper left")
    fig.suptitle("The optimal object is the trajectory integral, not the best position", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIG / "fig2_peak_vs_integral.png", bbox_inches="tight")
    plt.close(fig)
    print("fig2 done")


def fig3():
    data = json.load(open(REPO / "research" / "final_v8" / "figures" / "fig3_grid.json"))
    eta_v = np.array(data["eta_v"]); eta_r = np.array(data["eta_r"])
    Z = np.array(data["V_minus_L"])
    fig, ax = plt.subplots(figsize=(4.6, 3.6))
    vmax = np.nanmax(np.abs(Z))
    im = ax.pcolormesh(eta_v, eta_r, Z.T, cmap="RdBu_r", vmin=-vmax, vmax=vmax,
                       shading="nearest")
    cb = fig.colorbar(im, ax=ax)
    cb.set_label(r"$\max_s |V-L|$  (degeneracy violation)")
    ax.axvline(1.0, color="k", lw=0.7, ls="--")
    ax.axhline(1.0, color="k", lw=0.7, ls="--")
    ax.set_xlabel(r"speed ratio $\eta_v$"); ax.set_ylabel(r"range ratio $\eta_r$")
    ax.set_title("What breaks the closed-loop degeneracy")
    fig.text(0.02, -0.02,
             "Interaction-strength asymmetry (horizontal axis) breaks the collapse;\n"
             "speed asymmetry (vertical axis) leaves it essentially intact.",
             fontsize=8, va="top", ha="left")
    fig.tight_layout()
    fig.savefig(FIG / "fig3_degeneracy_boundary.png", bbox_inches="tight")
    plt.close(fig)
    print("fig3 done")


def fig4():
    rows = list(csv.DictReader(open(REPO / "research" / "final_v8" / "commitment"
                                    / "certification_results.csv")))
    rows = [r for r in rows if int(float(r["K"])) == 6 and float(r["eta_r"]) != 1.0]
    geoms = ("head_on", "parallel", "crossing")
    eta_vs = sorted({float(r["eta_v"]) for r in rows})
    eta_rs = sorted({float(r["eta_r"]) for r in rows})
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.2), sharey=True)
    for ax, g, title in zip(axes, geoms, ("head-on", "parallel chase", "crossing")):
        for r in rows:
            if r["geometry"] != g:
                continue
            ev, er = float(r["eta_v"]), float(r["eta_r"])
            sign = int(r["certified_sign"])
            pl, pu = float(r["P_lower"]), float(r["P_upper"])
            certified = bool(int(r["sign_certified"]))
            face = {1: "#2166ac", -1: "#b2182b", 0: "#f0f0f0"}[sign] if certified else "#f0f0f0"
            edge = "k" if certified else "#999999"
            hatch = None if certified else "///"
            ax.add_patch(Rectangle((ev - 0.09, er - 0.06), 0.18, 0.12,
                                   facecolor=face, edgecolor=edge,
                                   hatch=hatch, lw=1.0))
            ax.text(ev, er, f"[{pl:+.1f},\n{pu:+.1f}]", ha="center",
                    va="center", fontsize=6.2,
                    color="white" if certified and sign != 0 else "black")
        ax.set_xticks(eta_vs); ax.set_yticks(eta_rs)
        ax.set_xlabel(r"speed ratio $\eta_v$")
        ax.set_title(title)
        ax.set_xlim(min(eta_vs) - 0.2, max(eta_vs) + 0.2)
        ax.set_ylim(min(eta_rs) - 0.15, max(eta_rs) + 0.15)
    axes[0].set_ylabel(r"range ratio $\eta_r$")
    import matplotlib.patches as mpatches
    handles = [mpatches.Patch(facecolor="#2166ac", label="certified $P_6>0$"),
               mpatches.Patch(facecolor="#b2182b", label="certified $P_6<0$"),
               mpatches.Patch(facecolor="#f0f0f0", hatch="///", edgecolor="#999999",
                              label="uncertified (interval crosses 0)")]
    axes[-1].legend(handles=handles, loc="center left", bbox_to_anchor=(1.02, 0.5),
                    fontsize=8)
    fig.suptitle("Certified commitment comparative statics: sign of the value of a 6-turn commitment",
                 fontsize=10)
    fig.tight_layout(rect=(0, 0, 0.86, 0.92))
    fig.savefig(FIG / "fig4_commitment_certification.png", bbox_inches="tight")
    plt.close(fig)
    print("fig4 done")


def fig5():
    """Delayed threat: (a) threat mass moves to future turns, per cell;
    (b) time-dependence of the hazard (single-pulse hot share);
    (c) response-set contraction vs salvo thickness."""
    stats = list(csv.DictReader(open(REPO / "research" / "results" / "b10"
                                     / "field_stats.csv")))
    td = json.load(open(REPO / "research" / "results" / "b10"
                        / "time_dependence.json"))
    contr = list(csv.DictReader(open(REPO / "research" / "results" / "b11"
                                     / "contraction.csv")))
    ks = sorted({int(float(r["k"])) for r in contr})
    c_by_k = {k: np.mean([float(r["c_resp"]) for r in contr
                          if int(float(r["k"])) == k]) for k in ks}
    ci_by_k = {k: (np.percentile([float(r["c_resp"]) for r in contr
                                  if int(float(r["k"])) == k], 25),
                   np.percentile([float(r["c_resp"]) for r in contr
                                  if int(float(r["k"])) == k], 75)) for k in ks}

    fig, axes = plt.subplots(1, 3, figsize=(9.8, 2.9))
    # (a) future-turn threat mass fraction per cell
    frac = sorted(float(r["future_turn_threat_mass_fraction"]) for r in stats)
    axes[0].bar(range(len(frac)), [100 * f for f in frac], color=RED, alpha=0.8)
    axes[0].axhline(0, color="k", lw=0.7)
    axes[0].set_xlabel("tested engagement cells")
    axes[0].set_ylabel("% of threat mass in later turns")
    axes[0].set_title("(a) Threat mass lies in the future")
    axes[0].set_ylim(0, 50)
    axes[0].annotate(f"{100 * min(frac):.0f}--{100 * max(frac):.0f}% of the field's\n"
                     "threat mass acts after the\nlaunch turn, with no further\n"
                     "attacker decision", xy=(0.04, 0.72), xycoords="axes fraction",
                     fontsize=7.5)

    # (b) hazard time-dependence: hot-pulse count distribution for one cell
    cell = td["cells"]["chase:1v1"]["time_dependence"]
    dist = cell["hot_pulse_count_distribution"]
    xs = [int(k) for k in dist]
    ys = [dist[str(x)] for x in xs]
    axes[1].bar(xs, ys, color="#777777")
    axes[1].set_xlabel("impulses at which the hex is hot")
    axes[1].set_ylabel("hot hexes")
    axes[1].set_title("(b) The same hex is hot at some impulses only")
    axes[1].annotate(f"single-pulse hot share {100 * cell['single_pulse_hot_share']:.0f}%\n"
                     f"(mean {cell['mean_hot_pulses_per_hot_hex']:.1f} of "
                     f"{td['cells']['chase:1v1']['n_pulses']} impulses)",
                     xy=(0.36, 0.72), xycoords="axes fraction", fontsize=7.5)

    # (c) response-set contraction vs thickness
    axes[2].errorbar(ks, [c_by_k[k] for k in ks],
                     yerr=[[abs(c_by_k[k] - ci_by_k[k][0]) for k in ks],
                           [abs(ci_by_k[k][1] - c_by_k[k]) for k in ks]],
                     fmt="o-", color=BLUE, capsize=3, lw=1.2, ms=5)
    axes[2].set_xlabel("torpedo salvo thickness $k$")
    axes[2].set_ylabel(r"contraction $C_{\rm resp}$")
    axes[2].set_title("(c) Thicker salvos contract responses")
    axes[2].set_ylim(-0.02, 0.45)
    fig.tight_layout()
    fig.savefig(FIG / "fig5_delayed_threat.png", bbox_inches="tight")
    plt.close(fig)
    print("fig5 done")


def fig6():
    res = json.load(open(REPO / "research" / "results" / "final_v7"
                         / "must2_results.json"))
    cells = res["per_cell"]
    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    markers = {"head_on": "o", "parallel": "s", "crossing": "^"}
    for c in cells:
        x, y = c["V_surrogate"], c["F-F"]["axis_adv"]
        err = (c["F-F"]["ci"][1] - c["F-F"]["ci"][0]) / 2
        ax.errorbar(x, y, yerr=err, fmt=markers[c["geometry"]],
                    color=BLUE if c["speed"] == 4 else RED,
                    ms=7, capsize=2.5, lw=1,
                    markeredgecolor="k", markeredgewidth=0.5)
    ax.axhline(0, color="k", lw=0.7); ax.axvline(0, color="k", lw=0.7)
    ax.set_xlabel(r"model: formation surrogate value $\Delta J_{\rm model}$")
    ax.set_ylabel(r"engine: axis advantage $\Delta J_{\rm engine}$")
    g = res["gates"]
    ax.annotate(f"sign agreement {g['sign_agreement']:.0%} (gate $\\geq$80%)\n"
                f"Spearman $\\rho$ = {g['spearman_rho']:.2f} (gate $\\geq$0.60)\n"
                f"pairwise ordering {g['pairwise_ordering']:.0%} (gate $\\geq$75%)\n"
                f"verdict: {res['verdict']}",
                xy=(0.03, 0.03), xycoords="axes fraction", fontsize=8,
                bbox=dict(boxstyle="round", fc="white", ec="#999999", alpha=0.9))
    for geom, mk in markers.items():
        ax.scatter([], [], marker=mk, color="k", label=geom.replace("_", "-"))
    ax.scatter([], [], marker="s", color=BLUE, label="$v_0=4$")
    ax.scatter([], [], marker="s", color=RED, label="$v_0=6$")
    ax.legend(fontsize=7, loc="upper right")
    ax.set_title("Transfer of reduced-model comparative statics to the rules engine")
    fig.tight_layout()
    fig.savefig(FIG / "fig6_engine_transfer.png", bbox_inches="tight")
    plt.close(fig)
    print("fig6 done")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("figs", nargs="*", default=["1", "2", "5", "6"])
    a = ap.parse_args()
    table = {"1": fig1, "2": fig2, "3": fig3, "4": fig4, "5": fig5, "6": fig6}
    for f in a.figs:
        table[f]()
