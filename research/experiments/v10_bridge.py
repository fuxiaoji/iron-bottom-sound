"""v10 Phase 2: rigid vs leader-follower bridge experiment (plan sections 10-18).

Question: how much does the rigid formation representation distort the core
comparative statics?  Same leader control plans are fed to both formations and
we compare geometry, formation shape, the directional field, the integrated
payoff and the commitment value P_6.

Cells (pre-specified, plan sections 11-12; no post-hoc selection):
    6 core   : geometry in {head_on, parallel, crossing} x eta_r in {0.8, 1.2},
               eta_v = 1.0
    3 stress : (crossing, 1.2, 1.2), (crossing, 0.8, 0.8), and
               (crossing, 1.0, 1.2) -- the tightest-turn cell of the v9 grid

Metrics per cell:
    J_rigid, J_leader_follower, delta_J
    P6_rigid, P6_leader_follower   (same discretised plans, same definitions)
    sign_match
    max_shape_error  max_{k,t} |x_k^LF - x_k^rigid|
    heading_dispersion  max_k psi_k - min_k psi_k  (max over t)
    field_deviation    normalised L1 difference of the formation fire fields
    kappa_L_F          chi_F = max_t |kappa(t)| * L_F   (plan section 17)

Outputs: research/final_v10/bridge/{bridge_cells.csv, bridge_summary.json,
bridge_report.md, rigid_vs_lf_exact.csv}
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

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

from research.geometry.committed_game import wrap_deg  # noqa: E402
from research.formation.path_following import (  # noqa: E402
    DEFAULT_NSUB, LeaderPath, batch_payoff_lf, line_ahead_offsets,
    make_lf_game, vessel_states_rigid_line_ahead,
)

OUT = REPO / "research" / "final_v10" / "bridge"
KD = json.load(open(REPO / "research" / "results" / "e01" / "kernel_fits.json"))["CA"]
H = 6
GRID5 = (-1.0, -0.5, 0.0, 0.5, 1.0)
OMEGA_MAX = 60.0

CORE = [(g, er, 1.0) for g in ("head_on", "parallel", "crossing")
        for er in (0.8, 1.2)]
STRESS = [("crossing", 1.2, 1.2), ("crossing", 0.8, 0.8), ("crossing", 1.0, 1.2)]
CELLS = CORE + STRESS


def enumerate_plans(levels=GRID5, h=H):
    import itertools
    import itertools
    return np.array(list(itertools.product(levels, repeat=h))) * OMEGA_MAX


def curvature_metrics(game, plans: np.ndarray) -> tuple[float, float]:
    """max |kappa| * L_F over the plan set (kappa in 1/hex, L_F in hex)."""
    L_F = float(line_ahead_offsets(game.spacing, game.n_ships)[-1])
    worst = 0.0
    for seq in plans:
        p = LeaderPath.from_sequence(game, "B", seq, H, game.n_sub)
        d = np.diff(p.stations, axis=0)
        seg = np.hypot(d[:, 0], d[:, 1])
        ang = np.arctan2(d[:, 1], d[:, 0])
        turn = np.abs(np.diff(ang))
        turn = (turn + math.pi) % (2 * math.pi) - math.pi
        kappa = np.abs(turn) / np.maximum(seg[1:], 1e-9)   # 1/hex
        worst = max(worst, float(kappa.max()) * L_F if len(kappa) else 0.0)
    return worst, L_F


def field_deviation(game, seqB, seqR, n_grid: int = 90) -> float:
    """Normalised L1 difference between the rigid and LF formation fields."""
    xs = np.linspace(-30, 40, n_grid)
    ys = np.linspace(-20, 45, n_grid)
    XX, YY = np.meshgrid(xs, ys)
    lf = make_lf_game(KD, None, 1.0, 1.0, H) if False else game
    p = LeaderPath.from_sequence(game, "B", seqB, H, game.n_sub)
    diff_num = 0.0
    base_num = 0.0
    for t in range(H):
        posLF, psiLF = p.vessel_states(t, game.offsets)
        posRG, psiRG = vessel_states_rigid_line_ahead(game, seqB, "B", t)
        FLF = np.zeros_like(XX)
        FRG = np.zeros_like(XX)
        for k in range(game.n_ships):
            for (pos, psi, acc) in ((posLF, psiLF, FLF), (posRG, psiRG, FRG)):
                dx = XX - pos[k, 0]
                dy = YY - pos[k, 1]
                r = np.maximum(np.hypot(dx, dy), 0.5)
                d = np.degrees(np.arctan2(dy, dx)) - psi[k]
                a = np.abs((d + 180.0) % 360.0 - 180.0)
                asp = np.where((a <= 30.0) | (a >= 150.0), "bow_stern", "broadside")
                acc += _field_vec(game.kB, r, d, asp)
        diff_num += float(np.abs(FLF - FRG).sum())
        base_num += float(np.abs(FRG).sum())
    return diff_num / max(base_num, 1e-9)


def _field_vec(kw, r, delta, aspect):
    from research.experiments.t1_exact_discrete_certification import fire_vec
    return fire_vec(kw, r, delta, aspect)


def batch_payoff_rigid_la(game, cands: np.ndarray, opp: np.ndarray,
                          blue: bool) -> np.ndarray:
    """Vectorised rigid line-ahead payoff (candidates vs one fixed opponent)."""
    from research.experiments.t1_exact_discrete_certification import fire_vec
    n, H = cands.shape
    seqB = cands if blue else np.broadcast_to(opp, (n, H))
    seqR = np.broadcast_to(opp, (n, H)) if blue else cands
    vB, vR = game.vB, game.vR
    hB0, hR0 = game.hB0_deg, game.hR0_deg
    xR0, yR0 = game.xR0, game.yR0
    hB = np.full(n, hB0); hR = np.full(n, hR0)
    xB = np.zeros(n); yB = np.zeros(n)
    xR = np.full(n, xR0); yR = np.full(n, yR0)
    offs = line_ahead_offsets(game.spacing, game.n_ships)
    cum = np.zeros(n); disc = 1.0
    for t in range(H):
        # vessel positions: leader minus ell * heading unit vector
        cB = np.stack([xB, yB], axis=1); cR = np.stack([xR, yR], axis=1)
        uB = np.stack([np.cos(np.radians(hB)), np.sin(np.radians(hB))], axis=1)
        uR = np.stack([np.cos(np.radians(hR)), np.sin(np.radians(hR))], axis=1)
        posB = cB[:, None, :] - offs[None, :, None] * uB[:, None, :]
        posR = cR[:, None, :] - offs[None, :, None] * uR[:, None, :]
        J = np.zeros(n)
        K = game.n_ships
        for kb in range(K):
            for kr in range(K):
                dx = posR[:, kr, 0] - posB[:, kb, 0]
                dy = posR[:, kr, 1] - posB[:, kb, 1]
                r = np.maximum(np.hypot(dx, dy), 0.5)
                brg = np.degrees(np.arctan2(dy, dx))
                dB = wrap_deg(brg - hB); dR = wrap_deg(brg + 180.0 - hR)
                aspR = np.where((np.abs(dR) <= 30.0) | (np.abs(dR) >= 150.0),
                                "bow_stern", "broadside")
                aspB = np.where((np.abs(dB) <= 30.0) | (np.abs(dB) >= 150.0),
                                "bow_stern", "broadside")
                J += fire_vec(game.kB, r, dB, aspR) - fire_vec(game.kR, r, dR, aspB)
        cum += disc * J
        disc *= game.gamma
        hB = wrap_deg(hB + seqB[:, t]); hR = wrap_deg(hR + seqR[:, t])
        xB = xB + vB * np.cos(np.radians(hB)); yB = yB + vB * np.sin(np.radians(hB))
        xR = xR + vR * np.cos(np.radians(hR)); yR = yR + vR * np.sin(np.radians(hR))
    return cum


def _do_bounds(game, batch_fn, max_iters: int = 12) -> dict:
    """Double Oracle with exhaustive full-space bounds (v9 machinery, pluggable
    payoff).  Returns the validated interval for one representation."""
    import itertools
    seqs = np.array(list(itertools.product(GRID5, repeat=H))) * OMEGA_MAX
    n = len(seqs)
    seed_actions = (0.0, 0.5, -0.5, 1.0, -1.0)
    idx = []
    for a in seed_actions:
        sig = np.full(H, a * OMEGA_MAX)
        idx.append(int(np.argmin(np.abs(seqs - sig).sum(axis=1))))
    idx += [int(np.argmin(np.abs(seqs - np.concatenate(
        [np.full(H // 2, a * OMEGA_MAX), np.full(H - H // 2, b * OMEGA_MAX)])
        ).sum(axis=1))) for a, b in ((1.0, -1.0), (-1.0, 1.0))]
    X = list(dict.fromkeys(idx))
    Y = list(dict.fromkeys(idx))
    cols: dict[int, np.ndarray] = {}
    rows: dict[int, np.ndarray] = {}
    LB = UB = V = float("nan")

    def col(j):
        if j not in cols:
            cols[j] = batch_fn(game, seqs, seqs[j], True)
        return cols[j]

    def row(i):
        if i not in rows:
            rows[i] = batch_fn(game, seqs, seqs[i], False)
        return rows[i]

    for it in range(max_iters):
        pay = np.zeros((len(X), len(Y)))
        for b, j in enumerate(Y):
            pay[:, b] = col(j)[X]
        V, xr, yr = _lp(pay)
        xf = np.zeros(n); xf[X] = xr
        yf = np.zeros(n); yf[Y] = yr
        totR = np.zeros(n)
        for i in np.where(xf > 0)[0]:
            totR += xf[i] * row(int(i))
        LB = float(totR.min())
        jmin = int(np.argmin(totR))
        totB = np.zeros(n)
        for j in np.where(yf > 0)[0]:
            totB += yf[j] * col(int(j))
        UB = float(totB.max())
        imax = int(np.argmax(totB))
        if (UB - LB) / max(1.0, abs(V)) < 0.05:
            break
        newB = imax not in X
        newR = jmin not in Y
        if newB:
            X.append(imax)
        if newR:
            Y.append(jmin)
        if not newB and not newR:
            break
    return {"V": float(V), "LB": LB, "UB": UB, "iters": it + 1,
            "rel_gap": (UB - LB) / max(1.0, abs(V))}


def _do_h1(game, batch_fn) -> float:
    """Exact H=1 value on the complete |A|x|A| action grid."""
    import itertools
    seqs = np.array(list(itertools.product(GRID5, repeat=1))) * OMEGA_MAX
    n = len(seqs)
    pay = np.zeros((n, n))
    for j in range(n):
        pay[:, j] = batch_fn(game, seqs, seqs[j], True)[:n] if False else \
            batch_fn(game, seqs, seqs[j], True)
    V, _, _ = _lp(pay)
    return float(V)


def run_cell(args):
    geometry, eta_r, eta_v = args
    t0 = time.time()
    plans = enumerate_plans()
    gLF = make_lf_game(KD, geometry, eta_r, eta_v, H,
                       formation_mode="leader_follower")
    gRG = make_lf_game(KD, geometry, eta_r, eta_v, H,
                       formation_mode="rigid_line_ahead")

    r6_lf = _do_bounds(gLF, batch_payoff_lf)
    r6_rg = _do_bounds(gRG, batch_payoff_rigid_la)
    V1_lf = _do_h1(gLF, batch_payoff_lf)
    V1_rg = _do_h1(gRG, batch_payoff_rigid_la)
    P6_lf = r6_lf["V"] - V1_lf
    P6_rg = r6_rg["V"] - V1_rg

    chi, L_F = curvature_metrics(gLF, plans)
    max_shape = 0.0
    max_disp = 0.0
    for seq in plans[::7]:
        p = LeaderPath.from_sequence(gLF, "B", seq, H, gLF.n_sub)
        for t in range(H):
            posLF, psiLF = p.vessel_states(t, gLF.offsets)
            posRG, psiRG = vessel_states_rigid_line_ahead(gLF, seq, "B", t)
            max_shape = max(max_shape, float(np.hypot(*(posLF - posRG).T).max()))
            max_disp = max(max_disp, float(np.ptp(np.unwrap(np.radians(psiLF))))*180.0/math.pi)
    fdev = field_deviation(gLF, plans[60], plans[0])
    J_lf = float(gLF.payoff(plans[60], plans[0], 1))
    J_rg = float(gRG.payoff(plans[60], plans[0], 1))

    return {"cell_id": f"{geometry}|{eta_r}|{eta_v}",
            "geometry": geometry, "eta_r": eta_r, "eta_v": eta_v,
            "max_curvature": round(chi / max(L_F, 1e-9), 6),
            "formation_length": L_F, "kappa_L_F": round(chi, 4),
            "J_rigid": round(J_rg, 4), "J_leader_follower": round(J_lf, 4),
            "delta_J": round(J_lf - J_rg, 4),
            "P6_rigid": round(P6_rg, 4), "P6_leader_follower": round(P6_lf, 4),
            "LB6_lf": round(r6_lf["LB"], 4), "UB6_lf": round(r6_lf["UB"], 4),
            "LB6_rigid": round(r6_rg["LB"], 4), "UB6_rigid": round(r6_rg["UB"], 4),
            "P6_sign_certified_lf": int(not (r6_lf["LB"] - V1_lf <= 0 <= r6_lf["UB"] - V1_lf)),
            "sign_match": int(np.sign(P6_lf) == np.sign(P6_rg)),
            "field_deviation": round(fdev, 4),
            "max_shape_error": round(max_shape, 4),
            "heading_dispersion": round(max_disp, 2),
            "seconds": round(time.time() - t0, 1)}


def _lp(pay: np.ndarray):
    from scipy.optimize import linprog
    m, n = pay.shape
    c = np.zeros(m + 1); c[-1] = -1.0
    A_ub = np.zeros((n, m + 1)); A_ub[:, :m] = -pay.T; A_ub[:, m] = 1.0
    A_eq = np.zeros((1, m + 1)); A_eq[0, :m] = 1.0
    rB = linprog(c, A_ub=A_ub, b_ub=np.zeros(n), A_eq=A_eq, b_eq=[1.0],
                 bounds=[(0, None)] * m + [(None, None)])
    cR = np.zeros(n + 1); cR[-1] = 1.0
    A_ubR = np.zeros((m, n + 1)); A_ubR[:, :n] = pay; A_ubR[:, n] = -1.0
    A_eqR = np.zeros((1, n + 1)); A_eqR[0, :n] = 1.0
    rR = linprog(cR, A_ub=A_ubR, b_ub=np.zeros(m), A_eq=A_eqR, b_eq=[1.0],
                 bounds=[(0, None)] * n + [(None, None)])
    x = np.clip(rB.x[:m], 0, None); x /= x.sum()
    y = np.clip(rR.x[:n], 0, None); y /= y.sum()
    return float((rB.x[-1] + rR.x[-1]) / 2), x, y


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    print(f"[v10-bridge] {len(CELLS)} cells (6 core + 3 pre-specified stress)",
          flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(run_cell, c): c for c in CELLS}
        for fut in as_completed(futs):
            r = fut.result()
            rows.append(r)
            print(f"  {r['cell_id']:24s} P6_rigid={r['P6_rigid']:+.3f} "
                  f"P6_LF={r['P6_leader_follower']:+.3f} "
                  f"match={r['sign_match']} kL_F={r['kappa_L_F']:.3f} "
                  f"shape_err={r['max_shape_error']:.2f} "
                  f"field={r['field_deviation']:.1%} ({r['seconds']}s)", flush=True)

    fields = list(rows[0].keys())
    with open(OUT / "bridge_cells.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader(); w.writerows(rows)

    n_match = sum(r["sign_match"] for r in rows)
    # rank agreement across cells
    from scipy.stats import kendalltau, spearmanr
    pr = [r["P6_rigid"] for r in rows]
    pl = [r["P6_leader_follower"] for r in rows]
    tau = float(kendalltau(pr, pl).statistic)
    rho = float(spearmanr(pr, pl).statistic)
    dist = [abs(l - r) / max(1.0, abs(r)) for l, r in zip(pl, pr)]
    # does the error grow with kappa L_F?
    chi = [r["kappa_L_F"] for r in rows]
    err = [abs(r["delta_J"]) for r in rows]
    err_rho = float(spearmanr(chi, err).statistic) if len(set(chi)) > 1 else float("nan")

    verdict = ("ROBUST" if n_match >= 8 else
               "MODERATE" if n_match >= 6 else "NON-ROBUST")
    summary = {"n_cells": len(rows), "sign_match": n_match,
               "sign_match_fraction": n_match / len(rows),
               "kendall_tau": tau, "spearman_rho": rho,
               "median_magnitude_distortion": float(np.median(dist)),
               "kappa_LF_vs_absdeltaJ_spearman": err_rho,
               "verdict": verdict, "wall_time_s": round(time.time() - t0, 1)}
    json.dump(summary, open(OUT / "bridge_summary.json", "w"), indent=2)
    with open(OUT / "rigid_vs_lf_exact.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["cell_id", "geometry", "eta_r", "eta_v",
                                           "P6_rigid", "P6_leader_follower",
                                           "sign_match", "kappa_L_F"])
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in w.fieldnames})

    lines = ["# v10 Phase 2: rigid vs leader-follower bridge", "",
             f"Cells: {len(rows)} (6 pre-specified core + 3 pre-specified stress)",
             f"Commitment sign agreement: **{n_match}/{len(rows)}**",
             f"Kendall tau = {tau:.3f}, Spearman rho = {rho:.3f}",
             f"Median magnitude distortion: {np.median(dist):.1%}",
             f"kappa*L_F vs |delta J| Spearman: {err_rho:.3f}",
             f"**VERDICT: {verdict}**", "",
             "| cell | P6 rigid | P6 LF | match | kappa L_F | shape err | heading disp | field dev |",
             "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['cell_id']} | {r['P6_rigid']:+.3f} | "
                     f"{r['P6_leader_follower']:+.3f} | "
                     f"{'yes' if r['sign_match'] else 'NO'} | {r['kappa_L_F']:.3f} | "
                     f"{r['max_shape_error']:.2f} | {r['heading_dispersion']:.1f} | "
                     f"{r['field_deviation']:.1%} |")
    (OUT / "bridge_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"[v10-bridge] DONE {n_match}/{len(rows)} sign match, verdict={verdict}, "
          f"tau={tau:.3f} in {time.strftime('%H:%M:%S', time.gmtime(time.time() - t0))}",
          flush=True)


if __name__ == "__main__":
    main()
