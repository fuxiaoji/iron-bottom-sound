"""MG4-R corridor: geometric search over ALL legal torpedo configurations,
then a real launch + engine cross-validation.

The engine's `torpedo_tactical_combos` offers only intercept-aimed options
(2 identical combos in the S-01 states), so the corridor requires enumerating
the legal configuration space myself — permitted by PRE_REGISTRATION_R21
("自己做 legal per-ship enumeration"), with every launched order validated by
the engine and the space-time prediction cross-checked against the engine's
own `torpedo_contact` events.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mg.mg4r import (IronBottomEngine, advance_with_scripts, launch_and_advance,  # noqa: E402
                     route_trajectory, torpedo_step_positions, victim_routes)
from mg.mg_cases import ships_of  # noqa: E402
from mg.micro import reach  # noqa: E402
from iron_bottom_sound.models import (HexCoord, OrderBatch, Phase, Side,  # noqa: E402
                                      TorpedoOrder)

OUT = Path(__file__).resolve().parents[2] / "metrics"
ANGLES = ("A", "B", "X", "Y")


def enumerate_configs(eng, st, side, shooter):
    """Legal configurations at a TORPEDO_PLANNING state (launch positions come
    from the sealed MOVEMENT_PLANNING batch, so this only works at T)."""
    """All legal torpedo configurations for one ship: launcher x launch MF x
    side x angle x setting, with the engine's geometric projection."""
    rel = eng.rules.torpedo_launch_directions["relative_heading"]
    rows = [r for r in eng._torpedo_candidates(st, side) if r["ship_id"] == shooter.id]
    if not rows:
        return []
    row = rows[0]
    if row.get("blocked_reason"):
        return []
    torp_type = shooter.torpedo_type or ""
    settings = eng.rules.torpedoes.get(torp_type, {}).get("settings", [])
    out = []
    for launcher in row["launchers"]:
        for pos in row["launch_positions"]:
            for setting in row["settings"]:
                idx = setting["index"]
                cycle = settings[idx]["speed"]
                for lside in launcher["sides"]:
                    for angle in ANGLES:
                        heading = ((pos["heading"] - 1
                                    + rel[lside][angle]) % 6) + 1
                        proj = eng._project_torpedo_path(
                            st, torp_type, HexCoord(**pos["hex"]), heading, idx,
                            pos["mf"], angle, pos["heading"])
                        out.append({
                            "launcher_id": launcher["launcher_id"], "launch_at_mf": pos["mf"],
                            "launch_hex": HexCoord(**pos["hex"]),
                            # TorpedoOrder.bearing is the SHIP's heading at the
                            # launch MF (validator: "bearing N does not match
                            # ship heading"); the torpedo direction is derived
                            # from bearing + side + angle.
                            "bearing": pos["heading"],
                            "torp_heading": heading,
                            "launch_side": lside, "launch_angle": angle,
                            "setting_index": idx, "salvo": min(2, launcher["loaded"]),
                            "cycle": cycle, "range": settings[idx]["range"],
                            "path": proj["path"], "distance": proj["distance_travelled"],
                        })
    return out


def t1_segment(cfg):
    """(MF, hex) pairs the track occupies during the NEXT turn.

    path[0] is the launch anchor; the turn-T move consumes
    ``allowance = cycle[0] - launch_at_mf`` hexes, so the track sits at
    path[allowance] when T+1 begins and the next cycle[1] hexes are
    path[allowance+1 .. allowance+cycle[1]].  (The first version started the
    segment at path[allowance], one hex early — M21R-F22.)"""
    allowance = max(0, cfg["cycle"][0] - cfg["launch_at_mf"])
    seg = cfg["path"][allowance + 1: allowance + 1 + cfg["cycle"][1]]
    return [(i + 1, h) for i, h in enumerate(seg)]


def main() -> int:
    report = {"search": [], "corridor": None}
    chosen = None
    for scenario in ("IBS-S-01", "IBS-S-03", "IBS-S-EM-01"):
        for seed in range(1, 9):
            base = launch_and_advance(scenario, seed)
            if base is None:
                continue
            # victim routes live at T+1 (that is where the decision happens)
            eng1, st1 = base["eng"], base["state"]
            victim_id = base["victim"]
            routes = victim_routes(eng1, st1, victim_id)
            if len(routes) < 10:
                continue
            trajs = {e["plan"]: route_trajectory(eng1, st1, victim_id, e["plan"])
                     for e in routes}
            # configurations must be enumerated at T (torpedo planning), where
            # launch positions exist; score them by their projected T+1 segment
            engT, stT, seT = reach(scenario, seed, Phase.TORPEDO_PLANNING, 2)
            if stT is None:
                continue
            shooter = stT.ships[base["shooter"]]
            best = None
            cfgs = enumerate_configs(engT, stT, Side.ALLIES, shooter)
            for cfg in cfgs:
                seg = set(t1_segment(cfg))
                if not seg:
                    continue
                inter = sum(1 for t in trajs.values() if set(t) & seg)
                if best is None or inter > best[0]:
                    best = (inter, cfg)
            report["search"].append({
                "scenario": scenario, "seed": seed, "n_configs": len(cfgs),
                "n_routes": len(routes), "best_intersect": best[0] if best else 0,
                "best_setting": best[1]["setting_index"] if best else None,
                "best_range": best[1]["range"] if best else None,
            })
            if best and best[0] >= 2:
                chosen = (scenario, seed, base, best[1], routes, trajs)
                break
        if chosen:
            break
    if chosen is None:
        report["verdict"] = "CASE_CONSTRUCTION_FAIL (no config yields >=2 route intersections)"
        (OUT / "mg4r_corridor.json").write_text(json.dumps(report, indent=1, default=str))
        print(json.dumps(report, indent=1, default=str))
        return 1

    scenario, seed, base, cfg, routes, trajs = chosen
    # ---- real launch of the chosen configuration ------------------------
    eng, st, se = reach(scenario, seed, Phase.TORPEDO_PLANNING, 2)
    st2 = st.model_copy(deep=True)
    e2 = IronBottomEngine(); e2.games[st2.game_id] = st2
    batch = OrderBatch(side=Side.ALLIES, phase=Phase.TORPEDO_PLANNING)
    batch.torpedoes.append(TorpedoOrder(
        ship_id=base["shooter"], launcher_id=cfg["launcher_id"],
        count=cfg["salvo"], launch_at_mf=cfg["launch_at_mf"],
        launch_hex=cfg["launch_hex"], bearing=cfg["bearing"],
        launch_side=cfg["launch_side"], launch_angle=cfg["launch_angle"],
        setting_index=cfg["setting_index"]))
    valid = e2.validate_orders(st2.game_id, batch).valid
    e2.submit_orders(st2.game_id, batch)
    ok = advance_with_scripts(e2, st2, se, stop_phase=Phase.MOVEMENT_PLANNING)
    track = next((t for t in st2.torpedo_tracks if t.launcher_ship_id == base["shooter"]), None)
    if not ok or track is None:
        report["verdict"] = "CASE_CONSTRUCTION_FAIL (chosen config did not produce a track)"
        (OUT / "mg4r_corridor.json").write_text(json.dumps(report, indent=1, default=str))
        print(json.dumps(report, indent=1, default=str))
        return 1
    predicted = torpedo_step_positions(track, st2.turn, set(st2.land_hexes),
                                       columns=st2.map_columns, rows=st2.map_rows)
    report["launch"] = {"scenario": scenario, "seed": seed, "valid": valid,
                        "track": track.id, "position": track.position.label,
                        "heading": track.heading, "range_remaining": track.range_remaining,
                        "distance_travelled": track.distance_travelled,
                        "set_len": len(cfg["path"]), "t1_predicted": predicted,
                        "victim": base["victim"]}

    # ---- classify each route: geometric + engine ------------------------
    from mg.mg4r import engine_contact_for_route
    rows = []
    agree = checked = 0
    for e in routes:
        traj = route_trajectory(e2, st2, base["victim"], e["plan"])
        geo = bool(set(traj) & set(predicted))
        first = next((mf for mf, h in traj if (mf, h) in set(predicted)), None)
        eng_res = engine_contact_for_route(st2, base["victim"], e["plan"], se, track.id)
        rows.append({"plan": e["plan"], "geo_unsafe": geo, "first_contact_mf": first,
                     "engine_contact": (eng_res or {}).get("engine_contact"),
                     "engine_ran": eng_res is not None})
        if eng_res is not None:
            checked += 1
            if geo == eng_res["engine_contact"]:
                agree += 1
    contact = sum(1 for r in rows if r["geo_unsafe"])
    safe = len(rows) - contact
    frac = contact / max(1, len(rows))
    corpus = {"scenario": scenario, "seed": seed, "victim": base["victim"],
              "track": track.id, "n_routes": len(rows), "contact_routes": contact,
              "safe_routes": safe, "contact_fraction": frac,
              "cross_validation": {"checked": checked, "agree": agree},
              "t1_predicted": predicted, "rows": rows}
    corpus["gate"] = {
        "contact_fraction_ge_025": frac >= 0.25,
        "engine_agreement_full": agree == checked and checked >= 12,
        "verdict": "PASS" if (frac >= 0.25 and agree == checked and checked >= 12) else "FAIL",
    }
    report["corridor"] = corpus
    report["verdict"] = corpus["gate"]["verdict"]
    (OUT / "mg4r_corridor.json").write_text(json.dumps(report, indent=1, default=str))
    print(json.dumps({k: v for k, v in report.items() if k != "corridor"}, indent=1, default=str))
    print(json.dumps({k: v for k, v in corpus.items() if k != "rows"}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
