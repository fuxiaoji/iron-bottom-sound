"""B13 aggregation from games.csv (boots variable fix)."""
import csv
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

REPO = Path(__file__).resolve().parents[2]
N = 100
rows = list(csv.DictReader(open(REPO / "research" / "results" / "b13" / "games.csv")))
print("games:", len(rows))
index = {(r["policy"], r["geometry"], int(r["seed"])): r for r in rows}
preds = json.load(open(REPO / "research" / "results" / "b13" / "model_predictions.json")) \
    if (REPO / "research" / "results" / "b13" / "model_predictions.json").exists() else None

# recompute model predictions inline (same as the b13 script)
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))
from research.geometry.committed_game import KernelWrap, make_maneuver_library, simulate  # noqa: E402
from research.geometry.firepower_kernel import KernelFit  # noqa: E402

fits = json.load(open(REPO / "research" / "results" / "e01" / "kernel_fits.json"))
kB = KernelWrap(KernelFit.from_dict(fits["CA"]))
kR = KernelWrap(KernelFit.from_dict(fits["CA"]))
lib = make_maneuver_library()
GEOM = {"head_on": (0.0, 0.0, 180.0),
        "parallel": (90.0, 0.0, 0.0),
        "crossing": (45.0, 0.0, 180.0)}
preds = {}
for gname, (brg, hB, hR) in GEOM.items():
    pay = []
    for name_b, plan_b in lib.items():
        out = simulate(kB, kR, plan_b, [0.0] * 40, 16, brg, hB, hR, 6.0, 6.0, 40)
        pay.append(out["payoff_B"])
    preds[gname] = {"model_value_vs_straight": round(float(np.mean(pay)), 4)}

cells = []
rng = np.random.default_rng(20260911)
for g in GEOM:
    gd = np.array([float(index[("geometry", g, s)]["diff"]) for s in range(1, N + 1)
                   if ("geometry", g, s) in index])
    sd = np.array([float(index[("straight", g, s)]["diff"]) for s in range(1, N + 1)
                   if ("straight", g, s) in index])
    n = min(len(gd), len(sd))
    gd, sd = gd[:n], sd[:n]
    mean_diff = float(np.mean(gd) - np.mean(sd))
    boot = []
    for _ in range(4000):
        pick = rng.choice(n, size=n, replace=True)
        boot.append(float(np.mean(gd[pick]) - np.mean(sd[pick])))
    lo, hi = np.percentile(boot, [2.5, 97.5])
    mv = preds[g]["model_value_vs_straight"]
    cells.append({
        "geometry": g, "n": n,
        "engine_mean_diff": round(mean_diff, 3),
        "engine_ci95": [round(float(lo), 2), round(float(hi), 2)],
        "engine_positive_frac": round(float(np.mean(gd > sd)), 3),
        "model_value_vs_straight": mv,
        "sign_agree": int((mv > 0) == (mean_diff > 0)),
        "model_class": ("advantage" if abs(mv) >= 0.3 else "neutral"),
        "engine_class": ("advantage" if mean_diff >= 0.3 else
                         "disadvantage" if mean_diff <= -0.3 else "neutral"),
    })
    print(cells[-1])

agree = int(np.mean([c["sign_agree"] for c in cells]) * 100)
mvals = [abs(c["model_value_vs_straight"]) for c in cells]
evals = [abs(c["engine_mean_diff"]) for c in cells]
rho, _ = spearmanr(mvals, evals)
regime_ok = sum(1 for c in cells
                if (c["model_class"] == "advantage") == (c["engine_mean_diff"] > 0))
regime_agree = int(regime_ok / len(cells) * 100)

result = {
    "cells": cells,
    "gates": {
        "sign_agreement": {"value_pct": agree, "gate": 80,
                           "pass": bool(agree >= 80)},
        "rank_correlation": {"value": round(float(rho), 4), "gate": 0.60,
                             "pass": bool(rho >= 0.60)},
        "regime_agreement": {"value_pct": regime_agree, "gate": 75,
                             "pass": bool(regime_agree >= 75)},
    },
    "overall": ("PASS" if (agree >= 80 and rho >= 0.60 and regime_agree >= 75)
                else "PARTIAL" if agree >= 80 else "FAIL"),
}
json.dump(result, open(REPO / "research" / "results" / "b13" / "results.json",
                       "w"), indent=2)
with open(REPO / "research" / "results" / "b13" / "cells.csv", "w",
          newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(cells[0].keys())
    for c in cells:
        w.writerow(c.values())
lines = ["# B13 engine validation (v4 gates)", ""]
for c in cells:
    lines.append(f"- {c['geometry']}: engine {c['engine_mean_diff']:+.2f} "
                 f"CI {c['engine_ci95']} | model {c['model_value_vs_straight']:+.3f} "
                 f"| sign agree {bool(c['sign_agree'])}")
lines.append(f"- sign agreement: {agree}% (gate 80%)")
lines.append(f"- rank correlation: rho={rho:.4f} (gate 0.60)")
lines.append(f"- regime agreement: {regime_agree}% (gate 75%)")
open(REPO / "research" / "results" / "b13" / "report.md", "w").write(
    "\n".join(lines) + "\n")
print(json.dumps(result["gates"], indent=2))
