"""M2.1 P2+P3: candidate generators (classic movement/gunnery/torpedo) and
snapshot sampling.  Every candidate is expanded through the engine's own
candidate tables and must pass the full side-level validator; NO hidden enemy
information is used (proposals derive from own plan tables, engine assists, or
the pre-registered policy pool).

    PYTHONPATH=backend/src:research/m2_1/scripts .venv/bin/python \
        research/m2_1/scripts/p2p3_candidates.py capture
"""

from __future__ import annotations

import gzip
import json
import random
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "backend" / "src"))
OUT = REPO / "research" / "m2_1"

POLICY_POOL = ("balanced", "fleet", "line", "brawl", "cautious")
SNAP_CAPS = {"movement": 15, "gunnery": 10, "torpedo": 5}
SCENARIOS = ("IBS-S-01", "IBS-S-03", "IBS-S-EM-01")


# --------------------------------------------------------------------------
# movement candidate batches (per side)
# --------------------------------------------------------------------------

def movement_candidates_for(eng, st, side, commander_plans):
    """8-12 unique validated joint movement batches (plan §6.1).

    commander_plans: {profile_name: {ship_id: plan}} from the 5 policy
    commanders.  Sources: policy proposals (5), slower/faster legal scaling,
    port/starboard-biased, dispersed, formation-preserving (own-order
    identity), per-ship local perturbation of 1-2 high-VP ships, random legal.
    """
    ships = [s for s in st.ships.values()
             if s.side == side and not s.sunk and s.position]
    ids = [s.id for s in ships]
    if not ids:
        return {}
    plan_tables = {i: _plans(eng, st, i) for i in ids}
    vp = {i: st.ships[i].vp for i in ids}
    by_vp = sorted(ids, key=lambda i: -vp[i])

    def mk(overrides: dict[str, str]):
        b = {}
        for i in ids:
            p = overrides.get(i)
            if p is not None and p in plan_tables[i]:
                b[i] = p
            else:
                b[i] = _default_plan(plan_tables[i])
        return b

    cands: dict[str, dict] = {}

    def add(name, overrides):
        b = mk(overrides)
        key = tuple(sorted(b.items()))
        if key not in {tuple(sorted(c.items())) for c in cands.values()}:
            cands[name] = b

    # 1) the five policy commanders' own joint proposals
    for prof, plans in commander_plans.items():
        add(f"policy_{prof}", plans)
    # 2) slower / faster scaling of the balanced proposal
    base = commander_plans.get("balanced") or {}
    for i in ids:
        pass
    slow = {}
    fast = {}
    for i in ids:
        p = base.get(i)
        if p is None:
            slow[i] = fast[i] = None
            continue
        slow[i] = _scaled(plan_tables[i], p, -1)
        fast[i] = _scaled(plan_tables[i], p, +1)
    add("slower", slow)
    add("faster", fast)
    # 3) port / starboard biased
    add("port_biased", {i: _biased(plan_tables[i], "P") for i in ids})
    add("starboard_biased", {i: _biased(plan_tables[i], "S") for i in ids})
    # 4) dispersed: each ship its own max-advance plan
    add("dispersed", {i: _extreme(plan_tables[i], +1) for i in ids})
    # 5) formation-preserving: everyone holds if possible
    add("hold", {i: ("0" if "0" in plan_tables[i] else _extreme(plan_tables[i], -1))
                 for i in ids})
    # 6) local perturbation of the top-2 VP ships
    rng = random.Random(211)
    for k, ship_id in enumerate(by_vp[:2]):
        plans = list(plan_tables[ship_id])
        if not plans:
            continue
        pert = dict(base)
        pert[ship_id] = rng.choice(plans)
        add(f"perturb_vp{k+1}", pert)
    # 7) two random legal joint batches
    for d in range(2):
        add(f"random{d}", {i: (rng.choice(list(plan_tables[i])) if plan_tables[i] else "0")
                           for i in ids})
    return cands


def _plans(eng, st, ship_id):
    ship = st.ships[ship_id]
    info = eng.movement_candidates(st, ship, include_plans=True)
    plans = {e["plan"] for e in info.get("reachable", []) if e.get("plan")}
    if info.get("reachable"):
        plans.add("0")
    return plans


def _advance(plan):
    return sum(int(t) for t in __import__("re").findall(r"\d+", plan or "")) if plan and plan != "0" else 0


def _default_plan(plans):
    if "0" in plans:
        return "0"
    return min(plans, key=_advance) if plans else "0"


def _scaled(plans, base, direction):
    """Pick a legal plan with advance closest to base±2."""
    if not plans or base is None:
        return None
    tgt = _advance(base) + 2 * direction
    return min((p for p in plans), key=lambda p: abs(_advance(p) - tgt))


def _biased(plans, side_ch):
    cand = [p for p in plans if (p.count(side_ch) > p.count("S" if side_ch == "P" else "P"))]
    return (max(cand, key=_advance) if cand else
            (max(plans, key=_advance) if plans else "0"))


def _extreme(plans, sign):
    if not plans:
        return "0"
    return (max if sign > 0 else min)(plans, key=_advance)


def gunnery_candidates_for(eng, st, side, commander_batches):
    """6-10 gunnery batch variants (plan §6.3)."""
    cands = {}
    for prof, b in commander_batches.items():
        cands[f"policy_{prof}"] = b
    base = commander_batches.get("balanced")
    if base is None:
        return cands
    # hold: empty gunnery for the side
    from iron_bottom_sound.models import OrderBatch, Phase
    hold = base.model_copy(deep=True)
    hold.gunnery = []
    cands["hold"] = hold
    # concentrated: all ships target the single highest-VP visible enemy
    enemies = [s for s in st.ships.values()
               if s.side != side and not s.sunk and s.position]
    if enemies:
        vp = max(enemies, key=lambda s: s.vp)
        conc = base.model_copy(deep=True)
        for go in conc.gunnery:
            go.primary_target = vp.id
        cands["concentrate_hvp"] = conc
        # finish damaged: target the lowest-hull-fraction enemy
        dam = min(enemies, key=lambda s: (s.hull / s.max_hull) if s.hull and s.max_hull else 1.0)
        fin = base.model_copy(deep=True)
        for go in fin.gunnery:
            go.primary_target = dam.id
        cands["finish_damaged"] = fin
    # random legal: drop half the orders
    rng = random.Random(2199)
    rnd = base.model_copy(deep=True)
    rnd.gunnery = rng.sample(rnd.gunnery, max(1, len(rnd.gunnery) // 2)) if rnd.gunnery else []
    cands["random_half"] = rnd
    return cands


def torpedo_candidates_for(eng, st, side, commander_batches):
    """5-8 torpedo batch variants (plan §6.4): hold, current policy proposals,
    direct (nearest-target), random legal drop."""
    cands = {}
    for prof, b in commander_batches.items():
        if b.torpedoes:
            cands[f"policy_{prof}"] = b
    base = commander_batches.get("balanced")
    if base is None:
        return cands
    hold = base.model_copy(deep=True)
    hold.torpedoes = []
    cands["hold"] = hold
    rng = random.Random(2203)
    rnd = base.model_copy(deep=True)
    rnd.torpedoes = rng.sample(rnd.torpedoes, max(1, len(rnd.torpedoes) // 2)) if rnd.torpedoes else []
    cands["random_half"] = rnd
    return cands


# --------------------------------------------------------------------------
# snapshot capture
# --------------------------------------------------------------------------


def _reach(eng, st, se, phase, turn_min):
    g = 0
    while st.phase != Phase.COMPLETE and g < 400:
        g += 1
        if st.phase == phase and st.turn >= turn_min:
            return True
        if st.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                        Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                        Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
            for side in Side:
                if side.value not in st.submitted_orders:
                    b = se[side].choose_plan(eng, st.game_id, side)[1]
                    res = eng.submit_orders(st.game_id, b)
                    if not res.valid:
                        return False
        eng.advance(st.game_id)
    return False


def capture():
    from iron_bottom_sound.engine import IronBottomEngine
    from iron_bottom_sound.models import GameOptions, Phase, Side
    from iron_bottom_sound.tactical import PROFILES, TacticalCommander
    snap_dir = OUT / "snapshots"
    snap_dir.mkdir(exist_ok=True)
    manifest = []
    for scenario in SCENARIOS:
        counts = {"movement": 0, "gunnery": 0, "torpedo": 0}
        for pair_i, (axis_p, allies_p) in enumerate(
                [("balanced", "balanced"), ("fleet", "line"), ("brawl", "cautious")]):
            for seed in range(1, 9):
                if all(counts[k] >= SNAP_CAPS[k] for k in counts):
                    break
                eng = IronBottomEngine()
                st = eng.reset(scenario, seed, GameOptions(mode="llm"))
                se = {Side.AXIS: TacticalCommander(profile=PROFILES[axis_p]),
                      Side.ALLIES: TacticalCommander(profile=PROFILES[allies_p])}
                guard = 0
                while st.phase != Phase.COMPLETE and guard < 300:
                    guard += 1
                    layer = {Phase.MOVEMENT_PLANNING: "movement",
                             Phase.GUNNERY: "gunnery",
                             Phase.TORPEDO_PLANNING: "torpedo"}.get(st.phase)
                    if layer and counts[layer] < SNAP_CAPS[layer]:
                        for side in Side:
                            # per-profile commander batches for this state
                            cmds = {}
                            ok_profiles = True
                            for prof in POLICY_POOL:
                                try:
                                    e2 = IronBottomEngine()
                                    e2.games[st.game_id] = st
                                    c = TacticalCommander(profile=PROFILES[prof])
                                    _, b, _ = c.choose_plan(e2, st.game_id, side)
                                    cmds[prof] = b
                                except Exception:
                                    ok_profiles = False
                                    break
                            if not ok_profiles:
                                continue
                            if layer == "movement":
                                plans = {p: {o.ship_id: o.plan for o in b.movement}
                                         for p, b in cmds.items()}
                                cands = movement_candidates_for(eng, st, side, plans)
                            elif layer == "gunnery":
                                cands = gunnery_candidates_for(eng, st, side, cmds)
                            else:
                                cands = torpedo_candidates_for(eng, st, side, cmds)
                            if len(cands) < 4:
                                continue
                            sid = (f"{scenario}_s{seed}_{axis_p}-{allies_p}"
                                   f"_t{st.turn}_{side.value}_{layer}")
                            with gzip.open(snap_dir / f"{sid}.json.gz", "wb") as fh:
                                fh.write(json.dumps({
                                    "snapshot_id": sid, "scenario": scenario,
                                    "seed": seed, "turn": st.turn,
                                    "phase": st.phase.value, "side": side.value,
                                    "layer": layer,
                                    "axis_profile": axis_p, "allies_profile": allies_p,
                                    "state": st.model_dump_json(),
                                    "candidates": {n: (b.model_dump_json()
                                                       if hasattr(b, "model_dump_json")
                                                       else json.dumps(b))
                                                   for n, b in cands.items()},
                                }).encode())
                            manifest.append({"snapshot_id": sid, "layer": layer,
                                             "scenario": scenario,
                                             "n_candidates": len(cands)})
                            counts[layer] += 1
                    if st.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                                    Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                                    Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
                        for side in Side:
                            if side.value not in st.submitted_orders:
                                b = se[side].choose_plan(eng, st.game_id, side)[1]
                                res = eng.submit_orders(st.game_id, b)
                                if not res.valid:
                                    break
                    eng.advance(st.game_id)
        print(f"{scenario}: {counts}", flush=True)
    (OUT / "metrics" / "snapshot_manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"total snapshots: {len(manifest)}")


if __name__ == "__main__":
    capture()
