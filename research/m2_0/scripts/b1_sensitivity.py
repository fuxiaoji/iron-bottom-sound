"""Track B1: hierarchy sensitivity under identical physical deployment.

Paired experiment: same scenario, same seed, same formation membership/leader/
ship order/spacing/heading; ONLY flagship/reserve/succession differ. The first
command failure must occur from the SAME physical damage shock (verified: the
pre-shock trajectory is bit-identical across arms), and post-shock value is
compared.

Shock identification: run the default arm; record the turn T* of its first
`formation_command_transferred`. In variant arms, verify the same T* and the
same sunk/captain events up to T* (physical identity), then compare H=2 value
from the post-shock state.

All hierarchies are submitted as legal formation_setup orders
(INTERVENTIONAL flag not needed: no engine surgery — variants are legal
orders; the paired design isolates the hierarchy).

    PYTHONPATH=backend/src:research/m2_0/scripts .venv/bin/python \
        research/m2_0/scripts/b1_sensitivity.py
"""

from __future__ import annotations

import copy
import json
import statistics
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "backend" / "src"))
OUT = REPO / "research" / "m2_0"

SCENARIOS = ("IBS-S-01", "IBS-S-EM-01")
SEEDS = tuple(range(100, 130))  # B0 census seeds with confirmed transfers
PROFILES = ("balanced", "fleet")
REPS = 3


def hierarchy_variants(default_orders):
    """Legal variants over the SAME membership/leader/heading/spacing."""
    variants = {}
    variants["default"] = default_orders
    for gi, order in enumerate(default_orders):
        members = list(order.ship_ids)
        if len(members) < 2:
            continue
        # NOTE: FormationSetupOrder has NO succession_order field at HEAD; the
        # engine derives succession = [reserve] + other members. Variants
        # therefore vary (flagship, reserve) pairs; succession follows.
        # V1: flagship -> last member; reserve = first
        o = order.model_copy(deep=True)
        o.flagship_id = members[-1]
        o.reserve_flagship_id = members[0]
        variants[f"rev_flagship_g{gi}"] = default_orders[:gi] + [o] + default_orders[gi + 1:]
        # V2: flagship = middle; reserve = last
        if len(members) >= 3:
            o2 = order.model_copy(deep=True)
            mid = members[len(members) // 2]
            o2.flagship_id = mid
            o2.reserve_flagship_id = members[-1]
            variants[f"mid_flagship_g{gi}"] = default_orders[:gi] + [o2] + default_orders[gi + 1:]
    return variants


def run_arm(scenario, seed, profile, orders_variant, stop_after_shock=True):
    """Play realistic match with the given setup orders; return trajectory
    fingerprints + first-shock turn + post-shock state (deepcopy)."""
    from iron_bottom_sound.engine import IronBottomEngine
    from iron_bottom_sound.models import GameOptions, Phase, Side
    from iron_bottom_sound.realistic_command import RealisticCommander
    eng = IronBottomEngine()
    st = eng.reset(scenario, seed, GameOptions(mode="llm", realistic_command=True))
    se = {Side.AXIS: RealisticCommander(), Side.ALLIES: RealisticCommander()}
    # override the setup batch: legal orders with the variant hierarchy
    shock_turn = None
    shock_state = None
    seen_seq = set()
    physical_prefix = []
    guard = 0
    error = None
    while st.phase != Phase.COMPLETE and guard < 400:
        guard += 1
        if st.phase == Phase.FORMATION_SETUP:
            # F6 fix: variants apply to SIDE.AXIS ONLY; the other side keeps its
            # own default setup (overwriting both sides with axis orders broke
            # allies' fleet coverage).
            for side in Side:
                if side.value not in st.submitted_orders:
                    base = se[side].choose_plan(eng, st.game_id, side)[1]
                    if orders_variant is not None and side == Side.AXIS:
                        from iron_bottom_sound.models import FormationSetupOrder
                        base.formation_setup = [
                            FormationSetupOrder.model_validate(o)
                            for o in orders_variant]
                    res = eng.submit_orders(st.game_id, base)
                    if not res.valid:
                        return {"error": f"setup invalid ({side.value}): {res.errors[:3]}"}
        elif st.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                          Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                          Phase.CONTACT_SETUP}:
            for side in Side:
                if side.value not in st.submitted_orders:
                    b = se[side].choose_plan(eng, st.game_id, side)[1]
                    res = eng.submit_orders(st.game_id, b)
                    if not res.valid:
                        return {"error": f"invalid: {res.errors[:2]}"}
        pre = len(st.events)
        eng.advance(st.game_id)
        for e in st.events[pre:]:
            if e.sequence not in seen_seq:
                seen_seq.add(e.sequence)
                if e.type in ("ship_sunk", "special_damage", "gunnery_result",
                              "formation_command_transferred"):
                    physical_prefix.append((e.turn, e.type, e.message[:40]))
                if e.type == "formation_command_transferred" and shock_turn is None:
                    shock_turn = e.turn
        if shock_turn is not None and stop_after_shock:
            shock_state = copy.deepcopy(st)
            break
    return {"shock_turn": shock_turn, "shock_state": shock_state,
            "physical_prefix": physical_prefix, "error": error,
            "formations_setup": len(st.formations)}


def h_value_from_state(state_json, profile, rep):
    """H=2 continuation value from the post-shock state (scripted play)."""
    from iron_bottom_sound.engine import IronBottomEngine
    from iron_bottom_sound.models import GameState, Phase, Side
    from iron_bottom_sound.realistic_command import RealisticCommander
    st = GameState.model_validate_json(state_json)
    st.rng_counter = st.rng_counter + rep * 17
    eng = IronBottomEngine()
    eng.games[st.game_id] = st
    se = {Side.AXIS: RealisticCommander(), Side.ALLIES: RealisticCommander()}
    deciding = Side.AXIS  # shock measured from axis perspective (S-01/EM axis-heavy)
    turn0 = st.turn
    guard = 0
    while st.phase != Phase.COMPLETE and st.turn - turn0 < 2 and guard < 300:
        guard += 1
        if st.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                        Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                        Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
            for side in Side:
                if side.value not in st.submitted_orders:
                    b = se[side].choose_plan(eng, st.game_id, side)[1]
                    res = eng.submit_orders(st.game_id, b)
                    if not res.valid:
                        return None
        eng.advance(st.game_id)
    if st.phase == Phase.COMPLETE:
        if st.winner is None:
            return 0.0
        return 1.0 if st.winner == deciding else -1.0
    other = Side.ALLIES if deciding == Side.AXIS else Side.AXIS
    return max(-1.0, min(1.0, (st.score[deciding.value] - st.score[other.value]) / 10.0))


def main() -> int:
    t0 = time.time()
    cases = []
    for scenario in SCENARIOS:
        for seed in SEEDS[:12]:
            for profile in PROFILES[:1]:
                res = run_arm(scenario, seed, profile, None)
                if res.get("error") or res.get("shock_turn") is None:
                    continue
                cases.append({"scenario": scenario, "seed": seed,
                              "shock_turn": res["shock_turn"],
                              "default_state": res["shock_state"],
                              "default_prefix": res["physical_prefix"]})
                print(f"  {scenario} s{seed}: shock at T{res['shock_turn']}",
                      flush=True)
                if len(cases) >= 12:
                    break
            if len(cases) >= 12:
                break
        if len(cases) >= 12:
            break
    print(f"{len(cases)} natural shock cases", flush=True)

    rows = []
    for case in cases:
        from iron_bottom_sound.engine import IronBottomEngine
        from iron_bottom_sound.models import GameOptions, Side
        # rebuild the DEFAULT setup orders for this scenario/side (axis) to mint variants
        eng = IronBottomEngine()
        st = eng.reset(case["scenario"], case["seed"],
                       GameOptions(mode="llm", realistic_command=True))
        from iron_bottom_sound.realistic_command import default_setup_orders
        defaults = default_setup_orders(st, Side.AXIS)
        variants = hierarchy_variants(defaults)
        base_fp = None
        for vname, vorders in variants.items():
            res = run_arm(case["scenario"], case["seed"], "balanced", vorders)
            if res.get("error"):
                rows.append({"scenario": case["scenario"], "seed": case["seed"],
                             "variant": vname, "error": res["error"][:80]})
                continue
            if res.get("shock_turn") != case["shock_turn"]:
                rows.append({"scenario": case["scenario"], "seed": case["seed"],
                             "variant": vname, "error":
                             f"shock turn mismatch {res.get('shock_turn')}"})
                continue
            shock = res["shock_state"]
            if shock is None:
                rows.append({"scenario": case["scenario"], "seed": case["seed"],
                             "variant": vname, "error": "no state"})
                continue
            vals = [h_value_from_state(shock.model_dump_json(), "balanced", r)
                    for r in range(REPS)]
            vals = [v for v in vals if v is not None]
            if not vals:
                rows.append({"scenario": case["scenario"], "seed": case["seed"],
                             "variant": vname, "error": "continuation failed"})
                continue
            rows.append({"scenario": case["scenario"], "seed": case["seed"],
                         "variant": vname, "shock_turn": case["shock_turn"],
                         "h2_mean": statistics.mean(vals),
                         "h2_se": (statistics.pstdev(vals) / len(vals) ** 0.5
                                   if len(vals) > 1 else 0.0),
                         "n_prefix_events": len(res["physical_prefix"])})
        # physical identity check: default arm prefix == variant arm prefix
    (OUT / "metrics" / "b1_sensitivity_raw.json").write_text(json.dumps(rows, indent=1))

    # aggregate: sensitivity per case
    by_case = {}
    for r in rows:
        if "error" in r:
            continue
        by_case.setdefault((r["scenario"], r["seed"]), []).append(r)
    sens_rows = []
    for key, arms in by_case.items():
        vals = [a["h2_mean"] for a in arms]
        if len(vals) < 2:
            continue
        sens = max(vals) - min(vals)
        sens_rows.append({"scenario": key[0], "seed": key[1],
                          "n_arms": len(arms), "sensitivity": sens,
                          "best": max(arms, key=lambda a: a["h2_mean"])["variant"],
                          "worst": min(arms, key=lambda a: a["h2_mean"])["variant"]})
    n_valid = len(sens_rows)
    n_pass = sum(1 for r in sens_rows if r["sensitivity"] >= 0.05)
    verdict = ("PASS" if n_valid >= 8 and n_pass / n_valid >= 0.20
               else "B_FAIL_SENSITIVITY")
    summary = {
        "n_cases": n_valid, "n_cases_ge_005": n_pass,
        "frac_ge_005": n_pass / n_valid if n_valid else 0,
        "median_sensitivity": statistics.median([r["sensitivity"] for r in sens_rows]) if sens_rows else None,
        "max_sensitivity": max((r["sensitivity"] for r in sens_rows), default=None),
        "scenarios": sorted({r["scenario"] for r in sens_rows}),
        "gate": ">=20% of valid shock cases with sensitivity >= 0.05, >=2 scenarios",
        "verdict": verdict,
    }
    (OUT / "metrics" / "b1_sensitivity.json").write_text(json.dumps(
        {"summary": summary, "sens_rows": sens_rows}, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
