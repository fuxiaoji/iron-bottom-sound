"""Track D identification experiment: distinguish the defect MECHANISM, cheaply.

Protocol
--------
* A *test* is one exact-lab decision node (game + information set with an active
  commitment).  Presenting a test to an agent yields its option there.
* The evaluator holds a uniform posterior over the five zoo types and must
  identify the true type from as few tests as possible.
* Deterministic agents (discovery phase): a mismatching answer eliminates a type
  outright — twenty questions.  Metric: tests until posterior mass >= 0.90 on
  the true type.
* Selection methods compared:
    random        uniform over the pool (5 seeds)
    hardest       static ranking by worst-case defect regret
    disagreement  static ranking by answer entropy over ALL zoo types
    infogain      ADAPTIVE: maximise expected posterior entropy reduction given
                  the currently-consistent types (the candidate)

Pre-declared gates (fixed before running):
    PASS_TO_DISCOVERY: infogain or disagreement needs <= 0.5x the tests of
                       random (>= 2x efficiency), OR >= +20pp accuracy at a
                       fixed budget of 5 tests, AND identification is mechanism-
                       level (>= 4 defect types identifiable, not just OPT vs
                       bad).
    D_FAIL: methods only separate optimal-vs-bad, or inseparable pairs dominate.

Run:
    PYTHONPATH=backend/src:research/m0 .venv/bin/python research/m0/d0_diaggame/identify.py
"""

from __future__ import annotations

import json
import math
import random
import statistics
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO / "research" / "m0"))

from exact_lab import ExactLab, enumerate_all_nodes  # noqa: E402
from exact_lab.generator import grid  # noqa: E402
from d0_diaggame.zoo import ZOO, agent_answer, regret_of  # noqa: E402

OUT = REPO / "research" / "m0" / "results"
CONFIDENT = 0.90
BUDGET_ACC = 5     # accuracy-at-fixed-budget for the second gate
CAP = 60           # give up after this many tests


def build_pool(max_tests_per_game: int = 12):
    """Pool of (spec, lab, node, belief) tests + precomputed answers/regrets."""
    pool = []
    for spec in grid("discovery"):
        lab = ExactLab(spec)
        try:
            nodes = enumerate_all_nodes(spec)
        except RuntimeError:
            continue
        kept = 0
        for (t, af, rf, obs), belief in nodes:
            if rf <= 0 or t >= spec.T:
                continue
            answers = {z: agent_answer(z, spec, lab, (t, af, rf, obs), belief)
                       for z in ZOO}
            regrets = {z: regret_of(spec, lab, (t, af, rf, obs), belief, answers[z])
                       for z in ZOO}
            pool.append({
                "game": spec.name, "spec": spec, "lab": lab,
                "node": (t, af, rf, obs), "belief": belief,
                "answers": answers, "regrets": regrets,
            })
            kept += 1
            if kept >= max_tests_per_game:
                break
    return pool


def score_static_hardest(test) -> float:
    return max(test["regrets"].values())


def score_static_disagreement(test) -> float:
    cnt = Counter(str(v) for v in test["answers"].values())
    n = sum(cnt.values())
    return -sum((c / n) * math.log2(c / n) for c in cnt.values())


def expected_entropy_after(test, consistent):
    """Greedy expected posterior entropy for deterministic agents."""
    buckets = {}
    for z in consistent:
        buckets.setdefault(str(test["answers"][z]), []).append(z)
    n = len(consistent)
    h = 0.0
    for members in buckets.values():
        p = len(members) / n
        h += p * (-p * math.log2(p))   # entropy of the resulting posterior
    return h


def run_identification(pool, true_type: str, method: str, seed: int = 0):
    rng = random.Random(seed)
    consistent = list(ZOO)
    asked = 0
    remaining = list(range(len(pool)))
    history = []
    while asked < CAP and len(consistent) > 1:
        if method == "random":
            idx = remaining[rng.randrange(len(remaining))]
        elif method == "hardest":
            idx = max(remaining, key=lambda i: score_static_hardest(pool[i]))
        elif method == "disagreement":
            idx = max(remaining, key=lambda i: score_static_disagreement(pool[i]))
        elif method == "infogain":
            idx = min(remaining,
                      key=lambda i: expected_entropy_after(pool[i], consistent))
        else:
            raise ValueError(method)
        remaining.remove(idx)
        test = pool[idx]
        observed = test["answers"][true_type]
        before = len(consistent)
        consistent = [z for z in consistent if test["answers"][z] == observed]
        asked += 1
        history.append({"test": idx, "game": test["game"],
                        "n_consistent": len(consistent)})
        if len(consistent) <= 1:
            break
    p_true = (1.0 / len(consistent)) if true_type in consistent else 0.0
    identified = (len(consistent) == 1 and consistent[0] == true_type
                  and p_true >= CONFIDENT)
    return {"true_type": true_type, "method": method, "seed": seed,
            "tests": asked if identified else None,
            "identified": identified, "final_consistent": consistent,
            "history": history}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    pool = build_pool()
    print(f"test pool: {len(pool)} decision nodes "
          f"({len({t['game'] for t in pool})} games)")

    # ---- global separability audit (before any selection comparison) -------
    never_split = []
    for a in ZOO:
        for b in ZOO:
            if a < b:
                sep = any(t["answers"][a] != t["answers"][b] for t in pool)
                if not sep:
                    never_split.append((a, b))
    print("inseparable pairs (identical answers on every test):",
          never_split or "none")

    rows = []
    methods = ["random", "hardest", "disagreement", "infogain"]
    for true_type in ZOO:
        for method in methods:
            seeds = range(5) if method == "random" else [0]
            for seed in seeds:
                res = run_identification(pool, true_type, method, seed)
                res["budget_accuracy"] = None
                rows.append(res)
    # accuracy at fixed budget
    for true_type in ZOO:
        for method in methods:
            seeds = range(5) if method == "random" else [0]
            hits = 0
            for seed in seeds:
                r = run_identification(pool, true_type, method, seed)
                h = r["history"][:BUDGET_ACC]
                if len(h) == BUDGET_ACC:
                    pass
                # identified within budget?
                hits += 1 if (r["identified"] and (r["tests"] or CAP) <= BUDGET_ACC) else 0
            rows.append({"true_type": true_type, "method": method,
                         "budget_accuracy": hits / len(list(seeds)),
                         "tests": None, "identified": None,
                         "seed": -1, "final_consistent": [],
                         "history": []})

    # ---- aggregate -------------------------------------------------------
    agg = {}
    for method in methods:
        tests = [r["tests"] for r in rows
                 if r["method"] == method and r["tests"] is not None
                 and r["budget_accuracy"] is None]
        ident = [r["identified"] for r in rows
                 if r["method"] == method and r["budget_accuracy"] is None]
        acc = [r["budget_accuracy"] for r in rows
               if r["method"] == method and r["budget_accuracy"] is not None]
        agg[method] = {
            "n_runs": len(tests),
            "identification_rate": (sum(ident) / len(ident)) if ident else None,
            "tests_mean": statistics.mean(tests) if tests else None,
            "tests_median": statistics.median(tests) if tests else None,
            "tests_max": max(tests) if tests else None,
            "budget_accuracy_at_5": statistics.mean(acc) if acc else None,
        }

    # per-type identifiability (any method)
    per_type = {}
    for z in ZOO:
        t = [r["tests"] for r in rows if r["true_type"] == z and r["tests"] is not None]
        per_type[z] = {"identified_runs": len(t),
                       "median_tests": statistics.median(t) if t else None}

    rand_med = agg["random"]["tests_median"]
    verdict = "D_FAIL"
    reasons = []
    eff = {}
    for m in ("hardest", "disagreement", "infogain"):
        if rand_med and agg[m]["tests_median"]:
            eff[m] = rand_med / agg[m]["tests_median"]
    gain = {m: (agg[m]["budget_accuracy_at_5"] or 0) -
            (agg["random"]["budget_accuracy_at_5"] or 0)
            for m in ("hardest", "disagreement", "infogain")}
    n_defects_identifiable = sum(
        1 for z in ZOO if z != "OPT" and per_type[z]["identified_runs"] > 0)
    if n_defects_identifiable >= 4 and (
            any(e >= 2.0 for e in eff.values())
            or any(g >= 0.20 for g in gain.values())):
        verdict = "PASS_TO_DISCOVERY"
    elif n_defects_identifiable < 4:
        verdict = "D_FAIL"
        reasons.append(f"only {n_defects_identifiable}/4 defect types identifiable")
    else:
        verdict = "WEAK"
    if never_split:
        reasons.append(f"inseparable pairs: {never_split}")

    summary = {
        "pool_size": len(pool),
        "n_games": len({t["game"] for t in pool}),
        "inseparable_pairs": never_split,
        "methods": agg,
        "efficiency_vs_random": eff,
        "accuracy_gain_at_5_vs_random": gain,
        "per_type": per_type,
        "n_defect_types_identifiable": n_defects_identifiable,
        "verdict": verdict,
        "verdict_reasons": reasons,
        "gates": {"efficiency": ">= 2x fewer tests than random",
                  "or_accuracy_gain": ">= +20pp at budget 5",
                  "mechanism_requirement": ">= 4 defect types identifiable"},
    }
    (OUT / "D0_summary.json").write_text(json.dumps(summary, indent=2))
    # flat CSV
    import csv
    with (OUT / "D0_identification.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["true_type", "method", "seed",
                                           "tests", "identified",
                                           "budget_accuracy"])
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in w.fieldnames})
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
