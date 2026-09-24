"""IR-5: reporting is event-driven, and the radio policy actually prevents traffic.

The plan's four cases:

1. a no-change mission over five turns generates no routine messages unless the order
   asked for them;
2. a new contact breaks CONTACT_ONLY correctly (i.e. it is allowed, routine traffic is not);
3. strict silence blocks a routine report;
4. a queued urgent contact is transmitted ahead of routine traffic.

The v2.2 behaviour these replace: every formation drafted a report every phase - 68 in one
seven-turn battle, 40 in another - so silence was never modelled and the channel was full
of "no change".
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from iron_bottom_sound import command_delay, reporting  # noqa: E402
from iron_bottom_sound.delegation import mission_order_template  # noqa: E402
from iron_bottom_sound.communications import queue as channel_queue  # noqa: E402
from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine  # noqa: E402
from iron_bottom_sound.llm import LLMPlayerSession  # noqa: E402
from iron_bottom_sound.models import (  # noqa: E402
    CommandMessage, GameOptions, MessageKind, MessagePrecedence, OrderBatch, Phase,
    RadioPolicy, Side,
)
from iron_bottom_sound.realistic_command import (  # noqa: E402
    RealisticCommander, default_setup_orders,
)

SCENARIO = "IBS-S-EM-01"
SEED = 19440619


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


def _advance_turns(engine, state, sessions, turns: int):
    target = state.turn + turns
    steps = 0
    while state.turn < target and state.phase is not Phase.COMPLETE and steps < 400:
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


# --------------------------------------------------------------------- 1

def test_1_a_quiet_mission_generates_no_routine_traffic(monkeypatch) -> None:
    """Five turns of nothing happening produce no reports at all (no periodic order)."""
    engine, state, sessions = _game()
    _advance_turns(engine, state, sessions, turns=3)
    reports = [message for message in state.command_delay.messages
               if message.kind in (MessageKind.SITREP, MessageKind.CONTACT_REPORT)]
    assert reports == [], (
        "no contact, no damage and no periodic requirement means no traffic: "
        f"{[m.message_id for m in reports]}"
    )
    # The silence is the default: an order that *asks* for periodic reporting gets it,
    # and only then.  Contacts are forced to zero and the damage baseline is set, because a
    # contact report or a damage report legitimately outranks a periodic sitrep - that
    # ordering is what case 2 and the trigger list are about.  The order's report window
    # names this very turn so the test does not depend on the cycle phase.
    monkeypatch.setattr(command_delay, "_formation_contact_count",
                        lambda engine_, state_, formation: 0)
    axis_authority = state.command_delay.authorities["axis"]
    remote = next(formation for formation in command_delay.active_formations(state, Side.AXIS)
                  if formation.id != axis_authority.fleet_formation_id)
    order = mission_order_template(
        order_id="periodic-1", formation_id=remote.id, side=Side.AXIS, turn=state.turn,
        issued_by="fleet", mission="保持监视并定期报告。", intent="监视", task="监视",
        report_requirements=["PERIODIC_SITREP"], report_window_turns=[state.turn],
    )
    # an order is only in force once it has been delivered (confirmed_turn), so the test
    # stages it as delivered rather than reaching into the order book
    order.confirmed_turn = state.turn
    order.valid_from_turn = state.turn
    state.command_delay.mission_orders.append(order)
    entry = state.command_delay.formations[remote.id]
    entry.active_order_id = order.order_id
    entry.last_reported_hull = reporting.hull_fraction(state, remote)
    entry.last_reported_contacts = 0
    assert reporting.periodic_due(state, order) is True, "the window names this turn"
    command_delay.draft_reports(engine, state)
    sreps = [message for message in state.command_delay.messages
             if message.kind is MessageKind.SITREP]
    assert sreps, "an order that asks for periodic reporting must get it"
    assert all((message.payload or {}).get("trigger") == "PERIODIC_DUE" for message in sreps)
    assert all((message.payload or {}).get("report", {}).get("reporting_formation_id")
               == remote.id for message in sreps)
    # and without that requirement the very same geometry sends nothing
    order.report_requirements = ["contact report on first sighting"]
    order.report_window_turns = []
    state.command_delay.formations[remote.id].last_reported_contacts = 0
    before = len(state.command_delay.messages)
    command_delay.draft_reports(engine, state)
    assert len(state.command_delay.messages) == before, "no requirement, no periodic traffic"


# --------------------------------------------------------------------- 2

def test_2_a_new_contact_breaks_contact_only_correctly(monkeypatch) -> None:
    engine, state, sessions = _game()
    axis = state.command_delay.authorities["axis"]
    remote = next(formation for formation in command_delay.active_formations(state, Side.AXIS)
                  if formation.id != axis.fleet_formation_id)
    state.command_delay.formations[remote.id].radio_policy = RadioPolicy.CONTACT_ONLY

    # no contact: nothing may be transmitted, and the suppression is recorded
    monkeypatch.setattr(command_delay, "_formation_contact_count",
                        lambda engine_, state_, formation: 0)
    command_delay.draft_reports(engine, state)
    assert not [m for m in state.command_delay.messages if m.side is Side.AXIS]

    # a new contact: the contact report goes
    monkeypatch.setattr(command_delay, "_formation_contact_count",
                        lambda engine_, state_, formation: 3)
    drafted = command_delay.draft_reports(engine, state)
    assert drafted, "CONTACT_ONLY exists to let contact reports through"
    assert all(message.kind is MessageKind.CONTACT_REPORT for message in drafted)
    assert all(message.precedence is MessagePrecedence.URGENT for message in drafted)

    # and a *routine* item under the same policy is refused with a reason
    allowed, reason = reporting.policy_allows(
        RadioPolicy.CONTACT_ONLY,
        reporting.Trigger("PERIODIC_DUE", MessageKind.SITREP,
                          MessagePrecedence.ROUTINE, "定期报告"),
        window_open=False, under_attack=False,
    )
    assert not allowed and "CONTACT_ONLY" in reason


# --------------------------------------------------------------------- 3

def test_3_strict_silence_blocks_routine_and_yields_only_to_emergency(monkeypatch) -> None:
    engine, state, sessions = _game()
    axis = state.command_delay.authorities["axis"]
    remote = next(formation for formation in command_delay.active_formations(state, Side.AXIS)
                  if formation.id != axis.fleet_formation_id)
    entry = state.command_delay.formations[remote.id]
    entry.radio_policy = RadioPolicy.STRICT_SILENCE
    entry.last_reported_hull = 1.0        # nothing has damaged it
    before = len(state.command_delay.messages)

    monkeypatch.setattr(command_delay, "_formation_contact_count",
                        lambda engine_, state_, formation: 2)
    command_delay.draft_reports(engine, state)
    from_remote = [m for m in state.command_delay.messages[before:]
                   if m.origin == remote.flagship_id]
    assert from_remote == [], (
        "strict silence must actually prevent the transmission, so that no report can "
        "claim 'maintaining radio silence' in the same turn as a routine message"
    )
    suppressed = [event for event in state.events if event.type == "report_suppressed"]
    assert suppressed, "the suppression is recorded, not silent"

    # an emergency is not the formation's to withhold
    allowed, reason = reporting.policy_allows(
        RadioPolicy.STRICT_SILENCE,
        reporting.Trigger("MAJOR_DAMAGE", MessageKind.CONTACT_REPORT,
                          MessagePrecedence.URGENT, "编队重创"),
        window_open=False, under_attack=True,
    )
    assert allowed and "遇袭" in reason


# --------------------------------------------------------------------- 4

def test_4_urgent_traffic_preempts_routine_in_the_queue() -> None:
    """A full channel still gets the urgent message out; the routine one waits."""
    queues = {medium: channel_queue.schedule(medium)
              for medium in channel_queue.CHANNEL_CAPACITY}
    tbs = command_delay.CommunicationMedium.TBS_SHORT
    capacity = channel_queue.CHANNEL_CAPACITY[tbs]
    assert capacity >= 2

    def message(index: int, kind: MessageKind, precedence: MessagePrecedence):
        return CommandMessage(
            message_id=f"MSG-{index:03d}", side=Side.AXIS, origin="a", destination="b",
            kind=kind, precedence=precedence, medium=tbs,
            issued_turn=1, issued_phase=Phase.MOVEMENT_PLANNING,
            payload={"report_text": "x" * 20},
        )

    routine = [message(index, MessageKind.SITREP, MessagePrecedence.ROUTINE)
               for index in range(capacity)]           # fills the channel
    urgent = message(99, MessageKind.CONTACT_REPORT, MessagePrecedence.URGENT)
    outcome = channel_queue.drain(routine + [urgent], turn=1,
                                  phase=Phase.TORPEDO_EFFECTS, queues=queues)
    delivered_ids = {item.message_id for item in outcome.delivered}
    assert urgent.message_id in delivered_ids, (
        "precedence reorders the queue: the urgent contact takes the slot"
    )
    assert len(outcome.delivered) == capacity
    assert outcome.waiting, "and a routine message is the one left waiting"
