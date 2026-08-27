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
    paths = [STRUCTURED / "ships" / "ship-records.yaml"]
    extension_root = STRUCTURED / "ships" / "extensions"
    if extension_root.exists():
        paths.extend(sorted(extension_root.glob("*.yaml")))
    documents = [read_yaml(path) for path in paths]
    families: dict[str, dict[str, Any]] = {}
    for document in documents:
        overlap = set(families) & set(document.get("families", {}))
        if overlap:
            raise ValueError(f"Duplicate ship-record families: {sorted(overlap)}")
        families.update(document.get("families", {}))
    records: dict[str, ShipRecord] = {}
    for document in documents:
        for record_id, override in document.get("records", {}).items():
            if record_id in records:
                raise ValueError(f"Duplicate ship record {record_id}")
            family_id = override["family"]
            payload = _merge(families[family_id], {key: value for key, value in override.items() if key != "family"})
            payload["id"] = record_id
            records[record_id] = ShipRecord.model_validate(payload)
    return records
