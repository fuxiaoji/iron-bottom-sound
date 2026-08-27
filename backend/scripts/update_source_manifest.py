from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]
ORIGINALS = ROOT / "resources" / "originals"
MANIFEST = ORIGINALS / "manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    indexed = {entry["path"]: entry for entry in document["files"]}
    extensions = [
        yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in sorted((ORIGINALS / "extensions").glob("*/source-manifest.yaml"))
    ]
    extension_roots = tuple(str(Path(item["source_root"])).replace("/", "\\") for item in extensions)
    for entry in indexed.values():
        entry["original_paths"] = [
            path for path in entry["original_paths"] if not path.startswith(extension_roots)
        ]
    for extension in extensions:
        source_root = Path(extension["source_root"])
        mappings = list(extension.get("documents", []))
        mappings.extend(
            {
                "canonical": f"resources/originals/assets/images/{name}",
                "original": f"images/{name}",
            }
            for name in extension.get("assets", [])
        )
        for mapping in mappings:
            canonical = str(mapping["canonical"]).replace("\\", "/")
            canonical_path = ROOT / canonical
            if not canonical_path.is_file():
                raise FileNotFoundError(canonical_path)
            original_path = str(source_root / Path(mapping["original"])).replace("/", "\\")
            entry = indexed.setdefault(canonical, {"path": canonical, "original_paths": []})
            entry["bytes"] = canonical_path.stat().st_size
            entry["sha256"] = sha256(canonical_path)
            entry["original_paths"] = sorted(set(entry["original_paths"]) | {original_path})
            if canonical_path.suffix.lower() == ".pdf":
                entry["pages"] = len(PdfReader(str(canonical_path)).pages)
    for entry in indexed.values():
        canonical_path = ROOT / entry["path"]
        entry["bytes"] = canonical_path.stat().st_size
        entry["sha256"] = sha256(canonical_path)
    files = sorted(indexed.values(), key=lambda entry: entry["path"])
    document["files"] = files
    document["canonical_file_count"] = len(files)
    document["source_path_count"] = sum(len(entry["original_paths"]) for entry in files)
    document["total_bytes"] = sum(int(entry["bytes"]) for entry in files)
    MANIFEST.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
