"""Offline behavioral evaluation of realistic AI styles; never touches the save DB."""
from __future__ import annotations

import argparse
import json
import time
import traceback
from collections import Counter
from pathlib import Path

from iron_bottom_sound.engine import IronBottomEngine, ORDER_PHASES
from iron_bottom_sound.models import GameOptions, Phase, Side
from iron_bottom_sound.realistic_command import RealisticCommander
from iron_bottom_sound.tactical import PROFILES


def evaluate(scenario, profile, opponent, seed, player_side, turn_limit=None, progress=False):
    started = time.perf_counter()
    engine = IronBottomEngine()
    state = engine.reset(scenario, seed, GameOptions(realistic_command=True, battle_report=False))
    commanders = {side: RealisticCommander(PROFILES[profile if side == player_side else opponent]) for side in Side}
    counters = Counter()
    for name in ("torpedo_launches", "friendly_collisions", "friendly_torpedo_hits", "emergency_stops"):
        counters[name] = 0
    states = Counter()
    residual_risks = []
    phases = 0
    failure = None
    failure_traceback = None
    failure_side = None
    max_plan_seconds = 0.0
    while state.phase != Phase.COMPLETE and (turn_limit is None or state.turn <= turn_limit):
        if phases > 1500:
            failure = "phase limit exceeded"
            break
        try:
            if state.phase in ORDER_PHASES:
                for side in Side:
                    failure_side = side.value
                    plan_start = time.perf_counter()
                    plan, batch, _audits = commanders[side].choose_plan(engine, state.game_id, side)
                    max_plan_seconds = max(max_plan_seconds, time.perf_counter() - plan_start)
                    result = engine.submit_orders(state.game_id, batch)
                    counters["orders_validated"] += 1
                    if not result.valid:
                        raise ValueError(result.errors)
                    if side == player_side and plan.tactical_analysis:
                        audit = plan.tactical_analysis
                        counters["predicted_friendly_conflicts"] += audit.get("predicted_friendly_conflicts", 0)
                        counters["predicted_torpedo_contacts"] += audit.get("predicted_torpedo_contacts", 0)
                        if audit.get("predicted_friendly_conflicts") or audit.get("predicted_torpedo_contacts"):
                            residual_risks.append({
                                "turn": state.turn, "conflicts": audit.get("remaining_conflicts", []),
                                "torpedo_contacts": audit.get("predicted_torpedo_contacts", 0),
                                "formations": audit.get("formations", []),
                                "constraints": [{
                                    "ship_id": ship.id, "formation_id": ship.formation_id,
                                    "command_status": ship.command_status, "position": ship.position.label,
                                    "forced_straight": ship.forced_straight_turns,
                                    "forced_circle": ship.forced_circle_turns,
                                    "speed_range": engine._legal_speed_range(ship, state.turn),
                                } for ship in state.ships.values() if ship.side == side and ship.position and not ship.sunk],
                            })
                        for row in audit.get("formations", []):
                            states[row["state"]] += 1
                            counters["coordinated_tasks"] += int(row.get("partner_id") is not None)
                            counters["crossing_t_improvements"] += int(row.get("crossing_t_after", 0) > row.get("crossing_t_before", 0) + 0.01)
                            counters["evade_tasks"] += int(row["state"] == "evade")
            previous_turn = state.turn
            failure_side = None
            engine.advance(state.game_id)
            if progress and state.turn != previous_turn:
                print(json.dumps({"progress": True, "scenario": scenario, "profile": profile,
                                  "seed": seed, "side": player_side.value, "turn": state.turn,
                                  "max_turns": state.max_turns, "score": state.score}), flush=True)
            phases += 1
        except Exception as error:  # Offline harness: record crashes, never count them as wins.
            failure = f"{type(error).__name__}: {error}"
            failure_traceback = traceback.format_exc()
            break
    for event in state.events:
        payload = event.payload
        if event.type == "torpedo_launched":
            ship = state.ships.get(payload.get("ship_id") or payload.get("launcher_ship_id"))
            if ship and ship.side == player_side:
                counters["torpedo_launches"] += 1
        elif event.type == "collision_check" and len(payload.get("ships", [])) == 2:
            left, right = (state.ships[item] for item in payload["ships"])
            if left.side == right.side == player_side and payload.get("collided"):
                counters["friendly_collisions"] += 1
        elif event.type == "torpedo_attack" and payload.get("attacker_side") == payload.get("target_side") == player_side.value:
            counters["friendly_torpedo_hits"] += payload.get("hits", 0)
        elif event.type == "formation_emergency_stop":
            for ship_id in payload.get("ship_ids", []) or [payload.get("ship_id")]:
                ship = state.ships.get(ship_id)
                if ship and ship.side == player_side:
                    counters["emergency_stops"] += 1
    completed = state.phase == Phase.COMPLETE
    replay_equal = False if failure else engine.replay(state.game_id).model_dump(mode="json") == state.model_dump(mode="json")
    return {
        "scenario": scenario, "profile": profile, "opponent": opponent, "seed": seed,
        "side": player_side.value, "completed": completed, "turn": state.turn,
        "phase": state.phase.value, "winner": state.winner.value if state.winner else None,
        "score": state.score, "failure": failure, "replay_equal": replay_equal,
        "failure_side": failure_side if failure else None, "failure_traceback": failure_traceback,
        "victory_reason": state.victory_reason,
        "fleets": {side.value: {
            "ships": sum(ship.side == side for ship in state.ships.values()),
            "sunk": sum(ship.side == side and ship.sunk for ship in state.ships.values()),
            "hull_lost": sum(ship.max_hull - ship.hull for ship in state.ships.values() if ship.side == side),
            "formations": sum(formation.side == side for formation in state.formations.values()),
        } for side in Side},
        "combat": dict(Counter(event.type for event in state.events)),
        "behavior": dict(counters), "formation_states": dict(states),
        "residual_risks": residual_risks,
        "max_plan_seconds": round(max_plan_seconds, 3), "elapsed_seconds": round(time.perf_counter() - started, 3),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", nargs="+", default=[name for name in PROFILES if name.startswith("rc_")], choices=list(PROFILES))
    parser.add_argument("--scenarios", nargs="+", default=["IBS-S-03", "IBS-S-EM-01"])
    parser.add_argument("--opponent", default="adaptive", choices=list(PROFILES))
    parser.add_argument("--seeds", nargs="+", type=int, default=[91])
    parser.add_argument("--sides", nargs="+", default=["axis", "allies"], choices=[side.value for side in Side])
    parser.add_argument("--turn-limit", type=int)
    parser.add_argument("--output", type=Path, default=Path("artifacts/realistic-ai/evaluation.json"))
    args = parser.parse_args()
    records = []
    for scenario in args.scenarios:
        for profile in args.profiles:
            for seed in args.seeds:
                for side in args.sides:
                    row = evaluate(scenario, profile, args.opponent, seed, Side(side), args.turn_limit)
                    records.append(row)
                    args.output.parent.mkdir(parents=True, exist_ok=True)
                    args.output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
                    print(json.dumps({key: value for key, value in row.items() if key != "residual_risks"}, ensure_ascii=False), flush=True)
    return int(any(row["failure"] or not row["replay_equal"] or (args.turn_limit is None and not row["completed"]) for row in records))


if __name__ == "__main__":
    raise SystemExit(main())
