"""Leakage scan for the LLM-vs-LLM battle: what an agent was handed, and from where.

The first version of this scan asked "does a prompt contain an enemy ship id the
receiving side had not sighted yet".  That question turned out to be vacuous in this
scenario: on IBS-S-01 both sides are inside optical range from turn 1 (the axis side
can see all 9 USN ships, the allies all 5 IJN ships), so the identity test could
never fail.  A test that cannot fail is not evidence, so this scan was rewritten
around the channel that can actually leak: the **provenance of the text**.

Every distinctive string in a request is traced back to the record it came from -
a formation decision, a memory note, a target-priority reason, a fleet order - and
the prompt is checked against one rule:

    a prompt for (side, formation, turn T) may contain a string only if that string
    has a legitimate provenance for that reader: the reader's own formation at an
    earlier turn, or a fleet order addressed to it that has already been delivered.
    Nothing from the other side, nothing from a sibling formation's decisions, and
    nothing from a later turn - that last clause is what makes "the enemy's plan
    leaked" and "this commander read tomorrow's newspaper" both fail here.

Three further checks run alongside it:

* ``message_ledger`` - every ``received_messages[*].message_id`` in a prompt must
  resolve to a ledger entry of the *same side* addressed to that formation.  This is
  exact, needs no replay, and is the check that the CD12-F2a/F2b defects would have
  failed: those were orders and priorities crossing sides.
* ``identity`` - the original visibility test, kept but labelled with its teeth
  (when each enemy hull first became visible) so a reader can see it is weak here.
* ``field_ownership`` - ``active_mission_order`` / ``stale_external_reports`` must
  name the reader's own side.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from iron_bottom_sound.engine import IronBottomEngine, ORDER_PHASES  # noqa: E402
from iron_bottom_sound.llm import LLMPlayerSession  # noqa: E402
from iron_bottom_sound.models import GameOptions, OrderBatch, Phase, Side  # noqa: E402
from iron_bottom_sound.realistic_command import (  # noqa: E402
    RealisticCommander,
    default_setup_orders,
)

DEFAULT_BATTLE = Path(__file__).resolve().parent / "battle"
MIN_TOKEN = 8
SIDE_PREFIX = {"axis": "IBS-U-IJN", "allies": "IBS-U-USN"}


def tokens(text: str) -> set[str]:
    """Distinctive prose fragments of a string, long enough not to collide by chance."""
    found: set[str] = set()
    for run in re.split(r"""[\s，。；：、,.;:!?（）()\[\]「」/"'\\|]+""", str(text or "")):
        run = run.strip()
        if len(run) >= MIN_TOKEN:
            found.add(run)
    return found


def flatten_text(node) -> list[str]:
    out: list[str] = []
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, dict):
        for value in node.values():
            out.extend(flatten_text(value))
    elif isinstance(node, list):
        for item in node:
            out.extend(flatten_text(item))
    return out


def provenance(data: dict) -> tuple[list[tuple[str, str, int, set[str]]],
                                    list[tuple[str, str, int, set[str]]]]:
    """Distinctive strings split into decision provenance and fleet-order provenance.

    Decision provenance is ``(side, formation, turn, tokens)``: material a formation
    wrote for itself, which only that formation may read, and only in later turns.
    Fleet-order provenance is ``(side, formation, delivered_turn, tokens)``, using the
    delivery turn from the message ledger rather than the issue turn, because that is
    when the reader is entitled to know it.
    """
    decisions: list[tuple[str, str, int, set[str]]] = []
    for record in data.get("decisions", []):
        texts = [record.get("rationale_summary") or "", record.get("memory_note") or ""]
        for adjust in record.get("target_priority_adjustments") or []:
            texts.append(adjust.get("reason") or "")
        collected: set[str] = set()
        for text in texts:
            collected |= tokens(text)
        if collected:
            decisions.append((
                record.get("side") or _side_of(record.get("formation_id")),
                record.get("formation_id") or "",
                int(record.get("turn") or 0),
                collected,
            ))

    ledger = {m.get("message_id"): m for m in data.get("messages", [])}
    orders: list[tuple[str, str, int, set[str]]] = []
    for order in data.get("fleet_orders", []):
        text = order.get("text") or ""
        if not text:
            continue
        message = ledger.get(order.get("message_id")) or {}
        delivered = message.get("delivered_turn")
        if delivered is None:
            delivered = order.get("delivered_turn", order.get("turn", 0))
        orders.append((
            order.get("side") or "",
            order.get("formation_id") or "",
            int(delivered),
            tokens(text),
        ))
    return decisions, orders


def _side_of(formation_id: str | None) -> str:
    name = formation_id or ""
    return "axis" if name.startswith("axis") else "allies"


def request_records(battle: Path) -> list[dict]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((battle / "requests").glob("*.request.json"))
    ]


def check_content(records: list[dict], decisions, orders) -> tuple[list[str], int, int]:
    """The provenance rule.  Returns findings plus the tokens actually exercised."""
    findings: list[str] = []
    checked = 0
    exercised = 0
    for record in records:
        side = record["side"]
        turn = int(record["turn"])
        formation = record.get("formation_id") or ""
        role = record.get("role") or "formation_commander"
        prompt_text = json.dumps(record, ensure_ascii=False, default=str)

        allowed: set[str] = set()
        for prov_side, prov_form, prov_turn, prov_tokens in decisions:
            if prov_side != side or prov_turn >= turn:
                continue
            # A formation reads only what it wrote itself; the fleet commander reads
            # its own side's subordinate reports (that is what its view aggregates).
            if role == "formation_commander" and prov_form != formation:
                continue
            allowed |= prov_tokens
        for prov_side, prov_form, delivered, prov_tokens in orders:
            if prov_side != side or delivered > turn:
                continue
            if role == "formation_commander" and prov_form != formation:
                continue
            allowed |= prov_tokens

        candidates = tokens(prompt_text)
        checked += len(candidates)
        for token in sorted(candidates):
            sources = [
                (ps, pf, pt, "decision") for ps, pf, pt, ptoks in decisions if token in ptoks
            ] + [
                (ps, pf, pt, "order") for ps, pf, pt, ptoks in orders if token in ptoks
            ]
            if not sources:
                continue
            exercised += 1
            if token in allowed:
                continue
            detail = ", ".join(
                f"{kind} {ps}/{pf}@{pt}" for ps, pf, pt, kind in sources[:3]
            )
            findings.append(
                f"T{turn} {role} {formation or side} ({side}): text with no legitimate "
                f"provenance for this reader: 「{token[:40]}」 from {detail}"
            )
    return findings, checked, exercised


def check_message_ledger(records: list[dict], ledger: dict) -> list[str]:
    findings: list[str] = []
    for record in records:
        side = record["side"]
        formation = record.get("formation_id") or ""
        for message in record.get("received_messages") or []:
            mid = message.get("message_id")
            entry = ledger.get(mid)
            if entry is None:
                findings.append(f"{mid} received by {formation} is not in the ledger")
                continue
            if entry.get("side") != side:
                findings.append(
                    f"{mid} ({entry.get('side')}) delivered into {side} prompt for "
                    f"{formation or record.get('role')}"
                )
            destination = entry.get("destination")
            if formation and destination and destination != formation:
                findings.append(
                    f"{mid} addressed to {destination} but read by {formation}"
                )
    return findings


def check_field_ownership(records: list[dict]) -> list[str]:
    findings: list[str] = []
    for record in records:
        side = record["side"]
        own = SIDE_PREFIX[side]
        order = record.get("active_mission_order")
        if isinstance(order, dict):
            for text in flatten_text(order):
                if text.startswith("IBS-U-") and not text.startswith(own):
                    findings.append(
                        f"T{record['turn']} {record.get('formation_id')} ({side}): "
                        f"active_mission_order names enemy hull {text}"
                    )
        for report in record.get("stale_external_reports") or []:
            if not isinstance(report, dict):
                continue
            other = report.get("formation_id")
            if other and not str(other).startswith(side):
                findings.append(
                    f"T{record['turn']} {record.get('formation_id')} ({side}): "
                    f"stale report from enemy formation {other}"
                )
    return findings


def visible_by_turn(data: dict) -> dict[int, dict[str, set[str]]]:
    """Per-turn sightings, from the engine's own rule, replayed turn by turn."""
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

    visible: dict[int, dict[str, set[str]]] = {}
    steps = 0
    while state.phase != Phase.COMPLETE and steps < 400:
        steps += 1
        snapshot: dict[str, set[str]] = {}
        for side in Side:
            own_positions = [
                ship.position for ship in state.ships.values()
                if ship.side is side and ship.position is not None and not ship.sunk
            ]
            seen: set[str] = set()
            if own_positions:
                for ship in state.ships.values():
                    if ship.side is not side and ship.position is not None:
                        if engine._visible_to(state, ship, side, own_positions):
                            seen.add(ship.id)
            snapshot[side.value] = seen
        visible[state.turn] = snapshot
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                engine.submit_orders(
                    state.game_id, sessions[side].choose_orders(engine, state.game_id)
                )
        engine.advance(state.game_id)
    return visible


def opponents_of(side_key: str) -> set[str]:
    from iron_bottom_sound.data import load_scenario

    scenario = load_scenario("IBS-S-01")
    other = "allies" if side_key == "axis" else "axis"
    return {entry["id"] for entry in scenario["ships"] if entry.get("side") == other}


def check_identity(records: list[dict], visible: dict[int, dict[str, set[str]]]) -> dict:
    cumulative: dict[int, dict[str, set[str]]] = {}
    running: dict[str, set[str]] = {"axis": set(), "allies": set()}
    for turn in sorted(visible):
        for side_key, seen in visible[turn].items():
            running[side_key] |= seen
        cumulative[turn] = {k: set(v) for k, v in running.items()}

    findings: list[str] = []
    for record in records:
        side = record["side"]
        turn = int(record["turn"])
        allowed = cumulative.get(turn, {}).get(side, set())
        text = json.dumps(record, ensure_ascii=False, default=str)
        for ship_id in opponents_of(side):
            if ship_id in text and ship_id not in allowed:
                findings.append(
                    f"T{turn} {record.get('formation_id') or record.get('role')} "
                    f"({side}): unseen enemy {ship_id} in the prompt"
                )

    first_sighting: dict[str, dict[str, int | None]] = {}
    for side_key in ("axis", "allies"):
        first_sighting[side_key] = {}
        for ship_id in sorted(opponents_of(side_key)):
            when = next(
                (turn for turn in sorted(visible) if ship_id in visible[turn][side_key]),
                None,
            )
            first_sighting[side_key][ship_id] = when
    turn_one_full = all(
        value == 1 for per_side in first_sighting.values() for value in per_side.values()
    )
    return {
        "findings": findings,
        "first_sighting_turn": first_sighting,
        "vacuous_in_this_scenario": turn_one_full,
        "note": (
            "Every enemy hull is inside optical range from turn 1, so this test cannot "
            "fail on this scenario; it is reported for completeness, not as evidence. "
            "The content-provenance check is the one with teeth here."
            if turn_one_full else
            "Some enemy hulls are sighted later than turn 1, so this test does have teeth."
        ),
    }


def scan(battle: Path) -> dict:
    data = json.loads((battle / "battle_data.json").read_text(encoding="utf-8"))
    records = request_records(battle)
    ledger = {m.get("message_id"): m for m in data.get("messages", [])}
    decisions, orders = provenance(data)

    content_findings, tokens_checked, tokens_exercised = check_content(
        records, decisions, orders
    )
    ledger_findings = check_message_ledger(records, ledger)
    ownership_findings = check_field_ownership(records)
    identity = check_identity(records, visible_by_turn(data))

    findings = content_findings + ledger_findings + ownership_findings
    payload = {
        "battle": str(battle),
        "request_files_scanned": len(records),
        "provenance_strings": {"decisions": len(decisions), "fleet_orders": len(orders)},
        "content_provenance": {
            "findings": content_findings,
            "tokens_examined": tokens_checked,
            "tokens_with_provenance": tokens_exercised,
        },
        "message_ledger": {"findings": ledger_findings},
        "field_ownership": {"findings": ownership_findings},
        "identity": identity,
        "findings": findings,
        "verdict": "PASS" if not findings else "FAIL",
    }
    return payload


def self_test(battle: Path) -> dict:
    """Positive control: real strings from this battle must be caught when cross-wired.

    A PASS is only evidence if the same scanner would have failed on a leak, so three
    controls are run against one real request, using strings that actually exist in
    this battle rather than invented text: an enemy fleet order, an enemy formation's
    decision prose, and an enemy message-ledger entry in ``received_messages``.  The
    first two exercise the content rule, the third the exact ledger check.
    """
    data = json.loads((battle / "battle_data.json").read_text(encoding="utf-8"))
    records = request_records(battle)
    decisions, orders = provenance(data)
    victim = next(r for r in records if r["side"] == "axis"
                  and r["turn"] >= 3 and r.get("role") == "formation_commander")
    side = victim["side"]
    other = "allies"

    enemy_order = next((toks for ps, _pf, _t, toks in orders
                        if ps == other and toks), set())
    enemy_decision = next((toks for ps, _pf, _t, toks in decisions
                           if ps == other and toks), set())
    enemy_message = next((m for m in data.get("messages", []) if m.get("side") == other
                          and m.get("status") == "delivered"), None)

    results: dict[str, dict] = {}
    baseline, _, _ = check_content([victim], decisions, orders)
    results["baseline_findings"] = len(baseline)

    for label, extra in (("enemy_fleet_order", enemy_order),
                         ("enemy_decision_prose", enemy_decision)):
        poisoned = dict(victim, order_text=" ".join(sorted(extra)))
        found, _, _ = check_content(
            [poisoned],
            [*decisions, (other, f"{other}-active-heavy", 1, extra)],
            orders,
        )
        results[label] = {
            "injected": " ".join(sorted(extra))[:60],
            "caught": any(any(tok in f for tok in extra) for f in found),
            "findings": len(found),
        }

    poisoned = dict(victim, received_messages=[enemy_message] if enemy_message else [])
    ledger_found = check_message_ledger([poisoned],
                                        {m.get("message_id"): m
                                         for m in data.get("messages", [])})
    results["enemy_message_ledger_entry"] = {
        "injected": (enemy_message or {}).get("message_id"),
        "caught": bool(ledger_found),
        "findings": len(ledger_found),
    }

    caught_all = (
        results["baseline_findings"] == 0
        and all(results[k]["caught"] for k in
                ("enemy_fleet_order", "enemy_decision_prose",
                 "enemy_message_ledger_entry"))
    )
    results["verdict"] = "PASS" if caught_all else "FAIL"
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--battle", type=Path, default=DEFAULT_BATTLE)
    parser.add_argument("--self-test", action="store_true",
                        help="run the positive control instead of the scan")
    args = parser.parse_args()

    payload = self_test(args.battle) if args.self_test else scan(args.battle)
    out = args.battle / ("self_test.json" if args.self_test else "leakage_scan.json")
    out.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    return 0 if payload["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
