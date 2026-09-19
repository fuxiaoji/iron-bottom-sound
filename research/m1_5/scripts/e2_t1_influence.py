"""E2-T1: does strategic influence change the chosen torpedo action?

Samples reachable TORPEDO_PLANNING states from real matches (both sides
decide each turn), enumerates the planner's own torpedo options per decision,
and compares three fixed scorers (PRE_REGISTRATION.md):

  Direct-only   rank by expected_hits
  Influence-only rank by the influence composite (planner's counterfactual
                 response fields, min-max normalised within the state)
  Hybrid        expected_hits + 1.0 * influence composite

No rollouts at this stage; the planner's own scores are used only as heuristic
rankings, never as ground truth (that is E2-T2's job).

    PYTHONPATH=backend/src:research/m1_5/scripts .venv/bin/python \
        research/m1_5/scripts/e2_t1_influence.py
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "backend" / "src"))

from iron_bottom_sound.engine import IronBottomEngine  # noqa: E402
from iron_bottom_sound.models import GameOptions, Phase, Side  # noqa: E402
from iron_bottom_sound.tactical import PROFILES, TacticalCommander  # noqa: E402
from iron_bottom_sound.torpedo_tactics import AdaptiveTorpedoPlanner  # noqa: E402

OUT = REPO / "research" / "m1_5"

SCENARIOS = ("IBS-S-01", "IBS-S-03")
PROFILES_LIST = ("adaptive", "direct_attack", "area_denial",
                 "break_crossing_t", "crossfire")
SEEDS = tuple(range(1, 31))
TARGET_STATES = 200
LAMBDA = 1.0  # pre-registered
INFLUENCE_FIELDS = ("forced_deviation", "speed_loss", "fire_position_loss",
                    "crossing_t_loss", "formation_split", "local_force_ratio_gain")


def minmax(vals: list[float]) -> list[float]:
    if not vals:
        return []
    lo, hi = min(vals), max(vals)
    if hi - lo < 1e-12:
        return [0.0] * len(vals)
    return [(v - lo) / (hi - lo) for v in vals]


def collect_decisions():
    """Run matches; at every TORPEDO_PLANNING phase record both sides' option sets."""
    decisions = []
    matches_started = 0
    per_scenario = TARGET_STATES // len(SCENARIOS)
    per_profile = max(1, per_scenario // len(PROFILES_LIST))
    for scenario in SCENARIOS:
        n_scen = sum(1 for x in decisions if x["scenario"] == scenario)
        for profile in PROFILES_LIST:
            n_prof = sum(1 for x in decisions
                         if x["scenario"] == scenario and x["profile"] == profile)
            for seed in SEEDS:
                if n_prof >= per_profile:
                    break
                eng = IronBottomEngine()
                state = eng.reset(scenario, seed, GameOptions(mode="llm"))
                sessions = {Side.AXIS: TacticalCommander(profile=PROFILES[profile]),
                            Side.ALLIES: TacticalCommander(profile=PROFILES[profile])}
                matches_started += 1
                guard = 0
                while state.phase != Phase.COMPLETE and guard < 200:
                    guard += 1
                    if state.phase == Phase.TORPEDO_PLANNING:
                        for side in Side:
                            n_prof = sum(1 for x in decisions
                                         if x["scenario"] == scenario
                                         and x["profile"] == profile)
                            if n_prof < per_profile:
                                dec = capture_decision(eng, state, side, profile)
                                if dec:
                                    decisions.append(dec)
                        # continue the real match: both sides submit torpedo plans
                    if state.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                                       Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                                       Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
                        for side in Side:
                            if side.value not in state.submitted_orders:
                                batch = sessions[side].choose_plan(
                                    eng, state.game_id, side)[1]
                                eng.submit_orders(state.game_id, batch)
                    eng.advance(state.game_id)
                n_scen = sum(1 for x in decisions if x["scenario"] == scenario)
                if n_scen >= per_scenario:
                    break
    return decisions, matches_started


def capture_decision(eng, state, side, profile_name):
    planner = AdaptiveTorpedoPlanner(PROFILES[profile_name])
    routes = planner.enemy_routes(eng, state, side)
    raw = eng.torpedo_tactical_combos(state, side)
    if not raw:
        return None
    doctrine = planner._select_doctrine(eng, state, side, routes, raw)
    options = []
    for row in raw:
        opt = planner._score_option(row, doctrine, routes)
        if opt is None:
            continue
        options.append({
            "option_id": opt.option_id,
            "doctrine": str(opt.doctrine),
            "target_id": opt.target_id,
            "order": opt.order,
            "expected_hits": float(opt.expected_hits),
            "salvo": int(opt.order.get("count", 1)),
            "denial_score": float(opt.denial_score),
            "influence_raw": {f: float(getattr(opt.response, f))
                              for f in INFLUENCE_FIELDS},
            "route_changed": bool(opt.response.route_changed),
            "baseline_route": opt.response.baseline_route,
            "threatened_route": opt.response.threatened_route,
        })
    if len(options) < 2:
        return None
    # influence composite: per-field min-max across the state's candidates
    comp = []
    for f in INFLUENCE_FIELDS:
        comp.append(minmax([o["influence_raw"][f] for o in options]))
    rc = minmax([1.0 if o["route_changed"] else 0.0 for o in options])
    for i, o in enumerate(options):
        o["influence_composite"] = statistics.mean(
            [comp[k][i] for k in range(len(INFLUENCE_FIELDS))] + [rc[i]])
    return {
        "scenario": state.scenario_id,
        "seed": state.seed,
        "turn": state.turn,
        "side": side.value,
        "profile": profile_name,
        "doctrine": str(doctrine),
        "n_options": len(options),
        "options": options,
    }


def top1(options, keyfn):
    return max(options, key=keyfn)["option_id"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=TARGET_STATES)
    args = ap.parse_args()
    t0 = time.time()
    decisions, matches = collect_decisions()
    print(f"sampled {len(decisions)} decisions from {matches} matches "
          f"({time.time()-t0:.0f}s)", flush=True)

    rows = []
    for d in decisions:
        opts = d["options"]
        t_direct = top1(opts, lambda o: (-o["expected_hits"], o["salvo"], o["option_id"]))
        t_infl = top1(opts, lambda o: (-o["influence_composite"], o["option_id"]))
        t_hybrid = top1(opts, lambda o: (-(o["expected_hits"] + LAMBDA * o["influence_composite"]),
                                         o["option_id"]))
        # degeneracy flag: direct scores all tied (direct cannot discriminate)
        eh = [o["expected_hits"] for o in opts]
        direct_degenerate = (max(eh) - min(eh)) < 1e-9
        # spearman-ish rank agreement direct vs hybrid
        order_direct = {o["option_id"]: i for i, o in enumerate(
            sorted(opts, key=lambda o: (-o["expected_hits"], o["option_id"])))}
        order_hybrid = {o["option_id"]: i for i, o in enumerate(
            sorted(opts, key=lambda o: (-(o["expected_hits"] + LAMBDA * o["influence_composite"]),
                                        o["option_id"])))}
        n = len(opts)
        d2 = sum((order_direct[o["option_id"]] - order_hybrid[o["option_id"]]) ** 2
                 for o in opts)
        rho = 1 - 6 * d2 / (n * (n * n - 1)) if n > 1 else 1.0
        rows.append({
            "scenario": d["scenario"], "seed": d["seed"], "turn": d["turn"],
            "side": d["side"], "profile": d["profile"], "doctrine": d["doctrine"],
            "n_options": d["n_options"],
            "top_direct": t_direct, "top_influence": t_infl, "top_hybrid": t_hybrid,
            "hybrid_changes_top": t_hybrid != t_direct,
            "influence_changes_top": t_infl != t_direct,
            "direct_degenerate": direct_degenerate,
            "rank_corr_direct_hybrid": rho,
            "max_influence_composite": max(o["influence_composite"] for o in opts),
            "max_expected_hits": max(eh),
        })

    (OUT / "metrics" / "e2_t1_decisions.json").write_text(
        json.dumps(decisions, ensure_ascii=False))
    import csv
    with (OUT / "metrics" / "e2_t1_rows.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    def rate(key, subset=None):
        rs = [r for r in rows if (subset is None or subset(r))]
        return (sum(1 for r in rs if r[key]) / len(rs), len(rs)) if rs else (None, 0)

    hyb_all, n_all = rate("hybrid_changes_top")
    hyb_nd, n_nd = rate("hybrid_changes_top", lambda r: not r["direct_degenerate"])
    inf_all, _ = rate("influence_changes_top")
    inf_nd, _ = rate("influence_changes_top", lambda r: not r["direct_degenerate"])
    corrs = [r["rank_corr_direct_hybrid"] for r in rows if not r["direct_degenerate"]]
    summary = {
        "n_decisions": len(rows),
        "n_matches_started": matches,
        "n_scenarios": len({r["scenario"] for r in rows}),
        "lambda": LAMBDA,
        "hybrid_vs_direct_top1_change_rate_all": hyb_all,
        "hybrid_vs_direct_top1_change_rate_nondegenerate": (hyb_nd, n_nd),
        "influence_only_vs_direct_top1_change_rate_all": inf_all,
        "influence_only_vs_direct_top1_change_rate_nondegenerate": (inf_nd, n_nd),
        "median_rank_corr_direct_hybrid_nondegenerate": statistics.median(corrs) if corrs else None,
        "per_scenario": {s: {
            "n": sum(1 for r in rows if r["scenario"] == s),
            "hybrid_change_rate": sum(1 for r in rows if r["scenario"] == s and r["hybrid_changes_top"]) /
                                  max(1, sum(1 for r in rows if r["scenario"] == s)),
        } for s in sorted({r["scenario"] for r in rows})},
        "per_profile": {p: {
            "n": sum(1 for r in rows if r["profile"] == p),
            "hybrid_change_rate": sum(1 for r in rows if r["profile"] == p and r["hybrid_changes_top"]) /
                                  max(1, sum(1 for r in rows if r["profile"] == p)),
        } for p in sorted({r["profile"] for r in rows})},
        "gate_threshold": 0.20,
    }
    (OUT / "metrics" / "e2_t1_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
