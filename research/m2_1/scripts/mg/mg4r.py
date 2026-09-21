"""MG4-R: real torpedo corridor with space-time contact classification.

Three mandatory parts (PRE_REGISTRATION_R21):
  A. persistence probe  — a launched track must survive to T+1 with
     range_remaining > 0 and increased distance_travelled;
  B. space-time corridor — route unsafe iff ship and track share (MF, hex);
  C. torpedo-only classification cross-validated against the engine's own
     `torpedo_contact` events (never hull damage).

    PYTHONPATH=backend/src:research/m2_1/scripts .venv/bin/python \
        research/m2_1/scripts/mg/mg4r.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mg.micro import (IronBottomEngine, reach, scripted_plans)  # noqa: E402
from mg.mg_cases import ships_of  # noqa: E402
from iron_bottom_sound.models import (HexCoord, MovementOrder, OrderBatch,  # noqa: E402
                                      Phase, Side, TorpedoOrder)
from iron_bottom_sound.tactical import PROFILES, TacticalCommander  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "metrics"


def advance_with_scripts(eng, st, se, stop_phase=None, guard=10):
    """Advance one turn, scripting both sides; stop (without advancing) when
    ``stop_phase`` is reached."""
    g = 0
    while g < guard:
        g += 1
        if stop_phase is not None and st.phase == stop_phase:
            return True
        if st.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                        Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                        Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
            for s in Side:
                if s.value not in st.submitted_orders:
                    b = se[s].choose_plan(eng, st.game_id, s)[1]
                    if not eng.submit_orders(st.game_id, b).valid:
                        return False
        eng.advance(st.game_id)
        if st.phase == Phase.COMPLETE:
            return False
    return True


def launch_and_advance(scenario, seed, combo=None, launch_now=True):
    """Launch real torpedoes at TORPEDO_PLANNING, return (st_t1, track_id,
    shooter_id, victim_id, launch_info) at the next MOVEMENT_PLANNING."""
    eng, st, se = reach(scenario, seed, Phase.TORPEDO_PLANNING, 2)
    if st is None:
        return None
    shooter = next((s for s in ships_of(st, Side.ALLIES)
                    if s.torpedo and any(l.loaded > 0 and not l.destroyed
                                         for l in s.torpedo_launchers)), None)
    if shooter is None:
        return None
    enemies = ships_of(st, Side.AXIS)
    victim = min(enemies, key=lambda e: shooter.position.distance(e.position))
    if shooter.position.distance(victim.position) > 14:
        return None
    combos = [c for c in eng.torpedo_tactical_combos(st, Side.ALLIES)
              if c.get("ship_id") == shooter.id and not c.get("blocked_reason")]
    if combo is not None:
        combos = [c for c in combos
                  if (c["ship_id"], c["launcher_id"], c["setting_index"],
                      c["launch_side"], c["launch_angle"], c["launch_at_mf"])
                  == combo]
    if not combos:
        return None
    st2 = st.model_copy(deep=True)
    e2 = IronBottomEngine(); e2.games[st2.game_id] = st2
    batch = OrderBatch(side=Side.ALLIES, phase=Phase.TORPEDO_PLANNING)
    used = set()
    kinds = []
    for c in combos:
        key = (c["ship_id"], c["launcher_id"])
        if key in used:
            continue
        used.add(key)
        batch.torpedoes.append(TorpedoOrder(
            ship_id=c["ship_id"], launcher_id=c["launcher_id"],
            count=c["salvo_size"], launch_at_mf=c["launch_at_mf"],
            launch_hex=HexCoord.from_label(c["launch_hex"]),
            bearing=c["launch_heading"], launch_side=c["launch_side"],
            launch_angle=c["launch_angle"], setting_index=c["setting_index"]))
        kinds.append(c)
        if len(batch.torpedoes) >= 2:
            break
    if not e2.validate_orders(st2.game_id, batch).valid:
        return None
    e2.submit_orders(st2.game_id, batch)
    tracks_before = {t.id for t in st2.torpedo_tracks}
    if not advance_with_scripts(e2, st2, se, stop_phase=Phase.MOVEMENT_PLANNING):
        return None
    if st2.phase != Phase.MOVEMENT_PLANNING:
        return None
    new_tracks = [t for t in st2.torpedo_tracks if t.id not in tracks_before]
    return {"eng": e2, "state": st2, "se": se, "tracks": new_tracks,
            "shooter": shooter.id, "victim": victim.id, "combos": kinds,
            "scenario": scenario, "seed": seed}


def torpedo_step_positions(track, turn, obstacle_labels=frozenset(),
                           columns=46, rows=39):
    """(MF, hex) pairs the track will occupy this turn, mirroring the engine's
    straight-line advance: allowance = speed_cycle[(turn - launched_turn) % 3]."""
    allow = track.speed_cycle[(turn - track.launched_turn) % 3]
    allow = min(allow, track.range_remaining)
    pos = track.position
    out = []
    for mf in range(1, allow + 1):
        nxt = pos.neighbor(track.heading, columns=columns, rows=rows)
        if nxt is None or nxt.label in obstacle_labels:
            break
        pos = nxt
        out.append((mf, pos.label))
    return out


def victim_routes(eng, st, victim_id, limit=40):
    victim = st.ships.get(victim_id)
    if victim is None or victim.sunk or not victim.position:
        return []
    info = eng.movement_candidates(st, victim, include_plans=True)
    return [e for e in info.get("reachable", []) if e.get("plan")][:limit]


def route_trajectory(eng, st, victim_id, plan):
    victim = st.ships[victim_id]
    traj, _h = eng.movement_trajectory(victim, plan)
    return [(i + 1, p.label) for i, (p, _h2) in enumerate(traj)]


def engine_contact_for_route(st_base, victim_id, plan, se, test_track_id,
                             axis_profile="balanced", allies_profile="balanced"):
    """Apply the route for the victim side, resolve the turn, and report
    whether the TEST track registered contact (torpedo-only)."""
    st = st_base.model_copy(deep=True)
    eng = IronBottomEngine(); eng.games[st.game_id] = st
    victim = st.ships[victim_id]
    info = eng.movement_candidates(st, victim, include_plans=True)
    legal = {e["plan"] for e in info.get("reachable", []) if e.get("plan")}
    if plan not in legal:
        return None
    batch = OrderBatch(side=victim.side, phase=Phase.MOVEMENT_PLANNING)
    for s in ships_of(st, victim.side):
        if s.id == victim_id:
            p = plan
            cost = next((e.get("cost", 0) for e in info.get("reachable", [])
                         if e.get("plan") == plan), None)
        else:
            i2 = eng.movement_candidates(st, s, include_plans=True)
            first = (i2.get("reachable") or [{}])[0]
            p = first.get("plan", "0")
            cost = first.get("cost", None)
        batch.movement.append(MovementOrder(ship_id=s.id, plan=p, speed=cost))
    if not eng.validate_orders(st.game_id, batch).valid:
        return None
    eng.submit_orders(st.game_id, batch)
    pre_events = len(st.events)
    sess = {x: TacticalCommander(profile=PROFILES[allies_profile if x == Side.ALLIES
                                                    else axis_profile]) for x in Side}
    g = 0
    while st.phase not in (Phase.FIRE_END, Phase.COMPLETE) and g < 8:
        g += 1
        if st.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                        Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                        Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
            for s in Side:
                if s.value not in st.submitted_orders:
                    b = sess[s].choose_plan(eng, st.game_id, s)[1]
                    if not eng.submit_orders(st.game_id, b).valid:
                        return None
        try:
            eng.advance(st.game_id)
        except Exception:
            return None
    contacts = [e for e in st.events[pre_events:]
                if e.type == "torpedo_contact"
                and e.payload.get("track_id") == test_track_id]
    track = next((t for t in st.torpedo_tracks if t.id == test_track_id), None)
    return {"engine_contact": bool(contacts),
            "contact_ids": (track.contact_ship_ids if track else []),
            "victim_hit": victim_id in ((track.contact_ship_ids) if track else [])}


def main() -> int:
    report = {"persistence_probe": None, "corridor": None}
    # ---- A. persistence probe -----------------------------------------
    probes = []
    for scenario in ("IBS-S-01", "IBS-S-03", "IBS-S-EM-01"):
        for seed in range(1, 9):
            r = launch_and_advance(scenario, seed)
            if r is None or not r["tracks"]:
                continue
            t = r["tracks"][0]
            track = r["state"].torpedo_tracks[[x.id for x in r["state"].torpedo_tracks].index(t.id)]
            probes.append({
                "scenario": scenario, "seed": seed,
                "track_id": track.id, "launcher": track.launcher_ship_id,
                "position": track.position.label, "heading": track.heading,
                "range_remaining": track.range_remaining,
                "distance_travelled": track.distance_travelled,
                "speed_cycle": list(track.speed_cycle),
                "next_turn_allowance": track.speed_cycle[(r["state"].turn - track.launched_turn) % 3],
                "launched_turn": track.launched_turn, "now_turn": r["state"].turn,
                "survives": track.range_remaining > 0,
                "travelled": track.distance_travelled > 0,
                "visible_to_victim": any(
                    x.id == track.id
                    for x in r["eng"].observe(r["state"].game_id, Side.AXIS).torpedo_tracks),
            })
            if len(probes) >= 6:
                break
        if len(probes) >= 6:
            break
    report["persistence_probe"] = probes
    if not probes or not all(p["survives"] and p["travelled"] for p in probes):
        report["verdict"] = "STOP: persistence probe failed"
        (OUT / "mg4r.json").write_text(json.dumps(report, indent=1, default=str))
        print(json.dumps(report, indent=1, default=str))
        return 1

    # ---- B. corridor on the first probe state fulfilling the preconditions
    corridor = None
    for scenario in ("IBS-S-01", "IBS-S-03", "IBS-S-EM-01"):
        for seed in range(1, 9):
            base = launch_and_advance(scenario, seed)
            if base is None:
                continue
            # pre-registration: prefer long-range settings, then engine combo order
            settings = sorted({(c["setting_index"], -int(c.get("range", 0) or 0))
                               for c in base["combos"]},
                              key=lambda t: (t[1], t[0]))
            chosen = None
            for setting_idx, _neg_range in settings:
                cands = [c for c in base["combos"] if c["setting_index"] == setting_idx]
                for c in cands[:12]:
                    key = (c["ship_id"], c["launcher_id"], c["setting_index"],
                           c["launch_side"], c["launch_angle"], c["launch_at_mf"])
                    r = launch_and_advance(scenario, seed, combo=key)
                    if r is None or not r["tracks"]:
                        continue
                    st, eng, se = r["state"], r["eng"], r["se"]
                    victim_id = r["victim"]
                    routes = victim_routes(eng, st, victim_id)
                    if len(routes) < 10:
                        continue
                    track = r["tracks"][0]
                    tpos = torpedo_step_positions(track, st.turn, set(st.land_hexes),
                                                  columns=st.map_columns, rows=st.map_rows)
                    if not tpos:
                        continue
                    inter = sum(1 for e in routes
                                if set(route_trajectory(eng, st, victim_id, e["plan"]))
                                & set(tpos))
                    if inter >= 2:
                        chosen = (r, track, tpos, inter, len(routes), c)
                        break
                if chosen:
                    break
            if chosen is None:
                continue
            r, track, tpos, inter, n_routes, combo_used = chosen
            st, eng, se = r["state"], r["eng"], r["se"]
            victim_id = r["victim"]
            routes = victim_routes(eng, st, victim_id)
            corridor = {"scenario": scenario, "seed": seed, "victim": victim_id,
                        "test_track": track.id,
                        "track_position": track.position.label,
                        "track_heading": track.heading,
                        "track_range_remaining": track.range_remaining,
                        "launch_combo": {k: combo_used[k] for k in
                                         ("setting_index", "launch_side",
                                          "launch_angle", "launch_at_mf")},
                        "track_step_positions": tpos,
                        "n_routes": len(routes),
                        "geometric_intersect_routes": inter}
            # ---- C. classify every route, both ways
            rows = []
            agree = 0
            checked = 0
            for e in routes:
                traj = route_trajectory(eng, st, victim_id, e["plan"])
                geo_unsafe = bool(set(traj) & set(tpos))
                first_mf = next((mf for mf, h in traj if (mf, h) in set(tpos)), None)
                eng_res = engine_contact_for_route(st, victim_id, e["plan"], se,
                                                   track.id)
                rows.append({"plan": e["plan"],
                             "geo_unsafe": geo_unsafe, "first_contact_mf": first_mf,
                             "engine": eng_res})
                if eng_res is not None:
                    checked += 1
                    if geo_unsafe == eng_res["engine_contact"]:
                        agree += 1
            corridor["routes"] = rows
            corridor["cross_validation"] = {"checked": checked, "agree": agree,
                                            "agreement_rate": agree / max(1, checked)}
            # ---- gate
            safe_geo = sum(1 for x in rows if not x["geo_unsafe"])
            contact_geo = len(rows) - safe_geo
            corridor["total_routes"] = len(rows)
            corridor["contact_routes"] = contact_geo
            corridor["safe_routes"] = safe_geo
            corridor["contact_fraction"] = contact_geo / max(1, len(rows))
            corridor["gate"] = {
                "contact_fraction_ge_025": corridor["contact_fraction"] >= 0.25,
                "engine_agreement_full": agree == checked and checked >= 12,
                "verdict": "PASS" if (corridor["contact_fraction"] >= 0.25
                                      and agree == checked and checked >= 12
                                      and contact_geo > 0) else "FAIL",
            }
            break
        if corridor:
            break
    report["corridor"] = corridor
    report["verdict"] = corridor["gate"]["verdict"] if corridor else "CASE_CONSTRUCTION_FAIL"
    (OUT / "mg4r.json").write_text(json.dumps(report, indent=1, default=str))
    print(json.dumps({k: v for k, v in report.items() if k != "corridor"}, indent=1, default=str))
    if corridor:
        print(json.dumps({k: v for k, v in corridor.items() if k != "routes"},
                         indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
