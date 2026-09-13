"""v11 Figure 4: matched-horizon replanning-cadence result C_6.

All cells use the same six-step evaluation horizon; only the replanning
cadence changes (h=1 maximum flexibility vs h=6 full commitment).  Colour is
the paired mean C_6; a solid border means the 95% paired bootstrap interval
excludes zero, hatching means it contains zero.  A cross marks a cell whose
significant sign contradicts sign(eta_r - 1).  The rightmost panel reports the
symmetric control diagnostic (eta_r = eta_v = 1), where C_6 must vanish by
symmetry.
"""
from __future__ import annotations
import csv, json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

REPO = Path(__file__).resolve().parents[3]
FIG = REPO / "paper_v11" / "figures"
D = REPO / "research" / "final_v11" / "commitment_matched"
plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
                     "legend.fontsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
                     "figure.dpi": 300, "savefig.dpi": 300, "axes.spines.top": False,
                     "axes.spines.right": False})
BLUE, RED, GREY = "#2166ac", "#b2182b", "#777777"
GT = {"head_on": "head-on", "parallel": "parallel chase", "crossing": "crossing"}

rows = list(csv.DictReader(open(D / "main_18cells.csv")))
ctr = json.load(open(D / "symmetric_controls.json")) if (D / "symmetric_controls.json").exists() else [
    {"geometry": "head_on", "C6": 1.03, "lo": -0.82, "hi": 2.99},
    {"geometry": "parallel", "C6": -2.66, "lo": -3.70, "hi": -1.61},
    {"geometry": "crossing", "C6": 6.14, "lo": 4.88, "hi": 7.45}]
eta_vs = sorted({float(r["eta_v"]) for r in rows})
eta_rs = sorted({float(r["eta_r"]) for r in rows})
vmax = max(abs(float(r["C6"])) for r in rows)

fig, axes = plt.subplots(1, 4, figsize=(12.6, 3.3),
                         gridspec_kw={"width_ratios": [1, 1, 1, 0.8]})
for ax, g in zip(axes[:3], ("head_on", "parallel", "crossing")):
    for r in rows:
        if r["geometry"] != g:
            continue
        ev, er = float(r["eta_v"]), float(r["eta_r"])
        c6, lo, hi = float(r["C6"]), float(r["C6_lo"]), float(r["C6_hi"])
        sig = int(r["C6_significant"]); exp = int(r["expect_sign"])
        wrong = sig and (np.sign(c6) != exp)
        ax.add_patch(Rectangle((ev - 0.11, er - 0.07), 0.22, 0.14, facecolor="none",
                               edgecolor=GREY, lw=0.6))
        ax.add_patch(Rectangle((ev - 0.11, er - 0.07), 0.22, 0.14,
                               facecolor=BLUE if c6 > 0 else RED,
                               alpha=min(0.9, 0.15 + 0.75 * abs(c6) / vmax),
                               edgecolor="none"))
        if sig:
            ax.add_patch(Rectangle((ev - 0.11, er - 0.07), 0.22, 0.14, facecolor="none",
                                   edgecolor="k", lw=2.0))
        else:
            ax.add_patch(Rectangle((ev - 0.11, er - 0.07), 0.22, 0.14, facecolor="none",
                                   edgecolor="k", lw=1.0, hatch="///"))
        ax.text(ev, er, f"{c6:+.1f}", ha="center", va="center", fontsize=7)
        if wrong:
            ax.plot(ev, er, "x", color="k", ms=8, mew=1.8)
    ax.set_xticks(eta_vs); ax.set_yticks(eta_rs)
    ax.set_xlabel(r"speed ratio $\eta_v$"); ax.set_title(GT[g])
    ax.set_xlim(min(eta_vs) - 0.22, max(eta_vs) + 0.22)
    ax.set_ylim(min(eta_rs) - 0.14, max(eta_rs) + 0.14)
axes[0].set_ylabel(r"range ratio $\eta_r$")

ax = axes[3]
names = [c["geometry"].replace("_", "-") for c in ctr]
vals = [float(c["C6"]) for c in ctr]
los = [float(c["lo"]) for c in ctr]
his = [float(c["hi"]) for c in ctr]
xs = np.arange(len(ctr))
ax.errorbar(xs, vals, yerr=[np.array(vals) - np.array(los), np.array(his) - np.array(vals)],
            fmt="o", color="#333333", capsize=4, ms=6)
ax.axhline(0, color="k", lw=0.8)
ax.set_xticks(xs); ax.set_xticklabels(names, fontsize=7.5)
ax.set_title("symmetric control\n($\\eta_r=\\eta_v=1$)")
ax.set_ylabel(r"$C_6$ (must vanish by symmetry)")
for i, (v, lo, hi) in enumerate(zip(vals, los, his)):
    if lo > 0 or hi < 0:
        ax.plot(i, v, "x", color=RED, ms=9, mew=2.0)
import matplotlib.patches as mpatches
handles = [mpatches.Patch(fc=BLUE, alpha=0.6, label="$C_6>0$ (commitment helps)"),
           mpatches.Patch(fc=RED, alpha=0.6, label="$C_6<0$"),
           mpatches.Patch(fc="none", ec="k", lw=2.0, label="95% CI excludes 0"),
           mpatches.Patch(fc="none", ec="k", lw=1.0, hatch="///", label="CI contains 0"),
           plt.Line2D([], [], ls="none", marker="x", color="k",
                      label="significant, sign opposite to prediction"),
           plt.Line2D([], [], ls="none", marker="x", color=RED,
                      label="symmetric cell with CI excluding 0 (control failure)")]
fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False,
           bbox_to_anchor=(0.5, -0.20), fontsize=7.5)
fig.suptitle("Matched-horizon replanning cadence: all cells use the same six-step "
             "evaluation horizon; only the cadence changes", fontsize=10)
fig.tight_layout(rect=(0, 0.02, 1, 0.93))
FIG.mkdir(exist_ok=True)
fig.savefig(FIG / "fig4_commitment_certification.pdf", bbox_inches="tight")
fig.savefig(FIG / "fig4_commitment_certification.png", dpi=300, bbox_inches="tight")
print("fig4 (v11, C6) written")
