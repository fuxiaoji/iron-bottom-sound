"""Directional firepower kernel: Layer-1 surrogate calibrated to the engine.

Structure (exact, from engine mount arcs via `engine._mount_can_bear`):
    which mounts bear on which relative-bearing sector.

Response surface: the engine adjudicates a shot as a D66 roll shifted by an
integer modifier, mapped through the gunnery hit table.  The kernel keeps
that structure — for each mount-kind and effective firepower it precomputes
h(m) = (1/36) * sum_raw hit_count(fp, d66_adjust(raw, m)) using *engine
functions only* — and fits smooth additive modifier curves
    m(r, v, aspect) = M_range(r) + M_speed(v) + M_long(r) * I[bow/stern]
to ground truth by (1) inverting h to per-cell effective modifiers and
(2) additive least-squares decomposition.  M_range replaces the engine's 8
discrete range bands with a continuous response — that smoothing step (and
its residual) is what E01 measures.

Ground truth scanning mutates ship kinematics only inside a sandbox game
that is never adjudicated (audited by E00).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

import numpy as np

from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import FiringArc, GameState, HexCoord, ShipState

GUN_KINDS = ("primary", "secondary", "tertiary")
SECTOR_FOR_REL = {0: "bow", 1: "starboard", 2: "starboard",
                  3: "stern", 4: "port", 5: "port"}
AXIS_DIRS = {1: (1, -1), 2: (1, 0), 3: (0, 1), 4: (-1, 1), 5: (-1, 0), 6: (0, -1)}
ALL_D66 = tuple(a * 10 + b for a in range(1, 7) for b in range(1, 7))
M_MIN, M_MAX = -45, 25  # modifier search window (engine uses about [-24, +18])


def angle_to_sector(delta_deg: float) -> str:
    """Continuous relative bearing (degrees, + = starboard) -> engine sector."""
    a = (delta_deg + 180.0) % 360.0 - 180.0
    if -30.0 <= a <= 30.0:
        return "bow"
    if 30.0 < a <= 150.0:
        return "starboard"
    if -150.0 <= a < -30.0:
        return "port"
    return "stern"


def rel_of_angle(delta_deg: float) -> int:
    """Continuous relative bearing -> engine relative-bearing index 0..5."""
    return int(round((delta_deg % 360) / 60.0)) % 6


@dataclass
class KernelFit:
    """Fitted kernel for one (attacker ship, target ship-class) pair."""

    attacker_id: str
    attacker_class: str
    target_class: str
    kind_sector_fp: dict[str, dict[str, int]] = field(default_factory=dict)
    range_knots: list[float] = field(default_factory=list)
    kind_m_range: dict[str, list[float]] = field(default_factory=dict)  # per kind
    speed_knots: list[float] = field(default_factory=list)
    kind_m_speed: dict[str, list[float]] = field(default_factory=dict)
    long_knots: list[float] = field(default_factory=list)
    kind_m_long: dict[str, list[float]] = field(default_factory=dict)
    # h(m) response curves per (kind, fp): {"kind:fp": {"m": [...], "h": [...]}}
    response_curves: dict[str, dict[str, list[float]]] = field(default_factory=dict)

    # ---- evaluators ----
    def _m(self, kind: str, r: float, v: int, aspect: str) -> float:
        m = float(np.interp(r, self.range_knots, self.kind_m_range[kind]))
        m += float(np.interp(v, self.speed_knots, self.kind_m_speed[kind]))
        if aspect == "bow_stern":
            m += float(np.interp(r, self.long_knots, self.kind_m_long[kind]))
        return m

    def _h(self, kind: str, fp: int, m: float) -> float:
        curve = self.response_curves.get(f"{kind}:{fp}")
        if curve is None:
            return 0.0
        return float(np.interp(m, curve["m"], curve["h"]))

    def expected_hits(self, r: float, delta_deg: float, target_speed: int = 4,
                      target_aspect: str = "broadside") -> float:
        sector = angle_to_sector(delta_deg)
        total = 0.0
        for kind, sms in self.kind_sector_fp.items():
            fp = sms.get(sector, 0)
            if fp <= 0:
                continue
            total += self._h(kind, fp, self._m(kind, float(r), int(target_speed),
                                               target_aspect))
        return total

    def expected_hits_array(self, r: np.ndarray, delta_deg: float, target_speed: int = 4,
                            target_aspect: str = "broadside") -> np.ndarray:
        sector = angle_to_sector(delta_deg)
        total = np.zeros_like(np.asarray(r, dtype=float))
        for kind, sms in self.kind_sector_fp.items():
            fp = sms.get(sector, 0)
            if fp <= 0:
                continue
            m = np.interp(r, self.range_knots, self.kind_m_range[kind])
            m += float(np.interp(target_speed, self.speed_knots, self.kind_m_speed[kind]))
            if target_aspect == "bow_stern":
                m = m + np.interp(r, self.long_knots, self.kind_m_long[kind])
            curve = self.response_curves[f"{kind}:{fp}"]
            total += np.interp(m, curve["m"], curve["h"])
        return total

    @classmethod
    def from_dict(cls, data: dict) -> "KernelFit":
        fit = cls(attacker_id=data["attacker_id"],
                  attacker_class=data["attacker_class"],
                  target_class=data["target_class"])
        fit.kind_sector_fp = data["kind_sector_fp"]
        fit.range_knots = data["range_knots"]
        fit.kind_m_range = data["kind_m_range"]
        fit.speed_knots = data["speed_knots"]
        fit.kind_m_speed = data["kind_m_speed"]
        fit.long_knots = data["long_knots"]
        fit.kind_m_long = data["kind_m_long"]
        fit.response_curves = data["response_curves"]
        return fit


def response_curve(engine: IronBottomEngine, fp: int) -> dict[str, list[float]]:
    """h(m): exact engine-expected hits for firepower `fp` at modifier m.

    Built by enumerating all 36 raw D66 outcomes through the engine's own
    d66_adjust + hit table.  Structural, not fitted.
    """
    from iron_bottom_sound.engine import d66_adjust

    ms = list(range(M_MIN, M_MAX + 1))
    h = [sum(engine.rules.hit_count(fp, d66_adjust(raw, m)) for raw in ALL_D66) / 36.0
         for m in ms]
    return {"m": [float(x) for x in ms], "h": [float(x) for x in h]}


def expected_hits_exact(engine: IronBottomEngine, state: GameState,
                        attacker: ShipState, target: ShipState,
                        distance: int) -> dict[str, float]:
    """Exact engine-true expected hits per mount kind for one firing phase."""
    from iron_bottom_sound.engine import d66_adjust

    per_kind: dict[str, float] = {}
    for kind in GUN_KINDS:
        mounts = [m for m in attacker.gun_mounts
                  if m.kind == kind and not m.destroyed
                  and IronBottomEngine._mount_can_bear(attacker, target, m.arcs)]
        fp = sum(m.firepower for m in mounts)
        if fp <= 0:
            continue
        caliber = max((m.caliber for m in mounts), default=0) or attacker.primary.caliber
        mod = engine._gunnery_modifier(state, attacker, target, distance, 1, caliber, 1)
        hits = sum(engine.rules.hit_count(fp, d66_adjust(raw, mod)) for raw in ALL_D66)
        per_kind[kind] = hits / 36.0
    return per_kind


def ring_hexes(origin: HexCoord, state: GameState, max_dist: int,
               heading: int) -> list[tuple[HexCoord, int, int]]:
    """Ring hexes with their ENGINE relative bearing: (hex, rel 0..5, dist).

    The engine computes bearings from continuous screen-space angles between
    hex centres (see engine._bearing_between); on the odd-q offset grid these
    are not equal to the axial walk direction, so every bearing label here
    comes from the engine itself.  For each (distance, relative sector) the
    first hex encountered is kept — mount arcs only depend on the sector.
    """
    seen: set[tuple[int, int]] = set()
    out: list[tuple[HexCoord, int, int]] = []
    for dist in range(1, max_dist + 1):
        for dq in range(-dist, dist + 1):
            for dr in range(-dist, dist + 1):
                if max(abs(dq), abs(dr), abs(-dq - dr)) != dist:
                    continue
                q, r = origin.q + dq, origin.r + dr
                if not (0 <= q < state.map_columns and 0 <= r < state.map_rows):
                    continue
                hex_ = HexCoord(q=q, r=r)
                bearing = IronBottomEngine._bearing_between(origin, hex_)
                rel = (bearing - heading) % 6
                key = (rel, dist)
                if key in seen:
                    continue
                seen.add(key)
                out.append((hex_, rel, dist))
    return out


def scan_ground_truth(engine: IronBottomEngine, state: GameState,
                      attacker: ShipState, target: ShipState,
                      max_distance: int = 24,
                      speeds: tuple[int, ...] = (0, 1, 2, 3, 4, 5),
                      target_headings: tuple[int, ...] = (1, 2, 3, 4, 5, 6)) -> list[dict[str, Any]]:
    """Scan (distance, relative bearing, target heading, target speed) grid."""
    origin = attacker.position
    rows: list[dict[str, Any]] = []
    saved = (target.position, target.heading, target.current_speed)
    try:
        for hex_, rel, dist in ring_hexes(origin, state, max_distance, attacker.heading):
            sector = SECTOR_FOR_REL[rel]
            for t_head in target_headings:
                for t_speed in speeds:
                    target.position = hex_
                    target.heading = t_head
                    target.current_speed = t_speed
                    per_kind = expected_hits_exact(engine, state, attacker, target, dist)
                    aspect = IronBottomEngine._target_aspect(attacker, target)
                    row: dict[str, Any] = {
                        "distance": dist, "sector": sector, "rel": rel,
                        "attacker_heading": attacker.heading,
                        "target_heading": t_head, "target_speed": t_speed,
                        "target_aspect": aspect, "total": sum(per_kind.values()),
                    }
                    row.update({f"kind_{k}": v for k, v in per_kind.items()})
                    rows.append(row)
    finally:
        target.position, target.heading, target.current_speed = saved
    return rows


def _invert_modifier(curve: dict[str, list[float]], value: float) -> float:
    """Effective modifier consistent with observed expected hits `value`.

    The engine's D66 convention ranks LOW rolls best (roll 11 = top of the
    hit table, 32+/66 = miss), and good circumstances carry NEGATIVE
    modifiers, so h(m) is non-increasing in m.  Inversion returns, for
    value on the zero plateau, the *first* (least-positive) modifier where
    h reaches zero; otherwise the linearly interpolated crossing point.
    """
    m = curve["m"]
    h = curve["h"]
    for i, hi in enumerate(h):
        if hi <= value:
            if i == 0 or hi == value:
                return m[i]
            frac = (value - h[i]) / (h[i - 1] - h[i])
            return m[i] + frac * (m[i - 1] - m[i])
    return m[-1]


def fit_kernel(engine: IronBottomEngine, rows: list[dict[str, Any]], attacker: ShipState, state: GameState,
               attacker_class: str, target_class: str,
               range_knots: tuple[float, ...] = tuple(range(1, 25)),
               long_knots: tuple[float, ...] = (1, 6, 10, 16, 21)) -> KernelFit:
    """Two-stage calibration: invert per-cell modifiers, decompose additively.

    Stage 1: per (kind, sector) estimate effective firepower fp (max observed
    truth = full broadside), pull the engine response curve h_{fp}(m).
    Stage 2: invert truth to per-cell modifier m_hat; least-squares decompose
        m_hat = M_range(r) + M_speed(v) + M_long(r) * I[bow_stern]
    with M_speed anchored at 0 for the neutral speed v=4.
    """
    fit = KernelFit(attacker_id=attacker.id, attacker_class=attacker_class,
                    target_class=target_class,
                    range_knots=list(range_knots),
                    speed_knots=list(range(0, 7)),
                    long_knots=list(long_knots))
    rk = np.asarray(list(range_knots))
    lk = np.asarray(list(long_knots))
    # Speed dummies only for speeds present in the scan.  Adding columns for
    # unseen speeds would make the least-squares system rank-deficient and
    # pollute the solution (the engine treats every speed >= 4 as neutral).
    speed_vals = sorted({int(row["target_speed"]) for row in rows})

    for kind in GUN_KINDS:
        col = f"kind_{kind}"
        sel = [row for row in rows if col in row]
        if not any(row[col] > 0 for row in sel):
            continue

        # Structural per-sector firepower: exact from mount arcs via the
        # engine's own aspect rule, keyed by the engine's own bearing of the
        # six adjacent hexes.
        sec_fp: dict[str, int] = {sec: 0 for sec in set(SECTOR_FOR_REL.values())}
        pos = attacker.position
        for hex_, rel, _dist in ring_hexes(pos, state, 1, attacker.heading):
            arc = IronBottomEngine._relative_aspect(pos, attacker.heading, hex_)
            bearing_fp = sum(
                mount.firepower for mount in attacker.gun_mounts
                if mount.kind == kind and not mount.destroyed and arc in mount.arcs
            )
            sec_fp[SECTOR_FOR_REL[rel]] = bearing_fp
        fit.kind_sector_fp[kind] = sec_fp

        # per (sector, distance, speed, aspect) mean truth for inversion
        cells: dict[tuple[str, int, int, str], list[float]] = {}
        for row in sel:
            key = (row["sector"], row["distance"], row["target_speed"], row["target_aspect"])
            cells.setdefault(key, []).append(row[col])

        # response curves per distinct fp in this kind
        curves: dict[int, dict[str, list[float]]] = {}
        for sec, fp in sec_fp.items():
            if fp > 0 and fp not in curves:
                curves[fp] = response_curve(engine, fp)
                fit.response_curves[f"{kind}:{fp}"] = curves[fp]

        # per-cell inversion with interval censoring.  Censored cells carry a
        # one-sided bound only; they are imputed from the current model and
        # refit EM-style (fit_uncensored -> impute -> refit).
        cell_records = []  # (dist, v, aspect, kind_status, m_uncens_or_bound)
        for (sec, dist, v, aspect), vals in cells.items():
            fp = sec_fp[sec]
            if fp <= 0:
                continue
            curve = curves[fp]
            mean_truth = float(np.mean(vals))
            h_max = curve["h"][0]
            h_min = curve["h"][-1]
            if mean_truth <= h_min:
                plateau = next(m for m, h in zip(curve["m"], curve["h"]) if h <= h_min)
                cell_records.append((dist, v, aspect, "zero", float(plateau)))
            elif mean_truth >= h_max:
                satur = max(m for m, h in zip(curve["m"], curve["h"]) if h >= h_max)
                cell_records.append((dist, v, aspect, "sat", float(satur)))
            else:
                cell_records.append((dist, v, aspect, "ok",
                                     _invert_modifier(curve, mean_truth)))

        knots = sorted({int(r) for r, _, _, _, _ in cell_records if _ == "ok"} |
                       {int(r) for r, _, _, s, _ in cell_records})
        r_index = {r: i for i, r in enumerate(knots)}
        ncol = len(knots) + (len(speed_vals) - 1) + len(long_knots)

        def design(m_hat_values):
            A_mat = np.zeros((len(cell_records), ncol))
            for i, (dist, v, aspect, status, m_hat) in enumerate(cell_records):
                A_mat[i, r_index[dist]] = 1.0
                if v != 4:
                    A_mat[i, len(knots) + speed_vals.index(v)] = 1.0
                if aspect == "bow_stern":
                    li = max(0, int(np.searchsorted(lk, dist, side="right") - 1))
                    A_mat[i, len(knots) + len(speed_vals) - 1 + li] = 1.0
            return A_mat, np.array(m_hat_values, dtype=float)

        def solve(m_hat_values):
            A_mat, y = design(m_hat_values)
            coef, *_ = np.linalg.lstsq(A_mat, y, rcond=None)
            return coef

        def model_m(coef, dist, v, aspect):
            base = coef[r_index[dist]] if dist in r_index else 0.0
            if v != 4:
                base += coef[len(knots) + speed_vals.index(v)]
            if aspect == "bow_stern":
                li = max(0, int(np.searchsorted(lk, dist, side="right") - 1))
                base += coef[len(knots) + len(speed_vals) - 1 + li]
            return float(base)

        # EM iterations: uncensored cells fixed; censored cells imputed to
        # their bound only while the model violates it.
        m_hat = [rec[4] for rec in cell_records]
        coef = None
        for _ in range(40):
            m_hat = []
            for dist, v, aspect, status, bound in cell_records:
                if status == "ok":
                    m_hat.append(bound)
                else:
                    probe = model_m(coef, dist, v, aspect) if coef is not None else 0.0
                    if status == "zero":
                        m_hat.append(max(probe, bound))
                    else:  # "sat"
                        m_hat.append(min(probe, bound))
            new_coef = solve(m_hat)
            if coef is not None and float(np.max(np.abs(new_coef - coef))) < 1e-6:
                coef = new_coef
                break
            coef = new_coef

        # map per-distance modifiers onto the requested range knots; distances
        # without uncensored cells keep the nearest fitted value on the left
        per_distance = {r: float(coef[r_index[r]]) for r in knots}
        fit.range_knots = [float(k) for k in range(1, 25)]
        prev = 0.0
        fit.kind_m_range[kind] = []
        for k in fit.range_knots:
            if int(k) in per_distance:
                prev = per_distance[int(k)]
            fit.kind_m_range[kind].append(prev)
        m_speed = np.zeros(7)
        for v in speed_vals:
            if v != 4:
                m_speed[v] = coef[len(knots) + speed_vals.index(v)]
        fit.kind_m_speed[kind] = [float(x) for x in m_speed]
        m_long = coef[len(knots) + len(speed_vals) - 1:]
        fit.kind_m_long[kind] = [float(x) for x in m_long]
    return fit
