"""Read-only snapshot extraction from the Iron Bottom Sound engine.

`extract_snapshot` builds a `ResearchSnapshot` purely from public engine
interfaces (`engine.observe`).  It is the single data source for every paper
experiment so that E00 (audit) can verify: no hidden-information leakage and
no state mutation.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import GameState, Side


@dataclass
class ShipSnapshot:
    ship_id: str
    name: str
    side: str
    ship_type: str
    q: int | None
    r: int | None
    heading: int
    speed: int
    hull_fraction: float | None  # None = hidden (fog of war)
    vp: float
    radar: bool
    sunk: bool
    gun_mounts: list[dict[str, Any]] = field(default_factory=list)
    torpedo_launchers: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ResearchSnapshot:
    turn: int
    phase: str
    scenario_id: str
    seed: int
    observer_side: str
    ships: list[ShipSnapshot] = field(default_factory=list)
    torpedo_tracks: list[dict[str, Any]] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(dataclasses.asdict(self), ensure_ascii=False, sort_keys=True)

    def hash(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()[:16]


def _side_str(side: Any) -> str:
    return side.value if isinstance(side, Side) else str(side)


def extract_snapshot(engine: IronBottomEngine, game_id: str, side: Side) -> ResearchSnapshot:
    """Build a research snapshot from the point of view of `side` (fog-respecting)."""
    state: GameState = engine.get(game_id)
    obs = engine.observe(game_id, side)

    ships: list[ShipSnapshot] = []
    for ps in obs.ships:
        hull_fraction = (
            (ps.hull / ps.max_hull) if ps.hull is not None and ps.max_hull else None
        )
        ships.append(
            ShipSnapshot(
                ship_id=ps.id,
                name=ps.name,
                side=_side_str(ps.side),
                ship_type=ps.ship_type,
                q=ps.position.q if ps.position is not None else None,
                r=ps.position.r if ps.position is not None else None,
                heading=ps.heading,
                speed=ps.current_speed,
                hull_fraction=hull_fraction,
                vp=float(ps.vp or 0),
                radar=bool(ps.radar) if hasattr(ps, "radar") else False,
                sunk=bool(ps.sunk),
                gun_mounts=[
                    {"id": m.id, "kind": m.kind, "position": m.position,
                     "arcs": [a.value for a in m.arcs], "firepower": m.firepower,
                     "destroyed": m.destroyed}
                    for m in (ps.gun_mounts or [])
                ],
                torpedo_launchers=[
                    {"id": t.id, "arcs": [a.value for a in t.arcs],
                     "torpedoes": t.torpedoes, "destroyed": t.destroyed}
                    for t in (ps.torpedo_launchers or [])
                ],
            )
        )

    tracks = []
    for t in getattr(obs, "torpedo_tracks", None) or []:
        pos = getattr(t, "position", None)
        tracks.append(
            {
                "q": pos.q if pos else None,
                "r": pos.r if pos else None,
                "heading": t.heading,
                "launch_side": t.launch_side,
                "salvo_size": t.salvo_size,
                "hidden": bool(getattr(t, "hidden", False)),
            }
        )

    return ResearchSnapshot(
        turn=state.turn,
        phase=state.phase.value if hasattr(state.phase, "value") else str(state.phase),
        scenario_id=state.scenario_id,
        seed=state.seed,
        observer_side=_side_str(side),
        ships=ships,
        torpedo_tracks=tracks,
    )
