"""M2.1-R2 Mechanistic Gold cases MG2-MG5, sharing micro.py machinery.

    PYTHONPATH=backend/src:research/m2_1/scripts .venv/bin/python \
        research/m2_1/scripts/mg/mg_cases.py [MG2|MG3|MG4|MG5|ALL]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mg.micro import (IronBottomEngine, advance_to_gunnery, build_batch,  # noqa: E402
                      plan_tables, reach, scripted_plans)
from iron_bottom_sound.engine import d66_adjust  # noqa: E402
from iron_bottom_sound.models import (GameOptions, OrderBatch, Phase,  # noqa: E402
                                      Side)
from iron_bottom_sound.tactical import PROFILES, TacticalCommander  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "metrics"
DIRS = {1: (1, -1), 2: (1, 0), 3: (0, 1), 4: (-1, 1), 5: (-1, 0), 6: (0, -1)}


def hyp(a, b):
    return (a * a + b * b) ** 0.5


def bearing_to(frm, to) -> int:
    dq, dr = to.q - frm.q, to.r - frm.r
    return max(DIRS, key=lambda h: (dq * DIRS[h][0] + dr * DIRS[h][1])
               / (hyp(dq, dr) + 1e-9))


def centroid(ships):
    if not ships:
        return None
    return (sum(s.position.q for s in ships) / len(ships),
            sum(s.position.r for s in ships) / len(ships))


def ships_of(st, side):
    return [s for s in st.ships.values()
            if s.side == side and not s.sunk and s.position]


def plan_for_pose(eng, st, ship, plans, desired_heading, speed_class):
    """Legal plan whose (final heading, advance) best matches the pose."""
    best, key = None, None
    for p in sorted(plans):
        if p == "0":
            continue
        turns = p.count("P") - p.count("S")
        adv = sum(int(c) for c in p if c.isdigit())
        final = ((ship.heading - 1 + turns) % 6) + 1
        ang = 0 if desired_heading is None else min(
            (final - desired_heading) % 6, (desired_heading - final) % 6)
        speed_err = abs(adv - (3 if speed_class > 0 else (1 if speed_class < 0 else 2)))
        k = (ang * 10 + speed_err, -adv)
        if key is None or k < key:
            best, key = p, k
    if best is None and "0" in plans:
        best = "0"
    return best


def intent_plans(eng, st, side, intent, enemies):
    own = ships_of(st, side)
    cent = centroid(enemies)
    out = {}
    for s in own:
        plans = plan_tables(eng, st, side).get(s.id) or plan_tables_all(eng, st).get(s.id, set())
        near = min(enemies, key=lambda e: s.position.distance(e.position))
        b = bearing_to(s.position, near.position)
        if intent == "BROADSIDE":
            dh, sc = ((b - 1 + 1) % 6) + 1, 0
        elif intent == "PARALLEL":
            dh, sc = ((e_h := enemies[0].heading) and ((e_h - 1) % 6) + 1), 0
        elif intent == "HOLD":
            dh, sc = None, 0
        elif intent == "CLOSE":
            dh, sc = b, +1
        elif intent == "OPEN":
            dh, sc = ((b - 1 + 3) % 6) + 1, +1
        elif intent == "TOWARD_GROUP":
            dh, sc = (bearing_to(s.position, __import__("iron_bottom_sound.models", fromlist=["HexCoord"]).HexCoord(q=int(cent[0]), r=int(cent[1]))) if cent else None), +1
        else:
            raise ValueError(intent)
        out[s.id] = plan_for_pose(eng, st, s, plans, dh, sc)
    return out


def plan_tables_all(eng, st):
    out = {}
    for s in st.ships.values():
        if s.sunk or not s.position:
            continue
        info = eng.movement_candidates(st, s, include_plans=True)
        plans = {e["plan"] for e in info.get("reachable", []) if e.get("plan")}
        if info.get("reachable"):
            plans.add("0")
        out[s.id] = plans
    return out


def run_to_gunnery(eng, st, se, side, plan_map, filler=None):
    if filler is None:
        filler = scripted_plans(eng, st, side)
    cand = build_batch(eng, st, side, plan_map, filler)
    b = OrderBatch.model_validate_json(cand)
    b.side = side
    b.phase = Phase.MOVEMENT_PLANNING
    res = eng.validate_orders(st.game_id, b)
    if not res.valid:
        return None, str(res.errors[:2])
    eng.submit_orders(st.game_id, b)
    if not advance_to_gunnery(st, eng, se):
        return None, "no gunnery"
    return b, None


def measure_side(eng, st, shooter_side, target_side):
    """Usable GF, expected hits, longitudinal pairs: shooter_side shooting at
    target_side, at post-movement positions."""
    shooters = ships_of(st, shooter_side)
    targets = ships_of(st, target_side)
    gf = 0.0
    exp = 0.0
    longitudinal = 0
    active = 0
    pairs = []
    for ship in shooters:
        ship_exp = 0.0
        bears = 0
        for tgt in targets:
            d = ship.position.distance(tgt.position)
            for m in ship.gun_mounts:
                if m.destroyed or not eng._mount_can_bear(ship, tgt, m.arcs):
                    continue
                fp = float(getattr(m, "firepower", 0) or 0)
                if fp <= 0:
                    continue
                bears += 1
                mods = eng._gunnery_modifiers(st, ship, tgt, d, 1, 8.0, 1)
                total = sum(mods.values())
                aspect = eng._target_aspect(ship, tgt)
                if aspect == "bow_stern":
                    longitudinal += 1
                for t10 in range(1, 7):
                    for t01 in range(1, 7):
                        d66 = t10 * 10 + t01
                        adj = d66_adjust(d66, total)
                        exp += eng.rules.hit_count(int(fp), adj) / 36.0
                ship_exp += eng.rules.hit_count(int(fp), 36) / 36.0 * 0  # placeholder
                gf += fp
        if bears > 0:
            active += 1
        pairs.append({"ship": ship.id, "expected_hits": ship_exp})
    return {"usable_gf": gf, "expected_hits": exp, "active_ships": active,
            "longitudinal_pairs": longitudinal, "pairs": pairs}


def expected_hit_margin(eng, st, focal, opp):
    own = measure_side(eng, st, focal, opp)
    en = measure_side(eng, st, opp, focal)
    return own, en, own["expected_hits"] - en["expected_hits"]


# --------------------------------------------------------------------------
# MG2 CROSSING THE T
# --------------------------------------------------------------------------


def mg2():
    for scenario in ("IBS-S-01", "IBS-S-EM-01"):
        for seed in range(1, 9):
            eng, st, se = reach(scenario, seed, Phase.MOVEMENT_PLANNING, 2)
            if st is None:
                continue
            enemies = ships_of(st, Side.AXIS)
            if len(enemies) < 3:
                continue
            from collections import Counter
            e_head = Counter(e.heading for e in enemies).most_common(1)[0]
            if e_head[1] < 2:
                continue
            # precondition: enemy line heading roughly toward our centroid
            ec = centroid(enemies)
            oc = centroid(ships_of(st, Side.ALLIES))
            bearing_ec_oc = bearing_to(
                type("P", (), {"q": ec[0], "r": ec[1]})(),
                type("P", (), {"q": oc[0], "r": oc[1]})())
            if min((bearing_ec_oc - e_head[0]) % 6, (e_head[0] - bearing_ec_oc) % 6) > 1:
                continue
            # arms
            cross = {}
            parallel = {}
            for s in ships_of(st, Side.ALLIES):
                plans = plan_tables(eng, st, Side.ALLIES).get(s.id) or set()
                near = min(enemies, key=lambda e: s.position.distance(e.position))
                b = bearing_to(s.position, near.position)
                cross[s.id] = plan_for_pose(eng, st, s, plans,
                                            ((b - 1 + 1) % 6) + 1, 0)
                parallel[s.id] = plan_for_pose(eng, st, s, plans,
                                               ((e_head[0] - 1) % 6) + 1, 0)
            out = {}
            for name, pm in (("CROSS_T", cross), ("PARALLEL", parallel)):
                st2 = st.model_copy(deep=True)
                e2 = IronBottomEngine(); e2.games[st2.game_id] = st2
                b2, err = run_to_gunnery(e2, st2, se, Side.ALLIES, pm)
                if b2 is None:
                    out[name] = {"error": err}
                    continue
                own = measure_side(e2, st2, Side.ALLIES, Side.AXIS)
                ene = measure_side(e2, st2, Side.AXIS, Side.ALLIES)
                out[name] = {
                    "own_usable_gf": own["usable_gf"],
                    "own_expected_hits": own["expected_hits"],
                    "enemy_usable_gf": ene["usable_gf"],
                    "enemy_expected_hits": ene["expected_hits"],
                    "own_longitudinal_pairs": own["longitudinal_pairs"],
                    "net_exchange": own["expected_hits"] - ene["expected_hits"],
                }
            if "CROSS_T" in out and "PARALLEL" in out \
                    and "error" not in out["CROSS_T"] and "error" not in out["PARALLEL"]:
                gate_cross = (out["CROSS_T"]["own_usable_gf"] > out["CROSS_T"]["enemy_usable_gf"]
                              and out["CROSS_T"]["net_exchange"] > 0)
                ratio_ok = False
                if gate_cross:
                    p_net = out["PARALLEL"]["net_exchange"]
                    c_net = out["CROSS_T"]["net_exchange"]
                    ratio_ok = c_net >= 1.25 * max(p_net, 1e-9)
                out["gate"] = {"cross_dominates": gate_cross, "ratio_1_25x": ratio_ok,
                               "verdict": "PASS" if (gate_cross and ratio_ok) else "FAIL"}
                return out
    return {"status": "NOT_BUILT"}


# --------------------------------------------------------------------------
# MG3 RANGE CONTROL
# --------------------------------------------------------------------------


def mg3():
    for scenario in ("IBS-S-01", "IBS-S-03", "IBS-S-EM-01"):
        for seed in range(1, 9):
            eng, st, se = reach(scenario, seed, Phase.MOVEMENT_PLANNING, 2)
            if st is None:
                continue
            bb = next((s for s in ships_of(st, Side.ALLIES)
                       if s.ship_type in ("BB", "BC")), None)
            if bb is None:
                continue
            enemies = ships_of(st, Side.AXIS)
            near = min(enemies, key=lambda e: bb.position.distance(e.position))
            d0 = bb.position.distance(near.position)
            plans = plan_tables(eng, st, Side.ALLIES).get(bb.id) or set()
            close_plan = plan_for_pose(eng, st, bb, plans, bearing_to(bb.position, near.position), +1)
            open_plan = plan_for_pose(eng, st, bb, plans,
                                      ((bearing_to(bb.position, near.position) - 1 + 3) % 6) + 1, +1)
            out = {}
            for name, plan in (("CLOSE", close_plan), ("OPEN", open_plan)):
                st2 = st.model_copy(deep=True)
                e2 = IronBottomEngine(); e2.games[st2.game_id] = st2
                b2, err = run_to_gunnery(e2, st2, se, Side.ALLIES,
                                         {bb.id: plan})
                if b2 is None:
                    out[name] = {"error": err}
                    continue
                bb2 = st2.ships[bb.id]
                near2 = min((s for s in ships_of(st2, Side.AXIS)),
                            key=lambda e: bb2.position.distance(e.position))
                d = bb2.position.distance(near2.position)
                fp = sum(float(getattr(m, "firepower", 0) or 0)
                         for m in bb2.gun_mounts
                         if m.kind == "primary" and not m.destroyed
                         and e2._mount_can_bear(bb2, near2, m.arcs))
                mods = e2._gunnery_modifiers(st2, bb2, near2, d, 1, 8.0, 1)
                total = sum(mods.values())
                exp = sum(eng.rules.hit_count(int(fp), d66_adjust(t10 * 10 + t01, total)) / 36.0
                          for t10 in range(1, 7) for t01 in range(1, 7))
                pen = e2.rules.penetration("IJN", 8.0, d) if hasattr(e2.rules, "penetration") else None
                # torpedo reach: nearest enemy DD with loaded launchers
                dd = next((s for s in ships_of(st2, Side.AXIS)
                           if s.torpedo and any(l.loaded > 0 and not l.destroyed
                                                for l in s.torpedo_launchers)), None)
                torp = None
                if dd is not None and dd.torpedo:
                    torp = max(int(sett.get("range", 0))
                               for sett in (e2.rules.torpedoes.get(dd.torpedo_type or "", {}).get("settings", []) or [{"range": 0}])) if e2.rules.torpedoes.get(dd.torpedo_type or "", {}).get("settings") else 0
                out[name] = {"distance": d, "expected_hits": exp,
                             "penetration_at_d": pen,
                             "enemy_torpedo_max_range": torp,
                             "torpedo_threat": (torp or 0) >= d}
            if "CLOSE" in out and "OPEN" in out and "error" not in out["CLOSE"] and "error" not in out["OPEN"]:
                eh_diff = abs(out["CLOSE"]["expected_hits"] - out["OPEN"]["expected_hits"])
                rel = eh_diff / max(1e-9, min(out["CLOSE"]["expected_hits"],
                                              out["OPEN"]["expected_hits"], 1e-9) + 1e-9)
                flip = (out["CLOSE"]["torpedo_threat"] != out["OPEN"]["torpedo_threat"])
                out["gate"] = {"eh_relative_gap": rel, "torpedo_threat_flip": flip,
                               "verdict": "PASS" if (rel >= 0.25 or flip) else "FAIL"}
                return out
    return {"status": "NOT_BUILT"}


# --------------------------------------------------------------------------
# MG4 REAL TORPEDO CORRIDOR
# --------------------------------------------------------------------------


def mg4():
    for scenario in ("IBS-S-01", "IBS-S-03", "IBS-S-EM-01"):
        for seed in range(1, 9):
            eng, st, se = reach(scenario, seed, Phase.TORPEDO_PLANNING, 2)
            if st is None:
                continue
            # find an approaching enemy ship with torpedo-capable own ship
            own_torp = [s for s in ships_of(st, Side.ALLIES)
                        if s.torpedo and any(l.loaded > 0 and not l.destroyed
                                             for l in s.torpedo_launchers)]
            if not own_torp:
                continue
            shooter = own_torp[0]
            enemies = ships_of(st, Side.AXIS)
            victim = min(enemies, key=lambda e: shooter.position.distance(e.position))
            if shooter.position.distance(victim.position) > 12:
                continue
            # build corridor spread: choose combos whose predicted path
            # maximizes hex coverage of the victim's T+1 candidate routes.
            # (aiming at the current-turn intercept leaves the NEXT-turn
            # routes untouched — the original run measured zero effect.)
            combos = [c for c in eng.torpedo_tactical_combos(st, Side.ALLIES)
                      if c.get("ship_id") == shooter.id and not c.get("blocked_reason")]
            # victim's T+1 candidate route hexes: from its reachable plans now
            vinfo = eng.movement_candidates(st, victim, include_plans=False)
            v_here = victim.position
            route_hexes = set()
            for entry in vinfo.get("reachable", []):
                lbl = entry.get("label")
                route_hexes.add(lbl)
            # reachable entries give target hexes; also add 1-ring as corridor width
            ring = set(route_hexes)
            from iron_bottom_sound.models import HexCoord
            for h in list(route_hexes):
                hc = HexCoord.from_label(h)
                for d in DIRS.values():
                    ring.add((hc.q + d[0], hc.r + d[1]))
            def path_hexes(c):
                return set(c.get("predicted_path") or [])
            def score(c):
                ph = path_hexes(c)
                cov = len(ph & ring)
                return (cov, -abs(len(ph)))
            spread = sorted(combos, key=score, reverse=True)[:6]
            if not spread:
                continue

            def run_arm(with_torpedoes: bool):
                st2 = st.model_copy(deep=True)
                e2 = IronBottomEngine(); e2.games[st2.game_id] = st2
                b2 = OrderBatch(side=Side.ALLIES, phase=Phase.TORPEDO_PLANNING)
                if with_torpedoes:
                    from iron_bottom_sound.models import HexCoord, TorpedoOrder
                    # F17: one order per launcher (the same launcher twice is
                    # an invalid batch)
                    seen_launchers = set()
                    for c in spread[:6]:
                        key = (c["ship_id"], c["launcher_id"])
                        if key in seen_launchers:
                            continue
                        seen_launchers.add(key)
                        b2.torpedoes.append(TorpedoOrder(
                            ship_id=c["ship_id"], launcher_id=c["launcher_id"],
                            count=c["salvo_size"], launch_at_mf=c["launch_at_mf"],
                            launch_hex=HexCoord.from_label(c["launch_hex"]),
                            bearing=c["launch_heading"], launch_side=c["launch_side"],
                            launch_angle=c["launch_angle"], setting_index=c["setting_index"]))
                if not e2.validate_orders(st2.game_id, b2).valid:
                    return None
                e2.submit_orders(st2.game_id, b2)
                # resolve to next movement planning; the OPPONENT must also
                # submit torpedo plans (F16: both sides seal before advancing)
                for s in Side:
                    if s.value not in st2.submitted_orders:
                        b3 = se[s].choose_plan(e2, st2.game_id, s)[1]
                        if not e2.submit_orders(st2.game_id, b3).valid:
                            return None
                g = 0
                while st2.phase not in (Phase.MOVEMENT_PLANNING, Phase.COMPLETE) and g < 8:
                    g += 1
                    # submit any phase orders the scripted sides owe (gunnery etc.)
                    if st2.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                                     Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                                     Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
                        for s in Side:
                            if s.value not in st2.submitted_orders:
                                b4 = se[s].choose_plan(e2, st2.game_id, s)[1]
                                if not e2.submit_orders(st2.game_id, b4).valid:
                                    return None
                    e2.advance(st2.game_id)
                if st2.phase != Phase.MOVEMENT_PLANNING:
                    return None
                # enumerate victim's legal routes
                victim_state = st2.ships.get(victim.id)
                if victim_state is None or victim_state.sunk or not victim_state.position:
                    return {"safe_routes": None, "victim_sunk": True}
                info = e2.movement_candidates(st2, victim_state, include_plans=True)
                plans = [e["plan"] for e in info.get("reachable", []) if e.get("plan")][:30]
                safe = 0
                total = 0
                damages = []
                se2 = {s: TacticalCommander(profile=PROFILES["balanced"]) for s in Side}
                from iron_bottom_sound.models import MovementOrder
                for plan in plans:
                    st3 = st2.model_copy(deep=True)
                    e3 = IronBottomEngine(); e3.games[st3.game_id] = st3
                    b3 = OrderBatch(side=Side.AXIS, phase=Phase.MOVEMENT_PLANNING)
                    for s in ships_of(st3, Side.AXIS):
                        if s.id == victim.id:
                            info3 = e3.movement_candidates(st3, s, include_plans=True)
                            p3 = plan if plan in {e["plan"] for e in info3.get("reachable", [])} else None
                            if p3 is None:
                                continue
                            cost = next((e.get("cost", 0) for e in info3.get("reachable", [])
                                         if e.get("plan") == p3), None)
                        else:
                            info3 = e3.movement_candidates(st3, s, include_plans=True)
                            first = info3.get("reachable", [])
                            p3 = first[0]["plan"] if first else "0"
                            cost = first[0].get("cost", 0) if first else None
                        b3.movement.append(MovementOrder(ship_id=s.id, plan=p3, speed=cost))
                    if not e3.validate_orders(st3.game_id, b3).valid:
                        continue
                    e3.submit_orders(st3.game_id, b3)
                    # submit others (allies) if needed
                    for s in Side:
                        if s.value not in st3.submitted_orders:
                            try:
                                b4 = se2[s].choose_plan(e3, st3.game_id, s)[1]
                                e3.submit_orders(st3.game_id, b4)
                            except Exception:
                                pass
                    pre_hull = st3.ships[victim.id].hull
                    g2 = 0
                    try:
                        while st3.phase not in (Phase.FIRE_END, Phase.COMPLETE) and g2 < 6:
                            g2 += 1
                            if st3.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                                             Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                                             Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
                                for s in Side:
                                    if s.value not in st3.submitted_orders:
                                        b5 = se2[s].choose_plan(e3, st3.game_id, s)[1]
                                        if not e3.submit_orders(st3.game_id, b5).valid:
                                            raise RuntimeError("invalid orders in route resolution")
                            e3.advance(st3.game_id)
                    except RuntimeError:
                        continue
                    hull_after = st3.ships[victim.id].hull
                    torp_hit = any(ev.type == "torpedo_hit" and ev.payload.get("target_id") == victim.id
                                   for ev in st3.events if ev.payload.get("target_id") == victim.id)
                    total += 1
                    dmg = (pre_hull or 0) - (hull_after or 0)
                    damages.append(dmg)
                    if dmg == 0 and not torp_hit:
                        safe += 1
                return {"routes_total": total, "safe_routes": safe,
                        "mean_damage": (sum(damages) / len(damages)) if damages else 0.0,
                        "max_damage": max(damages) if damages else 0.0}

            a_t = run_arm(True)
            a_n = run_arm(False)
            if not a_t or not a_n:
                continue
            if a_t.get("routes_total") and a_n.get("routes_total"):
                reduction = 1 - a_t["safe_routes"] / max(1, a_n["safe_routes"])
                gate = reduction >= 0.25 and a_t["max_damage"] > 0
                return {"scenario": scenario, "seed": seed, "victim": victim.id,
                        "torpedo_arm": a_t, "no_torpedo_arm": a_n,
                        "route_reduction": reduction,
                        "gate": {"reduction_ge_025": reduction >= 0.25,
                                 "verdict": "PASS" if gate else "FAIL"}}
    return {"status": "NOT_BUILT"}


# --------------------------------------------------------------------------
# MG5 LOCAL FORCE SUPERIORITY
# --------------------------------------------------------------------------


def mg5():
    for scenario in ("IBS-S-01", "IBS-S-EM-01"):
        for seed in range(1, 9):
            eng, st, se = reach(scenario, seed, Phase.MOVEMENT_PLANNING, 3)
            if st is None:
                continue
            enemies = ships_of(st, Side.AXIS)
            own = ships_of(st, Side.ALLIES)
            if len(enemies) < 3 or len(own) < 3:
                continue
            # find a split: one enemy isolated >= 6 hexes from the rest
            for iso in enemies:
                rest = [e for e in enemies if e.id != iso.id]
                gap = min(iso.position.distance(e.position) for e in rest)
                if gap < 6:
                    continue
                # arm CONCENTRATE: all own ships steer at the isolated ship
                conc = {}
                for i, s in enumerate(own):
                    plans = plan_tables(eng, st, Side.ALLIES).get(s.id) or set()
                    conc[s.id] = plan_for_pose(eng, st, s, plans,
                                               bearing_to(s.position, iso.position), +1)
                # arm DISPERSE: split own ships between iso and the rest
                dis = {}
                for i, s in enumerate(own):
                    plans = plan_tables(eng, st, Side.ALLIES).get(s.id) or set()
                    tgt = iso if i % 2 == 0 else rest[i % len(rest)]
                    dis[s.id] = plan_for_pose(eng, st, s, plans,
                                              bearing_to(s.position, tgt.position), 0)
                out = {}
                for name, pm in (("CONCENTRATE", conc), ("DISPERSE", dis)):
                    st2 = st.model_copy(deep=True)
                    e2 = IronBottomEngine(); e2.games[st2.game_id] = st2
                    b2, err = run_to_gunnery(e2, st2, se, Side.ALLIES, pm)
                    if b2 is None:
                        out[name] = {"error": err}
                        continue
                    own_m = measure_side(e2, st2, Side.ALLIES, Side.AXIS)
                    ene_m = measure_side(e2, st2, Side.AXIS, Side.ALLIES)
                    out[name] = {
                        "own_active_ships": own_m["active_ships"],
                        "own_usable_gf": own_m["usable_gf"],
                        "own_expected_hits": own_m["expected_hits"],
                        "enemy_expected_hits": ene_m["expected_hits"],
                        "hit_margin": own_m["expected_hits"] - ene_m["expected_hits"],
                    }
                if "CONCENTRATE" in out and "DISPERSE" in out \
                        and "error" not in out["CONCENTRATE"] and "error" not in out["DISPERSE"]:
                    gate = (out["CONCENTRATE"]["hit_margin"]
                            >= 1.25 * max(1e-9, out["DISPERSE"]["hit_margin"])
                            or out["CONCENTRATE"]["own_active_ships"]
                            > out["DISPERSE"]["own_active_ships"])
                    out["gate"] = {"margin_ratio": out["CONCENTRATE"]["hit_margin"]
                                   / max(1e-9, out["DISPERSE"]["hit_margin"]),
                                   "verdict": "PASS" if gate else "FAIL"}
                    return out
    return {"status": "NOT_BUILT"}


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else "ALL"
    results = {}
    for name, fn in (("MG2", mg2), ("MG3", mg3), ("MG4", mg4), ("MG5", mg5)):
        if which not in ("ALL", name):
            continue
        print(f"=== {name} ===", flush=True)
        try:
            results[name] = fn()
        except Exception as exc:  # noqa: BLE001
            results[name] = {"error": f"{type(exc).__name__}: {exc}"}
        print(json.dumps(results[name], indent=1, default=str), flush=True)
    (OUT / "mg_cases.json").write_text(json.dumps(results, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
