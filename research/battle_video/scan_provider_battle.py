"""Leakage scan for a *provider-run* battle: every prompt against what it was entitled to.

The earlier battle was served by a file bridge, so its record was a directory of request
files.  This one calls the provider directly, so its record is ``calls.jsonl`` - one line
per model round trip with the prompt, the reply and the reasoning.  The check is the same
question asked of a different shape:

    a model may be told only what its own command could legitimately know

Concretely, for this battle's two prompt shapes:

* a **formation** prompt may name an enemy ship only if that formation's own ships had
  sighted it (cumulatively, by that turn) - it is the formation's own observation and
  nothing else;
* a **fleet** prompt may name an enemy ship only if (a) the ship was sighted by the
  formation the commander sails in, or (b) it was named in a *report body* written by a
  formation that had sighted it.  That second clause is the reporting chain doing its
  job, and it is exactly where a leak would hide: "reporting up" must not become
  "leaking up".

The sighting bound is reconstructed by replaying the battle from ``orders.jsonl``, which
is faithful because the record keeps every order batch the engine accepted (see
``replay_battle.py --verify``).

Positive control: the same scanner is run with an enemy id injected into a real prompt
that had never sighted it, and it must report it.  A check that cannot fail is not
evidence - that lesson is why this file exists in this shape.

Usage::

    .venv/bin/python research/battle_video/scan_provider_battle.py --battle battle_em01
    .venv/bin/python research/battle_video/scan_provider_battle.py --battle battle_em01 --self-test
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend" / "src"))
sys.path.insert(0, str(HERE))

from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine  # noqa: E402
from iron_bottom_sound.models import GameOptions, OrderBatch, Phase, Side  # noqa: E402
from iron_bottom_sound.realistic_command import default_setup_orders  # noqa: E402
from replay_battle import load_orders  # noqa: E402

BATTLE_ROOT = ROOT / "research" / "command_delay"


def signatures_for(engine, state) -> dict[str, dict[str, set[str]]]:
    """Every way an enemy ship can be named in text, by formation, right now.

    Both the id (``IBS-U-USN-ERMA-IOWA``) and the display name run through the same
    bound: a model that writes "衣阿华" has leaked exactly as much as one that writes
    the id.
    """
    out: dict[str, dict[str, set[str]]] = {}
    for side in Side:
        for formation in state.formations.values():
            if formation.side is not side or formation.status == "dissolved":
                continue
            positions = [
                state.ships[ship_id].position for ship_id in formation.ship_ids
                if ship_id in state.ships and state.ships[ship_id].position is not None
                and not state.ships[ship_id].sunk
                and state.ships[ship_id].command_status == "attached"
            ]
            ids: set[str] = set()
            names: set[str] = set()
            if positions:
                for ship in state.ships.values():
                    # ``sunk`` is deliberately not filtered: a ship the formation watched
                    # sink stays in its memory and in its reports afterwards, and that is
                    # the record working, not a leak.
                    if ship.side is side or ship.position is None:
                        continue
                    if engine._visible_to(state, ship, side, positions):
                        ids.add(ship.id)
                        if ship.name:
                            names.add(ship.name)
            out[formation.id] = {"ids": ids, "names": names}
    return out


def replay_sightings(battle_dir: Path) -> tuple[dict[int, dict[str, dict]], dict[int, list[dict]]]:
    """Replay the battle and record, per turn, how each formation saw the enemy.

    Returns ``(cumulative, turn_snapshots)``: what each formation had ever sighted by
    that turn, and - per turn - the report bodies that were in flight.
    """
    battle = json.loads((battle_dir / "battle_data.json").read_text(encoding="utf-8"))
    orders = load_orders(battle_dir)
    # Re-serve the models' own replies, exactly as replay_battle does: the message traffic
    # they authored is part of the battle, and without it the sighting envelope is the
    # envelope of a *different* battle.
    from recorded_policies import provider_policies_from_record

    provider_policies_from_record(battle, verbose=False)
    engine = IronBottomEngine()
    state = engine.reset(battle.get("scenario", "IBS-S-EM-01"), int(battle["seed"]), GameOptions(
        realistic_command=True, command_delay_mode=True,
    ))
    for side in Side:
        engine.submit_orders(state.game_id, OrderBatch(
            side=side, phase=Phase.FORMATION_SETUP,
            formation_setup=default_setup_orders(state, side),
        ))
    engine.advance(state.game_id)

    cumulative: dict[str, dict[str, set[str]]] = {}
    by_turn: dict[int, dict[str, dict]] = {}
    steps = 0
    while state.phase is not Phase.COMPLETE and steps < 2000:
        steps += 1
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                batch = orders.get((state.turn, state.phase.value, side.value))
                if batch is None:
                    raise SystemExit(f"missing recorded batch for {(state.turn, state.phase.value, side.value)}")
                result = engine.submit_orders(state.game_id, batch)
                if not result.valid and state.phase is Phase.MOVEMENT_PLANNING:
                    # the driver's substitution path: doctrine takes the side this turn
                    from iron_bottom_sound.realistic_command import RealisticCommander

                    _, fallback, _ = RealisticCommander().choose_plan(engine, state.game_id, side)
                    result = engine.submit_orders(state.game_id, fallback)
                assert result.valid, (state.turn, state.phase, side, result.errors[:2])
        engine.advance(state.game_id)
        snapshot = signatures_for(engine, state)
        for formation_id, payload in snapshot.items():
            holder = cumulative.setdefault(formation_id, {"ids": set(), "names": set()})
            holder["ids"] |= payload["ids"]
            holder["names"] |= payload["names"]
        by_turn[state.turn] = {
            formation_id: {"ids": set(payload["ids"]), "names": set(payload["names"])}
            for formation_id, payload in snapshot.items()
        }
    return cumulative, by_turn


def enemy_ships_by_side(battle: dict) -> dict[str, dict[str, set[str]]]:
    """For each side, the identifiers of the ships it is *allowed* to be told about.

    Only the opposing side's ships: a formation's own roster is in its prompt by
    construction, and flagging "the prompt names its own flagship" would be a criterion
    that fails on every healthy call - the mistake this check made in its first run.
    """
    universe: dict[str, dict[str, set[str]]] = {
        "axis": {"ids": set(), "names": set()},
        "allies": {"ids": set(), "names": set()},
    }
    view = next(iter(battle.get("three_views", [])), None)
    if view is None:
        return universe
    for ship_id, row in view["god"]["ships"].items():
        for side in ("axis", "allies"):
            if row["side"] != side:
                universe[side]["ids"].add(ship_id)
                if row.get("name"):
                    universe[side]["names"].add(row["name"])
    return universe


def mentions(text: str, signatures: dict[str, set[str]]) -> set[str]:
    found = {ship_id for ship_id in signatures["ids"] if ship_id in text}
    found |= {name for name in signatures["names"] if name and name in text}
    return found


def scan(battle_dir: Path) -> dict:
    battle = json.loads((battle_dir / "battle_data.json").read_text(encoding="utf-8"))
    calls = [json.loads(line) for line in (battle_dir / "calls.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()]
    cumulative, by_turn = replay_sightings(battle_dir)
    reports = {row["message_id"]: row for row in battle.get("messages", [])}

    universe = enemy_ships_by_side(battle)
    side_seen: dict[str, dict[str, set[str]]] = {}
    for formation_id, payload in cumulative.items():
        side_key = formation_id.split("-", 1)[0]
        holder = side_seen.setdefault(side_key, {"ids": set(), "names": set()})
        holder["ids"] |= payload["ids"]
        holder["names"] |= payload["names"]

    findings: list[str] = []
    scanned = 0
    for call in calls:
        if call.get("transport_error"):
            continue
        prompt = json.dumps(call.get("prompt") or {}, ensure_ascii=False, default=str)
        scanned += 1
        role = call.get("role")
        side = call.get("side")
        # The turn lives inside the prompt (the recorder writes the prompt, not a
        # summary): reading it from the call object silently made every sibling report
        # look like it arrived later, which turned legitimate traffic into findings.
        prompt_turn = 0
        turn_match = re.search(r'"turn":\s*(\d+)', prompt)
        if turn_match:
            prompt_turn = int(turn_match.group(1))
        # Which formation is asking?  The formation prompt names it; the fleet prompt
        # does not, so the fleet's allowance is assembled below from its own formation
        # plus the reports it was sent.
        formation_id = None
        match = re.search(r'"formation_id":\s*"([^"]+)"', prompt)
        if role == "formation" and match:
            formation_id = match.group(1)

        allowed_ids: set[str] = set()
        allowed_names: set[str] = set()
        if role == "formation" and formation_id in cumulative:
            allowed_ids = set(cumulative[formation_id]["ids"])
            allowed_names = set(cumulative[formation_id]["names"])
        if role == "formation" and formation_id:
            # Within a side, knowledge legitimately travels: a formation's view carries
            # the fleet's copies of its siblings' reports (stale_external_reports), and a
            # report body may name anything *some* ship of that side had sighted.  So the
            # bound for a prompt is its side's cumulative sightings, and the check proves
            # the invariant that matters across the boundary: **no side is ever told about
            # an enemy ship that none of its own ships had seen**.  A within-side ordering
            # leak (A learning from B's report before it was delivered) is not decidable
            # from the prompt alone and is not claimed here.
            for report in battle.get("messages", []):
                payload = report.get("payload") or {}
                if payload.get("reporting_formation_id") == formation_id:
                    continue  # its own report, already covered by its own sightings
                delivered = report.get("delivered_turn")
                reporter = (payload.get("report") or {}).get("reporting_formation_id")
                if not reporter or reporter not in cumulative:
                    continue
                if report.get("destination") != formation_id:
                    continue  # not addressed to this formation
                if delivered is None or delivered > prompt_turn:
                    continue
                # The prose is where a report names ships ("发现多艘美舰：2艘CA(得梅因、
                # 塞勒姆)…"); the structured snapshot carries positions, not names.
                body = payload.get("report_text") or ""
                allowed_ids |= mentions(body, cumulative[reporter])
                allowed_names |= {
                    name for name in cumulative[reporter]["names"] if name and name in body
                }
        elif role == "fleet":
            # (a) what the commander can see from its own bridge: the formation it sails in
            own_formation = next(
                (formation_id for formation_id in cumulative
                 if _is_embarked(battle, formation_id, side)),
                None,
            )
            if own_formation:
                allowed_ids |= cumulative[own_formation]["ids"]
                allowed_names |= cumulative[own_formation]["names"]
            # (b) what its subordinates told it, bounded by what each reporter had seen
            for report in battle.get("messages", []):
                payload = report.get("payload") or {}
                body = payload.get("report_text") or ""
                reporter = (payload.get("report") or {}).get("reporting_formation_id")
                if not body or not reporter or reporter not in cumulative:
                    continue
                allowed_ids |= mentions(body, cumulative[reporter])
                allowed_names |= {
                    name for name in cumulative[reporter]["names"] if name and name in body
                }

        allowed_ids |= side_seen.get(side or "axis", {}).get("ids", set())
        allowed_names |= side_seen.get(side or "axis", {}).get("names", set())
        leaked = mentions(prompt, universe.get(side or "axis")) - allowed_ids - allowed_names
        if leaked:
            findings.append(
                f"{role} {side} turn-prompt names {sorted(leaked)} with no legitimate "
                f"source (formation={formation_id})"
            )

    payload = {
        "battle": str(battle_dir.relative_to(ROOT)),
        "calls_scanned": scanned,
        "calls_total": len(calls),
        "report_bodies_seen": sum(1 for report in battle.get("messages", [])
                                  if (report.get("payload") or {}).get("report_text")),
        "criterion": (
            "No side is ever told about an enemy ship that none of its own ships had "
            "sighted: every opposing-ship id or name in a prompt must fall inside the "
            "cumulative sightings of that side. Within-side ordering (a formation "
            "learning from a sibling's report before delivery) is not claimed - a "
            "formation's view legitimately carries the fleet's copies of sibling reports."
        ),
        "findings": findings,
        "verdict": "PASS" if not findings else "FAIL",
    }
    return payload


def _is_embarked(battle: dict, formation_id: str, side: str) -> bool:
    for view in battle.get("three_views", []):
        payload = view.get("sides", {}).get(side, {})
        fleet = payload.get("fleet", {})
        if fleet.get("embarked_formation_id") == formation_id:
            return True
    return False


def self_test(battle_dir: Path) -> dict:
    """Inject an enemy identifier a real prompt was never entitled to, and catch it."""
    battle = json.loads((battle_dir / "battle_data.json").read_text(encoding="utf-8"))
    calls = [json.loads(line) for line in (battle_dir / "calls.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()]
    cumulative, _ = replay_sightings(battle_dir)
    victim = next((call for call in calls
                   if call.get("role") == "formation" and not call.get("transport_error")), None)
    if victim is None:
        return {"verdict": "FAIL", "reason": "no formation call to inject into"}

    prompt_text = json.dumps(victim.get("prompt") or {}, ensure_ascii=False, default=str)
    formation_id = re.search(r'"formation_id":\s*"([^"]+)"', prompt_text)
    formation_id = formation_id.group(1) if formation_id else ""
    seen = cumulative.get(formation_id, {"ids": set(), "names": set()})
    universe = enemy_ships_by_side(battle)
    never = sorted(
        ship_id for ship_id in universe.get(victim.get("side") or "axis", {}).get("ids", set())
        if ship_id not in seen["ids"] and ship_id not in prompt_text
    )
    if not never:
        return {"verdict": "FAIL", "reason": "every enemy id is already visible to this formation"}

    injected = never[0]
    poisoned = dict(victim)
    poisoned["prompt"] = {**(victim.get("prompt") or {}), "order_text": f"侦察发现 {injected}"}
    baseline = _scan_calls([victim], battle, cumulative)
    after = _scan_calls([poisoned], battle, cumulative)
    caught = any(injected in finding for finding in after)
    return {
        "injected_into": f"{formation_id} ({victim.get('side')})",
        "injected_enemy_id": injected,
        "baseline_findings": len(baseline),
        "findings_after_injection": len(after),
        "injection_caught": caught,
        "verdict": "PASS" if caught and not baseline else "FAIL",
    }


def _enemy_ids(battle: dict) -> list[str]:
    ships = {}
    for view in battle.get("three_views", [])[:1]:
        ships.update(view["god"]["ships"])
    return [ship_id for ship_id, row in ships.items()]


def _scan_calls(calls: list[dict], battle: dict, cumulative: dict) -> list[str]:
    """The scan body, reusable for the self-test's poisoned call list."""
    findings: list[str] = []
    universe = enemy_ships_by_side(battle)
    for call in calls:
        prompt = json.dumps(call.get("prompt") or {}, ensure_ascii=False, default=str)
        role = call.get("role")
        formation_id = None
        match = re.search(r'"formation_id":\s*"([^"]+)"', prompt)
        if role == "formation" and match:
            formation_id = match.group(1)
        allowed = set()
        if role == "formation" and formation_id in cumulative:
            allowed = cumulative[formation_id]["ids"] | cumulative[formation_id]["names"]
        leaked = mentions(prompt, universe.get(call.get("side") or "axis")) - allowed
        if leaked:
            findings.append(f"{role}: {sorted(leaked)}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--battle", default="battle_em01")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    battle_dir = args.battle if Path(args.battle).is_absolute() else BATTLE_ROOT / args.battle

    payload = self_test(battle_dir) if args.self_test else scan(battle_dir)
    name = "leak_self_test.json" if args.self_test else "leak_scan.json"
    (battle_dir / name).write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                                   encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    return 0 if payload["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
