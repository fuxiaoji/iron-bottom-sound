#!/usr/bin/env python3
"""One-click reproduction entry point for the v9 paper (v9 section 41).

Usage:
  python reproduce_paper_v9.py                 # frozen exact results -> figures,
                                               # tables, summaries, PDF
  python reproduce_paper_v9.py --recompute-exact   # re-run the exact Grid-5/Grid-7
                                               # commitment certification first
  python reproduce_paper_v9.py --pdf-only      # LaTeX compile only

The default path never re-runs the exhaustive solvers: it uses the frozen
result files under research/final_v9/commitment_exact/ so that paper
reproduction is fast and deterministic.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
PY = (str(REPO / ".venv" / "bin" / "python")
      if (REPO / ".venv" / "bin" / "python").exists() else sys.executable)
EXACT = REPO / "research" / "final_v9" / "commitment_exact"
PAPER = REPO / "paper_v8"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=str(cwd or REPO))


def check_exact_results() -> None:
    need = ["exact_grid5_results.csv", "exact_grid7_results.csv",
            "exact_certification_summary.json", "exact_h1_baselines.json"]
    missing = [f for f in need if not (EXACT / f).exists()]
    if missing:
        raise SystemExit(f"missing frozen exact results: {missing}\n"
                         f"run with --recompute-exact first")
    print(f"frozen exact results present in {EXACT.relative_to(REPO)}")


def recompute_exact() -> None:
    print("== recomputing the exact finite-game certification ==", flush=True)
    run([PY, "research/experiments/t1_exact_discrete_certification.py",
         "--grids", "5,7", "--phase", "all"])
    run([PY, "research/experiments/t1_exact_discrete_certification.py",
         "--grids", "5,7", "--phase", "sanity"])


def figures() -> None:
    # v9 figure rebuild: Fig3/4/5/6 come from the v9 exact data + engine results
    run([PY, "research/final_v9/make_figures_v9.py", "3", "4", "5", "6"])
    # Fig1/Fig2 are unchanged from the v8 rebuild
    run([PY, "research/final_v8/figures/make_figures.py", "1", "2"])


def pdf() -> None:
    for _ in range(2):
        run(["pdflatex", "-interaction=nonstopmode", "main.tex"], cwd=PAPER)
    out = PAPER / "main.pdf"
    if not out.exists():
        raise SystemExit("PDF build failed")
    print(f"OK  {out} ({out.stat().st_size // 1024} KB)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--recompute-exact", action="store_true")
    ap.add_argument("--pdf-only", action="store_true")
    a = ap.parse_args()
    if a.pdf_only:
        pdf()
        return
    if a.recompute_exact:
        recompute_exact()
    check_exact_results()
    figures()
    pdf()


if __name__ == "__main__":
    main()
