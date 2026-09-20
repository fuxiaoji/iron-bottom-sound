"""MG1 BROADSIDE — RESEARCH_MICRO_SANITY_CASE (v2, first-MF-straight aware).

Original design used pure-turn plans; the engine enforces first-MF-straight
(no cost-0 turn plans exist in movement_candidates).  v2 design:

  focal ship chosen with the target already near its bow line (rel == 0);
  NARROW arm    : plan "0" (hold; heading, position, distance unchanged);
  BROADSIDE arm : cheapest legal plan whose final relative bearing is +/-1
                  or +/-2 (broadside mounts bear; e.g. "1P1");
  expected hits are normalized to a COMMON reference distance via the
  engine's own modifier table, isolating the heading -> mounts channel.

Gate: broadside >= +25% available main-GF that can bear, or >= +25%
common-distance expected hits.
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
from iron_bottom_sound.models import OrderBatch, Phase, Side  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "metrics"


def rel_bearing(ship_heading: int, bearing: int) -> int:
    return (bearing - ship_heading) % 6


def final_rel(plan: str, ship_heading: int, bearing: int) -> int:
    turns = plan.count("P") - plan.count("S")
    return (bearing - ((ship_heading - 1 + turns) % 6 + 1)) % 6


def focal_expected(eng, st, focal, target, d_ref) -> dict:
    ship, tgt = st.ships[focal], st.ships[target]
    main_gf = sec_gf = 0.0
    exp = 0.0
    n_bear = 0
    for m in ship.gun_mounts:
        if m.destroyed or not eng._mount_can_bear(ship, tgt, m.arcs):
            continue
        fp = float(getattr(m, "firepower", 0) or 0)
        n_bear += 1
        if fp <= 0:
            continue
        d = d_ref if d_ref is not None else ship.position.distance(tgt.position)
        mods = eng._gunnery_modifiers(st, ship, tgt, d, 1, 8.0, 1)
        total = sum(mods.values())
        D66 = [t * 10 + u for t in range(1, 7) for u in range(1, 7)]
        for d66 in D66:                      # uniform 1/36 over D66 outcomes
            adjusted = d66_adjust(d66, total)
            exp += eng.rules.hit_count(int(fp), adjusted) / 36.0
        if m.kind == "primary":
            main_gf += fp
        else:
            sec_gf += fp
    return {"main_gf_bearing": main_gf, "sec_gf_bearing": sec_gf,
            "n_mounts_bearing": n_bear, "expected_hits_at_dref": exp,
            "distance": ship.position.distance(tgt.position)}



def main() -> int:
    eng, st, se = reach("IBS-S-01", 5, Phase.MOVEMENT_PLANNING, 2)
    assert st is not None
    side = Side.AXIS
    filler = scripted_plans(eng, st, side)
    tables = plan_tables(eng, st, side)
    own = [s for s in st.ships.values() if s.side == side and not s.sunk and s.position]
    enemies = [s for s in st.ships.values()
               if s.side != side and not s.sunk and s.position]
    dirs = {1: (1, -1), 2: (1, 0), 3: (0, 1), 4: (-1, 1), 5: (-1, 0), 6: (0, -1)}

    def hyp(a, b):
        return (a * a + b * b) ** 0.5

    def bearing_to(frm_q, frm_r, to_q, to_r):
        dq, dr = to_q - frm_q, to_r - frm_r
        return max(dirs, key=lambda h: (dq * dirs[h][0] + dr * dirs[h][1])
                   / (hyp(dq, dr) + 1e-9))

    # ---- two-pass design: learn each candidate target's post-movement
    # position (opponent plans independently of our batch), then choose
    # broadside/narrow plans against the POST bearing. ----
    focal = None
    for s in sorted(own, key=lambda x: -x.vp):
        near = min(enemies, key=lambda e: s.position.distance(e.position))
        # pass 1: probe run with focal holding; learn near's post position
        st_p = st.model_copy(deep=True)
        e_p = IronBottomEngine(); e_p.games[st_p.game_id] = st_p
        batch = build_batch(eng, st, side, {s.id: "0"}, filler)
        b = OrderBatch.model_validate_json(batch)
        b.side = side; b.phase = Phase.MOVEMENT_PLANNING
        if not e_p.validate_orders(st_p.game_id, b).valid:
            continue
        e_p.submit_orders(st_p.game_id, b)
        if not advance_to_gunnery(st_p, e_p, se):
            continue
        tgt_post = st_p.ships[near.id]
        if not tgt_post.position:
            continue
        post_bearing = bearing_to(st_p.ships[s.id].position.q,
                                  st_p.ships[s.id].position.r,
                                  tgt_post.position.q, tgt_post.position.r)
        plans = sorted(tables[s.id])
        broad_plan = narrow_plan = None
        for plan in plans:
            frel = (post_bearing - ((s.heading - 1 + plan.count("P")
                                     - plan.count("S")) % 6 + 1)) % 6
            if frel in (1, 2, 4, 5) and broad_plan is None and plan != "0":
                broad_plan = plan
            if frel in (0, 3) and narrow_plan is None and plan != "0":
                narrow_plan = plan
        if broad_plan and narrow_plan and broad_plan != narrow_plan:
            focal, target = s.id, near.id
            break
    assert focal, "no focal ship with distinct broadside/narrow plans"
    print(f"focal={focal} target={target} broad={broad_plan} narrow={narrow_plan}")

    def measure(plan: str, eh_distance=None):
        """Apply plan, advance to post-movement/pre-fire, measure geometry.
        EH evaluated at ``eh_distance`` (common reference) when given, else at
        the arm's own post distance."""
        st2 = st.model_copy(deep=True)
        e2 = IronBottomEngine(); e2.games[st2.game_id] = st2
        batch = build_batch(eng, st, side, {focal: plan}, filler)
        b = OrderBatch.model_validate_json(batch)
        b.side = side; b.phase = Phase.MOVEMENT_PLANNING
        res = e2.validate_orders(st2.game_id, b)
        if not res.valid:
            return {"error": str(res.errors[:2])}
        e2.submit_orders(st2.game_id, b)
        if not advance_to_gunnery(st2, e2, se):
            return {"error": "no gunnery"}
        tgt2 = st2.ships[target]
        my = st2.ships[focal]
        post_b = bearing_to(my.position.q, my.position.r,
                            tgt2.position.q, tgt2.position.r)
        rel = (post_b - my.heading) % 6
        gf = exp = 0.0
        n_bear = 0
        d = my.position.distance(tgt2.position)
        d_use = eh_distance if eh_distance is not None else d
        for m in my.gun_mounts:
            if m.destroyed or not e2._mount_can_bear(my, tgt2, m.arcs):
                continue
            fp = float(getattr(m, "firepower", 0) or 0)
            n_bear += 1
            if fp <= 0:
                continue
            mods = e2._gunnery_modifiers(st2, my, tgt2, d_use, 1, 8.0, 1)
            total = sum(mods.values())
            for t10 in range(1, 7):
                for t01 in range(1, 7):
                    d66 = t10 * 10 + t01
                    adjusted = d66_adjust(d66, total)
                    exp += e2.rules.hit_count(int(fp), adjusted) / 36.0
            if m.kind == "primary":
                gf += fp
        return {"post_bearing": post_b, "post_rel": rel, "distance": d,
                "mounts_bearing": n_bear, "main_gf_bearing": gf,
                "expected_hits": exp}

    # common reference distance = max of the two arms' post distances
    probe_b = measure(broad_plan)
    probe_n = measure(narrow_plan)
    if "error" in probe_b or "error" in probe_n:
        results = {"error": [probe_b, probe_n]}
        (OUT / "mg1_broadside.json").write_text(json.dumps(results, indent=1))
        print(json.dumps(results, indent=1)); return 1
    d_ref = max(probe_b["distance"], probe_n["distance"])
    results = {"BROADSIDE": measure(broad_plan, eh_distance=d_ref),
               "NARROW": measure(narrow_plan, eh_distance=d_ref)}
    gb = results["BROADSIDE"]["main_gf_bearing"]
    gn = results["NARROW"]["main_gf_bearing"]
    eb = results["BROADSIDE"]["expected_hits"]
    en = results["NARROW"]["expected_hits"]
    imp_gf = 100 * (gb - gn) / max(1e-9, gn)
    imp_eh = 100 * (eb - en) / max(1e-9, en)
    gate = imp_gf >= 25 or imp_eh >= 25
    results["verdict"] = {
        "gate": "PASS" if gate else "FAIL",
        "threshold": ">= +25% available main-GF (post-movement bearing) or "
                     "common-distance expected hits",
        "gf_improvement_pct": round(imp_gf, 1),
        "eh_improvement_pct_common_distance": round(imp_eh, 1),
        "d_ref": d_ref,
        "post_rel_broad": results["BROADSIDE"]["post_rel"],
        "post_rel_narrow": results["NARROW"]["post_rel"],
    }
    (OUT / "mg1_broadside.json").write_text(json.dumps(results, indent=1, default=str))
    print(json.dumps(results, indent=1, default=str))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
