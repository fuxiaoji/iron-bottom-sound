from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable

from .data import STRUCTURED, load_scenario
from .models import GameState, Side


@dataclass(frozen=True)
class ScenarioRuleSet:
    """Executable scenario exceptions loaded from the scenario definition.

    The generic engine delegates only the places where a scenario may override
    a base rule.  This keeps fan-expansion tables and victory arithmetic out of
    the already large engine module.
    """

    scenario_id: str
    definition: dict
    gunnery_extension: tuple[dict[str, str], ...] = ()

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
        margin = state.score[Side.AXIS.value] - state.score[Side.ALLIES.value]
        winner = Side.AXIS if margin > 0 else (Side.ALLIES if margin < 0 else None)
        return winner, ("想定结束时胜利点领先" if margin else "平局"), 1


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
