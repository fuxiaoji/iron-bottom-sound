"""B1E verdict + figures — reads only the frozen metric JSONs.

    PYTHONPATH=backend/src:research/m2_2r/scripts:research/m2_2/scripts:research/m2_1/scripts \
        .venv/bin/python research/m2_2r/scripts/b1e_verdict.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
M = ROOT / "metrics"
F = ROOT / "figures"
F.mkdir(exist_ok=True)
sys.path.insert(0, str(HERE))

from b1e import SCENARIOS  # noqa: E402

plt.rcParams.update({"figure.dpi": 140, "font.size": 9, "axes.grid": True,
                     "grid.alpha": 0.25, "axes.axisbelow": True})
ARMS = ["BEAM_SEARCH_COMPILER", "REPAIRED_INTENT_BASELINE",
        "CURRENT_INTENT_PRE_FIX", "RANDOM_LEGAL"]
SHORT = {"BEAM_SEARCH_COMPILER": "BEAM", "REPAIRED_INTENT_BASELINE": "REPAIRED",
         "CURRENT_INTENT_PRE_FIX": "PRE_FIX", "RANDOM_LEGAL": "RANDOM"}
LABELS = [SHORT[a] for a in ARMS]


def load(name):
    p = M / name
    return json.loads(p.read_text()) if p.exists() else None


def median(v):
    v = sorted(x for x in v if x is not None)
    if not v:
        return None
    n = len(v)
    return v[n // 2] if n % 2 else 0.5 * (v[n // 2 - 1] + v[n // 2])


def movement_verdict(mv):
    """Frozen rules §7, applied to the movement census.  See M22R-F1: the
    '>=2 mechanisms' clause is unsatisfiable by a one-mechanism census design and
    is reported as such instead of being silently relaxed."""
    if not mv:
        return {"verdict": "NO_DATA"}
    states = mv["states"]
    rows = []
    for r in states:
        arms = r["arms"]
        base = arms.get("CURRENT_POLICY")
        if not base or "error" in base:
            continue
        b0, b1 = base["L0"]["L0"], base["L1"]["U_team"]
        for arm in ARMS:
            a = arms.get(arm)
            if not a or "error" in a:
                continue
            d0 = a["L0"]["L0"] - b0
            d1 = a["L1"]["U_team"] - b1
            rel = d0 / max(abs(b0), 1e-9)
            rows.append({"scenario": r["scenario"], "seed": r["seed"], "turn": r["turn"],
                         "side": r["side"], "bucket": r["bucket"], "arm": arm,
                         "delta_L0": d0, "delta_L1": d1, "rel_L0": rel,
                         "externality": d1 - d0,
                         "mech": bool(d0 >= 0.05 and rel >= 0.25),
                         "usable": bool(d1 >= 0.05),
                         "neg_ext": bool(d0 > 0 and d1 < 0)})
    per = {}
    for scen in SCENARIOS:
        sr = [x for x in rows if x["scenario"] == scen]
        if not sr:
            continue
        d = {}
        for arm in ARMS:
            ar = [x for x in sr if x["arm"] == arm]
            if not ar:
                continue
            d[arm] = {
                "n": len(ar),
                "mech_opp_rate": sum(x["mech"] for x in ar) / len(ar),
                "usable_rate": sum(x["usable"] for x in ar) / len(ar),
                "neg_externality_rate": sum(x["neg_ext"] for x in ar) / len(ar),
                "median_delta_L0": median([x["delta_L0"] for x in ar]),
                "median_delta_L1": median([x["delta_L1"] for x in ar]),
                "median_rel_L0": median([x["rel_L0"] for x in ar]),
                "median_externality": median([x["externality"] for x in ar]),
            }
        per[scen] = d
    beam = {s: per[s]["BEAM_SEARCH_COMPILER"] for s in per
            if "BEAM_SEARCH_COMPILER" in per[s]}
    rnd = {s: per[s]["RANDOM_LEGAL"] for s in per if "RANDOM_LEGAL" in per[s]}
    scen_with_opp = [s for s, v in beam.items() if v["mech_opp_rate"] >= 0.20]
    median_beam_rel = median([v["median_rel_L0"] for v in beam.values()])
    random_clearly_worse = None
    if beam and rnd:
        mb = median([v["median_delta_L0"] for v in beam.values()])
        mr = median([v["median_delta_L0"] for v in rnd.values()])
        random_clearly_worse = None if (mb is None or mr is None) else bool(mr <= 0.5 * mb)
    max_rate = max((v["mech_opp_rate"] for s in per for a, v in per[s].items()
                    if a == "BEAM_SEARCH_COMPILER"), default=0.0)
    usable_rates = [v["usable_rate"] for s in per for a, v in per[s].items()
                    if a == "BEAM_SEARCH_COMPILER"]
    exts = [v["median_externality"] for s in per for a, v in per[s].items()
            if a == "BEAM_SEARCH_COMPILER"]
    inputs = {
        "mechanism_rows_in_census": 1,
        "mechanism_note": "one local mechanism quantity (focal-pair legal visible-fire "
                          "EH) driven by five arms; Range's executable status comes from "
                          "MG3-E, not from a second census row (M22R-F1)",
        "scenarios_with_mech_opp_ge_20pct": scen_with_opp,
        "median_beam_median_rel_L0": median_beam_rel,
        "random_clearly_worse": random_clearly_worse,
        "max_scenario_mech_opp_rate": max_rate,
        "median_usable_rate": median(usable_rates),
        "median_externality": median(exts),
        "not_driven_by_one_scenario": len(scen_with_opp) >= 2,
    }
    if (len(scen_with_opp) >= 2 and (median_beam_rel or 0) >= 0.30
            and random_clearly_worse and len(scen_with_opp) >= 2):
        v = "NATURAL_COMPILER_GAP"
        note = ("reached under the rule's single-mechanism form; the frozen '>=2 "
                "mechanisms' clause is unsatisfiable by this census design (M22R-F1)")
    elif (len(scen_with_opp) >= 2 and (median(usable_rates) or 0) < 0.10
          and (median(exts) or 0) <= 0):
        v = "LOCAL_ONLY_MECHANISM"
        note = "local opportunity present, team utility does not follow"
    elif max_rate < 0.10:
        v = "MECHANISM_RARE"
        note = "no scenario reaches the 10% floor"
    elif (max_rate < 0.10 and (median_beam_rel or 0) < 0.10
          and not scen_with_opp):
        v = "NO_NATURAL_GAP"
        note = "search does not beat the deployed policy"
    else:
        v = "MIXED"
        note = "frozen thresholds not jointly met in any single branch"
    return {"verdict": v, "note": note, "inputs": inputs, "per_scenario": per,
            "n_state_arms": len(rows)}


def torpedo_verdict(tv):
    if not tv:
        return {"verdict": "NO_DATA"}
    st = tv["states"]
    per = {}
    for scen in SCENARIOS:
        rows = [r for r in st if r["scenario"] == scen]
        if not rows:
            continue
        per[scen] = {
            "n": len(rows),
            "material_rate": sum(r["material"] for r in rows) / len(rows),
            "median_R_shared": median([r["R_shared"] for r in rows]),
            "median_R_bayes_uniform": median([r["R_bayes_uniform"] for r in rows]),
            "mean_RR": {a: sum(r["RR_by_arm"][a] for r in rows) / len(rows)
                        for a in rows[0]["RR_by_arm"]},
            "current_fired_rate": sum(1 for r in rows
                                      if r["current_meta"].get("n_orders")) / len(rows),
        }
    scen_ok = [s for s, v in per.items() if v["material_rate"] >= 0.20]
    v = ("TORPEDO_PARTIAL_OBSERVABILITY" if len(scen_ok) >= 2
         else "PUBLIC_PROXY_AMBIGUITY (unchanged; material regret not confirmed)")
    return {"verdict": v, "scenarios_with_material_ge_20pct": scen_ok,
            "material_rate_pooled": sum(r["material"] for r in st) / len(st),
            "median_R_shared_pooled": median([r["R_shared"] for r in st]),
            "per_scenario": per}


def fig_movement(mv, mvres):
    states = mv["states"]
    rows = []
    for r in states:
        base = r["arms"].get("CURRENT_POLICY")
        if not base or "error" in base:
            continue
        for arm in ARMS:
            a = r["arms"].get(arm)
            if not a or "error" in a:
                continue
            rows.append({"scenario": r["scenario"], "arm": arm,
                         "d0": a["L0"]["L0"] - base["L0"]["L0"],
                         "d1": a["L1"]["U_team"] - base["L1"]["U_team"],
                         "bucket": r["bucket"], "side": r["side"]})
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.8))
    for ax, key, lab in ((axes[0], "d0", "delta local (L0 EH)"),
                         (axes[1], "d1", "delta team (L1 U_team)"),
                         (axes[2], "ext", "externality (L1 - L0)")):
        data = []
        for arm in ARMS:
            v = [(x[key] if key != "ext" else x["d1"] - x["d0"])
                 for x in rows if x["arm"] == arm]
            data.append(v or [0.0])
        bp = ax.boxplot(data, tick_labels=LABELS,
                        showfliers=True, patch_artist=True)
        for patch in bp["boxes"]:
            patch.set_facecolor("#8ea9db")
        ax.axhline(0, c="#c00000", lw=1)
        ax.set_title(lab, fontsize=9)
        ax.tick_params(axis="x", labelsize=7)
    fig.suptitle(f"B1E natural movement census — {mvres['verdict']} "
                 f"({len(states)} state-sides, {mvres['inputs']['mechanism_rows_in_census']} mechanism row)",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(F / "fig01_b1e_movement_local_team_ext.png", bbox_inches="tight")
    plt.close(fig)
    # per-scenario opportunity rates
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    scen = list(mvres["per_scenario"])
    width = 0.2
    for i, arm in enumerate(ARMS):
        rates = [mvres["per_scenario"][s].get(arm, {}).get("mech_opp_rate", 0) for s in scen]
        ax.bar([x + i * width for x in range(len(scen))], rates, width,
               label=arm.replace("_", " ").title())
    ax.axhline(0.20, ls="--", c="#c00000", lw=1)
    ax.set_xticks([x + 1.5 * width for x in range(len(scen))])
    ax.set_xticklabels(scen, fontsize=8)
    ax.set_ylabel("MECHANISM_OPPORTUNITY rate")
    ax.set_title("local opportunity rate by scenario (frozen 20% line)\n"
                 "legend order: BEAM · REPAIRED · PRE_FIX · RANDOM", fontsize=8)
    ax.legend(fontsize=7)  # arms named in the caption
    fig.tight_layout()
    fig.savefig(F / "fig02_b1e_opportunity_rates.png", bbox_inches="tight")
    plt.close(fig)
    # bucket coverage
    fig, ax = plt.subplots(figsize=(5.6, 3.2))
    cnt = Counter("|".join(r["bucket"]) for r in states)
    ax.bar(list(cnt), [cnt[k] for k in cnt], color="#548235")
    ax.set_ylabel("state-sides")
    ax.set_title("B1E strata actually filled\n(structural shortfalls are reported, not back-filled)",
                 fontsize=9)
    fig.tight_layout()
    fig.savefig(F / "fig03_b1e_strata.png", bbox_inches="tight")
    plt.close(fig)


def fig_torpedo(tv, tvres):
    st = tv["states"]
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.6))
    arms = list(st[0]["RR_by_arm"]) if st else []
    means = {a: [r["RR_by_arm"][a] for r in st] for a in arms}
    tshort = {"HOLD": "HOLD", "CURRENT_ADAPTIVE": "ADAPT",
              "INTERCEPT_ASSIST": "INTERCEPT", "PUBLIC_SET_COVER": "PUB_SET",
              "PUBLIC_BELIEF_AWARE": "PUB_BAYES", "FULL_STATE_CEILING": "FULLSTATE"}
    bp = axes[0].boxplot([means[a] for a in arms],
                         tick_labels=[tshort.get(a, a[:8]) for a in arms],
                         patch_artist=True, showfliers=True)
    for p in bp["boxes"]:
        p.set_facecolor("#8ea9db")
    axes[0].set_ylabel("RouteReduction")
    axes[0].set_title("route reduction by arm (n=%d states)" % len(st), fontsize=9)
    axes[0].tick_params(axis="x", labelsize=7)
    axes[1].scatter([r["R_shared"] for r in st], [r["R_bayes_uniform"] for r in st],
                    s=22, c="#c00000")
    axes[1].axvline(0.25, ls="--", c="k", lw=1)
    axes[1].set_xlabel("R_shared (minimax shared-action regret)")
    axes[1].set_ylabel("R_Bayes (uniform prior)")
    axes[1].set_title("shared vs Bayes regret", fontsize=9)
    for s in SCENARIOS:
        rr = [r["RR_by_arm"]["FULL_STATE_CEILING"] - r["RR_by_arm"]["PUBLIC_SET_COVER"]
              for r in st if r["scenario"] == s]
        if rr:
            axes[2].scatter([s] * len(rr), rr, s=22, label=s)
    axes[2].axhline(0, c="k", lw=0.8)
    axes[2].set_ylabel("full-state ceiling − public set-cover")
    axes[2].set_title("public vs full-state gap", fontsize=9)
    axes[2].tick_params(axis="x", labelsize=7)
    fig.suptitle(f"B1E torpedo census — {tvres['verdict']}", fontsize=10)
    fig.tight_layout()
    fig.savefig(F / "fig04_b1e_torpedo.png", bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    mv = load("b1e_movement_census.json")
    tv = load("b1e_torpedo_census.json")
    mvres = movement_verdict(mv)
    tvres = torpedo_verdict(tv)
    out = {"movement": mvres, "torpedo": tvres}
    (M / "b1e_verdicts.json").write_text(json.dumps(out, indent=1, default=str))
    if mv:
        fig_movement(mv, mvres)
    if tv:
        fig_torpedo(tv, tvres)
    print(json.dumps({"movement_verdict": mvres["verdict"],
                      "movement_inputs": mvres.get("inputs"),
                      "torpedo_verdict": tvres["verdict"],
                      "torpedo_material_rate": tvres.get("material_rate_pooled"),
                      "torpedo_scenarios_material": tvres.get("scenarios_with_material_ge_20pct")},
                     indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
