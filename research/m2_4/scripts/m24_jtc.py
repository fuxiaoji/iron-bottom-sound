"""M2.4 — JTC interaction-aware last-chance gate.

Gate I (interaction existence) then, only if PRESENT, Gate II (coordination
effect at equal budget). Every verdict number is engine-exact; the cheap
surrogate only guides search.

    PYTHONPATH=backend/src:research/m2_4/scripts:research/m2_3/scripts:research/m2_2r/scripts:research/m2_2/scripts:research/m2_1/scripts \
        .venv/bin/python research/m2_4/scripts/m24_jtc.py [gate1|gate2|all]
"""

from __future__ import annotations

import json
import random
import sys
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
for extra in ("m2_3", "m2_2r", "m2_2"):
    sys.path.insert(0, str(HERE.parents[1] / extra / "scripts"))

from b1e import OTHER, _median, play_movement, team_metric  # noqa: E402
from m23_jtc import (INTENTS, intent_focal, plan_pools,  # noqa: E402
                     raking_rule_plan, scan_states)
from m22_b0 import plan_cost  # noqa: E402
from m22_core import fire_search, materialize_batch  # noqa: E402
from iron_bottom_sound.engine import IronBottomEngine  # noqa: E402
from iron_bottom_sound.models import (GameOptions, HexCoord, MovementOrder,  # noqa: E402
                                      OrderBatch, Phase, Side)
from iron_bottom_sound.tactical import PROFILES, TacticalCommander  # noqa: E402
from mg.micro import scripted_plans  # noqa: E402

OUT = HERE.parent / "metrics"
OUT.mkdir(exist_ok=True, parents=True)
K_PLANS = 6
EXACT_BUDGET = 24
FLOOR_PHI = 0.05
FLOOR_GAIN = 0.05
BOOTSTRAP_N = 10000
RNG_SEED = 20260921


# --------------------------------------------------------------------------
# exact evaluation
# --------------------------------------------------------------------------


def u_exact(st, eng, side, plans, enemy_plans, se):
    """One engine-exact joint evaluation: play the joint, then
    U = FIRE_SEARCH own EH - enemy EH, with the gunnery batch validated."""
    st2, e2, err = play_movement(st, side, plans, enemy_plans, se)
    if st2 is None:
        return None, err
    own = fire_search(e2, st2, side, OTHER[side])
    ene = fire_search(e2, st2, OTHER[side], side)
    _, ok_o, err_o = materialize_batch(e2, st2, side, own)
    _, ok_e, err_e = materialize_batch(e2, st2, OTHER[side], ene)
    return {"U": own["eh"] - ene["eh"], "own_eh": own["eh"], "enemy_eh": ene["eh"],
            "batch_valid": bool(ok_o and ok_e), "err": (err_o + err_e)[:2]}, None


def state_context(st, eng, side, plans, enemy_plans, se):
    """Collision count during resolution, concentration, aspect/range/visibility
    summary at the post-movement instant."""
    st2, e2, err = play_movement(st, side, plans, enemy_plans, se)
    if st2 is None:
        return {"error": err}
    events = [e for e in st2.events if e.type in ("collision", "ramming",
                                                  "grounding", "movement_blocked")]
    opp = OTHER[side]
    own = [s for s in st2.ships.values() if s.side == side and not s.sunk and s.position]
    ene = [s for s in st2.ships.values() if s.side == opp and not s.sunk and s.position]
    pairs = 0
    vis = 0
    aspects = Counter()
    ranges = []
    for a in own:
        for b in ene:
            if e2._can_see(st2, a, b):
                vis += 1
                if any(not m.destroyed and e2._mount_can_bear(a, b, m.arcs)
                       for m in a.gun_mounts):
                    pairs += 1
                    aspects[e2._target_aspect(a, b)] += 1
                    ranges.append(a.position.distance(b.position))
    conc = Counter()
    for a in own:
        tgts = [b.id for b in ene
                if any(not m.destroyed and e2._mount_can_bear(a, b, m.arcs)
                       for m in a.gun_mounts)]
        if tgts:
            conc[len(tgts)] += 1
    return {"collision_events": len(events), "legal_pairs": pairs,
            "visible_pairs": vis, "aspects": dict(aspects),
            "range_mean": (sum(ranges) / len(ranges)) if ranges else None,
            "split_fire_ships": sum(v for k, v in conc.items() if k > 1),
            "concentration_max": max(conc.values()) if conc else 0}


# --------------------------------------------------------------------------
# candidate set (identical object for every method)
# --------------------------------------------------------------------------


def candidates(eng, st, side, policy_map):
    ships, pools = plan_pools(eng, st, side, policy_map)
    return ships, {s: pools[s][:K_PLANS] for s in pools}


def additive_rank(st, eng, side, policy_map, enemy_plans, ships, pools):
    """Cheap-surrogate contribution per (ship, plan) — guidance only."""
    from b1e import _decomposed_scores
    contrib = _decomposed_scores(eng, st, side, policy_map, enemy_plans, pools, ships)
    return contrib


# --------------------------------------------------------------------------
# methods
# --------------------------------------------------------------------------


def joint_of(assign, ships, policy_map):
    return {s: assign.get(s, policy_map.get(s, "0")) for s in ships}


def run_methods(st, eng, side, enemy_plans, se, policy_map, ships, pools, contrib, rng):
    """All five methods on one state; returns U_exact records and eval counts."""
    evals = {"n": 0}
    cache = {}

    def exact(assign):
        key = tuple(sorted(assign.items()))
        if key in cache:
            return cache[key]
        evals["n"] += 1
        r, err = u_exact(st, eng, side, assign, enemy_plans, se)
        cache[key] = r
        if r is None:
            raise RuntimeError(f"exact eval failed: {err}")
        return r

    out = {}
    a0 = dict(policy_map)
    out["CURRENT_PRODUCTION"] = {"assign": a0, "U": exact(a0)["U"], "evals": 1}

    # additive greedy
    greedy = {}
    for s in ships:
        row = contrib.get(s) or {}
        greedy[s] = max(row.items(), key=lambda kv: (kv[1], kv[0]))[0] if row \
            else policy_map.get(s, "0")
    n0 = evals["n"]
    g = exact(greedy)
    out["PER_SHIP_GREEDY_ADDITIVE"] = {"assign": greedy, "U": g["U"],
                                       "evals": evals["n"] - n0}

    # sequential team best response, one sweep, top-2 per ship
    n0 = evals["n"]
    cur = dict(greedy)
    curU = g["U"]
    for s in ships:
        row = contrib.get(s) or {}
        alternatives = [p for p, _ in sorted(row.items(), key=lambda kv: -kv[1])[:2]]
        for p in alternatives:
            if p == cur.get(s):
                continue
            trial = dict(cur)
            trial[s] = p
            if evals["n"] - n0 >= EXACT_BUDGET:
                break
            r = exact(trial)
            if r["U"] > curU:
                cur, curU = trial, r["U"]
    out["SEQUENTIAL_TEAM_BEST_RESPONSE"] = {"assign": cur, "U": curU,
                                            "evals": evals["n"] - n0}

    # random matched budget
    n0 = evals["n"]
    best, bestU = None, None
    while evals["n"] - n0 < EXACT_BUDGET:
        assign = {s: rng.choice(pools[s]) for s in ships}
        r = exact(assign)
        if bestU is None or r["U"] > bestU:
            best, bestU = assign, r["U"]
    out["RANDOM_MATCHED_BUDGET"] = {"assign": best, "U": bestU,
                                    "evals": evals["n"] - n0}

    # interaction-aware beam: measure q_i probes, pairwise probes, fit, choose
    n0 = evals["n"]
    probes_single = []
    for s in ships:
        row = contrib.get(s) or {}
        for p, _ in sorted(row.items(), key=lambda kv: -kv[1])[:2]:
            if evals["n"] - n0 >= 12:
                break
            trial = dict(a0)
            trial[s] = p
            r = exact(trial)
            probes_single.append((s, p, r["U"] - exact(a0)["U"]))
    q = defaultdict(dict)
    for s, p, dq in probes_single:
        q[s][p] = dq
    pair_probes = []
    order = sorted(ships, key=lambda s: -max(q.get(s, {}).values(), default=0.0))
    for i, j in list(combinations(order, 2)):
        if evals["n"] - n0 >= 12 + 10:
            break
        ai = max(q.get(i, {"": 0.0}), key=q[i].get) if q.get(i) else None
        aj = max(q.get(j, {"": 0.0}), key=q[j].get) if q.get(j) else None
        if ai is None or aj is None:
            continue
        trial = dict(a0)
        trial[i], trial[j] = ai, aj
        u0 = exact(a0)["U"]
        u_ij = exact(trial)["U"]
        u_i = u0 + q[i][ai]      # U(a_i, a_-i^0)
        u_j = u0 + q[j][aj]      # U(a_j, a_-j^0)
        phi = u_ij - u_i - u_j + u0
        pair_probes.append({"i": i, "j": j, "phi": phi, "a_i": ai, "a_j": aj})
    phi_map = {(p["i"], p["j"]): p["phi"] for p in pair_probes}
    # model-guided final selection over the additive beam's top survivors
    beam = [{}]
    for s in ships:
        nxt = []
        for assign in beam:
            for p in pools[s]:
                a2 = dict(assign)
                a2[s] = p
                nxt.append(a2)
        nxt.sort(key=lambda a: -sum(contrib.get(x, {}).get(
            a.get(x, policy_map.get(x, "0")), 0.0) for x in ships))
        beam = nxt[:64]
    best_assign, best_score = None, None
    for assign in beam:
        score = sum(q.get(s, {}).get(assign[s], 0.0) for s in ships)
        for pr in pair_probes:
            if assign.get(pr["i"]) == pr["a_i"] and assign.get(pr["j"]) == pr["a_j"]:
                score += pr["phi"]
        if best_score is None or score > best_score:
            best_assign, best_score = assign, score
    ib = exact(best_assign)
    out["INTERACTION_AWARE_BEAM"] = {
        "assign": best_assign, "U": ib["U"], "evals": evals["n"] - n0,
        "n_q_probes": len(probes_single), "n_pair_probes": len(pair_probes),
        "pair_probes": pair_probes}
    out["_total_exact_evals"] = evals["n"]
    return out


# --------------------------------------------------------------------------
# Gate I — interaction existence
# --------------------------------------------------------------------------


def load_main_states():
    p = HERE.parents[1] / "m2_3" / "metrics" / "m23_jtc_census.json"
    d = json.loads(p.read_text())
    keys, seen = [], set()
    for r in d["states"]:
        k = (r["scenario"], r["seed"], r["turn"], r["side"], r["intent"])
        if k not in seen:
            seen.add(k)
            keys.append(r)
    keys.sort(key=lambda r: (r["scenario"], r["seed"], r["turn"], r["side"], r["intent"]))
    return keys


def rebuild_state(scenario, seed, turn, side):
    """Re-derive the state snapshot for a frozen locator (deterministic replay)."""
    eng = IronBottomEngine()
    st = eng.reset(scenario, seed, GameOptions(mode="llm"))
    se = {s: TacticalCommander(profile=PROFILES["balanced"]) for s in Side}
    g = 0
    while st.phase != Phase.COMPLETE and g < 400:
        g += 1
        if st.phase == Phase.MOVEMENT_PLANNING and st.turn == turn:
            snap = st.model_copy(deep=True)
            e_snap = IronBottomEngine()
            e_snap.games[snap.game_id] = snap
            return snap, e_snap, se
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
    return None, None, se


def gate1(log=print):
    t0 = time.time()
    keys = load_main_states()[:10]
    out = {"pilot_locators": [[k["scenario"], k["seed"], k["turn"], k["side"], k["intent"]]
                              for k in keys],
           "floors": {"phi": FLOOR_PHI, "rank_agreement": 0.95},
           "pilots": []}
    all_phi = []
    agreements = []
    model_agreements = []
    for k in keys:
        st, eng, se = rebuild_state(k["scenario"], k["seed"], k["turn"], k["side"])
        if st is None:
            continue
        side = Side(k["side"])
        policy_map = scripted_plans(eng, st, side)
        enemy_plans = scripted_plans(eng, st, OTHER[side])
        ships, pools = candidates(eng, st, side, policy_map)
        contrib = additive_rank(st, eng, side, policy_map, enemy_plans, ships, pools)
        rng = random.Random(RNG_SEED + k["seed"] * 1000 + k["turn"])
        a0U = u_exact(st, eng, side, dict(policy_map), enemy_plans, se)[0]["U"]
        # per-ship additive-best
        best = {}
        for s in ships:
            row = contrib.get(s) or {}
            best[s] = max(row.items(), key=lambda kv: (kv[1], kv[0]))[0] if row \
                else policy_map.get(s, "0")
        q = {}
        n_failed = 0
        for s in ships:
            trial = dict(policy_map)
            trial[s] = best[s]
            r, err = u_exact(st, eng, side, trial, enemy_plans, se)
            if r is None:
                n_failed += 1
                continue
            q[s] = r["U"] - a0U
        rows = []
        for i, j in combinations(ships, 2):
            if i not in q or j not in q:
                continue
            trial = dict(policy_map)
            trial[i], trial[j] = best[i], best[j]
            rr, _e = u_exact(st, eng, side, trial, enemy_plans, se)
            if rr is None:
                n_failed += 1
                continue
            u_ij = rr["U"]
            phi = u_ij - (a0U + q[i]) - (a0U + q[j]) + a0U
            si, sj = st.ships[i], st.ships[j]
            shared = bool(set(contrib) and False)
            rows.append({"i": i, "j": j, "phi": phi,
                         "distance": si.position.distance(sj.position),
                         "phi_abs": abs(phi)})
            all_phi.append(abs(phi))
        # rank agreement between the additive surrogate and exact U on a sample
        sample = []
        for _ in range(24):
            assign = {s: rng.choice(pools[s]) for s in ships}
            sample.append(assign)
        add_scores = [sum(contrib.get(s, {}).get(a[s], 0.0) for s in ships) for a in sample]
        ex_scores = []
        model_scores = []
        for a in sample:
            rr, _e = u_exact(st, eng, side, a, enemy_plans, se)
            if rr is None:
                continue
            ex_scores.append(rr["U"])
            # ADDITIVE_EXACT_MODEL: sum of the exactly measured single-ship deltas
            model_scores.append(sum(q.get(s, 0.0) for s in ships if a[s] == best[s]))
        agree = spearman(add_scores[:len(ex_scores)], ex_scores) if len(ex_scores) > 2 else None
        agree_model = spearman(model_scores, ex_scores) if len(ex_scores) > 2 else None
        if agree is not None:
            agreements.append(agree)
        model_agreements.append(agree_model)
        out["pilots"].append({"locator": k, "n_ships": len(ships),
                              "n_pairs": len(rows), "phi_rows": rows,
                              "surrogate_vs_exact_agreement": agree,
                              "exact_additive_model_vs_exact_agreement": agree_model,
                              "n_failed_evals": n_failed,
                              "q_values": q, "a0_U": a0U})
        log(f"  pilot {k['scenario']} s{k['seed']} t{k['turn']} {k['side']} "
            f"{k['intent']}: pairs={len(rows)} "
            f"median|phi|={_median([r['phi_abs'] for r in rows])} "
            f"agree(surrogate)={agree} agree(exact-additive)={agree_model}")
    out["summary"] = phi_summary(all_phi, agreements, model_agreements)
    out["wall_seconds"] = round(time.time() - t0, 1)
    (OUT / "m24_gate1_interaction.json").write_text(json.dumps(out, indent=1, default=str))
    log(json.dumps(out["summary"], indent=1))
    return out


def phi_summary(all_phi, agreements, model_agreements):
    if not all_phi:
        return {"n_pairs": 0}
    s = sorted(all_phi)
    n = len(s)
    nz = sum(1 for x in s if x >= FLOOR_PHI)
    median_agree = _median(agreements)
    median_model = _median([x for x in model_agreements if x is not None])
    # Frozen rule (PRE_REGISTRATION_M24 §3) keys on the SURROGATE agreement.
    absent_frozen = (nz / n < 0.10) and (median_agree is not None and median_agree >= 0.95)
    # The interaction-specific reading uses the EXACT additive model, i.e. the sum
    # of exactly measured single-ship deltas: high agreement there means no
    # interaction is needed to rank joints, whatever the cheap surrogate does.
    absent_interaction = (nz / n < 0.10) and (median_model is not None
                                              and median_model >= 0.95)
    return {"n_pairs": n, "median_abs_phi": _median(s),
            "p90_abs_phi": s[int(0.9 * (n - 1))], "max_abs_phi": s[-1],
            "practical_nonzero_fraction": nz / n,
            "median_surrogate_vs_exact_agreement": median_agree,
            "median_exact_additive_model_vs_exact_agreement": median_model,
            "frozen_rule_verdict": "ABSENT" if absent_frozen else "PRESENT",
            "interaction_specific_reading": "ABSENT" if absent_interaction else "PRESENT",
            "INTERACTION_STRUCTURE": "ABSENT" if absent_frozen else "PRESENT",
            "note": ("the frozen gate keys on the cheap surrogate's agreement, which "
                     "conflates guide quality with interaction; both readings are "
                     "reported (see 03_INTERACTION_EXISTENCE.md)")}


def spearman(x, y):
    def rank(v):
        idx = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        for pos, i in enumerate(idx):
            r[i] = pos
        return r
    rx, ry = rank(x), rank(y)
    n = len(x)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else 0.0


# --------------------------------------------------------------------------
# Gate II — coordination effect
# --------------------------------------------------------------------------


def supplemental_states(log=print, per_scenario=10):
    picked = {}
    for scenario in ("IBS-S-01", "IBS-S-03", "IBS-S-EM-01"):
        rows = []
        for seed in range(1, 9):
            eng = IronBottomEngine()
            st = eng.reset(scenario, seed, GameOptions(mode="llm"))
            se = {s: TacticalCommander(profile=PROFILES["balanced"]) for s in Side}
            g = 0
            while st.phase != Phase.COMPLETE and g < 400:
                g += 1
                if st.phase == Phase.MOVEMENT_PLANNING and st.turn >= 2:
                    for side in (Side.AXIS, Side.ALLIES):
                        pm = scripted_plans(eng, st, side)
                        _, pools = plan_pools(eng, st, side, pm)
                        multi = sum(1 for s, ps in pools.items()
                                    if len(set(ps)) >= 2)
                        if multi < 2:
                            continue
                        ep = scripted_plans(eng, st, OTHER[side])
                        ctx = state_context(st, eng, side, pm, ep, se)
                        if ctx.get("legal_pairs", 0) >= 1:
                            snap = st.model_copy(deep=True)
                            e_snap = IronBottomEngine()
                            e_snap.games[snap.game_id] = snap
                            rows.append({"seed": seed, "turn": st.turn, "side": side,
                                         "st": snap, "eng": e_snap, "se": se,
                                         "n_multi": multi})
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
        rows.sort(key=lambda r: (r["seed"], r["turn"], r["side"].value))
        picked[scenario] = rows[:per_scenario]
        log(f"  supplemental {scenario}: {len(picked[scenario])}/{len(rows)}")
    return picked


def gate2(log=print):
    t0 = time.time()
    out = {"budget": EXACT_BUDGET, "floors": {"gain": FLOOR_GAIN},
           "main": [], "supplemental": [], "counts": {}}
    # main set: the frozen 35 common opportunity states
    keys = load_main_states()
    main_keys = []
    seen = set()
    for r in keys:
        k = (r["scenario"], r["seed"], r["turn"], r["side"])
        if k in seen:
            continue
        seen.add(k)
        main_keys.append(r)
    log(f"  main state-sides: {len(main_keys)}")
    for i, k in enumerate(main_keys):
        st, eng, se = rebuild_state(k["scenario"], k["seed"], k["turn"], k["side"])
        if st is None:
            continue
        rec = evaluate_state(k["scenario"], k["seed"], k["turn"], k["side"], st, eng, se,
                             intent=k["intent"], panel="main")
        if rec:
            out["main"].append(rec)
        if i % 5 == 0:
            (OUT / "m24_gate2_partial.json").write_text(json.dumps(
                {"n_main": len(out["main"]), "n_sup": len(out["supplemental"])}, indent=1))
            log(f"    main {i+1}/{len(main_keys)}")
    sup = supplemental_states(log=log)
    for scenario, rows in sup.items():
        for r in rows:
            rec = evaluate_state(scenario, r["seed"], r["turn"], r["side"].value,
                                 r["st"], r["eng"], r["se"], intent="SUPPLEMENTAL",
                                 panel="supplemental")
            if rec:
                out["supplemental"].append(rec)
        log(f"  supplemental done {scenario}: {len(out['supplemental'])} total")
    out["verdict"] = gate2_verdict(out)
    out["wall_seconds"] = round(time.time() - t0, 1)
    (OUT / "m24_gate2_coordination.json").write_text(json.dumps(out, indent=1, default=str))
    log(json.dumps(out["verdict"], indent=1))
    return out


def evaluate_state(scenario, seed, turn, side_value, st, eng, se, intent, panel):
    side = Side(side_value)
    policy_map = scripted_plans(eng, st, side)
    enemy_plans = scripted_plans(eng, st, OTHER[side])
    ships, pools = candidates(eng, st, side, policy_map)
    if len(ships) < 2:
        return None
    contrib = additive_rank(st, eng, side, policy_map, enemy_plans, ships, pools)
    rng = random.Random(RNG_SEED + seed * 1000 + turn * 10 + list(Side).index(side))
    try:
        m = run_methods(st, eng, side, enemy_plans, se, policy_map, ships, pools,
                        contrib, rng)
    except RuntimeError:
        return None
    ctx = state_context(st, eng, side, m["CURRENT_PRODUCTION"]["assign"],
                        enemy_plans, se)
    dg = m["INTERACTION_AWARE_BEAM"]["U"] - m["PER_SHIP_GREEDY_ADDITIVE"]["U"]
    ds = m["INTERACTION_AWARE_BEAM"]["U"] - m["SEQUENTIAL_TEAM_BEST_RESPONSE"]["U"]
    dr = m["INTERACTION_AWARE_BEAM"]["U"] - m["RANDOM_MATCHED_BUDGET"]["U"]
    return {"panel": panel, "scenario": scenario, "seed": seed, "turn": turn,
            "side": side_value, "intent": intent, "n_ships": len(ships),
            "U": {k: v["U"] for k, v in m.items() if not k.startswith("_")},
            "evals": {k: v["evals"] for k, v in m.items() if not k.startswith("_")},
            "total_evals": m["_total_exact_evals"],
            "n_q_probes": m["INTERACTION_AWARE_BEAM"]["n_q_probes"],
            "n_pair_probes": m["INTERACTION_AWARE_BEAM"]["n_pair_probes"],
            "pair_probes": m["INTERACTION_AWARE_BEAM"]["pair_probes"],
            "delta_joint_greedy": dg, "delta_joint_seq": ds,
            "delta_joint_random": dr, "context": ctx}


def bootstrap_ci(vals, n=BOOTSTRAP_N, seed=RNG_SEED):
    if not vals:
        return None
    rng = random.Random(seed)
    meds = []
    k = len(vals)
    for _ in range(n):
        meds.append(_median([vals[rng.randrange(k)] for _ in range(k)]))
    meds.sort()
    return [meds[int(0.025 * n)], meds[int(0.975 * n)]]


def gate2_verdict(out):
    def block(rows, name):
        dg = [r["delta_joint_greedy"] for r in rows]
        if not dg:
            return None
        per_scen = {}
        for scen in ("IBS-S-01", "IBS-S-03", "IBS-S-EM-01"):
            rs = [r["delta_joint_greedy"] for r in rows if r["scenario"] == scen]
            if rs:
                per_scen[scen] = {"n": len(rs), "median": _median(rs),
                                  "mean": sum(rs) / len(rs)}
        wins = sum(1 for x in dg if x > 1e-9)
        ties = sum(1 for x in dg if abs(x) <= 1e-9)
        losses = len(dg) - wins - ties
        srt = sorted(rows, key=lambda r: -abs(r["delta_joint_greedy"]))[2:]
        return {"panel": name, "n": len(rows),
                "delta_greedy": {"mean": sum(dg) / len(dg), "median": _median(dg),
                                 "win": wins, "tie": ties, "loss": losses,
                                 "win_rate": wins / len(dg),
                                 "bootstrap_ci": bootstrap_ci(dg)},
                "delta_seq": {"mean": sum(r["delta_joint_seq"] for r in rows) / len(rows),
                              "median": _median([r["delta_joint_seq"] for r in rows]),
                              "bootstrap_ci": bootstrap_ci([r["delta_joint_seq"] for r in rows])},
                "delta_random": {"median": _median([r["delta_joint_random"] for r in rows])},
                "per_scenario": per_scen,
                "scenarios_median_positive": sum(1 for v in per_scen.values()
                                                 if v["median"] > 0),
                "robust_median_after_dropping_top2": _median(
                    [r["delta_joint_greedy"] for r in srt]),
                "exact_evals_mean": sum(r["total_evals"] for r in rows) / len(rows)}
    blocks = {k: v for k, v in (("main", block(out["main"], "main")),
                                ("supplemental", block(out["supplemental"], "supplemental")))
              if v}
    main = blocks.get("main")
    cond = {}
    if main:
        d = main["delta_greedy"]
        cond = {
            "1_median_positive_in_ge2_scenarios": main["scenarios_median_positive"] >= 2,
            "2_pooled_win_rate_ge_060": d["win_rate"] >= 0.60,
            "3_pooled_median_ge_floor": (d["median"] or 0) >= FLOOR_GAIN,
            "4_not_worse_than_sequential": (main["delta_seq"]["bootstrap_ci"] or [0])[0] > -FLOOR_GAIN,
            "5_random_clearly_worse": (main["delta_random"]["median"] or 0) >= FLOOR_GAIN,
            "6_not_driven_by_extremes": (main["robust_median_after_dropping_top2"] or 0) >= FLOOR_GAIN,
        }
    passed = bool(cond) and all(cond.values())
    return {"panels": blocks, "conditions": cond,
            "JTC_INTERACTION_GATE": "PASS" if passed else "FAIL"}


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("gate1", "all"):
        g1 = gate1()
        if g1["summary"].get("INTERACTION_STRUCTURE") == "ABSENT":
            (OUT / "m24_final.json").write_text(json.dumps(
                {"INTERACTION_STRUCTURE": "ABSENT",
                 "JTC_INTERACTION_GATE": "NOT_RUN",
                 "JTC_FINAL_STATUS": "PERMANENTLY_KILL",
                 "BARD_FINAL_STATUS": "ARCHIVED",
                 "IBS_NEXT_ROLE": "APPLICATION_BENCHMARK_ONLY"}, indent=1))
            print("INTERACTION_STRUCTURE = ABSENT -> PERMANENTLY_KILL")
            return 0
        print("INTERACTION_STRUCTURE = PRESENT -> Gate II")
    if which in ("gate2", "all"):
        g2 = gate2()
        gate = g2["verdict"]["JTC_INTERACTION_GATE"]
        final = {"INTERACTION_STRUCTURE": "PRESENT", "JTC_INTERACTION_GATE": gate,
                 "JTC_FINAL_STATUS": ("SURVIVES_FOR_NOVELTY_REVIEW" if gate == "PASS"
                                      else "PERMANENTLY_KILL"),
                 "BARD_FINAL_STATUS": "ARCHIVED",
                 "IBS_NEXT_ROLE": ("METHOD_DISCOVERY_CONTINUES" if gate == "PASS"
                                   else "APPLICATION_BENCHMARK_ONLY")}
        (OUT / "m24_final.json").write_text(json.dumps(final, indent=1))
        print(json.dumps(final, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
