"""v11 matched-horizon commitment experiment (plan sections 7-18, 62).

Fixed evaluation horizon T for every policy class; the ONLY thing that varies
is the replanning cadence h in {1,2,3,6}:

    C_h = V_T^{(h)} - V_T^{(1)},   C_1 = 0.

Stage rewards are trapezoid interval rewards, so every action affects the
reward of the step in which it is executed.  Receding policies sample from the
COMPLETE equilibrium mixture (no truncation, no argmax).  Values are Monte
Carlo expectations of this receding-equilibrium implementation.

Modes:
  --pilot          small N to measure runtime / variance / support sizes
  --main           the 18-cell h in {1,2,3,6} experiment (paired seeds, CRN)
  --grid7          Grid-7 anchors: 6 cells, h=1 vs h=6
  --horizon        T in {4,6,8} on the 6 anchor cells, h=1 vs h=T
  --bridge         rigid vs LF matched-horizon C_6 on 6 anchors

Outputs: research/final_v11/commitment_matched/*.csv/json/report.md
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

from research.formation.path_following import make_lf_game  # noqa: E402
from research.formation.matched_horizon import (  # noqa: E402
    GRIDS, LeaderState, initial_states, run_cadence, T_DEFAULT,
)

OUT = REPO / "research" / "final_v11" / "commitment_matched"
KD = json.load(open(REPO / "research" / "results" / "e01" / "kernel_fits.json"))["CA"]
CELLS = [(g, er, ev) for g in ("head_on", "parallel", "crossing")
         for er in (0.8, 1.2) for ev in (0.8, 1.0, 1.2)]
ANCHORS = [(g, er, 1.0) for g in ("head_on", "parallel", "crossing")
           for er in (0.8, 1.2)]
CADENCES = (1, 2, 3, 6)


def mc_cell(geometry, eta_r, eta_v, h, T, grid, n_seeds, seed0,
            do_iters, model="leader_follower"):
    game = make_lf_game(KD, geometry, eta_r, eta_v, T, formation_mode=model)
    levels = GRIDS[grid]
    cache: dict = {}
    Js = []
    diag = []
    for i in range(n_seeds):
        rng = np.random.default_rng(seed0 + i)
        out = run_cadence(game, *initial_states(game), h, T, levels, cache,
                          rng, do_iters=do_iters)
        Js.append(out["J"])
        if i == 0:
            diag = out["epochs"]
    return {"J": Js, "epochs": diag, "cache_states": len(
        {k[:5] for k in cache}), "n_cache_entries": len(cache)}


def paired_ci(d: np.ndarray, n: int = 10000) -> tuple:
    rng = np.random.default_rng(12345)
    idx = rng.integers(0, len(d), size=(n, len(d)))
    m = d[idx].mean(axis=1)
    return float(d.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def run_cell_main(args):
    (geometry, eta_r, eta_v), T, grid, n_seeds, seed0, do_iters = args
    t0 = time.time()
    res = {}
    for h in CADENCES:
        res[h] = mc_cell(geometry, eta_r, eta_v, h, T, grid, n_seeds, seed0,
                         do_iters)
    base = np.array(res[1]["J"])
    row = {"geometry": geometry, "eta_r": eta_r, "eta_v": eta_v, "T": T,
           "grid": grid, "n_seeds": n_seeds}
    for h in CADENCES:
        d = np.array(res[h]["J"]) - base          # paired CRN difference
        m, lo, hi = paired_ci(d)
        row[f"C{h}"] = round(m, 4)
        row[f"C{h}_lo"] = round(lo, 4)
        row[f"C{h}_hi"] = round(hi, 4)
        row[f"C{h}_significant"] = int((lo > 0) or (hi < 0))
        row[f"V{h}"] = round(float(np.mean(res[h]["J"])), 4)
        row[f"sd{h}"] = round(float(np.std(res[h]["J"])), 4)
    row["expect_sign"] = 0 if eta_r == 1.0 else (1 if eta_r > 1 else -1)
    row["C6_matches_expect"] = int(
        np.sign(row["C6"]) == row["expect_sign"]) if row["expect_sign"] else None
    row["seconds"] = round(time.time() - t0, 1)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="pilot",
                    choices=["pilot", "main", "grid7", "horizon", "bridge"])
    ap.add_argument("--seeds", type=int, default=0)
    ap.add_argument("--do-iters", type=int, default=15)
    ap.add_argument("--workers", type=int, default=5)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    if a.mode == "pilot":
        row = run_cell_main((("head_on", 1.2, 1.0), 6, "5", 10, 10_000, a.do_iters))
        print(json.dumps(row, indent=1))
        return

    if a.mode == "main":
        n = a.seeds or 200
        jobs = [(c, 6, "5", n, 10_000, a.do_iters) for c in CELLS]
        tag = "main_18cells"
    elif a.mode == "grid7":
        n = a.seeds or 100
        jobs = [(c, 6, "7", n, 20_000, 6) for c in ANCHORS]
        tag = "grid7_anchors"
    elif a.mode == "horizon":
        n = a.seeds or 100
        jobs = [((g, er, 1.0), T, "5", n, 30_000, a.do_iters)
                for T in (4, 6, 8) for (g, er, _) in ANCHORS]
        tag = "horizon_anchors"
    else:  # bridge
        n = a.seeds or 100
        jobs = []
        for c in ANCHORS:
            jobs.append((c, 6, "5", n, 40_000, a.do_iters))
        tag = "bridge_anchors"
        rows = []
        for c in ANCHORS:
            for model in ("leader_follower", "rigid_line_ahead"):
                res1 = mc_cell(*c, 1, 6, "5", n, 40_000, a.do_iters, model=model)
                res6 = mc_cell(*c, 6, 6, "5", n, 40_000, a.do_iters, model=model)
                d = np.array(res6["J"]) - np.array(res1["J"])
                m, lo, hi = paired_ci(d)
                rows.append({"geometry": c[0], "eta_r": c[1], "model": model,
                             "C6": round(m, 4), "C6_lo": round(lo, 4),
                             "C6_hi": round(hi, 4),
                             "significant": int((lo > 0) or (hi < 0))})
        with open(OUT / "bridge_rigid_vs_lf_C6.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        ok = 0
        for c in ANCHORS:
            lf = next(r for r in rows if r["geometry"] == c[0] and r["eta_r"] == c[1]
                      and r["model"] == "leader_follower")
            rg = next(r for r in rows if r["geometry"] == c[0] and r["eta_r"] == c[1]
                      and r["model"] == "rigid_line_ahead")
            ok += int(np.sign(lf["C6"]) == np.sign(rg["C6"]))
        print(f"[v11-bridge] rigid vs LF C6 sign agreement: {ok}/{len(ANCHORS)}")
        json.dump({"sign_agreement": f"{ok}/{len(ANCHORS)}", "rows": rows},
                  open(OUT / "bridge_summary.json", "w"), indent=2)
        return

    print(f"[v11-{tag}] {len(jobs)} runs, {n} paired seeds each", flush=True)
    t0 = time.time()
    rows = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(run_cell_main, j): j for j in jobs}
        for fut in as_completed(futs):
            r = fut.result()
            rows.append(r)
            print(f"  {r['geometry']:9s} er={r['eta_r']} ev={r['eta_v']} T={r['T']} "
                  f"g{r['grid']}: C6={r['C6']:+.3f} [{r['C6_lo']:+.3f},{r['C6_hi']:+.3f}] "
                  f"sig={r['C6_significant']} C3={r['C3']:+.3f} C2={r['C2']:+.3f} "
                  f"({r['seconds']}s)", flush=True)
    fields = list(rows[0].keys())
    with open(OUT / f"{tag}.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader(); w.writerows(rows)

    asym = [r for r in rows if r["expect_sign"] != 0]
    sig = [r for r in asym if r["C6_significant"]]
    sig_ok = [r for r in sig if np.sign(r["C6"]) == r["expect_sign"]]
    geom_ok = {}
    for g in ("head_on", "parallel", "crossing"):
        sub = [r for r in sig_ok if r["geometry"] == g]
        geom_ok[g] = {"pos": sum(1 for r in sub if r["C6"] > 0),
                      "neg": sum(1 for r in sub if r["C6"] < 0)}
    n_ok = len(sig_ok)
    if n_ok >= 15 and all(v["pos"] >= 1 and v["neg"] >= 1 for v in geom_ok.values()):
        verdict = "CORE-STRONG"
    elif n_ok >= 10:
        verdict = "CORE-CONDITIONAL"
    else:
        verdict = "REMOVE-CORE"
    summary = {"mode": tag, "n_cells": len(rows), "n_asymmetric": len(asym),
               "n_significant": len(sig), "n_sign_correct": n_ok,
               "n_significant_wrong_sign": len(sig) - n_ok,
               "geometry_support": geom_ok, "verdict": verdict,
               "wall_time_s": round(time.time() - t0, 1)}
    json.dump(summary, open(OUT / f"commitment_summary_{tag}.json", "w"), indent=2)
    print(f"[v11-{tag}] DONE verdict={verdict} significant={len(sig)}/{len(asym)} "
          f"correct-sign={n_ok} in {time.strftime('%H:%M:%S', time.gmtime(time.time()-t0))}",
          flush=True)


if __name__ == "__main__":
    main()
