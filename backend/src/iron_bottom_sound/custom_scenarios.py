from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from .data import ROOT, build_initial_state, load_scenario, register_custom_scenario
from .models import (
    FormationSetupOrder,
    GameOptions,
    HexCoord,
    MAP_COLUMNS,
    MAP_ROWS,
    MAX_MAP_COLUMNS,
    MAX_MAP_ROWS,
    OptionalRules,
    Side,
)
from .ship_records import load_ship_records


ASSET_ROOT = ROOT / "resources" / "originals" / "assets" / "images"


class CustomShip(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    side: Side
    position: str
    heading: int = Field(ge=1, le=6)
    speed: int = Field(ge=0, le=8)
    asset: str = Field(min_length=1, max_length=240)

    @field_validator("position")
    @classmethod
    def valid_position(cls, value: str) -> str:
        HexCoord.from_label(value)
        return value.upper()


class CustomScenarioInput(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    turns: int = Field(default=12, ge=1, le=99)
    visibility: dict[Side, int] = Field(default_factory=lambda: {Side.AXIS: 4, Side.ALLIES: 4})
    optional_rules: list[str] = Field(default_factory=list)
    ships: list[CustomShip] = Field(min_length=2)
    formations: dict[Side, list[FormationSetupOrder]] = Field(default_factory=dict)
    description: str = Field(default="", max_length=400)
    recommended_mode: Literal["pvp", "pve"] | None = None
    # Playable map size.  Defaults keep every legacy scenario byte-identical on
    # the fixed 46×39 IBS-R-MAP-01 board; a "大战场" scenario declares e.g.
    # map_columns=92/map_rows=78.  printed_* smaller than map_* mark an inner
    # "printed" region; None defaults to the standard 34×27 printed sea.
    map_columns: int = Field(default=MAP_COLUMNS, ge=1, le=MAX_MAP_COLUMNS)
    map_rows: int = Field(default=MAP_ROWS, ge=1, le=MAX_MAP_ROWS)
    printed_columns: int | None = None
    printed_rows: int | None = None

    @field_validator("optional_rules")
    @classmethod
    def known_optional_rules(cls, values: list[str]) -> list[str]:
        allowed = set(OptionalRules.model_fields)
        unknown = sorted(set(values) - allowed)
        if unknown:
            raise ValueError(f"Unknown optional rules: {unknown}")
        return list(dict.fromkeys(values))

    @model_validator(mode="after")
    def _within_declared_map(self) -> "CustomScenarioInput":
        printed_columns = self.printed_columns if self.printed_columns is not None else self.map_columns
        printed_rows = self.printed_rows if self.printed_rows is not None else self.map_rows
        if printed_columns > self.map_columns or printed_rows > self.map_rows:
            raise ValueError(
                f"Printed region {printed_columns}x{printed_rows} exceeds the playable map"
            )
        for ship in self.ships:
            position = HexCoord.from_label(ship.position)
            display_row = position.r + (position.q - (position.q & 1)) // 2
            if position.q >= self.map_columns or display_row >= self.map_rows:
                raise ValueError(
                    f"{ship.id}: position {ship.position} lies outside the "
                    f"{self.map_columns}x{self.map_rows} map"
                )
        return self


def new_id() -> str:
    return f"IBS-CUSTOM-{uuid4().hex[:12].upper()}"


def with_engine_default_formations(definition: dict) -> dict:
    """Translate authored ``formations`` into ``setup.engine_default_formations``
    so a realistic-mode opening proposal presents the author's groupings.

    Returns a deep copy; the input is never mutated.  Flagship markers are stamped
    onto the matching ship entries so ``default_setup_orders`` honours them.
    """
    copy = deepcopy(definition)
    formations = copy.get("formations") or {}
    seeds: dict[str, list[dict]] = {}
    flagships: set[str] = set()
    for side, orders in formations.items():
        orders = orders or []
        if not orders:
            continue
        seeds[side] = [
            {
                "id": str(order.get("formation_id") or f"{side}-formation-{index}"),
                "role": "authored",
                "ships": list(order.get("ship_ids") or []),
            }
            for index, order in enumerate(orders, 1)
        ]
        flagships.update(str(order["flagship_id"]) for order in orders if order.get("flagship_id"))
    if not seeds:
        return copy
    setup = copy.setdefault("setup", {})
    merged = dict(setup.get("engine_default_formations") or {})
    merged.update(seeds)
    setup["engine_default_formations"] = merged
    for ship in copy.get("ships", []):
        if ship.get("id") in flagships:
            ship["flagship"] = True
    return copy


def builtin_as_editable_template(scenario_id: str) -> dict:
    """Adapt a built-in scenario into a POST-able custom-scenario body.

    Only initial (non-reinforcement) ships with complete records are kept.  When
    the scenario seeds ``engine_default_formations`` those groupings become
    ``formations``; otherwise each side's ships collapse into a single formation
    (mirroring the engine's own fallback for these all-light scenarios).  Dropped
    content is reported in a Chinese ``warnings`` list.
    """
    if scenario_id.startswith("IBS-CUSTOM-"):
        raise KeyError(f"{scenario_id} is already a custom scenario")
    definition = load_scenario(scenario_id)
    records = load_ship_records()
    kept: list[dict] = []
    by_id: dict[str, dict] = {}
    for entry in definition.get("ships") or []:
        ship_id = str(entry["id"])
        if ship_id not in records:
            continue
        kept.append(
            {
                "id": ship_id,
                "side": entry["side"],
                "position": str(entry["position"]).upper(),
                "heading": int(entry.get("heading", 1)),
                "speed": int(entry.get("speed", 5)),
                "asset": entry["asset"],
            }
        )
        by_id[ship_id] = entry

    def order_for(side: str, number: int, ids: list[str], authored: dict | None) -> dict:
        flagged = [sid for sid in ids if by_id[sid].get("flagship")]
        flagship = flagged[0] if flagged else ids[0]
        reserve = next((sid for sid in ids if sid != flagship), ids[0])
        return {
            "formation_id": (authored or {}).get("id") or f"{side}-template-{number}",
            "name": f"{'轴心' if side == 'axis' else '同盟'}第{number}编队",
            "ship_ids": ids,
            "leader_id": ids[0],
            "flagship_id": flagship,
            "reserve_flagship_id": reserve,
            "spacing": 1,
            "heading": int(by_id[ids[0]].get("heading", 1)),
        }

    def side_orders(side: str) -> list[dict]:
        owned = [ship["id"] for ship in kept if ship["side"] == side]
        authored_groups = (definition.get("setup", {}).get("engine_default_formations") or {}).get(side) or []
        orders: list[dict] = []
        used: list[str] = []
        number = 0
        for authored in authored_groups:
            ids = [sid for sid in authored.get("ships", []) if sid in owned and sid not in used]
            if len(ids) < 2:
                continue
            used.extend(ids)
            number += 1
            orders.append(order_for(side, number, ids, authored))
        leftover = [sid for sid in owned if sid not in used]
        if leftover and orders:
            orders[-1]["ship_ids"] = orders[-1]["ship_ids"] + leftover
        elif leftover and len(leftover) >= 2:
            number += 1
            orders.append(order_for(side, number, leftover, None))
        return orders

    formations: dict[str, list[dict]] = {}
    if all(len([ship for ship in kept if ship["side"] == side]) >= 2 for side in ("axis", "allies")):
        formations = {side: side_orders(side) for side in ("axis", "allies")}

    warnings: list[str] = []
    reinforcements = definition.get("reinforcements") or {}
    reinforcement_ships = reinforcements.get("ships") if isinstance(reinforcements, dict) else None
    if reinforcement_ships:
        warnings.append(
            f"想定原有 {len(reinforcement_ships)} 艘增援舰，模板只保留初始舰船；如需增援，请在编辑器中手动添加。"
        )
    initial_phase = definition.get("initial_phase")
    if initial_phase not in (None, "reinforcement"):
        warnings.append(
            f"想定原设定为从「{initial_phase}」阶段直接开局；改编后统一从标准开局流程开始。"
        )
    for key, label in (("victory", "胜负条件"), ("special_rules", "特殊规则"), ("scenario_rules", "想定规则")):
        if definition.get(key):
            warnings.append(f"想定的{label}不会迁移到自定义剧本，统一按常规比分判定胜负。")
    if definition.get("optional_rules"):
        warnings.append("想定的可选规则未自动迁移，请在「其他设置」中按需重新勾选。")

    return {
        "title": str(definition.get("title")),
        "turns": int(definition.get("turns", 12)),
        "visibility": dict(definition.get("visibility") or {"axis": 4, "allies": 4}),
        "optional_rules": [],
        "ships": kept,
        "formations": formations,
        "description": "",
        "recommended_mode": None,
        "warnings": warnings,
    }


def _asset_exists(asset: str) -> bool:
    return (ASSET_ROOT / Path(asset).name).is_file() and Path(asset).name == asset


def validate_definition(scenario_id: str, definition: dict) -> list[str]:
    errors: list[str] = []
    try:
        payload = CustomScenarioInput.model_validate(definition)
    except Exception as error:
        return [str(error)]
    records = load_ship_records()
    ids = [ship.id for ship in payload.ships]
    if len(ids) != len(set(ids)):
        errors.append("Ship ids must be unique")
    for ship in payload.ships:
        if ship.id not in records:
            errors.append(f"{ship.id}: no complete combat record")
        if not _asset_exists(ship.asset):
            errors.append(f"{ship.id}: missing counter asset {ship.asset}")
        elif ship.id in records and ship.asset not in _candidate_assets(ship.id, records[ship.id].name, records[ship.id].ship_type):
            errors.append(f"{ship.id}: counter asset is not bound to this ship")
        if ship.id in records and ship.speed > max(records[ship.id].speed_damage_track[0][0], records[ship.id].speed_damage_track[1][0], records[ship.id].speed_damage_track[2][0]):
            errors.append(f"{ship.id}: speed exceeds record maximum")
    if {ship.side for ship in payload.ships} != {Side.AXIS, Side.ALLIES}:
        errors.append("Both sides must have at least one ship")
    positions = [ship.position for ship in payload.ships]
    if len(positions) != len(set(positions)):
        errors.append("Ships may not overlap")
    if errors:
        return errors
    for ship in definition["ships"]:
        ship["name"] = records[ship["id"]].name
    definition = deepcopy(definition)
    definition["id"] = scenario_id
    register_custom_scenario(definition)
    try:
        state = build_initial_state("CUSTOM-VALIDATION", scenario_id, 1, GameOptions())
        for ship in state.ships.values():
            if ship.position is not None and ship.position.label in state.land_hexes:
                errors.append(f"{ship.id}: position is land")
        if any(payload.formations.values()):
            from .engine import IronBottomEngine
            from .models import OrderBatch, Phase
            from .realistic_command import validate_setup

            checker = IronBottomEngine()
            for side, formations in payload.formations.items():
                batch = OrderBatch(
                    side=side,
                    phase=Phase.FORMATION_SETUP,
                    formation_setup=formations,
                )
                errors.extend(f"{side.value}: {error}" for error in validate_setup(checker, state, batch))
    except Exception as error:
        errors.append(str(error))
    return errors


def _candidate_assets(ship_id: str, name: str, ship_type: str) -> set[str]:
    """Return exact or legacy-compatible candidates for the explicit binding check."""
    from .counter_assets import asset_candidates

    return asset_candidates(ship_id, name, ship_type)
