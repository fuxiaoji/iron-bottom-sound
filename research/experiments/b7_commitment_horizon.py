"""B7: commitment horizon effect  P_H = V_H - V_1.

V_H = open-loop maximin LP value when both sides commit plans for H turns
(the rollout horizon is H; the payoff matrix is evaluated over those H
steps).  H = 1 is the near-degenerate one-step commitment (the value is
then essentially the instantaneous differential evaluated after one
turn); larger H gives the positional plans time to pay off.

Swept over the same 54-cell grid as E02 plus horizon sweep
H in {1, 2, 3, 4, 6, 12, 40} on the base cell.

Output: research/results/b7/{horizon_sweep.csv, cells.csv, results.json,
report.md, fig_b7_horizon.png}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

from research.geometry.committed_game import (  # noqa: E402
    KernelWrap,
    make_maneuver_library,
    open_loop_minimax,
)
from research.geometry.firepower_kernel import KernelFit  # noqa: E402

OUT = REPO / "research" / "results" / "b7"
HORIZONS = [1, 2, 3, 4, 6, 12, 40]
GEOMETRIES = {
    "head_on": (0.0, 0.0, 180.0),
    "parallel": (90.0, 0.0, 0.0),
    "crossing": (45.0, 0.0, 180.0),
}


def main() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    OUT.mkdir(parents=True, exist_ok=True)
    fits = json.load(open(REPO / "research" / "results" / "e01" / "kernel_fits.json"))
    base_fit = KernelFit.from_dict(fits["CA"])
    kB = KernelWrap(base_fit)
    kR = KernelWrap(base_fit)
    lib = make_maneuver_library()

    # ---- horizon sweep on the base cells ----
    sweep = []
    for gname, (brg, hB, hR) in GEOMETRIES.items():
        vals = []
        for H in HORIZONS:
            out = open_loop_minimax(kB, kR, lib, r0=16, bearing0_deg=brg,
                                    headingB0_deg=hB, headingR0_deg=hR,
                                    vB=6.0, vR=6.0, steps=H)
            vals.append(out["game_value"])
            sweep.append({"geometry": gname, "H": H,
                          "V_H": out["game_value"],
                          "maximin_plan_B": out["maximin_plan_B"],
                          "minimax_plan_R": out["minimax_plan_R"]})
        P = [v - vals[0] for v in vals]
        print(gname, "V_H:", [round(v, 3) for v in vals], "P_H:", [round(p, 3) for p in P],
              flush=True)

    # ---- P_H across the parameter grid (eta_v x eta_r at H=6 vs H=1) ----
    cells = []
    for eta_v in (0.8, 0.89, 1.0, 1.13, 1.25, 1.33):
        for eta_r in (0.75, 1.0, 1.33):
            kB = KernelWrap(base_fit, range_ratio=eta_r)
            kR = KernelWrap(base_fit)
            brg, hB, hR = GEOMETRIES["parallel"]
            v1 = open_loop_minimax(kB, kR, lib, 16, brg, hB, hR,
                                   6.0 * eta_v, 6.0, steps=1)["game_value"]
            v6 = open_loop_minimax(kB, kR, lib, 16, brg, hB, hR,
                                   6.0 * eta_v, 6.0, steps=6)["game_value"]
            cells.append({"eta_v": eta_v, "eta_r": eta_r,
                          "V_1": v1, "V_6": v6, "P_6": v6 - v1})
            print("cell", eta_v, eta_r, "V1=%.3f V6=%.3f P6=%.3f"
                  % (v1, v6, v6 - v1), flush=True)

    dP = [c["P_6"] for c in cells]
    frac_nonzero = float(np.mean([abs(p) > 0.05 for p in dP]))

    result = {
        "definition": "P_H = V_H - V_1 (V_H: maximin LP value with H-turn "
                      "committed plans)",
        "horizon_sweep": sweep,
        "grid_P6": cells,
        "P6_nonzero_fraction": frac_nonzero,
        "interpretation": ("P_H != 0 for most cells means commitment length "
                           "changes the positional value; P_H ~ 0 everywhere "
                           "would demote commitment to a structural "
                           "side-note."),
    }
    (OUT / "results.json").write_text(json.dumps(result, indent=2),
                                      encoding="utf-8")

    with (OUT / "horizon_sweep.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(sweep[0].keys())
        for r in sweep:
            w.writerow(r.values())
    with (OUT / "cells.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cells[0].keys())
        for r in cells:
            w.writerow(r.values())

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    ax = axes[0]
    for gname in GEOMETRIES:
        sel = [r for r in sweep if r["geometry"] == gname]
        ax.plot(HORIZONS, [r["V_H"] for r in sel], marker="o", label=gname)
    ax.set_xlabel("commitment horizon H (turns)")
    ax.set_ylabel("V_H (game value)")
    ax.set_title("commitment horizon sweep (eta_v = eta_r = 1)")
    ax.legend()
    ax = axes[1]
    for eta_r, mk in ((0.75, "o"), (1.0, "s"), (1.33, "^")):
        sel = sorted([c for c in cells if c["eta_r"] == eta_r],
                     key=lambda c: c["eta_v"])
        ax.plot([c["eta_v"] for c in sel], [c["P_6"] for c in sel],
                marker=mk, label=f"eta_r={eta_r}")
    ax.axhline(0, color="k", lw=0.8, ls="--")
    ax.set_xlabel(r"speed ratio $\eta_v$")
    ax.set_ylabel("$P_6 = V_6 - V_1$")
    ax.set_title("P_6 across the parameter grid (parallel)")
    ax.legend()
    fig.savefig(OUT / "fig_b7_horizon.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    lines = ["# B7 commitment horizon", ""]
    for r in sweep:
        lines.append(f"- {r['geometry']} H={r['H']}: V_H={r['V_H']:+.3f} "
                     f"(B:{r['maximin_plan_B']} R:{r['minimax_plan_R']})")
    lines.append(f"- grid P_6 nonzero fraction: {frac_nonzero:.2f}")
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items()
                      if k != "horizon_sweep"}, indent=2)[:800])


if __name__ == "__main__":
    import csv
    main()
