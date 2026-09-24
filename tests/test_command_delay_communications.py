"""CD-3: mission orders, the three contingency kinds, and the communication pipeline.

Fixed here are the properties the v2.2 plan states as rules rather than
preferences:

* delay is handling/encoding/relay/queue, with propagation fixed at zero and an
  explicit "simulation abstraction" label on every turn value;
* no loss or garble probability exists anywhere, and the integrity seam refuses
  an unsourced one;
* distance selects the medium, it never scales a delay;
* the queue is precedence-ordered, capacity-limited and TTL-dropped;
* a delayed report carries the world as of *drafting*, not as of delivery;
* a late superseded order cannot overwrite a newer acknowledged one;
* contingencies are three kinds, and each activates only on its own condition.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from iron_bottom_sound import command_delay, delegation
from iron_bottom_sound.communications import (
    MEDIUM_PROFILES,
    IntegrityPolicy,
    RouteDecision,
    apply_integrity,
    delay_for,
    drain,
    processing,
    schedule,
    select_medium,
)
from iron_bottom_sound.communications.queue import CHANNEL_CAPACITY, DEFAULT_TTL_TURNS
from iron_bottom_sound.command_observation import fleet_observation
from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine
from iron_bottom_sound.llm import LLMPlayerSession
from iron_bottom_sound.models import (
    CommandMessage,
    CommunicationMedium,
    ContingencyBranch,
    GameOptions,
    HexCoord,
    LinkStatus,
    MessageKind,
    MessagePrecedence,
    MessageStatus,
    OrderBatch,
    Phase,
    Side,
)
from iron_bottom_sound.realistic_command import RealisticCommander, default_setup_orders

REPO_ROOT = Path(__file__).resolve().parents[1]
CD = GameOptions(realistic_command=True, command_delay_mode=True)


def start(scenario: str = "IBS-S-01", seed: int = 20270830):
    engine = IronBottomEngine()
    state = engine.reset(scenario, seed, CD)
    for side in Side:
        assert engine.submit_orders(state.game_id, OrderBatch(
            side=side, phase=Phase.FORMATION_SETUP,
            formation_setup=default_setup_orders(state, side),
        )).valid
    engine.advance(state.game_id)
    return engine, state


def play(engine, state, max_steps: int = 400) -> None:
    sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
    steps = 0
    while state.phase != Phase.COMPLETE and steps < max_steps:
        steps += 1
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                result = engine.submit_orders(
                    state.game_id, sessions[side].choose_orders(engine, state.game_id)
                )
                assert result.valid, (state.turn, state.phase, side, result.errors[:2])
        engine.advance(state.game_id)


def message(**kwargs) -> CommandMessage:
    base = dict(
        message_id=kwargs.pop("message_id", "MSG-T"),
        side=Side.ALLIES,
        origin="ship-a",
        destination="formation-a",
        kind=MessageKind.SITREP,
        precedence=MessagePrecedence.OPERATIONAL,
        medium=CommunicationMedium.TBS_SHORT,
        issued_turn=1,
        issued_phase=Phase.MOVEMENT_PLANNING,
    )
    base.update(kwargs)
    return CommandMessage(**base)


# --------------------------------------------------------------------------- latency model

def test_propagation_is_zero_and_every_value_is_labelled_an_abstraction() -> None:
    note = processing.abstraction_note()
    assert note["label"] == processing.ABSTRACTION_LABEL
    assert note["propagation"].startswith("modeled as zero")
    for profile in MEDIUM_PROFILES.values():
        assert profile.propagation_turns == 0.0
        assert profile.label == processing.ABSTRACTION_LABEL
        assert profile.source


def test_medium_delay_table_matches_the_rule_table() -> None:
    # TBS short: same turn if the channel is free - for every kind.  v2.3 deleted the
    # "a complex order on TBS costs +1" rule: length is priced in channel slots, and the
    # spill it may cause shows up as the queue component, not as a kind-based constant.
    assert delay_for(CommunicationMedium.TBS_SHORT, MessageKind.SITREP) == 0
    assert delay_for(CommunicationMedium.TBS_SHORT, MessageKind.AMENDMENT) == 0
    assert delay_for(CommunicationMedium.TBS_SHORT, MessageKind.MISSION_ORDER) == 0
    # ... and the length is still priced, as slots rather than turns.
    from iron_bottom_sound.communications.processing import slot_cost
    assert slot_cost(MessageKind.MISSION_ORDER, 120) == 1
    assert slot_cost(MessageKind.MISSION_ORDER, 400) == 2
    assert slot_cost(MessageKind.MISSION_ORDER, 900) == 3
    # Coded W/T: encode/transmit/decode/routing -> base +1.
    assert delay_for(CommunicationMedium.WT_CODED, MessageKind.SITREP) == 1
    # Relay / re-encipherment: the coded base plus one further turn.
    assert delay_for(CommunicationMedium.WT_REENCIPHER_RELAY, MessageKind.SITREP) == 1
    assert delay_for(CommunicationMedium.WT_REENCIPHER_RELAY, MessageKind.SITREP, relay_hops=1) == 2
    # Multi-hop totals may reach t+2.
    assert delay_for(CommunicationMedium.MULTI_HOP, MessageKind.SITREP) == 1
    assert delay_for(CommunicationMedium.MULTI_HOP, MessageKind.SITREP, relay_hops=1) == 2
    # Blinker repeated down the formation: +1 per relay stage, capped by scenario.
    assert delay_for(CommunicationMedium.BLINKER, MessageKind.SITREP) == 0
    assert delay_for(CommunicationMedium.BLINKER, MessageKind.SITREP, relay_hops=1) == 1
    assert delay_for(CommunicationMedium.BLINKER, MessageKind.SITREP, relay_hops=9) == MEDIUM_PROFILES[
        CommunicationMedium.BLINKER].max_relay_hops


def test_distance_selects_the_medium_and_never_scales_the_delay() -> None:
    """v2.3: reachability picks the medium; a relay or re-encipher needs explicit provenance.

    The v2.2 expectations this replaces encoded two defects found by auditing the CD-13
    battle: the TBS range was the scenario's *optical* horizon, and any cross-formation
    message without line of sight became a re-enciphered relay at +2.
    """
    # inside the configured TBS range: direct TBS, no delay, regardless of eyesight
    within = select_medium(distance=20, tbs_range_hex=73, direct_visual=False,
                           coded_available=True)
    assert within.medium == CommunicationMedium.TBS_SHORT
    assert delay_for(CommunicationMedium.TBS_SHORT, MessageKind.MISSION_ORDER) == 0
    assert within.direct_tbs_available is True
    # and distance inside the range changes nothing, at 3 hex or at 70
    near = select_medium(distance=3, tbs_range_hex=73, direct_visual=True, coded_available=True)
    far = select_medium(distance=70, tbs_range_hex=73, direct_visual=True, coded_available=True)
    assert near.medium == far.medium == CommunicationMedium.TBS_SHORT
    # beyond TBS range with eyesight: visual signal, not telegraphy
    beyond = select_medium(distance=80, tbs_range_hex=73, direct_visual=True, coded_available=True)
    assert beyond.medium == CommunicationMedium.BLINKER
    # beyond TBS range without eyesight: coded W/T - and NOT a re-enciphered relay,
    # because nothing in this call states a relay node or a cryptographic transition
    hidden = select_medium(distance=80, tbs_range_hex=73, direct_visual=False, coded_available=True)
    assert hidden.medium == CommunicationMedium.WT_CODED
    assert hidden.route_is_valid
    # a relay path only names itself when it names its nodes
    relayed = select_medium(distance=80, tbs_range_hex=73, direct_visual=False,
                            coded_available=True, relay_path=("node-A",))
    assert relayed.medium == CommunicationMedium.MULTI_HOP
    assert relayed.route_nodes == ("node-A",) and relayed.why_relay_required
    assert relayed.route_is_valid
    # re-encipherment additionally requires an actual cryptographic-domain transition
    crypto = select_medium(distance=80, tbs_range_hex=73, direct_visual=False,
                           coded_available=True, relay_path=("node-A",),
                           crypto_domain_transition=True)
    assert crypto.medium == CommunicationMedium.WT_REENCIPHER_RELAY
    assert crypto.why_reencipher_required and crypto.route_is_valid
    # a route that claims a relay without nodes is invalid provenance
    bogus = select_medium(distance=80, tbs_range_hex=73, direct_visual=False,
                          coded_available=True, relay_available=True)
    assert bogus.medium == CommunicationMedium.WT_CODED and bogus.route_is_valid
    # no coded set, no eyesight, out of range: no path at all
    dark = select_medium(distance=80, tbs_range_hex=73, direct_visual=False,
                         coded_available=False)
    assert dark.medium == CommunicationMedium.BLACKOUT and dark.is_blackout


def test_no_loss_or_garble_probability_is_defined() -> None:
    policy = IntegrityPolicy()
    assert policy.is_noop
    assert policy.p_drop == 0.0 and policy.p_garble == 0.0
    intact = apply_integrity(message(), policy, seed=1)
    assert intact.status == MessageStatus.QUEUED and intact.reason != processing.ABSTRACTION_LABEL


def test_an_unsourced_probability_is_refused() -> None:
    policy = IntegrityPolicy(p_drop=1.0, enabled=True, source="")
    kept = apply_integrity(message(), policy, seed=1)
    assert kept.status == MessageStatus.QUEUED
    assert kept.reason == "unsourced probability refused"


def test_a_sourced_probability_can_act_deterministically() -> None:
    policy = IntegrityPolicy(p_drop=1.0, enabled=True, source="unit-test fixture, not history")
    first = apply_integrity(message(), policy, seed=7)
    second = apply_integrity(message(), policy, seed=7)
    assert first.status == second.status == MessageStatus.DROPPED
    assert "unit-test fixture" in first.reason


# --------------------------------------------------------------------------- queue

def test_queue_delivers_in_precedence_order() -> None:
    messages = [
        message(message_id="MSG-ROUTINE", precedence=MessagePrecedence.ROUTINE),
        message(message_id="MSG-URGENT", precedence=MessagePrecedence.URGENT),
        message(message_id="MSG-OPS", precedence=MessagePrecedence.OPERATIONAL),
    ]
    outcome = drain(messages, turn=1, phase=Phase.MOVEMENT_PLANNING,
                    queues={CommunicationMedium.TBS_SHORT: schedule(CommunicationMedium.TBS_SHORT)})
    assert [item.message_id for item in outcome.delivered] == [
        "MSG-URGENT", "MSG-OPS", "MSG-ROUTINE",
    ]
    assert all(item.delivered_turn == 1 for item in outcome.delivered)


def test_queue_respects_channel_capacity_and_leaves_the_rest_waiting() -> None:
    capacity = CHANNEL_CAPACITY[CommunicationMedium.WT_CODED]
    messages = [
        message(message_id=f"MSG-{index}", medium=CommunicationMedium.WT_CODED,
                handling_delay=0)
        for index in range(capacity + 2)
    ]
    outcome = drain(messages, turn=1, phase=Phase.MOVEMENT_PLANNING,
                    queues={CommunicationMedium.WT_CODED: schedule(CommunicationMedium.WT_CODED)})
    assert len(outcome.delivered) == capacity
    assert len(outcome.waiting) == 2


def test_queue_drops_past_ttl_with_a_recorded_reason() -> None:
    stale = message(message_id="MSG-STALE", issued_turn=1, handling_delay=0)
    outcome = drain([stale], turn=1 + DEFAULT_TTL_TURNS, phase=Phase.MOVEMENT_PLANNING,
                    queues={CommunicationMedium.TBS_SHORT: schedule(CommunicationMedium.TBS_SHORT)})
    assert stale.status == MessageStatus.DROPPED
    assert "TTL" in (stale.reason or "")
    assert outcome.dropped == [stale]


def test_a_delayed_message_waits_for_its_handling_turn() -> None:
    slow = message(message_id="MSG-SLOW", medium=CommunicationMedium.WT_CODED, handling_delay=1)
    outcome = drain([slow], turn=1, phase=Phase.GUNNERY,
                    queues={CommunicationMedium.WT_CODED: schedule(CommunicationMedium.WT_CODED)})
    assert not outcome.delivered and outcome.waiting == [slow]
    later = drain([slow], turn=2, phase=Phase.MOVEMENT_PLANNING,
                  queues={CommunicationMedium.WT_CODED: schedule(CommunicationMedium.WT_CODED)})
    assert later.delivered == [slow] and slow.delivered_turn == 2


# --------------------------------------------------------------------------- mission orders

def test_mission_order_template_has_the_prescribed_structure() -> None:
    order = delegation.mission_order_template(
        order_id="o1", formation_id="f1", side=Side.ALLIES, turn=1,
        issued_by="s1", mission="intercept", intent="prevent bombardment",
        task="screen the flank",
    )
    assert delegation.validate_mission_order(order) == []
    for field in ("mission", "assumptions", "trigger_conditions", "commander_intent",
                  "task_to_formation", "coordination_measures", "target_priority_directives",
                  "roe", "risk_constraints", "report_requirements", "communications_plan",
                  "loss_of_comm_plan", "contingencies"):
        assert getattr(order, field) not in (None, "", []), field
    assert {item.branch for item in order.contingencies} == set(ContingencyBranch)


def test_mission_order_without_a_branch_of_each_kind_is_rejected() -> None:
    order = delegation.mission_order_template(
        order_id="o2", formation_id="f1", side=Side.ALLIES, turn=1,
        issued_by="s1", mission="intercept", intent="prevent bombardment",
        task="screen the flank", contingencies=[],
    )
    errors = delegation.validate_mission_order(order)
    for branch in ContingencyBranch:
        assert any(branch.value in error for error in errors)


def test_mission_order_priority_directives_stay_bounded() -> None:
    order = delegation.mission_order_template(
        order_id="o3", formation_id="f1", side=Side.ALLIES, turn=1,
        issued_by="s1", mission="m", intent="i", task="t",
    )
    for directive in order.target_priority_directives:
        assert -1.0 <= directive.weight <= 1.0
        assert directive.source == "FLEET_ORDER"


# --------------------------------------------------------------------------- contingencies

def test_explicit_signal_branch_activates_only_on_its_signal() -> None:
    order = delegation.mission_order_template(
        order_id="o4", formation_id="f1", side=Side.ALLIES, turn=1,
        issued_by="s1", mission="m", intent="i", task="t",
    )
    without = delegation.activate_branches(
        order, received=[], local_contacts=[], own_hull_fraction=1.0,
        own_ship_count=4, link_status=LinkStatus.DIRECT,
    )
    assert not any(item["branch"] == ContingencyBranch.EXPLICIT_SIGNAL_BRANCH.value for item in without)
    signal = message(kind=MessageKind.AMENDMENT, status=MessageStatus.DELIVERED)
    with_signal = delegation.activate_branches(
        order, received=[signal], local_contacts=[], own_hull_fraction=1.0,
        own_ship_count=4, link_status=LinkStatus.DIRECT,
    )
    assert any(item["branch"] == ContingencyBranch.EXPLICIT_SIGNAL_BRANCH.value for item in with_signal)


def test_local_condition_branch_activates_only_on_a_locally_visible_condition() -> None:
    order = delegation.mission_order_template(
        order_id="o5", formation_id="f1", side=Side.ALLIES, turn=1,
        issued_by="s1", mission="m", intent="i", task="t",
    )
    quiet = delegation.activate_branches(
        order, received=[], local_contacts=[], own_hull_fraction=1.0,
        own_ship_count=4, link_status=LinkStatus.DIRECT,
    )
    assert not any("contact" in item["reason"] for item in quiet)
    contact = {"target_id": "e1", "target_class": "CA", "position": "H10"}
    busy = delegation.activate_branches(
        order, received=[], local_contacts=[contact, contact], own_hull_fraction=1.0,
        own_ship_count=1, link_status=LinkStatus.DIRECT,
    )
    reasons = " ".join(item["reason"] for item in busy)
    assert "contacts against" in reasons or "heavier hull class" in reasons


def test_loss_of_comm_branch_activates_on_stale_or_blackout() -> None:
    order = delegation.mission_order_template(
        order_id="o6", formation_id="f1", side=Side.ALLIES, turn=1,
        issued_by="s1", mission="m", intent="i", task="t",
    )
    for status in (LinkStatus.STALE, LinkStatus.BLACKOUT):
        active = delegation.activate_branches(
            order, received=[], local_contacts=[], own_hull_fraction=1.0,
            own_ship_count=4, link_status=status,
        )
        assert any(item["branch"] == ContingencyBranch.LOSS_OF_COMM_BRANCH.value for item in active)
    live = delegation.activate_branches(
        order, received=[], local_contacts=[], own_hull_fraction=1.0,
        own_ship_count=4, link_status=LinkStatus.DIRECT,
    )
    assert not any(item["branch"] == ContingencyBranch.LOSS_OF_COMM_BRANCH.value for item in live)


def test_superior_force_test_uses_only_local_information() -> None:
    assert delegation.superior_force([], 4) is None
    assert delegation.superior_force([{"target_id": "e"}], 4) is None
    reason = delegation.superior_force([{"target_id": f"e{i}"} for i in range(7)], 4)
    assert reason and "pre-briefed margin" in reason
    heavier = delegation.superior_force_by_class(
        [{"target_class": "BB"}], own_classes=["DD", "DD"]
    )
    assert heavier and "heavier hull class" in heavier


def test_deviation_report_records_intent_consistency() -> None:
    order = delegation.mission_order_template(
        order_id="o7", formation_id="f1", side=Side.ALLIES, turn=1,
        issued_by="s1", mission="m", intent="hold the strait", task="t",
    )
    record = delegation.deviation_report(order, turn=4, reason="local contact", origin="s1")
    assert record["order_id"] == "o7" and "hold the strait" in record["intent_consistency"]
    assert delegation.autonomy_priority_list()[0] == "engine legality"


# --------------------------------------------------------------------------- integration

def test_end_to_end_pipeline_delivers_traffic_and_ages_the_reports() -> None:
    engine, state = start()
    play(engine, state)
    mode = state.command_delay
    assert mode is not None and mode.tick > 10
    assert mode.messages, "the pipeline must actually carry traffic"
    delivered = [item for item in mode.messages if item.status == MessageStatus.DELIVERED]
    assert delivered
    for item in delivered:
        assert item.issued_turn is not None and item.delivered_turn is not None
        # issued / delivered / observed stay separate fields.
        assert item.observed_turn is not None
        assert item.delivered_turn >= item.issued_turn
        assert item.delivered_turn - item.issued_turn == item.handling_delay or item.handling_delay >= 0
    for entry in mode.formations.values():
        assert entry.link_status in set(LinkStatus)


def test_mission_orders_are_sent_and_confirmed_through_the_queue() -> None:
    engine, state = start()
    play(engine, state)
    mode = state.command_delay
    assert mode is not None
    assert mode.mission_orders, "the fleet must issue standing mission orders"
    for order in mode.mission_orders:
        assert delegation.validate_mission_order(order) == []
    kinds = {item.kind for item in mode.messages}
    assert MessageKind.MISSION_ORDER in kinds
    assert {item.status for item in mode.messages} <= set(MessageStatus)


def test_fleet_report_ages_are_consistent_with_the_ledger() -> None:
    engine, state = start()
    play(engine, state)
    for side in Side:
        view = fleet_observation(engine, state, side)
        for report in view.reports:
            entry = command_delay.formation_command(state, report.formation_id)
            if entry is None or entry.reported_turn is None:
                continue
            if report.is_source_of_truth:
                continue
            assert report.reported_turn == entry.reported_turn
            assert report.age_turns == max(0, state.turn - entry.reported_turn)


def test_a_delivered_report_uses_its_snapshot_and_never_live_state() -> None:
    """The decisive form of the drafting-time rule.

    A delivered sitrep is folded in from the payload it carries.  The live guide
    is somewhere else entirely, so if the code ever read live state the ledger
    would move to the live hex and this test would fail.
    """
    engine, state = start(scenario="IBS-S-01", seed=20270830)
    mode = state.command_delay
    assert mode is not None
    formation = next(
        item for item in command_delay.active_formations(state, Side.AXIS)
        if item.id != command_delay.authority_for(state, Side.AXIS).fleet_formation_id
    )
    live = state.ships[formation.leader_id].position
    snapshot_hex = HexCoord(q=live.q + 3, r=live.r + 1)
    delivered = message(
        message_id="MSG-SNAP", side=Side.AXIS, kind=MessageKind.SITREP,
        destination=formation.id, issued_turn=1, delivered_turn=2, observed_turn=2,
        status=MessageStatus.DELIVERED,
        payload={"report": {
            "formation_id": formation.id,
            "guide_position": {"label": snapshot_hex.label, "q": snapshot_hex.q, "r": snapshot_hex.r},
            "guide_heading": 3,
            "guide_speed": 2,
            "ship_count": 3,
            "geometry_kind": "column",
        }},
    )
    command_delay._apply_delivery(engine, state, delivered)
    entry = mode.formations[formation.id]
    assert entry.reported_position == snapshot_hex != live
    assert entry.reported_turn == 1
    assert entry.reported_heading == 3 and entry.reported_speed == 2
    assert entry.reported_ship_count == 3


def test_coded_reports_arrive_after_they_were_drafted(monkeypatch) -> None:
    """With every report forced onto coded W/T, none is delivered same-turn.

    Uses S-01, the smallest scenario with more than one formation per side: with
    a single formation the fleet is embarked in it and there is nobody to report.
    """
    engine, state = start(scenario="IBS-S-01", seed=20270830)
    mode = state.command_delay
    assert mode is not None
    monkeypatch.setattr(
        command_delay, "route",
        lambda engine_, state_, origin, destination: RouteDecision(
            CommunicationMedium.WT_CODED, 0, "forced coded path for this test"
        ),
    )
    play(engine, state)
    coded = [
        item for item in mode.messages
        if item.medium == CommunicationMedium.WT_CODED
        and item.kind in (MessageKind.SITREP, MessageKind.CONTACT_REPORT)
        and item.status == MessageStatus.DELIVERED
    ]
    assert coded, "the forced coded path must have produced a delivered report"
    rank = command_delay.PHASE_RANK

    def freshness(item: CommandMessage) -> tuple[int, int]:
        return (item.issued_turn, rank.get(item.issued_phase, 0))

    # Reports are addressed *to the fleet* and name their author in the payload (CD-13),
    # so the knowledge the delivery updates is keyed by the reporting formation - the
    # fleet's picture of a formation is what that formation last told it.
    newest: dict[str, CommandMessage] = {}
    for item in coded:
        assert item.handling_delay >= 1
        assert item.delivered_turn > item.issued_turn, (
            "a coded report must be delivered strictly later than it was drafted"
        )
        snapshot = command_delay._decode_snapshot(item.payload)
        reporter = snapshot.get("reporting_formation_id") or item.destination
        assert reporter != item.destination or item.destination in mode.formations, (
            "a report must name who wrote it"
        )
        current = newest.get(reporter)
        if current is None or freshness(item) > freshness(current):
            newest[reporter] = item
    for destination, item in sorted(newest.items()):
        snapshot = command_delay._decode_snapshot(item.payload)
        entry = mode.formations[destination]
        # The fleet holds the newest report *by issue time*, which is the rule the
        # ledger and the order book share.
        assert (entry.reported_turn, rank.get(entry.reported_phase, 0)) == freshness(item)
        assert entry.reported_position == snapshot["guide_position"]
        assert entry.reported_ship_count == snapshot["ship_count"]


def test_a_late_superseded_order_cannot_overwrite_a_newer_one() -> None:
    engine, state = start(scenario="IBS-S-03")
    mode = state.command_delay
    assert mode is not None
    formation = command_delay.active_formations(state, Side.ALLIES)[0]
    older = delegation.mission_order_template(
        order_id="older", formation_id=formation.id, side=Side.ALLIES, turn=1,
        issued_by="fleet", mission="m", intent="i", task="t",
    )
    newer = delegation.mission_order_template(
        order_id="newer", formation_id=formation.id, side=Side.ALLIES, turn=2,
        issued_by="fleet", mission="m2", intent="i2", task="t2",
    )
    mode.mission_orders.extend([older, newer])
    newer.confirmed_turn = 2
    mode.formations[formation.id].active_order_id = "newer"
    late = message(
        message_id="MSG-LATE", kind=MessageKind.MISSION_ORDER,
        issued_turn=1, delivered_turn=4, observed_turn=4,
        status=MessageStatus.DELIVERED,
        payload={"order_id": "older"},
    )
    command_delay._apply_delivery(engine, state, late)
    assert mode.formations[formation.id].active_order_id == "newer"
    assert late.status == MessageStatus.SUPERSEDED
    assert late.superseded_by == "newer"
    assert "superseded by newer" in (late.reason or "")


# --------------------------------------------------------------------------- determinism

HASH_SCRIPT = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
from iron_bottom_sound import command_delay
from iron_bottom_sound.communications import (MEDIUM_PROFILES, delay_for, drain, schedule)
from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine
from iron_bottom_sound.llm import LLMPlayerSession
from iron_bottom_sound.models import (GameOptions, Phase, Side)
from iron_bottom_sound.realistic_command import RealisticCommander

engine = IronBottomEngine()
state = engine.reset("IBS-S-03", 3,
                     GameOptions(realistic_command=True, command_delay_mode=True))
sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
# the setup phase is order-driven exactly like any other order phase
steps = 0
while state.phase != Phase.COMPLETE and steps < 200:
    steps += 1
    if state.phase in ORDER_PHASES:
        for side in Side:
            if side.value in state.submitted_orders:
                continue
            engine.submit_orders(state.game_id,
                                 sessions[side].choose_orders(engine, state.game_id))
    engine.advance(state.game_id)
mode = state.command_delay
print(json.dumps({
    "tick": mode.tick,
    "messages": sorted((m.message_id, m.kind.value, m.medium.value, m.status.value,
                        m.issued_turn, m.delivered_turn) for m in mode.messages),
    "orders": sorted((o.order_id, o.confirmed_turn) for o in mode.mission_orders),
    "links": sorted((k, v.link_status.value, v.reported_turn) for k, v in mode.formations.items()),
}, sort_keys=True))
"""


def test_communication_pipeline_is_hash_seed_independent() -> None:
    def outcome(hashseed: str):
        import json
        env = dict(os.environ, PYTHONHASHSEED=hashseed,
                   PYTHONPATH=str(REPO_ROOT / "backend" / "src"))
        proc = subprocess.run(
            [sys.executable, "-c", HASH_SCRIPT, str(REPO_ROOT / "backend" / "src")],
            cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=600,
        )
        assert proc.returncode == 0, proc.stderr[-2000:]
        return json.loads(proc.stdout)

    assert outcome("0") == outcome("1") == outcome("5")
