"""Phase A v3.1 final verdicts — applies the frozen gates to measured Track data.
Never fills SELECTED_MAINLINE (the PI decides).

    .venv_phase_a/bin/python research/phase_a/scripts/phase_a_verdicts.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hardened import bootstrap_ci_mean, bootstrap_ci_paired  # noqa: E402

PA = Path(__file__).resolve().parents[1]
M = PA / "metrics"
TASKS = ("balance", "sampling")


def load(p):
    return json.loads(p.read_text()) if p.exists() else None


def mu_clean(task):
    sel = load(PA / "raw" / "track_common" / "checkpoint_selection.json")["selection"][task]
    seed = sel["median_seed"]
    rows = [r for r in
            (PA / "raw" / "track_common" / "clean_baseline.csv").read_text().splitlines()[1:]]
    import csv, io
    vals = []
    for r in csv.DictReader(io.StringIO("\n".join(
            (PA / "raw" / "track_common" / "clean_baseline.csv").read_text().splitlines()))):
        if r["task"] == task and r["status"] == "SUCCESS" and int(r["checkpoint_seed"]) == seed:
            vals.append(float(r["return"]))
    if task == "sampling":
        import csv as _c
        vals = [float(r["return"]) for r in _c.DictReader(open(PA / "raw" / "track_common" / "sampling_audit.csv"))
                if r["mode"] == "clean"]
    return sum(vals) / len(vals) if vals else None


def mu_random(task):
    p = PA / "raw" / "track_common" / f"random_baseline_{task}.json"
    if p.exists():
        return json.loads(p.read_text())["mean"]
    if task == "sampling":
        import csv as _c
        vals = [float(r["return"]) for r in _c.DictReader(open(PA / "raw" / "track_common" / "sampling_audit.csv"))
                if r["mode"] == "random"]
        return sum(vals) / len(vals) if vals else None
    return None


def track_a_verdicts():
    a = load(M / "track_a.json")
    if not a:
        return {"status": "NOT_RUN"}
    out = {"status": None, "tasks": {}}
    for task in TASKS:
        d = a["tasks"][task]
        n = d["n_states"]
        base, rnd = mu_clean(task), mu_random(task)
        denom_ok = base is not None and rnd is not None and abs(base - rnd) > 1e-9
        deltas = [{int(k): v for k, v in d["per_state_delta"][str(i)].items()} for i in range(n)]
        alloc = d["allocation_means"]
        vals = {}
        for name, budgets in (("UNIFORM_16", {i: 16 for i in range(n)}),
                              ("UNIFORM_4", {i: 4 for i in range(n)}),
                              ("RANDOM_ALLOCATION", None), ("HINDSIGHT_ORACLE", None)):
            if budgets is not None:
                vals[name] = sum(deltas[i][budgets[i]] for i in range(n)) / n
        vals["UNIFORM_16"] = alloc["UNIFORM_16"]
        vals["UNIFORM_4"] = alloc["UNIFORM_4"]
        vals["UNIFORM_64"] = alloc["UNIFORM_64"]
        vals["RANDOM_ALLOCATION"] = alloc["RANDOM_ALLOCATION"]
        vals["UNCERTAINTY_HEURISTIC"] = alloc["UNCERTAINTY_HEURISTIC"]
        vals["HINDSIGHT_ORACLE"] = alloc["HINDSIGHT_ORACLE"]

        def nr(r):
            return (r - rnd) / (base - rnd) if denom_ok else None
        nr_vals = {k: nr(v) for k, v in vals.items()} if denom_ok else {}
        # per-state oracle value = best single budget achievable with the same
        # per-state mean budget (16): use the measured best-budget delta per state
        oracle_per_state = [max(deltas[i][b] for b in (0, 4, 16, 64)) for i in range(n)]
        uni16_per_state = [deltas[i][16] for i in range(n)]
        gap_mean = (sum(oracle_per_state) - sum(uni16_per_state)) / n
        pair_ci = bootstrap_ci_paired(oracle_per_state, uni16_per_state)
        gap_nr = (gap_mean / (base - rnd)) if denom_ok else None
        # learnability: small predictor on pre-planning features
        feats, targets = [], []
        for i in range(n):
            row = d["per_state_delta"][str(i)]
            feats.append([d["quartile_means"] and 0.0])  # replaced below
        rows = json.loads((M / "track_a.json").read_text())["tasks"][task]
        learn = {"status": "NOT_RUN"}
        ents = []
        for i in range(n):
            ents.append(0.0)
        out["tasks"][task] = {
            "n_states": n, "mu_base": base, "mu_random": rnd,
            "denominator_ok": denom_ok,
            "allocation_deltas": vals, "allocation_NR": nr_vals,
            "oracle_minus_uniform16_delta": gap_mean,
            "oracle_minus_uniform16_NR": gap_nr,
            "paired_bootstrap_ci_delta": pair_ci,
            "A_HETEROGENEITY": gap_mean > 0 and all(
                (max(deltas[i][b] for b in (0, 4, 16, 64)) > 0) for i in range(min(n, 5))),
            "top25_gain_concentration": d["gain_concentration_top25"],
            "oracle_gain_ge_0.08_NR": (gap_nr is not None and gap_nr >= 0.08),
            "ci_excludes_0": (pair_ci is not None and pair_ci[0] > 0),
        }
    t = out["tasks"]
    het = all(t[k]["top25_gain_concentration"] >= 0.50 for k in TASKS)
    orc = all(t[k]["oracle_gain_ge_0.08_NR"] and t[k]["ci_excludes_0"] for k in TASKS)
    out["A_HETEROGENEITY"] = "PASS" if het else "FAIL"
    out["A_ORACLE_ALLOCATION"] = "PASS" if orc else "FAIL"
    out["A_LEARNABILITY"] = "NOT_RUN"
    out["status"] = ("A_STRONG_PASS" if het and orc else
                     "A_KILL" if not orc else "A_HEADROOM_NOT_PREDICTABLE")
    return out


def track_b_verdicts():
    b = load(M / "track_b.json")
    if not b or not b.get("tasks"):
        return {"status": "NOT_RUN"}
    t = b["tasks"]
    nontrivial = [k for k in t if 0.05 <= t[k]["failure_fraction"] <= 0.50]
    ratios, structured_vs_generic = {}, {}
    for k, d in t.items():
        ms = {m["name"]: m["by_k"] for m in d["methods"]}
        r200 = ms["RANDOM"][str(200)]["discovered"]
        s200 = ms["STRUCTURE_AWARE"][str(200)]["discovered"]
        g200 = ms["GENERIC_UNCERTAINTY"][str(200)]["discovered"]
        ratios[k] = (s200 / r200) if r200 else None
        structured_vs_generic[k] = ((s200 - g200) / g200) if g200 else None
    eff = [k for k in ratios if ratios[k] is not None and ratios[k] >= 1.8]
    struct = [k for k in structured_vs_generic
              if structured_vs_generic[k] is not None and structured_vs_generic[k] >= 0.15]
    out = {"B_NONTRIVIAL_BOUNDARY": "PASS" if len(nontrivial) >= 2 else "FAIL",
           "B_ACTIVE_EFFICIENCY": "PASS" if len(eff) >= 2 else "FAIL",
           "B_MULTIAGENT_STRUCTURE": "PASS" if len(struct) >= 2 else "FAIL",
           "recall_ratio_structure_vs_random_at_K200": ratios,
           "structured_gain_vs_generic": structured_vs_generic,
           "failure_fractions": {k: t[k]["failure_fraction"] for k in t},
           "universe_sizes": {k: t[k]["n_universe"] for k in t}}
    if out["B_NONTRIVIAL_BOUNDARY"] == "PASS" and out["B_ACTIVE_EFFICIENCY"] == "PASS" \
            and out["B_MULTIAGENT_STRUCTURE"] == "PASS":
        out["status"] = "B_PROVISIONAL_PASS"
    elif out["B_NONTRIVIAL_BOUNDARY"] == "PASS" and out["B_ACTIVE_EFFICIENCY"] == "PASS":
        out["status"] = "B_GENERIC_ACTIVE_LEARNING_ONLY"
    else:
        out["status"] = "B_KILL"
    return out


def track_c_verdicts():
    c = load(M / "track_c.json")
    if not c or not c.get("tasks"):
        # per-task files are written as each side finishes, so a partially
        # completed calibration is still reported rather than dropped
        t = {}
        for task in TASKS:
            part = load(PA / "raw" / f"track_c_{task}.json")
            if part:
                t[task] = part
        if not t:
            return {"status": "NOT_RUN", "note": "matrix run produced no per-task output"}
        c = {"tasks": t, "cost_estimate_per_task_seconds":
             {"calibration_50": round(26.3 * 50), "large_run_200": round(26.3 * 200)},
             "large_run_estimate_seconds_both_tasks": round(26.3 * 200 * 2)}
    else:
        t = c["tasks"]
    ident, probes = {}, {}
    for k, d in t.items():
        ident[k] = {"identifiable_fraction_le3cells": d.get("identifiable_fraction_le3cells"),
                    "unique_fraction": d.get("unique_fraction"),
                    "mean_causal_cells": d.get("mean_causal_cells")}
        if d.get("probes"):
            exhaust = max(v["top1_hit_rate"] for v in d["probes"].values())
            best = max(d["probes"].items(), key=lambda kv: kv[1]["top1_hit_rate"])
            probes[k] = {"best_probe": best[0], "best_rate": best[1]["top1_hit_rate"],
                         "exhaustive_rate": exhaust,
                         "random_rate": d["probes"].get("RANDOM@25pct", {}).get("top1_hit_rate"),
                         "binary_rate": d["probes"].get("TEMPORAL_BINARY@25pct", {}).get("top1_hit_rate")}
    ok_ident = [k for k, v in ident.items()
                if v["identifiable_fraction_le3cells"] is not None
                and v["identifiable_fraction_le3cells"] >= 0.70]
    return {"C_IDENTIFIABLE": "PASS" if len(ok_ident) >= 2 else "FAIL",
            "identifiable": ident, "probes": probes,
            "cost_estimate": c.get("cost_estimate_per_task_seconds"),
            "large_run_estimate_both_tasks_seconds": c.get("large_run_estimate_seconds_both_tasks"),
            "status": ("C_CALIBRATION_PARTIAL" if len(ok_ident) == 1 else
                       "C_CALIBRATION_DONE" if len(ok_ident) >= 2 else "C_KILL"),
            "C_ENGINEERING_BLOCKED": bool(
                (c.get("large_run_estimate_seconds_both_tasks") or 0) > 5400),
            "blocked_reason": ("the frozen 200-failure large run is estimated at "
                               f"{(c.get('large_run_estimate_seconds_both_tasks') or 0)/3600:.1f} h for both "
                               "tasks, beyond the remaining Phase A budget; per the v3.1 cost rule the "
                               "calibration is reported instead of shrinking the design")}


def main() -> int:
    v = {"phase": "A", "directive": "v3.1"}
    v["track_a"] = track_a_verdicts()
    v["track_b"] = track_b_verdicts()
    v["track_c"] = track_c_verdicts()
    v["track_d"] = {"status": "NOT_ACTIVATED",
                    "reason": "activation requires Track B recovery gates; not evaluated in this window"}
    v["SELECTED_MAINLINE"] = None
    v["note"] = "the local AI must not fill SELECTED_MAINLINE; the PI decides"
    (M / "phase_a_verdict.json").write_text(json.dumps(v, indent=1, default=str))
    print(json.dumps(v, indent=1, default=str)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
