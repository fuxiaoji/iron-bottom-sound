"""FIRE_SEARCH vs LEGAL_FIRE_HEURISTIC calibration on 10-20 states."""
from __future__ import annotations
import json, statistics, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from m22_core import (IronBottomEngine, Phase, Side, fire_search,
                      legal_fire_heuristic, materialize_batch, net_eh)
from m22_core import REPO  # noqa
sys.path.insert(0, str(REPO / "research" / "m2_1" / "scripts"))
from mg.micro import reach
from mg.mg_cases import ships_of

OUT = Path(__file__).resolve().parents[1] / "metrics"
SCEN = ("IBS-S-01", "IBS-S-03", "IBS-S-EM-01")

rows = []
t0 = time.time()
for scen in SCEN:
    for seed in range(1, 8):
        for turn in (2, 5):
            eng, st, se = reach(scen, seed, Phase.GUNNERY, turn)
            if st is None:
                continue
            for side in (Side.ALLIES, Side.AXIS):
                h = net_eh(eng, st, side, fire=legal_fire_heuristic)
                s = net_eh(eng, st, side, fire=fire_search)
                # rank of the top target by EH under each method
                rows.append({
                    "scenario": scen, "seed": seed, "turn": turn, "side": side.value,
                    "heuristic_net_eh": h["net_eh"], "search_net_eh": s["net_eh"],
                    "heuristic_own_eh": h["own_eh"], "search_own_eh": s["own_eh"],
                    "same_target_count": sum(1 for k, v in h["own"]["targets"].items()
                                             if s["own"]["targets"].get(k) == v),
                    "n_ships": len(h["own"]["targets"]),
                })
                if len(rows) >= 20:
                    break
            if len(rows) >= 20:
                break
        if len(rows) >= 20:
            break
    if len(rows) >= 20:
        break

def _ranks(vals):
    """Tie-aware average ranks (the naive value->index map collapses ties and
    produced a bogus -0.45 correlation, M22-F1)."""
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    ranks = [0.0] * len(vals)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman(a, b):
    n = len(a)
    if n < 3:
        return None
    ra, rb = _ranks(a), _ranks(b)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    da = sum((x - ma) ** 2 for x in ra) ** 0.5
    db = sum((y - mb) ** 2 for y in rb) ** 0.5
    return None if da * db == 0 else num / (da * db)

h_vals = [r["heuristic_net_eh"] for r in rows]
s_vals = [r["search_net_eh"] for r in rows]
same_frac = [r["same_target_count"] / max(1, r["n_ships"]) for r in rows]
summary = {
    "n_states": len(rows),
    "spearman_net_eh": spearman(h_vals, s_vals),
    "mean_abs_net_eh_diff": statistics.mean([abs(a - b) for a, b in zip(h_vals, s_vals)]) if rows else None,
    "max_abs_net_eh_diff": max([abs(a - b) for a, b in zip(h_vals, s_vals)], default=None),
    "mean_same_target_fraction": statistics.mean(same_frac) if same_frac else None,
    "mean_rel_diff_own_eh": statistics.mean(
        [abs(r["search_own_eh"] - r["heuristic_own_eh"]) / max(1e-9, r["heuristic_own_eh"])
         for r in rows]) if rows else None,
    "wall_seconds": time.time() - t0,
    "verdict": None,
}
corr = summary["spearman_net_eh"]
rel = summary["mean_rel_diff_own_eh"]
if corr is not None and corr >= 0.9 and (rel or 0) <= 0.05:
    summary["verdict"] = "HEURISTIC_ADEQUATE (rank corr >=0.9, mean rel diff <=5%)"
elif corr is not None and corr >= 0.7:
    summary["verdict"] = "HEURISTIC_PARTIAL (rank corr >=0.7) - report both"
else:
    summary["verdict"] = "HEURISTIC_INADEQUATE - use FIRE_SEARCH for mechanism metrics"
OUT.mkdir(exist_ok=True)
(OUT / "fire_calibration.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=1))
print(json.dumps(summary, indent=1))
