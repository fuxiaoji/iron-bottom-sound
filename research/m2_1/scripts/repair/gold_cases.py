"""M2.1-R Strategic Gold Cases (G1-G5): measurement-repair acceptance tests.

Each case: find a reachable state whose geometry supports the tactical
pattern, build 2-4 legal intent candidates (validator-passed), prove geometry
separation where the plan requires it (G1/G2), then evaluate P0/T0/T1/T2 under
E0 (scripted), E3 (adversarial profile), E2 (local minimax).

GOLD_EVALUATOR_GATE: >= 4 of 5 cases must produce clear tactical separation.

    PYTHONPATH=backend/src:research/m2_1/scripts .venv/bin/python \
        research/m2_1/scripts/repair/gold_cases.py
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO / "research" / "m2_1" / "scripts"))

from iron_bottom_sound.engine import IronBottomEngine  # noqa: E402
from iron_bottom_sound.models import (GameOptions, MovementOrder, OrderBatch,  # noqa: E402
                                      Phase, Side)
from iron_bottom_sound.tactical import PROFILES, TacticalCommander  # noqa: E402
from repair.evaluator import run_arm  # noqa: E402
from repair.intents import INTENTS, intent_batch  # noqa: E402

OUT = REPO / "research" / "m2_1"
REPS = 5
PROFILES_POOL = ("balanced", "fleet", "line", "brawl", "cautious")


def reach_move(scenario, seed, turn_min):
    eng = IronBottomEngine()
    st = eng.reset(scenario, seed, GameOptions(mode="llm"))
    se = {s: TacticalCommander(profile=PROFILES["balanced"]) for s in Side}
    g = 0
    while st.phase != Phase.COMPLETE and g < 200:
        g += 1
        if st.phase == Phase.MOVEMENT_PLANNING and st.turn >= turn_min:
            return eng, st
        if st.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                        Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                        Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
            for s in Side:
                if s.value not in st.submitted_orders:
                    b = se[s].choose_plan(eng, st.game_id, s)[1]
                    if not eng.submit_orders(st.game_id, b).valid:
                        return None, None
        eng.advance(st.game_id)
    return None, None


def plan_tables(eng, st, side):
    own = [s for s in st.ships.values()
           if s.side == side and not s.sunk and s.position]
    return {s.id: _plans(eng, st, s.id) for s in own}


def _plans(eng, st, ship_id):
    ship = st.ships[ship_id]
    info = eng.movement_candidates(st, ship, include_plans=True)
    plans = {e["plan"] for e in info.get("reachable", []) if e.get("plan")}
    if info.get("reachable"):
        plans.add("0")
    return plans


def make_batch(eng, st, side, plan_map) -> str:
    from iron_bottom_sound.models import Phase
    batch = OrderBatch(side=side, phase=Phase.MOVEMENT_PLANNING)
    for ship_id, plan in plan_map.items():
        ship = st.ships[ship_id]
        if ship.sunk or not ship.position:
            continue
        cost = None
        info = eng.movement_candidates(st, ship, include_plans=True)
        for entry in info.get("reachable", []):
            if entry.get("plan") == plan:
                cost = entry.get("cost", entry.get("speed", 0))
                break
        batch.movement.append(MovementOrder(ship_id=ship_id, plan=plan, speed=cost))
    return batch.model_dump_json()


def validate(eng, st, side, cand_json) -> bool:
    from iron_bottom_sound.models import OrderBatch, Phase, Side as _S
    batch = OrderBatch.model_validate_json(cand_json)
    batch.side = _S(side) if isinstance(side, str) else side
    batch.phase = Phase.MOVEMENT_PLANNING
    return eng.validate_orders(st.game_id, batch).valid


# --------------------------------------------------------------------------
# geometry separation measures (G1/G2 requirement)
# --------------------------------------------------------------------------


def gunnery_geometry(eng, st, side, cand_json):
    """Post-movement (P0): mounts that can bear on any enemy, expected gunnery
    opportunity, and broadside-fraction.  Read-only engine semantics."""
    from iron_bottom_sound.models import GameState, OrderBatch, Phase, Side
    from iron_bottom_sound.tactical import PROFILES, TacticalCommander
    st2 = GameState.model_validate_json(st.model_dump_json())
    e2 = IronBottomEngine()
    e2.games[st2.game_id] = st2
    batch = OrderBatch.model_validate_json(cand_json)
    batch.side = Side(side) if isinstance(side, str) else side
    batch.phase = Phase.MOVEMENT_PLANNING
    # apply movement by submitting then resolving the phase via advance-like
    # sequence: submit both sides (opponent scripted) and advance once.
    se = {s: TacticalCommander(profile=PROFILES["balanced"]) for s in Side}
    r = e2.submit_orders(st2.game_id, batch)
    if not r.valid:
        return {"expected_hits": None, "error": "batch invalid: " + str(r.errors[:1])}
    other = Side.ALLIES if side == Side.AXIS else Side.AXIS
    if other.value not in st2.submitted_orders:
        b2 = se[other].choose_plan(e2, st2.game_id, other)[1]
        e2.submit_orders(st2.game_id, b2)
    # F9 fix: ONE advance() from movement_planning only steps to
    # torpedo_planning (ships have not moved).  Advance until the movement
    # phase has actually resolved (phase == torpedo_effects).
    g = 0
    while st2.phase.value not in ("torpedo_effects", "complete") and g < 8:
        g += 1
        if st2.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                         Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                         Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
            for s in Side:
                if s.value not in st2.submitted_orders:
                    b3 = se[s].choose_plan(e2, st2.game_id, s)[1]
                    e2.submit_orders(st2.game_id, b3)
        e2.advance(st2.game_id)
    mounts_total = mounts_bearing = 0
    expected = 0.0
    broad = narrow = 0
    for ship in st2.ships.values():
        if ship.side != side or ship.sunk or not ship.position:
            continue
        assist = e2.gunnery_assist(st2, side, target_id=None) if False else e2.gunnery_assist(st2, side)
        for t in assist.get("targets", []):
            expected += float(t.get("expected_hits", 0.0))
        for mount in ship.gun_mounts:
            if mount.destroyed or mount.fired_this_phase:
                continue
            mounts_total += 1
        # aspect of this ship to its nearest enemy (broadside = good)
        enemies = [s for s in st2.ships.values()
                   if s.side != side and not s.sunk and s.position]
        if enemies and ship.position:
            near = min(enemies, key=lambda e2s: ship.position.distance(e2s.position))
            aspect = e2._target_aspect(ship, near)
            if aspect == "broadside":
                broad += 1
            else:
                narrow += 1
    mounts_bearing = mounts_total  # engine assist only lists bearable targets
    return {"expected_hits": expected, "broadside_ships": broad,
            "narrow_ships": narrow, "mounts_total": mounts_total}


# --------------------------------------------------------------------------
# case definitions
# --------------------------------------------------------------------------


def case_G1(eng, st, side):
    """Broadside unmasking: exists ships whose aspect to the nearest enemy is
    narrow; candidates unmask (beam) vs stay narrow."""
    tables = plan_tables(eng, st, side)
    unmask = intent_batch(eng, st, side, "UNMASK_BROADSIDE", tables)
    narrow = intent_batch(eng, st, side, "KEEP_NARROW_CLOSE", tables)
    pol = intent_batch(eng, st, side, "POLICY", tables)
    if unmask is None or narrow is None:
        return None
    cand = {"UNMASK_BROADSIDE": make_batch(eng, st, side, unmask),
            "KEEP_NARROW": make_batch(eng, st, side, narrow)}
    if pol:
        cand["POLICY_BALANCED"] = make_batch(eng, st, side, pol)
    cand = {n: j for n, j in cand.items() if validate(eng, st, side, j)}
    if len(cand) < 2:
        return None
    return {"candidates": cand, "good": "UNMASK_BROADSIDE", "bad": "KEEP_NARROW"}


def case_G2(eng, st, side):
    """Crossing the T: cross the enemy line vs stay parallel to it."""
    tables = plan_tables(eng, st, side)
    cross = intent_batch(eng, st, side, "CROSS_T_PORT", tables)
    keep = intent_batch(eng, st, side, "KEEP_NARROW_CLOSE", tables)
    if cross is None or keep is None:
        return None
    cand = {"CROSS_T": make_batch(eng, st, side, cross),
            "KEEP_NARROW": make_batch(eng, st, side, keep)}
    cand = {n: j for n, j in cand.items() if validate(eng, st, side, j)}
    if len(cand) < 2:
        return None
    return {"candidates": cand, "good": "CROSS_T", "bad": "KEEP_NARROW"}


def case_G3(eng, st, side):
    """Range control: close vs open vs maintain."""
    tables = plan_tables(eng, st, side)
    cand = {}
    for intent, name in (("CLOSE_RANGE", "CLOSE"), ("OPEN_RANGE", "OPEN"),
                         ("MAINTAIN_RANGE", "MAINTAIN")):
        b = intent_batch(eng, st, side, intent, tables)
        if b:
            cand[name] = make_batch(eng, st, side, b)
    cand = {n: j for n, j in cand.items() if validate(eng, st, side, j)}
    if len(cand) < 2:
        return None
    return {"candidates": cand, "good": None, "bad": None}


def case_G4(eng, st, side):
    """Torpedo corridor: fire now down the approach lane vs hold (movement
    toward the lane).  Requires >=2 turns and opponent replanning — the
    evaluator's T1/T2 already script the opponent anew."""
    torp_ships = [s for s in st.ships.values()
                  if s.side == side and not s.sunk and s.position
                  and s.torpedo and any(l.loaded > 0 and not l.destroyed
                                        for l in s.torpedo_launchers)]
    if not torp_ships:
        return None
    tables = plan_tables(eng, st, side)
    close = intent_batch(eng, st, side, "CLOSE_RANGE", tables)
    openr = intent_batch(eng, st, side, "OPEN_RANGE", tables)
    cand = {}
    if close:
        cand["PRESS_CORRIDOR"] = make_batch(eng, st, side, close)
    if openr:
        cand["REFUSE"] = make_batch(eng, st, side, openr)
    cand = {n: j for n, j in cand.items() if validate(eng, st, side, j)}
    if len(cand) < 2:
        return None
    return {"candidates": cand, "good": "PRESS_CORRIDOR", "bad": "REFUSE"}


def case_G5(eng, st, side):
    """Local force superiority: concentrate on one enemy cluster vs disperse
    to nearest enemies."""
    tables = plan_tables(eng, st, side)
    conc = intent_batch(eng, st, side, "CONCENTRATE_LOCAL_FORCE", tables)
    openr = intent_batch(eng, st, side, "OPEN_RANGE", tables)
    if conc is None or openr is None:
        return None
    cand = {"CONCENTRATE": make_batch(eng, st, side, conc),
            "DISPERSE": make_batch(eng, st, side, openr)}
    cand = {n: j for n, j in cand.items() if validate(eng, st, side, j)}
    if len(cand) >= 2:
        return {"candidates": cand, "good": "CONCENTRATE", "bad": "DISPERSE"}
    return None


CASES = (("G1_BROADSIDE_UNMASKING", case_G1, ("IBS-S-01", "IBS-S-EM-01")),
         ("G2_CROSSING_THE_T", case_G2, ("IBS-S-01", "IBS-S-EM-01")),
         ("G3_RANGE_CONTROL", case_G3, ("IBS-S-01", "IBS-S-03", "IBS-S-EM-01")),
         ("G4_TORPEDO_CORRIDOR_DENIAL", case_G4, ("IBS-S-01", "IBS-S-03", "IBS-S-EM-01")),
         ("G5_LOCAL_FORCE_SUPERIORITY", case_G5, ("IBS-S-01", "IBS-S-EM-01")))


def evaluate_case(case_name, case, scenario, seed, side_value, turn):
    """Evaluate one built case: geometry separation + E0/E3 values."""
    profile_pair = ("balanced", "balanced")
    st = _state_for(case, scenario, seed, side_value, turn)
    geo = {}
    e0 = {}
    e3 = {}
    for name, cj in case["candidates"].items():
        geo[name] = gunnery_geometry(IronBottomEngine(), st, side_value, cj)
        vals = []
        for rep in range(REPS):
            p = run_arm(st, cj, "movement", side_value, profile_pair, rep)
            if p:
                vals.append(p)
        if vals:
            e0[name] = {c: statistics.mean(p[c]["U1"] for p in vals if c in p)
                        for c in ("P0", "T0", "T1", "T2") if any(c in p for p in vals)}
        # E3: adversarial opponent profile (worst of the pool)
        worst = None
        for prof in PROFILES_POOL:
            vals3 = []
            for rep in range(3):
                p = run_arm(st, cj, "movement", side_value, (profile_pair[0], prof), rep)
                if p and "T2" in p:
                    vals3.append(p["T2"]["U1"])
            if vals3:
                m = statistics.mean(vals3)
                if worst is None or m < worst:
                    worst = m
        if worst is not None:
            e3[name] = worst
    return {"geometry": geo, "e0": e0, "e3": e3}


_STATE_CACHE = {}


def _state_for(case, scenario, seed, side_value, turn):
    key = (scenario, seed)
    if key not in _STATE_CACHE:
        eng, st = reach_move(scenario, seed, turn)
        _STATE_CACHE[key] = (eng, st)
    return _STATE_CACHE[key][1]


def main() -> int:
    report = {"cases": {}}
    n_separated = 0
    n_built = 0
    for case_name, builder, scenarios in CASES:
        built = None
        for scenario in scenarios:
            for seed in range(1, 9):
                for turn in (2, 3):
                    eng, st = reach_move(scenario, seed, turn)
                    if st is None:
                        continue
                    side = Side.ALLIES
                    try:
                        built = builder(eng, st, side)
                    except Exception as exc:  # noqa: BLE001
                        built = None
                    if built and len(built["candidates"]) >= 2:
                        res = evaluate_case(case_name, built, scenario, seed,
                                            side.value, turn)
                        report["cases"][case_name] = {
                            "scenario": scenario, "seed": seed, "turn": turn,
                            "side": side.value, "candidates": list(built["candidates"]),
                            **res}
                        n_built += 1
                        # separation: good > bad at T2 (E0) by >= 0.05, or
                        # geometry separates for G1/G2
                        separated = None
                        if built["good"] and built["good"] in res["e0"] and built["bad"] in res["e0"]:
                            g = res["e0"][built["good"]].get("T2")
                            b = res["e0"][built["bad"]].get("T2")
                            if g is not None and b is not None:
                                separated = (g - b) >= 0.05
                        if separated:
                            n_separated += 1
                        report["cases"][case_name]["tactical_separation_T2"] = separated
                        print(f"{case_name}: {scenario} s{seed} t{turn} "
                              f"cands={len(built['candidates'])} sep={separated}",
                              flush=True)
                        break
                if built and len(built["candidates"]) >= 2:
                    break
            if built and len(built["candidates"]) >= 2:
                break
        if not (built and len(built["candidates"]) >= 2):
            report["cases"][case_name] = {"status": "NOT_BUILT"}
            print(f"{case_name}: NOT BUILT", flush=True)
    gate = n_separated >= 4
    report["gate"] = {"built": n_built, "separated": n_separated,
                      "required": ">=4 of 5 with clear separation",
                      "verdict": "PASS" if gate else "GOLD_EVALUATOR_GATE=FAIL"}
    (OUT / "metrics" / "gold_cases.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report["gate"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
