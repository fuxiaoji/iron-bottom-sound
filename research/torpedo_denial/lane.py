"""Analytic torpedo-lane timeline, mirroring the engine's impulse-loop semantics.

The engine (`_resolve_movement` + `_check_torpedo_contacts`) advances ships one
hex per impulse, then launches any torpedo whose `launch_at_mf` matches the
impulse, then moves surviving tracks (within their per-turn allowance), then
marks a contact whenever an opposing ship and a track share a hex.  Tracks keep
crossing turns with allowance `speed_cycle[(turn - launched_turn) % 3]` until
range is spent, they ground, or they contact; a spent track is removed after the
impulse in which its range reached zero (it can still be contacted on that very
impulse).

`build_lane` reproduces that (turn, impulse) -> hex map analytically, without
adjudicating anything.  `first_contact` scans it against a ship timeline and
evaluates aspect/modifier/hit-probability with the ENGINE's own functions
(`_torpedo_track_aspect` logic, `_torpedo_modifier`, `torpedo_hit_probability`,
`expected_torpedo_hits`) at the contact geometry.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import GameState, HexCoord, ShipState


@dataclass
class Lane:
    """Deterministic spatio-temporal projection of one torpedo launch."""

    torpedo_heading: int
    anchor: HexCoord
    positions: dict[tuple[int, int], HexCoord] = field(default_factory=dict)  # (turn, impulse) -> hex
    distances: dict[tuple[int, int], int] = field(default_factory=dict)       # distance travelled by then
    removed_at: tuple[int, int] | None = None   # (turn, impulse) after which the track no longer exists
    path: list[HexCoord] = field(default_factory=list)

    def position_at(self, turn: int, impulse: int) -> HexCoord | None:
        if self.removed_at is not None and (turn, impulse) >= self.removed_at:
            return None
        hit = self.positions.get((turn, impulse))
        if hit is not None:
            return hit
        # Stationary hold within a turn: after the track has entered turn `turn`
        # and not moved this impulse, it stays at the last position of that turn
        # (engine checks contacts every impulse so ships can drive into it).
        turn_keys = [key for key in self.positions if key[0] == turn]
        if not turn_keys:
            return None
        first_impulse = min(key[1] for key in turn_keys)
        if impulse < first_impulse:
            return None
        earlier = [key for key in turn_keys if key[1] <= impulse]
        if not earlier:
            return None
        return self.positions[max(earlier)]

    def last_impulse(self, turn: int) -> int:
        keys = [key[1] for key in self.positions if key[0] == turn]
        return max(keys) if keys else 0

    def turns(self) -> list[int]:
        return sorted({key[0] for key in self.positions})


def build_lane(
    engine: IronBottomEngine, state: GameState, attacker: ShipState,
    launch_hex: HexCoord, ship_heading: int, launch_side: str, launch_angle: str,
    setting_index: int, launch_at_mf: int, horizon_turn: int = 8,
    launched_turn: int = 2,
) -> Lane:
    """Project one launch (engine semantics; launched on `launched_turn`).

    Same-turn protocol (E04 primary): the launch happens during the target's
    response turn, so first-turn allowance is `cycle[0] - launch_at_mf` and
    later turns use `cycle[(t - launched_turn) % 3]`, exactly mirroring the
    engine's `track_allowance` formula.
    """
    torpedo_type = attacker.torpedo_type or ""
    setting = engine.rules.torpedoes[torpedo_type]["settings"][setting_index]
    cycle = [int(value) for value in setting["speed"]]
    torpedo_heading = engine._torpedo_launch_heading(ship_heading, launch_side, launch_angle)
    anchor = engine._torpedo_anchor_hex(
        launch_hex, ship_heading, launch_angle,
        columns=state.map_columns, rows=state.map_rows,
    )
    lane = Lane(torpedo_heading=torpedo_heading, anchor=anchor)
    position = anchor
    travelled = 0
    range_remaining = int(setting["range"])
    lane.positions[(launched_turn, launch_at_mf)] = position
    lane.distances[(launched_turn, launch_at_mf)] = 0
    lane.path.append(position)

    def advance() -> HexCoord | None:
        try:
            nxt = position.neighbor(torpedo_heading, columns=state.map_columns, rows=state.map_rows)
        except ValueError:
            return None
        if engine._terrain_impassable(state, nxt):
            return None
        return nxt

    # Launch turn: allowance = cycle[0] - MF already spent by the launcher.
    # `removed_at` marks the first (turn, impulse) at which the track no longer
    # exists.  The engine checks contacts BEFORE pruning a spent track, so a
    # track is still contactable on the impulse its range reaches zero; removal
    # therefore takes effect from the NEXT impulse.
    allowance = max(0, cycle[0] - launch_at_mf)
    impulse = launch_at_mf
    for _ in range(allowance):
        if range_remaining <= 0:
            break
        impulse += 1
        nxt = advance()
        if nxt is None:
            lane.positions[(launched_turn, impulse)] = position
            lane.distances[(launched_turn, impulse)] = travelled
            lane.removed_at = (launched_turn, impulse + 1)
            break
        position = nxt
        travelled += 1
        range_remaining -= 1
        lane.positions[(launched_turn, impulse)] = position
        lane.distances[(launched_turn, impulse)] = travelled
        lane.path.append(position)
    # Later turns: allowance = cycle[(turn - launched_turn) % 3].
    turn = launched_turn
    while range_remaining > 0 and lane.removed_at is None and turn < horizon_turn:
        turn += 1
        allowance = cycle[(turn - launched_turn) % 3]
        for step in range(allowance):
            if range_remaining <= 0:
                break
            impulse = step + 1
            nxt = advance()
            if nxt is None:
                lane.positions[(turn, impulse)] = position
                lane.distances[(turn, impulse)] = travelled
                lane.removed_at = (turn, impulse + 1)
                break
            position = nxt
            travelled += 1
            range_remaining -= 1
            lane.positions[(turn, impulse)] = position
            lane.distances[(turn, impulse)] = travelled
            lane.path.append(position)
        if range_remaining <= 0 and lane.removed_at is None:
            lane.removed_at = (turn, lane.last_impulse(turn) + 1)
    return lane


@dataclass(frozen=True)
class Contact:
    turn: int
    impulse: int
    hex: HexCoord
    lane_distance: int
    ship_heading: int
    ship_speed: int
    aspect: str
    modifier: int
    hit_probability: float
    expected_hits: float


def evaluate_contact(
    engine: IronBottomEngine, state: GameState, attacker: ShipState, target: ShipState,
    lane: Lane, turn: int, impulse: int, ship_heading: int, ship_speed: int,
    salvo_size: int,
) -> Contact:
    """Aspect/modifier/hit probability at a contact, via engine functions only."""
    distance = max(1, lane.distances[(turn, impulse)])
    # Mirror engine `_torpedo_track_aspect` (track bearing = torpedo heading).
    source_bearing = ((lane.torpedo_heading + 2) % 6) + 1
    relative = (source_bearing - ship_heading) % 6
    aspect = "bow_stern" if relative in {0, 3} else "broadside"
    shim = target.model_copy(update={"current_speed": int(ship_speed)})
    try:
        # Current engine API: _torpedo_modifier(state, attacker, target, distance).
        modifier = engine._torpedo_modifier(state, attacker, shim, distance)
    except TypeError:
        # Legacy engine API (pre state argument).
        modifier = engine._torpedo_modifier(attacker, shim, distance)
    return Contact(
        turn=turn, impulse=impulse, hex=lane.positions[(turn, impulse)],
        lane_distance=distance, ship_heading=ship_heading, ship_speed=int(ship_speed),
        aspect=aspect, modifier=modifier,
        hit_probability=engine.torpedo_hit_probability(aspect, modifier),
        expected_hits=engine.expected_torpedo_hits(aspect, modifier, salvo_size),
    )


def first_contact(
    engine: IronBottomEngine, state: GameState, attacker: ShipState, target: ShipState,
    lane: Lane, ship_timeline: dict[tuple[int, int], tuple[HexCoord, int]],
    ship_speed_by_turn: dict[int, int], salvo_size: int, min_turn: int = 1,
) -> Contact | None:
    """First spatio-temporal overlap between the lane and a ship timeline."""
    for turn in lane.turns():
        if turn < min_turn:
            continue
        last = lane.last_impulse(turn)
        ship_len = max(
            (impulse for (t, impulse) in ship_timeline if t == turn),
            default=0,
        )
        for impulse in range(1, max(last, ship_len) + 1):
            lane_hex = lane.position_at(turn, impulse)
            if lane_hex is None:
                break  # track removed: no further contact possible
            entry = ship_timeline.get((turn, impulse))
            if entry is None:
                continue
            ship_hex, ship_heading = entry
            if ship_hex == lane_hex:
                return evaluate_contact(
                    engine, state, attacker, target, lane, turn, impulse,
                    ship_heading, ship_speed_by_turn[turn], salvo_size,
                )
    return None


def build_ship_timeline(
    engine: IronBottomEngine, state: GameState, trajectory, end_hex: HexCoord,
    end_heading: int, cost: int, start_turn: int, horizon_turn: int,
) -> tuple[dict[tuple[int, int], tuple[HexCoord, int]], dict[int, int]]:
    """(turn, impulse) -> (hex, heading) for one decision turn plus a
    hold-course continuation (same end heading / speed) up to `horizon_turn`.

    Mirrors the engine's per-impulse semantics: positions are the plan timeline
    while entries remain, then the ship holds its endpoint.  Continuation turns
    assume the committed course and speed (decision documented in E04 report).
    """
    timeline: dict[tuple[int, int], tuple[HexCoord, int]] = {}
    speed_by_turn: dict[int, int] = {start_turn: int(cost)}
    length = len(trajectory)
    for impulse in range(1, length + 1):
        timeline[(start_turn, impulse)] = trajectory[impulse - 1]
    timeline[(start_turn, length + 1)] = (end_hex, end_heading)  # held endpoint
    position, heading = end_hex, end_heading
    for turn in range(start_turn + 1, horizon_turn + 1):
        speed_by_turn[turn] = int(cost)
        for impulse in range(1, int(cost) + 1):
            try:
                nxt = position.neighbor(heading, columns=state.map_columns, rows=state.map_rows)
            except ValueError:
                nxt = None
            if nxt is not None and not engine._terrain_impassable(state, nxt):
                position = nxt
            # Record even when blocked: the ship still occupies its hex this impulse.
            timeline[(turn, impulse)] = (position, heading)
        timeline[(turn, int(cost) + 1)] = (position, heading)
    return timeline, speed_by_turn
