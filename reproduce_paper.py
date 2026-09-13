#!/usr/bin/env python3
"""One-click reproduction entry point for the IBS formation-game paper.

Usage:
  python reproduce_paper.py            # figures 1-6 + summaries + PDF (uses cached results)
  python reproduce_paper.py --full     # ALSO re-runs the two core solvers (hours)
  python reproduce_paper.py --pdf-only # only the LaTeX compile

Outputs: paper_v8/figures/fig{1..6}_*.png,
         research/final_v8/commitment/certification_{summary.json,report.md},
         research/results/final_v7/must2_report.md (engine transfer summary),
         paper_v8/main.pdf.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
PY = str(REPO / ".venv" / "bin" / "python") if (REPO / ".venv" / "bin" / "python").exists() else sys.executable


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=str(cwd or REPO))


def figures() -> None:
    run([PY, "research/final_v8/figures/make_figures.py", "1", "2", "5", "6"])
    # fig3 needs the DP grid (fast); fig4 needs the certification CSV
    if not (REPO / "research/final_v8/figures/fig3_grid.json").exists():
        run([PY, "research/final_v8/figures/make_fig3_data.py"])
    run([PY, "research/final_v8/figures/make_figures.py", "3"])
    if (REPO / "research/final_v8/commitment/certification_results.csv").exists():
        run([PY, "research/final_v8/figures/make_figures.py", "4"])
    else:
        print("!! certification_results.csv missing -- run --full first; fig4 skipped")


def full() -> None:
    print("== FULL reproduction: re-running the two core solvers (hours) ==", flush=True)
    run([PY, "research/experiments/t1_certification.py"])
    run([PY, "research/experiments/must2_matched_engine.py"])
    figures()


def pdf() -> None:
    for _ in range(2):
        run(["pdflatex", "-interaction=nonstopmode", "main.tex"], cwd=REPO / "paper_v8")
    out = REPO / "paper_v8" / "main.pdf"
    print(f"OK  {out} ({out.stat().st_size // 1024} KB)" if out.exists() else "PDF FAILED")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="re-run core solvers first")
    ap.add_argument("--pdf-only", action="store_true")
    a = ap.parse_args()
    if a.pdf_only:
        pdf()
        return
    if a.full:
        full()
    else:
        figures()
    pdf()


if __name__ == "__main__":
    main()
