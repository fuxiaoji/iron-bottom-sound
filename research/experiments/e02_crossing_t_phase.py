"""E02: Crossing-the-T committed-maneuver game — phase diagram + mechanism.

Experiment cells (plan section 8, E02/E03):
  eta_v in {0.80, 0.89, 1.00, 1.13, 1.25, 1.33}   speed ratio B/R
  eta_r in {0.75, 1.00, 1.33}                      gun range ratio (kernel scaling)
  eta_g = 1.0 (firepower ratio; sensitivity in a separate sweep)
Initial geometries: head-on, parallel-broadside, crossing (45 deg).
For each cell: open-loop minimax over the committed-maneuver library for each
geometry; record game value, maximin plan, regime classification, and the
fire-advantage time fraction of the saddle-point pair.

Acceptance (plan E02, adapted to the open-loop formulation):
  - regime boundaries reproducible on a fresh grid of parameter samples;
  - minimax plan's worst-case payoff >= every fixed doctrine plan's worst case;
  - symmetric parameter cells reproduce antisymmetric values (role swap).
Outputs under research/results/e02/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

from research.geometry.firepower_kernel import KernelFit  # noqa: E402
from research.geometry.committed_game import (  # noqa: E402
    KernelWrap,
    make_maneuver_library,
    open_loop_minimax,
    simulate,
    solve_matrix_game,
)

OUT = REPO / "research" / "results" / "e02"

ETA_V = [0.80, 0.89, 1.00, 1.13, 1.25, 1.33]
ETA_R = [0.75, 1.00, 1.33]
ETA_G_SWEEP = [0.80, 1.00, 1.25]

GEOMETRIES = {
    # name: (bearing of R from B, heading B, heading R)
    "head_on": (0.0, 0.0, 180.0),
    "parallel": (90.0, 0.0, 0.0),
    "crossing": (45.0, 0.0, 180.0),
}


def wrap(a):
    return (a + 180.0) % 360.0 - 180.0


def classify_regime(plan_name: str, traj: list[dict], value: float = 0.0) -> str:
    """Regime of the saddle-point engagement from the maximin plan + value."""
    if plan_name in ("turn+120", "turn+180", "turn-120", "turn-180"):
        return "disengage"
    if plan_name in ("turn+60", "turn+90", "turn-60", "turn-90"):
        return "cross_or_beam"
    if plan_name in ("turn+30", "turn-30"):
        return "oblique_duel"
    # straight: classify by the sign of the committed-closure value
    if value > 0.3:
        return "closure_advantage"
    if value < -0.3:
        return "closure_disadvantage"
    return "even_closure"


def fire_advantage_fraction(traj: list[dict], ratio: float = 1.5) -> float:
    if not traj:
        return 0.0
    hits = 0
    for p in traj:
        # reconstruct fire advantage from the trajectory L sign pattern is not
        # enough; recompute per-step fire ratio is implicit in L. Use L>0 with
        # |L| threshold as an exchange-win proxy counted per step.
        if p["L"] > 0:
            hits += 1
    return hits / len(traj)


def main() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    OUT.mkdir(parents=True, exist_ok=True)
    fits = json.load(open(REPO / "research" / "results" / "e01" / "kernel_fits.json"))
    base_fit = KernelFit.from_dict(fits["CA"])
    lib = make_maneuver_library()

    rows = []
    matrices = {}
    for eta_v in ETA_V:
        for eta_r in ETA_R:
            kB = KernelWrap(base_fit, range_ratio=eta_r, firepower_ratio=1.0)
            kR = KernelWrap(base_fit, range_ratio=1.0, firepower_ratio=1.0)
            for gname, (brg, hB, hR) in GEOMETRIES.items():
                out = open_loop_minimax(kB, kR, lib, r0=16, bearing0_deg=brg,
                                        headingB0_deg=hB, headingR0_deg=hR,
                                        vB=6.0 * eta_v, vR=6.0, steps=40)
                sim = simulate(kB, kR, lib[out["maximin_plan_B"]],
                               lib[out["minimax_plan_R"]], 16, brg, hB, hR,
                               6.0 * eta_v, 6.0, 40)
                regime = classify_regime(out["maximin_plan_B"], sim["trajectory"], out["game_value"])
                fa = fire_advantage_fraction(sim["trajectory"])
                rows.append({
                    "eta_v": eta_v, "eta_r": eta_r, "geometry": gname,
                    "game_value": out["game_value"],
                    "pure_value": out["pure_value"],
                    "maximin_plan_B": out["maximin_plan_B"],
                    "minimax_plan_R": out["minimax_plan_R"],
                    "regime": regime,
                    "fire_adv_fraction": fa,
                })
                matrices[f"eta_v{eta_v}_eta_r{eta_r}_{gname}"] = {
                    "plans": out["plans_B"], "payoff": out["payoff_matrix"]}
    # sensitivity sweep over firepower ratio at eta_v = 1.13, parallel geometry
    sens = []
    for eta_g in ETA_G_SWEEP:
        kB = KernelWrap(base_fit, range_ratio=1.0, firepower_ratio=eta_g)
        kR = KernelWrap(base_fit, range_ratio=1.0, firepower_ratio=1.0)
        brg, hB, hR = GEOMETRIES["parallel"]
        out = open_loop_minimax(kB, kR, lib, r0=16, bearing0_deg=brg,
                                headingB0_deg=hB, headingR0_deg=hR,
                                vB=6.0 * 1.13, vR=6.0, steps=40)
        sens.append({"eta_g": eta_g, "game_value": out["game_value"],
                     "maximin_plan_B": out["maximin_plan_B"]})

    # ---- symmetry / swap check at the symmetric cell ----
    kB = KernelWrap(base_fit, 1.0, 1.0)
    kR = KernelWrap(base_fit, 1.0, 1.0)
    brg, hB, hR = GEOMETRIES["crossing"]
    fwd = open_loop_minimax(kB, kR, lib, 16, brg, hB, hR, 6.0, 6.0)
    # swap: B<->R means bearing from new B = brg+180, headings swapped
    swp = open_loop_minimax(kR, kB, lib, 16, wrap(brg + 180.0), hR, hB, 6.0, 6.0)
    sym_err = abs(fwd["game_value"] + swp["game_value"])

    # ---- degeneracy proposition record (closed-loop stationary game) ----
    from research.geometry.differential_game import ReducedGame
    deg = {}
    for n_r, n_a in [(16, 12), (30, 24)]:
        gg = ReducedGame(kB, kR, n_r=n_r, n_alpha=n_a)
        gg.solve(max_sweeps=500, tol=1e-8)
        dev = float(np.max(np.abs(gg.V - gg._L)))
        deg[f"grid_{n_r}x{n_a}"] = {"max_abs_V_minus_L": dev,
                                    "sweeps": gg.sweeps}
    deg["interpretation"] = (
        "With simultaneous moves, identical instantaneous capabilities and "
        "full observability, the successor-payoff matrix is exactly "
        "skew-symmetric in (u_B, u_R); the stationary value equals the "
        "instantaneous fire differential and positional maneuvering has zero "
        "equilibrium value. Tactical geometry therefore acquires game value "
        "only under order commitment (open loop), which is what the engine's "
        "sealed-order discipline — and naval doctrine — provides.")

    # ---- fresh parameter grid: reproducibility of regime boundaries ----
    fresh = []
    for eta_v in (0.95, 1.05, 1.20):
        for eta_r in (0.85, 1.15):
            kB = KernelWrap(base_fit, range_ratio=eta_r)
            kR = KernelWrap(base_fit, 1.0)
            brg, hB, hR = GEOMETRIES["parallel"]
            out = open_loop_minimax(kB, kR, lib, 16, brg, hB, hR, 6.0 * eta_v, 6.0)
            sim = simulate(kB, kR, lib[out["maximin_plan_B"]],
                           lib[out["minimax_plan_R"]], 16, brg, hB, hR,
                           6.0 * eta_v, 6.0, 40)
            fresh.append({"eta_v": eta_v, "eta_r": eta_r,
                          "regime": classify_regime(out["maximin_plan_B"], sim["trajectory"],
                                                    out["game_value"]),
                          "value": out["game_value"]})

    # ---- persistence of outputs ----
    with (OUT / "phase_diagram.csv").open("w", encoding="utf-8") as fh:
        cols = list(rows[0].keys())
        fh.write(",".join(cols) + "\n")
        for r in rows:
            fh.write(",".join(str(r[c]) for c in cols) + "\n")
    (OUT / "payoff_matrices.json").write_text(json.dumps(matrices), encoding="utf-8")
    (OUT / "degeneracy_check.json").write_text(
        json.dumps({"degeneracy": deg, "symmetry_swap_error": sym_err,
                    "sensitivity_eta_g": sens, "fresh_grid": fresh},
                   indent=2), encoding="utf-8")

    # ---- figure 1: regime phase diagram over (eta_v, eta_r) ----
    regimes = sorted({r["regime"] for r in rows})
    cmap = {"cross_or_beam": 0, "oblique_duel": 1, "even_closure": 2,
            "closure_advantage": 3, "closure_disadvantage": 4, "disengage": 5}
    for gname in GEOMETRIES:
        grid = np.full((len(ETA_V), len(ETA_R)), np.nan)
        val = np.zeros_like(grid)
        for r in rows:
            if r["geometry"] == gname:
                grid[ETA_V.index(r["eta_v"]), ETA_R.index(r["eta_r"])] = \
                    cmap.get(r["regime"], 6)
                val[ETA_V.index(r["eta_v"]), ETA_R.index(r["eta_r"])] = \
                    r["game_value"]
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
        im0 = axes[0].imshow(grid, origin="lower", aspect="auto", cmap="tab10",
                             vmin=0, vmax=9)
        axes[0].set_xticks(range(len(ETA_R)), [str(e) for e in ETA_R])
        axes[0].set_yticks(range(len(ETA_V)), [str(e) for e in ETA_V])
        axes[0].set_xlabel(r"gun range ratio $\eta_r$")
        axes[0].set_ylabel(r"speed ratio $\eta_v$")
        axes[0].set_title(f"{gname}: tactical regime")
        for iv in range(len(ETA_V)):
            for ir_ in range(len(ETA_R)):
                axes[0].text(ir_, iv, [k for k, v in cmap.items() if v == grid[iv, ir_]][0][:8],
                             ha="center", va="center", fontsize=7)
        im1 = axes[1].imshow(val, origin="lower", aspect="auto", cmap="RdBu_r")
        axes[1].set_xticks(range(len(ETA_R)), [str(e) for e in ETA_R])
        axes[1].set_yticks(range(len(ETA_V)), [str(e) for e in ETA_V])
        axes[1].set_xlabel(r"gun range ratio $\eta_r$")
        axes[1].set_title(f"{gname}: game value")
        fig.colorbar(im1, ax=axes[1], shrink=0.85)
        fig.tight_layout()
        fig.savefig(OUT / f"fig_e02_phase_{gname}.png", dpi=160,
                    bbox_inches="tight")
        plt.close(fig)

    # ---- figure 2: speed mechanism (E03) ----
    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    for gname in GEOMETRIES:
        xs = ETA_V
        ys = [next(r["game_value"] for r in rows
                   if r["eta_v"] == e and r["eta_r"] == 1.0 and r["geometry"] == gname)
              for e in ETA_V]
        ax.plot(xs, ys, marker="o", label=gname)
    ax.axhline(0, color="k", lw=0.6, ls="--")
    ax.set_xlabel(r"speed ratio $\eta_v$")
    ax.set_ylabel("game value (B)")
    ax.set_title(r"speed advantage value by geometry ($\eta_r=1$)")
    ax.legend()
    fig.savefig(OUT / "fig_e02_speed_mechanism.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    result = {
        "symmetry_swap_error": sym_err,
        "degeneracy": deg,
        "sensitivity_eta_g": sens,
        "fresh_grid": fresh,
        "n_cells": len(rows),
    }
    (OUT / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    lines = ["# E02 committed-maneuver game", "",
             f"- swap-symmetry error at symmetric cell: {sym_err:.4f}",
             f"- closed-loop degeneracy (max|V-L|): " +
             ", ".join(f"{k}={v['max_abs_V_minus_L']:.2e}" for k, v in deg.items()
                       if k.startswith("grid")),
             f"- cells scanned: {len(rows)}", ""]
    for r in rows:
        lines.append(f"- eta_v={r['eta_v']} eta_r={r['eta_r']} {r['geometry']}: "
                     f"value={r['game_value']:+.3f} regime={r['regime']} "
                     f"B:{r['maximin_plan_B']} R:{r['minimax_plan_R']}")
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2)[:1500])
    print("... wrote", OUT)


if __name__ == "__main__":
    main()
