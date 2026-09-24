"""IR-4: a MissionOrder is a persistent object with a revision lineage.

The plan's six-turn case, executed as a test:

    T1 an order is issued
    T2-T4 no new order; the formation continues its task from the standing order
    T5 a delayed amendment arrives and takes effect as a later revision
    T6 an old superseded order arrives late and is refused

Plus the anti-spam rule the battle report exposed: a commander that restates the mission
it already holds issues nothing (the CD-13 battle sent 63 mission orders over 11 turns,
most of them restatements of "continue as ordered").
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from iron_bottom_sound import command_delay  # noqa: E402
from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine  # noqa: E402
from iron_bottom_sound.llm import LLMPlayerSession  # noqa: E402
from iron_bottom_sound.models import (  # noqa: E402
    GameOptions, MessageKind, MessageStatus, OrderBatch, Phase, Side,
)
from iron_bottom_sound.realistic_command import (  # noqa: E402
    RealisticCommander, default_setup_orders,
)

SCENARIO = "IBS-S-EM-01"
SEED = 19440619


def _advance(engine, state, sessions, *, turns: int, max_steps: int = 400):
    """Advance the game ``turns`` turns, submitting the mode's own batches."""
    target = state.turn + turns
    steps = 0
    while state.turn < target and state.phase is not Phase.COMPLETE and steps < max_steps:
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


def _game():
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
    return engine, state, sessions


def _deliver_now(engine, state, message):
    """Deliver a message immediately (the tests stage the traffic, not the clock)."""
    message.status = MessageStatus.DELIVERED
    message.delivered_turn = state.turn
    message.delivered_phase = state.phase
    command_delay._apply_delivery(engine, state, message)
    return message


def test_mission_order_persists_with_a_revision_lineage() -> None:
    engine, state, sessions = _game()
    axis = state.command_delay.authorities["axis"]
    own, remote = axis.fleet_formation_id, None
    for formation in command_delay.active_formations(state, Side.AXIS):
        if formation.id != own:
            remote = formation.id
            break
    assert remote, "need a subordinate formation"

    # T1: the fleet issues the mission
    first = command_delay.draft_natural_order(
        engine, state, side=Side.AXIS, formation_id=remote,
        text="向东南接敌，压制敌巡洋舰；如遇优势敌力则跟踪并报告。",
    )
    assert first is not None
    order = next(item for item in state.command_delay.mission_orders
                 if item.order_id == first.payload["order_id"])
    assert order.order_event == "NEW_ORDER" and order.revision == 1
    _deliver_now(engine, state, first)
    assert state.command_delay.formations[remote].active_order_id == order.order_id

    # the order persists across turns with no further traffic
    memory = state.command_delay.memories.get(remote)
    _advance(engine, state, sessions, turns=3)   # T2, T3, T4
    assert state.turn >= 4
    active = command_delay.active_mission_order(state, remote)
    assert active is not None and active.order_id == order.order_id, (
        "a standing order must persist until superseded, expired or cancelled"
    )
    assert active.is_active and active.cancelled_turn is None

    # T2-T4: a commander restating the same mission issues nothing
    before = len(state.command_delay.mission_orders)
    restated = command_delay.draft_natural_order(
        engine, state, side=Side.AXIS, formation_id=remote,
        text="向东南接敌，压制敌巡洋舰；如遇优势敌力则跟踪并报告。",   # same words
    )
    assert restated is None, "a restatement must not create a revision"
    assert len(state.command_delay.mission_orders) == before
    assert any(event.type == "mission_order_restated" for event in state.events)

    # declined outright
    assert command_delay.draft_natural_order(
        engine, state, side=Side.AXIS, formation_id=remote, text="保持现状。",
        order_event="NO_NEW_ORDER",
    ) is None

    # T5: a delayed amendment arrives and becomes revision 2
    amendment = command_draft = command_delay.draft_natural_order(
        engine, state, side=Side.AXIS, formation_id=remote,
        text="改令：转向东北，脱离接触并保持监视。",
    )
    assert amendment is not None
    amended = next(item for item in state.command_delay.mission_orders
                   if item.order_id == amendment.payload["order_id"])
    assert amended.order_event == "AMEND_ORDER"
    assert amended.revision == 2 and amended.amends_order_id == order.order_id
    _deliver_now(engine, state, amendment)
    assert state.command_delay.formations[remote].active_order_id == amended.order_id

    # T6: an old straggler from the same lineage arrives late and is refused
    straggler = CommandMessage_stub(state, remote, order)
    before_orders = len(state.command_delay.mission_orders)
    _deliver_now(engine, state, straggler)
    assert straggler.status == MessageStatus.SUPERSEDED
    assert "revision" in (straggler.reason or "") or "superseded" in (straggler.reason or "")
    assert state.command_delay.formations[remote].active_order_id == amended.order_id
    assert len(state.command_delay.mission_orders) == before_orders


def CommandMessage_stub(state, formation_id, older):
    """A late redelivery of the *older* order, which must be refused."""
    from iron_bottom_sound.models import CommandMessage, MessagePrecedence

    return CommandMessage(
        message_id="", side=Side.AXIS, origin=older.issued_by or "fleet",
        destination=formation_id, kind=MessageKind.MISSION_ORDER,
        precedence=MessagePrecedence.OPERATIONAL,
        medium=command_delay.CommunicationMedium.TBS_SHORT,
        issued_turn=older.issued_turn, issued_phase=Phase.MOVEMENT_PLANNING,
        payload={"order_id": older.order_id,
                 "order_text": older.mission,
                 "order_event": older.order_event,
                 "revision": older.revision,
                 "amends_order_id": older.amends_order_id},
    )


def test_a_face_to_face_order_is_confirmed_in_force_and_lineaged() -> None:
    """An order handed over in person must be as binding as one sent by radio.

    The regression this pins: the in-person path folded the delivery in *before* stamping
    the delivery turn, so `confirmed_turn` stayed None.  The order was consequently never
    "in force" - the revision lineage never advanced and an identical order could be issued
    again, which the IR-9 battle report caught as "every order rev=1, one restatement
    accepted".
    """
    engine, state, sessions = _game()
    axis = state.command_delay.authorities["axis"]
    own = axis.fleet_formation_id                      # the formation the admiral sails in

    first = command_delay.draft_natural_order(
        engine, state, side=Side.AXIS, formation_id=own, text="保持队形，向东南接敌。",
    )
    assert first is not None and first.medium.value == "face_to_face"
    order = next(item for item in state.command_delay.mission_orders
                 if item.order_id == first.payload["order_id"])
    assert order.confirmed_turn is not None, "a hand-over in person is a delivery"
    active = command_delay.active_mission_order(state, own)
    assert active is not None and active.order_id == order.order_id, (
        "the order the admiral handed over must be the one in force"
    )

    # the same words again are a restatement, not a new order
    again = command_delay.draft_natural_order(
        engine, state, side=Side.AXIS, formation_id=own, text="保持队形，向东南接敌。")
    assert again is None
    assert any(event.type == "mission_order_restated" for event in state.events)

    # a changed order becomes revision 2 of that lineage
    second = command_delay.draft_natural_order(
        engine, state, side=Side.AXIS, formation_id=own, text="转向东北，脱离接触。")
    assert second is not None
    amended = next(item for item in state.command_delay.mission_orders
                   if item.order_id == second.payload["order_id"])
    assert amended.revision == 2 and amended.amends_order_id == order.order_id


def test_cancel_order_removes_the_active_order() -> None:
    engine, state, sessions = _game()
    axis = state.command_delay.authorities["axis"]
    own = axis.fleet_formation_id
    remote = next(formation.id for formation in command_delay.active_formations(state, Side.AXIS)
                  if formation.id != own)
    first = command_delay.draft_natural_order(
        engine, state, side=Side.AXIS, formation_id=remote, text="向西北接敌。")
    _deliver_now(engine, state, first)
    assert state.command_delay.formations[remote].active_order_id is not None

    cancel = command_delay.draft_natural_order(
        engine, state, side=Side.AXIS, formation_id=remote,
        text="撤销前述命令，就地待命。", order_event="CANCEL_ORDER",
    )
    assert cancel is not None
    _deliver_now(engine, state, cancel)
    entry = state.command_delay.formations[remote]
    assert entry.active_order_id is None
    cancelled = next(item for item in state.command_delay.mission_orders
                     if item.order_id == cancel.payload["order_id"])
    assert cancelled.cancelled_turn is not None
    assert any(event.type == "mission_order_cancelled" for event in state.events)
