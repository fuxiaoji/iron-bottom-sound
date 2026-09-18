"""C0 sampling-policy comparison on meta-games calibrated from REAL IBS matches.

The outcome distributions come from ``c0_calibration_*.json`` (real Iron Bottom
Sound matches).  Each simulated "match" draws one outcome from a cell's
calibrated distribution; the certificate machinery only sees counts.  This is a
calibrated-simulator comparison, NOT new engine evidence — its verdict is about
sampling policy efficiency given the calibrated meta-games.

Pre-declared gates (fixed before any run):
    PASS_TO_DISCOVERY : median saving >= 40% vs uniform on BOTH scenarios
    C_SMALL_EFFECT    : saving 10-40%, or inconsistent across scenarios
    FAIL              : median saving < 10%
    saving = 1 - games(candidate) / games(uniform), per scenario, medians.

Run:
    PYTHONPATH=backend/src:research/m0 .venv/bin/python research/m0/c0_psro/simulate.py
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO / "research" / "m0"))

from c0_psro.certs import (POLICIES, game_value, run_sampling,  # noqa: E402
                           true_value_matrix)

OUT = REPO / "research" / "m0" / "results"

TARGET_WIDTH = 0.20
ALPHA = 0.05
MAX_SAMPLES = 90_000
BATCH = 25
SEEDS = (11, 22, 33, 44, 55)
GATE_PASS = 0.40
GATE_SMALL = 0.10


def main() -> int:
    scenarios = {}
    for name in ("IBS-S-03", "IBS-S-01"):
        p = OUT / f"c0_calibration_{name}.json"
        if not p.exists():
            print(f"missing calibration for {name}, skipping", file=sys.stderr)
            continue
        d = json.loads(p.read_text())
        dist = [[tuple(cell) for cell in row] for row in d["distribution"]]
        scenarios[name] = dist

    rows = []
    summary = {"target_width": TARGET_WIDTH, "alpha": ALPHA, "batch": BATCH,
               "seeds": list(SEEDS), "scenarios": {}}

    for scen, dist in scenarios.items():
        v_star = game_value(true_value_matrix(dist))
        res = {"true_value": v_star, "policies": {}}
        for policy in POLICIES:
            print(f"[{scen}] policy={policy} ...", flush=True)
            runs = []
            for seed in SEEDS:
                r = run_sampling(dist, policy, target=TARGET_WIDTH, alpha=ALPHA,
                                 max_samples=MAX_SAMPLES, seed=seed, batch=BATCH)
                print(f"  seed={seed} reached={r['reached']} "
                      f"samples={r['samples']} width={r['width']:.3f}", flush=True)
                runs.append({"seed": seed, "reached": r["reached"],
                             "samples": r["samples"],
                             "final_width": r["width"]})
            reached = [x["samples"] for x in runs if x["reached"]]
            res["policies"][policy] = {
                "runs": runs,
                "n_reached": len(reached),
                "median_samples": statistics.median(reached) if reached else None,
                "mean_samples": statistics.mean(reached) if reached else None,
                "max_samples": max(reached) if reached else None,
            }
            for x in runs:
                rows.append({"scenario": scen, "policy": policy, **x})
        # savings vs uniform
        u = res["policies"]["uniform"]["median_samples"]
        for policy in POLICIES:
            m = res["policies"][policy]["median_samples"]
            if u and m:
                res["policies"][policy]["saving_vs_uniform"] = 1 - m / u
        summary["scenarios"][scen] = res

    # ---- verdict ---------------------------------------------------------
    cand = "cert_sensitivity"
    savings = []
    for scen, res in summary["scenarios"].items():
        s = res["policies"][cand].get("saving_vs_uniform")
        savings.append(s)
    reasons = []
    if all(s is not None for s in savings) and savings:
        med = statistics.median(savings)
        all_pass = all(s >= GATE_PASS for s in savings)
        any_pass = any(s >= GATE_PASS for s in savings)
        if all_pass:
            verdict = "PASS_TO_DISCOVERY"
        elif any(s >= GATE_SMALL for s in savings):
            verdict = "C_SMALL_EFFECT"
            reasons.append(f"savings {['%.1f%%' % (100*s) for s in savings]} "
                           f"below the {GATE_PASS:.0%} gate on at least one scenario")
        else:
            verdict = "FAIL"
            reasons.append(f"all savings below {GATE_SMALL:.0%}")
        reasons.append(f"candidate={cand}, per-scenario median savings="
                       f"{['%.3f' % s for s in savings]}")
    else:
        verdict = "FAIL"
        reasons.append("candidate never reached the target width "
                       "(or uniform never did, making savings undefined)")
    summary["verdict"] = verdict
    summary["verdict_reasons"] = reasons
    summary["gates"] = {"pass": ">=40% saving on both scenarios",
                        "small": "10-40% or inconsistent",
                        "fail": "<10%"}

    (OUT / "C0_summary.json").write_text(json.dumps(summary, indent=2))
    import csv
    with (OUT / "C0_sampling_runs.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["scenario", "policy", "seed",
                                           "reached", "samples", "final_width"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(json.dumps({"verdict": verdict, "reasons": reasons,
                      "per_scenario": {s: {
                          p: {"median": v["median_samples"],
                              "saving": v.get("saving_vs_uniform")}
                          for p, v in r["policies"].items()}
                       for s, r in summary["scenarios"].items()}},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
