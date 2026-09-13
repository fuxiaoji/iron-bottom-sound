"""B6 landscape quantiles from perplan_distribution.csv."""
import csv
import numpy as np

rows = list(csv.DictReader(open("research/results/b6/perplan_distribution.csv")))
for r in rows:
    r["peak_ratio"] = float(r["peak_ratio"])
    r["share_ratio"] = float(r["share_ratio"])
    r["eta_v"] = float(r["eta_v"])
    r["eta_omega"] = float(r["eta_omega"])

lines = ["# B6 viability landscape (per-plan distribution over R's library)", ""]
for g in ("head_on", "parallel", "crossing"):
    for ew in (0.7, 1.0, 1.3):
        body = []
        for ev in sorted({r["eta_v"] for r in rows
                          if r["geometry"] == g and r["eta_omega"] == ew}):
            sel = [r["share_ratio"] for r in rows
                   if r["geometry"] == g and r["eta_omega"] == ew
                   and r["eta_v"] == ev]
            if sel:
                q25, med, q75 = np.percentile(sel, [25, 50, 75])
                body.append(f"  eta_v={ev}: n={len(sel)} median={med:.2f} "
                            f"IQR=[{q25:.2f},{q75:.2f}] max={max(sel):.2f}")
        if body:
            lines.append(f"## {g} (eta_omega={ew})")
            lines.extend(body)
open("research/results/b6/landscape.md", "w").write("\n".join(lines) + "\n")
print("\n".join(lines[:20]))
