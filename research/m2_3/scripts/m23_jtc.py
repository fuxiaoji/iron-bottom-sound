"""M2.3 JTC — Joint Tactical Compilation cheap-kill.

MID and DAMAGED supplemental state sets (never merged into the old prevalence),
three intent families, five methods, local/team/externality per (state, intent).

    PYTHONPATH=backend/src:research/m2_3/scripts:research/m2_2r/scripts:research/m2_2/scripts:research/m2_1/scripts \
        .venv/bin/python research/m2_3/scripts/m23_jtc.py [mid|damaged|all]
"""

from __future__ import annotations

import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "m2_2r" / "scripts"))
sys.path.insert(0, str(HERE.parents[1] / "m2_2" / "scripts"))

from b1e import (SCENARIOS, _decomposed_scores, play_movement,  # noqa: E402
                 team_metric)
from intent_compiler import repaired_intent_plans  # noqa: E402
from iron_bottom_sound.engine import IronBottomEngine  # noqa: E402
from iron_bottom_sound.models import GameOptions, Phase, Side  # noqa: E402
from iron_bottom_sound.tactical import PROFILES, TacticalCommander  # noqa: E402
from m22_b0 import OTHER as MC_OTHER  # noqa: E402
from mg.mg_cases import bearing_to, plan_for_pose  # noqa: E402
from mg.micro import plan_tables, scripted_plans  # noqa: E402

OUT = HERE.parent / "metrics"
OUT.mkdir(exist_ok=True, parents=True)

MID_WINDOWS = {"IBS-S-01": (3, 5), "IBS-S-03": (2, 3), "IBS-S-EM-01": (4, 8)}
MID_TARGET = 12
DMG_TARGET = 12
BEAM_WIDTH = 64
REAL_BUDGET = 8          # real engine plays per arm, matched between beam and random
PLAN_LIMIT = 8
RNG_SEED = 20260921
INTENTS = ("I1_BROADSIDE", "I2_RANGE", "I3_RAKING")


# --------------------------------------------------------------------------
# state scan
# --------------------------------------------------------------------------


def _damaged(st, side, strict=False):
    for s in st.ships.values():
        if s.side != side or s.sunk or not s.position:
            continue
        lim = 0.75 * s.max_hull if strict else s.max_hull
        if s.hull < lim or s.mfc_destroyed or s.radar_destroyed:
            return True
    return False


def scan_states(mode, log=print):
    """mode 'mid' = deterministic turn windows; mode 'damaged' = event-conditioned."""
    picked = {}
    diag = {}
    for scenario in SCENARIOS:
        rows = []
        for seed in range(1, 9):
            eng = IronBottomEngine()
            st = eng.reset(scenario, seed, GameOptions(mode="llm"))
            se = {s: TacticalCommander(profile=PROFILES["balanced"]) for s in Side}
            g = 0
            while st.phase != Phase.COMPLETE and g < 400:
                g += 1
                if st.phase == Phase.MOVEMENT_PLANNING and st.turn >= 2:
                    snap = st.model_copy(deep=True)
                    e_snap = IronBottomEngine()
                    e_snap.games[snap.game_id] = snap
                    if mode == "mid":
                        lo, hi = MID_WINDOWS[scenario]
                        if lo <= st.turn <= hi:
                            for side in (Side.AXIS, Side.ALLIES):
                                rows.append((seed, st.turn, side, snap, e_snap, se))
                    else:
                        for side in (Side.AXIS, Side.ALLIES):
                            if _damaged(snap, side):
                                rows.append((seed, st.turn, side, snap, e_snap, se))
                if st.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                                Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                                Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
                    for s in Side:
                        if s.value not in st.submitted_orders:
                            try:
                                eng.submit_orders(st.game_id,
                                                  se[s].choose_plan(eng, st.game_id, s)[1])
                            except Exception:  # noqa: BLE001
                                pass
                try:
                    eng.advance(st.game_id)
                except Exception:  # noqa: BLE001
                    break
        rows.sort(key=lambda r: (r[0], r[1], r[2].value))
        picked[scenario] = rows[:MID_TARGET if mode == "mid" else DMG_TARGET]
        # diagnostics: literal vs strict predicate coverage over the scanned pool
        diag[scenario] = {
            "pool_state_sides": len(rows),
            "strict_0.75max_pool_state_sides": sum(
                1 for r in rows if _damaged(r[3], r[2], strict=True)),
        }
        log(f"  {scenario} [{mode}]: pool={len(rows)} picked={len(picked[scenario])} "
            f"strict={diag[scenario]['strict_0.75max_pool_state_sides']}")
    return picked, diag


# --------------------------------------------------------------------------
# intent compilers (per-ship research rules; no value search)
# --------------------------------------------------------------------------


def intent_focal(st, side):
    """The lever pair: most own mounts bearing on one enemy at the current
    geometry (deterministic, outcome-free) — same rule as B1E."""
    eng_ok = True
    opp = MC_OTHER[side]
    best, key = (None, None), None
    for a in sorted((s for s in st.ships.values()
                     if s.side == side and not s.sunk and s.position), key=lambda s: s.id):
        for b in sorted((s for s in st.ships.values()
                         if s.side == opp and not s.sunk and s.position), key=lambda s: s.id):
            n = sum(1 for m in a.gun_mounts
                    if not m.destroyed
                    and IronBottomEngine._mount_can_bear(a, b, m.arcs))
            k = (-n, a.id, b.id)
            if key is None or k < key:
                best, key = (a.id, b.id), k
    return best


def raking_rule_plan(eng, st, side, ship, enemies):
    """I3 compiler: the reachable hex with the most enemies presenting bow/stern
    to us, judged by the engine's own `_target_aspect`; ties by fewer turns then
    plan string.  No value function, no search over outcomes.

    Note: in this engine the longitudinal modifier is a property of the TARGET's
    heading relative to the bearing to us, so it depends on our *position* and not
    on our own heading — the compiler therefore selects a station, not a turn.
    """
    from types import SimpleNamespace
    from iron_bottom_sound.models import HexCoord
    info = eng.movement_candidates(st, ship, include_plans=True)
    best, key = None, None
    for e in info.get("reachable", []):
        plan = e.get("plan")
        if not plan:
            continue
        turns = plan.count("P") - plan.count("S")
        stand = SimpleNamespace(position=HexCoord(**e["hex"]), heading=ship.heading)
        n_rake = n_legal = 0
        for tgt in enemies:
            # own fire legality at the candidate station
            if not (eng._can_see(st, ship, tgt)
                    and any(not m.destroyed for m in ship.gun_mounts)):
                continue
            n_legal += 1
            if IronBottomEngine._target_aspect(stand, tgt) == "bow_stern":
                n_rake += 1
        k = (-n_rake, turns, plan)
        if key is None or k < key:
            best, key = plan, k
    return best


def compile_intent(eng, st, side, intent, focal, target):
    """The repaired research intent compiler for one intent."""
    enemies = [s for s in st.ships.values()
               if s.side != side and not s.sunk and s.position]
    if intent == "I1_BROADSIDE":
        return repaired_intent_plans(eng, st, side, "BROADSIDE", enemies)
    f = st.ships[focal]
    t = st.ships[target]
    tables = plan_tables(eng, st, side)
    plans = tables.get(focal, set())
    b = bearing_to(f.position, t.position)
    if intent == "I2_RANGE":
        toward = plan_for_pose(eng, st, f, plans, b, +1)
        away = plan_for_pose(eng, st, f, plans, ((b - 1 + 3) % 6) + 1, +1)
        pol = scripted_plans(eng, st, side)
        return {"_candidates": {"CLOSE": {**pol, focal: toward},
                                "OPEN": {**pol, focal: away}},
                "_primary": {**pol, focal: toward}}
    if intent == "I3_RAKING":
        pol = scripted_plans(eng, st, side)
        plan = raking_rule_plan(eng, st, side, f, enemies)
        return {**pol, focal: plan} if plan else pol
    raise ValueError(intent)


# --------------------------------------------------------------------------
# local metrics
# --------------------------------------------------------------------------


def local_metric(eng, st, intent, focal, target):
    f, t = st.ships.get(focal), st.ships.get(target)
    if f is None or t is None or f.sunk or t.sunk or not f.position or not t.position:
        return {"M": 0.0, "executable": False, "distance": None,
                "visible": False, "mounts": 0, "raking": 0, "legal_pairs": 0}
    vis = bool(eng._can_see(st, f, t))
    mounts = [m for m in f.gun_mounts if not m.destroyed
              and eng._mount_can_bear(f, t, m.arcs)]
    from m22_core import _group_eh
    eh = _group_eh(eng, st, f, mounts, t, 1, 1)
    d = f.position.distance(t.position)
    # raking fraction over ALL own legal firing pairs
    pairs = 0
    rake = 0
    for a in st.ships.values():
        if a.side != f.side or a.sunk or not a.position:
            continue
        for b in st.ships.values():
            if b.side == f.side or b.sunk or not b.position:
                continue
            if not eng._can_see(st, a, b):
                continue
            if not any(not m.destroyed and eng._mount_can_bear(a, b, m.arcs)
                       for m in a.gun_mounts):
                continue
            pairs += 1
            if eng._target_aspect(a, b) == "bow_stern":
                rake += 1
    frac = rake / pairs if pairs else 0.0
    M = {"I1_BROADSIDE": eh, "I2_RANGE": -float(d), "I3_RAKING": frac}[intent]
    return {"M": M, "eh": eh, "executable": bool(vis and mounts), "distance": d,
            "visible": vis, "mounts": len(mounts), "raking": rake,
            "legal_pairs": pairs, "raking_fraction": frac}


# --------------------------------------------------------------------------
# arms
# --------------------------------------------------------------------------


def plan_pools(eng, st, side, policy_map):
    ships = sorted(s.id for s in st.ships.values()
                   if s.side == side and not s.sunk and s.position)
    pools = {}
    for sid in ships:
        info = eng.movement_candidates(st, st.ships[sid], include_plans=True)
        entries = [e for e in info.get("reachable", []) if e.get("plan")]
        if not entries:
            pools[sid] = [policy_map.get(sid, "0")]
            continue

        def adv(e):
            return sum(int(c) for c in e["plan"] if c.isdigit())

        order = sorted(entries, key=adv)
        pool = [policy_map.get(sid), "0", order[0]["plan"], order[-1]["plan"]]
        pool += [e["plan"] for e in entries]
        pools[sid] = [p for p in dict.fromkeys(pool) if p][:PLAN_LIMIT]
    return ships, pools


def beam_joints(eng, st, side, policy_map, enemy_plans, pools, ships, rng):
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
    top = [a for a, _ in beams[:REAL_BUDGET]]
    rand = []
    for _ in range(REAL_BUDGET):
        rand.append({sid: rng.choice(pools[sid]) for sid in ships})
    return top, rand


def greedy_joint(eng, st, side, policy_map, enemy_plans, pools, ships):
    contrib = _decomposed_scores(eng, st, side, policy_map, enemy_plans, pools, ships)
    out = {}
    for sid in ships:
        row = contrib.get(sid) or {}
        out[sid] = max(row.items(), key=lambda kv: (kv[1], kv[0]))[0] if row \
            else policy_map.get(sid, "0")
    return out


def run_state(scenario, seed, turn, side, st, eng, se, log=None):
    """Play the shared arms ONCE, then evaluate each intent's local metric on the
    resulting states.  The intent compilers are the only intent-specific plays."""
    policy_map = scripted_plans(eng, st, side)
    enemy_plans = scripted_plans(eng, st, MC_OTHER[side])
    focal, target = intent_focal(st, side)
    if focal is None:
        return []
    ships, pools = plan_pools(eng, st, side, policy_map)
    rng = random.Random(RNG_SEED + seed * 1000 + turn * 10 + list(Side).index(side))
    top, rand = beam_joints(eng, st, side, policy_map, enemy_plans, pools, ships, rng)
    greedy = greedy_joint(eng, st, side, policy_map, enemy_plans, pools, ships)

    def play(plan_map):
        st2, e2, err = play_movement(st, side, plan_map, enemy_plans, se)
        return None if st2 is None else (st2, e2)

    base = play(policy_map)
    # ADMISSION RULE (frozen before measurement, PRE_REGISTRATION_M23 §4.3): the
    # state-side is admitted only if the focal pair survives movement resolution
    # under the CURRENT arm.  Enemy movement is byte-identical across arms, so
    # this filter is arm-independent and cannot favour a method; a pair that dies
    # in the baseline would make M(current) = 0 and manufacture a spurious
    # opportunity (observed: a hull-2 target sunk during movement resolution).
    if base is None:
        return [{"_rejected": "current_arm_failed"}]
    bf, bt = base[0].ships.get(focal), base[0].ships.get(target)
    if bf is None or bt is None or bf.sunk or bt.sunk or not bf.position or not bt.position:
        return [{"_rejected": "pair_lost_during_movement"}]
    played = {"CURRENT_PRODUCTION_POLICY": base,
              "PER_SHIP_GREEDY": play(greedy)}
    for i, a in enumerate(top):
        played[f"BEAM_{i}"] = play(a)
    for i, a in enumerate(rand):
        played[f"RAND_{i}"] = play(a)

    rows = []
    for intent in INTENTS:
        cand = compile_intent(eng, st, side, intent, focal, target)
        intent_played = {}
        if intent == "I2_RANGE":
            for name, pm in cand["_candidates"].items():
                intent_played[f"REPAIRED_RANGE_{name}"] = play(pm)
        else:
            intent_played["REPAIRED_RESEARCH_INTENT"] = play(cand)
        st_plays = dict(played)
        st_plays.update(intent_played)

        def meval(key):
            pl = st_plays.get(key)
            if pl is None:
                return None
            st2, e2 = pl
            return {"L0": local_metric(e2, st2, intent, focal, target),
                    "L1": team_metric(e2, st2, side)}

        cur = meval("CURRENT_PRODUCTION_POLICY")
        if cur is None:
            continue
        rec = {"scenario": scenario, "seed": seed, "turn": turn, "side": side.value,
               "intent": intent, "focal": focal, "target": target, "arms": {}}
        rec["arms"]["CURRENT_PRODUCTION_POLICY"] = cur
        if intent == "I2_RANGE":
            best_name, best_v = None, None
            for name in ("REPAIRED_RANGE_CLOSE", "REPAIRED_RANGE_OPEN"):
                m = meval(name)
                if m is None:
                    continue
                rec["arms"][name] = m
                sc = m["L0"]["M"] - cur["L0"]["M"]
                if best_v is None or sc > best_v:
                    best_v, best_name = sc, name
            if best_name:
                rec["arms"]["REPAIRED_RESEARCH_INTENT"] = rec["arms"][best_name]
                rec["range_direction"] = best_name.split("_")[-1]
        else:
            rec["arms"]["REPAIRED_RESEARCH_INTENT"] = meval("REPAIRED_RESEARCH_INTENT")
        rec["arms"]["PER_SHIP_GREEDY"] = meval("PER_SHIP_GREEDY")
        cur_M = cur["L0"]["M"]
        beam_ms = [(meval(f"BEAM_{i}"), i) for i in range(len(top))]
        beam_ms = [(m, i) for m, i in beam_ms if m]
        if beam_ms:
            ok = [x for x in beam_ms if x[0]["L0"]["M"] >= cur_M]
            if ok:
                ok.sort(key=lambda x: (-x[0]["L1"]["U_team"], x[1]))
                rec["arms"]["JOINT_BEAM_SEARCH"] = ok[0][0]
                rec["beam_selected_by_constraint"] = True
            else:
                beam_ms.sort(key=lambda x: (-x[0]["L0"]["M"], -x[0]["L1"]["U_team"], x[1]))
                rec["arms"]["JOINT_BEAM_SEARCH"] = beam_ms[0][0]
                rec["beam_selected_by_constraint"] = False
        rnd_ms = [(meval(f"RAND_{i}"), i) for i in range(len(rand))]
        rnd_ms = [(m, i) for m, i in rnd_ms if m]
        if rnd_ms:
            ok = [x for x in rnd_ms if x[0]["L0"]["M"] >= cur_M]
            pick = ok or rnd_ms
            pick.sort(key=lambda x: (-x[0]["L1"]["U_team"], x[1]))
            rec["arms"]["RANDOM_MATCHED_BUDGET"] = pick[0][0]
        rows.append(rec)
    return rows


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    t0 = time.time()
    out = {"intents": list(INTENTS), "windows": MID_WINDOWS,
           "real_budget": REAL_BUDGET, "beam_width": BEAM_WIDTH, "states": []}
    rej, rej_by_scen = Counter(), {}
    for m in (("mid", "damaged") if mode == "all" else (mode,)):
        picked, diag = scan_states(m)
        out[f"{m}_pool_diagnostics"] = diag
        for scenario in SCENARIOS:
            for seed, turn, side, st, eng, se in picked[scenario]:
                rows = run_state(scenario, seed, turn, side, st, eng, se)
                if rows and "_rejected" in rows[0]:
                    rej[rows[0]["_rejected"]] = rej.get(rows[0]["_rejected"], 0) + 1
                    rej_by_scen.setdefault(f"{m}:{scenario}", Counter())[
                        rows[0]["_rejected"]] += 1
                    continue
                for r in rows:
                    r["panel"] = m
                    out["states"].append(r)
                print(f"  [{m}] {scenario} s{seed} t{turn} {side.value}: "
                      f"{len(rows)} intent rows", flush=True)
                (OUT / "m23_jtc_partial.json").write_text(json.dumps(
                    {k: v for k, v in out.items() if k != "states"} |
                    {"n_rows": len(out["states"])}, indent=1, default=str))
    out["rejections"] = dict(rej)
    out["rejections_by_panel_scenario"] = {k: dict(v) for k, v in rej_by_scen.items()}
    out["wall_seconds"] = round(time.time() - t0, 1)
    (OUT / "m23_jtc_census.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"done: {len(out['states'])} (state, intent) rows in {out['wall_seconds']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
