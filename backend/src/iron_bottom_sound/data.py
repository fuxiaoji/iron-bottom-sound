from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from .models import GameOptions, GameState, HexCoord, Phase, ShipState, Side, WeaponMount


ROOT = Path(__file__).resolve().parents[3]
STRUCTURED = ROOT / "resources" / "derived" / "structured"


def read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def scenario_catalog() -> list[dict[str, Any]]:
    return read_yaml(STRUCTURED / "scenarios" / "catalog.yaml")["scenarios"]


def load_scenario(scenario_id: str) -> dict[str, Any]:
    number = int(scenario_id.rsplit("-", 1)[-1])
    path = STRUCTURED / "scenarios" / f"scenario-{number:02d}.yaml"
    if not path.exists():
        raise KeyError(f"Scenario {scenario_id} is catalogued but not playable")
    return read_yaml(path)


def load_templates() -> dict[str, dict[str, Any]]:
    return read_yaml(STRUCTURED / "ships" / "templates.yaml")["templates"]


def make_ship(entry: dict[str, Any], templates: dict[str, dict[str, Any]]) -> ShipState:
    data = deepcopy(templates[entry["template"]])
    primary = WeaponMount(kind="primary", firepower=data.get("primary_gf", 0), caliber=data.get("primary_caliber", 0))
    secondary = None
    if data.get("secondary_gf", 0):
        secondary = WeaponMount(kind="secondary", firepower=data["secondary_gf"], caliber=data.get("secondary_caliber", 5))
    torpedo = None
    if data.get("torpedoes", 0):
        torpedo = WeaponMount(kind="torpedo", ammo=data["torpedoes"])
    return ShipState(
        id=entry["id"],
        name=entry["name"],
        side=Side(entry["side"]),
        ship_type=data["type"],
        position=HexCoord.from_label(entry["position"]) if entry.get("position") else None,
        heading=entry["heading"],
        speed_track=tuple(data["speed_track"]),
        current_speed=entry["speed"],
        previous_speed=entry["speed"],
        hull=data["hull"],
        max_hull=data["hull"],
        primary=primary,
        secondary=secondary,
        torpedo=torpedo,
        torpedo_type=data.get("torpedo_type"),
        belt_armor=data.get("belt_armor", 0),
        vp=data.get("vp", 0),
        asset=entry.get("asset"),
        reinforcement_turn=entry.get("reinforcement_turn"),
    )


def build_initial_state(game_id: str, scenario_id: str, seed: int, options: GameOptions) -> GameState:
    scenario = load_scenario(scenario_id)
    templates = load_templates()
    ships = {entry["id"]: make_ship(entry, templates) for entry in scenario["ships"]}
    for key in scenario.get("optional_rules", []):
        setattr(options.optional_rules, key, True)
    return GameState(
        game_id=game_id,
        scenario_id=scenario_id,
        scenario_title=scenario["title"],
        max_turns=scenario["turns"],
        phase=Phase(scenario.get("initial_phase", Phase.REINFORCEMENT.value)),
        seed=seed,
        options=options,
        visibility=scenario["visibility"],
        ships=ships,
    )
