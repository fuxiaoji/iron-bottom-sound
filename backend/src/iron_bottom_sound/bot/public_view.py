"""Bounded group maps: PVP intersection or the seated PVE human's view."""
from __future__ import annotations

from io import BytesIO
import json
from types import SimpleNamespace

from PIL import ImageDraw

from .. import battle_report
from ..models import MarkerState, PlayerObservation, PublicShip, Side, TorpedoTrack, WreckState


def _key(value) -> str:
    return json.dumps(value.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)


def _intersection(left, right):
    right_keys = {_key(item) for item in right}
    return [item.model_copy(deep=True) for item in left if _key(item) in right_keys]


def public_observation(engine, state) -> PlayerObservation:
    """Publish only independently matching facts, without consulting hidden ships.

    Side-specific recognition aliases deliberately do not get resolved against
    world truth. If their IDs differ, the unit is absent from the public view.
    """
    axis = engine.observe(state.game_id, Side.AXIS)
    allies = engine.observe(state.game_id, Side.ALLIES)
    metadata = ("game_id", "scenario_id", "scenario_title", "turn", "max_turns", "phase",
                "map_columns", "map_rows", "printed_columns", "printed_rows", "ruleset_version")
    if any(getattr(axis, key) != getattr(allies, key) for key in metadata):
        raise ValueError("双方观察不属于同一公开阶段")
    other = {ship.id: ship for ship in allies.ships}
    ships = []
    # These rendered facts must agree; private damage/capability fields are never copied.
    shown = ("id", "position", "heading", "name", "side", "ship_type", "current_speed",
             "fire_markers", "fired", "sunk")
    for ship in axis.ships:
        peer = other.get(ship.id)
        if peer is None or not ship.identified or not peer.identified or ship.position is None:
            continue
        if any(getattr(ship, field) != getattr(peer, field) for field in shown):
            continue
        # Explicit construction prevents new engine/model fields from leaking.
        ships.append(PublicShip(
            **{field: getattr(peer, field) for field in shown}, identified=True,
            hull=None, max_hull=None, asset=peer.asset if peer.asset == ship.asset else None,
            primary_armor=None, secondary_armor=None, belt_armor=None, bridge_armor=None,
        ))
    private_events = ("command_delay_", "command_message_", "formation_agent_", "mission_order")
    events = [event for event in _intersection(axis.recent_events, allies.recent_events)
              if event.type not in {"orders_submitted", "game_created"}
              and not event.type.startswith(private_events)
              and not event.payload.get("secret_side") and not event.payload.get("debug_only")]
    markers = [marker for marker in _intersection(axis.markers, allies.markers)
               if marker.secret_side is None and marker.contact_truth is None]
    return PlayerObservation(
        **{key: getattr(axis, key) for key in metadata}, side=Side.AXIS,
        visibility=min(axis.visibility, allies.visibility), ships=ships,
        realistic_command=axis.realistic_command and allies.realistic_command,
        command_delay_mode=axis.command_delay_mode and allies.command_delay_mode,
        torpedo_tracks=_intersection(axis.torpedo_tracks, allies.torpedo_tracks),
        wrecks=_intersection(axis.wrecks, allies.wrecks), markers=markers, formations=[],
        score=dict(axis.score) if axis.score == allies.score else {}, recent_events=events,
        winner=axis.winner if axis.winner == allies.winner else None,
        victory_reason=axis.victory_reason if axis.victory_reason == allies.victory_reason else None,
        enabled_optional_rules=[r for r in axis.enabled_optional_rules if r in allies.enabled_optional_rules],
    )


def pve_public_observation(engine, state, side: Side) -> PlayerObservation:
    """Map-only projection of the PVE human seat's already restricted observation.

    The service must derive ``side`` from the unique non-bot seat, never from a
    group request. Do not resolve contact aliases against world ships, even for
    labels. Orders, formations, events and marker truth have no map purpose.
    """
    side = Side(side)
    source = engine.observe(state.game_id, side)
    if source.game_id != state.game_id or source.side != side:
        raise ValueError("PVE玩家观察对局或阵营不匹配")
    metadata = ("game_id", "scenario_id", "scenario_title", "turn", "max_turns", "phase",
                "map_columns", "map_rows", "printed_columns", "printed_rows", "ruleset_version")
    shown = ("id", "position", "heading", "side", "current_speed", "fire_markers", "fired", "sunk")
    ships = [PublicShip(
        **{field: getattr(ship, field) for field in shown}, identified=ship.identified,
        name=ship.name if ship.identified else "敌舰",
        ship_type=ship.ship_type if ship.identified else "unknown",
        asset=ship.asset if ship.identified else None,
        hull=None, max_hull=None, primary_armor=None, secondary_armor=None,
        belt_armor=None, bridge_armor=None,
    ) for ship in source.ships if ship.position is not None]
    # Markers in observe() may include discovered contacts whose secret_side and
    # contact_truth still describe the deployment. Retain only the visible glyph.
    markers = [MarkerState(
        id=f"map-marker-{index}", kind=marker.kind,
        position=marker.position, heading=marker.heading,
    ) for index, marker in enumerate(source.markers) if marker.position is not None]
    tracks = [TorpedoTrack(
        id=f"map-torpedo-{index}", side=track.side, launcher_ship_id="",
        torpedo_type="", position=track.position, heading=track.heading,
        speed_cycle=track.speed_cycle, range_remaining=track.range_remaining,
        distance_travelled=track.distance_travelled, launched_turn=track.launched_turn,
        salvo_size=track.salvo_size,
    ) for index, track in enumerate(source.torpedo_tracks)]
    wrecks = [WreckState(id=f"map-wreck-{index}", position=wreck.position, source_ship_id="")
              for index, wreck in enumerate(source.wrecks)]
    return PlayerObservation(
        **{key: getattr(source, key) for key in metadata}, side=side,
        visibility=source.visibility, realistic_command=source.realistic_command,
        command_delay_mode=source.command_delay_mode, ships=ships, markers=markers,
        torpedo_tracks=tracks, wrecks=wrecks, formations=[], recent_events=[],
        score={key.value: source.score[key.value] for key in Side if key.value in source.score},
        winner=source.winner, victory_reason=None,
    ).model_copy(deep=True)


def _map_png(view, state, side, title, empty_hint=None) -> bytes:
    """Render an isolated observation with only immutable source terrain labels."""

    class PublicEngine:
        def observe(self, game_id, side):
            if game_id != view.game_id or side != view.side:
                raise ValueError("群图观察对局或阵营不匹配")
            return view.model_copy(deep=True)

    public_state = SimpleNamespace(
        game_id=view.game_id, scenario_title=view.scenario_title,
        map_columns=view.map_columns, map_rows=view.map_rows,
        land_hexes=tuple(state.land_hexes), coast_hexes=tuple(state.coast_hexes),
    )
    image = battle_report.render_map_image(public_state, PublicEngine(), side, ship_names=True)
    # The player renderer normally labels a side. Replace that title on this new
    # generated game image so recipients cannot mistake it for an axis seat view.
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, image.width, 38), fill=battle_report.OCEAN)
    draw.text((battle_report.ORIGIN_X, 20), f"{view.scenario_title} · {title}",
              fill=battle_report.TEXT_COLOR, font=battle_report._cjk_font(16), anchor="lm")
    if empty_hint and not view.ships:
        draw.text((battle_report.ORIGIN_X, image.height - 24), empty_hint,
                  fill=battle_report.TEXT_COLOR, font=battle_report._cjk_font(16), anchor="lm")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def public_png(engine, state) -> bytes:
    """PVP keeps the strict intersection even when that leaves an empty board."""
    return _map_png(public_observation(engine, state), state, Side.AXIS, "双方共同公开视角",
                    "尚无双方共同可见舰船，请私聊查看本方态势")


def pve_public_png(engine, state, side: Side) -> bytes:
    """PVE group map for the service-selected human seat, with observed names."""
    view = pve_public_observation(engine, state, side)
    label = "盟军" if view.side == Side.ALLIES else "日军"
    return _map_png(view, state, view.side, f"PVE玩家视角·{label}")
