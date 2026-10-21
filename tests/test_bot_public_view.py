from copy import deepcopy
from io import BytesIO
from types import SimpleNamespace

from PIL import Image
import pytest

from iron_bottom_sound.bot.public_view import public_observation, public_png
from iron_bottom_sound.models import GameEvent, HexCoord, MarkerState, Phase, PlayerObservation, PublicShip, Side, TorpedoTrack, WreckState


def ship(identity="shared", side=Side.AXIS, **changes):
    data = dict(id=identity, name="共同可见舰", side=side, ship_type="DD", position=HexCoord(q=1, r=1),
                heading=2, current_speed=3, hull=1, max_hull=9, fire_markers=0, fired=False,
                sunk=False, asset=None, primary_armor=20, max_speed=8,
                captain_status="killed", formation_id="private-formation", combat_history=[])
    data.update(changes)
    return PublicShip(**data)


def observation(side, ships, **changes):
    data = dict(game_id="test", scenario_id="S03", scenario_title="公开想定", side=side,
                turn=1, max_turns=3, phase=Phase.MOVEMENT_PLANNING, visibility=10,
                map_columns=4, map_rows=4, ships=ships, score={"axis": 0, "allies": 0},
                recent_events=[], winner=None, victory_reason=None,
                environment={"SECRET": "only one side"}, battle_losses={"SECRET": []})
    data.update(changes)
    return PlayerObservation(**data)


class Engine:
    def __init__(self, axis, allies):
        self.views = {Side.AXIS: axis, Side.ALLIES: allies}
        self.calls = []

    def observe(self, game_id, side):
        assert game_id == "test"
        self.calls.append(side)
        return self.views[side].model_copy(deep=True)


def state():
    return SimpleNamespace(game_id="test", land_hexes=[], coast_hexes=[],
                           submitted_orders={"axis": {"SECRET": "orders"}})


def test_intersection_omits_hidden_one_side_and_unknown_aliases():
    axis = observation(Side.AXIS, [ship(), ship("axis-only"), ship("unknown-axis", identified=False)])
    allies = observation(Side.ALLIES, [ship(), ship("allies-only"), ship("unknown-allies", identified=False)])
    engine = Engine(axis, allies)
    public = public_observation(engine, state())
    assert [s.id for s in public.ships] == ["shared"]
    assert engine.calls == [Side.AXIS, Side.ALLIES]
    assert public.environment == public.battle_losses == {}
    assert public.formations == []
    assert "SECRET" not in public.model_dump_json()


@pytest.mark.parametrize("change", [{"position": HexCoord(q=2, r=1)}, {"heading": 3}, {"name": "different"}, {"identified": False}, {"side": Side.ALLIES}])
def test_one_side_knows_different_position_or_identity_is_omitted(change):
    engine = Engine(observation(Side.AXIS, [ship()]), observation(Side.ALLIES, [ship(**change)]))
    assert public_observation(engine, state()).ships == []


def test_even_common_ship_never_contains_damage_weapons_or_private_state():
    axis = observation(Side.AXIS, [ship(hull=1, radar_destroyed=True)])
    allies = observation(Side.ALLIES, [ship(hull=None, max_hull=None)])
    public = public_observation(Engine(axis, allies), state()).ships[0]
    assert public.hull is public.max_hull is None
    assert public.gun_mounts == public.torpedo_launchers == public.combat_history == []
    assert public.primary_armor is public.max_speed is public.captain_status is public.formation_id is None
    assert public.radar_destroyed is False
    assert axis.ships[0].hull == 1  # Projection must not mutate either view.


def test_events_markers_wrecks_require_identical_full_json_and_no_private_orders():
    event_args = dict(turn=1, phase=Phase.MOVEMENT_PLANNING)
    common = GameEvent(sequence=1, type="phase_changed", message="共同阶段", **event_args)
    private = GameEvent(sequence=2, type="orders_submitted", message="SECRET", **event_args)
    unequal_a = GameEvent(sequence=3, type="move", message="own position", **event_args)
    unequal_b = unequal_a.model_copy(update={"message": "unknown contact"})
    marker = MarkerState(id="public", kind="smoke", position=HexCoord(q=1, r=1))
    secret = MarkerState(id="secret", kind="contact", secret_side=Side.AXIS, contact_truth="real")
    wreck = WreckState(id="wreck", position=HexCoord(q=0, r=0), source_ship_id="shared")
    left = observation(Side.AXIS, [], recent_events=[common, private, unequal_a], markers=[marker, secret], wrecks=[wreck])
    right = observation(Side.ALLIES, [], recent_events=[deepcopy(common), deepcopy(private), unequal_b], markers=[deepcopy(marker), deepcopy(secret)])
    public = public_observation(Engine(left, right), state())
    assert public.recent_events == [common]
    assert public.markers == [marker]
    assert public.wrecks == []
    assert "SECRET" not in public.model_dump_json()


def test_score_and_metadata_must_match():
    left, right = observation(Side.AXIS, []), observation(Side.ALLIES, [], score={"axis": 9})
    assert public_observation(Engine(left, right), state()).score == {}
    right.turn = 2
    with pytest.raises(ValueError, match="公开阶段"):
        public_observation(Engine(left, right), state())


def test_torpedo_tracks_use_complete_intersection_not_common_ids():
    common = TorpedoTrack(id="shared-track", side=Side.AXIS, launcher_ship_id="shared",
                         torpedo_type="test", position=HexCoord(q=1, r=1), heading=2,
                         speed_cycle=(1, 1, 1), range_remaining=3, launched_turn=1)
    different = common.model_copy(deep=True, update={"id": "mismatched", "range_remaining": 2})
    other = different.model_copy(deep=True, update={"range_remaining": 1})
    left = observation(Side.AXIS, [], torpedo_tracks=[common, different])
    right = observation(Side.ALLIES, [], torpedo_tracks=[common.model_copy(deep=True), other])
    assert public_observation(Engine(left, right), state()).torpedo_tracks == [common]


def test_public_png_is_valid_and_renderer_never_sees_original_engine_or_secrets():
    engine = Engine(observation(Side.AXIS, [ship(), ship("hidden")]), observation(Side.ALLIES, [ship()]))
    raw = public_png(engine, state())
    assert raw.startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(BytesIO(raw)) as image:
        image.verify()
    assert engine.calls == [Side.AXIS, Side.ALLIES]
