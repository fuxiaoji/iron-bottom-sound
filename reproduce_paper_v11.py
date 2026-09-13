#!/usr/bin/env python3
"""One-click reproduction for the v11 manuscript.

  python reproduce_paper_v11.py                 # frozen results -> figures + PDF
  python reproduce_paper_v11.py --recompute-commitment   # re-run the matched-horizon MC
  python reproduce_paper_v11.py --recompute-figures      # figures only
  python reproduce_paper_v11.py --pdf-only
"""
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
PY = (str(REPO / ".venv" / "bin" / "python")
      if (REPO / ".venv" / "bin" / "python").exists() else sys.executable)
PAPER = REPO / "paper_v11"
V11 = REPO / "research" / "final_v11"
SEED_REGISTRY = {
    "main_18cells": 10000, "grid7_anchors": 20000,
    "horizon_anchors": 30000, "bridge_anchors": 40000,
    "symmetric_controls": 90000, "unit_tests": 0,
}


def run(cmd, cwd=None):
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=str(cwd or REPO))


def check():
    need = [V11 / "commitment_matched" / "main_18cells.csv",
            V11 / "commitment_matched" / "grid7_anchors.csv",
            V11 / "claim_registry_v11.csv"]
    missing = [str(p.relative_to(REPO)) for p in need if not p.exists()]
    if missing:
        raise SystemExit("missing frozen v11 results: " + ", ".join(missing))
    print("frozen v11 results present; seed registry:", SEED_REGISTRY)


def recompute():
    run([PY, "research/final_v11/commitment_matched/run_unit_tests_v11.py"])
    run([PY, "research/experiments/v11_commitment.py", "--mode", "main", "--seeds", "200"])
    run([PY, "research/experiments/v11_commitment.py", "--mode", "grid7", "--seeds", "100"])


def figures():
    run([PY, "research/final_v11/figures/make_fig4_v11.py"])
    run([PY, "research/final_v10/figures/make_figures_v10.py", "1", "7"])
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
    ap.add_argument("--recompute-commitment", action="store_true")
    ap.add_argument("--recompute-figures", action="store_true")
    ap.add_argument("--pdf-only", action="store_true")
    a = ap.parse_args()
    if a.pdf_only:
        pdf(); return
    if a.recompute_commitment:
        recompute()
    check()
    figures()
    pdf()


if __name__ == "__main__":
    main()
