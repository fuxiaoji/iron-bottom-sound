"""Durable form of the live verification: API transparency, report privacy, autonomy.

These four things were checked by ``research/command_delay/verify_live.py`` during
the delivery review and are pinned here so they cannot regress:

1. the HTTP API is *transparent* — ``/games/{id}/view`` must equal the engine's own
   filtered ``observe(side)``, so the API layer can never widen the fog;
2. the neutral battle report must not carry a side's command traffic;
3. the fleet commander's own formation is on a physical link: DIRECT, never stale;
4. a formation whose link is cut entirely still decides, moves legally and fights
   to the end of the scenario on its pre-briefed plan, on LOCAL_AUTONOMY.
"""
from __future__ import annotations

import json

import pytest

from iron_bottom_sound import battle_report, command_delay
from iron_bottom_sound.communications import CommunicationMedium, RouteDecision
from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine
from iron_bottom_sound.llm import LLMPlayerSession
from iron_bottom_sound.models import (
    AuthorityLevel,
    GameOptions,
    LinkStatus,
    MessageKind,
    OrderBatch,
    Phase,
    Side,
)
from iron_bottom_sound.realistic_command import RealisticCommander, default_setup_orders

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


def play(engine, state, hook=None, max_steps: int = 400) -> None:
    sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
    steps = 0
    while state.phase != Phase.COMPLETE and steps < max_steps:
        steps += 1
        if hook is not None:
            hook(engine, state)
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                result = engine.submit_orders(
                    state.game_id, sessions[side].choose_orders(engine, state.game_id)
                )
                assert result.valid, (state.turn, state.phase, side, result.errors[:2])
        engine.advance(state.game_id)


# --------------------------------------------------------------------------- 1. API

def test_the_api_view_is_exactly_the_engines_filtered_observation() -> None:
    """The API must not be wider than ``engine.observe`` — the isolation rule.

    A spotted enemy is supposed to appear; the question is whether the *transport
    layer* ever adds anything.  Comparing the response with the engine's own view
    for both sides over a whole game answers it without guessing which ships are
    legitimately visible.
    """
    from fastapi.testclient import TestClient

    from iron_bottom_sound.api import app, engine as api_engine

    client = TestClient(app)
    created = client.post("/games", json={
        "scenario_id": "IBS-S-03", "seed": 3,
        "options": {"mode": "hotseat", "realistic_command": True,
                    "command_delay_mode": True},
    })
    assert created.status_code == 201, created.text
    game_id = created.json()["game_id"]
    state = api_engine.get(game_id)
    sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
    comparisons = 0
    steps = 0
    while state.phase != Phase.COMPLETE and steps < 400:
        steps += 1
        for side in Side:
            response = client.get(f"/games/{game_id}/view",
                                  headers={"X-Player-Side": side.value})
            assert response.status_code == 200
            expected = api_engine.observe(game_id, side).model_dump(mode="json")
            assert response.json() == json.loads(json.dumps(expected, default=str)), (
                f"/view for {side.value} is not the engine's own observation"
            )
            comparisons += 1
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                assert api_engine.submit_orders(
                    game_id, sessions[side].choose_orders(api_engine, game_id)
                ).valid
        assert client.post(f"/games/{game_id}/advance",
                           headers={"X-Player-Side": "axis"}).status_code == 200
    assert comparisons > 30, "the comparison must run across the whole game"


def test_the_event_endpoints_never_return_the_other_sides_command_traffic() -> None:
    from fastapi.testclient import TestClient

    from iron_bottom_sound.api import app, engine as api_engine

    client = TestClient(app)
    game_id = client.post("/games", json={
        "scenario_id": "IBS-S-01", "seed": 20270830,
        "options": {"mode": "hotseat", "realistic_command": True,
                    "command_delay_mode": True},
    }).json()["game_id"]
    state = api_engine.get(game_id)
    sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
    steps = 0
    seen_command_events = 0
    while state.phase != Phase.COMPLETE and steps < 400:
        steps += 1
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                assert api_engine.submit_orders(
                    game_id, sessions[side].choose_orders(api_engine, game_id)
                ).valid
        returned = client.post(f"/games/{game_id}/advance",
                              headers={"X-Player-Side": "axis"}).json()
        listed = client.get(f"/games/{game_id}/events",
                            headers={"X-Player-Side": "axis"}).json()
        for event in returned + listed:
            secret = event.get("payload", {}).get("secret_side")
            assert secret in (None, "axis"), (
                f"{event['type']} addressed to {secret} reached the axis player"
            )
            if event["type"].startswith(("command_delay", "command_message",
                                         "formation_agent")):
                seen_command_events += 1
    assert seen_command_events, "the axis player must still see its own command events"


# --------------------------------------------------------------------------- 2. report

def test_the_neutral_battle_report_carries_no_side_command_traffic() -> None:
    engine, state = start()
    play(engine, state)
    entries: list[dict] = []
    for turn in range(1, state.turn + 1):
        entries.extend(battle_report.public_events_for_turn(state, engine, turn))
    types = {event.type for event in entries}
    for private in ("command_delay_initialised", "command_delay_turn_state",
                    "formation_agent_decision", "command_message_delivered",
                    "command_message_queued", "orders_submitted"):
        assert private not in types, f"{private} reached the neutral report"
    payload = json.dumps(
        [event.payload for event in entries], ensure_ascii=False, default=str
    )
    for needle in ("mission_order", "target_priorities", "local_agent",
                   "loss_of_comm_branch"):
        assert needle not in payload, f"the report carries {needle}"
    # The report must still contain the battle itself.
    assert any(event.type.startswith(("gunnery", "torpedo", "collision", "movement"))
               for event in entries)


# --------------------------------------------------------------------------- 3/4. autonomy

def test_the_embarked_formation_link_is_direct_and_never_stale() -> None:
    """Checked on live formations: a destroyed one has no link to be on."""
    engine, state = start()
    mode = state.command_delay
    checked = 0
    for side in Side:
        authority = command_delay.authority_for(state, side)
        held: set[tuple[str, str]] = set()

        def hook(engine_, state_, side=side, authority=authority, held=held):
            entry = state_.command_delay.formations.get(authority.fleet_formation_id)
            formation = state_.formations.get(authority.fleet_formation_id)
            if entry is None or formation is None or formation.status == "dissolved":
                return
            held.add((entry.link_status.value, entry.authority.value))

        play(engine, state, hook=hook)
        for status, level in sorted(held):
            checked += 1
            assert level == AuthorityLevel.FLEET_DIRECTED.value
            assert status == LinkStatus.DIRECT.value, (
                "the admiral's own formation cannot be out of touch with itself"
            )
    assert checked, "the embarked formation must have been live at some point"


def test_a_formation_on_a_stale_link_is_on_local_autonomy() -> None:
    """The label must agree with the doctrine the agent is already executing."""
    engine, state = start()
    mode = state.command_delay
    assert mode is not None
    for side in Side:
        authority = command_delay.authority_for(state, side)
        for formation in command_delay.active_formations(state, side):
            entry = mode.formations[formation.id]
            if formation.id == authority.fleet_formation_id:
                continue
            if entry.link_status in (LinkStatus.STALE, LinkStatus.BLACKOUT):
                assert entry.authority == AuthorityLevel.LOCAL_AUTONOMY, (
                    f"{formation.id} is {entry.link_status.value} but {entry.authority.value}"
                )
            else:
                assert entry.authority == AuthorityLevel.DELEGATED


def test_a_formation_with_its_link_cut_still_fights_the_whole_scenario() -> None:
    """One formation gets no orders and no sitreps in either direction."""
    engine, state = start()
    cut = next(
        item.id for item in command_delay.active_formations(state, Side.ALLIES)
        if item.id != command_delay.authority_for(state, Side.ALLIES).fleet_formation_id
    )
    original_route, original_send = command_delay.route, command_delay.send

    def blackout(engine_, state_, origin, destination):
        decision = original_route(engine_, state_, origin, destination)
        if cut in (origin.id, destination.id):
            return RouteDecision(CommunicationMedium.BLACKOUT, 0, "link cut by test")
        return RouteDecision(decision.medium, decision.relay_hops, decision.reason)

    def drop_orders(engine_, state_, message):
        if message.kind in (MessageKind.MISSION_ORDER, MessageKind.AMENDMENT):
            message.medium = CommunicationMedium.BLACKOUT
        return original_send(engine_, state_, message)

    command_delay.route, command_delay.send = blackout, drop_orders
    try:
        seen_autonomy = False

        def hook(engine_, state_):
            nonlocal seen_autonomy
            entry = state_.command_delay.formations.get(cut)
            if entry is not None and entry.authority == AuthorityLevel.LOCAL_AUTONOMY:
                seen_autonomy = True

        play(engine, state, hook=hook)
    finally:
        command_delay.route, command_delay.send = original_route, original_send

    mode = state.command_delay
    assert state.phase == Phase.COMPLETE, "the scenario must still finish"
    assert seen_autonomy, "the cut formation must have gone to local autonomy"
    cut_decisions = [r for r in mode.decisions if r["formation_id"] == cut]
    assert cut_decisions, "the cut formation must still have decided"
    assert all(r["audit"].get("order_received") is False for r in cut_decisions)
    assert any(r["selected_movement_plan"] for r in cut_decisions), (
        "acting independently means it still chose a legal plan"
    )
    # And the fleet only ever held an aged report of it.
    assert not [r for r in mode.mission_orders
                if r.formation_id == cut and r.confirmed_turn is not None]
    assert not any(
        event.type == "collision" and event.payload.get("friendly")
        for event in state.events
    )


# --------------------------------------------------------------------------- 5. UI payload

def test_the_fleet_and_local_views_agree_on_a_formation_strength() -> None:
    """The two halves of the command-delay panel must not disagree.

    The fleet view and the local view are rendered side by side, so any difference
    in "how many ships does this formation have" is visible to the player as a
    contradiction.  ``ship_ids`` is therefore the roster *afloat* (the same set the
    per-ship cards describe), and the declared roster — which keeps sunk ships — is
    published separately as ``declared_ship_ids``.
    """
    from iron_bottom_sound.command_observation import (
        fleet_observation, formation_observation,
    )

    engine, state = start()
    comparisons = 0
    sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
    steps = 0
    while state.phase != Phase.COMPLETE and steps < 400:
        steps += 1
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                assert engine.submit_orders(
                    state.game_id, sessions[side].choose_orders(engine, state.game_id)
                ).valid
        engine.advance(state.game_id)
        fleet = fleet_observation(engine, state, Side.AXIS)
        if not fleet.embarked:
            continue  # the admiral's formation is gone; nothing to compare
        local = formation_observation(
            engine, state, Side.AXIS, fleet.embarked_formation_id
        )
        afloat = len(fleet.embarked["ship_ids"])
        declared = len(fleet.embarked["declared_ship_ids"])
        cards = len(fleet.embarked["ships"])
        assert afloat == cards == len(local.formation_state["ships"]), (
            f"t{state.turn} {state.phase.value}: fleet says {afloat}/{cards}, local says "
            f"{len(local.formation_state['ships'])}"
        )
        assert declared >= afloat, "the declared roster cannot be smaller than the afloat one"
        comparisons += 1
    assert comparisons >= 5, "the comparison must run across several phases"
