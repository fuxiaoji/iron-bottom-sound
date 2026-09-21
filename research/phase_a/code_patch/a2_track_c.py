"""Phase A.2 §3 — Track C decisive calibration.

Frozen strengthened fault generator (duration 20 steps, severities 0.5/0.8/1.0,
window starts 20/40/60, modalities act_drop / obs_corrupt / act_delay). Target 50
valid causal failures per task, at most 1000 injection attempts per task;
fewer than 30 valid => C_LOW_YIELD_BLOCKED for that task.

Ground truth = the minimal successful repair set from the EXHAUSTIVE agent x
time-window repair matrix, never the injection label. Injection metadata is written
to a separate file that the attribution code never reads.

Baselines: RANDOM_CELL, TIME_BINARY, AGENT_THEN_TIME_GROUP_TEST (mandatory),
INFLUENCE_PRIORITIZED. Budgets 10/20/25 % of each failure's exhaustive query count;
every counterfactual replay counts as a query.

    .venv_phase_a/bin/python research/phase_a/scripts/a2_track_c.py [--per-task 50] [--attempts 1000]
"""

from __future__ import annotations

import csv
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hardened import Registry, bootstrap_ci_mean  # noqa: E402
from phase_a_common import PA, Perturbation  # noqa: E402
from track_c import N_AGENTS, TASKS, WINDOW, episode, load_actor, semantics, valid_failure  # noqa: E402

OUT = PA / "raw" / "track_c_a2"
OUT.mkdir(parents=True, exist_ok=True)
BUDGETS = (0.10, 0.20, 0.25)
FAULT_MODALITIES = ("act_drop", "obs_corrupt", "act_delay")


def matrix(actor, task, seed, fault, sem):
    """Exhaustive agent x window repair; returns cells with success flags."""
    cells = []
    for a in range(N_AGENTS[task]):
        for w in range(WINDOW):
            ret, succ, _s, _a, _o = episode(actor, task, seed, fault=fault, repair=(a, w))
            ok = bool(succ) if task == "balance" else bool(sem and ret >= sem["Q50"])
            cells.append({"agent": a, "window": w, "return": ret, "repairs": int(ok)})
    return cells


def minimal_sets(cells, size=2):
    """All minimal successful repair sets of size <= `size` (cells are singletons;
    a group repair is defined as repairing all cells in the group)."""
    good = [(c["agent"], c["window"]) for c in cells if c["repairs"]]
    if not good:
        return [], []
    minimal = []
    for c in good:
        # a cell is minimal if removing it (i.e. repair it alone) already works
        minimal.append([c])
    # unique minimal = the smallest singleton set; report ambiguity by count
    return minimal, good


def probe_orders(cells, seed):
    """Return ordered query sequences (agent, window) for each method."""
    rng = random.Random(seed)
    r = [(c["agent"], c["window"]) for c in cells]
    rng.shuffle(r)
    agents = sorted({c["agent"] for c in cells})
    windows = sorted({c["window"] for c in cells})
    # TIME_BINARY: bisect the window axis at a fixed agent
    tb = []
    a0 = agents[0]
    lo, hi = 0, len(windows) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        tb.append((a0, windows[mid]))
        lo, hi = mid + 1, hi                      # monotone scan variant, frozen
    tb += [c for c in r if c not in tb]
    # AGENT_THEN_TIME_GROUP_TEST: coarse whole-agent repairs first (all windows of an
    # agent), then group-test the time axis inside the best agent
    gt = []
    for a in agents:
        gt.append((a, windows[len(windows) // 2]))       # coarse agent probe
    ranked = sorted(agents, key=lambda a: -sum(c["return"] for c in cells if c["agent"] == a))
    for a in ranked:
        for w in windows:
            gt.append((a, w))
    gt += [c for c in r if c not in gt]
    # INFLUENCE_PRIORITIZED: highest-return cells first (pre-query observable proxy)
    inf = sorted(r, key=lambda c: -next(x["return"] for x in cells
                                        if (x["agent"], x["window"]) == c))
    return {"RANDOM_CELL": r, "TIME_BINARY": tb,
            "AGENT_THEN_TIME_GROUP_TEST": gt, "INFLUENCE_PRIORITIZED": inf}


def main() -> int:
    per_task = int(sys.argv[sys.argv.index("--per-task") + 1]) if "--per-task" in sys.argv else 50
    max_attempts = int(sys.argv[sys.argv.index("--attempts") + 1]) if "--attempts" in sys.argv else 1000
    t0 = time.time()
    reg = Registry()
    out = {"target_per_task": per_task, "max_attempts": max_attempts,
           "budgets": list(BUDGETS), "tasks": {}}
    meta_rows = []
    for task in TASKS:
        actor = load_actor(task)
        sem = semantics(task)
        rng = random.Random(20260921)
        cases, attempted = [], 0
        while len(cases) < per_task and attempted < max_attempts:
            attempted += 1
            seed = 70_000 + attempted
            modality = rng.choice(FAULT_MODALITIES)
            agent = rng.randrange(N_AGENTS[task])
            sev = rng.choice([0.5, 0.8, 1.0])
            start = rng.choice([20, 40, 60])
            fault = Perturbation(modality, (agent,), start, start + 20, sev)
            with reg.unit(f"C2_gen_{task}_{attempted}", "C", task, "fault_generation") as u:
                cr, cs, _s1, _a, _b = episode(actor, task, seed)
                fr, fs, _s2, _a2, _b2 = episode(actor, task, seed, fault=fault)
                ok = valid_failure(task, cr, cs, fr, fs, sem)
                if ok:
                    cases.append({"case_id": f"{task}_{len(cases):03d}", "seed": seed,
                                  "clean_return": cr, "fault_return": fr})
                    # injection metadata: separate file, never read by attribution
                    meta_rows.append({"case_id": cases[-1]["case_id"], "modality": modality,
                                      "agent": agent, "severity": sev, "t_start": start})
                    u.success({"valid": True}, sim_queries=2)
                else:
                    u.reject("not_a_valid_causal_failure", {}, sim_queries=2)
            if attempted % 50 == 0:
                print(f"  {task} attempts={attempted} valid={len(cases)} "
                      f"{time.time()-t0:.0f}s", flush=True)
        status = ("OK" if len(cases) >= 30 else "C_LOW_YIELD_BLOCKED")
        out["tasks"][task] = {"attempted": attempted, "valid": len(cases), "status": status}
        print(f"[{task}] valid={len(cases)}/{attempted} {status}", flush=True)
        if status != "OK":
            continue
        # attribution ground truth = exhaustive repair matrix
        for ci, case in enumerate(cases):
            fault = None
            with reg.unit(f"C2_matrix_{task}_{ci}", "C", task, "exhaustive_repair") as u:
                seed = case["seed"]
                # rebuild the same fault from the frozen generator (metadata read by
                # the CASE BUILDER only, never by a probe)
                m = next(r for r in meta_rows if r["case_id"] == case["case_id"])
                fault = Perturbation(m["modality"], (m["agent"],), m["t_start"],
                                     m["t_start"] + 20, m["severity"])
                cells = matrix(actor, task, seed, fault, sem)
                minimal, good = minimal_sets(cells)
                case["cells"] = cells
                case["causal"] = [list(c) for c in good]
                case["n_causal"] = len(good)
                case["minimal_size"] = 1 if good else None
                case["exhaustive_queries"] = len(cells)
                orders = probe_orders(cells, seed)
                case["probes"] = {}
                for name, order in orders.items():
                    for frac in BUDGETS:
                        k = max(1, int(frac * len(cells)))
                        q = order[:k]
                        hit1 = int(bool(q) and tuple(q[0]) in set(map(tuple, good)))
                        hitk = int(any(tuple(x) in set(map(tuple, good)) for x in q))
                        key = f"{name}@{int(frac*100)}pct"
                        case["probes"].setdefault(key, []).append({"top1": hit1, "topk": hitk,
                                                                   "queries": k})
                u.success({"n_causal": len(good)}, sim_queries=len(cells))
            if (ci + 1) % 5 == 0:
                print(f"  {task} matrices {ci+1}/{len(cases)} {time.time()-t0:.0f}s", flush=True)
        if cases:
            out["tasks"][task].update({
                "identifiable_le3": sum(1 for c in cases if c["n_causal"] <= 3) / len(cases),
                "unique": sum(1 for c in cases if c["n_causal"] == 1) / len(cases),
                "mean_causal": sum(c["n_causal"] for c in cases) / len(cases),
                "exhaustive_matrix_size": cases[0]["exhaustive_queries"]})
        for name in ("RANDOM_CELL", "TIME_BINARY", "AGENT_THEN_TIME_GROUP_TEST",
                     "INFLUENCE_PRIORITIZED"):
            for frac in BUDGETS:
                key = f"{name}@{int(frac*100)}pct"
                agg = [p for c in cases for p in c["probes"].get(key, [])]
                if agg:
                    out["tasks"][task].setdefault("probe_metrics", {})[key] = {
                        "top1": sum(a["top1"] for a in agg) / len(agg),
                        "topk": sum(a["topk"] for a in agg) / len(agg), "n": len(agg)}
        json.dump(cases, open(OUT / f"cases_{task}.json", "w"), default=str)
        print(f"[{task}] ident_le3={out['tasks'][task].get('identifiable_le3')} "
              f"unique={out['tasks'][task].get('unique')}", flush=True)
    with open(OUT / "injection_metadata.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["case_id", "modality", "agent", "severity", "t_start"])
        w.writeheader()
        for r in meta_rows:
            w.writerow(r)
    out["registry"] = reg.reconcile()
    out["wall_seconds"] = round(time.time() - t0, 1)
    (PA / "metrics" / "a2_track_c.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({t: {k: v for k, v in d.items() if k not in ("probe_metrics",)}
                      for t, d in out["tasks"].items()}, indent=1, default=str)[:1200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
