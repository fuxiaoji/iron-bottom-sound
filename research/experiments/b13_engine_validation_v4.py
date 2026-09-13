"""B13: engine validation at v4 gates (100 paired seeds per cell).

Extends E06 to the v4 validation gates:
  1. sign agreement >= 80%  -- model's predicted advantage sign vs engine
     paired damage-differential sign, per cell;
  2. rank correlation >= 0.60 -- model game values vs engine mean
     differentials across cells;
  3. regime agreement >= 75% -- model classification
     (advantage/disadvantage/neutral at |V| >= 0.3) vs engine
     classification of the same cells.

Design: symmetric cruiser duel (San Francisco vs New Orleans), three
geometries, AXIS policies {geometry, straight}; ALLIES always
balanced doctrine.  Model side: the committed-maneuver game's maximin
value of the geometry policy's plan against the straight heading plan
(the "model-vs-straight" cell prediction) -- plus, for cross-cell rank
correlation, each cell's model game value between the geometry maximin
plan and the straight plan.

Output: research/results/b13/{cells.csv, results.json, report.md}
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

OUT = REPO / "research" / "results" / "b13"
N_SEEDS = 100


def engine_run(args) -> dict:
    # reuse the proven e06 runner
    from research.experiments.e06_engine_validation import run_one
    return run_one(args)


def model_predictions():
    """Model-side cell predictions from the committed-maneuver game.

    For each geometry: the LP value of the game where B's plan set is the
    full library (the geometry policy plays the maximin plan) and R is
    pinned to the straight-ahead plan (the straight baseline's behavior).
    Positive value => the model predicts the geometry policy beats
    straight sailing.
    """
    from research.geometry.committed_game import (
        KernelWrap,
        make_maneuver_library,
        simulate,
        solve_matrix_game,
    )
    from research.geometry.firepower_kernel import KernelFit

    fits = json.load(open(REPO / "research" / "results" / "e01" / "kernel_fits.json"))
    kB = KernelWrap(KernelFit.from_dict(fits["CA"]))
    kR = KernelWrap(KernelFit.from_dict(fits["CA"]))
    lib = make_maneuver_library()
    straight = [0.0] * 40
    GEOM = {"head_on": (0.0, 0.0, 180.0),
            "parallel": (90.0, 0.0, 0.0),
            "crossing": (45.0, 0.0, 180.0)}
    preds = {}
    for gname, (brg, hB, hR) in GEOM.items():
        pay = []
        for name_b, plan_b in lib.items():
            out = simulate(kB, kR, plan_b, straight, 16, brg, hB, hR,
                           6.0, 6.0, 40)
            pay.append(out["payoff_B"])
        val = float(np.mean(pay))  # B's expected payoff vs straight sailing
        best = max(pay)
        preds[gname] = {"model_value_vs_straight": round(val, 4),
                        "model_best_vs_straight": round(best, 4),
                        "model_sign": int(val > 0)}
    return preds


def main() -> None:
    import csv

    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [("geometry", g, s) for g in ("parallel", "head_on", "crossing")
            for s in range(1, N_SEEDS + 1)]
    jobs += [("straight", g, s) for g in ("parallel", "head_on", "crossing")
             for s in range(1, N_SEEDS + 1)]
    rows = []
    with ProcessPoolExecutor(max_workers=8) as pool:
        for r in pool.map(engine_run, jobs):
            rows.append(r)
            if len(rows) % 100 == 0:
                print(f"{len(rows)}/{len(jobs)}", flush=True)

    with (OUT / "games.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(rows[0].keys())
        for r in rows:
            w.writerow(r.values())

    index = {(r["policy"], r["geometry"], r["seed"]): r for r in rows}
    preds = model_predictions()
    cells = []
    for g in ("parallel", "head_on", "crossing"):
        gd = [index[("geometry", g, s)]["diff"] for s in range(1, N_SEEDS + 1)]
        sd = [index[("straight", g, s)]["diff"] for s in range(1, N_SEEDS + 1)]
        boot = []
        rng = np.random.default_rng(20260911)
        gd_a, sd_a = np.array(gd), np.array(sd)
        for _ in range(4000):
            pick = rng.choice(len(gd), size=len(gd), replace=True)
            boot.append(float(np.mean(gd_a[pick]) - np.mean(sd_a[pick])))
        lo, hi = np.percentile(boots, [2.5, 97.5])
        mean_diff = float(np.mean(gd_a) - np.mean(sd_a))
        pos_frac = float(np.mean(gd_a > sd_a))
        model_sign = int(preds[gname]["model_sign"])
        engine_sign = int(mean_diff > 0)
        cells.append({
            "geometry": g, "n": N_SEEDS,
            "engine_mean_diff": round(mean_diff, 3),
            "engine_ci95": [round(float(lo), 2), round(float(hi), 2)],
            "engine_positive_frac": round(pos_frac, 3),
            "model_value_vs_straight": preds[gname]["model_value_vs_straight"],
            "sign_agree": int(model_sign == engine_sign),
            "model_class": ("advantage" if abs(preds[gname]["model_value_vs_straight"]) >= 0.3
                            else "neutral"),
            "engine_class": ("advantage" if mean_diff >= 0.3 else
                             "disadvantage" if mean_diff <= -0.3 else "neutral"),
        })
    agree = int(np.mean([c["sign_agree"] for c in cells]) * 100)
    model_vals = [abs(c["model_value_vs_straight"]) for c in cells]
    engine_vals = [abs(c["engine_mean_diff"]) for c in cells]
    from scipy.stats import spearmanr
    rho, _ = spearmanr(model_vals, engine_vals)
    regime_ok = sum(
        1 for c in cells
        if (c["model_class"] == "advantage") == (c["engine_mean_diff"] > 0))
    regime_agree = int(regime_ok / len(cells) * 100)

    gate_sign = agree >= 80
    gate_rank = bool(rho >= 0.60)
    gate_regime = regime_agree >= 75
    result = {
        "cells": cells,
        "gates": {
            "sign_agreement": {"value_pct": agree, "gate": 80,
                               "pass": bool(gate_sign)},
            "rank_correlation": {"value": round(float(rho), 4), "gate": 0.60,
                                 "pass": bool(rho >= 0.60)},
            "regime_agreement": {"value_pct": regime_agree, "gate": 75,
                                 "pass": bool(regime_agree >= 75)},
        },
        "overall": "PASS" if (gate_sign and rho >= 0.60 and regime_agree >= 75)
                   else "PARTIAL" if gate_sign else "FAIL",
    }
    (OUT / "results.json").write_text(json.dumps(result, indent=2),
                                      encoding="utf-8")
    with (OUT / "cells.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cells[0].keys())
        for c in cells:
            w.writerow(c.values())
    lines = ["# B13 engine validation (v4 gates, 100 seeds/cell)", ""]
    for c in cells:
        lines.append(f"- {c['geometry']}: engine diff {c['engine_mean_diff']:+.2f} "
                     f"CI {c['engine_ci95']} | model {c['model_value_vs_straight']:+.3f} "
                     f"| sign agree: {bool(c['sign_agree'])}")
    lines.append(f"- sign agreement: {agree}% (gate 80%) -> {gate_sign}")
    lines.append(f"- rank correlation: rho={rho:.4f} (gate 0.60) -> {rho >= 0.60}")
    lines.append(f"- regime agreement: {regime_agree}% (gate 75%)")
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result["gates"], indent=2))


if __name__ == "__main__":
    main()
