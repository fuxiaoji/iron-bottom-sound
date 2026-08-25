from __future__ import annotations

import csv
import math
import random
import re
import uuid
from collections import deque
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
    MarkerState,
    MovementOrder,
    MountPosition,
    OrderBatch,
    Phase,
    PlayerObservation,
    PublicShip,
    RuleReference,
    ShipCombatEntry,
    ShipState,
    Side,
    TorpedoTrack,
    ValidationResult,
    WreckState,
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
ORDER_PHASES.add(Phase.CONTACT_SETUP)
# 齐射推荐器的"质量相近"容差（UI 偏好，非规则常量）：同档炮位数量下，与最佳修正差
# 不超过该值时优先分散目标以避集火；差更大则仍选修正最佳者。
GUNNERY_ASSIST_BAND = 3


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
        self.torpedo_launch_directions = self._yaml("torpedo-launch-directions.yaml")
        self.modifiers = self._yaml("modifiers.yaml")
        self.fire_table = self._yaml("fire-table.yaml")
        self.fire_results = self.fire_table["results"]
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
        # 同格（碰撞检定失败的舰只，distance=0）按最近射程行处理：下限钳到 1。
        return next(row for row in rows if int(row["min"]) <= max(1, distance) <= int(row["max"]))

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
        # 同格（碰撞检定失败，distance=0）按最近档处理。
        distance = max(1, distance)
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
        # 命中期望值实例级缓存：对抗评分在单次移动决策里对同一 (firepower, distance,
        # target_speed) 求值约数万次，命中表/修正查表是该热点的唯一重复成本；
        # 键与规则常量无关、跨游戏复用，行为与不缓存完全等价。
        self._gunnery_expect_cache: dict[tuple[int, int, int], float] = {}

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
            payload={
                "game_id": identifier,
                "scenario_id": scenario_id,
                "seed": seed,
                "options": state.options.model_dump(mode="json"),
            },
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

    def observe(self, game_id: str, side: Side, debug: bool = False) -> PlayerObservation:
        """调试模式（debug=True）解除战争迷雾：两阵营舰船/损伤/鱼雷/事件/比分全可见，
        仅用于本地调试，不参与任何裁决路径。"""
        state = self.get(game_id)
        ships: list[PublicShip] = []
        all_safe_events = [
            event
            for event in state.events
            if debug
            or (
                event.payload.get("secret_side") in (None, side.value)
                and not self._hidden_damage_event(state, event, side)
            )
        ]
        own_positions = [ship.position for ship in state.ships.values() if ship.side == side and not ship.sunk and ship.position]
        for ship in state.ships.values():
            visible = debug or ship.side == side or bool(ship.position and self._visible_to(state, ship, side, own_positions))
            if not visible:
                continue
            reveal = debug or ship.side == side
            hide_damage = not debug and state.options.optional_rules.hidden_damage and ship.side != side
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
                    vp=ship.vp,
                    max_speed=ship.max_speed_for_turn(state.turn) if reveal else None,
                    speed_damage_crossed=list(ship.speed_damage_crossed) if reveal else None,
                    speed_damage_track=[list(row) for row in ship.speed_damage_track] if reveal else None,
                    min_legal_speed=self._legal_speed_range(ship, state.turn)[0] if reveal else None,
                    max_legal_speed=self._legal_speed_range(ship, state.turn)[1] if reveal else None,
                    torpedo_type=ship.torpedo_type if reveal else None,
                    gun_mounts=deepcopy(ship.gun_mounts) if reveal else [],
                    torpedo_launchers=deepcopy(ship.torpedo_launchers) if reveal else [],
                    turn_limit_degrees=ship.turn_limit_degrees if reveal else None,
                    forced_straight_turns=ship.forced_straight_turns if reveal else 0,
                    forced_circle_turns=ship.forced_circle_turns if reveal else 0,
                    forced_turn_side=ship.forced_turn_side if reveal else None,
                    forced_speed=ship.forced_speed if reveal else None,
                    mfc_destroyed=ship.mfc_destroyed if reveal else False,
                    radar_destroyed=ship.radar_destroyed if reveal else False,
                    bridge_destroyed=ship.bridge_destroyed if reveal else False,
                    rudder_destroyed=ship.rudder_destroyed if reveal else False,
                    captain_status=ship.captain_status if reveal else None,
                    combat_history=self._ship_combat_history(state, ship.id, all_safe_events),
                )
            )
        safe_events = all_safe_events[-40:]
        tracks = [
            track.model_copy(deep=True)
            for track in state.torpedo_tracks
            if debug
            or not state.options.optional_rules.blind_torpedoes
            or track.side == side
            or bool(track.contact_ship_ids)
        ]
        markers: list[MarkerState] = []
        for marker in state.markers:
            if marker.kind == "contact":
                if marker.position is None and marker.secret_side != side and not debug:
                    continue
                public_marker = marker.model_copy(deep=True)
                if marker.secret_side != side and not debug:
                    public_marker.contact_truth = None
                markers.append(public_marker)
            elif marker.secret_side in (None, side) or debug:
                markers.append(marker.model_copy(deep=True))
        return PlayerObservation(
            game_id=game_id,
            scenario_id=state.scenario_id,
            scenario_title=state.scenario_title,
            side=side,
            turn=state.turn,
            max_turns=state.max_turns,
            phase=state.phase,
            visibility=int(state.visibility[side.value]),
            ships=ships,
            torpedo_tracks=tracks,
            markers=markers,
            wrecks=deepcopy(state.wrecks),
            score=(
                deepcopy(state.score)
                if debug or not (state.options.optional_rules.hidden_damage and state.phase != Phase.COMPLETE)
                else {Side.AXIS.value: 0, Side.ALLIES.value: 0}
            ),
            recent_events=safe_events,
            winner=state.winner,
            victory_reason=state.victory_reason,
        )

    @staticmethod
    def _ship_combat_history(
        state: GameState, ship_id: str, events: list[GameEvent]
    ) -> list[ShipCombatEntry]:
        combat_types = {
            "gun_mount_attack", "gunnery_result", "torpedo_attack", "torpedo_result",
            "special_damage", "fire_check", "collision_check", "collision_result", "ship_sunk",
        }
        history: list[ShipCombatEntry] = []
        for event in events:
            if event.type not in combat_types:
                continue
            attacker = event.payload.get("attacker")
            target = event.payload.get("target") or event.payload.get("ship_id")
            ships = event.payload.get("ships", [])
            directions: list[tuple[str, str | None]] = []
            if attacker == ship_id:
                directions.append(("inflicted", target if isinstance(target, str) else None))
            if target == ship_id:
                directions.append(("received", attacker if isinstance(attacker, str) else None))
            if isinstance(ships, list) and ship_id in ships:
                other = next((item for item in ships if item != ship_id), None)
                directions.append(("received", other if isinstance(other, str) else None))
            for direction, related_id in directions:
                related = state.ships.get(related_id) if related_id else None
                history.append(
                    ShipCombatEntry(
                        sequence=event.sequence,
                        turn=event.turn,
                        phase=event.phase,
                        direction=direction,
                        event_type=event.type,
                        message=event.message,
                        related_ship_id=related_id,
                        related_ship_name=related.name if related else None,
                        rule=event.rule,
                        dice=event.dice,
                        payload=event.payload,
                    )
                )
        return history[-80:]

    @staticmethod
    def _hidden_damage_event(state: GameState, event: GameEvent, side: Side) -> bool:
        if not state.options.optional_rules.hidden_damage:
            return False
        if event.type not in {"gunnery_result", "special_damage", "torpedo_result", "fire_check", "collision_result"}:
            return False
        ship_id = event.payload.get("target") or event.payload.get("ship_id")
        return bool(ship_id in state.ships and state.ships[ship_id].side != side)

    @staticmethod
    def _damage_snapshot(ship: ShipState) -> dict[str, Any]:
        """结算前状态快照：五个结算点以此为基准计算归一化损伤摘要。"""
        return {
            "hull": ship.hull,
            "speed_damage_crossed": list(ship.speed_damage_crossed),
            "fire_markers": ship.fire_markers,
            "gun_mounts_destroyed": sum(1 for mount in ship.gun_mounts if mount.destroyed),
            "torpedo_launchers_destroyed": sum(1 for launcher in ship.torpedo_launchers if launcher.destroyed),
            "sunk": ship.sunk,
            "mfc_destroyed": ship.mfc_destroyed,
            "radar_destroyed": ship.radar_destroyed,
            "bridge_destroyed": ship.bridge_destroyed,
            "rudder_destroyed": ship.rudder_destroyed,
            "captain_status": ship.captain_status,
            "guns_disabled_turns": ship.guns_disabled_turns,
            "turn_limit_degrees": ship.turn_limit_degrees,
            "forced_straight_turns": ship.forced_straight_turns,
            "forced_circle_turns": ship.forced_circle_turns,
            "forced_speed": ship.forced_speed,
            "forced_speed_turns": ship.forced_speed_turns,
        }

    @staticmethod
    def _damage_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
        """归一化损伤摘要：仅统计 actually 发生的差异，flag 只列置位项。"""
        crossed_before = sum(before["speed_damage_crossed"])
        crossed_after = sum(after["speed_damage_crossed"])
        flags: dict[str, Any] = {}
        for key in ("mfc_destroyed", "radar_destroyed", "bridge_destroyed", "rudder_destroyed"):
            if after[key] and not before[key]:
                flags[key] = True
        if after["captain_status"] != before["captain_status"]:
            flags["captain_status"] = after["captain_status"]
        if after["guns_disabled_turns"] > before["guns_disabled_turns"]:
            flags["guns_disabled_turns"] = after["guns_disabled_turns"]
        if after["turn_limit_degrees"] != before["turn_limit_degrees"]:
            flags["turn_limit_degrees"] = after["turn_limit_degrees"]
        if after["forced_straight_turns"] > before["forced_straight_turns"]:
            flags["forced_straight_turns"] = after["forced_straight_turns"]
        if after["forced_circle_turns"] > before["forced_circle_turns"]:
            flags["forced_circle_turns"] = after["forced_circle_turns"]
        if after["forced_speed"] != before["forced_speed"]:
            flags["forced_speed"] = after["forced_speed"]
        if after["forced_speed_turns"] > before["forced_speed_turns"]:
            flags["forced_speed_turns"] = after["forced_speed_turns"]
        return {
            "hull_lost": before["hull"] - after["hull"],
            "speed_lost": crossed_after - crossed_before,
            "fire_added": max(0, after["fire_markers"] - before["fire_markers"]),
            "fire_remaining": after["fire_markers"],
            "gun_mounts_destroyed": after["gun_mounts_destroyed"] - before["gun_mounts_destroyed"],
            "torpedo_launchers_destroyed": after["torpedo_launchers_destroyed"] - before["torpedo_launchers_destroyed"],
            "sank": bool(after["sunk"] and not before["sunk"]),
            "flags": flags,
        }

    def _add_fire(self, state: GameState, ship: ShipState, attacker: ShipState | None = None, count: int = 1) -> None:
        """统一加火源；首次点火者记入 ship.fire_source_attacker 供火灾沉没追溯。"""
        if count <= 0:
            return
        ship.fire_markers += count
        if ship.fire_source_attacker is None:
            ship.fire_source_attacker = attacker.id if attacker is not None else None
            ship.fire_source_turn = state.turn

    def legal_actions(self, game_id: str, side: Side) -> list[LegalAction]:
        state = self.get(game_id)
        if state.phase == Phase.COMPLETE:
            return []
        if state.phase in ORDER_PHASES and side.value not in state.submitted_orders:
            schemas: dict[Phase, dict[str, Any]] = {
                Phase.CONTACT_SETUP: {"contacts": "four edge markers; two real formations and two decoys"},
                Phase.REINFORCEMENT: {
                    "reinforcements": "entry_hex, heading, speed",
                    "reinforcement_candidates": self._reinforcement_candidates(state, side),
                    "confirmation": {"ready": True},
                },
                Phase.MOVEMENT_PLANNING: {
                    "movement": {"ship_id": "owned ship", "speed": "legal MF", "commands": "advance/turn_*"},
                    "movement_candidates": [
                        self.movement_candidates(state, ship)
                        for ship in state.ships.values()
                        if ship.side == side and ship.position is not None
                    ],
                    "confirmation": {"ready": True},
                },
                Phase.TORPEDO_PLANNING: {
                    "torpedoes": "launcher, launch_at_mf, launch_hex, bearing, setting_index",
                    "torpedo_candidates": self._torpedo_candidates(state, side),
                    "confirmation": {"ready": True},
                },
                Phase.GUNNERY: {
                    "gunnery": "per-mount target orders",
                    "gunnery_candidates": self._gunnery_candidates(state, side),
                    "illumination": "star-shell target hex",
                    "searchlights": "target and active flag",
                    "smoke": "deploy flag",
                    "confirmation": {"ready": True},
                },
            }
            return [LegalAction(kind="submit_phase_orders", schema_hint=schemas[state.phase])]
        return [LegalAction(kind="advance")] if state.phase not in ORDER_PHASES or len(state.submitted_orders) == 2 else []

    def _gunnery_candidates(self, state: GameState, side: Side) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for ship in state.ships.values():
            if ship.side != side or ship.sunk or not ship.position:
                continue
            blocked_reason: str | None = None
            if state.scenario_id == "IBS-S-01" and state.turn == 1 and side == Side.AXIS:
                blocked_reason = "想定特例：日军第 1 回合不得开火"
            elif ship.guns_disabled_turns:
                blocked_reason = "本回合全部火炮失效"
            elif state.options.optional_rules.squalls and self._in_squall(state, ship.position):
                blocked_reason = "舰船位于飑区内"
            targets: list[dict[str, Any]] = []
            if not blocked_reason:
                for target in state.ships.values():
                    if target.side == side or target.sunk or not target.position or not self._can_see(state, ship, target):
                        continue
                    mount_ids = [
                        mount.id for mount in ship.gun_mounts
                        if not mount.destroyed and not mount.fired_this_phase
                        and self._mount_can_bear(ship, target, mount.arcs)
                    ]
                    if mount_ids:
                        distance = ship.position.distance(target.position)
                        caliber = max(
                            (mount.caliber for mount in ship.gun_mounts if mount.id in mount_ids),
                            default=ship.primary.caliber,
                        )
                        # 单人单目标固有修正（不含集火附加射手/多目标惩罚两项分配相关项）；
                        # 修正值由引擎计算下发，前端不复制规则常量。
                        modifier = self._gunnery_modifier(state, ship, target, distance, 1, caliber, 1)
                        # 期望命中同样由引擎计算下发（规则公式唯一在引擎，AI 不复制）。
                        expected_hits = sum(
                            self.expected_gunnery_hits(mount.firepower, distance)
                            for mount in ship.gun_mounts
                            if mount.id in mount_ids
                        )
                        targets.append({
                            "target_id": target.id,
                            "mount_ids": mount_ids,
                            "range": distance,
                            "modifier": modifier,
                            "expected_hits": expected_hits,
                        })
            candidates.append({"ship_id": ship.id, "targets": targets, "blocked_reason": blocked_reason})
        return candidates

    def gunnery_assist(
        self, state: GameState, side: Side, assigned: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """为全舰齐射推荐目标分配（只读、不落库）。

        优先级：1) 每舰优先射界炮位最多的目标（火力）→ 2) 同档内修正最佳（距离+各类修正；
        D66 骰点越小越好、命中表低段命中更多，故修正为负更好、取最小修正为目标最佳）；
        3) 修正差不超过 GUNNERY_ASSIST_BAND 时优先分散到负载最小目标，避免多舰集火同一目标。
        `assigned` 为草稿中既有齐射 {ship_id,target_id}：这些舰不再推荐，其目标计入负载。
        目标/射界/修正全部来自引擎 `_gunnery_candidates`，前端不复制任何规则常量。
        """
        candidates = self._gunnery_candidates(state, side)
        load: dict[str, int] = {}
        already = set()
        for entry in assigned or []:
            ship_id, target_id = entry.get("ship_id"), entry.get("target_id")
            if ship_id and target_id:
                already.add(ship_id)
                load[target_id] = load.get(target_id, 0) + 1
        options: list[dict[str, Any]] = []
        excluded: list[dict[str, Any]] = []
        for candidate in candidates:
            if candidate["ship_id"] in already:
                continue
            if candidate["blocked_reason"] or not candidate["targets"]:
                excluded.append({
                    "ship_id": candidate["ship_id"],
                    "reason": candidate["blocked_reason"] or "当前无合法目标/射界",
                })
                continue
            options.append(candidate)
        # 越受限越先分配：目标少的舰先选，灵活舰后补空档，避免把资源耗在同一目标上。
        options.sort(key=lambda item: (len(item["targets"]), -max(len(t["mount_ids"]) for t in item["targets"])))
        recommendations: list[dict[str, Any]] = []
        for candidate in options:
            targets = candidate["targets"]
            max_mounts = max(len(t["mount_ids"]) for t in targets)
            tier = [t for t in targets if len(t["mount_ids"]) == max_mounts]
            # D66 命中表骰点越小越好：修正为负更好，最佳修正 = 最小的修正值。
            best_modifier = min(t["modifier"] for t in tier)
            band = [t for t in tier if t["modifier"] <= best_modifier + GUNNERY_ASSIST_BAND]
            chosen = min(band, key=lambda t: (load.get(t["target_id"], 0), t["modifier"], t["range"]))
            load[chosen["target_id"]] = load.get(chosen["target_id"], 0) + 1
            recommendations.append({
                "ship_id": candidate["ship_id"],
                "target_id": chosen["target_id"],
                "mount_ids": chosen["mount_ids"],
                "range": chosen["range"],
                "modifier": chosen["modifier"],
                "expected_hits": chosen["expected_hits"],
            })
        return {"recommendations": recommendations, "excluded": excluded}

    def gunnery_target_options(self, state: GameState, side: Side) -> list[dict[str, Any]]:
        """只读：每舰全部合法炮击目标选项（含 `expected_hits`），供 AI 概率抽样。
        与 `gunnery_assist` 的"每舰一条推荐"不同，这里返回每舰每个合法目标一条。"""
        return self._gunnery_candidates(state, side)

    @staticmethod
    def _ship_fire_heat(ship: ShipState, viewer: Side, expected_hits, cells: list[HexCoord]) -> dict[str, float]:
        """单舰射界热力：可指向该格的炮位 `firepower × 期望命中` 之和。

        热值 = Σ 每门炮 firepower × 该距离的 D66 期望命中数（用户公式）；火力大的炮位贡献更大，
        多炮位/多舰线性叠加。本方用真实状态（已毁炮位剔除）；敌方按记录全炮位（不剔除已毁，
        避免隐藏损伤泄漏）。与 `field_of_fire_heatmap` 全方模式共用同一公式。
        """
        heat: dict[str, float] = {}
        for mount in ship.gun_mounts:
            if ship.side == viewer and mount.destroyed:
                continue
            for cell in cells:
                if cell == ship.position:
                    continue
                if IronBottomEngine._relative_aspect(ship.position, ship.heading, cell) not in mount.arcs:
                    continue
                value = expected_hits(mount.firepower, ship.position.distance(cell))
                if value <= 0:
                    continue
                heat[cell.label] = heat.get(cell.label, 0.0) + mount.firepower * value
        return heat

    def expected_gunnery_hits(self, firepower: int, distance: int, target_speed: int = 4) -> float:
        """单门炮对指定距离的 D66 期望命中数：对 36 档 D66 全举
        `d66_adjust(roll, 距离修正 + 目标航速修正)` 后查命中表取均值。

        命中表/距离/航速修正是规则常量，全部由引擎唯一计算并下发；热力图与
        战术 AI 的 `ship_gun_pressure` 共用本方法，避免公式在引擎外复制。
        """
        key = (firepower, distance, target_speed)
        cached = self._gunnery_expect_cache.get(key)
        if cached is not None:
            return cached
        speed_mod = self.rules.target_speed_modifier("gunnery", target_speed)
        value = sum(
            self.rules.hit_count(
                firepower,
                d66_adjust(roll, self.rules.range_modifier("gunnery", distance) + speed_mod),
            )
            for roll in D66_VALUES
        ) / len(D66_VALUES)
        self._gunnery_expect_cache[key] = value
        return value

    def ship_gun_pressure(
        self, state: GameState, ship: ShipState,
        position: HexCoord | None = None, heading: int | None = None,
        target_hexes: list[HexCoord] | None = None,
    ) -> float:
        """舰在（可选假想）位/航向下对目标格的火力压力：Σ 可指向该格的未毁炮位
        `firepower × 期望命中`。

        默认 `target_hexes` = 本方可见敌舰格（`_visible_to` 与 observe/热力图同源，
        不泄漏隐蔽舰位置）。战术 AI 在候选移动位/航向上调用本方法做"让敌方处于
        我方火力覆盖"的打分；命中公式唯一在 `expected_gunnery_hits`。
        """
        position = position if position is not None else ship.position
        heading = heading if heading is not None else ship.heading
        if position is None:
            return 0.0
        if target_hexes is None:
            own_positions = [
                other.position for other in state.ships.values()
                if other.side == ship.side and not other.sunk and other.position
            ]
            target_hexes = [
                enemy.position for enemy in state.ships.values()
                if enemy.side != ship.side and not enemy.sunk and enemy.position
                and self._visible_to(state, enemy, ship.side, own_positions)
            ]
        total = 0.0
        for mount in ship.gun_mounts:
            if mount.destroyed:
                continue
            for target in target_hexes:
                if target == position:
                    continue
                if self._relative_aspect(position, heading, target) not in mount.arcs:
                    continue
                total += mount.firepower * self.expected_gunnery_hits(mount.firepower, position.distance(target))
        return total

    def field_of_fire_heatmap(self, state: GameState, viewer: Side, ship_id: str | None = None, target_speed: int = 4) -> dict[str, Any]:
        """只读射界热力图：把双方各舰每门可射火炮的射界/射程覆盖叠加到地图每格。

        热值 = Σ 可指向该格的炮位 `firepower` × 该格 D66 期望命中数。期望命中 = 对 36 档
        D66 全举 `d66_adjust(roll, 距离修正 + 目标航速修正)` 后查命中表取均值；近格修正更负 →
        期望命中更高 → 更热；跨舰/跨炮线性叠加。

        `target_speed` 是假定被射击目标的航速，其修正按已验证的目标航速表
        `target_speed_modifier("gunnery", speed)` 取值（0→-18、1→-9、2-3→-4、4+→0），默认
        航速 4 → 修正 0。命中表/距离/航速修正是规则常量，全部由引擎唯一计算并下发，前端只渲染颜色。

        本方用真实状态（已毁炮位剔除）；敌方按记录全炮位（不泄漏隐藏损伤），且只含
        `_visible_to` 可见敌舰（不泄漏隐蔽舰位置）。

        `ship_id` 给定时只算该舰（"选中哪艘就展示哪艘"），所属方填充该舰热值，另一侧为空；
        本方舰走真实炮位、敌方舰走记录炮位，敌方舰仍须可见（兜底，前端只能选到已渲染的可见舰）。
        """
        expected: dict[tuple[int, int], float] = {}

        def expected_hits(firepower: int, distance: int) -> float:
            key = (firepower, distance)
            if key not in expected:
                expected[key] = self.expected_gunnery_hits(firepower, distance, target_speed)
            return expected[key]

        cells = [
            HexCoord(q=q, r=row - (q - (q & 1)) // 2)
            for q in range(34)
            for row in range(27)
        ]
        own_positions = [
            ship.position for ship in state.ships.values()
            if ship.side == viewer and not ship.sunk and ship.position
        ]

        def empty_side() -> dict[str, Any]:
            return {"hexes": {}, "max_heat": 0.0, "ships": []}

        if ship_id is not None:
            target = state.ships.get(ship_id)
            if target is None or target.sunk or not target.position:
                return {"viewer": viewer.value, "sides": {s.value: empty_side() for s in (Side.AXIS, Side.ALLIES)}}
            if target.side != viewer and not self._visible_to(state, target, viewer, own_positions):
                return {"viewer": viewer.value, "sides": {s.value: empty_side() for s in (Side.AXIS, Side.ALLIES)}}
            heat = self._ship_fire_heat(target, viewer, expected_hits, cells)
            sides: dict[str, Any] = {s.value: empty_side() for s in (Side.AXIS, Side.ALLIES)}
            sides[target.side.value] = {
                "hexes": {label: round(value, 4) for label, value in sorted(heat.items())},
                "max_heat": round(max(heat.values(), default=0.0), 4),
                "ships": [{
                    "ship_id": target.id,
                    "name": target.name,
                    "position": target.position.label,
                    "heading": target.heading,
                }],
            }
            return {"viewer": viewer.value, "sides": sides}

        sides: dict[str, Any] = {}
        for side in (Side.AXIS, Side.ALLIES):
            heat: dict[str, float] = {}
            ships_info: list[dict[str, Any]] = []
            for ship in state.ships.values():
                if ship.sunk or not ship.position or ship.side != side:
                    continue
                if side != viewer and not self._visible_to(state, ship, viewer, own_positions):
                    continue
                if ship.gun_mounts:
                    ships_info.append({
                        "ship_id": ship.id,
                        "name": ship.name,
                        "position": ship.position.label,
                        "heading": ship.heading,
                    })
                for label, value in self._ship_fire_heat(ship, viewer, expected_hits, cells).items():
                    heat[label] = heat.get(label, 0.0) + value
            sides[side.value] = {
                "hexes": {label: round(value, 4) for label, value in sorted(heat.items())},
                "max_heat": round(max(heat.values(), default=0.0), 4),
                "ships": ships_info,
            }
        return {"viewer": viewer.value, "sides": sides}

    def _reinforcement_candidates(self, state: GameState, side: Side) -> dict[str, Any]:
        """本回合本方待入场增援与入场信息（只读，供增援阶段 UI 使用）。

        只列本方 `reinforcement_turn == 当前回合` 且尚未入场的舰船；入口走廊格按
        `_reinforcement_entry_legal`（E17-U27 最短六角边走廊）枚举。检定结果取最后一条
        `reinforcement_roll` 事件。前端据此展示"检定失败/未到回合"或逐舰入场表。
        """
        pending = [
            ship for ship in state.ships.values()
            if ship.side == side and ship.position is None and ship.reinforcement_turn == state.turn
        ]
        entry_hexes: list[str] = []
        if state.reinforcement_entry_start is not None and state.reinforcement_entry_end is not None:
            for q in range(1, 34):
                for r in range(1, 28):
                    candidate = HexCoord(q=q, r=r)
                    if self._reinforcement_entry_legal(state, candidate):
                        entry_hexes.append(candidate.label)
        roll_result = None
        for event in reversed(state.events):
            if event.type == "reinforcement_roll":
                roll_result = {
                    "roll": event.payload["roll"],
                    "available": event.payload["available"],
                }
                break
        return {
            "group_available": bool(state.reinforcement_available),
            "arrival_turn": state.reinforcement_arrival_turn,
            "trigger_turn": state.reinforcement_trigger_turn,
            "succeeds_on": list(state.reinforcement_succeeds_on),
            "roll_result": roll_result,
            "entry_range": [
                state.reinforcement_entry_start.label, state.reinforcement_entry_end.label,
            ] if state.reinforcement_entry_start is not None else None,
            "entry_hexes": entry_hexes,
            "ships": [
                {
                    "ship_id": ship.id,
                    "name": ship.name,
                    "asset": ship.asset,
                    "max_speed": ship.max_speed_for_turn(state.turn),
                }
                for ship in sorted(pending, key=lambda item: item.id)
            ],
        }

    def movement_plan_trajectories(
        self, state: GameState, side: Side, plans: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """本回合已编排移动计划的逐舰航迹（只读，供地图画线/目标点淡算子）。

        逐舰复用 `movement_preview`：引擎计算航迹，前端只画线。非本方/无位舰返回
        invalid 条目而不是抛错，便于前端一次批量画草稿里全部计划。
        """
        trajectories: list[dict[str, Any]] = []
        for entry in plans:
            ship_id = entry.get("ship_id")
            plan = entry.get("plan", "0")
            ship = state.ships.get(ship_id)
            if not ship or ship.side != side or ship.sunk or not ship.position:
                trajectories.append({
                    "ship_id": ship_id,
                    "plan": plan,
                    "cost": 0,
                    "valid": False,
                    "commitable": False,
                    "errors": ["该舰不可规划移动"],
                    "trajectory": [],
                    "end_hex": None,
                    "end_heading": None,
                })
                continue
            preview = self.movement_preview(state, ship, plan=plan)
            trajectories.append({
                "ship_id": ship_id,
                "plan": plan,
                "cost": preview["cost"],
                "valid": preview["valid"],
                "commitable": preview["commitable"],
                "errors": preview["errors"],
                "trajectory": preview["trajectory"],
                "end_hex": preview["current_label"],
                "end_heading": preview["current_heading"],
            })
        return {"trajectories": trajectories}

    def sealed_movement_trajectories(
        self, state: GameState, side: Side, debug: bool = False,
    ) -> dict[str, Any]:
        """从已封存的移动计划重放本回合逐舰航迹（供鱼雷计划阶段保留显示）。

        移动阶段结束时双方计划已封存；鱼雷计划阶段调用本接口把航迹画回地图。
        默认只含本方（敌方计划属机密），调试模式（debug=True）下全阵营可见。
        """
        trajectories: list[dict[str, Any]] = []
        for batch in self._sealed_batches(state, Phase.MOVEMENT_PLANNING):
            for movement in batch.movement:
                ship = state.ships.get(movement.ship_id)
                if not ship or ship.sunk or not ship.position:
                    continue
                if ship.side != side and not debug:
                    continue
                preview = self.movement_preview(state, ship, plan=movement.plan or "0")
                trajectories.append({
                    "ship_id": ship.id,
                    "name": ship.name,
                    "side": ship.side.value,
                    "plan": movement.plan or "0",
                    "cost": preview["cost"],
                    "valid": preview["valid"],
                    "trajectory": preview["trajectory"],
                    "end_hex": preview["current_label"],
                    "end_heading": preview["current_heading"],
                })
        return {"trajectories": trajectories}

    def _torpedo_candidates(self, state: GameState, side: Side) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for ship in state.ships.values():
            if ship.side != side or ship.sunk or not ship.position or not ship.torpedo or ship.torpedo.destroyed:
                continue
            blocked_reason: str | None = None
            if state.scenario_id == "IBS-S-01" and state.turn < 4 and side == Side.AXIS:
                blocked_reason = "想定特例：日军第 4 回合前不得发射鱼雷"
            elif ship.ship_type in {"BB", "BC"} and ship.current_speed >= 4:
                blocked_reason = "战列舰/战列巡洋舰以 4 MF 或更高速度航行"
            elif state.options.optional_rules.squalls and self._in_squall(state, ship.position):
                blocked_reason = "舰船位于飑区内"
            movement = next(
                (
                    item for batch in self._sealed_batches(state, Phase.MOVEMENT_PLANNING)
                    for item in batch.movement if item.ship_id == ship.id
                ),
                None,
            )
            launch_positions: list[dict[str, Any]] = []
            if movement:
                trajectory, _ = self.movement_trajectory(ship, movement.plan, self.movement_commands(movement))
                launch_positions = [{
                    "mf": 0,
                    "hex": ship.position.model_dump(mode="json"),
                    "heading": ship.heading,
                }] + [
                    {"mf": index, "hex": position.model_dump(mode="json"), "heading": heading}
                    for index, (position, heading) in enumerate(trajectory, start=1)
                ]
            launchers = [] if blocked_reason else [
                {
                    "launcher_id": launcher.id,
                    "loaded": launcher.loaded,
                    "sides": [arc.value for arc in launcher.arcs if arc in {FiringArc.PORT, FiringArc.STARBOARD}],
                    "angles": self.rules.torpedo_launch_directions["angles"],
                    "relative_heading": self.rules.torpedo_launch_directions["relative_heading"],
                }
                for launcher in ship.torpedo_launchers
                if not launcher.destroyed and not launcher.reload_turns_remaining and launcher.loaded > 0
            ]
            definition = self.rules.torpedoes.get(ship.torpedo_type or "", {})
            settings = [
                {"index": index, "speed": setting["speed"], "range": setting["range"]}
                for index, setting in enumerate(definition.get("settings", []))
            ]
            candidates.append({
                "ship_id": ship.id,
                "launchers": launchers,
                "launch_positions": launch_positions,
                "settings": settings,
                "blocked_reason": blocked_reason or ("缺少已封存的移动计划" if not movement else None),
            })
        return candidates

    @staticmethod
    def torpedo_hit_count(aspect: str, adjusted: int) -> int:
        """IBS-R-08.2 鱼雷命中阈值，从 _resolve_torpedoes 提取，引擎与推荐器共用防漂移。"""
        if aspect == "broadside":
            return 2 if adjusted >= 13 else (1 if adjusted >= 11 else 0)
        return 1 if adjusted >= 13 else 0

    @staticmethod
    def expected_torpedo_hits(aspect: str, modifier: int, salvo_size: int) -> float:
        """2D6 36 结果穷举的期望命中数（按齐射枚数封顶，与结算一致）。"""
        total = 0
        for die_one in range(1, 7):
            for die_two in range(1, 7):
                total += min(IronBottomEngine.torpedo_hit_count(aspect, die_one + die_two + modifier), salvo_size)
        return total / 36

    @staticmethod
    def torpedo_hit_probability(aspect: str, modifier: int) -> float:
        """至少 1 发命中的概率（2D6 36 结果穷举）。"""
        hits = 0
        for die_one in range(1, 7):
            for die_two in range(1, 7):
                if IronBottomEngine.torpedo_hit_count(aspect, die_one + die_two + modifier) >= 1:
                    hits += 1
        return hits / 36

    def _project_torpedo_path(
        self, state: GameState, torpedo_type: str, launch_hex: HexCoord,
        heading: int, setting_index: int, launch_at_mf: int,
        launch_angle: str = "A", ship_heading: int | None = None,
    ) -> dict[str, Any]:
        """纯几何直线投影，与 _resolve_movement 鱼雷循环一致：逐格直行、
        range_remaining 递减、触陆/越界截停；跨回合按 speed_cycle[(回合-发射)%3]
        推进（发射回合首段扣已耗 MF）。起点按锚点偏移（B 船尾外 1 格、X 船头外
        1 格）落格。"""
        definition = self.rules.torpedoes[torpedo_type]
        setting = definition["settings"][setting_index]
        cycle = setting["speed"]
        position = self._torpedo_anchor_hex(launch_hex, ship_heading or heading, launch_angle)
        path: list[HexCoord] = [position]
        distance_travelled = 0
        range_remaining = int(setting["range"])
        obstacle: str | None = None
        rel_turn = 0
        allowance = max(0, int(cycle[0]) - launch_at_mf)
        while range_remaining > 0:
            if allowance <= 0:
                rel_turn += 1
                allowance = int(cycle[rel_turn % 3])
                continue
            try:
                next_position = position.neighbor(heading)
            except ValueError:
                obstacle = "edge"
                break
            if self._terrain_impassable(state, next_position):
                obstacle = "land"
                break
            position = next_position
            path.append(position)
            distance_travelled += 1
            range_remaining -= 1
            allowance -= 1
        return {
            "start_hex": path[0].label,
            "end_hex": position.label,
            "heading": heading,
            "path": [coord.label for coord in path],
            "distance_travelled": distance_travelled,
            "range_remaining": range_remaining,
            "obstacle": obstacle,
        }

    def _project_target_position(self, state: GameState, ship: ShipState, turns: int) -> HexCoord | None:
        """可见信息匀速直线外推：目标沿当前航向每回合走 current_speed 格，触界钳制。"""
        position = ship.position
        if position is None or turns <= 0:
            return position
        for _ in range(turns * max(0, ship.current_speed)):
            try:
                position = position.neighbor(ship.heading)
            except ValueError:
                break
        return position

    def _assist_intercept(
        self, state: GameState, torpedo_type: str, launch_hex: HexCoord, heading: int,
        setting_index: int, launch_at_mf: int, target: ShipState,
        launch_angle: str = "A", ship_heading: int | None = None,
    ) -> tuple[HexCoord | None, int, str | None, int]:
        """逐 impulse 同时推进鱼雷与目标，返回 (交点, 鱼雷到交点距离, 截停原因, 第几回合)。
        与 _resolve_movement 同步移动语义一致：同格即接触，船撞静止雷也算；
        发射回合目标在发射前领先 launch_at_mf 步。起点按锚点偏移落格。"""
        definition = self.rules.torpedoes[torpedo_type]
        setting = definition["settings"][setting_index]
        cycle = setting["speed"]
        position = self._torpedo_anchor_hex(launch_hex, ship_heading or heading, launch_angle)
        target_position = target.position
        target_speed = max(0, target.current_speed)
        distance = 0
        range_remaining = int(setting["range"])
        rel_turn = 0
        allowance = max(0, int(cycle[0]) - launch_at_mf)
        target_moved = min(launch_at_mf, target_speed)
        for _ in range(target_moved):
            try:
                target_position = target_position.neighbor(target.heading)
            except ValueError:
                break
        while range_remaining > 0:
            target_remaining = target_speed - target_moved
            if allowance <= 0 and target_remaining <= 0:
                rel_turn += 1
                allowance = int(cycle[rel_turn % 3])
                target_moved = 0
                continue
            for _ in range(max(allowance, target_remaining)):
                if allowance > 0 and range_remaining > 0:
                    try:
                        next_position = position.neighbor(heading)
                    except ValueError:
                        return None, max(1, distance), "edge", rel_turn
                    if self._terrain_impassable(state, next_position):
                        return None, max(1, distance), "land", rel_turn
                    position = next_position
                    distance += 1
                    range_remaining -= 1
                    allowance -= 1
                if target_remaining > 0:
                    try:
                        target_position = target_position.neighbor(target.heading)
                    except ValueError:
                        pass
                    target_moved += 1
                    target_remaining -= 1
                if position == target_position:
                    return position, max(1, distance), None, rel_turn
                if allowance <= 0 and target_remaining <= 0:
                    break
            if range_remaining <= 0:
                break
        return None, max(1, distance), None, rel_turn

    def _assist_launch_combos(self, state: GameState, side: Side) -> list[dict[str, Any]]:
        """枚举某阵营当前可发射的全部合法组合（复用 _torpedo_candidates 为唯一事实来源）。"""
        combos: list[dict[str, Any]] = []
        for candidate in self._torpedo_candidates(state, side):
            if candidate["blocked_reason"]:
                continue
            ship = state.ships[candidate["ship_id"]]
            for launcher in candidate["launchers"]:
                salvo_size = int(launcher["loaded"])
                for launch_position in candidate["launch_positions"]:
                    for launch_side in launcher["sides"]:
                        for launch_angle in launcher["angles"]:
                            for setting in candidate["settings"]:
                                combos.append({
                                    "ship_id": ship.id,
                                    "launcher_id": launcher["launcher_id"],
                                    "launch_at_mf": int(launch_position["mf"]),
                                    "launch_hex": HexCoord(**launch_position["hex"]),
                                    "launch_heading": int(launch_position["heading"]),
                                    "launch_side": launch_side,
                                    "launch_angle": launch_angle,
                                    "setting_index": int(setting["index"]),
                                    "salvo_size": salvo_size,
                                })
        return combos

    def _assist_launch_from_dict(
        self, state: GameState, side: Side, launch: dict[str, Any],
    ) -> dict[str, Any] | None:
        """从 API 下发的单个发射参数还原组合（launch_hex/舰首取自已封存移动计划）。"""
        ship = state.ships.get(launch.get("ship_id"))
        if not ship or ship.side != side:
            return None
        candidate = next(
            (item for item in self._torpedo_candidates(state, side) if item["ship_id"] == ship.id), None
        )
        if not candidate or candidate["blocked_reason"]:
            return None
        launcher = next(
            (item for item in candidate["launchers"] if item["launcher_id"] == launch.get("launcher_id")), None
        )
        if not launcher:
            return None
        launch_at_mf = int(launch.get("launch_at_mf", 0))
        position = next(
            (item for item in candidate["launch_positions"] if item["mf"] == launch_at_mf), None
        )
        if not position:
            return None
        launch_side = launch.get("launch_side")
        launch_angle = launch.get("launch_angle")
        if launch_side not in launcher["sides"] or launch_angle not in launcher["angles"]:
            return None
        setting_index = int(launch.get("setting_index", 0))
        if setting_index >= len(candidate["settings"]):
            return None
        return {
            "ship_id": ship.id,
            "launcher_id": launcher["launcher_id"],
            "launch_at_mf": launch_at_mf,
            "launch_hex": HexCoord(**position["hex"]),
            "launch_heading": int(position["heading"]),
            "launch_side": launch_side,
            "launch_angle": launch_angle,
            "setting_index": setting_index,
            "salvo_size": int(launcher["loaded"]),
        }

    def _assist_evaluate(
        self, state: GameState, target: ShipState, combo: dict[str, Any],
    ) -> dict[str, Any]:
        """对单个组合投影鱼雷航迹、推算与目标外推的交点、命中概率与期望命中。"""
        ship = state.ships[combo["ship_id"]]
        torpedo_type = ship.torpedo_type or ""
        torpedo_heading = self._torpedo_launch_heading(
            int(combo["launch_heading"]), combo["launch_side"], combo["launch_angle"]
        )
        ship_heading = int(combo["launch_heading"])
        projection = self._project_torpedo_path(
            state, torpedo_type, combo["launch_hex"], torpedo_heading,
            int(combo["setting_index"]), int(combo["launch_at_mf"]),
            combo["launch_angle"], ship_heading,
        )
        intercept_hex, distance, obstacle, intercept_turn = self._assist_intercept(
            state, torpedo_type, combo["launch_hex"], torpedo_heading,
            int(combo["setting_index"]), int(combo["launch_at_mf"]), target,
            combo["launch_angle"], ship_heading,
        )
        result: dict[str, Any] = {
            **combo,
            "torpedo_heading": torpedo_heading,
            "launch_hex": combo["launch_hex"].label,
            "distance": max(1, distance),
            "aspect": None,
            "modifier": None,
            "hit_probability": None,
            "expected_hits": 0,
            "intercept_hex": intercept_hex.label if intercept_hex else None,
            "intercept_turn": intercept_turn,
            "predicted_path": projection["path"],
            "predicted_end": projection["end_hex"],
            "blocked_reason": obstacle,
        }
        if intercept_hex:
            source_bearing = ((torpedo_heading + 2) % 6) + 1
            relative = (source_bearing - target.heading) % 6
            aspect = "bow_stern" if relative in {0, 3} else "broadside"
            modifier = self._torpedo_modifier(ship, target, distance)
            result["aspect"] = aspect
            result["modifier"] = modifier
            result["hit_probability"] = self.torpedo_hit_probability(aspect, modifier)
            result["expected_hits"] = self.expected_torpedo_hits(aspect, modifier, int(combo["salvo_size"]))
        return result

    def torpedo_assist(
        self, state: GameState, side: Side,
        target_id: str | None = None, launch: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """鱼雷辅助推荐：仅用可见信息（目标当前航向/航速匀速外推），按期望命中
        降序返回合法组合与预测航迹；不读敌方封存计划。给 launch 只算该组合。"""
        target: ShipState | None = None
        if target_id and target_id in state.ships:
            chosen = state.ships[target_id]
            if chosen.side != side and not chosen.sunk and chosen.position:
                target = chosen
        if target is None:
            own = [ship for ship in state.ships.values() if ship.side == side and ship.position and not ship.sunk]
            enemies = [ship for ship in state.ships.values() if ship.side != side and ship.position and not ship.sunk]
            if own and enemies:
                target = min(enemies, key=lambda enemy: min(enemy.position.distance(ship.position) for ship in own))
        if target is None:
            return {"target_id": None, "target_name": None, "projected_target": None, "combos": []}
        if launch is not None:
            combo = self._assist_launch_from_dict(state, side, launch)
            combos = [self._assist_evaluate(state, target, combo)] if combo else []
        else:
            combos = [self._assist_evaluate(state, target, combo) for combo in self._assist_launch_combos(state, side)]
        combos = [combo for combo in combos if combo]
        combos.sort(key=lambda combo: (-combo["expected_hits"], combo["distance"]))
        top = combos[:12]
        best_turn = top[0]["intercept_turn"] if top and top[0]["intercept_hex"] else 0
        projected = self._project_target_position(state, target, best_turn)
        return {
            "target_id": target.id,
            "target_name": target.name,
            "projected_target": {
                "hex": projected.model_dump(mode="json") if projected else None,
                "label": projected.label if projected else None,
                "heading": target.heading,
                "speed": target.current_speed,
                "turns": best_turn,
            },
            "combos": top,
        }

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
            Phase.CONTACT_SETUP: {"contacts"},
            Phase.REINFORCEMENT: {"reinforcements"},
            Phase.MOVEMENT_PLANNING: {"movement", "contact_movement"},
            Phase.TORPEDO_PLANNING: {"torpedoes"},
            Phase.GUNNERY: {"gunnery", "smoke", "smoke_ships", "illumination", "searchlights"},
        }.get(state.phase, set())
        populated = {
            name for name in ("contacts", "reinforcements", "movement", "contact_movement", "torpedoes", "gunnery", "smoke", "smoke_ships", "illumination", "searchlights")
            if getattr(batch, name)
        }
        for name in sorted(populated - allowed_fields):
            errors.append(f"{name} orders are not legal during {state.phase}")
        if state.phase == Phase.CONTACT_SETUP:
            self._validate_contact_setup(state, batch, errors)
        for order in batch.movement if state.phase == Phase.MOVEMENT_PLANNING else []:
            ship = owned.get(order.ship_id)
            if not ship:
                errors.append(f"Movement references non-owned ship {order.ship_id}")
                continue
            try:
                commands = self.movement_commands(order)
                self.validate_movement_commands(commands)
                cost = self.movement_cost(order.plan, commands)
                trajectory, _ = self.movement_trajectory(ship, order.plan, commands)
                if any(self._terrain_impassable(state, position) for position, _ in trajectory):
                    errors.append(f"{order.ship_id}: movement plan enters land")
            except ValueError as error:
                errors.append(f"{order.ship_id}: {error}")
                continue
            minimum, maximum = self._legal_speed_range(ship, state.turn)
            if not minimum <= cost <= maximum:
                errors.append(f"{order.ship_id}: movement cost {cost} outside legal range {minimum}-{maximum}")
            if order.speed is not None and order.speed != cost:
                errors.append(f"{order.ship_id}: declared speed {order.speed} does not match {cost} MF plan")
            turns = [command for command in commands if command != "advance"]
            if ship.turn_limit_degrees == 60 and any(command.endswith("120") for command in turns):
                errors.append(f"{order.ship_id}: rudder damage limits turns to 60 degrees")
            if ship.forced_straight_turns:
                if turns:
                    errors.append(f"{order.ship_id}: rudder/bridge damage requires straight movement")
                if ship.forced_speed is not None and cost != ship.forced_speed:
                    errors.append(f"{order.ship_id}: bridge damage requires original speed {ship.forced_speed}")
            if ship.forced_circle_turns:
                sixty_turns = [command for command in turns if command.endswith("60")]
                if not sixty_turns or len(sixty_turns) != len(turns):
                    errors.append(f"{order.ship_id}: rudder/bridge damage requires a 60-degree circling turn")
                sides = {"port" if "port" in command else "starboard" for command in sixty_turns}
                if len(sides) > 1 or (ship.forced_turn_side and sides and ship.forced_turn_side not in sides):
                    errors.append(f"{order.ship_id}: circling direction must remain {ship.forced_turn_side or 'constant'}")
        if state.phase == Phase.MOVEMENT_PLANNING:
            expected = {ship.id for ship in owned.values() if ship.position}
            submitted = {order.ship_id for order in batch.movement}
            if submitted != expected:
                errors.append(f"Movement plans must cover every active ship; missing={sorted(expected-submitted)}, extra={sorted(submitted-expected)}")
            self._validate_contact_movement(state, batch, errors)
        for order in batch.reinforcements if state.phase == Phase.REINFORCEMENT else []:
            ship = owned.get(order.ship_id)
            if not ship or ship.position is not None or ship.reinforcement_turn != state.turn:
                errors.append(f"Reinforcement references unavailable ship {order.ship_id}")
                continue
            if not state.reinforcement_available:
                errors.append(f"Reinforcement group is not available on turn {state.turn}")
            if not self._reinforcement_entry_legal(state, order.entry_hex):
                errors.append(f"Illegal reinforcement entry hex {order.entry_hex.label}")
            if self._terrain_impassable(state, order.entry_hex):
                errors.append(f"Reinforcement entry hex {order.entry_hex.label} is land")
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
            if attacker.guns_disabled_turns:
                errors.append(f"{order.ship_id}: all guns are disabled this turn")
            if state.options.optional_rules.squalls and self._in_squall(state, attacker.position):
                errors.append(f"{order.ship_id}: ships in squalls may not fire")
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
                elif not self._can_see(state, attacker, target):
                    errors.append(f"{order.ship_id}: cannot see {target.id}")
                elif mount and not self._mount_can_bear(attacker, target, mount.arcs):
                    errors.append(f"{order.ship_id}:{mount.id} cannot bear on {target.id}")
        if state.phase == Phase.GUNNERY:
            optional = state.options.optional_rules
            if batch.illumination and not optional.star_shells:
                errors.append("Star-shell orders require optional rule 9.3")
            if batch.searchlights and not optional.searchlights:
                errors.append("Searchlight orders require optional rule 9.4")
            if (batch.smoke or batch.smoke_ships) and not optional.smoke:
                errors.append("Smoke orders require optional rule 9.7")
            for order in batch.illumination:
                ship = owned.get(order.ship_id)
                mount = next((item for item in ship.gun_mounts if item.id == order.mount_id), None) if ship else None
                if not ship or ship.mfc_destroyed or not mount or mount.destroyed:
                    errors.append(f"{order.ship_id}: cannot fire star shell from {order.mount_id}")
            for order in batch.searchlights:
                ship = owned.get(order.ship_id)
                target = state.ships.get(order.target_id or "") if order.target_id else None
                if not ship or ship.mfc_destroyed:
                    errors.append(f"{order.ship_id}: cannot use searchlight")
                elif order.active and (
                    not target or target.side == batch.side or not ship.position or not target.position
                    or ship.position.distance(target.position) > (14 if ship.side == Side.AXIS else 12)
                ):
                    errors.append(f"{order.ship_id}: illegal searchlight target {order.target_id}")
            smoke_ids = batch.smoke_ships + [order.ship_id for order in batch.smoke if order.deploy]
            for ship_id in smoke_ids:
                ship = owned.get(ship_id)
                if not ship or ship.ship_type not in {"DD", "CL"}:
                    errors.append(f"{ship_id}: only DD or CL may release smoke")
        for order in batch.torpedoes if state.phase == Phase.TORPEDO_PLANNING else []:
            ship = owned.get(order.ship_id)
            if not ship or not ship.torpedo or ship.torpedo.destroyed:
                errors.append(f"{order.ship_id} cannot fire torpedoes")
                continue
            if state.scenario_id == "IBS-S-01" and state.turn < 4 and batch.side == Side.AXIS:
                errors.append("Japanese ships may not launch torpedoes before scenario 1 turn 4")
            if ship.ship_type in {"BB", "BC"} and ship.current_speed >= 4:
                errors.append(f"{order.ship_id}: BB/BC moving at 4 MF or more may not launch torpedoes")
            if state.options.optional_rules.squalls and self._in_squall(state, ship.position):
                errors.append(f"{order.ship_id}: ships in squalls may not launch torpedoes")
            launcher = next((item for item in ship.torpedo_launchers if item.id == order.launcher_id), None)
            if not launcher or launcher.destroyed or launcher.reload_turns_remaining:
                errors.append(f"{order.ship_id}: unavailable torpedo launcher {order.launcher_id}")
                continue
            if order.count > launcher.loaded:
                errors.append(f"{order.ship_id} lacks torpedo ammunition")
            if not order.launch_side or not order.launch_angle:
                errors.append(f"{order.ship_id}: launch_side and launch_angle are required")
            elif FiringArc(order.launch_side) not in launcher.arcs:
                errors.append(f"{order.ship_id}:{launcher.id} cannot launch to {order.launch_side}")
            definition = self.rules.torpedoes.get(ship.torpedo_type or "")
            if not definition or order.setting_index >= len(definition["settings"]):
                errors.append(f"{order.ship_id}: invalid torpedo speed setting {order.setting_index}")
            movement = next(
                (
                    item
                    for batch_item in self._sealed_batches(state, Phase.MOVEMENT_PLANNING)
                    for item in batch_item.movement
                    if item.ship_id == ship.id
                ),
                None,
            )
            if not movement:
                errors.append(f"{order.ship_id}: missing sealed movement plan")
                continue
            commands = self.movement_commands(movement)
            trajectory, _ = self.movement_trajectory(ship, movement.plan, commands)
            if order.launch_at_mf > len(trajectory):
                errors.append(f"{order.ship_id}: launch MF exceeds movement plan")
            else:
                expected_hex = ship.position if order.launch_at_mf == 0 else trajectory[order.launch_at_mf - 1][0]
                if not order.launch_hex or order.launch_hex != expected_hex:
                    errors.append(f"{order.ship_id}: launch_hex does not match its MF position")
                expected_heading = ship.heading if order.launch_at_mf == 0 else trajectory[order.launch_at_mf - 1][1]
                if order.bearing is not None and order.bearing != expected_heading:
                    errors.append(
                        f"{order.ship_id}: bearing {order.bearing} does not match ship heading "
                        f"{expected_heading} at launch MF {order.launch_at_mf}"
                    )
        if state.phase == Phase.TORPEDO_PLANNING:
            launcher_keys = [(order.ship_id, order.launcher_id) for order in batch.torpedoes]
            if len(launcher_keys) != len(set(launcher_keys)):
                errors.append("A torpedo launcher may receive only one launch order per turn")
        return ValidationResult(valid=not errors, errors=errors)

    @staticmethod
    def _legal_speed_range(ship: ShipState, turn: int) -> tuple[int, int]:
        maximum = min(ship.max_speed_for_turn(turn), ship.previous_speed + 2)
        deceleration = 3 if ship.ship_type in {"BB", "BC"} else 5
        minimum = max(0, ship.previous_speed - deceleration)
        if ship.forced_straight_turns and ship.forced_speed is not None:
            return ship.forced_speed, ship.forced_speed
        return minimum, maximum

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
            payload={"secret_side": batch.side.value, "order_batch": batch.model_dump(mode="json")},
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
        if state.phase == Phase.CONTACT_SETUP:
            if set(state.submitted_orders) != {Side.AXIS.value, Side.ALLIES.value}:
                raise ValueError("Both sides must submit hidden contact setup before advancing")
            self._seal_orders(state)
            self._resolve_contact_setup(state)
            state.phase = state.resume_phase or Phase.REINFORCEMENT
            state.resume_phase = None
        elif state.phase == Phase.REINFORCEMENT:
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
            if state.options.optional_rules.squalls:
                self._move_squalls(state)
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
            state.markers = [
                marker
                for marker in state.markers
                if marker.kind == "squall" or marker.expires_turn is None or marker.expires_turn > state.turn
            ]
            self._check_victory(state)
            if state.phase != Phase.COMPLETE:
                state.turn += 1
                state.phase = Phase.REINFORCEMENT
                for ship in state.ships.values():
                    ship.fired = False
                    ship.smoke = False
                    for mount in ship.gun_mounts:
                        mount.fired_this_phase = False
                    for launcher in ship.torpedo_launchers:
                        if launcher.reload_turns_remaining:
                            launcher.reload_turns_remaining -= 1
                            if launcher.reload_turns_remaining == 0 and launcher.reloads_remaining:
                                launcher.loaded = launcher.torpedoes
                                launcher.reloads_remaining -= 1
                                if ship.torpedo:
                                    ship.torpedo.ammo = sum(item.loaded for item in ship.torpedo_launchers)
                                self._event(
                                    state,
                                    "torpedo_launcher_reloaded",
                                    f"{ship.name} {launcher.id} 再装填完成",
                                    payload={"ship_id": ship.id, "launcher_id": launcher.id},
                                    rule=self._rule("IBS-R-08.2.2", 11, "8.2 发射鱼雷"),
                                )
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
                        contacts=source.contacts if state.phase == Phase.CONTACT_SETUP else [],
                        reinforcements=source.reinforcements if state.phase == Phase.REINFORCEMENT else [],
                        movement=source.movement if state.phase == Phase.MOVEMENT_PLANNING else [],
                        contact_movement=source.contact_movement if state.phase == Phase.MOVEMENT_PLANNING else [],
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

    def replay(self, event_log: str | Iterable[GameEvent]) -> GameState:
        """Rebuild state only from the initial event and submitted command events."""
        source_events = list(self.get(event_log).events) if isinstance(event_log, str) else list(event_log)
        if not source_events or source_events[0].type != "game_created":
            raise ValueError("An event log must begin with game_created")
        created = source_events[0].payload
        replay_engine = IronBottomEngine()
        state = replay_engine.reset(
            str(created["scenario_id"]),
            int(created["seed"]),
            GameOptions.model_validate(created["options"]),
            game_id=str(created["game_id"]),
        )
        for event in source_events[1:]:
            if event.type == "orders_submitted":
                raw_batch = event.payload.get("order_batch")
                if raw_batch is None:
                    raise ValueError(f"Event {event.sequence} lacks replayable order_batch")
                result = replay_engine.submit_orders(state.game_id, OrderBatch.model_validate(raw_batch))
                if not result.valid:
                    raise ValueError(f"Replay rejected event {event.sequence}: {result.errors}")
            elif event.type == "phase_changed":
                replay_engine.advance(state.game_id)
        return state.model_copy(deep=True)

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
        program, heading = self._movement_program(ship.position, ship.heading, parsed)
        return [(position, pulse_heading) for position, pulse_heading, _ in program], heading

    def _movement_program(
        self, position: HexCoord, initial_heading: int, commands: list[str]
    ) -> tuple[list[tuple[HexCoord, int, int | None]], int]:
        heading = initial_heading
        trajectory: list[tuple[HexCoord, int, int | None]] = []
        for command in commands:
            if command == "advance":
                try:
                    position = position.neighbor(heading)
                    trajectory.append((position, heading, None))
                except ValueError:
                    trajectory.append((position, heading, heading))
            elif command == "turn_port_60":
                heading = 6 if heading == 1 else heading - 1
            elif command == "turn_starboard_60":
                heading = 1 if heading == 6 else heading + 1
            elif command == "turn_port_120":
                heading = ((heading - 3) % 6) + 1
                trajectory.append((position, heading, None))
            elif command == "turn_starboard_120":
                heading = ((heading + 1) % 6) + 1
                trajectory.append((position, heading, None))
        return trajectory, heading

    @staticmethod
    def commands_to_plan(commands: list[str]) -> str:
        """Compress a command list back into the plan shorthand (1P2S...)."""
        tokens: list[str] = []
        advances = 0
        mapping = {
            "turn_port_60": "P",
            "turn_starboard_60": "S",
            "turn_port_120": "PP",
            "turn_starboard_120": "SS",
        }
        for command in commands:
            if command == "advance":
                advances += 1
            else:
                if advances:
                    tokens.append(str(advances))
                    advances = 0
                tokens.append(mapping[command])
        if advances:
            tokens.append(str(advances))
        return "".join(tokens) if tokens else "0"

    @staticmethod
    def _path_to_commands(position: HexCoord, heading: int, hexes: list[HexCoord]) -> list[str]:
        """Convert a click/drag hex path into movement commands from an explicit
        start state, turning as needed between adjacent steps. 180-degree
        reversals are rejected outright."""
        commands: list[str] = []
        for target in hexes:
            if position.distance(target) != 1:
                raise ValueError(
                    f"Movement path step {position.label} → {target.label} is not adjacent"
                )
            bearing = IronBottomEngine._bearing_between(position, target)
            relative = (bearing - heading) % 6
            if relative == 0:
                commands.append("advance")
            elif relative == 1:
                commands.extend(["turn_starboard_60", "advance"])
            elif relative == 5:
                commands.extend(["turn_port_60", "advance"])
            elif relative == 2:
                commands.extend(["turn_starboard_120", "advance"])
            elif relative == 4:
                commands.extend(["turn_port_120", "advance"])
            else:
                raise ValueError(
                    f"Movement path cannot reverse 180 degrees at {position.label}"
                )
            position = target
            heading = bearing
        return commands

    @staticmethod
    def path_to_commands(ship: ShipState, hexes: list[HexCoord]) -> list[str]:
        """Ship convenience wrapper over _path_to_commands starting from the
        ship's current position and heading."""
        if not ship.position:
            raise ValueError(f"{ship.name} has no position to plan movement from")
        return IronBottomEngine._path_to_commands(ship.position, ship.heading, hexes)

    @staticmethod
    def _turn_side(heading: int, new_heading: int) -> str:
        return "starboard" if (new_heading - heading) % 6 == 1 else "port"

    @staticmethod
    def _forced_constraints(ship: ShipState) -> dict[str, Any]:
        return {
            "turn_limit_degrees": ship.turn_limit_degrees,
            "forced_straight_turns": ship.forced_straight_turns,
            "forced_circle_turns": ship.forced_circle_turns,
            "forced_turn_side": ship.forced_turn_side,
            "forced_speed": ship.forced_speed,
        }

    @staticmethod
    def _movement_expand(
        state: GameState, ship: ShipState,
        position: HexCoord, heading: int, cost: int, last: str | None, turned_flag: bool,
        maximum: int,
    ) -> Iterable[tuple[HexCoord, int, int, str, bool, str]]:
        """单状态合法转移枚举器：`_movement_reachable` 与 `movement_path` 共用。

        逐分支等价于原 `_movement_reachable` 的展开逻辑（首命令 advance、转后必接
        advance、60° 免费、120° 计 1MF、forced/界/陆约束）。产出
        `(new_pos, new_head, new_cost, new_last, new_turned, action)`。
        """
        turn_ok = not ship.forced_straight_turns
        turn_120_ok = turn_ok and ship.turn_limit_degrees != 60 and not ship.forced_circle_turns
        circle_side = ship.forced_turn_side if ship.forced_circle_turns else None
        if cost < maximum:
            try:
                target = position.neighbor(heading)
            except ValueError:
                target = None
            if target is not None and not IronBottomEngine._terrain_impassable(state, target):
                yield target, heading, cost + 1, "advance", turned_flag, "advance"
        if last == "advance" and turn_ok:
            port60 = 6 if heading == 1 else heading - 1
            starboard60 = 1 if heading == 6 else heading + 1
            for new_head, action in (
                (port60, "turn_port_60"),
                (starboard60, "turn_starboard_60"),
            ):
                if circle_side and IronBottomEngine._turn_side(heading, new_head) != circle_side:
                    continue
                yield position, new_head, cost, action, True, action
            if turn_120_ok and cost + 1 <= maximum:
                port120 = ((heading - 3) % 6) + 1
                starboard120 = ((heading + 1) % 6) + 1
                for new_head, action in (
                    (port120, "turn_port_120"),
                    (starboard120, "turn_starboard_120"),
                ):
                    yield position, new_head, cost + 1, action, True, action

    def movement_path(
        self, state: GameState, ship: ShipState,
        target_hex: HexCoord, heading: int | None = None,
    ) -> dict[str, Any]:
        """从舰当前位/航向到 `target_hex`（可选固定末航向）的最短合法命令路径。

        用与 `movement_candidates` 完全相同的状态机（`_movement_expand`）做 0-1 BFS
        （转向=0 成本边进队首、推进=1 成本边进队尾，保证首次弹出的状态即最短路径），
        记录 parent，返回 `{valid, reason, commands, plan, cost, end_hex,
        end_heading}`。终态须落在 `[min,max]` 成本内且末动作合法；`heading` 给定
        时末航向须匹配（不可达则该航向返回 `valid=False`，调用方回退）。纯只读。
        """
        if not ship.position:
            return {"valid": False, "reason": "ship has no position"}
        minimum, maximum = self._legal_speed_range(ship, state.turn)
        start: tuple[Any, ...] = (ship.position, ship.heading, None, False)
        dist: dict[tuple[Any, ...], int] = {start: 0}
        parents: dict[tuple[Any, ...], tuple[Any, ...]] = {}
        parent_actions: dict[tuple[Any, ...], str] = {}
        queue: deque[tuple[Any, ...]] = deque([start])
        while queue:
            key = queue.popleft()
            pos, head, last, turned_flag = key
            cost = dist[key]
            terminal = (
                minimum <= cost <= maximum
                and last in (None, "advance", "turn_port_60", "turn_starboard_60")
                and (not ship.forced_circle_turns or turned_flag)
            )
            if terminal and pos == target_hex and (heading is None or head == heading):
                commands: list[str] = []
                current: tuple[Any, ...] = key
                while current in parents:
                    commands.append(parent_actions[current])
                    current = parents[current]
                commands.reverse()
                return {
                    "valid": True,
                    "reason": None,
                    "commands": commands,
                    "plan": self.commands_to_plan(commands),
                    "cost": cost,
                    "end_hex": pos.label,
                    "end_heading": head,
                }
            for new_pos, new_head, new_cost, new_last, new_turned, action in self._movement_expand(
                state, ship, pos, head, cost, last, turned_flag, maximum
            ):
                new_key = (new_pos, new_head, new_last, new_turned)
                if new_key not in dist or new_cost < dist[new_key]:
                    dist[new_key] = new_cost
                    parents[new_key] = key
                    parent_actions[new_key] = action
                    if new_cost == cost:
                        queue.appendleft(new_key)
                    else:
                        queue.append(new_key)
        return {"valid": False, "reason": "target hex not reachable within legal speed range", "commands": [], "plan": None, "cost": None, "end_hex": None, "end_heading": None}

    def _movement_reachable(
        self,
        state: GameState,
        ship: ShipState,
        position: HexCoord,
        heading: int,
        spent: int,
        has_turned: bool,
    ) -> tuple[list[dict[str, Any]], int, int]:
        """Enumerate every final hex/heading a ship can occupy from a movement
        prefix, walking the exact command-legality state machine:
        first command advance, turns only after advance, a free 60-degree turn
        allowed at the end, 120-degree turns cost 1 MF, cost must fall in the
        legal speed range, land and map-edge block advance. Pure read-only."""
        minimum, maximum = self._legal_speed_range(ship, state.turn)
        finals: dict[HexCoord, dict[int, set[int]]] = {}
        queue: deque[tuple[HexCoord, int, int, str | None, bool]] = deque(
            [(position, heading, spent, None, has_turned)]
        )
        seen: set[tuple[HexCoord, int, int, str | None, bool]] = set()
        while queue:
            pos, head, cost, last, turned_flag = queue.popleft()
            key = (pos, head, cost, last, turned_flag)
            if key in seen:
                continue
            seen.add(key)
            if (
                minimum <= cost <= maximum
                and last in (None, "advance", "turn_port_60", "turn_starboard_60")
                and (not ship.forced_circle_turns or turned_flag)
            ):
                finals.setdefault(pos, {}).setdefault(cost, set()).add(head)
            for new_pos, new_head, new_cost, new_last, new_turned, _action in self._movement_expand(
                state, ship, pos, head, cost, last, turned_flag, maximum
            ):
                queue.append((new_pos, new_head, new_cost, new_last, new_turned))
        reachable = [
            {
                "hex": {"q": pos.q, "r": pos.r},
                "label": pos.label,
                "cost": min(costs),
                "final_headings": sorted(costs[min(costs)]),
            }
            for pos, costs in finals.items()
        ]
        reachable.sort(key=lambda item: item["label"])
        return reachable, minimum, maximum

    def movement_candidates(self, state: GameState, ship: ShipState) -> dict[str, Any]:
        """Full reachable-hex overlay for one owned ship at its current state."""
        forced = self._forced_constraints(ship)
        if not ship.position:
            return {
                "ship_id": ship.id,
                "position": None,
                "heading": ship.heading,
                "min_cost": 0,
                "max_cost": 0,
                "forced": forced,
                "reachable": [],
                "blocked_reason": "ship has no position to move from",
            }
        reachable, minimum, maximum = self._movement_reachable(
            state, ship, ship.position, ship.heading, 0, False
        )
        return {
            "ship_id": ship.id,
            "position": {"q": ship.position.q, "r": ship.position.r},
            "heading": ship.heading,
            "min_cost": minimum,
            "max_cost": maximum,
            "forced": forced,
            "reachable": reachable,
        }

    def movement_preview(
        self,
        state: GameState,
        ship: ShipState,
        commands: list[str] | None = None,
        plan: str | None = None,
        hexes: list[HexCoord] | None = None,
    ) -> dict[str, Any]:
        """Pure read-only snapshot of a movement prefix: trajectory so far, the
        next legal commands, and whether the plan is ready to commit. Exactly one
        of commands/plan/hexes drives the prefix; defaults to the empty plan."""
        def base() -> dict[str, Any]:
            return {
                "ship_id": ship.id,
                "commands": [],
                "plan": "0",
                "cost": 0,
                "valid": False,
                "errors": [],
                "commitable": False,
                "current_hex": None,
                "current_label": None,
                "current_heading": ship.heading if ship.position else None,
                "trajectory": [],
                "min_cost": 0,
                "max_cost": 0,
                "next_options": {"advance": [], "turns": []},
                "reachable": [],
                "forced": self._forced_constraints(ship),
            }

        if not ship.position:
            return base()
        if hexes:
            # drag continuation: hexes are appended to the commands prefix and
            # turned from the prefix's end state, not the ship's real position
            prefix = commands or []
            program, prefix_heading = self._movement_program(ship.position, ship.heading, prefix)
            end_pos = program[-1][0] if program else ship.position
            try:
                continuation = IronBottomEngine._path_to_commands(end_pos, prefix_heading, hexes)
            except ValueError as error:
                result = base()
                result["errors"] = [str(error)]
                return result
            commands = prefix + continuation
        elif commands is None:
            try:
                commands = self.movement_commands(
                    MovementOrder(ship_id=ship.id, plan=plan or "0")
                )
            except ValueError as error:
                result = base()
                result["errors"] = [str(error)]
                return result
        errors: list[str] = []
        try:
            self.validate_movement_commands(commands)
        except ValueError as error:
            errors.append(str(error))
        program, final_heading = self._movement_program(ship.position, ship.heading, commands)
        cost = self.movement_cost("", commands)
        minimum, maximum = self._legal_speed_range(ship, state.turn)
        trajectory = [
            {
                "hex": {"q": pos.q, "r": pos.r},
                "label": pos.label,
                "heading": head,
                "mf": index + 1,
            }
            for index, (pos, head, _shift) in enumerate(program)
        ]
        current_pos = program[-1][0] if program else ship.position
        current_label = current_pos.label
        turns = [command for command in commands if command != "advance"]
        if not errors and not minimum <= cost <= maximum:
            errors.append(f"movement cost {cost} outside legal range {minimum}-{maximum}")
        if not errors and ship.turn_limit_degrees == 60 and any(command.endswith("120") for command in turns):
            errors.append("rudder damage limits turns to 60 degrees")
        if not errors and ship.forced_straight_turns:
            if turns:
                errors.append("rudder/bridge damage requires straight movement")
            if ship.forced_speed is not None and cost != ship.forced_speed:
                errors.append(f"bridge damage requires original speed {ship.forced_speed}")
        if not errors and ship.forced_circle_turns:
            sixty_turns = [command for command in turns if command.endswith("60")]
            if not sixty_turns or len(sixty_turns) != len(turns):
                errors.append("rudder/bridge damage requires a 60-degree circling turn")
            sides = {"port" if "port" in command else "starboard" for command in sixty_turns}
            if len(sides) > 1 or (ship.forced_turn_side and sides and ship.forced_turn_side not in sides):
                errors.append(f"circling direction must remain {ship.forced_turn_side or 'constant'}")
        valid = not errors
        commitable = valid
        next_options: dict[str, Any] = {"advance": [], "turns": []}
        last = commands[-1] if commands else None
        if cost < maximum:
            try:
                target = current_pos.neighbor(final_heading)
            except ValueError:
                target = None
            if target is not None and not self._terrain_impassable(state, target):
                next_options["advance"].append(
                    {
                        "hex": {"q": target.q, "r": target.r},
                        "label": target.label,
                        "heading": final_heading,
                        "cost_delta": 1,
                    }
                )
        if last == "advance" and not ship.forced_straight_turns:
            circle_side = ship.forced_turn_side if ship.forced_circle_turns else None
            port60 = 6 if final_heading == 1 else final_heading - 1
            starboard60 = 1 if final_heading == 6 else final_heading + 1
            port120 = ((final_heading - 3) % 6) + 1
            starboard120 = ((final_heading + 1) % 6) + 1
            for action, new_head, cost_delta in (
                ("turn_port_60", port60, 0),
                ("turn_starboard_60", starboard60, 0),
                ("turn_port_120", port120, 1),
                ("turn_starboard_120", starboard120, 1),
            ):
                legal = True
                reason: str | None = None
                if action.endswith("120"):
                    if ship.turn_limit_degrees == 60:
                        legal, reason = False, "rudder damage limits turns to 60 degrees"
                    elif ship.forced_circle_turns:
                        legal, reason = False, "circling requires 60-degree turns"
                else:
                    if ship.forced_circle_turns and circle_side and IronBottomEngine._turn_side(final_heading, new_head) != circle_side:
                        legal, reason = False, f"circling direction must remain {circle_side}"
                if legal and cost + cost_delta > maximum:
                    legal, reason = False, "exceeds maximum speed"
                next_options["turns"].append(
                    {
                        "action": action,
                        "cost_delta": cost_delta,
                        "heading_after": new_head,
                        "legal": legal,
                        "reason": reason,
                    }
                )
        reachable, _, _ = self._movement_reachable(
            state, ship, current_pos, final_heading, cost, bool(turns)
        )
        return {
            "ship_id": ship.id,
            "commands": commands,
            "plan": self.commands_to_plan(commands),
            "cost": cost,
            "valid": valid,
            "errors": errors,
            "commitable": commitable,
            "current_hex": {"q": current_pos.q, "r": current_pos.r},
            "current_label": current_label,
            "current_heading": final_heading,
            "trajectory": trajectory,
            "min_cost": minimum,
            "max_cost": maximum,
            "next_options": next_options,
            "reachable": reachable,
            "forced": self._forced_constraints(ship),
        }

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

    def _validate_contact_setup(self, state: GameState, batch: OrderBatch, errors: list[str]) -> None:
        markers = {
            marker.id: marker
            for marker in state.markers
            if marker.kind == "contact" and marker.secret_side == batch.side
        }
        submitted_ids = [order.marker_id for order in batch.contacts]
        if len(submitted_ids) != len(set(submitted_ids)):
            errors.append("Duplicate hidden contact setup order")
        if set(submitted_ids) != set(markers):
            errors.append("Hidden contact setup must cover all four owned markers")
        entry_labels = [order.entry_hex.label for order in batch.contacts]
        if len(entry_labels) != len(set(entry_labels)):
            errors.append("Hidden contacts must use distinct entry hexes")
        assigned: list[str] = []
        for order in batch.contacts:
            marker = markers.get(order.marker_id)
            if not marker:
                errors.append(f"Non-owned hidden contact {order.marker_id}")
                continue
            if not self._map_edge(order.entry_hex):
                errors.append(f"Hidden contact {order.marker_id} must start on a map edge")
            if marker.contact_truth == "real" and not order.ship_ids:
                errors.append(f"Real hidden contact {order.marker_id} requires a formation")
            if marker.contact_truth == "decoy" and order.ship_ids:
                errors.append(f"Decoy hidden contact {order.marker_id} may not contain ships")
            assigned.extend(order.ship_ids)
            if order.ship_ids:
                original = [state.contact_reserve_positions.get(ship_id) for ship_id in order.ship_ids]
                if any(position is None for position in original):
                    errors.append(f"{order.marker_id} formation contains a non-owned or unavailable ship")
                else:
                    anchor = original[0]
                    for position in original:
                        q = order.entry_hex.q + position.q - anchor.q  # type: ignore[union-attr]
                        r = order.entry_hex.r + position.r - anchor.r  # type: ignore[union-attr]
                        if not self._coord_on_map(q, r):
                            errors.append(f"{order.marker_id} translated formation leaves the map")
                            break
        expected = {
            ship_id for ship_id in state.contact_reserve_positions
            if state.ships[ship_id].side == batch.side
        }
        if len(assigned) != len(set(assigned)) or set(assigned) != expected:
            errors.append("The two real hidden contacts must partition every owned starting ship exactly once")

    def _validate_contact_movement(self, state: GameState, batch: OrderBatch, errors: list[str]) -> None:
        markers = {
            marker.id: marker
            for marker in state.markers
            if marker.kind == "contact" and marker.secret_side == batch.side and marker.position
        }
        submitted = {order.marker_id for order in batch.contact_movement}
        if submitted != set(markers):
            errors.append(
                f"Contact movement must cover all owned contacts; missing={sorted(set(markers)-submitted)}, "
                f"extra={sorted(submitted-set(markers))}"
            )
        for order in batch.contact_movement:
            marker = markers.get(order.marker_id)
            if not marker:
                continue
            try:
                commands = self.movement_commands(MovementOrder(ship_id=marker.id, plan=order.plan))
                self.validate_movement_commands(commands)
                cost = self.movement_cost(order.plan, commands)
                if cost not in {4, 5}:
                    errors.append(f"{marker.id}: hidden contacts must move at 4 or 5 MF")
                trajectory, _ = self._marker_trajectory(marker, commands)
                if any(self._terrain_impassable(state, position) for position, _ in trajectory):
                    errors.append(f"{marker.id}: hidden contact plan enters land")
            except ValueError as error:
                errors.append(f"{marker.id}: {error}")

    @staticmethod
    def _map_edge(coord: HexCoord) -> bool:
        display_row = coord.r + (coord.q - (coord.q & 1)) // 2
        return coord.q in {0, 33} or display_row in {0, 26}

    @staticmethod
    def _coord_on_map(q: int, r: int) -> bool:
        display_row = r + (q - (q & 1)) // 2
        return 0 <= q <= 33 and 0 <= display_row <= 26

    @staticmethod
    def _terrain_impassable(state: GameState, coord: HexCoord) -> bool:
        return coord.label in state.land_hexes

    @staticmethod
    def _hex_line(origin: HexCoord, target: HexCoord) -> list[HexCoord]:
        distance = origin.distance(target)
        if distance == 0:
            return [origin]

        def cube_round(x: float, y: float, z: float) -> tuple[int, int]:
            rx, ry, rz = round(x), round(y), round(z)
            x_delta, y_delta, z_delta = abs(rx - x), abs(ry - y), abs(rz - z)
            if x_delta > y_delta and x_delta > z_delta:
                rx = -ry - rz
            elif y_delta > z_delta:
                ry = -rx - rz
            else:
                rz = -rx - ry
            return rx, rz

        ox, oz = origin.q, origin.r
        oy = -ox - oz
        tx, tz = target.q, target.r
        ty = -tx - tz
        line: list[HexCoord] = []
        for step in range(distance + 1):
            fraction = step / distance
            q, r = cube_round(
                ox + (tx - ox) * fraction,
                oy + (ty - oy) * fraction,
                oz + (tz - oz) * fraction,
            )
            line.append(HexCoord(q=q, r=r))
        return line

    def _terrain_blocks_sight(
        self, state: GameState, origin: HexCoord, target: HexCoord, *, radar: bool = False
    ) -> bool:
        blockers = (state.land_hexes | state.radar_blocking_hexes) if radar else state.land_hexes
        if not blockers:
            return False
        line = self._hex_line(origin, target)
        if any(coord.label in blockers for coord in line[1:-1]):
            return True
        return bool(
            radar and any(
                HexCoord.from_label(label).distance(target) <= 4
                for label in blockers
            )
        )

    def _resolve_contact_setup(self, state: GameState) -> None:
        markers = {marker.id: marker for marker in state.markers if marker.kind == "contact"}
        for batch in self._sealed_batches(state, Phase.CONTACT_SETUP):
            for order in batch.contacts:
                marker = markers[order.marker_id]
                marker.position = order.entry_hex
                marker.heading = order.heading
                marker.movement_rate = order.speed
                state.contact_formations[marker.id] = list(order.ship_ids)
                if order.ship_ids:
                    anchor = state.contact_reserve_positions[order.ship_ids[0]]
                    state.contact_offsets[marker.id] = {
                        ship_id: (
                            state.contact_reserve_positions[ship_id].q - anchor.q,
                            state.contact_reserve_positions[ship_id].r - anchor.r,
                        )
                        for ship_id in order.ship_ids
                    }
            self._event(
                state,
                "contact_setup_sealed",
                f"{batch.side.value} 隐蔽标记已部署",
                payload={"secret_side": batch.side.value},
                rule=self._rule("IBS-R-09.1", 13, "9.1 隐蔽标记算子"),
            )

    def _marker_trajectory(self, marker: MarkerState, commands: list[str]) -> tuple[list[tuple[HexCoord, int]], int]:
        if not marker.position or not marker.heading:
            return [], marker.heading or 1
        heading = marker.heading
        position = marker.position
        trajectory: list[tuple[HexCoord, int]] = []
        for command in commands:
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

    def _reveal_detected_contacts(self, state: GameState) -> None:
        contacts = [marker for marker in state.markers if marker.kind == "contact" and marker.position]
        detected: set[str] = set()
        for observer in contacts:
            if observer.contact_truth != "real" or not observer.position or not observer.secret_side:
                continue
            radar = state.options.optional_rules.radar and any(
                state.ships[ship_id].radar and not state.ships[ship_id].radar_destroyed
                for ship_id in state.contact_formations.get(observer.id, [])
            )
            visibility = int(state.visibility[observer.secret_side.value])
            for target in contacts:
                if target.secret_side == observer.secret_side or not target.position:
                    continue
                if radar or observer.position.distance(target.position) <= visibility:
                    detected.add(target.id)
        for marker_id in sorted(detected):
            marker = next((item for item in state.markers if item.id == marker_id), None)
            if marker:
                self._reveal_contact(state, marker)

    def _reveal_contact(self, state: GameState, marker: MarkerState) -> None:
        formation = state.contact_formations.get(marker.id, [])
        if marker.contact_truth == "real" and marker.position:
            for ship_id in formation:
                ship = state.ships[ship_id]
                dq, dr = state.contact_offsets[marker.id][ship_id]
                ship.position = HexCoord(q=marker.position.q + dq, r=marker.position.r + dr)
                ship.heading = marker.heading or ship.heading
                ship.current_speed = marker.movement_rate or 4
                ship.previous_speed = ship.current_speed
            message = f"真实隐蔽标记 {marker.id} 揭示编队"
        else:
            message = f"假隐蔽标记 {marker.id} 揭示并移除"
        self._event(
            state,
            "contact_revealed",
            message,
            payload={"marker_id": marker.id, "truth": marker.contact_truth, "ship_ids": formation},
            rule=self._rule("IBS-R-09.1", 13, "9.1 隐蔽标记算子"),
        )
        state.markers = [item for item in state.markers if item.id != marker.id]

    @staticmethod
    def _translated_hex(coord: HexCoord, dq: int, dr: int) -> HexCoord:
        translated = HexCoord(q=coord.q + dq, r=coord.r + dr)
        display_row = translated.r + (translated.q - (translated.q & 1)) // 2
        if not 0 <= display_row <= 26:
            raise ValueError("Map-edge world shift would move a counter beyond the opposite edge")
        return translated

    def _shift_world_for_map_edge(
        self,
        state: GameState,
        *,
        moving_ship_id: str,
        heading: int,
        impulse: int,
        ship_paths: dict[str, list[tuple[HexCoord, int, int | None]]],
        contact_paths: dict[str, list[tuple[HexCoord, int]]],
        torpedo_orders: list[TorpedoOrder],
    ) -> None:
        leaving_dq, leaving_dr = HexCoord.direction_delta(heading)
        dq, dr = -leaving_dq, -leaving_dr

        # Validate the complete translation before mutating state.  The
        # printed rule does not define the pathological case where another
        # counter is already on the opposite edge, so it is rejected instead
        # of silently clipping or inventing wrap-around movement.
        current_coords: list[HexCoord] = [
            ship.position
            for ship in state.ships.values()
            if ship.id != moving_ship_id and not ship.sunk and ship.position
        ]
        current_coords.extend(track.position for track in state.torpedo_tracks)
        current_coords.extend(wreck.position for wreck in state.wrecks)
        current_coords.extend(marker.position for marker in state.markers if marker.position)
        for coord in current_coords:
            self._translated_hex(coord, dq, dr)

        for ship in state.ships.values():
            if ship.id != moving_ship_id and not ship.sunk and ship.position:
                ship.position = self._translated_hex(ship.position, dq, dr)
        for track in state.torpedo_tracks:
            track.position = self._translated_hex(track.position, dq, dr)
        for wreck in state.wrecks:
            wreck.position = self._translated_hex(wreck.position, dq, dr)
        for marker in state.markers:
            if marker.position:
                marker.position = self._translated_hex(marker.position, dq, dr)

        for ship_id, path in ship_paths.items():
            if ship_id == moving_ship_id:
                continue
            for index in range(impulse, len(path)):
                position, pulse_heading, shift_heading = path[index]
                path[index] = (
                    self._translated_hex(position, dq, dr),
                    pulse_heading,
                    shift_heading,
                )
        for path in contact_paths.values():
            for index in range(impulse, len(path)):
                position, pulse_heading = path[index]
                path[index] = (self._translated_hex(position, dq, dr), pulse_heading)
        for order in torpedo_orders:
            if order.ship_id != moving_ship_id and order.launch_hex:
                order.launch_hex = self._translated_hex(order.launch_hex, dq, dr)

        self._event(
            state,
            "world_shifted",
            f"{state.ships[moving_ship_id].name} 越过地图边缘：其他全部算子反向平移 1 格",
            payload={
                "moving_ship_id": moving_ship_id,
                "heading": heading,
                "shift": {"dq": dq, "dr": dr},
                "movement_impulse": impulse + 1,
            },
            rule=self._rule("IBS-R-06.1.8", 7, "6.1 移动机制第8条"),
        )

    def _launch_torpedo_order(
        self,
        state: GameState,
        order: TorpedoOrder,
        launch_heading: int,
    ) -> TorpedoTrack | None:
        if not order.launch_hex or not order.launcher_id:
            return None
        ship = state.ships[order.ship_id]
        if ship.sunk or ship.position != order.launch_hex:
            self._event(
                state,
                "torpedo_launch_cancelled",
                f"{ship.name} 未到达计划发射格，鱼雷发射取消",
                payload={"ship_id": ship.id, "planned_hex": order.launch_hex.label},
                rule=self._rule("IBS-R-08.2.2", 11, "8.2 发射鱼雷"),
            )
            return None
        if state.options.optional_rules.squalls and self._in_squall(state, ship.position):
            self._event(
                state,
                "torpedo_launch_cancelled",
                f"{ship.name} 处于雨飑中，鱼雷发射取消",
                payload={"ship_id": ship.id, "reason": "squall"},
                rule=self._rule("IBS-R-09.6", 13, "9.6 雨飑"),
            )
            return None
        launcher = next(item for item in ship.torpedo_launchers if item.id == order.launcher_id)
        definition = self.rules.torpedoes[ship.torpedo_type or ""]
        setting = definition["settings"][order.setting_index]
        heading = self._torpedo_launch_heading(
            launch_heading,
            order.launch_side or "port",
            order.launch_angle or "A",
        )
        anchor_hex = self._torpedo_anchor_hex(
            order.launch_hex, launch_heading, order.launch_angle or "A"
        )
        track = TorpedoTrack(
            id=f"TT-{state.turn}-{ship.id}-{launcher.id}-{len(state.torpedo_tracks)+1}",
            side=ship.side,
            launcher_ship_id=ship.id,
            torpedo_type=ship.torpedo_type or "",
            position=anchor_hex,
            heading=heading,
            speed_cycle=tuple(setting["speed"]),
            range_remaining=int(setting["range"]),
            launched_turn=state.turn,
            salvo_size=order.count,
            launch_position=anchor_hex,
            launch_side=order.launch_side,
            launch_angle=order.launch_angle,
            traversed_hexes=[anchor_hex],
            hidden=state.options.optional_rules.blind_torpedoes,
        )
        state.torpedo_tracks.append(track)
        launcher.loaded -= order.count
        if launcher.loaded == 0 and launcher.reloads_remaining:
            reload_duration = 3 if ship.ship_type in {"DD", "APD"} else 2
            launcher.reload_turns_remaining = reload_duration + 1
        if ship.torpedo:
            ship.torpedo.ammo = sum(item.loaded for item in ship.torpedo_launchers)
        self._event(
            state,
            "torpedo_launched",
            f"{ship.name} {launcher.id} 在 {order.launch_hex.label} 发射鱼雷",
            payload={
                "track_id": track.id,
                "ship_id": ship.id,
                "launcher_id": launcher.id,
                "launch_mf": order.launch_at_mf,
                "launch_hex": order.launch_hex.label,
                "launch_side": order.launch_side,
                "launch_angle": order.launch_angle,
                "heading": heading,
                "setting": order.setting_index,
                "salvo_size": order.count,
            },
            rule=self._rule("IBS-R-08.2.2", 11, "8.2 发射鱼雷"),
        )
        return track

    def _resolve_movement(self, state: GameState) -> None:
        self._resolve_sinking_drift(state)
        movement_orders = {
            order.ship_id: order
            for batch in self._sealed_batches(state, Phase.MOVEMENT_PLANNING)
            for order in batch.movement
        }
        torpedo_orders = [
            order
            for batch in self._sealed_batches(state, Phase.TORPEDO_PLANNING)
            for order in batch.torpedoes
        ]
        contact_orders = {
            order.marker_id: order
            for batch in self._sealed_batches(state, Phase.MOVEMENT_PLANNING)
            for order in batch.contact_movement
        }
        contact_markers = {
            marker.id: marker
            for marker in state.markers
            if marker.kind == "contact" and marker.position and marker.id in contact_orders
        }
        contact_paths: dict[str, list[tuple[HexCoord, int]]] = {}
        contact_headings: dict[str, int] = {}
        for marker_id, marker in contact_markers.items():
            order = contact_orders[marker_id]
            commands = self.movement_commands(MovementOrder(ship_id=marker_id, plan=order.plan))
            trajectory, heading = self._marker_trajectory(marker, commands)
            contact_paths[marker_id] = trajectory
            contact_headings[marker_id] = heading
            marker.movement_rate = self.movement_cost(order.plan, commands)
        paths: dict[str, list[tuple[HexCoord, int, int | None]]] = {}
        final_headings: dict[str, int] = {}
        for ship in state.ships.values():
            if ship.sunk or not ship.position:
                continue
            order = movement_orders.get(ship.id, MovementOrder(ship_id=ship.id, plan="0"))
            commands = self.movement_commands(order)
            if ship.forced_circle_turns and not ship.forced_turn_side:
                turn = next((command for command in commands if command != "advance"), None)
                if turn:
                    ship.forced_turn_side = "port" if "port" in turn else "starboard"
            trajectory, heading = self._movement_program(ship.position, ship.heading, commands)
            paths[ship.id] = trajectory
            final_headings[ship.id] = heading
            ship.current_speed = self.movement_cost(order.plan, commands)
        track_allowance = {
            track.id: track.speed_cycle[(state.turn - track.launched_turn) % 3]
            for track in state.torpedo_tracks
            if not track.contact_ship_ids
        }
        planned_torpedo_allowance = [
            self.rules.torpedoes[state.ships[order.ship_id].torpedo_type or ""]["settings"][order.setting_index]["speed"][0]
            for order in torpedo_orders
        ]
        maximum_impulses = max(
            [len(path) for path in paths.values()]
            + [len(path) for path in contact_paths.values()]
            + list(track_allowance.values())
            + planned_torpedo_allowance
            + [0]
        )
        stopped: set[str] = set()
        moved_tracks: dict[str, int] = {track.id: 0 for track in state.torpedo_tracks}
        movement_trace_start: dict[str, str] = {}
        movement_trace_tracks: dict[str, TorpedoTrack] = {}
        for order in torpedo_orders:
            if order.launch_at_mf != 0:
                continue
            track = self._launch_torpedo_order(state, order, state.ships[order.ship_id].heading)
            if track:
                # IBS-R-08.2.x: a torpedo's first-turn speed is reduced by the
                # MF the launcher already consumed before firing.  At MF 0 this
                # is simply the full first-cycle speed.
                track_allowance[track.id] = max(0, track.speed_cycle[0] - order.launch_at_mf)
                moved_tracks[track.id] = 0
        for impulse in range(maximum_impulses):
            # 6.1.8: when a ship would leave the printed map, keep that ship on
            # its edge hex and translate every other counter in the opposite
            # direction.  Translating the remaining planned coordinates keeps
            # simultaneous movement relative after the reference-map shift.
            edge_attempts = [
                (ship_id, path[impulse][1])
                for ship_id, path in paths.items()
                if ship_id not in stopped and impulse < len(path) and path[impulse][2] is not None
            ]
            for ship_id, heading in sorted(edge_attempts):
                ship = state.ships[ship_id]
                if not ship.position:
                    continue
                try:
                    # An earlier simultaneous map shift may already have made
                    # this movement legal.
                    destination = ship.position.neighbor(heading)
                    paths[ship_id][impulse] = (destination, heading, None)
                    continue
                except ValueError:
                    pass
                self._shift_world_for_map_edge(
                    state,
                    moving_ship_id=ship_id,
                    heading=heading,
                    impulse=impulse,
                    ship_paths=paths,
                    contact_paths=contact_paths,
                    torpedo_orders=torpedo_orders,
                )
            destinations: dict[str, HexCoord] = {}
            for ship_id, path in paths.items():
                ship = state.ships[ship_id]
                if not ship.position:
                    continue  # 上一脉冲沉没：不再参与移动/碰撞结算
                if ship_id in stopped or impulse >= len(path):
                    destinations[ship_id] = ship.position  # type: ignore[assignment]
                else:
                    destinations[ship_id] = path[impulse][0]
            for ship_id, destination in list(destinations.items()):
                if ship_id not in stopped and self._terrain_impassable(state, destination):
                    destinations[ship_id] = state.ships[ship_id].position  # type: ignore[assignment]
                    stopped.add(ship_id)
                    self._event(
                        state,
                        "movement_blocked_by_land",
                        f"{state.ships[ship_id].name} 在 {destination.label} 前停止：陆地不可进入",
                        payload={"ship_id": ship_id, "land_hex": destination.label, "movement_impulse": impulse + 1},
                        rule=self._rule("IBS-R-06.1", 7, "6.1 海上移动"),
                    )
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
            for collision_set in sorted(collision_sets, key=lambda group: sorted(group)):
                ids = sorted(collision_set)
                for left_index, left_id in enumerate(ids):
                    for right_id in ids[left_index + 1:]:
                        if left_id in stopped or right_id in stopped:
                            continue
                        if self._resolve_ship_collision(state, state.ships[left_id], state.ships[right_id]):
                            stopped.update((left_id, right_id))
            wreck_positions = {wreck.position: wreck for wreck in state.wrecks}
            for ship_id, destination in destinations.items():
                if ship_id in stopped or destination not in wreck_positions:
                    continue
                if self._resolve_wreck_collision(state, state.ships[ship_id], wreck_positions[destination]):
                    stopped.add(ship_id)
            for ship_id, position in destinations.items():
                if ship_id not in stopped:
                    state.ships[ship_id].position = position
                    if impulse < len(paths[ship_id]):
                        state.ships[ship_id].heading = paths[ship_id][impulse][1]
            for marker_id, path in contact_paths.items():
                marker = contact_markers[marker_id]
                if marker not in state.markers or not marker.position or impulse >= len(path):
                    continue
                marker.position, marker.heading = path[impulse]
            self._reveal_detected_contacts(state)
            launched_this_impulse: set[str] = set()
            for order in torpedo_orders:
                if order.launch_at_mf != impulse + 1 or not order.launch_hex or not order.launcher_id:
                    continue
                ship = state.ships[order.ship_id]
                launch_heading = paths[ship.id][impulse][1]
                track = self._launch_torpedo_order(state, order, launch_heading)
                if not track:
                    continue
                # First-turn speed is reduced by the launcher's already-spent MF.
                track_allowance[track.id] = max(0, track.speed_cycle[0] - order.launch_at_mf)
                moved_tracks[track.id] = 0
                launched_this_impulse.add(track.id)
            for track in list(state.torpedo_tracks):
                if (
                    track.id in launched_this_impulse
                    or track.contact_ship_ids
                    or track.range_remaining == 0
                    or moved_tracks.get(track.id, 0) >= track_allowance.get(track.id, 0)
                ):
                    continue
                try:
                    next_position = track.position.neighbor(track.heading)
                except ValueError:
                    track.range_remaining = 0
                    continue
                if self._terrain_impassable(state, next_position):
                    track.range_remaining = 0
                    self._event(
                        state,
                        "torpedo_grounded",
                        f"鱼雷航迹 {track.id} 在 {next_position.label} 撞击陆地并移除",
                        payload={"track_id": track.id, "land_hex": next_position.label},
                        rule=self._rule("IBS-R-08.2.3", 11, "8.2 鱼雷移动"),
                    )
                    continue
                movement_trace_start.setdefault(track.id, track.position.label)
                movement_trace_tracks[track.id] = track
                if not track.traversed_hexes:
                    track.traversed_hexes.append(track.position)
                track.position = next_position
                track.traversed_hexes.append(next_position)
                track.range_remaining -= 1
                track.distance_travelled += 1
                moved_tracks[track.id] = moved_tracks.get(track.id, 0) + 1
            # IBS-R-08.2.3: any torpedo and ship sharing a hex is a contact,
            # whether the torpedo moved this impulse or a ship drove into its
            # stationary hex.
            self._check_torpedo_contacts(state)
            state.torpedo_tracks = [
                track for track in state.torpedo_tracks if track.range_remaining > 0 or track.contact_ship_ids
            ]
        for track_id, track in movement_trace_tracks.items():
            full_path = [position.label for position in track.traversed_hexes]
            self._event(
                state,
                "torpedo_moved",
                f"鱼雷航迹 {track.id} 从 {movement_trace_start[track_id]} 沿方向 {track.heading} 移动至 {track.position.label}",
                payload={
                    "track_id": track.id,
                    "launcher_ship_id": track.launcher_ship_id,
                    "start_hex": movement_trace_start[track_id],
                    "end_hex": track.position.label,
                    "heading": track.heading,
                    "salvo_size": track.salvo_size,
                    "distance_travelled": track.distance_travelled,
                    "range_remaining": track.range_remaining,
                    "path": full_path,
                },
                rule=self._rule("IBS-R-08.2.3", 12, "8.2 鱼雷移动"),
            )
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
            if ship.forced_straight_turns:
                ship.forced_straight_turns -= 1
            if ship.forced_circle_turns:
                ship.forced_circle_turns -= 1
                if ship.forced_circle_turns == 0:
                    ship.forced_turn_side = None
            if ship.forced_speed_turns:
                ship.forced_speed_turns -= 1
                if ship.forced_speed_turns == 0:
                    ship.forced_speed = None
        for marker_id, heading in contact_headings.items():
            marker = contact_markers[marker_id]
            if marker not in state.markers:
                continue
            marker.heading = heading
            self._event(
                state,
                "contact_moved",
                f"隐蔽标记 {marker.id} 移动至 {marker.position.label if marker.position else '场外'}",
                payload={"marker_id": marker.id, "position": marker.position.label if marker.position else None},
                rule=self._rule("IBS-R-09.1", 13, "9.1 隐蔽标记算子"),
            )

    def _check_torpedo_contacts(self, state: GameState) -> None:
        """IBS-R-08.2.3: mark any torpedo sharing a hex with an opposing,
        unsunk ship as in contact.  Runs every impulse so a ship that drives
        into a stationary torpedo's hex is detected even when the torpedo does
        not move that impulse."""
        for track in state.torpedo_tracks:
            if track.contact_ship_ids:
                continue
            contacts = [
                ship.id
                for ship in state.ships.values()
                if ship.side != track.side and not ship.sunk and ship.position == track.position
            ]
            if contacts:
                track.contact_ship_ids = contacts
                self._event(
                    state,
                    "torpedo_contact",
                    f"鱼雷 {track.id} 进入目标格 {track.position.label}",
                    payload={"track_id": track.id, "candidate_targets": contacts},
                    rule=self._rule("IBS-R-08.2.3", 12, "8.2 鱼雷攻击过程"),
                )

    def _resolve_gunnery(self, state: GameState) -> None:
        disabled_before = {ship.id for ship in state.ships.values() if ship.guns_disabled_turns}
        batches = self._sealed_batches(state, Phase.GUNNERY)
        self._resolve_optional_gunnery(state, batches)
        orders = [order for batch in batches for order in batch.gunnery]
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
        grouped_attacks: dict[tuple[str, str, str], tuple[ShipState, list[Any], ShipState]] = {}
        for attacker, mount, target in attacks:
            key = (attacker.id, target.id, mount.kind)
            if key not in grouped_attacks:
                grouped_attacks[key] = (attacker, [], target)
            grouped_attacks[key][1].append(mount)
        attacking_ships: dict[str, set[str]] = {}
        targets_per_attacker: dict[str, set[str]] = {}
        for attacker, _, target in grouped_attacks.values():
            attacking_ships.setdefault(target.id, set()).add(attacker.id)
            targets_per_attacker.setdefault(attacker.id, set()).add(target.id)
        prepared: list[tuple[ShipState, list[Any], ShipState, int, dict[str, int], int, float]] = []
        for attacker, mounts, target in grouped_attacks.values():
            distance = attacker.position.distance(target.position)
            if not self._can_see(state, attacker, target):
                self._event(state, "gunnery_rejected", f"{attacker.name} 无法看见 {target.name}", rule=self._rule("IBS-R-08.1", 9, "8.1"))
                continue
            caliber = max(mount.caliber for mount in mounts)
            modifiers = self._gunnery_modifiers(
                state,
                attacker,
                target,
                distance,
                len(attacking_ships[target.id]),
                caliber,
                len(targets_per_attacker[attacker.id]),
            )
            firepower = sum(mount.firepower for mount in mounts)
            if state.scenario_id == "IBS-S-01" and attacker.side == Side.ALLIES:
                firepower = (firepower + 1) // 2
            prepared.append((attacker, mounts, target, distance, modifiers, firepower, caliber))
        # The attack list and all modifiers are frozen before damage is applied: sunk ships still complete this phase's fire.
        for attacker, mounts, target, distance, modifiers, firepower, caliber in prepared:
            modifier = sum(modifiers.values())
            raw, dice = self._roll_d66(state)
            adjusted = d66_adjust(raw, modifier)
            hits = self.rules.hit_count(firepower, adjusted)
            attacker.fired = True
            mount_ids = [mount.id for mount in mounts]
            self._event(
                state,
                "gun_mount_attack",
                f"{attacker.name} {'+'.join(mount_ids)} 炮击 {target.name}：{hits} 发命中",
                payload={
                    "attacker": attacker.id,
                    "attacker_side": attacker.side.value,
                    "mount_id": mount_ids[0] if len(mount_ids) == 1 else "+".join(mount_ids),
                    "mount_ids": mount_ids,
                    "battery_kind": mounts[0].kind,
                    "target": target.id,
                    "target_side": target.side.value,
                    "distance": distance, "modifier": modifier, "firepower": firepower,
                    "modifiers": modifiers, "caliber": caliber, "hits": hits,
                },
                rule=self._rule("IBS-T-GHT", 2, "炮击命中表"),
                dice=DiceRoll(dice=dice, notation="D66", raw=raw, adjusted=adjusted),
            )
            if state.options.optional_rules.malfunction_66 and raw == 66:
                self._resolve_malfunction(state, attacker)
            for _ in range(hits):
                result_roll, result_dice = self._roll_d66(state)
                result = self.rules.gunnery_result(result_roll)
                before = self._damage_snapshot(target)
                self._apply_gunnery_result(state, attacker, target, result_roll, result, distance, caliber)
                damage = self._damage_delta(before, self._damage_snapshot(target))
                self._event(
                    state,
                    "gunnery_result",
                    f"{target.name} 命中结果 {result_roll}",
                    payload={
                        "attacker": attacker.id,
                        "attacker_name": attacker.name,
                        "target": target.id,
                        "target_name": target.name,
                        "result": result,
                        "damage": damage,
                    },
                    rule=self._rule("IBS-T-GHRT", 1, "炮击结果表"),
                    dice=DiceRoll(dice=result_dice, notation="D66", raw=result_roll),
                )
        for ship_id in disabled_before:
            state.ships[ship_id].guns_disabled_turns -= 1

    def _resolve_optional_gunnery(self, state: GameState, batches: list[OrderBatch]) -> None:
        optional = state.options.optional_rules
        if optional.star_shells:
            for order in [item for batch in batches for item in batch.illumination]:
                ship = state.ships[order.ship_id]
                mount = next(item for item in ship.gun_mounts if item.id == order.mount_id)
                mount.fired_this_phase = True
                roll, die = self._roll_d6(state)
                success = roll >= 4
                if success:
                    state.markers.append(
                        MarkerState(
                            id=f"STAR-{state.turn}-{ship.id}-{mount.id}",
                            kind="star_shell",
                            position=order.target_hex,
                            expires_turn=state.turn + 1,
                        )
                    )
                self._event(
                    state,
                    "star_shell_fired",
                    f"{ship.name} 闪光弹检定 {roll}",
                    payload={"ship_id": ship.id, "mount_id": mount.id, "target_hex": order.target_hex.label, "success": success},
                    rule=self._rule("IBS-R-09.3", 13, "9.3 闪光弹"),
                    dice=DiceRoll(dice=[die], notation="1D6", raw=roll),
                )
        if optional.searchlights:
            for order in [item for batch in batches for item in batch.searchlights if item.active and item.target_id]:
                ship = state.ships[order.ship_id]
                state.markers.append(
                    MarkerState(
                        id=f"SEARCH-{state.turn}-{ship.id}",
                        kind="searchlight",
                        ship_id=ship.id,
                        target_ship_id=order.target_id,
                        expires_turn=state.turn,
                    )
                )
                self._event(
                    state,
                    "searchlight_activated",
                    f"{ship.name} 开启探照灯",
                    payload={"ship_id": ship.id, "target_id": order.target_id},
                    rule=self._rule("IBS-R-09.4", 13, "9.4 探照灯"),
                )
        if optional.smoke:
            smoke_ids = {
                ship_id for batch in batches for ship_id in batch.smoke_ships
            } | {
                order.ship_id for batch in batches for order in batch.smoke if order.deploy
            }
            for ship_id in sorted(smoke_ids):
                ship = state.ships[ship_id]
                ship.smoke = True
                state.markers.append(
                    MarkerState(
                        id=f"SMOKE-{state.turn}-{ship.id}",
                        kind="smoke",
                        position=ship.position,
                        ship_id=ship.id,
                        expires_turn=state.turn,
                    )
                )
                self._event(
                    state,
                    "smoke_released",
                    f"{ship.name} 释放烟幕",
                    payload={"ship_id": ship.id, "position": ship.position.label if ship.position else None},
                    rule=self._rule("IBS-R-09.7", 14, "9.7 烟幕"),
                )

    def _resolve_torpedoes(self, state: GameState) -> None:
        resolved_track_ids: set[str] = set()
        for track in [item for item in state.torpedo_tracks if item.contact_ship_ids]:
            attacker = state.ships[track.launcher_ship_id]
            definition = self.rules.torpedoes[track.torpedo_type]
            distance = max(1, track.distance_travelled)
            candidates: list[tuple[int, ShipState, int, list[int], str]] = []
            for target_id in track.contact_ship_ids:
                target = state.ships[target_id]
                roll, dice = self._roll_2d6(state)
                adjusted = roll + self._torpedo_modifier(attacker, target, distance)
                aspect = self._torpedo_track_aspect(track, target)
                candidates.append((adjusted, target, roll, dice, aspect))
            adjusted, target, roll, dice, aspect = max(candidates, key=lambda item: item[0])
            hits = min(self.torpedo_hit_count(aspect, adjusted), track.salvo_size)
            self._event(
                state,
                "torpedo_attack",
                f"{attacker.name} 对 {target.name} 发射鱼雷：{hits} 命中",
                payload={
                    "track_id": track.id,
                    "attacker": attacker.id,
                    "attacker_side": attacker.side.value,
                    "target": target.id,
                    "target_side": target.side.value,
                    "distance": distance,
                    "aspect": aspect,
                    "hits": hits,
                },
                rule=self._rule("IBS-R-08.2", 12, "8.2"),
                dice=DiceRoll(dice=dice, notation="2D6", raw=roll, adjusted=adjusted),
            )
            for _ in range(hits):
                raw_damage_roll, damage_dice = self._roll_2d6(state)
                damage_modifier = int(definition.get("damage_modifier", 0))
                damage_roll = raw_damage_roll + damage_modifier
                effect = self.rules.torpedo_effect(damage_roll, target.displacement_band)
                hull, speed, sunk, fire = parse_effect(effect)
                before = self._damage_snapshot(target)
                self._damage_hull(state, target, target.hull if sunk else hull, "torpedo", attacker)
                self._lose_speed(target, speed)
                if fire or damage_roll == 8:
                    self._add_fire(state, target, attacker)
                damage = self._damage_delta(before, self._damage_snapshot(target))
                self._event(
                    state,
                    "torpedo_result",
                    f"{target.name} 鱼雷效果：{effect}",
                    payload={
                        "track_id": track.id,
                        "attacker": attacker.id,
                        "attacker_name": attacker.name,
                        "target": target.id,
                        "target_name": target.name,
                        "effect": effect,
                        "modifier": damage_modifier,
                        "damage": damage,
                    },
                    rule=self._rule("IBS-T-THDT", 3, "鱼雷与碰撞结果表"),
                    dice=DiceRoll(dice=damage_dice, notation="2D6", raw=raw_damage_roll, adjusted=damage_roll),
                )
            resolved_track_ids.add(track.id)
        state.torpedo_tracks = [track for track in state.torpedo_tracks if track.id not in resolved_track_ids]

    def _torpedo_launch_heading(self, ship_heading: int, side: str, angle: str) -> int:
        relative = int(self.rules.torpedo_launch_directions["relative_heading"][side][angle])
        return ((ship_heading - 1 + relative) % 6) + 1

    def _torpedo_anchor_hex(self, launch_hex: HexCoord, ship_heading: int, angle: str) -> HexCoord:
        """鱼雷算子起点：沿舰船头轴偏移（A/Y 在舰格；B 向船尾外 1 格；X 向船头外 1 格）。

        偏移取朝向以发射时点舰首为准（"朝船头方向/朝船头反方向一格"），与鱼雷行进方向无关。
        锚点越出地图时退回舰发射格。
        """
        offset = int(self.rules.torpedo_launch_directions["launch_anchor"][angle])
        if offset == 0:
            return launch_hex
        direction = ship_heading if offset > 0 else ((ship_heading + 2) % 6) + 1
        try:
            return launch_hex.neighbor(direction)
        except ValueError:
            return launch_hex

    @staticmethod
    def _torpedo_track_aspect(track: TorpedoTrack, target: ShipState) -> str:
        source_bearing = ((track.heading + 2) % 6) + 1
        relative = (source_bearing - target.heading) % 6
        return "bow_stern" if relative in {0, 3} else "broadside"

    def _resolve_fire(self, state: GameState) -> None:
        for ship in state.ships.values():
            for _ in range(ship.fire_markers):
                raw, dice = self._roll_2d6(state)
                did_not_fire = not ship.fired
                modifier = int(self.rules.fire_table["modifiers"]["ship_did_not_fire"]) if did_not_fire else 0
                roll = min(12, raw + modifier)
                ignored = did_not_fire and roll in self.rules.fire_table["modifiers"]["ignore_results_if_ship_did_not_fire"]
                result = {"kind": "no_effect"} if ignored else self.rules.table_2d6(self.rules.fire_results, roll)
                before = self._damage_snapshot(ship)
                if result.get("kind") == "special_damage":
                    self._resolve_special_damage(state, ship, armour_already_penetrated=True)
                self._damage_hull(state, ship, int(result.get("hull", 0)), "fire")
                self._lose_speed(ship, int(result.get("speed_loss", 0)))
                if result.get("secondary"):
                    self._destroy_gun_mounts(state, ship, "secondary", int(result["secondary"]), None, "fire")
                if result.get("primary"):
                    self._destroy_gun_mounts(state, ship, "primary", int(result["primary"]), None, "fire")
                if result.get("extinguish") and (result.get("applies_to") != "US_only" or ship.id.startswith("IBS-U-USN-")):
                    ship.fire_markers = max(0, ship.fire_markers - 1)
                self._event(
                    state,
                    "fire_check",
                    f"{ship.name} 火灾检定 {raw}{' +1' if modifier else ''} = {roll}",
                    payload={
                        "ship_id": ship.id,
                        "target_name": ship.name,
                        "modifier": modifier,
                        "result": result,
                        "ignored_for_no_fire": ignored,
                        "damage": self._damage_delta(before, self._damage_snapshot(ship)),
                    },
                    rule=self._rule("IBS-R-08.1", 10, "8.1 火灾"),
                    dice=DiceRoll(dice=dice, notation="2D6", raw=raw, adjusted=roll),
                )

    def _check_victory(self, state: GameState) -> None:
        if state.turn < state.max_turns:
            return
        if state.scenario_id == "IBS-S-03":
            axis_ships = [ship for ship in state.ships.values() if ship.side == Side.AXIS]
            qualifying = [
                ship for ship in axis_ships
                if ship.sunk or all(speed <= 2 for speed in ship.speed_track)
            ]
            sunk_allies = sum(ship.sunk for ship in state.ships.values() if ship.side == Side.ALLIES)
            if len(qualifying) >= 2:
                state.winner = Side.ALLIES
                state.victory_reason = "英军战略胜利：多艘德军驱逐舰被击沉或减速至2-2-2"
            elif len(qualifying) == 1:
                state.winner = Side.ALLIES
                state.victory_reason = "英军战术胜利：一艘德军驱逐舰被击沉或减速至2-2-2"
            elif sunk_allies >= 2:
                state.winner = Side.AXIS
                state.victory_reason = "德军小型战略胜利：无德舰达到英军目标且击沉至少两艘英舰"
            else:
                state.winner = Side.AXIS
                state.victory_reason = "德军战术胜利：无德舰被击沉或减速至2-2-2"
        elif state.scenario_id == "IBS-S-01":
            margin = state.score[Side.AXIS.value] - state.score[Side.ALLIES.value]
            if abs(margin) >= 4:
                state.winner = Side.AXIS if margin > 0 else Side.ALLIES
                state.victory_reason = f"想定1胜利点领先 {abs(margin)} 分"
            else:
                state.victory_reason = "平局：胜利点差小于4"
        else:
            margin = state.score[Side.AXIS.value] - state.score[Side.ALLIES.value]
            state.winner = Side.AXIS if margin > 0 else (Side.ALLIES if margin < 0 else None)
            state.victory_reason = "想定结束时胜利点领先" if margin else "平局"
        state.phase = Phase.COMPLETE
        self._event(
            state,
            "victory",
            f"{state.winner.value if state.winner else '无胜方'}：{state.victory_reason}",
            rule=self._scenario_rule(f"{state.scenario_id}-VICTORY", 3 if state.scenario_id == "IBS-S-03" else 1, "胜利条件"),
        )

    def _gunnery_modifiers(
        self,
        state: GameState,
        attacker: ShipState,
        target: ShipState,
        distance: int,
        attackers: int,
        caliber: float,
        target_count: int,
    ) -> dict[str, int]:
        values = {
            "range": self.rules.range_modifier("gunnery", distance),
            "target_speed": self.rules.target_speed_modifier("gunnery", target.current_speed),
            "longitudinal": self.rules._range_value(self.rules.modifiers["longitudinal_modifier"], distance)["value"]
            if self._target_aspect(attacker, target) == "bow_stern" else 0,
            "caliber_target": self._caliber_target_modifier(caliber, target.ship_type),
            "fire_control_destroyed": int(self.rules.modifiers["other"]["mfc_destroyed"])
            if attacker.mfc_destroyed else 0,
            "additional_attackers": max(0, attackers - 1)
            * int(self.rules.modifiers["other"]["each_additional_attacker"]),
            "multiple_targets": int(self.rules.modifiers["other"]["each_additional_target"])
            if target_count > 1 else 0,
            "target_on_fire": int(self.rules.modifiers["other"]["target_on_fire"])
            if target.fire_markers else 0,
        }
        radar = state.options.optional_rules.radar and distance > int(state.visibility[attacker.side.value]) and attacker.radar
        star_shell = state.options.optional_rules.star_shells and any(
            marker.kind == "star_shell" and marker.expires_turn == state.turn and marker.position
            and target.position and marker.position.distance(target.position) <= 2
            for marker in state.markers
        )
        values["radar_or_star_shell"] = (
            int(self.rules.modifiers["optional"]["star_shell_or_radar_illumination"])
            if radar or star_shell else 0
        )
        if state.options.optional_rules.searchlights:
            if any(marker.kind == "searchlight" and marker.target_ship_id == target.id for marker in state.markers):
                values["target_searchlit"] = int(self.rules.modifiers["optional"]["target_searchlit"])
            if any(marker.kind == "searchlight" and marker.ship_id == attacker.id for marker in state.markers):
                values["searchlight_user"] = int(self.rules.modifiers["optional"]["searchlight_user"])
        values["through_smoke"] = (
            int(self.rules.modifiers["optional"]["through_smoke"])
            if state.options.optional_rules.smoke and (target.smoke or attacker.smoke) else 0
        )
        return values

    def _gunnery_modifier(
        self, state: GameState, attacker: ShipState, target: ShipState, distance: int, attackers: int,
        caliber: float | None = None, target_count: int = 1,
    ) -> int:
        return sum(self._gunnery_modifiers(
            state, attacker, target, distance, attackers, caliber or attacker.primary.caliber, target_count
        ).values())

    def _caliber_target_modifier(self, caliber: float, ship_type: str) -> int:
        target_group = "BB_BC" if ship_type in {"BB", "BC"} else (
            "CA" if ship_type == "CA" else ("CL_AV" if ship_type in {"CL", "AV"} else "DD_APD")
        )
        for label, row in self.rules.modifiers["gunnery_caliber_target_modifier"]["rows"].items():
            lower, upper = (float(value) for value in label.split("-"))
            if lower <= caliber <= upper:
                columns = self.rules.modifiers["gunnery_caliber_target_modifier"]["columns"]
                return int(row[columns.index(target_group)])
        return 0

    def _torpedo_modifier(self, attacker: ShipState, target: ShipState, distance: int) -> int:
        modifier = self.rules.range_modifier("torpedo", distance, japanese=attacker.id.startswith("IBS-U-IJN-"))
        modifier += self.rules.target_speed_modifier("torpedo", target.current_speed)
        return modifier

    @staticmethod
    def _target_aspect(attacker: ShipState, target: ShipState) -> str:
        if not attacker.position or not target.position:
            return "broadside"
        bearing = IronBottomEngine._bearing_between(target.position, attacker.position)
        return "bow_stern" if (bearing - target.heading) % 6 in {0, 3} else "broadside"

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
                    self._destroy_gun_mounts(state, target, "primary", 1, self._result_mount_position(item), "gunnery")
                elif item == "secondary":
                    self._destroy_gun_mounts(state, target, "secondary", 1, None, "gunnery")
            return
        if isinstance(result, str):
            if result.startswith("primary"):
                self._destroy_gun_mounts(state, target, "primary", 1, self._result_mount_position(result), "gunnery")
            return
        if isinstance(result, dict):
            if "hull_by_ship_type" in result:
                group = "BB_BC" if target.ship_type in {"BB", "BC"} else (
                    "AV_CA_CL" if target.ship_type in {"AV", "CA", "CL"} else "other"
                )
                group = group if group in result["hull_by_ship_type"] else "other"
                self._damage_hull(state, target, int(result["hull_by_ship_type"][group]), "gunnery", attacker)
                return
            armour = target.belt_armor
            if any(key.startswith("primary") for key in result):
                armour = target.primary_armor
            elif "secondary" in result:
                armour = target.secondary_armor
            if result.get("armour_check") and not self._penetrates(attacker, armour, distance, caliber):
                return
            self._damage_hull(state, target, int(result.get("hull", 0)), "gunnery", attacker)
            self._lose_speed(target, int(result.get("speed_loss", 0)))
            if result.get("fire_check"):
                self._add_fire(state, target, attacker)
            if "secondary" in result:
                self._destroy_gun_mounts(state, target, "secondary", int(result.get("secondary", 1)), None, "gunnery")
            for key, value in result.items():
                if key.startswith("primary"):
                    self._destroy_gun_mounts(
                        state, target, "primary", int(value), self._result_mount_position(key), "gunnery"
                    )

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
        before = self._damage_snapshot(target)
        penetrated = True
        if result.get("armour_check") and not armour_already_penetrated:
            penetrated = bool(
                attacker and distance is not None and self._penetrates(attacker, target.belt_armor, distance, caliber)
            )
        bridge_penetrated = True
        if result.get("bridge_armour_check") and not armour_already_penetrated:
            bridge_penetrated = bool(
                attacker and distance is not None and self._penetrates(attacker, target.bridge_armor, distance, caliber)
            )
        if result.get("radar"):
            target.radar_destroyed = True
        if penetrated:
            if "effect" in result:
                hull, speed, sunk, fire = parse_effect(result["effect"])
                percent = re.search(r"-(25|50|100)%", result["effect"])
                if percent:
                    speed = target.initial_max_speed * int(percent.group(1)) // 100
                self._damage_hull(state, target, target.hull if sunk else hull, "special_damage", attacker)
                self._lose_speed(target, speed)
                if fire:
                    self._add_fire(state, target, attacker)
            else:
                self._damage_hull(state, target, target.hull if result.get("sunk") else int(result.get("hull", 0)), "special_damage", attacker)
                self._lose_speed(target, int(result.get("speed_loss", 0)))
                fire = int(result.get("fire", 0))
                if result.get("ignore_fire_if_no_aircraft") and not target.aircraft:
                    fire = 0
                if result.get("torpedo_launcher_hit") and (not target.torpedo or not target.torpedo.ammo):
                    fire = 0
                self._add_fire(state, target, attacker, fire)
                if result.get("fire_control"):
                    target.mfc_destroyed = True
                if result.get("captain_killed") and not result.get("bridge_hit"):
                    target.captain_status = "killed"
                elif result.get("captain_wounded") and target.captain_status != "killed":
                    target.captain_status = "wounded"
                if result.get("all_guns_disabled_turns"):
                    target.guns_disabled_turns = max(
                        target.guns_disabled_turns, int(result["all_guns_disabled_turns"])
                    )
                if result.get("primary"):
                    self._destroy_gun_mounts(state, target, "primary", int(result["primary"]), None, "special_damage")
                if result.get("secondary"):
                    self._destroy_gun_mounts(state, target, "secondary", int(result["secondary"]), None, "special_damage")
                if result.get("torpedo_launcher_hit"):
                    self._destroy_torpedo_launchers(state, target, int(result["torpedo_launcher_hit"]), "special_damage")
                if result.get("rudder_hit"):
                    target.rudder_destroyed = True
                if result.get("future_turn_limit_degrees"):
                    target.turn_limit_degrees = int(result["future_turn_limit_degrees"])
                if result.get("straight_turns"):
                    target.forced_straight_turns = max(target.forced_straight_turns, int(result["straight_turns"]))
                if result.get("circle_turns") and not result.get("bridge_hit"):
                    target.forced_circle_turns = max(target.forced_circle_turns, int(result["circle_turns"]))
                if result.get("fire_control"):
                    target.mfc_destroyed = True
            if result.get("bridge_hit") and bridge_penetrated:
                target.bridge_destroyed = True
                if result.get("hold_turn_degrees"):
                    target.turn_limit_degrees = int(result["hold_turn_degrees"])
                if result.get("circle_turns"):
                    target.forced_circle_turns = max(target.forced_circle_turns, int(result["circle_turns"]))
                if result.get("next_turn_straight_at_original_speed"):
                    target.forced_straight_turns = max(target.forced_straight_turns, 1)
                    target.forced_speed = target.previous_speed
                    target.forced_speed_turns = 1
                if result.get("captain_killed"):
                    target.captain_status = "killed"
                elif result.get("captain_wounded") and target.captain_status != "killed":
                    target.captain_status = "wounded"
            additional = result.get("additional")
            if additional in {"primary_1", "primary_1_secondary_1"}:
                self._destroy_gun_mounts(state, target, "primary", 1, None, "special_damage")
            if additional in {"secondary_1", "primary_1_secondary_1"}:
                self._destroy_gun_mounts(state, target, "secondary", 1, None, "special_damage")
        self._event(
            state,
            "special_damage",
            f"{target.name} 特殊损伤 {roll}",
            payload={
                "attacker": attacker.id if attacker else None,
                "attacker_name": attacker.name if attacker else None,
                "target": target.id,
                "target_name": target.name,
                "result": roll,
                "effect": result,
                "penetrated": penetrated,
                "bridge_penetrated": bridge_penetrated,
                "damage": self._damage_delta(before, self._damage_snapshot(target)),
            },
            rule=self._rule("IBS-T-SPECIAL", 4, "特殊伤害表"),
            dice=DiceRoll(dice=dice, notation="D66", raw=roll),
        )

    def _resolve_malfunction(self, state: GameState, attacker: ShipState) -> None:
        roll, dice = self._roll_2d6(state)
        result = self.rules.table_2d6(self.rules.malfunction_results, roll)
        if result.get("destroy_random_primary"):
            self._destroy_gun_mounts(state, attacker, "primary", 1, None, "malfunction", random_choice=True)
        if result.get("power_failure_turns"):
            attacker.guns_disabled_turns = max(
                attacker.guns_disabled_turns, int(result["power_failure_turns"])
            )
        if result.get("destroy_random_secondary"):
            self._destroy_gun_mounts(state, attacker, "secondary", 1, None, "malfunction", random_choice=True)
        if result.get("fire") or (result.get("fire_if_aircraft_aboard") and attacker.aircraft):
            self._add_fire(state, attacker)
        if result.get("special_damage"):
            self._resolve_special_damage(state, attacker, armour_already_penetrated=True)
        self._event(
            state,
            "malfunction",
            f"{attacker.name} 发生 66 故障：{roll}",
            payload={"ship_id": attacker.id, "result": result},
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
    def _result_mount_position(label: str) -> MountPosition | None:
        if label.endswith("_bow"):
            return MountPosition.BOW
        if label.endswith("_mid"):
            return MountPosition.MIDSHIPS
        if label.endswith("_stern"):
            return MountPosition.STERN
        return None

    def _destroy_gun_mounts(
        self,
        state: GameState,
        ship: ShipState,
        kind: str,
        count: int,
        position: MountPosition | None,
        cause: str,
        random_choice: bool = False,
    ) -> list[str]:
        destroyed: list[str] = []
        for _ in range(count):
            candidates = [
                mount for mount in ship.gun_mounts
                if mount.kind == kind and not mount.destroyed and (position is None or mount.position == position)
            ]
            if not candidates:
                break
            chosen = candidates[0]
            dice_roll = None
            if random_choice and len(candidates) > 1:
                roll, die = self._roll_d6(state)
                chosen = candidates[(roll - 1) % len(candidates)]
                dice_roll = DiceRoll(dice=[die], notation="1D6", raw=roll)
            chosen.destroyed = True
            destroyed.append(chosen.id)
            self._event(
                state,
                "gun_mount_destroyed",
                f"{ship.name} {chosen.id} 被摧毁",
                payload={"ship_id": ship.id, "mount_id": chosen.id, "kind": kind, "cause": cause},
                rule=self._rule("IBS-T-GHRT", 1, "炮击结果表"),
                dice=dice_roll,
            )
        operational = [mount for mount in ship.gun_mounts if mount.kind == kind and not mount.destroyed]
        aggregate = ship.primary if kind == "primary" else ship.secondary
        if aggregate:
            aggregate.destroyed = not operational
        return destroyed

    def _destroy_torpedo_launchers(
        self, state: GameState, ship: ShipState, count: int, cause: str
    ) -> list[str]:
        destroyed: list[str] = []
        for launcher in [item for item in ship.torpedo_launchers if not item.destroyed][:count]:
            launcher.destroyed = True
            launcher.loaded = 0
            launcher.reloads_remaining = 0
            launcher.reload_turns_remaining = 0
            destroyed.append(launcher.id)
            self._event(
                state,
                "torpedo_launcher_destroyed",
                f"{ship.name} {launcher.id} 被摧毁",
                payload={"ship_id": ship.id, "launcher_id": launcher.id, "cause": cause},
                rule=self._rule("IBS-T-SPECIAL", 4, "特殊伤害表"),
            )
        if ship.torpedo:
            ship.torpedo.ammo = sum(item.loaded for item in ship.torpedo_launchers)
            ship.torpedo.destroyed = not any(not item.destroyed for item in ship.torpedo_launchers)
        return destroyed

    @staticmethod
    def _relative_aspect(origin: HexCoord, heading: int, target: HexCoord) -> FiringArc:
        """目标相对舰首的射界扇区（规则 8.1a 中心连线方位）。`_mount_can_bear` 与
        射界热力图共用同一几何，避免两处方位/扇区判定漂移。"""
        bearing = IronBottomEngine._bearing_between(origin, target)
        relative = (bearing - heading) % 6
        return {
            0: FiringArc.BOW,
            1: FiringArc.STARBOARD,
            2: FiringArc.STARBOARD,
            3: FiringArc.STERN,
            4: FiringArc.PORT,
            5: FiringArc.PORT,
        }[relative]

    @staticmethod
    def _mount_can_bear(attacker: ShipState, target: ShipState, arcs: Iterable[FiringArc]) -> bool:
        if not attacker.position or not target.position:
            return False
        return IronBottomEngine._relative_aspect(attacker.position, attacker.heading, target.position) in arcs

    @staticmethod
    def _bearing_between(origin: HexCoord, target: HexCoord) -> int:
        # 方位 = 与"射击格中心→目标格中心"连线最接近的六方向（规则 8.1a 中心连线）。
        # 在 flat-top odd-q 渲染下按屏幕空间角度计算，与玩家所见一致；旧的"最近邻格"
        # 近似在错位网格上会误判约四成目标（例如正前方的目标被归为左舷 60°），
        # 导致射界与纵射判定错误。相邻格时两种算法结果完全相同（逐格移动不受影响）。
        dq = target.q - origin.q
        dr = target.r - origin.r
        dx = dq * 1.5
        dy = (dr + dq / 2.0) * math.sqrt(3.0)
        angle = math.degrees(math.atan2(dy, dx))
        # 舰首朝向的屏幕角度：heading 1..6 分别为 330/30/90/150/210/270 度。
        return min(
            range(1, 7),
            key=lambda heading: abs(((330 + (heading - 1) * 60) % 360 - angle + 180) % 360 - 180),
        )

    def _damage_hull(
        self, state: GameState, ship: ShipState, amount: int, cause: str, attacker: ShipState | None = None
    ) -> int:
        if amount <= 0 or ship.sunk:
            return 0
        before = ship.hull
        ship.hull = max(0, ship.hull - amount)
        actual = before - ship.hull
        state.hull_damage_taken[ship.side.value] += actual
        if state.scenario_id == "IBS-S-01":
            state.score[ship.side.opponent.value] = state.hull_damage_taken[ship.side.value] // 3
        elif state.scenario_id not in {"IBS-S-03"}:
            state.score[ship.side.opponent.value] += actual
        if ship.hull == 0:
            ship.sunk = True
            ship.sinking_turn = state.turn
            ship.sinking_drift_pending = bool(ship.position and ship.previous_speed > 0)
            sinking_position = ship.position
            if state.scenario_id not in {"IBS-S-01", "IBS-S-03"}:
                state.score[ship.side.opponent.value] += ship.vp
            attacker_id = ship.fire_source_attacker if cause == "fire" else (attacker.id if attacker else None)
            self._event(
                state,
                "ship_sunk",
                f"{ship.name} 沉没" + ("，等待下一回合漂移" if ship.sinking_drift_pending else "于原地"),
                payload={
                    "ship_id": ship.id,
                    "cause": cause,
                    "drift_pending": ship.sinking_drift_pending,
                    "attacker": attacker_id,
                    "attacker_name": state.ships[attacker_id].name if attacker_id else None,
                    "position": sinking_position.label if sinking_position else None,
                },
                rule=self._rule("IBS-R-08.1-F1", 10, "8.1 f.1 船体损伤与沉没"),
            )
            if sinking_position and not ship.sinking_drift_pending:
                self._place_sinking_wreck(state, ship, sinking_position, drifted=False)
        return actual

    def _place_sinking_wreck(
        self, state: GameState, ship: ShipState, position: HexCoord, *, drifted: bool
    ) -> None:
        if not any(wreck.source_ship_id == ship.id for wreck in state.wrecks):
            state.wrecks.append(
                WreckState(id=f"WRECK-{ship.id}", position=position, source_ship_id=ship.id)
            )
        ship.position = None
        ship.sinking_drift_pending = False
        self._event(
            state,
            "sinking_marker_placed",
            f"{ship.name} {'向舰首漂移一格后' if drifted else ''}移出游戏并放置沉没标记",
            payload={"ship_id": ship.id, "position": position.label, "drifted": drifted},
            rule=self._rule("IBS-R-08.1-F1", 10, "8.1 f.1 船体损伤与沉没"),
        )

    def _resolve_sinking_drift(self, state: GameState) -> None:
        for ship in state.ships.values():
            if (
                not ship.sinking_drift_pending
                or ship.sinking_turn is None
                or state.turn <= ship.sinking_turn
                or not ship.position
            ):
                continue
            try:
                position = ship.position.neighbor(ship.heading)
            except ValueError:
                # The sinking counter itself remains on the last printed edge
                # hex; it is then replaced by the wreck marker.
                position = ship.position
            self._place_sinking_wreck(state, ship, position, drifted=True)

    def _resolve_ship_collision(self, state: GameState, left: ShipState, right: ShipState) -> bool:
        check, die = self._roll_d6(state)
        self._event(
            state,
            "collision_check",
            f"{left.name}与{right.name}碰撞检定 {check}",
            payload={"ships": [left.id, right.id], "collided": check >= 5},
            rule=self._rule("IBS-R-06.4", 8, "6.4 碰撞"),
            dice=DiceRoll(dice=[die], notation="1D6", raw=check),
        )
        if check < 5:
            return False
        for ship, other in ((left, right), (right, left)):
            modifier = self._collision_modifier(ship, other.ship_type)
            if left.current_speed <= 2 and right.current_speed <= 2:
                modifier += int(self.rules.modifiers["collision_modifier"]["both_moved_2mf_or_less"])
            self._apply_collision_damage(state, ship, modifier, other.id)
        return True

    def _resolve_wreck_collision(self, state: GameState, ship: ShipState, wreck: WreckState) -> bool:
        check, die = self._roll_d6(state)
        self._event(
            state,
            "collision_check",
            f"{ship.name}与船骸碰撞检定 {check}",
            payload={"ship_id": ship.id, "wreck_id": wreck.id, "collided": check >= 5},
            rule=self._rule("IBS-R-06.4", 8, "6.4 碰撞"),
            dice=DiceRoll(dice=[die], notation="1D6", raw=check),
        )
        if check < 5:
            return False
        self._apply_collision_damage(state, ship, self._collision_modifier(ship, "wreck"), wreck.id)
        return True

    def _collision_modifier(self, ship: ShipState, other_type: str) -> int:
        own = "BB_BC" if ship.ship_type in {"BB", "BC"} else (
            "CA_CL_AV" if ship.ship_type in {"CA", "CL", "AV"} else "DD_APD"
        )
        other = "wreck" if other_type == "wreck" else (
            "BB_BC" if other_type in {"BB", "BC"} else (
                "CA_CL_AV" if other_type in {"CA", "CL", "AV"} else "DD_APD"
            )
        )
        table = self.rules.modifiers["collision_modifier"]
        return int(table["rows"][own][table["columns"].index(other)])

    def _apply_collision_damage(self, state: GameState, ship: ShipState, modifier: int, obstacle_id: str) -> None:
        raw, dice = self._roll_2d6(state)
        adjusted = raw + modifier
        effect = self.rules.torpedo_effect(adjusted, ship.displacement_band)
        hull, speed, sunk, fire = parse_effect(effect)
        obstacle_ship = state.ships.get(obstacle_id) if obstacle_id in state.ships else None
        self._damage_hull(state, ship, ship.hull if sunk else hull, "collision", obstacle_ship)
        self._lose_speed(ship, speed)
        if fire:
            self._add_fire(state, ship, obstacle_ship)
        self._event(
            state,
            "collision_result",
            f"{ship.name}碰撞结果：{effect}",
            payload={"ship_id": ship.id, "obstacle_id": obstacle_id, "modifier": modifier, "effect": effect},
            rule=self._rule("IBS-T-THDT", 3, "鱼雷与碰撞结果表"),
            dice=DiceRoll(dice=dice, notation="2D6", raw=raw, adjusted=adjusted),
        )

    @staticmethod
    def _lose_speed(ship: ShipState, amount: int) -> int:
        if amount <= 0:
            return 0
        before = ship.speed_damage_crossed
        crossed = list(before)
        for _ in range(amount):
            values = [
                row[crossed[index]] if crossed[index] < len(row) else 0
                for index, row in enumerate(ship.speed_damage_track)
            ]
            maximum = max(values)
            if maximum == 0:
                break
            index = max(index for index, value in enumerate(values) if value == maximum)
            crossed[index] += 1
        ship.speed_damage_crossed = tuple(crossed)  # type: ignore[assignment]
        values = tuple(
            row[crossed[index]] if crossed[index] < len(row) else 0
            for index, row in enumerate(ship.speed_damage_track)
        )
        ship.speed_track = values
        ship.current_speed = min(ship.current_speed, max(values))
        return sum(crossed) - sum(before)

    def _visible_to(self, state: GameState, target: ShipState, side: Side, own_positions: Iterable[HexCoord | None]) -> bool:
        if target.sunk or not target.position:
            return True
        if state.options.optional_rules.squalls and self._in_squall(state, target.position):
            return False
        if any(
            marker.kind == "searchlight" and marker.target_ship_id == target.id
            or marker.kind == "star_shell" and marker.expires_turn == state.turn and marker.position
            and marker.position.distance(target.position) <= 2
            for marker in state.markers
        ):
            return True
        visibility = int(state.visibility[side.value])
        positions = [position for position in own_positions if position]
        if target.fire_markers and any(
            not self._terrain_blocks_sight(state, position, target.position) for position in positions
        ):
            return True
        if any(
            position.distance(target.position) <= visibility
            and not self._terrain_blocks_sight(state, position, target.position)
            for position in positions
        ):
            return True
        if state.options.optional_rules.radar and any(
            ship.side == side and ship.radar and not ship.radar_destroyed and not ship.sunk and ship.position
            and not self._in_squall(state, ship.position)
            and not self._terrain_blocks_sight(state, ship.position, target.position, radar=True)
            for ship in state.ships.values()
        ):
            return True
        return state.options.optional_rules.silhouettes and self._silhouetted(state, target)

    def _can_see(self, state: GameState, attacker: ShipState, target: ShipState) -> bool:
        if state.options.optional_rules.squalls and (
            self._in_squall(state, attacker.position) or self._in_squall(state, target.position)
        ):
            return False
        if not attacker.position or not target.position:
            return False
        illuminated = any(
            marker.kind == "searchlight" and marker.target_ship_id == target.id
            or marker.kind == "star_shell" and marker.expires_turn == state.turn and marker.position
            and marker.position.distance(target.position) <= 2
            for marker in state.markers
        )
        optical_blocked = self._terrain_blocks_sight(state, attacker.position, target.position)
        if not optical_blocked and (
            illuminated or attacker.position.distance(target.position) <= int(state.visibility[attacker.side.value])
        ):
            return True
        if not optical_blocked and state.options.optional_rules.silhouettes and self._silhouetted(state, target):
            return True
        return bool(
            state.options.optional_rules.radar and attacker.radar and not attacker.radar_destroyed
            and not self._terrain_blocks_sight(state, attacker.position, target.position, radar=True)
        )

    def _silhouetted(self, state: GameState, candidate: ShipState) -> bool:
        if not candidate.position:
            return False
        firing_pairs: set[tuple[str, str]] = set()
        for batch in self._sealed_batches(state, Phase.GUNNERY):
            for order in batch.gunnery:
                targets = {item.target_id for item in order.mounts}
                targets.update(target for target in (order.primary_target, order.secondary_target) if target)
                firing_pairs.update((order.ship_id, target_id) for target_id in targets)
        for event in state.events:
            if event.type != "gun_mount_attack" or event.turn != state.turn:
                continue
            firing_pairs.add((str(event.payload.get("attacker")), str(event.payload.get("target"))))
        for attacker_id, target_id in firing_pairs:
            if candidate.id in {attacker_id, target_id}:
                continue
            attacker = state.ships.get(attacker_id)
            target = state.ships.get(target_id)
            if not attacker or not target or not attacker.position or not target.position:
                continue
            if (
                attacker.position.distance(candidate.position) > 0
                and candidate.position.distance(target.position) > 0
                and attacker.position.distance(candidate.position) + candidate.position.distance(target.position)
                == attacker.position.distance(target.position)
            ):
                return True
        return False

    @staticmethod
    def _in_squall(state: GameState, position: HexCoord | None) -> bool:
        return bool(
            position and any(
                marker.kind == "squall" and marker.position and marker.position.distance(position) <= 1
                for marker in state.markers
            )
        )

    def _move_squalls(self, state: GameState) -> None:
        for marker in [item for item in state.markers if item.kind == "squall" and item.position]:
            roll, die = self._roll_d6(state)
            distance = 0 if roll == 1 else (2 if roll == 6 else 1)
            for _ in range(distance):
                try:
                    marker.position = marker.position.neighbor(2)
                except ValueError:
                    marker.position = None
                    break
            self._event(
                state,
                "squall_moved",
                f"雨飑 {marker.id} 移动 {distance} 格",
                payload={"marker_id": marker.id, "distance": distance, "position": marker.position.label if marker.position else None},
                rule=self._rule("IBS-R-09.6", 13, "9.6 雨飑"),
                dice=DiceRoll(dice=[die], notation="1D6", raw=roll),
            )
        state.markers = [marker for marker in state.markers if marker.position or marker.kind != "squall"]

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
