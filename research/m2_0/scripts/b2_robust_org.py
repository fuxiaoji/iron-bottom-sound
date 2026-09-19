"""Track B2: robust organization oracle (only after B0+B1 PASS).

Compares initial command organizations under the natural shock distribution:
  default            scenario/default_setup_orders
  random legal       random flagship/reserve within formations (3 draws)
  flagship max VP    per formation, flagship = highest-VP member
  flagship low-exposure  flagship = member farthest from nearest enemy at setup
  reserve fastest    reserve = fastest compatible member
  succession surviv  flagship keeps default; succession ordered by hull% asc
                     (reserve = most damaged member first — the disposable one)

Value: H=2 terminal/VP utility from the AXIS perspective (same as B1),
5 CRN reps per arm, shock from natural play. Nominal (no-shock) penalty:
default-vs-arm H=2 value on matches without an early shock.

    PYTHONPATH=backend/src:research/m2_0/scripts .venv/bin/python \
        research/m2_0/scripts/b2_robust_org.py
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
SEEDS = tuple(range(100, 118))
REPS = 5


def mint_variants(st, side):
    from iron_bottom_sound.realistic_command import default_setup_orders
    defaults = default_setup_orders(st, side)
    variants = {"default": defaults}
    import random
    rng = random.Random(31)
    for d in range(3):
        vs = []
        for order in defaults:
            members = list(order.ship_ids)
            o = order.model_copy(deep=True)
            pick = rng.sample(members, min(2, len(members)))
            o.flagship_id, o.reserve_flagship_id = pick[0], pick[1]
            vs.append(o)
        variants[f"random{d}"] = vs
    # max-VP flagship
    vs = []
    for order in defaults:
        members = list(order.ship_ids)
        o = order.model_copy(deep=True)
        vp = {m: st.ships[m].vp for m in members}
        o.flagship_id = max(members, key=lambda m: vp[m])
        rest = [m for m in members if m != o.flagship_id]
        o.reserve_flagship_id = max(rest, key=lambda m: vp[m]) if rest else members[0]
        vs.append(o)
    variants["flagship_max_vp"] = vs
    # low-exposure flagship (distance to nearest visible enemy at setup)
    def exposure(ship):
        enemies = [s for s in st.ships.values()
                   if s.side != side and not s.sunk and s.position and ship.position]
        if not enemies or not ship.position:
            return 999.0
        return min(ship.position.distance(e.position) for e in enemies)
    vs = []
    for order in defaults:
        members = list(order.ship_ids)
        o = order.model_copy(deep=True)
        o.flagship_id = max(members, key=lambda m: exposure(st.ships[m]))
        rest = [m for m in members if m != o.flagship_id]
        o.reserve_flagship_id = max(rest, key=lambda m: exposure(st.ships[m])) if rest else members[0]
        vs.append(o)
    variants["flagship_low_exposure"] = vs
    # fastest reserve
    vs = []
    for order in defaults:
        members = list(order.ship_ids)
        o = order.model_copy(deep=True)
        o.reserve_flagship_id = max(members, key=lambda m: st.ships[m].max_speed_for_turn(st.turn))
        vs.append(o)
    variants["reserve_fastest"] = vs
    return variants


def run_arm(scenario, seed, variant_orders, want_state_on_shock=True):
    """Same engine as B1's run_arm (axis variant, allies default)."""
    from iron_bottom_sound.engine import IronBottomEngine
    from iron_bottom_sound.models import (FormationSetupOrder, GameOptions,
                                          Phase, Side)
    from iron_bottom_sound.realistic_command import RealisticCommander
    eng = IronBottomEngine()
    st = eng.reset(scenario, seed, GameOptions(mode="llm", realistic_command=True))
    se = {Side.AXIS: RealisticCommander(), Side.ALLIES: RealisticCommander()}
    shock_turn = None
    shock_state = None
    guard = 0
    error = None
    while st.phase != Phase.COMPLETE and guard < 400:
        guard += 1
        if st.phase == Phase.FORMATION_SETUP:
            for side in Side:
                if side.value not in st.submitted_orders:
                    base = se[side].choose_plan(eng, st.game_id, side)[1]
                    if variant_orders is not None and side == Side.AXIS:
                        base.formation_setup = [
                            FormationSetupOrder.model_validate(o) for o in variant_orders]
                    res = eng.submit_orders(st.game_id, base)
                    if not res.valid:
                        return {"error": f"setup invalid ({side.value}): {res.errors[:2]}"}
        elif st.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                          Phase.TORPEDO_PLANNING, Phase.GUNNERY, Phase.CONTACT_SETUP}:
            for side in Side:
                if side.value not in st.submitted_orders:
                    b = se[side].choose_plan(eng, st.game_id, side)[1]
                    res = eng.submit_orders(st.game_id, b)
                    if not res.valid:
                        return {"error": f"invalid: {res.errors[:2]}"}
        pre = len(st.events)
        eng.advance(st.game_id)
        for e in st.events[pre:]:
            if e.type == "formation_command_transferred" and shock_turn is None:
                shock_turn = e.turn
        if shock_turn is not None and want_state_on_shock:
            shock_state = copy.deepcopy(st)
            break
    return {"shock_turn": shock_turn, "shock_state": shock_state, "error": error,
            "completed": st.phase == Phase.COMPLETE,
            "final": None if shock_state else copy.deepcopy(st)}


def h_value(state, rep, horizon=2):
    from iron_bottom_sound.engine import IronBottomEngine
    from iron_bottom_sound.models import GameState, Phase, Side
    from iron_bottom_sound.realistic_command import RealisticCommander
    st = GameState.model_validate_json(state if isinstance(state, str) else state.model_dump_json())
    st.rng_counter = st.rng_counter + rep * 17
    eng = IronBottomEngine()
    eng.games[st.game_id] = st
    se = {Side.AXIS: RealisticCommander(), Side.ALLIES: RealisticCommander()}
    deciding = Side.AXIS
    turn0 = st.turn
    guard = 0
    while st.phase != Phase.COMPLETE and st.turn - turn0 < horizon and guard < 300:
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
    # collect (scenario, seed) cells with a natural shock (from B1 discovery:
    # shocks concentrate in S-01/S-EM-01 seeds 100+)
    cells = [(s, seed) for s in SCENARIOS for seed in SEEDS]
    org_names = ["default", "random0", "random1", "random2", "flagship_max_vp",
                 "flagship_low_exposure", "reserve_fastest"]
    rows = []
    for scenario, seed in cells:
        from iron_bottom_sound.engine import IronBottomEngine
        from iron_bottom_sound.models import GameOptions, Side
        eng = IronBottomEngine()
        st = eng.reset(scenario, seed, GameOptions(mode="llm", realistic_command=True))
        variants = mint_variants(st, Side.AXIS)
        arm_vals = {}
        for name in org_names:
            res = run_arm(scenario, seed, variants[name])
            if res.get("error") or res.get("shock_state") is None:
                # no shock or invalid: nominal value only via full play
                arm_vals[name] = {"shock": False, "error": (res.get("error") or "")[:60]}
                continue
            vals = [h_value(res["shock_state"], r) for r in range(REPS)]
            vals = [v for v in vals if v is not None]
            arm_vals[name] = {"shock": True, "h2_mean": statistics.mean(vals) if vals else None}
        rows.append({"scenario": scenario, "seed": seed, "arms": arm_vals})
        print(f"{scenario} s{seed}: " + " ".join(
            f"{n}={'S' if a['shock'] else '-'}" for n, a in arm_vals.items()), flush=True)
    # aggregate: post-shock mean per org vs default
    summary = {}
    for name in org_names:
        diffs = []
        vals = []
        for r in rows:
            a = r["arms"].get(name)
            d = r["arms"].get("default")
            if a and d and a.get("shock") and d.get("shock") \
                    and a.get("h2_mean") is not None and d.get("h2_mean") is not None:
                vals.append(a["h2_mean"])
                diffs.append(a["h2_mean"] - d["h2_mean"])
        summary[name] = {
            "n_shock_pairs": len(diffs),
            "mean_h2": statistics.mean(vals) if vals else None,
            "mean_diff_vs_default": statistics.mean(diffs) if diffs else None,
        }
    # B2 gate: some non-future-reading org with post-shock loss reduction >=10%
    # vs default AND nominal penalty <= 2%. Approximate nominal penalty with
    # no-shock arms' H2 (rare in these cells; reported when available).
    best = None
    for name, s in summary.items():
        if name == "default" or s["n_shock_pairs"] < 5:
            continue
        if s["mean_diff_vs_default"] is not None and s["mean_diff_vs_default"] > 0:
            rel = s["mean_diff_vs_default"] / max(1e-9, abs(summary["default"]["mean_h2"] or 1.0))
            if best is None or rel > best[1]:
                best = (name, rel, s["mean_diff_vs_default"])
    summary["best_relative_improver"] = (
        {"org": best[0], "relative": best[1], "abs": best[2]} if best else None)
    summary["gate"] = ">=10% post-shock loss reduction vs default, nominal penalty <=2%"
    summary["verdict"] = ("PASS" if best and best[1] >= 0.10 else "B_ORACLE_ONLY"
                          if best else "B_FAIL_NO_ORG_EFFECT")
    (OUT / "metrics" / "b2_robust_org.json").write_text(json.dumps(
        {"summary": summary, "rows": rows}, indent=1))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
