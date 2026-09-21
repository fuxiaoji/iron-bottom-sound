"""B1E — Exploratory Natural Opportunity Census (PRE_REGISTRATION_B1E).

Subcommands:
    movement   20 natural movement states / scenario x 5 arms, L0/L1/externality
    torpedo    <=10 legal torpedo states / scenario x 6 arms + identifiability
    mg3e       MG3-E executable range-control gold (selection rules frozen)

Naming: L0 = intent/mechanism fidelity, L1 = team tactical utility
(`FIRE_SEARCH` own EH - enemy EH), externality = delta_L1 - delta_L0.

Everything here is exploratory and never overrides a prior gate.
"""

from __future__ import annotations

import json
import random
import sys
import time
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "m2_2" / "scripts"))

from intent_compiler import (NAME_PRE_FIX, NAME_REPAIRED,  # noqa: E402
                            pre_fix_intent_plans, repaired_intent_plans)
from iron_bottom_sound.engine import IronBottomEngine  # noqa: E402
from iron_bottom_sound.models import (GameOptions, HexCoord, MovementOrder,  # noqa: E402
                                      OrderBatch, Phase, Side, TorpedoOrder)
from iron_bottom_sound.tactical import PROFILES, TacticalCommander  # noqa: E402
from m22_b0 import (OTHER, play_movement, predict as predict_arc_safe)  # noqa: E402
from m22_core import D66, _group_eh as _ge, fire_search, legal_fire_heuristic  # noqa: E402
from mg.mg4r import (advance_with_scripts, launch_and_advance, route_trajectory,  # noqa: E402
                     torpedo_step_positions, victim_routes)
from mg.mg4r_corridor import enumerate_configs, t1_segment  # noqa: E402
from mg.micro import plan_tables, reach, scripted_plans  # noqa: E402
from mg.mg_cases import ships_of  # noqa: E402

OUT = HERE.parent / "metrics"
OUT.mkdir(exist_ok=True)
SCENARIOS = ("IBS-S-01", "IBS-S-03", "IBS-S-EM-01")
BUCKETS = ("early", "contact", "damaged", "late")
MOVE_QUOTA = 20
TORP_QUOTA = 10
N_RANDOM = 8
BEAM_WIDTH = 64
PLAN_LIMIT = 8
RNG_SEED = 20260921
TH_REL, TH_ABS = 0.25, 0.05


# --------------------------------------------------------------------------
# state scan (frozen order: scenario, seed ascending, turn ascending)
# --------------------------------------------------------------------------


def _engage_count(eng, st, side):
    opp = OTHER[side]
    n = 0
    for a in ships_of(st, side):
        for b in ships_of(st, opp):
            if eng._can_see(st, a, b) and any(
                    not m.destroyed and eng._mount_can_bear(a, b, m.arcs)
                    for m in a.gun_mounts):
                n += 1
    return n


def _hull_frac(st, side):
    ships = [s for s in st.ships.values() if s.side == side]
    now = sum(s.hull for s in ships)
    start = sum(getattr(s, "hull_max", s.hull) or s.hull for s in ships)
    return now / max(1.0, float(start))


def bucket_labels(eng, st, first_contact_turn):
    """Labels a state satisfies.  A state may satisfy several (turn 2 is `early`
    and may be the `contact` turn; a damaged turn-9 state is `damaged` and
    `late`); the census round-robins over labels and never picks a state twice.
    Replaces the earlier first-match chain, in which `early` shadowed `contact`
    (amended before any census measurement — see PRE_REGISTRATION_B1E §5)."""
    labels = set()
    if st.turn <= 3:
        labels.add("early")
    if first_contact_turn == st.turn:
        labels.add("contact")
    if _hull_frac(st, Side.AXIS) < 0.75 or _hull_frac(st, Side.ALLIES) < 0.75:
        labels.add("damaged")
    if st.turn >= 8:
        labels.add("late")
    return labels


def scan_movement_states(scenario, seeds=8, log=print):
    """Walk each seed once, snapshot every MOVEMENT_PLANNING state, then take the
    quota round-robin over the four phase buckets in scan order."""
    pool = []  # (seed, turn, bucket, state, eng, se)
    for seed in range(1, seeds + 1):
        eng = IronBottomEngine()
        st = eng.reset(scenario, seed, GameOptions(mode="llm"))
        se = {s: TacticalCommander(profile=PROFILES["balanced"]) for s in Side}
        contact_turn = {}
        g = 0
        while st.phase != Phase.COMPLETE and g < 400 and len(pool) < 200:
            g += 1
            if st.phase == Phase.MOVEMENT_PLANNING:
                ct = contact_turn.get(seed)
                if ct is None and _engage_count(eng, st, Side.AXIS) >= 3 \
                        and _engage_count(eng, st, Side.ALLIES) >= 3:
                    ct = st.turn
                    contact_turn[seed] = ct
                b = bucket_labels(eng, st, contact_turn.get(seed))
                if b and st.turn >= 2:
                    snap = st.model_copy(deep=True)
                    e_snap = IronBottomEngine()
                    e_snap.games[snap.game_id] = snap
                    pool.append((seed, st.turn, b, snap, e_snap, se))
            if st.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                            Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                            Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
                for s in Side:
                    if s.value not in st.submitted_orders:
                        try:
                            b2 = se[s].choose_plan(eng, st.game_id, s)[1]
                            eng.submit_orders(st.game_id, b2)
                        except Exception:  # noqa: BLE001
                            pass
            try:
                eng.advance(st.game_id)
            except Exception:  # noqa: BLE001
                break
    picked, used = [], set()
    i = 0
    while len(picked) < MOVE_QUOTA and i < len(BUCKETS) * 40:
        b = BUCKETS[i % len(BUCKETS)]
        i += 1
        for row in pool:
            key = (row[0], row[1])
            if b in row[2] and key not in used:
                used.add(key)
                picked.append(row)
                break
    picked.sort(key=lambda r: (r[0], r[1]))
    label_counts = Counter()
    for row in picked:
        for lb in row[2]:
            label_counts[lb] += 1
    log(f"  {scenario}: pool={len(pool)} picked={len(picked)} "
        f"labels={dict(label_counts)} pool_labels="
        f"{dict(Counter(lb for row in pool for lb in row[2]))}")
    return picked


# --------------------------------------------------------------------------
# arms and metrics
# --------------------------------------------------------------------------


def _decomposed_scores(eng, st, side, policy_map, enemy_plans, pools, ships):
    """Per-ship contribution of the cheap geometry surrogate.

    geom_score decomposes exactly into a sum over own ships once the enemy's
    predicted post-movement geometry is fixed, so the beam's inner loop becomes
    dictionary lookups instead of arc tests.  Same surrogate, same ordering as
    the B0 beam.
    """
    epred = {}
    for sid, p in enemy_plans.items():
        sh = st.ships.get(sid)
        if sh is None or sh.sunk or not sh.position:
            continue
        pr = predict_arc_safe(eng, st, sh, p)
        if pr:
            epred[sid] = pr
    contrib = {}
    for sid in ships:
        sh = st.ships[sid]
        row = {}
        plans = list(pools.get(sid, [])) + [policy_map.get(sid, "0")]
        for plan in plans:
            pr = predict_arc_safe(eng, st, sh, plan)
            if pr is None:
                continue
            v = 0.0
            for eid, (ep, eh) in epred.items():
                v += _bearing_fp(eng, pr[0], pr[1], ep, sh.gun_mounts)
                v -= _bearing_fp(eng, ep, eh, pr[0], st.ships[eid].gun_mounts)
            row[plan] = v
        contrib[sid] = row
    return contrib


def _bearing_fp(eng, pos_a, head_a, pos_b, mounts):
    a = SimpleNamespace(position=pos_a, heading=head_a)
    b = SimpleNamespace(position=pos_b)
    return sum(float(getattr(m, "firepower", 0) or 0) for m in mounts
               if not m.destroyed
               and IronBottomEngine._mount_can_bear(a, b, m.arcs))


def beam_decomposed(eng, st, side, policy_map, enemy_plans, se, log=None):
    ships = sorted(s.id for s in ships_of(st, side))
    pools = {}
    for sid in ships:
        info = eng.movement_candidates(st, st.ships[sid], include_plans=True)
        entries = [e for e in info.get("reachable", []) if e.get("plan")]

        def adv(e):
            return sum(int(c) for c in e["plan"] if c.isdigit())

        order = sorted(entries, key=adv)
        pool = [policy_map.get(sid), "0"]
        if entries:
            pool += [order[0]["plan"], order[-1]["plan"]]
        pool = [p for p in dict.fromkeys(pool) if p]
        pools[sid] = pool[:PLAN_LIMIT]
    contrib = _decomposed_scores(eng, st, side, policy_map, enemy_plans, pools, ships)
    beams = [({}, 0.0)]
    for sid in ships:
        nxt = []
        for assign, sc in beams:
            for plan, v in contrib.get(sid, {}).items():
                a2 = dict(assign)
                a2[sid] = plan
                nxt.append((a2, sc + v))
        nxt.sort(key=lambda t: (-t[1], json.dumps(t[0], sort_keys=True)))
        beams = nxt[:BEAM_WIDTH]
    best = None
    for assign, _sc in beams:
        st2, e2, err = play_movement(st, side, assign, enemy_plans, se)
        if st2 is None:
            continue
        ne = team_metric(e2, st2, side)
        if best is None or ne["U_team"] > best[0]:
            best = (ne["U_team"], assign, ne)
    if best is None:
        return None, None, None
    return best[0], best[1], {"n_joints_played": len(beams), "pools": {k: len(v) for k, v in pools.items()}}


def team_metric(eng, st, side):
    """L1: U_team = FIRE_SEARCH own EH - FIRE_SEARCH enemy EH (frozen)."""
    own = fire_search(eng, st, side, OTHER[side])
    ene = fire_search(eng, st, OTHER[side], side)
    return {"own_eh": own["eh"], "enemy_eh": ene["eh"],
            "U_team": own["eh"] - ene["eh"]}


def local_metric(eng, st, a_id, b_id):
    """L0: the focal pair's legal visible-fire EH and usable mount count."""
    a, b = st.ships.get(a_id), st.ships.get(b_id)
    if a is None or b is None or a.sunk or b.sunk or not a.position or not b.position:
        return {"L0": 0.0, "mounts": 0, "visible": False}
    vis = bool(eng._can_see(st, a, b))
    mounts = [m for m in a.gun_mounts if not m.destroyed
              and eng._mount_can_bear(a, b, m.arcs)]
    return {"L0": _ge(eng, st, a, mounts, b, 1, 1), "mounts": len(mounts),
            "visible": vis}


def pick_lever(eng, st, side):
    """Deterministic lever ship/target pair from the PRE-movement state only.

    Selection uses pre-movement geometry exclusively (no arm outcome, no EH
    value): among the focal side's ships and the opposing ships, take the pair
    with the largest number of the ship's non-destroyed mounts bearing on the
    enemy at the CURRENT geometry; ties break by ship id then enemy id.  This
    asks "presenting a broadside" of the pair where the question is live, without
    letting any arm's result influence the choice.
    """
    opp = OTHER[side]
    best, key = (None, None), None
    for a in sorted(ships_of(st, side), key=lambda s: s.id):
        if not a.position:
            continue
        for b in sorted(ships_of(st, opp), key=lambda s: s.id):
            if not b.position:
                continue
            n = sum(1 for m in a.gun_mounts
                    if not m.destroyed and eng._mount_can_bear(a, b, m.arcs))
            k = (-n, a.id, b.id)
            if key is None or k < key:
                best, key = (a.id, b.id), k
    return best


def arms_for_state(scenario, seed, turn, st, eng, se, log=print, state_index=0):
    """Five arms.  The four cheap arms run on BOTH sides; BEAM_SEARCH_COMPILER
    runs on one side per state, chosen by the state index parity — a rule that
    consults no arm's output, so the expensive arm's side cannot be selected to
    favour a method."""
    rows = {}
    for side in (Side.AXIS, Side.ALLIES):
        pol = scripted_plans(eng, st, side)
        en = scripted_plans(eng, st, OTHER[side])
        lever, target = pick_lever(eng, st, side)
        if lever is None:
            continue
        rand_plans = sorted(plan_tables(eng, st, side).get(lever, {"0"}))
        rng = random.Random(RNG_SEED + seed * 100 + turn)
        draws = [rng.choice(rand_plans) for _ in range(N_RANDOM)]
        arm_maps = {
            "CURRENT_POLICY": pol,
            NAME_PRE_FIX: pre_fix_intent_plans(eng, st, side, "BROADSIDE",
                                               ships_of(st, OTHER[side])),
            NAME_REPAIRED: repaired_intent_plans(eng, st, side, "BROADSIDE",
                                                 ships_of(st, OTHER[side])),
        }
        rec = {"scenario": scenario, "seed": seed, "turn": turn, "side": side.value,
               "lever": lever, "target": target, "arms": {}}
        for name, pm in arm_maps.items():
            st2, e2, err = play_movement(st, side, pm, en, se)
            if st2 is None:
                rec["arms"][name] = {"error": err}
                continue
            rec["arms"][name] = {"L0": local_metric(e2, st2, lever, target),
                                 "L1": team_metric(e2, st2, side)}
        # RANDOM_LEGAL: 8 same-lever draws, mean reported
        r0, r1, n_ok = {"L0": 0.0, "mounts": 0, "visible": False}, {"U_team": 0.0}, 0
        rr = []
        for p in draws:
            st2, e2, err = play_movement(st, side, {**pol, lever: p}, en, se)
            if st2 is None:
                continue
            l0 = local_metric(e2, st2, lever, target)
            l1 = team_metric(e2, st2, side)
            rr.append({"plan": p, "L0": l0["L0"], "U_team": l1["U_team"]})
            r0["L0"] += l0["L0"]; r0["mounts"] += l0["mounts"]
            r0["visible"] = r0["visible"] or l0["visible"]
            r1["U_team"] += l1["U_team"]; n_ok += 1
        if n_ok:
            r0["L0"] /= n_ok; r0["mounts"] /= n_ok; r1["U_team"] /= n_ok
        rec["arms"]["RANDOM_LEGAL"] = {"L0": r0, "L1": r1, "draws": rr,
                                       "n_ok": n_ok, "mean_over_draws": True}
        # BEAM (focal side only would halve cost; PRE_REGISTRATION_B1E names both
        # sides for the cheap arms — the beam runs on the side whose lever ship
        # has the higher policy-arm L0, so both sides are represented across the
        # census without doubling the most expensive arm)
        rec["beam_side"] = None
        rows[side.value] = rec
    if rows:
        best_side = (Side.AXIS if state_index % 2 == 0 else Side.ALLIES).value
        if best_side not in rows:
            best_side = sorted(rows)[0]
        rec = rows[best_side]
        side = Side(best_side)
        pol = scripted_plans(eng, st, side)
        en = scripted_plans(eng, st, OTHER[side])
        u, assign, meta = beam_decomposed(eng, st, side, pol, en, se, log=log)
        if u is not None:
            st2, e2, err = play_movement(st, side, assign, en, se)
            rec["arms"]["BEAM_SEARCH_COMPILER"] = {
                "L0": local_metric(e2, st2, rec["lever"], rec["target"]),
                "L1": team_metric(e2, st2, side)}
        else:
            rec["arms"]["BEAM_SEARCH_COMPILER"] = {"error": "no joint"}
        rec["beam_side"] = best_side
        rec["beam_meta"] = meta
        rec["beam_assign"] = assign
    return rows


# --------------------------------------------------------------------------
# movement census
# --------------------------------------------------------------------------


def movement_census(log=print):
    t0 = time.time()
    out = {"arms": [{"name": "CURRENT_POLICY", "role": "baseline"},
                    {"name": NAME_PRE_FIX, "role": "bug provenance only"},
                    {"name": NAME_REPAIRED, "role": "repaired intent baseline"},
                    {"name": "BEAM_SEARCH_COMPILER", "role": "search"},
                    {"name": "RANDOM_LEGAL", "role": "matched-budget random"}],
           "thresholds": {"relative": TH_REL, "absolute": TH_ABS,
                          "beam_width": BEAM_WIDTH, "plan_limit": PLAN_LIMIT,
                          "n_random": N_RANDOM},
           "states": [], "shortfalls": {}}
    for scenario in SCENARIOS:
        log(f"=== {scenario} ===")
        picked = scan_movement_states(scenario, log=log)
        out["shortfalls"][scenario] = MOVE_QUOTA - len(picked)
        for seed, turn, bucket, st, eng, se in picked:
            rows = arms_for_state(scenario, seed, turn, st, eng, se, log=log,
                                  state_index=len(out["states"]))
            for side_value, rec in rows.items():
                rec["bucket"] = sorted(bucket)
                out["states"].append(rec)
                with open(OUT / "b1e_movement_states.jsonl", "a") as fh:
                    fh.write(json.dumps(rec, default=str) + "\n")
            log(f"  s{seed} t{turn} {bucket}: sides={list(rows)}")
            (OUT / "b1e_movement_partial.json").write_text(
                json.dumps({k: v for k, v in out.items() if k != "states"} |
                           {"n_states": len(out["states"])}, indent=1))
    out["summary"] = summarize(out["states"])
    out["wall_seconds"] = round(time.time() - t0, 1)
    (OUT / "b1e_movement_census.json").write_text(json.dumps(out, indent=1, default=str))
    log(json.dumps(out["summary"], indent=1))
    return out


def _delta(arm, base, key, sub=None):
    if not arm or not base or "error" in arm or "error" in base:
        return None
    a = arm[key] if sub is None else arm[key].get(sub)
    b = base[key] if sub is None else base[key].get(sub)
    if a is None or b is None:
        return None
    return a - b


def summarize(states):
    """L0/L1/externality per arm per state, then the frozen opportunity rates."""
    mech_rows = []
    for rec in states:
        arms = rec["arms"]
        base = arms.get("CURRENT_POLICY")
        if not base or "error" in base:
            continue
        row = {"scenario": rec["scenario"], "seed": rec["seed"], "turn": rec["turn"],
               "side": rec["side"], "bucket": rec["bucket"], "lever": rec["lever"],
               "target": rec["target"], "per_arm": {}}
        base_l0 = base["L0"]["L0"]
        base_l1 = base["L1"]["U_team"]
        for name, v in arms.items():
            if "error" in v:
                continue
            dl0 = v["L0"]["L0"] - base_l0
            dl1 = v["L1"]["U_team"] - base_l1
            denom = max(abs(base_l0), 1e-9)
            rel = dl0 / denom
            row["per_arm"][name] = {
                "L0": v["L0"]["L0"], "mounts": v["L0"]["mounts"],
                "visible": v["L0"]["visible"], "U_team": v["L1"]["U_team"],
                "delta_L0": dl0, "delta_L1": dl1, "rel_L0": rel,
                "externality": dl1 - dl0,
                "MECHANISM_OPPORTUNITY": bool(dl0 >= TH_ABS and rel >= TH_REL),
                "USABLE_TACTICAL_OPPORTUNITY": bool(dl1 >= TH_ABS and dl1 >= TH_REL * abs(base_l1)),
                "MECHANISM_SUCCESS_BUT_NEGATIVE_EXTERNALITY": bool(dl0 > 0 and dl1 < 0)}
        mech_rows.append(row)
    per_scenario = {}
    for scen in SCENARIOS:
        rows = [r for r in mech_rows if r["scenario"] == scen]
        if not rows:
            continue
        d = {}
        for arm in ("BEAM_SEARCH_COMPILER", NAME_REPAIRED, NAME_PRE_FIX, "RANDOM_LEGAL"):
            vals = [r["per_arm"][arm] for r in rows if arm in r["per_arm"]]
            if not vals:
                continue
            d[arm] = {
                "n": len(vals),
                "mech_opp_rate": sum(v["MECHANISM_OPPORTUNITY"] for v in vals) / len(vals),
                "usable_rate": sum(v["USABLE_TACTICAL_OPPORTUNITY"] for v in vals) / len(vals),
                "median_delta_L0": _median([v["delta_L0"] for v in vals]),
                "median_delta_L1": _median([v["delta_L1"] for v in vals]),
                "median_rel_L0": _median([v["rel_L0"] for v in vals]),
                "median_externality": _median([v["externality"] for v in vals]),
                "neg_externality_rate": sum(
                    v["MECHANISM_SUCCESS_BUT_NEGATIVE_EXTERNALITY"] for v in vals) / len(vals),
            }
        per_scenario[scen] = d
    return {"n_state_sides": len(mech_rows),
            "state_sides_per_scenario": dict(Counter(r["scenario"] for r in mech_rows)),
            "buckets": dict(Counter("|".join(sorted(r["bucket"])) for r in mech_rows)),
            "per_scenario": per_scenario}
def _median(v):
    v = sorted(x for x in v if x is not None)
    if not v:
        return None
    n = len(v)
    return v[n // 2] if n % 2 else 0.5 * (v[n // 2 - 1] + v[n // 2])


# --------------------------------------------------------------------------
# MG3-E — executable range-control gold (selection rules frozen in
# PRE_REGISTRATION_B1E §3; no selection on EH magnitude)
# --------------------------------------------------------------------------


def _pair_eh(eng, st, a_id, b_id):
    a, b = st.ships.get(a_id), st.ships.get(b_id)
    if a is None or b is None or a.sunk or b.sunk or not a.position or not b.position:
        return None
    vis = bool(eng._can_see(st, a, b))
    mounts = [m for m in a.gun_mounts if not m.destroyed
              and eng._mount_can_bear(a, b, m.arcs)]
    return {"visible": vis, "mounts": [m.id for m in mounts],
            "eh": _ge(eng, st, a, mounts, b, 1, 1),
            "distance": a.position.distance(b.position)}


def mg3e(log=print):
    """Scan every MOVEMENT_PLANNING state in (scenario, seed, turn) order and take
    the first that satisfies the frozen rules 1-6.  No selection on EH."""
    from mg.mg_cases import bearing_to, plan_for_pose
    reasons = Counter()
    rows = []
    chosen = None
    for scenario in SCENARIOS:
        for seed in range(1, 9):
            eng = IronBottomEngine()
            st = eng.reset(scenario, seed, GameOptions(mode="llm"))
            se = {x: TacticalCommander(profile=PROFILES["balanced"]) for x in Side}
            g = 0
            while st.phase != Phase.COMPLETE and g < 400 and chosen is None:
                g += 1
                if st.phase == Phase.MOVEMENT_PLANNING and st.turn >= 2:
                    snap = st.model_copy(deep=True)
                    e_snap = IronBottomEngine()
                    e_snap.games[snap.game_id] = snap
                    chosen = _mg3e_try_state(scenario, seed, snap, e_snap, se,
                                             reasons, log)
                    if chosen is not None:
                        break
                if st.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                                Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                                Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
                    for x in Side:
                        if x.value not in st.submitted_orders:
                            try:
                                eng.submit_orders(st.game_id,
                                                  se[x].choose_plan(eng, st.game_id, x)[1])
                            except Exception:  # noqa: BLE001
                                pass
                try:
                    eng.advance(st.game_id)
                except Exception:  # noqa: BLE001
                    break
            if chosen is not None:
                break
        if chosen is not None:
            break
    out = {"scan_rule": "every MOVEMENT_PLANNING state, (scenario, seed, turn) order",
           "rejection_reasons": dict(reasons),
           "total_states_checked": sum(reasons.values()),
           "chosen": None}
    if chosen is None:
        out["verdict"] = "MG3E = NOT_FOUND"
        (OUT / "mg3e.json").write_text(json.dumps(out, indent=1, default=str))
        log(f"{out['verdict']} after {out['total_states_checked']} state-checks; "
            f"reasons={dict(reasons)}")
        return out
    row = chosen
    a = row["arms"]
    gaps = [abs(a["CLOSE"]["own_eh"] - a["OPEN"]["own_eh"]),
            abs(a["CLOSE"]["net_eh"] - a["OPEN"]["net_eh"])]
    rel = [gaps[0] / max(1e-9, max(a["CLOSE"]["own_eh"], a["OPEN"]["own_eh"])),
           gaps[1] / max(1e-9, abs(max(a["CLOSE"]["net_eh"], a["OPEN"]["net_eh"])))]
    out["chosen"] = row
    out["local_gap_own_eh"] = gaps[0]
    out["local_gap_net_eh"] = gaps[1]
    out["relative_gap_own_eh"] = rel[0]
    out["relative_gap_net_eh"] = rel[1]
    out["gate"] = {"executable_both_arms": bool(a["CLOSE"]["executable"]
                                                and a["OPEN"]["executable"]),
                   "abs_ge_005": gaps[0] >= TH_ABS,
                   "rel_ge_025": rel[0] >= TH_REL}
    out["verdict"] = ("MG3E = PASS" if all(out["gate"].values()) else "MG3E = FAIL")
    (OUT / "mg3e.json").write_text(json.dumps(out, indent=1, default=str))
    log(f"{out['verdict']}  {row['scenario']} seed={row['seed']} {row['side']} "
        f"{row['focal']}->{row['target']} own EH "
        f"{a['CLOSE']['own_eh']:.3f}@{a['CLOSE']['distance']}hex vs "
        f"{a['OPEN']['own_eh']:.3f}@{a['OPEN']['distance']}hex "
        f"(net {a['CLOSE']['net_eh']:.3f} vs {a['OPEN']['net_eh']:.3f})")
    return out


def _mg3e_try_state(scenario, seed, st, eng, se, reasons, log):
    """Apply rules 1-6 to one state; return the row if all hold, else None."""
    from mg.mg_cases import bearing_to, plan_for_pose
    for side in (Side.AXIS, Side.ALLIES):
        focal = next((x for x in sorted(ships_of(st, side), key=lambda y: y.id)
                      if x.ship_type in ("BB", "BC")), None)
        if focal is None:
            reasons["no_bb_on_side"] += 1
            continue
        opp = [e for e in ships_of(st, OTHER[side]) if e.position]
        if not opp:
            reasons["no_enemy"] += 1
            continue
        target = min(opp, key=lambda e: focal.position.distance(e.position))
        tables = plan_tables(eng, st, side).get(focal.id) or set()
        b = bearing_to(focal.position, target.position)
        close_plan = plan_for_pose(eng, st, focal, tables, b, +1)
        open_plan = plan_for_pose(eng, st, focal, tables, ((b - 1 + 3) % 6) + 1, +1)
        if close_plan == open_plan:
            reasons["arms_identical"] += 1
            continue
        pol = scripted_plans(eng, st, side)
        en = scripted_plans(eng, st, OTHER[side])
        arms = {}
        for name, plan in (("CLOSE", close_plan), ("OPEN", open_plan)):
            st2, e2, err = play_movement(st, side, {**pol, focal.id: plan}, en, se)
            if st2 is None:
                arms = None
                break
            own = _pair_eh(e2, st2, focal.id, target.id)
            ret = _pair_eh(e2, st2, target.id, focal.id)
            arms[name] = {"plan": plan, "own": own, "return": ret,
                          "executable": bool(own and own["visible"] and own["mounts"])}
        if not arms:
            reasons["arm_play_failed"] += 1
            continue
        row = {"scenario": scenario, "seed": seed, "side": side.value,
               "focal": focal.id, "target": target.id,
               "turn": st.turn,
               "arms": {k: {"plan": v["plan"], "own_visible": v["own"]["visible"],
                            "own_mounts": v["own"]["mounts"], "own_eh": v["own"]["eh"],
                            "return_eh": v["return"]["eh"],
                            "net_eh": v["own"]["eh"] - v["return"]["eh"],
                            "distance": v["own"]["distance"],
                            "executable": v["executable"]}
                        for k, v in arms.items()}}
        a = row["arms"]
        if not (a["CLOSE"]["executable"] and a["OPEN"]["executable"]):
            reasons["not_executable"] += 1
            continue
        d1, d2 = a["CLOSE"]["distance"], a["OPEN"]["distance"]
        brk = {d for d in range(1, 30)
               if eng.rules.range_modifier("gunnery", d)
               != eng.rules.range_modifier("gunnery", max(0, d - 1))}
        if abs(d1 - d2) >= 2 or any(min(d1, d2) < x <= max(d1, d2) for x in brk):
            reasons["accepted"] += 1
            return row
        reasons["distance_rule"] += 1
    return None

# --------------------------------------------------------------------------
# Torpedo census + public identifiability (PRE_REGISTRATION_B1E §4, §5)
# --------------------------------------------------------------------------


def advance_no_launch(st, eng, se, log=None):
    """Advance the TORPEDO_PLANNING state to T+1 MOVEMENT_PLANNING with the
    scripted commanders for both sides (no injected launch)."""
    st2 = st.model_copy(deep=True)
    e2 = IronBottomEngine()
    e2.games[st2.game_id] = st2
    ok = advance_with_scripts(e2, st2, se, stop_phase=Phase.MOVEMENT_PLANNING)
    if not ok or st2.phase != Phase.MOVEMENT_PLANNING:
        return None, None
    return st2, e2


def torpedo_states(scenario, quota=TORP_QUOTA, log=print):
    picked = []
    for seed in range(1, 9):
        eng = IronBottomEngine()
        st = eng.reset(scenario, seed, GameOptions(mode="llm"))
        se = {s: TacticalCommander(profile=PROFILES["balanced"]) for s in Side}
        g = 0
        while st.phase != Phase.COMPLETE and g < 400 and len(picked) < quota:
            g += 1
            if st.phase == Phase.TORPEDO_PLANNING and st.turn >= 2:
                snap = st.model_copy(deep=True)
                e_snap = IronBottomEngine()
                e_snap.games[snap.game_id] = snap
                if any(x.torpedo and any(l.loaded > 0 and not l.destroyed
                                         for l in x.torpedo_launchers)
                       for x in snap.ships.values()):
                    picked.append((seed, st.turn, snap, e_snap, se))
            if st.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                            Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                            Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
                for s in Side:
                    if s.value not in st.submitted_orders:
                        try:
                            eng.submit_orders(st.game_id, se[s].choose_plan(eng, st.game_id, s)[1])
                        except Exception:  # noqa: BLE001
                            pass
            try:
                eng.advance(st.game_id)
            except Exception:  # noqa: BLE001
                break
        if len(picked) >= quota:
            break
    picked.sort(key=lambda r: (r[0], r[1]))
    log(f"  {scenario}: torpedo states={len(picked)} (quota {quota})")
    return picked[:quota]


def safe_neighbor(pos, heading, st):
    """HexCoord.neighbor raises ValueError off-map (it does not return None);
    an off-map step is simply not a legal hypothesis, so it ends the walk."""
    try:
        return pos.neighbor(heading, columns=st.map_columns, rows=st.map_rows)
    except ValueError:
        return None


def public_hypotheses(stT, victim, sp_hex=6):
    """PUBLIC-only route hypotheses: trajectories simulated from the victim's
    OBSERVED position, heading and speed — the only inputs, listed in the record
    as `public_inputs`.  Nothing here reads the sealed movement batch.

    Leak guard (real, not vacuous): every hypothesis cell must lie within
    `speed + 1` hexes of the victim's observed position and its MF index must not
    exceed the observed speed.  A hypothesis built from sealed data would violate
    both, so the check fails loudly instead of silently smuggling information.
    """
    vic = stT.ships[victim]
    sp = max(1, min(int(getattr(vic, "current_speed", 2) or 2), sp_hex))
    out = []
    for turn in (-1, 0, 1):
        h = ((vic.heading - 1 + turn) % 6) + 1
        pos = vic.position
        traj = []
        for mf in range(1, sp + 1):
            nxt = safe_neighbor(pos, h, stT)
            if nxt is None:
                break
            pos = nxt
            traj.append((mf, pos.label))
        if traj:
            out.append({"label": f"hold_course_turn{turn:+d}", "traj": set(traj)})
    out.append({"label": "hold_in_place", "traj": set()})
    for hyp in out:
        for mf, label in hyp["traj"]:
            if mf > sp:
                raise AssertionError(f"public hypothesis exceeds observed speed: {hyp['label']}")
            d = vic.position.distance(HexCoord.from_label(label))
            if d > sp + 1:
                raise AssertionError(
                    f"public hypothesis cell {label} is {d} hexes from the observed "
                    f"position (limit {sp + 1}) — sealed data may have leaked")
    return out


def torpedo_census(log=print):
    t0 = time.time()
    out = {"arms": ["HOLD", "CURRENT_ADAPTIVE", "INTERCEPT_ASSIST", "PUBLIC_SET_COVER",
                    "PUBLIC_BELIEF_AWARE", "FULL_STATE_CEILING"],
           "materiality": {"R_shared_ge": TH_REL, "requires_different_best": True},
           "states": [], "shortfalls": {}}
    for scenario in SCENARIOS:
        picked = torpedo_states(scenario, log=log)
        out["shortfalls"][scenario] = TORP_QUOTA - len(picked)
        for seed, turn, st, eng, se in picked:
            rec = one_torpedo_state(scenario, seed, turn, st, eng, se, log=log)
            if rec:
                out["states"].append(rec)
                log(f"  s{seed} t{turn}: shooter={rec['shooter']} victim={rec['victim']} "
                    f"n_routes={rec['n_routes']} R_shared={rec['R_shared']} "
                    f"sel={rec['RR_by_arm']}")
            (OUT / "b1e_torpedo_partial.json").write_text(json.dumps(
                {k: v for k, v in out.items() if k != "states"} |
                {"n_states": len(out["states"])}, indent=1, default=str))
    out["summary"] = torpedo_summary(out["states"])
    out["wall_seconds"] = round(time.time() - t0, 1)
    (OUT / "b1e_torpedo_census.json").write_text(json.dumps(out, indent=1, default=str))
    log(json.dumps(out["summary"], indent=1))
    return out


def one_torpedo_state(scenario, seed, turn, stT, engT, seT, log=print):
    side = Side.ALLIES
    shooters = [x for x in ships_of(stT, side)
                if x.torpedo and any(l.loaded > 0 and not l.destroyed
                                     for l in x.torpedo_launchers)]
    if not shooters:
        return None
    enemies = ships_of(stT, OTHER[side])
    if not enemies:
        return None
    shooter = min(shooters, key=lambda x: min(
        x.position.distance(e.position) for e in enemies))
    victim = min(enemies, key=lambda e: shooter.position.distance(e.position))
    if shooter.position.distance(victim.position) > 14:
        return None
    st1, eng1 = advance_no_launch(stT, engT, seT)
    if st1 is None or victim.id not in st1.ships or st1.ships[victim.id].sunk:
        return None
    routes = victim_routes(eng1, st1, victim.id)
    if len(routes) < 10:
        return None
    trajs = {e["plan"]: set(route_trajectory(eng1, st1, victim.id, e["plan"]))
             for e in routes}
    cfgs = [c for c in enumerate_configs(engT, stT, side, stT.ships[shooter.id])]
    for c in cfgs:
        c["seg"] = set(t1_segment(c))
    cfgs = [c for c in cfgs if c["seg"]]
    if not cfgs:
        return None

    def D_bin(seg, traj):
        return 1.0 if (seg & traj) else 0.0

    def D_grad(seg, traj):
        return (len(seg & traj) / len(traj)) if traj else 0.0

    def rr(segs, key="bin"):
        if not segs:
            return 0.0
        unsafe = 0
        for traj in trajs.values():
            if any((seg & traj) for seg in segs):
                unsafe += 1
        return unsafe / len(trajs)

    # actions: every legal configuration is a legal (single-order) action
    acts = {i: c for i, c in enumerate(cfgs)}
    pub_h = public_hypotheses(stT, victim.id)
    public_inputs = ["victim.position", "victim.heading", "victim.current_speed",
                     "map_bounds", "engine._mount_can_bear/_can_see on own ships"]

    def cover_worst(seg):
        vals = []
        for h in pub_h:
            t = h["traj"]
            vals.append(len(seg & t) / max(1, len(t)) if t else 0.0)
        return min(vals)

    def cover_mean(seg):
        vals = []
        for h in pub_h:
            t = h["traj"]
            vals.append(len(seg & t) / max(1, len(t)) if t else 0.0)
        return sum(vals) / len(vals)

    pub_cover = max(acts.values(), key=lambda c: (cover_worst(c["seg"]), cover_mean(c["seg"])))
    pub_belief = max(acts.values(), key=lambda c: cover_mean(c["seg"]))
    fs_best = max(acts.values(), key=lambda c: sum(
        D_grad(c["seg"], t) for t in trajs.values()))
    # ---- Identifiability risks (PI formula) under TWO per-route payoffs.
    # D_bin (0/1 "route blocked") makes the formula degenerate whenever the
    # number of compatible routes exceeds what one action can touch: R_shared is
    # then 1 for every state regardless of hidden-state structure, so it measures
    # action-space coverage, not belief conflict (M22R-F2).  D_grad (fraction of
    # the route's own trajectory that the action blocks) keeps V_c per-route
    # achievable, which is what the formula presupposes.  Both are reported; the
    # graded form is primary and the binary form is kept as the counterexample.
    def risk(pay):
        coverable = [p for p, t in trajs.items()
                     if max(pay(c["seg"], t) for c in acts.values()) > 0]
        if not coverable:
            return {"R_shared": None, "R_bayes": None, "n_coverable": 0,
                    "n_distinct_best": 0, "jaccard": None, "V_min": None, "V_max": None}
        Vc_ = {p: max(pay(c["seg"], trajs[p]) for c in acts.values()) for p in coverable}
        rs, best_action = None, None
        for i, c in acts.items():
            worst = max(Vc_[p] - pay(c["seg"], trajs[p]) for p in coverable)
            if rs is None or worst < rs:
                rs, best_action = worst, i
        rb = min(sum(Vc_[p] - pay(c["seg"], trajs[p]) for p in coverable) / len(coverable)
                 for c in acts.values())
        per_route_best = {}
        for p in coverable:
            b = max(acts.items(), key=lambda kv: pay(kv[1]["seg"], trajs[p]))[0]
            per_route_best.setdefault(b, []).append(p)
        sets = []
        for i in per_route_best:
            sets.append(frozenset(p for p in coverable
                                  if pay(acts[i]["seg"], trajs[p]) > 0))
        jac = None
        if len(sets) >= 2:
            jac = len(sets[0] & sets[-1]) / max(1, len(sets[0] | sets[-1]))
        return {"R_shared": rs, "R_bayes": rb, "n_coverable": len(coverable),
                "n_distinct_best": len(per_route_best), "jaccard": jac,
                "best_action_index": best_action,
                "V_min": min(Vc_.values()), "V_max": max(Vc_.values())}

    risk_bin = risk(lambda seg, traj: D_bin(seg, traj))
    risk_grad = risk(lambda seg, traj: D_grad(seg, traj))
    # Control that separates the observational component from route diversity and
    # action-space size: the SAME formula evaluated on the route set the public
    # actor itself hypothesises (C_public).  A public set that is a superset of
    # the true routes can only raise R_shared, so
    #   R_shared(C_public) ~= R_shared(C_FULLSTATE)  ->  the regret is not
    #       primarily observational (it survives knowing the true route set);
    #   R_shared(C_public) >> R_shared(C_FULLSTATE)  ->  observational component.
    risk_public = None
    pub_trajs = [h["traj"] for h in pub_h if h["traj"]]
    if pub_trajs:
        def risk_on(pay, tset):
            cov = [t for t in tset if max(pay(c["seg"], t) for c in acts.values()) > 0]
            if not cov:
                return {"R_shared": None, "n_coverable": 0, "n_distinct_best": 0}
            Vc_ = {i: max(pay(c["seg"], t) for c in acts.values()) for i, t in enumerate(cov)}
            rs = None
            for c in acts.values():
                worst = max(Vc_[i] - pay(c["seg"], t) for i, t in enumerate(cov))
                if rs is None or worst < rs:
                    rs = worst
            per_best = {}
            for i, t in enumerate(cov):
                b = max(acts.items(), key=lambda kv: pay(kv[1]["seg"], t))[0]
                per_best.setdefault(b, []).append(i)
            return {"R_shared": rs, "n_coverable": len(cov),
                    "n_distinct_best": len(per_best)}
        risk_public = risk_on(lambda seg, traj: D_grad(seg, traj), pub_trajs)
    r_shared = risk_grad["R_shared"]
    r_bayes = risk_grad["R_bayes"]
    n_distinct = risk_grad["n_distinct_best"] or 0
    jac = risk_grad["jaccard"]
    material = bool(r_shared is not None and r_shared >= TH_REL and n_distinct > 1)
    # binary-payoff counterpart, kept as the counterexample record
    material_bin = bool(risk_bin["R_shared"] is not None
                        and risk_bin["R_shared"] >= TH_REL
                        and (risk_bin["n_distinct_best"] or 0) > 1)
    n_ok = risk_grad["n_coverable"]
    # deployed commander
    cur_segs, cur_meta = [], {"n_orders": 0}
    cmd = TacticalCommander(profile=PROFILES["balanced"])
    st_c = stT.model_copy(deep=True)
    e_c = IronBottomEngine(); e_c.games[st_c.game_id] = st_c
    try:
        _, b_c, _ = cmd.choose_plan(e_c, st_c.game_id, side)
        cur_meta["n_orders"] = len(getattr(b_c, "torpedoes", []) or [])
        if cur_meta["n_orders"] and e_c.validate_orders(st_c.game_id, b_c).valid:
            e_c.submit_orders(st_c.game_id, b_c)
            if advance_with_scripts(e_c, st_c, seT, stop_phase=Phase.MOVEMENT_PLANNING) \
                    and st_c.phase == Phase.MOVEMENT_PLANNING:
                for t in st_c.torpedo_tracks:
                    if t.launched_turn >= stT.turn:
                        try:
                            step = torpedo_step_positions(
                                t, st_c.turn, set(st_c.land_hexes),
                                columns=st_c.map_columns, rows=st_c.map_rows)
                        except ValueError as exc:
                            cur_meta.setdefault("step_errors", []).append(str(exc))
                            continue
                        cur_segs.append({(mf, h) for mf, h in step})
    except Exception as exc:  # noqa: BLE001
        cur_meta["error"] = f"{type(exc).__name__}: {exc}"
    cur_meta["segs_nonempty"] = sum(1 for s in cur_segs if s)
    # engine's own intercept combos
    inter_rr, inter_meta = 0.0, {"combos": 0}
    try:
        combos = [c for c in engT.torpedo_tactical_combos(stT, side)
                  if c.get("ship_id") == shooter.id and not c.get("blocked_reason")]
        inter_meta["combos"] = len(combos)
        if combos:
            best = max(combos, key=lambda c: float(c.get("expected_hits") or 0))
            seg = {(i + 1, h) for i, h in enumerate(best.get("predicted_path") or [])}
            inter_rr = rr([seg])
            inter_meta["chosen"] = {k: best.get(k) for k in
                                    ("launcher_id", "setting_index", "launch_angle",
                                     "launch_at_mf", "salvo_size")}
    except Exception as exc:  # noqa: BLE001
        inter_meta["error"] = f"{type(exc).__name__}: {exc}"
    RR = {"HOLD": 0.0,
          "CURRENT_ADAPTIVE": rr(cur_segs),
          "INTERCEPT_ASSIST": inter_rr,
          "PUBLIC_SET_COVER": rr([pub_cover["seg"]]),
          "PUBLIC_BELIEF_AWARE": rr([pub_belief["seg"]]),
          "FULL_STATE_CEILING": rr([fs_best["seg"]])}
    grad = {"PUBLIC_SET_COVER": cover_worst(pub_cover["seg"]),
            "PUBLIC_BELIEF_AWARE": cover_mean(pub_belief["seg"]),
            "FULL_STATE_CEILING": sum(D_grad(fs_best["seg"], t) for t in trajs.values())
            / len(trajs)}
    return {"scenario": scenario, "seed": seed, "turn": turn, "side": side.value,
            "shooter": shooter.id, "victim": victim.id,
            "n_routes": len(trajs), "n_routes_coverable": n_ok,
            "n_configs": len(cfgs), "n_public_hypotheses": len(pub_h),
            "RR_by_arm": RR, "graded_cover": grad,
            "R_shared": r_shared, "R_bayes_uniform": r_bayes,
            "DIFFERENT_BEST": n_distinct > 1,
            "n_distinct_best_actions": n_distinct,
            "best_set_jaccard_first_last": jac,
            "material": material,
            "risk_binary": risk_bin, "material_binary": material_bin,
            "risk_public_hypotheses": risk_public,
            "per_route_payoff": "D_grad = blocked fraction of the route's own trajectory",
            "current_meta": cur_meta, "intercept_meta": inter_meta,
            "public_choice": {"setting": pub_cover["setting_index"],
                              "side": pub_cover["launch_side"],
                              "angle": pub_cover["launch_angle"]},
            "fullstate_choice": {"setting": fs_best["setting_index"],
                                 "side": fs_best["launch_side"],
                                 "angle": fs_best["launch_angle"]},
            "public_hypotheses": [h["label"] for h in pub_h],
            "public_inputs": public_inputs}


def torpedo_summary(states):
    if not states:
        return {"n_states": 0}
    per = {}
    for scen in SCENARIOS:
        rows = [r for r in states if r["scenario"] == scen]
        if not rows:
            continue
        per[scen] = {
            "n": len(rows),
            "material_rate": sum(r["material"] for r in rows) / len(rows),
            "median_R_shared": _median([r["R_shared"] for r in rows]),
            "median_R_bayes_uniform": _median([r["R_bayes_uniform"] for r in rows]),
            "mean_RR": {arm: sum(r["RR_by_arm"][arm] for r in rows) / len(rows)
                        for arm in rows[0]["RR_by_arm"]},
            "current_fired_rate": sum(1 for r in rows if r["current_meta"].get("n_orders")) / len(rows),
        }
    return {"n_states": len(states),
            "states_per_scenario": dict(Counter(r["scenario"] for r in states)),
            "material_rate_pooled": sum(r["material"] for r in states) / len(states),
            "median_R_shared_pooled": _median([r["R_shared"] for r in states]),
            "per_scenario": per,
            "verdict_inputs": {
                "material_ge_20pct_in_ge_2_scenarios":
                    sum(1 for v in per.values() if v["material_rate"] >= 0.20) >= 2}}


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else "movement"
    if which == "movement":
        movement_census()
    elif which == "movement_summary":
        rows = [json.loads(line) for line in
                (OUT / "b1e_movement_states.jsonl").read_text().splitlines() if line.strip()]
        out = {"states": rows, "summary": summarize(rows),
               "arms": ["CURRENT_POLICY", NAME_PRE_FIX, NAME_REPAIRED,
                        "BEAM_SEARCH_COMPILER", "RANDOM_LEGAL"],
               "recovered_from": "b1e_movement_states.jsonl"}
        (OUT / "b1e_movement_census.json").write_text(json.dumps(out, indent=1, default=str))
        print(json.dumps(out["summary"], indent=1, default=str))
    elif which == "mg3e":
        mg3e()
    elif which == "torpedo":
        torpedo_census()
    else:
        raise SystemExit(f"unknown subcommand {which}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
