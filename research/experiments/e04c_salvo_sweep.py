"""E04c: salvo-size sweep -- is denial a function of threat thickness?

For each geometry and seed, the attacker's legal launches are sorted by
expected hits and the hazard of the top-k launches is combined
(complemented) for k = 1, 2, 4, and all available.  V_denial(k),
V_direct(k) and route_changed(k) are recorded, giving the
threat-thickness response curve that the single-launch protocol cannot
identify.

Output: research/results/e04salvo/{sweep.csv, results.json, report.md,
fig_e04salvo_curve.png}
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

from e04_min_denial import (  # noqa: E402
    CA,
    DD,
    GEOMETRIES,
    as_cells,
    drive_to_torpedo_phase,
    setup,
)
OUT = None
from iron_bottom_sound.models import Phase, Side  # noqa: E402

CA_VALUE = 11.0
SALVO_LEVELS = (1, 2, 4, 6, None)  # None = all
SEEDS = range(1, 31)
OUT = REPO / "research" / "results" / "e04salvo"


def measure_salvo(geometry: str, seed: int):
    engine, state = setup(geometry, seed)
    state = drive_to_torpedo_phase(engine, state)
    if state is None or state.phase != Phase.TORPEDO_PLANNING:
        return None
    from iron_bottom_sound.models import HexCoord  # noqa: F401

    target = state.ships[CA] if CA in state.ships else state.ships[
        "IBS-U-USN-NORTHAMPTON"]
    dd = state.ships[DD]
    if not target.position or target.sunk or not dd.position:
        return None

    cands = engine.movement_candidates(state, target, include_plans=True)
    options = []
    for entry in cands.get("reachable") or []:
        plan = entry.get("plan")
        if not plan:
            continue
        end_hex = HexCoord(q=entry["hex"]["q"], r=entry["hex"]["r"])
        heading = (entry.get("final_headings") or [target.heading])[0]
        J = float(engine.ship_gun_pressure(state, target, position=end_hex,
                                           heading=heading,
                                           target_hexes=[dd.position]))
        route, _f = engine.movement_trajectory(target, plan)
        options.append({"J": J, "route": route})
    if len(options) < 2:
        return None

    assist = engine.torpedo_assist(state, Side.AXIS, target_id=target.id)
    launches = [l for l in assist.get("combos", [])
                if (l.get("expected_hits") or 0) > 0]
    if not launches:
        return None
    launches.sort(key=lambda l: -float(l.get("expected_hits", 0.0)))

    Js = np.array([o["J"] for o in options])
    idx0 = int(np.argmax(Js))

    def hazard_of(subset):
        H = np.stack([single_hazard(l) for l in subset])
        return 1.0 - np.prod(1.0 - np.clip(H, 0.0, 1.0), axis=0)

    def single_hazard(launch):
        track_cells = []
        for key in ("predicted_path", "path", "track", "trajectory"):
            if launch.get(key):
                track_cells = [c for c in (as_cells(x) for x in launch[key]) if c]
                break
        intercept = (as_cells(launch.get("intercept_hex"))
                     if launch.get("intercept_hex") else None)
        p_hit = float(launch.get("hit_probability")
                      or min(1.0, launch.get("expected_hits", 0.0)))
        hs = np.zeros(len(options))
        for i, o in enumerate(options):
            h = 0.0
            for cell, _h in o["route"]:
                if intercept is not None and cell.distance(intercept) <= 1:
                    h += p_hit
                for tc in track_cells:
                    if cell == tc:
                        h += p_hit
            hs[i] = min(1.0, h)
        return hs

    rows = []
    seen_k = set()
    for k in SALVO_LEVELS:
        subset = launches if k is None else launches[:k]
        kk = len(subset)
        if kk in seen_k:
            continue  # deduplicate: distinct levels can yield the same subset
        seen_k.add(kk)
        haz = hazard_of(subset)
        e_total = float(sum(float(l.get("expected_hits", 0.0) or 0.0)
                            for l in subset))
        idxT = int(np.argmax(Js - lam_scale(Js) * haz))
        rows.append({
            "geometry": geometry, "seed": seed, "k": kk,
            "e_total": e_total,
            "v_direct": e_total * CA_VALUE,
            "v_denial": float(max(0.0, Js[idx0] - Js[idxT])),
            "v_denial_raw": float(Js[idx0] - Js[idxT]),
            "route_changed": int(idx0 != idxT),
        })
    return rows


def lam_scale(Js):
    return max(float(Js.max()), 1e-6)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for geometry in GEOMETRIES:
        for seed in SEEDS:
            r = measure_salvo(geometry, seed)
            if r:
                rows.extend(r)
    if not rows:
        print("no samples")
        return
    with (OUT / "sweep.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    agg = {}
    for k in (1, 2, 4, 6):
        sel = [r for r in rows if r["k"] == k]
        low = [r for r in sel if r["e_total"] / max(r["k"], 1) < 0.15]
        agg[str(k)] = {
            "n": len(sel),
            "mean_v_denial": float(np.mean([r["v_denial"] for r in sel])),
            "mean_v_direct": float(np.mean([r["v_direct"] for r in sel])),
            "route_changed": float(np.mean([r["route_changed"] for r in sel])),
            "low_hit_mean_v_denial": (float(np.mean([r["v_denial"] for r in low]))
                                      if low else None),
            "low_hit_n": len(low),
        }
    result = {"aggregate_by_k": agg, "n_rows": len(rows)}
    (OUT / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ks = sorted(int(k) for k in agg)
    colors = {"close_high_hit": "#d62728", "mid_low_hit": "#1f77b4",
              "long_low_hit": "#2ca02c"}
    for geometry in GEOMETRIES:
        xs, ys = [], []
        for k in ks:
            sel = [r for r in rows if r["geometry"] == geometry and r["k"] == k]
            if sel:
                xs.append(k)
                ys.append(np.mean([r["v_denial"] for r in sel]))
        ax.plot(xs, ys, marker="o", label=geometry, color=colors[geometry])
    ax.set_xlabel("salvo size k (best-k launches)")
    ax.set_ylabel("V_denial (gun-position value)")
    ax.set_title("E04c: denial vs threat thickness")
    ax.legend()
    fig.savefig(OUT / "fig_e04salvo_curve.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    lines = ["# E04c salvo-size sweep", ""]
    for k, st in agg.items():
        lines.append(f"- k={k}: n={st['n']} V_denial={st['mean_v_denial']:.4f} "
                     f"route_changed={100*st['route_changed']:.0f}% "
                     f"V_direct={st['mean_v_direct']:.2f}")
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2)[:1000])


if __name__ == "__main__":
    main()
