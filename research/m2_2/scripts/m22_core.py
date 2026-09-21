"""M2.2 shared machinery: legal fire (heuristic + search), movement beam search,
torpedo corridor search, and mechanism values.

Naming discipline (PRE_REGISTRATION_M22): LEGAL_FIRE_HEURISTIC (one target per
ship), FIRE_SEARCH (per-mount target search), BEAM_SEARCH_COMPILER (movement),
PUBLIC_CORRIDOR_SEARCH / FULL_STATE_CORRIDOR_CEILING (torpedo). Never
"optimal"/"oracle".
"""

from __future__ import annotations

import itertools
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
for p in (REPO / "backend" / "src", REPO / "research" / "m2_1" / "scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from iron_bottom_sound.engine import IronBottomEngine, d66_adjust  # noqa: E402
from iron_bottom_sound.models import (GameOptions, GunMountOrder,  # noqa: E402
                                      GunneryOrder, HexCoord, MovementOrder,
                                      OrderBatch, Phase, Side, TorpedoOrder)
from iron_bottom_sound.tactical import PROFILES, TacticalCommander  # noqa: E402

D66 = [t * 10 + u for t in range(1, 7) for u in range(1, 7)]
OTHER = {Side.AXIS: Side.ALLIES, Side.ALLIES: Side.AXIS}


# --------------------------------------------------------------------------
# fire evaluators
# --------------------------------------------------------------------------


def _kind_groups(mounts):
    g = {}
    for m in mounts:
        g.setdefault(m.kind, []).append(m)
    return g


def _group_eh(eng, st, ship, mounts, target, attackers, target_count):
    if not mounts:
        return 0.0
    d = ship.position.distance(target.position)
    total = 0.0
    for _kind, km in _kind_groups(mounts).items():
        fp = sum(float(getattr(m, "firepower", 0) or 0) for m in km)
        if fp <= 0:
            continue
        caliber = max((getattr(m, "caliber", 8.0) or 8.0) for m in km)
        mods = eng._gunnery_modifiers(st, ship, target, d, attackers, caliber, target_count)
        shift = sum(mods.values())
        total += sum(eng.rules.hit_count(int(fp), d66_adjust(x, shift)) for x in D66) / 36.0
    return total


def _engageable(eng, st, ship, target):
    try:
        return bool(eng._can_see(st, ship, target))
    except Exception:
        return False


def _bearing(eng, ship, target, st=None):
    """Mounts that can bear AND whose target the engine lets this ship engage
    (``_can_see``); the validator rejects orders against unseen ships."""
    if st is not None and not _engageable(eng, st, ship, target):
        return []
    return [m for m in ship.gun_mounts
            if not m.destroyed and not m.fired_this_phase
            and eng._mount_can_bear(ship, target, m.arcs)]


def legal_fire_heuristic(eng, st, side, opp, rounds=3):
    """LEGAL_FIRE_HEURISTIC: one target per ship, each mount once."""
    side = Side(side); opp = Side(opp)
    enemies = [s for s in st.ships.values() if s.side == opp and not s.sunk and s.position]
    shooters = [s for s in st.ships.values() if s.side == side and not s.sunk and s.position]
    legal = {sh.id: [e for e in enemies if _bearing(eng, sh, e, st)] for sh in shooters}
    choice = {sh.id: (legal[sh.id][0] if legal[sh.id] else None) for sh in shooters}
    for _ in range(rounds):
        counts = {}
        for sh in shooters:
            t = choice.get(sh.id)
            if t is not None:
                counts[t.id] = counts.get(t.id, 0) + 1
        for sh in shooters:
            if not legal[sh.id]:
                continue
            best = None
            for tgt in legal[sh.id]:
                mounts = _bearing(eng, sh, tgt, st)
                atk = counts.get(tgt.id, 0) + (1 if choice.get(sh.id) is not tgt else 0)
                v = _group_eh(eng, st, sh, mounts, tgt, max(1, atk), 1)
                if best is None or v > best[0]:
                    best = (v, tgt)
            if best:
                choice[sh.id] = best[1]
    counts = {}
    for sh in shooters:
        t = choice.get(sh.id)
        if t is not None:
            counts[t.id] = counts.get(t.id, 0) + 1
    detail, eh, gf, active, long_pairs = [], 0.0, 0.0, 0, 0
    for sh in shooters:
        tgt = choice.get(sh.id)
        if tgt is None:
            detail.append({"ship": sh.id, "target": None, "mounts": [], "eh": 0.0, "gf": 0.0})
            continue
        mounts = _bearing(eng, sh, tgt, st)
        v = _group_eh(eng, st, sh, mounts, tgt, counts[tgt.id], 1)
        f = sum(float(getattr(m, "firepower", 0) or 0) for m in mounts)
        asp = eng._target_aspect(sh, tgt)
        if asp == "bow_stern":
            long_pairs += 1
        if mounts:
            active += 1
        eh += v; gf += f
        detail.append({"ship": sh.id, "target": tgt.id,
                       "mounts": [(m.id, tgt.id) for m in mounts], "eh": v, "gf": f,
                       "aspect": asp})
    return {"method": "LEGAL_FIRE_HEURISTIC", "eh": eh, "gf": gf, "active": active,
            "longitudinal": long_pairs, "detail": detail,
            "targets": {r["ship"]: r["target"] for r in detail if r["target"]}}


def fire_search(eng, st, side, opp, budget=8):
    """FIRE_SEARCH: per-mount target allocation search.

    Option representation is ``{target_id: [mounts]}`` so a ship's mounts on the
    same target are scored as ONE group per mount kind (the engine's own
    grouping) and each mount is counted exactly once.  Named SEARCH, not
    optimal.  (The first version stored the same mount list under every mount id
    and then extended by it once per key, multiplying firepower by the mount
    count — M22-F2, caught by the heuristic-vs-search calibration.)
    """
    side = Side(side); opp = Side(opp)
    enemies = [s for s in st.ships.values() if s.side == opp and not s.sunk and s.position]
    shooters = [s for s in st.ships.values() if s.side == side and not s.sunk and s.position]

    def score_option(sh, option, counts):
        n_targets = len(option)
        v = 0.0
        for tid, ms in option.items():
            v += _group_eh(eng, st, sh, ms, st.ships[tid],
                           max(1, counts.get(tid, 0)), n_targets)
        return v

    ship_opts = {}
    for sh in shooters:
        cands = []
        # A) per-mount best target (may split)
        split = {}
        for m in sh.gun_mounts:
            if m.destroyed or m.fired_this_phase:
                continue
            best = None
            for tgt in enemies:
                if not _bearing(eng, sh, tgt, st):
                    continue
                v = _group_eh(eng, st, sh, [m], tgt, 1, 1)
                if best is None or v > best[0]:
                    best = (v, tgt.id)
            if best:
                split.setdefault(best[1], []).append(m)
        if split:
            cands.append(split)
        # B) all bearing mounts on one target
        for tgt in enemies:
            ms = _bearing(eng, sh, tgt, st)
            if ms:
                cands.append({tgt.id: ms})
        ship_opts[sh.id] = cands[:budget]

    choice = {sh.id: (ship_opts[sh.id][0] if ship_opts[sh.id] else {}) for sh in shooters}
    for _ in range(3):
        counts = {}
        for sh in shooters:
            for tid in choice.get(sh.id, {}):
                counts[tid] = counts.get(tid, 0) + 1
        for sh in shooters:
            best = None
            for opt in ship_opts[sh.id]:
                v = score_option(sh, opt, counts)
                if best is None or v > best[0]:
                    best = (v, opt)
            if best:
                choice[sh.id] = best[1]

    counts = {}
    for sh in shooters:
        for tid in choice.get(sh.id, {}):
            counts[tid] = counts.get(tid, 0) + 1
    detail, eh, gf, active, long_pairs = [], 0.0, 0.0, 0, 0
    for sh in shooters:
        opt = choice.get(sh.id, {})
        if not opt:
            detail.append({"ship": sh.id, "target": None, "mounts": [], "eh": 0.0, "gf": 0.0})
            continue
        v = score_option(sh, opt, counts)
        f = sum(float(getattr(m, "firepower", 0) or 0)
                for ms in opt.values() for m in ms)
        dom = max(opt, key=lambda t: len(opt[t]))
        asp = eng._target_aspect(sh, st.ships[dom])
        if asp == "bow_stern":
            long_pairs += 1
        active += 1
        eh += v; gf += f
        detail.append({"ship": sh.id, "target": dom,
                       "mounts": [(m.id, tid) for tid, ms in opt.items() for m in ms],
                       "eh": v, "gf": f, "aspect": asp, "n_targets": len(opt)})
    return {"method": "FIRE_SEARCH", "eh": eh, "gf": gf, "active": active,
            "longitudinal": long_pairs, "detail": detail,
            "targets": {r["ship"]: r["target"] for r in detail if r["target"]}}


def materialize_batch(eng, st, side, result):
    side = Side(side)
    batch = OrderBatch(side=side, phase=Phase.GUNNERY)
    for row in result["detail"]:
        if not row["mounts"]:
            continue
        order = GunneryOrder(ship_id=row["ship"], primary_target=row["target"])
        order.mounts = [GunMountOrder(mount_id=m, target_id=t) for m, t in row["mounts"]]
        batch.gunnery.append(order)
    res = eng.validate_orders(st.game_id, batch, _prepared=True)
    return batch.model_dump_json(), res.valid, res.errors[:3]


def net_eh(eng, st, side, fire=legal_fire_heuristic):
    """Mechanism panel at one state: own/enemy legal EH, GF, aspects, net."""
    opp = OTHER[Side(side)]
    own = fire(eng, st, side, opp)
    ene = fire(eng, st, opp, side)
    return {"own_eh": own["eh"], "enemy_eh": ene["eh"], "net_eh": own["eh"] - ene["eh"],
            "own_gf": own["gf"], "enemy_gf": ene["gf"],
            "own_active": own["active"], "enemy_active": ene["active"],
            "own_long_frac": own["longitudinal"] / max(1, own["active"]),
            "enemy_long_frac": ene["longitudinal"] / max(1, ene["active"]),
            "own": own, "enemy": ene}


# --------------------------------------------------------------------------
# movement application
# --------------------------------------------------------------------------


def apply_movement(st, side, plan_map, se, profile_pair=("balanced", "balanced")):
    """Apply a joint movement batch for `side`, script all other phases, stop at
    GUNNERY (post-movement, pre-fire).  Returns (state, eng, error)."""
    st2 = st.model_copy(deep=True)
    eng = IronBottomEngine(); eng.games[st2.game_id] = st2
    batch = OrderBatch(side=Side(side), phase=Phase.MOVEMENT_PLANNING)
    for ship_id, plan in plan_map.items():
        ship = st2.ships.get(ship_id)
        if ship is None or ship.sunk or not ship.position:
            continue
        cost = 0 if plan == "0" else None
        if plan != "0":
            info = eng.movement_candidates(st2, ship, include_plans=True)
            for e in info.get("reachable", []):
                if e.get("plan") == plan:
                    cost = e.get("cost", e.get("speed", 0)); break
        batch.movement.append(MovementOrder(ship_id=ship_id, plan=plan, speed=cost))
    if not eng.validate_orders(st2.game_id, batch).valid:
        return None, None, "movement batch invalid"
    eng.submit_orders(st2.game_id, batch)
    g = 0
    while st2.phase not in (Phase.GUNNERY, Phase.COMPLETE) and g < 8:
        g += 1
        if st2.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                         Phase.TORPEDO_PLANNING, Phase.CONTACT_SETUP,
                         Phase.FORMATION_SETUP}:
            for s in Side:
                if s.value not in st2.submitted_orders:
                    b = se[s].choose_plan(eng, st2.game_id, s)[1]
                    if not eng.submit_orders(st2.game_id, b).valid:
                        return None, None, "scripted submit invalid"
        eng.advance(st2.game_id)
    if st2.phase != Phase.GUNNERY:
        return None, None, "did not reach gunnery"
    return st2, eng, None


def ship_plan_pool(eng, st, side, ship, limit=8):
    """<=8 legal plans per ship: policy, hold, fastest, slowest, port/starboard
    extreme, plus the next engine-listed plans (deterministic order)."""
    info = eng.movement_candidates(st, ship, include_plans=True)
    entries = [e for e in info.get("reachable", []) if e.get("plan")]
    if not entries:
        return []
    def adv(e):
        return sum(int(c) for c in e["plan"] if c.isdigit())
    pool = []
    # policy plan
    try:
        cmd = TacticalCommander(profile=PROFILES["balanced"])
        e2 = IronBottomEngine(); e2.games[st.game_id] = st
        _, b, _ = cmd.choose_plan(e2, st.game_id, side)
        pol = next((o.plan for o in b.movement if o.ship_id == ship.id), None)
        if pol is not None and pol in {e["plan"] for e in entries}:
            pool.append(pol)
    except Exception:
        pass
    if info.get("reachable"):
        pool.append("0") if "0" not in pool else None
    order = sorted(entries, key=adv)
    pool += [order[0]["plan"], order[-1]["plan"]]
    # port/starboard extremes: net turn count
    port = sorted(entries, key=lambda e: (e["plan"].count("P") - e["plan"].count("S"), -adv(e)))[-1]["plan"]
    star = sorted(entries, key=lambda e: (e["plan"].count("S") - e["plan"].count("P"), -adv(e)))[-1]["plan"]
    pool += [port, star]
    for e in entries:
        if len(pool) >= limit:
            break
        if e["plan"] not in pool:
            pool.append(e["plan"])
    seen, out = set(), []
    for p in pool:
        if p not in seen:
            seen.add(p); out.append(p)
    return out[:limit]
