#!/usr/bin/env python3
"""One-click reproduction for the v14 study.

  python reproduce_v14.py                 # verify freezes -> analysis -> tables
                                          # -> figures -> PDF (no re-solving)
  python reproduce_v14.py --run-phases    # ALSO run the frozen solver phases
                                          # (development/test/robustness/ablation)
  python reproduce_v14.py --check-only    # integrity checks only
  python reproduce_v14.py --pdf-only      # LaTeX build only

The default path never re-solves a game: it reads the frozen solver outputs
under research/final_v14/runs/ and regenerates the analysis, the four tables
and the eight figures deterministically.  Every stage records what it did in
research/final_v14/reproduction_log.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
PY = (str(REPO / ".venv" / "bin" / "python")
      if (REPO / ".venv" / "bin" / "python").exists() else sys.executable)
V14 = REPO / "research" / "final_v14"
PAPER = REPO / "paper_v14"
LOG: list[dict] = []


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest()


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    t0 = time.time()
    subprocess.run(cmd, check=True, cwd=str(cwd or REPO))
    LOG.append({"cmd": cmd, "seconds": round(time.time() - t0, 2)})


def verify() -> None:
    """Frozen execution code and design must match their recorded hashes."""
    freeze = json.loads((V14 / "RUN_FREEZE.json").read_text())
    for rel, want in freeze["core_hashes"].items():
        p = REPO / rel
        if not p.exists():
            raise SystemExit(f"missing frozen dependency: {rel}")
        got = sha(p)
        if got != want:
            raise SystemExit(f"frozen dependency changed: {rel}\n  want {want}\n  got  {got}")
    design = json.loads((V14 / "DESIGN.json").read_text())
    if sha(V14 / "DESIGN.json") != freeze["design_sha256"]:
        raise SystemExit("DESIGN.json changed since the freeze")
    print(f"freeze verified: {len(freeze['core_hashes'])} dependencies, "
          f"{len(design['cells'])} design cells")
    LOG.append({"stage": "verify_freeze", "ok": True})


def run_phases() -> None:
    for phase in ("development", "test", "robustness", "ablation"):
        run([PY, "-m", "research.experiments.v14_run", "--phase", phase])


def analysis() -> None:
    run([PY, "research/final_v14/analysis_v14.py"])
    run([PY, "research/final_v14/make_tables_v14.py"])
    run([PY, "research/final_v14/make_figures_v14.py"])


def pdf() -> None:
    for name in ("main.tex", "supplement.tex"):
        for _ in range(2):
            run(["pdflatex", "-interaction=nonstopmode", name], cwd=PAPER)
    for name, out in (("main", PAPER / "main.pdf"),
                      ("supplement", PAPER / "supplement.pdf")):
        if not out.exists():
            raise SystemExit(f"{name} PDF build failed")
        print(f"OK  {out} ({out.stat().st_size // 1024} KB)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-phases", action="store_true")
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--pdf-only", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    if a.pdf_only:
        pdf(); return
    verify()
    if a.check_only:
        print("integrity checks passed"); return
    if a.run_phases:
        run_phases()
    analysis()
    pdf()
    (V14 / "reproduction_log.json").write_text(
        json.dumps({"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                   time.gmtime()),
                    "total_seconds": round(time.time() - t0, 1),
                    "python": sys.version, "log": LOG}, indent=2),
        encoding="utf-8")
    print(f"reproduction complete in {time.time() - t0:.0f}s; "
          f"log: research/final_v14/reproduction_log.json")


if __name__ == "__main__":
    main()
