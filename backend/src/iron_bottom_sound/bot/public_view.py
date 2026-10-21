"""Conservative intersection of both player observations for group chat."""
from __future__ import annotations

from io import BytesIO
import json
from types import SimpleNamespace

from PIL import ImageDraw

from .. import battle_report
from ..models import PlayerObservation, PublicShip, Side


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


def public_png(engine, state) -> bytes:
    """Use the established renderer with only public observation and terrain."""
    view = public_observation(engine, state)

    class PublicEngine:
        def observe(self, game_id, side):
            if game_id != view.game_id:
                raise ValueError("公共观察对局不匹配")
            return view.model_copy(deep=True)

    public_state = SimpleNamespace(
        game_id=view.game_id, scenario_title=view.scenario_title,
        map_columns=view.map_columns, map_rows=view.map_rows,
        land_hexes=tuple(state.land_hexes), coast_hexes=tuple(state.coast_hexes),
    )
    image = battle_report.render_map_image(public_state, PublicEngine(), Side.AXIS, ship_names=True)
    # The player renderer normally labels a side. Replace that title on this new
    # generated game image so recipients cannot mistake it for an axis seat view.
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, image.width, 38), fill=battle_report.OCEAN)
    draw.text((battle_report.ORIGIN_X, 20), f"{view.scenario_title} · 双方共同公开视角",
              fill=battle_report.TEXT_COLOR, font=battle_report._cjk_font(16), anchor="lm")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
