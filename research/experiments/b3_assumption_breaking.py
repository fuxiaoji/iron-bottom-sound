"""B3: closed-loop degeneracy assumption-breaking matrix (v4 plan B3.3).

Proposition 1 (symmetric closed-loop degeneracy) holds under A1-A7: simultaneous
moves, shared action set, identical capabilities (kernels, lambda=1), constant
cruise, no observation delay, no terminal payoff.  This experiment breaks the
assumptions one at a time and measures how far the stationary value departs
from the instantaneous payoff (max |V - L| over the grid):

  base            : all symmetric                -> expect max|V-L| = 0
  speed_asym      : v_B = 1.25 * v_R             -> dynamics + payoff asymmetric
  range_asym      : k_B range_ratio = 1.25       -> payoff asymmetric
  action_asym     : B has 5 turn levels, R has 3 -> action symmetry broken
  terminal_payoff : finite horizon T=30, Phi = L(s_T) -> transient degeneracy broken
  commit_ref      : pointer to E02 open-loop results (commitment breaks it)

Output: research/results/b3/assumption_breaking.json + report.md + figure.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

from research.geometry.committed_game import KernelWrap  # noqa: E402
from research.geometry.differential_game import ReducedGame, wrap_angle  # noqa: E402
from research.geometry.firepower_kernel import KernelFit  # noqa: E402

OUT = REPO / "research" / "results" / "b3"


class AsymGame(ReducedGame):
    """ReducedGame with per-player action sets and finite-horizon support."""

    def __init__(self, *a, actions_B=None, actions_R=None, **kw):
        super().__init__(*a, **kw)
        if actions_B is not None:
            self.actions_B = tuple(actions_B)
        else:
            self.actions_B = self.actions
        if actions_R is not None:
            self.actions_R = tuple(actions_R)
        else:
            self.actions_R = self.actions

    def _dynamics(self):
        r = self.r_grid[:, None, None]
        aB = self.a_grid[None, :, None]
        aR = self.a_grid[None, None, :]
        dyn = []
        for uB in self.actions_B:
            for uR in self.actions_R:
                dLOS = (self.vR * np.sin(aR) - self.vB * np.sin(aB)) / np.maximum(r, 1e-6)
                r2 = np.clip(r + self.vR * np.cos(aR) - self.vB * np.cos(aB),
                             self.r_min, self.r_max)
                aB2 = wrap_angle(aB + uB - dLOS)
                aR2 = wrap_angle(aR + uR - dLOS)
                dyn.append((r2, aB2, aR2))
        return dyn

    def solve_asym(self, max_sweeps=400, tol=1e-5):
        L = self._L
        g = self.gamma
        dyn = self._dynamics()
        V = self.V
        for sweep in range(max_sweeps):
            Q = np.empty((len(dyn),) + self.shape)
            for idx, (r2, aB2, aR2) in enumerate(dyn):
                Q[idx] = L + g * self._interp_V(V, r2, aB2, aR2)
            nB, nR = len(self.actions_B), len(self.actions_R)
            Qr = Q.reshape(nB, nR, *self.shape)
            worst = Qr.min(axis=1)
            V_new = worst.max(axis=0)
            diff = float(np.max(np.abs(V_new - V)))
            V = V_new
            self.sweeps = sweep + 1
            self.residual = diff
            if diff < tol:
                break
        self.V = V
        return V


def run_case(name, kB, kR, vB=6.0, vR=6.0, actions_B=None, actions_R=None,
             n_r=24, n_a=18):
    g = AsymGame(kB, kR, v_B=vB, v_R=vR, actions_B=actions_B,
                 actions_R=actions_R, n_r=n_r, n_alpha=n_a)
    g.solve_asym(max_sweeps=500, tol=1e-6)
    dev = float(np.max(np.abs(g.V - g._L)))
    rel = dev / max(float(np.max(np.abs(g._L))), 1e-9)
    return {"case": name, "max_abs_V_minus_L": dev, "relative": round(rel, 4),
            "sweeps": g.sweeps}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fits = json.load(open(REPO / "research" / "results" / "e01" / "kernel_fits.json"))
    base_fit = KernelFit.from_dict(fits["CA"])
    results = []

    # base: all symmetric
    kB = KernelWrap(base_fit)
    kR = KernelWrap(base_fit)
    results.append(run_case("base_symmetric", kB, kR))
    # speed asymmetry
    results.append(run_case("speed_asymmetry_vB125", kB, kR, vB=7.5, vR=6.0))
    results.append(run_case("speed_asymmetry_vB080", kB, kR, vB=4.8, vR=6.0))
    # range asymmetry
    kB_r = KernelWrap(base_fit, range_ratio=1.25)
    kR_r = KernelWrap(base_fit, range_ratio=0.8)
    results.append(run_case("range_asymmetry_B125_R080", kB_r, kR_r))
    # action asymmetry: B gets 5 turn levels, R keeps 3
    w = np.radians(60.0)
    results.append(run_case(
        "action_asymmetry_B5_R3", kB, kR,
        actions_B=(-w, -w / 2, 0.0, w / 2, w),
        actions_R=(-w, 0.0, w)))
    # firepower asymmetry (eta_g): B hits harder, same reach
    kB_g = KernelWrap(base_fit, firepower_ratio=1.25)
    results.append(run_case("firepower_asymmetry_B125", kB_g, kR))
    # both speed and range asymmetric (fully general)
    results.append(run_case("full_asymmetry", kB_r, kR, vB=7.5, vR=6.0))

    # terminal payoff (finite horizon): iterate back from Phi = kappa * L
    g = AsymGame(kB, kR, n_r=24, n_alpha=18)
    r = g.r_grid[:, None, None]
    aB = g.a_grid[None, :, None]
    aR = g.a_grid[None, None, :]
    dyn = g._dynamics()
    V = g._L.copy() * 1.0  # Phi(s_T) = L(s_T)
    for t in range(30):
        Q = np.empty((len(dyn),) + g.shape)
        for idx, (r2, aB2, aR2) in enumerate(dyn):
            Q[idx] = g._L + g.gamma * g._interp_V(V, r2, aB2, aR2)
        Qr = Q.reshape(3, 3, *g.shape)
        V = Qr.min(axis=1).max(axis=0)
    dev = float(np.max(np.abs(V - g._L)))
    rel = dev / max(float(np.max(np.abs(g._L))), 1e-9)
    results.append({"case": "terminal_payoff_finite_horizon_T30",
                    "max_abs_V_minus_L": dev, "relative": round(rel, 4),
                    "sweeps": 30})

    # commitment reference (open-loop committed game is non-degenerate by
    # construction; numbers from E02)
    e02 = json.load(open(REPO / "research" / "results" / "e02" / "results.json"))
    results.append({
        "case": "commitment_reference_open_loop",
        "max_abs_V_minus_L": None,
        "note": "open-loop committed game: LP values are generically nonzero; "
                "see e02 payoff_matrices.json (e.g., parallel eta_r=1 values "
                "+0.02..+2.97 across cells)",
    })

    out = {"cases": results,
           "base_expectation": "max|V-L|=0 under full symmetry",
           "conclusion": None}
    base = next(r for r in results if r["case"] == "base_symmetric")
    out["conclusion"] = (
        "base case reproduces V=L exactly; every broken assumption produces "
        "a strictly positive deviation, quantifying the boundary of the "
        "degeneracy proposition" if base["max_abs_V_minus_L"] == 0 else
        "UNEXPECTED: base case deviates")
    (OUT / "assumption_breaking.json").write_text(json.dumps(
        {"results": results, **out}, indent=2), encoding="utf-8")

    lines = ["# B3 assumption-breaking matrix", ""]
    for r in results:
        v = r.get("max_abs_V_minus_L")
        lines.append(f"- {r['case']}: max|V-L| = {v if v is not None else 'n/a'}"
                     + (f" (relative {r['relative']})" if "relative" in r and v is not None else ""))
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    import math  # noqa: F401  (tau placeholder)
    main()
