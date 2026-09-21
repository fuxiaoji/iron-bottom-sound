"""Phase A.2 §1 — Track A hindsight-oracle audit.

Under TOTAL_BUDGET = 16·N, assigning 16 to every state is feasible, so a true
hindsight oracle must satisfy V_oracle >= V_uniform16 on the SAME held-out matrix.
The Phase A v3.1 `allocate_oracle` was a greedy gain-per-unit heuristic (it also
skipped zero-budget states), which is why sampling showed oracle < Uniform16; that
aggregate is INVALID and is recomputed here exactly.

Exact solution: multiple-choice knapsack with increments 0->4->16->64 (costs 4, 12,
48), solved by DP over states x capacity. No new held-out evaluations are needed:
every allocation is scored on the raw R[state, budget] matrix already measured.

    .venv_phase_a/bin/python research/phase_a/scripts/a2_oracle_audit.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hardened import bootstrap_ci_paired  # noqa: E402

PA = Path(__file__).resolve().parents[1]
M = PA / "metrics"
OUT = PA / "raw" / "track_a_audit"
OUT.mkdir(parents=True, exist_ok=True)
BUDGETS = (0, 4, 16, 64)
STEPS = ((4, 0), (16, 4), (64, 16))          # (target budget, source budget)


def exact_oracle(delta, total):
    """Maximise sum delta[i][b_i] subject to sum b_i == total, b_i in BUDGETS."""
    n = len(delta)
    best = {}
    # state 0
    best = {(0, 0): (0.0, ())}
    for i in range(n):
        nxt = {}
        for (idx, used), (val, path) in best.items():
            for b in BUDGETS:
                u2 = used + b
                if u2 > total:
                    continue
                v2 = val + delta[i][b]
                key = (idx + 1, u2)
                if key not in nxt or v2 > nxt[key][0]:
                    nxt[key] = (v2, path + (b,))
        best = nxt
    key = (n, total)
    if key not in best:
        raise AssertionError(f"infeasible: cannot spend exactly {total}")
    val, path = best[key]
    return val, list(path)


def greedy_oracle(delta, total):
    """The Phase A v3.1 heuristic, kept for the record."""
    n = len(delta)
    order = sorted(range(n), key=lambda i: -max(delta[i][b] for b in BUDGETS))
    budgets = {i: 0 for i in range(n)}
    remaining = total
    for i in order:
        if remaining <= 0:
            break
        best_b, best_gain = 0, 0.0
        for b in BUDGETS:
            if b > 0 and b <= remaining:
                g = delta[i][b] / b
                if g > best_gain:
                    best_gain, best_b = g, b
        budgets[i] = best_b
        remaining -= best_b
    return sum(delta[i][budgets[i]] for i in range(n)), budgets


def main() -> int:
    a = json.loads((M / "track_a.json").read_text())
    out = {"audit": "A2 §1", "budgets": list(BUDGETS), "tasks": {}}
    for task, d in a["tasks"].items():
        n = d["n_states"]
        total = 16 * n
        delta = [{int(k): v for k, v in d["per_state_delta"][str(i)].items()}
                 for i in range(n)]
        checks = {}
        # 1. all-16 feasible
        checks["all_16_feasible"] = (16 * n <= total)
        # 2. exact-total allocations exist
        u16 = [16] * n
        checks["uniform16_spends_exactly_total"] = (sum(u16) == total)
        v_u16 = sum(delta[i][16] for i in range(n)) / n
        # 3-5. true oracle vs the Phase A heuristic
        v_ora_mean, ora_alloc = exact_oracle(delta, total)
        checks["oracle_spends_exactly_total"] = (sum(ora_alloc) == total)
        counts = {b: ora_alloc.count(b) for b in BUDGETS}
        v_ora = v_ora_mean / n
        v_greedy_mean, greedy_alloc = greedy_oracle(delta, total)
        v_greedy = v_greedy_mean / n
        # paired bootstrap on the same held-out matrix
        ora_per_state = [delta[i][ora_alloc[i]] for i in range(n)]
        u16_per_state = [delta[i][16] for i in range(n)]
        ci = bootstrap_ci_paired(ora_per_state, u16_per_state)
        # normalised objective
        sel = json.loads((PA / "raw" / "track_common" / "checkpoint_selection.json").read_text())
        seed = sel["selection"][task]["median_seed"]
        import csv as _c
        if task == "sampling":
            clean = [float(r["return"]) for r in _c.DictReader(
                open(PA / "raw" / "track_common" / "sampling_audit.csv")) if r["mode"] == "clean"]
            rnd_p = PA / "raw" / "track_common" / "random_baseline_sampling.json"
            if rnd_p.exists():
                rnd = json.loads(rnd_p.read_text())["mean"]
            else:
                rv = [float(r["return"]) for r in _c.DictReader(
                    open(PA / "raw" / "track_common" / "sampling_audit.csv"))
                    if r["mode"] == "random"]
                rnd = sum(rv) / len(rv) if rv else None
        else:
            clean = [float(r["return"]) for r in _c.DictReader(
                open(PA / "raw" / "track_common" / "clean_baseline.csv"))
                if r["task"] == task and r["status"] == "SUCCESS"
                and int(r["checkpoint_seed"]) == seed]
            rnd_p = PA / "raw" / "track_common" / "random_baseline_balance.json"
            rnd = json.loads(rnd_p.read_text())["mean"] if rnd_p.exists() else None
        mu_base = sum(clean) / len(clean) if clean else None
        denom = (mu_base - rnd) if (mu_base is not None and rnd is not None) else None
        gap = v_ora - v_u16
        gap_nr = (gap / denom) if denom else None
        out["tasks"][task] = {
            "n_states": n, "total_budget": total,
            "checks": checks,
            "counts_oracle_allocation": {str(k): v for k, v in counts.items()},
            "V_uniform16_raw": v_u16, "V_oracle_raw": v_ora, "gap_raw": gap,
            "V_phaseA_greedy_raw": v_greedy,
            "phaseA_greedy_below_uniform16": v_greedy < v_u16 - 1e-12,
            "mu_base": mu_base, "mu_random": rnd,
            "gap_normalised": gap_nr, "paired_bootstrap_ci_gap": ci,
            "oracle_minus_greedy_raw": v_ora - v_greedy,
            "A2_oracle_gain_ge_0.08_NR": bool(gap_nr is not None and gap_nr >= 0.08),
            "A2_ci_gt_0": bool(ci is not None and ci[0] > 0),
        }
        (OUT / f"oracle_audit_{task}.json").write_text(json.dumps(
            out["tasks"][task], indent=1, default=str))
        print(f"[{task}] oracle={v_ora:.6f} uniform16={v_u16:.6f} greedy_phaseA={v_greedy:.6f} "
              f"gap_nr={gap_nr} counts={counts} ci={ci}", flush=True)

    tasks = out["tasks"]
    survive = all(tasks[k]["A2_oracle_gain_ge_0.08_NR"] and tasks[k]["A2_ci_gt_0"]
                  for k in tasks)
    out["phaseA_v31_aggregate"] = ("INVALID: the Phase A 'oracle' was a greedy "
                                   "heuristic, not an oracle, and it scored below "
                                   "the feasible all-16 allocation"
                                   if any(tasks[k]["phaseA_greedy_below_uniform16"] for k in tasks)
                                   else "consistent with the exact oracle")
    out["verdict"] = ("A_KILL_CONFIRMED" if not survive else "A_RESURRECTED_FOR_PI")
    out["note"] = ("A_RESURRECTED_FOR_PI requires the frozen small learnability probe; "
                   "it is run only when the corrected oracle gate passes on BOTH tasks.")
    (M / "a2_oracle_audit.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({"verdict": out["verdict"], "phaseA_aggregate": out["phaseA_v31_aggregate"]},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
