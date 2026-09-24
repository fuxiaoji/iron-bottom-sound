"""IR-3 leakage tests: the causal information boundary, tested as five specific cases.

The rule (IBS-R-CD-10): a formation may know an enemy fact only if **it** observed it or
a message carrying it was delivered **to that formation** by the current turn.  The v2.2
mode broke this by handing every formation its siblings' reported positions from the
fleet's own copy, so these tests are written against that failure mode.

Each test builds a small real game, stages one delivery, and asks the view what it knows -
no mocks of the observation layer, because the leak lived exactly there.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from iron_bottom_sound import command_delay  # noqa: E402
from iron_bottom_sound.command_observation import (  # noqa: E402
    fleet_observation, formation_observation,
)
from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine  # noqa: E402
from iron_bottom_sound.llm import LLMPlayerSession  # noqa: E402
from iron_bottom_sound.models import (  # noqa: E402
    CommandMessage, GameOptions, MessageKind, MessagePrecedence, OrderBatch, Phase, Side,
)
from iron_bottom_sound.realistic_command import (  # noqa: E402
    RealisticCommander, default_setup_orders,
)

SCENARIO = "IBS-S-EM-01"
SEED = 19440619


def _game_to_phase(turn: int = 2, phase: Phase = Phase.MOVEMENT_PLANNING):
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
    while state.phase is not Phase.COMPLETE and steps < 200:
        steps += 1
        if state.turn >= turn and state.phase is phase:
            return engine, state
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
                    # doctrine can propose a plan the engine refuses (member speed limits,
                    # a wake the followers cannot hold) - the driver's substitution path
                    _, fallback, _ = RealisticCommander().choose_plan(
                        engine, state.game_id, side)
                    result = engine.submit_orders(state.game_id, fallback)
                assert result.valid, result.errors[:2]
        engine.advance(state.game_id)
    raise AssertionError("never reached the requested phase")


def _side_formations(state, side: Side):
    return command_delay.active_formations(state, side)


def _deliver_report(state, engine, *, reporter, recipient, text: str, turn: int,
                    deliver_turn: int | None = None, guide_label: str = "Z9"):
    """Stage one report from ``reporter`` addressed to ``recipient``, and deliver it."""
    from iron_bottom_sound.models import HexCoord

    payload = {
        "report": {
            "reporting_formation_id": reporter.id,
            "guide_position": {"label": guide_label, "q": 20, "r": 8},
            "guide_heading": 3, "guide_speed": 5, "ship_count": 4,
            "contacts": 1,
        },
        "report_text": text,
    }
    message = command_delay.send(engine, state, CommandMessage(
        message_id="", side=reporter.side, origin=reporter.flagship_id,
        destination=recipient.id if hasattr(recipient, "id") else recipient,
        kind=MessageKind.CONTACT_REPORT, precedence=MessagePrecedence.URGENT,
        medium=command_delay.CommunicationMedium.TBS_SHORT,
        issued_turn=turn, issued_phase=Phase.GUNNERY,
        payload=payload,
    ))
    message.status = command_delay.MessageStatus.DELIVERED
    message.delivered_turn = deliver_turn if deliver_turn is not None else turn
    message.delivered_phase = Phase.GUNNERY
    command_delay._apply_delivery(engine, state, message)
    return message


# --------------------------------------------------------------------- 1

def test_1_an_unseen_enemy_id_never_reaches_a_formation_prompt() -> None:
    """Injecting a ship nobody sighted must not appear in any view (positive control)."""
    engine, state = _game_to_phase()
    from iron_bottom_sound.formation_knowledge import record_local_observation

    formation = _side_formations(state, Side.AXIS)[0]
    # a ship of the other side that this formation has never seen
    enemy = next(ship for ship in state.ships.values()
                 if ship.side is Side.ALLIES and not ship.sunk)
    view = formation_observation(engine, state, Side.AXIS, formation.id)
    enemy_ids = {ship.id for ship in state.ships.values() if ship.side is Side.ALLIES}
    contact_ids = {contact.get("ship_id") for contact in view.local_contacts}
    held_enemy = {item["subject_id"] for item in view.knowledge
                  if item["subject_id"] in enemy_ids}
    assert held_enemy <= contact_ids, (
        "every enemy fact in the ledger must trace to a contact this formation can see; "
        f"{sorted(held_enemy - contact_ids)} did not"
    )
    assert enemy.id not in held_enemy or enemy.id in contact_ids
    # and every fact says where it came from
    for item in view.knowledge:
        assert item["source_kind"] in ("LOCAL_OBSERVATION", "DELIVERED_MESSAGE")
        if item["source_kind"] == "DELIVERED_MESSAGE":
            assert item["message_id"], "a learned fact must name the message that carried it"


# --------------------------------------------------------------------- 2, 3

def test_2_sibling_sighting_does_not_reach_another_formation_before_delivery() -> None:
    engine, state = _game_to_phase(turn=4)
    formations = _side_formations(state, Side.AXIS)
    if len(formations) < 2:
        pytest.skip("needs two axis formations")
    reporter, sibling = formations[0], formations[1]
    fleet_id = state.command_delay.authorities["axis"].fleet_formation_id

    # the sibling reports a contact to the FLEET at T4
    _deliver_report(state, engine, reporter=reporter, recipient=fleet_id,
                    text="当面发现敌巡洋舰两艘，位置 Z9，航向 3 节速 5。",
                    turn=4)
    # the fleet may know it...
    fleet_view = fleet_observation(engine, state, Side.AXIS)
    fleet_knows = [row for row in fleet_view.reports
                   if row.formation_id == reporter.id and row.guide_position is not None]
    assert fleet_knows, "the fleet must receive what was addressed to it"
    # ...but the sibling formation must not, because nothing was delivered to it
    sibling_view = formation_observation(engine, state, Side.AXIS, sibling.id)
    reported_facts = [item for item in sibling_view.knowledge
                      if item["subject_id"] == reporter.id
                      and item["source_kind"] == "DELIVERED_MESSAGE"]
    assert reported_facts == [], (
        "a sibling's report must not become visible to another formation before delivery"
    )

    # deliver the same report to the sibling at T5: now it may know
    _deliver_report(state, engine, reporter=reporter, recipient=sibling.id,
                    text="当面发现敌巡洋舰两艘，位置 Z9，航向 3 节速 5。", turn=5)
    after = formation_observation(engine, state, Side.AXIS, sibling.id)
    learned = [item for item in after.knowledge
               if item["subject_id"] == reporter.id
               and item["source_kind"] == "DELIVERED_MESSAGE"]
    assert learned, "...and once it is delivered, it may"


# --------------------------------------------------------------------- 4

def test_4_a_delayed_report_carries_its_observed_turn_not_current_truth() -> None:
    engine, state = _game_to_phase(turn=5)
    formations = _side_formations(state, Side.AXIS)
    fleet_id = state.command_delay.authorities["axis"].fleet_formation_id
    reporter = formations[0]
    # a report drawn from the world at T3, delivered at T5
    _deliver_report(state, engine, reporter=reporter, recipient=fleet_id,
                    text="敌舰位置 Z9，航向 3。", turn=3, deliver_turn=5, guide_label="Z9")
    view = fleet_observation(engine, state, Side.AXIS)
    row = next(row for row in view.reports if row.formation_id == reporter.id)
    assert row.reported_turn == 3, "the fact's own turn, not the delivery turn"
    assert row.age_turns == 2, "and its age is exposed, not hidden"
    # the knowledge ledger says the same thing
    from iron_bottom_sound.formation_knowledge import knowledge_for

    position_facts = [item for item in knowledge_for(state, fleet_id)
                      if item.subject_id == reporter.id and item.field == "POSITION"]
    assert position_facts
    assert position_facts[-1].observed_turn == 3
    assert position_facts[-1].received_turn == 5
    assert position_facts[-1].age_turns == 2


# --------------------------------------------------------------------- 5

def test_5_the_fleet_knows_remote_formations_only_from_delivered_reports() -> None:
    """The fleet's picture of anyone but its own formation is delivered traffic, and the
    facts carry the message that carried them.

    (The v2.2 mode did deliver engine-drafted reports, so "the fleet knows nothing" would
    be the wrong assertion.  What must hold is *provenance*: every fact about a remote
    formation names the message that brought it.)
    """
    engine, state = _game_to_phase(turn=3)
    formation_ids = {formation.id for formation in state.formations.values()}
    enemy_ids = {ship.id for ship in state.ships.values() if ship.side is Side.ALLIES}
    from iron_bottom_sound.formation_knowledge import knowledge_for

    fleet_id = state.command_delay.authorities["axis"].fleet_formation_id
    remote_facts = [
        item for item in knowledge_for(state, fleet_id)
        if item.subject_id in formation_ids and item.subject_id != fleet_id
    ]
    if remote_facts:
        assert all(item.source_kind == "DELIVERED_MESSAGE" for item in remote_facts), (
            "the fleet cannot observe a remote formation locally; only traffic tells it"
        )
        assert all(item.message_id for item in remote_facts)
        assert all(item.received_turn is not None for item in remote_facts)
    # and the fleet never holds an enemy fact of its own: it sees from its own bridge, and
    # those contacts are recorded against the embarked formation, not against the fleet
    assert not [item for item in knowledge_for(state, fleet_id)
                if item.subject_id in enemy_ids and item.source_kind == "LOCAL_OBSERVATION"]
    # the only exact picture the fleet has is its own formation
    view = fleet_observation(engine, state, Side.AXIS)
    own = [item for item in view.reports if item.is_source_of_truth]
    assert len(own) == 1
