"""MG2-R and MG5-R: cross-T and local-force with LEGAL fire allocation."""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mg.micro import IronBottomEngine, advance_to_gunnery, build_batch, reach, scripted_plans
from mg.mg_cases import bearing_to, measure_side, plan_for_pose, plan_tables_all, run_to_gunnery, ships_of
from mg.legal_fire2 import materialize_batch, team_legal_fire_v2 as team_legal_fire
from iron_bottom_sound.models import OrderBatch, Phase, Side

OUT = Path(__file__).resolve().parents[2] / "metrics"


def legal_measure(eng, st, side, opp):
    own = team_legal_fire(eng, st, side, opp)
    ene = team_legal_fire(eng, st, opp, side)
    batch_json, ok, errs = materialize_batch(eng, st, side, own)
    _bj2, ok2, errs2 = materialize_batch(eng, st, opp, ene)
    own["batch_valid"] = ok
    own["batch_errors"] = errs
    ene["batch_valid"] = ok2
    ene["batch_errors"] = errs2
    return own, ene


def mg2r():
    scenario, seed = "IBS-S-01", 1
    eng, st, se = reach(scenario, seed, Phase.MOVEMENT_PLANNING, 2)
    assert st is not None
    enemies_ax = ships_of(st, Side.AXIS)
    from collections import Counter
    e_head = Counter(e.heading for e in enemies_ax).most_common(1)[0][0]
    cross, parallel = {}, {}
    for s in ships_of(st, Side.ALLIES):
        plans = plan_tables_all(eng, st).get(s.id, set())
        near = min(enemies_ax, key=lambda e: s.position.distance(e.position))
        b = bearing_to(s.position, near.position)
        cross[s.id] = plan_for_pose(eng, st, s, plans, ((b - 1 + 1) % 6) + 1, 0)
        parallel[s.id] = plan_for_pose(eng, st, s, plans, ((e_head - 1) % 6) + 1, 0)
    out = {"scenario": scenario, "seed": seed, "enemy_line_heading": e_head}
    for name, pm in (("CROSS_T", cross), ("PARALLEL", parallel)):
        st2 = st.model_copy(deep=True)
        e2 = IronBottomEngine(); e2.games[st2.game_id] = st2
        b2, err = run_to_gunnery(e2, st2, se, Side.ALLIES, pm)
        if b2 is None:
            out[name] = {"error": err}; continue
        own, ene = legal_measure(e2, st2, Side.ALLIES, Side.AXIS)
        n_targets = len([e for e in ships_of(st2, Side.AXIS)])
        out[name] = {
            "own_team_gf": own["team_gf"], "own_team_eh": own["team_eh"],
            "own_active_shooters": own["active_shooters"],
            "own_longitudinal_fraction": own["longitudinal"] / max(1, own["active_shooters"]),
            "enemy_team_gf": ene["team_gf"], "enemy_team_eh": ene["team_eh"],
            "net_eh": own["team_eh"] - ene["team_eh"],
            "own_batch_valid": own["batch_valid"], "own_batch_errors": own["batch_errors"],
            "selected_targets": {r["ship"]: r["target"] for r in own["detail"] if r["target"]},
            "aspects": {r["ship"]: r.get("aspect") for r in own["detail"] if r.get("target")},
        }
    c, p = out.get("CROSS_T", {}), out.get("PARALLEL", {})
    if "error" in c or "error" in p:
        out["gate"] = {"verdict": "FAIL", "reason": "arm build failed", "detail": [c, p]}
    else:
        c1 = c["own_team_gf"] > c["enemy_team_gf"]
        c2 = c["net_eh"] > 0
        c3 = c["own_longitudinal_fraction"] >= 0.5
        c4 = c["net_eh"] >= 1.25 * max(p["net_eh"], 1e-9)
        out["gate"] = {"own_gf_gt_enemy": c1, "net_eh_positive": c2,
                       "longitudinal_frac_ge_50pct": c3, "ratio_1_25x": c4,
                       "dual_win": c1, "batch_valid": c["own_batch_valid"],
                       "verdict": "PASS" if (c1 and c2 and c3 and c4) else "FAIL"}
    return out


def mg5r():
    # state reuse: M2.1-R2's MG5 resolved on IBS-S-01 s1 t3 (isolated IJN-FUBUKI,
    # gap 7).  The EM-01 t3 roster is a tight formation (gap 1), not the case.
    scenario, seed, turn = "IBS-S-01", 1, 3
    eng, st, se = reach(scenario, seed, Phase.MOVEMENT_PLANNING, turn)
    assert st is not None
    enemies = ships_of(st, Side.AXIS)
    own = ships_of(st, Side.ALLIES)
    iso = rest = None
    for e in enemies:
        rest = [x for x in enemies if x.id != e.id]
        if min(e.position.distance(x.position) for x in rest) >= 6:
            iso = e
            break
    assert iso is not None, "no isolated enemy at this state"
    conc, disp = {}, {}
    for i, s in enumerate(own):
        plans = plan_tables_all(eng, st).get(s.id, set())
        conc[s.id] = plan_for_pose(eng, st, s, plans, bearing_to(s.position, iso.position), +1)
        tgt = iso if i % 2 == 0 else rest[i % len(rest)]
        disp[s.id] = plan_for_pose(eng, st, s, plans, bearing_to(s.position, tgt.position), 0)
    out = {"scenario": scenario, "seed": seed, "isolated_enemy": iso.id}
    for name, pm in (("CONCENTRATE", conc), ("DISPERSE", disp)):
        st2 = st.model_copy(deep=True)
        e2 = IronBottomEngine(); e2.games[st2.game_id] = st2
        b2, err = run_to_gunnery(e2, st2, se, Side.ALLIES, pm)
        if b2 is None:
            out[name] = {"error": err}; continue
        o, e = legal_measure(e2, st2, Side.ALLIES, Side.AXIS)
        out[name] = {"own_active_shooters": o["active_shooters"],
                     "own_team_eh": o["team_eh"], "enemy_team_eh": e["team_eh"],
                     "net_legal_eh": o["team_eh"] - e["team_eh"],
                     "own_batch_valid": o["batch_valid"],
                     "target_distribution": {k: round(v, 2) for k, v in o["target_distribution"].items()},
                     "enemy_active_shooters": e["active_shooters"],
                     "fire_graph": {r["ship"]: r["target"] for r in o["detail"] if r["target"]}}
    c, d = out.get("CONCENTRATE", {}), out.get("DISPERSE", {})
    if "error" in c or "error" in d:
        out["gate"] = {"verdict": "FAIL", "reason": "arm build failed"}
    else:
        c1 = c["net_legal_eh"] >= 1.25 * max(d["net_legal_eh"], 1e-9)
        c2 = c["own_active_shooters"] > d["own_active_shooters"]
        out["gate"] = {"margin_ratio": c["net_legal_eh"] / max(1e-9, d["net_legal_eh"]),
                       "ratio_ge_125": c1, "more_active": c2,
                       "verdict": "PASS" if (c1 or c2) else "FAIL"}
    return out


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "ALL"
    res = {}
    for name, fn in (("MG2R", mg2r), ("MG5R", mg5r)):
        if which not in ("ALL", name):
            continue
        print(f"=== {name} ===", flush=True)
        res[name] = fn()
        print(json.dumps(res[name], indent=1, default=str), flush=True)
    (OUT / "mg2r_mg5r.json").write_text(json.dumps(res, indent=1, default=str))
    raise SystemExit(0)
