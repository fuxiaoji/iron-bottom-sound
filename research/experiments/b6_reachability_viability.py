"""B6: reachability / viability thresholds for the favorable set G_alpha.

Operationalization on the committed-maneuver game (open loop):
- favorable state G_alpha: L(t) >= alpha at a step;
- Reachability (B6.2): B commits its maximin plan; the metric is
  min over ALL of R's library plans of max_t L(t)  (worst-case peak).
  Reachable at level alpha iff worst-case peak >= alpha.
- Viability (B6.3): min over R's plans of the fraction of steps with
  L(t) >= alpha (worst-case holding share).  Viable at (alpha, tau)
  iff worst-case share >= tau.
- Threshold (B6.4): eta_v^*(eta_omega, alpha) = smallest speed ratio at
  which reachability/viability holds, for B turn-rate scaling
  eta_omega in {0.7, 1.0, 1.3} (B's plan turn magnitudes scaled; clipped
  to the engine's 60 deg/turn granularity).

Output: research/results/b6/{thresholds.csv, viability_curves.csv,
results.json, report.md, fig_b6_thresholds.png}
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
    simulate,
)
from research.geometry.firepower_kernel import KernelFit  # noqa: E402

OUT = REPO / "research" / "results" / "b6"
ALPHA = 0.5
TAU = 0.5
ETA_V_GRID = [round(0.75 + 0.05 * i, 2) for i in range(16)]  # 0.75 .. 1.50
ETA_OMEGA = [0.7, 1.0, 1.3]
GEOMETRIES = {
    "head_on": (0.0, 0.0, 180.0),
    "parallel": (90.0, 0.0, 0.0),
    "crossing": (45.0, 0.0, 180.0),
}


def scaled_library(base, eta_omega: float):
    lib = {}
    for name, plan in base.items():
        lib[name] = [min(60.0, max(-60.0, d * eta_omega)) for d in plan]
    return lib


def main() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    OUT.mkdir(parents=True, exist_ok=True)
    fits = json.load(open(REPO / "research" / "results" / "e01" / "kernel_fits.json"))
    base_fit = KernelFit.from_dict(fits["CA"])
    base_lib = make_maneuver_library()
    r_lib = make_maneuver_library()  # R's option set (fixed, unscaled)

    rows = []
    perplan_rows = []
    for eta_omega in ETA_OMEGA:
        lib_b = scaled_library(base_lib, eta_omega)
        for gname, (brg, hB, hR) in GEOMETRIES.items():
            for eta_v in ETA_V_GRID:
                kB = KernelWrap(base_fit)
                kR = KernelWrap(base_fit)
                # B's maximin plan under this configuration
                mm = open_loop_minimax(kB, kR, lib_b, r0=16, bearing0_deg=brg,
                                       headingB0_deg=hB, headingR0_deg=hR,
                                       vB=6.0 * eta_v, vR=6.0, steps=40)
                plan_b = lib_b[mm["maximin_plan_B"]]
                # scale-free favorable-set metric: L thresholds are defined
                # RELATIVE to the cooperative peak (best-case R), so the
                # criterion is comparable across geometries and ranges
                per_plan = []
                for name_r, plan_r in r_lib.items():
                    out = simulate(kB, kR, plan_b, plan_r, 16, brg, hB, hR,
                                   6.0 * eta_v, 6.0, 40)
                    Ls = [p["L"] for p in out["trajectory"]]
                    per_plan.append((name_r, Ls))
                peak_coop = max(max(Ls) for _n, Ls in per_plan)
                ref = max(peak_coop, 1e-9)
                worst_peak_ratio = min(max(Ls) / ref for _n, Ls in per_plan)
                worst_share_ratio = min(
                    sum(1 for x in Ls if x >= ALPHA * ref) / len(Ls)
                    for _n, Ls in per_plan)
                reachable = worst_peak_ratio >= ALPHA
                viable = worst_share_ratio >= TAU
                worst_peak = worst_peak_ratio
                worst_share = worst_share_ratio
                worst_name = min(per_plan, key=lambda t: max(t[1]) / ref)[0]
                rows.append({"eta_v": eta_v, "eta_omega": eta_omega,
                             "geometry": gname,
                             "worst_peak": round(worst_peak, 4),
                             "worst_share": round(worst_share, 4),
                             "reachable": int(reachable),
                             "viable": int(viable),
                             "worst_R_plan": worst_name})
                for name_r, Ls in per_plan:
                    perplan_rows.append({
                        "eta_v": eta_v, "eta_omega": eta_omega,
                        "geometry": gname, "R_plan": name_r,
                        "peak_ratio": round(max(Ls) / ref, 4),
                        "share_ratio": round(
                            sum(1 for x in Ls if x >= ALPHA * ref) / len(Ls), 4)})
                print(rows[-1], flush=True)

    with (OUT / "thresholds.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(rows[0].keys())
        for r in rows:
            w.writerow(r.values())
    with (OUT / "perplan_distribution.csv").open("w", newline="",
                                                 encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(perplan_rows[0].keys())
        for r in perplan_rows:
            w.writerow(r.values())

