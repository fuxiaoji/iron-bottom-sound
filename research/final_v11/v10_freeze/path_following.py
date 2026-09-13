"""Leader-follower path-following line-ahead formation (v10 plan sections 3-7).

Formation representations
-------------------------
rigid, abeam offsets (v9 frozen baseline)
    x_ik(t) = c_i(t) + R(psi_i(t)) p_ik,  p_ik = (0, -ell k)
    In the code frame the heading is +x, so these offsets are perpendicular to
    the course: the frozen v9 experiments describe a line-ABREAST column.

rigid, line-ahead ("rigid_line_ahead")
    x_ik(t) = c_i(t) - ell_k e(psi_i(t))       all vessels share psi_i
    Same shape as the leader-follower model on a straight course, but the whole
    column rotates with the leader (rigid-body turning).

leader-follower / path following (v10 main numerical model)
    x_ik(t)   = gamma_i(s_i(t) - ell_k)        fixed ARC-LENGTH offsets
    psi_ik(t) = arg gamma_i'(s_i(t) - ell_k)
    A designated lead vessel generates the track; trailing vessels follow that
    track at fixed arc-length offsets and adopt the local tangent, so the
    column BENDS through a turn instead of sweeping laterally.

Numerical construction
----------------------
Each turn is subdivided into `n_sub` sub-steps, so the polyline resolves the
piecewise-constant-turn leader trajectory at sub-step resolution.  Arc length
per station is seg = v / n_sub, and station q sits at arc length q * seg.
Index M+q holds station q; the backward straight history is pre-filled so
trailing vessels never stack on the leader (v10 section 4).
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

from research.geometry.committed_game import wrap_deg  # noqa: E402

DEFAULT_SPACING = 2.0      # hex of arc length between consecutive vessels
DEFAULT_NSUB = 6           # sub-steps per turn (station spacing = v / n_sub)
N_SHIPS = 3


def line_ahead_offsets(spacing: float = DEFAULT_SPACING, n: int = N_SHIPS) -> np.ndarray:
    """Arc-length offsets of the vessels behind the leader (lead = 0)."""
    return np.array([k * spacing for k in range(n)], dtype=float)


class LeaderPath:
    """Arc-length parameterised polyline of a leader trajectory."""

    def __init__(self, x0: float, y0: float, psi0_deg: float, v: float,
                 max_offset: float, n_sub: int = DEFAULT_NSUB):
        self.v = float(v)
        self.n_sub = int(n_sub)
        self.seg = self.v / self.n_sub
        self.psi0 = float(psi0_deg)
        self.M = int(math.ceil(max_offset / self.seg)) + 2 * self.n_sub
        h = math.radians(psi0_deg)
        self.stations = np.array(
            [[x0 + m * self.seg * math.cos(h), y0 + m * self.seg * math.sin(h)]
             for m in range(-self.M, 1)], dtype=float)
        self.head = 0

    def extend(self, turn_rate_deg: float) -> None:
        """Advance the leader one turn, subdivided into n_sub sub-steps.

        The sub-steps are chained (each starts from the previous sub-step's
        endpoint), so the heading accumulates by turn_rate/n_sub per sub-step.
        """
        step = float(turn_rate_deg) / self.n_sub
        pts = list(self.stations)
        for _ in range(self.n_sub):
            d = pts[-1] - pts[-2]
            psi = math.degrees(math.atan2(d[1], d[0])) + step
            h = math.radians(psi)
            pts.append(pts[-1] + self.seg * np.array([math.cos(h), math.sin(h)]))
        self.stations = np.array(pts)
        self.head += self.n_sub

    def _heading_of_segment(self, j: int) -> float:
        d = self.stations[j + 1] - self.stations[j]
        return math.degrees(math.atan2(d[1], d[0]))

    def sample(self, q: float) -> tuple[np.ndarray, float]:
        """Position and tangent at fractional station q (arc length q * seg)."""
        i = int(math.floor(q))
        w = q - i
        i = max(-self.M, min(i, self.head))
        j = min(i + self.M, len(self.stations) - 2)
        p = (1.0 - w) * self.stations[j] + w * self.stations[j + 1]
        return p, self._heading_of_segment(j)

    def vessel_states(self, t: int, offsets: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Positions and headings of every vessel at turn t."""
        pos = np.zeros((len(offsets), 2))
        psi = np.zeros(len(offsets))
        for k, ell in enumerate(offsets):
            pos[k], psi[k] = self.sample(t * self.v / self.seg - ell / self.seg)
        return pos, psi

    # ---- v10 section 7 API -------------------------------------------
    def positions(self, t: int, offsets: np.ndarray) -> np.ndarray:
        return self.vessel_states(t, offsets)[0]

    def headings(self, t: int, offsets: np.ndarray) -> np.ndarray:
        return self.vessel_states(t, offsets)[1]

    @classmethod
    def from_sequence(cls, game, side: str, seq, H: int, n_sub: int = DEFAULT_NSUB):
        if side == "B":
            x0, y0, psi0, v = 0.0, 0.0, game.hB0_deg, game.vB
        else:
            x0, y0, psi0, v = game.xR0, game.yR0, game.hR0_deg, game.vR
        max_off = float(line_ahead_offsets(game.spacing, game.n_ships)[-1]) \
            + 2.0 * game.spacing
        p = cls(x0, y0, psi0, v, max_off, n_sub)
        for t in range(H):
            p.extend(float(seq[t]))
        return p


def _aspect(d: float) -> str:
    a = abs(wrap_deg(d))
    return "bow_stern" if (a <= 30.0 or a >= 150.0) else "broadside"


@dataclass
class FormationGameLF:
    """Leader-follower formation game with the paper's payoff definition."""
    kB: object
    kR: object
    r0: float = 16.0
    bearing0_deg: float = 0.0
    hB0_deg: float = 0.0
    hR0_deg: float = 180.0
    vB: float = 6.0
    vR: float = 6.0
    H: int = 6
    spacing: float = DEFAULT_SPACING
    n_ships: int = N_SHIPS
    gamma: float = 0.96
    n_sub: int = DEFAULT_NSUB

    def __post_init__(self) -> None:
        br = math.radians(self.bearing0_deg)
        self.xR0 = self.r0 * math.cos(br)
        self.yR0 = self.r0 * math.sin(br)
        self.offsets = line_ahead_offsets(self.spacing, self.n_ships)
        self.formation_length = float(self.offsets[-1])

    def payoff(self, seqB: np.ndarray, seqR: np.ndarray, tps: int = 1) -> float:
        pB = LeaderPath.from_sequence(self, "B", seqB, self.H, self.n_sub)
        pR = LeaderPath.from_sequence(self, "R", seqR, self.H, self.n_sub)
        cum = 0.0
        disc = 1.0
        for t in range(self.H):
            posB, psiB = pB.vessel_states(t, self.offsets)
            posR, psiR = pR.vessel_states(t, self.offsets)
            J = 0.0
            for kb in range(self.n_ships):
                for kr in range(self.n_ships):
                    dx = posR[kr, 0] - posB[kb, 0]
                    dy = posR[kr, 1] - posB[kb, 1]
                    r = max(math.hypot(dx, dy), 0.5)
                    brg = math.degrees(math.atan2(dy, dx))
                    dB = wrap_deg(brg - psiB[kb])
                    dR = wrap_deg(brg + 180.0 - psiR[kr])
                    J += (self.kB.fire(r, float(dB), 6, _aspect(float(dR)))
                          - self.kR.fire(r, float(dR), 6, _aspect(float(dB))))
            cum += disc * J
            disc *= self.gamma
        return cum


def _leader_state(game, seq, side: str, t: int):
    if side == "B":
        x, y, psi, v = 0.0, 0.0, game.hB0_deg, game.vB
    else:
        x, y, psi, v = game.xR0, game.yR0, game.hR0_deg, game.vR
    for s in range(t):
        psi = wrap_deg(psi + float(seq[s]))
        x += v * math.cos(math.radians(psi))
        y += v * math.sin(math.radians(psi))
    return np.array([x, y]), psi


def vessel_states_rigid_line_ahead(game, seq, side: str, t: int, spacing=None,
                                   n_ships=None):
    """Rigid column: fixed aft offsets along the heading, one shared heading."""
    offs = line_ahead_offsets(spacing or game.spacing, n_ships or game.n_ships)
    c, psi = _leader_state(game, seq, side, t)
    h = math.radians(psi)
    fwd = np.array([math.cos(h), math.sin(h)])
    return np.array([c - ell * fwd for ell in offs]), np.full(len(offs), psi)


def vessel_states_rigid_abeam(game, seq, side: str, t: int):
    """Frozen v9 convention: offsets (0, -ell k) in the code frame (abeam)."""
    from research.experiments.must1_formation_do import _OFFSETS, _rot
    c, psi = _leader_state(game, seq, side, t)
    return c + _rot(psi, _OFFSETS), np.full(len(_OFFSETS), psi)


class RigidLineAheadGame(FormationGameLF):
    """Rigid column baseline (same shape as LF when straight, rigid turns)."""

    def payoff(self, seqB: np.ndarray, seqR: np.ndarray, tps: int = 1) -> float:
        cum = 0.0
        disc = 1.0
        for t in range(self.H):
            posB, psiB = vessel_states_rigid_line_ahead(self, seqB, "B", t)
            posR, psiR = vessel_states_rigid_line_ahead(self, seqR, "R", t)
            J = 0.0
            for kb in range(self.n_ships):
                for kr in range(self.n_ships):
                    dx = posR[kr, 0] - posB[kb, 0]
                    dy = posR[kr, 1] - posB[kb, 1]
                    r = max(math.hypot(dx, dy), 0.5)
                    brg = math.degrees(math.atan2(dy, dx))
                    dB = wrap_deg(brg - psiB[kb])
                    dR = wrap_deg(brg + 180.0 - psiR[kr])
                    J += (self.kB.fire(r, float(dB), 6, _aspect(float(dR)))
                          - self.kR.fire(r, float(dR), 6, _aspect(float(dB))))
            cum += disc * J
            disc *= self.gamma
        return cum


def batch_payoff_lf(game, cands: np.ndarray, opp: np.ndarray, blue: bool,
                    n_sub=None) -> np.ndarray:
    """Vectorised LF payoff: n candidates against one fixed opponent sequence."""
    from research.experiments.t1_exact_discrete_certification import fire_vec
    n_sub = n_sub or game.n_sub
    n, H = cands.shape
    seqB = cands if blue else np.broadcast_to(opp, (n, H))
    seqR = np.broadcast_to(opp, (n, H)) if blue else cands
    offs = line_ahead_offsets(game.spacing, game.n_ships)

    def build(x0, y0, psi0, v, seqs):
        seg = v / n_sub
        max_off = float(offs[-1]) + 2.0 * game.spacing
        M = int(math.ceil(max_off / seg)) + 2 * n_sub
        st = np.zeros((n, M + n_sub * H + 1, 2))
        h0 = math.radians(psi0)
        for m in range(-M, 1):
            st[:, m + M, 0] = x0 + m * seg * math.cos(h0)
            st[:, m + M, 1] = y0 + m * seg * math.sin(h0)
        j = M
        step = np.asarray(seqs, float) / n_sub
        for t in range(H):
            for _ in range(n_sub):
                d = st[:, j] - st[:, j - 1]
                phi = np.degrees(np.arctan2(d[:, 1], d[:, 0])) + step[:, t]
                h = np.radians(phi)
                st[:, j + 1, 0] = st[:, j, 0] + seg * np.cos(h)
                st[:, j + 1, 1] = st[:, j, 1] + seg * np.sin(h)
                j += 1
        return st, seg, M

    stB, segB, MB = build(0.0, 0.0, game.hB0_deg, game.vB, seqB)
    stR, segR, MR = build(game.xR0, game.yR0, game.hR0_deg, game.vR, seqR)
    ar = np.arange(n)
    npts = stB.shape[1]

    def heading(st, j):
        d = st[ar, j + 1] - st[ar, j]        # element-wise: j is per-candidate
        return np.degrees(np.arctan2(d[:, 1], d[:, 0]))

    def sample(st, seg, M, q):
        q = np.full(n, float(q))
        i = np.floor(q).astype(int)
        w = q - i
        i = np.clip(i, -M, npts - 2 - M)
        j = i + M
        p = (1 - w)[:, None] * st[ar, j] + w[:, None] * st[ar, j + 1]
        return p, heading(st, j)

    K = game.n_ships
    cum = np.zeros(n)
    disc = 1.0
    for t in range(H):
        posB = np.zeros((n, K, 2)); psiB = np.zeros((n, K))
        posR = np.zeros((n, K, 2)); psiR = np.zeros((n, K))
        for k, ell in enumerate(offs):
            posB[:, k, :], psiB[:, k] = sample(stB, segB, MB,
                                            t * game.vB / segB - ell / segB)
            posR[:, k, :], psiR[:, k] = sample(stR, segR, MR,
                                            t * game.vR / segR - ell / segR)
        J = np.zeros(n)
        for kb in range(K):
            for kr in range(K):
                dx = posR[:, kr, 0] - posB[:, kb, 0]
                dy = posR[:, kr, 1] - posB[:, kb, 1]
                r = np.maximum(np.hypot(dx, dy), 0.5)
                brg = np.degrees(np.arctan2(dy, dx))
                dB = wrap_deg(brg - psiB[:, kb])
                dR = wrap_deg(brg + 180.0 - psiR[:, kr])
                aspR = np.where((np.abs(dR) <= 30.0) | (np.abs(dR) >= 150.0),
                                "bow_stern", "broadside")
                aspB = np.where((np.abs(dB) <= 30.0) | (np.abs(dB) >= 150.0),
                                "bow_stern", "broadside")
                J += fire_vec(game.kB, r, dB, aspR) - fire_vec(game.kR, r, dR, aspB)
        cum += disc * J
        disc *= game.gamma
    return cum


def make_lf_game(kernel_dict, geometry: str, eta_r: float, eta_v: float, H: int,
                 formation_mode: str = "leader_follower",
                 spacing: float = DEFAULT_SPACING, n_sub: int = DEFAULT_NSUB):
    """Factory mirroring the v9 game construction, with a formation-mode switch."""
    from research.geometry.committed_game import KernelWrap
    from research.geometry.firepower_kernel import KernelFit
    from research.experiments.must1_formation_do import GEOM
    fit = KernelFit.from_dict(kernel_dict)
    kB = KernelWrap(fit, range_ratio=eta_r)
    kR = KernelWrap(fit, 1.0)
    brg, hB, hR = GEOM[geometry]
    kw = dict(r0=16.0, bearing0_deg=brg, hB0_deg=hB, hR0_deg=hR,
              vB=6.0 * eta_v, vR=6.0, H=H, spacing=spacing, n_sub=n_sub)
    if formation_mode == "leader_follower":
        return FormationGameLF(kB, kR, **kw)
    if formation_mode == "rigid_line_ahead":
        return RigidLineAheadGame(kB, kR, **kw)
    from research.experiments.must1_formation_do import FormationGame
    return FormationGame(kB, kR, r0=16.0, bearing0_deg=brg, hB0_deg=hB,
                         hR0_deg=hR, vB=6.0 * eta_v, vR=6.0, H=H)
