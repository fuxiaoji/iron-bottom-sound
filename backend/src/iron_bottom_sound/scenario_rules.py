from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Callable

from .data import STRUCTURED, load_scenario
from .models import GameState, HexCoord, Side


def _display_row(coord: HexCoord) -> int:
    """奇 q 偏移布局下的显示行（越大越靠南）。"""
    return coord.r + (coord.q - (coord.q & 1)) // 2


@dataclass(frozen=True)
class ScenarioRuleSet:
    """Executable scenario exceptions loaded from the scenario definition.

    The generic engine delegates only the places where a scenario may override
    a base rule.  This keeps fan-expansion tables and victory arithmetic out of
    the already large engine module.

    想定特例分两层：``scenario_rules``（引擎已识别的 kind 分支）与
    ``special_rule_kinds``（数据驱动的通用规则条目：回合限制、编制修改、
    骰点/火力修正、移动约束、能见度日程、警戒状态、暴风雨格、胜利判定）。
    """

    scenario_id: str
    definition: dict
    gunnery_extension: tuple[dict[str, str], ...] = ()

    # ------------------------------------------------------------------ kinds
    def kinds(self, kind: str) -> list[dict[str, Any]]:
        return [item for item in self.definition.get("special_rule_kinds", []) if item.get("kind") == kind]

    def first_kind(self, kind: str) -> dict[str, Any] | None:
        entries = self.kinds(kind)
        return entries[0] if entries else None

    # ------------------------------------------------------- turn restrictions
    def turn_restriction_reason(self, side_value: str, turn: int, action: str) -> str | None:
        """想定禁止某侧在第 turn 回合执行 action（gunnery/torpedo）时给出原因。"""
        for item in self.kinds("turn_restriction"):
            if (
                side_value in item.get("sides", [])
                and turn in item.get("turns", [])
                and action in item.get("actions", [])
            ):
                return str(item.get("reason") or f"想定特例 {item.get('id')}：该回合禁止{action}")
        return None

    # ------------------------------------------------------------ dice modifier
    def torpedo_roll_bonus(self, side_value: str, turn: int) -> int:
        total = 0
        for item in self.kinds("torpedo_roll_bonus"):
            if side_value in item.get("sides", []) and turn in item.get("turns", []):
                total += int(item.get("bonus", 0))
        return total

    def gunnery_situation_modifier(self, attacker_pos: HexCoord | None, target_pos: HexCoord | None) -> int:
        """按射向生效的炮击修正（如 S-14 月光下向南射击 -2）。"""
        total = 0
        for item in self.kinds("gunnery_direction_modifier"):
            direction = item.get("toward")
            if direction == "south":
                if attacker_pos and target_pos and _display_row(target_pos) > _display_row(attacker_pos):
                    total += int(item.get("modifier", 0))
        return total

    def firepower_multiplier(
        self, side_value: str, ship_type: str, caliber: float, direction: str
    ) -> tuple[float, bool] | None:
        """返回 (系数, 是否向上取整)；不匹配返回 None。

        ``unless_direction`` 命中时该条目豁免（S-04：向东射击不受陆地火控影响）。
        """
        for item in self.kinds("firepower_multiplier"):
            if side_value not in item.get("sides", []):
                continue
            if item.get("ship_types") and ship_type not in item["ship_types"]:
                continue
            caliber_min = float(item.get("caliber_min", 0))
            caliber_max = float(item.get("caliber_max", 999))
            if not (caliber_min <= caliber <= caliber_max):
                continue
            if item.get("unless_direction") and item["unless_direction"] == direction:
                continue
            return float(item.get("factor", 1)), bool(item.get("ceil", False))
        return None

    def penetration_blocked(self, side_value: str, turn: int, ship_type: str) -> bool:
        for item in self.kinds("penetration_block"):
            if (
                side_value in item.get("sides", [])
                and turn in item.get("turns", [])
                and (not item.get("ship_types") or ship_type in item["ship_types"])
            ):
                return True
        return False

    # ------------------------------------------------------- setup & movement
    def setup_modifications(self) -> list[dict[str, Any]]:
        return self.kinds("setup_modification")

    def movement_constraints(self) -> list[dict[str, Any]]:
        return self.kinds("movement_constraint")

    def visibility_for_turn(self, side_value: str, turn: int) -> int | None:
        for item in self.kinds("visibility_schedule"):
            if side_value != item.get("side"):
                continue
            schedule = item.get("from_turn", {})
            applicable = [int(t) for t in schedule if turn >= int(t)]
            if applicable:
                return int(schedule[str(max(applicable))])
        return None

    def alert_rule(self) -> dict[str, Any] | None:
        return self.first_kind("alert_states")

    def storm_hexes(self) -> list[str]:
        hexes: list[str] = []
        for item in self.kinds("storm_markers"):
            hexes.extend(str(label) for label in item.get("hexes", []))
        return hexes

    # -------------------------------------------------------------- alert state
    def initial_alerted(
        self, ships: dict[str, Any]
    ) -> set[str]:
        rule = self.alert_rule()
        if not rule:
            return set()
        alerted: set[str] = set()
        initial = rule.get("initial", {})
        if initial.get("sides"):
            alerted.update(ship.id for ship in ships.values() if ship.side.value in initial["sides"])
        alerted.update(ship_id for ship_id in initial.get("ships", []) if ship_id in ships)
        return alerted

    def speed_capped_ships(self, ships: dict[str, Any]) -> set[str]:
        rule = self.alert_rule()
        if not rule:
            return set()
        return {ship_id for ship_id in rule.get("speed_cap_ships", []) if ship_id in ships}

    # ------------------------------------------------------------------ scoring
    def torpedo_expenditure_points(self) -> int:
        entry = self.first_kind("torpedo_expenditure_points")
        return int(entry.get("points_per_torpedo", 0)) if entry else 0

    # ------------------------------------------------------------------ victory
    def _sunk_counts(self, state: GameState, ship_types: set[str], side: Side | None = None) -> int:
        return sum(
            1
            for ship in state.ships.values()
            if ship.sunk and ship.ship_type in ship_types and (side is None or ship.side == side)
        )

    def refresh_score(self, state: GameState) -> None:
        kind = self.definition.get("victory", {}).get("kind")
        if kind != "erma_damage_points":
            return
        scoring = self.definition["victory"]["scoring"]
        result = {Side.AXIS.value: 0, Side.ALLIES.value: 0}
        hull_per = int(scoring["hull_loss"]["per"])
        hull_points = int(scoring["hull_loss"]["points"])
        for victim in Side:
            points = (state.hull_damage_taken[victim.value] // hull_per) * hull_points
            for ship in state.ships.values():
                if ship.side != victim or ship.ship_type != "BB":
                    continue
                points += int(ship.mfc_destroyed) * int(scoring["battleship_fire_control_destroyed"])
                points += int(ship.radar_destroyed) * int(scoring["battleship_radar_destroyed"])
                points += sum(mount.destroyed and mount.kind == "primary" for mount in ship.gun_mounts)
                speed_rule = scoring["battleship_speed_loss"]
                points += (sum(ship.speed_damage_crossed) // int(speed_rule["per"])) * int(speed_rule["points"])
            result[victim.opponent.value] = points
        state.score = result

    def _generic_vp_result(self, state: GameState, margin_threshold: int | None = None) -> tuple[Side | None, str, int]:
        margin = state.score[Side.AXIS.value] - state.score[Side.ALLIES.value]
        threshold = margin_threshold if margin_threshold is not None else 1
        if abs(margin) >= threshold:
            winner = Side.AXIS if margin > 0 else Side.ALLIES
            return winner, f"想定结束胜利点领先 {abs(margin)} 分", 1
        return None, "平局", 1

    def resolve_victory(self, state: GameState) -> tuple[Side | None, str, int]:
        kind = self.definition.get("victory", {}).get("kind")
        if self.scenario_id == "IBS-S-03":
            axis_ships = [ship for ship in state.ships.values() if ship.side == Side.AXIS]
            qualifying = [
                ship for ship in axis_ships if ship.sunk or all(speed <= 2 for speed in ship.speed_track)
            ]
            sunk_allies = sum(ship.sunk for ship in state.ships.values() if ship.side == Side.ALLIES)
            if len(qualifying) >= 2:
                return Side.ALLIES, "英军战略胜利：多艘德军驱逐舰被击沉或减速至2-2-2", 3
            if len(qualifying) == 1:
                return Side.ALLIES, "英军战术胜利：一艘德军驱逐舰被击沉或减速至2-2-2", 3
            if sunk_allies >= 2:
                return Side.AXIS, "德军小型战略胜利：无德舰达到英军目标且击沉至少两艘英舰", 3
            return Side.AXIS, "德军战术胜利：无德舰被击沉或减速至2-2-2", 3
        if self.scenario_id == "IBS-S-01":
            margin = state.score[Side.AXIS.value] - state.score[Side.ALLIES.value]
            if abs(margin) >= 4:
                winner = Side.AXIS if margin > 0 else Side.ALLIES
                return winner, f"想定1胜利点领先 {abs(margin)} 分", 1
            return None, "平局：胜利点差小于4", 1
        if kind == "erma_damage_points":
            self.refresh_score(state)
            margin = state.score[Side.AXIS.value] - state.score[Side.ALLIES.value]
            threshold = int(self.definition["victory"]["win_margin"])
            if abs(margin) >= threshold:
                winner = Side.AXIS if margin > 0 else Side.ALLIES
                return winner, f"二马想定损伤分领先 {abs(margin)} 分（门槛 {threshold}）", 2
            return None, f"平局：损伤分差 {abs(margin)}，未达到 {threshold} 分", 2
        if kind == "bc_kill_comparison":
            # S-07：领先分差达到门槛，且击沉战巡（BC）比对方多，才算胜利。
            margin = state.score[Side.AXIS.value] - state.score[Side.ALLIES.value]
            threshold = int(self.definition.get("victory", {}).get("leader_margin", 5))
            axis_bc_kills = self._sunk_counts(state, {"BC"}, Side.ALLIES)
            allies_bc_kills = self._sunk_counts(state, {"BC"}, Side.AXIS)
            if abs(margin) >= threshold and axis_bc_kills != allies_bc_kills:
                if margin > 0 and axis_bc_kills > allies_bc_kills:
                    return Side.AXIS, f"胜利点领先 {abs(margin)} 分且击沉战巡 {axis_bc_kills} 比 {allies_bc_kills}", 1
                if margin < 0 and allies_bc_kills > axis_bc_kills:
                    return Side.ALLIES, f"胜利点领先 {abs(margin)} 分且击沉战巡 {allies_bc_kills} 比 {axis_bc_kills}", 1
            return None, "平局：未同时满足分差门槛与击沉战巡优势", 1
        if kind == "score_threshold_tiers":
            # S-10：轴心分含鱼雷消耗奖励；50+ 决定性、16+ 战术，其余按条款判盟军。
            expenditure = int(state.scenario_state.get("torpedo_expended", {}).get(Side.AXIS.value, 0))
            axis_score = state.score[Side.AXIS.value] + expenditure * self.torpedo_expenditure_points()
            margin = axis_score - state.score[Side.ALLIES.value]
            tactical = int(self.definition.get("victory", {}).get("tactical_margin", 16))
            decisive = int(self.definition.get("victory", {}).get("decisive_margin", 50))
            axis_ca_sunk = self._sunk_counts(state, {"CA"}, Side.AXIS)
            if axis_ca_sunk >= 3 and state.score[Side.ALLIES.value] > axis_score:
                return Side.ALLIES, f"盟军决定性胜利：击沉 {axis_ca_sunk} 艘日军重巡且分数领先", 1
            if margin >= decisive:
                return Side.AXIS, f"日军决定性胜利：领先 {margin} 分", 1
            if margin >= tactical:
                return Side.AXIS, f"日军战术胜利：领先 {margin} 分", 1
            return Side.ALLIES, f"盟军战术胜利：分数差 {margin}，不足 {tactical} 分", 1
        if kind == "vp_with_decisive_margin":
            # S-11：标准 VP 制，分差达到决定性门槛时在战报中标注。
            margin = state.score[Side.AXIS.value] - state.score[Side.ALLIES.value]
            decisive = int(self.definition.get("victory", {}).get("decisive_margin", 20))
            if abs(margin) >= decisive:
                winner = Side.AXIS if margin > 0 else Side.ALLIES
                return winner, f"决定性胜利：领先 {abs(margin)} 分（门槛 {decisive}）", 1
            if abs(margin) >= 4:
                winner = Side.AXIS if margin > 0 else Side.ALLIES
                return winner, f"想定结束胜利点领先 {abs(margin)} 分", 1
            return None, "平局：胜利点差小于4", 1
        if kind == "vp_with_bb_decisive_clause":
            # S-12：标准 VP 之外，敌方损失 1-2 艘 BB 而己方无 BB 损失 = 决定性胜利。
            for side in Side:
                enemy_bb_lost = self._sunk_counts(state, {"BB"}, side.opponent)
                own_bb_lost = self._sunk_counts(state, {"BB"}, side)
                if 1 <= enemy_bb_lost <= 2 and own_bb_lost == 0:
                    return side, f"决定性胜利：敌方损失 {enemy_bb_lost} 艘战列舰而己方战列舰无损", 1
            margin = state.score[Side.AXIS.value] - state.score[Side.ALLIES.value]
            if abs(margin) >= 4:
                winner = Side.AXIS if margin > 0 else Side.ALLIES
                return winner, f"想定结束胜利点领先 {abs(margin)} 分", 1
            return None, "平局：胜利点差小于4", 1
        if kind == "dd_kill_comparison":
            # S-13：按双方击沉驱逐舰数判定战役级胜利。
            allies_dd_kills = self._sunk_counts(state, {"DD", "APD"}, Side.AXIS)
            axis_dd_kills = self._sunk_counts(state, {"DD", "APD"}, Side.ALLIES)
            allies_losses = axis_dd_kills
            axis_losses = allies_dd_kills
            if allies_dd_kills >= 3 and allies_losses <= 1:
                return Side.ALLIES, f"盟军战役级胜利：击沉 {allies_dd_kills} 艘日军DD，仅损失 {allies_losses} 艘", 1
            if axis_dd_kills >= 3 and axis_losses == 0:
                return Side.AXIS, f"日军战役级胜利：击沉 {axis_dd_kills} 艘盟军DD，己方DD无损", 1
            return None, "平局：未达成任何一方的战役级胜利条件", 1
        if kind == "margin_tiers":
            # S-14：领先 3 分战术胜利，领先 6 分战役级胜利。
            margin = state.score[Side.AXIS.value] - state.score[Side.ALLIES.value]
            tactical = int(self.definition.get("victory", {}).get("tactical_margin", 3))
            campaign = int(self.definition.get("victory", {}).get("campaign_margin", 6))
            if abs(margin) >= campaign:
                winner = Side.AXIS if margin > 0 else Side.ALLIES
                return winner, f"战役级胜利：领先 {abs(margin)} 分", 1
            if abs(margin) >= tactical:
                winner = Side.AXIS if margin > 0 else Side.ALLIES
                return winner, f"战术胜利：领先 {abs(margin)} 分", 1
            return None, "平局：分数差不足 3 分", 1
        margin = state.score[Side.AXIS.value] - state.score[Side.ALLIES.value]
        winner = Side.AXIS if margin > 0 else (Side.ALLIES if margin < 0 else None)
        return winner, ("想定结束时胜利点领先" if margin else "平局"), 1

    # --------------------------------------------------------------- legacy API
    def gunnery_hits(
        self, base_lookup: Callable[[int, int], int], firepower: int, adjusted_roll: int
    ) -> int:
        row = next(
            (
                item
                for item in self.gunnery_extension
                if int(item["firepower_min"]) <= firepower
                and (not item["firepower_max"] or firepower <= int(item["firepower_max"]))
            ),
            None,
        )
        if row is None:
            return base_lookup(firepower, adjusted_roll)
        column = str(adjusted_roll) if adjusted_roll < 36 else "36_plus"
        return int(row[column])

    def penetration_caliber(self, attacker_id: str, caliber: float) -> float:
        kinds = {item.get("kind") for item in self.definition.get("scenario_rules", [])}
        if (
            "japanese_3_9_penetrates_as_3_inch" in kinds
            and attacker_id.startswith("IBS-U-IJN-")
            and abs(caliber - 3.9) < 0.001
        ):
            return 3.0
        return caliber

    def penetration_period(self) -> str:
        """装甲穿透表的年份档：想定日期在 1942 年之前用 1928 行，否则用 post_1942 行。

        穿甲表脚注：美 16"/45* 仅适用于 1942 年之后；1928 年使用 16"('*28) 一行。
        想定缺日期时按 1942 后处理（与既有行为一致）。
        """
        date = str(self.definition.get("date") or "")
        year = int(date[:4]) if date[:4].isdigit() else 1942
        return "1928" if year < 1942 else "post_1942"


@lru_cache(maxsize=32)
def scenario_rules(scenario_id: str) -> ScenarioRuleSet:
    definition = load_scenario(scenario_id)
    rows: tuple[dict[str, str], ...] = ()
    extension = next(
        (
            item.get("table")
            for item in definition.get("scenario_rules", [])
            if item.get("kind") == "gunnery_hit_table_extension"
        ),
        None,
    )
    if extension:
        path = STRUCTURED / "scenarios" / str(extension)
        with path.open("r", encoding="utf-8", newline="") as stream:
            rows = tuple(csv.DictReader(stream))
    return ScenarioRuleSet(scenario_id=scenario_id, definition=definition, gunnery_extension=rows)
