"""M2.3 verdict — applies PRE_REGISTRATION_M23 §5 (JTC) and §7 (BARD) literally.

    PYTHONPATH=backend/src:research/m2_3/scripts:research/m2_2r/scripts:research/m2_2/scripts:research/m2_1/scripts \
        .venv/bin/python research/m2_3/scripts/m23_verdict.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
M = ROOT / "metrics"
F = ROOT / "figures"
F.mkdir(exist_ok=True, parents=True)
sys.path.insert(0, str(HERE))
from b1e import SCENARIOS, _median  # noqa: E402

plt.rcParams.update({"figure.dpi": 140, "font.size": 9, "axes.grid": True,
                     "grid.alpha": 0.25, "axes.axisbelow": True})
ARMS = ["REPAIRED_RESEARCH_INTENT", "PER_SHIP_GREEDY", "JOINT_BEAM_SEARCH",
        "RANDOM_MATCHED_BUDGET"]
SHORT = {"REPAIRED_RESEARCH_INTENT": "REPAIRED", "PER_SHIP_GREEDY": "GREEDY",
         "JOINT_BEAM_SEARCH": "JOINT", "RANDOM_MATCHED_BUDGET": "RANDOM"}
FLOOR = {"I1_BROADSIDE": ("abs", 0.05), "I2_RANGE": ("hex", 2.0),
         "I3_RAKING": ("frac", 0.05)}


def load(name):
    p = M / name
    return json.loads(p.read_text()) if p.exists() else None


def opportunity(intent, rec):
    a = rec["arms"]
    cur = a.get("CURRENT_PRODUCTION_POLICY")
    if not cur:
        return {}
    out = {}
    for arm in ARMS:
        v = a.get(arm)
        if not v:
            out[arm] = None
            continue
        dm = v["L0"]["M"] - cur["L0"]["M"]
        du = v["L1"]["U_team"] - cur["L1"]["U_team"]
        kind, th = FLOOR[intent]
        if intent == "I2_RANGE":
            cur_dist = cur["L0"]["distance"]
            arm_dist = v["L0"]["distance"]
            exec_ok = bool(v["L0"]["executable"] and cur["L0"]["executable"])
            mech = (cur_dist is not None and arm_dist is not None
                    and abs(arm_dist - cur_dist) >= th and exec_ok)
        elif intent == "I3_RAKING":
            mech = bool(dm >= th and v["L0"]["raking"] >= 1)
        else:
            mech = bool(dm >= th and dm >= 0.25 * max(abs(cur["L0"]["M"]), 1e-9))
        out[arm] = {"dM": dm, "dU": du, "externality": du - dm,
                    "mech_opp": mech, "team_beneficial": bool(mech and du > 0),
                    "neg_ext": bool(dm > 0 and du < 0)}
    return out


def jtc_verdict(jtc):
    if not jtc or not jtc.get("states"):
        return {"verdict": "NO_DATA"}
    rows = []
    for rec in jtc["states"]:
        opp = opportunity(rec["intent"], rec)
        for arm, v in opp.items():
            if v:
                rows.append({"panel": rec["panel"], "scenario": rec["scenario"],
                             "seed": rec["seed"], "turn": rec["turn"],
                             "side": rec["side"], "intent": rec["intent"],
                             "arm": arm, **v})
    per = {}
    for scen in SCENARIOS:
        for intent in ("I1_BROADSIDE", "I2_RANGE", "I3_RAKING"):
            sr = [r for r in rows if r["scenario"] == scen and r["intent"] == intent]
            if not sr:
                continue
            d = {}
            for arm in ARMS:
                ar = [r for r in sr if r["arm"] == arm]
                if not ar:
                    continue
                opp_states = [r for r in ar if r["mech_opp"]]
                d[arm] = {
                    "n": len(ar),
                    "mech_opp_rate": sum(r["mech_opp"] for r in ar) / len(ar),
                    "team_beneficial_rate": sum(r["team_beneficial"] for r in ar) / len(ar),
                    "neg_ext_rate": sum(r["neg_ext"] for r in ar) / len(ar),
                    "median_dM": _median([r["dM"] for r in ar]),
                    "cond_median_dU_on_opp": _median([r["dU"] for r in opp_states]),
                    "cond_mean_dU_on_opp": (sum(r["dU"] for r in opp_states)
                                            / len(opp_states)) if opp_states else None,
                    "n_opp": len(opp_states),
                }
            per[f"{scen}|{intent}"] = d
    # JTC_MULTI_INTENT: >=2 intents with team-beneficial opportunity >=20% in >=2 scenarios
    intent_scen = defaultdict(set)
    for key, d in per.items():
        scen, intent = key.split("|")
        j = d.get("JOINT_BEAM_SEARCH")
        if j and j["team_beneficial_rate"] >= 0.20:
            intent_scen[intent].add(scen)
    multi = {i: sorted(s) for i, s in intent_scen.items() if len(s) >= 2}
    # JTC_JOINT_COORDINATION_EFFECT — PRE_REGISTRATION_M23 §4.2 requires the SAME
    # opportunity-state set for every arm: the set where the intent-constrained
    # search (JOINT) achieves the mechanism.  (M23-F2: the first implementation
    # averaged each arm over its own opportunity set, which compares different
    # state sets.)
    common_keys = {(r["panel"], r["scenario"], r["seed"], r["turn"], r["side"],
                    r["intent"])
                   for r in rows if r["arm"] == "JOINT_BEAM_SEARCH" and r["mech_opp"]}
    def mean_on_common(arm):
        sub = [r["dU"] for r in rows
               if r["arm"] == arm and (r["panel"], r["scenario"], r["seed"],
                                       r["turn"], r["side"],
                                       r["intent"]) in common_keys]
        return (sum(sub) / len(sub)) if sub else None
    joint_mean = mean_on_common("JOINT_BEAM_SEARCH")
    gaps = {}
    for arm in ("PER_SHIP_GREEDY", "RANDOM_MATCHED_BUDGET"):
        m = mean_on_common(arm)
        ok = (joint_mean is not None and m is not None
              and joint_mean >= m + 0.25 * max(0.05, abs(m)))
        gaps[arm] = {"mean_dU_on_common_opp_set": m, "beat_by_25pct": bool(ok)}
    gaps["common_opportunity_states"] = len(common_keys)
    coord = bool(joint_mean is not None and joint_mean > 0
                 and gaps["PER_SHIP_GREEDY"]["beat_by_25pct"]
                 and gaps["RANDOM_MATCHED_BUDGET"]["beat_by_25pct"])
    # not carried by the BROADSIDE bug: holds for I2/I3 as well
    non_broad = [i for i in multi if i != "I1_BROADSIDE"]
    single_scenario = len({s for i in multi for s in multi[i]}) <= 1
    verdict = ("PASS" if (len(multi) >= 2 and coord and non_broad and not single_scenario)
               else "FAIL")
    return {"verdict": verdict,
            "JTC_MULTI_INTENT": "PASS" if len(multi) >= 2 else "FAIL",
            "JTC_JOINT_COORDINATION_EFFECT": "PASS" if coord else "FAIL",
            "intents_with_team_beneficial_ge20pct_in_ge2_scenarios": multi,
            "not_carried_by_broadside_bug": bool(non_broad),
            "single_scenario_only": single_scenario,
            "joint_mean_dU_on_common_opportunity_set": joint_mean,
            "gaps_vs": gaps,
            "per_scenario_intent": per,
            "n_rows": len(rows),
            "rejections": jtc.get("rejections"),
            "panels": dict(Counter(r["panel"] for r in jtc["states"])),
            "damaged_pool_diagnostics": jtc.get("damaged_pool_diagnostics")}


def bard_verdict(bard):
    if not bard or not bard.get("sets"):
        return {"verdict": "NO_DATA"}
    sets = bard["sets"]
    per = {}
    for scen in SCENARIOS:
        rows = [r for r in sets if r["scenario"] == scen]
        if not rows:
            continue
        per[scen] = {
            "n": len(rows),
            "material_true_rate": sum(r["material_true"] for r in rows) / len(rows),
            "material_match_rate": sum(r["material_match"] for r in rows) / len(rows),
            "material_naive_rate": sum(r["material_naive"] for r in rows) / len(rows),
            "median_R_shared_true": _median([r["true_risk"]["R_shared"] for r in rows]),
            "median_R_shared_match": _median([r["match_risk"]["R_shared"] for r in rows]),
            "no_eps_good_rate": sum(1 for r in rows
                                    if not r["true_risk"]["eps_good_shared"]) / len(rows),
            "planners": {k: sum(r["planners"][k] for r in rows) / len(rows)
                         for k in rows[0]["planners"]},
        }
    pooled_match = sum(r["material_match"] for r in sets) / len(sets)
    pooled_true = sum(r["material_true"] for r in sets) / len(sets)
    scen_match = [s for s, v in per.items() if v["material_match_rate"] >= 0.20]
    scen_conflict = [s for s, v in per.items() if v["no_eps_good_rate"] >= 0.20]
    # public recovery: best public planner vs ceiling, per scenario, scored on truth
    recov = {}
    for s, v in per.items():
        pub = max(v["planners"][k] for k in ("PUBLIC_SET_COVER_ROBUST",
                                             "PUBLIC_BELIEF_EXPECTED"))
        ceil = v["planners"]["FULL_STATE_CEILING"]
        recov[s] = {"best_public": pub, "ceiling": ceil,
                    "ratio": (pub / ceil) if ceil > 1e-9 else None}
    ok_recovery = [s for s, v in recov.items()
                   if v["ratio"] is not None and v["ratio"] >= 0.50]
    matched_ok = len(scen_match) >= 2
    conflict_ok = len(scen_conflict) >= 2
    recovery_ok = len(ok_recovery) >= 2
    if matched_ok and conflict_ok and recovery_ok:
        v = "PASS"
    elif matched_ok and conflict_ok and not recovery_ok:
        v = "INFORMATION_LIMIT_ONLY"
    elif pooled_match < 0.20:
        v = "ARTIFACT"
    else:
        v = "FAIL"
    return {"verdict": v,
            "BARD_MATCHED_CONTROL": "PASS" if matched_ok else "FAIL",
            "BARD_ACTION_CONFLICT": "PASS" if conflict_ok else "FAIL",
            "BARD_PUBLIC_RECOVERY": "PASS" if recovery_ok else "FAIL",
            "material_rate_true": pooled_true, "material_rate_matched": pooled_match,
            "material_rate_naive": sum(r["material_naive"] for r in sets) / len(sets),
            "scenarios_material_after_match": scen_match,
            "scenarios_no_eps_good": scen_conflict,
            "recovery_ratios": recov, "scenarios_recovery_ge50pct": ok_recovery,
            "reading_note": ("pooled matched rate %.3f vs the 20%% bar; the "
                             ">=2-scenarios clause is met by %d scenario(s)"
                             % (pooled_match, len(scen_match))),
            "per_scenario": per, "n_sets": len(sets),
            "rejections": bard.get("rejections"),
            "degenerate_matched_matrices": sum(
                1 for r in sets if r.get("match_diagnostics", {}).get("degenerate"))}


def figures(jtc_res, bard_res, jtc, bard):
    # fig 1: JTC local vs team by arm (opportunity states)
    if jtc and jtc.get("states"):
        rows = []
        for rec in jtc["states"]:
            opp = opportunity(rec["intent"], rec)
            for arm, v in opp.items():
                if v:
                    rows.append({"intent": rec["intent"], "arm": arm, **v})
        fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
        for ax, intent in zip(axes, ("I1_BROADSIDE", "I2_RANGE", "I3_RAKING")):
            data = [[r["dU"] for r in rows if r["intent"] == intent and r["arm"] == a]
                    for a in ARMS]
            bp = ax.boxplot([d or [0.0] for d in data],
                            tick_labels=[SHORT[a] for a in ARMS],
                            patch_artist=True, showfliers=False)
            for p in bp["boxes"]:
                p.set_facecolor("#8ea9db")
            ax.axhline(0, c="#c00000", lw=1)
            ax.set_title(intent, fontsize=9)
            ax.set_ylabel("Δ team utility")
        fig.suptitle("M2.3 JTC — joint vs per-ship greedy vs random (ΔU, all states)",
                     fontsize=10)
        fig.tight_layout()
        fig.savefig(F / "fig01_jtc_team_by_arm.png", bbox_inches="tight")
        plt.close(fig)
        # fig 2: opportunity/team-beneficial rates per intent x scenario (JOINT arm)
        fig, ax = plt.subplots(figsize=(9, 3.6))
        keys = list(jtc_res["per_scenario_intent"])
        keys.sort()
        labels, tb, mo = [], [], []
        for k in keys:
            d = jtc_res["per_scenario_intent"][k]
            j = d.get("JOINT_BEAM_SEARCH")
            if not j:
                continue
            labels.append(k.replace("IBS-", "").replace("|I", "\nI"))
            tb.append(j["team_beneficial_rate"])
            mo.append(j["mech_opp_rate"])
        idx = range(len(labels))
        ax.bar([i - 0.2 for i in idx], mo, 0.4, label="mechanism opportunity")
        ax.bar([i + 0.2 for i in idx], tb, 0.4, label="team-beneficial")
        ax.axhline(0.20, ls="--", c="#c00000", lw=1)
        ax.set_xticks(list(idx))
        ax.set_xticklabels(labels, fontsize=7)
        ax.set_ylabel("rate")
        ax.set_title("M2.3 JTC — JOINT_BEAM opportunity rates (frozen 20% line)", fontsize=9)
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(F / "fig02_jtc_opportunity_rates.png", bbox_inches="tight")
        plt.close(fig)
        # fig 3: joint vs greedy scatter on opportunity states
        fig, ax = plt.subplots(figsize=(5.4, 4))
        j = {(r["scenario"], r["seed"], r["turn"], r["side"], r["intent"]): r
             for r in jtc["states"]}
        xs, ys = [], []
        for rec in jtc["states"]:
            opp = opportunity(rec["intent"], rec)
            if opp.get("JOINT_BEAM_SEARCH", {}) and opp["JOINT_BEAM_SEARCH"]["mech_opp"]:
                g = opp.get("PER_SHIP_GREEDY", {})
                if g:
                    xs.append(g["dU"])
                    ys.append(opp["JOINT_BEAM_SEARCH"]["dU"])
        ax.scatter(xs, ys, s=22, c="#2e75b6")
        lim = [min(xs + ys + [0]) - 1, max(xs + ys + [0]) + 1]
        ax.plot(lim, lim, ls="--", c="k", lw=1)
        ax.set_xlabel("PER_SHIP_GREEDY ΔU")
        ax.set_ylabel("JOINT_BEAM ΔU")
        ax.set_title("JTC — joint vs greedy on opportunity states", fontsize=9)
        fig.tight_layout()
        fig.savefig(F / "fig03_joint_vs_greedy.png", bbox_inches="tight")
        plt.close(fig)
    # fig 4: BARD heatmap of the decisive set + matched control
    if bard and bard.get("sets"):
        best = max(bard["sets"], key=lambda r: r["match_risk"]["R_shared"])
        fig, axes = plt.subplots(1, 2, figsize=(11, 4))
        for ax, key, title in ((axes[0], "payoff_matrix", "true hidden set"),
                               (axes[1], "payoff_matrix_matched",
                                "size/diversity-matched control")):
            mat = best[key]
            import numpy as np
            arr = np.array(mat)
            im = ax.imshow(arr, aspect="auto", cmap="viridis", vmin=0, vmax=1)
            ax.set_xlabel("torpedo action index")
            ax.set_ylabel("hidden sealed route (variant)")
            ax.set_title(f"{title} — {best['scenario']} s{best['seed']} t{best['turn']}",
                         fontsize=9)
            plt.colorbar(im, ax=ax, fraction=0.046)
        fig.suptitle(f"BARD action-conflict matrix — R_shared true "
                     f"{best['true_risk']['R_shared']:.2f} vs matched "
                     f"{best['match_risk']['R_shared']:.2f}", fontsize=10)
        fig.tight_layout()
        fig.savefig(F / "fig04_bard_conflict_matrix.png", bbox_inches="tight")
        plt.close(fig)
        # fig 5: R_shared true vs matched per set
        fig, ax = plt.subplots(figsize=(7.5, 3.6))
        lab = [f"{r['scenario'][-5:]} s{r['seed']}t{r['turn']}" for r in bard["sets"]]
        x = range(len(lab))
        ax.bar([i - 0.2 for i in x], [r["true_risk"]["R_shared"] for r in bard["sets"]],
               0.4, label="R_shared true hidden set")
        ax.bar([i + 0.2 for i in x], [r["match_risk"]["R_shared"] for r in bard["sets"]],
               0.4, label="R_shared matched control")
        ax.axhline(0.25, ls="--", c="#c00000", lw=1)
        ax.set_xticks(list(x))
        ax.set_xticklabels(lab, fontsize=6, rotation=45)
        ax.set_ylabel("R_shared")
        ax.legend(fontsize=7)
        ax.set_title("M2.3 BARD — matched control attenuates the conflict", fontsize=9)
        fig.tight_layout()
        fig.savefig(F / "fig05_bard_matched_control.png", bbox_inches="tight")
        plt.close(fig)


def main() -> int:
    jtc = load("m23_jtc_census.json")
    bard = load("m23_bard.json")
    j = jtc_verdict(jtc)
    b = bard_verdict(bard)
    if j["verdict"] == "PASS" and b["verdict"] != "PASS":
        mainline = "JOINT_TACTICAL_COMPILATION"
    elif b["verdict"] == "PASS" and j["verdict"] != "PASS":
        mainline = "BELIEF_AWARE_ROUTE_DENIAL"
    else:
        mainline = "NONE"
    out = {"JTC": j, "BARD": b, "MAINLINE_CANDIDATE": mainline}
    (M / "m23_verdicts.json").write_text(json.dumps(out, indent=1, default=str))
    try:
        figures(j, b, jtc, bard)
    except Exception as exc:  # noqa: BLE001
        print("figure error:", type(exc).__name__, exc)
    print(json.dumps({k: v for k, v in j.items() if k != "per_scenario_intent"},
                     indent=1, default=str))
    print(json.dumps({k: v for k, v in b.items() if k != "per_scenario"},
                     indent=1, default=str))
    print("MAINLINE_CANDIDATE =", mainline)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
