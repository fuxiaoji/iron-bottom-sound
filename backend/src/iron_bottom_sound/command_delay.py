"""Command Delay mode shell (CD-2): mode isolation, authority state, per-turn tick.

Mode isolation
--------------
``GameOptions.command_delay_mode`` is a *new* flag.  ``realistic_command`` keeps
its original meaning, and the three player-visible entries are

======================  ================  ===================
entry                   realistic_command command_delay_mode
======================  ================  ===================
Classic                 False             False
Realistic               True              False
Command Delay           True              True
======================  ================  ===================

``command_delay_mode`` requires the Realistic formation core and *never* alters
Realistic's own communication or observation semantics: the flag is checked
before any branching, so a Realistic game has ``state.command_delay is None`` and
follows the frozen path exactly.

What the shell owns at this stage
---------------------------------
* authority state (who governs execution: fleet, delegated formation, or local
  autonomy under loss of communication);
* the fleet view and the formation-local view (``command_observation``), with
  the fleet's knowledge of a remote formation stored as a *report*, never read
  from the live formation;
* the per-phase tick that refreshes those reports and the link status.

CD-3 adds the deterministic communication pipeline (TBS / blinker / coded W/T /
relay, precedence, queue, TTL) and makes the reports genuinely delayed.  Until
then the tick records a current-turn report, which is what "no communication
noise yet" means: the *plumbing* is in place and is the only writer.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from . import communications, delegation
from .communications import (
    ChannelQueue,
    CommandMessage,  # noqa: F401  (re-exported for callers of this module)
    CommunicationMedium,
    MessageKind,
    MessagePrecedence,
    RouteDecision,
    delay_for,
    drain,
    schedule,
    select_medium,
)
from .models import (
    AuthorityLevel,
    CommandAuthority,
    CommandDelayState,
    FormationCommandState,
    FormationGeometryKind,
    FormationMovementOrder,
    FormationState,
    GameOptions,
    GameState,
    HexCoord,
    LinkStatus,
    MessageStatus,
    MissionOrder,
    OrderBatch,
    Phase,
    Side,
    TargetPriorityDirective,
)
from .communications.queue import PHASE_RANK
from .realistic_command import MAX_FORMATIONS_PER_SIDE, SUPPORTED_SCENARIOS

if TYPE_CHECKING:
    from .engine import IronBottomEngine

RULE_AUTHORITY = "IBS-R-CD-02"
RULE_COMMS = "IBS-R-CD-03"

# Model policies live in process memory, keyed by side, never in the game state.
_SIDE_POLICIES: dict[str, tuple[Any, str]] = {}


def enabled(state: GameState) -> bool:
    """True only for the Command Delay mode (never for Classic or Realistic)."""
    return bool(state.options.command_delay_mode)


def validate_mode_options(options: GameOptions, scenario_id: str) -> None:
    """Fail closed on an inconsistent mode request.

    ``command_delay_mode`` is not silently coerced into ``realistic_command``:
    the two switches have distinct meanings and the UI presents them as three
    exclusive entries, so an inconsistent combination is a caller error.
    """
    if not options.command_delay_mode:
        return
    if not options.realistic_command:
        raise ValueError(
            "Command Delay requires the realistic command formation core; "
            "set realistic_command=True together with command_delay_mode=True"
        )
    if scenario_id not in SUPPORTED_SCENARIOS:
        raise ValueError(f"Command Delay is not available for scenario {scenario_id}")


def state_for(state: GameState) -> CommandDelayState:
    """Return the mode state, creating the empty shell on first use."""
    if state.command_delay is None:
        state.command_delay = CommandDelayState()
    return state.command_delay


def active_formations(state: GameState, side: Side) -> list[FormationState]:
    """Formations of one side that still have attached, positioned ships."""
    active = []
    for formation in state.formations.values():
        if formation.side != side or formation.status == "dissolved":
            continue
        if any(
            state.ships[ship_id].position is not None
            and not state.ships[ship_id].sunk
            and state.ships[ship_id].command_status == "attached"
            for ship_id in formation.ship_ids
            if ship_id in state.ships
        ):
            active.append(formation)
    return sorted(active, key=lambda item: item.id)


def fleet_formation_id(state: GameState, side: Side) -> str | None:
    """The formation the fleet commander sails with.

    Deterministic rule, stated so it can be audited and reproduced: the active
    formation with the most ships; ties break on the lowest formation id.  The
    fleet commander is not omniscient — being embarked is what makes this one
    formation's state directly knowable, and every other formation is known only
    through its reports.
    """
    candidates = active_formations(state, side)
    if not candidates:
        return None
    ranked = sorted(
        candidates,
        key=lambda formation: (
            -sum(1 for ship_id in formation.ship_ids if ship_id in state.ships),
            formation.id,
        ),
    )
    return ranked[0].id


def initialise(engine: "IronBottomEngine", state: GameState) -> None:
    """Build the authority table.  Idempotent; only writes for Command Delay."""
    if not enabled(state):
        return
    mode = state_for(state)
    for side in Side:
        fleet_id = fleet_formation_id(state, side)
        flagship = state.ships.get(state.formations[fleet_id].flagship_id) if fleet_id else None
        mode.authorities[side.value] = CommandAuthority(
            side=side,
            level=AuthorityLevel.FLEET_DIRECTED,
            fleet_commander_ship_id=flagship.id if flagship else None,
            fleet_formation_id=fleet_id,
        )
        for formation in active_formations(state, side):
            embarked = formation.id == fleet_id
            mode.formations[formation.id] = FormationCommandState(
                formation_id=formation.id,
                commander_ship_id=formation.flagship_id,
                authority=(
                    AuthorityLevel.FLEET_DIRECTED if embarked else AuthorityLevel.DELEGATED
                ),
                link_status=LinkStatus.DIRECT,
                reported_turn=state.turn,
                active_order_id=None,
            )
            _write_report(state, formation)
    # Emitted once per side with ``secret_side`` set.  The authority table names
    # each side's fleet formation and fleet commander; an unfiltered event would
    # hand the opponent's whole command chain to the other player, which the
    # leakage audit checks for directly.
    for side in Side:
        engine._event(
            state, "command_delay_initialised",
            "命令延迟模式：建立舰队—编队指挥链与权限表",
            payload={
                "secret_side": side.value,
                "tick": mode.tick,
                **link_summary(state, side),
            },
            rule=engine._rule(RULE_AUTHORITY, None, "命令延迟：权限状态"),
        )


def _write_report(state: GameState, formation: FormationState) -> FormationCommandState:
    """Refresh the *reported* summary of one formation.

    Only the communication layer (CD-3) and this report writer may fill these
    fields, and only with what a signal could carry: a guide position, heading,
    speed, ship count and declared geometry.  Exact per-ship detail never leaves
    the formation.
    """
    mode = state_for(state)
    entry = mode.formations.get(formation.id)
    if entry is None:
        entry = FormationCommandState(formation_id=formation.id)
        mode.formations[formation.id] = entry
    snapshot = report_snapshot(state, formation)
    entry.reported_turn = state.turn
    entry.last_report_turn = state.turn
    entry.reported_position = snapshot["guide_position"]
    entry.reported_heading = snapshot["guide_heading"]
    entry.reported_speed = snapshot["guide_speed"]
    entry.reported_ship_count = snapshot["ship_count"]
    entry.reported_geometry_kind = snapshot["geometry_kind"]
    entry.commander_ship_id = formation.flagship_id
    return entry


def report_snapshot(state: GameState, formation: FormationState) -> dict[str, Any]:
    """The exact content a sitrep may carry — taken at *drafting* time.

    A delayed report must describe the world as it was when it was written, so
    the snapshot is captured here and travels inside the message payload; the
    fleet's copy is never refreshed from live state on delivery.
    """
    members = [
        state.ships[ship_id] for ship_id in formation.ship_ids
        if ship_id in state.ships
        and state.ships[ship_id].position is not None
        and not state.ships[ship_id].sunk
        and state.ships[ship_id].command_status == "attached"
    ]
    guide = state.ships.get(formation.leader_id)
    if guide is None or guide.position is None or guide.sunk:
        guide = members[0] if members else None
    return {
        "formation_id": formation.id,
        "guide_position": guide.position if guide is not None else None,
        "guide_heading": guide.heading if guide is not None else None,
        "guide_speed": guide.current_speed if guide is not None else None,
        "ship_count": len(members),
        "geometry_kind": formation.geometry_kind,
        "hull_fraction": round(delegation.own_hull_fraction(state, formation), 3),
        "contacts": 0,
    }


def refresh_link_status(state: GameState) -> None:
    """Derive each formation's link status from the delivered traffic ledger.

    The status is a function of how old the fleet's newest *delivered* report
    from that formation is, so it can only improve by actually receiving
    traffic:

    ``DIRECT``    a report delivered this turn;
    ``RELAYED``   the newest report is one turn old (it needed a relay stage);
    ``STALE``     two or more turns old;
    ``BLACKOUT``  nothing has ever been delivered.
    """
    mode = state_for(state)
    for formation_id in sorted(mode.formations):
        entry = mode.formations[formation_id]
        formation = state.formations.get(formation_id)
        if formation is None or formation.status == "dissolved":
            # The command entity is gone -- no ships left to be in touch with.  The
            # last authority is kept as history; live formations are the ones the
            # DIRECT / RELAYED / STALE / LOCAL_AUTONOMY rules below describe.
            entry.link_status = LinkStatus.BLACKOUT
            continue
        authority = mode.authorities.get(formation.side.value)
        embarked = authority is not None and authority.fleet_formation_id == formation_id
        if embarked:
            # The fleet commander is embarked in this formation: the command link
            # is physical, needs no traffic, and cannot go stale.  Deriving it from
            # sitrep age (there is no sitrep to itself) would have shown a link
            # degrading in the very formation the admiral is standing on.
            entry.link_status = LinkStatus.DIRECT
            entry.authority = AuthorityLevel.FLEET_DIRECTED
            continue
        age = (
            None if entry.reported_turn is None
            else max(0, state.turn - entry.reported_turn)
        )
        if age is None:
            entry.link_status = LinkStatus.BLACKOUT
        elif age == 0:
            entry.link_status = LinkStatus.DIRECT
        elif age == 1:
            entry.link_status = LinkStatus.RELAYED
        else:
            entry.link_status = LinkStatus.STALE
        base = AuthorityLevel.DELEGATED
        if not embarked and entry.link_status in (LinkStatus.STALE, LinkStatus.BLACKOUT):
            # The link has failed, so the formation is on its pre-briefed plan and
            # runs on local autonomy.  STALE counts, not just BLACKOUT: the
            # contingency evaluator already treats "stale or blacked out" as loss
            # of communication (LOSS_OF_COMM_BRANCH), and a label reading
            # DELEGATED while the agent is demonstrably executing the loss-of-comm
            # plan would contradict the mode's own rule.  BLACKOUT alone was
            # reachable only before a formation's first report ever arrived, so the
            # label was in practice almost never set.
            base = AuthorityLevel.LOCAL_AUTONOMY
        entry.authority = base


# --------------------------------------------------------------------------- messages

def _queues(state: GameState) -> dict[CommunicationMedium, ChannelQueue]:
    """Fresh per-turn channel slots, one queue per medium."""
    return {medium: schedule(medium) for medium in CommunicationMedium}


def send(
    engine: "IronBottomEngine", state: GameState, message: CommandMessage,
) -> CommandMessage:
    """Route one drafted message and place it in the queue.

    Routing picks the medium from the link picture (distance and line of sight);
    the handling delay then comes from the medium profile.  Nothing here invents
    a probability: a message is delivered when its turn budget and a channel slot
    are both available, or dropped when its TTL expires.
    """
    mode = state_for(state)
    message.message_id = message.message_id or f"MSG-{mode.next_sequence:05d}"
    mode.next_sequence += 1
    mode.messages.append(message)
    engine._event(
        state, "command_message_queued",
        f"{message.medium.value} 报文 {message.message_id}（{message.kind.value}）已发出",
        payload={
            "secret_side": message.side.value,
            "message_id": message.message_id,
            "kind": message.kind.value,
            "precedence": message.precedence.value,
            "medium": message.medium.value,
            "origin": message.origin,
            "destination": message.destination,
            "handling_delay": message.handling_delay,
            "relay_hops": message.relay_hops,
            "issued_turn": message.issued_turn,
            "issued_phase": message.issued_phase.value,
        },
        rule=engine._rule(RULE_COMMS, None, "命令延迟：通信处理链"),
    )
    return message


def route(
    engine: "IronBottomEngine", state: GameState, origin: FormationState, destination: FormationState,
) -> RouteDecision:
    """Select a medium between two formations from the scenario's own horizon.

    The direct-signal horizon reuses the scenario's optical visibility rather
    than inventing a second range constant: the scenario already declares how far
    its lookouts see, and a direct tactical circuit is bounded by the same
    horizon.  Line of sight between guides is the engine's own visibility rule.
    """
    origin_guide = state.ships.get(origin.leader_id)
    destination_guide = state.ships.get(destination.leader_id)
    if (
        origin_guide is None or destination_guide is None
        or origin_guide.position is None or destination_guide.position is None
    ):
        return RouteDecision(CommunicationMedium.BLACKOUT, 0, "a formation has no guide afloat")
    distance = origin_guide.position.distance(destination_guide.position)
    line_of_sight = engine._can_see(state, destination_guide, origin_guide)
    same_command = origin.id == destination.id
    return select_medium(
        distance=distance,
        tactical_range=int(state.visibility[origin.side.value]),
        line_of_sight=line_of_sight,
        coded_available=True,
        relay_available=not same_command,
    )


def draft_reports(
    engine: "IronBottomEngine", state: GameState,
) -> list[CommandMessage]:
    """Every active formation drafts its own sitrep for the fleet.

    Drafted once per phase boundary; the snapshot inside the payload is the
    world at drafting time.  A formation with local contacts drafts a contact
    report at urgent precedence instead, which is why precedence matters to the
    queue.
    """
    mode = state_for(state)
    drafted: list[CommandMessage] = []
    for side in Side:
        authority = mode.authorities.get(side.value)
        fleet_id = authority.fleet_formation_id if authority else None
        fleet_formation = state.formations.get(fleet_id) if fleet_id else None
        if fleet_formation is None:
            continue
        for formation in active_formations(state, side):
            if formation.id == fleet_id:
                continue  # the commander is embarked; no report is needed
            decision = route(engine, state, formation, fleet_formation)
            snapshot = report_snapshot(state, formation)
            contacts = _formation_contact_count(engine, state, formation)
            snapshot["contacts"] = contacts
            kind = MessageKind.CONTACT_REPORT if contacts else MessageKind.SITREP
            precedence = (
                MessagePrecedence.URGENT if contacts else MessagePrecedence.ROUTINE
            )
            drafted.append(send(engine, state, CommandMessage(
                message_id="",
                side=side,
                origin=formation.flagship_id,
                destination=formation.id,
                kind=kind,
                precedence=precedence,
                medium=decision.medium,
                issued_turn=state.turn,
                issued_phase=state.phase,
                handling_delay=delay_for(
                    decision.medium, kind, decision.relay_hops
                ),
                relay_hops=decision.relay_hops,
                reason=decision.reason,
                payload={"report": _encode_snapshot(snapshot)},
            )))
    return drafted


def _encode_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """JSON-safe form of a report snapshot (a HexCoord becomes its label)."""
    encoded = dict(snapshot)
    position = encoded.get("guide_position")
    if position is not None:
        encoded["guide_position"] = {
            "label": position.label, "q": position.q, "r": position.r
        }
    geometry = encoded.get("geometry_kind")
    if geometry is not None:
        encoded["geometry_kind"] = geometry.value
    return encoded


def _decode_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    snapshot = dict(payload.get("report") or {})
    position = snapshot.get("guide_position")
    if isinstance(position, dict):
        snapshot["guide_position"] = HexCoord(q=position["q"], r=position["r"])
    geometry = snapshot.get("geometry_kind")
    if isinstance(geometry, str):
        snapshot["geometry_kind"] = FormationGeometryKind(geometry)
    return snapshot


def _formation_contact_count(
    engine: "IronBottomEngine", state: GameState, formation: FormationState,
) -> int:
    """Contacts this formation's own ships can see (never the side's)."""
    from .command_observation import visible_enemies

    positions = [
        state.ships[ship_id].position for ship_id in formation.ship_ids
        if ship_id in state.ships and state.ships[ship_id].position is not None
        and state.ships[ship_id].command_status == "attached"
        and not state.ships[ship_id].sunk
    ]
    if not positions:
        return 0
    return len(visible_enemies(engine, state, formation.side, positions))


def deliver_due(engine: "IronBottomEngine", state: GameState) -> dict[str, list[str]]:
    """Drain the channels for this (turn, phase) and apply every delivery."""
    mode = state_for(state)
    outcome = drain(
        mode.messages, turn=state.turn, phase=state.phase, queues=_queues(state),
    )
    applied = {"delivered": [], "waiting": [], "dropped": [], "superseded": []}
    for message in outcome.delivered:
        applied["delivered"].append(message.message_id)
        _apply_delivery(engine, state, message)
        engine._event(
            state, "command_message_delivered",
            f"报文 {message.message_id}（{message.kind.value}）送达 {message.destination}",
            payload={
                "secret_side": message.side.value,
                "message_id": message.message_id,
                "kind": message.kind.value,
                "medium": message.medium.value,
                "origin": message.origin,
                "destination": message.destination,
                "issued_turn": message.issued_turn,
                "issued_phase": message.issued_phase.value,
                "delivered_turn": message.delivered_turn,
                "delivered_phase": (
                    message.delivered_phase.value if message.delivered_phase else None
                ),
                "observed_turn": message.observed_turn,
            },
            rule=engine._rule(RULE_COMMS, None, "命令延迟：通信处理链"),
        )
    for message in outcome.waiting:
        applied["waiting"].append(message.message_id)
    for message in outcome.dropped:
        applied["dropped"].append(message.message_id)
        engine._event(
            state, "command_message_dropped",
            f"报文 {message.message_id} 因 {message.reason} 丢弃",
            payload={
                "secret_side": message.side.value,
                "message_id": message.message_id,
                "reason": message.reason,
                "issued_turn": message.issued_turn,
            },
            rule=engine._rule(RULE_COMMS, None, "命令延迟：通信拥塞"),
        )
    return applied


def _apply_delivery(
    engine: "IronBottomEngine", state: GameState, message: CommandMessage,
) -> None:
    """Fold one delivered message into the fleet's knowledge or the order book."""
    mode = state_for(state)
    if message.kind in (MessageKind.SITREP, MessageKind.CONTACT_REPORT):
        entry = mode.formations.get(message.destination)
        if entry is None:
            entry = FormationCommandState(formation_id=message.destination)
            mode.formations[message.destination] = entry
        # Flights can cross: a same-turn TBS report overtakes a coded one sent
        # earlier.  Arrival order is therefore not freshness order, and a report
        # must never overwrite knowledge that is newer *by issue time* — the same
        # rule the order book applies.  Phase rank breaks ties inside one turn,
        # because a later phase is drawn from a later world.
        if entry.reported_turn is not None and (
            message.issued_turn, PHASE_RANK.get(message.issued_phase, 0)
        ) < (
            entry.reported_turn, PHASE_RANK.get(entry.reported_phase, 0)
        ):
            message.status = MessageStatus.SUPERSEDED
            message.reason = (
                f"overtaken by a newer report already held from turn {entry.reported_turn}"
            )
            return
        snapshot = _decode_snapshot(message.payload)
        entry.reported_turn = message.issued_turn
        entry.reported_phase = message.issued_phase
        entry.last_report_turn = message.delivered_turn
        entry.reported_position = snapshot.get("guide_position")
        entry.reported_heading = snapshot.get("guide_heading")
        entry.reported_speed = snapshot.get("guide_speed")
        entry.reported_ship_count = snapshot.get("ship_count")
        entry.reported_geometry_kind = snapshot.get("geometry_kind")
        return
    if message.kind in (MessageKind.MISSION_ORDER, MessageKind.AMENDMENT):
        order_id = message.payload.get("order_id")
        order_text = message.payload.get("order_text")
        order = next(
            (item for item in mode.mission_orders if item.order_id == order_id), None
        )
        if order is None:
            return
        entry = mode.formations.get(order.formation_id)
        if entry is None:
            entry = FormationCommandState(formation_id=order.formation_id)
            mode.formations[order.formation_id] = entry
        # A late order may not overwrite a newer acknowledged one: compare issue
        # order, not arrival order, and record the refusal.
        current = next(
            (item for item in mode.mission_orders if item.order_id == entry.active_order_id),
            None,
        )
        if current is not None and current.issued_turn > order.issued_turn:
            message.status = MessageStatus.SUPERSEDED
            message.reason = (
                f"superseded by {current.order_id} issued on turn {current.issued_turn}"
            )
            message.superseded_by = current.order_id
            return
        order.confirmed_turn = message.delivered_turn
        entry.active_order_id = order.order_id
        # The formation now knows the order; record it in *its* memory so the next
        # agent call reads the words the fleet actually sent.
        from .formation_memory import set_active_order

        set_active_order(
            state, order.formation_id,
            text=str(order_text or order.mission),
            turn=int(message.delivered_turn or message.issued_turn),
            order_id=order.order_id,
        )
        return
    if message.kind == MessageKind.ACKNOWLEDGEMENT:
        return


def on_phase_advanced(engine: "IronBottomEngine", state: GameState) -> None:
    """The single per-phase hook; inert unless the mode is on.

    Called at the end of every ``engine.advance`` transition, which covers phase
    boundaries and the turn rollover in one place.  Order of operations is the
    communication pipeline itself: deliver whatever the channels are carrying,
    let every formation draft its own report, then re-derive link status from the
    delivered ledger — so a link can only improve by receiving traffic.
    """
    if not enabled(state):
        return
    mode = state_for(state)
    if not mode.formations:
        initialise(engine, state)
    mode.tick += 1
    deliver_due(engine, state)
    draft_reports(engine, state)
    if state.phase == Phase.REINFORCEMENT:
        # The fleet's staff work for the new turn: one standing mission order per
        # formation that does not already hold one.
        for side in Side:
            issue_mission_orders(engine, state, side)
    if state.phase == Phase.MOVEMENT_PLANNING:
        # Every formation's local agent decides for this turn, from its own local
        # view only.  The gunnery phase later consumes only the priority part.
        run_formation_agents(engine, state)
    refresh_link_status(state)
    _prune_messages(state)
    if state.phase == Phase.REINFORCEMENT:
        # Emitted per side with ``secret_side`` set: the authority table names
        # formations, links and commanders, and the engine filters events by
        # ``secret_side`` for observations.  A single unfiltered event would hand
        # the opponent the whole command picture.
        for side in Side:
            engine._event(
                state, "command_delay_turn_state",
                f"命令延迟模式：第 {state.turn} 回合指挥链状态",
                payload={
                    "secret_side": side.value,
                    "turn": state.turn,
                    "tick": mode.tick,
                    **link_summary(state, side),
                },
                rule=engine._rule(RULE_AUTHORITY, None, "命令延迟：权限状态"),
            )


def _prune_messages(state: GameState, keep: int = 400) -> None:
    """Bound the ledger so a long game cannot grow without limit.

    Delivered and dropped messages are the audit trail, so the most recent
    ``keep`` are retained; nothing that is still queued is ever pruned.
    """
    mode = state_for(state)
    if len(mode.messages) <= keep:
        return
    pending = [item for item in mode.messages if item.status == MessageStatus.QUEUED]
    settled = [item for item in mode.messages if item.status != MessageStatus.QUEUED]
    keep_settled = max(0, keep - len(pending))
    mode.messages = settled[-keep_settled:] + pending if keep_settled else pending


def link_summary(state: GameState, side: Side | None = None) -> dict[str, Any]:
    """Auditable digest of the authority table, for events and the fleet view.

    With ``side`` given, only that side's formations appear: the digest is used
    in payloads, and an unfiltered one would publish the opponent's order of
    battle by formation.
    """
    mode = state_for(state)
    own = {
        formation.id
        for formation in state.formations.values()
        if side is None or formation.side == side
    }
    return {
        "authorities": {
            key: {
                "level": authority.level.value,
                "fleet_formation_id": authority.fleet_formation_id,
                "fleet_commander_ship_id": authority.fleet_commander_ship_id,
            }
            for key, authority in sorted(mode.authorities.items())
            if side is None or key == side.value
        },
        "formations": {
            formation_id: {
                "authority": entry.authority.value,
                "link_status": entry.link_status.value,
                "active_order_id": entry.active_order_id,
                "reported_turn": entry.reported_turn,
                "commander_ship_id": entry.commander_ship_id,
            }
            for formation_id, entry in sorted(mode.formations.items())
            if formation_id in own
        },
    }


def draft_natural_order(
    engine: "IronBottomEngine", state: GameState, *, side: Side, formation_id: str,
    text: str, priority_classes: list[str] | None = None,
    roe: list[str] | None = None, deadline_turn: int | None = None,
) -> CommandMessage:
    """Send the fleet commander's own words to one formation.

    This is the mode's input channel: the human writes an order in natural
    language, it is drafted into a signal like any other and it is subject to the
    same routing, queue and TTL.  It can therefore arrive late, or not at all —
    which is the point.

    The directive fields are optional and stay bounded: a priority class list only
    produces FleetOrder weights, so nothing here can name a mount or a solution.
    """
    mode = state_for(state)
    authority = mode.authorities.get(side.value)
    fleet_formation = (
        state.formations.get(authority.fleet_formation_id) if authority else None
    )
    formation = state.formations.get(formation_id)
    if formation is None or formation.side is not side:
        raise ValueError(f"unknown formation {formation_id} for side {side.value}")
    cleaned = " ".join((text or "").split())
    if not cleaned:
        raise ValueError("an order needs text")
    order = delegation.mission_order_template(
        order_id=f"{side.value}-nl-{state.turn}-{formation_id}",
        formation_id=formation_id,
        side=side,
        turn=state.turn,
        issued_by=(
            authority.fleet_commander_ship_id or fleet_formation.flagship_id
            if authority and fleet_formation else "fleet"
        ),
        mission=cleaned,
        intent=cleaned,
        task=cleaned,
        priority_classes=tuple(priority_classes) if priority_classes else delegation.DEFAULT_FIRE_PRIORITY,
        roe=list(roe) if roe else None,
        deadline_turn=deadline_turn,
    )
    mode.mission_orders.append(order)
    decision = (
        route(engine, state, fleet_formation, formation)
        if fleet_formation is not None
        else RouteDecision(CommunicationMedium.BLACKOUT, 0, "no fleet formation afloat")
    )
    kind = MessageKind.MISSION_ORDER
    return send(engine, state, CommandMessage(
        message_id="",
        side=side,
        origin=order.issued_by,
        destination=formation_id,
        kind=kind,
        precedence=MessagePrecedence.OPERATIONAL,
        medium=decision.medium,
        issued_turn=state.turn,
        issued_phase=state.phase,
        handling_delay=delay_for(decision.medium, kind, decision.relay_hops),
        relay_hops=decision.relay_hops,
        reason=decision.reason,
        payload={"order_id": order.order_id, "order_text": cleaned},
    ))


def formation_orders(state: GameState, side: Side) -> list[FormationMovementOrder]:
    """Movement orders for a side, produced by its formations' own agents.

    In this mode a player is the fleet commander, not a per-ship plotter: the
    formations execute what their agents decided, and the player's lever is the
    order they were sent.  The batch still goes through the engine's validation, so
    an agent that chose an illegal plan fails loudly instead of being corrected
    silently.
    """
    own = {
        formation.id for formation in state.formations.values()
        if formation.side is side
    }
    order_by_formation: dict[str, FormationMovementOrder] = {}
    for record in state.command_delay.decisions if state.command_delay else []:
        if record.get("turn") != state.turn or record.get("formation_id") not in own:
            # 另一侧编队的代理决策属于对方的指挥链，绝不进入本侧订单。
            continue
        formation_id = record.get("formation_id")
        plan = record.get("selected_movement_plan")
        if not formation_id or not plan:
            continue
        order_by_formation[formation_id] = FormationMovementOrder(
            formation_id=formation_id, leader_plan=plan,
        )
    return [order_by_formation[key] for key in sorted(order_by_formation)]


def gunnery_batch(state: GameState, side: Side) -> OrderBatch:
    """The GUNNERY-phase batch a Command Delay commander may submit.

    Carries **only** target priority directives — the fleet's from its mission
    orders plus the local agents' bounded adjustments.  The engine's selector
    turns them into final gunnery orders in ``submit_orders``; nothing on this
    path can name a mount or a firing solution.
    """
    mode = state_for(state)
    own = {
        formation.id for formation in state.formations.values()
        if formation.side is side
    }
    directives: list[TargetPriorityDirective] = []
    for order in mode.mission_orders:
        if order.side is side and order.confirmed_turn is not None:
            directives.extend(order.target_priority_directives)
    # 本地代理的调整同样按阵营取：另一侧代理的权重绝不能影响本侧选择器。
    directives.extend(
        directive for directive in mode.local_directives
        if directive.formation_id in own
    )
    return OrderBatch(side=side, phase=state.phase, target_priorities=directives)


def set_side_policy(side: Side, policy: Any, label: str) -> None:
    """Register the model policy a side's formations run under (process memory only).

    The key itself never enters the game state, and a policy registered here is
    deliberately *not* persisted: a reloaded save falls back to the deterministic
    agent until a key is supplied again, which is the honest behaviour for a secret.
    """
    _SIDE_POLICIES[side.value] = (policy, label)


def clear_side_policies() -> None:
    _SIDE_POLICIES.clear()


def side_policy(side: Side) -> tuple[Any, str]:
    return _SIDE_POLICIES.get(side.value, (None, "deterministic-formation-v1"))


def side_agent(side: Side):
    """The agent a side's formations use: a model when available, doctrine otherwise."""
    from .formation_agents import DeterministicFormationAgent
    from .formation_llm import FormationLLMAgent

    policy, label = side_policy(side)
    if policy is None:
        return DeterministicFormationAgent(), label
    return FormationLLMAgent(policy, name=label, max_retries=2), label


def run_formation_agents(engine: "IronBottomEngine", state: GameState) -> list[dict[str, Any]]:
    """Run every formation's own agent for this turn, with its own memory.

    Each agent sees only its own ``FormationObservation`` plus *its own* memory and
    the order text it was sent.  Its decision is stored for audit, its movement plan
    is offered to the commander, and its bounded priority adjustments are collected
    for the gunnery selector — nothing else.

    A side with no model configured still fights: its formations run the
    deterministic doctrine and the label on the decision says so, so a reader can
    never mistake doctrine output for a model's.
    """
    from .command_observation import formation_observation
    from .formation_memory import memory_for, remember, render_for_prompt, write_note

    mode = state_for(state)
    decisions: list[dict[str, Any]] = []
    mode.local_directives = []
    for side in Side:
        agent, label = side_agent(side)
        mode.policy_labels[side.value] = label
        for formation in active_formations(state, side):
            observation = formation_observation(engine, state, side, formation.id)
            order = active_mission_order(state, formation.id)
            memory = memory_for(state, formation.id)
            order_text = memory.active_order_text
            if order is not None and order_text is None:
                # A structured order from the fleet is in force; render it as the
                # text the formation is acting on so the agent reads one thing.
                order_text = (
                    f"{order.mission}；意图：{order.commander_intent}；"
                    f"任务：{order.task_to_formation}"
                )
            attempts_before = len(getattr(agent, "attempts", []))
            decision = agent.act(
                observation,
                mission_order=order,
                comm_state=observation.comm_state,
                legal_action_mask=observation.legal_formation_actions,
                target_priority_space=observation.legal_target_priority_options,
                memory_text=render_for_prompt(memory),
                order_text=order_text,
            )
            decision.audit = {**decision.audit, "agent": label, "policy": label}
            mode.decisions.append(decision.model_dump(mode="json"))
            decisions.append(decision)
            mode.local_directives.extend(
                adjustment.as_directive(decision.formation_id)
                for adjustment in decision.target_priority_adjustments
            )
            _record_memory(
                state, formation, decision, observation,
                memory_for=memory_for, remember=remember, write_note=write_note,
            )
            _record_agent_log(
                state, formation, side, observation, order, decision, label,
                order_text=order_text, memory=memory,
                attempts=getattr(agent, "attempts", [])[attempts_before:],
            )
            engine._event(
                state, "formation_agent_decision",
                f"{formation.name} 本地代理决策：{decision.rationale_summary}",
                payload={
                    "secret_side": side.value,
                    "formation_id": formation.id,
                    "agent": label,
                    "turn": state.turn,
                    "selected_movement_action_id": decision.selected_movement_action_id,
                    "selected_movement_plan": decision.selected_movement_plan,
                    "selected_contingency_branch": decision.selected_contingency_branch,
                    "report_actions": decision.report_actions,
                    "adjustments": [
                        item.model_dump(mode="json")
                        for item in decision.target_priority_adjustments
                    ],
                    "acknowledgement": decision.acknowledgement,
                    "memory_note": decision.memory_note,
                    "audit": decision.audit,
                },
                rule=engine._rule("IBS-R-CD-02", None, "命令延迟：编队本地代理"),
            )
    return decisions


def _record_memory(
    state: GameState, formation, decision, observation, *, memory_for, remember, write_note,
) -> None:
    """Write this turn's experience into the formation's own memory."""
    memory = memory_for(state, formation.id)
    for contact in observation.local_contacts:
        # ``local_contacts`` is the payload form (a dict per contact).
        text = (
            f"见到 {contact.get('name')}（{contact.get('ship_type')}）"
            f"距离 {contact.get('range')}"
        )
        signature = f"{contact.get('ship_id')}@{contact.get('position')}"
        if memory.last_contact_signature == signature:
            continue  # the same sighting as last turn: do not pad the log
        remember(
            state, formation.id, kind="contact_seen", text=text,
            turn=state.turn, phase=state.phase.value,
            meta={"ship_id": contact.get("ship_id"), "range": contact.get("range")},
        )
        memory.last_contact_signature = signature
    remember(
        state, formation.id, kind="decision",
        text=(
            f"{decision.selected_movement_plan or '保持'} / "
            f"{decision.selected_contingency_branch or '无分支'}："
            f"{decision.rationale_summary}"
        ),
        turn=state.turn, phase=state.phase.value,
        meta={"plan": decision.selected_movement_plan},
    )
    active = observation.active_mission_order
    if active is not None:
        remember(
            state, formation.id, kind="contingency",
            text=f"命令 {active.order_id} 生效中",
            turn=state.turn, phase=state.phase.value,
        )
    if decision.report_actions:
        remember(
            state, formation.id, kind="report_sent",
            text="发出：" + "、".join(decision.report_actions),
            turn=state.turn, phase=state.phase.value,
        )
        memory.last_report_turn = state.turn
    if decision.memory_note:
        write_note(state, formation.id, text=decision.memory_note, turn=state.turn)


def _record_agent_log(
    state: GameState, formation, side: Side, observation, order, decision, label,
    *, order_text, memory, attempts,
) -> None:
    """Keep the raw transcript for the debug view and for replay without the model."""
    from .formation_memory import memory_payload, render_for_prompt
    from .formation_llm import build_prompt, compact_local_map

    mode = state_for(state)
    mode.agent_log.append({
        "turn": state.turn,
        "phase": state.phase.value,
        "side": side.value,
        "formation_id": formation.id,
        "formation_name": formation.name,
        "agent": label,
        "order_text": order_text,
        "memory_text": render_for_prompt(memory),
        "memory": memory_payload(memory),
        "prompt": compact_local_map(build_prompt(
            observation, order, memory_text=render_for_prompt(memory),
            order_text=order_text,
        )),
        "attempts": [
            {
                "attempt": item.attempt,
                "raw_response": item.raw_response,
                "errors": list(item.errors),
                "accepted": item.accepted,
                "fallback": item.fallback,
            }
            for item in attempts
        ],
        "decision": decision.model_dump(mode="json"),
    })
    keep = 600
    if len(mode.agent_log) > keep:
        mode.agent_log = mode.agent_log[-keep:]


def formation_plan(state: GameState, formation_id: str) -> str | None:
    """The plan the formation's local agent selected for the current turn."""
    mode = state_for(state)
    for record in reversed(mode.decisions):
        if record.get("formation_id") != formation_id:
            continue
        if record.get("turn") != state.turn:
            continue
        return record.get("selected_movement_plan")
    return None


def authority_for(state: GameState, side: Side) -> CommandAuthority | None:
    return state_for(state).authorities.get(side.value)


def issue_mission_orders(
    engine: "IronBottomEngine", state: GameState, side: Side,
) -> list[MissionOrder]:
    """Draft one MissionOrder per active formation, excluding the fleet's own.

    Deterministic and structural: the fleet commander states the task, the intent
    and the coordination measures; the *how* is left to the formation.  The order
    is sent as a message, so it is subject to the same routing and queue as
    everything else — a formation the fleet cannot reach never receives it.
    """
    mode = state_for(state)
    authority = mode.authorities.get(side.value)
    if authority is None or authority.fleet_formation_id is None:
        return []
    fleet_formation = state.formations[authority.fleet_formation_id]
    issued: list[MissionOrder] = []
    for formation in active_formations(state, side):
        if formation.id == fleet_formation.id:
            continue
        if any(
            order.formation_id == formation.id and order.expiry_turn is None
            for order in mode.mission_orders
        ):
            continue  # a standing order is already in force for this formation
        order = delegation.mission_order_template(
            order_id=f"{side.value}-order-{state.turn}-{formation.id}",
            formation_id=formation.id,
            side=side,
            turn=state.turn,
            issued_by=authority.fleet_commander_ship_id or fleet_formation.flagship_id,
            mission=(
                f"维持与主力相对位置，并在第 {state.turn} 回合内拦截进入责任区的敌舰"
            ),
            intent="阻止敌方巡洋舰群抵达炮击区",
            task=f"{formation.name} 保持与主力相对位置；发现敌轻型兵力时可脱离编队侧面接敌",
        )
        errors = delegation.validate_mission_order(order)
        if errors:
            engine._event(
                state, "mission_order_rejected",
                f"{formation.name} 的作战命令不完整，未发出",
                payload={
                    "secret_side": side.value,
                    "formation_id": formation.id,
                    "errors": errors,
                },
                rule=engine._rule("IBS-R-CD-04", None, "命令延迟：任务式命令"),
            )
            continue
        mode.mission_orders.append(order)
        decision = route(engine, state, fleet_formation, formation)
        kind = MessageKind.MISSION_ORDER
        send(engine, state, CommandMessage(
            message_id="",
            side=side,
            origin=order.issued_by,
            destination=formation.id,
            kind=kind,
            precedence=MessagePrecedence.OPERATIONAL,
            medium=decision.medium,
            issued_turn=state.turn,
            issued_phase=state.phase,
            handling_delay=delay_for(decision.medium, kind, decision.relay_hops),
            relay_hops=decision.relay_hops,
            reason=decision.reason,
            payload={"order_id": order.order_id},
        ))
        issued.append(order)
    return issued


def active_mission_order(state: GameState, formation_id: str) -> MissionOrder | None:
    """The newest confirmed order for one formation, if any."""
    mode = state_for(state)
    entry = mode.formations.get(formation_id)
    orders = [
        order for order in mode.mission_orders
        if order.formation_id == formation_id and order.confirmed_turn is not None
    ]
    if not orders:
        return None
    if entry is not None and entry.active_order_id is not None:
        match = next(
            (item for item in orders if item.order_id == entry.active_order_id), None
        )
        if match is not None:
            return match
    return sorted(orders, key=lambda item: (item.issued_turn, item.order_id))[-1]


def formation_command(state: GameState, formation_id: str) -> FormationCommandState | None:
    return state_for(state).formations.get(formation_id)


def is_embarked(state: GameState, formation: FormationState) -> bool:
    """True when the fleet commander sails in this formation."""
    authority = authority_for(state, formation.side)
    return authority is not None and authority.fleet_formation_id == formation.id


def max_formations_per_side() -> int:
    """Exposed for the UI so the mode cannot invent its own formation cap."""
    return MAX_FORMATIONS_PER_SIDE
