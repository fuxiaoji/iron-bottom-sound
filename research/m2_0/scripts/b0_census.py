"""Track B0: natural command-failure census in realistic mode.

50 matches/scenario pilot (S-01/S-03/EM-01), profiles from the M2-0 pool,
event census per match with sequence dedupe and state-derived disruption
counting (see FAILURES F2). Budget: <=500 realistic matches total.

    PYTHONPATH=backend/src:research/m2_0/scripts .venv/bin/python \
        research/m2_0/scripts/b0_census.py [--per-scenario 50]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "backend" / "src"))
OUT = REPO / "research" / "m2_0"

SCENARIOS = ("IBS-S-01", "IBS-S-03", "IBS-S-EM-01")
PROFILE_POOL = ("balanced", "fleet", "line", "brawl", "cautious")
BUDGET_TOTAL = 500


def one_match(job):
    scenario, seed, axis_p, allies_p = job
    from iron_bottom_sound.engine import IronBottomEngine
    from iron_bottom_sound.models import GameOptions, Phase, Side
    from iron_bottom_sound.realistic_command import RealisticCommander
    t0 = time.perf_counter()
    eng = IronBottomEngine()
    st = eng.reset(scenario, seed, GameOptions(mode="llm", realistic_command=True))
    se = {Side.AXIS: RealisticCommander(), Side.ALLIES: RealisticCommander()}
    seen_seq = set()
    counts = {"formation_command_transferred": 0, "ship_detached": 0,
              "ship_withdrawn": 0, "formation_created": 0}
    disruption_pairs = set()
    error = None
    guard = 0
    try:
        while st.phase != Phase.COMPLETE and guard < 400:
            guard += 1
            for e in st.events:
                if e.sequence not in seen_seq:
                    seen_seq.add(e.sequence)
                    if e.type in counts:
                        counts[e.type] += 1
            for f in st.formations.values():
                if f.disruption_turn is not None:
                    disruption_pairs.add((f.id, f.disruption_turn))
            if st.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                            Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                            Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
                for side in Side:
                    if side.value not in st.submitted_orders:
                        b = se[side].choose_plan(eng, st.game_id, side)[1]
                        res = eng.submit_orders(st.game_id, b)
                        if not res.valid:
                            error = f"invalid: {res.errors[:2]}"
                            break
                if error:
                    break
            eng.advance(st.game_id)
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
    return {
        "scenario": scenario, "seed": seed, "axis": axis_p, "allies": allies_p,
        "completed": st.phase == Phase.COMPLETE and error is None,
        "error": error, "turns": st.turn,
        "seconds": time.perf_counter() - t0,
        "transfers": counts["formation_command_transferred"],
        "detaches": counts["ship_detached"],
        "withdrawn": counts["ship_withdrawn"],
        "disruption_turns": len(disruption_pairs),
        "dissolved": sum(1 for f in st.formations.values() if f.status == "dissolved"),
        "flagship_sunk": sum(
            1 for f in st.formations.values()
            if st.ships.get(f.flagship_id) is not None
            and st.ships[f.flagship_id].sunk),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-scenario", type=int, default=50)
    args = ap.parse_args()
    jobs = []
    for scenario in SCENARIOS:
        for i in range(args.per_scenario):
            seed = 100 + i * 7
            axis = PROFILE_POOL[i % len(PROFILE_POOL)]
            allies = PROFILE_POOL[(i // len(PROFILE_POOL) + i) % len(PROFILE_POOL)]
            jobs.append((scenario, seed, axis, allies))
    assert len(jobs) <= BUDGET_TOTAL, "B0 budget cap"
    print(f"B0 census: {len(jobs)} realistic matches", flush=True)
    t0 = time.time()
    rows = []
    with ProcessPoolExecutor(max_workers=10) as ex:
        for i, r in enumerate(ex.map(one_match, jobs)):
            rows.append(r)
            if (i + 1) % 20 == 0:
                done = sum(1 for x in rows if x["completed"])
                print(f"  {i+1}/{len(jobs)} ({time.time()-t0:.0f}s) completed={done}",
                      flush=True)
    summary = {"n": len(rows), "completed": sum(1 for r in rows if r["completed"]),
               "wall_min": (time.time() - t0) / 60}
    for scen in SCENARIOS:
        sub = [r for r in rows if r["scenario"] == scen]
        matches_with = sum(1 for r in sub if r["transfers"] > 0 or r["disruption_turns"] > 0)
        summary[scen] = {
            "n": len(sub),
            "completed": sum(1 for r in sub if r["completed"]),
            "matches_with_transfer_or_disruption": matches_with,
            "rate": matches_with / len(sub) if sub else 0,
            "total_transfers": sum(r["transfers"] for r in sub),
            "total_disruptions": sum(r["disruption_turns"] for r in sub),
            "total_detaches": sum(r["detaches"] for r in sub),
            "total_dissolved": sum(r["dissolved"] for r in sub),
            "profiles_seen": len({(r["axis"], r["allies"]) for r in sub}),
        }
    all_disrupt = [r for r in rows if r["disruption_turns"] > 0 or r["transfers"] > 0]
    summary["overall"] = {
        "matches_with_transfer_or_disruption": len(all_disrupt),
        "rate": len(all_disrupt) / len(rows),
        "independent_disruption_cases": sum(r["transfers"] for r in rows),
        "scenario_profile_cells": len({(r["scenario"], r["axis"], r["allies"])
                                       for r in all_disrupt}),
    }
    gate = {
        "c1_rate_ge_5pct": summary["overall"]["rate"] >= 0.05,
        "c2_cases_ge_30": summary["overall"]["independent_disruption_cases"] >= 30,
        "c3_multi_cell": summary["overall"]["scenario_profile_cells"] >= 3,
    }
    summary["gate"] = gate
    summary["verdict"] = ("PASS" if (gate["c1_rate_ge_5pct"] or gate["c2_cases_ge_30"])
                          and gate["c3_multi_cell"] else "B_FAIL_NATURALITY")
    (OUT / "metrics" / "b0_census.json").write_text(json.dumps(
        {"summary": summary, "rows": rows}, indent=1))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
