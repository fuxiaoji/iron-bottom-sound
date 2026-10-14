"""Public-information, cooperative state machine for realistic-mode fleets.

The engine expands every proposed guide route and checks the entire order batch.
Roles, stations and scores below are tactical preferences, never new game rules.
No persistent commander memory is needed: API requests, saves and replays derive
the same state transitions from the current side-filtered observation.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .models import FormationMovementOrder, HexCoord, MovementOrder, OrderBatch, Side
from .realistic_command import expand_movement_orders
from .scenario_guidance import public_search_target

if TYPE_CHECKING:
    from .engine import IronBottomEngine
    from .models import FormationState, GameState, PlayerObservation, PublicShip, ShipState
    from .tactical import TacticalProfile


STATE_LABELS = {
    "search": "搜索接敌", "approach": "协同接敌", "cross_t": "抢占 T 头",
    "torpedo_run": "侧翼雷击", "evade": "规避鱼雷", "cover": "掩护友军",
    "disrupted": "指挥中断直航", "withdraw": "受损编队脱离交战",
}
ROLE_LABELS = {"battle_line": "炮战纵队", "torpedo_wing": "雷击翼队", "screen": "掩护支队"}


@dataclass
class Mission:
    formation_id: str
    role: str
    state: str
    target_id: str | None
    station: HexCoord | None
    partner_id: str | None = None
    flank: int = 0


@dataclass
class Route:
    order: FormationMovementOrder
    paths: dict[str, list[HexCoord]]
    headings: dict[str, int]
    next_paths: dict[str, list[HexCoord]]
    score: float


@dataclass
class TorpedoThreat:
    track_id: str
    paths: list[HexCoord]
    # None: a still-live torpedo stays in its final hex after its speed allowance.
    expires_at: int | None


def vector(position: HexCoord) -> tuple[float, float]:
    return position.q + position.r * 0.5, position.r * math.sqrt(3) * 0.5


def crossing_t_value(position: HexCoord, heading: int, target, standoff: int) -> float:
    """Prefer our broadside across the visible enemy's bow, at useful distance."""
    if not target.position or position == target.position:
        return 0.0
    px, py = vector(position)
    tx, ty = vector(target.position)
    dx, dy = px - tx, py - ty
    distance = math.hypot(dx, dy)
    enemy_dq, enemy_dr = HexCoord.direction_delta(target.heading)
    enemy_dx, enemy_dy = enemy_dq + enemy_dr * 0.5, enemy_dr * math.sqrt(3) * 0.5
    own_dq, own_dr = HexCoord.direction_delta(heading)
    own_dx, own_dy = own_dq + own_dr * 0.5, own_dr * math.sqrt(3) * 0.5
    ahead = max(0.0, (dx * enemy_dx + dy * enemy_dy) / distance)
    broadside = 1.0 - abs((dx * own_dx + dy * own_dy) / distance)
    range_weight = max(0.0, 1.0 - abs(position.distance(target.position) - standoff) / max(standoff, 1))
    return ahead * broadside * range_weight


def friendly_conflicts(paths: dict[str, list[HexCoord]]) -> list[tuple[str, str, int]]:
    """Whole-column reservations include moving followers and stationary endpoints."""
    pairs = {}
    for pulse in range(1, max((len(path) for path in paths.values()), default=1)):
        destinations, edges = {}, {}
        for ship_id in sorted(paths):
            path = paths[ship_id]
            before, after = path[min(pulse - 1, len(path) - 1)], path[min(pulse, len(path) - 1)]
            for other in destinations.get(after, []):
                pairs.setdefault((other, ship_id), pulse)
            for other in edges.get((after, before), []):
                pairs.setdefault((other, ship_id), pulse)
            destinations.setdefault(after, []).append(ship_id)
            edges.setdefault((before, after), []).append(ship_id)
    return [(left, right, pairs[(left, right)]) for left, right in sorted(pairs)]


def visible_torpedo_forecast(engine, state, observation) -> list[TorpedoThreat]:
    """Advisory one-turn paths from visible track cycles, including our own lanes."""
    threats = []
    for track in observation.torpedo_tracks:
        if track.contact_ship_ids or track.range_remaining <= 0:
            continue
        allowance = track.speed_cycle[(state.turn - track.launched_turn) % len(track.speed_cycle)]
        path = [track.position]
        expires = None
        for pulse in range(1, allowance + 1):
            try:
                position = path[-1].neighbor(
                    track.heading, columns=state.map_columns, rows=state.map_rows,
                )
            except ValueError:
                expires = pulse - 1
                break
            if engine._terrain_impassable(state, position):
                expires = pulse - 1
                break
            path.append(position)
            if pulse >= track.range_remaining:
                expires = pulse
                break
        threats.append(TorpedoThreat(track.id, path, expires))
    return threats


def torpedo_contacts(paths: dict[str, list[HexCoord]], threats: list[TorpedoThreat]) -> int:
    count = 0
    for path in paths.values():
        for threat in threats:
            horizon = max(len(path), len(threat.paths)) - 1
            for pulse in range(1, horizon + 1):
                if threat.expires_at is not None and pulse > threat.expires_at:
                    break
                if path[min(pulse, len(path) - 1)] == threat.paths[min(pulse, len(threat.paths) - 1)]:
                    count += 1
                    break
    return count


class CooperativeFormationPlanner:
    """Joint fleet tasking and bounded coordinate search over expanded legal routes."""

    CANDIDATE_LIMIT = 48

    def __init__(self, profile: TacticalProfile) -> None:
        self.profile = profile

    @staticmethod
    def _members(state, formation, order=None):
        detached = set(order.speed_decision.detach_ship_ids) if (
            order and order.speed_decision and order.speed_decision.action == "detach"
        ) else set()
        return [state.ships[item] for item in formation.ship_ids if (
            state.ships[item].position and not state.ships[item].sunk
            and state.ships[item].command_status == "attached" and item not in detached
        )]

    @staticmethod
    def _leader(state, formation, order=None):
        members = CooperativeFormationPlanner._members(state, formation, order)
        return next((ship for ship in members if ship.id == formation.leader_id), members[0] if members else None)

    def missions(self, engine, state, side, observation, baseline) -> list[Mission]:
        own = {ship.id: ship for ship in observation.ships if ship.side == side}
        blocked_guns = {item["ship_id"] for item in engine.gunnery_target_options(state, side)
                        if item["blocked_reason"]}
        enemies = sorted((ship for ship in observation.ships if (
            ship.side != side and ship.position and not ship.sunk
        )), key=lambda ship: ship.id)
        formations = [state.formations[item.formation_id] for item in baseline.formation_movement]
        heavy_ids = [formation.id for formation in formations if any(
            own[item].ship_type in {"BB", "BC", "CB", "CA"}
            for item in formation.ship_ids if item in own
        )]
        # Assign each light wing its nearest side of the shared enemy axis. Reserve
        # alternate sides for wings that start at the same station.
        flank_use: dict[int, int] = {-1: 0, 1: 0}
        main = next((formation for formation in formations if formation.id in heavy_ids), formations[0] if formations else None)
        main_leader = self._leader(state, main) if main else None
        focus = min(enemies, key=lambda ship: (main_leader.position.distance(ship.position), ship.id)) if (
            enemies and main_leader
        ) else None
        search = public_search_target(state, side) if not enemies else None
        if not enemies and search is None and self.profile.fleet_tactics_version >= 4:
            # Workshop scenarios often publish no deployment zones. Search the
            # map's centre, derived from geometry only, rather than reading any
            # hidden enemy positions (or wandering at the board edge forever).
            q = state.map_columns // 2
            search = HexCoord(q=q, r=state.map_rows // 2 - (q - (q & 1)) // 2)
        threats = visible_torpedo_forecast(engine, state, observation)
        result = []
        by_id = {order.formation_id: order for order in baseline.formation_movement}
        for formation in sorted(formations, key=lambda item: (item.id not in heavy_ids, item.id)):
            order = by_id[formation.id]
            leader = self._leader(state, formation, order)
            if leader is None:
                result.append(Mission(formation.id, "screen", "withdraw", None, None))
                continue
            members = self._members(state, formation, order)
            armed = any(launcher.loaded and not launcher.destroyed for ship in members for launcher in ship.torpedo_launchers)
            role = "battle_line" if formation.id in heavy_ids else "torpedo_wing" if armed else "screen"
            if self.profile.formation_doctrine == "screen" and role == "torpedo_wing" and heavy_ids:
                role = "screen"
            nearest = min(enemies, key=lambda ship: (leader.position.distance(ship.position), ship.id)) if enemies else None
            # Share a target locally, not fleet-wide: a distant southern battle
            # line must not abandon the enemy opposite it to chase the flagship
            # selected by our northernmost formation.
            target = focus if focus and nearest and leader.position.distance(focus.position) <= leader.position.distance(nearest.position) + 3 else nearest
            if self.profile.fleet_tactics_version < 3:
                target = focus or nearest
            station = search
            flank = 0
            mode = "search" if target is None else "approach"
            if target:
                wing_range = max(3, self.profile.formation_standoff - 3)
                standoff = wing_range if role == "torpedo_wing" else self.profile.formation_standoff
                stations = {sign: self._station(state, target, sign, standoff) for sign in (-1, 1)}
                flank = min((-1, 1), key=lambda sign: (
                    leader.position.distance(stations[sign]) + flank_use[sign] * 3, sign,
                ))
                flank_use[flank] += 1
                station = stations[flank]
                distance = leader.position.distance(target.position)
                if role == "battle_line":
                    mode = "cross_t" if distance <= standoff + 8 else "approach"
                elif role == "torpedo_wing":
                    mode = "torpedo_run" if distance <= standoff + 10 else "approach"
                else:
                    mode = "cover"
                    vulnerable = [ship for ship in observation.ships if (
                        ship.side == side and ship.position and not ship.sunk
                        and (ship.command_status == "retreating" or (
                            ship.hull is not None and ship.max_hull and ship.hull / ship.max_hull < self.profile.retreat_hull_threshold
                        ))
                    )]
                    protected = min(vulnerable, key=lambda ship: leader.position.distance(ship.position)) if vulnerable else main_leader
                    if protected and protected.position:
                        station = self._toward(state, protected.position, target.position, 2)
                if all(ship.hull / ship.max_hull < self.profile.retreat_hull_threshold for ship in members):
                    mode = "withdraw"
                    station = self._away(state, leader.position, target.position, 4)
                elif members and all(ship.id in blocked_guns for ship in members):
                    # Do not close for a salvo the authoritative engine forbids.
                    # Keep the column mobile until its guns are available again;
                    # this is tactical cover, not an adjudicated detachment.
                    mode = "cover"
                    station = self._away(state, leader.position, target.position, 4)
            straight = {ship.id: [ship.position] + [pos for pos, _ in engine.movement_trajectory(
                ship, str(min(engine.movement_speed_range(state, ship)[1], formation.speed)),
                columns=state.map_columns, rows=state.map_rows,
            )[0]] for ship in members}
            if torpedo_contacts(straight, threats):
                mode = "evade"
            if formation.disruption_turn == state.turn:
                mode = "disrupted"
            partners = [item for item in formations if item.id in heavy_ids and item.id != formation.id and self._leader(state, item)]
            partner = min(partners, key=lambda item: (leader.position.distance(self._leader(state, item).position), item.id)) if partners else None
            if self.profile.fleet_tactics_version < 3:
                partner = main if main and main.id != formation.id else None
            result.append(Mission(
                formation.id, role, mode, target.id if target else None, station,
                partner.id if partner else None, flank,
            ))
        return result

    @staticmethod
    def _toward(state, position, target, steps):
        current = position
        for _ in range(steps):
            choices = []
            for heading in range(1, 7):
                try:
                    choices.append(current.neighbor(heading, columns=state.map_columns, rows=state.map_rows))
                except ValueError:
                    pass
            if not choices:
                break
            current = min(choices, key=lambda cell: (cell.distance(target), cell.label))
        return current

    @staticmethod
    def _away(state, position, target, steps):
        current = position
        for _ in range(steps):
            choices = []
            for heading in range(1, 7):
                try:
                    choices.append(current.neighbor(heading, columns=state.map_columns, rows=state.map_rows))
                except ValueError:
                    pass
            if not choices:
                break
            current = max(choices, key=lambda cell: (cell.distance(target), cell.label))
        return current

    @staticmethod
    def _station(state, target, flank, standoff):
        position = target.position
        for heading, steps in ((target.heading, min(5, max(2, target.current_speed))),
                               (((target.heading - 1 + flank) % 6) + 1, standoff)):
            for _ in range(steps):
                try:
                    position = position.neighbor(heading, columns=state.map_columns, rows=state.map_rows)
                except ValueError:
                    break
        return position

    @staticmethod
    def _paths(engine, state, prepared):
        paths, headings = {}, {}
        for order in prepared.movement:
            ship = state.ships[order.ship_id]
            if not ship.position:
                continue
            trajectory, heading = engine.movement_trajectory(
                ship, order.plan, columns=state.map_columns, rows=state.map_rows,
            )
            paths[ship.id] = [ship.position] + [position for position, _ in trajectory]
            headings[ship.id] = heading
        return paths, headings

    @staticmethod
    def _next_paths(engine, state, paths, headings, prepared):
        """One-pulse lookahead keeps a stopped column out of a moving ally's bow.

        This is a public, own-fleet assumption, not a future order or damage
        prediction. It avoids deliberately parking where a compulsory first
        advance would trap another formation on the next turn.
        """
        orders = {item.ship_id: item for item in prepared.movement}
        future = {}
        for ship_id, path in paths.items():
            order = orders[ship_id]
            speed = order.speed if order.speed is not None else engine.movement_cost(
                order.plan, engine.movement_commands(order),
            )
            ship = state.ships[ship_id].model_copy(update={"current_speed": speed, "previous_speed": speed})
            minimum, maximum = engine._legal_speed_range(ship, state.turn + 1)
            end = path[-1]
            future[ship_id] = [end]
            if maximum > 0 and (minimum > 0 or speed > 0):
                try:
                    front = end.neighbor(headings[ship_id], columns=state.map_columns, rows=state.map_rows)
                    if not engine._terrain_impassable(state, front):
                        future[ship_id].append(front)
                except ValueError:
                    pass
        return future

    def _route(self, engine, state, baseline, order, mission, enemies):
        formation = state.formations[order.formation_id]
        # Expand only this formation's followers. Other formations' immutable
        # candidate paths are composed later for joint reservation and validation.
        # Keep exactly the authoritative member inventory and speed decision.
        # Removing a newly detached old leader changes rebuilt wake geometry,
        # even though that ship will no longer follow it. A candidate must be
        # equivalent to expanding this same order in the complete fleet.
        projection = state.model_copy(update={
            "formations": {formation.id: formation},
            "ships": {item: state.ships[item] for item in formation.ship_ids},
        })
        partial = OrderBatch(side=baseline.side, phase=baseline.phase, formation_movement=[order])
        prepared, errors, _ = expand_movement_orders(
            engine, projection, partial, _withdrawal_orders=self._baseline_movement,
        )
        if errors:
            self._route_errors = errors
            return None
        # Autonomous withdrawals are immutable within this search. Reuse their
        # authoritative baseline orders rather than re-running an expensive
        # withdrawal path search for every candidate of every formation.
        own_ids = set(formation.ship_ids)
        generated_ids = {item.ship_id for item in prepared.movement}
        prepared.movement += [item for item in self._prepared_baseline.movement if (
            item.ship_id in own_ids and item.ship_id not in generated_ids
        )]
        paths, headings = self._paths(engine, state, prepared)
        paths = {key: value for key, value in paths.items() if key in own_ids}
        next_paths = self._next_paths(engine, state, paths, headings, prepared)
        leader = self._leader(state, formation, order)
        if not leader or leader.id not in paths:
            return Route(order, paths, headings, next_paths, 0.0)
        # Validate using all the baseline orders for total ship coverage; this
        # catches terrain, forced turns, wrecks and speed limits for every follower.
        full = self._prepared_baseline.model_copy()
        full.movement = [item for item in full.movement if item.ship_id not in own_ids] + prepared.movement
        validation = engine.validate_orders(state.game_id, full, _prepared=True)
        if not validation.valid:
            self._route_errors = validation.errors
            return None
        end, heading = paths[leader.id][-1], headings[leader.id]
        progress = (leader.position.distance(mission.station) - end.distance(mission.station)) if mission.station else 0
        score = self.profile.w_coordination * progress / 3
        target = enemies.get(mission.target_id)
        if target and target.position:
            crossing = crossing_t_value(end, heading, target, self.profile.formation_standoff)
            score += self.profile.w_cross_t * crossing
            if mission.state == "withdraw":
                score += end.distance(target.position) - leader.position.distance(target.position)
            # Use actual engine GF/arc pressure at the candidate stations. Enemy
            # destinations are public straight-line hypotheses, never sealed orders.
            pressure = sum(self._pressure(engine, state,
                state.ships[ship_id], position=path[-1], heading=headings[ship_id],
                target_hexes=[target.position],
            ) for ship_id, path in paths.items() if state.ships[ship_id].command_status == "attached")
            score += self.profile.w_fire_pressure * math.log1p(pressure) / max(1, len(paths))
            enemy_pressure = sum(self._pressure(engine, state,
                enemy, target_hexes=[path[-1] for path in paths.values()],
            ) for enemy in enemies.values())
            score -= self.profile.w_enemy_heat * math.log1p(enemy_pressure) / max(2, len(paths) * 2)
            # Avoid bow-on ramming against the public enemy's possible track.
            score -= sum(3.0 for path in paths.values() if target.position in path[1:])
            if self.profile.fleet_tactics_version >= 4:
                # Rank the whole column's firing opportunities against a local
                # enemy set, rather than only the flagship's chosen target.
                # Public straight-line hypotheses do not read sealed orders.
                local = sorted(enemies.values(), key=lambda enemy: (end.distance(enemy.position), enemy.id))[:5]
                outgoing, incoming = [], []
                speed_of = {item.ship_id: item.speed for item in prepared.movement}
                for ship_id, path in paths.items():
                    ship = state.ships[ship_id]
                    if ship.command_status != "attached":
                        continue
                    options, threats = [], []
                    for enemy in local:
                        projected = self._projected_enemies[enemy.id]
                        positions = [enemy.position, projected.position]
                        options.append(sum(self._pressure(engine, state,
                            ship, position=path[-1], heading=headings[ship_id],
                            target_hexes=[position], target_speed=enemy.current_speed,
                        ) for position in positions) / len(positions))
                        threats.append(sum(self._pressure(engine, state,
                            hypothesis, target_hexes=[path[-1]], target_speed=speed_of.get(ship_id) or 0,
                        ) for hypothesis in (enemy, projected)) / 2)
                    outgoing.append(math.log1p(max(options, default=0)))
                    incoming.append(math.log1p(sum(threats)))
                if outgoing:
                    # Tactical weights, not rule modifiers. The engine computes
                    # GF, firing arcs, distance and target-speed expectations.
                    score += self.profile.w_fire_pressure * sum(outgoing) / len(outgoing)
                    score -= self.profile.w_enemy_heat * sum(incoming) / len(incoming)
                cost = engine.movement_cost(order.leader_plan, engine.movement_commands(MovementOrder(ship_id=leader.id, plan=order.leader_plan)))
                # Keep way on under fire; stopping merely to improve T geometry
                # can expose every follower to very accurate enemy salvos.
                score += .3 * min(cost, 4)
        score += 0.05 * (len(paths[leader.id]) - 1)
        if state.options.ruleset_version == "night-v2":
            # Weather is shared public environment; do not read any enemy plans.
            score -= 4 * sum(engine._weather_blocked(state, path[-1]) for path in paths.values())
        return Route(order, paths, headings, next_paths, score)

    @staticmethod
    def _project_enemy(state, enemy):
        position = enemy.position
        for _ in range(max(0, enemy.current_speed)):
            try:
                step = position.neighbor(enemy.heading, columns=state.map_columns, rows=state.map_rows)
            except ValueError:
                break
            if step.label in state.land_hexes:
                break
            position = step
        return enemy.model_copy(update={"position": position})

    def _pressure(self, engine, state, ship, position=None, heading=None, target_hexes=None, target_speed=4):
        if ship.id in getattr(self, "_blocked_own_guns", set()):
            return 0.0
        position = position if position is not None else ship.position
        heading = heading if heading is not None else ship.heading
        key = (ship.id, position, heading, tuple(target_hexes), target_speed)
        if key not in self._pressure_cache:
            self._pressure_cache[key] = engine.ship_gun_pressure(
                state, ship, position=position, heading=heading, target_hexes=target_hexes, target_speed=target_speed,
            )
        return self._pressure_cache[key]

    def _candidates(self, engine, state, baseline, order, mission, enemies):
        formation = state.formations[order.formation_id]
        leader = self._leader(state, formation, order)
        if leader is None or mission.state == "disrupted":
            route = self._route(engine, state, baseline, order, mission, enemies)
            return [route] if route else []
        members = self._members(state, formation, order)
        minimum = max(engine.movement_speed_range(state, ship)[0] for ship in members)
        maximum = min(engine.movement_speed_range(state, ship)[1] for ship in members)
        plans = {order.leader_plan}
        for speed in range(minimum, maximum + 1):
            plans.add(str(speed))
            for bend in range(1, speed + 1):
                for turn in ("P", "S"):
                    plans.add(f"{bend}{turn}" + (str(speed - bend) if speed > bend else ""))
                    for second in range(bend + 1, speed + 1):
                        for second_turn in ("P", "S"):
                            plans.add(f"{bend}{turn}{second-bend}{second_turn}" + (str(speed-second) if speed > second else ""))
        ranked = []
        for plan in sorted(plans):
            trajectory, heading = engine.movement_trajectory(
                leader, plan, columns=state.map_columns, rows=state.map_rows,
            )
            end = trajectory[-1][0] if trajectory else leader.position
            score = -end.distance(mission.station) if mission.station else 0.0
            path = [leader.position] + [pos for pos, _ in trajectory]
            score -= self.profile.w_torpedo_avoid * 3 * torpedo_contacts({leader.id: path}, self._threats)
            target = enemies.get(mission.target_id)
            if target:
                score += self.profile.w_cross_t * crossing_t_value(end, heading, target, self.profile.formation_standoff)
                if self.profile.fleet_tactics_version >= 4:
                    projected = self._projected_enemies[target.id]
                    score += self.profile.w_fire_pressure * math.log1p(self._pressure(engine, state,
                        leader, position=end, heading=heading,
                        target_hexes=[target.position, projected.position], target_speed=target.current_speed,
                    ))
            ranked.append((score, plan))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        # Keep straight/slowing alternatives even if the tactical station score
        # is poor: these are necessary for yielding at friendly intersections.
        selected = {plan for _score, plan in ranked[:self.CANDIDATE_LIMIT]}
        selected.update(str(speed) for speed in range(minimum, maximum + 1))
        selected.add(order.leader_plan)
        result = []
        for plan in sorted(selected):
            candidate = order.model_copy(deep=True)
            candidate.leader_plan = plan
            if candidate.speed_decision and candidate.speed_decision.action == "reduce":
                candidate.speed_decision = None
            route = self._route(engine, state, baseline, candidate, mission, enemies)
            if route:
                result.append(route)
        return result

    def optimize(self, engine, state, side, baseline):
        observation = engine.observe(state.game_id, side)
        self._blocked_own_guns = {item["ship_id"] for item in engine.gunnery_target_options(state, side)
                                  if item["blocked_reason"]}
        enemies = {ship.id: ship for ship in observation.ships if ship.side != side and ship.position and not ship.sunk}
        self._pressure_cache = {}
        self._projected_enemies = {enemy.id: self._project_enemy(state, enemy) for enemy in enemies.values()}
        threats = visible_torpedo_forecast(engine, state, observation)
        self._threats = threats
        self._prepared_baseline, errors, _ = expand_movement_orders(engine, state, baseline)
        self._baseline_movement = {item.ship_id: item for item in self._prepared_baseline.movement}
        if errors:
            raise ValueError(errors)
        missions = self.missions(engine, state, side, observation, baseline)
        order_by_id = {order.formation_id: order for order in baseline.formation_movement}
        choices = {mission.formation_id: self._candidates(
            engine, state, baseline, order_by_id[mission.formation_id], mission, enemies,
        ) for mission in missions}
        fixed, _headings = self._paths(engine, state, self._prepared_baseline)
        moving_ids = {item for mission in missions for item in state.formations[mission.formation_id].ship_ids}
        fixed = {key: value for key, value in fixed.items() if key not in moving_ids}
        next_fixed = self._next_paths(engine, state, fixed, _headings, self._prepared_baseline)
        selected = {}
        for mission in missions:
            routes = choices[mission.formation_id]
            baseline_route = next((route for route in routes if route.order == order_by_id[mission.formation_id]), None)
            if baseline_route is None:
                baseline_route = self._route(engine, state, baseline, order_by_id[mission.formation_id], mission, enemies)
            if baseline_route is None and routes:
                # A scenario can reject the initial proposal while another
                # expanded route is legal. Validate the joint assignment below.
                baseline_route = max(routes, key=lambda route: route.score)
            if baseline_route is None:
                raise ValueError(f"No engine-valid formation route for {mission.formation_id}: {getattr(self, '_route_errors', [])}")
            selected[mission.formation_id] = baseline_route

        def objective(assignment):
            paths = dict(fixed)
            next_paths = dict(next_fixed)
            for route in assignment.values():
                paths.update(route.paths)
                next_paths.update(route.next_paths)
            return (len(friendly_conflicts(paths)), torpedo_contacts(paths, threats),
                    len(friendly_conflicts(next_paths)),
                    -sum(route.score for route in assignment.values()))

        # Whole-fleet coordinate descent: collision avoidance outranks visible
        # torpedoes, which outrank positional tactics. A second sweep lets the
        # battle line exploit the safe lane just opened by its light screen.
        priority = sorted(missions, key=lambda mission: (mission.state != "evade", mission.role != "battle_line", mission.formation_id))
        for _ in range(2):
            for mission in priority:
                fid = mission.formation_id
                best = objective(selected)
                for candidate in choices[fid]:
                    proposal = {**selected, fid: candidate}
                    value = objective(proposal)
                    if value < best:
                        selected = proposal
                        best = value
        # If changing one column cannot resolve a crossing, search the two
        # affected columns jointly (bounded, deterministic, no emergency orders).
        paths = dict(fixed)
        for route in selected.values():
            paths.update(route.paths)
        for left, right, _pulse in friendly_conflicts(paths):
            lf, rf = state.ships[left].formation_id, state.ships[right].formation_id
            if lf == rf or lf not in selected or rf not in selected:
                continue
            # Retain slow/yielding choices in joint repair; tactical-only top-K
            # can exclude the very routes needed to untangle two columns.
            lchoices = sorted(choices[lf], key=lambda route: objective({**selected, lf: route}))[:20]
            rchoices = sorted(choices[rf], key=lambda route: objective({**selected, rf: route}))[:20]
            best = objective(selected)
            for lroute in lchoices:
                for rroute in rchoices:
                    proposal = {**selected, lf: lroute, rf: rroute}
                    value = objective(proposal)
                    if value < best:
                        selected = proposal
                        best = value
        batch = baseline.model_copy(deep=True)
        batch.formation_movement = [selected[order.formation_id].order for order in baseline.formation_movement]
        validation = engine.validate_orders(state.game_id, batch)
        if not validation.valid:
            raise ValueError(validation.errors)
        conflicts, contacts, next_conflicts, _score = objective(selected)
        final_paths = dict(fixed)
        for route in selected.values():
            final_paths.update(route.paths)
        intents, rows = {}, []
        for mission in missions:
            route = selected[mission.formation_id]
            leader = self._leader(state, state.formations[mission.formation_id], route.order)
            target = enemies.get(mission.target_id)
            mode = mission.state
            intents[mission.formation_id] = f"{ROLE_LABELS[mission.role]} · {STATE_LABELS[mode]}" + (
                f" · 协同 {mission.partner_id}" if mission.partner_id else ""
            ) + (f" · 目标 {target.name}" if target else "")
            rows.append({
                "formation_id": mission.formation_id, "role": mission.role, "state": mode,
                "target_id": mission.target_id, "partner_id": mission.partner_id,
                "station": mission.station.label if mission.station else None, "flank": mission.flank,
                "leader_plan": route.order.leader_plan,
                "end_hex": route.paths[leader.id][-1].label if leader and leader.id in route.paths else None,
                "legal_candidates": len(choices[mission.formation_id]),
                "crossing_t_before": crossing_t_value(leader.position, leader.heading, target, self.profile.formation_standoff) if leader and target else 0.0,
                "crossing_t_after": crossing_t_value(route.paths[leader.id][-1], route.headings[leader.id], target, self.profile.formation_standoff) if leader and target and leader.id in route.paths else 0.0,
            })
        audit = {
            "planner": "cooperative-formation-v2", "doctrine": self.profile.formation_doctrine,
            "formations": rows, "visible_torpedo_tracks": [track.track_id for track in threats],
            "predicted_friendly_conflicts": conflicts, "predicted_torpedo_contacts": contacts,
            "next_pulse_conflicts": next_conflicts,
            "remaining_conflicts": [
                {"ships": [left, right], "pulse": pulse}
                for left, right, pulse in friendly_conflicts(final_paths)
            ],
            "constraint_notice": "强制移动或狭窄航道可能使风险无法完全消除" if conflicts or contacts else None,
        }
        return batch, intents, audit
