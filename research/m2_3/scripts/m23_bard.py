"""M2.3 BARD — Belief-Aware Route Denial under Hidden Commitments cheap-kill.

Same-public-history information sets, matched size/diversity control, the full
hidden-state x action payoff matrix, risk metrics and deployable public planners.

    PYTHONPATH=backend/src:research/m2_3/scripts:research/m2_2r/scripts:research/m2_2/scripts:research/m2_1/scripts \
        .venv/bin/python research/m2_3/scripts/m23_bard.py
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "m2_2r" / "scripts"))
sys.path.insert(0, str(HERE.parents[1] / "m2_2" / "scripts"))

from b1e import (SCENARIOS, OTHER, safe_neighbor)  # noqa: E402
from m22_b0 import plan_cost  # noqa: E402
from b1e import _median  # noqa: E402
from intent_compiler import repaired_intent_plans  # noqa: E402
from iron_bottom_sound.engine import IronBottomEngine  # noqa: E402
from iron_bottom_sound.models import (HexCoord, MovementOrder,  # noqa: E402
                                      OrderBatch, Phase, Side)
from iron_bottom_sound.tactical import PROFILES, TacticalCommander  # noqa: E402
from mg.mg4r import (advance_with_scripts, route_trajectory,  # noqa: E402
                     torpedo_step_positions, victim_routes)
from mg.mg4r_corridor import enumerate_configs, t1_segment  # noqa: E402
from mg.micro import reach  # noqa: E402

OUT = HERE.parent / "metrics"
OUT.mkdir(exist_ok=True, parents=True)
K_HIDDEN = 6
TH_SHARED = 0.25
TH_PUBLIC_RECOVERY = 0.50


# --------------------------------------------------------------------------
# information sets: hidden = the opponent's sealed movement plan for turn T
# --------------------------------------------------------------------------


def movement_plan_pool(eng, st, ship, limit=K_HIDDEN):
    info = eng.movement_candidates(st, ship, include_plans=True)
    plans = [e["plan"] for e in info.get("reachable", []) if e.get("plan")]
    # deterministic engine order, first K; "0" (hold) included if legal
    out = []
    for p in plans:
        if p not in out:
            out.append(p)
        if len(out) >= limit:
            break
    return out


def observation_hash(eng, st, side):
    obs = eng.observe(st.game_id, side)
    parts = []
    for s in sorted(obs.ships, key=lambda x: x.id):
        pos = s.position.label if s.position else None
        parts.append(f"{s.id}:{pos}:{s.heading}:{s.hull}:{s.sunk}:{s.current_speed}")
    for t in sorted(getattr(obs, "torpedo_tracks", []) or [], key=lambda x: x.id):
        parts.append(f"T:{t.id}:{t.position.label}:{t.heading}")
    for m in sorted(getattr(obs, "markers", []) or [], key=lambda x: x.id):
        parts.append(f"M:{m.id}:{m.kind}")
    return json.dumps(parts)


def variant_states(stM, engM, se, victim_id, shooter_id, victim_plan):
    """From the turn's MOVEMENT_PLANNING state, submit the victim's sealed plan,
    resolve to TORPEDO_PLANNING (the shooter's decision instant) and then to T+1.

    Returns (h_state, h_eng, t1_state, t1_eng) or (None, ...).  The shooter's own
    movement is at policy in every variant, so the only difference is the victim's
    sealed plan.
    """
    from mg.micro import scripted_plans
    vside = stM.ships[victim_id].side
    pm = {**scripted_plans(engM, stM, vside), victim_id: victim_plan}
    oth = scripted_plans(engM, stM, OTHER[vside])
    st1 = stM.model_copy(deep=True)
    e1 = IronBottomEngine()
    e1.games[st1.game_id] = st1
    for sd, plans in ((vside, pm), (OTHER[vside], oth)):
        b = OrderBatch(side=sd, phase=Phase.MOVEMENT_PLANNING)
        for sid, plan in plans.items():
            ship = st1.ships.get(sid)
            if ship is None or ship.sunk or not ship.position:
                continue
            c = plan_cost(e1, st1, ship, plan)
            b.movement.append(MovementOrder(ship_id=sid, plan=plan, speed=c))
        if not b.movement:
            continue
        if not e1.validate_orders(st1.game_id, b).valid:
            return None, None, None, None
        e1.submit_orders(st1.game_id, b)
    g = 0
    while st1.phase not in (Phase.TORPEDO_PLANNING, Phase.COMPLETE) and g < 6:
        g += 1
        e1.advance(st1.game_id)
    if st1.phase != Phase.TORPEDO_PLANNING:
        return None, None, None, None
    h_state, h_eng = st1, e1
    st2 = st1.model_copy(deep=True)
    e2 = IronBottomEngine()
    e2.games[st2.game_id] = st2
    if not advance_with_scripts(e2, st2, se, stop_phase=Phase.MOVEMENT_PLANNING):
        return None, None, None, None
    if st2.phase != Phase.MOVEMENT_PLANNING:
        return None, None, None, None
    return h_state, h_eng, st2, e2


def action_signature(cfgs):
    return sorted((c["cfg"]["launcher_id"], c["cfg"]["launch_at_mf"],
                   c["cfg"]["launch_side"], c["cfg"]["launch_angle"],
                   c["cfg"]["setting_index"], c["cfg"]["salvo"]) for c in cfgs)


def action_configs(engT, stT, side, shooter_id, cap=400):
    cfgs = enumerate_configs(engT, stT, side, stT.ships[shooter_id])
    out = []
    for c in cfgs:
        seg = set(t1_segment(c))
        if seg:
            out.append({"cfg": c, "seg": seg})
        if len(out) >= cap:
            break
    return out


def straight_matched(traj, start_pos, st):
    """Matched-kinematics straight-line surrogate: same MF length and same net
    displacement from the observed start, with no commitment structure."""
    if not traj:
        return set()
    pts = sorted(traj)
    end_label = pts[-1][1]
    end = HexCoord.from_label(end_label)
    n = len(pts)
    dq, dr = end.q - start_pos.q, end.r - start_pos.r
    from mg.mg_cases import DIRS
    heading = max(range(1, 7),
                  key=lambda h: dq * DIRS[h][0] + dr * DIRS[h][1])
    cells = set()
    pos = start_pos
    for mf in range(1, n + 1):
        nxt = safe_neighbor(pos, heading, st)
        if nxt is None:
            break
        pos = nxt
        cells.add((mf, pos.label))
    return cells


def public_naive(stT, victim_id, speed_cap=6):
    """Naive public hypothesis: hold course from the observed position."""
    vic = stT.ships[victim_id]
    sp = max(1, min(int(getattr(vic, "current_speed", 2) or 2), speed_cap))
    cells = set()
    pos = vic.position
    for mf in range(1, sp + 1):
        nxt = safe_neighbor(pos, vic.heading, stT)
        if nxt is None:
            break
        pos = nxt
        cells.add((mf, pos.label))
    return cells


def one_information_set(scenario, seed, turn, stM, engM, se, log=None):
    side = Side.ALLIES
    shooters = [x for x in stM.ships.values()
                if x.side == side and not x.sunk and x.position and x.torpedo
                and any(l.loaded > 0 and not l.destroyed for l in x.torpedo_launchers)]
    enemies = [x for x in stM.ships.values()
               if x.side == OTHER[side] and not x.sunk and x.position]
    if not shooters or not enemies:
        return {"_rejected": "no_shooter_or_enemy"}
    shooter = min(shooters, key=lambda x: min(x.position.distance(e.position)
                                              for e in enemies))
    victim = min(enemies, key=lambda e: shooter.position.distance(e.position))
    if shooter.position.distance(victim.position) > 14:
        return {"_rejected": "out_of_range"}
    plans = movement_plan_pool(engM, stM, stM.ships[victim.id])
    if len(plans) < 2:
        return {"_rejected": "victim_has_one_plan"}

    variants, cfgs_ref, sig_ref, hash_ref = [], None, None, None
    for p in plans:
        h_state, h_eng, t1_state, t1_eng = variant_states(
            stM, engM, se, victim.id, shooter.id, p)
        if h_state is None:
            continue
        # (1) identical public observation/history?
        h = observation_hash(h_eng, h_state, side)
        if hash_ref is None:
            hash_ref = h
        elif h != hash_ref:
            variants.append({"plan": p, "_hash_mismatch": True})
            continue
        # (2) identical focal legal action set?
        cfgs = action_configs(h_eng, h_state, side, shooter.id)
        if not cfgs:
            continue
        sig = action_signature(cfgs)
        if sig_ref is None:
            sig_ref, cfgs_ref = sig, cfgs
        elif sig != sig_ref:
            variants.append({"plan": p, "_action_mismatch": True})
            continue
        # (3) only the sealed route differs
        if t1_state.ships.get(victim.id) is None or t1_state.ships[victim.id].sunk \
                or not t1_state.ships[victim.id].position:
            continue
        routes = victim_routes(t1_eng, t1_state, victim.id)
        if len(routes) < 3:
            continue
        trajs = [set(route_trajectory(t1_eng, t1_state, victim.id, e["plan"]))
                 for e in routes]
        variants.append({"plan": p, "trajs": trajs, "n_routes": len(trajs),
                         "victim_pos": t1_state.ships[victim.id].position.label})
    bad = [v for v in variants if v.get("_hash_mismatch") or v.get("_action_mismatch")]
    good = [v for v in variants if not v.get("_hash_mismatch")
            and not v.get("_action_mismatch")]
    if len(good) < 2:
        return {"_rejected": "few_valid_variants", "n_good": len(good),
                "n_hash_mismatch": sum(1 for v in bad if v.get("_hash_mismatch")),
                "n_action_mismatch": sum(1 for v in bad if v.get("_action_mismatch"))}
    variants, cfgs = good, cfgs_ref
    n_a = len(cfgs)

    def rr_over(seg, trajs):
        if not trajs:
            return 0.0
        return sum(1 for t in trajs if (seg & t)) / len(trajs)

    M = [[rr_over(c["seg"], v["trajs"]) for c in cfgs] for v in variants]
    n_h = len(M)

    def risk(mat):
        V = [max(row) for row in mat]
        r_shared = min(max(V[i] - mat[i][j] for i in range(len(mat)))
                       for j in range(len(mat[0])))
        r_bayes = min(sum(V[i] - mat[i][j] for i in range(len(mat))) / len(mat)
                      for j in range(len(mat[0])))
        best = [max(range(len(mat[0])), key=lambda j: mat[i][j]) for i in range(len(mat))]
        eps = any(all(mat[i][j] >= V[i] - TH_SHARED for i in range(len(mat)))
                  for j in range(len(mat[0])))
        return {"R_shared": r_shared, "R_bayes": r_bayes,
                "n_distinct_best": len(set(best)), "best_actions": best,
                "eps_good_shared": eps, "crossover": len(set(best)) > 1, "V": V}

    true_risk = risk(M)
    M_match = []
    for v in variants:
        # anchor at THIS variant's T+1 victim position: anchoring at the
        # pre-movement position displaces the surrogate by the victim's own
        # T-move and makes it disjoint from every corridor, which would report
        # R_shared = 0 for a reason that has nothing to do with the hypothesis
        # set (M23-F1).
        start = HexCoord.from_label(v["victim_pos"])
        group = [straight_matched(t, start, stM) for t in v["trajs"]]
        M_match.append([sum(1 for t in group if (c["seg"] & t)) / max(1, len(group))
                        for c in cfgs])
    match_risk = risk(M_match)
    nz = sum(1 for row in M_match for x in row if x > 0)
    match_diag = {"matrix_cells": len(M_match) * max(1, len(M_match[0])),
                  "nonzero_cells": nz,
                  "mean_overlap": (sum(sum(row) for row in M_match)
                                   / max(1, len(M_match) * len(M_match[0]))),
                  "degenerate": nz == 0}
    naive = public_naive(stM, victim.id)
    naive_risk = risk([[1.0 if (c["seg"] & naive) else 0.0 for c in cfgs]])

    cur_segs, cur_meta = [], {"n_orders": 0}
    cmd = TacticalCommander(profile=PROFILES["balanced"])
    st_c = stM.model_copy(deep=True)
    e_c = IronBottomEngine()
    e_c.games[st_c.game_id] = st_c
    try:
        _, b_c, _ = cmd.choose_plan(e_c, st_c.game_id, side)
        cur_meta["n_orders"] = len(getattr(b_c, "torpedoes", []) or [])
        if cur_meta["n_orders"] and e_c.validate_orders(st_c.game_id, b_c).valid:
            e_c.submit_orders(st_c.game_id, b_c)
            if advance_with_scripts(e_c, st_c, se, stop_phase=Phase.MOVEMENT_PLANNING) \
                    and st_c.phase == Phase.MOVEMENT_PLANNING:
                for t in st_c.torpedo_tracks:
                    if t.launched_turn >= stM.turn:
                        try:
                            step = torpedo_step_positions(
                                t, st_c.turn, set(st_c.land_hexes),
                                columns=st_c.map_columns, rows=st_c.map_rows)
                        except ValueError:
                            continue
                        cur_segs.append({(mf, hh) for mf, hh in step})
    except Exception as exc:  # noqa: BLE001
        cur_meta["error"] = f"{type(exc).__name__}: {exc}"

    def mean_true(seg):
        return 0.0 if not seg else sum(rr_over(seg, v["trajs"])
                                       for v in variants) / len(variants)

    robust_j, best_v = None, None
    for j in range(n_a):
        w = min(M_match[i][j] for i in range(len(M_match)))
        if best_v is None or w > best_v:
            best_v, robust_j = w, j
    planners = {
        "CURRENT_ADAPTIVE": (sum(mean_true(s) for s in cur_segs) / len(cur_segs))
        if cur_segs else 0.0,
        "SIMPLE_PUBLIC_PROXY": mean_true(naive),
        "PUBLIC_SET_COVER_ROBUST": (sum(rr_over(cfgs[robust_j]["seg"], v["trajs"])
                                        for v in variants) / len(variants))
        if robust_j is not None else 0.0,
        "PUBLIC_BELIEF_EXPECTED": belief_choice_true_score(M_match, variants, cfgs, rr_over),
        "FULL_STATE_CEILING": max((sum(M[i][j] for i in range(n_h)) / n_h
                                   for j in range(n_a)), default=0.0),
    }
    ceiling = planners["FULL_STATE_CEILING"]
    return {"scenario": scenario, "seed": seed, "turn": turn, "side": side.value,
            "shooter": shooter.id, "victim": victim.id,
            "n_hidden": n_h, "n_actions": n_a,
            "n_routes_per_hidden": [v["n_routes"] for v in variants],
            "observation_hash_checked": True,
            "observation_hash_identical": True,
            "action_set_identical": True,
            "action_signature_size": len(sig_ref),
            "hidden_plans": [v["plan"] for v in variants],
            "victim_positions": [v["victim_pos"] for v in variants],
            "true_risk": true_risk, "match_risk": match_risk, "naive_risk": naive_risk,
            "match_diagnostics": match_diag,
            "material_true": bool(true_risk["R_shared"] >= TH_SHARED and true_risk["crossover"]),
            "material_match": bool(match_risk["R_shared"] >= TH_SHARED and match_risk["crossover"]),
            "material_naive": bool(naive_risk["R_shared"] >= TH_SHARED and naive_risk["crossover"]),
            "planners": planners, "current_meta": cur_meta,
            "payoff_matrix": M, "payoff_matrix_matched": M_match,
            "public_recovery": (planners["PUBLIC_SET_COVER_ROBUST"] / ceiling
                                if ceiling > 1e-9 else None)}


def belief_choice_true_score(M_match, variants, cfgs, rr_over):
    """PUBLIC_BELIEF_EXPECTED: choose the action maximising the mean payoff over
    the MATCHED public set, then report that action's mean payoff over the TRUE
    hidden set — the same convention as the robust planner, so the two are
    comparable and neither can exceed the full-state ceiling."""
    n_a = len(cfgs)
    best_j, best_v = None, None
    for j in range(n_a):
        v = sum(M_match[i][j] for i in range(len(M_match))) / max(1, len(M_match))
        if best_v is None or v > best_v:
            best_v, best_j = v, j
    if best_j is None:
        return 0.0
    return sum(rr_over(cfgs[best_j]["seg"], var["trajs"]) for var in variants) / len(variants)


def max_mean_under_match(M_match, variants, cfgs, rr_over):
    """Robust public choice: maximise the worst-case payoff over the MATCHED set,
    then report that action's mean payoff over the TRUE set."""
    n_a = len(cfgs)
    best_j, best_v = None, None
    for j in range(n_a):
        v = min(M_match[i][j] for i in range(len(M_match)))
        if best_v is None or v > best_v:
            best_v, best_j = v, j
    if best_j is None:
        return 0.0
    return sum(rr_over(cfgs[best_j]["seg"], var["trajs"]) for var in variants) / len(variants)


def scan_information_sets(log=print, per_scenario=8):
    from iron_bottom_sound.models import GameOptions
    picked = {}
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
                    rows.append((seed, st.turn, snap, e_snap, se))
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
            if len(rows) >= per_scenario * 4:
                break
        rows.sort(key=lambda r: (r[0], r[1]))
        picked[scenario] = rows[:per_scenario]
        log(f"  {scenario}: information sets={len(picked[scenario])} (pool {len(rows)})")
    return picked


def main() -> int:
    t0 = time.time()
    out = {"K_hidden": K_HIDDEN, "thresholds": {"shared": TH_SHARED,
                                                "public_recovery": TH_PUBLIC_RECOVERY},
           "sets": []}
    picked = scan_information_sets()
    rej = Counter()
    for scenario in SCENARIOS:
        for seed, turn, stT, engT, se in picked[scenario]:
            rec = one_information_set(scenario, seed, turn, stT, engT, se)
            if "_rejected" in rec:
                rej[rec["_rejected"]] += 1
                continue
            out["sets"].append(rec)
            print(f"  {scenario} s{seed} t{turn}: hidden={rec['n_hidden']} "
                  f"actions={rec['n_actions']} Rsh_true={rec['true_risk']['R_shared']:.3f} "
                  f"Rsh_match={rec['match_risk']['R_shared']:.3f} "
                  f"mat={rec['material_true']}/{rec['material_match']} "
                  f"recovery={rec['public_recovery']}", flush=True)
            (OUT / "m23_bard_partial.json").write_text(json.dumps(
                {"n_sets": len(out["sets"]), "rejections": dict(rej)}, indent=1))
    out["rejections"] = dict(rej)
    out["summary"] = summarize(out["sets"])
    out["wall_seconds"] = round(time.time() - t0, 1)
    (OUT / "m23_bard.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out["summary"], indent=1, default=str))
    return 0


def summarize(sets):
    if not sets:
        return {"n_sets": 0}
    per = {}
    for scen in SCENARIOS:
        rows = [r for r in sets if r["scenario"] == scen]
        if not rows:
            continue
        per[scen] = {
            "n": len(rows),
            "material_true_rate": sum(r["material_true"] for r in rows) / len(rows),
            "material_match_rate": sum(r["material_match"] for r in rows) / len(rows),
            "material_naive_rate": sum(r["material_naive"] for r in rows) / len(rows),
            "median_R_shared_true": _median([r["true_risk"]["R_shared"] for r in rows]),
            "median_R_shared_match": _median([r["match_risk"]["R_shared"] for r in rows]),
            "median_R_bayes_true": _median([r["true_risk"]["R_bayes"] for r in rows]),
            "mean_planner": {k: sum(r["planners"][k] for r in rows) / len(rows)
                             for k in rows[0]["planners"]},
        }
    ok = [s for s, v in per.items() if v["material_match_rate"] >= 0.20]
    return {"n_sets": len(sets),
            "material_true_rate": sum(r["material_true"] for r in sets) / len(sets),
            "material_match_rate": sum(r["material_match"] for r in sets) / len(sets),
            "material_naive_rate": sum(r["material_naive"] for r in sets) / len(sets),
            "median_R_shared_true": _median([r["true_risk"]["R_shared"] for r in sets]),
            "median_R_shared_match": _median([r["match_risk"]["R_shared"] for r in sets]),
            "scenarios_with_material_match_ge_20pct": ok,
            "per_scenario": per}


if __name__ == "__main__":
    raise SystemExit(main())
