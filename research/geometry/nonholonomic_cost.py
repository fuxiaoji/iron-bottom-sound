"""B5: nonholonomic repositioning cost under engine-faithful pulse kinematics.

Engine semantics (backend engine `_movement_program` / `movement_cost`):
per impulse either "advance" (one cell along the current heading) or a
60-degree turn pulse that changes heading and produces NO displacement.
The existing proxy (committed_game.simulate) DECOUPLES steering from
propulsion: heading updates every step and the ship advances every step.
B5 implements both models on one discrete pulse clock so their difference
IS the nonholonomic coupling cost:

    coupled    (engine-faithful): 3 pulses/turn; a turn pulse (±60 deg)
               consumes its pulse and yields no displacement.
    decoupled  (proxy semantics): 3 pulses/turn; a turn pulse turns AND
               advances speed/3 along the NEW heading (heading update
               precedes advance, as in simulate).

Task: target R starts abeam of B at lateral offset d_perp (both heading
east = 0 deg, R on the +y side), sails straight at 6 units/turn.  B must
bring |y_R - y_B| <= 1 within T_max turns (parallel criterion additionally
requires heading back to 0).  Measured per (d_perp, eta_v, model):

  T_min               first completion turn (pruned-exhaustive BFS)
  heading excursion   sum of |heading| after each turn (deg, until completion)
  exposure            sum |L| over the horizon (L = expected-hits differential)
  J_stay, J_man       cumulative net fire differential over the SAME horizon,
                      holding course vs best completion plan
  C_reposition        J_stay - J_man  (positive = staying was better)

Search: breadth-first over pulse depth with exact geometry dedup
((x, y, h, k) lattice); per key the run-optimal partial objective is kept
(optimal substructure: future payoff depends only on geometry).  Firing is
one exchange per turn after movement (engine: gunnery follows movement);
kernel target speeds = ACTUAL operating speeds (B: 6*eta_v, R: 6;
KernelWrap clips to its 0..5 support) — a documented deviation from the
E02 constant-6 convention, engine-faithful for v < 4.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

PULSES_PER_TURN = 3
TURN_DEG = 60.0
R_SPEED = 6.0            # target ship: 6 units/turn straight, heading 0
LAT_TOL = 1.0            # "within 1 grid cell"
HEADING_LIMIT = 120.0    # no reversal drills (engine rejects 180 deg)
MAX_DX = 28.0            # prune along-track gaps beyond kernel support
GAMMA_DISC = 0.96


@dataclass(frozen=True)
class PulseModel:
    coupled: bool  # True: turn pulse consumes the pulse without advancing

    @property
    def name(self) -> str:
        return "coupled_60" if self.coupled else "decoupled"


COUPLED = PulseModel(True)
DECOUPLED = PulseModel(False)


def _wrap180(a: float) -> float:
    return (a + 180.0) % 360.0 - 180.0


def _aspect(delta_deg: float) -> str:
    a = abs(_wrap180(delta_deg))
    return "bow_stern" if (a <= 30.0 or a >= 150.0) else "broadside"


def fire_differential(kB, kR, xB: float, yB: float, hB: float,
                      xR: float, yR: float, speedB: float,
                      speedR: float) -> tuple[float, float]:
    """One simultaneous exchange at the given (post-movement) geometry.

    Returns (L, own_damage): L = expected hits by B - expected hits on B,
    own_damage = expected hits B receives.  R's heading is 0 by the task.
    """
    dx, dy = xR - xB, yR - yB
    r = max(math.hypot(dx, dy), 0.5)
    bearing = math.degrees(math.atan2(dy, dx))
    delta_B = _wrap180(bearing - hB)            # target off B's bow
    delta_R = _wrap180(bearing + 180.0)         # B off R's bow (R heads 0)
    aB, aR = _aspect(delta_B), _aspect(delta_R)
    hits_by_B = kB.fire(r, delta_B, int(min(max(speedR, 0), 5)), aR)
    hits_on_B = kR.fire(r, delta_R, int(min(max(speedB, 0), 5)), aB)
    return hits_by_B - hits_on_B, hits_on_B


def analytic_lower_bound_turns(d: float, eta_v: float, coupled: bool,
                               tol: float = LAT_TOL) -> int:
    """T_min lower bound: lateral gain <= eta_v*sqrt(3) per advance (60-deg
    leg); coupled needs 2 turn pulses to leave/return heading 0; 3 pulses
    per turn."""
    adv = math.ceil(max(d - tol, 0.0) / (eta_v * math.sqrt(3.0)) - 1e-9)
    pulses = adv + (2 if coupled else 0)
    return math.ceil(pulses / PULSES_PER_TURN - 1e-9)


@dataclass
class RepositionResult:
    d_perp: float
    eta_v: float
    model: str
    feasible: bool = False
    T_min_literal: int | None = None      # lateral <= 1 (spec-literal)
    T_min_parallel: int | None = None     # + heading back to 0
    J_stay: float = 0.0
    J_man: float = float("nan")
    C_reposition: float = float("nan")    # J_stay - J_man
    exposure_man: float = float("nan")
    exposure_stay: float = 0.0
    damage_man: float = float("nan")
    damage_stay: float = 0.0
    excursion_man: float = float("nan")
    best_plan: str = ""                   # pulse actions, '-' per turn
    best_plan_completion_turn: int | None = None
    best_traj: list = field(default_factory=list)
    min_lateral_reached: float = float("inf")
    analytic_bound_turns: int = 0
    bound_respected: bool = True
    n_states_expanded: int = 0
    n_states_retained: int = 0


class RepositionProblem:
    def __init__(self, kB, kR, d_perp: float, eta_v: float,
                 model: PulseModel, T_max: int = 6,
                 horizon: int | None = None, lat_tol: float = LAT_TOL):
        self.kB, self.kR = kB, kR
        self.d = float(d_perp)
        self.eta_v = float(eta_v)
        self.model = model
        self.T_max = T_max
        self.horizon = horizon if horizon is not None else T_max
        self.lat_tol = lat_tol
        self.speedB = R_SPEED * eta_v
        self.step = self.speedB / PULSES_PER_TURN
        self._parents: dict[tuple, tuple[tuple | None, str]] = {}

    # ---------------- kinematics ----------------
    def _apply(self, geo: tuple, action: str, t_boundary: int):
        """Advance one pulse from geometry geo=(x, y, h, k).

        Returns new geometry, or None if the action is illegal (reversal).
        Fires when the pulse closes a turn; returns (geo2, L, dmg) then.
        """
        x, y, h, k = geo
        if action == "A":
            x2 = x + self.step * math.cos(math.radians(h))
            y2 = y + self.step * math.sin(math.radians(h))
            h2 = h
        else:
            h2 = h + TURN_DEG if action == "U" else h - TURN_DEG
            if abs(h2) > HEADING_LIMIT + 1e-9:
                return None
            x2, y2 = x, y
            if not self.model.coupled:   # steering free: turn AND advance
                x2 = x + self.step * math.cos(math.radians(h2))
                y2 = y + self.step * math.sin(math.radians(h2))
        k2 = k + 1
        L = dmg = 0.0
        fired = False
        if k2 % PULSES_PER_TURN == 0:    # turn boundary: gunnery phase
            L, dmg = fire_differential(self.kB, self.kR, x2, y2, h2,
                                       R_SPEED * t_boundary, self.d,
                                       self.speedB, R_SPEED)
            fired = True
        return (x2, y2, h2, k2 % PULSES_PER_TURN), L, dmg, fired

    # ---------------- hold-after-completion rollout ----------------
    def _hold_suffix(self, x0: float, y0: float, t0: int) -> tuple[float, float, float]:
        """(J, exposure, damage) for turns t0+1..horizon holding heading 0."""
        key = (round(x0, 6), round(y0, 6), t0)
        memo = self._hold_memo
        if key in memo:
            return memo[key]
        J = ex = dm = 0.0
        x = x0
        for t in range(t0 + 1, self.horizon + 1):
            x += self.speedB
            L, dmg = fire_differential(self.kB, self.kR, x, y0, 0.0,
                                       R_SPEED * t, self.d,
                                       self.speedB, R_SPEED)
            J += L
            ex += abs(L)
            dm += dmg
        memo[key] = (J, ex, dm)
        return J, ex, dm

    # ---------------- main search ----------------
    def solve(self, objective: str = "J") -> RepositionResult:
        """objective: 'J' maximizes net differential among completions;
        'exposure' minimizes sum |L| among completions."""
        assert objective in ("J", "exposure")
        res = RepositionResult(d_perp=self.d, eta_v=self.eta_v,
                               model=self.model.name)
        res.analytic_bound_turns = analytic_lower_bound_turns(
            self.d, self.eta_v, self.model.coupled)
        self._parents = {}
        self._hold_memo = {}
        self._n_retained = 0

        # ---- stay baseline over the same horizon ----
        jS = eS = dS = 0.0
        for t in range(1, self.horizon + 1):
            L, dmg = fire_differential(self.kB, self.kR,
                                       self.speedB * t, 0.0, 0.0,
                                       R_SPEED * t, self.d,
                                       self.speedB, R_SPEED)
            jS += L
            eS += abs(L)
            dS += dmg
        res.J_stay, res.exposure_stay, res.damage_stay = jS, eS, dS

        start = (0.0, 0.0, 0.0, 0)
        self._parents[start] = (None, "")
        frontier: dict[tuple, tuple] = {start: (0.0, 0.0, 0.0, 0.0)}
        # frontier values: (J, exposure, damage, excursion) running sums
        tmin_lit = tmin_par = None
        min_lat = float("inf")
        best = None   # (score, geo, t_complete, totals)

        for depth in range(1, self.T_max * PULSES_PER_TURN + 1):
            t_bound = depth // PULSES_PER_TURN
            boundary = depth % PULSES_PER_TURN == 0
            nxt: dict[tuple, tuple] = {}
            for geo, acc in frontier.items():
                self._n_retained += 1
                for action in ("A", "U", "D"):
                    out = self._apply(geo, action, t_bound)
                    if out is None:
                        continue
                    geo2, L, dmg, fired = out
                    J, ex, dm, exc = acc
                    if fired:
                        J += L
                        ex += abs(L)
                        dm += dmg
                        exc += abs(geo2[2])
                    key2 = (round(geo2[0], 6), round(geo2[1], 6), geo2[2], geo2[3])
                    if boundary:
                        lat = abs(geo2[1] - self.d)
                        if lat < min_lat:
                            min_lat = lat
                        if lat <= self.lat_tol:
                            if tmin_lit is None:
                                tmin_lit = t_bound
                            if geo2[2] == 0.0:
                                if tmin_par is None:
                                    tmin_par = t_bound
                                jT, exT, dmT = self._hold_suffix(
                                    geo2[0], geo2[1], t_bound)
                                totals = (J + jT, ex + exT, dm + dmT, exc)
                                score = totals[0] if objective == "J" \
                                    else -totals[1]
                                if best is None or score > best[0]:
                                    best = (score, geo2, t_bound, totals)
                    old = nxt.get(key2)
                    if old is None or (J > old[0] if objective == "J"
                                       else ex < old[1]):
                        self._parents[key2] = (geo, action)
                        nxt[key2] = (J, ex, dm, exc)
            # prune
            frontier = {}
            for key2, acc in nxt.items():
                if key2[1] < -2.0 or key2[1] > self.d + 2.0:
                    continue
                if abs(key2[0] - R_SPEED * t_bound) > MAX_DX:
                    continue
                frontier[key2] = acc
            if not frontier:
                break

        res.T_min_literal, res.T_min_parallel = tmin_lit, tmin_par
        res.min_lateral_reached = min_lat
        res.n_states_expanded = self._n_retained
        res.n_states_retained = len(self._parents)
        if best is not None:
            _, geo_b, t_comp, (J, ex, dm, exc) = best
            res.feasible = True
            res.J_man, res.exposure_man = J, ex
            res.damage_man, res.excursion_man = dm, exc
            res.C_reposition = res.J_stay - J
            res.best_plan_completion_turn = t_comp
            res.best_plan = self._plan_string(geo_b)
            res.bound_respected = (tmin_par is None
                                   or tmin_par >= res.analytic_bound_turns)
            res.best_traj = self._trajectory(geo_b)
        return res

    # ---------------- reconstruction ----------------
    def _chain(self, geo: tuple) -> list[tuple]:
        chain = []
        key = (round(geo[0], 6), round(geo[1], 6), geo[2], geo[3])
        while True:
            parent, action = self._parents[key]
            if parent is None:
                break
            chain.append((key, action))
            key = parent
        chain.reverse()
        return chain

    def _plan_string(self, geo: tuple) -> str:
        acts = [a for _, a in self._chain(geo)]
        turns = ["".join(acts[i:i + PULSES_PER_TURN])
                 for i in range(0, len(acts), PULSES_PER_TURN)]
        return "-".join(turns)

    def _trajectory(self, geo: tuple) -> list[dict]:
        """Replay the best plan to completion, then hold, recording geometry
        and per-turn fire at each turn boundary."""
        chain = self._chain(geo)
        g = (0.0, 0.0, 0.0, 0)
        traj = []
        for i, (key, action) in enumerate(chain, start=1):
            out = self._apply(g, action, i // PULSES_PER_TURN)
            g = out[0]
            if i % PULSES_PER_TURN == 0:
                t = i // PULSES_PER_TURN
                traj.append({"t": t, "x": round(g[0], 3), "y": round(g[1], 3),
                             "h": g[2], "lat": round(abs(g[1] - self.d), 3),
                             "x_R": R_SPEED * t})
        return traj


def canonical_plan(d: float, eta_v: float, coupled: bool) -> tuple[str, int]:
    """Hand-built minimal maneuver (U, A*n, D, hold) for cross-checks:
    returns (pulse plan string, completion turn)."""
    step_lat = eta_v * math.sqrt(3.0)
    n = math.ceil(max(d - LAT_TOL, 0.0) / step_lat - 1e-9)
    if abs(n * step_lat - d) > LAT_TOL + 1e-9 and n * step_lat > d + LAT_TOL:
        n = max(0, n - 1)  # allow the one-pulse-coarser lattice point
    pulses = (["U"] + ["A"] * n + ["D"]) if coupled else \
             (["U"] + ["A"] * max(n - 1, 0) + ["D"])
    t_comp = math.ceil(len(pulses) / PULSES_PER_TURN - 1e-9)
    return "-".join("".join(pulses[i:i + PULSES_PER_TURN])
                    for i in range(0, len(pulses), PULSES_PER_TURN)), t_comp
