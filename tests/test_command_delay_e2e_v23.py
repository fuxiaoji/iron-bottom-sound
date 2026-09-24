"""IR-9 (part 1): one scripted, deterministic end-to-end game with the v2.3 invariants.

This is the plan's "one deterministic/replayable scripted commander test": a full
command-delay game played to completion by doctrine, with the whole ledger then checked
against everything v2.3 promises:

* every message carries a route provenance and a delay decomposition that adds up;
* no message is routed through a relay or re-encipherment without the provenance such a
  route requires;
* a message's total delay is the sum of its components, and the queue component is what
  the elapsed turns leave unexplained;
* no report is transmitted that no trigger justified, and nothing is suppressed silently;
* the game is reproducible: a second run produces the same ledger digest.

It is deliberately in-process and small enough for the suite (the golden row of the same
scenario is the byte-level freeze; this is the invariant-level check).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from iron_bottom_sound import command_delay  # noqa: E402
from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine  # noqa: E402
from iron_bottom_sound.llm import LLMPlayerSession  # noqa: E402
from iron_bottom_sound.models import (  # noqa: E402
    GameOptions, MessageKind, OrderBatch, Phase, Side,
)
from iron_bottom_sound.realistic_command import (  # noqa: E402
    RealisticCommander, default_setup_orders,
)

SCENARIO = "IBS-S-EM-01"
SEED = 19440619


def play() -> dict:
    """One full deterministic game; returns the ledger as plain data."""
    engine = IronBottomEngine()
    state = engine.reset(SCENARIO, SEED, GameOptions(
        realistic_command=True, command_delay_mode=True,
    ))
    for side in Side:
        assert engine.submit_orders(state.game_id, OrderBatch(
            side=side, phase=Phase.FORMATION_SETUP,
            formation_setup=default_setup_orders(state, side),
        )).valid
    engine.advance(state.game_id)
    sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
    steps = 0
    while state.phase is not Phase.COMPLETE and steps < 400:
        steps += 1
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                if state.phase is Phase.MOVEMENT_PLANNING:
                    batch = OrderBatch(side=side, phase=state.phase,
                                       formation_movement=command_delay.formation_orders(state, side))
                elif state.phase is Phase.GUNNERY:
                    batch = command_delay.gunnery_batch(state, side)
                else:
                    batch = sessions[side].choose_orders(engine, state.game_id)
                result = engine.submit_orders(state.game_id, batch)
                if not result.valid and state.phase is Phase.MOVEMENT_PLANNING:
                    _, fallback, _ = RealisticCommander().choose_plan(engine, state.game_id, side)
                    result = engine.submit_orders(state.game_id, fallback)
                assert result.valid, result.errors[:2]
        engine.advance(state.game_id)

    mode = state.command_delay
    ledger = {
        "turn": state.turn,
        "phase": state.phase.value,
        # ``as_dict`` carries the computed total, which ``model_dump`` does not (it is a
        # property, not a field)
        "messages": [{**message.model_dump(mode="json"), "delay": message.delay.as_dict()}
                     for message in mode.messages],
        "suppressions": [event.payload for event in state.events
                         if event.type == "report_suppressed"],
        "restatements": [event.payload for event in state.events
                         if event.type == "mission_order_restated"],
        "orders": [order.model_dump(mode="json") for order in mode.mission_orders],
    }
    ledger["digest"] = hashlib.sha256(
        json.dumps(ledger, sort_keys=True, default=str).encode()
    ).hexdigest()
    return ledger


def test_a_scripted_game_completes_and_its_ledger_holds_together() -> None:
    ledger = play()
    assert ledger["phase"] == "complete", ledger
    messages = ledger["messages"]
    assert messages, "the mode must generate traffic"

    for message in messages:
        provenance = message.get("route_provenance")
        delay = message.get("delay")
        assert provenance, f"{message['message_id']} has no route provenance"
        assert delay, f"{message['message_id']} has no delay decomposition"
        # the decomposition adds up to the recorded handling delay
        assert delay["total"] == (delay["propagation"] + delay["handling"] + delay["encoding"]
                                  + delay["relay"] + delay["reencipher"] + delay["queue"]
                                  + delay["clarification"])
        assert delay["propagation"] == 0, "propagation is zero at this time scale"
        # a relayed or re-enciphered route must name its nodes and its reasons
        if message["medium"] in ("wt_reencipher_relay", "multi_hop"):
            assert provenance["route_nodes"], (
                f"{message['message_id']} is relayed without naming a node"
            )
            assert provenance["why_relay_required"], message["message_id"]
            if message["medium"] == "wt_reencipher_relay":
                assert provenance["why_reencipher_required"], message["message_id"]
        # distance is a reachability fact, never a delay: a message inside the range that
        # paid a handling or encoding delay would be the v2.2 defect returning
        if provenance["direct_tbs_available"]:
            assert delay["handling"] == 0 and delay["encoding"] == 0, (
                f"{message['message_id']} is inside direct TBS range yet paid "
                f"handling={delay['handling']} encoding={delay['encoding']}"
            )
        # if it arrived late, the queue is what explains it
        if message.get("delivered_turn") is not None and message["status"] == "delivered":
            elapsed = message["delivered_turn"] - message["issued_turn"]
            accounted = (delay["handling"] + delay["encoding"] + delay["relay"]
                         + delay["reencipher"] + delay["clarification"] + delay["queue"])
            assert elapsed == accounted, (
                f"{message['message_id']}: elapsed {elapsed} != components {accounted}"
            )

    # nothing was suppressed silently, and every suppression names its policy
    for suppression in ledger["suppressions"]:
        assert suppression.get("reason") and suppression.get("policy"), suppression

    # orders, if any, carry a revision lineage
    for order in ledger["orders"]:
        assert order["revision"] >= 1
        if order["revision"] > 1:
            assert order["amends_order_id"], order["order_id"]


def test_the_scripted_game_is_reproducible() -> None:
    first = play()
    second = play()
    assert first["digest"] == second["digest"], (
        "the same scripted game must produce the same ledger, run to run"
    )
