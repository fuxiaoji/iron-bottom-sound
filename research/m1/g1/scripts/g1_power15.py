"""Power extension: 15 dice-stream replicates for ALL evaluable pairs.

Amendment (pre-registered before this run's results were inspected, see
EXPERIMENT_REGISTRY.csv row G1-POWER-002): the 5-replicate pilot could not
satisfy the pre-declared CI rule for 104/120 evaluable pairs (power wall,
FAILURES F2). This run increases replicates uniformly and outcome-blind to 15
for every evaluable pair (main and control-B), leaving pairs, candidate sets,
value functions and the CI rule frozen.
"""
import json, statistics, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import g1_lab as L
REPS = 15

def eval_pair_15(rec):
    cands = [c for c in rec["candidates"] if c["valid_a"] and c["valid_b"]]
    if len(cands) < 2:
        return None
    states = {}
    for tag in ("A", "B"):
        import gzip
        states[tag] = gzip.open(L.OUT / "states" / f"{rec['pair_id']}_{tag}.json.gz",
                                "rb").read().decode()
    Q = {"A": [], "B": []}
    for ci, c in enumerate(cands):
        for tag in ("A", "B"):
            vals = [L.eval_branch_state(states[tag], c["batch"], j) for j in range(REPS)]
            ok = [v for v in vals if v["error"] is None]
            row = {"ci": ci, "errors": [v["error"] for v in vals if v["error"]][:2]}
            for key in ("outcome", "damage_diff"):
                xs = [v[key] for v in ok]
                row[f"{key}_mean"] = statistics.mean(xs) if xs else None
                row[f"{key}_se"] = (statistics.pstdev(xs) / len(xs) ** 0.5
                                    if len(xs) > 1 else 0.0)
            row["n_ok"] = len(ok)
            Q[tag].append(row)
    # control A determinism: repeat one cell
    import g1_driver as D
    r1 = L.eval_branch_state(states["A"], cands[0]["batch"], 0)
    r2 = L.eval_branch_state(states["A"], cands[0]["batch"], 0)
    ctl_a = (max(abs(r1[k] - r2[k]) for k in ("outcome", "damage_diff"))
             if r1["error"] is None and r2["error"] is None else None)
    return {"pair_id": rec["pair_id"], "Q": Q, "control_a_max_diff": ctl_a,
            "n_candidates_shared": len(cands)}

def main():
    lines = [json.loads(l) for l in (L.OUT / "IBS_ALIAS_PAIRS.jsonl").open()]
    todo = [r for r in lines if r["public_obs_equal"] and r["legal_actions_equal"]
            and r["own_sealed_equal"] and r["n_candidates_shared"] >= 2
            and len([c for c in r["candidates"] if c["valid_a"] and c["valid_b"]]) >= 2]
    print(f"POWER15: {len(todo)} pairs x 2 branches x ~4.5 cands x {REPS} reps",
          flush=True)
    t0 = time.time()
    out = {}
    with ProcessPoolExecutor(max_workers=10) as ex:
        for i, res in enumerate(ex.map(eval_pair_15, todo)):
            if res is not None:
                out[res["pair_id"]] = res
            if (i + 1) % 10 == 0:
                print(f"  {i+1}/{len(todo)} ({time.time()-t0:.0f}s)", flush=True)
    (L.OUT / "g1_power15.json").write_text(json.dumps(out, indent=1))
    print(f"DONE {len(out)} pairs in {time.time()-t0:.0f}s")

if __name__ == "__main__":
    main()
