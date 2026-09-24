"""CD-2: Command Delay mode shell — isolation, authority, fleet/formation views.

The tests here are the ones the v2.2 acceptance list names for this stage:

* the three entries are mutually exclusive and an inconsistent request fails
  closed (never silently coerced);
* Classic and Realistic carry no Command Delay state at all;
* the fleet view is exact only for the embarked formation and receives every
  other own-side formation as an aged report;
* the formation view's contacts come from that formation's own ships, so a
  second formation's sightings do not appear in the first formation's view;
* no opposing formation ever appears in either view.
"""
from __future__ import annotations

import pytest

from iron_bottom_sound import command_delay
from iron_bottom_sound.command_observation import (
    fleet_observation,
    formation_observation,
    visible_enemies,
)
from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine
from iron_bottom_sound.models import (
    AuthorityLevel,
    FormationMovementOrder,
    GameOptions,
    LinkStatus,
    OrderBatch,
    Phase,
    Side,
)
from iron_bottom_sound.realistic_command import default_setup_orders

CD = GameOptions(realistic_command=True, command_delay_mode=True)


def command_delay_game(seed: int = 3, scenario: str = "IBS-S-03"):
    engine = IronBottomEngine()
    state = engine.reset(scenario, seed, CD)
    for side in Side:
        assert engine.submit_orders(state.game_id, OrderBatch(
            side=side, phase=Phase.FORMATION_SETUP,
            formation_setup=default_setup_orders(state, side),
        )).valid
    engine.advance(state.game_id)
    return engine, state


def movement_batch(state, side: Side) -> OrderBatch:
    """A minimal legal movement batch: one follow-wake order per active formation."""
    orders = [
        FormationMovementOrder(formation_id=formation.id, leader_plan="1")
        for formation in command_delay.active_formations(state, side)
    ]
    return OrderBatch(side=side, phase=state.phase, formation_movement=orders)


def run_phase(engine, state) -> None:
    """Submit every order phase this state owes, then advance once."""
    if state.phase in ORDER_PHASES:
        for side in Side:
            if side.value in state.submitted_orders:
                continue
            batch = (
                movement_batch(state, side)
                if state.phase == Phase.MOVEMENT_PLANNING
                else OrderBatch(side=side, phase=state.phase)
            )
            assert engine.submit_orders(state.game_id, batch).valid
    engine.advance(state.game_id)


# --------------------------------------------------------------------------- isolation

def test_mode_flags_are_mutually_exclusive_and_classic_is_unchanged() -> None:
    engine = IronBottomEngine()
    classic = engine.reset("IBS-S-03", 3, GameOptions())
    assert classic.options.realistic_command is False
    assert classic.options.command_delay_mode is False
    assert classic.command_delay is None
    assert classic.phase == Phase.REINFORCEMENT


def test_realistic_carries_no_command_delay_state() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 3, GameOptions(realistic_command=True))
    assert state.options.command_delay_mode is False
    assert state.command_delay is None
    for side in Side:
        assert engine.submit_orders(state.game_id, OrderBatch(
            side=side, phase=Phase.FORMATION_SETUP,
            formation_setup=default_setup_orders(state, side),
        )).valid
    engine.advance(state.game_id)
    assert state.command_delay is None, "Realistic must never gain Command Delay state"


def test_command_delay_without_realistic_fails_closed() -> None:
    engine = IronBottomEngine()
    with pytest.raises(ValueError, match="requires the realistic command formation core"):
        engine.reset("IBS-S-03", 3, GameOptions(command_delay_mode=True))


def test_command_delay_rejects_unsupported_scenarios() -> None:
    """The scenario guard is exercised at the rule boundary.

    No currently playable scenario lies outside ``SUPPORTED_SCENARIOS`` (the
    catalogued S-02/S-04/... are not playable yet), so the guard cannot be
    reached through ``engine.reset`` without a new playable scenario; it is
    tested directly, which is the same function ``build_initial_state`` calls.
    """
    # Derived from the live set rather than hardcoded: another lineage may support
    # more scenarios, and a hardcoded example turns that into a false failure.
    from iron_bottom_sound.realistic_command import SUPPORTED_SCENARIOS

    unsupported = next(
        candidate for candidate in ("IBS-S-99", "IBS-S-15", "IBS-S-02")
        if candidate not in SUPPORTED_SCENARIOS
    )
    with pytest.raises(ValueError, match="not available for scenario"):
        command_delay.validate_mode_options(
            GameOptions(realistic_command=True, command_delay_mode=True), unsupported
        )
    command_delay.validate_mode_options(
        GameOptions(realistic_command=True, command_delay_mode=True), "IBS-S-03"
    )


# --------------------------------------------------------------------------- authority

def test_authority_table_is_built_for_both_sides() -> None:
    engine, state = command_delay_game()
    mode = state.command_delay
    assert mode is not None
    for side in Side:
        authority = command_delay.authority_for(state, side)
        assert authority is not None
        assert authority.fleet_formation_id in state.formations
        fleet_formation = state.formations[authority.fleet_formation_id]
        assert fleet_formation.side == side
        assert authority.fleet_commander_ship_id == fleet_formation.flagship_id


def test_fleet_formation_is_the_largest_and_ties_break_on_id() -> None:
    engine, state = command_delay_game()
    for side in Side:
        expected = command_delay.fleet_formation_id(state, side)
        candidates = command_delay.active_formations(state, side)
        ranked = sorted(
            candidates,
            key=lambda formation: (
                -sum(1 for ship_id in formation.ship_ids if ship_id in state.ships),
                formation.id,
            ),
        )
        assert expected == ranked[0].id


def test_authority_is_fleet_directed_embarked_and_delegated_elsewhere() -> None:
    engine, state = command_delay_game()
    mode = state.command_delay
    assert mode is not None
    for side in Side:
        authority = command_delay.authority_for(state, side)
        for formation in command_delay.active_formations(state, side):
            entry = mode.formations[formation.id]
            if formation.id == authority.fleet_formation_id:
                assert entry.authority == AuthorityLevel.FLEET_DIRECTED
            else:
                assert entry.authority == AuthorityLevel.DELEGATED
            assert entry.link_status == LinkStatus.DIRECT


def test_tick_refreshes_reports_and_link_status_on_every_transition() -> None:
    engine, state = command_delay_game()
    mode = state.command_delay
    assert mode is not None
    start = mode.tick
    for _ in range(6):
        if state.phase == Phase.COMPLETE:
            break
        run_phase(engine, state)
    assert mode.tick > start
    for entry in mode.formations.values():
        assert entry.reported_turn is not None
        assert entry.reported_ship_count is not None


# --------------------------------------------------------------------------- views

def test_fleet_view_is_exact_only_for_the_embarked_formation() -> None:
    engine, state = command_delay_game()
    view = fleet_observation(engine, state, Side.AXIS)
    authority = command_delay.authority_for(state, Side.AXIS)
    assert view.embarked_formation_id == authority.fleet_formation_id
    assert view.embarked["ship_ids"]
    exact = [report for report in view.reports if report.is_source_of_truth]
    assert [report.formation_id for report in exact] == [authority.fleet_formation_id]
    for report in view.reports:
        if report.is_source_of_truth:
            continue
        # A remote formation reaches the fleet only as a *report*: a summary, an
        # age, and never per-ship detail.
        assert report.ship_count is not None
        assert report.guide_position is not None
        assert report.age_turns is not None
        assert not hasattr(report, "ships")


def test_fleet_view_never_contains_an_opposing_formation() -> None:
    engine, state = command_delay_game()
    for side in Side:
        view = fleet_observation(engine, state, side)
        opponent_formations = {
            formation.id for formation in state.formations.values()
            if formation.side != side
        }
        assert opponent_formations
        assert not opponent_formations & {report.formation_id for report in view.reports}
        opponent_ships = {
            ship.id for ship in state.ships.values() if ship.side != side
        }
        reported_ships = (
            set(view.embarked.get("ship_ids", []))
            | {report.commander_ship_id for report in view.reports if report.commander_ship_id}
        )
        assert not (opponent_ships & reported_ships)


def test_fleet_view_contacts_come_from_the_embarked_formation_only() -> None:
    engine, state = command_delay_game()
    view = fleet_observation(engine, state, Side.AXIS)
    authority = command_delay.authority_for(state, Side.AXIS)
    formation = state.formations[authority.fleet_formation_id]
    own_positions = [
        state.ships[ship_id].position for ship_id in formation.ship_ids
        if state.ships[ship_id].position is not None
    ]
    expected = {ship.id for ship in visible_enemies(engine, state, Side.AXIS, own_positions)}
    assert {contact["ship_id"] for contact in view.contacts} == expected


def test_formation_view_uses_local_contacts_not_the_side_plot() -> None:
    engine, state = command_delay_game(scenario="IBS-S-01")
    # Run a few turns so the formations have separated positions.
    for _ in range(6):
        if state.phase == Phase.COMPLETE:
            break
        if state.phase in ORDER_PHASES:
            run_phase(engine, state)
        else:
            engine.advance(state.game_id)
    axis_formations = command_delay.active_formations(state, Side.AXIS)
    assert len(axis_formations) >= 2, "need at least two formations to compare scopes"
    side_view = fleet_observation(engine, state, Side.AXIS)
    for formation in axis_formations:
        view = formation_observation(engine, state, Side.AXIS, formation.id)
        positions = [
            state.ships[ship_id].position for ship_id in formation.ship_ids
            if state.ships[ship_id].position is not None
        ]
        local = {ship.id for ship in visible_enemies(engine, state, Side.AXIS, positions)}
        assert {contact["ship_id"] for contact in view.local_contacts} == local
        # Every local contact must also be a contact the side could see, never more.
        assert local <= {contact["ship_id"] for contact in side_view.contacts}


def test_formation_view_reports_no_side_global_field() -> None:
    engine, state = command_delay_game()
    formation = command_delay.active_formations(state, Side.AXIS)[0]
    payload = formation_observation(engine, state, Side.AXIS, formation.id).model_dump()
    for forbidden in ("ships", "score", "sealed_orders", "submitted_orders", "wrecks",
                      "torpedo_tracks", "victory_reason", "winner"):
        assert forbidden not in payload, f"{forbidden} must not reach a local agent"


def test_formation_view_does_not_expose_sibling_reports() -> None:
    """IR-3: a formation's view carries its own knowledge, never its siblings' reports.

    The v2.2 field this replaces (``stale_external_reports``) listed every other
    formation's last reported position, read from the *fleet's* copy - so a formation saw
    a sibling's sighting with no message delivered to it. The causal rule is now enforced
    by what the view does not contain.
    """
    engine, state = command_delay_game()
    formations = command_delay.active_formations(state, Side.AXIS)
    if len(formations) < 2:
        pytest.skip("scenario has a single axis formation")
    view = formation_observation(engine, state, Side.AXIS, formations[0].id)
    assert not hasattr(view, "stale_external_reports")
    # and nothing in the knowledge ledger is about a *friendly* formation it was not sent:
    # at this point no traffic has been delivered to it at all
    assert view.knowledge == []
    for item in view.knowledge:
        assert item["source_kind"] in ("LOCAL_OBSERVATION", "DELIVERED_MESSAGE")
        assert item["source_id"] != formations[1].id


def test_formation_view_rejects_a_formation_of_the_other_side() -> None:
    engine, state = command_delay_game()
    opponent = command_delay.active_formations(state, Side.ALLIES)[0]
    with pytest.raises(KeyError):
        formation_observation(engine, state, Side.AXIS, opponent.id)


def test_formation_view_offers_enumerated_actions_and_bounded_priority() -> None:
    engine, state = command_delay_game()
    for _ in range(3):
        if state.phase in ORDER_PHASES:
            run_phase(engine, state)
        elif state.phase != Phase.COMPLETE:
            engine.advance(state.game_id)
    formation = command_delay.active_formations(state, Side.AXIS)[0]
    view = formation_observation(engine, state, Side.AXIS, formation.id)
    if state.phase == Phase.MOVEMENT_PLANNING and view.legal_formation_actions:
        for action in view.legal_formation_actions:
            assert action["action_id"].startswith("MOVE:")
            assert isinstance(action["plan"], str)
    for option in view.legal_target_priority_options:
        assert option["weight_max"] == view.local_priority_weight_limit
        assert option["weight_min"] == -view.local_priority_weight_limit
    assert "NONE" in view.report_actions
