"""M2.1 E0: scripted-evaluator leverage census.

For each snapshot x candidate action: apply the candidate, script both sides
with the source profile pair to the horizon, and record the U0/U1/U2/U3 panel
at each horizon point (H0 end-of-turn, H1, H2, terminal when reachable).

Lambda9010(s) = Q90{Q_E(s,a)} - Q10{Q_E(s,a)} over candidates, computed on
U1 (primary) and U0 (alongside). R=5 matched-seed replicates (rng_counter
offsets). Bootstrap CI per state.

    PYTHONPATH=backend/src:research/m2_1/scripts .venv/bin/python \
        research/m2_1/scripts/e0_scripted.py eval [--limit N]
"""

from __future__ import annotations

import argparse
import gzip
import json
import random
import statistics
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "backend" / "src"))
OUT = REPO / "research" / "m2_1"
REPS = 5


def _utility_panel(st, side, horizon_turn0):
    from iron_bottom_sound.models import Phase, Side
    other = Side.ALLIES if side == Side.AXIS else Side.AXIS
    if st.phase == Phase.COMPLETE:
        u0 = 1.0 if st.winner == side else (-1.0 if st.winner else 0.0)
    else:
        m = st.score[side.value] - st.score[other.value]
        u0 = max(-1.0, min(1.0, m / 10.0))
    my_vp = sum((s.vp if s.sunk else s.vp * (s.hull / s.max_hull if s.hull and s.max_hull else 1.0))
                for s in st.ships.values() if s.side == side)
    en_vp = sum((s.vp if s.sunk else s.vp * (s.hull / s.max_hull if s.hull and s.max_hull else 1.0))
                for s in st.ships.values() if s.side != side)
    tot = my_vp + en_vp
    u1 = (en_vp - my_vp) / tot if tot > 0 else 0.0
    return {"U0": u0, "U1": u1}


def _material_now(st, side):
    """U1 sampled immediately after the candidate's own phase resolution (the
    damage the candidate itself caused, before any scripted counter-play)."""
    my_vp = sum((s.vp if s.sunk else s.vp * (s.hull / s.max_hull if s.hull and s.max_hull else 1.0))
                for s in st.ships.values() if s.side == side)
    en_vp = sum((s.vp if s.sunk else s.vp * (s.hull / s.max_hull if s.hull and s.max_hull else 1.0))
                for s in st.ships.values() if s.side != side)
    tot = my_vp + en_vp
    return (en_vp - my_vp) / tot if tot > 0 else 0.0


def eval_snapshot(path_str: str, horizons=(0, 1, 2), reps=REPS):
    import gzip as _gz
    from iron_bottom_sound.engine import IronBottomEngine
    from iron_bottom_sound.models import (GameState, OrderBatch, Phase, Side)
    from iron_bottom_sound.tactical import PROFILES, TacticalCommander
    path = Path(path_str)
    rec = json.loads(_gz.decompress(path.read_bytes()).decode())
    st0 = GameState.model_validate_json(rec["state"])
    side = Side(rec["side"])
    layer = rec["layer"]
    axis_p, allies_p = rec["axis_profile"], rec["allies_profile"]
    sessions_prof = {
        Side.AXIS: TacticalCommander(profile=PROFILES[axis_p]),
        Side.ALLIES: TacticalCommander(profile=PROFILES[allies_p]),
    }

    def run(state0, cand_json, rep, max_extra_turns):
        """Apply candidate (if any), script to horizon; return per-horizon panel
        plus the intra-turn instant material sample (h1 = 'own-phase effect')."""
        st = state0.model_copy(deep=True)
        st.rng_counter = state0.rng_counter + rep
        eng = IronBottomEngine()
        eng.games[st.game_id] = st
        instant = None
        if cand_json is not None:
            parsed = json.loads(cand_json)
            if isinstance(parsed, dict) and layer == "movement":
                # dict form: {ship_id: plan} -> build MovementOrders with engine costs
                from iron_bottom_sound.models import MovementOrder
                batch = OrderBatch(side=side, phase=Phase.MOVEMENT_PLANNING)
                c = eng.movement_candidates
                for ship_id, plan in parsed.items():
                    ship = st.ships.get(ship_id)
                    if ship is None or ship.sunk or not ship.position:
                        continue
                    cost = None
                    info = c(st, ship, include_plans=True)
                    for entry in info.get("reachable", []):
                        if entry.get("plan") == plan:
                            cost = entry.get("cost", entry.get("speed", 0))
                            break
                    batch.movement.append(MovementOrder(ship_id=ship_id, plan=plan, speed=cost))
            else:
                batch = OrderBatch.model_validate_json(cand_json)
                batch.side = side
                batch.phase = Phase(layer)
            if not eng.validate_orders(st.game_id, batch).valid:
                return None
            eng.submit_orders(st.game_id, batch)
            # resolve the candidate's own phase to capture its immediate effect
            # (mirror of advance()): seal BOTH sides' submitted orders first —
            # resolve_* reads only sealed batches (F7). For gunnery snapshots the
            # opposing side has not submitted yet, so we script their batch too.
            if layer == "gunnery":
                other = Side.ALLIES if side == Side.AXIS else Side.AXIS
                if other.value not in st.submitted_orders:
                    sessions_prof[other].choose_plan(eng, st.game_id, other)
                eng._seal_orders(st)
                st.phase = Phase.TORPEDO_EFFECTS
                eng._resolve_gunnery(st)
                eng._resolve_torpedoes(st)
                instant = _material_now(st, side)
        panels = {}
        turn0 = st.turn
        guard = 0
        for h in horizons:
            target_turn = turn0 + h
            while st.phase != Phase.COMPLETE and st.turn < target_turn and guard < 160:
                guard += 1
                if st.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                                Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                                Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
                    for s in Side:
                        if s.value not in st.submitted_orders:
                            b = sessions_prof[s].choose_plan(eng, st.game_id, s)[1]
                            res = eng.submit_orders(st.game_id, b)
                            if not res.valid:
                                return None
                eng.advance(st.game_id)
            panels[h] = _utility_panel(st, side, turn0)
            if instant is not None:
                panels[h]["U1_instant"] = instant
            if st.phase == Phase.COMPLETE:
                for hh in horizons:
                    panels.setdefault(hh, panels[h])
                break
        return panels

    # per-candidate per-replicate panel trajectories
    cand_jsons = {"__baseline__": None}
    for name, cj in rec["candidates"].items():
        cand_jsons[name] = cj
    per_cand = {}
    for name, cj in cand_jsons.items():
        reps_panels = []
        for rep in range(reps):
            p = run(st0, cj, rep, max(horizons))
            if p is None:
                break
            reps_panels.append(p)
        if len(reps_panels) >= 3:
            per_cand[name] = {
                h: {
                    "U0": statistics.mean(p[h]["U0"] for p in reps_panels),
                    "U1": statistics.mean(p[h]["U1"] for p in reps_panels),
                    **({"U1_instant": statistics.mean(p[h]["U1_instant"] for p in reps_panels
                                                 if "U1_instant" in p[h])}
                       if any("U1_instant" in p[h] for p in reps_panels) else {}),
                } for h in horizons
            }
    # per-layer filtering: only same-layer candidates matter (baseline always)
    out = {"snapshot_id": rec["snapshot_id"], "scenario": rec["scenario"],
           "layer": layer, "turn": rec["turn"], "side": rec["side"],
           "candidates": per_cand}
    return out


def lambda9010(values):
    if len(values) < 2:
        return None, None, None
    s = sorted(values)
    def q(p):
        idx = p * (len(s) - 1)
        lo = int(idx)
        hi = min(lo + 1, len(s) - 1)
        frac = idx - lo
        return s[lo] * (1 - frac) + s[hi] * frac
    return q(0.9) - q(0.1), (s[-1] - s[0]), (s[-1] - s[-2] if len(s) >= 2 else 0.0)


def bootstrap_ci(values, stat=lambda v: v, n=1000, seed=11):
    if len(values) < 2:
        return None
    rng = random.Random(seed)
    stats = []
    for _ in range(n):
        sample = [rng.choice(values) for _ in values]
        s = sorted(sample)
        idx90 = 0.9 * (len(s) - 1)
        idx10 = 0.1 * (len(s) - 1)
        lo = int(idx90); hi = min(lo + 1, len(s) - 1)
        q90 = s[lo] * (1 - (idx90 - lo)) + s[hi] * (idx90 - lo)
        lo2 = int(idx10); hi2 = min(lo2 + 1, len(s) - 1)
        q10 = s[lo2] * (1 - (idx10 - lo2)) + s[hi2] * (idx10 - lo2)
        stats.append(q90 - q10)
    stats.sort()
    return (stats[int(0.05 * n)], stats[int(0.95 * n)])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    snap_dir = OUT / "snapshots"
    paths = sorted(str(q) for q in snap_dir.glob("*.json.gz"))
    if args.limit:
        paths = paths[:args.limit]
    print(f"E0: {len(paths)} snapshots", flush=True)
    t0 = time.time()
    results = []
    for i, p in enumerate(paths):
        try:
            r = eval_snapshot(p)
        except Exception as exc:  # noqa: BLE001
            r = {"snapshot_id": Path(p).stem, "error": f"{type(exc).__name__}: {exc}"}
        results.append(r)
        if (i + 1) % 5 == 0:
            print(f"  {i+1}/{len(paths)} ({time.time()-t0:.0f}s)", flush=True)
    (OUT / "metrics" / "e0_raw.json").write_text(json.dumps(results))
    # aggregate per (layer, scenario)
    summary = {}
    for layer in ("movement", "gunnery", "torpedo"):
        for scen in ("IBS-S-01", "IBS-S-03", "IBS-S-EM-01"):
            lam = []
            details = []
            for r in results:
                if r.get("error") or r["layer"] != layer or r["scenario"] != scen:
                    continue
                for h in (0, 1, 2):
                    vals = [c[h]["U1"] for c in r["candidates"].values() if h in c]
                    if len(vals) >= 3:
                        l9010, lrange, top2 = lambda9010(vals)
                        lam.append({"snapshot_id": r["snapshot_id"], "h": h,
                                    "lambda9010": l9010, "range": lrange,
                                    "top2": top2,
                                    "ci": bootstrap_ci(vals)})
            if lam:
                central = [x["lambda9010"] for x in lam if x["lambda9010"] is not None]
                summary[f"{layer}/{scen}"] = {
                    "n_state_horizons": len(central),
                    "median_lambda": statistics.median(central),
                    "p75": sorted(central)[int(0.75 * len(central))],
                    "p90": sorted(central)[int(0.90 * len(central))],
                    "frac_ge_005": sum(1 for x in central if x >= 0.05) / len(central),
                    "frac_ge_010": sum(1 for x in central if x >= 0.10) / len(central),
                    "frac_ge_020": sum(1 for x in central if x >= 0.20) / len(central),
                }
    (OUT / "metrics" / "e0_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
