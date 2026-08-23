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
    FiringArc,
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
ORDER_PHASES = {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING, Phase.TORPEDO_PLANNING, Phase.GUNNERY}


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
        self.modifiers = self._yaml("modifiers.yaml")
        self.fire_results = self._yaml("fire-table.yaml")["results"]
        self.malfunction_results = self._yaml("malfunction-table.yaml")["results"]
        self.special_damage = self._yaml("special-damage-table.yaml")
        with (RULES / "armour-penetration-table.csv").open("r", encoding="utf-8", newline="") as stream:
            self.armour_penetration = list(csv.DictReader(stream))

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

    @staticmethod
    def _range_value(rows: list[dict[str, Any]], distance: int) -> dict[str, Any]:
        return next(row for row in rows if int(row["min"]) <= distance <= int(row["max"]))

    def range_modifier(self, kind: str, distance: int, japanese: bool = False) -> int:
        row = self._range_value(self.modifiers["range_modifier"][kind], distance)
        return int(row["value"]) + (0 if japanese else int(row.get("non_japanese_additional", 0)))

    def target_speed_modifier(self, kind: str, speed: int) -> int:
        table = self.modifiers["target_speed_modifier"][kind]
        if speed in table:
            return int(table[speed])
        for key, value in table.items():
            if isinstance(key, str) and key.endswith("+") and speed >= int(key[:-1]):
                return int(value)
            if isinstance(key, str) and "-" in key:
                lower, upper = (int(number) for number in key.split("-"))
                if lower <= speed <= upper:
                    return int(value)
        raise KeyError(speed)

    @staticmethod
    def table_2d6(table: dict[Any, Any], roll: int) -> dict[str, Any]:
        if roll in table:
            return table[roll]
        for key, value in table.items():
            if isinstance(key, str) and "-" in key:
                lower, upper = (int(number) for number in key.split("-"))
                if lower <= roll <= upper:
                    return value
        raise KeyError(roll)

    def gunnery_result(self, roll: int) -> Any:
        return self.gunnery_results["66+"] if roll >= 66 else self.gunnery_results[roll]

    def special_damage_result(self, roll: int, displacement_band: str) -> dict[str, Any]:
        direct = self.special_damage["direct_results"]
        key = str(roll)
        if key in direct:
            return deepcopy(direct[key])
        for candidate, result in direct.items():
            if "-" in candidate:
                lower, upper = (int(number) for number in candidate.split("-"))
                if lower <= roll <= upper:
                    return deepcopy(result)
        result = self.special_damage["results"][key]
        return {"effect": result[displacement_band], "additional": result.get("additional"), "armour_check": True}

    def penetration(self, nation: str, caliber: float, distance: int) -> float:
        distance_column = next(
            label
            for label, lower, upper in (
                ("1-2", 1, 2), ("3-5", 3, 5), ("6-7", 6, 7), ("8-10", 8, 10),
                ("11-13", 11, 13), ("14-17", 14, 17), ("18-20", 18, 20), ("21-25", 21, 25),
            )
            if lower <= distance <= upper
        )
        candidates = []
        for row in self.armour_penetration:
            calibers = [float(value) for value in row["caliber_in"].split("|")]
            nations = row["nation"].split("_")
            if caliber in calibers and (nation in nations or row["nation"] == "GENERIC"):
                candidates.append(row)
        if not candidates:
            return 0
        row = next((item for item in candidates if nation in item["nation"].split("_")), candidates[0])
        value = row[distance_column]
        return 0 if value == "-" else float(value)


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
        if state.phase in ORDER_PHASES and side.value not in state.submitted_orders:
            schemas: dict[Phase, dict[str, Any]] = {
                Phase.REINFORCEMENT: {"reinforcements": "entry_hex, heading, speed", "confirmation": {"ready": True}},
                Phase.MOVEMENT_PLANNING: {
                    "movement": {"ship_id": "owned ship", "speed": "legal MF", "commands": "advance/turn_*"},
                    "confirmation": {"ready": True},
                },
                Phase.TORPEDO_PLANNING: {
                    "torpedoes": "launcher, launch_at_mf, launch_hex, bearing, setting_index",
                    "confirmation": {"ready": True},
                },
                Phase.GUNNERY: {
                    "gunnery": "per-mount target orders",
                    "illumination": "star-shell target hex",
                    "searchlights": "target and active flag",
                    "smoke": "deploy flag",
                    "confirmation": {"ready": True},
                },
            }
            return [LegalAction(kind="submit_phase_orders", schema_hint=schemas[state.phase])]
        return [LegalAction(kind="advance")] if state.phase not in ORDER_PHASES or len(state.submitted_orders) == 2 else []

    def validate_orders(self, game_id: str, batch: OrderBatch) -> ValidationResult:
        state = self.get(game_id)
        errors: list[str] = []
        if state.phase not in ORDER_PHASES:
            errors.append(f"Orders may not be submitted during {state.phase}")
        if batch.phase is not None and batch.phase != state.phase:
            errors.append(f"Order phase {batch.phase} does not match current phase {state.phase}")
        if batch.side.value in state.submitted_orders:
            errors.append("This side already submitted orders")
        owned = {ship.id: ship for ship in state.ships.values() if ship.side == batch.side and not ship.sunk}
        allowed_fields = {
            Phase.REINFORCEMENT: {"reinforcements"},
            Phase.MOVEMENT_PLANNING: {"movement"},
            Phase.TORPEDO_PLANNING: {"torpedoes"},
            Phase.GUNNERY: {"gunnery", "smoke", "smoke_ships", "illumination", "searchlights"},
        }.get(state.phase, set())
        populated = {
            name for name in ("reinforcements", "movement", "torpedoes", "gunnery", "smoke", "smoke_ships", "illumination", "searchlights")
            if getattr(batch, name)
        }
        for name in sorted(populated - allowed_fields):
            errors.append(f"{name} orders are not legal during {state.phase}")
        for order in batch.movement if state.phase == Phase.MOVEMENT_PLANNING else []:
            ship = owned.get(order.ship_id)
            if not ship:
                errors.append(f"Movement references non-owned ship {order.ship_id}")
                continue
            try:
                commands = self.movement_commands(order)
                self.validate_movement_commands(commands)
                cost = self.movement_cost(order.plan, commands)
                self.movement_trajectory(ship, order.plan, commands)
            except ValueError as error:
                errors.append(f"{order.ship_id}: {error}")
                continue
            maximum = min(ship.max_speed_for_turn(state.turn), ship.previous_speed + 2)
            deceleration = 3 if ship.ship_type in {"BB", "BC"} else 5
            minimum = max(0, ship.previous_speed - deceleration)
            if not minimum <= cost <= maximum:
                errors.append(f"{order.ship_id}: movement cost {cost} outside legal range {minimum}-{maximum}")
            if order.speed is not None and order.speed != cost:
                errors.append(f"{order.ship_id}: declared speed {order.speed} does not match {cost} MF plan")
        if state.phase == Phase.MOVEMENT_PLANNING:
            expected = {ship.id for ship in owned.values() if ship.position}
            submitted = {order.ship_id for order in batch.movement}
            if submitted != expected:
                errors.append(f"Movement plans must cover every active ship; missing={sorted(expected-submitted)}, extra={sorted(submitted-expected)}")
        for order in batch.reinforcements if state.phase == Phase.REINFORCEMENT else []:
            ship = owned.get(order.ship_id)
            if not ship or ship.position is not None or ship.reinforcement_turn != state.turn:
                errors.append(f"Reinforcement references unavailable ship {order.ship_id}")
                continue
            if not state.reinforcement_available:
                errors.append(f"Reinforcement group is not available on turn {state.turn}")
            if not self._reinforcement_entry_legal(state, order.entry_hex):
                errors.append(f"Illegal reinforcement entry hex {order.entry_hex.label}")
            if order.speed > ship.max_speed_for_turn(state.turn):
                errors.append(f"{order.ship_id}: entry speed exceeds current maximum")
        if state.phase == Phase.REINFORCEMENT:
            entry_labels = [order.entry_hex.label for order in batch.reinforcements]
            if len(entry_labels) != len(set(entry_labels)):
                errors.append("Reinforcements may not share an entry hex")
            occupied = {ship.position.label for ship in state.ships.values() if ship.position and not ship.sunk}
            for label in sorted(set(entry_labels) & occupied):
                errors.append(f"Reinforcement entry hex {label} is occupied")
            expected_reinforcements = {
                ship.id for ship in owned.values()
                if ship.position is None and ship.reinforcement_turn == state.turn and state.reinforcement_available
            }
            submitted_reinforcements = {order.ship_id for order in batch.reinforcements}
            if submitted_reinforcements != expected_reinforcements:
                errors.append(
                    "Reinforcement orders must cover the available group; "
                    f"missing={sorted(expected_reinforcements-submitted_reinforcements)}, "
                    f"extra={sorted(submitted_reinforcements-expected_reinforcements)}"
                )
        for order in batch.gunnery if state.phase == Phase.GUNNERY else []:
            attacker = owned.get(order.ship_id)
            if not attacker:
                errors.append(f"Gunnery references non-owned ship {order.ship_id}")
                continue
            if state.scenario_id == "IBS-S-01" and state.turn == 1 and batch.side == Side.AXIS:
                errors.append("Japanese ships may not fire during scenario 1 turn 1")
            for target in (order.primary_target, order.secondary_target, order.searchlight_target):
                if target and (target not in state.ships or state.ships[target].side == batch.side):
                    errors.append(f"Illegal target {target}")
            mount_ids = [mount.mount_id for mount in order.mounts]
            if len(mount_ids) != len(set(mount_ids)):
                errors.append(f"{order.ship_id}: duplicate gun mount order")
            mounts = {mount.id: mount for mount in attacker.gun_mounts}
            for mount_order in order.mounts:
                mount = mounts.get(mount_order.mount_id)
                target = state.ships.get(mount_order.target_id)
                if not mount or mount.destroyed or mount.fired_this_phase:
                    errors.append(f"{order.ship_id}: unavailable gun mount {mount_order.mount_id}")
                if not target or target.side == batch.side or target.sunk or not target.position:
                    errors.append(f"Illegal target {mount_order.target_id}")
                elif mount and not self._mount_can_bear(attacker, target, mount.arcs):
                    errors.append(f"{order.ship_id}:{mount.id} cannot bear on {target.id}")
        for order in batch.torpedoes if state.phase == Phase.TORPEDO_PLANNING else []:
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

    @staticmethod
    def _seal_orders(state: GameState) -> None:
        key = f"{state.turn}:{state.phase.value}"
        state.sealed_orders[key] = deepcopy(state.submitted_orders)
        state.submitted_orders.clear()

    @staticmethod
    def _sealed_batches(state: GameState, phase: Phase) -> list[OrderBatch]:
        return list(state.sealed_orders.get(f"{state.turn}:{phase.value}", {}).values())

    def advance(self, game_id: str) -> list[GameEvent]:
        state = self.get(game_id)
        before = len(state.events)
        if state.phase == Phase.COMPLETE:
            return []
        if state.phase == Phase.REINFORCEMENT:
            if set(state.submitted_orders) != {Side.AXIS.value, Side.ALLIES.value}:
                raise ValueError("Both sides must confirm reinforcement orders before advancing")
            self._seal_orders(state)
            self._resolve_reinforcements(state)
            state.phase = Phase.MOVEMENT_PLANNING
        elif state.phase == Phase.MOVEMENT_PLANNING:
            if set(state.submitted_orders) != {Side.AXIS.value, Side.ALLIES.value}:
                raise ValueError("Both sides must submit orders before advancing")
            self._seal_orders(state)
            state.phase = Phase.TORPEDO_PLANNING
        elif state.phase == Phase.TORPEDO_PLANNING:
            if set(state.submitted_orders) != {Side.AXIS.value, Side.ALLIES.value}:
                raise ValueError("Both sides must submit torpedo plans before advancing")
            self._seal_orders(state)
            state.phase = Phase.MOVEMENT_RESOLUTION
        elif state.phase == Phase.MOVEMENT_RESOLUTION:
            self._resolve_movement(state)
            state.phase = Phase.GUNNERY
        elif state.phase == Phase.GUNNERY:
            if set(state.submitted_orders) != {Side.AXIS.value, Side.ALLIES.value}:
                raise ValueError("Both sides must submit gunnery orders before advancing")
            self._seal_orders(state)
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
                for ship in state.ships.values():
                    ship.fired = False
                    ship.smoke = False
                    for mount in ship.gun_mounts:
                        mount.fired_this_phase = False
        self._event(state, "phase_changed", f"阶段：{state.phase.value}", rule=self._rule("IBS-R-05", 6, "5.0"))
        return state.events[before:]

    def step(self, game_id: str, joint_orders: dict[Side, OrderBatch]) -> tuple[dict[Side, PlayerObservation], list[GameEvent]]:
        events: list[GameEvent] = []
        starting_turn = self.get(game_id).turn
        while self.get(game_id).phase != Phase.COMPLETE:
            state = self.get(game_id)
            if state.phase in ORDER_PHASES:
                for side in Side:
                    source = joint_orders[side]
                    projected = OrderBatch(
                        side=side,
                        phase=state.phase,
                        reinforcements=source.reinforcements if state.phase == Phase.REINFORCEMENT else [],
                        movement=source.movement if state.phase == Phase.MOVEMENT_PLANNING else [],
                        torpedoes=source.torpedoes if state.phase == Phase.TORPEDO_PLANNING else [],
                        gunnery=source.gunnery if state.phase == Phase.GUNNERY else [],
                        smoke=source.smoke if state.phase == Phase.GUNNERY else [],
                        smoke_ships=source.smoke_ships if state.phase == Phase.GUNNERY else [],
                        illumination=source.illumination if state.phase == Phase.GUNNERY else [],
                        searchlights=source.searchlights if state.phase == Phase.GUNNERY else [],
                    )
                    result = self.submit_orders(game_id, projected)
                    if not result.valid:
                        raise ValueError(result.errors)
            events.extend(self.advance(game_id))
            if self.get(game_id).turn != starting_turn:
                break
        return {side: self.observe(game_id, side) for side in Side}, events

    def replay(self, game_id: str) -> GameState:
        """Return a detached projection; stored events and snapshots are canonical persistence inputs."""
        return self.get(game_id).model_copy(deep=True)

    @staticmethod
    def movement_commands(order: MovementOrder) -> list[str]:
        if order.commands:
            return [command.action for command in order.commands]
        plan = order.plan.strip().upper().replace("左", "P").replace("右", "S")
        if plan == "0":
            return []
        tokens = re.findall(r"\d+|PP|SS|LL|RR|P|S|L|R", plan)
        if "".join(tokens) != plan:
            raise ValueError(f"Invalid movement plan {order.plan!r}")
        commands: list[str] = []
        mapping = {
            "P": "turn_port_60", "L": "turn_port_60",
            "S": "turn_starboard_60", "R": "turn_starboard_60",
            "PP": "turn_port_120", "LL": "turn_port_120",
            "SS": "turn_starboard_120", "RR": "turn_starboard_120",
        }
        for token in tokens:
            if token.isdigit():
                commands.extend(["advance"] * int(token))
            else:
                commands.append(mapping[token])
        return commands

    @staticmethod
    def validate_movement_commands(commands: list[str]) -> None:
        if not commands:
            return
        if commands[0] != "advance":
            raise ValueError("The first movement command must be advance")
        turn_actions = {
            "turn_port_60", "turn_starboard_60", "turn_port_120", "turn_starboard_120"
        }
        for index, command in enumerate(commands):
            if command not in turn_actions | {"advance"}:
                raise ValueError(f"Unknown movement command {command}")
            if command in turn_actions:
                if index == len(commands) - 1:
                    if command not in {"turn_port_60", "turn_starboard_60"}:
                        raise ValueError("Only a free 60-degree turn is allowed after the final MF")
                elif commands[index + 1] != "advance":
                    raise ValueError("A ship must advance one MF after turning")

    @staticmethod
    def movement_cost(plan: str, commands: list[str] | None = None) -> int:
        if commands is not None:
            return sum(command == "advance" or command.endswith("120") for command in commands)
        plan = plan.strip().upper().replace("左", "P").replace("右", "S")
        if plan == "0":
            return 0
        tokens = re.findall(r"\d+|PP|SS|LL|RR|P|S|L|R", plan)
        if "".join(tokens) != plan:
            raise ValueError(f"Invalid movement plan {plan!r}")
        return sum(int(token) if token.isdigit() else (1 if token in {"PP", "SS", "LL", "RR"} else 0) for token in tokens)

    def movement_trajectory(
        self, ship: ShipState, plan: str, commands: list[str] | None = None
    ) -> tuple[list[tuple[HexCoord, int]], int]:
        if not ship.position:
            return [], ship.heading
        parsed = commands if commands is not None else self.movement_commands(MovementOrder(ship_id=ship.id, plan=plan))
        if not parsed:
            return [], ship.heading
        heading = ship.heading
        position = ship.position
        trajectory: list[tuple[HexCoord, int]] = []
        for command in parsed:
            if command == "advance":
                position = position.neighbor(heading)
                trajectory.append((position, heading))
            elif command == "turn_port_60":
                heading = 6 if heading == 1 else heading - 1
            elif command == "turn_starboard_60":
                heading = 1 if heading == 6 else heading + 1
            elif command == "turn_port_120":
                heading = ((heading - 3) % 6) + 1
                trajectory.append((position, heading))
            elif command == "turn_starboard_120":
                heading = ((heading + 1) % 6) + 1
                trajectory.append((position, heading))
        return trajectory, heading

    def _resolve_reinforcements(self, state: GameState) -> None:
        if state.reinforcement_trigger_turn == state.turn and not state.reinforcement_roll_done:
            roll, die = self._roll_d6(state)
            state.reinforcement_roll_done = True
            state.reinforcement_available = roll in state.reinforcement_succeeds_on
            self._event(
                state,
                "reinforcement_roll",
                f"想定增援检定 {roll}：" + ("成功" if state.reinforcement_available else "失败"),
                payload={"roll": roll, "available": state.reinforcement_available},
                rule=self._scenario_rule("IBS-S-01-R5", 1, "想定1增援"),
                dice=DiceRoll(dice=[die], notation="1D6", raw=roll),
            )
        orders = [order for batch in self._sealed_batches(state, Phase.REINFORCEMENT) for order in batch.reinforcements]
        by_ship = {order.ship_id: order for order in orders}
        for ship in state.ships.values():
            if ship.position is None and ship.reinforcement_turn == state.turn and ship.id in by_ship:
                order = by_ship[ship.id]
                ship.position = order.entry_hex
                ship.heading = order.heading
                ship.current_speed = order.speed
                ship.previous_speed = order.speed
                self._event(state, "reinforcement_entered", f"{ship.name} 从 {order.entry_hex.label} 入场", rule=self._rule("IBS-R-05", 6, "5.0 A"))

    @staticmethod
    def _reinforcement_entry_legal(state: GameState, entry: HexCoord) -> bool:
        start = state.reinforcement_entry_start
        end = state.reinforcement_entry_end
        if not start or not end:
            return False
        # The printed entry boundary is the shortest hex-edge corridor between its two labelled endpoints.
        return start.distance(entry) + entry.distance(end) == start.distance(end)

    def _resolve_movement(self, state: GameState) -> None:
        movement_orders = {
            order.ship_id: order
            for batch in self._sealed_batches(state, Phase.MOVEMENT_PLANNING)
            for order in batch.movement
        }
        paths: dict[str, list[tuple[HexCoord, int]]] = {}
        final_headings: dict[str, int] = {}
        for ship in state.ships.values():
            if ship.sunk or not ship.position:
                continue
            order = movement_orders.get(ship.id, MovementOrder(ship_id=ship.id, plan="0"))
            commands = self.movement_commands(order)
            trajectory, heading = self.movement_trajectory(ship, order.plan, commands)
            paths[ship.id] = trajectory
            final_headings[ship.id] = heading
            ship.current_speed = self.movement_cost(order.plan, commands)
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
            collision_sets = {frozenset(ids) for ids in collisions}
            active_ids = sorted(destinations)
            for left_index, left_id in enumerate(active_ids):
                for right_id in active_ids[left_index + 1:]:
                    left = state.ships[left_id]
                    right = state.ships[right_id]
                    if destinations[left_id] == right.position and destinations[right_id] == left.position:
                        collision_sets.add(frozenset((left_id, right_id)))
            for collision_set in collision_sets:
                ids = sorted(collision_set)
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
                    if impulse < len(paths[ship_id]):
                        state.ships[ship_id].heading = paths[ship_id][impulse][1]
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
        orders = [order for batch in self._sealed_batches(state, Phase.GUNNERY) for order in batch.gunnery]
        attacks: list[tuple[ShipState, Any, ShipState]] = []
        for order in orders:
            attacker = state.ships[order.ship_id]
            if attacker.sunk or not attacker.position:
                continue
            requested = [(mount_order.mount_id, mount_order.target_id) for mount_order in order.mounts]
            if not requested:
                for mount in attacker.gun_mounts:
                    target_id = order.primary_target if mount.kind == "primary" else order.secondary_target
                    if target_id:
                        requested.append((mount.id, target_id))
            mounts = {mount.id: mount for mount in attacker.gun_mounts}
            for mount_id, target_id in requested:
                mount = mounts.get(mount_id)
                target = state.ships.get(target_id)
                if (
                    mount and target and not mount.destroyed and not mount.fired_this_phase
                    and target.side != attacker.side and target.position
                    and self._mount_can_bear(attacker, target, mount.arcs)
                ):
                    attacks.append((attacker, mount, target))
                    mount.fired_this_phase = True
        attacking_ships: dict[str, set[str]] = {}
        for attacker, _, target in attacks:
            attacking_ships.setdefault(target.id, set()).add(attacker.id)
        prepared: list[tuple[ShipState, Any, ShipState, int, int, int]] = []
        for attacker, mount, target in attacks:
            distance = attacker.position.distance(target.position)
            if not self._can_see(state, attacker, target):
                self._event(state, "gunnery_rejected", f"{attacker.name} 无法看见 {target.name}", rule=self._rule("IBS-R-08.1", 9, "8.1"))
                continue
            modifier = self._gunnery_modifier(state, attacker, target, distance, len(attacking_ships[target.id]))
            firepower = mount.firepower
            if state.scenario_id == "IBS-S-01" and attacker.side == Side.ALLIES:
                firepower = (firepower + 1) // 2
            prepared.append((attacker, mount, target, distance, modifier, firepower))
        # The attack list and all modifiers are frozen before damage is applied: sunk ships still complete this phase's fire.
        for attacker, mount, target, distance, modifier, firepower in prepared:
            raw, dice = self._roll_d66(state)
            adjusted = d66_adjust(raw, modifier)
            hits = self.rules.hit_count(firepower, adjusted)
            attacker.fired = True
            self._event(
                state,
                "gun_mount_attack",
                f"{attacker.name} {mount.id} 炮击 {target.name}：{hits} 发命中",
                payload={
                    "attacker": attacker.id, "mount_id": mount.id, "target": target.id,
                    "distance": distance, "modifier": modifier, "firepower": firepower,
                    "caliber": mount.caliber, "hits": hits,
                },
                rule=self._rule("IBS-T-GHT", 2, "炮击命中表"),
                dice=DiceRoll(dice=dice, notation="D66", raw=raw, adjusted=adjusted),
            )
            if state.options.optional_rules.malfunction_66 and raw == 66:
                self._resolve_malfunction(state, attacker)
            for _ in range(hits):
                result_roll, result_dice = self._roll_d66(state)
                result = self.rules.gunnery_result(result_roll)
                self._apply_gunnery_result(state, attacker, target, result_roll, result, distance, mount.caliber)
                self._event(
                    state,
                    "gunnery_result",
                    f"{target.name} 命中结果 {result_roll}",
                    payload={"target": target.id, "result": result},
                    rule=self._rule("IBS-T-GHRT", 1, "炮击结果表"),
                    dice=DiceRoll(dice=result_dice, notation="D66", raw=result_roll),
                )

    def _resolve_torpedoes(self, state: GameState) -> None:
        orders = [order for batch in self._sealed_batches(state, Phase.TORPEDO_PLANNING) for order in batch.torpedoes]
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
            max_range = max(setting["range"] for setting in definition["settings"])
            if distance > max_range:
                continue
            roll, dice = self._roll_2d6(state)
            adjusted = roll + self._torpedo_modifier(attacker, target, distance)
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
                result = self.rules.table_2d6(self.rules.fire_results, roll)
                if result.get("kind") == "special_damage":
                    self._resolve_special_damage(state, ship, armour_already_penetrated=True)
                self._damage_hull(state, ship, int(result.get("hull", 0)), "fire")
                self._lose_speed(ship, int(result.get("speed_loss", 0)))
                if result.get("secondary") and ship.secondary:
                    ship.secondary.destroyed = True
                if result.get("primary"):
                    ship.primary.destroyed = True
                if result.get("extinguish") and (result.get("applies_to") != "US_only" or ship.id.startswith("IBS-U-USN-")):
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
        modifier = self.rules.range_modifier("gunnery", distance)
        modifier += self.rules.target_speed_modifier("gunnery", target.current_speed)
        if attacker.mfc_destroyed:
            modifier += int(self.rules.modifiers["other"]["mfc_destroyed"])
        modifier += max(0, attackers - 1) * int(self.rules.modifiers["other"]["each_additional_attacker"])
        if target.fire_markers:
            modifier += int(self.rules.modifiers["other"]["target_on_fire"])
        if state.options.optional_rules.smoke and target.smoke:
            modifier += int(self.rules.modifiers["optional"]["through_smoke"])
        return modifier

    def _torpedo_modifier(self, attacker: ShipState, target: ShipState, distance: int) -> int:
        modifier = self.rules.range_modifier("torpedo", distance, japanese=attacker.id.startswith("IBS-U-IJN-"))
        modifier += self.rules.target_speed_modifier("torpedo", target.current_speed)
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

    def _apply_gunnery_result(
        self, state: GameState, attacker: ShipState, target: ShipState, roll: int, result: Any, distance: int,
        caliber: float | None = None,
    ) -> None:
        if result == "miss":
            return
        if result == "special":
            self._resolve_special_damage(state, target, attacker, distance, caliber=caliber)
            return
        if isinstance(result, list):
            for item in result:
                if item == "special":
                    self._resolve_special_damage(state, target, attacker, distance, caliber=caliber)
                elif item == "radar":
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
            if "hull_by_ship_type" in result:
                group = "BB_BC" if target.ship_type in {"BB", "BC"} else (
                    "AV_CA_CL" if target.ship_type in {"AV", "CA", "CL"} else "other"
                )
                group = group if group in result["hull_by_ship_type"] else "other"
                self._damage_hull(state, target, int(result["hull_by_ship_type"][group]), "gunnery")
                return
            armour = target.belt_armor
            if any(key.startswith("primary") for key in result):
                armour = target.primary_armor
            elif "secondary" in result:
                armour = target.secondary_armor
            if result.get("armour_check") and not self._penetrates(attacker, armour, distance, caliber):
                return
            self._damage_hull(state, target, int(result.get("hull", 0)), "gunnery")
            self._lose_speed(target, int(result.get("speed_loss", 0)))
            if result.get("fire_check"):
                target.fire_markers += 1
            if "secondary" in result and target.secondary:
                target.secondary.destroyed = True
            if any(key.startswith("primary") for key in result):
                target.primary.destroyed = True

    def _resolve_special_damage(
        self,
        state: GameState,
        target: ShipState,
        attacker: ShipState | None = None,
        distance: int | None = None,
        armour_already_penetrated: bool = False,
        caliber: float | None = None,
    ) -> None:
        roll, dice = self._roll_d66(state)
        result = self.rules.special_damage_result(roll, target.displacement_band)
        penetrated = True
        if result.get("armour_check") and not armour_already_penetrated:
            penetrated = bool(
                attacker and distance is not None and self._penetrates(attacker, target.belt_armor, distance, caliber)
            )
        if penetrated:
            if "effect" in result:
                hull, speed, sunk, fire = parse_effect(result["effect"])
                percent = re.search(r"-(25|50|100)%", result["effect"])
                if percent:
                    speed = target.initial_max_speed * int(percent.group(1)) // 100
                self._damage_hull(state, target, target.hull if sunk else hull, "special_damage")
                self._lose_speed(target, speed)
                if fire:
                    target.fire_markers += 1
            else:
                self._damage_hull(state, target, target.hull if result.get("sunk") else int(result.get("hull", 0)), "special_damage")
                self._lose_speed(target, int(result.get("speed_loss", 0)))
                target.fire_markers += int(result.get("fire", 0))
                if result.get("fire_control"):
                    target.mfc_destroyed = True
                if result.get("radar"):
                    target.radar_destroyed = True
                if result.get("primary"):
                    target.primary.destroyed = True
                if result.get("secondary") and target.secondary:
                    target.secondary.destroyed = True
            additional = result.get("additional")
            if additional in {"primary_1", "primary_1_secondary_1"}:
                target.primary.destroyed = True
            if additional in {"secondary_1", "primary_1_secondary_1"} and target.secondary:
                target.secondary.destroyed = True
        self._event(
            state,
            "special_damage",
            f"{target.name} 特殊损伤 {roll}",
            payload={"target": target.id, "result": roll, "effect": result, "penetrated": penetrated},
            rule=self._rule("IBS-T-SPECIAL", 4, "特殊伤害表"),
            dice=DiceRoll(dice=dice, notation="D66", raw=roll),
        )

    def _resolve_malfunction(self, state: GameState, attacker: ShipState) -> None:
        roll, dice = self._roll_2d6(state)
        result = self.rules.table_2d6(self.rules.malfunction_results, roll)
        if result.get("destroy_random_primary"):
            attacker.primary.destroyed = True
        if result.get("power_failure_turns"):
            attacker.mfc_destroyed = True
        if result.get("destroy_random_secondary") and attacker.secondary:
            attacker.secondary.destroyed = True
        if result.get("fire") or (result.get("fire_if_aircraft_aboard") and attacker.aircraft):
            attacker.fire_markers += 1
        if result.get("special_damage"):
            self._resolve_special_damage(state, attacker, armour_already_penetrated=True)
        self._event(
            state,
            "malfunction",
            f"{attacker.name} 发生 66 故障：{roll}",
            rule=self._rule("IBS-R-09.5", 13, "9.5"),
            dice=DiceRoll(dice=dice, notation="2D6", raw=roll),
        )

    def _penetrates(self, attacker: ShipState, armour: float, distance: int, caliber: float | None = None) -> bool:
        if armour <= 0:
            return True
        nation = "JP" if attacker.id.startswith("IBS-U-IJN-") else (
            "US" if attacker.id.startswith("IBS-U-USN-") else (
                "UK" if attacker.id.startswith("IBS-U-RN-") else "DE"
            )
        )
        return self.rules.penetration(nation, caliber or attacker.primary.caliber, distance) >= armour

    @staticmethod
    def _mount_can_bear(attacker: ShipState, target: ShipState, arcs: Iterable[FiringArc]) -> bool:
        if not attacker.position or not target.position:
            return False
        candidates: list[tuple[int, int]] = []
        for heading in range(1, 7):
            try:
                candidates.append((attacker.position.neighbor(heading).distance(target.position), heading))
            except ValueError:
                continue
        if not candidates:
            return False
        bearing = min(candidates)[1]
        relative = (bearing - attacker.heading) % 6
        aspect = {
            0: FiringArc.BOW,
            1: FiringArc.STARBOARD,
            2: FiringArc.STARBOARD,
            3: FiringArc.STERN,
            4: FiringArc.PORT,
            5: FiringArc.PORT,
        }[relative]
        return aspect in arcs

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

    def _roll_d6(self, state: GameState) -> tuple[int, int]:
        rng = random.Random(state.seed * 1_000_003 + state.rng_counter)
        state.rng_counter += 1
        die = rng.randint(1, 6)
        return die, die

    @staticmethod
    def _rule(rule_id: str, page: int, section: str) -> RuleReference:
        document = "player-aid-tables-zh.pdf" if rule_id.startswith("IBS-T") else "iron-bottom-sound-iv-rules-zh.pdf"
        return RuleReference(rule_id=rule_id, document=document, pdf_page=page, section=section)

    @staticmethod
    def _scenario_rule(rule_id: str, page: int, section: str) -> RuleReference:
        return RuleReference(rule_id=rule_id, document="scenario-book-zh.pdf", pdf_page=page, section=section)

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
