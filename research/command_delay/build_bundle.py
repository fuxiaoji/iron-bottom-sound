"""Assemble COMMAND_DELAY_MODE_V2_2_IMPLEMENTATION_BUNDLE.zip.

Layout is fixed by the task specification::

    00_EXECUTIVE_SUMMARY.md ... 08_REPLAY_DETERMINISM_AUDIT.md
    BUG_AND_RERUN_LOG.md  DATA_MODEL_DIFF.md  TEST_MANIFEST.md
    code_patch/   logs/   tests/

Everything is copied from the working tree, so the bundle is exactly what was
audited.  Run after ``run_audits.py`` and the test suite::

    python research/command_delay/build_bundle.py
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BUNDLE = HERE / "bundle"
STAGE = HERE / "_bundle_stage"
OUTPUT = ROOT / "COMMAND_DELAY_MODE_V2_2_IMPLEMENTATION_BUNDLE.zip"

DOCS = (
    "00_EXECUTIVE_SUMMARY.md",
    "01_FREEZE_REGRESSION_AUDIT.md",
    "02_MOVEMENT_STYLE_AUDIT.md",
    "03_COMMUNICATION_PIPELINE.md",
    "04_MISSION_ORDER_AND_CONTINGENCY.md",
    "05_OBSERVATION_LEAKAGE_AUDIT.md",
    "06_FORMATION_AGENT_INTERFACE.md",
    "07_TARGET_PRIORITY_SELECTOR_AUDIT.md",
    "08_REPLAY_DETERMINISM_AUDIT.md",
    "BUG_AND_RERUN_LOG.md",
    "DATA_MODEL_DIFF.md",
    "TEST_MANIFEST.md",
    "REPRODUCE.md",
)

TEST_FILES = (
    "test_command_delay_agents_and_memory.py",
    "test_command_delay_live_surface.py",
    "test_command_delay_movement_style.py",
    "test_command_delay_mode_shell.py",
    "test_command_delay_communications.py",
    "test_command_delay_formation_agent.py",
    "test_command_delay_formation_llm.py",
    "test_command_delay_research_hooks.py",
)


def copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    missing = [name for name in DOCS if not (BUNDLE / name).exists()]
    if missing:
        print("missing bundle documents: " + ", ".join(missing))
        return 1
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)

    for name in DOCS:
        copy(BUNDLE / name, STAGE / name)

    # code_patch/
    for name in ("00_READ_ME.md", "COMMITS.md", "frozen_surface_touched.patch",
                 "command_delay_v2_2_source_and_tests.patch", "research_harness.patch"):
        copy(BUNDLE / "code_patch" / name, STAGE / "code_patch" / name)

    # tests/
    for name in TEST_FILES:
        copy(ROOT / "tests" / name, STAGE / "tests" / name)

    # logs/ — every cd* log, the audit log, the full suite, and the probe records
    logs = STAGE / "logs"
    logs.mkdir()
    for path in sorted((HERE / "logs").glob("*.log")):
        copy(path, logs / path.name)
    for path in sorted((HERE / "audits").glob("*.json")):
        copy(path, logs / f"audit_{path.name}" if not path.name.startswith("audit")
             else logs / path.name)

    # Evidence that is small and load-bearing: the golden index and the commit list.
    copy(HERE / "golden" / "GOLDEN_INDEX.json", STAGE / "logs" / "GOLDEN_INDEX.json")
    for extra in ("verify_live.log", "post_fix_tests.log", "post_fix_audits.log",
                  "cd10_tests.log", "post_cd10_audits.log"):
        source = HERE / "logs" / extra
        if source.exists():
            copy(source, logs / extra)
    commits = subprocess.run(
        ["git", "log", "--oneline", "realistic-command-v1-frozen..HEAD"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=120,
    ).stdout
    tags = subprocess.run(
        ["git", "tag", "-l", "-n1", "realistic-command-v1-frozen"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=120,
    ).stdout
    (logs / "GIT_COMMITS.txt").write_text(
        f"tag: {tags}\ncommits since freeze:\n{commits}", encoding="utf-8"
    )

    # tests/README so the copied files are self-explanatory.
    (STAGE / "tests" / "README.md").write_text(
        "# tests/\n\n"
        "These are verbatim copies of the six test files added by CD-1..CD-6\n"
        "(108 test cases).  In the repository they live in `tests/` and import\n"
        "`iron_bottom_sound` from `backend/src` via the pytest `pythonpath` setting.\n\n"
        "```bash\n"
        "cp tests/test_command_delay_*.py <repo>/tests/\n"
        "cd <repo> && .venv/bin/python -m pytest tests/test_command_delay_*.py -q\n"
        "```\n\n"
        "Coverage per file is listed in `../TEST_MANIFEST.md`.\n",
        encoding="utf-8",
    )

    files = sorted(path for path in STAGE.rglob("*") if path.is_file())
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            archive.write(path, arcname=str(path.relative_to(STAGE)))
    digest = sha256(OUTPUT)
    print(f"files: {len(files)}")
    for path in files:
        print(f"  {path.relative_to(STAGE)}")
    print(f"\nBUNDLE = {OUTPUT}")
    print(f"SHA256 = {digest}")
    shutil.rmtree(STAGE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
