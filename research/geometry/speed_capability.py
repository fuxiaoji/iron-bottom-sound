"""B4.1: speed-CAPABILITY monotonicity over nested control sets.

Semantics (v4 B0 audit, research/audit_v4/speed_semantics.md): E02's "speed
paradox" was measured under a FIXED OPERATING SPEED protocol — speed is a
constant parameter chosen by the experimenter, never by the plan.  B4.1
promotes speed to a capability: a committed plan is now a pair
(heading sequence, constant speed tier v) and a capability level vbar
restricts the admissible tiers to {v : v <= vbar}, giving nested control
sets

    U(vbar=2) = {2}  subset  U(vbar=4) = {2,4}  subset  U(vbar=6) = {2,4,6}.

For nested row sets of the SAME payoff matrix (same initial geometry, same
opponent capability vbar_R = 6) the matrix-game value is monotone
non-decreasing in vbar by the minimax theorem.  The experiment therefore
VERIFIES a theorem numerically (gate: no decrease beyond LP tolerance);
any observed decrease is a numerical/procedural artifact to be debugged
(nesting broken, LP degeneracy, or speed forced by the plan family) and
must never be reported as a "speed paradox".

The firing channel is held at the E02 proxy convention (kernel target-speed
argument = the constant speed0B/speed0R = 6, engine-neutral for v >= 4), so
the capability acts through the reachable-position channel only.  A local
sensitivity variant `simulate_actual_speed` re-runs cells with the actual
per-plan target speed passed to the kernel — the nesting theorem holds for
ANY fixed payoff matrix, so this only rescales the capability value gains.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from research.geometry.committed_game import (
    KernelWrap,
    make_maneuver_library,
    simulate,
    solve_matrix_game,
    wrap_deg,
)

SPEED_TIERS = (2.0, 4.0, 6.0)


def make_speed_plan_library(
    headings: dict[str, list[float]] | None = None,
    tiers: tuple[float, ...] = SPEED_TIERS,
) -> dict[str, tuple[list[float], float]]:
    """Plan = (committed heading sequence, constant speed tier)."""
    if headings is None:
        headings = make_maneuver_library()
    lib: dict[str, tuple[list[float], float]] = {}
    for name, plan in headings.items():
        for v in tiers:
            lib[f"{name}@v{int(v)}"] = (plan, v)
    return lib


def plan_keys_for_capability(
    lib: dict[str, tuple[list[float], float]], vbar: float
) -> list[str]:
    """Nested admissible set U(vbar) = {plans with speed tier v <= vbar}."""
    return [k for k, (_, v) in lib.items() if v <= vbar + 1e-9]


def payoff_matrix(kB: KernelWrap, kR: KernelWrap,
                  lib: dict[str, tuple[list[float], float]],
                  keysB: list[str], keysR: list[str],
                  r0: float, bearing0_deg: float, headingB0_deg: float,
                  headingR0_deg: float, steps: int = 40,
                  gamma: float = 0.96) -> np.ndarray:
    pay = np.zeros((len(keysB), len(keysR)))
    for i, kb_ in enumerate(keysB):
        planB, vB = lib[kb_]
        for j, kr_ in enumerate(keysR):
            planR, vR = lib[kr_]
            pay[i, j] = simulate(kB, kR, planB, planR, r0, bearing0_deg,
                                 headingB0_deg, headingR0_deg, vB, vR,
                                 steps, gamma)["payoff_B"]
    return pay


def lp_diagnostics(pay: np.ndarray) -> dict:
    """Independent dual-side LP + equilibrium residuals for the matrix game.

    solve_matrix_game returns max_x min_j x^T P[:, j].  The dual solves
    min_y max_i (P y)_i from R's side; at optimality the two values coincide
    (duality gap ~ 0 up to LP tolerance).  Also reports the violated
    equilibrium constraints of the returned primal solution.
    """
    from scipy.optimize import linprog

    m, n = pay.shape
    # primal (B side): maximize v s.t. x^T P >= v, sum x = 1, x >= 0
    pri = solve_matrix_game(pay)
    # dual (R side): minimize w s.t. P y <= w, sum y = 1, y >= 0
    c = np.zeros(n + 1)
    c[-1] = 1.0
    A_ub = np.zeros((m, n + 1))
    A_ub[:, :n] = pay
    A_ub[:, n] = -1.0
    b_ub = np.zeros(m)
    A_eq = np.zeros((1, n + 1))
    A_eq[0, :n] = 1.0
    b_eq = [1.0]
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=[(0, None)] * n + [(None, None)])
    w = float(res.x[-1]) if res.success else float("nan")
    gap = abs(pri["value"] - w) if res.success else float("nan")
    diag = {"primal_value": pri["value"], "dual_value": w,
            "duality_gap": gap, "primal_pure": pri["pure"]}
    x = np.asarray(pri["x"], dtype=float)
    if x.size:
        slack = x @ pay - pri["value"]          # B's equilibrium inequalities
        diag["min_eq_slack"] = float(np.min(slack))   # >= -tol expected
        diag["support"] = int(np.sum(x > 1e-9))
    return diag


def capability_values(pay_full: np.ndarray, keysB: list[str],
                      vbars: tuple[float, ...] = (2.0, 4.0, 6.0),
                      lp_tol: float = 1e-8) -> dict:
    """LP value V(vbar) over the nested row slices of one payoff matrix.

    Asserts exact nesting (a lower-capability row block is bit-identical in
    the bigger matrix — guaranteed by deterministic simulate) and checks
    V(vbar) non-decreasing within `lp_tol`.
    """
    out: dict = {"vbars": list(vbars), "cells": []}
    prev_rows: list[int] | None = None
    prev_pay_rows: np.ndarray | None = None
    for vbar in vbars:
        keys = [k for k in keysB if float(k.split("@v")[1]) <= vbar + 1e-9]
        idx = [keysB.index(k) for k in keys]
        rows = pay_full[idx, :]
        # (a) nesting audit: the smaller row set must be a prefix-identical
        # subset of the previous (bigger) row set — bit-exact.
        nesting_ok = True
        if prev_rows is not None:
            sub = [i for i in idx if i in prev_rows]
            nesting_ok = (len(sub) == len(prev_rows) and np.array_equal(
                pay_full[sub, :], prev_pay_rows))
        diag = lp_diagnostics(rows)
        pri = solve_matrix_game(rows)
        support = sorted({float(k.split("@v")[1]) for xi, k in zip(pri["x"], keys)
                          if xi > 1e-9}) if pri.get("x") else []
        out["cells"].append({
            "vbar": vbar, "n_plans": len(idx),
            "V_lp": diag["primal_value"], "V_dual": diag["dual_value"],
            "duality_gap": diag["duality_gap"], "min_eq_slack": diag["min_eq_slack"],
            "support_size": diag["support"],
            "support_speed_tiers": support,
            "V_pure_maximin": float(rows.min(axis=1).max()),
            "V_pure_minimax": float(rows.max(axis=0).min()),
            "nesting_bitexact": bool(nesting_ok),
        })
        prev_rows, prev_pay_rows = idx, rows
    vals = [c["V_lp"] for c in out["cells"]]
    diffs = [vals[i + 1] - vals[i] for i in range(len(vals) - 1)]
    out["increments"] = diffs
    out["max_decrease"] = min(diffs) if diffs else 0.0
    out["monotone_within_tol"] = bool(out["max_decrease"] >= -lp_tol)
    return out


def simulate_actual_speed(kB: KernelWrap, kR: KernelWrap,
                          planB: list[float], planR: list[float],
                          r0: float, bearing0_deg: float, headingB0_deg: float,
                          headingR0_deg: float, vB: float, vR: float,
                          steps: int = 40, gamma: float = 0.96,
                          speed0B: int = 6, speed0R: int = 6,
                          world_scale: float = 1.0) -> dict:
    """Sensitivity twin of committed_game.simulate (unmodified original).

    Identical kinematics and payoff accumulation, but the kernel's
    target-speed argument receives the plan's ACTUAL operating speed
    (clipped to the kernel's 0..5 support) instead of the constant 6.
    """
    xB = yB = 0.0
    xR, yR = world_scale * r0 * math.cos(math.radians(bearing0_deg)), \
        world_scale * r0 * math.sin(math.radians(bearing0_deg))
    hB, hR = float(headingB0_deg), float(headingR0_deg)
    speedB, speedR = speed0B * vB / 6.0, speed0R * vR / 6.0
    cum = 0.0
    disc = 1.0
    traj = []
    T = min(steps, len(planB), len(planR))
    for t in range(T):
        dx, dy = xR - xB, yR - yB
        r = max(math.hypot(dx, dy), 0.5)
        bearing = math.degrees(math.atan2(dy, dx))
        delta_B = float(wrap_deg(bearing - hB))
        delta_R = float(wrap_deg(bearing + 180.0 - hR))

        def aspect(d):
            a = abs(wrap_deg(d))
            return "bow_stern" if (a <= 30.0 or a >= 150.0) else "broadside"

        L = (kB.fire(r, delta_B, int(np.clip(speedR, 0, 5)), aspect(delta_R))
             - kR.fire(r, delta_R, int(np.clip(speedB, 0, 5)), aspect(delta_B)))
        cum += disc * L
        disc *= gamma
        traj.append({"t": t, "r": round(r, 2), "L": round(L, 4)})
        hB = wrap_deg(hB + planB[t])
        hR = wrap_deg(hR + planR[t])
        xB += speedB * math.cos(math.radians(hB))
        yB += speedB * math.sin(math.radians(hB))
        xR += speedR * math.cos(math.radians(hR))
        yR += speedR * math.sin(math.radians(hR))
    return {"payoff_B": cum, "trajectory": traj}


def payoff_matrix_actual_speed(kB: KernelWrap, kR: KernelWrap,
                               lib: dict[str, tuple[list[float], float]],
                               keysB: list[str], keysR: list[str],
                               r0: float, bearing0_deg: float,
                               headingB0_deg: float, headingR0_deg: float,
                               steps: int = 40, gamma: float = 0.96) -> np.ndarray:
    pay = np.zeros((len(keysB), len(keysR)))
    for i, kb_ in enumerate(keysB):
        planB, vB = lib[kb_]
        for j, kr_ in enumerate(keysR):
            planR, vR = lib[kr_]
            pay[i, j] = simulate_actual_speed(
                kB, kR, planB, planR, r0, bearing0_deg, headingB0_deg,
                headingR0_deg, vB, vR, steps, gamma)["payoff_B"]
    return pay
