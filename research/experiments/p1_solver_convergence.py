"""P1: Reduced-state finite-horizon DP solver for asymmetric commitment.

B8 showed that the plan-library approach doesn't converge: 11→21→41 plans
still change values by >5% in 75% of cells.  The root cause is that a
finite library of fixed heading plans cannot represent the full action
space.

This solver replaces the plan library with backward induction on the
(r, alpha_B, alpha_R) grid:

    V_T(s) = Phi(s_T)                    (terminal payoff)
    V_t(s) = max_{u_B} min_{u_R} [L(s)*dt + V_{t+1}(F(s,u_B,u_R))]

Key difference from the open-loop plan library: the DP implicitly optimises
over ALL possible action sequences, not just a finite library.  Convergence
is measured by grid refinement (coarse→medium→fine).

Three grid levels:
  coarse : n_r=16, n_alpha=12 (fewer states, coarser interpolation)
  medium : n_r=30, n_alpha=24
  fine   : n_r=48, n_alpha=36

Test cells (from B8 worst / representative):
  symmetric head-on, symmetric parallel,
  range advantage (eta_r=1.25), range disadvantage (eta_r=0.8),
  crossing, B8 worst cell, B8 stable cell

Output: research/results/p1/{convergence.csv, results.json, report.md}
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

OUT = REPO / "research" / "results" / "p1"

# grid levels
LEVELS = {"coarse": (16, 12), "medium": (30, 24), "fine": (48, 36)}

TEST_CELLS = [
    {"name": "symmetric_head_on", "eta_v": 1.0, "eta_r": 1.0, "geometry": "head_on"},
    {"name": "symmetric_parallel", "eta_v": 1.0, "eta_r": 1.0, "geometry": "parallel"},
    {"name": "range_adv_head_on", "eta_v": 1.0, "eta_r": 1.33, "geometry": "head_on"},
    {"name": "range_disadv_head_on", "eta_v": 1.0, "eta_r": 0.75, "geometry": "head_on"},
    {"name": "crossing_sym", "eta_v": 1.0, "eta_r": 1.0, "geometry": "crossing"},
    {"name": "speed_adv_parallel", "eta_v": 1.25, "eta_r": 1.0, "geometry": "parallel"},
    {"name": "range_adv_crossing", "eta_v": 1.0, "eta_r": 1.33, "geometry": "crossing"},
]

GEOM_PARAMS = {
    "head_on": (0.0, 0.0, 180.0),
    "parallel": (90.0, 0.0, 0.0),
    "crossing": (45.0, 0.0, 180.0),
}


def solve_finite_horizon(kB, kR, vB, vR, n_r, n_a, T=40, gamma=0.96):
    """Finite-horizon backward induction on the reduced-state grid.

    V_T = 0 (no terminal payoff); V_t = max min [L + gamma V_{t+1}(s')].
    Returns the value at t=0 averaged over the grid (mean, std).
    """
    g = ReducedGame(kB, kR, v_B=vB, v_R=vR, n_r=n_r, n_alpha=n_a, gamma=gamma)
    L = g._L
    dyn = g._dynamics()
    V = np.zeros(g.shape)

    for t in range(T - 1, -1, -1):
        Q = np.empty((len(dyn),) + g.shape)
        for idx, (r2, aB2, aR2) in enumerate(dyn):
            Q[idx] = L + g.gamma * g._interp_V(V, r2, aB2, aR2)
        acts = len(g.actions)
        Qr = Q.reshape(acts, acts, *g.shape)
        V = Qr.min(axis=1).max(axis=0)

    return {
        "mean": float(np.mean(V)),
        "std": float(np.std(V)),
        "min": float(np.min(V)),
        "max": float(np.max(V)),
        "value_at_r12_headon": float(V[g._state_index(12, np.radians(0), np.radians(180))]),
        "value_at_r12_parallel": float(V[g._state_index(12, np.radians(-90), np.radians(90))]),
        "value_at_r12_crossing": float(V[g._state_index(12, np.radians(45), np.radians(180))]),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fits = json.load(open(REPO / "research" / "results" / "e01" / "kernel_fits.json"))
    base_fit = KernelFit.from_dict(fits["CA"])

    all_results = []
    for cell in TEST_CELLS:
        name = cell["name"]
        eta_v, eta_r = cell["eta_v"], cell["eta_r"]
        brg, hB, hR = GEOM_PARAMS[cell["geometry"]]

        kB = KernelWrap(base_fit, range_ratio=eta_r)
        kR = KernelWrap(base_fit)

        level_results = {}
        for level, (n_r, n_a) in LEVELS.items():
            res = solve_finite_horizon(kB, kR, 6.0 * eta_v, 6.0, n_r, n_a)
            level_results[level] = res
            print(f"{name} [{level}]: mean={res['mean']:.4f}", flush=True)

        # convergence: |V_fine - V_medium| / max(1, |V_fine|)
        d_fine_med = abs(level_results["fine"]["mean"] - level_results["medium"]["mean"])
        conv = d_fine_med / max(1.0, abs(level_results["fine"]["mean"]))
        level_results["convergence_delta"] = round(conv, 6)
        level_results["convergence_pass"] = bool(conv < 0.05)

        all_results.append({
            "cell": name,
            "eta_v": eta_v, "eta_r": eta_r, "geometry": cell["geometry"],
            "levels": level_results,
        })
        print(f"  delta_V = {conv:.6f} ({'PASS' if conv < 0.05 else 'FAIL'})", flush=True)

    # summary
    conv_passes = [r for r in all_results if r["levels"]["convergence_pass"]]
    conv_frac = len(conv_passes) / len(all_results) * 100
    gate_pass = conv_frac >= 80

    result = {
        "solver": "finite-horizon backward induction (reduced-state grid)",
        "horizon_T": 40,
        "gamma": 0.96,
        "grid_levels": LEVELS,
        "cells": all_results,
        "convergence_fraction_pct": round(conv_frac),
        "gate_80pct": gate_pass,
        "overall": "PASS" if gate_pass else "FAIL",
    }
    (OUT / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    with (OUT / "convergence.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["cell", "eta_v", "eta_r", "geometry",
                     "V_coarse", "V_medium", "V_fine", "delta_V", "pass"])
        for r in all_results:
            lv = r["levels"]
            w.writerow([r["cell"], r["eta_v"], r["eta_r"], r["geometry"],
                        f"{lv['coarse']['mean']:.6f}",
                        f"{lv['medium']['mean']:.6f}",
                        f"{lv['fine']['mean']:.6f}",
                        f"{lv['convergence_delta']:.6f}",
                        lv["convergence_pass"]])

    lines = ["# P1: finite-horizon DP solver convergence", "",
             f"Gate: >= 80% cells with delta_V < 5%", ""]
    for r in all_results:
        lv = r["levels"]
        lines.append(f"- {r['cell']}: V_coarse={lv['coarse']['mean']:.4f} "
                     f"V_medium={lv['medium']['mean']:.4f} "
                     f"V_fine={lv['fine']['mean']:.4f} "
                     f"delta={lv['convergence_delta']:.4f} "
                     f"{'PASS' if lv['convergence_pass'] else 'FAIL'}")
    lines.append(f"\nGate: {conv_frac:.0f}% -> {result['overall']}")
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "cells"},
                     indent=2))


if __name__ == "__main__":
    import csv
    main()
