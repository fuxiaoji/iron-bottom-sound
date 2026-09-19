"""G1 driver: generate alias pairs, evaluate Q tables, compute regret + controls.

Stages
------
  gen   — run legal matches, build branch A/B per variant, verify hashes,
          persist branch states + pair specs (pairs_gen.jsonl)
  eval  — per pair: shared candidate torpedo batches, CRN dice-stream
          replicates, Q tables, regret R, normalized regret, controls
  report— PAIR_VALIDATION.csv / CONTROL_PAIRS.csv / jsonl / figures

Pre-declared parameters live in g1_lab.py constants.  No result-dependent
filtering is applied before the primary statistics: ALL valid pairs generated
in the pre-declared node grid are evaluated (cap 60 per scenario, taken in
(seed, turn, variant) order — an order fixed before any Q is known).
"""

from __future__ import annotations

import argparse
import copy
import gzip
import json
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import g1_lab as L  # noqa: E402
from iron_bottom_sound.engine import IronBottomEngine  # noqa: E402
from iron_bottom_sound.models import OrderBatch, Phase, Side  # noqa: E402

OUT = L.OUT
LOG = L.LOG
STATES_DIR = OUT / "states"
PAIR_CAP_PER_SCENARIO = 60   # pre-declared, order = (seed, turn, variant)


# --------------------------------------------------------------------------
# stage: gen
# --------------------------------------------------------------------------


def stage_gen() -> None:
    STATES_DIR = OUT / "states"
    STATES_DIR.mkdir(parents=True, exist_ok=True)
    LOG.mkdir(parents=True, exist_ok=True)
    records = []
    failures = []
    t0 = time.time()
    for scenario in L.SCENARIOS:
        n_pairs = 0
        n_controls = 0
        for seed in L.SEEDS:
            if n_pairs >= PAIR_CAP_PER_SCENARIO:
                break
            # one run yields branch nodes at every target turn of this seed
            got = collect_nodes(scenario, seed, failures)
            for node in got:
                for variant in node["variants"]:
                    is_ctl = bool(variant.get("is_control_b"))
                    if not is_ctl and n_pairs >= PAIR_CAP_PER_SCENARIO:
                        break
                    errors = []
                    rec = build_pair(scenario, seed, node, variant, errors)
                    if rec is None:
                        failures.append({"stage": "build_pair", "scenario": scenario,
                                         "seed": seed, "turn": node["turn"],
                                         "errors": errors[:4]})
                        continue
                    # candidate-count filter is outcome-blind (known before any
                    # Q evaluation): pairs with <2 shared candidates cannot yield
                    # a regret and do not consume the pre-declared cap.
                    if sum(1 for c in rec["candidates"]
                           if c["valid_a"] and c["valid_b"]) < 2 and not is_ctl:
                        records.append(rec)
                        continue
                    records.append(rec)
                    if is_ctl:
                        n_controls += 1
                    else:
                        n_pairs += 1
            print(f"  [{scenario} seed={seed}] pairs so far {n_pairs} "
                  f"({time.time()-t0:.0f}s)", flush=True)
    with (OUT / "pairs_gen.jsonl").open("w") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    (OUT / "logs" / "gen_failures.json").write_text(
        json.dumps(failures, indent=2, ensure_ascii=False))
    print(f"GEN: {len(records)} candidate pairs, {len(failures)} failures "
          f"-> pairs_gen.jsonl")


def collect_nodes(scenario: str, seed: int, failures: list) -> list[dict]:
    """One legal match run; at each MOVEMENT_PLANNING turn build variants.

    The match itself continues on the X_A trajectory (branch clones are separate).
    """
    from iron_bottom_sound.tactical import PROFILES
    eng = IronBottomEngine()
    state = eng.reset(scenario, seed, L.GameOptions(mode="llm"))
    sessions = {Side.AXIS: L.TacticalCommander(profile=PROFILES[L.PROFILES[0]]),
                Side.ALLIES: L.TacticalCommander(profile=PROFILES[L.PROFILES[1]])}
    nodes = []
    guard = 0
    while state.phase != Phase.COMPLETE and len(nodes) < len(L.TARGET_TURNS):
        guard += 1
        if guard > L.ADVANCE_GUARD:
            break
        if state.phase == Phase.MOVEMENT_PLANNING and state.turn in L.TARGET_TURNS:
            x_a = sessions[Side.AXIS].choose_plan(eng, state.game_id, Side.AXIS)[1]
            y = sessions[Side.ALLIES].choose_plan(eng, state.game_id, Side.ALLIES)[1]
            pre = state.model_copy(deep=True)
            pre_eng = L.fresh_engine(pre)
            main, control = L.build_variants(pre_eng, pre, x_a, None,
                                             L.MAX_VARIANTS_PER_NODE)
            variants = list(main)
            if control is not None:
                control["is_control_b"] = True
                variants.append(control)
            if variants:
                nodes.append({"turn": state.turn, "pre": pre, "x_a": x_a,
                              "y": y, "variants": variants})
        if state.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                           Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                           Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
            for side in Side:
                if side.value not in state.submitted_orders:
                    batch = sessions[side].choose_plan(eng, state.game_id, side)[1]
                    res = eng.submit_orders(state.game_id, batch)
                    if not res.valid:
                        failures.append({"stage": "gen_submit", "scenario": scenario,
                                         "seed": seed, "errors": res.errors[:3]})
                        return nodes
        eng.advance(state.game_id)
    return nodes


def build_pair(scenario, seed, node, variant, errors) -> dict | None:
    pre = node["pre"]
    branch_a = L.make_branch(pre, node["x_a"], node["y"], errors)
    if branch_a is None:
        return None
    branch_b = L.make_branch(pre, variant["batch"], node["y"], errors)
    if branch_b is None:
        return None
    valid = (branch_a["public_obs_hash"] == branch_b["public_obs_hash"]
             and branch_a["legal_hash"] == branch_b["legal_hash"]
             and branch_a["own_sealed_hash"] == branch_b["own_sealed_hash"])
    pid = (f"{scenario}_s{seed}_t{node['turn']}_{variant['ship_id']}"
           f"_{variant['from_plan']}-{variant['to_plan']}"
           + ("_ctlB" if variant.get("is_control_b") else ""))
    # persist branch states for the eval workers
    for tag, br in (("A", branch_a), ("B", branch_b)):
        with gzip.open(STATES_DIR / f"{pid}_{tag}.json.gz", "wb") as fh:
            fh.write(br["state"].model_dump_json().encode())
    chosen_a = L.commander_torpedo_batch(branch_a["state"])
    chosen_b = L.commander_torpedo_batch(branch_b["state"])
    cands = L.torpedo_candidates(branch_a["engine"], branch_a["state"],
                                 chosen_a, chosen_b)
    cand_specs = []
    for c in cands:
        ok_a = branch_a["engine"].validate_orders(
            branch_a["state"].game_id, c).valid
        ok_b = branch_b["engine"].validate_orders(
            branch_b["state"].game_id, c).valid
        cand_specs.append({"batch": c.model_dump_json(), "valid_a": ok_a,
                           "valid_b": ok_b, "n_torpedoes": len(c.torpedoes)})
    rec = {
        "pair_id": pid,
        "scenario": scenario,
        "seed": seed,
        "turn": node["turn"],
        "phase": "torpedo_planning",
        "public_observation_hash": branch_a["public_obs_hash"],
        "public_obs_equal": branch_a["public_obs_hash"] == branch_b["public_obs_hash"],
        "own_state_hash": branch_a["own_sealed_hash"],
        "own_sealed_equal": branch_a["own_sealed_hash"] == branch_b["own_sealed_hash"],
        "legal_action_hash": branch_a["legal_hash"],
        "legal_actions_equal": branch_a["legal_hash"] == branch_b["legal_hash"],
        "axis_view_differs": branch_a["axis_view_hash"] != branch_b["axis_view_hash"],
        "hidden_commitment_A": {o.ship_id: o.plan for o in node["x_a"].movement},
        "hidden_commitment_B": {o.ship_id: o.plan for o in variant["batch"].movement},
        "variant": {k: variant[k] for k in ("ship_id", "ship_name", "from_plan",
                                            "to_plan", "min_dist_allies")},
        "is_control_b": bool(variant.get("is_control_b")),
        "candidates": cand_specs,
        "c0": branch_a["c0"],
        "errors": errors[:4],
    }
    return rec


# --------------------------------------------------------------------------
# stage: eval
# --------------------------------------------------------------------------


def eval_pair(rec: dict) -> dict:
    out = {"pair_id": rec["pair_id"], "branches": {}, "control_a_max_diff": None}
    cands = [c for c in rec["candidates"] if c["valid_a"] and c["valid_b"]]
    out["n_candidates_shared"] = len(cands)
    out["n_candidates_dropped"] = len(rec["candidates"]) - len(cands)
    branch_states = {}
    for tag in ("A", "B"):
        with gzip.open(OUT / "states" / f"{rec['pair_id']}_{tag}.json.gz", "rb") as fh:
            branch_states[tag] = fh.read().decode()
    # shared candidate evaluations, CRN across branches via same replicate index
    Q = {"A": [], "B": []}
    for ci, c in enumerate(cands):
        for tag in ("A", "B"):
            vals = []
            for j in range(L.REPLICATES):
                r = L.eval_branch_state(branch_states[tag], c["batch"], j)
                vals.append(r)
            ok = [v for v in vals if v["error"] is None]
            errs = [v["error"] for v in vals if v["error"] is not None]
            row = {"ci": ci, "errors": errs[:2]}
            for key in ("outcome", "damage_diff"):
                xs = [v[key] for v in ok]
                row[f"{key}_mean"] = statistics.mean(xs) if xs else None
                row[f"{key}_se"] = (statistics.pstdev(xs) / len(xs) ** 0.5
                                    if len(xs) > 1 else 0.0)
            row["n_ok"] = len(ok)
            Q[tag].append(row)
    # Control A: same branch twice, same stream -> must be identical
    if cands:
        r1 = L.eval_branch_state(branch_states["A"], cands[0]["batch"], 0)
        r2 = L.eval_branch_state(branch_states["A"], cands[0]["batch"], 0)
        if r1["error"] is None and r2["error"] is None:
            diffs = [abs(r1[k] - r2[k]) for k in ("outcome", "damage_diff")]
            out["control_a_max_diff"] = max(diffs)
    out["Q"] = Q
    out["candidate_labels"] = [c["n_torpedoes"] for c in cands]
    return out


def compute_regret(qa, qb, key="outcome"):
    """R = min_a max(V_A - Q_A(a), V_B - Q_B(a)); normalized by decision stake.

    ``key`` selects the value function: "outcome" (primary) or "damage_diff".
    """
    mk = lambda q: q.get(f"{key}_mean")
    sk = lambda q: q.get(f"{key}_se")
    a_ok = [q for q in qa if mk(q) is not None]
    b_ok = [q for q in qb if mk(q) is not None]
    if not a_ok or not b_ok or len(a_ok) != len(qa) or len(b_ok) != len(qb):
        return None
    v_a = max(mk(q) for q in a_ok)
    v_b = max(mk(q) for q in b_ok)
    worst = [max(v_a - mk(x), v_b - mk(y)) for x, y in zip(qa, qb)]
    r = min(worst)
    stake = max(v_a - min(mk(q) for q in a_ok),
                v_b - min(mk(q) for q in b_ok))
    norm = (r / stake) if stake > L.TIE_EPS else 0.0
    arg_a = max(range(len(qa)), key=lambda i: mk(qa[i]))
    arg_b = max(range(len(qb)), key=lambda i: mk(qb[i]))
    sig_a = max(mk(q) for q in a_ok) - min(mk(q) for q in a_ok)
    sig_b = max(mk(q) for q in b_ok) - min(mk(q) for q in b_ok)
    noise_a = max((sk(q) or 0.0) for q in a_ok)
    noise_b = max((sk(q) or 0.0) for q in b_ok)
    confident = (sig_a > 2 * noise_a and sig_b > 2 * noise_b)
    return {"R": r, "stake": stake, "normalized_regret": norm,
            "V_A": v_a, "V_B": v_b,
            "argmax_A": arg_a, "argmax_B": arg_b,
            "argmax_differs": arg_a != arg_b,
            "signal_A": sig_a, "signal_B": sig_b,
            "q_ranking_confident": confident}


def stage_eval() -> None:
    recs = [json.loads(l) for l in (OUT / "pairs_gen.jsonl").open()]
    print(f"EVAL: {len(recs)} candidate pairs x <=6 candidates x "
          f"{L.REPLICATES} replicates x 2 branches", flush=True)
    t0 = time.time()
    results = []
    with ProcessPoolExecutor(max_workers=10) as ex:
        for i, res in enumerate(ex.map(eval_pair, recs)):
            results.append(res)
            if (i + 1) % 10 == 0:
                print(f"  {i+1}/{len(recs)} pairs ({time.time()-t0:.0f}s)",
                      flush=True)
    by_id = {r["pair_id"]: r for r in results}
    # merge + write outputs
    import csv
    rows = []
    controls = []
    pair_lines = []
    for rec in recs:
        res = by_id[rec["pair_id"]]
        merged = {**rec, **{k: res[k] for k in
                            ("n_candidates_shared", "n_candidates_dropped",
                             "control_a_max_diff", "candidate_labels")}}
        reg = None
        reg_dd = None
        if res["n_candidates_shared"] >= 2:
            reg = compute_regret(res["Q"]["A"], res["Q"]["B"], "outcome")
            reg_dd = compute_regret(res["Q"]["A"], res["Q"]["B"], "damage_diff")
        merged["regret"] = reg
        merged["regret_damage_diff"] = reg_dd
        merged["Q"] = res["Q"]
        pair_lines.append(json.dumps(merged, ensure_ascii=False))
        base = {
            "pair_id": rec["pair_id"], "scenario": rec["scenario"],
            "seed": rec["seed"], "turn": rec["turn"],
            "public_equal": rec["public_obs_equal"],
            "own_state_equal": rec["own_sealed_equal"],
            "legal_actions_equal": rec["legal_actions_equal"],
            "reachable": True,
            "hidden_commitment_only_difference": rec["axis_view_differs"],
            "n_candidates_shared": res["n_candidates_shared"],
            "q_ranking_confident": reg["q_ranking_confident"] if reg else None,
            "shared_action_regret": reg["R"] if reg else None,
            "normalized_regret": reg["normalized_regret"] if reg else None,
            "normalized_regret_damage_diff": (reg_dd["normalized_regret"]
                                              if reg_dd else None),
            "argmax_differs": reg["argmax_differs"] if reg else None,
            "control_a_max_diff": res["control_a_max_diff"],
        }
        if rec["is_control_b"]:
            controls.append({**base, "control": "B_distant_ship"})
        else:
            rows.append({**base, "valid_for_primary_analysis":
                         bool(base["public_equal"] and base["own_state_equal"]
                              and base["legal_actions_equal"]
                              and base["n_candidates_shared"] >= 2
                              and reg is not None
                              and (base["control_a_max_diff"] or 0) < L.TIE_EPS)})

    def write_csv(path, rws, fields):
        with path.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            for r in rws:
                w.writerow({k: r.get(k) for k in fields})

    fields = ["pair_id", "scenario", "seed", "turn", "public_equal",
              "own_state_equal", "legal_actions_equal", "reachable",
              "hidden_commitment_only_difference", "n_candidates_shared",
              "q_ranking_confident", "shared_action_regret",
              "normalized_regret", "normalized_regret_damage_diff",
              "argmax_differs", "control_a_max_diff",
              "valid_for_primary_analysis"]
    write_csv(OUT / "PAIR_VALIDATION.csv", rows, fields + ["valid_for_primary_analysis"])
    write_csv(OUT / "CONTROL_PAIRS.csv", controls,
              [f for f in fields if f != "valid_for_primary_analysis"] + ["control"])
    with (OUT / "IBS_ALIAS_PAIRS.jsonl").open("w") as fh:
        for line in pair_lines:
            fh.write(line + "\n")
    print(f"EVAL done in {time.time()-t0:.0f}s -> "
          f"{len(rows)} pairs, {len(controls)} control-B pairs")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["gen", "eval", "all"])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.stage in ("gen", "all"):
        stage_gen()
    if args.stage in ("eval", "all"):
        stage_eval()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
