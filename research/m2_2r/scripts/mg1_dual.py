"""MG1 dual-scale freeze (PI Decision 1): L0 intent fidelity vs L1 team utility.

Re-measures the frozen MG1 case (exact reproduction re-checked) with the B1E arm
set and metric hierarchy:

    L0  focal ship -> its recorded target: legal visible-fire EH + usable mounts
    L1  U_team = FIRE_SEARCH own EH - FIRE_SEARCH enemy EH          (frozen)
    ExternalityGain = delta_L1 - delta_L0

`CURRENT_INTENT_PRE_FIX` is carried for bug provenance only; the repaired
compiler is `REPAIRED_INTENT_BASELINE` and is never labelled CURRENT.

    PYTHONPATH=backend/src:research/m2_2r/scripts:research/m2_2/scripts:research/m2_1/scripts \
        .venv/bin/python research/m2_2r/scripts/mg1_dual.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "m2_2" / "scripts"))

from b1e import (NAME_PRE_FIX, NAME_REPAIRED, N_RANDOM, OUT, SCENARIOS,  # noqa: E402
                 TH_ABS, TH_REL, local_metric, team_metric)
from intent_compiler import pre_fix_intent_plans, repaired_intent_plans  # noqa: E402
from m22_b0 import OTHER, beam_search_movement, build_mg1, play_movement, verify_mg1  # noqa: E402
from mg.micro import plan_tables  # noqa: E402
from mg.mg_cases import ships_of  # noqa: E402


def main() -> int:
    case = build_mg1(log=lambda *a: None)
    if case is None:
        raise SystemExit("MG1 case construction failed")
    rep = verify_mg1(case, log=lambda *a: None)
    side, focal, target = case["side"], case["focal"], case["target"]
    st, se, en, pol = case["st"], case["se"], case["enemy_plans"], case["policy_map"]
    enemies = ships_of(st, OTHER[side])

    def ev(plan_map):
        st2, e2, err = play_movement(st, side, plan_map, en, se)
        if st2 is None:
            return None
        return {"L0": local_metric(e2, st2, focal, target),
                "L1": team_metric(e2, st2, side)}

    arms = {
        "CURRENT_POLICY": ev(pol),
        NAME_PRE_FIX: ev(pre_fix_intent_plans(case["eng"], st, side, "BROADSIDE", enemies)),
        NAME_REPAIRED: ev(repaired_intent_plans(case["eng"], st, side, "BROADSIDE", enemies)),
    }
    rng = random.Random(20260921)
    rp = sorted(plan_tables(case["eng"], st, side).get(focal, {"0"}))
    draws = [rng.choice(rp) for _ in range(N_RANDOM)]
    rv = [ev({**pol, focal: p}) for p in draws]
    rv = [r for r in rv if r]
    arms["RANDOM_LEGAL"] = {
        "L0": {"L0": sum(r["L0"]["L0"] for r in rv) / len(rv),
               "mounts": sum(r["L0"]["mounts"] for r in rv) / len(rv),
               "visible": any(r["L0"]["visible"] for r in rv)},
        "L1": {"U_team": sum(r["L1"]["U_team"] for r in rv) / len(rv)},
        "n_ok": len(rv), "draws": [{"plan": p} for p in draws]}
    u, assign, meta = beam_search_movement(case["eng"], st, side, pol, en, se, width=64)
    arms["BEAM_SEARCH_COMPILER"] = ev(assign) if assign else None

    base = arms["CURRENT_POLICY"]
    out = {"case": {"scenario": "IBS-S-01", "seed": 5, "side": side.value,
                    "focal": focal, "target": target,
                    "gold_plan": case["gold_plan"], "counter_plan": case["ref_plan"]},
           "reproduction": rep,
           "metrics": {"L0": "focal->target legal visible-fire EH, usable mounts",
                       "L1": "U_team = FIRE_SEARCH own EH - enemy EH (frozen)",
                       "externality": "delta_L1 - delta_L0"},
           "arms": {}, "beam_assign": assign, "beam_meta": meta,
           "thresholds": {"relative": TH_REL, "absolute": TH_ABS}}
    for name, v in arms.items():
        if v is None:
            out["arms"][name] = {"error": "arm failed"}
            continue
        d0 = v["L0"]["L0"] - base["L0"]["L0"]
        d1 = v["L1"]["U_team"] - base["L1"]["U_team"]
        out["arms"][name] = {
            "L0_eh": v["L0"]["L0"], "L0_mounts": v["L0"]["mounts"],
            "L0_visible": v["L0"]["visible"], "L1_U_team": v["L1"]["U_team"],
            "delta_L0": d0, "delta_L1": d1, "externality": d1 - d0,
            "rel_L0": d0 / max(abs(base["L0"]["L0"]), 1e-9),
            "MECHANISM_OPPORTUNITY": bool(d0 >= TH_ABS and d0 / max(abs(base["L0"]["L0"]), 1e-9) >= TH_REL),
            "USABLE_TACTICAL_OPPORTUNITY": bool(d1 >= TH_ABS),
            "MECHANISM_SUCCESS_BUT_NEGATIVE_EXTERNALITY": bool(d0 > 0 and d1 < 0)}
    b = out["arms"].get("BEAM_SEARCH_COMPILER", {})
    c = out["arms"].get("CURRENT_POLICY", {})
    out["headline"] = {
        "beam_local_gain_over_policy": b.get("delta_L0"),
        "beam_team_gain_over_policy": b.get("delta_L1"),
        "beam_externality": b.get("externality"),
        "repaired_local_gain_over_policy": out["arms"].get(NAME_REPAIRED, {}).get("delta_L0"),
        "repaired_team_gain_over_policy": out["arms"].get(NAME_REPAIRED, {}).get("delta_L1"),
        "pre_fix_local_gain_over_policy": out["arms"].get(NAME_PRE_FIX, {}).get("delta_L0"),
        "pre_fix_team_gain_over_policy": out["arms"].get(NAME_PRE_FIX, {}).get("delta_L1"),
    }
    (OUT / "mg1_dual_scale.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({"reproduction_ok": rep["reproduced"],
                      "headline": out["headline"],
                      "arms": {k: {kk: vv for kk, vv in v.items()
                                   if kk in ("L0_eh", "L0_mounts", "L1_U_team",
                                             "delta_L0", "delta_L1", "externality")}
                               for k, v in out["arms"].items()}},
                     indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
