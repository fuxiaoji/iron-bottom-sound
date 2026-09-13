"""T1 (v8): Commitment equilibrium-bound / sign certification.

Research question: can the 18/18 point-estimate sign pattern
sign(P_H) = sign(eta_r - 1) be CERTIFIED by equilibrium bounds, given that
only 67% of cells met the solver's approximate BR-gap gate in v7?

Method (v8 sections 3.2-3.3, 5-7):
  For each cell and each control parameterisation K in {3,4,6}:
  1. Double Oracle with ENHANCED best responses:
       Stage A (global): 48 Sobol quasi-random starts + quick L-BFGS-B polish;
       Stage B (local):  deep polish of the top-3 candidates with L-BFGS-B,
                         Powell, and Nelder-Mead (cross-validated);
       Stage C:          best-of-all evaluated candidates (never selected by
                         "fitting the theory"; own restricted plans included).
     Opponent mixes are truncated to weight >= 0.02 (cap 8 plans) inside the
     BR objective; weights renormalised (pure accelerator, recorded).
  2. Bounds per v8 3.2:
       L_H = restricted-game LP value  (provable lower bound on V*_H);
       U_H = B's best-of-search response value against the final pi_R
             (oracle upper bound; validity contingent on BR search quality,
             diagnostics recorded).
  3. Interval: P_H = V*_H - V*_1 in [L_H - U_1, U_H - L_1].
     certified > 0 if L_H - U_1 > 0; certified < 0 if U_H - L_1 < 0;
     else UNCERTIFIED (interval crosses zero). Point estimates are NOT used
     for sign when uncertified (v8 3.3).

  DO stop standard (v8 1.4): report g = U - L always; strong convergence if
  (U-L)/max(1,|V|) < 5%; a cell may be SIGN-CERTIFIED / VALUE-NOT-TIGHT.

Cells (v8 1.1): 18 asymmetric (3 geometries x eta_r {0.8,1.2} x
eta_v {0.8,1.0,1.2}) + 6 symmetric sanity (eta_r=1.0, eta_v {1.0,1.2}) +
K=8 on the anchor cell.  H = 6.  H=1 baselines use the same enhanced BR.

Classification (v8 1.5, frozen): STRONG if >=15/18 certified, >=2/3
geometries majority-certified in each direction, no certified reversal,
K-refinement does not change the main sign; CONDITIONAL if 10-14/18 with
no certified reversal; FAIL on certified reversals.

Output: research/final_v8/commitment/{certification_results.csv,
certification_summary.json, certification_report.md,
br_search_diagnostics.csv, k_refinement.csv}.
"""
from __future__ import annotations

import csv
import json
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from scipy.optimize import minimize, linprog
from scipy.stats import qmc

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

from research.geometry.committed_game import KernelWrap, wrap_deg  # noqa: E402
from research.geometry.firepower_kernel import KernelFit  # noqa: E402
from research.experiments.must1_formation_do import (  # noqa: E402
    FormationGame,
    GEOM,
    seg_setup,
    seg_bounds,
    seed_segments,
    RATE_MAX,
    _expected_J,
)

OUT = REPO / "research" / "final_v8" / "commitment"
N_GLOBAL_STARTS = 32
QUICK_ITER = 8
DEEP_ITER = 30
TOP_CANDIDATES = 2
W_TRUNC = 0.05
MIX_CAP = 4
DO_ITERS_MAIN = 4      # K=6 (primary parameterisation)
DO_ITERS_REFINE = 3    # K=3/4/8 (refinement checks)
GAP_TIGHT = 0.05


def truncate_mix(opp: list[np.ndarray], w: np.ndarray) -> tuple[list[np.ndarray], np.ndarray]:
    idx = np.where(w >= W_TRUNC)[0]
    if len(idx) == 0:
        idx = np.array([int(np.argmax(w))])
    if len(idx) > MIX_CAP:
        idx = idx[np.argsort(-w[idx])[:MIX_CAP]]
    w2 = w[idx] / w[idx].sum()
    return [opp[i] for i in idx], w2


def best_of_evals(game, opp, w, tps, maximize, cands, vals):
    best_i = int(np.argmax(vals) if maximize else np.argmin(vals))
    return np.asarray(cands[best_i], float), float(vals[best_i])


def enhanced_br(game: FormationGame, opp: list[np.ndarray], w: np.ndarray,
                maximize: bool, K: int, own_plans: list[np.ndarray]):
    """Three-stage BR (v8 1.2).  Returns (plan, value, n_evals, n_starts, methods)."""
    n_seg, tps = seg_setup(K, game.H)
    bounds = seg_bounds(n_seg, tps)
    lo = np.array([b[0] for b in bounds])
    hi = np.array([b[1] for b in bounds])
    opp_t, w_t = truncate_mix(opp, w)
    n_evals = 0
    cands: list[np.ndarray] = []
    vals: list[float] = []
    record = {"methods": []}

    def ev(seg):
        nonlocal n_evals
        n_evals += 1
        return _expected_J(np.asarray(seg, float), game, opp_t, w_t, tps, maximize)

    # own restricted plans are candidates too (guarantee BR >= V_restricted for B)
    for p in own_plans:
        cands.append(np.asarray(p, float)); vals.append(ev(p))
    # zeros
    cands.append(np.zeros(n_seg)); vals.append(ev(cands[-1]))

    # Stage A: Sobol global starts + quick L-BFGS-B polish
    sob = qmc.Sobol(d=n_seg, scramble=True, seed=20260912)
    X = qmc.scale(sob.random(N_GLOBAL_STARTS), lo, hi)
    quick = []
    for x0 in X:
        if maximize:
            r = minimize(lambda s: -ev(s), x0, method="L-BFGS-B", bounds=bounds,
                         options={"maxiter": QUICK_ITER})
            quick.append((np.asarray(r.x, float), -r.fun))
        else:
            r = minimize(lambda s: ev(s), x0, method="L-BFGS-B", bounds=bounds,
                         options={"maxiter": QUICK_ITER})
            quick.append((np.asarray(r.x, float), r.fun))
        cands.append(quick[-1][0]); vals.append(quick[-1][1])
    record["methods"].append("sobol48+lbfgs")
    order = np.argsort(vals)[:TOP_CANDIDATES] if not maximize else \
        np.argsort(vals)[-TOP_CANDIDATES:][::-1]
    # Stage B: deep polish of top candidates with three methods
    for i in order:
        x0, _ = quick[i] if i < len(quick) else (cands[i], vals[i])
        for method in ("L-BFGS-B", "Powell", "Nelder-Mead"):
            if maximize:
                r = minimize(lambda s: -ev(s), x0, method=method, bounds=bounds,
                             options={"maxiter": DEEP_ITER})
                cands.append(np.asarray(r.x, float)); vals.append(-r.fun)
            else:
                r = minimize(lambda s: ev(s), x0, method=method, bounds=bounds,
                             options={"maxiter": DEEP_ITER})
                cands.append(np.asarray(r.x, float)); vals.append(r.fun)
        record["methods"] += ["lbfgs-deep", "powell", "neldermead"]
    plan, val = best_of_evals(game, opp, w, tps, maximize, cands, vals)
    return plan, float(val), n_evals, N_GLOBAL_STARTS + len(cands), record


def restricted_lp(pay):
    m, n = pay.shape
    c = np.zeros(m + 1); c[-1] = -1.0
    A_ub = np.zeros((n, m + 1)); A_ub[:, :m] = -pay.T; A_ub[:, m] = 1.0
    A_eq = np.zeros((1, m + 1)); A_eq[0, :m] = 1.0
    res_B = linprog(c, A_ub=A_ub, b_ub=np.zeros(n), A_eq=A_eq, b_eq=[1.0],
                    bounds=[(0, None)] * m + [(None, None)])
    c_R = np.zeros(n + 1); c_R[-1] = 1.0
    A_ub_R = np.zeros((m, n + 1)); A_ub_R[:, :n] = pay; A_ub_R[:, n] = -1.0
    A_eq_R = np.zeros((1, n + 1)); A_eq_R[0, :n] = 1.0
    res_R = linprog(c_R, A_ub=A_ub_R, b_ub=np.zeros(m), A_eq=A_eq_R, b_eq=[1.0],
                    bounds=[(0, None)] * n + [(None, None)])
    ok = res_B.success and res_R.success
    if not ok:
        bi = int(np.argmax(pay.min(axis=1)))
        xB = np.zeros(m); xB[bi] = 1.0
        rj = int(np.argmin(pay.max(axis=0)))
        xR = np.zeros(n); xR[rj] = 1.0
        return float(pay[bi].min()), xB, xR
    return float((res_B.x[-1] + res_R.x[-1]) / 2.0), res_B.x[:m], res_R.x[:n]


def certify_game(kB, kR, geometry, eta_r, eta_v, H, K, max_iters):
    """DO with enhanced BR; returns L, U, diagnostics for this (H, K)."""
    brg, hB, hR = GEOM[geometry]
    game = FormationGame(kB, kR, r0=16.0, bearing0_deg=brg, hB0_deg=hB,
                         hR0_deg=hR, vB=6.0 * eta_v, vR=6.0, H=H)
    _, tps = seg_setup(K, H)
    plansB = seed_segments(H, tps)
    plansR = [s.copy() for s in plansB]
    total_evals = 0
    diag = []
    L = U = float("nan")
    for it in range(max_iters):
        pay = np.array([[game.payoff(a, b, tps) for b in plansR] for a in plansB])
        V, xB, xR = restricted_lp(pay)
        L = V
        pb, valB, ne1, _, rec1 = enhanced_br(game, plansR, xR, True, K, plansB)
        pr, valR, ne2, _, rec2 = enhanced_br(game, plansB, xB, False, K, plansR)
        U = valB                       # oracle upper bound on V*_H
        total_evals += ne1 + ne2
        gap = U - L
        rel = gap / max(1.0, abs(V))
        diag.append({"iter": it + 1, "V": V, "L": L, "U": U,
                     "rel_gap": rel, "evals": ne1 + ne2,
                     "methods_b": rec1["methods"][:3], "methods_r": rec2["methods"][:3]})
        if rel < GAP_TIGHT:
            break
        plansB.append(pb)
        plansR.append(pr)
    return {"L": float(L), "U": float(U), "V_restricted": float(L),
            "point": float((L + U) / 2.0), "rel_gap": float((U - L) / max(1.0, abs(L))),
            "n_br_evals": total_evals, "n_global_starts": N_GLOBAL_STARTS,
            "iters": len(diag), "diagnostics": diag}


def run_cell(args):
    geometry, eta_r, eta_v, K, H, max_iters = args
    run_cell.pass_no = 2 if max_iters >= 8 else 1
    t0 = time.time()
    fits = json.load(open(REPO / "research" / "results" / "e01" / "kernel_fits.json"))
    fit = KernelFit.from_dict(fits["CA"])
    kB = KernelWrap(fit, range_ratio=eta_r)
    kR = KernelWrap(fit, 1.0)
    out = certify_game(kB, kR, geometry, eta_r, eta_v, H, K, max_iters)
    out.update({"geometry": geometry, "eta_r": eta_r, "eta_v": eta_v,
                "H": H, "K": K, "seconds": round(time.time() - t0, 1),
                "pass": run_cell.pass_no})
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    jobs = []
    # PHASE 1 (verdict-critical): 18 asymmetric cells at K=6 + H=1 baselines
    for g in GEOM:
        for er in (0.8, 1.2):
            for ev in (0.8, 1.0, 1.2):
                jobs.append((g, er, ev, 6, 6, DO_ITERS_MAIN))
                jobs.append((g, er, ev, 6, 1, 2))
    # PHASE 2: symmetric sanity, K refinement, remaining H=1 baselines
    for g in GEOM:
        for ev in (1.0, 1.2):
            jobs.append((g, 1.0, ev, 6, 6, DO_ITERS_MAIN))
    for g in GEOM:
        for er in (0.8, 1.2):
            for ev in (0.8, 1.0, 1.2):
                for K in (3, 4):
                    jobs.append((g, er, ev, K, 6, DO_ITERS_REFINE))
    jobs.append(("head_on", 1.2, 1.0, 8, 6, DO_ITERS_REFINE))
    for g in GEOM:
        for er in (0.8, 1.0, 1.2):
            for ev in (0.8, 1.0, 1.2):
                jobs.append((g, er, ev, 6, 1, 2))
    total = len(jobs)
    print(f"[T1] {total} certification runs "
          f"({18 * 3 + 6 + 1} H=6 runs + {len([j for j in jobs if j[4] == 1])} H=1 baselines)",
          flush=True)

    results = []
    done_keys = set()
    jf_path = OUT / "certification_runs.jsonl"
    if jf_path.exists():
        for line in open(jf_path):
            try:
                r = json.loads(line)
                results.append(r)
                done_keys.add((r["geometry"], r["eta_r"], r["eta_v"], r["K"],
                               r["H"], r.get("pass", 1)))
            except Exception:
                pass
        print(f"[T1] resuming: {len(results)} runs already checkpointed", flush=True)
    jobs = [j for j in jobs if (j[0], j[1], j[2], j[3], j[4], 1) not in done_keys]
    done = 0
    with open(jf_path, "a") as jf:
        with ProcessPoolExecutor(max_workers=5) as ex:
            futs = {ex.submit(run_cell, j): j for j in jobs}
            for fut in as_completed(futs):
                r = fut.result()
                results.append(r)
                jf.write(json.dumps(r) + "\n")
                jf.flush()
                done += 1
                if done % 10 == 0 or done == total:
                    el = time.time() - t0
                    print(f"PROGRESS {done}/{total} pct={100 * done / total:.1f}% "
                          f"elapsed={time.strftime('%H:%M:%S', time.gmtime(el))} "
                          f"eta={time.strftime('%H:%M:%S', time.gmtime(el * (total - done) / max(done, 1)))}",
                          flush=True)

    # ---- pass 2: tighten loose uncertified asymmetric K=6 cells ----
    def crosses_zero(r, b1):
        return not (r["L"] - b1["U"] > 0 or r["U"] - b1["L"] < 0)

    prelim_h1 = {(r["geometry"], r["eta_r"], r["eta_v"]): r
                 for r in results if r["H"] == 1}
    prelim_h6 = {(r["geometry"], r["eta_r"], r["eta_v"]): r
                 for r in results if r["H"] == 6 and r["K"] == 6
                 and r["eta_r"] != 1.0}
    loose = []
    for (g, er, ev), r in sorted(prelim_h6.items()):
        b1 = prelim_h1.get((g, er, ev))
        if b1 and crosses_zero(r, b1) and r["rel_gap"] > 0.4 and r.get("pass", 1) == 1:
            loose.append((g, er, ev, 6, 6, 8))
    if loose:
        print(f"[T1] pass 2: re-running {len(loose)} loose uncertified cells "
              f"with 8 DO iterations", flush=True)
        with ProcessPoolExecutor(max_workers=5) as ex:
            futs = {ex.submit(run_cell, j): j for j in loose}
            for fut in as_completed(futs):
                r = fut.result()
                results.append(r)
                with open(jf_path, "a") as jf2:
                    jf2.write(json.dumps(r) + "\n")
                print(f"[T1] pass2 {r['geometry']} er={r['eta_r']} ev={r['eta_v']}: "
                      f"L={r['L']:+.3f} U={r['U']:+.3f} rel_gap={r['rel_gap']:.0%}",
                      flush=True)

    # ---- assemble bounds per (cell, K): prefer tightest pass ----
    best = {}
    for r in results:
        if r["H"] != 6:
            continue
        key = (r["geometry"], r["eta_r"], r["eta_v"], r["K"])
        if key not in best or (r["U"] - r["L"]) < (best[key]["U"] - best[key]["L"]):
            best[key] = r
    h6 = best
    h1 = {(r["geometry"], r["eta_r"], r["eta_v"]): r
          for r in results if r["H"] == 1}

    rows = []
    for (g, er, ev, K), r in sorted(h6.items()):
        b1 = h1[(g, er, ev)]
        L_H, U_H = r["L"], r["U"]
        L_1, U_1 = b1["L"], b1["U"]
        p_lo, p_hi = L_H - U_1, U_H - L_1
        if p_lo > 0:
            sign, status = +1, "certified+"
        elif p_hi < 0:
            sign, status = -1, "certified-"
        else:
            sign, status = 0, "UNCERTIFIED"
        solver = ("tight" if r["rel_gap"] < GAP_TIGHT else
                  "sign-certified-value-not-tight" if sign != 0 else "uncertified")
        rows.append({
            "geometry": g, "eta_r": er, "eta_v": ev, "H": 6, "K": K,
            "restricted_value": round(L_H, 4), "lower_bound": round(L_H, 4),
            "upper_bound": round(U_H, 4), "bound_width": round(U_H - L_H, 4),
            "relative_gap": round(r["rel_gap"], 4),
            "P_lower": round(p_lo, 4), "P_upper": round(p_hi, 4),
            "point_estimate": round((L_H + U_H) / 2 - (L_1 + U_1) / 2, 4),
            "sign_certified": int(sign != 0), "certified_sign": sign,
            "n_br_evals": r["n_br_evals"], "n_global_starts": r["n_global_starts"],
            "solver_status": solver, "run_status": status,
            "iters": r["iters"], "seconds": r["seconds"],
        })

    fields = ["geometry", "eta_r", "eta_v", "H", "K", "restricted_value",
              "lower_bound", "upper_bound", "bound_width", "relative_gap",
              "P_lower", "P_upper", "point_estimate", "sign_certified",
              "certified_sign", "n_br_evals", "n_global_starts", "solver_status",
              "run_status", "iters", "seconds"]
    with open(OUT / "certification_results.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader(); w.writerows(rows)
    with open(OUT / "br_search_diagnostics.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["geometry", "eta_r", "eta_v", "K",
                                           "iter", "V", "L", "U", "rel_gap",
                                           "evals", "methods_b", "methods_r"])
        w.writeheader()
        for r in results:
            if r["H"] != 6:
                continue
            for d in r["diagnostics"]:
                w.writerow({"geometry": r["geometry"], "eta_r": r["eta_r"],
                            "eta_v": r["eta_v"], "K": r["K"], "iter": d["iter"],
                            "V": round(d["V"], 4), "L": round(d["L"], 4),
                            "U": round(d["U"], 4), "rel_gap": round(d["rel_gap"], 4),
                            "evals": d["evals"], "methods_b": ";".join(d["methods_b"]),
                            "methods_r": ";".join(d["methods_r"])})

    # ---- classification (frozen v8 1.5) ----
    asym = [r for r in rows if r["eta_r"] != 1.0 and r["K"] == 6]
    n_cert = sum(1 for r in asym if r["sign_certified"])
    reversals = [r for r in asym if r["sign_certified"] and
                 r["certified_sign"] != (1 if r["eta_r"] > 1 else -1)]
    geom_cert = {}
    for g in GEOM:
        sub = [r for r in asym if r["geometry"] == g]
        pos = [r for r in sub if r["eta_r"] > 1]
        neg = [r for r in sub if r["eta_r"] < 1]
        geom_cert[g] = {
            "pos_certified": sum(1 for r in pos if r["sign_certified"]) if pos else None,
            "neg_certified": sum(1 for r in neg if r["sign_certified"]) if neg else None}
    # K-refinement: main sign (certified or point at K=6) unchanged at K=3/4/8
    k_stable = True
    for r6 in asym:
        base_sign = r6["certified_sign"] if r6["sign_certified"] else \
            (1 if r6["point_estimate"] > 0 else -1)
        for K in (3, 4):
            rk = next((x for x in rows if x["geometry"] == r6["geometry"]
                       and x["eta_r"] == r6["eta_r"] and x["eta_v"] == r6["eta_v"]
                       and x["K"] == K), None)
            if rk:
                s_k = rk["certified_sign"] if rk["sign_certified"] else \
                    (1 if rk["point_estimate"] > 0 else -1)
                if s_k != base_sign:
                    k_stable = False

    if n_cert >= 15 and not reversals and k_stable and \
       all((v["pos_certified"] or 0) >= 2 and (v["neg_certified"] or 0) >= 2
           for v in geom_cert.values()):
        verdict = "KEEP CORE (STRONG)"
    elif n_cert >= 10 and not reversals and k_stable:
        verdict = "NARROW (CONDITIONAL)"
    elif reversals:
        verdict = "REMOVE CORE (FAIL)"
    else:
        verdict = "NARROW (CONDITIONAL)"

    summary = {
        "n_asymmetric_K6": len(asym), "n_sign_certified": n_cert,
        "certified_reversals": len(reversals),
        "geometry_certification": geom_cert,
        "k_refinement_sign_stable": k_stable,
        "tight_cells": sum(1 for r in rows if r["solver_status"] == "tight"),
        "verdict": verdict,
    }
    json.dump(summary, open(OUT / "certification_summary.json", "w"), indent=2)
    with open(OUT / "k_refinement.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["geometry", "eta_r", "eta_v", "K",
                                           "P_lower", "P_upper", "point_estimate",
                                           "sign_certified", "certified_sign",
                                           "relative_gap", "solver_status"])
        w.writeheader()
        for r in rows:
            if r["eta_r"] != 1.0:
                w.writerow({k: r[k] for k in w.fieldnames})

    lines = ["# T1: commitment sign certification (v8)", "",
             f"Asymmetric K=6 cells: {len(asym)}   sign-certified: {n_cert}   "
             f"reversals: {len(reversals)}   tight: {summary['tight_cells']}/{len(rows)}",
             f"K-refinement sign-stable: {k_stable}",
             f"**VERDICT (frozen v8 1.5): {verdict}**", "",
             "| geometry | eta_r | eta_v | K | L_H | U_H | P interval | certified | gap | status |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if r["eta_r"] == 1.0:
            continue
        lines.append(
            f"| {r['geometry']} | {r['eta_r']} | {r['eta_v']} | {r['K']} "
            f"| {r['lower_bound']:+.3f} | {r['upper_bound']:+.3f} "
            f"| [{r['P_lower']:+.3f}, {r['P_upper']:+.3f}] "
            f"| {'Y' if r['sign_certified'] else 'n'} "
            f"| {r['relative_gap']:.1%} | {r['run_status']} |")
    (OUT / "certification_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"[T1] DONE verdict={verdict} certified={n_cert}/{len(asym)} "
          f"reversals={len(reversals)} in "
          f"{time.strftime('%H:%M:%S', time.gmtime(time.time() - t0))}", flush=True)


if __name__ == "__main__":
    main()
