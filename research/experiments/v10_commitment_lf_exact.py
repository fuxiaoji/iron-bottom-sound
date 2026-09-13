"""v10 Phase 3: exact finite-game commitment certification under the
leader-follower path-following formation (plan sections 19-24).

The v9 certification framework is unchanged: frozen action grids
Grid-5 = {-1,-1/2,0,1/2,1} (5^6 = 15 625 sequences) and
Grid-7 = {-1,-2/3,-1/3,0,1/3,2/3,1} (7^6 = 117 649), exhaustive full-space
best responses against the COMPLETE restricted mixture (no truncation), and
valid equilibrium bounds

    LB = min_{tau_R in Omega} E_{tau_B ~ x} J   <=  V*  <=
    UB = max_{tau_B in Omega} E_{tau_R ~ y} J

with H=1 solved exactly on the complete |A|x|A| matrix.  The only change is
that the payoff J is evaluated with the leader-follower formation
(batch_payoff_lf) instead of rigid rotation.  The same run is repeated for the
rigid line-ahead baseline so that P6 can be compared like for like
(plan section 24: rigid_vs_lf_exact.csv).

Outputs: research/final_v10/commitment_lf_exact/
    lf_grid5_results.csv, lf_grid7_results.csv,
    lf_certification_summary.json, lf_certification_report.md,
    rigid_grid5_results.csv, rigid_grid7_results.csv,
    rigid_vs_lf_exact.csv
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

from research.geometry.committed_game import wrap_deg  # noqa: E402
from research.formation.path_following import (  # noqa: E402
    DEFAULT_NSUB, batch_payoff_lf, make_lf_game,
)
from research.experiments.v10_bridge import batch_payoff_rigid_la, _lp  # noqa: E402
from research.experiments.t1_exact_discrete_certification import GRIDS  # noqa: E402
from research.experiments.must1_formation_do import GEOM  # noqa: E402

OUT = REPO / "research" / "final_v10" / "commitment_lf_exact"
KD = json.load(open(REPO / "research" / "results" / "e01" / "kernel_fits.json"))["CA"]
OMEGA_MAX = 60.0
H = 6
CELLS = [(g, er, ev) for g in GEOM for er in (0.8, 1.2)
         for ev in (0.8, 1.0, 1.2)]
SANITY = [(g, 1.0, 1.0) for g in GEOM]
DO_MAX_ITERS = 30
GAP_TOL = 0.05
SEED_ACTIONS = (0.0, 0.5, -0.5, 1.0, -1.0)


def _seeds(seqs):
    idx = []
    for a in SEED_ACTIONS:
        sig = np.full(H, a * OMEGA_MAX)
        idx.append(int(np.argmin(np.abs(seqs - sig).sum(axis=1))))
    for a, b in ((1.0, -1.0), (-1.0, 1.0), (1.0, 0.0), (0.0, 1.0)):
        sig = np.concatenate([np.full(H // 2, a * OMEGA_MAX),
                              np.full(H - H // 2, b * OMEGA_MAX)])
        idx.append(int(np.argmin(np.abs(seqs - sig).sum(axis=1))))
    return list(dict.fromkeys(idx))


def certify(game, batch_fn, grid_id: str) -> dict:
    import itertools
    seqs = np.array(list(itertools.product(GRIDS[grid_id], repeat=H))) * OMEGA_MAX
    n = len(seqs)
    X = _seeds(seqs)
    Y = list(X)
    cols: dict[int, np.ndarray] = {}
    rows: dict[int, np.ndarray] = {}
    LB = UB = V = float("nan")
    hist = []

    def col(j):
        if j not in cols:
            cols[j] = batch_fn(game, seqs, seqs[j], True)
        return cols[j]

    def row(i):
        if i not in rows:
            rows[i] = batch_fn(game, seqs, seqs[i], False)
        return rows[i]

    it = 0
    for it in range(DO_MAX_ITERS):
        pay = np.zeros((len(X), len(Y)))
        for b, j in enumerate(Y):
            pay[:, b] = col(j)[X]
        V, xr, yr = _lp(pay)
        xf = np.zeros(n); xf[X] = xr
        yf = np.zeros(n); yf[Y] = yr
        totR = np.zeros(n)
        for i in np.where(xf > 0)[0]:
            totR += xf[i] * row(int(i))
        jmin = int(np.argmin(totR)); LB = float(totR[jmin])
        totB = np.zeros(n)
        for j in np.where(yf > 0)[0]:
            totB += yf[j] * col(int(j))
        imax = int(np.argmax(totB)); UB = float(totB[imax])
        hist.append({"iter": it + 1, "V": V, "LB": LB, "UB": UB,
                     "rel_gap": (UB - LB) / max(1.0, abs(V))})
        if (UB - LB) / max(1.0, abs(V)) < GAP_TOL:
            break
        newB = imax not in X; newR = jmin not in Y
        if newB:
            X.append(imax)
        if newR:
            Y.append(jmin)
        if not newB and not newR:
            break
    return {"V": float(V), "LB": LB, "UB": UB, "iters": it + 1,
            "rel_gap": (UB - LB) / max(1.0, abs(V)), "n_full": n,
            "n_support_B": len(X), "n_support_R": len(Y), "trace": hist}


def h1_exact(game, batch_fn, grid_id: str) -> dict:
    import itertools
    seqs = np.array(list(itertools.product(GRIDS[grid_id], repeat=1))) * OMEGA_MAX
    n = len(seqs)
    pay = np.zeros((n, n))
    for j in range(n):
        pay[:, j] = batch_fn(game, seqs, seqs[j], True)
    V, x, y = _lp(pay)
    lb = float((x @ pay).min()); ub = float((pay @ y).max())
    return {"V1": float(V), "LB1": lb, "UB1": ub, "exact": abs(ub - lb) < 1e-8}


def run_cell(args):
    geometry, eta_r, eta_v, grid_id, model = args
    t0 = time.time()
    mode = "leader_follower" if model == "lf" else "rigid_line_ahead"
    batch = batch_payoff_lf if model == "lf" else batch_payoff_rigid_la
    game = make_lf_game(KD, geometry, eta_r, eta_v, H, formation_mode=mode)
    r6 = certify(game, batch, grid_id)
    r1 = h1_exact(game, batch, grid_id)
    plo, phi = r6["LB"] - r1["UB1"], r6["UB"] - r1["LB1"]
    sign = 1 if plo > 0 else (-1 if phi < 0 else 0)
    expected = 0 if eta_r == 1.0 else (1 if eta_r > 1 else -1)
    return {"model": model, "geometry": geometry, "eta_r": eta_r, "eta_v": eta_v,
            "grid": grid_id, "H": H,
            "V_restricted": round(r6["V"], 4),
            "lower_bound": round(r6["LB"], 4), "upper_bound": round(r6["UB"], 4),
            "bound_width": round(r6["UB"] - r6["LB"], 4),
            "relative_gap": round(r6["rel_gap"], 4),
            "LB_1": round(r1["LB1"], 4), "UB_1": round(r1["UB1"], 4),
            "P_lower": round(plo, 4), "P_upper": round(phi, 4),
            "point_estimate": round((r6["LB"] + r6["UB"]) / 2
                                    - (r1["LB1"] + r1["UB1"]) / 2, 4),
            "sign_certified": int(sign != 0), "certified_sign": sign,
            "expected_sign": expected,
            "solver_status": ("tight" if r6["rel_gap"] < GAP_TOL
                              else "SIGN-CERTIFIED/VALUE-LOOSE" if sign != 0
                              else "UNCERTIFIED"),
            "n_full_strategies": r6["n_full"], "DO_iterations": r6["iters"],
            "restricted_rows": r6["n_support_B"], "restricted_cols": r6["n_support_R"],
            "h1_exact": int(r1["exact"]), "runtime_sec": round(time.time() - t0, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grids", default="5,7")
    ap.add_argument("--models", default="lf,rigid")
    ap.add_argument("--phase", default="all", choices=["all", "sanity"])
    ap.add_argument("--cell", default=None, help="single cell 'geom,eta_r,eta_v'")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    grids = a.grids.split(",")
    models = a.models.split(",")
    cells = SANITY if a.phase == "sanity" else CELLS
    if a.cell:
        g, er, ev = a.cell.split(",")
        cells = [(g, float(er), float(ev))]
    jobs = [(g, er, ev, gid, m) for gid in grids for m in models
            for (g, er, ev) in cells]
    print(f"[v10-T3] {len(jobs)} certification runs "
          f"(grids {grids}, models {models}, cells {len(cells)})", flush=True)
    t0 = time.time()
    rows = []
    jf = open(OUT / "lf_certification_trace.jsonl", "a")
    with ProcessPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(run_cell, j): j for j in jobs}
        for fut in as_completed(futs):
            r = fut.result()
            rows.append(r)
            for tr in r.get("trace", []):
                jf.write(json.dumps({"model": r["model"], "geometry": r["geometry"],
                                     "eta_r": r["eta_r"], "eta_v": r["eta_v"],
                                     "grid": r["grid"], **tr}) + "\n")
            jf.flush()
            print(f"  {r['model']:13s} {r['geometry']:9s} er={r['eta_r']} "
                  f"ev={r['eta_v']} g{r['grid']}: LB={r['lower_bound']:+.3f} "
                  f"UB={r['upper_bound']:+.3f} P=[{r['P_lower']:+.2f},"
                  f"{r['P_upper']:+.2f}] sign={r['certified_sign']:+d} "
                  f"({r['runtime_sec']}s)", flush=True)
    jf.close()
    phase_tag = "" if a.phase == "all" else f"_{a.phase}"
    for model in models:
        for gid in grids:
            sub = [r for r in rows if r["model"] == model and r["grid"] == gid]
            if not sub:
                continue
            with open(OUT / f"{model}_grid{gid}{phase_tag}_results.csv", "w",
                      newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(sub[0].keys()))
                w.writeheader(); w.writerows(sub)

    lf5 = [r for r in rows if r["model"] == "lf" and r["grid"] == "5"
           and r["eta_r"] != 1.0]
    lf7 = [r for r in rows if r["model"] == "lf" and r["grid"] == "7"
           and r["eta_r"] != 1.0]
    rg5 = {(r["geometry"], r["eta_r"], r["eta_v"]): r for r in rows
           if r["model"] == "rigid" and r["grid"] == "5"}
    n_cert = sum(r["sign_certified"] for r in lf5)
    rev = [r for r in lf5 if r["sign_certified"]
           and r["certified_sign"] != r["expected_sign"]]
    rev7 = [r for r in lf7 if r["sign_certified"]
            and r["certified_sign"] != r["expected_sign"]]
    geom_ok = {}
    for g in GEOM:
        sub = [r for r in lf5 if r["geometry"] == g]
        geom_ok[g] = {"pos": sum(1 for r in sub if r["certified_sign"] > 0),
                      "neg": sum(1 for r in sub if r["certified_sign"] < 0),
                      "n": len(sub)}
    # rigid-vs-LF exact comparison on the same cells
    cmp_rows = []
    for r in lf5:
        k = (r["geometry"], r["eta_r"], r["eta_v"])
        rr = rg5.get(k)
        cmp_rows.append({"geometry": k[0], "eta_r": k[1], "eta_v": k[2],
                         "P6_lf": r["point_estimate"], "P6_rigid": rr["point_estimate"] if rr else None,
                         "sign_lf": r["certified_sign"],
                         "sign_rigid": rr["certified_sign"] if rr else None,
                         "sign_match": int(bool(rr) and r["certified_sign"] == rr["certified_sign"])})
    with open(OUT / "rigid_vs_lf_exact.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cmp_rows[0].keys()))
        w.writeheader(); w.writerows(cmp_rows)
    n_match = sum(c["sign_match"] for c in cmp_rows)

    if (n_cert >= 15 and not rev and not rev7
            and all(v["pos"] >= 1 and v["neg"] >= 1 for v in geom_ok.values())):
        verdict = "LF-CORE-STRONG"
    elif n_cert >= 10 and not rev and not rev7:
        verdict = "LF-CORE-CONDITIONAL"
    elif rev or rev7:
        verdict = "LF-REMOVE-CORE"
    else:
        verdict = "LF-CORE-CONDITIONAL"
    summary = {"grid5_lf_cells": len(lf5), "grid5_lf_sign_certified": n_cert,
               "grid5_lf_reversals": len(rev), "grid7_lf_cells": len(lf7),
               "grid7_lf_reversals": len(rev7), "geometry_support": geom_ok,
               "rigid_vs_lf_sign_match": f"{n_match}/{len(cmp_rows)}",
               "h1_exact_all": all(r["h1_exact"] for r in rows),
               "verdict": verdict,
               "wall_time_s": round(time.time() - t0, 1)}
    json.dump(summary, open(OUT / f"lf_certification_summary{phase_tag}.json", "w"),
              indent=2)
    lines = ["# v10: leader-follower exact commitment certification", "",
             f"Grids: {grids}; H=1 exact on every cell: {summary['h1_exact_all']}",
             f"Grid-5 LF: {n_cert}/{len(lf5)} sign-certified, {len(rev)} reversals",
             f"Grid-7 LF: {len(lf7)} cells, {len(rev7)} reversals",
             f"Geometry support: {geom_ok}",
             f"Rigid vs LF sign match (Grid-5): {n_match}/{len(cmp_rows)}",
             f"**VERDICT: {verdict}**", "",
             "| model | geometry | eta_r | eta_v | grid | LB | UB | P interval | sign | gap | status |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (r["model"], r["grid"], r["geometry"],
                                         r["eta_r"], r["eta_v"])):
        if r["eta_r"] == 1.0:
            continue
        lines.append(f"| {r['model']} | {r['geometry']} | {r['eta_r']} | {r['eta_v']} "
                     f"| {r['grid']} | {r['lower_bound']:+.3f} | {r['upper_bound']:+.3f} "
                     f"| [{r['P_lower']:+.2f}, {r['P_upper']:+.2f}] "
                     f"| {r['certified_sign']:+d} | {r['relative_gap']:.0%} "
                     f"| {r['solver_status']} |")
    (OUT / f"lf_certification_report{phase_tag}.md").write_text("\n".join(lines),
                                                                encoding="utf-8")
    print(f"[v10-T3] DONE verdict={verdict} lf5={n_cert}/{len(lf5)} "
          f"rigid-vs-lf match={n_match}/{len(cmp_rows)} in "
          f"{time.strftime('%H:%M:%S', time.gmtime(time.time() - t0))}", flush=True)


if __name__ == "__main__":
    main()
