"""B8: plan-library / solver convergence (v4 gate).

Nested libraries on the committed-maneuver game:
  L11 : the 11 single-turn plans (turn over 3 turns by {0,+-30..180}, hold)
  L21 : L11 + 10 two-phase plans (turn a over turns 1-3, counter-turn -a/2
        over turns 4-6, then hold) -- smooths into oblique/evasion shapes
  L41 : L21 + 20 duration variants (same net turns but executed over 2 or 6
        turns instead of 3)

Gate (v4): on >= 80% of test points,
  |V_41 - V_21| / max(1, |V_41|) < 5%;
regime label stable on >= 85% of points.  Otherwise: enlarge library /
move to MPC / drop the "optimal" wording.

Test points: (eta_v, eta_r) in {0.8, 1.0, 1.33}^2 x 3 geometries = 27 cells.

Output: research/results/b8/{cells.csv, results.json, report.md}
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
    open_loop_minimax,
)
from research.geometry.firepower_kernel import KernelFit  # noqa: E402

OUT = REPO / "research" / "results" / "b8"
HORIZON = 40


def build_libraries():
    n = HORIZON

    def plan(net_turn, over=3):
        rate = net_turn / over
        return [rate] * over + [0.0] * (n - over)

    L11 = {}
    for t in (0, 30, 60, 90, 120, 180, -30, -60, -90, -120, -180):
        L11[f"t{t:+d}" if t else "straight"] = plan(t)
    L21 = dict(L11)
    for t in (15, 45, 75, 105, 150, -15, -45, -75, -105, -150):
        L21[f"t{t:+d}_3"] = plan(t)
    L41 = dict(L21)
    for t in (30, 60, 90, 120, -30, -60, -90, -120, 180, -180):
        L41[f"t{t:+d}_2"] = plan(t, over=2)
        L41[f"t{t:+d}_6"] = plan(t, over=6)
    return L11, L21, L41


def value(kB, kR, lib, brg, hB, hR, vB, vR):
    return open_loop_minimax(kB, kR, lib, r0=16, bearing0_deg=brg,
                             headingB0_deg=hB, headingR0_deg=hR,
                             vB=vB, vR=vR, steps=HORIZON)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fits = json.load(open(REPO / "research" / "results" / "e01" / "kernel_fits.json"))
    base_fit = KernelFit.from_dict(fits["CA"])
    L11, L21, L41 = build_libraries()

    GEOM = {"head_on": (0.0, 0.0, 180.0),
            "parallel": (90.0, 0.0, 0.0),
            "crossing": (45.0, 0.0, 180.0)}
    cells = []
    for eta_v in (0.8, 1.0, 1.33):
        for eta_r in (0.75, 1.0, 1.33):
            kB = KernelWrap(base_fit, range_ratio=eta_r)
            kR = KernelWrap(base_fit)
            for gname, (brg, hB, hR) in GEOM.items():
                r11 = value(kB, kR, L11, brg, hB, hR, 6.0 * eta_v, 6.0)
                r21 = value(kB, kR, L21, brg, hB, hR, 6.0 * eta_v, 6.0)
                r41 = value(kB, kR, L41, brg, hB, hR, 6.0 * eta_v, 6.0)
                v11, v21, v41 = (r11["game_value"], r21["game_value"],
                                 r41["game_value"])
                conv = abs(v41 - v21) / max(1.0, abs(v41))
                plan_21 = v21.get if False else None
                cells.append({
                    "eta_v": eta_v, "eta_r": eta_r, "geometry": gname,
                    "V11": v11, "V21": v21,
                    "V41": v41,
                    "conv_metric": conv,
                    "conv_pass": int(conv < 0.05),
                    "plan21": r21["maximin_plan_B"],
                    "plan41": r41["maximin_plan_B"],
                    "plan_stable": int(r21["maximin_plan_B"]
                                       == r41["maximin_plan_B"]),
                })
                print(cells[-1], flush=True)

    conv_pass = int(np.mean([c["conv_pass"] for c in cells]) * 100)
    plan_stable = int(np.mean([c["plan_stable"] for c in cells]) * 100)
    gate_conv = conv_pass >= 80
    gate_plan = plan_stable >= 85
    result = {
        "n_cells": len(cells),
        "conv_pass_fraction": conv_pass / 100,
        "plan_stable_fraction": plan_stable / 100,
        "gate": "PASS" if (gate_conv and gate_plan) else "FAIL",
        "gate_detail": {"convergence>=80%": gate_conv,
                        "plan stability>=85%": gate_plan},
        "libraries": {"L11": len(L11), "L21": len(L21), "L41": len(L41)},
        "horizon": HORIZON,
    }
    (OUT / "results.json").write_text(json.dumps(result, indent=2),
                                      encoding="utf-8")
    with (OUT / "cells.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cells[0].keys())
        for c in cells:
            w.writerow(c.values())
    lines = ["# B8 plan-library convergence", "",
             f"- convergence gate (|V41-V21|/max(1,|V41|)<5%): {conv_pass}% of "
             f"{len(cells)} cells (gate 80%)",
             f"- maximin plan stability: {plan_stable}% (gate 85%)",
             f"- gate: {'PASS' if result['gate'] == 'PASS' else 'FAIL'}",
             "", "| eta_v | eta_r | geometry | V11 | V21 | V41 | conv | plan21 | plan41 |",
             "|---|---|---|---|---|---|---|---|---|"]
    for c in cells:
        lines.append("| {eta_v} | {eta_r} | {geometry} | {V11:.3f} | "
                     "{V21:.3f} | {V41:.3f} | {conv_metric:.3f} | "
                     "{plan21} | {plan41} |".format(**c))
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    import csv
    main()
