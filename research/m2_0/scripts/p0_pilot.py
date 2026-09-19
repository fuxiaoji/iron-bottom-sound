"""P0.4 small-scale run audit: 5 matches per (scenario, mode).

Records sec/game, completion, failure reasons, turns, and realistic-mode
command events (succession / detach / dissolution / disruption).

    PYTHONPATH=backend/src:research/m2_0/scripts .venv/bin/python \
        research/m2_0/scripts/p0_pilot.py
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "backend" / "src"))
OUT = REPO / "research" / "m2_0"

SCENARIOS = ("IBS-S-01", "IBS-S-03", "IBS-S-EM-01")
N = 5
# NOTE (audit correction): there is NO "command_disrupted" event type at HEAD.
# Command disruption is a State flag (formation.disruption_turn) plus a next-turn
# movement restriction applied in realistic_command.py:475/734. It is therefore
# counted from state, not from the event log.
CMD_EVENTS = ("formation_command_transferred", "command_disrupted",
              "ship_detached", "ship_withdrawn")


def run_one(scenario, seed, realistic):
    from iron_bottom_sound.engine import IronBottomEngine
    from iron_bottom_sound.models import GameOptions, Phase, Side
    from iron_bottom_sound.tactical import PROFILES, TacticalCommander
    from iron_bottom_sound.realistic_command import RealisticCommander
    t0 = time.perf_counter()
    eng = IronBottomEngine()
    opts = GameOptions(mode="llm", realistic_command=realistic)
    state = eng.reset(scenario, seed, opts)
    if realistic:
        sessions = {Side.AXIS: RealisticCommander(),
                    Side.ALLIES: RealisticCommander()}
    else:
        sessions = {Side.AXIS: TacticalCommander(profile=PROFILES["balanced"]),
                    Side.ALLIES: TacticalCommander(profile=PROFILES["balanced"])}
    events_seen = {k: 0 for k in CMD_EVENTS}
    seen_seq: set[int] = set()
    disruption_turns: set[tuple] = set()
    n_formations = 0
    guard = 0
    error = None
    try:
        while state.phase != Phase.COMPLETE:
            guard += 1
            if guard > 400:
                error = "advance guard"
                break
            if state.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                               Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                               Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
                for side in Side:
                    if side.value not in state.submitted_orders:
                        b = sessions[side].choose_plan(eng, state.game_id, side)[1]
                        res = eng.submit_orders(state.game_id, b)
                        if not res.valid:
                            error = f"invalid orders: {res.errors[:2]}"
                            break
                if error:
                    break
            for e in state.events:
                if e.sequence in seen_seq:
                    continue
                seen_seq.add(e.sequence)
                if e.type in events_seen:
                    events_seen[e.type] += 1
            # disruption is a state flag, not an event: refresh_command_chain sets
            # disruption_turn = state.turn + 1 DURING GUNNERY/TORPEDO_EFFECTS, before
            # advance() increments state.turn at FIRE_END. Count each (formation,
            # disruption_turn) pair once; `command_disrupted` is a synthetic key
            # (verified absent from the event vocabulary at HEAD).
            for f in state.formations.values():
                if f.disruption_turn is not None:
                    key = (f.id, f.disruption_turn)
                    if key not in disruption_turns:
                        disruption_turns.add(key)
                        events_seen["command_disrupted"] += 1
            if state.phase.value == "reinforcement" and state.turn == 1:
                n_formations = max(n_formations, len(state.formations))
            eng.advance(state.game_id)
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
    dt = time.perf_counter() - t0
    return {
        "scenario": scenario, "seed": seed, "mode": "realistic" if realistic else "classic",
        "seconds": dt, "completed": state.phase == Phase.COMPLETE and error is None,
        "error": error, "turns": state.turn,
        "winner": state.winner.value if state.winner else None,
        "n_formations_setup": n_formations,
        "command_events": events_seen,
        "n_formations_final": len(state.formations),
        "dissolved": sum(1 for f in state.formations.values() if f.status == "dissolved"),
    }


def main() -> int:
    rows = []
    for scenario in SCENARIOS:
        for realistic in (False, True):
            for seed in range(1, N + 1):
                r = run_one(scenario, seed, realistic)
                rows.append(r)
                print(f"{scenario} {r['mode']} s{seed}: "
                      f"{'OK' if r['completed'] else 'FAIL:' + str(r['error'])[:60]} "
                      f"{r['seconds']:.1f}s turns={r['turns']} "
                      f"cmd={r['command_events']} dissolved={r['dissolved']}",
                      flush=True)
    summary = {}
    for scen in SCENARIOS:
        for mode in ("classic", "realistic"):
            sub = [r for r in rows if r["scenario"] == scen and r["mode"] == mode]
            ok = [r for r in sub if r["completed"]]
            summary[f"{scen}/{mode}"] = {
                "n": len(sub), "completed": len(ok),
                "sec_per_game_mean": statistics.mean([r["seconds"] for r in sub]),
                "turns_mean": statistics.mean([r["turns"] for r in sub]) if ok else None,
                "errors": [r["error"] for r in sub if r["error"]][:3],
                "total_command_transfers": sum(r["command_events"]["formation_command_transferred"] for r in sub),
                "total_disruptions": sum(r["command_events"]["command_disrupted"] for r in sub),
                "total_detaches": sum(r["command_events"]["ship_detached"] for r in sub),
                "total_dissolved": sum(r["dissolved"] for r in sub),
            }
    (OUT / "metrics" / "p0_pilot.json").write_text(
        json.dumps({"rows": rows, "summary": summary}, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
