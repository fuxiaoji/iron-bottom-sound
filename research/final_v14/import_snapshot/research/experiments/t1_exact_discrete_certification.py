"""T1 (v9): EXACT discretized open-loop commitment certification.

Why a new script (v9 sections 0, 6): the v8 certification had two
mathematical defects.

  Defect A: the restricted-game value was reported as a full-game lower
  bound.  With BOTH strategy sets restricted, V_R = max_{x in X_R}
  min_{y in Y_R} f(x,y) carries no one-sided bound on V*: restricting the
  maximiser lowers it, restricting the minimiser raises it.

  Defect B: the best-response search truncated the opponent mixture
  (top-k / probability threshold), so it optimised against a *different*
  game than the one being certified.

This script works inside an explicitly frozen, finite open-loop game and
computes bounds that are valid there.

Frozen action grids (normalised turn rate a = omega / omega_max, with
omega_max = 60 deg/turn, the engine's turn granularity; the mapping is
frozen BEFORE any run):
    Grid-5:  a in {-1, -1/2, 0, +1/2, +1}          -> |A_5|^H, H=6: 15 625
    Grid-7:  a in {-1, -2/3, -1/3, 0, +1/3, +2/3, +1} -> 7^6: 117 649
A pure open-loop strategy is a full sequence tau = (u_0..u_{H-1}) of
per-turn turn rates; the payoff J(tau_B, tau_R) is the formation-aggregate
path-integrated exposure of the same 3-vessel line-ahead game used
throughout the paper.

Bounds (v9 section 4), with Blue the maximiser:
    LB = min_{tau_R in Omega_m} E_{tau_B ~ x_R} J(tau_B, tau_R)   (<= V*)
    UB = max_{tau_B in Omega_m} E_{tau_R ~ y_R} J(tau_B, tau_R)   (>= V*)
Both are EXHAUSTIVE over the full finite space (itertools.product, no
sampling) and use the COMPLETE restricted mixture (no truncation, no
top-k, no renormalisation).  Double Oracle adds the exact argmin/argmax
sequences until (UB-LB)/max(1,|V_R|) < 0.05 or the iteration cap is hit.

Commitment interval (v9 section 10):  P_H in [LB_H - UB_1, UB_H - LB_1],
positive-certified if LB_H - UB_1 > 0, negative-certified if
UB_H - LB_1 < 0, else UNCERTIFIED.  H=1 is solved exactly on the complete
|A_m| x |A_m| matrix, so LB_1 = UB_1 = V*_1 to LP tolerance.

Incremental payoff caching keeps the exhaustive work affordable: columns
of the (|Omega_m| x |support|) matrix are computed once per newly added
opponent sequence and reused across Double Oracle iterations.

Outputs (v9 section 6): research/final_v9/commitment_exact/
    exact_grid5_results.csv, exact_grid7_results.csv,
    exact_certification_summary.json, exact_certification_report.md,
    double_oracle_trace.jsonl, exact_br_diagnostics.csv, grid_refinement.csv
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

from research.geometry.committed_game import KernelWrap, wrap_deg  # noqa: E402
from research.geometry.firepower_kernel import KernelFit  # noqa: E402
from research.experiments.must1_formation_do import GEOM, N_SHIPS, _rot, _OFFSETS  # noqa: E402

OUT = REPO / "research" / "final_v9" / "commitment_exact"
GAMMA = 0.96
OMEGA_MAX = 60.0                      # deg per turn (frozen mapping)
GRIDS = {"5": (-1.0, -0.5, 0.0, 0.5, 1.0),
         "7": (-1.0, -2.0 / 3.0, -1.0 / 3.0, 0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0)}
DO_MAX_ITERS = 40
GAP_TOL = 0.05
SEED_ACTIONS = (0.0, 0.5, -0.5, 1.0, -1.0)   # deterministic DO seeds (levels)

CELLS = [(g, er, ev) for g in GEOM for er in (0.8, 1.2) for ev in (0.8, 1.0, 1.2)]
SANITY = [(g, 1.0, 1.0) for g in GEOM]


# ---------------------------------------------------------------- geometry
def _aspect(d: float) -> str:
    a = abs(wrap_deg(d))
    return "bow_stern" if (a <= 30.0 or a >= 150.0) else "broadside"


def make_game(geometry: str, eta_r: float, eta_v: float, H: int,
              kernel_dict: dict):
    """Formation game identical to the paper's (3-vessel line-ahead column)."""
    from research.experiments.must1_formation_do import FormationGame
    fit = KernelFit.from_dict(kernel_dict)
    kB = KernelWrap(fit, range_ratio=eta_r)
    kR = KernelWrap(fit, 1.0)
    brg, hB, hR = GEOM[geometry]
    return FormationGame(kB, kR, r0=16.0, bearing0_deg=brg, hB0_deg=hB,
                         hR0_deg=hR, vB=6.0 * eta_v, vR=6.0, H=H)


# ------------------------------------------------------- payoff evaluation
_SECTORS = ("bow", "starboard", "port", "stern")


def _sector_codes(delta: np.ndarray) -> np.ndarray:
    """Vectorised angle_to_sector: 0=bow 1=starboard 2=port 3=stern."""
    a = (delta + 180.0) % 360.0 - 180.0
    code = np.full(a.shape, 3, dtype=int)
    code[(a >= -30.0) & (a <= 30.0)] = 0
    code[(a > 30.0) & (a <= 150.0)] = 1
    code[(a >= -150.0) & (a < -30.0)] = 2
    return code


def fire_vec(kw, r: np.ndarray, delta: np.ndarray,
             target_aspect: np.ndarray) -> np.ndarray:
    """Vectorised equivalent of KernelWrap.fire for a batch of points.

    The calibrated kernel's firepower depends on the relative-bearing
    SECTOR only (angle_to_sector), so batching by (sector, target aspect)
    and evaluating the range dependence with np.interp is exact, not an
    approximation.  Verified against the scalar path to machine precision.
    """
    fit = kw.fit
    r_eff = np.clip(r / max(kw.eta_r, 1e-6), 1.0, 24.0)
    speed = int(np.clip(6, 0, 5))   # matches KernelWrap.fire
    sec = _sector_codes(delta)
    out = np.zeros_like(r_eff)
    for si, sname in enumerate(_SECTORS):
        for asp in ("bow_stern", "broadside"):
            m = (sec == si) & (target_aspect == asp)
            if not m.any():
                continue
            total = np.zeros(int(m.sum()))
            rm = r_eff[m]
            for kind, sms in fit.kind_sector_fp.items():
                fp = sms.get(sname, 0)
                if fp <= 0:
                    continue
                mm = np.interp(rm, fit.range_knots, fit.kind_m_range[kind])
                mm = mm + float(np.interp(speed, fit.speed_knots,
                                          fit.kind_m_speed[kind]))
                if asp == "bow_stern":
                    mm = mm + np.interp(rm, fit.long_knots, fit.kind_m_long[kind])
                curve = fit.response_curves[f"{kind}:{fp}"]
                total += np.interp(mm, curve["m"], curve["h"])
            out[m] = total
    return kw.eta_g * out


def batch_payoff(game, cands: np.ndarray, opp: np.ndarray, blue: bool) -> np.ndarray:
    """J for a batch of candidate sequences against one fixed opponent.

    blue=True  -> candidates are Blue, `opp` is the (single) Red sequence.
    blue=False -> candidates are Red, `opp` is the (single) Blue sequence.
    Fully vectorised over the batch; no role-swap trick (the game is not
    antisymmetric when the range ratio differs).
    """
    n, H = cands.shape
    if blue:
        seqB, seqR = cands, np.broadcast_to(opp, (n, H))
        kB, kR = game.kB, game.kR
        vB, vR = game.vB, game.vR
        hB0, hR0 = game.hB0, game.hR0
    else:
        seqB, seqR = np.broadcast_to(opp, (n, H)), cands
        kB, kR = game.kB, game.kR
        vB, vR = game.vB, game.vR
        hB0, hR0 = game.hB0, game.hR0
    xB = np.zeros(n); yB = np.zeros(n); hB = np.full(n, hB0)
    xR = np.full(n, game.xR0); yR = np.full(n, game.yR0); hR = np.full(n, hR0)

    def offs(head, c0, s0):
        c = np.cos(np.radians(head)); s = np.sin(np.radians(head))
        return np.stack([_OFFSETS[:, 0][None, :] * c[:, None]
                         - _OFFSETS[:, 1][None, :] * s[:, None],
                         _OFFSETS[:, 0][None, :] * s[:, None]
                         + _OFFSETS[:, 1][None, :] * c[:, None]], axis=-1)

    offB = offs(hB, 0, 0)
    offR = offs(hR, 0, 0)
    cum = np.zeros(n); disc = 1.0
    for t in range(H):
        J = np.zeros(n)
        for kb in range(N_SHIPS):
            xbk = xB + offB[:, kb, 0]; ybk = yB + offB[:, kb, 1]
            for kr in range(N_SHIPS):
                dx = (xR + offR[:, kr, 0]) - xbk
                dy = (yR + offR[:, kr, 1]) - ybk
                r = np.maximum(np.hypot(dx, dy), 0.5)
                brg = np.degrees(np.arctan2(dy, dx))
                dB = wrap_deg(brg - hB)
                dR = wrap_deg(brg + 180.0 - hR)
                aspR = np.where((np.abs(dR) <= 30.0) | (np.abs(dR) >= 150.0),
                                "bow_stern", "broadside")
                aspB = np.where((np.abs(dB) <= 30.0) | (np.abs(dB) >= 150.0),
                                "bow_stern", "broadside")
                J += fire_vec(kB, r, dB, aspR) - fire_vec(kR, r, dR, aspB)
        cum += disc * J
        disc *= GAMMA
        hB = wrap_deg(hB + seqB[:, t])
        hR = wrap_deg(hR + seqR[:, t])
        xB = xB + vB * np.cos(np.radians(hB)); yB = yB + vB * np.sin(np.radians(hB))
        xR = xR + vR * np.cos(np.radians(hR)); yR = yR + vR * np.sin(np.radians(hR))
        offB = offs(hB, 0, 0)
        offR = offs(hR, 0, 0)
    return cum


# ------------------------------------------------------------ double oracle
def restricted_lp(pay: np.ndarray):
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
    if not (res_B.success and res_R.success):
        bi = int(np.argmax(pay.min(axis=1)))
        x = np.zeros(m); x[bi] = 1.0
        rj = int(np.argmin(pay.max(axis=0)))
        y = np.zeros(n); y[rj] = 1.0
        return float(pay[bi].min()), x, y
    x = np.clip(res_B.x[:m], 0, None); x = x / x.sum()
    y = np.clip(res_R.x[:n], 0, None); y = y / y.sum()
    return float((res_B.x[-1] + res_R.x[-1]) / 2.0), x, y


class ExactCommitmentGame:
    """Finite open-loop game on a frozen action grid with exhaustive BRs."""

    def __init__(self, game, levels, H: int):
        self.game = game
        self.H = H
        self.levels = levels
        seqs = np.array(list(itertools.product(levels, repeat=H)), dtype=float)
        self.seqs = seqs * OMEGA_MAX           # (n_full, H) deg/turn
        self.n_full = len(self.seqs)
        self.hashes = [hashlib.blake2b(s.tobytes(), digest_size=8).hexdigest()
                       for s in self.seqs]
        self.trace: list[dict] = []
        self.n_evals = 0
        self._cols: dict[int, np.ndarray] = {}
        self._rows: dict[int, np.ndarray] = {}

    def payoff(self, i: int, j: int, blue_idx: bool = True) -> float:
        self.n_evals += 1
        return float(self.game.payoff(self.seqs[i], self.seqs[j], 1))

    # ---- exhaustive full-space best responses over the COMPLETE mixture ----
    def full_br_blue(self, y: np.ndarray, cols: dict) -> tuple[int, float, list]:
        """max over the full space of E_{tau_R ~ y} J; y is the FULL mixture."""
        support = np.where(y > 0)[0]
        if len(support) == 0:
            support = np.array([int(np.argmax(y))])
        total = np.zeros(self.n_full)
        for j in support:
            if j not in cols:
                cols[j] = self._col_blue(j)
            total += y[j] * cols[j]
        i = int(np.argmax(total))
        return i, float(total[i]), list(support)

    def full_br_red(self, x: np.ndarray, rows: dict) -> tuple[int, float, list]:
        """min over the full space of E_{tau_B ~ x} J; x is the FULL mixture."""
        support = np.where(x > 0)[0]
        if len(support) == 0:
            support = np.array([int(np.argmax(x))])
        total = np.zeros(self.n_full)
        for i in support:
            if i not in rows:
                rows[i] = self._row_red(i)
            total += x[i] * rows[i]
        j = int(np.argmin(total))
        return j, float(total[j]), list(support)

    def _col_blue(self, j: int) -> np.ndarray:
        """J(every Blue sequence, fixed Red sequence j); cached."""
        if j not in self._cols:
            self._cols[j] = batch_payoff(self.game, self.seqs, self.seqs[j],
                                         blue=True)
        return self._cols[j]

    def _row_red(self, i: int) -> np.ndarray:
        """J(fixed Blue sequence i, every Red sequence); cached."""
        if i not in self._rows:
            self._rows[i] = batch_payoff(self.game, self.seqs, self.seqs[i],
                                         blue=False)
        return self._rows[i]

    def solve(self) -> dict:
        n = self.n_full
        cols = self._cols
        rows = self._rows
        seed_idx = []
        seen = set()

        def add(sig: np.ndarray) -> None:
            d = np.abs(self.seqs - np.asarray(sig, float)).sum(axis=1)
            i = int(np.argmin(d))
            if i not in seen:
                seen.add(i)
                seed_idx.append(i)

        for a in SEED_ACTIONS:                       # constant actions
            add(np.full(self.H, a * OMEGA_MAX))
        for a in SEED_ACTIONS:                       # single-turn pulses
            for j in range(self.H):
                sig = np.zeros(self.H)
                sig[j] = a * OMEGA_MAX
                add(sig)
        for a, b in ((1.0, -1.0), (-1.0, 1.0), (1.0, 0.0), (0.0, 1.0),
                     (0.5, -0.5), (-0.5, 0.5)):      # two-phase turns
            half = self.H // 2
            add(np.concatenate([np.full(half, a * OMEGA_MAX),
                                np.full(self.H - half, b * OMEGA_MAX)]))
        X = list(dict.fromkeys(seed_idx))       # Blue restricted support
        Y = list(dict.fromkeys(seed_idx))       # Red restricted support
        LB = UB = float("nan")
        V = float("nan")
        gap = float("inf")
        for it in range(DO_MAX_ITERS):
            pay = np.zeros((len(X), len(Y)))
            for b, j in enumerate(Y):
                pay[:, b] = self._col_blue(j)[X]   # vectorised + cached
            V, xr, yr = restricted_lp(pay)
            x_full = np.zeros(n); x_full[X] = xr     # COMPLETE mixture
            y_full = np.zeros(n); y_full[Y] = yr
            br_B, ub, supp_B = self.full_br_blue(y_full, cols)
            br_R, lb, supp_R = self.full_br_red(x_full, rows)
            LB, UB = lb, ub
            assert LB - 1e-6 <= V <= UB + 1e-6, f"bound order violated: {LB} {V} {UB}"
            gap = UB - LB
            self.trace.append({"iter": it + 1, "n_X": len(X), "n_Y": len(Y),
                               "V_restricted": V, "LB": LB, "UB": UB,
                               "rel_gap": gap / max(1.0, abs(V)),
                               "br_blue_support": len(supp_B),
                               "br_red_support": len(supp_R),
                               "evals": self.n_evals,
                               "blue_seq_hash": self.hashes[br_B],
                               "red_seq_hash": self.hashes[br_R]})
            if gap / max(1.0, abs(V)) < GAP_TOL:
                break
            new_B = br_B not in X
            new_R = br_R not in Y
            if new_B:
                X.append(br_B)
            if new_R:
                Y.append(br_R)
            if not new_B and not new_R:
                break          # exact BRs already in the restricted sets
        return {"V_restricted": V, "LB": LB, "UB": UB, "gap": gap,
                "rel_gap": gap / max(1.0, abs(V)),
                "iters": len(self.trace), "n_full": n,
                "n_restricted_B": len(X), "n_restricted_R": len(Y),
                "n_payoff_evals": self.n_evals,
                "converged": gap / max(1.0, abs(V)) < GAP_TOL,
                "trace": self.trace}


def solve_h1(kernel_dict, geometry, eta_r, eta_v, levels) -> dict:
    """H=1: solve the complete |A|x|A| matrix exactly -> LB_1 = UB_1 = V*_1."""
    game = make_game(geometry, eta_r, eta_v, 1, kernel_dict)
    seqs = np.array(list(itertools.product(levels, repeat=1)), dtype=float) * OMEGA_MAX
    m = len(seqs)
    pay = np.zeros((m, m))
    for i in range(m):
        pay[i] = batch_payoff(game, seqs, seqs[i], blue=True)
    V, x, y = restricted_lp(pay)
    # verify exactness: with complete sets, restricted value IS the value
    lb = float((x @ pay).min())
    ub = float((pay @ y).max())
    return {"V1": float(V), "LB1": lb, "UB1": ub, "n": m,
            "exact_check": abs(ub - lb) < 1e-8}


def run_cell(args):
    geometry, eta_r, eta_v, grid_id, H = args
    t0 = time.time()
    kernel_dict = json.load(open(REPO / "research" / "results" / "e01"
                                 / "kernel_fits.json"))["CA"]
    levels = GRIDS[grid_id]
    game = make_game(geometry, eta_r, eta_v, H, kernel_dict)
    eg = ExactCommitmentGame(game, levels, H)
    res = eg.solve()
    res.update({"geometry": geometry, "eta_r": eta_r, "eta_v": eta_v,
                "grid": grid_id, "H": H,
                "seconds": round(time.time() - t0, 1)})
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--grids", default="5,7")
    ap.add_argument("--phase", default="all",
                    choices=["all", "grid5", "grid7", "sanity"])
    ap.add_argument("--grid7-anchors", action="store_true",
                    help="run Grid-7 only on the pre-specified anchor subset")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    kernel_dict = json.load(open(REPO / "research" / "results" / "e01"
                                 / "kernel_fits.json"))["CA"]

    # ---- H=1 exact baselines (complete |A_m|x|A_m| matrix, one per grid) ----
    grids_pre = [g for g in a.grids.split(",") if g] or ["5"]
    h1 = {}
    for grid_id in grids_pre:
        for (g, er, ev) in CELLS + SANITY:
            h1[(g, er, ev, grid_id)] = solve_h1(kernel_dict, g, er, ev,
                                                GRIDS[grid_id])
            if not h1[(g, er, ev, grid_id)]["exact_check"]:
                print(f"!! H=1 exactness check failed for {(g, er, ev)} "
                      f"grid {grid_id}", flush=True)
    json.dump({f"{k[0]}|{k[1]}|{k[2]}|g{k[3]}": v for k, v in h1.items()},
              open(OUT / "exact_h1_baselines.json", "w"), indent=2)

    grids = [g for g in a.grids.split(",") if g]
    if a.phase == "grid5":
        grids = ["5"]
    elif a.phase == "grid7":
        grids = ["7"]
    jobs = []
    cells = SANITY if a.phase == "sanity" else CELLS
    for grid_id in grids:
        if grid_id == "7" and a.grid7_anchors:
            anchors = [c for c in CELLS if c[2] == 1.0]          # neutral speed
            anchors += [CELLS[0], CELLS[5], CELLS[10]]           # extremes
            cells_g = list(dict.fromkeys(anchors))
        else:
            cells_g = cells
        for (g, er, ev) in cells_g:
            jobs.append((g, er, ev, grid_id, 6))
    print(f"[v9-T1] {len(jobs)} exact runs on grids {grids}", flush=True)

    rows = []
    jf = open(OUT / "double_oracle_trace.jsonl", "a")
    done = 0
    with ProcessPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(run_cell, j): j for j in jobs}
        for fut in as_completed(futs):
            r = fut.result()
            rows.append(r)
            for tr in r["trace"]:
                jf.write(json.dumps({"geometry": r["geometry"], "eta_r": r["eta_r"],
                                     "eta_v": r["eta_v"], "grid": r["grid"],
                                     "H": r["H"], **tr}) + "\n")
            jf.flush()
            done += 1
            el = time.time() - t0
            print(f"PROGRESS {done}/{len(jobs)} "
                  f"elapsed={time.strftime('%H:%M:%S', time.gmtime(el))} "
                  f"eta={time.strftime('%H:%M:%S', time.gmtime(el * (len(jobs) - done) / max(done, 1)))} "
                  f"| {r['geometry']} er={r['eta_r']} ev={r['eta_v']} g{r['grid']}: "
                  f"LB={r['LB']:+.3f} UB={r['UB']:+.3f} gap={r['rel_gap']:.0%} "
                  f"({r['seconds']}s)", flush=True)
    jf.close()

    # -------- intervals and certification --------
    out_rows = []
    diag = []
    for r in rows:
        base = h1[(r["geometry"], r["eta_r"], r["eta_v"], r["grid"])]
        lb1, ub1 = base["LB1"], base["UB1"]   # exact: LB1 == UB1 == V*_1
        plo, phi = r["LB"] - ub1, r["UB"] - lb1
        sign = 1 if plo > 0 else (-1 if phi < 0 else 0)
        expected = 0 if r["eta_r"] == 1.0 else (1 if r["eta_r"] > 1 else -1)
        out_rows.append({
            "geometry": r["geometry"], "eta_r": r["eta_r"], "eta_v": r["eta_v"],
            "grid": r["grid"], "H": r["H"],
            "V_restricted": round(r["V_restricted"], 4),
            "lower_bound": round(r["LB"], 4), "upper_bound": round(r["UB"], 4),
            "bound_width": round(r["UB"] - r["LB"], 4),
            "relative_gap": round(r["rel_gap"], 4),
            "LB_1": round(lb1, 4), "UB_1": round(ub1, 4),
            "P_lower": round(plo, 4), "P_upper": round(phi, 4),
            "point_estimate": round((r["LB"] + r["UB"]) / 2 - (lb1 + ub1) / 2, 4),
            "sign_certified": int(sign != 0), "certified_sign": sign,
            "expected_sign": expected,
            "solver_status": ("tight" if r["rel_gap"] < GAP_TOL
                              else "SIGN-CERTIFIED/VALUE-LOOSE" if sign != 0
                              else "UNCERTIFIED"),
            "n_full_strategies": r["n_full"],
            "DO_iterations": r["iters"],
            "restricted_rows": r["n_restricted_B"],
            "restricted_cols": r["n_restricted_R"],
            "num_payoff_evals": r["n_payoff_evals"],
            "runtime_sec": r["seconds"],
        })
        diag.append({"geometry": r["geometry"], "eta_r": r["eta_r"],
                     "eta_v": r["eta_v"], "grid": r["grid"],
                     "trace": r["trace"]})
    phase_tag = "" if a.phase == "all" else f"_{a.phase}"
    for grid_id in grids:
        sub = [x for x in out_rows if x["grid"] == grid_id]
        if not sub:
            continue
        with open(OUT / f"exact_grid{grid_id}{phase_tag}_results.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(sub[0].keys()))
            w.writeheader(); w.writerows(sub)
    with open(OUT / "exact_br_diagnostics.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["geometry", "eta_r", "eta_v", "grid",
                                           "iter", "n_X", "n_Y", "V_restricted",
                                           "LB", "UB", "rel_gap",
                                           "br_blue_support", "br_red_support",
                                           "evals"])
        w.writeheader()
        for d in diag:
            for tr in d["trace"]:
                w.writerow({**{k: d[k] for k in ("geometry", "eta_r", "eta_v", "grid")},
                            **{k: tr[k] for k in w.fieldnames if k in tr}})

    # -------- grid refinement + classification --------
    g5 = {(x["geometry"], x["eta_r"], x["eta_v"]): x
          for x in out_rows if x["grid"] == "5" and x["eta_r"] != 1.0}
    g7 = {(x["geometry"], x["eta_r"], x["eta_v"]): x
          for x in out_rows if x["grid"] == "7" and x["eta_r"] != 1.0}
    refinement = []
    for k, v5 in g5.items():
        v7 = g7.get(k)
        s5 = v5["certified_sign"]
        s7 = v7["certified_sign"] if v7 else None
        refinement.append({"geometry": k[0], "eta_r": k[1], "eta_v": k[2],
                           "signal_grid5": s5,
                           "signal_grid7": s7 if s7 is not None else "not_run",
                           "grid_sign_agree": (s7 == s5) if v7 else None})
    with open(OUT / "grid_refinement.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(refinement[0].keys()) if refinement else
                           ["geometry", "eta_r", "eta_v", "signal_grid5",
                            "signal_grid7", "grid_sign_agree"])
        w.writeheader(); w.writerows(refinement)

    n_cert5 = sum(1 for x in g5.values() if x["sign_certified"])
    reversals = [x for x in g5.values() if x["sign_certified"]
                 and x["certified_sign"] != x["expected_sign"]]
    revals7 = [x for x in g7.values() if x["sign_certified"]
               and x["certified_sign"] != x["expected_sign"]]
    geom_ok = {}
    for g in GEOM:
        sub = [x for x in g5.values() if x["geometry"] == g]
        geom_ok[g] = {"pos": sum(1 for x in sub if x["certified_sign"] > 0),
                      "neg": sum(1 for x in sub if x["certified_sign"] < 0),
                      "n": len(sub)}
    sanity_ok = all(abs(x["point_estimate"]) < 0.05
                    for x in out_rows if x["eta_r"] == 1.0 and x["grid"] == "5")
    g7_ran = len(g7)
    if (n_cert5 >= 15 and not reversals and not revals7
            and all(v["pos"] >= 1 and v["neg"] >= 1 for v in geom_ok.values())):
        verdict = ("CORE-STRONG (Grid-7 full)" if g7_ran >= 18
                   else f"CORE-STRONG (Grid-7 anchors: {g7_ran}/18)")
    elif n_cert5 >= 10 and not reversals and not revals7:
        verdict = "CORE-CONDITIONAL"
    elif reversals or revals7:
        verdict = "REMOVE-CORE"
    else:
        verdict = "CORE-CONDITIONAL"

    summary = {"grid5_cells": len(g5), "grid5_sign_certified": n_cert5,
               "grid5_certified_reversals": len(reversals),
               "grid7_cells": g7_ran,
               "grid7_certified_reversals": len(revals7),
               "geometry_support": geom_ok,
               "symmetric_sanity_ok": sanity_ok,
               "h1_exact_all": all(v["exact_check"] for v in h1.values()),
               "verdict": verdict,
               "grids_run": grids,
               "wall_time_s": round(time.time() - t0, 1)}
    json.dump(summary, open(OUT / f"exact_certification_summary{phase_tag}.json", "w"), indent=2)

    lines = ["# v9 T1: exact discretized open-loop commitment certification", "",
             f"Grids run: {grids}   H=1 exact baselines: "
             f"{'all exact' if summary['h1_exact_all'] else 'CHECK FAILED'}",
             f"Grid-5: {n_cert5}/{len(g5)} sign-certified, "
             f"{len(reversals)} certified reversals",
             f"Grid-7: {g7_ran} cells, {len(revals7)} certified reversals",
             f"Geometry support: {geom_ok}",
             f"Symmetric sanity near zero: {sanity_ok}",
             f"**VERDICT: {verdict}**", "",
             "Bounds are exact for the frozen finite game: LB = exhaustive "
             "min over the full action space against the complete Blue "
             "mixture; UB = exhaustive max against the complete Red mixture. "
             "No mixture truncation is used anywhere.",
             "", "| geometry | eta_r | eta_v | grid | LB | UB | P interval | cert | gap | status |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for x in out_rows:
        if x["eta_r"] == 1.0:
            continue
        lines.append(f"| {x['geometry']} | {x['eta_r']} | {x['eta_v']} | {x['grid']} "
                     f"| {x['lower_bound']:+.3f} | {x['upper_bound']:+.3f} "
                     f"| [{x['P_lower']:+.3f}, {x['P_upper']:+.3f}] "
                     f"| {'Y' if x['sign_certified'] else 'n'} | {x['relative_gap']:.0%} "
                     f"| {x['solver_status']} |")
    (OUT / f"exact_certification_report{phase_tag}.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"[v9-T1] DONE verdict={verdict} grid5={n_cert5}/{len(g5)} "
          f"grid7={g7_ran} in "
          f"{time.strftime('%H:%M:%S', time.gmtime(time.time() - t0))}", flush=True)


if __name__ == "__main__":
    main()
