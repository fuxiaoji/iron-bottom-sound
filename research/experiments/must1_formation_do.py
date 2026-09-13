"""MUST-1 (v7): FORMATION-LEVEL open-loop commitment solver via Double Oracle.

Research question (v7): is the commitment-range comparative static
(P_H sign = sign(eta_r - 1)) a real formation-level result, or an artifact
of the finite hand-built plan library (B8 non-convergence)?

Formation semantics (v7 section 1):
  Each player i is a rigid line-ahead formation of N=3 vessels.
  Reference state c_i(t) = (x_i, y_i), heading psi_i(t), speed v_i(t).
  Vessel k world position:  x_ik(t) = c_i(t) + R(psi_i(t)) p_ik,
  with p_ik = (0, -l*k) in the formation frame (l = 2 hex, astern spacing).
  Formation firepower aggregates over vessel pairs:
      F_i(x,t) = sum_k sum_m K(x_km(t), ...)   (shooter k of i, target m of j)

Strategy of player i: open-loop heading schedule tau_i over H turns,
piecewise-constant on K segments (K in {3,4,6}); speed fixed (first version,
v7 4.4).  Payoff is the path-integrated objective
      J(tau_B, tau_R) = sum_t gamma^t [P_B->R(t) - lambda P_R->B(t)],
with P = formation-aggregate expected hits from the E01-calibrated kernel.

Solver (v7 4.3): Double Oracle.  Restricted game M_ij = J(tau_i^B, tau_j^R)
solved as a mixed zero-sum LP; best responses are continuous multi-start
trajectory optimisations on the segment parameterisation; BR plans join the
restricted sets until the APPROXIMATE BR gap
      g = BR_B(pi_R) - BR_R(pi_B),   gate g/max(1,|V|) < 5%
(or 3 consecutive value changes < 2%) is met or the iteration cap hits.

Grid (v7 4.6): geometry {head_on, parallel, crossing} x eta_r {0.8,1,1.2}
x eta_v {0.8,1,1.2} (27 cells) + 3 legacy-anchor cells at the B7/B8
extremes (eta_r 0.75 / 1.33).  Horizon H in {1,2,3,4,6}; P_H = V_H^OL - V_1.

Commitment decision (v7 4.9): PASS-STRONG if sign(P_H)=sign(eta_r-1) in
>=80% of asymmetric cells and >=2/3 geometries; CONDITIONAL if only some
geometries; FAIL if the pattern vanishes.  Definitions are frozen — no
post-hoc tuning to rescue the effect.

Output: research/results/final_v7/{must1_jobs.jsonl, must1_results.json,
must1_aggregate.json, must1_report.md}.
"""
from __future__ import annotations

import json
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from scipy.optimize import linprog, minimize

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

from research.geometry.committed_game import KernelWrap, wrap_deg  # noqa: E402
from research.geometry.firepower_kernel import KernelFit  # noqa: E402

OUT = REPO / "research" / "results" / "final_v7"
GAMMA = 0.96
N_SHIPS = 3          # vessels per formation (line-ahead)
SPACING = 2.0        # hex between consecutive vessels (astern)
RATE_MAX = 60.0      # deg per turn, engine turn granularity
BR_STARTS = 3
BR_MAXITER = 50
DO_MAX_ITER = 8
GAP_TOL = 0.05       # g / max(1, |V|)
STAG_TOL = 0.02      # 3 consecutive value changes < 2%

GEOM = {  # (bearing of R from B, heading of B, heading of R)
    "head_on": (0.0, 0.0, 180.0),
    "parallel": (90.0, 0.0, 0.0),
    "crossing": (45.0, 0.0, 180.0),
}

_OFFSETS = np.array([[0.0, -SPACING * k] for k in range(N_SHIPS)])


def _rot(psi_deg: float, P: np.ndarray) -> np.ndarray:
    c, s = math.cos(math.radians(psi_deg)), math.sin(math.radians(psi_deg))
    return P @ np.array([[c, -s], [s, c]]).T


def _aspect(d: float) -> str:
    a = abs(wrap_deg(d))
    return "bow_stern" if (a <= 30.0 or a >= 150.0) else "broadside"


class FormationGame:
    """Open-loop formation game; payoff J(tau_B, tau_R) per v7 section 1."""

    def __init__(self, kB: KernelWrap, kR: KernelWrap, r0: float = 16.0,
                 bearing0_deg: float = 0.0, hB0_deg: float = 0.0,
                 hR0_deg: float = 180.0, vB: float = 6.0, vR: float = 6.0,
                 H: int = 6):
        self.kB, self.kR = kB, kR
        self.H = H
        br = math.radians(bearing0_deg)
        self.xR0, self.yR0 = r0 * math.cos(br), r0 * math.sin(br)
        self.hB0, self.hR0 = hB0_deg, hR0_deg
        self.vB, self.vR = vB, vR

    def payoff(self, segB: np.ndarray, segR: np.ndarray, tps: int) -> float:
        """J for two segment-wise plans; tps = turns per segment."""
        planB = np.repeat(np.asarray(segB, float) / tps, tps)[:self.H]
        planR = np.repeat(np.asarray(segR, float) / tps, tps)[:self.H]
        xB = yB = 0.0
        xR, yR = self.xR0, self.yR0
        hB, hR = self.hB0, self.hR0
        cum = 0.0
        disc = 1.0
        for t in range(self.H):
            offB, offR = _rot(hB, _OFFSETS), _rot(hR, _OFFSETS)
            # vessel positions x_ik = c_i + R(psi_i) p_ik (rigid formation)
            J = 0.0
            for kb in range(N_SHIPS):
                xb = xB + offB[kb, 0]
                yb = yB + offB[kb, 1]
                for kr in range(N_SHIPS):
                    dx = (xR + offR[kr, 0]) - xb
                    dy = (yR + offR[kr, 1]) - yb
                    r = max(math.hypot(dx, dy), 0.5)
                    brg = math.degrees(math.atan2(dy, dx))
                    dB = float(wrap_deg(brg - hB))            # off B's bow
                    dR = float(wrap_deg(brg + 180.0 - hR))    # off R's bow
                    J += (self.kB.fire(r, dB, 6, _aspect(dR))
                          - self.kR.fire(r, dR, 6, _aspect(dB)))
            cum += disc * J
            disc *= GAMMA
            hB = float(wrap_deg(hB + planB[t]))
            hR = float(wrap_deg(hR + planR[t]))
            xB += self.vB * math.cos(math.radians(hB))
            yB += self.vB * math.sin(math.radians(hB))
            xR += self.vR * math.cos(math.radians(hR))
            yR += self.vR * math.sin(math.radians(hR))
        return cum


def seg_setup(K: int, H: int) -> tuple[int, int]:
    """(n_segments, turns_per_segment) for K requested segments over H turns."""
    tps = max(1, round(H / K))
    return math.ceil(H / tps), tps


def seg_bounds(n_seg: int, tps: int) -> list[tuple[float, float]]:
    lim = RATE_MAX * tps
    return [(-lim, lim)] * n_seg


def seed_segments(H: int, tps: int) -> list[np.ndarray]:
    """Legacy L11 turn family, segment-averaged (3-turn turn then straight)."""
    seeds = []
    for turn in (0, 30, 60, 90, 120, 180, -30, -60, -90, -120, -180):
        rate = [turn / 3.0] * min(3, H) + [0.0] * max(0, H - 3)
        segs = [float(np.mean(rate[s * tps:(s + 1) * tps]))
                for s in range(math.ceil(H / tps))]
        seeds.append(np.array(segs))
    return seeds


def _expected_J(seg: np.ndarray, game: FormationGame, opp: list[np.ndarray],
                w: np.ndarray, tps: int, b_first: bool) -> float:
    """Expected J of candidate plan `seg` against the opponent mix.

    b_first=True  -> seg is B's plan:  E = sum_k w_k * J(seg, opp_k)
    b_first=False -> seg is R's plan:  E = sum_k w_k * J(opp_k, seg)
    """
    if b_first:
        return sum(wi * game.payoff(seg, o, tps) for wi, o in zip(w, opp))
    return sum(wi * game.payoff(o, seg, tps) for wi, o in zip(w, opp))


def best_response(game: FormationGame, opp: list[np.ndarray], w: np.ndarray,
                  maximize: bool, K: int,
                  own_plans: list[np.ndarray]) -> tuple[np.ndarray, float]:
    """Multi-start continuous BR (v7 4.4).  The player's own current restricted
    plans are included as starts (the best of them is a lower bound on the BR
    value, which keeps the approximate BR gap >= 0 by construction)."""
    n_seg, tps = seg_setup(K, game.H)
    bounds = seg_bounds(n_seg, tps)
    rng = np.random.default_rng(12345 + game.H)
    own_vals = [_expected_J(p, game, opp, w, tps, maximize) for p in own_plans]
    own_best = own_plans[int(np.argmax(own_vals) if maximize
                             else np.argmin(own_vals))]
    starts = [np.asarray(own_best, float), np.zeros(n_seg),
              rng.uniform(-RATE_MAX * tps, RATE_MAX * tps, n_seg)]
    best_x, best_E = None, None
    # explicit start evaluation guards against L-BFGS-B line-search
    # anomalies on the piecewise-linear kernel: the returned BR value is
    # never worse than the best starting point (>= V for B, <= V for R)
    for x0 in starts:
        E0 = _expected_J(x0, game, opp, w, tps, maximize)
        if maximize:
            if best_E is None or E0 > best_E:
                best_x, best_E = np.asarray(x0, float), E0
        else:
            if best_E is None or E0 < best_E:
                best_x, best_E = np.asarray(x0, float), E0
    for x0 in starts:
        if maximize:   # B: maximise E[J] -> minimise -E[J]
            res = minimize(lambda s: -_expected_J(s, game, opp, w, tps, True),
                           x0, method="L-BFGS-B", bounds=bounds,
                           options={"maxiter": BR_MAXITER})
            E = -res.fun
            if best_E is None or E > best_E:
                best_x, best_E = res.x, E
        else:          # R: minimise E[J]
            res = minimize(lambda s: _expected_J(s, game, opp, w, tps, False),
                           x0, method="L-BFGS-B", bounds=bounds,
                           options={"maxiter": BR_MAXITER})
            E = res.fun
            if best_E is None or E < best_E:
                best_x, best_E = res.x, E
    return np.asarray(best_x, float), float(best_E)


def restricted_lp(pay: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
    """Mixed equilibrium of the restricted zero-sum game (B maximises)."""
    m, n = pay.shape
    c = np.zeros(m + 1); c[-1] = -1.0
    A_ub = np.zeros((n, m + 1)); A_ub[:, :m] = -pay.T; A_ub[:, m] = 1.0
    A_eq = np.zeros((1, m + 1)); A_eq[0, :m] = 1.0   # sum x = 1 (v excluded)
    res_B = linprog(c, A_ub=A_ub, b_ub=np.zeros(n),
                    A_eq=A_eq, b_eq=[1.0],
                    bounds=[(0, None)] * m + [(None, None)])
    c_R = np.zeros(n + 1); c_R[-1] = 1.0
    A_ub_R = np.zeros((m, n + 1)); A_ub_R[:, :n] = pay; A_ub_R[:, n] = -1.0
    A_eq_R = np.zeros((1, n + 1)); A_eq_R[0, :n] = 1.0  # sum y = 1
    res_R = linprog(c_R, A_ub=A_ub_R, b_ub=np.zeros(m),
                    A_eq=A_eq_R, b_eq=[1.0],
                    bounds=[(0, None)] * n + [(None, None)])
    ok = res_B.success and res_R.success and res_B.x is not None and res_R.x is not None
    if not ok:
        bi = int(np.argmax(pay.min(axis=1)))
        xB = np.zeros(m); xB[bi] = 1.0
        rj = int(np.argmin(pay.max(axis=0)))
        xR = np.zeros(n); xR[rj] = 1.0
        return float(pay[bi].min()), xB, xR
    v = (res_B.x[-1] + res_R.x[-1]) / 2.0
    return float(v), res_B.x[:m], res_R.x[:n]


def double_oracle(game: FormationGame, seeds: list[np.ndarray], K: int) -> dict:
    plansB, plansR = list(seeds), [s.copy() for s in seeds]
    _, tps = seg_setup(K, game.H)
    v, gap = np.nan, np.nan
    hist: list[float] = []
    converged = False
    for it in range(DO_MAX_ITER):
        pay = np.array([[game.payoff(a, b, tps) for b in plansR]
                        for a in plansB])
        v, xB, xR = restricted_lp(pay)
        hist.append(v)
        planBR_B, valBR_B = best_response(game, plansR, xR, True, K, plansB)
        planBR_R, valBR_R = best_response(game, plansB, xB, False, K, plansR)
        # approximate BR gap (v7 4.8): BR_B(pi_R) - BR_R(pi_B) >= 0
        gap = valBR_B - valBR_R
        norm = gap / max(1.0, abs(v))
        stag = (len(hist) >= 4 and all(
            abs(hist[-k] - hist[-k - 1]) / max(1.0, abs(hist[-k - 1])) < STAG_TOL
            for k in (1, 2, 3)))
        if 0.0 <= norm < GAP_TOL or stag:
            converged = True
            break
        plansB.append(planBR_B)
        plansR.append(planBR_R)
    return {"V": float(v), "gap": float(gap), "iters": it + 1,
            "converged": converged, "value_history": hist,
            "gap_norm": float(gap / max(1.0, abs(v))),
            "n_plans": [len(plansB), len(plansR)]}


def run_job(args) -> dict:
    geometry, eta_r, eta_v, H, K, tag = args
    t0 = time.time()
    fits = json.load(open(REPO / "research" / "results" / "e01" / "kernel_fits.json"))
    fit = KernelFit.from_dict(fits["CA"])
    kB = KernelWrap(fit, range_ratio=eta_r)
    kR = KernelWrap(fit, 1.0)
    brg, hB, hR = GEOM[geometry]
    game = FormationGame(kB, kR, r0=16.0, bearing0_deg=brg, hB0_deg=hB,
                         hR0_deg=hR, vB=6.0 * eta_v, vR=6.0, H=H)
    _, tps = seg_setup(K, H)
    out = double_oracle(game, seed_segments(H, tps), K)
    out.update({"geometry": geometry, "eta_r": eta_r, "eta_v": eta_v,
                "H": H, "K": K, "tag": tag,
                "seconds": round(time.time() - t0, 1)})
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    jobs = []
    for g in GEOM:
        for eta_r in (0.8, 1.0, 1.2):
            for eta_v in (0.8, 1.0, 1.2):
                for H in (1, 2, 3, 4, 6):
                    jobs.append((g, eta_r, eta_v, H, 6, "grid"))
    # legacy anchors (B7/B8 extremes): max/min effect + unstable-asymmetry cell
    jobs += [("head_on", 1.33, 1.0, H, 6, "legacy_max") for H in (1, 4, 6)]
    jobs += [("parallel", 0.75, 1.0, H, 6, "legacy_min") for H in (1, 4, 6)]
    jobs += [("parallel", 1.2, 0.8, H, 6, "legacy_unstable") for H in (1, 4, 6)]
    # K refinement on one representative asymmetric cell (v7 4.8):
    # only (K, H) with turns-per-segment >= 2 differ from the K=6 grid runs
    jobs += [("head_on", 1.2, 1.0, 6, 3, "kref"),
             ("head_on", 1.2, 1.0, 6, 2, "kref"),
             ("head_on", 1.2, 1.0, 4, 2, "kref")]
    total = len(jobs)
    print(f"[MUST1-F] {total} jobs (27 grid cells + 3 legacy cells + K-refinement, "
          f"H in 1..6)", flush=True)

    results: list[dict] = []
    done = 0
    with open(OUT / "must1_jobs.jsonl", "a") as jf:
        with ProcessPoolExecutor(max_workers=5) as ex:
            futs = {ex.submit(run_job, j): j for j in jobs}
            for fut in as_completed(futs):
                row = fut.result()
                results.append(row)
                jf.write(json.dumps(row) + "\n")
                jf.flush()
                done += 1
                if done % 10 == 0 or done == total:
                    el = time.time() - t0
                    eta = el * (total - done) / max(done, 1)
                    print(f"PROGRESS {done}/{total} "
                          f"pct={100.0 * done / total:.1f}% "
                          f"elapsed={time.strftime('%H:%M:%S', time.gmtime(el))} "
                          f"eta={time.strftime('%H:%M:%S', time.gmtime(eta))}",
                          flush=True)

    json.dump(results, open(OUT / "must1_results.json", "w"))

    # ---- aggregate: V_H per cell, P_H, commitment decision (frozen rules) ----
    by_cell: dict[tuple, dict] = {}
    for r in results:
        if r["tag"] != "grid":
            continue
        by_cell.setdefault((r["geometry"], r["eta_r"], r["eta_v"]), {})[r["H"]] = r
    rows = []
    for (g, er, ev), hs in sorted(by_cell.items()):
        v1 = hs.get(1, {}).get("V", np.nan)
        for H in (2, 3, 4, 6):
            r = hs.get(H)
            if r is None or v1 is None or (isinstance(v1, float) and math.isnan(v1)):
                continue
            rows.append({"geometry": g, "eta_r": er, "eta_v": ev, "H": H,
                         "V_H": r["V"], "P_H": r["V"] - v1,
                         "gap_norm": r["gap"] / max(1.0, abs(r["V"])),
                         "converged": r["converged"]})

    conv_rate = float(np.mean([r["converged"] for r in results])) if results else 0.0
    asym = [r for r in rows if r["eta_r"] != 1.0 and r["H"] == 6]
    sign_ok = [r for r in asym
               if (r["P_H"] > 0) == (r["eta_r"] > 1) and abs(r["P_H"]) > 0.05]
    geom_frac = {g: (len([r for r in sign_ok if r["geometry"] == g]) /
                     max(len([r for r in asym if r["geometry"] == g]), 1))
                 for g in GEOM}
    n_geom_ok = sum(1 for f in geom_frac.values() if f >= 0.5)
    frac = len(sign_ok) / max(len(asym), 1)
    if frac >= 0.8 and n_geom_ok >= 2:
        verdict = "PASS-STRONG"
    elif n_geom_ok >= 1 and frac >= 0.5:
        verdict = "CONDITIONAL"
    else:
        verdict = "FAIL"

    kref = [r for r in results if r["tag"] == "kref"]
    base = {(r["H"]): r for r in results if r["tag"] == "grid"
            and r["geometry"] == "head_on" and r["eta_r"] == 1.2
            and r["eta_v"] == 1.0}
    kref_stable = all(
        abs(r["V"] - base[r["H"]]["V"]) <= max(0.15, 0.1 * abs(base[r["H"]]["V"]))
        for r in kref if r["H"] in base)

    summary = {
        "n_jobs": total, "convergence_rate": conv_rate,
        "asymmetric_H6_cells": len(asym),
        "sign_consistent": len(sign_ok), "sign_fraction": frac,
        "geometry_pass_fraction": geom_frac,
        "k_refinement_stable": kref_stable,
        "verdict": verdict,
    }
    json.dump({"summary": summary, "rows": rows},
              open(OUT / "must1_aggregate.json", "w"), indent=2)

    lines = ["# MUST-1 (v7): formation-level open-loop commitment solver", "",
             f"Jobs: {total}   convergence (gap/stag gate): {conv_rate:.0%}",
             f"Asymmetric H=6 cells: {len(asym)}   sign(P_H)=sign(eta_r-1): "
             f"{len(sign_ok)} ({frac:.0%})",
             f"Geometry pass fraction: {geom_frac}",
             f"K-refinement stable: {kref_stable}",
             f"**VERDICT: {verdict}**", "",
             "| geometry | eta_r | eta_v | H | V_H | P_H | gap/V | conv |",
             "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['geometry']} | {r['eta_r']} | {r['eta_v']} "
                     f"| {r['H']} | {r['V_H']:+.3f} | {r['P_H']:+.3f} "
                     f"| {r['gap_norm']:.1%} | {'Y' if r['converged'] else 'N'} |")
    (OUT / "must1_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"[MUST1-F] DONE verdict={verdict} conv={conv_rate:.0%} "
          f"sign={frac:.0%} in "
          f"{time.strftime('%H:%M:%S', time.gmtime(time.time() - t0))}",
          flush=True)


if __name__ == "__main__":
    main()
