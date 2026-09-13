"""B6 aggregation from thresholds.csv (fix for crit/col key mismatch)."""
import csv
import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

rows = list(csv.DictReader(open("research/results/b6/thresholds.csv")))
for r in rows:
    r["eta_v"] = float(r["eta_v"])
    r["eta_omega"] = float(r["eta_omega"])
    r["worst_peak"] = float(r["worst_peak"])
    r["worst_share"] = float(r["worst_share"])
    r["reachable"] = int(r["reachable"])
    r["viable"] = int(r["viable"])

ALPHA, TAU = 0.5, 0.5
ETA_OMEGA = [0.7, 1.0, 1.3]
GEOM = ["head_on", "parallel", "crossing"]

thresholds = {}
for ew in ETA_OMEGA:
    for g in GEOM:
        for crit, col in (("reachability", "reachable"), ("viability", "viable")):
            cells = [r for r in rows if r["eta_omega"] == ew and r["geometry"] == g]
            ok = [r["eta_v"] for r in cells if r[col] == 1]
            thresholds[f"{g}|{ew}|{crit}"] = {
                "eta_v_star": min(ok) if ok else None,
                "n_grid": len(cells),
            }

result = {"alpha": ALPHA, "tau": TAU, "thresholds": thresholds,
          "n_cells": len(rows)}
json.dump(result, open("research/results/b6/results.json", "w"), indent=2)

lines = ["# B6 reachability / viability thresholds", "",
         f"G_alpha: L >= {ALPHA}; viability: worst-case share >= {TAU}", ""]
for key, st in sorted(thresholds.items()):
    lines.append(f"- {key}: eta_v* = {st['eta_v_star']} (grid n={st['n_grid']})")
open("research/results/b6/report.md", "w").write("\n".join(lines) + "\n")

fig, ax = plt.subplots(figsize=(7.2, 4.4))
for ew, style in zip(ETA_OMEGA, ("--", "-", ":")):
    sel = sorted([r for r in rows if r["eta_omega"] == ew
                  and r["geometry"] == "parallel"], key=lambda r: r["eta_v"])
    ax.plot([r["eta_v"] for r in sel], [r["worst_share"] for r in sel],
            style, marker="o", label=f"eta_omega={ew}")
ax.axhline(TAU, color="k", lw=0.8, ls="--")
ax.set_xlabel(r"speed ratio $\eta_v$")
ax.set_ylabel("worst-case share of steps with L >= alpha")
ax.set_title(r"B6 viability curves (parallel, $\alpha=0.5$)")
ax.legend()
fig.savefig("research/results/b6/fig_b6_thresholds.png", dpi=160,
            bbox_inches="tight")
print(json.dumps(thresholds, indent=1))
