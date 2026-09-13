"""Geometry policy: receding-horizon open-loop minimax translated to engine orders.

At each MOVEMENT_PLANNING phase the policy measures the true geometry from the
read-only state, solves the committed-maneuver game against the opponent's
most punishing library reply, and executes the first turn of the maximin plan
by selecting the legal engine plan (from `engine.movement_candidates`) that
best matches the desired heading change while preserving speed.  Gunnery
targets maximize expected hits weighted by target value.  No doctrine
heuristics, no hidden information.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "backend" / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "backend" / "src"))
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from iron_bottom_sound.engine import IronBottomEngine  # noqa: E402
from iron_bottom_sound.models import (  # noqa: E402
    FiringArc,
    GameState,
    GunneryOrder,
    HexCoord,
    MovementOrder,
    OrderBatch,
    Phase,
    Side,
    ShipState,
)

from research.geometry.firepower_kernel import KernelFit  # noqa: E402
from research.geometry.committed_game import (  # noqa: E402
    KernelWrap,
    make_maneuver_library,
    open_loop_minimax,
)

_HEADING_DEG = {h: (330.0 + (h - 1) * 60.0) % 360.0 for h in range(1, 7)}


def wrap_deg(a: float) -> float:
    return (a + 180.0) % 360.0 - 180.0


def bearing_deg(origin: HexCoord, target: HexCoord) -> float:
    """Continuous bearing using the engine's own screen-space convention."""
    dq = target.q - origin.q
    dr = target.r - origin.r
    return math.degrees(math.atan2((dr + dq / 2.0) * math.sqrt(3.0), dq * 1.5))


class GeometryPolicy:
    def __init__(self, kernel: KernelFit, horizon: int = 4, commit_turns: int = 3):
        self.kB = KernelWrap(kernel, 1.0, 1.0)
        self.kR = KernelWrap(kernel, 1.0, 1.0)
        self.lib = make_maneuver_library()
        self.horizon = horizon
        self.commit_turns = commit_turns
        self.last_plan = None
        self._committed: list[float] | None = None   # remaining turn deltas
        self._ship_key: str | None = None

    def _geometry(self, ship: ShipState, enemy: ShipState) -> tuple[float, float, float] | None:
        if not ship.position or not enemy.position:
            return None
        brg = bearing_deg(ship.position, enemy.position)
        hB = _HEADING_DEG[ship.heading]
        hR = _HEADING_DEG[enemy.heading]
        return ship.position.distance(enemy.position), brg, hB, hR

    def movement_plan_for(self, engine: IronBottomEngine, state: GameState,
                          ship: ShipState) -> str:
        enemy = self._nearest_enemy(state, ship)
        if enemy is None:
            return "0"
        geo = self._geometry(ship, enemy)
        if geo is None:
            return "0"
        r0, brg, hB, hR = geo
        # committed orders: re-solve only after the committed plan is exhausted
        if not self._committed or self._ship_key != ship.id:
            out = open_loop_minimax(self.kB, self.kR, self.lib, r0=r0,
                                    bearing0_deg=brg, headingB0_deg=hB,
                                    headingR0_deg=hR,
                                    vB=float(ship.current_speed),
                                    vR=float(enemy.current_speed),
                                    steps=self.horizon, gamma=0.9)
            plan = out["maximin_plan_B"]
            delta = float(plan.split("turn")[1]) if plan != "straight" else 0.0
            per_turn = delta / 3.0
            self._committed = [per_turn] * 3
            self._ship_key = ship.id
            self.last_plan = plan
        desired_delta = self._committed.pop(0)
        return self._engine_plan(engine, state, ship, desired_delta)

    def _nearest_enemy(self, state: GameState, ship: ShipState) -> ShipState | None:
        best = None
        best_d = 1e9
        for other in state.ships.values():
            if other.side == ship.side or other.sunk or not other.position:
                continue
            d = ship.position.distance(other.position)
            if d < best_d:
                best_d = d
                best = other
        return best

    def _engine_plan(self, engine: IronBottomEngine, state: GameState,
                     ship: ShipState, desired_delta: float) -> str:
        """Pick the legal engine plan best matching the desired heading change."""
        cands = engine.movement_candidates(state, ship, include_plans=True)
        reachable = cands.get("reachable") or []
        max_cost = int(cands.get("max_cost") or 0)
        target_cost = max(1, min(int(ship.current_speed), max_cost))
        desired_heading = wrap_deg(_HEADING_DEG[ship.heading] + desired_delta)
        best, best_score = None, None
        for entry in reachable:
            plan = entry.get("plan")
            if not plan:
                continue
            cost = int(entry.get("cost", 0))
            fh = entry.get("final_headings") or [ship.heading]
            ang = _HEADING_DEG.get(fh[0], _HEADING_DEG[ship.heading])
            err = abs(wrap_deg(ang - desired_heading))
            score = err + 8.0 * abs(cost - target_cost)
            if best_score is None or score < best_score:
                best_score = score
                best = plan
        return best or "0"

    def gunnery_orders(self, engine: IronBottomEngine, state: GameState,
                       side: Side) -> list[GunneryOrder]:
        orders: list[GunneryOrder] = []
        try:
            options = engine.gunnery_target_options(state, side)
        except Exception:
            options = []
        for opt in options:
            sid = opt.get("ship_id")
            if not sid:
                continue
            best_target, best_score = None, 0.0
            for t in opt.get("targets") or []:
                tid = t.get("target_id")
                hits = float(t.get("expected_hits") or 0.0)
                if not tid or hits <= 0:
                    continue
                target = state.ships.get(tid)
                value = (target.vp if target else 1.0) or 1.0
                score = hits * value
                if score > best_score:
                    best_score = score
                    best_target = tid
            if best_target:
                orders.append(GunneryOrder(ship_id=sid,
                                           primary_target=best_target,
                                           secondary_target=best_target))
        return orders


def geometry_orders(engine: IronBottomEngine, state: GameState, side: Side,
                    policy: GeometryPolicy) -> OrderBatch:
    batch = OrderBatch(side=side, phase=state.phase)
    if state.phase == Phase.MOVEMENT_PLANNING:
        batch.movement = []
        for ship in state.ships.values():
            if ship.side != side or ship.sunk or not ship.position:
                continue
            plan = policy.movement_plan_for(engine, state, ship)
            batch.movement.append(MovementOrder(ship_id=ship.id, plan=plan))
        if not batch.movement:
            batch.movement = [MovementOrder(ship_id=s.id, plan="0")
                              for s in state.ships.values()
                              if s.side == side and s.position]
    elif state.phase == Phase.GUNNERY:
        batch.gunnery = policy.gunnery_orders(engine, state, side)
    return batch
