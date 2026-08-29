"""Adaptive, explainable torpedo tactics above the authoritative rules engine.

This module never adjudicates a hit and never mutates ``GameState``.  It builds a
deterministic public-information route model, compares the opponent''s best response
with and without a proposed torpedo lane, and returns ordinary ``TorpedoOrder`` objects
which the engine validates through the same path used by humans and LLM players.
"""

from __future__ import annotations

from collections import defaultdict
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from .models import HexCoord, PublicShip, Side, TorpedoOrder


class TorpedoDoctrine(StrEnum):
    DIRECT_ATTACK = "direct_attack"
    AREA_DENIAL = "area_denial"
    BREAK_CROSSING_T = "break_crossing_t"
    FORMATION_SPLIT = "formation_split"
    CROSSFIRE = "crossfire"
    COVER_WITHDRAWAL = "cover_withdrawal"
    RESERVE = "reserve"


class EnemyRouteHypothesis(BaseModel):
    ship_id: str
    category: str
    probability: float = Field(ge=0, le=1)
    path: list[str]
    final_hex: str
    final_heading: int = Field(ge=1, le=6)
    speed: int = Field(ge=0)
    base_utility: float
    crossing_t_value: float = 0.0
    formation_cohesion: float = 0.0


class CounterfactualResponse(BaseModel):
    ship_id: str
    baseline_route: str
    threatened_route: str
    forced_deviation: int = Field(ge=0)
    speed_loss: int = Field(ge=0)
    fire_position_loss: float
    crossing_t_loss: float
    formation_split: float
    local_force_ratio_gain: float
    route_changed: bool


class TorpedoTacticalOption(BaseModel):
    option_id: str
    doctrine: TorpedoDoctrine
    order: dict[str, Any]
    target_id: str
    predicted_path: list[str]
    expected_hits: float
    denial_score: float
    opportunity_cost: float
    score: float
    response: CounterfactualResponse


class TorpedoDecisionAudit(BaseModel):
    doctrine: TorpedoDoctrine
    situation: str
    route_hypotheses: list[EnemyRouteHypothesis] = Field(default_factory=list)
    top_candidates: list[TorpedoTacticalOption] = Field(default_factory=list)
    selected_option_ids: list[str] = Field(default_factory=list)
    reserve_reason: str | None = None
    orders: list[dict[str, Any]] = Field(default_factory=list)


def _turn(heading: int, delta: int) -> int:
    return ((heading - 1 + delta) % 6) + 1


def _safe_step(state, position: HexCoord, heading: int) -> HexCoord | None:
    dq, dr = HexCoord.direction_delta(heading)
    q, r = position.q + dq, position.r + dr
    if not (0 <= q < 34 and 0 <= r < 27):
        return None
    nxt = HexCoord(q=q, r=r)
    if nxt.label in state.land_hexes:
        return None
    return nxt


def _bearing_toward(source: HexCoord, target: HexCoord) -> int:
    def raw_distance(heading: int) -> int:
        dq, dr = HexCoord.direction_delta(heading)
        q, r = source.q + dq, source.r + dr
        delta_q, delta_r = q - target.q, r - target.r
        return max(abs(delta_q), abs(delta_r), abs(delta_q + delta_r))
    return min(range(1, 7), key=raw_distance)


def _route_key(route: EnemyRouteHypothesis) -> str:
    return f"{route.category}:{route.final_hex}:h{route.final_heading}:s{route.speed}"


class AdaptiveTorpedoPlanner:
    """Rolling-horizon counterfactual planner with a small deterministic beam search."""

    MAX_ROUTES_PER_SHIP = 24
    TOP_PER_LAUNCHER = 8
    BEAM_WIDTH = 32

    def __init__(self, profile: Any) -> None:
        self.profile = profile

    def enemy_routes(self, engine, state, side: Side) -> list[EnemyRouteHypothesis]:
        observation = engine.observe(state.game_id, side)
        enemies = sorted(
            (ship for ship in observation.ships if ship.side != side and ship.position and not ship.sunk),
            key=lambda ship: ship.id,
        )
        own = [ship for ship in observation.ships if ship.side == side and ship.position and not ship.sunk]
        result: list[EnemyRouteHypothesis] = []
        for enemy in enemies:
            result.extend(self._routes_for_ship(state, enemy, enemies, own))
        return result

    def _routes_for_ship(
        self, state, enemy: PublicShip, enemies: list[PublicShip], own: list[PublicShip],
    ) -> list[EnemyRouteHypothesis]:
        assert enemy.position is not None
        speeds = sorted({
            max(0, enemy.current_speed - 1), enemy.current_speed,
            min(enemy.max_speed or enemy.current_speed + 1, enemy.current_speed + 1),
        })
        patterns = [
            ("straight", 0, None), ("left", -1, 0), ("right", 1, 0),
            ("left", -1, 1), ("right", 1, 1),
        ]
        if any(
            other.id != enemy.id and other.position and other.heading == enemy.heading
            and enemy.position.distance(other.position) <= 3 for other in enemies
        ):
            patterns.append(("formation", 0, None))
        if enemy.hull is not None and enemy.max_hull and enemy.hull / enemy.max_hull <= 0.35:
            patterns.append(("withdrawal", 0, None))
        rows: list[EnemyRouteHypothesis] = []
        for speed in speeds:
            speed_category = "maintain"
            if speed < enemy.current_speed:
                speed_category = "decelerate"
            elif speed > enemy.current_speed:
                speed_category = "accelerate"
            for category, delta, turn_at in patterns:
                position = enemy.position
                heading = enemy.heading
                path = [position.label]
                for mf in range(speed):
                    if turn_at is not None and mf == turn_at:
                        heading = _turn(heading, delta)
                    if category == "withdrawal" and own:
                        nearest = min(own, key=lambda ship: position.distance(ship.position))
                        safe_headings = [h for h in range(1, 7) if _safe_step(state, position, h)]
                        if not safe_headings:
                            break
                        heading = max(
                            safe_headings,
                            key=lambda h: _safe_step(state, position, h).distance(nearest.position),
                        )
                    nxt = _safe_step(state, position, heading)
                    if nxt is None:
                        break
                    position = nxt
                    path.append(position.label)
                if len(path) - 1 != speed:
                    continue
                route_category = category if category not in {"straight", "formation"} else (
                    category if speed == enemy.current_speed else speed_category
                )
                nearest_dist = min((position.distance(ship.position) for ship in own), default=12)
                fire_position = -abs(nearest_dist - 7) / 7.0
                crossing = self._crossing_t_value(position, heading, own)
                cohesion = self._cohesion(position, heading, enemy, enemies)
                prior = {
                    "maintain": 0.27, "straight": 0.27, "formation": 0.30,
                    "left": 0.12, "right": 0.12, "decelerate": 0.08,
                    "accelerate": 0.08, "withdrawal": 0.22,
                }.get(route_category, 0.08)
                rows.append(EnemyRouteHypothesis(
                    ship_id=enemy.id, category=route_category, probability=prior,
                    path=path, final_hex=position.label, final_heading=heading, speed=speed,
                    base_utility=fire_position + crossing + 0.35 * cohesion,
                    crossing_t_value=crossing, formation_cohesion=cohesion,
                ))
        rows.sort(key=lambda route: (-route.probability, -route.base_utility, _route_key(route)))
        rows = rows[: self.MAX_ROUTES_PER_SHIP]
        total = sum(route.probability for route in rows) or 1.0
        return [route.model_copy(update={"probability": route.probability / total}) for route in rows]

    @staticmethod
    def _crossing_t_value(position: HexCoord, heading: int, own: list[PublicShip]) -> float:
        if not own:
            return 0.0
        target = min(own, key=lambda ship: position.distance(ship.position))
        bearing = _bearing_toward(position, target.position)
        relative = (bearing - heading) % 6
        return 1.0 if relative in {1, 2, 4, 5} else 0.0

    @staticmethod
    def _cohesion(
        position: HexCoord, heading: int, enemy: PublicShip, enemies: list[PublicShip],
    ) -> float:
        friends = [ship for ship in enemies if ship.id != enemy.id and ship.position]
        if not friends:
            return 0.0
        distance = min(position.distance(ship.position) for ship in friends)
        aligned = any(ship.heading == heading for ship in friends)
        return (1.0 if 1 <= distance <= 3 else -0.5) + (0.3 if aligned else 0.0)

    def analyze(self, engine, state, side: Side) -> TorpedoDecisionAudit:
        routes = self.enemy_routes(engine, state, side)
        raw = engine.torpedo_tactical_combos(state, side)
        doctrine = self._select_doctrine(engine, state, side, routes, raw)
        options = [self._score_option(row, doctrine, routes) for row in raw]
        options = [option for option in options if option is not None]
        by_launcher: dict[tuple[str, str], list[TorpedoTacticalOption]] = defaultdict(list)
        for option in options:
            order = option.order
            by_launcher[(order["ship_id"], order["launcher_id"])].append(option)
        reduced: list[TorpedoTacticalOption] = []
        for key in sorted(by_launcher):
            ranked = sorted(by_launcher[key], key=lambda item: (-item.score, item.option_id))
            reduced.extend(ranked[: self.TOP_PER_LAUNCHER])
        selected = self._beam_select(reduced, doctrine)
        threshold = float(getattr(self.profile, "torpedo_min_tactical_score", 0.15))
        if doctrine == TorpedoDoctrine.RESERVE or not selected or sum(item.score for item in selected) < threshold:
            reason = "反事实收益不足，保留鱼雷等待更高价值航路" if raw else "当前没有合法且对友军安全的鱼雷发射组合"
            return TorpedoDecisionAudit(
                doctrine=TorpedoDoctrine.RESERVE, situation=self._situation(routes, raw),
                route_hypotheses=routes, top_candidates=sorted(options, key=lambda item: (-item.score, item.option_id))[:3],
                reserve_reason=reason,
            )
        orders = [item.order for item in selected]
        return TorpedoDecisionAudit(
            doctrine=doctrine, situation=self._situation(routes, raw), route_hypotheses=routes,
            top_candidates=sorted(options, key=lambda item: (-item.score, item.option_id))[:3],
            selected_option_ids=[item.option_id for item in selected], orders=orders,
        )

    def _select_doctrine(self, engine, state, side, routes, raw) -> TorpedoDoctrine:
        forced = getattr(self.profile, "torpedo_doctrine", "adaptive")
        if forced != "adaptive":
            return TorpedoDoctrine(forced)
        own = [ship for ship in engine.observe(state.game_id, side).ships if ship.side == side]
        if any(ship.command_status in {"detaching", "retreating"} or (
            ship.hull is not None and ship.max_hull and ship.hull / ship.max_hull <= 0.35
        ) for ship in own):
            return TorpedoDoctrine.COVER_WITHDRAWAL
        launcher_count = len({(row["ship_id"], row["launcher_id"]) for row in raw})
        if launcher_count >= 2 and len({row["ship_id"] for row in raw}) >= 2:
            return TorpedoDoctrine.CROSSFIRE
        if any(route.crossing_t_value > 0.5 for route in routes):
            return TorpedoDoctrine.BREAK_CROSSING_T
        if routes and sum(route.formation_cohesion > 0.5 for route in routes) >= 2:
            return TorpedoDoctrine.FORMATION_SPLIT
        if max((float(row.get("expected_hits", 0)) for row in raw), default=0) >= 0.5:
            return TorpedoDoctrine.DIRECT_ATTACK
        return TorpedoDoctrine.AREA_DENIAL if raw else TorpedoDoctrine.RESERVE

    @staticmethod
    def _situation(routes, raw) -> str:
        return f"公开敌方航路假设 {len(routes)} 条；合法安全鱼雷候选 {len(raw)} 个。"

    def _score_option(self, row, doctrine, routes) -> TorpedoTacticalOption | None:
        target_routes = [route for route in routes if route.ship_id == row["target_id"]]
        if not target_routes:
            return None
        lane = set(row.get("predicted_path") or [])
        baseline = max(target_routes, key=lambda route: (route.base_utility, _route_key(route)))

        def threat(route: EnemyRouteHypothesis) -> float:
            hits = len(lane.intersection(route.path))
            near = 0
            if not hits:
                lane_hexes = [HexCoord.from_label(label) for label in lane]
                near = sum(
                    1 for label in route.path
                    if lane_hexes and min(HexCoord.from_label(label).distance(cell) for cell in lane_hexes) <= 1
                )
            return hits * 4.0 + near * 0.75

        threatened = max(
            target_routes,
            key=lambda route: (route.base_utility - threat(route), _route_key(route)),
        )
        base_end = HexCoord.from_label(baseline.final_hex)
        threat_end = HexCoord.from_label(threatened.final_hex)
        changed = _route_key(baseline) != _route_key(threatened)
        response = CounterfactualResponse(
            ship_id=row["target_id"], baseline_route=_route_key(baseline),
            threatened_route=_route_key(threatened), forced_deviation=base_end.distance(threat_end),
            speed_loss=max(0, baseline.speed - threatened.speed),
            fire_position_loss=max(0.0, baseline.base_utility - threatened.base_utility),
            crossing_t_loss=max(0.0, baseline.crossing_t_value - threatened.crossing_t_value),
            formation_split=max(0.0, baseline.formation_cohesion - threatened.formation_cohesion),
            local_force_ratio_gain=0.5 if changed and threat(baseline) > 0 else 0.0,
            route_changed=changed,
        )
        denial = (
            response.forced_deviation * 0.35 + response.speed_loss * 0.45
            + response.fire_position_loss * 0.6 + response.crossing_t_loss * 1.2
            + response.formation_split * 0.8 + response.local_force_ratio_gain
        ) if changed else 0.0
        direct = float(row.get("expected_hits") or 0.0)
        count = int(row["salvo_size"])
        opportunity = 0.08 * count
        weights = {
            TorpedoDoctrine.DIRECT_ATTACK: (2.0, 0.25),
            TorpedoDoctrine.AREA_DENIAL: (0.5, 1.4),
            TorpedoDoctrine.BREAK_CROSSING_T: (0.45, 1.1),
            TorpedoDoctrine.FORMATION_SPLIT: (0.45, 1.2),
            TorpedoDoctrine.CROSSFIRE: (0.8, 0.9),
            TorpedoDoctrine.COVER_WITHDRAWAL: (0.45, 1.25),
            TorpedoDoctrine.RESERVE: (0.0, 0.0),
        }[doctrine]
        score = weights[0] * direct + weights[1] * denial - opportunity
        if doctrine == TorpedoDoctrine.BREAK_CROSSING_T:
            score += response.crossing_t_loss
        elif doctrine == TorpedoDoctrine.FORMATION_SPLIT:
            score += response.formation_split
        order = {
            "ship_id": row["ship_id"], "target_id": row["target_id"],
            "launcher_id": row["launcher_id"], "count": count,
            "launch_at_mf": row["launch_at_mf"], "launch_hex": HexCoord.from_label(row["launch_hex"]).model_dump(mode="json"),
            "bearing": row["launch_heading"], "launch_side": row["launch_side"],
            "launch_angle": row["launch_angle"], "setting_index": row["setting_index"],
        }
        option_id = ":".join(map(str, (
            row["ship_id"], row["launcher_id"], row["launch_at_mf"], row["launch_side"],
            row["launch_angle"], row["setting_index"], row["target_id"], count,
        )))
        return TorpedoTacticalOption(
            option_id=option_id, doctrine=doctrine, order=order, target_id=row["target_id"],
            predicted_path=list(row.get("predicted_path") or []), expected_hits=direct,
            denial_score=denial, opportunity_cost=opportunity, score=score, response=response,
        )

    def _beam_select(
        self, options: list[TorpedoTacticalOption], doctrine: TorpedoDoctrine,
    ) -> list[TorpedoTacticalOption]:
        launchers = sorted({(item.order["ship_id"], item.order["launcher_id"]) for item in options})
        grouped = {
            launcher: [item for item in options if (item.order["ship_id"], item.order["launcher_id"]) == launcher]
            for launcher in launchers
        }
        beams: list[tuple[float, list[TorpedoTacticalOption]]] = [(0.0, [])]
        for launcher in launchers:
            expanded = list(beams)
            for base_score, chosen in beams:
                for option in grouped[launcher]:
                    overlap = sum(
                        len(set(option.predicted_path).intersection(other.predicted_path)) /
                        max(1, len(set(option.predicted_path))) for other in chosen
                    )
                    diversity = 0.0
                    if chosen and doctrine == TorpedoDoctrine.CROSSFIRE:
                        diversity = 0.4 if any(
                            other.order["ship_id"] != option.order["ship_id"] and
                            other.order["bearing"] != option.order["bearing"] for other in chosen
                        ) else 0.0
                    expanded.append((base_score + option.score + diversity - 0.45 * overlap, chosen + [option]))
            expanded.sort(key=lambda item: (-item[0], [option.option_id for option in item[1]]))
            beams = expanded[: self.BEAM_WIDTH]
        return max(beams, key=lambda item: (item[0], [-ord(c) for c in "".join(x.option_id for x in item[1])]))[1]

    def orders(self, engine, state, side: Side) -> tuple[list[TorpedoOrder], TorpedoDecisionAudit]:
        audit = self.analyze(engine, state, side)
        orders = [TorpedoOrder.model_validate(order) for order in audit.orders]
        return orders, audit
