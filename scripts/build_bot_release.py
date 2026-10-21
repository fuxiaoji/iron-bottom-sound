#!/usr/bin/env python3
"""Build a bot runtime including the exact immutable night-snapshot sources.

Requires hydrated Git LFS originals. --source-root may point at an existing
checkout; every source is checked against this checkout's committed LFS OID.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    'resources/originals/rules/iron-bottom-sound-iv-rules-zh.pdf',
    'resources/originals/rules/player-aid-tables-zh.pdf',
    'resources/originals/scenarios/scenario-book-zh.pdf',
    'resources/originals/records/ship-record-manual-1.1-zh.pdf',
    'resources/originals/assets/images/岛屿.jpg',
)


def build(output: Path, source_root: Path):
    manifest = {}
    for name in SOURCES:
        raw = subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=ROOT)
        oid = re.search(rb'oid sha256:([0-9a-f]{64})', raw)
        expected = oid.group(1).decode() if oid else hashlib.sha256(raw).hexdigest()
        path = source_root / name
        data = path.read_bytes()
        if data.startswith(b'version https://git-lfs.github.com/spec/v1'):
            raise SystemExit('Hydrate Git LFS sources before packaging: ' + name)
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected:
            raise SystemExit('Source hash differs from committed source: ' + name)
        manifest[name] = {'sha256': actual, 'bytes': len(data)}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, 'w:gz') as tar:
        for name in ('backend/src', 'resources/derived/structured', 'pyproject.toml',
                     'scripts/bot_mcp_remote.py'):
            tar.add(ROOT / name, arcname=name,
                    filter=lambda item: None if '__pycache__' in item.name or item.name.endswith('.pyc') else item)
        for name in SOURCES:
            tar.add(source_root / name, arcname=name)
    record = {'archive': output.name, 'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
              'sources': manifest}
    output.with_suffix(output.suffix + '.json').write_text(json.dumps(record, ensure_ascii=False, indent=2))
    print(json.dumps({'archive': str(output.resolve()), 'bytes': output.stat().st_size,
                      'sha256': record['sha256'], 'verified_sources': len(manifest)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--source-root', type=Path, default=ROOT)
    args = parser.parse_args()
    build(args.output, args.source_root)


if __name__ == '__main__':
    main()
