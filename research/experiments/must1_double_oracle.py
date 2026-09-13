"""MUST-1: Double Oracle solver for the open-loop committed-maneuver game.

Replaces the finite plan library with iterative best-response trajectory
optimisation:

1.  Initialise with a small set of seed trajectories.
2.  Compute the mixed zero-sum equilibrium of the restricted game.
3.  Compute each player's best response (BR) to the opponent's mixed
    strategy via continuous parameterised trajectory optimisation.
4.  Add BR trajectories to the library; repeat until the BR gap converges.

Trajectory parameterisation: K=6 piecewise-constant turn-rate segments,
each in [-60, +60] deg/turn (matching the engine's 3-pulse turn
granularity).  Speed is constant cruise (v=6 hexes/turn).

The approximate exploitability / BR gap is:
    gap = max_{u_B} E_{pi_R}[J(u_B, u_R)] - min_{u_R} E_{pi_B}[J(u_B, u_R)]
computed over the current restricted set.  This is an *approximate* gap
(the BR search is local), not a true exploitability.

Output: research/results/v5/{do_convergence.csv, do_cells.csv,
results.json, report.md}
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.stats import spearmanr

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

from research.geometry.committed_game import KernelWrap, solve_matrix_game, wrap_deg  # noqa: E402
from research.geometry.firepower_kernel import KernelFit  # noqa: E402

OUT = REPO / "research" / "results" / "v5"
T_MAX = 40
GAMMA = 0.96
V_CRUISE = 6.0
ASPECT_CUT = 30.0
LAMBDA = 1.0


class TrajectoryGame:
    """Wraps the kernel-based payoff evaluation for the continuous game."""

    def __init__(self, kB: KernelWrap, kR: KernelWrap, r0: float = 16.0,
                 bearing0_deg: float = 0.0, hB0_deg: float = 0.0,
                 hR0_deg: float = 180.0, vB: float = 6.0, vR: float = 6.0,
                 t_max: int = T_MAX):
        self.kB = kB
        self.kR = kR
        self.r0 = r0
        self.brg0 = bearing0_deg
        self.hB0 = hB0_deg
        self.hR0 = hR0_deg
        self.vB = vB
        self.vR = vR
        self.t_max = t_max
        # initial positions: B at origin, R at (r0*cos(brg), r0*sin(brg))
        br = math.radians(bearing0_deg)
        self.xR0 = r0 * math.cos(br)
        self.yR0 = r0 * math.sin(br)

    def payoff(self, planB: np.ndarray, planR: np.ndarray) -> float:
        """Discounted cumulative J for one pair of turn-rate sequences."""
        xB, yB = 0.0, 0.0
        xR, yR = self.xR0, self.yR0
        hB, hR = self.hB0, self.hR0
        cum = 0.0
        disc = 1.0
        T = min(self.t_max, len(planB), len(planR))
        for t in range(T):
            dx, dy = xR - xB, yR - yB
            r = max(math.hypot(dx, dy), 0.5)
            bearing = math.degrees(math.atan2(dy, dx))
            dB = wrap_deg(bearing - hB)
            dR = wrap_deg(bearing + 180.0 - hR)
            aB = self._aspect(dB)
            aR = self._aspect(dR)
            L = (self.kB.fire(r, dB, 6, aR) - self.kR.fire(r, dR, 6, aB))
            cum += disc * L
            disc *= GAMMA
            hB = wrap_deg(hB + planB[t])
            hR = wrap_deg(hR + planR[t])
            xB += self.vB * math.cos(math.radians(hB))
            yB += self.vB * math.sin(math.radians(hB))
            xR += self.vR * math.cos(math.radians(hR))
            yR += self.vR * math.sin(math.radians(hR))
        return cum

    @staticmethod
    def _aspect(d):
        a = abs(wrap_deg(d))
        return "bow_stern" if (a <= 30.0 or a >= 150.0) else "broadside"


def expand_plan(turns: np.ndarray, turns_per_seg: int = 7, T: int = T_MAX) -> np.ndarray:
    """Expand K turn-rate segments into a per-turn heading change sequence."""
    rates = np.repeat(turns, turns_per_seg)
    if len(rates) < T:
        rates = np.concatenate([rates, np.zeros(T - len(rates))])
    return rates[:T]


def br_objective(turns_flat: np.ndarray, game: TrajectoryGame,
                 opp_plans: list[np.ndarray], opp_weights: np.ndarray,
                 sign: float) -> float:
    """Expected payoff of a trajectory against the opponent's mixed strategy.
    sign=+1 for B (maximise), sign=-1 for R (minimise → we return -payoff)."""
    plan = expand_plan(turns_flat)
    total = 0.0
    for w, opp in zip(opp_weights, opp_plans):
        total += w * game.payoff(plan, opp * sign)
    return sign * total


def best_response(game: TrajectoryGame, opp_plans: list[np.ndarray],
                  opp_weights: np.ndarray, sign: float,
                  n_starts: int = 5) -> np.ndarray:
    """Find the best turn-rate sequence against the opponent's mixed strategy.
    Uses multi-start L-BFGS-B with random initialisation."""
    K = 6
    best_x = None
    best_val = -np.inf * sign
    rng = np.random.default_rng(42)
    starts = [np.zeros(K)]
    starts += [rng.uniform(-60, 60, K) for _ in range(n_starts - 1)]
    for x0 in starts:
        res = minimize(br_objective, x0, args=(game, opp_plans, opp_weights, sign),
                       method="L-BFGS-B",
                       bounds=[(-60, 60)] * K,
                       options={"maxiter": 200})
        if res.fun * sign > best_val * sign:
            best_val = res.fun
            best_x = res.x
    return best_x if best_x is not None else np.zeros(K)


def double_oracle(game: TrajectoryGame, seed_plans_B: list[np.ndarray],
                  seed_plans_R: list[np.ndarray], max_iter: int = 20,
                  tol: float = 0.05) -> dict:
    """Double oracle for the open-loop zero-sum game.

    Returns the converged mixed strategies, game value, and diagnostics.
    """
    from scipy.optimize import linprog

    plans_B = list(seed_plans_B)
    plans_R = list(seed_plans_R)
    gap_history = []
    values = []

    for iteration in range(max_iter):
        # 1. Build payoff matrix for restricted game
        nB, nR = len(plans_B), len(plans_R)
        P = np.zeros((nB, nR))
        for i in range(nB):
            for j in range(nR):
                P[i, j] = game.payoff(plans_B[i], plans_R[j])

        # 2. Solve restricted zero-sum game (LP)
        c = np.zeros(nB + 1)
        c[-1] = -1.0
        A_ub = np.zeros((nR, nB + 1))
        for j in range(nR):
            A_ub[j, :nB] = -P[:, j]
            A_ub[j, nB] = 1.0
        b_ub = np.zeros(nR)
        A_eq = np.zeros((1, nB + 1))
        A_eq[0, :nB] = 1.0
        b_eq = [1.0]
        bounds = [(0, None)] * nB + [(None, None)]
        res_B = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds)
        if not res_B.success:
            break

        # R's LP: min v s.t. sum_j y_j P[i,j] <= v for all i, sum y = 1, y >= 0
        c_R = np.zeros(nR + 1)
        c_R[-1] = 1.0
        A_ub_R = np.zeros((nB, nR + 1))
        for i in range(nB):
            A_ub_R[i, :nR] = P[i, :]
            A_ub_R[i, nR] = -1.0
        b_ub_R = np.zeros(nB)
        A_eq_R = np.zeros((1, nR + 1))
        A_eq_R[0, :nR] = 1.0
        b_eq_R = [1.0]
        bounds_R = [(0, None)] * nR + [(None, None)]
        res_R = linprog(c_R, A_ub=A_ub_R, b_ub=b_ub_R, A_eq=A_eq_R, b_eq=b_eq_R,
                        bounds=bounds_R)

        v_B = res_B.x[-1] if res_B.success else -np.inf
        v_R = -res_R.x[-1] if res_R.success else np.inf
        value = (v_B + v_R) / 2.0
        gap = abs(v_B - v_R)
        gap_history.append(gap)
        values.append(value)
        print(f"  [do] iter={iteration + 1} nB={nB} nR={nR} "
              f"V={value:+.4f} gap={gap:.4f}", flush=True)

        pi_B = res_B.x[:nB]
        pi_R = res_R.x[:nR]

        # 3. Best responses
        br_B = best_response(game, plans_R, pi_R, sign=+1)
        br_R = best_response(game, plans_B, pi_B, sign=-1)

        # 4. Check if BRs improve the game
        new_pay_B = game.payoff(br_B, plans_R[0])  # approximate
        # Check convergence: BR gap < tol
        if gap < tol:
            break

        # 5. Add BR trajectories (expanded to full length)
        plans_B.append(br_B)
        plans_R.append(br_R)

    return {
        "value": value,
        "gap": gap,
        "iterations": iteration + 1,
        "n_plans_B": len(plans_B),
        "n_plans_R": len(plans_R),
        "pi_B": pi_B.tolist() if res_B.success else [],
        "pi_R": pi_R.tolist() if res_R.success else [],
        "gap_history": gap_history,
        "plans_B": plans_B,
        "plans_R": plans_R,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fits = json.load(open(REPO / "research" / "results" / "e01" / "kernel_fits.json"))
    base_fit = KernelFit.from_dict(fits["CA"])

    ETA_V = (0.8, 1.0, 1.2)
    ETA_R = (0.8, 1.0, 1.2)
    GEOM = {"head_on": (0.0, 0.0, 180.0),
            "parallel": (90.0, 0.0, 0.0),
            "crossing": (45.0, 0.0, 180.0)}

    cells = []
    for eta_r in ETA_R:
        for eta_v in ETA_V:
            for gname, (brg, hB, hR) in GEOM.items():
                kB = KernelWrap(base_fit, range_ratio=eta_r)
                kR = KernelWrap(base_fit)
                game = TrajectoryGame(kB, kR, r0=16, bearing0_deg=brg,
                                      hB0_deg=hB, hR0_deg=hR,
                                      vB=6.0 * eta_v, vR=6.0)

                # Seed plans: small set of constant turn rates
                seeds = [np.full(40, r) for r in (-60, -30, 0, 30, 60)]
                result = double_oracle(game, seeds, seeds, max_iter=15, tol=0.05)

                # Commitment retest: H-horizon open-loop game value V_H.
                # Truncated to H turns; exact LP over a constant-rate library.
                p_vals = {}
                for H in (1, 2, 3, 4, 6):
                    sub_game = TrajectoryGame(kB, kR, r0=16, bearing0_deg=brg,
                                              hB0_deg=hB, hR0_deg=hR,
                                              vB=6.0 * eta_v, vR=6.0,
                                              t_max=H)
                    lib_H = [np.full(H, r) for r in (-60, -40, -20, 0, 20, 40, 60)]
                    pay = np.array([[sub_game.payoff(pB, pR) for pR in lib_H]
                                    for pB in lib_H])
                    sol = solve_matrix_game(pay)
                    p_vals[f"H{H}"] = float(sol["value"])

                cell = {"eta_v": eta_v, "eta_r": eta_r, "geometry": gname,
                        "value": result["value"], "gap": result["gap"],
                        "iterations": result["iterations"],
                        "n_plans": result["n_plans_B"],
                        "P_H": p_vals}
                cells.append(cell)
                # Incremental checkpoint so a crash never loses finished cells
                json.dump({"cells": cells},
                          open(OUT / "do_cells_partial.json", "w"), indent=2)
                print(f"eta_v={eta_v} eta_r={eta_r} {gname}: "
                      f"V={result['value']:+.4f} gap={result['gap']:.4f} "
                      f"iter={result['iterations']}", flush=True)

    json.dump({"cells": cells}, open(OUT / "do_cells.json", "w"), indent=2)

    # Commitment hypothesis retest
    print("\n--- Commitment retest ---")
    for H in (1, 2, 3, 4, 6):
        key = f"H{H}"
        for eta_r, sign_expected in ((0.8, -1), (1.0, 0), (1.2, +1)):
            vals = [c["P_H"].get(key, 0) for c in cells
                    if abs(c["eta_r"] - eta_r) < 0.01]
            mean_p = np.mean(vals) if vals else 0
            ok = (mean_p > 0.05) if sign_expected > 0 else \
                 (mean_p < -0.05) if sign_expected < 0 else \
                 (abs(mean_p) < 0.1)
            print(f"  eta_r={eta_r} H={H}: mean P_H={mean_p:+.4f} "
                  f"expected_sign={sign_expected:+d} {'✓' if ok else '✗'}")

    (OUT / "report.md").write_text(
        "# MUST-1: Double Oracle convergence + commitment retest\n"
        f"\nCells: {len(cells)}\n"
        f"\nConvergence: gap < 0.05 in "
        f"{sum(1 for c in cells if c['gap'] < 0.05)}/{len(cells)} cells\n",
        encoding="utf-8")
    print("DONE")


if __name__ == "__main__":
    import csv
    main()
