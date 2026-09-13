"""B4: speed-capability monotonicity (B4.1) + operating-speed reclassification (B4.2).

B4.1 (new experiment): plans are (heading sequence, speed tier v in {2,4,6})
pairs; capability vbar restricts tiers to {v <= vbar} giving nested control
sets U(2) c U(4) c U(6).  Opponent capability fixed at vbar_R = 6.  Gate
(preregistered): V(6) >= V(4) >= V(2) within LP tolerance — no decrease.
By the minimax theorem this MUST hold for nested row sets of the same
payoff matrix; any decrease triggers the debugging protocol (nesting audit,
LP duality check, speed-forcing audit), never a "speed paradox" claim.

B4.2 (reclassification, no re-run): the v3/E02 eta_v sweep measured the
FIXED OPERATING SPEED semantics; its results are re-labelled as the
"operating-speed effect" per research/audit_v4/speed_semantics.md and
tabulated against the B4.1 capability numbers.

Outputs under research/results/b4/.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

from research.geometry.firepower_kernel import KernelFit  # noqa: E402
from research.geometry.committed_game import KernelWrap  # noqa: E402
from research.geometry.speed_capability import (  # noqa: E402
    SPEED_TIERS,
    capability_values,
    make_speed_plan_library,
    payoff_matrix,
    payoff_matrix_actual_speed,
    plan_keys_for_capability,
)

OUT = REPO / "research" / "results" / "b4"

GEOMETRIES = {
    # name: (bearing of R from B, heading B, heading R) — same as E02
    "head_on": (0.0, 0.0, 180.0),
    "parallel": (90.0, 0.0, 0.0),
}
ETA_R_SWEEP = (0.75, 1.0, 1.33)
R0 = 16.0
STEPS = 40
GAMMA = 0.96
LP_TOL = 1e-8
ETA_V_OPERATING = (0.8, 1.0, 1.25)  # B4.2 extraction from the E02 sweep


def run_b41(fit: KernelFit) -> dict:
    """B4.1 main grid: 2 geometries x 3 range-ratio cells, nested LP values."""
    lib = make_speed_plan_library()
    keysR = plan_keys_for_capability(lib, 6.0)
    rows_out: list[dict] = []
    cells: dict[str, dict] = {}
    for gname, (brg, hB, hR) in GEOMETRIES.items():
        for eta_r in ETA_R_SWEEP:
            t0 = time.time()
            kB = KernelWrap(fit, range_ratio=eta_r, firepower_ratio=1.0)
            kR = KernelWrap(fit, range_ratio=1.0, firepower_ratio=1.0)
            keysB = keysR  # B evaluated at full library; slices give U(vbar)
            pay = payoff_matrix(kB, kR, lib, keysB, keysR, R0, brg, hB, hR,
                                STEPS, GAMMA)
            cap = capability_values(pay, keysB, SPEED_TIERS, LP_TOL)
            cells[f"{gname}_etar{eta_r}"] = {"cap": cap}
            for ci, c in enumerate(cap["cells"]):
                rows_out.append({
                    "geometry": gname, "eta_r": eta_r,
                    "vbar": c["vbar"], "n_plans": c["n_plans"],
                    "V_lp": c["V_lp"], "V_dual": c["V_dual"],
                    "duality_gap": c["duality_gap"],
                    "min_eq_slack": c["min_eq_slack"],
                    "support_size": c["support_size"],
                    "support_speed_tiers": "|".join(str(int(s)) for s in c["support_speed_tiers"]),
                    "V_pure_maximin": c["V_pure_maximin"], "V_pure_minimax": c["V_pure_minimax"],
                    "nesting_bitexact": c["nesting_bitexact"],
                    "increment_vs_prev": ("" if ci == 0 else
                                          f"{c['V_lp'] - cap['cells'][ci - 1]['V_lp']:+.3e}"),
                })
            print(f"  b4.1 {gname} eta_r={eta_r}: V = "
                  f"{['%.6f' % c['V_lp'] for c in cap['cells']]} "
                  f"({time.time() - t0:.1f}s)")
    return {"cells": cells, "rows": rows_out}


def run_b41_sensitivity(fit: KernelFit) -> list[dict]:
    """Actual-speed firing channel: does the monotonicity gate survive?"""
    lib = make_speed_plan_library()
    keys = plan_keys_for_capability(lib, 6.0)
    out = []
    for gname, (brg, hB, hR) in GEOMETRIES.items():
        kB = KernelWrap(fit, range_ratio=1.0, firepower_ratio=1.0)
        kR = KernelWrap(fit, range_ratio=1.0, firepower_ratio=1.0)
        pay = payoff_matrix_actual_speed(kB, kR, lib, keys, keys,
                                         R0, brg, hB, hR, STEPS, GAMMA)
        cap = capability_values(pay, keys, SPEED_TIERS, LP_TOL)
        out.append({"geometry": gname, "channel": "actual_target_speed",
                    "cells": cap["cells"],
                    "monotone_within_tol": cap["monotone_within_tol"],
                    "max_decrease": cap["max_decrease"]})
        print(f"  b4.1-sens {gname}: V = "
              f"{['%.6f' % c['V_lp'] for c in cap['cells']]}")
    return out


def load_b42_operating_speed() -> list[dict]:
    """B4.2: extract the fixed-operating-speed sweep from the E02 results.

    Deterministic protocol (LP over a fixed matrix, no RNG): the stored
    phase_diagram.csv IS the experiment record; per v4 batch discipline it
    is cited, not re-run (a one-cell determinism re-check is logged in the
    report if present).
    """
    src = REPO / "research" / "results" / "e02" / "phase_diagram.csv"
    rows = []
    with src.open() as fh:
        for r in csv.DictReader(fh):
            if abs(float(r["eta_r"]) - 1.0) > 1e-9:
                continue
            if float(r["eta_v"]) not in ETA_V_OPERATING:
                continue
            rows.append({
                "protocol": "fixed_operating_speed (E02)",
                "geometry": r["geometry"], "eta_v": float(r["eta_v"]),
                "eta_r": float(r["eta_r"]),
                "game_value": float(r["game_value"]),
                "pure_value": float(r["pure_value"]),
                "maximin_plan_B": r["maximin_plan_B"],
                "minimax_plan_R": r["minimax_plan_R"],
                "regime": r["regime"],
            })
    return sorted(rows, key=lambda r: (r["geometry"], r["eta_v"]))


def main() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    OUT.mkdir(parents=True, exist_ok=True)
    fits = json.load(open(REPO / "research" / "results" / "e01" / "kernel_fits.json"))
    fit = KernelFit.from_dict(fits["CA"])

    print("B4.1 speed-capability monotonicity (nested control sets) ...")
    b41 = run_b41(fit)
    print("B4.1 sensitivity (actual-speed firing channel) ...")
    b41_sens = run_b41_sensitivity(fit)
    print("B4.2 operating-speed reclassification (citing E02) ...")
    b42 = load_b42_operating_speed()

    # ---------------- persistence: raw CSV ----------------
    cols = ["geometry", "eta_r", "vbar", "n_plans", "V_lp", "V_dual",
            "duality_gap", "min_eq_slack", "support_size", "support_speed_tiers",
            "V_pure_maximin", "V_pure_minimax", "nesting_bitexact",
            "increment_vs_prev"]
    with (OUT / "b41_monotonicity.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in b41["rows"]:
            w.writerow({c: r[c] for c in cols})

    with (OUT / "b42_operating_speed_e02.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(b42[0].keys()))
        w.writeheader()
        for r in b42:
            w.writerow(r)

    # semantics contrast table: two protocols side by side
    contrast = []
    for g in GEOMETRIES:
        for ev in ETA_V_OPERATING:
            op = next(r for r in b42
                      if r["geometry"] == g and r["eta_v"] == ev)
            contrast.append({
                "geometry": g,
                "eta_v_operating": ev,
                "V_operating (E02, speed forced)": op["game_value"],
                "note_operating": "speed = constant parameter, no speed action",
                "V_capability vbar=2 (B4.1)": "",
                "V_capability vbar=4 (B4.1)": "",
                "V_capability vbar=6 (B4.1)": "",
                "note_capability": "speed = plan-chosen tier, U(vbar) nested",
            })
    # fill capability values from the eta_r=1.0 cells
    for row in contrast:
        g = row["geometry"]
        for c in b41["cells"][f"{g}_etar1.0"]["cap"]["cells"]:
            row[f"V_capability vbar={int(c['vbar'])} (B4.1)"] = c["V_lp"]
    with (OUT / "b42_semantics_contrast.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(contrast[0].keys()))
        w.writeheader()
        for r in contrast:
            w.writerow(r)

    # ---------------- gate evaluation ----------------
    gate = {"per_cell": [], "pass": True}
    for key, cell in b41["cells"].items():
        cap = cell["cap"]
        ok = cap["monotone_within_tol"] and all(c["nesting_bitexact"]
                                                for c in cap["cells"])
        gate["per_cell"].append({"cell": key, "monotone_within_tol":
                                 cap["monotone_within_tol"],
                                 "max_decrease": cap["max_decrease"],
                                 "nesting_bitexact": all(
                                     c["nesting_bitexact"] for c in cap["cells"])})
        gate["pass"] = gate["pass"] and ok
    for s in b41_sens:
        gate["per_cell"].append({"cell": f"{s['geometry']} (actual-speed)",
                                 "monotone_within_tol": s["monotone_within_tol"],
                                 "max_decrease": s["max_decrease"],
                                 "nesting_bitexact": True})
        gate["pass"] = gate["pass"] and s["monotone_within_tol"]

    # ---------------- figures ----------------
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.3))
    for ax, eta_r in zip(axes, ETA_R_SWEEP):
        for g, (brg, hB, hR) in GEOMETRIES.items():
            cells = b41["cells"][f"{g}_etar{eta_r}"]["cap"]["cells"]
            ax.plot([c["vbar"] for c in cells], [c["V_lp"] for c in cells],
                    marker="o", label=g)
            ax.plot([c["vbar"] for c in cells],
                    [c["V_pure_maximin"] for c in cells],
                    marker="s", ls="--", alpha=0.5)
        ax.axhline(0, color="k", lw=0.6, ls=":")
        ax.set_title(f"$\\eta_r={eta_r}$")
        ax.set_xlabel(r"speed capability $\bar v$")
        ax.set_xticks(list(SPEED_TIERS))
    axes[0].set_ylabel("open-loop maximin value V")
    axes[-1].legend(["head_on (LP)", "parallel (LP)",
                     "head_on (pure)", "parallel (pure)"], fontsize=8)
    fig.suptitle("B4.1 speed-capability monotonicity: nested control sets "
                 r"$U(\bar v=2)\subset U(\bar v=4)\subset U(\bar v=6)$, "
                 r"$\bar v_R=6$")
    fig.tight_layout()
    fig.savefig(OUT / "fig_b41_monotonicity.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    # B4.2 contrast figure: operating-speed curve vs capability steps
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
    for ax, g in zip(axes, GEOMETRIES):
        op = [r["game_value"] for r in b42 if r["geometry"] == g]
        ax.plot(ETA_V_OPERATING, op, "o-", label="operating speed (E02 protocol)")
        cells = b41["cells"][f"{g}_etar1.0"]["cap"]["cells"]
        ax.step([c["vbar"] / 6.0 for c in cells], [c["V_lp"] for c in cells],
                where="post", marker="s", label="capability (B4.1, speed tier/6)")
        ax.axhline(0, color="k", lw=0.6, ls=":")
        ax.set_title(g)
        ax.set_xlabel(r"speed ratio $\eta_v$ / capability tier $\bar v/6$")
    axes[0].set_ylabel("open-loop maximin value V")
    axes[0].legend(fontsize=8)
    fig.suptitle("B4.2 two speed semantics: fixed operating speed vs "
                 "nested speed capability")
    fig.tight_layout()
    fig.savefig(OUT / "fig_b42_semantics_contrast.png", dpi=160,
                bbox_inches="tight")
    plt.close(fig)

    # ---------------- results.json ----------------
    results = {
        "batch": "B4 (v4.0): speed-capability monotonicity + operating-speed reclassification",
        "protocol": {
            "speed_tiers": list(SPEED_TIERS),
            "nested_sets": {"vbar2": [2], "vbar4": [2, 4], "vbar6": [2, 4, 6]},
            "opponent_capability_vbar_R": 6,
            "geometries": {k: list(v) for k, v in GEOMETRIES.items()},
            "r0": R0, "steps": STEPS, "gamma": GAMMA,
            "heading_library": "make_maneuver_library() (11 committed heading plans, unchanged)",
            "firing_channel": "E02 proxy convention: kernel target-speed arg = constant 6 "
                              "(engine-neutral for v>=4); capability acts via kinematics only",
            "lp_tolerance": LP_TOL,
        },
        "b41_cells": {k: v["cap"] for k, v in b41["cells"].items()},
        "b41_sensitivity_actual_speed": b41_sens,
        "b42_operating_speed_rows": b42,
        "b42_contrast_table": contrast,
        "gate": gate,
    }
    (OUT / "results.json").write_text(json.dumps(results, indent=2),
                                      encoding="utf-8")
    print("gate:", "PASS" if gate["pass"] else "FAIL")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
