"""T5/Fig3 data: closed-loop degeneracy violation on an (eta_v, eta_r) grid.

For each cell, solve the reduced closed-loop DP (differential_game.ReducedGame)
to convergence and record max_s |V(s) - L(s)|.  Speed asymmetry (eta_v) should
NOT break the degeneracy; interaction-strength asymmetry (eta_r) should.

Output: research/final_v8/figures/fig3_grid.json
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

OUT = REPO / "research" / "final_v8" / "figures"
ETA_V = (0.8, 0.9, 1.0, 1.1, 1.25)
ETA_R = (0.75, 0.9, 1.0, 1.1, 1.25)


def solve_cell(args):
    eta_v, eta_r = args
    from research.geometry.differential_game import KernelWrap, ReducedGame
    from research.geometry.firepower_kernel import KernelFit
    fits = json.load(open(REPO / "research" / "results" / "e01" / "kernel_fits.json"))
    fit = KernelFit.from_dict(fits["CA"])
    g = ReducedGame(KernelWrap(fit, range_ratio=eta_r), KernelWrap(fit, 1.0),
                    v_B=6.0 * eta_v, v_R=6.0, n_r=30, n_alpha=24)
    V = g.solve(max_sweeps=400, tol=1e-6)
    L = g._L
    return {"eta_v": eta_v, "eta_r": eta_r,
            "max_V_minus_L": float(np.max(np.abs(V - L))),
            "sweeps": g.sweeps}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [(ev, er) for ev in ETA_V for er in ETA_R]
    with ProcessPoolExecutor(max_workers=3) as ex:
        rows = list(ex.map(solve_cell, jobs))
    Z = np.zeros((len(ETA_R), len(ETA_V)))
    for r in rows:
        i = ETA_R.index(r["eta_r"])
        j = ETA_V.index(r["eta_v"])
        Z[i, j] = r["max_V_minus_L"]
    json.dump({"eta_v": list(ETA_V), "eta_r": list(ETA_R),
               "V_minus_L": Z.tolist(), "detail": rows},
              open(OUT / "fig3_grid.json", "w"), indent=2)
    print(f"fig3 grid done: {len(rows)} cells, max|V-L| = {Z.max():.4f}")


if __name__ == "__main__":
    main()
