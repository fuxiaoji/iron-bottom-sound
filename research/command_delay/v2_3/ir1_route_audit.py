"""IR-1 — route provenance audit of the old battle (v2.2 routing).

What this answers
-----------------
The PI's correction says distance on the standard map must not, by itself, force a
same-fleet formation onto relay/re-enciphered W/T, and that every `转报再加密 +2` route
must be explained.  This audit recomputes, for every message in the archived battle,
what the *corrected* rule would have chosen and compares it with what the v2.2 code
actually chose, flagging each message.

The v2.2 defect, stated exactly (code evidence in `communications/routing.py` and
`command_delay.route`):

* ``route()`` passed ``tactical_range = state.visibility[side]`` - the scenario's
  **optical** horizon - as the TBS range, so "direct TBS" ended where eyesight ended;
* ``relay_available = not same_command`` - true for every message to a different
  formation - so once line of sight failed, ``select_medium`` returned
  ``WT_REENCIPHER_RELAY`` with the reason "coded set but the ends are under different
  ciphers".  The mode has no model of cipher domains at all: the only thing that made
  the ends "different" was that they were different formations.

Everything here is recomputed from the archived record (positions come from the god's-eye
snapshots embedded in ``battle_data.json``), so the audit needs no engine replay and no
network.

Usage::

    .venv/bin/python research/command_delay/v2_3/ir1_route_audit.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BATTLE = Path(__file__).resolve().parent / "raw" / "battle_em01"
OUT = Path(__file__).resolve().parent

# Historically motivated TBS range: about 25 statute miles of VHF line-of-sight at
# 600 yd/hex.  Recorded as a configured profile value, not as a delay multiplier.
TBS_RANGE_HEX = 73
HEX_YARDS = 600
YARDS_PER_NMI = 2025.37

PHASE_RANK = {
    "contact_setup": 0, "reinforcement": 1, "movement_planning": 2,
    "torpedo_planning": 3, "movement_resolution": 4, "gunnery": 5,
    "torpedo_effects": 6, "fire_end": 7,
}


def hex_distance(a: tuple[int, int], b: tuple[int, int]) -> int:
    (q1, r1), (q2, r2) = a, b
    return (abs(q1 - q2) + abs(r1 - r2) + abs((q1 + r1) - (q2 + r2))) // 2


def load() -> dict:
    return json.loads((BATTLE / "battle_data.json").read_text(encoding="utf-8"))


def view_index(battle: dict) -> dict[tuple[int, str], dict]:
    return {(int(v["turn"]), v["phase"]): v for v in battle.get("three_views", [])}


def view_at(index: dict, turn: int, phase: str) -> dict | None:
    """The god snapshot nearest to (turn, phase) but never later than it."""
    if (turn, phase) in index:
        return index[(turn, phase)]
    rank = PHASE_RANK.get(phase, 0)
    same_turn = [key for key in index if key[0] == turn and PHASE_RANK.get(key[1], 0) <= rank]
    if same_turn:
        return index[max(same_turn, key=lambda key: PHASE_RANK.get(key[1], 0))]
    earlier = [key for key in index if key[0] < turn]
    if earlier:
        return index[max(earlier, key=lambda key: (key[0], PHASE_RANK.get(key[1], 0)))]
    return None


def position_of(ship_id: str, view: dict) -> tuple[int, int] | None:
    row = (view.get("god") or {}).get("ships", {}).get(ship_id)
    if not row or row.get("q") is None:
        return None
    return int(row["q"]), int(row["r"])


def optical_range(sender_ship: str, view: dict) -> int | None:
    """The scenario's optical horizon for the sender's side, as the v2.2 rule used it.

    This is the value the old ``route()`` passed as ``tactical_range`` - the reason a
    message at 20 hex could be treated as "beyond tactical range" on a board whose TBS
    radio range is 73 hex.
    """
    for side_key, payload in (view.get("sides") or {}).items():
        for observation in (payload.get("formations") or {}).values():
            cards = (observation.get("formation_state") or {}).get("ships") or []
            if any(card.get("ship_id") == sender_ship for card in cards):
                return observation.get("visibility")
    return None


def recipient_position(formation_id: str, view: dict) -> tuple[int, int] | None:
    """Where the recipient's guide is: the formation's leader, from its own view."""
    for side_payload in (view.get("sides") or {}).values():
        observation = (side_payload.get("formations") or {}).get(formation_id)
        if not observation:
            continue
        leader = (observation.get("formation_state") or {}).get("leader_id")
        if leader:
            return position_of(leader, view)
        for card in (observation.get("formation_state") or {}).get("ships") or []:
            if card.get("position") is not None:
                row = (view.get("god") or {}).get("ships", {}).get(card.get("ship_id"))
                if row and row.get("q") is not None:
                    return int(row["q"]), int(row["r"])
    return None


def main() -> int:
    battle = load()
    index = view_index(battle)
    messages = battle.get("messages", [])
    reports = {row.get("message_id"): row for row in
               (json.loads(line) for line in (BATTLE / "reports.jsonl").read_text(
                   encoding="utf-8").splitlines() if line.strip())}

    rows: list[dict] = []
    findings: dict[str, list[str]] = {
        "UNJUSTIFIED_RELAY": [], "UNJUSTIFIED_REENCIPHER": [],
        "DIRECT_TBS_AVAILABLE_BUT_NOT_USED": [], "DISTANCE_DELAY_BUG": [],
        "MISSING_ROUTE_PROVENANCE": [],
        "MISSING_RELAY_OR_CRYPTO_PROVENANCE": [],
    }
    for message in messages:
        issued_turn, issued_phase = int(message["issued_turn"]), message["issued_phase"]
        view = view_at(index, issued_turn, issued_phase)
        sender = message.get("origin") or ""
        recipient = message.get("destination") or ""
        sender_pos = position_of(sender, view) if view else None
        recipient_pos = recipient_position(recipient, view) if view else None
        distance = (hex_distance(sender_pos, recipient_pos)
                    if sender_pos and recipient_pos else None)
        medium = message.get("medium")
        relay_hops = int(message.get("relay_hops") or 0)
        handling = int(message.get("handling_delay") or 0)
        reason = message.get("reason") or ""
        in_person = bool((message.get("payload") or {}).get("delivered_in_person"))
        direct_tbs_available = bool(
            distance is not None and distance <= TBS_RANGE_HEX and not in_person
        )
        optical = optical_range(sender, view) if view else None
        row = {
            "message_id": message.get("message_id"),
            "kind": message.get("kind"),
            "side": message.get("side"),
            "sender": sender,
            "recipient": recipient,
            "issued_turn": issued_turn,
            "issued_phase": issued_phase,
            "sender_hex": sender_pos,
            "recipient_hex": recipient_pos,
            "hex_distance": distance,
            "tbs_range_hex": TBS_RANGE_HEX,
            "distance_within_tbs": direct_tbs_available,
            "optical_range_hex_v2_2_rule": optical,
            "selected_medium": medium,
            "relay_hops": relay_hops,
            "handling_delay": handling,
            "encoding_delay": "", "relay_delay": "", "reencipher_delay": "",
            "queue_delay": "", "clarification_delay": "",
            "total_delay": handling,
            "route_reason": reason,
            "delivered_turn": message.get("delivered_turn"),
            "status": message.get("status"),
            "in_person": in_person,
            "report_author": (reports.get(message.get("message_id")) or {}).get(
                "reporting_formation_id"),
            "flags": [],
        }
        # ---- flags
        if not reason:
            findings["MISSING_ROUTE_PROVENANCE"].append(message["message_id"])
            row["flags"].append("MISSING_ROUTE_PROVENANCE")
        if direct_tbs_available and medium in ("wt_reencipher_relay", "wt_coded", "blinker"):
            findings["DIRECT_TBS_AVAILABLE_BUT_NOT_USED"].append(message["message_id"])
            row["flags"].append("DIRECT_TBS_AVAILABLE_BUT_NOT_USED")
        if medium == "wt_reencipher_relay":
            row["flags"].append("UNJUSTIFIED_REENCIPHER")
            findings["UNJUSTIFIED_REENCIPHER"].append(message["message_id"])
        if relay_hops and not in_person:
            row["flags"].append("UNJUSTIFIED_RELAY")
            findings["UNJUSTIFIED_RELAY"].append(message["message_id"])
        if medium in ("wt_reencipher_relay", "multi_hop") and not in_person:
            # No relay nodes, no crypto-domain transition: the fields the v2.3 rule
            # requires in order for such a route to be legal at all.
            payload = message.get("payload") or {}
            if not (payload.get("relay_nodes") and payload.get("why_reencipher_required")):
                findings["MISSING_RELAY_OR_CRYPTO_PROVENANCE"].append(message["message_id"])
                row["flags"].append("MISSING_RELAY_OR_CRYPTO_PROVENANCE")
        # The distance defect: a delay was charged because the message lay beyond the
        # *optical* horizon while still well inside the TBS radio range.
        if (distance is not None and optical is not None and distance > optical
                and distance <= TBS_RANGE_HEX and handling > 0):
            findings["DISTANCE_DELAY_BUG"].append(message["message_id"])
            row["flags"].append("DISTANCE_DELAY_BUG")
        row["flags"] = ";".join(row["flags"])
        rows.append(row)

    # ---- evidence for the report
    by_medium: dict[str, int] = {}
    for row in rows:
        by_medium[row["selected_medium"]] = by_medium.get(row["selected_medium"], 0) + 1
    distances = [row["hex_distance"] for row in rows if row["hex_distance"] is not None]
    reencipher = [row for row in rows if row["selected_medium"] == "wt_reencipher_relay"]
    per_side_medium: dict[str, dict[str, int]] = {}
    for row in rows:
        side = row["side"]
        per_side_medium.setdefault(side, {})
        per_side_medium[side][row["selected_medium"]] = (
            per_side_medium[side].get(row["selected_medium"], 0) + 1
        )

    csv_path = OUT / "raw" / "old_message_route_audit.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    reencipher_kinds: dict[str, int] = {}
    for row in reencipher:
        reencipher_kinds[row["kind"]] = reencipher_kinds.get(row["kind"], 0) + 1
    beyond_optical = [row for row in rows
                      if row["hex_distance"] is not None
                      and row["optical_range_hex_v2_2_rule"] is not None
                      and row["hex_distance"] > row["optical_range_hex_v2_2_rule"]]
    summary = {
        "messages": len(rows),
        "reencipher_by_kind": reencipher_kinds,
        "messages_beyond_optical_range": len(beyond_optical),
        "optical_range_values": sorted({row["optical_range_hex_v2_2_rule"] for row in rows
                                        if row["optical_range_hex_v2_2_rule"] is not None}),
        "by_medium": by_medium,
        "by_side_medium": per_side_medium,
        "distance_hex": {
            "min": min(distances) if distances else None,
            "max": max(distances) if distances else None,
            "mean": round(sum(distances) / len(distances), 1) if distances else None,
            "unresolved": len(rows) - len(distances),
        },
        "tbs_range_hex": TBS_RANGE_HEX,
        "within_tbs_range": sum(1 for row in rows
                                if row["hex_distance"] is not None
                                and row["hex_distance"] <= TBS_RANGE_HEX),
        "reencipher_reason_strings": sorted({row["route_reason"] for row in reencipher}),
        "findings": {key: len(value) for key, value in findings.items()},
    }
    (OUT / "raw" / "ir1_route_audit_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"-> {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
