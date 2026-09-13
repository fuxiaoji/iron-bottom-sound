#!/usr/bin/env python3
"""One-click reproduction for the v10 manuscript.

  python reproduce_paper_v10.py                 # frozen results -> figures + PDF
  python reproduce_paper_v10.py --recompute     # re-run bridge + LF certification
  python reproduce_paper_v10.py --pdf-only

The default path never re-runs the solvers: it uses the frozen v10 results
under research/final_v10/, so paper reproduction is fast and deterministic.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
PY = (str(REPO / ".venv" / "bin" / "python")
      if (REPO / ".venv" / "bin" / "python").exists() else sys.executable)
PAPER = REPO / "paper_v10"
V10 = REPO / "research" / "final_v10"


def run(cmd, cwd=None):
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=str(cwd or REPO))


def check():
    need = [V10 / "commitment_lf_exact" / "lf_grid5_results.csv",
            V10 / "commitment_lf_exact" / "lf_grid7_results.csv",
            V10 / "bridge" / "bridge_cells.csv",
            V10 / "formation_tests" / "unit_test_results.json"]
    missing = [str(p.relative_to(REPO)) for p in need if not p.exists()]
    if missing:
        raise SystemExit("missing frozen v10 results: " + ", ".join(missing) +
                         "\nrun with --recompute first")
    print("frozen v10 results present")


def recompute():
    run([PY, "research/final_v10/formation_tests/run_unit_tests.py"])
    run([PY, "research/experiments/v10_bridge.py"])
    run([PY, "research/experiments/v10_commitment_lf_exact.py",
         "--grids", "5,7", "--models", "lf,rigid"])
    run([PY, "research/experiments/v10_sensitivity.py"])


def figures():
    run([PY, "research/final_v10/figures/make_figures_v10.py", "1", "4", "7"])
    run([PY, "research/final_v9/make_figures_v9.py", "3", "5", "6"])
    run([PY, "research/final_v8/figures/make_figures.py", "2"])


def pdf():
    for _ in range(2):
        run(["pdflatex", "-interaction=nonstopmode", "main.tex"], cwd=PAPER)
    out = PAPER / "main.pdf"
    if not out.exists():
        raise SystemExit("PDF build failed")
    print(f"OK  {out} ({out.stat().st_size // 1024} KB)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--recompute", action="store_true")
    ap.add_argument("--pdf-only", action="store_true")
    a = ap.parse_args()
    if a.pdf_only:
        pdf()
        return
    if a.recompute:
        recompute()
    check()
    figures()
    pdf()


if __name__ == "__main__":
    main()
