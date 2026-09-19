"""Track A: snapshot capture + candidate partitions + oracle evaluation.

Stage 1 (this script): capture movement-planning snapshots from classic
matches, build candidate partitions P0..P8, and evaluate V_H for
(flat, each candidate) with CRN dice-stream replicates per PRE_REGISTRATION_A.

Run:
  capture : build snapshots + persist partition candidates
  eval    : evaluate partition values
"""
from __future__ import annotations

import gzip
import json
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO / "research" / "m2_0" / "scripts"))

OUT = REPO / "research" / "m2_0"

from iron_bottom_sound.engine import IronBottomEngine  # noqa: E402

# ---- frozen knobs (PRE_REGISTRATION_A) ------------------------------------
SCENARIOS = ("IBS-S-01", "IBS-S-03")
PROFILE_PAIRS = (("balanced", "balanced"), ("fleet", "line"), ("brawl", "cautious"))
SEEDS = tuple(range(1, 11))
SNAP_CAP_PER_SCENARIO = 30  # A-MECH-03 fallback
H = 1
REPS = 5
EPSILON = 0.05
MAX_CANDS = 7          # macro budget per group
RANDOM_K_DRAWS = 3


# --------------------------------------------------------------------------
# capture
# --------------------------------------------------------------------------


def ship_row(s):
    return {"id": s.id, "type": s.ship_type, "hp": s.hull, "max_hp": s.max_hull,
            "pos": s.position.label if s.position else None,
            "heading": s.heading, "speed": s.current_speed, "vp": s.vp,
            "sunk": s.sunk}


def build_candidates(st, side):
    """P0..P8 candidate partitions over the alive own ships."""
    from research_group_executor import _plans_for
    eng = IronBottomEngine()
    eng.games[st.game_id] = st
    ships = [s for s in st.ships.values()
             if s.side == side and not s.sunk and s.position]
    ids = [s.id for s in ships]
    by_id = {s.id: s for s in ships}
    cands = {}

    def add(name, groups):
        groups = tuple(tuple(g) for g in groups if g)
        cands[name] = groups

    # P0 flat
    add("P0_flat", [(i,) for i in ids])
    # P1 fixed: nearest-neighbour chains by scenario default? classic has no
    # formations; the plan says "当前/默认 formation template". In classic there
    # is none, so P1 = contiguous ID-ordered chunks of size ceil(N/4) capped at
    # 4 groups — the natural "doctrine" template (4 groups, like realistic cap).
    k = max(1, min(4, (len(ids) + 3) // 4))
    add("P1_fixed", [ids[i:i + k] for i in range(0, len(ids), k)])
    # P2 type
    types = {}
    for s in ships:
        types.setdefault(s.ship_type, []).append(s.id)
    add("P2_type", list(types.values()))
    # P3 speed-compatible: cluster by legal speed interval overlap
    intervals = {}
    for s in ships:
        info = eng.movement_candidates(st, s, include_plans=False)
        lo = info.get("min_cost", 0)
        hi = info.get("max_cost", 0)
        intervals.setdefault((lo, hi), []).append(s.id)
    add("P3_speed", list(intervals.values()))
    # P4 spatial: sort by (q, r) and cut into k contiguous chunks
    ordered = sorted(ids, key=lambda i: (by_id[i].position.q, by_id[i].position.r))
    add("P4_spatial", [ordered[i:i + k] for i in range(0, len(ordered), k)])
    # P5 damage-aware split: damaged (hull < 60%) split out as singletons
    groups5 = [list(g) for g in cands["P1_fixed"]]
    split_out = []
    new5 = []
    for g in groups5:
        keep, out = [], []
        for i in g:
            s = by_id[i]
            (out if (s.hull is not None and s.max_hull and s.hull / s.max_hull < 0.6)
             else keep).append(i)
        if keep:
            new5.append(keep)
        split_out += [[i] for i in out]
    add("P5_damage_split", new5 + split_out)
    # P6 threat-aware: split ships by half-plane relative to nearest enemy
    enemies = [s for s in st.ships.values()
               if s.side != side and not s.sunk and s.position]
    if enemies:
        import statistics as _s
        ex = _s.mean(e.position.q for e in enemies)
        left, right = [], []
        for s in ships:
            (left if s.position.q <= ex else right).append(s.id)
        if left and right:
            add("P6_threat_split", [left, right])
    # P7 one-step neighbors of P1: split each group once
    base = [list(g) for g in cands["P1_fixed"]]
    for gi, g in enumerate(base):
        if len(g) < 2:
            continue
        for hi_, h in enumerate(g):
            rest = [x for x in g if x != h]
            add(f"P7_split{gi}_{h}", base[:gi] + [rest, [h]] + base[gi + 1:])
    # P8 random matched-K: 3 draws per structured K (K of P2/P3/P6)
    import random
    rng = random.Random(97)
    ks = sorted({len(v) for name, v in cands.items()
                 if name in ("P2_type", "P3_speed", "P6_threat_split", "P1_fixed")})
    for K in ks:
        if K <= 1 or K >= len(ids):
            continue
        for d in range(RANDOM_K_DRAWS):
            shuffled = ids[:]
            rng.shuffle(shuffled)
            add(f"P8_rand{K}_{d}", [shuffled[i:i + K] for i in range(0, len(shuffled), K)])
    # dedupe
    uniq = {}
    for name, groups in cands.items():
        key = tuple(tuple(g) for g in groups)
        if key not in uniq:
            uniq[key] = name
    return cands, uniq


def capture():
    from iron_bottom_sound.models import GameOptions, Phase, Side
    from iron_bottom_sound.tactical import PROFILES, TacticalCommander
    snap_dir = OUT / "snapshots"
    snap_dir.mkdir(exist_ok=True)
    manifest = []
    for scenario in SCENARIOS:
        n = 0
        for axis_p, allies_p in PROFILE_PAIRS:
            for seed in SEEDS:
                if n >= SNAP_CAP_PER_SCENARIO:
                    break
                eng = IronBottomEngine()
                st = eng.reset(scenario, seed, GameOptions(mode="llm"))
                se = {Side.AXIS: TacticalCommander(profile=PROFILES[axis_p]),
                      Side.ALLIES: TacticalCommander(profile=PROFILES[allies_p])}
                guard = 0
                while st.phase != Phase.COMPLETE and guard < 120 and n < SNAP_CAP_PER_SCENARIO:
                    guard += 1
                    if st.phase == Phase.MOVEMENT_PLANNING:
                        for side in Side:
                            cands, uniq = build_candidates(st, side)
                            if not uniq or len(uniq) < 3:
                                continue
                            sid = f"{scenario}_s{seed}_{axis_p}-{allies_p}_t{st.turn}_{side.value}"
                            with gzip.open(snap_dir / f"{sid}.json.gz", "wb") as fh:
                                fh.write(json.dumps({
                                    "snapshot_id": sid,
                                    "scenario": scenario, "seed": seed,
                                    "axis_profile": axis_p, "allies_profile": allies_p,
                                    "turn": st.turn, "side": side.value,
                                    "state": st.model_dump_json(),
                                    "ships": {s.id: ship_row(s) for s in st.ships.values()},
                                    "candidates": {name: [list(g) for g in groups]
                                                   for groups, name in uniq.items()},
                                    "candidate_count": len(uniq),
                                }, ensure_ascii=False).encode())
                            manifest.append({"snapshot_id": sid, "scenario": scenario,
                                             "seed": seed, "turn": st.turn,
                                             "side": side.value,
                                             "n_candidates": len(uniq)})
                            n += 1
                    if st.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                                    Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                                    Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
                        for side in Side:
                            if side.value not in st.submitted_orders:
                                b = se[side].choose_plan(eng, st.game_id, side)[1]
                                eng.submit_orders(st.game_id, b)
                    eng.advance(st.game_id)
                if n >= SNAP_CAP_PER_SCENARIO:
                    break
        print(f"{scenario}: {n} snapshots", flush=True)
    (OUT / "metrics" / "a_snapshots_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"total {len(manifest)} snapshots")


def load_snap():
    from iron_bottom_sound.models import GameState
    d = gzip.decompress(path.read_bytes()).decode()
    rec = json.loads(d)
    rec["game_state"] = GameState.model_validate_json(rec["state"])
    return rec


# --------------------------------------------------------------------------
# evaluation
# --------------------------------------------------------------------------


def eval_snapshot(path_str: str):
    import gzip as _gz
    import random as _rand
    from iron_bottom_sound.engine import IronBottomEngine
    from iron_bottom_sound.models import GameState, MovementOrder, OrderBatch, Phase, Side
    from iron_bottom_sound.tactical import PROFILES, TacticalCommander
    from research_group_executor import (MacroInvalid, execute_partition,
                                         orders_to_batch, plan_for_macro,
                                         _plans_for)
    path = Path(path_str)
    rec = json.loads(_gz.decompress(path.read_bytes()).decode())
    st0 = GameState.model_validate_json(rec["state"])
    side = Side(rec["side"])
    scenario, profile_pair = rec["scenario"], (rec["axis_profile"], rec["allies_profile"])

    def script_turns(st, eng, turns):
        """Script both sides with TacticalCommander for `turns` turns; return
        utility at end (terminal if game ended)."""
        sessions = {Side.AXIS: TacticalCommander(profile=PROFILES[profile_pair[0]]),
                    Side.ALLIES: TacticalCommander(profile=PROFILES[profile_pair[1]])}
        turn0 = st.turn
        guard = 0
        while st.phase != Phase.COMPLETE and st.turn - turn0 < turns and guard < 300:
            guard += 1
            if st.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                            Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                            Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
                for s in Side:
                    if s.value not in st.submitted_orders:
                        b = sessions[s].choose_plan(eng, st.game_id, s)[1]
                        res = eng.submit_orders(st.game_id, b)
                        if not res.valid:
                            return None
            eng.advance(st.game_id)
        utility = _utility(st, side, turn0)
        return utility

    def _utility(st, side, turn0):
        if st.phase == Phase.COMPLETE:
            if st.winner is None:
                return 0.0
            return 1.0 if st.winner == side else -1.0
        # VP swing normalized (PRE_REGISTRATION: /10 clipped)
        me = st.score[side.value]
        other = side.other() if hasattr(side, "other") else (
            Side.AXIS if side == Side.ALLIES else Side.ALLIES)
        opp = st.score[other.value]
        return max(-1.0, min(1.0, (me - opp) / 10.0))

    def eval_batch(batch_or_none, rep):
        st = st0.model_copy(deep=True)
        st.rng_counter = st0.rng_counter + rep
        eng = IronBottomEngine()
        eng.games[st.game_id] = st
        if batch_or_none is not None:
            if not eng.validate_orders(st.game_id, batch_or_none).valid:
                return None
            eng.submit_orders(st.game_id, batch_or_none)
        return script_turns(st, eng, H)

    # candidate macro sweep per partition: for each group pick the best macro
    # greedily by the SAME CRN replicates (shared eval fn), budget MAX_CANDS.
    def eval_partition(groups):
        # 1) build per-group macro plan tables (lead proposals from commander)
        proposal_map = {}
        for g in groups:
            lead = g[0]
            ship = st0.ships.get(lead)
            if ship is None or ship.sunk or not ship.position:
                continue
            try:
                eng_tmp = IronBottomEngine()
                eng_tmp.games[st0.game_id] = st0
                cmd = TacticalCommander(profile=PROFILES[profile_pair[0] if side == Side.AXIS else profile_pair[1]])
                plan_sheet, batch, _ = cmd.choose_plan(eng_tmp, st0.game_id, side)
                for o in batch.movement:
                    if o.ship_id == lead:
                        # The commander may emit plans outside the candidate
                        # table (its internal logic covers reachable-hex plans
                        # plus chained-command variants). Keep the proposal
                        # only if it IS in the lead's own legal plan table;
                        # otherwise LEADER_PROPOSAL is simply unavailable for
                        # this group (an explicit menu restriction, recorded,
                        # not a silent swap).
                        from research_group_executor import _plans_for
                        if o.plan in _plans_for(eng_tmp, st0, lead):
                            proposal_map[g] = o.plan
                        else:
                            proposal_map[g] = None
                        break
            except Exception:
                proposal_map[g] = None
        # 2) INDEPENDENT macro choice (Amendment A-MECH-01): each group's macro
        #    is scored with all other groups at HOLD; argmax per group. This is
        #    an upper-bound-friendly approximation chosen for tractability; it
        #    is recorded as conservative for the oracle.
        alive_groups = [g for g in groups if any(
            st0.ships[i].position and not st0.ships[i].sunk for i in g)]
        chosen = {g: "HOLD" for g in groups}
        feasible = True
        for g in alive_groups:
            best_macro, best_v = None, None
            for macro in ("HOLD", "STRAIGHT_SLOW", "STRAIGHT_FAST",
                          "TURN_PORT_60", "TURN_STARBOARD_60", "LEADER_PROPOSAL"):
                trial = {h: ("HOLD" if h != g else macro) for h in groups}
                # A-MECH-02: macro selection uses rep=0 only (heuristic
                # pre-selector); the reported partition value below keeps 5 reps.
                try:
                    eng_t = IronBottomEngine()
                    eng_t.games[st0.game_id] = st0
                    gos = execute_partition(eng_t, st0, side, groups,
                                            trial, proposal_map)
                    batch = orders_to_batch(eng_t, st0, side, gos)
                    v = eval_batch(batch, 0)
                    if v is None:
                        continue
                except (MacroInvalid, Exception):
                    continue
                if best_v is None or v > best_v:
                    best_v, best_macro = v, macro
            if best_macro is None:
                feasible = False
                break
            chosen[g] = best_macro
        if not feasible:
            return None
        # final eval with the chosen macro combination (fresh CRN)
        vals = []
        for rep in range(REPS):
            try:
                eng2 = IronBottomEngine()
                eng2.games[st0.game_id] = st0
                gos = execute_partition(eng2, st0, side, groups, chosen, proposal_map)
                batch = orders_to_batch(eng2, st0, side, gos)
                st = st0.model_copy(deep=True)
                st.rng_counter = st0.rng_counter + rep
                eng3 = IronBottomEngine()
                eng3.games[st.game_id] = st
                if not eng3.validate_orders(st.game_id, batch).valid:
                    return None
                eng3.submit_orders(st.game_id, batch)
                v = script_turns(st, eng3, H)
                if v is None:
                    return None
                vals.append(v)
            except MacroInvalid:
                return None
            except Exception:
                return None
        return statistics.mean(vals) if vals else None

    # flat reference
    v_flat = eval_partition([(i,) for i in sorted(
        s.id for s in st0.ships.values()
        if s.side == side and not s.sunk and s.position)])
    out = {"snapshot_id": rec["snapshot_id"], "scenario": rec["scenario"],
           "turn": rec["turn"], "side": rec["side"],
           "n_ships": len([1 for s in st0.ships.values()
                           if s.side == side and not s.sunk and s.position]),
           "v_flat": v_flat, "parts": {}}
    cands = rec["candidates"]
    for name, groups in cands.items():
        groups_t = [tuple(g) for g in groups]
        v = eval_partition(groups_t)
        K = sum(1 for g in groups_t if any(
            st0.ships[i].position and not st0.ships[i].sunk for i in g))
        out["parts"][name] = {"K": K, "value": v}
    return out


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else "capture"
    if stage == "capture":
        capture()
    elif stage == "eval":
        snap_dir = OUT / "snapshots"
        paths = sorted(str(p) for p in snap_dir.glob("*.json.gz"))
        print(f"evaluating {len(paths)} snapshots x ~15 partitions", flush=True)
        t0 = time.time()
        results = []
        with ProcessPoolExecutor(max_workers=10) as ex:
            for i, r in enumerate(ex.map(eval_snapshot, paths)):
                results.append(r)
                if (i + 1) % 5 == 0:
                    print(f"  {i+1}/{len(paths)} ({time.time()-t0:.0f}s)", flush=True)
        (OUT / "metrics" / "a_partition_eval.json").write_text(json.dumps(results))
        print(f"done in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
