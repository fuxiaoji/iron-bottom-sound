"""E02: committed-maneuver (open-loop) differential game for crossing-the-T.

Why open loop?  The closed-loop stationary game with simultaneous moves,
identical instantaneous capabilities, and full observability is degenerate:
the successor-payoff matrix is exactly skew-symmetric in (u_B, u_R), so the
value collapses to the instantaneous fire differential (verified numerically
to machine precision; see research/results/e02/degeneracy_check.json).
Positional maneuvering acquires value only under COMMITMENT — orders sealed
before execution, exactly as Iron Bottom Sound (and naval doctrine) resolves
turns: both sides commit a multi-pulse maneuver, then fire.  We therefore
solve the open-loop minimax over a library of committed maneuvers, which is
the textbook open-loop differential game and matches the engine's sealed-
order discipline.

Maneuvers are heading-rate sequences; the engagement payoff accumulates the
E01-calibrated expected-hits differential along the closed-loop-free (open
loop) trajectory.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass

import numpy as np

TWO_PI = 2 * math.pi


def wrap_deg(a):
    return (np.asarray(a, dtype=float) + 180.0) % 360.0 - 180.0


class KernelWrap:
    """Adapter over an E01 KernelFit with range-ratio scaling."""

    def __init__(self, fit, range_ratio: float = 1.0, firepower_ratio: float = 1.0):
        self.fit = fit
        self.eta_r = range_ratio
        self.eta_g = firepower_ratio

    def fire(self, r_hex: float, delta_deg: float, target_speed_knots: int,
             target_aspect: str) -> float:
        r_eff = float(np.clip(r_hex / max(self.eta_r, 1e-6), 1.0, 24.0))
        v = int(np.clip(target_speed_knots, 0, 5))
        return self.eta_g * self.fit.expected_hits(r_eff, float(delta_deg), v,
                                                   target_aspect)


def make_maneuver_library() -> dict[str, list[float]]:
    """Committed heading plans: a turn executed over the first 3 turns
    (matching the engine's 3-pulse turn granularity), then straight.

    Plans are open loop — fixed at t=0 from the initial geometry, like
    sealed battle orders.  The turn family spans chase (0), oblique turns,
    beam/crossing turns (+/-90), reversal disengages (+/-180).
    """
    n = 40
    lib: dict[str, list[float]] = {}
    for turn in (0, 30, 60, 90, 120, 180, -30, -60, -90, -120, -180):
        name = f"turn{turn:+d}" if turn else "straight"
        rate = turn / 3.0
        lib[name] = [rate] * 3 + [0.0] * (n - 3)
    return lib


def simulate(kB: KernelWrap, kR: KernelWrap,
             planB: list[float], planR: list[float],
             r0: float, bearing0_deg: float, headingB0_deg: float,
             headingR0_deg: float, vB: float, vR: float,
             steps: int = 40, gamma: float = 0.96,
             speed0B: int = 6, speed0R: int = 6,
             world_scale: float = 1.0,
             fire_after_move: bool = False) -> dict:
    """Simulate one committed-plan engagement in the continuous plane.

    Headings/bearings in degrees on the true world plane; the calibrated
    kernel is queried at the resulting (distance, bearing-off-bow, aspect).
    Returns the discounted payoff for B and the trajectory.

    fire_after_move: firing-order semantics within each step.  False
    (default, historical behaviour) fires at the pre-move geometry; True
    executes the step's maneuver first and fires at the post-move geometry,
    matching the engine's MOVEMENT_RESOLUTION -> GUNNERY order (B0 audit,
    objective_semantics.md).  Default preserves all pre-B2 results.
    """
    xB = yB = 0.0
    xR, yR = world_scale * r0 * math.cos(math.radians(bearing0_deg)), \
        world_scale * r0 * math.sin(math.radians(bearing0_deg))
    hB, hR = float(headingB0_deg), float(headingR0_deg)
    speedB = speed0B * vB / 6.0
    speedR = speed0R * vR / 6.0
    cum = 0.0
    disc = 1.0
    traj = []
    T = min(steps, len(planB), len(planR))
    for t in range(T):
        if fire_after_move:
            # engine order: MOVEMENT_RESOLUTION -> GUNNERY.  Execute the
            # step's maneuver first, then fire at the post-move geometry.
            hB = wrap_deg(hB + planB[t])
            hR = wrap_deg(hR + planR[t])
            xB += speedB * math.cos(math.radians(hB))
            yB += speedB * math.sin(math.radians(hB))
            xR += speedR * math.cos(math.radians(hR))
            yR += speedR * math.sin(math.radians(hR))
        # fire at the current geometry (gunnery phase follows movement in the
        # engine; with one-step plans this ordering is equivalent up to one turn)
        dx, dy = xR - xB, yR - yB
        r = math.hypot(dx, dy)
        if r < 0.5:
            r = 0.5
        bearing = math.degrees(math.atan2(dy, dx))
        delta_B = float(wrap_deg(bearing - hB))            # target off B's bow
        delta_R = float(wrap_deg(bearing + 180.0 - hR))    # target off R's bow
        def aspect(d):
            a = abs(wrap_deg(d))
            return "bow_stern" if (a <= 30.0 or a >= 150.0) else "broadside"
        L = (kB.fire(r, delta_B, speed0R, aspect(delta_R))
             - kR.fire(r, delta_R, speed0B, aspect(delta_B)))
        cum += disc * L
        disc *= gamma
        traj.append({"t": t, "r": round(r, 2), "deltaB": round(delta_B, 1),
                     "deltaR": round(delta_R, 1), "L": round(L, 4)})
        if not fire_after_move:
            # historical order: GUNNERY then MOVEMENT (pre-B2 behaviour)
            hB = wrap_deg(hB + planB[t])
            hR = wrap_deg(hR + planR[t])
            xB += speedB * math.cos(math.radians(hB))
            yB += speedB * math.sin(math.radians(hB))
            xR += speedR * math.cos(math.radians(hR))
            yR += speedR * math.sin(math.radians(hR))
    return {"payoff_B": cum, "trajectory": traj,
            "final_r": traj[-1]["r"] if traj else r0}


def solve_matrix_game(pay: np.ndarray) -> dict:
    """Exact value and mixed strategies of a zero-sum matrix game (LP)."""
    from scipy.optimize import linprog

    m, n = pay.shape
    # max_x min_j (x^T P)_j  <->  min 1^T y  s.t. P^T y >= 1... use standard form:
    # maximize v s.t. sum_i x_i P[i,j] >= v for all j, sum x_i = 1, x >= 0
    c = np.zeros(m + 1)
    c[-1] = -1.0
    A_ub = np.zeros((n, m + 1))
    for j in range(n):
        A_ub[j, :m] = -pay[:, j]
        A_ub[j, m] = 1.0
    b_ub = np.zeros(n)
    A_eq = np.zeros((1, m + 1))
    A_eq[0, :m] = 1.0
    b_eq = [1.0]
    bounds = [(0, None)] * m + [(None, None)]
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds)
    if not res.success:
        # fall back to pure maximin
        bi = int(np.argmax(pay.min(axis=1)))
        return {"value": float(pay[bi].min()), "x": None, "pure": True}
    x = res.x[:m]
    return {"value": float(res.x[-1]), "x": x.tolist(), "pure": False}


def open_loop_minimax(kB: KernelWrap, kR: KernelWrap, lib: dict[str, list[float]],
                      r0: float, bearing0_deg: float, headingB0_deg: float,
                      headingR0_deg: float, vB: float, vR: float,
                      steps: int = 40, gamma: float = 0.96,
                      fire_after_move: bool = False) -> dict:
    """max_{pB} min_{pR} cumulative payoff over committed plan pairs."""
    plansB, plansR = list(lib.keys()), list(lib.keys())
    pay = np.zeros((len(plansB), len(plansR)))
    for i, pb in enumerate(plansB):
        for j, pr in enumerate(plansR):
            out = simulate(kB, kR, lib[pb], lib[pr], r0, bearing0_deg,
                           headingB0_deg, headingR0_deg, vB, vR, steps, gamma,
                           fire_after_move=fire_after_move)
            pay[i, j] = out["payoff_B"]
    bi = int(np.argmax(pay.min(axis=1)))
    rj = int(np.argmin(pay.max(axis=0)))
    game = solve_matrix_game(pay)
    return {"plans_B": plansB, "plans_R": plansR, "payoff_matrix": pay.tolist(),
            "maximin_plan_B": plansB[bi], "minimax_plan_R": plansR[rj],
            "pure_value": float(pay[bi].min()),
            "game_value": game["value"], "mixed_x": game["x"],
            "B_best_response_payoffs": pay[bi].tolist(),
            "R_punishment_row": pay[:, rj].tolist()}
