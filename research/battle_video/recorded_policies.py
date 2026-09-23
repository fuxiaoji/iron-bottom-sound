"""Replay a battle **bit-identically** from its record, using the models' own replies.

Why this exists, and why orders alone are not enough
---------------------------------------------------
A battle record that keeps only the accepted order batches reproduces *movement and fire*
but not the battle.  In command-delay mode the message traffic — the fleet's orders, each
formation's report in its own words, acknowledgements, priority directives — is authored
by the agents *inside* the engine turn.  Replaying with no agents reproduces the
engine-issued standing orders instead, so the order book, the directives that reach the
gunnery selector and therefore the damage all drift.  (Measured on the CD-13 battle: the
first divergence was T5's torpedo resolution, three hull values, while every position,
heading and speed matched — the classic signature of "same ships, different decisions".)

So the replay re-serves the models' recorded replies: ``provider_policies_from_record``
builds a policy per side from ``battle_data.json``'s transcripts, and the engine then
takes the same path it took live, with no network involved.  This is what makes the
battle auditable after the fact, and what makes a rendered frame a fact rather than an
illustration.

Usage::

    .venv/bin/python research/battle_video/recorded_policies.py --battle battle_em01
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))

BATTLE_ROOT = ROOT / "research" / "command_delay"


class FleetRecordedPolicy:
    """The fleet commander's recorded replies, keyed by (side, turn)."""

    def __init__(self, records: dict[tuple[str, int], str]) -> None:
        self.records = dict(records)
        self.served: list[tuple[str, int]] = []

    def __call__(self, prompt: dict[str, Any]) -> str:
        key = (str(prompt.get("side")), int(prompt.get("turn") or 0))
        if key not in self.records:
            raise KeyError(f"no recorded fleet response for {key}")
        self.served.append(key)
        return self.records[key]

    @property
    def last_meta(self) -> dict:
        return {}


def _accepted_response(entry: dict) -> str | None:
    """The reply the agent actually used: the last accepted attempt, or a fallback's."""
    for attempt in reversed(entry.get("attempts") or []):
        if attempt.get("accepted") and attempt.get("raw_response"):
            return str(attempt["raw_response"])
    return None


def build_records(battle: dict) -> tuple[dict[str, dict[tuple[str, int], str]],
                                         dict[str, dict[tuple[str, int], str]]]:
    """Split the transcripts into per-side formation and fleet response maps."""
    formation: dict[str, dict[tuple[str, int], str]] = {"axis": {}, "allies": {}}
    fleet: dict[str, dict[tuple[str, int], str]] = {"axis": {}, "allies": {}}
    for entry in battle.get("agent_log", []):
        side = entry.get("side")
        turn = int(entry.get("turn") or 0)
        if side not in formation:
            continue
        response = _accepted_response(entry)
        if not response:
            continue
        if entry.get("role") == "fleet_agent":
            fleet[side][(side, turn)] = response
        else:
            formation_id = entry.get("formation_id")
            if formation_id:
                formation[side][(formation_id, turn)] = response
    return formation, fleet


def provider_policies_from_record(battle: dict, *, verbose: bool = True):
    """Register the recorded policies on both levels.  Returns counts for the record."""
    from iron_bottom_sound import command_delay
    from iron_bottom_sound.formation_llm import FormationLLMAgent, RecordedPolicy
    from iron_bottom_sound.fleet_llm import FleetLLMAgent
    from iron_bottom_sound.models import Side

    formation_records, fleet_records = build_records(battle)
    counts = {"formation": 0, "fleet": 0}
    for side in Side:
        key = side.value
        records = formation_records.get(key) or {}
        if records:
            policy = RecordedPolicy(records)
            command_delay.set_side_policy(side, policy, "recorded-formation")
            counts["formation"] += len(records)
        fleet = fleet_records.get(key) or {}
        if fleet:
            command_delay.set_fleet_policy(
                side, FleetRecordedPolicy(fleet), "recorded-fleet",
            )
            counts["fleet"] += len(fleet)
    if verbose:
        print(f"recorded policies: formation={counts['formation']} fleet={counts['fleet']}",
              flush=True)
    return counts, (formation_records, fleet_records)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--battle", default="battle_em01")
    args = parser.parse_args()
    battle_dir = args.battle if Path(args.battle).is_absolute() else BATTLE_ROOT / args.battle
    battle = json.loads((battle_dir / "battle_data.json").read_text(encoding="utf-8"))
    formation, fleet = build_records(battle)
    for side in ("axis", "allies"):
        print(f"{side}: formation records {len(formation[side])}, fleet records {len(fleet[side])}")
        missing_formations = sorted({
            entry.get("formation_id") for entry in battle.get("agent_log", [])
            if entry.get("side") == side and entry.get("role") != "fleet_agent"
        } - {formation_id for formation_id, _ in formation[side]})
        if missing_formations:
            print(f"  formations with no accepted reply: {missing_formations}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
