"""v14 figure generation (master plan section 4: eight main figures).

Every figure reads frozen data (analysis CSVs produced by analysis_v14.py or
the frozen design metadata); nothing is hand-entered.  Conventions follow the
scientific-visualization skill: colourblind-safe palettes, no chartjunk,
vector PDF plus >=300 dpi PNG, all axes labelled with units, and missing or
unresolved values shown explicitly rather than hidden.

Figure map
  F1  revision calendar and information structure (schematic)
  F2  directional field and path-integrated payoff (model)
  F3  budget frontier W_K (main result)
  F4  selected calendars (heat map over epochs)
  F5  loss certificates: bound versus realised loss
  F6  computation: certified gap and wall time
  F7  robustness and ablations
  F8  retention: minimum budget for 90/95/99% of full-flexibility value
"""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, Rectangle

REPO = Path(__file__).resolve().parents[2]
V14 = REPO / "research" / "final_v14"
ANALYSIS = V14 / "analysis"
FIG = REPO / "paper_v14" / "figures"

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
    "legend.fontsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "figure.dpi": 300, "savefig.dpi": 300, "axes.spines.top": False,
    "axes.spines.right": False, "lines.linewidth": 1.3, "lines.markersize": 5,
})
# Okabe-Ito colourblind-safe palette
CB = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#999999"]
GEO_COLOR = {"head_on": CB[0], "parallel": CB[1], "crossing": CB[2]}


def save(fig, name: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG / f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"{name}: pdf + png written")


def load(path: Path) -> list[dict]:
    return list(csv.DictReader(open(path))) if path.exists() else []


def frontier() -> list[dict]:
    return load(ANALYSIS / "budget_frontier.csv")


def f1_calendar() -> None:
    """Schematic: public calendar, sealed blocks, private unexecuted suffix."""
    fig, ax = plt.subplots(figsize=(6.6, 2.9))
    T = 6
    ax.plot([0, T], [0.62, 0.62], color="#333333", lw=1.0)
    for t in range(T + 1):
        ax.plot([t, t], [0.57, 0.67], color="#333333", lw=1.0)
        ax.text(t, 0.52, f"{t}", ha="center", va="top", fontsize=8)
    ax.text(T / 2, 0.72, "engaged epochs $t$", ha="center", fontsize=8)
    S = [1, 2, 4]
    for t in range(T):
        sealed = t + 1 in S
        ax.add_patch(Rectangle((t, 0.30), 1.0, 0.16,
                               facecolor=CB[0] if not sealed else CB[1],
                               alpha=0.30 if not sealed else 0.55,
                               edgecolor="none"))
        ax.text(t + 0.5, 0.38, "public" if sealed else "sealed", ha="center",
                va="center", fontsize=7)
    ax.text(-0.15, 0.38, "own\ncommands", ha="right", va="center", fontsize=8)
    for t in S:
        ax.add_patch(FancyArrowPatch((t, 0.24), (t, 0.10),
                                     arrowstyle="-|>", mutation_scale=10,
                                     color=CB[1], lw=1.2))
    ax.text(T / 2, 0.02, "revision epochs in $S=\\{1,2,4\\}$  (budget $K=3$): "
                         "the executed history is observed and a new block is sealed",
            ha="center", fontsize=8)
    ax.set_xlim(-1.6, T + 0.2); ax.set_ylim(-0.06, 0.82)
    ax.axis("off")
    ax.set_title("Public revision calendar, sealed command blocks private "
                 "until executed", fontsize=10)
    save(fig, "fig1_calendar_information")


def f2_field() -> None:
    """Directional kernel and the path-integrated objective."""
    sys.path.insert(0, str(REPO / "backend" / "src"))
    sys.path.insert(0, str(REPO))
    from research.geometry.firepower_kernel import KernelFit
    from research.geometry.committed_game import KernelWrap
    from research.experiments.t1_exact_discrete_certification import fire_vec
    kd = json.load(open(REPO / "research" / "results" / "e01" / "kernel_fits.json"))["CA"]
    fit = KernelFit.from_dict(kd); kw = KernelWrap(fit, 1.0)
    xs = np.linspace(-6, 26, 200); ys = np.linspace(-16, 16, 200)
    XX, YY = np.meshgrid(xs, ys)
    r = np.maximum(np.hypot(XX, YY), 0.5)
    d = np.degrees(np.arctan2(YY, XX))
    a = np.abs((d + 180.0) % 360.0 - 180.0)
    asp = np.where((a <= 30.0) | (a >= 150.0), "bow_stern", "broadside")
    F = fire_vec(kw, r, d, asp)
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.5))
    ax = axes[0]
    im = ax.pcolormesh(XX, YY, np.ma.masked_less(F, 0.01), cmap="cividis",
                       shading="auto", rasterized=True)
    cb = fig.colorbar(im, ax=ax, shrink=0.85, pad=0.02)
    cb.set_label("directional kernel $K$ (expected hits per pulse)")
    ax.plot(0, 0, "o", color="k", ms=5)
    ax.annotate("shooter", xy=(0, 0), xytext=(-5, 6), fontsize=8,
                arrowprops=dict(arrowstyle="->", lw=0.8))
    ax.set_aspect("equal"); ax.set_xlabel("down-range (hex)"); ax.set_ylabel("lateral (hex)")
    ax.set_title("(a) anisotropic interaction kernel")
    ax = axes[1]
    t = np.arange(6)
    L = np.array([1.0, -0.8, 2.4, 0.3, -0.4, 1.1])
    ax.step(t, L, where="post", color=CB[0], label="$L(h_t)$ instantaneous")
    ax.plot(t, np.cumsum(L), "o-", color=CB[1], label=r"$\sum_{t'\leq t} L$ integrated")
    ax.axhline(0, color="k", lw=0.7)
    ax.set_xlabel("engaged epoch $t$"); ax.set_ylabel("payoff")
    ax.set_title("(b) the objective integrates the field")
    ax.legend(fontsize=7.5)
    fig.suptitle("Directional field and path-integrated payoff (illustrative "
                 "trajectory; kernel from the frozen calibration)", fontsize=9.5)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    save(fig, "fig2_field_integral")


def f3_frontier() -> None:
    fr = frontier()
    if not fr:
        print("F3: no frontier data yet"); return
    grp = defaultdict(list)
    for r in fr:
        grp[(r["cell"], r["side"], r["opponent"])].append(r)
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.6), sharey=False)
    for ax, opp, title in zip(axes, ("C", "F"),
                              ("against committed opponent $C$",
                               "against flexible opponent $F$")):
        for (cell, side, o), rs in sorted(grp.items()):
            if o != opp or side != "blue":
                continue
            rs = sorted(rs, key=lambda x: int(x["K"]))
            ks = [int(x["K"]) for x in rs]; ws = [float(x["W_K"]) for x in rs]
            geo = cell.split("_")[0] + ("_" + cell.split("_")[1] if "_v" in cell else "")
            lab = cell.replace("_d16_T6_G3_none", "")
            ax.plot(ks, ws, "o-", color=GEO_COLOR.get(cell.split("_")[0], CB[6]),
                    alpha=0.85, label=lab)
        ax.set_xlabel("revision budget $K$")
        ax.set_title(title)
    axes[0].set_ylabel("value $W_K$")
    axes[0].legend(fontsize=6.5, ncol=2)
    fig.suptitle("Certified budget frontier: value attainable with at most $K$ "
                 "revisions (frozen design)", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    save(fig, "fig3_budget_frontier")


def f4_calendars() -> None:
    fr = frontier()
    if not fr: print("F4: no data"); return
    grp = {}
    for r in fr:
        grp.setdefault((r["cell"], r["side"], r["opponent"]), []).append(r)
    keys = [k for k in sorted(grp) if k[1] == "blue"]
    maxK = max(int(r["K"]) for r in fr)
    M = np.full((len(keys), maxK + 1), np.nan)
    for i, k in enumerate(keys):
        for r in grp[k]:
            S = json.loads(r["S_star"])
            M[i, int(r["K"])] = 1.0 if S else 0.0
    fig, ax = plt.subplots(figsize=(5.4, 0.34 * len(keys) + 1.6))
    im = ax.imshow(M, aspect="auto", cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(maxK + 1)); ax.set_xticklabels(range(maxK + 1))
    ax.set_yticks(range(len(keys)))
    ax.set_yticklabels([f"{k[0].replace('_d16_T6_G3_none','')} | opp {k[2]}"
                        for k in keys], fontsize=7)
    ax.set_xlabel("budget $K$")
    for i, k in enumerate(keys):
        for r in grp[k]:
            S = json.loads(r["S_star"])
            ax.text(int(r["K"]), i, "".join(str(s) for s in S) or "—",
                    ha="center", va="center", fontsize=6.5,
                    color="white" if S else "black")
    ax.set_title("Maximizing calendar by budget\n(entries: revision epochs in $S^{\\star}$)",
                 fontsize=9.5)
    save(fig, "fig4_optimal_calendars")


def f5_certificates() -> None:
    files = sorted((V14 / "certificates").glob("*.json")) if (V14 / "certificates").exists() else []
    cur = load(ANALYSIS / "certificate_summary.csv")
    fig, ax = plt.subplots(figsize=(5.6, 3.6))
    if cur:
        x = [float(c["realised_loss"]) for c in cur]
        y = [float(c["certified_bound"]) for c in cur]
        ax.plot(x, y, "o", color=CB[0], mec="k", mew=0.5)
        lim = [0, max(max(x), max(y)) * 1.1 + 1e-9]
        ax.plot(lim, lim, "--", color="#777777", lw=1, label="$y=x$")
        ax.set_xlabel("realised loss of the coarsened calendar")
        ax.set_ylabel("certificate upper bound")
        ax.legend(fontsize=8)
    else:
        ax.axis("off")
        ax.text(0.03, 0.5,
                "certificate experiment pending:\n"
                "the deletion and interval-loss certificates\n"
                "are reported once the frozen runs complete",
                fontsize=9)
    ax.set_title("Loss certificates: bound versus realised loss", fontsize=10)
    save(fig, "fig5_loss_certificates")


def f6_computation() -> None:
    fr = frontier()
    if not fr: print("F6: no data"); return
    gaps = [float(r["gap"]) for r in fr if r.get("gap")]
    secs = [float(r["seconds"]) for r in fr if r.get("seconds")]
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.2))
    ax = axes[0]
    ax.hist(np.log10(np.maximum(gaps, 1e-16)), bins=18, color=CB[0], alpha=0.85)
    ax.set_xlabel(r"$\log_{10}$ certified interval width")
    ax.set_ylabel("solver runs")
    ax.set_title("(a) certified residual")
    ax = axes[1]
    ax.hist(np.log10(np.maximum(secs, 1e-3)), bins=18, color=CB[1], alpha=0.85)
    ax.set_xlabel(r"$\log_{10}$ wall time (s)"); ax.set_ylabel("solver runs")
    ax.set_title("(b) single-calendar computation")
    fig.suptitle("Computation of the frozen frontier", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.91))
    save(fig, "fig6_computation")


def f7_robustness() -> None:
    fr = frontier()
    if not fr: print("F7: no data"); return
    cells = sorted({r["cell"] for r in fr})
    rob = [c for c in cells if "_T" in c and any(f"_T{t}_" in c for t in (4, 5, 7))]
    abl = [c for c in cells if c.split("_")[-1] in ("isotropic", "terminal", "rigid")]
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.4))
    ax = axes[0]
    by_geo = defaultdict(list)
    for c in rob:
        base = next((x for x in cells if x.startswith(c.split("_")[0])
                     and "_T6_" in x and x.endswith("_none")), None)
        if base is None: continue
        f_b = [float(r["W_K"]) for r in fr if r["cell"] == base and r["opponent"] == "C"
               and r["side"] == "blue"]
        f_c = [float(r["W_K"]) for r in fr if r["cell"] == c and r["opponent"] == "C"
               and r["side"] == "blue"]
        if f_b and f_c:
            by_geo[c.split("_")[0]].append((c, max(f_c) - max(f_b)))
    for g, xs in sorted(by_geo.items()):
        ax.plot([1, 2, 3], [x[1] for x in xs[:3]], "o-", color=GEO_COLOR.get(g, CB[6]), label=g)
    ax.axhline(0, color="k", lw=0.7)
    ax.set_xticks([1, 2, 3]); ax.set_xticklabels(["$T{=}4$", "$T{=}5$", "$T{=}7$"])
    ax.set_ylabel(r"$W_{\max}$ difference from $T{=}6$")
    ax.set_title("(a) horizon robustness"); ax.legend(fontsize=7)
    ax = axes[1]
    names, vals = [], []
    for c in abl:
        base = c.replace(c.split("_")[-1], "none")
        f_b = [float(r["W_K"]) for r in fr if r["cell"] == base and r["opponent"] == "C"
               and r["side"] == "blue"]
        f_c = [float(r["W_K"]) for r in fr if r["cell"] == c and r["opponent"] == "C"
               and r["side"] == "blue"]
        if f_b and f_c:
            names.append(c.split("_")[-1]); vals.append(max(f_c) - max(f_b))
    if names:
        ax.bar(range(len(names)), vals, color=CB[3])
        ax.set_xticks(range(len(names))); ax.set_xticklabels(names, fontsize=7.5)
        ax.axhline(0, color="k", lw=0.7)
        ax.set_ylabel(r"$W_{\max}$ difference from full model")
    else:
        ax.axis("off"); ax.text(0.03, 0.5, "ablation runs pending", fontsize=9)
    ax.set_title("(b) one-factor ablations")
    fig.suptitle("Robustness and ablations", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.91))
    save(fig, "fig7_robustness_ablation")


def f8_retention() -> None:
    rt = load(ANALYSIS / "retention_budgets.csv")
    if not rt:
        print("F8: no retention data yet"); return
    rows = [r for r in rt if r.get("retention") and r["side"] == "blue"]
    if not rows:
        print("F8: no retention rows"); return
    fig, ax = plt.subplots(figsize=(6.0, 3.8))
    fr = {r["retention"]: r for r in rows}
    labels, vals = [], []
    for frac in ("0.9", "0.95", "0.99"):
        rs = [r for r in rows if abs(float(r["retention"]) - float(frac)) < 1e-9]
        kc = [int(r["K_certified"]) for r in rs if r.get("K_certified")]
        labels.append(f"{float(frac)*100:.0f}%")
        vals.append(float(np.median(kc)) if kc else float("nan"))
    ax.bar(range(len(labels)), vals, color=CB[0], alpha=0.85)
    for i, v in enumerate(vals):
        if math.isnan(v):
            ax.text(i, 0.05, "unresolved", ha="center", fontsize=8, color="#b2182b")
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels)
    ax.set_xlabel("required retention of full-flexibility value")
    ax.set_ylabel("median certified budget $K$")
    ax.set_title("Certified minimum revision budget by retention target",
                 fontsize=10)
    save(fig, "fig8_retention_budget")


if __name__ == "__main__":
    which = sys.argv[1:] or ["1", "2", "3", "4", "5", "6", "7", "8"]
    table = {"1": f1_calendar, "2": f2_field, "3": f3_frontier, "4": f4_calendars,
             "5": f5_certificates, "6": f6_computation, "7": f7_robustness,
             "8": f8_retention}
    for w in which:
        table[w]()
