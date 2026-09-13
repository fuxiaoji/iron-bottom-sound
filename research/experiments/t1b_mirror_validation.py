"""T1b: mirror-consistency validation of the certified sign pattern.

Motivation (honesty check on the certification machinery): in cells where the
true game value is provably zero by exchange symmetry (head-on and crossing at
eta_r = eta_v = 1; the seed payoff matrix is exactly skew-symmetric), the
Double Oracle restricted value nevertheless reports up to +5.6.  That quantifies
an UPWARD BIAS of the restricted-game lower estimate (the restricted defender
set fails to punish).  Because the bias is upward, certified NEGATIVE intervals
are safe, but certified POSITIVE intervals could in principle be inflated.

Independent check: the game is antisymmetric under swapping the two formations
and inverting the range ratio.  So for the mirrored range ratios
eta_r' = 1/eta_r, the commitment value should flip sign:
      P_6(eta_r')  ~=  -P_6(eta_r).
If the four mirrored cells reproduce the sign flip, the sign pattern is
confirmed by a symmetry of the game rather than by the (biased) bound
machinery.

Cells: 3 geometries x eta_r in {1/0.8, 1/1.2} x eta_v = 1.0, at H = 6 and 1.

Output: research/final_v8/commitment/mirror_validation.csv + summary line.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

from research.experiments.t1_certification import run_cell  # noqa: E402

OUT = REPO / "research" / "final_v8" / "commitment"
MIRRORS = [(g, 1.0 / er_source, ev) for g in ("head_on", "parallel", "crossing")
           for er_source in (0.8, 1.2) for ev in (1.0,)]


def main() -> None:
    t0 = time.time()
    jobs = []
    for g, er, ev in MIRRORS:
        jobs.append((g, er, ev, 6, 6, 8))   # H=6 with the pass-2 iteration budget
        jobs.append((g, er, ev, 6, 1, 2))   # H=1 baseline
    print(f"[T1b] {len(jobs)} mirror-consistency runs", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(run_cell, j): j for j in jobs}
        for fut in as_completed(futs):
            r = fut.result()
            rows.append(r)
            print(f"[T1b] {r['geometry']:9s} er={r['eta_r']:.4f} H={r['H']}: "
                  f"L={r['L']:+.3f} U={r['U']:+.3f} gap={r['rel_gap']:.0%} "
                  f"({r['seconds']}s)", flush=True)

    h6 = {(r["geometry"], round(r["eta_r"], 4)): r for r in rows if r["H"] == 6}
    h1 = {(r["geometry"], round(r["eta_r"], 4)): r for r in rows if r["H"] == 1}
    out = []
    flips = 0
    total = 0
    for (g, er), r in sorted(h6.items()):
        b1 = h1[(g, er)]
        lo, hi = r["L"] - b1["U"], r["U"] - b1["L"]
        point = (r["L"] + r["U"]) / 2 - (b1["L"] + b1["U"]) / 2
        src = 1.0 / er            # the original eta_r this cell mirrors
        sign = 1 if point > 0 else -1
        predicted = -1 if src > 1 else 1     # mirror of a long-range cell is negative
        ok = sign == predicted
        flips += ok
        total += 1
        out.append({"geometry": g, "eta_r_mirror": round(er, 4),
                    "eta_r_source": src, "P_lower": round(lo, 4),
                    "P_upper": round(hi, 4), "point": round(point, 4),
                    "predicted_sign": predicted, "consistent": int(ok)})
    with open(OUT / "mirror_validation.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    summary = {"n_cells": total, "sign_consistent": flips,
               "consistent_fraction": flips / max(total, 1),
               "wall_time_s": round(time.time() - t0, 1)}
    json.dump(summary, open(OUT / "mirror_validation_summary.json", "w"), indent=2)
    print(f"[T1b] DONE mirror-consistent {flips}/{total} in "
          f"{time.strftime('%H:%M:%S', time.gmtime(time.time() - t0))}", flush=True)


if __name__ == "__main__":
    main()
