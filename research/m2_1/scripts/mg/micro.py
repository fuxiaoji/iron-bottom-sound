"""M2.1-R2 shared machinery for Mechanistic Gold micro-cases.

Measurement point convention: apply the arm's movement batch at
MOVEMENT_PLANNING, then advance the phase machine until phase == GUNNERY,
submitting NOTHING for gunnery — so all gunnery geometry/expected-hit APIs are
read at the post-movement, pre-fire instant.

All arm orders go through engine.validate_orders; no state surgery; no
hidden-information use for arm construction.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend" / "src"))

from iron_bottom_sound.engine import IronBottomEngine  # noqa: E402
from iron_bottom_sound.models import (GameOptions, MovementOrder,  # noqa: E402
                                      OrderBatch, Phase, Side)
from iron_bottom_sound.tactical import PROFILES, TacticalCommander  # noqa: E402

OTHER = {Side.AXIS: Side.ALLIES, Side.ALLIES: Side.AXIS}


def reach(scenario: str, seed: int, phase: Phase, turn_min: int):
    eng = IronBottomEngine()
    st = eng.reset(scenario, seed, GameOptions(mode="llm"))
    se = {s: TacticalCommander(profile=PROFILES["balanced"]) for s in Side}
    g = 0
    while st.phase != Phase.COMPLETE and g < 300:
        g += 1
        if st.phase == phase and st.turn >= turn_min:
            return eng, st, se
        if st.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                        Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                        Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
            for s in Side:
                if s.value not in st.submitted_orders:
                    b = se[s].choose_plan(eng, st.game_id, s)[1]
                    if not eng.submit_orders(st.game_id, b).valid:
                        return None, None, se
        eng.advance(st.game_id)
    return None, None, se


def plan_tables(eng, st, side):
    out = {}
    for s in st.ships.values():
        if s.side != side or s.sunk or not s.position:
            continue
        info = eng.movement_candidates(st, s, include_plans=True)
        plans = {e["plan"] for e in info.get("reachable", []) if e.get("plan")}
        if info.get("reachable"):
            plans.add("0")
        out[s.id] = plans
    return out


def scripted_plans(eng, st, side, profile="balanced") -> dict:
    """The side's own commander proposal (used as filler for non-focal ships)."""
    cmd = TacticalCommander(profile=PROFILES[profile])
    _, batch, _ = cmd.choose_plan(eng, st.game_id, side)
    return {o.ship_id: o.plan for o in batch.movement}


def build_batch(eng, st, side, override: dict, filler: dict) -> str:
    from iron_bottom_sound.models import Phase
    batch = OrderBatch(side=side, phase=Phase.MOVEMENT_PLANNING)
    plans = dict(filler)
    plans.update(override)
    for ship_id, plan in sorted(plans.items()):
        ship = st.ships.get(ship_id)
        if ship is None or ship.sunk or not ship.position:
            continue
        cost = None
        if plan != "0":
            info = eng.movement_candidates(st, ship, include_plans=True)
            for entry in info.get("reachable", []):
                if entry.get("plan") == plan:
                    cost = entry.get("cost", entry.get("speed", 0))
                    break
        else:
            cost = 0
        batch.movement.append(MovementOrder(ship_id=ship_id, plan=plan, speed=cost))
    return batch.model_dump_json()


def advance_to_gunnery(st, eng, se):
    """Advance phase-by-phase until GUNNERY, submitting nothing for gunnery.
    Movement (and any earlier phases) resolve normally."""
    g = 0
    while st.phase not in (Phase.GUNNERY, Phase.COMPLETE) and g < 8:
        g += 1
        if st.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                        Phase.TORPEDO_PLANNING, Phase.CONTACT_SETUP,
                        Phase.FORMATION_SETUP}:
            for s in Side:
                if s.value not in st.submitted_orders:
                    b = se[s].choose_plan(eng, st.game_id, s)[1]
                    if not eng.submit_orders(st.game_id, b).valid:
                        return False
        eng.advance(st.game_id)
    return st.phase == Phase.GUNNERY


def measure_gunnery(eng, st, focal_side: Side, target_side: Side | None = None):
    """Rule-native gunnery measurements at the post-movement, pre-fire instant.

    For every focal ship and every opposing ship: mounts that can bear,
    their firepower split main/secondary, expected hits via
    engine.expected_gunnery_hits with engine-computed modifiers, aspect,
    longitudinal flag."""
    focal_side = Side(focal_side) if isinstance(focal_side, str) else focal_side
    opp = OTHER[focal_side]
    ships = {}
    for s in st.ships.values():
        if s.sunk or not s.position:
            continue
        ships[s.id] = s
    rows = []
    totals = {"main_gf": 0.0, "sec_gf": 0.0, "expected_hits": 0.0,
              "legal_targets": 0, "longitudinal": 0, "broadside": 0,
              "pairs": 0}
    for ship_id, ship in ships.items():
        if ship.side != focal_side:
            continue
        for tid, tgt in ships.items():
            if tgt.side == focal_side:
                continue
            d = ship.position.distance(tgt.position)
            aspect = eng._target_aspect(ship, tgt)
            for m in ship.gun_mounts:
                if m.destroyed:
                    continue
                if not eng._mount_can_bear(ship, tgt, m.arcs):
                    continue
                fp = float(getattr(m, "firepower", 0) or 0)
                if fp <= 0:
                    continue
                caliber = 8.0
                mods = eng._gunnery_modifiers(st, ship, tgt, d, 1, caliber, 1)
                # expected hits over the 2d6 roll distribution
                exp = 0.0
                for roll in range(2, 13):
                    p = (6 - abs(roll - 7)) / 36.0
                    hits = eng.rules.hit_count(int(fp), roll + sum(mods.values()))
                    exp += p * hits
                kind = "main_gf" if m.kind == "primary" else "sec_gf"
                totals[kind] += fp
                totals["expected_hits"] += exp
                totals["pairs"] += 1
                if aspect == "bow_stern":
                    totals["longitudinal"] += 1
            can_bear = sum(1 for m in ship.gun_mounts
                           if not m.destroyed and eng._mount_can_bear(ship, tgt, m.arcs))
            if can_bear > 0:
                totals["legal_targets"] += 1
            if aspect == "broadside":
                totals["broadside"] += 1
            rows.append({"ship": ship_id, "target": tid, "distance": d,
                         "aspect": aspect, "can_bear_mounts": can_bear})
    return {"totals": totals, "pairs": rows}


def side_summary(measure, focal_side: Side) -> dict:
    """Aggregate a measure_gunnery result for one side (own GF / EH vs the
    opposing fleet)."""
    t = measure["totals"]
    return {"own_main_gf": t["main_gf"], "own_sec_gf": t["sec_gf"],
            "own_expected_hits": t["expected_hits"],
            "own_legal_targets": t["legal_targets"],
            "own_longitudinal_pairs": t["longitudinal"],
            "own_broadside_pairs": t["broadside"]}
