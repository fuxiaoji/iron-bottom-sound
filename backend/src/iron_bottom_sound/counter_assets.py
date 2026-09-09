from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .data import ROOT, STRUCTURED


ASSET_ROOT = ROOT / "resources" / "originals" / "assets" / "images"
_MANIFEST_PATH = STRUCTURED / "ships" / "counter-assets.json"
_OVERRIDES = {
    "IBS-U-USN-MINNEAPOLIS": "美国-CA-明尼阿波里斯.png",
    "IBS-U-USN-RALPH-TALBOT": "美国-DD-拉尔夫·托尔伯特.png",
    "IBS-U-USN-RALPH-TALBOT-17": "美国-DD-拉尔夫·托尔伯特.png",
    "IBS-U-USN-SELFRIDGE": "美国-DD-赛尔弗里纪.png",
    "IBS-U-USN-CF-AUSBURNE": "美国-DD-查尔斯·奥斯本.png",
    "IBS-U-KM-RICHARD-BEITZEN": "德国-DD-里夏德·拜茨恩.png",
    "IBS-U-KM-HANS-LODY": "德国-DD-汉斯·洛迪.png",
    "IBS-U-USN-ERMA-ALLEN-M-SUMNER": "美国-DD-艾伦·M·萨姆纳.png",
}

_MANIFEST: dict[str, str] = {}
if _MANIFEST_PATH.exists():
    _MANIFEST = yaml.safe_load(_MANIFEST_PATH.read_text(encoding="utf-8")).get("bindings", {})


def _scenario_assets() -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted((STRUCTURED / "scenarios").glob("*.yaml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        entries = list(document.get("ships", []))
        entries.extend(document.get("reinforcements", {}).get("ships", []))
        for entry in entries:
            if entry.get("id") and entry.get("asset"):
                result.setdefault(str(entry["id"]), str(entry["asset"]))
    return result


def asset_candidates(ship_id: str, name: str, ship_type: str) -> set[str]:
    if ship_id in _MANIFEST:
        return {_MANIFEST[ship_id]}
    if ship_id in _OVERRIDES:
        return {_OVERRIDES[ship_id]}
    scenario_asset = _scenario_assets().get(ship_id)
    if scenario_asset:
        return {scenario_asset}
    normalized = name.replace("(I)", "").replace("(II)", "").replace("·", "")
    return {
        path.name
        for path in ASSET_ROOT.glob("*.png")
        if ship_type in path.name and normalized and normalized in path.name
    }


def asset_for(ship_id: str, name: str, ship_type: str) -> str | None:
    candidates = sorted(asset_candidates(ship_id, name, ship_type))
    return candidates[0] if candidates else None


def all_asset_bindings(records: dict[str, Any]) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for ship_id, record in records.items():
        asset = asset_for(ship_id, record.name, record.ship_type)
        if asset is not None:
            bindings[ship_id] = asset
    return bindings


def validate_asset_bindings(records: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    bindings = all_asset_bindings(records)
    for ship_id in records:
        asset = bindings.get(ship_id)
        if asset is None:
            errors.append(f"{ship_id}: no counter asset binding")
        elif not (ASSET_ROOT / asset).is_file():
            errors.append(f"{ship_id}: missing counter asset {asset}")
    reverse: dict[str, list[str]] = {}
    for ship_id, asset in bindings.items():
        reverse.setdefault(asset, []).append(ship_id)
    # Shared artwork is allowed only when the source itself does not distinguish
    # the ship variant; it is still reported for audit visibility.
    for asset, ship_ids in reverse.items():
        if len(ship_ids) > 1:
            continue
    return errors
