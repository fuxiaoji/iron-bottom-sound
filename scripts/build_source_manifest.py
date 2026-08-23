#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "resources" / "originals"
ALIASES = {
    "resources/originals/records/ship-record-manual-1.1-zh.pdf": [
        r"D:\desktop\铁底湾\铁底湾舰船记录手册1.1.pdf",
        r"D:\desktop\铁底湾\铁底湾舰船记录手册1.1 (1).pdf",
    ]
}

RENAMED = {
    "resources/originals/rules/iron-bottom-sound-iv-rules-zh.pdf": r"D:\desktop\铁底湾\铁底湾规则预览.pdf",
    "resources/originals/rules/player-aid-tables-zh.pdf": r"D:\desktop\铁底湾\表.pdf",
    "resources/originals/scenarios/scenario-book-zh.pdf": r"D:\desktop\铁底湾\铁底湾的回响中文版 想定手册 (战鼓，kv)(1).pdf",
    "resources/originals/tables/ship-list-zh.docx": r"D:\desktop\铁底湾\舰船列表.docx",
    "resources/originals/tables/movement-attack-log-zh.xlsx": r"D:\desktop\铁底湾\铁底湾通用移动攻击表.xlsx",
}


def original_paths(relative: str, filename: str) -> list[str]:
    if relative in ALIASES:
        return ALIASES[relative]
    if relative in RENAMED:
        return [RENAMED[relative]]
    if "/assets/images/" in relative:
        return [rf"D:\desktop\铁底湾\images\{filename}"]
    if "/assets/ship-classes/japan/" in relative:
        return [rf"D:\desktop\铁底湾\船表\日\{filename}"]
    if "/assets/ship-classes/usa/" in relative:
        return [rf"D:\desktop\铁底湾\船表\美\{filename}"]
    return [rf"D:\desktop\铁底湾\{filename}"]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


items = []
for path in sorted(p for p in SOURCES.rglob("*") if p.is_file() and p.name != "manifest.json"):
    relative = path.relative_to(ROOT).as_posix()
    item = {
        "path": relative,
        "bytes": path.stat().st_size,
        "sha256": digest(path),
        "original_paths": original_paths(relative, path.name),
    }
    if path.suffix.lower() == ".pdf":
        item["pages"] = len(PdfReader(str(path)).pages)
    items.append(item)

manifest = {
    "schema_version": 1,
    "source_root": r"D:\desktop\铁底湾",
    "canonical_file_count": len(items),
    "source_path_count": sum(len(item["original_paths"]) for item in items),
    "total_bytes": sum(item["bytes"] for item in items),
    "files": items,
}
(SOURCES / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"canonical_file_count": manifest["canonical_file_count"], "source_path_count": manifest["source_path_count"], "total_bytes": manifest["total_bytes"]}, ensure_ascii=False))
