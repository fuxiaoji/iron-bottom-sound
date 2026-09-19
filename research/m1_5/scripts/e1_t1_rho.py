"""E1-T1: rho distribution over the M1 G1 pair population.

rho(s) = min_a max_x [V_x - Q_x(a)] is recomputed from the frozen 15-replicate
M1 G1 Q tables (g1_analysis15.json). Thresholds are in PRE_REGISTRATION.md,
written before this script produced any aggregate.

    PYTHONPATH=backend/src:research/m1_5/scripts .venv/bin/python \
        research/m1_5/scripts/e1_t1_rho.py
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
G1 = REPO / "research" / "m1" / "g1"
OUT = REPO / "research" / "m1_5"

# floors from PRE_REGISTRATION.md (do not touch after seeing results)
FLOOR_DAMAGE = 0.02
FLOOR_OUTCOME = 0.10
LOW_NORM = 0.05
HIGH_NORM = 0.10


def rho_metrics(rec: dict) -> dict | None:
    out = {}
    for key, attr in (("outcome", "regret"), ("damage_diff", "regret_damage_diff")):
        reg = rec.get(attr)
        if not reg:
            return None
        out[key] = {
            "rho_abs": reg["R"],
            "rho_norm": reg["normalized_regret"],
            "stake": reg["stake"],
            "confident": reg["q_ranking_confident"],
        }
    # value divergence and action disagreement per value function
    for key in ("outcome", "damage_diff"):
        qa, qb = rec["Q"]["A"], rec["Q"]["B"]
        ds = [abs(x.get(f"{key}_mean") - y.get(f"{key}_mean"))
              for x, y in zip(qa, qb)
              if x.get(f"{key}_mean") is not None]
        out[key]["value_divergence"] = max(ds) if ds else 0.0
    out["action_disagreement"] = rec["regret"]["argmax_differs"]
    out["scenario"] = rec["scenario"]
    out["pair_id"] = rec["pair_id"]
    out["n_candidates"] = rec["n_candidates_shared"]
    out["turn"] = rec["turn"]
    return out


def classify(m: dict, key: str) -> str:
    d = m[key]
    floor = FLOOR_OUTCOME if key == "outcome" else FLOOR_DAMAGE
    if d["rho_norm"] >= HIGH_NORM and d["rho_abs"] >= floor:
        return "high_meaningful"
    if d["rho_norm"] < LOW_NORM or d["rho_abs"] < floor:
        return "low"
    return "middle"


def main() -> int:
    rows = json.loads((G1 / "g1_analysis15.json").read_text())
    main = [r for r in rows if not r["is_control_b"]]
    ctl = [r for r in rows if r["is_control_b"]]

    metrics, ctl_metrics = [], []
    for rec in main:
        m = rho_metrics(rec)
        if m:
            m["is_control"] = False
            metrics.append(m)
    for rec in ctl:
        m = rho_metrics(rec)
        if m:
            m["is_control"] = True
            ctl_metrics.append(m)

    report = {"n_evaluable_main": len(metrics), "n_control": len(ctl_metrics)}
    for subset_name, pop in (("all_evaluable", metrics),
                             ("ci_passing", [m for m in metrics
                                             if m["outcome"]["confident"] or m["damage_diff"]["confident"]]),
                             ("control_B", ctl_metrics)):
        for key in ("outcome", "damage_diff"):
            rhos = [m[key]["rho_abs"] for m in pop]
            norms = [m[key]["rho_norm"] for m in pop]
            stakes = [m[key]["stake"] for m in pop]
            cls = [classify(m, key) for m in pop]
            n_high = cls.count("high_meaningful")
            n_low = cls.count("low")
            high_stakes = [m[key]["stake"] for m, c in zip(pop, cls)
                           if c == "high_meaningful"]
            conf = [m for m in pop if m[key]["confident"]]
            conf_cls = [classify(m, key) for m in conf]
            entry = {
                "n": len(pop),
                "rho_abs": {"median": statistics.median(rhos), "max": max(rhos),
                            "p90": sorted(rhos)[int(0.9 * len(rhos))]},
                "rho_norm": {"median": statistics.median(norms), "max": max(norms)},
                "stake": {"median": statistics.median(stakes), "max": max(stakes)},
                "frac_low": n_low / len(pop),
                "frac_high_meaningful": n_high / len(pop),
                "n_high_meaningful": n_high,
                "high_stake_median": statistics.median(high_stakes) if high_stakes else None,
                "ci_passing_frac_high": (conf_cls.count("high_meaningful") / len(conf)
                                         if conf else None),
                "action_disagreement_rate": (statistics.mean([m["action_disagreement"]
                                                              for m in pop])),
            }
            report.setdefault(subset_name, {})[key] = entry

    # scenario conditioning on the CI-passing subset (primary population)
    scen = {}
    for m in metrics:
        if not (m["outcome"]["confident"] or m["damage_diff"]["confident"]):
            continue
        scen.setdefault(m["scenario"], []).append(m)
    report["scenario_conditioned_ci_passing"] = {
        s: {
            "n": len(pop),
            "outcome": {"frac_high": sum(1 for m in pop if classify(m, "outcome") == "high_meaningful") / len(pop)},
            "damage_diff": {"frac_high": sum(1 for m in pop if classify(m, "damage_diff") == "high_meaningful") / len(pop)},
        }
        for s, pop in sorted(scen.items())}

    # gate evaluation, exactly as pre-registered
    ci = [m for m in metrics if m["outcome"]["confident"] or m["damage_diff"]["confident"]]
    gate = {}
    for key in ("outcome", "damage_diff"):
        cls = [classify(m, key) for m in ci]
        n_high = cls.count("high_meaningful")
        high_stakes = [m[key]["stake"] for m, c in zip(ci, cls) if c == "high_meaningful"]
        gate[key] = {
            "frac_low": cls.count("low") / len(ci),
            "frac_high": n_high / len(ci),
            "high_stake_median": statistics.median(high_stakes) if high_stakes else None,
            "c1_ge_50pct_low": cls.count("low") / len(ci) >= 0.50,
            "c2_ge_10pct_high": n_high / len(ci) >= 0.10,
            "c3_not_tiny_stake": (statistics.median(high_stakes) >= (FLOOR_OUTCOME if key == "outcome" else FLOOR_DAMAGE))
                                 if high_stakes else False,
        }
    report["gate"] = gate
    report["verdict"] = {
        "outcome": "PASS" if all(gate["outcome"][k] for k in
                                 ("c1_ge_50pct_low", "c2_ge_10pct_high", "c3_not_tiny_stake")) else "FAIL",
        "damage_diff": "PASS" if all(gate["damage_diff"][k] for k in
                                     ("c1_ge_50pct_low", "c2_ge_10pct_high", "c3_not_tiny_stake")) else "FAIL",
    }
    report["thresholds"] = {"FLOOR_DAMAGE": FLOOR_DAMAGE, "FLOOR_OUTCOME": FLOOR_OUTCOME,
                            "LOW_NORM": LOW_NORM, "HIGH_NORM": HIGH_NORM}

    (OUT / "metrics" / "e1_t1_rho.json").write_text(json.dumps(report, indent=2))
    # per-pair flat metrics for figures / E1-T2 features
    import csv
    with (OUT / "metrics" / "e1_t1_rho_pairs.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["pair_id", "scenario", "turn", "n_candidates",
                    "rho_abs_outcome", "rho_norm_outcome", "stake_outcome",
                    "rho_abs_damage", "rho_norm_damage", "stake_damage",
                    "value_divergence_outcome", "value_divergence_damage",
                    "action_disagreement", "confident_outcome", "confident_damage"])
        for m in metrics:
            w.writerow([m["pair_id"], m["scenario"], m["turn"], m["n_candidates"],
                        m["outcome"]["rho_abs"], m["outcome"]["rho_norm"], m["outcome"]["stake"],
                        m["damage_diff"]["rho_abs"], m["damage_diff"]["rho_norm"], m["damage_diff"]["stake"],
                        m["outcome"]["value_divergence"], m["damage_diff"]["value_divergence"],
                        m["action_disagreement"], m["outcome"]["confident"], m["damage_diff"]["confident"]])
    print(json.dumps({k: report[k] for k in ("n_evaluable_main", "gate", "verdict",
                                             "scenario_conditioned_ci_passing")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
