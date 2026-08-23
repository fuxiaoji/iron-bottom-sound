from __future__ import annotations

import csv
import random
import re
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

import yaml

from .data import ROOT, build_initial_state, scenario_catalog
from .models import (
    DiceRoll,
    GameEvent,
    GameOptions,
    GameState,
    GunneryOrder,
    HexCoord,
    LegalAction,
    MovementOrder,
    OrderBatch,
    Phase,
    PlayerObservation,
    PublicShip,
    RuleReference,
    ShipState,
    Side,
    ValidationResult,
)


RULES = ROOT / "resources" / "derived" / "structured" / "rules"
D66_VALUES = [tens * 10 + ones for tens in range(1, 7) for ones in range(1, 7)]
PHASES = [
    Phase.REINFORCEMENT,
    Phase.MOVEMENT_PLANNING,
    Phase.TORPEDO_PLANNING,
    Phase.MOVEMENT_RESOLUTION,
    Phase.GUNNERY,
    Phase.TORPEDO_EFFECTS,
    Phase.FIRE_END,
]


def d66_adjust(value: int, modifier: int) -> int:
    """Apply the rulebook's base-six step modifier to a D66 result."""
    if value not in D66_VALUES:
        raise ValueError(f"{value} is not a D66 result")
    index = min(max(D66_VALUES.index(value) + modifier, 0), len(D66_VALUES) - 1)
    return D66_VALUES[index]


def parse_effect(effect: str) -> tuple[int, int, bool, bool]:
    if effect == "Miss":
        return 0, 0, False, False
    if effect == "Sunk":
        return 999, 0, True, False
    hull_match = re.search(r"(\d+)H", effect)
    speed_match = re.search(r"/(?:-)?(\d+)MF", effect)
    return (
        int(hull_match.group(1)) if hull_match else 0,
        int(speed_match.group(1)) if speed_match else 0,
        False,
        "*" in effect,
    )


class RuleData:
    def __init__(self) -> None:
        with (RULES / "gunnery-hit-table.csv").open("r", encoding="utf-8", newline="") as stream:
            self.gunnery_hits = list(csv.DictReader(stream))
        self.gunnery_results = self._yaml("gunnery-results.yaml")["results"]
        self.torpedo_collision = self._yaml("torpedo-collision-table.yaml")
        self.torpedoes = self._yaml("torpedoes.yaml")["types"]

    @staticmethod
    def _yaml(name: str) -> dict[str, Any]:
        with (RULES / name).open("r", encoding="utf-8") as stream:
            return yaml.safe_load(stream)

    def hit_count(self, firepower: int, adjusted_roll: int) -> int:
        row = next(
            entry
            for entry in self.gunnery_hits
            if int(entry["firepower_min"]) <= firepower <= int(entry["firepower_max"])
        )
        column = str(adjusted_roll) if adjusted_roll <= 31 else "32_plus"
        return int(row[column])

    def torpedo_effect(self, roll: int, displacement: str) -> str:
        if roll <= 2:
            key = "2-"
        elif roll >= 12:
            key = "12+"
        else:
            key = str(roll)
        column = self.torpedo_collision["columns"].index(displacement)
        return self.torpedo_collision["rows"][key][column]


class IronBottomEngine:
    def __init__(self) -> None:
        self.games: dict[str, GameState] = {}
        self.initial_states: dict[str, GameState] = {}
        self.rules = RuleData()

    def scenarios(self) -> list[dict[str, Any]]:
        return scenario_catalog()

    def reset(
        self,
        scenario_id: str,
        seed: int = 1,
        options: GameOptions | None = None,
        game_id: str | None = None,
    ) -> GameState:
        identifier = game_id or str(uuid.uuid4())
        state = build_initial_state(identifier, scenario_id, seed, options or GameOptions())
        self._event(
            state,
            "game_created",
            f"加载想定 {state.scenario_title}",
            rule=self._rule("IBS-R-05", 6, "5.0"),
        )
        self.games[identifier] = state
        self.initial_states[identifier] = state.model_copy(deep=True)
        return state

    def get(self, game_id: str) -> GameState:
        try:
            return self.games[game_id]
        except KeyError as error:
            raise KeyError(f"Unknown game {game_id}") from error

    def observe(self, game_id: str, side: Side) -> PlayerObservation:
        state = self.get(game_id)
        ships: list[PublicShip] = []
        own_positions = [ship.position for ship in state.ships.values() if ship.side == side and not ship.sunk and ship.position]
        for ship in state.ships.values():
            visible = ship.side == side or self._visible_to(state, ship, side, own_positions)
            if not visible:
                continue
            hide_damage = state.options.optional_rules.hidden_damage and ship.side != side
            ships.append(
                PublicShip(
                    id=ship.id,
                    name=ship.name,
                    side=ship.side,
                    ship_type=ship.ship_type,
                    position=ship.position,
                    heading=ship.heading,
                    current_speed=ship.current_speed,
                    hull=None if hide_damage else ship.hull,
                    max_hull=None if hide_damage else ship.max_hull,
                    fire_markers=ship.fire_markers,
                    fired=ship.fired,
                    sunk=ship.sunk,
                    asset=ship.asset,
                )
            )
        safe_events = [event for event in state.events[-40:] if event.payload.get("secret_side") in (None, side.value)]
        return PlayerObservation(
            game_id=game_id,
            scenario_id=state.scenario_id,
            scenario_title=state.scenario_title,
            side=side,
            turn=state.turn,
            max_turns=state.max_turns,
            phase=state.phase,
            ships=ships,
            score=deepcopy(state.score),
            recent_events=safe_events,
            winner=state.winner,
            victory_reason=state.victory_reason,
        )

    def legal_actions(self, game_id: str, side: Side) -> list[LegalAction]:
        state = self.get(game_id)
        if state.phase == Phase.COMPLETE:
            return []
        if state.phase == Phase.MOVEMENT_PLANNING and side.value not in state.submitted_orders:
            return [
                LegalAction(
                    kind="submit_orders",
                    ship_id=ship.id,
                    schema_hint={"movement": "0 or digits plus P/S turns", "gunnery_target": "visible enemy id"},
                )
                for ship in state.ships.values()
                if ship.side == side and not ship.sunk and ship.position
            ]
        return [LegalAction(kind="advance")] if len(state.submitted_orders) == 2 else []

    def validate_orders(self, game_id: str, batch: OrderBatch) -> ValidationResult:
        state = self.get(game_id)
        errors: list[str] = []
        if state.phase != Phase.MOVEMENT_PLANNING:
            errors.append(f"Orders may only be submitted during {Phase.MOVEMENT_PLANNING}")
        if batch.side.value in state.submitted_orders:
            errors.append("This side already submitted orders")
        owned = {ship.id: ship for ship in state.ships.values() if ship.side == batch.side and not ship.sunk}
        for order in batch.movement:
            ship = owned.get(order.ship_id)
            if not ship:
                errors.append(f"Movement references non-owned ship {order.ship_id}")
                continue
            try:
                cost = self.movement_cost(order.plan)
            except ValueError as error:
                errors.append(f"{order.ship_id}: {error}")
                continue
            maximum = min(ship.max_speed_for_turn(state.turn), ship.previous_speed + 2)
            deceleration = 3 if ship.ship_type in {"BB", "BC"} else 5
            minimum = max(0, ship.previous_speed - deceleration)
            if not minimum <= cost <= maximum:
                errors.append(f"{order.ship_id}: movement cost {cost} outside legal range {minimum}-{maximum}")
        for order in batch.gunnery:
            if order.ship_id not in owned:
                errors.append(f"Gunnery references non-owned ship {order.ship_id}")
            for target in (order.primary_target, order.secondary_target, order.searchlight_target):
                if target and (target not in state.ships or state.ships[target].side == batch.side):
                    errors.append(f"Illegal target {target}")
        for order in batch.torpedoes:
            ship = owned.get(order.ship_id)
            if not ship or not ship.torpedo or ship.torpedo.destroyed:
                errors.append(f"{order.ship_id} cannot fire torpedoes")
            elif order.count > (ship.torpedo.ammo or 0):
                errors.append(f"{order.ship_id} lacks torpedo ammunition")
            if order.target_id and (order.target_id not in state.ships or state.ships[order.target_id].side == batch.side):
                errors.append(f"Illegal torpedo target {order.target_id}")
        return ValidationResult(valid=not errors, errors=errors)

    def submit_orders(self, game_id: str, batch: OrderBatch) -> ValidationResult:
        state = self.get(game_id)
        validation = self.validate_orders(game_id, batch)
        if not validation.valid:
            return validation
        state.submitted_orders[batch.side.value] = batch
        self._event(
            state,
            "orders_submitted",
            f"{batch.side.value} 已封存秘密计划",
            payload={"secret_side": batch.side.value},
            rule=self._rule("IBS-R-05", 6, "5.0 B-C"),
        )
        return validation

    def advance(self, game_id: str) -> list[GameEvent]:
        state = self.get(game_id)
        before = len(state.events)
        if state.phase == Phase.COMPLETE:
            return []
        if state.phase == Phase.REINFORCEMENT:
            self._resolve_reinforcements(state)
            state.phase = Phase.MOVEMENT_PLANNING
        elif state.phase == Phase.MOVEMENT_PLANNING:
            if set(state.submitted_orders) != {Side.AXIS.value, Side.ALLIES.value}:
                raise ValueError("Both sides must submit orders before advancing")
            state.phase = Phase.TORPEDO_PLANNING
        elif state.phase == Phase.TORPEDO_PLANNING:
            state.phase = Phase.MOVEMENT_RESOLUTION
        elif state.phase == Phase.MOVEMENT_RESOLUTION:
            self._resolve_movement(state)
            state.phase = Phase.GUNNERY
        elif state.phase == Phase.GUNNERY:
            self._resolve_gunnery(state)
            state.phase = Phase.TORPEDO_EFFECTS
        elif state.phase == Phase.TORPEDO_EFFECTS:
            self._resolve_torpedoes(state)
            state.phase = Phase.FIRE_END
        elif state.phase == Phase.FIRE_END:
            self._resolve_fire(state)
            self._check_victory(state)
            if state.phase != Phase.COMPLETE:
                state.turn += 1
                state.phase = Phase.REINFORCEMENT
                state.submitted_orders.clear()
                for ship in state.ships.values():
                    ship.fired = False
                    ship.smoke = False
        self._event(state, "phase_changed", f"阶段：{state.phase.value}", rule=self._rule("IBS-R-05", 6, "5.0"))
        return state.events[before:]

    def step(self, game_id: str, joint_orders: dict[Side, OrderBatch]) -> tuple[dict[Side, PlayerObservation], list[GameEvent]]:
        state = self.get(game_id)
        if state.phase == Phase.REINFORCEMENT:
            self.advance(game_id)
        for side in (Side.AXIS, Side.ALLIES):
            result = self.submit_orders(game_id, joint_orders[side])
            if not result.valid:
                raise ValueError(result.errors)
        events: list[GameEvent] = []
        while self.get(game_id).phase not in {Phase.REINFORCEMENT, Phase.COMPLETE}:
            events.extend(self.advance(game_id))
        return {side: self.observe(game_id, side) for side in Side}, events

    def replay(self, game_id: str) -> GameState:
        """Return a detached projection; stored events and snapshots are canonical persistence inputs."""
        return self.get(game_id).model_copy(deep=True)

    @staticmethod
    def movement_cost(plan: str) -> int:
        plan = plan.strip().upper().replace("左", "P").replace("右", "S")
        if plan == "0":
            return 0
        tokens = re.findall(r"\d+|PP|SS|LL|RR|P|S|L|R", plan)
        if "".join(tokens) != plan:
            raise ValueError(f"Invalid movement plan {plan!r}")
        return sum(int(token) if token.isdigit() else (1 if token in {"PP", "SS", "LL", "RR"} else 0) for token in tokens)

    def movement_trajectory(self, ship: ShipState, plan: str) -> tuple[list[tuple[HexCoord, int]], int]:
        if not ship.position:
            return [], ship.heading
        normalized = plan.strip().upper().replace("左", "P").replace("右", "S")
        if normalized == "0":
            return [], ship.heading
        tokens = re.findall(r"\d+|PP|SS|LL|RR|P|S|L|R", normalized)
        heading = ship.heading
        position = ship.position
        trajectory: list[tuple[HexCoord, int]] = []
        for token in tokens:
            if token.isdigit():
                for _ in range(int(token)):
                    position = position.neighbor(heading)
                    trajectory.append((position, heading))
            elif token in {"P", "L"}:
                heading = 6 if heading == 1 else heading - 1
            elif token in {"S", "R"}:
                heading = 1 if heading == 6 else heading + 1
            elif token in {"PP", "LL"}:
                heading = ((heading - 3) % 6) + 1
                trajectory.append((position, heading))
            elif token in {"SS", "RR"}:
                heading = ((heading + 1) % 6) + 1
                trajectory.append((position, heading))
        return trajectory, heading

    def _resolve_reinforcements(self, state: GameState) -> None:
        for ship in state.ships.values():
            if ship.position is None and ship.reinforcement_turn == state.turn:
                self._event(state, "reinforcement_pending", f"{ship.name} 等待想定入场格", rule=self._rule("IBS-R-05", 6, "5.0 A"))

    def _resolve_movement(self, state: GameState) -> None:
        movement_orders = {
            order.ship_id: order
            for batch in state.submitted_orders.values()
            for order in batch.movement
        }
        paths: dict[str, list[tuple[HexCoord, int]]] = {}
        final_headings: dict[str, int] = {}
        for ship in state.ships.values():
            if ship.sunk or not ship.position:
                continue
            plan = movement_orders.get(ship.id, MovementOrder(ship_id=ship.id, plan="0")).plan
            trajectory, heading = self.movement_trajectory(ship, plan)
            paths[ship.id] = trajectory
            final_headings[ship.id] = heading
            ship.current_speed = self.movement_cost(plan)
        maximum_impulses = max((len(path) for path in paths.values()), default=0)
        stopped: set[str] = set()
        for impulse in range(maximum_impulses):
            destinations: dict[str, HexCoord] = {}
            for ship_id, path in paths.items():
                ship = state.ships[ship_id]
                if ship_id in stopped or impulse >= len(path):
                    destinations[ship_id] = ship.position  # type: ignore[assignment]
                else:
                    destinations[ship_id] = path[impulse][0]
            by_hex: dict[str, list[str]] = {}
            for ship_id, position in destinations.items():
                by_hex.setdefault(position.label, []).append(ship_id)
            collisions = [ids for ids in by_hex.values() if len(ids) > 1]
            for ids in collisions:
                for ship_id in ids:
                    stopped.add(ship_id)
                    self._damage_hull(state, state.ships[ship_id], 1, "collision")
                self._event(
                    state,
                    "collision",
                    "发生碰撞：" + "、".join(state.ships[item].name for item in ids),
                    payload={"ships": ids},
                    rule=self._rule("IBS-R-06.4", 8, "6.4"),
                )
            for ship_id, position in destinations.items():
                if ship_id not in stopped:
                    state.ships[ship_id].position = position
        for ship_id, heading in final_headings.items():
            ship = state.ships[ship_id]
            ship.heading = heading
            ship.previous_speed = ship.current_speed
            self._event(
                state,
                "ship_moved",
                f"{ship.name} 移动至 {ship.position.label if ship.position else '场外'}",
                payload={"ship_id": ship.id, "position": ship.position.label if ship.position else None, "heading": ship.heading},
                rule=self._rule("IBS-R-06", 7, "6.0"),
            )

    def _resolve_gunnery(self, state: GameState) -> None:
        orders = [order for batch in state.submitted_orders.values() for order in batch.gunnery]
        attackers_per_target: dict[str, int] = {}
        for order in orders:
            if order.primary_target:
                attackers_per_target[order.primary_target] = attackers_per_target.get(order.primary_target, 0) + 1
        for order in orders:
            attacker = state.ships[order.ship_id]
            if attacker.sunk or not attacker.position or not order.primary_target:
                continue
            target = state.ships[order.primary_target]
            if target.sunk or not target.position or target.side == attacker.side:
                continue
            distance = attacker.position.distance(target.position)
            if not self._can_see(state, attacker, target):
                self._event(state, "gunnery_rejected", f"{attacker.name} 无法看见 {target.name}", rule=self._rule("IBS-R-08.1", 9, "8.1"))
                continue
            modifier = self._gunnery_modifier(state, attacker, target, distance, attackers_per_target.get(target.id, 1))
            raw, dice = self._roll_d66(state)
            adjusted = d66_adjust(raw, modifier)
            hits = self.rules.hit_count(attacker.primary.firepower, adjusted)
            attacker.fired = True
            self._event(
                state,
                "gunnery_attack",
                f"{attacker.name} 炮击 {target.name}：{hits} 发命中",
                payload={"attacker": attacker.id, "target": target.id, "distance": distance, "modifier": modifier, "hits": hits},
                rule=self._rule("IBS-T-GHT", 2, "炮击命中表"),
                dice=DiceRoll(dice=dice, notation="D66", raw=raw, adjusted=adjusted),
            )
            if state.options.optional_rules.malfunction_66 and raw == 66:
                self._resolve_malfunction(state, attacker)
            for _ in range(hits):
                result_roll, result_dice = self._roll_d66(state)
                result = self.rules.gunnery_results[result_roll]
                self._apply_gunnery_result(state, attacker, target, result_roll, result)
                self._event(
                    state,
                    "gunnery_result",
                    f"{target.name} 命中结果 {result_roll}",
                    payload={"target": target.id, "result": result},
                    rule=self._rule("IBS-T-GHRT", 1, "炮击结果表"),
                    dice=DiceRoll(dice=result_dice, notation="D66", raw=result_roll),
                )

    def _resolve_torpedoes(self, state: GameState) -> None:
        orders = [order for batch in state.submitted_orders.values() for order in batch.torpedoes]
        displacement = {"DD": "A", "APD": "A", "AV": "B", "CL": "B", "CA": "C", "BC": "F", "BB": "F"}
        for order in orders:
            attacker = state.ships[order.ship_id]
            if not order.target_id or attacker.sunk or not attacker.position or not attacker.torpedo:
                continue
            target = state.ships[order.target_id]
            if target.sunk or not target.position:
                continue
            distance = attacker.position.distance(target.position)
            if distance == 0:
                continue
            definition = self.rules.torpedoes.get(attacker.torpedo_type or "", {})
            max_range = max(definition.get("ranges", [10]))
            if distance > max_range:
                continue
            roll, dice = self._roll_2d6(state)
            adjusted = roll + self._torpedo_modifier(target, distance)
            aspect = self._target_aspect(attacker, target)
            hits = 0
            if aspect == "broadside":
                hits = 2 if adjusted >= 13 else (1 if adjusted >= 11 else 0)
            elif adjusted >= 13:
                hits = 1
            hits = min(hits, order.count, attacker.torpedo.ammo or 0)
            attacker.torpedo.ammo = (attacker.torpedo.ammo or 0) - order.count
            self._event(
                state,
                "torpedo_attack",
                f"{attacker.name} 对 {target.name} 发射鱼雷：{hits} 命中",
                payload={"attacker": attacker.id, "target": target.id, "distance": distance, "hits": hits},
                rule=self._rule("IBS-R-08.2", 12, "8.2"),
                dice=DiceRoll(dice=dice, notation="2D6", raw=roll, adjusted=adjusted),
            )
            for _ in range(hits):
                damage_roll, damage_dice = self._roll_2d6(state)
                damage_roll += int(definition.get("damage_modifier", 0))
                effect = self.rules.torpedo_effect(damage_roll, displacement.get(target.ship_type, "C"))
                hull, speed, sunk, fire = parse_effect(effect)
                self._damage_hull(state, target, target.hull if sunk else hull, "torpedo")
                self._lose_speed(target, speed)
                if fire or damage_roll == 8:
                    target.fire_markers += 1
                self._event(
                    state,
                    "torpedo_result",
                    f"{target.name} 鱼雷效果：{effect}",
                    payload={"target": target.id, "effect": effect},
                    rule=self._rule("IBS-T-THDT", 3, "鱼雷与碰撞结果表"),
                    dice=DiceRoll(dice=damage_dice, notation="2D6", raw=damage_roll),
                )

    def _resolve_fire(self, state: GameState) -> None:
        for ship in state.ships.values():
            for _ in range(ship.fire_markers):
                roll, dice = self._roll_2d6(state)
                if roll in {3, 7, 11}:
                    self._damage_hull(state, ship, 1, "fire")
                if roll in {4, 8, 9}:
                    ship.fire_markers = max(0, ship.fire_markers - 1)
                self._event(
                    state,
                    "fire_check",
                    f"{ship.name} 火灾检定 {roll}",
                    payload={"ship_id": ship.id},
                    rule=self._rule("IBS-R-08.1", 10, "8.1 火灾"),
                    dice=DiceRoll(dice=dice, notation="2D6", raw=roll),
                )

    def _check_victory(self, state: GameState) -> None:
        alive = {
            side: [ship for ship in state.ships.values() if ship.side == side and not ship.sunk]
            for side in Side
        }
        if not alive[Side.AXIS] or not alive[Side.ALLIES]:
            state.winner = Side.ALLIES if not alive[Side.AXIS] else Side.AXIS
            state.victory_reason = "对方已无可战舰只"
        elif state.turn >= state.max_turns:
            if state.score[Side.AXIS.value] != state.score[Side.ALLIES.value]:
                state.winner = max(Side, key=lambda side: state.score[side.value])
                state.victory_reason = "想定结束时胜利点领先"
            else:
                state.victory_reason = "平局"
            state.phase = Phase.COMPLETE
        if state.winner:
            state.phase = Phase.COMPLETE
            self._event(state, "victory", f"{state.winner.value} 获胜：{state.victory_reason}")

    def _gunnery_modifier(self, state: GameState, attacker: ShipState, target: ShipState, distance: int, attackers: int) -> int:
        if distance == 1:
            modifier = -24
        elif distance == 2:
            modifier = -15
        elif distance <= 5:
            modifier = -12
        elif distance <= 9:
            modifier = -6
        elif distance <= 15:
            modifier = 0
        elif distance <= 20:
            modifier = 2
        else:
            modifier = 4
        speed = target.current_speed
        modifier += 0 if speed >= 4 else (-4 if speed >= 2 else (-9 if speed == 1 else -18))
        if attacker.mfc_destroyed:
            modifier += 3
        modifier += max(0, attackers - 1)
        if target.fire_markers:
            modifier -= 2
        if state.options.optional_rules.silhouettes and target.fired:
            modifier -= 3
        if state.options.optional_rules.smoke and target.smoke:
            modifier += 6
        return modifier

    @staticmethod
    def _torpedo_modifier(target: ShipState, distance: int) -> int:
        if distance <= 2:
            modifier = 5
        elif distance <= 4:
            modifier = 3
        elif distance <= 6:
            modifier = 1
        elif distance <= 15:
            modifier = 0
        else:
            modifier = -1
        modifier += 4 if target.current_speed <= 1 else (2 if target.current_speed == 2 else (1 if target.current_speed == 3 else 0))
        return modifier

    @staticmethod
    def _target_aspect(attacker: ShipState, target: ShipState) -> str:
        if not attacker.position or not target.position:
            return "broadside"
        try:
            bow = target.position.neighbor(target.heading)
        except Exception:
            bow = None
        stern_heading = ((target.heading + 2) % 6) + 1
        try:
            stern = target.position.neighbor(stern_heading)
        except Exception:
            stern = None
        return "bow_stern" if attacker.position in {bow, stern} else "broadside"

    def _apply_gunnery_result(self, state: GameState, attacker: ShipState, target: ShipState, roll: int, result: Any) -> None:
        if result == "miss":
            return
        if result == "special":
            self._resolve_special_damage(state, target)
            return
        if result == "variable_hull_by_ship_type":
            amount = 3 if target.ship_type in {"BB", "BC"} else (2 if target.ship_type in {"AV", "CA", "CL"} else 1)
            self._damage_hull(state, target, amount, "gunnery")
            return
        if isinstance(result, list):
            for item in result:
                if item == "radar":
                    target.radar_destroyed = True
                elif item == "fire_control":
                    target.mfc_destroyed = True
                elif item.startswith("primary"):
                    target.primary.destroyed = True
                elif item == "secondary" and target.secondary:
                    target.secondary.destroyed = True
            return
        if isinstance(result, str):
            if result.startswith("primary"):
                target.primary.destroyed = True
            return
        if isinstance(result, dict):
            if result.get("armour_check") and not self._penetrates(attacker, target):
                return
            self._damage_hull(state, target, int(result.get("hull", 0)), "gunnery")
            self._lose_speed(target, int(result.get("speed_loss", 0)))
            if result.get("fire_check"):
                target.fire_markers += 1
            if "secondary" in result and target.secondary:
                target.secondary.destroyed = True
            if any(key.startswith("primary") for key in result):
                target.primary.destroyed = True

    def _resolve_special_damage(self, state: GameState, target: ShipState) -> None:
        roll, dice = self._roll_d66(state)
        if roll in {11, 12, 13, 14, 15, 16, 23, 31, 33, 34, 41}:
            target.fire_markers += 1
        if roll in {21, 22, 23, 33, 41, 44, 45, 46, 51, 52, 53, 54, 55, 56, 61, 63, 64, 65}:
            self._damage_hull(state, target, 1, "special_damage")
        if roll in {21, 23, 53, 55, 56, 61}:
            self._lose_speed(target, 1)
        if roll in {24, 25, 26, 31, 32}:
            target.heading = ((target.heading + (1 if roll % 2 else -1) - 1) % 6) + 1
        if roll in {42, 52, 54, 55, 61, 62, 63, 64, 65}:
            target.primary.destroyed = target.primary.destroyed or roll in {52, 54, 55}
        self._event(
            state,
            "special_damage",
            f"{target.name} 特殊损伤 {roll}",
            payload={"target": target.id, "result": roll},
            rule=self._rule("IBS-T-SPECIAL", 4, "特殊伤害表"),
            dice=DiceRoll(dice=dice, notation="D66", raw=roll),
        )

    def _resolve_malfunction(self, state: GameState, attacker: ShipState) -> None:
        roll, dice = self._roll_2d6(state)
        if roll in {4, 10, 11, 12}:
            attacker.primary.destroyed = True
        if roll in {2, 3}:
            attacker.mfc_destroyed = True
        if roll in {5, 9, 12}:
            attacker.fire_markers += 1
        self._event(
            state,
            "malfunction",
            f"{attacker.name} 发生 66 故障：{roll}",
            rule=self._rule("IBS-R-09.5", 13, "9.5"),
            dice=DiceRoll(dice=dice, notation="2D6", raw=roll),
        )

    @staticmethod
    def _penetrates(attacker: ShipState, target: ShipState) -> bool:
        if target.belt_armor <= 0:
            return True
        return attacker.primary.caliber >= target.belt_armor

    def _damage_hull(self, state: GameState, ship: ShipState, amount: int, cause: str) -> None:
        if amount <= 0 or ship.sunk:
            return
        ship.hull = max(0, ship.hull - amount)
        state.score[ship.side.opponent.value] += min(amount, ship.max_hull)
        if ship.hull == 0:
            ship.sunk = True
            state.score[ship.side.opponent.value] += ship.vp
            self._event(state, "ship_sunk", f"{ship.name} 沉没", payload={"ship_id": ship.id, "cause": cause})

    @staticmethod
    def _lose_speed(ship: ShipState, amount: int) -> None:
        if amount <= 0:
            return
        values = list(ship.speed_track)
        for _ in range(amount):
            maximum = max(values)
            index = max(index for index, value in enumerate(values) if value == maximum)
            values[index] = max(0, values[index] - 1)
        ship.speed_track = tuple(values)  # type: ignore[assignment]
        ship.current_speed = min(ship.current_speed, max(values))

    def _visible_to(self, state: GameState, target: ShipState, side: Side, own_positions: Iterable[HexCoord | None]) -> bool:
        if target.sunk or not target.position:
            return True
        if target.fire_markers:
            return True
        visibility = int(state.visibility[side.value])
        if state.options.optional_rules.radar:
            visibility = max(visibility, 60)
        return any(position and position.distance(target.position) <= visibility for position in own_positions)

    def _can_see(self, state: GameState, attacker: ShipState, target: ShipState) -> bool:
        return self._visible_to(state, target, attacker.side, [attacker.position])

    def _roll_d66(self, state: GameState) -> tuple[int, list[int]]:
        rng = random.Random(state.seed * 1_000_003 + state.rng_counter)
        state.rng_counter += 1
        dice = [rng.randint(1, 6), rng.randint(1, 6)]
        return dice[0] * 10 + dice[1], dice

    def _roll_2d6(self, state: GameState) -> tuple[int, list[int]]:
        rng = random.Random(state.seed * 1_000_003 + state.rng_counter)
        state.rng_counter += 1
        dice = [rng.randint(1, 6), rng.randint(1, 6)]
        return sum(dice), dice

    @staticmethod
    def _rule(rule_id: str, page: int, section: str) -> RuleReference:
        document = "player-aid-tables-zh.pdf" if rule_id.startswith("IBS-T") else "iron-bottom-sound-iv-rules-zh.pdf"
        return RuleReference(rule_id=rule_id, document=document, pdf_page=page, section=section)

    @staticmethod
    def _event(
        state: GameState,
        event_type: str,
        message: str,
        payload: dict[str, Any] | None = None,
        rule: RuleReference | None = None,
        dice: DiceRoll | None = None,
    ) -> GameEvent:
        event = GameEvent(
            sequence=len(state.events) + 1,
            turn=state.turn,
            phase=state.phase,
            type=event_type,
            message=message,
            payload=payload or {},
            rule=rule,
            dice=dice,
        )
        state.events.append(event)
        return event
