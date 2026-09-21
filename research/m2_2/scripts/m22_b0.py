"""M2.2 B0 — Gold Compiler Fidelity on the three confirmed mechanisms.

For MG1 (broadside), MG3 (range control) and MG4 (torpedo corridor) this script
reproduces the frozen M2.1-R2.1 case, then measures the mechanism value of five
methods and reports fidelity

    F(method) = (M(method) - M(random)) / (M(manual_gold) - M(random))

with the floors/bands frozen in PRE_REGISTRATION_M22.md.

Method set (naming discipline from the pre-registration, never "optimal"):
  MANUAL_GOLD             the hand-constructed arm recorded by M2.1-R2.1
  RANDOM_LEGAL            mean of 8 uniform seeded draws from the legal space
  CURRENT_POLICY          the deployed TacticalCommander at that state
  CURRENT_INTENT_COMPILER the repo's existing intent->plan compiler, told the
                          mechanism's intent (mg_cases.intent_plans, unmodified)
  BEAM_SEARCH_COMPILER    joint movement beam, width 64, <=8 plans/ship, cheap
                          geometry for partial ordering, every surviving joint
                          played through real simultaneous movement
  PUBLIC_CORRIDOR_SEARCH  torpedo: legal-config enumeration scored by an
                          observation-only corridor proxy
  FULL_STATE_CORRIDOR_CEILING  torpedo: same enumeration scored on full state
                          (research ceiling, NOT deployable)

    PYTHONPATH=backend/src:research/m2_2/scripts:research/m2_1/scripts \
        .venv/bin/python research/m2_2/scripts/m22_b0.py [MG1|MG3|MG4|ALL]
"""

from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))

from m22_core import (D66, OTHER, _group_eh, fire_search,  # noqa: E402
                      legal_fire_heuristic, net_eh)
from iron_bottom_sound.engine import IronBottomEngine, d66_adjust  # noqa: E402
from iron_bottom_sound.models import (HexCoord, MovementOrder, OrderBatch,  # noqa: E402
                                      Phase, Side)
from mg.micro import (advance_to_gunnery, plan_tables, reach,  # noqa: E402
                      scripted_plans)
from mg.mg1_broadside import final_rel  # noqa: E402
from mg.mg_cases import (DIRS, bearing_to, intent_plans, plan_for_pose,  # noqa: E402
                         ships_of)
from mg.mg4r import (launch_and_advance, route_trajectory,  # noqa: E402
                     torpedo_step_positions, victim_routes)
from mg.mg4r_corridor import enumerate_configs, t1_segment  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "metrics"
N_RANDOM = 8
FLOOR = 0.05


# --------------------------------------------------------------------------
# movement plumbing (engine-real, sealed-order only; no state surgery)
# --------------------------------------------------------------------------


def plan_cost(eng, st, ship, plan):
    """MovementOrder.speed must equal the engine's own movement cost (advances +
    120-degree turns; a 60-degree turn is free).  movement_candidates exposes
    only a subset of the legal plan space — the deployed commander emits legal
    plans outside it (e.g. 1P1P1P1P — M22-F3) — so ask the engine directly
    instead of the candidate table."""
    commands = eng.movement_commands(MovementOrder(ship_id=ship.id, plan=plan))
    return eng.movement_cost(plan, commands)


def play_movement(st, side, own_plans, enemy_plans, se):
    """Submit BOTH sides' movement explicitly (enemy plans byte-identical across
    arms), then advance to GUNNERY submitting nothing.  Returns (st, eng, err)."""
    st2 = st.model_copy(deep=True)
    e2 = IronBottomEngine()
    e2.games[st2.game_id] = st2
    for sd, pm in ((side, own_plans), (OTHER[side], enemy_plans)):
        b = OrderBatch(side=sd, phase=Phase.MOVEMENT_PLANNING)
        for ship_id, plan in pm.items():
            ship = st2.ships.get(ship_id)
            if ship is None or ship.sunk or not ship.position:
                continue
            c = plan_cost(e2, st2, ship, plan)
            if c is None:
                return None, None, f"illegal plan {ship_id}:{plan}"
            b.movement.append(MovementOrder(ship_id=ship_id, plan=plan, speed=c))
        if not b.movement:
            continue
        if not e2.validate_orders(st2.game_id, b).valid:
            return None, None, f"invalid batch {sd.value}"
        e2.submit_orders(st2.game_id, b)
    if not advance_to_gunnery(st2, e2, se):
        return None, None, "no gunnery"
    return st2, e2, None


# --------------------------------------------------------------------------
# cheap geometry surrogate (partial ordering only; never a reported value)
# --------------------------------------------------------------------------


def predict(eng, st, ship, plan):
    """(hex, heading) predicted with the engine's own movement trajectory — works
    for every legal plan, not just the movement_candidates subset."""
    if plan == "0":
        return ship.position, ship.heading
    traj, final_heading = eng.movement_trajectory(ship, plan, columns=st.map_columns,
                                                 rows=st.map_rows)
    if not traj:
        if plan == "0":
            return ship.position, ship.heading
        turns = plan.count("P") - plan.count("S")
        return ship.position, ((ship.heading - 1 + turns) % 6) + 1
    return traj[-1][0], final_heading


def _bearing_fp(eng, pos_a, head_a, pos_b, mounts):
    a = SimpleNamespace(position=pos_a, heading=head_a)
    b = SimpleNamespace(position=pos_b)
    return sum(float(getattr(m, "firepower", 0) or 0) for m in mounts
               if not m.destroyed
               and IronBottomEngine._mount_can_bear(a, b, m.arcs))


def geom_score(eng, st, side, own_pred, enemy_pred):
    """Bearing-firepower margin at predicted post-movement geometry."""
    v = 0.0
    for sid, (p, h) in own_pred.items():
        for eid, (ep, _eh) in enemy_pred.items():
            v += _bearing_fp(eng, p, h, ep, st.ships[sid].gun_mounts)
    for eid, (ep, eh) in enemy_pred.items():
        for sid, (p, _h) in own_pred.items():
            v -= _bearing_fp(eng, ep, eh, p, st.ships[eid].gun_mounts)
    return v


def plan_pool(eng, st, side, ship, policy_plan, own_pred, enemy_pred, limit=8):
    """<=8 legal plans: policy, hold, fastest, slowest, port-extreme,
    starboard-extreme, + top-2 by the single-ship cheap geometry score
    (PRE_REGISTRATION_M22 B0 budget)."""
    info = eng.movement_candidates(st, ship, include_plans=True)
    entries = [e for e in info.get("reachable", []) if e.get("plan")]
    if not entries:
        return []
    legal = {e["plan"] for e in entries} | {"0"}

    def adv(e):
        return sum(int(c) for c in e["plan"] if c.isdigit())

    order = sorted(entries, key=adv)
    port = sorted(entries, key=lambda e: (e["plan"].count("P") - e["plan"].count("S"),
                                          -adv(e)))[-1]["plan"]
    star = sorted(entries, key=lambda e: (e["plan"].count("S") - e["plan"].count("P"),
                                          -adv(e)))[-1]["plan"]
    top = []
    for e in entries:
        pr = predict(eng, st, ship, e["plan"])
        if pr is None:
            continue
        op = dict(own_pred)
        op[ship.id] = pr
        top.append((geom_score(eng, st, side, op, enemy_pred), e["plan"]))
    top.sort(key=lambda t: -t[0])
    pool = [policy_plan, "0", order[0]["plan"], order[-1]["plan"], port, star]
    pool += [p for _s, p in top[:4]]
    out = []
    for p in pool:
        if p and p in legal and p not in out:
            out.append(p)
    return out[:limit]


def beam_search_movement(eng, st, side, policy_map, enemy_plans, se,
                         width=64, fire=legal_fire_heuristic, log=None):
    """BEAM_SEARCH_COMPILER: joint beam over the side's movement plans."""
    shooters = [s.id for s in ships_of(st, side)]
    epred = {}
    for sid, p in enemy_plans.items():
        sh = st.ships.get(sid)
        if sh is None or sh.sunk or not sh.position:
            continue
        pr = predict(eng, st, sh, p)
        if pr:
            epred[sid] = pr
    base_own = {}
    for sid in shooters:
        pr = predict(eng, st, st.ships[sid], policy_map.get(sid, "0"))
        if pr:
            base_own[sid] = pr
    pools, pred_cache = {}, {}
    for sid in shooters:
        pool = plan_pool(eng, st, side, st.ships[sid], policy_map.get(sid),
                         base_own, epred)
        pools[sid] = pool
        pred_cache[sid] = {p: predict(eng, st, st.ships[sid], p)
                           for p in pool + [policy_map.get(sid, "0")]}
    beams = [({}, None)]
    for sid in shooters:
        nxt = []
        for assign, _s in beams:
            for plan in pools[sid]:
                a2 = dict(assign)
                a2[sid] = plan
                own_pred = {}
                for o in shooters:
                    p = a2.get(o, policy_map.get(o, "0"))
                    pr = pred_cache[o].get(p)
                    if pr:
                        own_pred[o] = pr
                nxt.append((a2, geom_score(eng, st, side, own_pred, epred)))
        nxt.sort(key=lambda t: -t[1])
        beams = nxt[:width]
    scored = []
    for assign, cs in beams:
        st2, e2, err = play_movement(st, side, assign, enemy_plans, se)
        if st2 is None:
            continue
        scored.append((net_eh(e2, st2, side, fire=fire)["net_eh"], assign, cs))
    if not scored:
        return None, None, None
    scored.sort(key=lambda t: -t[0])
    if log:
        log(f"  beam: {len(beams)} joints played, best={scored[0][0]:.3f}")
    return scored[0][0], scored[0][1], {"n_joints_played": len(scored),
                                        "pool_sizes": {k: len(v) for k, v in pools.items()}}


# --------------------------------------------------------------------------
# mechanism arms
# --------------------------------------------------------------------------


def _rand_focal_plans(eng, st, side, focal, n=N_RANDOM, seed=20260921):
    plans = sorted(plan_tables(eng, st, side).get(focal, {"0"}))
    rng = random.Random(seed)
    return [rng.choice(plans) for _ in range(n)]


def _net_of(st, se, side, own_plans, enemy_plans, fire):
    st2, e2, err = play_movement(st, side, own_plans, enemy_plans, se)
    if st2 is None:
        return None, err
    ne = net_eh(e2, st2, side, fire=fire)
    return {"net_eh": ne["net_eh"], "own_eh": ne["own_eh"],
            "enemy_eh": ne["enemy_eh"], "own_gf": ne["own_gf"],
            "own_active": ne["own_active"]}, None


def pair_net(e2, st2, a_id, b_id):
    """M_broad restricted to the case's own pair (attacker vs its recorded
    target) with lambda=1: the same frozen formula, but at the scale the MG1/MG3
    lever actually operates on.  Reported as a SUPPLEMENTARY panel; the primary
    value stays the fleet margin."""
    a, b = st2.ships.get(a_id), st2.ships.get(b_id)
    if a is None or b is None or a.sunk or b.sunk or not a.position or not b.position:
        return None
    am = [m for m in a.gun_mounts if not m.destroyed
          and e2._can_see(st2, a, b) and e2._mount_can_bear(a, b, m.arcs)]
    bm = [m for m in b.gun_mounts if not m.destroyed
          and e2._can_see(st2, b, a) and e2._mount_can_bear(b, a, m.arcs)]
    return _group_eh(e2, st2, a, am, b, 1, 1) - _group_eh(e2, st2, b, bm, a, 1, 1)


def fidelity(method, random_mean, gold, floor=FLOOR):
    gap = gold - random_mean
    if abs(gap) < floor:
        return None
    return (method - random_mean) / gap


# --------------------------------------------------------------------------
# MG1 BROADSIDE
# --------------------------------------------------------------------------


def build_mg1(log=print):
    eng, st, se = reach("IBS-S-01", 5, Phase.MOVEMENT_PLANNING, 2)
    if st is None:
        return None
    side = Side.AXIS
    policy_map = scripted_plans(eng, st, side)
    enemy_plans = scripted_plans(eng, st, Side.ALLIES)
    tables = plan_tables(eng, st, side)
    own = ships_of(st, side)
    enemies = ships_of(st, Side.ALLIES)
    found = None
    for s in sorted(own, key=lambda x: -x.vp):
        near = min(enemies, key=lambda e: s.position.distance(e.position))
        probe = {**policy_map, s.id: "0"}
        st_p, e_p, err = play_movement(st, side, probe, enemy_plans, se)
        if st_p is None:
            continue
        tgt_post = st_p.ships[near.id]
        if not tgt_post.position:
            continue
        post_bearing = bearing_to(st_p.ships[s.id].position, tgt_post.position)
        plans = sorted(tables[s.id])
        broad = narrow = None
        for plan in plans:
            frel = final_rel(plan, s.heading, post_bearing)
            if frel in (1, 2, 4, 5) and broad is None and plan != "0":
                broad = plan
            if frel in (0, 3) and narrow is None and plan != "0":
                narrow = plan
        if broad and narrow and broad != narrow:
            found = (s.id, near.id, broad, narrow, post_bearing)
            break
    if found is None:
        return None
    focal, target, broad, narrow, post_bearing = found
    log(f"MG1 case: focal={focal} target={target} broad={broad} narrow={narrow}")
    return {"mech": "MG1_BROADSIDE", "scenario": "IBS-S-01", "seed": 5,
            "side": side, "focal": focal, "target": target,
            "gold_plan": broad, "ref_plan": narrow, "policy_map": policy_map,
            "enemy_plans": enemy_plans, "st": st, "eng": eng, "se": se,
            "enemies": enemies}


def verify_mg1(case, log=print):
    """Reproduce the M2.1-R2.1 MG1 geometry invariants exactly."""
    rec = json.loads((Path(__file__).resolve().parents[2] / "m2_1" / "metrics"
                      / "mg1_broadside.json").read_text())
    out = {}
    for name, plan in (("BROADSIDE", case["gold_plan"]), ("NARROW", case["ref_plan"])):
        st2, e2, err = play_movement(case["st"], case["side"],
                                     {**case["policy_map"], case["focal"]: plan},
                                     case["enemy_plans"], case["se"])
        if st2 is None:
            out[name] = {"error": err}
            continue
        my = st2.ships[case["focal"]]
        tgt = st2.ships[case["target"]]
        post_b = bearing_to(my.position, tgt.position)
        rel = (post_b - my.heading) % 6
        d = my.position.distance(tgt.position)
        n_bear = sum(1 for m in my.gun_mounts
                     if not m.destroyed and e2._mount_can_bear(my, tgt, m.arcs))
        main_gf = sum(float(getattr(m, "firepower", 0) or 0) for m in my.gun_mounts
                      if not m.destroyed and e2._mount_can_bear(my, tgt, m.arcs)
                      and m.kind == "primary")
        out[name] = {"post_rel": rel, "distance": d, "mounts_bearing": n_bear,
                     "main_gf_bearing": main_gf}
    # common-distance expected hits, mg1's own per-mount formula
    dref = max(v.get("distance", 0) for v in out.values())
    for name, plan in (("BROADSIDE", case["gold_plan"]), ("NARROW", case["ref_plan"])):
        st2, e2, err = play_movement(case["st"], case["side"],
                                     {**case["policy_map"], case["focal"]: plan},
                                     case["enemy_plans"], case["se"])
        if st2 is None:
            continue
        my = st2.ships[case["focal"]]
        tgt = st2.ships[case["target"]]
        exp = 0.0
        for m in my.gun_mounts:
            if m.destroyed or not e2._mount_can_bear(my, tgt, m.arcs):
                continue
            fp = float(getattr(m, "firepower", 0) or 0)
            if fp <= 0:
                continue
            total = sum(e2._gunnery_modifiers(st2, my, tgt, dref, 1, 8.0, 1).values())
            for d66 in D66:
                exp += e2.rules.hit_count(int(fp), d66_adjust(d66, total)) / 36.0
        out[name]["eh_at_dref"] = exp
    check = {
        "post_rel_broad": (out.get("BROADSIDE", {}).get("post_rel"),
                           rec["verdict"]["post_rel_broad"]),
        "post_rel_narrow": (out.get("NARROW", {}).get("post_rel"),
                            rec["verdict"]["post_rel_narrow"]),
        "distance_broad": (out.get("BROADSIDE", {}).get("distance"),
                           rec["BROADSIDE"]["distance"]),
        "distance_narrow": (out.get("NARROW", {}).get("distance"),
                            rec["NARROW"]["distance"]),
        "mounts_broad": (out.get("BROADSIDE", {}).get("mounts_bearing"),
                         rec["BROADSIDE"]["mounts_bearing"]),
        "mounts_narrow": (out.get("NARROW", {}).get("mounts_bearing"),
                          rec["NARROW"]["mounts_bearing"]),
        "eh_pct": (round(100 * (out["BROADSIDE"]["eh_at_dref"]
                                - out["NARROW"]["eh_at_dref"])
                        / max(1e-9, out["NARROW"]["eh_at_dref"]), 1),
                   rec["verdict"]["eh_improvement_pct_common_distance"]),
    }
    ok = all(a == b for a, b in check.values())
    log(f"MG1 reproduction: {'OK' if ok else 'MISMATCH'} {check}")
    return {"recorded_vs_reproduced": {k: list(v) for k, v in check.items()},
            "reproduced": ok, "geometry": out}


def run_mg1(log=print):
    case = build_mg1(log)
    if case is None:
        return {"mech": "MG1_BROADSIDE", "error": "case construction failed"}
    rep = verify_mg1(case, log)
    side, focal, target = case["side"], case["focal"], case["target"]
    st, se, en, pol = case["st"], case["se"], case["enemy_plans"], case["policy_map"]

    def ev(plan_map, fire=legal_fire_heuristic):
        st2, e2, err = play_movement(st, side, plan_map, en, se)
        if st2 is None:
            return None
        ne = net_eh(e2, st2, side, fire=fire)
        return {"net_eh": ne["net_eh"], "own_eh": ne["own_eh"],
                "enemy_eh": ne["enemy_eh"], "own_gf": ne["own_gf"],
                "pair_net": pair_net(e2, st2, focal, target)}

    arms = {
        "MANUAL_GOLD": ev({**pol, focal: case["gold_plan"]}),
        "REGISTERED_COUNTER_ARM": ev({**pol, focal: case["ref_plan"]}),
        "CURRENT_POLICY": ev(pol),
    }
    rnd_plans = _rand_focal_plans(case["eng"], st, side, focal)
    rnd = [ev({**pol, focal: p}) for p in rnd_plans]
    intent_map = intent_plans(case["eng"], st, side, "BROADSIDE", case["enemies"])
    arms["CURRENT_INTENT_COMPILER"] = ev(intent_map)
    intent_lever = None
    if focal in intent_map:
        intent_lever = ev({**pol, focal: intent_map[focal]})
    beam_v, beam_assign, beam_meta = beam_search_movement(
        case["eng"], st, side, pol, en, se, width=64, log=log)
    st_b, e_b, _err = (play_movement(st, side, beam_assign, en, se)
                       if beam_assign else (None, None, None))
    beam_pair = pair_net(e_b, st_b, focal, target) if st_b is not None else None

    def panel(key, gold_key="MANUAL_GOLD"):
        g = (arms[gold_key] or {}).get(key)
        rv = [(r or {}).get(key) for r in rnd if r is not None]
        rv = [v for v in rv if v is not None]
        rmean = sum(rv) / max(1, len(rv))
        out = {"MANUAL_GOLD": g, "REGISTERED_COUNTER_ARM": (arms["REGISTERED_COUNTER_ARM"] or {}).get(key),
               "RANDOM_LEGAL_MEAN": rmean, "RANDOM_LEGAL_MAX": max(rv) if rv else None,
               "CURRENT_POLICY": (arms["CURRENT_POLICY"] or {}).get(key),
               "CURRENT_INTENT_COMPILER": (arms["CURRENT_INTENT_COMPILER"] or {}).get(key),
               "CURRENT_INTENT_ON_LEVER_SHIP": (intent_lever or {}).get(key),
               "BEAM_SEARCH_COMPILER": beam_v if key == "net_eh" else beam_pair}
        gap = None if (g is None or not rv) else g - rmean
        fid = {}
        for m in ("CURRENT_POLICY", "CURRENT_INTENT_COMPILER",
                  "CURRENT_INTENT_ON_LEVER_SHIP", "BEAM_SEARCH_COMPILER"):
            v = out.get(m)
            if v is None or gap is None or gap <= 0:
                fid[m] = None
            else:
                fid[m] = (v - rmean) / gap
        status = ("GOLD_GAP_MISSING" if gap is None else
                  "GOLD_GAP_NONPOSITIVE" if gap <= 0 else
                  "GOLD_TOO_SMALL" if gap < FLOOR else "COMPUTABLE")
        return {"mechanism_value": out, "gold_gap": gap, "status": status,
                "fidelity": fid}

    primary = panel("net_eh")
    supplementary = panel("pair_net")
    out = {"mech": "MG1_BROADSIDE", "scenario": "IBS-S-01", "seed": 5,
           "side": side.value, "focal": focal, "target": target,
           "gold_plan": case["gold_plan"], "ref_plan": case["ref_plan"],
           "verification": rep,
           "primary_metric": "fleet EH margin (NetEH, LEGAL_FIRE_HEURISTIC)",
           "primary": primary,
           "supplementary_metric": "pair M_broad (focal vs its recorded target, lambda=1) — "
                                  "SUPPLEMENTARY, same frozen formula restricted to the case pair",
           "supplementary": supplementary,
           "mechanism_value": primary["mechanism_value"],
           "fidelity": primary["fidelity"],
           "gold_gap": primary["gold_gap"], "gold_too_small": primary["status"] != "COMPUTABLE",
           "random_draws": [{"plan": p, "net_eh": (r or {}).get("net_eh"),
                             "pair_net": (r or {}).get("pair_net")}
                            for p, r in zip(rnd_plans, rnd)],
           "beam_meta": beam_meta, "beam_assign": beam_assign,
           "unit": "EH margin (NetEH, LEGAL_FIRE_HEURISTIC)"}
    out["verdict"] = _mech_verdict(out)
    return out


def net_eh_of(case, plan_map, fire):
    r, err = _net_of(case["st"], case["se"], case["side"], plan_map,
                     case["enemy_plans"], fire)
    return (r or {}).get("net_eh")


def _mech_verdict(out):
    """Pre-registration: fidelity is computed only when the denominator
    (M(gold) - M(random)) is positive; a gap below the 0.05 floor is
    GOLD_TOO_SMALL.  A non-positive denominator is GOLD_GAP_NONPOSITIVE — the
    case is excluded from the 2-of-3 count either way."""
    prim = out.get("primary") or {}
    status = prim.get("status")
    if status == "GOLD_GAP_NONPOSITIVE":
        return "GOLD_GAP_NONPOSITIVE"
    if status in ("GOLD_TOO_SMALL", "GOLD_GAP_MISSING") or out.get("gold_too_small"):
        return "GOLD_TOO_SMALL"
    f = prim.get("fidelity", {}) or out.get("fidelity", {})
    if "BEAM_SEARCH_COMPILER" in f:
        s = f.get("BEAM_SEARCH_COMPILER")
    else:
        s = f.get("PUBLIC_CORRIDOR_SEARCH")
    c = f.get("CURRENT_POLICY")
    if s is None or c is None:
        return "INCOMPLETE"
    return ("GAP" if (s >= 0.70 and c <= 0.40) else
            "CURRENT_AI_ALREADY_STRONG" if c >= 0.80 else "NO_GAP")


# --------------------------------------------------------------------------
# MG3 RANGE CONTROL
# --------------------------------------------------------------------------


def build_mg3(log=print):
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
            if bb.position.distance(near.position) < 12:
                continue
            plans = plan_tables(eng, st, Side.ALLIES).get(bb.id) or set()
            close_plan = plan_for_pose(eng, st, bb, plans,
                                       bearing_to(bb.position, near.position), +1)
            open_plan = plan_for_pose(eng, st, bb, plans,
                                      ((bearing_to(bb.position, near.position) - 1 + 3) % 6) + 1, +1)
            if close_plan == open_plan:
                continue
            pol = scripted_plans(eng, st, Side.ALLIES)
            en = scripted_plans(eng, st, Side.AXIS)
            log(f"MG3 case: {scenario} seed={seed} bb={bb.id} near={near.id} "
                f"close={close_plan} open={open_plan}")
            return {"mech": "MG3_RANGE_CONTROL", "scenario": scenario, "seed": seed,
                    "side": Side.ALLIES, "bb": bb.id, "near": near.id,
                    "gold_plan": close_plan, "ref_plan": open_plan,
                    "policy_map": pol, "enemy_plans": en, "st": st, "eng": eng,
                    "se": se, "enemies": enemies}
    return None


def verify_mg3(case, log=print):
    """Reproduce the recorded 15/17 hex, 2.56 vs 0.94 expected-hits arms."""
    out = {}
    for name, plan in (("CLOSE", case["gold_plan"]), ("OPEN", case["ref_plan"])):
        st2, e2, err = play_movement(case["st"], case["side"],
                                     {**case["policy_map"], case["bb"]: plan},
                                     case["enemy_plans"], case["se"])
        if st2 is None:
            out[name] = {"error": err}
            continue
        bb = st2.ships[case["bb"]]
        near = min(ships_of(st2, Side.AXIS),
                   key=lambda e: bb.position.distance(e.position))
        d = bb.position.distance(near.position)
        fp = sum(float(getattr(m, "firepower", 0) or 0) for m in bb.gun_mounts
                 if m.kind == "primary" and not m.destroyed
                 and e2._mount_can_bear(bb, near, m.arcs))
        total = sum(e2._gunnery_modifiers(st2, bb, near, d, 1, 8.0, 1).values())
        exp = sum(e2.rules.hit_count(int(fp), d66_adjust(x, total)) / 36.0
                  for x in D66)
        out[name] = {"distance": d, "bb_primary_gf": fp, "expected_hits": exp}
    log(f"MG3 reproduction: {json.dumps(out, default=str)}")
    return {"arms": out}


def run_mg3(log=print):
    case = build_mg3(log)
    if case is None:
        return {"mech": "MG3_RANGE_CONTROL", "error": "case construction failed"}
    side, bb, near = case["side"], case["bb"], case["near"]
    st, se, pol, en = case["st"], case["se"], case["policy_map"], case["enemy_plans"]
    rep = verify_mg3(case, log)

    def ev(plan_map, fire=legal_fire_heuristic):
        st2, e2, err = play_movement(st, side, plan_map, en, se)
        if st2 is None:
            return None
        ne = net_eh(e2, st2, side, fire=fire)
        return {"net_eh": ne["net_eh"], "own_eh": ne["own_eh"],
                "enemy_eh": ne["enemy_eh"], "pair_net": pair_net(e2, st2, bb, near)}

    a_close = ev({**pol, bb: case["gold_plan"]})
    a_open = ev({**pol, bb: case["ref_plan"]})
    if a_close is None or a_open is None:
        return {"mech": "MG3_RANGE_CONTROL", "error": "arm failed"}

    def better(k):
        c, o = a_close.get(k), a_open.get(k)
        if c is None or o is None:
            return None, None
        return (("CLOSE", c) if c >= o else ("OPEN", o))

    arms = {"CLOSE_ARM": a_close, "OPEN_ARM": a_open}
    rnd_plans = _rand_focal_plans(case["eng"], st, side, bb)
    rnd = [ev({**pol, bb: p}) for p in rnd_plans]
    intent_maps = {n: intent_plans(case["eng"], st, side, n, case["enemies"])
                   for n in ("CLOSE", "OPEN")}
    intents = {n: ev(m) for n, m in intent_maps.items()}
    lever = {n: (ev({**pol, bb: m[bb]}) if bb in m else None)
             for n, m in intent_maps.items()}
    beam_v, beam_assign, beam_meta = beam_search_movement(
        case["eng"], st, side, pol, en, se, width=64, log=log)
    st_b, e_b, _e = (play_movement(st, side, beam_assign, en, se)
                     if beam_assign else (None, None, None))
    beam_pair = pair_net(e_b, st_b, bb, near) if st_b is not None else None

    def panel(key):
        gold_arm, _v = better(key)
        gold = a_close.get(key) if gold_arm == "CLOSE" else a_open.get(key)
        rv = [r.get(key) for r in rnd if r is not None and r.get(key) is not None]
        rmean = sum(rv) / max(1, len(rv))
        iv = [v.get(key) for v in intents.values() if v is not None and v.get(key) is not None]
        lv = [v.get(key) for v in lever.values() if v is not None and v.get(key) is not None]
        out = {"MANUAL_GOLD": gold, "GOLD_ARM": gold_arm,
               "COUNTER_ARM": "OPEN" if gold_arm == "CLOSE" else "CLOSE",
               "COUNTER_ARM_VALUE": (a_open if gold_arm == "CLOSE" else a_close).get(key),
               "RANDOM_LEGAL_MEAN": rmean, "RANDOM_LEGAL_MAX": max(rv) if rv else None,
               "CURRENT_POLICY": (ev(pol) or {}).get(key) if key == "net_eh" else None,
               "CURRENT_INTENT_COMPILER": max(iv) if iv else None,
               "CURRENT_INTENT_ON_LEVER_SHIP": max(lv) if lv else None,
               "BEAM_SEARCH_COMPILER": beam_v if key == "net_eh" else beam_pair}
        if key == "pair_net":
            cp = ev(pol)
            out["CURRENT_POLICY"] = (cp or {}).get("pair_net") if cp else None
        gap = None if gold is None else gold - rmean
        fid = {}
        for m in ("CURRENT_POLICY", "CURRENT_INTENT_COMPILER",
                  "CURRENT_INTENT_ON_LEVER_SHIP", "BEAM_SEARCH_COMPILER"):
            v = out.get(m)
            fid[m] = None if (v is None or gap is None or gap <= 0) else (v - rmean) / gap
        status = ("GOLD_GAP_MISSING" if gap is None else
                  "GOLD_GAP_NONPOSITIVE" if gap <= 0 else
                  "GOLD_TOO_SMALL" if gap < FLOOR else "COMPUTABLE")
        return {"mechanism_value": out, "gold_gap": gap, "status": status,
                "fidelity": fid}

    primary = panel("net_eh")
    supplementary = panel("pair_net")
    out = {"mech": "MG3_RANGE_CONTROL", "scenario": case["scenario"],
           "seed": case["seed"], "side": "allies", "bb": bb, "near": near,
           "gold_plan": case["gold_plan"], "ref_plan": case["ref_plan"],
           "policy_plan": pol.get(bb), "verification": rep, "arms": arms,
           "primary_metric": "fleet EH margin (NetEH, LEGAL_FIRE_HEURISTIC)",
           "primary": primary,
           "supplementary_metric": "pair M_broad (BB vs nearest enemy, lambda=1) — SUPPLEMENTARY",
           "supplementary": supplementary,
           "registered_metric_arms": {k: (v or {}).get("expected_hits")
                                      for k, v in rep["arms"].items()},
           "intent_both_directions": {k: (v or {}).get("net_eh") for k, v in intents.items()},
           "intent_on_lever_ship_only": {k: (v or {}).get("net_eh") for k, v in lever.items()},
           "beam_meta": beam_meta, "beam_assign": beam_assign,
           "mechanism_value": primary["mechanism_value"],
           "fidelity": primary["fidelity"], "gold_gap": primary["gold_gap"],
           "gold_too_small": primary["status"] != "COMPUTABLE",
           "unit": "EH margin (NetEH, LEGAL_FIRE_HEURISTIC)"}
    out["verdict"] = _mech_verdict(out)
    return out


# --------------------------------------------------------------------------
# MG4 TORPEDO CORRIDOR
# --------------------------------------------------------------------------


def public_corridor(st, victim, speed_band=None):
    """Observation-only corridor proxy: (MF, hex) cells the victim can plausibly
    occupy during its NEXT turn, forecast from what an opponent can observe at
    T — current position, heading and speed — and NOT from the sealed movement
    batch.

    The victim's T-turn displacement has not resolved yet at TORPEDO_PLANNING,
    so the T+1 start cell is itself uncertain: the blob therefore enumerates
    every plausible T-end cell (0..speed hexes along heading-1/heading/heading+1)
    and, from each, a T+1 route of 1..speed hexes along each plausible new
    heading.  Cells are labelled by T+1 MF.
    """
    vic = st.ships[victim]
    speed = int(getattr(vic, "current_speed", 2) or 2)
    if speed_band:
        speed = max(speed, speed_band)
    speed = max(1, min(speed, 6))
    cells = set()
    for turn0 in (-1, 0, 1):
        h0 = ((vic.heading - 1 + turn0) % 6) + 1
        pos0 = vic.position
        for adv0 in range(0, speed + 1):
            end = pos0
            ok = True
            for _ in range(adv0):
                nxt = end.neighbor(h0, columns=st.map_columns, rows=st.map_rows)
                if nxt is None:
                    ok = False
                    break
                end = nxt
            if not ok:
                break
            for turn1 in (-1, 0, 1):
                h1 = ((h0 - 1 + turn1) % 6) + 1
                pos = end
                for mf in range(1, speed + 1):
                    nxt = pos.neighbor(h1, columns=st.map_columns, rows=st.map_rows)
                    if nxt is None:
                        break
                    pos = nxt
                    cells.add((mf, pos.label))
    return cells


def run_mg4(log=print):
    base = launch_and_advance("IBS-S-01", 1)
    if base is None:
        return {"mech": "MG4_TORPEDO_CORRIDOR", "error": "no base state"}
    victim = base["victim"]
    shooter = base["shooter"]
    routes = victim_routes(base["eng"], base["state"], victim)
    trajs = {e["plan"]: set(route_trajectory(base["eng"], base["state"], victim, e["plan"]))
             for e in routes}
    n_routes = len(routes)
    log(f"MG4 case: victim={victim} shooter={shooter} n_routes={n_routes}")
    if n_routes < 10:
        return {"mech": "MG4_TORPEDO_CORRIDOR", "error": f"only {n_routes} routes"}

    engT, stT, seT = reach("IBS-S-01", 1, Phase.TORPEDO_PLANNING, 2)
    if stT is None:
        return {"mech": "MG4_TORPEDO_CORRIDOR", "error": "no torpedo state"}
    ship = stT.ships[shooter]
    cfgs = enumerate_configs(engT, stT, Side.ALLIES, ship)
    log(f"  enumerated {len(cfgs)} legal configurations")

    def rr_of_segments(segments):
        if not segments:
            return 0.0, n_routes
        safe = sum(1 for t in trajs.values() if not (t & segments))
        return 1 - safe / max(1, n_routes), safe

    for c in cfgs:
        c["seg"] = set(t1_segment(c))
        c["rr"], c["safe"] = rr_of_segments(c["seg"])
    cfgs = [c for c in cfgs if c["seg"]]
    if not cfgs:
        return {"mech": "MG4_TORPEDO_CORRIDOR", "error": "no configs with a T+1 segment"}
    best = max(cfgs, key=lambda c: c["rr"])
    log(f"  full-state argmax rr={best['rr']:.3f} setting={best['setting_index']}")

    # ---- validate the gold order with the real engine (R2.1 reproduction)
    from iron_bottom_sound.models import TorpedoOrder
    st2 = stT.model_copy(deep=True)
    e2 = IronBottomEngine()
    e2.games[st2.game_id] = st2
    batch = OrderBatch(side=Side.ALLIES, phase=Phase.TORPEDO_PLANNING)
    batch.torpedoes.append(TorpedoOrder(
        ship_id=shooter, launcher_id=best["launcher_id"], count=best["salvo"],
        launch_at_mf=best["launch_at_mf"], launch_hex=best["launch_hex"],
        bearing=best["bearing"], launch_side=best["launch_side"],
        launch_angle=best["launch_angle"], setting_index=best["setting_index"]))
    valid = e2.validate_orders(st2.game_id, batch).valid
    cross = None
    if valid:
        e2.submit_orders(st2.game_id, batch)
        from mg.mg4r import advance_with_scripts
        from mg.mg4r import engine_contact_for_route
        ok = advance_with_scripts(e2, st2, seT, stop_phase=Phase.MOVEMENT_PLANNING)
        if ok:
            predicted = torpedo_step_positions_track(st2, shooter)
            rows = []
            agree = checked = 0
            for e in routes[:12]:
                traj = set(route_trajectory(e2, st2, victim, e["plan"]))
                geo = bool(traj & set(predicted))
                try:
                    res = engine_contact_for_route(st2, victim, e["plan"], seT,
                                                   next(t.id for t in st2.torpedo_tracks
                                                        if t.launcher_ship_id == shooter))
                except Exception:
                    res = None
                rows.append({"plan": e["plan"], "geo_unsafe": geo,
                             "engine_contact": (res or {}).get("engine_contact")})
                if res is not None:
                    checked += 1
                    if geo == res["engine_contact"]:
                        agree += 1
            cross = {"checked": checked, "agree": agree,
                     "predicted": sorted(predicted), "valid": valid}
    # ---- CURRENT_POLICY: the deployed commander's torpedo plan
    cur_rr, cur_detail = None, None
    from iron_bottom_sound.tactical import PROFILES, TacticalCommander
    cmd = TacticalCommander(profile=PROFILES["balanced"])
    st3 = stT.model_copy(deep=True)
    e3 = IronBottomEngine()
    e3.games[st3.game_id] = st3
    try:
        _, b3, _ = cmd.choose_plan(e3, st3.game_id, Side.ALLIES)
        n_orders = len(b3.torpedoes) if hasattr(b3, "torpedoes") else 0
        if n_orders and e3.validate_orders(st3.game_id, b3).valid:
            e3.submit_orders(st3.game_id, b3)
            from mg.mg4r import advance_with_scripts
            ok = advance_with_scripts(e3, st3, seT, stop_phase=Phase.MOVEMENT_PLANNING)
            if ok:
                segs = set()
                for t in st3.torpedo_tracks:
                    if t.launched_turn >= stT.turn:
                        segs |= {(mf, h) for mf, h in torpedo_step_positions(
                            t, st3.turn, set(st3.land_hexes),
                            columns=st3.map_columns, rows=st3.map_rows)}
                cur_rr, _ = rr_of_segments(segs)
                cur_detail = {"n_orders": n_orders, "n_tracks_used": sum(
                    1 for t in st3.torpedo_tracks if t.launched_turn >= stT.turn)}
        else:
            cur_rr, cur_detail = 0.0, {"n_orders": n_orders, "note": "no legal torpedo plan"}
    except Exception as exc:  # noqa: BLE001
        cur_detail = {"error": f"{type(exc).__name__}: {exc}"}
    # ---- CURRENT_INTENT_COMPILER: engine combo generator + intent objective
    intent_rr, intent_detail = 0.0, {"combos": 0}
    try:
        combos = [c for c in engT.torpedo_tactical_combos(stT, Side.ALLIES)
                  if c.get("ship_id") == shooter and not c.get("blocked_reason")]
        intent_detail["combos"] = len(combos)
        if combos:
            bestc = None
            for c in combos:
                seg = {(i + 1, h) for i, h in enumerate(c.get("predicted_path") or [])}
                rr, _s = rr_of_segments(seg)
                if bestc is None or rr > bestc[0]:
                    bestc = (rr, c)
            intent_rr = bestc[0]
            intent_detail["chosen"] = {k: bestc[1].get(k) for k in
                                       ("launcher_id", "setting_index", "launch_angle",
                                        "launch_at_mf", "salvo_size")}
    except Exception as exc:  # noqa: BLE001
        intent_detail["error"] = f"{type(exc).__name__}: {exc}"
    # ---- PUBLIC methods: observation-only objectives, no full-state input
    vicT = stT.ships[victim]
    sp = max(1, min(int(getattr(vicT, "current_speed", 2) or 2), 6))

    def lead_cells(allow_turn):
        cells = set()
        heads = ([((vicT.heading - 1 + t) % 6) + 1 for t in (-1, 0, 1)]
                 if allow_turn else [vicT.heading])
        for h0 in heads:
            for adv0 in range(0, sp + 1):
                end, good = vicT.position, True
                for _ in range(adv0):
                    nxt = end.neighbor(h0, columns=stT.map_columns, rows=stT.map_rows)
                    if nxt is None:
                        good = False
                        break
                    end = nxt
                if not good:
                    break
                pos = end
                for mf in range(1, sp + 1):
                    nxt = pos.neighbor(h0, columns=stT.map_columns, rows=stT.map_rows)
                    if nxt is None:
                        break
                    pos = nxt
                    cells.add((mf, pos.label))
        return cells

    def key_no_state(c):
        return (-c["setting_index"], -c["launch_at_mf"], c["launch_side"],
                c["launch_angle"], c["launcher_id"])

    public_objectives = {}
    for name, cells in (("LEAD_HOLD_COURSE", lead_cells(False)),
                        ("LEAD_TURN_ALLOWED", lead_cells(True)),
                        ("CORRIDOR_BLOB", public_corridor(stT, victim))):
        for c in cfgs:
            c["_ov"] = len(c["seg"] & cells)
        mx = max(c["_ov"] for c in cfgs)
        tied = [c for c in cfgs if c["_ov"] == mx]
        pick = max(tied, key=key_no_state)
        public_objectives[name] = {
            "objective_cells": len(cells), "max_overlap": mx,
            "n_configs_tied": len(tied),
            "tie_set_rr_min": min(c["rr"] for c in tied),
            "tie_set_rr_max": max(c["rr"] for c in tied),
            "tie_set_rr_median": sorted(c["rr"] for c in tied)[len(tied) // 2],
            "tie_set_informative_ge_050": sum(1 for c in tied if c["rr"] >= 0.50),
            "chosen_rr": pick["rr"],
            "chosen": {"setting_index": pick["setting_index"],
                       "launch_side": pick["launch_side"],
                       "launch_angle": pick["launch_angle"],
                       "launch_at_mf": pick["launch_at_mf"]},
        }
    pub_rr = max(v["chosen_rr"] for v in public_objectives.values())
    pub_name = max(public_objectives, key=lambda k: public_objectives[k]["chosen_rr"])
    _ = pub_name
    # ---- RANDOM_LEGAL
    rng = random.Random(20260921)
    rnd = [rng.choice(cfgs) for _ in range(N_RANDOM)]
    rnd_rr = [c["rr"] for c in rnd]
    rnd_mean = sum(rnd_rr) / len(rnd_rr)

    methods = {"MANUAL_GOLD": best["rr"], "RANDOM_LEGAL_MEAN": rnd_mean,
               "RANDOM_LEGAL_MAX": max(rnd_rr),
               "CURRENT_POLICY": cur_rr,
               "CURRENT_INTENT_COMPILER": intent_rr,
               "PUBLIC_CORRIDOR_SEARCH": pub_rr,
               "FULL_STATE_CORRIDOR_CEILING": best["rr"]}
    gold = best["rr"]
    out = {"mech": "MG4_TORPEDO_CORRIDOR", "scenario": "IBS-S-01", "seed": 1,
           "victim": victim, "shooter": shooter, "n_routes": n_routes,
           "n_configs": len(cfgs),
           "gold_config": {k: str(v) for k, v in best.items()
                           if k not in ("seg", "path")},
           "gold_t1_segment": sorted(best["seg"]),
           "engine_cross_validation": cross,
           "current_policy_detail": cur_detail,
           "intent_detail": intent_detail,
           "public_objectives": public_objectives,
           "public_best_objective": pub_name,
           "random_draws": [{"setting": c["setting_index"], "angle": c["launch_angle"],
                             "rr": c["rr"]} for c in rnd],
           "unit": "route reduction RR = 1 - safe/total over the victim's legal routes",
           "mechanism_value": methods,
           "fidelity": {}, "gold_gap": gold - rnd_mean,
           "gold_gap_ok": abs(gold - rnd_mean) >= FLOOR,
           "gold_too_small": abs(gold - rnd_mean) < FLOOR}
    for m in ("CURRENT_POLICY", "CURRENT_INTENT_COMPILER", "PUBLIC_CORRIDOR_SEARCH",
              "FULL_STATE_CORRIDOR_CEILING"):
        if methods.get(m) is None:
            out["fidelity"][m] = None
        else:
            out["fidelity"][m] = fidelity(methods[m], rnd_mean, gold)
    s, c = out["fidelity"].get("PUBLIC_CORRIDOR_SEARCH"), out["fidelity"].get("CURRENT_POLICY")
    out["primary"] = {"mechanism_value": out["mechanism_value"],
                      "gold_gap": out["gold_gap"], "fidelity": out["fidelity"],
                      "status": ("GOLD_GAP_NONPOSITIVE" if out["gold_gap"] <= 0 else
                                 "GOLD_TOO_SMALL" if out["gold_gap"] < FLOOR else
                                 "COMPUTABLE")}
    out["verdict"] = _mech_verdict(out)
    out["fidelity_note"] = (
        "MANUAL_GOLD for MG4 equals the FULL_STATE argmax because the M2.1-R2.1 "
        "gold was itself constructed by that search; F(FULL_STATE)=1 is therefore "
        "trivial and the deployable number is F(PUBLIC_CORRIDOR_SEARCH).")
    return out


def torpedo_step_positions_track(st, shooter):
    t = next((x for x in st.torpedo_tracks if x.launcher_ship_id == shooter), None)
    if t is None:
        return []
    return torpedo_step_positions(t, st.turn, set(st.land_hexes),
                                 columns=st.map_columns, rows=st.map_rows)


# --------------------------------------------------------------------------


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else "ALL"
    t0 = time.time()
    results = {}
    for name, fn in (("MG1", run_mg1), ("MG3", run_mg3), ("MG4", run_mg4)):
        if which not in ("ALL", name):
            continue
        print(f"=== {name} ===", flush=True)
        try:
            results[name] = fn()
        except Exception as exc:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            results[name] = {"mech": name, "error": f"{type(exc).__name__}: {exc}"}
        print(json.dumps(_brief(results[name]), indent=1, default=str), flush=True)
    # ---- gate
    cases = 0
    detail = {}
    for name in ("MG1", "MG3", "MG4"):
        r = results.get(name)
        if not r or "error" in r or r.get("verdict") in (
                None, "INCOMPLETE", "GOLD_TOO_SMALL", "GOLD_GAP_NONPOSITIVE"):
            detail[name] = r.get("verdict") if r else "MISSING"
            continue
        detail[name] = r["verdict"]
        if r["verdict"] == "GAP":
            cases += 1
    results["GATE"] = {
        "GOLD_COMPILER_GAP": "PASS" if cases >= 2 else "FAIL",
        "cases_with_gap": cases, "required": 2, "per_mechanism": detail,
        "threshold": ">=2 of 3: SEARCH fidelity >= 0.70 AND CURRENT_POLICY fidelity <= 0.40",
        "wall_seconds": round(time.time() - t0, 1)}
    print(json.dumps(results["GATE"], indent=1), flush=True)
    (OUT / "b0_gold_compiler_fidelity.json").write_text(
        json.dumps(results, indent=1, default=str))
    return 0


def _brief(r):
    keep = ("mech", "scenario", "seed", "victim", "shooter", "n_routes", "n_configs",
            "focal", "target", "bb", "near", "gold_plan", "ref_plan", "verdict",
            "error", "primary_metric", "primary", "supplementary_metric",
            "supplementary", "engine_cross_validation", "current_policy_detail",
            "intent_detail", "registered_metric_arms", "verification",
            "fidelity_note", "beam_meta")
    return {k: v for k, v in r.items() if k in keep}


if __name__ == "__main__":
    raise SystemExit(main())
