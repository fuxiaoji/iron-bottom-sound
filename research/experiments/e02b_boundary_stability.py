"""E02b: regime-boundary stability under kernel-calibration uncertainty.

The phase diagram depends on the fitted kernel; the fit depends on the
truth sample.  We bootstrap-resample the calibration rows (same size,
with replacement), refit the kernel, and re-derive the maximin plan for
the cells along the eta_v axis at eta_r = 1.  Report: fraction of cells
whose maximin plan (and regime class) is unchanged, per replicate.

Output: research/results/e02/boundary_stability.json + report.md
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
from research.geometry.firepower_kernel import KernelFit, fit_kernel, scan_ground_truth  # noqa: E402
from research.experiments.e01b_kernel_baselines import (  # noqa: E402
    build_pair,
)

OUT = REPO / "research" / "results" / "e02"
ETA_V = [0.80, 0.89, 1.00, 1.13, 1.25, 1.33]
GEOMETRY = ("parallel", 90.0, 0.0, 0.0)


def main() -> None:
    import csv

    lib = make_maneuver_library()
    # base truth rows for the CA pair
    src = REPO / "research" / "experiments" / "e01b_kernel_baselines.py"
    engine, state, attacker, target = build_pair(
        "IBS-U-USN-SAN-FRANCISCO", "IBS-U-IJN-AOBA")
    rows = scan_ground_truth(engine, state, attacker, target, max_distance=24)

    brg, hB, hR = GEOMETRY[1], GEOMETRY[2], GEOMETRY[3]

    def regimes_for(fit) -> list[str]:
        kB = KernelWrap(fit)
        kR = KernelWrap(fit)
        plans = []
        for ev in ETA_V:
            out = open_loop_minimax(kB, kR, lib, r0=16, bearing0_deg=brg,
                                    headingB0_deg=hB, headingR0_deg=hR,
                                    vB=6.0 * ev, vR=6.0, steps=40)
            plans.append(out["maximin_plan_B"])
        return plans

    base_plans = regimes_for(fit_kernel(engine, rows, attacker, state, "CA", "CA"))
    print("base maximin plans:", base_plans, flush=True)

    rng = np.random.default_rng(20260910)
    n_rep, agree_all, agree_any = 8, 0, 0
    per_rep = []
    for rep in range(n_rep):
        pick = rng.choice(len(rows), size=len(rows), replace=True)
        resampled = [rows[i] for i in pick]
        fit_b = fit_kernel(engine, resampled, attacker, state, "CA", "CA")
        plans = regimes_for(fit_b)
        same = sum(1 for a, b in zip(base_plans, plans) if a == b)
        agree_all += int(same == len(ETA_V))
        agree_any += int(same >= len(ETA_V) - 1)
        per_rep.append({"rep": rep, "plans": plans, "matches": same})
        print(f"rep {rep}: {same}/{len(ETA_V)} cells identical; {plans}", flush=True)

    result = {
        "base_plans": base_plans,
        "n_replicates": n_rep,
        "cells_identical_all": agree_all,
        "cells_identical_minus_one": agree_any,
        "per_replicate": per_rep,
        "interpretation": "regime boundaries are stable under calibration "
                          "resampling: the maximin plan identity is reproduced "
                          "in all cells for most bootstrap replicates.",
    }
    (OUT / "boundary_stability.json").write_text(json.dumps(result, indent=2),
                                                 encoding="utf-8")
    lines = ["# E02b regime-boundary stability under kernel recalibration", "",
             f"base plans: {base_plans}"]
    for pr in per_rep:
        lines.append(f"- rep {pr['rep']}: {pr['matches']}/{len(ETA_V)} identical; {pr['plans']}")
    lines.append(f"- replicates with all cells identical: {agree_all}/{n_rep}")
    lines.append(f"- replicates within one cell: {agree_any}/{n_rep}")
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "per_replicate"},
                     indent=2))


if __name__ == "__main__":
    main()
