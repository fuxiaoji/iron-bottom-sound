"""Assemble COMMAND_DELAY_V2_3_INTEGRITY_REPAIR_BUNDLE.zip.

The bundle's contents are fixed by the plan (§14), so this script's job is to refuse to
build an incomplete one: every required document must exist, the tests directory must hold
the batch's test files, and the code patch must be regenerated against the batch's base
commit rather than copied from a previous run.

Usage::

    .venv/bin/python research/command_delay/v2_3/build_v2_3_bundle.py
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTPUT = ROOT / "COMMAND_DELAY_V2_3_INTEGRITY_REPAIR_BUNDLE.zip"
STAGE = HERE / "bundle_stage"

# The plan's required documents, in order.
DOCS = (
    "00_EXECUTIVE_SUMMARY.md", "00_BASELINE_FREEZE.md", "01_COMM_ROUTE_AUDIT.md",
    "02_CAUSAL_INFORMATION_AUDIT.md", "03_MISSION_ORDER_AUDIT.md",
    "04_REPORTING_AND_RADIO_POLICY.md", "05_UNIT_AND_FACT_PROVENANCE.md",
    "06_GUNNERY_AUTHORITY_AUDIT.md", "07_MOVEMENT_AND_MODE_ISOLATION.md",
    "08_MODULE_DECOUPLING_AUDIT.md", "09_END_TO_END_BATTLE_AUDIT.md",
    "BUG_AND_RERUN_LOG.md", "DATA_MODEL_DIFF.md", "TEST_MANIFEST.md", "ROUTING_PROFILE.md",
)

TESTS = (
    "test_command_delay_routing_v23.py",
    "test_command_delay_causal_information_v23.py",
    "test_command_delay_mission_order_v23.py",
    "test_command_delay_reporting_v23.py",
    "test_command_delay_units_and_claims_v23.py",
    "test_command_delay_gunnery_authority_v23.py",
    "test_command_delay_move_together_v23.py",
    "test_command_delay_e2e_v23.py",
)

# Directories and files the patch carries, relative to the repo.
PATCH_PATHS = (
    "backend/src/iron_bottom_sound/command_delay.py",
    "backend/src/iron_bottom_sound/command_observation.py",
    "backend/src/iron_bottom_sound/communications/",
    "backend/src/iron_bottom_sound/formation_agents.py",
    "backend/src/iron_bottom_sound/formation_llm.py",
    "backend/src/iron_bottom_sound/formation_maneuver.py",
    "backend/src/iron_bottom_sound/formation_memory.py",
    "backend/src/iron_bottom_sound/formation_knowledge.py",
    "backend/src/iron_bottom_sound/fleet_llm.py",
    "backend/src/iron_bottom_sound/reporting.py",
    "backend/src/iron_bottom_sound/claims.py",
    "backend/src/iron_bottom_sound/target_priority.py",
    "backend/src/iron_bottom_sound/delegation.py",
    "backend/src/iron_bottom_sound/research_hooks.py",
    "backend/src/iron_bottom_sound/models.py",
    "backend/src/iron_bottom_sound/engine.py",
    "backend/src/iron_bottom_sound/realistic_command.py",
    "tests/",
    # research scripts only: the battle records, golden baselines and audit artefacts under
    # research/command_delay/ are data, and sweeping them in produced a 59 MB patch
    "research/command_delay/*.py",
    "research/command_delay/v2_3/*.py",
    "research/battle_video/*.py",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def main() -> int:
    missing = [name for name in DOCS if not (HERE / name).exists()]
    if missing:
        print("missing bundle documents: " + ", ".join(missing))
        print("(the bundle is not built from an incomplete batch)")
        return 1
    missing_tests = [name for name in TESTS if not (ROOT / "tests" / name).exists()]
    if missing_tests:
        print("missing test files: " + ", ".join(missing_tests))
        return 1
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)

    for name in DOCS:
        copy(HERE / name, STAGE / name)
    for name in ("baseline_manifest.json",):
        copy(HERE / name, STAGE / name)
    for name in TESTS:
        copy(ROOT / "tests" / name, STAGE / "tests" / name)
    (STAGE / "tests" / "README.md").write_text(
        "# tests/\n\n"
        "这些是本批次新增的八个测试文件（31 项），在仓库中位于 `tests/`，"
        "通过 pytest 的 `pythonpath = backend/src` 导入引擎。\n\n"
        "```bash\n"
        "cp tests/test_command_delay_*_v23.py <repo>/tests/ && cd <repo> && \\\n"
        "  .venv/bin/python -m pytest tests/test_command_delay_*_v23.py -q\n"
        "```\n\n"
        "逐文件覆盖见 `../TEST_MANIFEST.md`。\n",
        encoding="utf-8",
    )

    # logs and audit JSONs
    logs = STAGE / "logs"
    logs.mkdir()
    for path in sorted((HERE / "logs").glob("*")):
        if path.is_file():
            copy(path, logs / path.name)
    for name in ("full_pytest_cd12.log", "audit_golden_check.log"):
        source = ROOT / "research" / "command_delay" / "logs" / name
        if source.exists():
            copy(source, logs / name)
    for path in sorted((ROOT / "research" / "command_delay" / "audits").glob("*.json")):
        copy(path, logs / f"audit_{path.name}")
    copy(ROOT / "research" / "command_delay" / "golden" / "GOLDEN_INDEX.json",
         STAGE / "logs" / "GOLDEN_INDEX.json")

    # raw: the audits' own data
    raw = STAGE / "raw"
    raw.mkdir()
    for path in sorted((HERE / "raw").glob("*")):
        if path.is_file():
            copy(path, raw / path.name)
    for name in ("old_message_route_audit.csv", "ir1_route_audit_summary.json"):
        source = HERE / "raw" / name
        if source.exists():
            copy(source, raw / name)
    battle = ROOT / "research" / "command_delay" / "battle_v2_3"
    if battle.exists():
        for name in ("REPORT_V2_3.md", "ir9_assertions.json", "replay_verification.json",
                     "leak_scan.json", "leak_self_test.json", "driver.log"):
            source = battle / name
            if source.exists():
                copy(source, raw / f"battle_v2_3_{name}")
        # the record itself is large; the bundle carries the assertion summary and the
        # report, and points at the in-repo record for the rest
        (raw / "battle_v2_3_README.md").write_text(
            "# battle_v2_3/\n\n"
            "完整记录（battle_data.json、calls.jsonl、orders.jsonl、reports.jsonl、"
            "views/）留在仓库内 `research/command_delay/battle_v2_3/`，未复制进 zip"
            "（体积与可重演性考虑：指令批次 + 模型回复可逐阶段重演）。\n"
            "本目录只放核验结果与战报。\n",
            encoding="utf-8",
        )

    # code_patch: regenerated against the batch's base commit
    patch_dir = STAGE / "code_patch"
    patch_dir.mkdir()
    base = (HERE / "raw" / "baseline_commit.txt").read_text(encoding="utf-8").strip()
    spec = " ".join(PATCH_PATHS)
    diff = subprocess.run(
        ["git", "diff", base, "--stat"] + list(PATCH_PATHS),
        cwd=ROOT, capture_output=True, text=True,
    ).stdout
    full = subprocess.run(
        ["git", "diff", base, "--"] + list(PATCH_PATHS),
        cwd=ROOT, capture_output=True, text=True,
    ).stdout
    (patch_dir / "v2_3_repair.patch").write_text(full, encoding="utf-8")
    (patch_dir / "00_READ_ME.md").write_text(
        "# code_patch/\n\n"
        f"`v2_3_repair.patch` 相对本批次基线提交 `{base}`，覆盖：\n\n"
        f"```\n{spec}\n```\n\n"
        "应用：\n\n"
        "```bash\n"
        f"git checkout {base}\n"
        "git apply --stat code_patch/v2_3_repair.patch\n"
        "git apply       code_patch/v2_3_repair.patch\n"
        "```\n\n"
        "注意：patch 不含 `research/command_delay/v2_3/raw/battle_em01/`（旧证据副本，"
        "已在 .gitignore 中）与对局大记录。\n",
        encoding="utf-8",
    )
    (patch_dir / "DIFFSTAT.txt").write_text(diff, encoding="utf-8")

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
