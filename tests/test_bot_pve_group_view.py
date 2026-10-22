"""The PVE group sees the sole human seat, without a second world-truth lookup."""
from io import BytesIO
from types import SimpleNamespace

from PIL import Image, ImageDraw
import pytest

from iron_bottom_sound import battle_report
from iron_bottom_sound.bot.public_view import (
    public_observation, public_png, pve_public_observation, pve_public_png,
)
from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import (
    GameEvent, GameOptions, HexCoord, MarkerState, OptionalRules, Phase,
    PlayerObservation, PublicShip, Side, TorpedoTrack, WreckState,
)


def ship(identity, side=Side.ALLIES, **changes):
    data = dict(id=identity, name="己方舰", side=side, ship_type="DD",
                position=HexCoord(q=1, r=1), heading=2, current_speed=3,
                hull=1, max_hull=9, fire_markers=1, fired=False, sunk=False,
                asset=None, formation_id="SECRET-formation", captain_status="killed")
    data.update(changes)
    return PublicShip(**data)


def observation(side, ships, **changes):
    data = dict(game_id="test", scenario_id="S03", scenario_title="测试想定", side=side,
                turn=1, max_turns=3, phase=Phase.MOVEMENT_PLANNING, visibility=10,
                map_columns=4, map_rows=4, ships=ships, score={"axis": 0, "allies": 0},
                recent_events=[], winner=None, victory_reason=None,
                own_orders_submitted=True, both_orders_submitted=True,
                environment={"SECRET": "weather"}, battle_losses={"SECRET": []})
    data.update(changes)
    return PlayerObservation(**data)


class Engine:
    def __init__(self, views):
        self.views = views
        self.calls = []

    def observe(self, game_id, side):
        assert game_id == "test"
        self.calls.append(side)
        # Returning the source itself also checks that the projection owns copies.
        return self.views[side]


def state():
    # No ships, events, orders or other world fields are available to this code.
    return SimpleNamespace(game_id="test", land_hexes=["A1"], coast_hexes=[])


def test_pve_own_ships_survive_without_observing_ai_hidden_ships_or_orders():
    own = ship("own")
    source = observation(Side.ALLIES, [own], recent_events=[GameEvent(
        sequence=1, turn=1, phase=Phase.MOVEMENT_PLANNING, type="orders_submitted",
        message="SECRET-plan", payload={"SECRET": "sealed orders"},
    )])
    engine = Engine({Side.ALLIES: source})
    view = pve_public_observation(engine, state(), Side.ALLIES)
    assert engine.calls == [Side.ALLIES]
    assert [(s.id, s.name) for s in view.ships] == [("own", "己方舰")]
    assert view.recent_events == view.formations == []
    assert view.environment == view.battle_losses == {}
    assert not view.own_orders_submitted and not view.both_orders_submitted
    assert "SECRET" not in view.model_dump_json()
    assert view.ships[0].hull is view.ships[0].max_hull is None
    assert view.ships[0].formation_id is view.ships[0].captain_status is None
    assert view.ships[0].position is not own.position
    view.ships[0].position = HexCoord(q=2, r=1)
    assert own.position.q == 1


def test_pve_keeps_observed_enemy_aliases_and_never_restores_unknown_identity():
    unknown = ship("contact-blue-7", Side.AXIS, name="SECRET-name", identified=False,
                   ship_type="SECRET-class", asset="SECRET-image")
    visible = ship("observed-enemy", Side.AXIS, name="已识别敌舰")
    unplaced = ship("not-on-map", position=None)
    view = pve_public_observation(Engine({Side.ALLIES: observation(
        Side.ALLIES, [ship("own"), unknown, visible, unplaced])}), state(), Side.ALLIES)
    assert [s.id for s in view.ships] == ["own", "contact-blue-7", "observed-enemy"]
    assert view.ships[1].identified is False
    assert view.ships[1].name == "敌舰" and view.ships[1].ship_type == "unknown"
    assert view.ships[1].asset is None
    assert view.ships[2].name == "已识别敌舰"
    assert "SECRET" not in view.model_dump_json()


def test_visible_contacts_keep_glyphs_but_drop_secret_truth_and_all_private_references():
    source = observation(Side.ALLIES, [ship("own")], markers=[
        MarkerState(id="SECRET-real", kind="contact", position=HexCoord(q=0, r=0),
                    secret_side=Side.AXIS, contact_truth="real", ship_id="SECRET-enemy"),
        MarkerState(id="SECRET-decoy", kind="contact", position=HexCoord(q=2, r=1),
                    secret_side=Side.ALLIES, contact_truth="decoy"),
        MarkerState(id="SECRET-unplaced", kind="contact", secret_side=Side.ALLIES,
                    contact_truth="real"),
    ], torpedo_tracks=[TorpedoTrack(
        id="SECRET-track", side=Side.AXIS, launcher_ship_id="SECRET-enemy",
        torpedo_type="SECRET-type", position=HexCoord(q=0, r=0), heading=2,
        speed_cycle=(1, 1, 1), range_remaining=3, launched_turn=1,
        contact_ship_ids=["SECRET-contact"], hidden=True,
    )], wrecks=[WreckState(id="SECRET-wreck", position=HexCoord(q=0, r=1),
                          source_ship_id="SECRET-enemy")])
    view = pve_public_observation(Engine({Side.ALLIES: source}), state(), Side.ALLIES)
    assert len(view.markers) == 2
    assert [m.position for m in view.markers] == [m.position for m in source.markers[:2]]
    assert all(m.secret_side is m.contact_truth is m.ship_id is m.target_ship_id is None
               for m in view.markers)
    assert view.torpedo_tracks[0].launcher_ship_id == ""
    assert view.torpedo_tracks[0].contact_ship_ids == []
    assert view.wrecks[0].source_ship_id == ""
    assert "SECRET" not in view.model_dump_json()


@pytest.mark.parametrize("side", list(Side))
def test_pve_renderer_receives_only_projection_terrain_and_exact_human_side(monkeypatch, side):
    source = observation(side, [ship("own", side)])
    original_engine = Engine({side: source})
    original_state = state()
    render = battle_report.render_map_image
    calls = []

    def guarded_render(render_state, render_engine, render_side, **kwargs):
        assert render_engine is not original_engine and render_state is not original_state
        assert vars(render_state).keys() == {
            "game_id", "scenario_title", "map_columns", "map_rows", "land_hexes", "coast_hexes",
        }
        assert render_state.land_hexes == ("A1",) and render_state.coast_hexes == ()
        assert render_side == side and kwargs == {"ship_names": True}
        view = render_engine.observe("test", side)
        assert "SECRET" not in view.model_dump_json()
        assert [s.id for s in view.ships] == ["own"]
        with pytest.raises(ValueError):
            render_engine.observe("test", side.opponent)
        with pytest.raises(ValueError):
            render_engine.observe("wrong-game", side)
        calls.append(True)
        return render(render_state, render_engine, render_side, **kwargs)

    monkeypatch.setattr(battle_report, "render_map_image", guarded_render)
    texts = []
    text = ImageDraw.ImageDraw.text

    def capture_text(self, xy, value, *args, **kwargs):
        texts.append(value)
        return text(self, xy, value, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", capture_text)
    raw = pve_public_png(original_engine, original_state, side)
    assert calls == [True] and original_engine.calls == [side]
    with Image.open(BytesIO(raw)) as image:
        image.verify()
    label = "盟军" if side == Side.ALLIES else "日军"
    assert any(f"PVE玩家视角·{label}" in value for value in texts)
    assert texts[:2] == ["己方", "舰"]  # Counter names are wrapped into two lines.


def test_pve_rejects_wrong_game_or_side_observation():
    for change in ({"game_id": "wrong"}, {"side": Side.AXIS}):
        source = observation(Side.ALLIES, []).model_copy(update=change)
        with pytest.raises(ValueError, match="不匹配"):
            pve_public_observation(Engine({Side.ALLIES: source}), state(), Side.ALLIES)


def test_pvp_still_uses_strict_intersection_and_explains_empty_map(monkeypatch):
    engine = Engine({Side.ALLIES: observation(Side.ALLIES, [ship("own-allies")]),
                     Side.AXIS: observation(Side.AXIS, [ship("own-axis", Side.AXIS)])})
    assert public_observation(engine, state()).ships == []
    texts = []
    text = ImageDraw.ImageDraw.text

    def capture_text(self, xy, value, *args, **kwargs):
        texts.append(value)
        return text(self, xy, value, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", capture_text)
    raw = public_png(engine, state())
    assert raw.startswith(b"\x89PNG\r\n\x1a\n")
    assert "尚无双方共同可见舰船，请私聊查看本方态势" in texts
    assert engine.calls == [Side.AXIS, Side.ALLIES, Side.AXIS, Side.ALLIES]


@pytest.mark.parametrize("formation", [False, True])
@pytest.mark.parametrize("side", list(Side))
def test_real_engine_both_modes_keep_human_ships_and_no_hidden_enemy(formation, side):
    engine = IronBottomEngine()
    game = engine.reset("IBS-S-03", 1, GameOptions(
        realistic_command=formation, ruleset_version="night-v2", night_recognition=True,
        optional_rules=OptionalRules(hidden_damage=True),
    ))
    # Place one actual enemy outside the human optical/radar range. This checks
    # absence of an unseen world unit, not merely alias-vs-world ID differences.
    hidden_enemy = next(s for s in game.ships.values() if s.side != side and s.position)
    hidden_enemy.position = HexCoord(q=0, r=38)
    observed = engine.observe(game.game_id, side)
    view = pve_public_observation(engine, game, side)
    own_ids = {s.id for s in observed.ships if s.side == side and s.position is not None}
    assert own_ids and own_ids <= {s.id for s in view.ships}
    assert {s.id for s in view.ships} <= {s.id for s in observed.ships}
    hidden_ids = set(game.ships) - {s.id for s in observed.ships}
    assert hidden_ids and not hidden_ids.intersection(s.id for s in view.ships)
    assert not any(s.position == hidden_enemy.position for s in observed.ships)
    assert not any(s.position == hidden_enemy.position or s.id == hidden_enemy.id
                   or s.name == hidden_enemy.name for s in view.ships)
    assert view.recent_events == view.formations == []
    with Image.open(BytesIO(pve_public_png(engine, game, side))) as image:
        assert image.format == "PNG" and image.width > 1000
        image.verify()
