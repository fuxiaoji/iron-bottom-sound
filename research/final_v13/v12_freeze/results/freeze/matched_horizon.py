"""v11 matched-horizon commitment / replanning-cadence machinery.

Why (v11 section 1): the v10 metric P_H = V_H - V_1 varied BOTH the plan
length and the evaluation horizon, so it could not isolate the value of
commitment.  v11 fixes the evaluation horizon for every policy class,

    T = 6,     J_{0:T} = sum_{t<T} r_t,     r_t = interval reward over [t, t+1),

and varies only the *replanning cadence* h in {1,2,3,6}: a cadence of h means
a plan is locked for h steps before the state is re-observed and the
remaining-horizon open-loop game re-solved.  The commitment metric is

    C_h = V_T^{(h)} - V_T^{(1)},      C_1 = 0.

Stage reward (v11 section 2): the trapezoid interval reward
    r_t = (dt/2) [ L(s_t) + L(s_{t+1}) ]
so every action affects the reward of the step it is executed in (this also
retires the v10 artefact that a one-step policy's action could be
payoff-neutral).

Mixed equilibrium handling (v11 section 9): the receding policy samples from
the COMPLETE equilibrium mixture.  No argmax action, no averaged action, no
support truncation.  Because the planner is deterministic given the state and
the randomness comes only from mixture sampling, the reported values are
Monte Carlo expectations of this receding-equilibrium implementation --- not
an exact extensive-form feedback equilibrium.

Outputs are produced by the accompanying experiment script.
"""
from __future__ import annotations

import hashlib
import itertools
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

from research.geometry.committed_game import wrap_deg  # noqa: E402
from research.formation.path_following import (  # noqa: E402
    DEFAULT_NSUB, DEFAULT_SPACING, N_SHIPS, line_ahead_offsets,
)
from research.experiments.t1_exact_discrete_certification import fire_vec, GRIDS  # noqa: E402

OMEGA_MAX = 60.0
T_DEFAULT = 6


def _aspect_arr(delta: np.ndarray) -> np.ndarray:
    a = np.abs(wrap_deg(delta))
    return np.where((a <= 30.0) | (a >= 150.0), "bow_stern", "broadside")


# --------------------------------------------------------------- state
@dataclass
class LeaderState:
    """Leader path state: stations at integer sub-step indices from -M upwards.

    stations[q + M] is the position at arc length q * seg; `head` is the index
    of the current station.  Trailing vessels are sampled from this array, so
    the follower positions remain consistent with the leader's actual track.
    """
    x0: float
    y0: float
    psi0: float
    v: float
    n_sub: int
    spacing: float = DEFAULT_SPACING
    n_ships: int = N_SHIPS
    M: int = 0
    seg: float = 0.0
    stations: np.ndarray = field(default_factory=lambda: np.zeros((1, 2)))
    head: int = 0

    def __post_init__(self):
        self.seg = self.v / self.n_sub
        offs = line_ahead_offsets(self.spacing, self.n_ships)
        max_off = float(offs[-1]) + 2.0 * self.spacing
        self.M = int(math.ceil(max_off / self.seg)) + 2 * self.n_sub
        h = math.radians(self.psi0)
        self.stations = np.array(
            [[self.x0 + m * self.seg * math.cos(h), self.y0 + m * self.seg * math.sin(h)]
             for m in range(-self.M, 1)], dtype=float)
        self.head = 0

    # ---- mutation -------------------------------------------------
    def clone(self) -> "LeaderState":
        s = LeaderState(self.x0, self.y0, self.psi0, self.v, self.n_sub,
                        self.spacing, self.n_ships)
        s.M, s.seg = self.M, self.seg
        s.stations = self.stations.copy()
        s.head = self.head
        return s

    def extend_plan(self, seq: np.ndarray) -> None:
        """Append per-turn turn rates, subdividing each turn into n_sub steps."""
        for rate in seq:
            step = float(rate) / self.n_sub
            for _ in range(self.n_sub):
                j = len(self.stations) - 1
                d = self.stations[j] - self.stations[j - 1]
                psi = math.degrees(math.atan2(d[1], d[0])) + step
                h = math.radians(psi)
                self.stations = np.vstack([self.stations,
                                           self.stations[j] + self.seg *
                                           np.array([math.cos(h), math.sin(h)])])
                self.head += 1

    # ---- read -----------------------------------------------------
    def sample(self, q: float, offsets: np.ndarray):
        """Positions and headings at arc-length offsets behind station q."""
        pos = np.zeros((len(offsets), 2))
        psi = np.zeros(len(offsets))
        for k, ell in enumerate(offsets):
            qq = q - ell / self.seg
            i = int(math.floor(qq))
            w = qq - i
            i = max(-self.M, min(i, self.head))
            j = min(i + self.M, len(self.stations) - 1)
            if j + 1 >= len(self.stations):
                # sampling exactly at the current head: no following station yet,
                # so use the head position and the incoming segment direction
                pos[k] = self.stations[j]
                d = self.stations[j] - self.stations[j - 1]
            else:
                pos[k] = (1.0 - w) * self.stations[j] + w * self.stations[j + 1]
                d = self.stations[j + 1] - self.stations[j]
            psi[k] = math.degrees(math.atan2(d[1], d[0]))
        return pos, psi

    def vessel_states(self, turn: int, offsets: np.ndarray):
        """Positions/headings of all vessels at an executed turn index."""
        return self.sample(turn * self.v / self.seg, offsets)


# --------------------------------------------------------------- payoff
def stage_L(game, sB: LeaderState, sR: LeaderState, turn: int,
            offs: np.ndarray) -> float:
    """Instantaneous stage payoff L at an executed turn index."""
    posB, psiB = sB.vessel_states(turn, offs)
    posR, psiR = sR.vessel_states(turn, offs)
    L = 0.0
    for kb in range(len(offs)):
        for kr in range(len(offs)):
            dx = posR[kr, 0] - posB[kb, 0]
            dy = posR[kr, 1] - posB[kb, 1]
            r = max(math.hypot(dx, dy), 0.5)
            brg = math.degrees(math.atan2(dy, dx))
            dB = wrap_deg(brg - psiB[kb])
            dR = wrap_deg(brg + 180.0 - psiR[kr])
            L += (game.kB.fire(r, float(dB), 6, _aspect_arr(np.array([dR]))[0])
                  - game.kR.fire(r, float(dR), 6, _aspect_arr(np.array([dB]))[0]))
    return L


def interval_reward(game, sB: LeaderState, sR: LeaderState, turn: int,
                    offs: np.ndarray) -> float:
    """Trapezoid reward for the interval [turn, turn+1) using the states at the
    interval endpoints (v11 section 2)."""
    L0 = stage_L(game, sB, sR, turn, offs)
    L1 = stage_L(game, sB, sR, turn + 1, offs)
    return 0.5 * (L0 + L1)


# ---------------------------------------------- remaining-horizon solve
def enumerate_sequences(levels, R: int) -> np.ndarray:
    return np.array(list(itertools.product(levels, repeat=R))) * OMEGA_MAX


def _lp(pay: np.ndarray):
    from scipy.optimize import linprog
    m, n = pay.shape
    c = np.zeros(m + 1); c[-1] = -1.0
    A_ub = np.zeros((n, m + 1)); A_ub[:, :m] = -pay.T; A_ub[:, m] = 1.0
    A_e = np.zeros((1, m + 1)); A_e[0, :m] = 1.0
    rB = linprog(c, A_ub=A_ub, b_ub=np.zeros(n), A_eq=A_e, b_eq=[1.0],
                 bounds=[(0, None)] * m + [(None, None)])
    cR = np.zeros(n + 1); cR[-1] = 1.0
    A2 = np.zeros((m, n + 1)); A2[:, :n] = pay; A2[:, n] = -1.0
    A_e2 = np.zeros((1, n + 1)); A_e2[0, :n] = 1.0
    rR = linprog(cR, A_ub=A2, b_ub=np.zeros(m), A_eq=A_e2, b_eq=[1.0],
                 bounds=[(0, None)] * n + [(None, None)])
    if not (rB.success and rR.success):
        bi = int(np.argmax(pay.min(axis=1)))
        x = np.zeros(m); x[bi] = 1.0
        rj = int(np.argmin(pay.max(axis=0)))
        y = np.zeros(n); y[rj] = 1.0
        return float(pay[bi].min()), x, y
    x = np.clip(rB.x[:m], 0, None); x = x / x.sum()
    y = np.clip(rR.x[:n], 0, None); y = y / y.sum()
    return float((rB.x[-1] + rR.x[-1]) / 2), x, y


def scalar_interval_payoff(game, sB0: LeaderState, sR0: LeaderState,
                          seqB, seqR, R: int) -> float:
    """Scalar reference implementation (used to validate the vectorised path)."""
    a = sB0.clone(); b = sR0.clone()
    offs = line_ahead_offsets(game.spacing, game.n_ships)
    tot = 0.0
    for t in range(R):
        L0 = stage_L(game, a, b, t, offs)
        a.extend_plan([seqB[t]])
        b.extend_plan([seqR[t]])
        L1 = stage_L(game, a, b, t + 1, offs)
        tot += 0.5 * (L0 + L1)
    return tot


def batch_interval_payoff(game, sB0: LeaderState, sR0: LeaderState,
                          cands: np.ndarray, opp: np.ndarray, blue: bool,
                          R: int) -> np.ndarray:
    """Vectorised trapezoid interval payoff over R remaining steps.

    `cands` (n, R) are the candidate per-turn turn rates for the side given by
    `blue`; `opp` (R,) is the fixed opponent sequence.  Both sides start from
    the supplied leader states (which carry the realised path history), so the
    follower positions stay consistent with the leader's actual track.
    """
    n = cands.shape[0]
    offs = line_ahead_offsets(game.spacing, game.n_ships)
    K = len(offs)
    seqB = cands if blue else np.broadcast_to(opp, (n, R))
    seqR = np.broadcast_to(opp, (n, R)) if blue else cands

    def build(state: LeaderState, seqs: np.ndarray):
        """Station array (n, npts, 2) = shared history + candidate extension."""
        hist = state.stations                      # (Hpts, 2)
        npts = len(hist) + state.n_sub * R
        st = np.zeros((n, npts, 2))
        st[:, :len(hist)] = hist[None, :, :]
        j = len(hist) - 1
        step = np.asarray(seqs, float) / state.n_sub
        for tt in range(R):
            for _ in range(state.n_sub):
                d = st[:, j] - st[:, j - 1]
                phi = np.degrees(np.arctan2(d[:, 1], d[:, 0])) + step[:, tt]
                h = np.radians(phi)
                st[:, j + 1, 0] = st[:, j, 0] + state.seg * np.cos(h)
                st[:, j + 1, 1] = st[:, j, 1] + state.seg * np.sin(h)
                j += 1
        return st

    stB = build(sB0, seqB)
    stR = build(sR0, seqR)
    ar = np.arange(n)
    M = sB0.M
    segB, segR = sB0.seg, sR0.seg
    head0 = sB0.head

    def vessel(st, seg, q_scalar, Mside, headmax):
        """Positions (n, K, 2) and headings (n, K) at a fractional station."""
        pos = np.zeros((n, K, 2)); psi = np.zeros((n, K))
        for k, ell in enumerate(offs):
            q = np.full(n, q_scalar - ell / seg)
            i = np.floor(q).astype(int); w = q - i
            i = np.clip(i, -Mside, headmax)
            j = i + Mside
            j = np.clip(j, 0, st.shape[1] - 1)
            jn = np.clip(j + 1, 0, st.shape[1] - 1)
            pos[:, k, :] = (1 - w)[:, None] * st[ar, j] + w[:, None] * st[ar, jn]
            d = st[ar, jn] - st[ar, j]
            # at the head the forward difference is zero; fall back to the incoming segment
            zero = np.abs(d).sum(axis=1) < 1e-12
            if zero.any():
                jm = np.clip(j - 1, 0, st.shape[1] - 1)
                d = np.where(zero[:, None], st[ar, j] - st[ar, jm], d)
            psi[:, k] = np.degrees(np.arctan2(d[:, 1], d[:, 0]))
        return pos, psi

    headB, headR = sB0.head, sR0.head
    MB, MR = sB0.M, sR0.M

    def L_at(turn: int) -> np.ndarray:
        # station index measured from the epoch start, offset by the current head
        pB, psiB = vessel(stB, segB, headB + turn * sB0.n_sub, MB,
                          headB + sB0.n_sub * R)
        pR, psiR = vessel(stR, segR, headR + turn * sR0.n_sub, MR,
                          headR + sR0.n_sub * R)
        out = np.zeros(n)
        for kb in range(K):
            for kr in range(K):
                dx = pR[:, kr, 0] - pB[:, kb, 0]
                dy = pR[:, kr, 1] - pB[:, kb, 1]
                r = np.maximum(np.hypot(dx, dy), 0.5)
                brg = np.degrees(np.arctan2(dy, dx))
                dB = wrap_deg(brg - psiB[:, kb])
                dR = wrap_deg(brg + 180.0 - psiR[:, kr])
                out += (fire_vec(game.kB, r, dB, _aspect_arr(dR))
                        - fire_vec(game.kR, r, dR, _aspect_arr(dB)))
        return out

    total = np.zeros(n)
    for t in range(R):
        total += 0.5 * (L_at(t) + L_at(t + 1))
    return total


class RemainingHorizonGame:
    """Open-loop zero-sum game over R remaining steps from a given state pair.

    The payoff of a plan pair is the sum of interval rewards over the remaining
    steps (gamma = 1 for the main experiment), evaluated with the leader states
    extended along the candidate turn-rate sequences.
    """

    def __init__(self, game, sB: LeaderState, sR: LeaderState, R: int,
                 levels, cache: dict, do_iters: int = 15, gap_tol: float = 0.01):
        self.game = game
        self.offs = line_ahead_offsets(game.spacing, game.n_ships)
        self.R = R
        self.levels = levels
        self.seqs = enumerate_sequences(levels, R)
        self.n = len(self.seqs)
        self.cache = cache            # shared payoff cache across epochs
        self.do_iters = do_iters
        self.gap_tol = gap_tol
        self.sB0 = sB.clone()
        self.sR0 = sR.clone()
        self.sk = state_key(sB, sR)      # discretised state, for cache sharing

    # ---- payoff with caching --------------------------------------
    def _columns(self, j: int) -> np.ndarray:
        """J(all Blue candidates, fixed Red plan j); cached across epochs/seeds."""
        key = (self.sk, self.R, "col", j)
        if key not in self.cache:
            self.cache[key] = batch_interval_payoff(
                self.game, self.sB0, self.sR0, self.seqs, self.seqs[j], True, self.R)
        return self.cache[key]

    def _rows(self, i: int) -> np.ndarray:
        """J(fixed Blue plan i, all Red candidates); cached across epochs/seeds."""
        key = (self.sk, self.R, "row", i)
        if key not in self.cache:
            self.cache[key] = batch_interval_payoff(
                self.game, self.sB0, self.sR0, self.seqs, self.seqs[i], False, self.R)
        return self.cache[key]

    def payoff(self, i: int, j: int) -> float:
        return float(self._columns(j)[i])

    def solve(self):
        seeds = [int(np.argmin(np.abs(self.seqs -
                                      np.full(self.R, a * OMEGA_MAX)).sum(axis=1)))
                 for a in (0.0, 0.5, -0.5, 1.0, -1.0)]
        X = list(dict.fromkeys(seeds)); Y = list(X)
        V = LB = UB = float("nan"); xr = yr = None
        for _ in range(self.do_iters):
            pay = np.zeros((len(X), len(Y)))
            for b, j in enumerate(Y):
                pay[:, b] = self._columns(j)[X]
            V, xr, yr = _lp(pay)
            X_last, Y_last = list(X), list(Y)      # snapshot for final assembly
            xf = np.zeros(self.n); xf[X] = xr
            yf = np.zeros(self.n); yf[Y] = yr
            expR = np.zeros(self.n)
            for i in np.where(xf > 0)[0]:
                expR += xf[i] * self._rows(int(i))
            jmin = int(np.argmin(expR)); LB = float(expR[jmin])
            expB = np.zeros(self.n)
            for j in np.where(yf > 0)[0]:
                expB += yf[j] * self._columns(int(j))
            imax = int(np.argmax(expB)); UB = float(expB[imax])
            if (UB - LB) / max(1.0, abs(V)) < self.gap_tol:
                break
            newX = imax not in X; newY = jmin not in Y
            if newX:
                X.append(imax)
            if newY:
                Y.append(jmin)
            if not newX and not newY:
                break
        xf = np.zeros(self.n); xf[X_last] = xr
        yf = np.zeros(self.n); yf[Y_last] = yr
        return {"V": float(V), "x": xf / xf.sum(), "y": yf / yf.sum(),
                "LB": LB, "UB": UB, "rel_gap": (UB - LB) / max(1.0, abs(V)),
                "n_full": self.n, "support_B": int((xf > 0).sum()),
                "support_R": int((yf > 0).sum())}


def state_key(sB: LeaderState, sR: LeaderState) -> tuple:
    """Discretised key so that the solver cache is shared across Monte Carlo
    samples that realise the same trajectory prefix."""
    def k(s):
        p = s.stations[s.head]
        d = s.stations[s.head] - s.stations[max(s.head - 1, 0)]
        return (round(float(p[0]), 2), round(float(p[1]), 2),
                round(math.degrees(math.atan2(d[1], d[0])), 1))
    return k(sB) + k(sR) + (sB.head,)


def run_cadence(game, sB0: LeaderState, sR0: LeaderState, h: int, T: int,
                levels, cache: dict, rng: np.random.Generator,
                do_iters: int = 4) -> dict:
    """Execute one matched-horizon episode with replanning cadence h.

    Returns the realised total interval reward and per-step diagnostics.  The
    planner re-solves the remaining-horizon game at every replanning epoch and
    samples both sides from the COMPLETE equilibrium mixture.
    """
    sB, sR = sB0.clone(), sR0.clone()
    offs = line_ahead_offsets(game.spacing, game.n_ships)
    total = 0.0
    t = 0
    epochs = []
    while t < T:
        R = T - t
        Vg = RemainingHorizonGame(game, sB, sR, R, levels, cache, do_iters=do_iters)
        sol = Vg.solve()
        ib = int(rng.choice(len(sol["x"]), p=sol["x"]))
        ir = int(rng.choice(len(sol["y"]), p=sol["y"]))
        planB, planR = Vg.seqs[ib], Vg.seqs[ir]
        run = min(h, R)
        for k in range(run):
            L0 = stage_L(game, sB, sR, t, offs)
            sB.extend_plan([planB[k]])
            sR.extend_plan([planR[k]])
            L1 = stage_L(game, sB, sR, t + 1, offs)
            total += 0.5 * (L0 + L1)
            t += 1
        epochs.append({"t_end": t, "R": R, "V": sol["V"],
                       "LB": sol["LB"], "UB": sol["UB"],
                       "rel_gap": sol["rel_gap"],
                       "support_B": sol["support_B"], "support_R": sol["support_R"]})
    return {"J": total, "epochs": epochs,
            "final_B": sB, "final_R": sR}


def mc_expectation(game, h: int, T: int, levels, cache: dict, n_seeds: int,
                   seed0: int, do_iters: int = 4) -> dict:
    """Paired-seed Monte Carlo evaluation of the receding policy at cadence h."""
    from research.formation.path_following import make_lf_game  # noqa: F401
    raise NotImplementedError("use the experiment script's runner")


def initial_states(game) -> tuple[LeaderState, LeaderState]:
    sB = LeaderState(0.0, 0.0, game.hB0_deg, game.vB, game.n_sub,
                     game.spacing, game.n_ships)
    sR = LeaderState(game.xR0, game.yR0, game.hR0_deg, game.vR, game.n_sub,
                     game.spacing, game.n_ships)
    return sB, sR
