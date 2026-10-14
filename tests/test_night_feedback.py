"""Public night feedback and coordinated AI; synthetic positions isolate policy.

These tests do not supply missing S04/S10 canonical deployment parameters.
"""
from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from iron_bottom_sound import api, night
from iron_bottom_sound.engine import IronBottomEngine, ORDER_PHASES
from iron_bottom_sound.models import (
    GameOptions, OptionalRules, Side, Phase, HexCoord, OrderBatch,
    GunneryOrder, GunMountOrder, SearchlightOrder, IlluminationOrder, MarkerState,
)
from iron_bottom_sound.storage import GameRepository
from iron_bottom_sound.tactical import PROFILES, TacticalCommander
from iron_bottom_sound.realistic_command import RealisticCommander


@pytest.fixture
def fleet():
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", options=GameOptions(ruleset_version="night-v2",
        optional_rules=OptionalRules(star_shells=True, searchlights=True, squalls=True)))
    own = [s for s in state.ships.values() if s.side == Side.AXIS][:3]
    target = next(s for s in state.ships.values() if s.side == Side.ALLIES)
    for ship in state.ships.values():
        ship.position = None
    for ship, label in zip(own, ["M12", "M13", "M14"]):
        ship.position = HexCoord.from_label(label)
    target.position = HexCoord.from_label("P12")
    state.visibility = {"axis": 12, "allies": 12}
    state.phase = Phase.GUNNERY
    return engine, state, own, target


def shots(own, target):
    return OrderBatch(side=Side.AXIS, gunnery=[GunneryOrder(ship_id=s.id,
        mounts=[GunMountOrder(mount_id=s.gun_mounts[0].id, target_id=target.id)]) for s in own])


def test_many_shooters_coordinate_one_light_but_players_can_use_multiple(fleet):
    engine, state, own, target = fleet
    batch = shots(own, target)
    night.tactical_orders(engine, state, Side.AXIS, batch, {})
    assert len(batch.searchlights) == 1
    assert batch.searchlights[0].target_id == target.id
    assert not night.validate(engine, state, batch)
    player = OrderBatch(side=Side.AXIS, searchlights=[SearchlightOrder(ship_id=s.id, target_id=target.id) for s in own])
    assert not night.validate(engine, state, player)
    night.prepare_gunnery(engine, state, [player])
    # Several beams neither multiply the target modifier nor change legality.
    assert engine._gunnery_modifiers(state, own[0], target, 3, 1, 5, 1)["target_searchlit"] == -3


def test_lights_support_actual_distinct_targets_and_not_unfired_contacts(fleet):
    engine, state, own, target = fleet
    other = target.model_copy(deep=True)
    other.id = "SYNTHETIC-SECOND-TARGET"
    other.position = HexCoord.from_label("P14")
    state.ships[other.id] = other
    batch = shots(own, target)
    batch.gunnery[-1].mounts[0].target_id = other.id
    night.tactical_orders(engine, state, Side.AXIS, batch, {})
    assert {o.target_id for o in batch.searchlights} == {target.id, other.id}
    assert len({o.ship_id for o in batch.searchlights}) == 2
    empty = OrderBatch(side=Side.AXIS)
    night.tactical_orders(engine, state, Side.AXIS, empty, {})
    assert not empty.searchlights


def test_ai_does_not_add_light_to_existing_effect_or_spend_duplicate_star_groups(fleet):
    engine, state, own, target = fleet
    state.markers = [MarkerState(id="lit", kind="searchlight", ship_id=own[0].id,
        target_ship_id=target.id, expires_turn=state.turn)]
    batch = shots(own, target)
    night.tactical_orders(engine, state, Side.AXIS, batch, {})
    assert not batch.searchlights
    state.markers.clear()
    state.visibility["axis"] = 4
    batch = OrderBatch(side=Side.AXIS)
    night.tactical_orders(engine, state, Side.AXIS, batch, {})
    assert len(batch.illumination) == 1
    night.prepare_gunnery(engine, state, [batch])
    again = OrderBatch(side=Side.AXIS)
    night.tactical_orders(engine, state, Side.AXIS, again, {})
    assert not again.illumination


def test_night_feedback_is_filtered_and_never_reveals_enemy_pending_illumination(fleet):
    engine, state, own, target = fleet
    state.visibility = {"axis": 1, "allies": 1}
    pending = lambda ship, center: {"side":ship.side.value, "ship_id":ship.id,
        "position":HexCoord.from_label(center).model_dump(), "turn":state.turn+1}
    state.scenario_state["pending_illumination"] = [pending(own[0], "L12"), pending(target, "ZZ30")]
    state.markers = [MarkerState(id="invisible-beam", kind="searchlight", ship_id=target.id,
        target_ship_id=own[0].id, expires_turn=state.turn)]
    # Remove illumination before observing: only visible endpoints may be drawn.
    target.position = None
    view = engine.observe(state.game_id, Side.AXIS)
    assert [p["center"] for p in view.environment["pending_illumination"]] == ["L12"]
    assert not view.environment["beams"]
    assert "ZZ30" not in view.model_dump_json()
    assert str(engine.rules.modifiers["optional"]["target_searchlit"]) in view.environment["effect_notes"]["searchlights"]
    assert not view.environment["areas"]  # rain enabled, no centers stays calm


def test_preview_marks_future_area_without_mutating_state_or_illuminating_now(fleet, tmp_path, monkeypatch):
    engine, state, own, target = fleet
    repository = GameRepository(tmp_path / "preview.sqlite3")
    monkeypatch.setattr(api, "engine", engine)
    monkeypatch.setattr(api, "repository", repository)
    client = TestClient(api.app)
    group = night.candidates(engine, state, Side.AXIS)["illumination"][0]
    batch = OrderBatch(side=Side.AXIS, searchlights=[SearchlightOrder(ship_id=own[0].id, target_id=target.id)],
        illumination=[IlluminationOrder(ship_id=own[0].id, mount_id=group["mount_id"],
            broadside=group["broadside"], target_hex=HexCoord.from_label("Z20"))])
    before = state.model_dump()
    response = client.post(f"/games/{state.game_id}/night-preview", headers={"X-Player-Side":"axis"}, json=batch.model_dump(mode="json"))
    assert response.status_code == 200, response.text
    environment = response.json()
    assert environment["preview"] is True
    assert environment["pending_illumination"][0]["center"] == "Z20"
    assert environment["pending_illumination"][0]["turn"] == state.turn + 1
    assert len(environment["pending_illumination"][0]["hexes"]) == 19
    beam = environment["beams"][0]
    assert beam["ship_id"] == own[0].id and beam["target_id"] == target.id
    assert [beam["hexes"][0], beam["hexes"][-1]] == [own[0].position.label, target.position.label]
    assert "Z20" not in environment["optical_hexes"]
    assert state.model_dump() == before
    repository.close()


@pytest.mark.parametrize("profile", ["rc_coordinated", "rc_t_hunter", "rc_torpedo_wings", "rc_screen", "rc_pincer"])
@pytest.mark.parametrize("realistic", [False, True])
def test_all_state_machine_profiles_coordinate_source_legal_lights(profile, realistic):
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-06", 1, GameOptions(ruleset_version="night-v2", realistic_command=realistic,
        optional_rules=OptionalRules(searchlights=True, star_shells=True)))
    commanders = {side: RealisticCommander(PROFILES[profile]) if realistic else TacticalCommander(PROFILES[profile]) for side in Side}
    # Real setup and reinforcement, then isolate current-position gunnery to
    # test lighting policy without mixing in costly movement strength checks.
    while state.phase in (Phase.FORMATION_SETUP, Phase.REINFORCEMENT):
        for side in Side:
            _, batch, _ = commanders[side].choose_plan(engine, state.game_id, side)
            assert engine.submit_orders(state.game_id, batch).valid
        engine.advance(state.game_id)
    state.phase = Phase.GUNNERY
    # Synthetic broadside contacts: canonical S06 starts outside optical
    # range, so skipping its movement phase would otherwise test zero lights.
    for which, labels in ((Side.AXIS, ["M12", "M13", "M14"]), (Side.ALLIES, ["P12", "P13", "P14"])):
        ships = [s for s in state.ships.values() if s.side == which]
        for index, ship in enumerate(ships):
            ship.position = HexCoord.from_label(labels[index]) if index < len(labels) else None
            ship.heading = 6
    state.visibility = {"axis": 12, "allies": 12}
    counts = []
    for side in Side:
        before = deepcopy(state.model_dump())
        _, batch, _ = commanders[side].choose_plan(engine, state.game_id, side)
        assert engine.validate_orders(state.game_id, batch).valid
        assert len(batch.searchlights) == len({o.target_id for o in batch.searchlights})
        counts.append(len(batch.searchlights))
        assert state.model_dump() == before
    assert sum(counts) > 0
