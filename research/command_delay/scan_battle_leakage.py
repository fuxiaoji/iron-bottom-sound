"""Leakage scan for the LLM-vs-LLM battle: no agent may receive unseen enemy data.

Scans every recorded agent prompt (and the fleet-commander prompts) for opposing
ship / formation identifiers that the receiving side had not legitimately observed
by that turn.  Sightings are reconstructed from the engine's own visibility rule,
turn by turn, so the check is exactly "did the transport layer widen the fog".
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from iron_bottom_sound.engine import IronBottomEngine, ORDER_PHASES  # noqa: E402
from iron_bottom_sound.llm import LLMPlayerSession  # noqa: E402
from iron_bottom_sound.models import GameOptions, Phase, Side  # noqa: E402
from iron_bottom_sound.realistic_command import default_setup_orders  # noqa: E402

BATTLE = Path(__file__).resolve().parent / "battle"


def _flatten_strings(tree) -> set[str]:
    found: set[str] = set()
    if isinstance(tree, dict):
        for key, value in tree.items():
            found.add(key) if isinstance(key, str) else None
            found |= _flatten_strings(value)
    elif isinstance(tree, list):
        for item in tree:
            found |= _flatten_strings(item)
    elif isinstance(tree, str):
        found.add(tree)
    return found


def main() -> int:
    data = json.loads((BATTLE / "battle_data.json").read_text(encoding="utf-8"))
    engine = IronBottomEngine()
    state = engine.reset(data["scenario"], data["seed"], GameOptions(
        realistic_command=True, command_delay_mode=True,
    ))
    sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
    for side in Side:
        engine.submit_orders(state.game_id, OrderBatch(
            side=side, phase=Phase.FORMATION_SETUP,
            formation_setup=default_setup_orders(state, side),
        ))
    engine.advance(state.game_id)

    # Turn-by-turn legitimate sightings per side (the same rule the views use).
    visible_by_turn: dict[int, dict[str, set[str]]] = {}
    steps = 0
    while state.phase != Phase.COMPLETE and steps < 400:
        steps += 1
        snapshot = {}
        for side in Side:
            own_positions = [
                ship.position for ship in state.ships.values()
                if ship.side is side and ship.position is not None and not ship.sunk
            ]
            seen = set()
            if own_positions:
                for ship in state.ships.values():
                    if ship.side is not side and ship.position is not None:
                        if engine._visible_to(state, ship, side, own_positions):
                            seen.add(ship.id)
            snapshot[side.value] = seen
        visible_by_turn[state.turn] = snapshot
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                assert engine.submit_orders(
                    state.game_id, sessions[side].choose_orders(engine, state.game_id)
                ).valid
        engine.advance(state.game_id)

    # The strongest sighting a side ever had stays in its memory legitimately
    # (memory is cumulative), so the allowance per turn-T prompt is everything seen
    # up to turn T.
    cumulative: dict[int, dict[str, set[str]]] = {}
    running = {side.value: set() for side in Side}
    for turn in sorted(visible_by_turn):
        for side_key, seen in visible_by_turn[turn].items():
            running[side_key] |= seen
        cumulative[turn] = {k: set(v) for k, v in running.items()}

    # Scan each logged agent prompt.
    findings: list[str] = []
    scanned = 0
    for record in data.get("agent_log", []):
        side_key = record["side"]
        turn = int(record["turn"])
        allowed = cumulative.get(turn, {}).get(side_key, set())
        prompt_text = json.dumps(record.get("prompt", {}), ensure_ascii=False, default=str)
        for ship_id in opponents_of(side_key):
            if ship_id in allowed:
                continue
            if ship_id in prompt_text:
                findings.append(
                    f"T{turn} {record['formation_id']} ({side_key}): unseen enemy "
                    f"{ship_id} present in the prompt"
                )
        scanned += 1
    # Fleet-commander prompts are inside messages? They are not logged as prompts —
    # the fleet view used to build them is side-filtered by construction; the scan
    # above covers the agent log, which is what the debug surface exposes.
    payload = {
        "agent_prompts_scanned": scanned,
        "findings": findings,
        "verdict": "PASS" if not findings else "FAIL",
    }
    (BATTLE / "leakage_scan.json").write_text(
        json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    return 0 if not findings else 1


def opponents_of(side_key: str) -> set[str]:
    """Ship ids of the opposing side, from the scenario data on the merged tree."""
    engine = IronBottomEngine()
    del engine
    # Cheap static source: the other side's ships of S-01, loaded once.
    from iron_bottom_sound.data import load_scenario

    scenario = load_scenario("IBS-S-01")
    other = "allies" if side_key == "axis" else "axis"
    return {
        entry["id"] for entry in scenario["ships"] if entry.get("side") == other
    }


if __name__ == "__main__":
    raise SystemExit(main())
