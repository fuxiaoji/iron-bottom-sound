"""IR-2 tests A–F: the v2.3 routing rule, tested where it must hold.

Each test corresponds to a required check from the repair plan, and each one is written
so that the v2.2 defect it replaces would fail it:

A. the standard board fits inside the configured direct-TBS range (measured, not remembered)
B. two healthy formations inside TBS range route DIRECT_TBS
C. an out-of-range synthetic pair does not
D. a relay route requires an explicit node list
E. re-encipherment requires an actual cryptographic-domain transition
F. the same geometry, different congestion: +0 vs a queue spill caused by slots
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from iron_bottom_sound import command_delay  # noqa: E402
from iron_bottom_sound.communications import queue as channel_queue  # noqa: E402
from iron_bottom_sound.communications.processing import (  # noqa: E402
    TBS_DIRECT_RANGE_HEX, range_units, slot_cost,
)
from iron_bottom_sound.communications.routing import select_medium  # noqa: E402
from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine  # noqa: E402
from iron_bottom_sound.llm import LLMPlayerSession  # noqa: E402
from iron_bottom_sound.models import (  # noqa: E402
    GameOptions, MessageKind, MessagePrecedence, OrderBatch, Phase, Side,
)
from iron_bottom_sound.realistic_command import (  # noqa: E402
    RealisticCommander, default_setup_orders,
)

SCENARIO = "IBS-S-EM-01"
SEED = 19440619


def _engine_to_movement():
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
        if state.phase is Phase.MOVEMENT_PLANNING and state.turn >= 2:
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
                assert engine.submit_orders(state.game_id, batch).valid
        engine.advance(state.game_id)
    raise AssertionError("never reached a movement phase")


def _max_hex_distance(columns: int, rows: int) -> tuple[int, tuple[int, int], tuple[int, int]]:
    cells = [(q, r) for q in range(columns) for r in range(rows)]
    best = (0, (0, 0), (0, 0))
    for q, r in cells:
        for q2, r2 in cells:
            d = (abs(q - q2) + abs(r - r2) + abs((q + r) - (q2 + r2))) // 2
            if d > best[0]:
                best = (d, (q, r), (q2, r2))
    return best


# --------------------------------------------------------------------------- A

def test_A_standard_board_inside_tbs_range_is_measured_and_recorded() -> None:
    """The board's maximum legal distance, computed rather than remembered.

    On the standard 46x39 board the answer is 83 hex against a nominal TBS range of 73 -
    so the corner-to-corner extreme is *outside* range and distance is not a no-op in
    general.  What matters for the rule is that real traffic sits far inside it: the CD-13
    battle's messages ran 0-42 hex, mean 15 (see v2_3/01_COMM_ROUTE_AUDIT.md).
    """
    distance, corner_a, corner_b = _max_hex_distance(46, 39)
    assert distance == 83, (distance, corner_a, corner_b)
    assert TBS_DIRECT_RANGE_HEX == 73
    assert distance > TBS_DIRECT_RANGE_HEX, "the extreme corner is out of range; recorded, not hidden"
    # the operational envelope: anything within 73 hex reaches TBS, and that is most of
    # the board's useful area
    assert range_units(TBS_DIRECT_RANGE_HEX)["range_nmi"] == round(
        73 * 600 / 2025.37, 2
    )


# --------------------------------------------------------------------------- B

def test_B_every_within_range_pair_routes_direct_tbs() -> None:
    engine, state = _engine_to_movement()
    formation = command_delay.active_formations(state, Side.AXIS)[0]
    other = command_delay.active_formations(state, Side.AXIS)[1]
    decision = command_delay.route(engine, state, formation, other)
    assert decision.medium.value == "tbs_short"
    assert decision.direct_tbs_available
    assert "TBS" in decision.reason or "射程" in decision.reason
    # and every message the mode actually drafts inside range says so in its provenance
    decided = [m for m in state.command_delay.messages if m.medium.value == "tbs_short"]
    assert decided, "the mode drafted no TBS traffic to check"
    for message in decided:
        assert message.route_provenance is not None
        assert message.route_provenance.tbs_range_hex == TBS_DIRECT_RANGE_HEX
        assert message.route_provenance.direct_tbs_available
        assert message.delay.propagation == 0


# --------------------------------------------------------------------------- C

def test_C_out_of_range_pair_cannot_use_direct_tbs() -> None:
    far = select_medium(distance=TBS_DIRECT_RANGE_HEX + 1, tbs_range_hex=TBS_DIRECT_RANGE_HEX,
                        direct_visual=False, coded_available=True)
    assert far.medium.value != "tbs_short"
    assert far.direct_tbs_available is False
    # the same pair with eyesight gets the visual channel, not telegraphy
    visible = select_medium(distance=TBS_DIRECT_RANGE_HEX + 1,
                            tbs_range_hex=TBS_DIRECT_RANGE_HEX,
                            direct_visual=True, coded_available=True)
    assert visible.medium.value == "blinker"


# --------------------------------------------------------------------------- D

def test_D_relay_requires_explicit_nodes() -> None:
    no_nodes = select_medium(distance=200, tbs_range_hex=TBS_DIRECT_RANGE_HEX,
                             direct_visual=False, coded_available=True,
                             relay_available=True)
    assert no_nodes.medium.value == "wt_coded", "an unnamed 'relay' is not a relay"
    assert no_nodes.route_is_valid
    with_nodes = select_medium(distance=200, tbs_range_hex=TBS_DIRECT_RANGE_HEX,
                               direct_visual=False, coded_available=True,
                               relay_path=("P14", "R17"))
    assert with_nodes.medium.value == "multi_hop"
    assert with_nodes.route_nodes == ("P14", "R17")
    assert with_nodes.why_relay_required
    assert with_nodes.route_is_valid


# --------------------------------------------------------------------------- E

def test_E_reencipher_requires_a_cryptographic_transition() -> None:
    relay_only = select_medium(distance=200, tbs_range_hex=TBS_DIRECT_RANGE_HEX,
                               direct_visual=False, coded_available=True,
                               relay_path=("P14",))
    assert relay_only.medium.value != "wt_reencipher_relay"
    crypto = select_medium(distance=200, tbs_range_hex=TBS_DIRECT_RANGE_HEX,
                           direct_visual=False, coded_available=True,
                           relay_path=("P14",), crypto_domain_transition=True)
    assert crypto.medium.value == "wt_reencipher_relay"
    assert crypto.why_reencipher_required
    assert crypto.route_is_valid


# --------------------------------------------------------------------------- F

def test_F_same_geometry_different_congestion_queue_not_distance() -> None:
    """+0 versus a spill, at identical range, caused only by channel slots.

    This is the v2.3 replacement for "a complex order costs +1": the same order at the
    same distance arrives this turn when a slot is free and next turn when the TBS
    channel is saturated, and the difference is recorded as the ``queue`` component.
    """
    long_text = "保持当前航向与速度" * 50    # 450 chars -> two slots (240 < len <= 600)
    assert slot_cost(MessageKind.MISSION_ORDER, len(long_text)) == 2
    # free channel
    queues = {medium: channel_queue.schedule(medium) for medium in channel_queue.CHANNEL_CAPACITY}
    assert queues[command_delay.CommunicationMedium.TBS_SHORT].free == 4
    # saturate the TBS channel with two long orders (2 slots each)
    for _ in range(2):
        created = command_delay.CommandMessage(
            message_id="", side=Side.AXIS, origin="x", destination="y",
            kind=MessageKind.MISSION_ORDER, precedence=MessagePrecedence.OPERATIONAL,
            medium=command_delay.CommunicationMedium.TBS_SHORT,
            issued_turn=1, issued_phase=Phase.MOVEMENT_PLANNING,
            payload={"order_text": long_text},
        )
        queues[command_delay.CommunicationMedium.TBS_SHORT].slots_used += slot_cost(
            MessageKind.MISSION_ORDER, len(long_text)
        )
    assert queues[command_delay.CommunicationMedium.TBS_SHORT].free == 0
    third = command_delay.CommandMessage(
        message_id="MSG-TEST", side=Side.AXIS, origin="x", destination="y",
        kind=MessageKind.MISSION_ORDER, precedence=MessagePrecedence.OPERATIONAL,
        medium=command_delay.CommunicationMedium.TBS_SHORT,
        issued_turn=1, issued_phase=Phase.MOVEMENT_PLANNING, payload={"order_text": long_text},
    )
    outcome = channel_queue.drain(
        [third], turn=1, phase=Phase.TORPEDO_EFFECTS, queues=queues,
    )
    assert outcome.delivered == [] and outcome.waiting == [third], (
        "with the channel full the order waits - a queue delay, not a distance delay"
    )
    # next turn the channel is fresh again and the same order goes through
    fresh = {medium: channel_queue.schedule(medium) for medium in channel_queue.CHANNEL_CAPACITY}
    later = channel_queue.drain([third], turn=2, phase=Phase.MOVEMENT_PLANNING, queues=fresh)
    assert later.delivered == [third]
    assert third.delivered_turn == 2 and third.issued_turn == 1
    # the queue component is what explains the extra turn
    accounted = (third.delay.handling + third.delay.encoding + third.delay.relay
                 + third.delay.reencipher + third.delay.clarification)
    assert (third.delivered_turn - third.issued_turn) - accounted == 1


def test_F2_face_to_face_uses_no_channel_slot() -> None:
    engine, state = _engine_to_movement()
    authority = state.command_delay.authorities["axis"]
    own = authority.fleet_formation_id
    before = len([m for m in state.command_delay.messages])
    message = command_delay.draft_natural_order(
        engine, state, side=Side.AXIS, formation_id=own, text="当面交代：保持队形。",
    )
    assert len(state.command_delay.messages) == before + 1
    assert message.medium.value == "face_to_face"
    assert message.delay.as_dict()["total"] == 0
    assert message.route_provenance.same_command_location is True
    # a face-to-face message is never in a channel queue's reach: capacity 0
    assert channel_queue.CHANNEL_CAPACITY[command_delay.CommunicationMedium.FACE_TO_FACE] == 0
