"""Observation views for Command Delay (CD-2): fleet plot vs formation-local.

Two views, deliberately asymmetric
---------------------------------
``fleet_observation`` is what the fleet commander may know.  The commander is
embarked in one formation, so that formation's state is directly knowable; every
other own-side formation is known **only through its last received report**
(``FormationReport``), which carries a guide position, heading, speed, ship count
and declared geometry — never per-ship hull detail, never the live positions.
This is what acceptance criterion 4 means by "never leaks remote exact formation
state to the Fleet Commander", and it is enforced structurally: the report
fields are the only channels, and they are written by the communication layer.

``formation_observation`` is what a formation's local agent may know, and it is
the input list of the v2.2 plan §12 exactly: local formation state, local map,
**local** contacts, active mission order, received messages, comm state, stale
external reports, legal formation actions, legal target-priority options and the
allowed report actions.  Its contacts are computed from *this formation's own
ships'* visibility, not the side's, so no side-global truth can enter.

Both functions are read-only.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from . import command_delay
from .communications.processing import range_units
from .models import (
    AuthorityLevel,
    CommandMessage,
    CommunicationMedium,
    FormationState,
    GameState,
    HexCoord,
    LinkStatus,
    MissionOrder,
    MovementOrder,
    Phase,
    Side,
)

if TYPE_CHECKING:
    from .engine import IronBottomEngine

# How far a formation's own lookouts make its local map.  Uses the scenario's
# optical visibility, the same value the engine already uses for sighting, so
# the local map can never be wider than what the ships could actually see.
REPORT_ACTIONS = (
    "NONE",
    "SITREP",
    "CONTACT_REPORT",
    "DEVIATION_REPORT",
    "ACKNOWLEDGEMENT",
    "CLARIFICATION_REQUEST",
)

# Bound on a local agent's target-priority adjustment (plan §3.2).
LOCAL_PRIORITY_WEIGHT_LIMIT = 0.5


class FormationReport(BaseModel):
    """What the fleet knows about one formation, as of a turn."""

    formation_id: str
    name: str
    side: Side
    reported_turn: int | None = None
    age_turns: int | None = None
    link_status: LinkStatus = LinkStatus.DIRECT
    authority: AuthorityLevel = AuthorityLevel.DELEGATED
    commander_ship_id: str | None = None
    active_order_id: str | None = None
    guide_position: HexCoord | None = None
    # The map label players actually read on the board ("R14"), so a view never
    # has to show raw axial coordinates next to a labelled one.
    guide_label: str | None = None
    guide_heading: int | None = None
    guide_speed: int | None = None
    ship_count: int | None = None
    geometry_kind: str | None = None
    # The formation's own words, as delivered - this is what the fleet commander
    # actually has to reason about, so it travels with the report (CD-13).
    reported_text: str | None = None
    acknowledged_turn: int | None = None
    is_source_of_truth: bool = False


class FleetObservation(BaseModel):
    """The fleet commander's plot: exact only for the embarked formation."""

    game_id: str
    side: Side
    turn: int
    phase: Phase
    visibility: int
    map_columns: int
    map_rows: int
    embarked_formation_id: str | None = None
    fleet_commander_ship_id: str | None = None
    embarked: dict[str, Any] = Field(default_factory=dict)
    reports: list[FormationReport] = Field(default_factory=list)
    contacts: list[dict[str, Any]] = Field(default_factory=list)
    messages: list[dict[str, Any]] = Field(default_factory=list)
    authority: dict[str, Any] = Field(default_factory=dict)


class FormationObservation(BaseModel):
    """The local agent's view for one formation; no side-global truth."""

    game_id: str
    side: Side
    formation_id: str
    formation_name: str
    turn: int
    phase: Phase
    visibility: int
    map_columns: int
    map_rows: int
    authority: AuthorityLevel = AuthorityLevel.DELEGATED
    link_status: LinkStatus = LinkStatus.DIRECT
    formation_state: dict[str, Any] = Field(default_factory=dict)
    local_map: list[dict[str, Any]] = Field(default_factory=list)
    local_contacts: list[dict[str, Any]] = Field(default_factory=list)
    active_mission_order: MissionOrder | None = None
    received_messages: list[CommandMessage] = Field(default_factory=list)
    comm_state: dict[str, Any] = Field(default_factory=dict)
    # v2.3 replaced ``stale_external_reports`` (which handed a formation its siblings'
    # positions straight from the fleet's copy) with this formation's own knowledge
    # ledger: only what it observed or was actually sent.
    knowledge: list[dict[str, Any]] = Field(default_factory=list)
    legal_formation_actions: list[dict[str, Any]] = Field(default_factory=list)
    legal_target_priority_options: list[dict[str, Any]] = Field(default_factory=list)
    report_actions: list[str] = Field(default_factory=lambda: list(REPORT_ACTIONS))
    local_priority_weight_limit: float = LOCAL_PRIORITY_WEIGHT_LIMIT


def formation_members(state: GameState, formation: FormationState) -> list[str]:
    return [
        ship_id for ship_id in formation.ship_ids
        if ship_id in state.ships
        and state.ships[ship_id].position is not None
        and not state.ships[ship_id].sunk
        and state.ships[ship_id].command_status == "attached"
    ]


def _ship_card(state: GameState, ship) -> dict[str, Any]:
    return {
        "ship_id": ship.id,
        "name": ship.name,
        "ship_type": ship.ship_type,
        "position": ship.position.label if ship.position else None,
        "heading": ship.heading,
        "speed": ship.current_speed,
        "hull": ship.hull,
        "max_hull": ship.max_hull,
        "command_status": ship.command_status,
        "guns_disabled_turns": ship.guns_disabled_turns,
        "forced_straight_turns": ship.forced_straight_turns,
        "forced_circle_turns": ship.forced_circle_turns,
    }


def visible_enemies(
    engine: "IronBottomEngine", state: GameState, side: Side, own_positions: list[HexCoord],
) -> list[Any]:
    """Enemies visible to *these* observers only (never to the whole side)."""
    found = []
    for ship in state.ships.values():
        if ship.side == side or ship.sunk or ship.position is None:
            continue
        if engine._visible_to(state, ship, side, own_positions):
            found.append(ship)
    return sorted(found, key=lambda item: item.id)


def local_map_hexes(
    engine: "IronBottomEngine", state: GameState, positions: list[HexCoord],
    contact_labels: set[str], side: Side,
) -> list[dict[str, Any]]:
    """Hexes within the formation's own optical range, with terrain and contacts.

    Bounds are checked on the raw axial arithmetic *before* a ``HexCoord`` is
    constructed: ``HexCoord`` rejects a negative column, so an off-map
    neighbourhood is skipped rather than built and caught.
    """
    radius = _optical_range(state, side)
    cells: list[dict[str, Any]] = []
    for position in positions:
        for dq in range(-radius, radius + 1):
            for dr in range(-radius, radius + 1):
                q = position.q + dq
                r = position.r + dr
                if not (0 <= q < state.map_columns):
                    continue
                candidate = HexCoord(q=q, r=r)
                if position.distance(candidate) > radius:
                    continue
                display_row = r + (q - (q & 1)) // 2
                if not (0 <= display_row < state.map_rows):
                    continue
                label = candidate.label
                cells.append({
                    "hex": label,
                    "q": q,
                    "r": r,
                    "land": label in state.land_hexes,
                    "coast": label in state.coast_hexes,
                    "contact": label in contact_labels,
                })
    deduped: dict[str, dict[str, Any]] = {}
    for cell in cells:
        deduped.setdefault(cell["hex"], cell)
    return [deduped[label] for label in sorted(deduped)]


def _optical_range(state: GameState, side: Side | None = None) -> int:
    """The horizon a view is granted.

    With ``side`` given this is that side's own optical visibility, the same value
    the engine uses for sighting; without it, the narrower of the two sides', so
    a side-agnostic caller can never be handed a wider horizon than the stricter
    side has.
    """
    if not state.visibility:
        return 0
    if side is not None:
        return int(state.visibility[side.value])
    return int(min(state.visibility.values()))


def fleet_observation(engine: "IronBottomEngine", state: GameState, side: Side) -> FleetObservation:
    """Build the fleet commander's plot.  Read-only."""
    mode = command_delay.state_for(state)
    authority = mode.authorities.get(side.value)
    embarked_id = authority.fleet_formation_id if authority else None
    embarked: dict[str, Any] = {}
    reports: list[FormationReport] = []
    embarked_positions: list[HexCoord] = []
    for formation in command_delay.active_formations(state, side):
        entry = mode.formations.get(formation.id)
        members = formation_members(state, formation)
        is_embarked = formation.id == embarked_id
        if is_embarked:
            embarked = {
                "formation_id": formation.id,
                "name": formation.name,
                # ``ship_ids`` is the roster *afloat* — the same set ``ships``
                # describes — because that is what every consumer means by
                # "strength".  The declared roster (which keeps sunk ships) is
                # published separately so nothing has to infer the difference.
                "ship_ids": list(members),
                "declared_ship_ids": list(formation.ship_ids),
                "leader_id": formation.leader_id,
                "flagship_id": formation.flagship_id,
                "spacing": formation.spacing,
                "movement_style": formation.movement_style.value,
                "geometry_kind": formation.geometry_kind.value,
                "line_axis": formation.line_axis,
                "ships": [_ship_card(state, state.ships[ship_id]) for ship_id in members],
                # The wake the commander can see from the bridge.
                "guide_trail": [hexc.label for hexc in formation.guide_trail],
            }
            embarked_positions = [
                state.ships[ship_id].position for ship_id in members
                if state.ships[ship_id].position is not None
            ]
        reports.append(FormationReport(
            formation_id=formation.id,
            name=formation.name,
            side=formation.side,
            reported_turn=entry.reported_turn if entry else None,
            age_turns=(
                None if entry is None or entry.reported_turn is None
                else max(0, state.turn - entry.reported_turn)
            ),
            link_status=entry.link_status if entry else LinkStatus.DIRECT,
            authority=entry.authority if entry else AuthorityLevel.DELEGATED,
            commander_ship_id=entry.commander_ship_id if entry else formation.flagship_id,
            active_order_id=entry.active_order_id if entry else None,
            guide_position=entry.reported_position if entry else None,
            guide_label=(
                entry.reported_position.label if entry and entry.reported_position else None
            ),
            guide_heading=entry.reported_heading if entry else None,
            guide_speed=entry.reported_speed if entry else None,
            ship_count=entry.reported_ship_count if entry else None,
            geometry_kind=(
                entry.reported_geometry_kind.value
                if entry and entry.reported_geometry_kind else None
            ),
            reported_text=entry.reported_text if entry else None,
            acknowledged_turn=entry.last_ack_turn if entry else None,
            is_source_of_truth=is_embarked,
        ))
    contacts = [
        {
            "ship_id": enemy.id,
            "name": enemy.name,
            "ship_type": enemy.ship_type,
            "position": enemy.position.label if enemy.position else None,
            "heading": enemy.heading,
            "sunk": enemy.sunk,
        }
        for enemy in visible_enemies(engine, state, side, embarked_positions)
    ] if embarked_positions else []
    return FleetObservation(
        game_id=state.game_id,
        side=side,
        turn=state.turn,
        phase=state.phase,
        visibility=_optical_range(state, side),
        map_columns=state.map_columns,
        map_rows=state.map_rows,
        embarked_formation_id=embarked_id,
        fleet_commander_ship_id=authority.fleet_commander_ship_id if authority else None,
        embarked=embarked,
        reports=reports,
        contacts=contacts,
        messages=[_message_card(item) for item in _addressed_messages(state, side, None)],
        authority=command_delay.link_summary(state, side),
    )


def _message_card(message: CommandMessage) -> dict[str, Any]:
    return {
        "message_id": message.message_id,
        "kind": message.kind.value,
        "precedence": message.precedence.value,
        "medium": message.medium.value,
        "origin": message.origin,
        "destination": message.destination,
        "issued_turn": message.issued_turn,
        "issued_phase": message.issued_phase.value,
        "delivered_turn": message.delivered_turn,
        "observed_turn": message.observed_turn,
        "status": message.status.value,
        "reason": message.reason,
    }


def _addressed_messages(
    state: GameState, side: Side, formation_id: str | None,
) -> list[CommandMessage]:
    mode = command_delay.state_for(state)
    found = [
        message for message in mode.messages
        if message.side == side and (formation_id is None or message.destination == formation_id)
    ]
    return sorted(found, key=lambda item: (item.issued_turn, item.message_id))


def formation_observation(
    engine: "IronBottomEngine", state: GameState, side: Side, formation_id: str,
) -> FormationObservation:
    """Build one formation's local view.  Read-only; no side-global truth."""
    formation = state.formations.get(formation_id)
    if formation is None or formation.side != side:
        raise KeyError(f"Unknown formation {formation_id} for side {side.value}")
    mode = command_delay.state_for(state)
    entry = mode.formations.get(formation_id)
    members = formation_members(state, formation)
    positions = [
        state.ships[ship_id].position for ship_id in members
        if state.ships[ship_id].position is not None
    ]
    enemies = visible_enemies(engine, state, side, positions) if positions else []
    contact_labels = {
        enemy.position.label for enemy in enemies if enemy.position is not None
    }
    active_order = _active_order(state, formation_id)
    return FormationObservation(
        game_id=state.game_id,
        side=side,
        formation_id=formation_id,
        formation_name=formation.name,
        turn=state.turn,
        phase=state.phase,
        visibility=_optical_range(state, side),
        map_columns=state.map_columns,
        map_rows=state.map_rows,
        authority=entry.authority if entry else AuthorityLevel.DELEGATED,
        link_status=entry.link_status if entry else LinkStatus.DIRECT,
        formation_state={
            "leader_id": formation.leader_id,
            "flagship_id": formation.flagship_id,
            "reserve_flagship_id": formation.reserve_flagship_id,
            "spacing": formation.spacing,
            "heading": formation.heading,
            "speed": formation.speed,
            "status": formation.status,
            "disruption_turn": formation.disruption_turn,
            "movement_style": formation.movement_style.value,
            "geometry_kind": formation.geometry_kind.value,
            "line_axis": formation.line_axis,
            "ships": [_ship_card(state, state.ships[ship_id]) for ship_id in members],
        },
        local_map=(
            local_map_hexes(engine, state, positions, contact_labels, side)
            if positions else []
        ),
        # v2.3 (IR-6): the engine owns the unit conversion.  Every contact carries
        # range_hex / range_yards / range_nmi computed here, so a model never converts a
        # hex distance into miles itself - the v2.2 battle produced a report claiming
        # "12-15 海里" for what was 12-15 hex (about 3.5-4.4 nmi).
        local_contacts=[
            {
                "ship_id": enemy.id,
                "name": enemy.name,
                "ship_type": enemy.ship_type,
                "position": enemy.position.label if enemy.position else None,
                "heading": enemy.heading,
                "speed": enemy.current_speed,
                "range": (
                    min(position.distance(enemy.position) for position in positions)
                    if positions and enemy.position else None
                ),
                **range_units(
                    min(position.distance(enemy.position) for position in positions)
                    if positions and enemy.position else None
                ),
            }
            for enemy in enemies
        ],
        active_mission_order=active_order,
        received_messages=[
            message for message in _addressed_messages(state, side, formation_id)
            if message.delivered_turn is not None
        ],
        comm_state={
            "link_status": (entry.link_status.value if entry else LinkStatus.DIRECT.value),
            "authority": (entry.authority.value if entry else AuthorityLevel.DELEGATED.value),
            "tick": mode.tick,
            "mediums_available": [medium.value for medium in
                                  _available_mediums(state)],
        },
        knowledge=_knowledge_payload(state, formation_id),
        legal_formation_actions=legal_formation_actions(engine, state, formation),
        legal_target_priority_options=legal_target_priority_options(enemies, positions),
        report_actions=list(REPORT_ACTIONS),
        local_priority_weight_limit=LOCAL_PRIORITY_WEIGHT_LIMIT,
    )


def _available_mediums(state: GameState) -> tuple[CommunicationMedium, ...]:
    return (
        CommunicationMedium.TBS_SHORT,
        CommunicationMedium.BLINKER,
        CommunicationMedium.WT_CODED,
        CommunicationMedium.WT_REENCIPHER_RELAY,
        CommunicationMedium.BLACKOUT,
    )


def _active_order(state: GameState, formation_id: str) -> MissionOrder | None:
    mode = command_delay.state_for(state)
    entry = mode.formations.get(formation_id)
    orders = [
        order for order in mode.mission_orders
        if order.formation_id == formation_id and order.confirmed_turn is not None
    ]
    if not orders:
        return None
    if entry is not None and entry.active_order_id is not None:
        match = next((item for item in orders if item.order_id == entry.active_order_id), None)
        if match is not None:
            return match
    return sorted(orders, key=lambda item: (item.issued_turn, item.order_id))[-1]


def _knowledge_payload(state: GameState, formation_id: str) -> list[dict[str, Any]]:
    """This formation's own knowledge, with provenance (v2.3)."""
    from .formation_knowledge import knowledge_payload

    return knowledge_payload(state, formation_id)


# The movement plan shorthand, spelled out.  ``S``/``P`` are the engine's own letters
# (starboard / port); the degrees are what each command does to the heading.
MANOEUVRE_TEXT: dict[str, str] = {
    "advance": "前进",
    "turn_port_60": "左转 60°",
    "turn_starboard_60": "右转 60°",
    "turn_port_120": "左转 120°（原地调头一步）",
    "turn_starboard_120": "右转 120°（原地调头一步）",
}
MANOEUVRE_STEPS: dict[str, int] = {
    "turn_port_60": -1,
    "turn_starboard_60": 1,
    "turn_port_120": -2,
    "turn_starboard_120": 2,
}

NOTATION_LEGEND = (
    "机动记号读法：数字＝沿当前航向直线前进的格数，S＝右转 60°，SS＝右转 120°，"
    "P＝左转 60°，PP＝左转 120°（例：1SS1S2＝前进 1 格→右转 120°→前进 1 格→右转 60°→前进 2 格）。"
    "不要自己解析记号：每条合法机动都给了 manoeuvre（中文逐步说明）、ends_heading（该方案结束时的航向）、"
    "heading_change_steps（净转向，以 60° 为单位，正数＝右转）、keeps_heading（是否保持航向）"
    "与 jams_spaced_column（是否含原地 120° 转向；为 true 时纵队后舰会在同一脉冲挤进领舰格而被结算为急停，"
    "除非你真的要调头，否则不要选）。"
)


def manoeuvre_summary(commands: list[str]) -> str:
    """The plan's commands as one readable line ("前进 2 格 → 右转 120° → 前进 1 格")."""
    parts: list[str] = []
    pending = 0
    for command in commands:
        if command == "advance":
            pending += 1
            continue
        if pending:
            parts.append(f"前进 {pending} 格")
            pending = 0
        parts.append(MANOEUVRE_TEXT.get(command, command))
    if pending:
        parts.append(f"前进 {pending} 格")
    return " → ".join(parts) or "原地不动"


def heading_change_steps(commands: list[str]) -> int:
    """Net heading change in 60-degree steps (positive = starboard)."""
    return sum(MANOEUVRE_STEPS.get(command, 0) for command in commands)


def legal_formation_actions(
    engine: "IronBottomEngine", state: GameState, formation: FormationState,
) -> list[dict[str, Any]]:
    """Enumerated, engine-validated body/leader programmes for this formation.

    An action is an identifier plus the engine's own plan shorthand; the agent
    selects, it never invents a movement program (plan §12/§13).  Each action also
    carries what its plan does in words and to the heading, so a reader (model or
    player) never has to decode the shorthand itself.
    """
    members = formation_members(state, formation)
    if not members:
        return []
    leader = state.ships.get(formation.leader_id)
    if leader is None or leader.position is None or formation.leader_id not in members:
        leader = state.ships[members[0]]
    # Formation-level feasibility, by the engine's own rule (``validate_orders``: "speed N is
    # outside member limits; reduce or detach"): a body manoeuvre is only selectable while
    # its cost lies inside every member's legal speed interval.  Without this the agent can
    # pick a plan its own formation cannot execute, and the interface used to paper over that
    # by clamping the plan to the maximum speed - valid on paper, but a movement nobody chose.
    # When the interval is empty (a damaged ship that cannot keep station with the others)
    # nothing is filtered: that formation's answer is "reduce or detach", which the mode
    # already handles elsewhere, and hiding the whole list would leave the agent no answer.
    intervals = [engine._legal_speed_range(state.ships[ship_id], state.turn) for ship_id in members]
    minimum = max(low for low, _ in intervals)
    maximum = min(high for _, high in intervals)
    speed_interval_exists = minimum <= maximum
    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in engine.movement_candidates(state, leader, include_plans=True)["reachable"]:
        plans = [entry["plan"]] if entry.get("plan") is not None else []
        for heading in entry["final_headings"]:
            position = HexCoord(q=entry["hex"]["q"], r=entry["hex"]["r"])
            path = engine.movement_path(state, leader, position, heading=heading)
            if path.get("valid") and path["plan"] not in plans:
                plans.append(path["plan"])
        for plan in plans:
            if plan in seen:
                continue
            preview = engine.movement_preview(state, leader, plan=plan)
            if not preview["commitable"]:
                continue
            if speed_interval_exists and not (minimum <= preview["cost"] <= maximum):
                continue
            seen.add(plan)
            commands = list(preview["commands"])
            actions.append({
                "action_id": f"MOVE:{plan}",
                "plan": plan,
                "hex": entry["hex"],
                "label": HexCoord(q=entry["hex"]["q"], r=entry["hex"]["r"]).label,
                "cost": preview["cost"],
                # v2.4: the plan shorthand is unreadable to anyone who has not been told what
                # S/P mean, and a commander that misreads it orders a turn while its own note
                # says "hold course" (measured: EM-01 T2, the agent chose ``1SS1S2`` - a
                # 180-degree about-face - and wrote "heading 2, continue straight ahead").  So
                # the engine states the manoeuvre in words and gives the single heading this
                # plan ends on, instead of the set of headings the *destination hex* admits
                # (that set reads as "this plan turns" even for a plain ``5``).
                "manoeuvre": manoeuvre_summary(commands),
                "heading_now": leader.heading,
                "ends_heading": preview["current_heading"],
                "heading_change_steps": heading_change_steps(commands),
                "keeps_heading": heading_change_steps(commands) == 0,
                # The engine's own rule for a spaced column: an in-place 120-degree impulse
                # cannot propagate down it, so followers arrive into the leader's hex in the
                # same pulse and are emergency-stopped there.  Choosing such a plan is legal
                # but rarely what "hold course" means, so it is flagged rather than hidden.
                "jams_spaced_column": any(
                    command.endswith("120") for command in commands
                ),
            })
    actions.sort(key=lambda item: (item["label"], item["plan"]))
    return actions


def legal_target_priority_options(enemies: list[Any], positions: list[HexCoord]) -> list[dict[str, Any]]:
    """Targets this formation may weight, with the bounded adjustment interval."""
    options = []
    for enemy in enemies:
        if enemy.position is None:
            continue
        options.append({
            "target_id": enemy.id,
            "target_class": enemy.ship_type,
            "position": enemy.position.label,
            "range": min(position.distance(enemy.position) for position in positions) if positions else None,
            "weight_min": -LOCAL_PRIORITY_WEIGHT_LIMIT,
            "weight_max": LOCAL_PRIORITY_WEIGHT_LIMIT,
        })
    return sorted(options, key=lambda item: item["target_id"])
