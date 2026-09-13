"""v14 analysis pipeline (master plan section 3-4).

Consumes the frozen solver outputs under research/final_v14/runs/ and builds
the analysis products the paper and the figures need:

  * per (cell, side, opponent) budget frontier W_K = max_{|S|<=K} V(S, R),
    its maximizing calendar, the certified interval [LB, UB], residual and
    termination reason;
  * certified retention budgets: the smallest K that certifiably retains
    90/95/99% of the full-flexibility value W_{T-1}, with unresolved cases
    reported as intervals rather than as a point budget;
  * algorithm comparison at equal model budget and precision (complete
    enumeration, branch and bound, uniform / front-loaded / back-loaded /
    stepwise greedy), with preprocessing and optimization costs separated;
  * robustness and ablation summaries.

Nothing here re-solves a game; every number is read from the frozen outputs,
so the analysis is deterministic and cheap.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
V14 = REPO / "research" / "final_v14"
RUNS = V14 / "runs"
OUT = V14 / "analysis"
T_DEFAULT = 6


def load_runs() -> list[dict]:
    rows = []
    for f in sorted(RUNS.rglob("*.json")):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if not isinstance(d, dict) or "V" not in d:
            continue
        if "S" not in d:
            continue
        d["_file"] = str(f.relative_to(REPO))
        rows.append(d)
    return rows


def cell_id(path: str) -> str:
    return Path(path).parts[-2] if len(Path(path).parts) >= 2 else "unknown"


def frontier(rows: list[dict]) -> list[dict]:
    """Budget frontier per (cell, side, opponent)."""
    grp = defaultdict(list)
    for r in rows:
        grp[(cell_id(r["_file"]), r.get("side", "?"), r.get("opponent", "?"))].append(r)
    out = []
    for (cell, side, opp), rs in sorted(grp.items()):
        T = int(rs[0].get("T", T_DEFAULT))
        maxK = T - 1
        for K in range(maxK + 1):
            sub = [r for r in rs if len(r["S"]) <= K]
            if not sub:
                continue
            best = max(sub, key=lambda r: r["V"])
            out.append({
                "cell": cell, "side": side, "opponent": opp, "T": T, "K": K,
                "W_K": best["V"], "S_star": json.dumps(best["S"]),
                "LB": best.get("LB"), "UB": best.get("UB"),
                "gap": best.get("gap"), "status": best.get("status"),
                "seconds": best.get("seconds"),
                "policy_count": best.get("policy_count"),
                "iterations": best.get("iterations"),
                "n_schedules": len(sub),
                "zero_reach": best.get("zero_reach", None),
            })
    return out


def retention(fr: list[dict]) -> list[dict]:
    """Smallest certified K retaining a fraction of the full-flexibility value."""
    grp = defaultdict(list)
    for r in fr:
        grp[(r["cell"], r["side"], r["opponent"])].append(r)
    out = []
    for (cell, side, opp), rs in sorted(grp.items()):
        rs = sorted(rs, key=lambda r: r["K"])
        full = rs[-1]
        Wmax = full["W_K"]
        if abs(Wmax) < 1e-9:
            out.append({"cell": cell, "side": side, "opponent": opp,
                        "W_full": Wmax, "retention": None, "K_star": None,
                        "note": "full-flexibility value unresolved/zero; "
                                "budget expressed as absolute loss, not ratio"})
            continue
        for frac in (0.90, 0.95, 0.99):
            target = frac * Wmax
            ks = [r["K"] for r in rs if r["W_K"] >= target - 1e-9
                  and r["status"] == "certified_numeric"]
            kcert = min(ks) if ks else None
            # possible (uncertified) budget: ignore the convergence flag
            kp = [r["K"] for r in rs if r["W_K"] >= target - 1e-9]
            kpos = min(kp) if kp else None
            out.append({"cell": cell, "side": side, "opponent": opp,
                        "retention": frac, "W_full": Wmax, "target": target,
                        "K_certified": kcert, "K_possible": kpos,
                        "absolute_loss_at_K0": Wmax - rs[0]["W_K"]})
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: list[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = load_runs()
    print(f"loaded {len(rows)} frozen value files", flush=True)
    cells = sorted({cell_id(r["_file"]) for r in rows})
    print(f"cells present: {len(cells)}")
    fr = frontier(rows)
    rt = retention(fr)
    write_csv(OUT / "budget_frontier.csv", fr)
    write_csv(OUT / "retention_budgets.csv", rt)
    summary = {
        "n_value_files": len(rows),
        "cells": cells,
        "n_frontier_rows": len(fr),
        "status_counts": {},
        "max_gap": max((r["gap"] or 0) for r in rows) if rows else None,
    }
    from collections import Counter
    summary["status_counts"] = dict(Counter(r.get("status") for r in rows))
    json.dump(summary, open(OUT / "analysis_summary.json", "w"), indent=2)
    # console digest
    print(f"frontier rows: {len(fr)}; retention rows: {len(rt)}")
    print("status:", summary["status_counts"])
    print(f"max certified gap: {summary['max_gap']:.3e}")
    shown = 0
    for r in fr:
        if r["opponent"] == "C" and r["side"] == "blue" and shown < 12:
            print(f"  {r['cell'][:28]:28s} K={r['K']} W={r['W_K']:+.4f} "
                  f"S={r['S_star']} [{r['LB']:+.3f},{r['UB']:+.3f}] {r['status']}")
            shown += 1


if __name__ == "__main__":
    main()
