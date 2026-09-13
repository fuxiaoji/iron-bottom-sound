"""E04-min: independent decision-level cross-check of torpedo denial (plan 5.2).

Standalone minimal protocol.  At the first torpedo-planning phase of a 1v1
DD-vs-CA engagement, the target's best movement plan is compared with and
without the salvo hazard of the attacker's full legal launch set:

    tau0* = argmax J  over legal movement plans, where J(hex, heading) is
            engine.ship_gun_pressure at the hypothetical endpoint;
    tauT* = argmax (J - lam * hazard_total), hazard_total combines every
            launch's engine-projected track intersections (this-turn route
            plus straight continuation to the intercept turn), weighted by
            engine.torpedo_hit_probability;
    V_denial = J(tau0*) - J(tauT*);  route_changed = (tau0* != tauT*).

lambda = J(tau0*): a torpedo hit forfeits the ship's gun-position value for
the window (engine collision effects remove ~5 of 12 hull and -7 MF).
lambda sensitivity is recorded.  The decision objective contains only the
threat, so the threat-only regime (plan condition D) holds by construction.

Output: research/results/e04min/{samples.csv, results.json, report.md}
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

from iron_bottom_sound.data import register_custom_scenario  # noqa: E402
from iron_bottom_sound.engine import IronBottomEngine  # noqa: E402
from iron_bottom_sound.models import (  # noqa: E402
    HexCoord,
    MovementOrder,
    OrderBatch,
    Phase,
    Side,
)
from iron_bottom_sound.tactical import PROFILES, TacticalCommander  # noqa: E402

OUT = REPO / "research" / "results" / "e04min"

DD = "IBS-U-IJN-FUBUKI"
CA = "IBS-U-USN-NEW-ORLEANS"
CA_VALUE = 11.0
LOW_HIT = 0.15

_B = HexCoord(q=10, r=4)


def _pos(dq, dr):
    return HexCoord(q=10 + dq, r=4 + dr).label


# scan-selected geometries: close broadside (high direct-hit control) and two
# low-direct-hit geometries with valuable gun positions at stake
GEOMETRIES = {
    "close_high_hit": (_B.label, 3, _pos(6, -4), 4),
    "mid_low_hit": (_B.label, 2, _pos(8, 2), 4),
    "long_low_hit": (_B.label, 3, _pos(10, 0), 5),
}


def setup(geometry: str, seed: int):
    bhex, bh, rhex, rh = GEOMETRIES[geometry]
    definition = {
        "id": f"IBS-CUSTOM-E04M-{geometry}", "title": f"E04min {geometry}",
        "turns": 4, "visibility": {"axis": 16, "allies": 16},
        "optional_rules": [],
        "ships": [
            {"id": DD, "name": "Fubuki", "side": "axis",
             "position": bhex, "heading": bh, "speed": 5},
            {"id": CA, "name": "NewOrleans", "side": "allies",
             "position": rhex, "heading": rh, "speed": 5},
        ],
    }
    register_custom_scenario(definition)
    engine = IronBottomEngine()
    state = engine.reset(definition["id"], seed=seed)
    return engine, state


def drive_to_torpedo_phase(engine: IronBottomEngine, state):
    gid = state.game_id
    ally = TacticalCommander(PROFILES["balanced"])
    order_phases = {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                    Phase.TORPEDO_PLANNING, Phase.GUNNERY}
    guard = 0
    while state.phase != Phase.COMPLETE and guard < 60:
        guard += 1
        ph = state.phase
        if ph == Phase.TORPEDO_PLANNING:
            return state
        if ph in order_phases:
            batch = OrderBatch(side=Side.AXIS, phase=ph)
            if ph == Phase.MOVEMENT_PLANNING:
                obs = engine.observe(gid, Side.AXIS)
                batch = OrderBatch(
                    side=Side.AXIS, phase=ph,
                    movement=[MovementOrder(ship_id=s.id, plan="0")
                              for s in obs.ships
                              if s.side == Side.AXIS and s.position is not None])
            engine.submit_orders(gid, batch)
            engine.submit_orders(gid, ally.choose_plan(engine, gid, Side.ALLIES)[1])
        engine.advance(gid)
        state = engine.get(gid)
    return None


def as_cells(item):
    if isinstance(item, HexCoord):
        return item
    if isinstance(item, dict) and "q" in item:
        return HexCoord(q=item["q"], r=item["r"])
    if isinstance(item, str):
        try:
            return HexCoord.from_label(item)
        except Exception:
            return None
    return None


def continuation_cells(engine, state, ship, route, turns):
    """Straight continuation of a route beyond the one-turn plan window."""
    if not route:
        return []
    last_hex, last_heading = route[-1]
    cells = []
    cell = last_hex
    for _ in range(int(turns) * max(1, ship.current_speed)):
        try:
            cell = cell.neighbor(last_heading, columns=state.map_columns,
                                 rows=state.map_rows)
        except Exception:
            break
        cells.append(cell)
    return cells


def measure(geometry: str, seed: int) -> list[dict] | None:
    engine, state = setup(geometry, seed)
    state = drive_to_torpedo_phase(engine, state)
    if state is None or state.phase != Phase.TORPEDO_PLANNING:
        return None
    target = state.ships[CA]
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
        options.append({"plan": plan, "J": J, "route": route})
    if len(options) < 2:
        return None

    assist = engine.torpedo_assist(state, Side.AXIS, target_id=CA)
    launches = [l for l in assist.get("combos", [])
                if (l.get("expected_hits") or 0) > 0]
    if not launches:
        return None

    Js = np.array([o["J"] for o in options])

    def launch_hazard(launch):
        track_cells = []
        for key in ("predicted_path", "path", "track", "trajectory"):
            if launch.get(key):
                track_cells = [c for c in (as_cells(x) for x in launch[key]) if c]
                break
        intercept = (as_cells(launch.get("intercept_hex"))
                     if launch.get("intercept_hex") else None)
        iturn = int(launch.get("intercept_turn") or 0)
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
            if intercept is not None:
                for cell in continuation_cells(engine, state, target,
                                               o["route"], min(iturn, 4)):
                    if cell.distance(intercept) <= 1:
                        h += p_hit
                        break
            hs[i] = min(1.0, h)
        return hs

    H = np.stack([launch_hazard(l) for l in launches])
    haz_total = 1.0 - np.prod(1.0 - np.clip(H, 0.0, 1.0), axis=0)
    e_total = float(sum(float(l.get("expected_hits", 0.0) or 0.0)
                        for l in launches))
    low_salvo = all((l.get("expected_hits") or 0.0) < LOW_HIT for l in launches)

    idx0 = int(np.argmax(Js))
    lam = max(float(Js[idx0]), 1e-6)
    rows = []
    for mult, tag in ((0.5, "_l05"), (1.0, ""), (2.0, "_l20")):
        idxT = int(np.argmax(Js - lam * mult * haz_total))
        rows.append({
            "geometry": geometry, "seed": seed,
            "expected_hits_total": e_total,
            "n_launches": len(launches),
            "low_hit": int(low_salvo),
            "v_direct": e_total * CA_VALUE,
            "v_denial": float(max(0.0, Js[idx0] - Js[idxT])),
            "v_denial_raw": float(Js[idx0] - Js[idxT]),
            "route_changed": int(idx0 != idxT),
            "hazard_at_tauT": float(haz_total[idxT]),
            "lambda_tag": tag,
        })
    return rows


def wilson(p: float, n: int, z: float = 1.96):
    if n == 0:
        return 0.0, 0.0
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return center - half, center + half


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    all_rows = []
    for geometry in GEOMETRIES:
        for seed in range(1, 31):
            rows = measure(geometry, seed)
            if rows:
                all_rows.extend(rows)
    base = [r for r in all_rows if r["lambda_tag"] == ""]
    if not base:
        print("no samples")
        return
    with (OUT / "samples.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(base[0].keys()))
        writer.writeheader()
        writer.writerows(base)

    rng = np.random.default_rng(20260910)
    summary = {}
    for geometry in GEOMETRIES:
        entry = {}
        for subset, filt in (("all", lambda r: True),
                             ("low_hit", lambda r: r["low_hit"] == 1)):
            sel = [r for r in base if r["geometry"] == geometry and filt(r)]
            if not sel:
                continue
            v = np.array([r["v_denial"] for r in sel])
            boots = [float(np.mean(rng.choice(v, size=len(v))))
                     for _ in range(4000)]
            lo, hi = np.percentile(boots, [2.5, 97.5])
            rc = float(np.mean([r["route_changed"] for r in sel]))
            rc_lo, rc_hi = wilson(rc, len(sel))
            entry[subset] = {"n": len(sel),
                             "mean_v_denial": float(np.mean(v)),
                             "ci95": [float(lo), float(hi)],
                             "route_changed_rate": rc,
                             "route_changed_ci95": [float(rc_lo), float(rc_hi)],
                             "mean_v_direct": float(np.mean([r["v_direct"]
                                                             for r in sel]))}
        summary[geometry] = entry

    low = [r for r in base if r["low_hit"] == 1]
    v = np.array([r["v_denial"] for r in low])
    boots = [float(np.mean(rng.choice(v, size=len(v)))) for _ in range(4000)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    overall = {"n": len(low), "mean_v_denial": float(np.mean(v)),
               "ci95": [float(lo), float(hi)],
               "positive_fraction": float(np.mean(v > 0))}

    result = {"per_geometry": summary, "low_hit_overall": overall,
              "n_samples": len(base)}
    (OUT / "results.json").write_text(json.dumps(result, indent=2),
                                      encoding="utf-8")

    lines = ["# E04-min torpedo denial (independent decision-level cross-check)",
             ""]
    for geometry, entry in summary.items():
        for subset, st in entry.items():
            lines.append(
                f"- {geometry} [{subset}]: n={st['n']} "
                f"V_denial={st['mean_v_denial']:.4f} "
                f"CI [{st['ci95'][0]:+.4f}, {st['ci95'][1]:+.4f}] "
                f"route_changed={100 * st['route_changed_rate']:.0f}%")
    lines.append(f"- low-hit overall: n={overall['n']} "
                 f"V_denial={overall['mean_v_denial']:.4f} "
                 f"CI [{overall['ci95'][0]:+.4f}, {overall['ci95'][1]:+.4f}], "
                 f"positive {100 * overall['positive_fraction']:.0f}%")
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2)[:1200])


if __name__ == "__main__":
    main()
