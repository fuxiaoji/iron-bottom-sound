"""E2-T2 + T3: real counterfactual continuations for influence-changed decisions.

For sampled states where the Hybrid top action differs from the Direct top
action (non-degenerate direct ranking), re-run the deterministic match to the
same TORPEDO_PLANNING state, then roll out three arms with common random
numbers (5 dice-stream replicates each):

  direct    the Direct-only top candidate
  hybrid    the true Hybrid top candidate (expected_hits + 1.0 * influence)
  shuffled  the Hybrid top after permuting influence composites across the
            state's candidates (causal ablation; E2-T3)

Terminal value = game outcome from the deciding side's perspective (+1 win /
0 draw / -1 loss), scripted play afterwards, both sides on the same profile.

    PYTHONPATH=backend/src:research/m1_5/scripts .venv/bin/python \
        research/m1_5/scripts/e2_t2_rollout.py
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "backend" / "src"))

OUT = REPO / "research" / "m1_5"
REPS = 5
N_STATES = 48  # 12 per (scenario x profile-block), spread


def select_states():
    rows = list(csv.DictReader((OUT / "metrics" / "e2_t1_rows.csv").open()))
    changed = [r for r in rows if r["hybrid_changes_top"] == "True"
               and r["direct_degenerate"] == "False"]
    picked = []
    per = max(1, N_STATES // 10)
    for scen in ("IBS-S-01", "IBS-S-03"):
        for prof in ("adaptive", "direct_attack", "area_denial",
                     "break_crossing_t", "crossfire"):
            cand = [r for r in changed if r["scenario"] == scen and r["profile"] == prof]
            picked += cand[:per]
    return picked[:N_STATES]


def load_or_build_states(picked):
    """Re-run the deterministic matches and persist the selected decision states."""
    states_path = OUT / "metrics" / "e2_t2_states.json"
    if states_path.exists():
        return json.loads(states_path.read_text())
    import gzip
    from iron_bottom_sound.engine import IronBottomEngine
    from iron_bottom_sound.models import GameOptions, Phase, Side
    from iron_bottom_sound.tactical import PROFILES, TacticalCommander
    keys = {(r["scenario"], int(r["seed"]), int(r["turn"]), r["side"], r["profile"])
            for r in picked}
    found = {}
    by_match = {}
    for (scenario, seed, turn, side, profile) in sorted(keys):
        by_match.setdefault((scenario, seed, profile), []).append((turn, side))
    for (scenario, seed, profile), wants in sorted(by_match.items()):
        eng = IronBottomEngine()
        state = eng.reset(scenario, seed, GameOptions(mode="llm"))
        sessions = {Side.AXIS: TacticalCommander(profile=PROFILES[profile]),
                    Side.ALLIES: TacticalCommander(profile=PROFILES[profile])}
        guard = 0
        remaining = list(wants)
        while state.phase != Phase.COMPLETE and guard < 200 and remaining:
            guard += 1
            if state.phase == Phase.TORPEDO_PLANNING:
                for side in Side:
                    for (t, s) in list(remaining):
                        if t == state.turn and s == side.value:
                            found[(scenario, seed, t, s, profile)] = \
                                state.model_copy(deep=True).model_dump_json()
                            remaining.remove((t, s))
            if state.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                               Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                               Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
                for side in Side:
                    if side.value not in state.submitted_orders:
                        batch = sessions[side].choose_plan(
                            eng, state.game_id, side)[1]
                        eng.submit_orders(state.game_id, batch)
            eng.advance(state.game_id)
        print(f"  {scenario} s{seed} {profile}: {len(wants)-len(remaining)}/{len(wants)}",
              flush=True)
    payload = {json.dumps(k): v for k, v in found.items()}
    states_path.write_text(json.dumps(payload))
    return payload


def _rollout(state_json, batch_json, side_value, profile, rep):
    import sys as _sys
    _sys.path.insert(0, str(REPO / "backend" / "src"))
    from iron_bottom_sound.engine import IronBottomEngine
    from iron_bottom_sound.models import (GameOptions, OrderBatch, Phase, Side,
                                          GameState, TorpedoOrder)
    from iron_bottom_sound.tactical import PROFILES, TacticalCommander
    st = GameState.model_validate_json(state_json)
    st.rng_counter = st.rng_counter + rep
    eng = IronBottomEngine()
    eng.games[st.game_id] = st
    batch = OrderBatch.model_validate_json(batch_json)
    batch.side = Side(side_value)
    batch.phase = Phase.TORPEDO_PLANNING
    if not eng.validate_orders(st.game_id, batch).valid:
        return {"outcome": None, "error": "candidate rejected"}
    eng.submit_orders(st.game_id, batch)
    sessions = {Side.AXIS: TacticalCommander(profile=PROFILES[profile]),
                Side.ALLIES: TacticalCommander(profile=PROFILES[profile])}
    deciding = Side(side_value)
    guard = 0
    try:
        while st.phase != Phase.COMPLETE:
            guard += 1
            if guard > 300:
                return {"outcome": None, "error": "guard"}
            if st.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                            Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                            Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
                for side in Side:
                    if side.value not in st.submitted_orders:
                        b = sessions[side].choose_plan(eng, st.game_id, side)[1]
                        eng.submit_orders(st.game_id, b)
            eng.advance(st.game_id)
        mine = st.score[deciding.value]
        other = Side.AXIS if deciding == Side.ALLIES else Side.ALLIES
        theirs = st.score[other.value]
        outcome = 0.0
        if st.winner is not None:
            outcome = 1.0 if st.winner == deciding else -1.0
        return {"outcome": outcome, "vp_margin": mine - theirs, "turns": st.turn,
                "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"outcome": None, "error": f"{type(exc).__name__}: {exc}"}


def eval_state(job):
    import gzip
    import sys as _sys
    _sys.path.insert(0, str(REPO / "backend" / "src"))
    from iron_bottom_sound.models import (OrderBatch, Phase, Side, TorpedoOrder)
    key_str, state_json, decision = job
    key = tuple(json.loads(key_str))
    scenario, seed, turn, side_value, profile = key
    opts = decision["options"]
    import csv as _csv
    row = None
    for r in _csv.DictReader((OUT / "metrics" / "e2_t1_rows.csv").open()):
        if (r["scenario"] == scenario and int(r["turn"]) == turn
                and r["side"] == side_value and r["profile"] == profile
                and r["seed"] == str(seed)):
            row = r
            break
    if row is None:
        return {"key": key_str, "error": "no row"}
    top_direct, top_hybrid = row["top_direct"], row["top_hybrid"]
    opt_by_id = {o["option_id"]: o for o in opts}

    def make_batch(option_id):
        o = opt_by_id[option_id]
        tor = TorpedoOrder.model_validate(o["order"])
        b = OrderBatch(side=Side(side_value), phase=Phase.TORPEDO_PLANNING)
        b.torpedoes = [tor]
        return b.model_dump_json()

    # shuffled hybrid: permute influence composites across candidates (T3)
    comps = [o["influence_composite"] for o in opts]
    import random
    rng = random.Random(hash(key_str) % (2**32))
    shuf = comps[:]
    rng.shuffle(shuf)
    eh = {o["option_id"]: o["expected_hits"] for o in opts}
    id_by_idx = [o["option_id"] for o in opts]
    hybrid_shuffled_id = max(
        range(len(opts)),
        key=lambda i: (-(eh[id_by_idx[i]] + shuf[i]), id_by_idx[i]))

    arms = {
        "direct": make_batch(top_direct),
        "hybrid": make_batch(top_hybrid),
        "shuffled": make_batch(id_by_idx[hybrid_shuffled_id]),
    }
    out = {"key": key_str, "scenario": scenario, "profile": profile,
           "turn": turn, "side": side_value, "arms": {}}
    for arm, bjson in arms.items():
        vals = []
        for rep in range(REPS):
            r = _rollout(state_json, bjson, side_value, profile, rep)
            vals.append(r)
        ok = [v["outcome"] for v in vals if v["error"] is None]
        out["arms"][arm] = {
            "outcome_mean": statistics.mean(ok) if ok else None,
            "outcome_se": (statistics.pstdev(ok) / len(ok) ** 0.5) if len(ok) > 1 else 0.0,
            "n_ok": len(ok),
            "errors": [v["error"] for v in vals if v["error"] is not None][:2],
        }
    return out


def main() -> int:
    picked = select_states()
    print(f"selected {len(picked)} changed states", flush=True)
    states = load_or_build_states(picked)
    decisions = json.loads((OUT / "metrics" / "e2_t1_decisions.json").read_text())
    dec_by = {(d["scenario"], d["seed"], d["turn"], d["side"], d["profile"]): d
              for d in decisions}
    jobs = []
    for r in picked:
        key = (r["scenario"], int(r["seed"]), int(r["turn"]), r["side"], r["profile"])
        ks = json.dumps(list(key))
        if ks not in states:
            continue
        d = dec_by.get(key)
        if d is None:
            continue
        jobs.append((ks, states[ks], d))
    print(f"rolling out {len(jobs)} states x 3 arms x {REPS} reps", flush=True)
    t0 = time.time()
    results = []
    with ProcessPoolExecutor(max_workers=10) as ex:
        for i, res in enumerate(ex.map(eval_state, jobs)):
            results.append(res)
            if (i + 1) % 10 == 0:
                print(f"  {i+1}/{len(jobs)} ({time.time()-t0:.0f}s)", flush=True)
    def complete(r):
        return ("error" not in r and all(
            r["arms"][a]["outcome_mean"] is not None
            for a in ("direct", "hybrid", "shuffled")))
    ok = [r for r in results if complete(r)]
    incomplete = [r for r in results if not complete(r)]
    summary = {"n_states": len(results), "n_complete": len(ok), "reps": REPS,
               "n_incomplete": len(incomplete),
               "incomplete_examples": [
                   {"key": r.get("key"), "arms": {a: r["arms"][a].get("errors")
                    for a in r.get("arms", {})}}
                   for r in incomplete[:6]]}
    # persist per-state results BEFORE any aggregate so failures stay visible
    with (OUT / "metrics" / "e2_t2_states_rollout.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["scenario", "seed", "turn", "side", "profile", "complete",
                    "direct_outcome", "hybrid_outcome", "shuffled_outcome"])
        for r, j in zip(results, jobs):
            key = json.loads(j[0])
            row = key + [complete(r)]
            for a in ("direct", "hybrid", "shuffled"):
                row.append((r.get("arms", {}).get(a, {}) or {}).get("outcome_mean"))
            w.writerow(row)
    for a, b in (("hybrid", "direct"), ("hybrid", "shuffled"), ("shuffled", "direct")):
        diffs = [r["arms"][a]["outcome_mean"] - r["arms"][b]["outcome_mean"] for r in ok]
        if not diffs:
            summary[f"{a}_vs_{b}"] = {"mean_diff": None, "note": "no complete states"}
            continue
        wins = sum(1 for d in diffs if d > 1e-9)
        losses = sum(1 for d in diffs if d < -1e-9)
        summary[f"{a}_vs_{b}"] = {
            "mean_diff": statistics.mean(diffs),
            "median_diff": statistics.median(diffs),
            "win_loss_tie": [wins, losses, len(diffs) - wins - losses],
            "mean_relative_improvement": (statistics.mean(
                d / max(1e-9, abs(r["arms"][b]["outcome_mean"]))
                for d, r in zip(diffs, ok)) if a == "hybrid" and b == "direct" else None),
        }
    # per scenario
    for scen in ("IBS-S-01", "IBS-S-03"):
        sub = [r for r in ok if r["scenario"] == scen]
        if sub:
            diffs = [r["arms"]["hybrid"]["outcome_mean"] - r["arms"]["direct"]["outcome_mean"]
                     for r in sub]
            summary[f"hybrid_vs_direct_{scen}"] = {
                "n": len(sub), "mean_diff": statistics.mean(diffs),
                "median_diff": statistics.median(diffs),
                "wins": sum(1 for d in diffs if d > 1e-9)}
    (OUT / "metrics" / "e2_t2_rollout.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
