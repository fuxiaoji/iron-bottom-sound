#!/usr/bin/env python3
"""Export the repository's structured data into an RTT-platform module file.

Reads the backend's canonical data loaders (ship records, scenarios,
templates) plus the raw rules tables, then writes ``rtt-module/data.js`` as a
plain JavaScript module.  The output file is generated -- do not edit by hand.

Usage::

    .venv-ibsglm/bin/python scripts/export_rtt_data.py
"""

from __future__ import annotations

import csv
import datetime
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from iron_bottom_sound.data import STRUCTURED, load_scenario, load_templates, scenario_catalog  # noqa: E402
from iron_bottom_sound.engine import D66_VALUES  # noqa: E402
from iron_bottom_sound.models import MAX_MAP_COLUMNS, MAX_MAP_ROWS, HexCoord  # noqa: E402
from iron_bottom_sound.ship_records import load_ship_records  # noqa: E402

RULES = STRUCTURED / "rules"
OUTPUT_PATH = ROOT / "rtt-module" / "data.js"

EXPECTED_SCENARIO_COUNT = 16
EXPECTED_SHIP_COUNT = 214


# ---------------------------------------------------------------------------
# Plain-data conversion helpers
# ---------------------------------------------------------------------------

def _read_yaml(path: Path) -> dict[str, Any]:
    import yaml

    with path.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    """Read a rules CSV into dicts, converting numeric-looking cells."""
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = []
        for raw in reader:
            row: dict[str, Any] = {}
            for key, value in raw.items():
                if value is None:
                    row[key] = None
                    continue
                text = value.strip()
                row[key] = _coerce_number(text)
            rows.append(row)
        return rows


def _coerce_number(text: str) -> Any:
    """Return int/float when possible, otherwise the original string."""
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def to_plain(value: Any) -> Any:
    """Recursively convert loaded data into JSON/JS-safe plain structures.

    HexCoord objects become their label strings; dates become ISO strings;
    sets/tuples become lists; pydantic models become dicts.
    """
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        # Keep numbers tidy (8.0 -> 8); numerically identical in JS.
        return int(value) if value.is_integer() else value
    if isinstance(value, HexCoord):
        return str(value.label)
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, (list, tuple, set, frozenset)):
        if isinstance(value, (set, frozenset)):
            value = sorted(value)
        return [to_plain(item) for item in value]
    # Pydantic models (defensive: loaders already return dicts, but HexCoord or
    # similar objects may appear anywhere in a scenario definition).
    if hasattr(value, "model_dump"):
        return to_plain(value.model_dump())
    if hasattr(value, "label") and not isinstance(value, dict):
        return str(value.label)
    if isinstance(value, dict):
        return {str(key): to_plain(item) for key, item in value.items()}
    return str(value)


def export_ship_record(record: Any) -> dict[str, Any]:
    """Convert a ShipRecord into the flat pure-data shape used by the module."""
    return {
        "id": record.id,
        "name": record.name,
        "ship_type": record.ship_type,
        "displacement_band": record.displacement_band,
        "hull_rows": list(record.hull_rows),
        "speed_damage_track": [list(row) for row in record.speed_damage_track],
        "guns": [
            {
                "id": gun.id,
                "kind": str(gun.kind.value) if hasattr(gun.kind, "value") else str(gun.kind),
                "position": str(gun.position.value) if hasattr(gun.position, "value") else str(gun.position),
                "firepower": gun.firepower,
                "caliber": gun.caliber,
                "arcs": [str(arc.value) if hasattr(arc, "value") else str(arc) for arc in gun.arcs],
            }
            for gun in record.guns
        ],
        "torpedo_launchers": [
            {
                "id": launcher.id,
                "position": str(launcher.position.value)
                if hasattr(launcher.position, "value")
                else str(launcher.position),
                "arcs": [str(arc.value) if hasattr(arc, "value") else str(arc) for arc in launcher.arcs],
                "torpedoes": launcher.torpedoes,
                "reloads": launcher.reloads,
            }
            for launcher in record.torpedo_launchers
        ],
        "torpedo_type": record.torpedo_type,
        "armour": {
            "primary": record.armour.primary,
            "secondary": record.armour.secondary,
            "belt": record.armour.belt,
            "bridge": record.armour.bridge,
        },
        "fire_control": record.fire_control,
        "radar": record.radar,
        "aircraft": record.aircraft,
        "vp": record.vp,
        "special_rules": list(record.special_rules),
    }


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def build_hex() -> dict[str, Any]:
    direction_delta = {str(heading): list(HexCoord.direction_delta(heading)) for heading in range(1, 7)}
    return {
        "MAX_COLUMNS": MAX_MAP_COLUMNS,
        "MAX_ROWS": MAX_MAP_ROWS,
        "direction_delta": direction_delta,
    }


def build_rules() -> dict[str, Any]:
    gunnery_results = _read_yaml(RULES / "gunnery-results.yaml")["results"]
    torpedo_collision = _read_yaml(RULES / "torpedo-collision-table.yaml")
    torpedoes = _read_yaml(RULES / "torpedoes.yaml")["types"]
    torpedo_launch_directions = _read_yaml(RULES / "torpedo-launch-directions.yaml")
    modifiers = _read_yaml(RULES / "modifiers.yaml")
    fire_table = _read_yaml(RULES / "fire-table.yaml")
    special_damage = _read_yaml(RULES / "special-damage-table.yaml")
    return {
        "fireTable": to_plain(fire_table),
        "specialDamage": to_plain(special_damage),
        "gunneryHitTable": _read_csv_rows(RULES / "gunnery-hit-table.csv"),
        "gunneryResults": to_plain(gunnery_results),
        "torpedoCollision": to_plain(torpedo_collision),
        "torpedoes": to_plain(torpedoes),
        "torpedoLaunchDirections": to_plain(torpedo_launch_directions),
        "modifiers": to_plain(modifiers),
        "armourPenetration": _read_csv_rows(RULES / "armour-penetration-table.csv"),
        "d66Values": list(D66_VALUES),
    }


def build_ships() -> dict[str, dict[str, Any]]:
    records = load_ship_records()
    return {record_id: export_ship_record(record) for record_id, record in records.items()}


def build_scenarios() -> dict[str, dict[str, Any]]:
    scenarios: dict[str, dict[str, Any]] = {}
    for entry in scenario_catalog():
        definition = to_plain(load_scenario(entry["id"]))
        scenarios[definition["id"]] = definition
    return scenarios


def build_templates() -> dict[str, dict[str, Any]]:
    return to_plain(load_templates())


def build() -> dict[str, Any]:
    hex_data = build_hex()
    rules = build_rules()
    ships = build_ships()
    scenarios = build_scenarios()
    templates = build_templates()

    assert len(scenarios) == EXPECTED_SCENARIO_COUNT, (
        f"Expected {EXPECTED_SCENARIO_COUNT} scenarios, got {len(scenarios)}"
    )
    assert len(ships) == EXPECTED_SHIP_COUNT, (
        f"Expected {EXPECTED_SHIP_COUNT} ship records, got {len(ships)}"
    )
    assert len(rules["d66Values"]) == 36, "D66_VALUES must contain 36 entries"
    assert rules["gunneryHitTable"], "gunnery hit table must not be empty"
    assert rules["armourPenetration"], "armour penetration table must not be empty"
    assert templates, "templates must not be empty"

    return {
        "meta": {
            "generator": "scripts/export_rtt_data.py",
            "generated_at": datetime.datetime.now(datetime.timezone.utc)
            .replace(microsecond=0)
            .isoformat(),
            "counts": {
                "ships": len(ships),
                "scenarios": len(scenarios),
                "templates": len(templates),
                "gunnery_hit_rows": len(rules["gunneryHitTable"]),
                "armour_penetration_rows": len(rules["armourPenetration"]),
            },
        },
        "hex": hex_data,
        "rules": rules,
        "ships": ships,
        "scenarios": scenarios,
        "templates": templates,
    }


# ---------------------------------------------------------------------------
# JavaScript serialization
# ---------------------------------------------------------------------------

def js_literal(value: Any, indent: int = 0) -> str:
    """Serialize plain data as a formatted JavaScript object literal."""
    pad = "  " * indent
    pad_inner = "  " * (indent + 1)
    if isinstance(value, dict):
        if not value:
            return "{}"
        lines = []
        for key, item in value.items():
            lines.append(f"{pad_inner}{json.dumps(str(key))}: {js_literal(item, indent + 1)}")
        return "{\n" + ",\n".join(lines) + f"\n{pad}}}"
    if isinstance(value, list):
        if not value:
            return "[]"
        # Short numeric lists stay on one line for readability.
        if value and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value):
            inner = ", ".join(js_literal(item, indent + 1) for item in value)
            return f"[{inner}]"
        lines = [f"{pad_inner}{js_literal(item, indent + 1)}" for item in value]
        return "[\n" + ",\n".join(lines) + f"\n{pad}]"
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return repr(value)
    return json.dumps(str(value), ensure_ascii=False)


def render_module(data: dict[str, Any]) -> str:
    sections = ", ".join(
        f"{key}: {js_literal(data[key], 1)}" for key in ("meta", "hex", "rules", "ships", "scenarios", "templates")
    )
    body = f"var data = {{\n  {sections}\n}}\n"
    return (
        "// 由 export_rtt_data.py 生成，勿手改\n"
        '"use strict"\n'
        + body
        + 'if (typeof module !== "undefined" && module.exports) module.exports = data\n'
    )


def main() -> int:
    data = build()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    rendered = render_module(data)
    OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(
        f"Wrote {OUTPUT_PATH} ({size_kb:.1f} KiB): "
        f"{len(data['ships'])} ships, {len(data['scenarios'])} scenarios, "
        f"{len(data['templates'])} templates"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
