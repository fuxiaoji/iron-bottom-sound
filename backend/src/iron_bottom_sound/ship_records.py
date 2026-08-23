from __future__ import annotations

from copy import deepcopy
from typing import Any

from .data import STRUCTURED, read_yaml
from .models import ShipRecord


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def load_ship_records() -> dict[str, ShipRecord]:
    document = read_yaml(STRUCTURED / "ships" / "ship-records.yaml")
    families = document["families"]
    records: dict[str, ShipRecord] = {}
    for record_id, override in document["records"].items():
        family_id = override["family"]
        payload = _merge(families[family_id], {key: value for key, value in override.items() if key != "family"})
        payload["id"] = record_id
        records[record_id] = ShipRecord.model_validate(payload)
    return records
