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

from .models import (
    AuthorityLevel,
    CommandAuthority,
    CommandDelayState,
    FormationCommandState,
    FormationState,
    GameOptions,
    GameState,
    LinkStatus,
    Phase,
    Side,
)
from .realistic_command import MAX_FORMATIONS_PER_SIDE, SUPPORTED_SCENARIOS

if TYPE_CHECKING:
    from .engine import IronBottomEngine

RULE_AUTHORITY = "IBS-R-CD-02"


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
    engine._event(
        state, "command_delay_initialised",
        "命令延迟模式：建立舰队—编队指挥链与权限表",
        payload={
            "tick": mode.tick,
            "authorities": {
                side.value: {
                    "level": mode.authorities[side.value].level.value,
                    "fleet_formation_id": mode.authorities[side.value].fleet_formation_id,
                    "fleet_commander_ship_id": mode.authorities[side.value].fleet_commander_ship_id,
                }
                for side in Side if side.value in mode.authorities
            },
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
    entry.reported_turn = state.turn
    entry.last_report_turn = state.turn
    entry.reported_position = guide.position if guide is not None else None
    entry.reported_heading = guide.heading if guide is not None else None
    entry.reported_speed = guide.current_speed if guide is not None else None
    entry.reported_ship_count = len(members)
    entry.reported_geometry_kind = formation.geometry_kind
    entry.commander_ship_id = formation.flagship_id
    return entry


def refresh_link_status(state: GameState) -> None:
    """Recompute each formation's link status.

    CD-2 declares every link ``DIRECT``: the mode shell deliberately models no
    delay yet, and CD-3 is the only stage allowed to make this depend on the
    communication ledger.  Keeping the assignment behind a single function is
    what lets the CD-2 and CD-3 behaviour be compared directly.
    """
    mode = state_for(state)
    for formation_id in sorted(mode.formations):
        entry = mode.formations[formation_id]
        entry.link_status = LinkStatus.DIRECT
        formation = state.formations.get(formation_id)
        if formation is None or formation.status == "dissolved":
            entry.link_status = LinkStatus.BLACKOUT
            continue
        authority = mode.authorities.get(formation.side.value)
        embarked = authority is not None and authority.fleet_formation_id == formation_id
        entry.authority = (
            AuthorityLevel.FLEET_DIRECTED if embarked else AuthorityLevel.DELEGATED
        )


def on_phase_advanced(engine: "IronBottomEngine", state: GameState) -> None:
    """The single per-phase hook; inert unless the mode is on.

    Called at the end of every ``engine.advance`` transition, which covers phase
    boundaries and the turn rollover in one place.  It both lazily initialises
    (so a game saved before the option existed still boots) and refreshes
    authority, link status and reports.
    """
    if not enabled(state):
        return
    mode = state_for(state)
    if not mode.formations:
        initialise(engine, state)
    mode.tick += 1
    refresh_link_status(state)
    for side in Side:
        for formation in active_formations(state, side):
            _write_report(state, formation)
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


def authority_for(state: GameState, side: Side) -> CommandAuthority | None:
    return state_for(state).authorities.get(side.value)


def formation_command(state: GameState, formation_id: str) -> FormationCommandState | None:
    return state_for(state).formations.get(formation_id)


def is_embarked(state: GameState, formation: FormationState) -> bool:
    """True when the fleet commander sails in this formation."""
    authority = authority_for(state, formation.side)
    return authority is not None and authority.fleet_formation_id == formation.id


def max_formations_per_side() -> int:
    """Exposed for the UI so the mode cannot invent its own formation cap."""
    return MAX_FORMATIONS_PER_SIDE
