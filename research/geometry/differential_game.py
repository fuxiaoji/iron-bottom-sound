"""Layer-1 reduced differential game for directional naval gunnery.

Two ships in the plane with Dubins-like kinematics are reduced, by rotational
symmetry, to the classic three-dimensional relative state

    s = (r, alpha_B, alpha_R)

  r       distance (hex units, the kernel's native range unit)
  alpha_B angle of B's heading relative to the line of sight B->R
  alpha_R angle of R's heading relative to the line of sight B->R

with alpha periodic in (-pi, pi].  Both ships hold constant cruise speed
(constant-cruise approximation: steam plants change speed slowly and the
engine AI itself cruises at max speed; speed enters the game only through
the parameter eta_v = v_B_max / v_R_max).  The control of each ship is its
turn rate, quantised to {-omega_max, 0, +omega_max}.

The instantaneous payoff is the calibrated expected-hits differential

    L(s) = K_B(r, delta_B, v_R, aspect_R) - lambda * K_R(r, delta_R, v_B, aspect_B)

where K comes from the E01-calibrated firepower kernel (engine-validated).
delta_i is the target's bearing off ship i's bow (+ = starboard);
aspect_i is the presentation of ship i toward its opponent (broadside vs
bow/stern-on).  No tactical doctrine (crossing-the-T, formation split, ...)
enters the objective anywhere.

The zero-sum stationary game

    V(s) = max_{u_B} min_{u_R} E[ sum_t gamma^t L(s_t) ]

is solved by value iteration with trilinear interpolation on a periodic grid
in (alpha_B, alpha_R) and an absorbing corridor in r.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

TWO_PI = 2 * math.pi


def wrap_angle(a):
    """Wrap angles to (-pi, pi] (numpy-compatible)."""
    return (np.asarray(a, dtype=float) + math.pi) % TWO_PI - math.pi


@dataclass
class KernelWrap:
    """Kernel adapter: loads an E01 KernelFit and applies range-ratio scaling."""

    fit: object                # research.geometry.firepower_kernel.KernelFit
    range_ratio: float = 1.0   # eta_r: >1 = this ship's guns reach farther
    max_knot_speed: int = 5    # engine speed modifier is neutral for 4+

    def fire(self, r_hex: float, delta_deg: float, target_speed_knots: int,
             target_aspect: str) -> float:
        r_eff = float(np.clip(r_hex / max(self.range_ratio, 1e-6), 1.0, 24.0))
        return self.fit.expected_hits(
            r_eff, float(delta_deg),
            int(np.clip(target_speed_knots, 0, self.max_knot_speed)),
            target_aspect)


class ReducedGame:
    def __init__(self,
                 kernel_B: KernelWrap,
                 kernel_R: KernelWrap,
                 v_B: float = 6.0,
                 v_R: float = 6.0,
                 omega_max_deg: float = 60.0,
                 lambda_payoff: float = 1.0,
                 r_min: float = 1.0,
                 r_max: float = 20.0,
                 n_r: int = 40,
                 n_alpha: int = 24,
                 gamma: float = 0.96,
                 aspect_cut_deg: float = 30.0):
        self.kB, self.kR = kernel_B, kernel_R
        self.vB, self.vR = float(v_B), float(v_R)
        self.omega_max = math.radians(omega_max_deg)
        self.actions = (-self.omega_max, 0.0, self.omega_max)
        self.lam = lambda_payoff
        self.r_min, self.r_max = r_min, r_max
        self.gamma = gamma
        self.aspect_cut = math.radians(aspect_cut_deg)

        self.r_grid = np.linspace(r_min, r_max, n_r)
        self.a_grid = np.linspace(-math.pi, math.pi, n_alpha, endpoint=False)
        self.n_r, self.n_a = n_r, n_alpha
        self.shape = (n_r, n_alpha, n_alpha)

        self._KB, self._KR, self._L = self._build_L()
        self.V = np.zeros(self.shape)
        self.sweeps = 0
        self.residual = np.inf

    # ---------------- geometry / payoff ----------------
    def _classify(self, deg: np.ndarray) -> np.ndarray:
        cut = math.degrees(self.aspect_cut)
        a = np.abs((deg + 180.0) % 360.0 - 180.0)
        return np.where((a <= cut) | (a >= 180.0 - cut), "bow_stern", "broadside")

    def _build_L(self):
        r = self.r_grid[:, None, None]
        aB = self.a_grid[None, :, None]          # B's heading vs LOS
        aR = self.a_grid[None, None, :]          # R's heading vs LOS
        # target bearing off the shooter's bow (+ = starboard):
        #   delta_B = wrap(phi - psi_B)  = -alpha_B
        #   delta_R = wrap(phi + pi - psi_R) = wrap(pi - alpha_R)
        dB = wrap_angle(-aB)                                  # per (1, na, 1), rad
        dR = wrap_angle(math.pi - aR)                         # per (1, 1, na), rad
        aspect_R = self._classify(np.broadcast_to(dR, self.shape))
        aspect_B = self._classify(np.broadcast_to(dB, self.shape))

        KB = np.zeros(self.shape)
        KR = np.zeros(self.shape)
        dB_deg = np.degrees(dB)
        dR_deg = np.degrees(dR)
        for i in range(self.n_r):
            for j in range(self.n_a):
                for k in range(self.n_a):
                    KB[i, j, k] = self.kB.fire(self.r_grid[i], dB_deg[0, j, 0],
                                               int(round(self.vR)), aspect_R[i, j, k])
                    KR[i, j, k] = self.kR.fire(self.r_grid[i], dR_deg[0, 0, k],
                                               int(round(self.vB)), aspect_B[i, j, k])
        return KB, KR, KB - self.lam * KR

    def payoff_grid(self) -> np.ndarray:
        return self._L.copy()

    # ---------------- dynamics ----------------
    def step(self, r, aB, aR, uB, uR):
        """Relative-state dynamics for one time unit."""
        dLOS = (self.vR * np.sin(aR) - self.vB * np.sin(aB)) / np.maximum(r, 1e-6)
        r2 = np.clip(r + self.vR * np.cos(aR) - self.vB * np.cos(aB),
                     self.r_min, self.r_max)
        aB2 = wrap_angle(aB + uB - dLOS)
        aR2 = wrap_angle(aR + uR - dLOS)
        return r2, aB2, aR2

    # ---------------- interpolation ----------------
    def _interp_V(self, V, r2, aB2, aR2):
        nr, na = self.n_r, self.n_a
        fr = (r2 - self.r_grid[0]) / (self.r_grid[1] - self.r_grid[0])
        i0 = np.clip(np.floor(fr).astype(int), 0, nr - 2)
        wr = np.clip(fr - i0, 0.0, 1.0)
        fa = (wrap_angle(aB2) + math.pi) / TWO_PI * na
        j0 = np.floor(fa).astype(int)
        wa = fa - np.floor(fa)
        fb = (wrap_angle(aR2) + math.pi) / TWO_PI * na
        k0 = np.floor(fb).astype(int)
        wb = fb - np.floor(fb)
        out = None
        for di, wi in ((0, 1 - wr), (1, wr)):
            for dj, wj in ((0, 1 - wa), (1, wa)):
                for dk, wk in ((0, 1 - wb), (1, wb)):
                    val = V[i0 + di, (j0 + dj) % na, (k0 + dk) % na]
                    term = val * (wi * wj * wk)
                    out = term if out is None else out + term
        return out

    # ---------------- solve ----------------
    def _dynamics(self):
        r = self.r_grid[:, None, None]
        aB = self.a_grid[None, :, None]
        aR = self.a_grid[None, None, :]
        dyn = []
        for uB in self.actions:
            for uR in self.actions:
                dLOS = (self.vR * np.sin(aR) - self.vB * np.sin(aB)) / np.maximum(r, 1e-6)
                r2 = np.clip(r + self.vR * np.cos(aR) - self.vB * np.cos(aB),
                             self.r_min, self.r_max)
                aB2 = wrap_angle(aB + uB - dLOS)
                aR2 = wrap_angle(aR + uR - dLOS)
                dyn.append((r2, aB2, aR2))
        return dyn

    def solve(self, max_sweeps: int = 400, tol: float = 1e-5, verbose: bool = False):
        L = self._L
        g = self.gamma
        dyn = self._dynamics()
        V = self.V
        for sweep in range(max_sweeps):
            Q = np.empty((len(dyn),) + self.shape)
            for idx, (r2, aB2, aR2) in enumerate(dyn):
                Q[idx] = L + g * self._interp_V(V, r2, aB2, aR2)
            acts = len(self.actions)
            Qr = Q.reshape(acts, acts, *self.shape)
            worst = Qr.min(axis=1)          # R best-replies: min over uR
            V_new = worst.max(axis=0)       # B maximises
            diff = float(np.max(np.abs(V_new - V)))
            V = V_new
            self.sweeps = sweep + 1
            self.residual = diff
            if verbose and sweep % 50 == 0:
                print(f"  sweep {sweep:3d} residual {diff:.2e}")
            if diff < tol:
                break
        self.V = V
        return V

    def q_values(self):
        """Q(s, uB, uR) under the current value: (3, 3, *shape)."""
        dyn = self._dynamics()
        Q = np.empty((3, 3) + self.shape)
        idx = 0
        for ib in range(3):
            for ir_ in range(3):
                r2, aB2, aR2 = dyn[idx]
                Q[ib, ir_] = self._L + self.gamma * self._interp_V(self.V, r2, aB2, aR2)
                idx += 1
        return Q

    def policy_actions(self):
        """Saddle-point action index grids (pi_B, pi_R)."""
        Q = self.q_values()
        after_R = Q.min(axis=1)                 # R's best reply per uB
        pi_B = np.argmax(after_R, axis=0)
        worst_for_R = Q.max(axis=0)             # B's best punish per uR
        pi_R = np.argmin(worst_for_R, axis=0)
        return pi_B, pi_R, Q

    # ---------------- rollout ----------------
    def _state_index(self, r, aB, aR):
        ir = int(np.clip(np.searchsorted(self.r_grid, r) - 1, 0, self.n_r - 1))
        na = self.n_a
        ja = int((wrap_angle(aB) + math.pi) / TWO_PI * na) % na
        ka = int((wrap_angle(aR) + math.pi) / TWO_PI * na) % na
        return (ir, ja, ka)

    def _L_value(self, r, aB, aR):
        return float(self._L[self._state_index(r, aB, aR)])

    def rollout(self, r0: float, aB0_deg: float, aR0_deg: float, steps: int = 40,
                policy: str = "minimax") -> dict:
        r, aB, aR = float(r0), math.radians(aB0_deg), math.radians(aR0_deg)
        piB, piR, _ = self.policy_actions()
        traj = []
        cum = 0.0
        disc = 1.0
        for t in range(steps):
            i = self._state_index(r, aB, aR)
            if policy == "minimax":
                uB, uR = self.actions[piB[i]], self.actions[piR[i]]
            elif policy == "straight":
                uB = uR = 0.0
            elif policy == "greedy":
                uB, uR = self._greedy_actions(r, aB, aR)
            elif policy == "parallel":
                uB = self._parallel_control(aB)
                uR = self._parallel_control(wrap_angle(math.pi - aR))
            else:
                raise ValueError(policy)
            L = self._L_value(r, aB, aR)
            cum += disc * L
            disc *= self.gamma
            traj.append({"t": t, "r": round(r, 2), "aB_deg": round(math.degrees(aB), 1),
                         "aR_deg": round(math.degrees(aR), 1), "L": round(L, 3),
                         "uB_deg": round(math.degrees(uB), 0),
                         "uR_deg": round(math.degrees(uR), 0)})
            r, aB, aR = self.step(np.float64(r), np.float64(aB), np.float64(aR), uB, uR)
            r, aB, aR = float(r), float(wrap_angle(aB)), float(wrap_angle(aR))
        return {"cumulative_L": cum, "final_r": r, "trajectory": traj}

    def _parallel_control(self, aB):
        """Keep the opponent on the beam: drive alpha_B -> +90 deg."""
        target = math.pi / 2
        err = float(wrap_angle(aB - target))
        if err > self.omega_max / 2:
            return self.omega_max * -1
        if err < -self.omega_max / 2:
            return self.omega_max
        return 0.0

    def _greedy_actions(self, r, aB, aR):
        best, worst = None, None
        for ib, uB in enumerate(self.actions):
            r2, aB2, aR2 = self.step(np.float64(r), np.float64(aB), np.float64(aR), uB, 0.0)
            L2 = self._L_value(float(r2), float(wrap_angle(aB2)), float(wrap_angle(aR2)))
            if best is None or L2 > best[0]:
                best = (L2, ib)
        for ir_, uR in enumerate(self.actions):
            r2, aB2, aR2 = self.step(np.float64(r), np.float64(aB), np.float64(aR), 0.0, uR)
            L2 = self._L_value(float(r2), float(wrap_angle(aB2)), float(wrap_angle(aR2)))
            if worst is None or L2 < worst[0]:
                worst = (L2, ir_)
        return self.actions[best[1]], self.actions[worst[1]]


def geometry_to_alphas(bearing_deg: float, heading_B_deg: float, heading_R_deg: float):
    """World geometry (bearing of R from B, both world headings) -> alphas."""
    aB = wrap_angle(math.radians(heading_B_deg - bearing_deg))
    aR = wrap_angle(math.radians(heading_R_deg - bearing_deg))
    return float(aB), float(aR)
