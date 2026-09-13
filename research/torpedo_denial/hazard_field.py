"""B10 formalization: torpedoes as a DELAYED STATEFUL threat field.

Guns are an instantaneous field: threat exists only while the firing solution
is being executed, and nothing physical persists after the impulse of fire.
Torpedoes are different: a launch is a COMMITMENT that creates a persistent
spatio-temporal entity which (i) was created in the past, (ii) occupies
well-defined hexes at well-defined future (turn, impulse) pulses, and
(iii) expires deterministically (range spent / grounding / map edge).

This module makes that state explicit:

    z_t = (s_t, q_t)

    s_t  the world snapshot at decision time t (the engine GameState the
         measurement starts from; read-only),
    q_t  the set of live torpedo tracks already in the water: for each track
         its launch time/position/heading, speed cycle, remaining range, the
         FULL future position-by-pulse map (turn, impulse) -> hex, and its
         expiration pulse `removed_at`.

From q_t we build the spatio-temporal hazard field

    H(x, t) = 1 - prod_k (1 - p_k(x, t))

over (hex, turn, impulse) cells, where p_k(x, t) is the engine's own
`torpedo_hit_probability` evaluated at track k's contact geometry IF track k
occupies hex x at pulse t (and 0 otherwise).  Because hit probability depends
on the target's aspect and speed, the field uses a documented REFERENCE
TARGET convention: broadside aspect (worst case for the target) and the
reference target's nominal speed.  The field is therefore a property of the
threat state alone (ship-independent), while route-level hazards used by
B11/B12 continue to use the exact per-plan aspect via `first_contact`.

All rule quantities come from engine functions; nothing here modifies the
engine or any GameState.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import GameState, HexCoord, ShipState

from research.torpedo_denial.lane import Lane


@dataclass(frozen=True)
class TrackState:
    """One torpedo salvo's persistent state inside q_t.

    `position_by_pulse` / `distance_by_pulse` are the track's full future
    trajectory by (turn, impulse) pulse, analytically identical to the
    engine's impulse loop (verified against engine traversed_hexes in E04).
    `removed_at` is the first pulse at which the track no longer exists.
    """

    track_id: str
    attacker_id: str
    launcher_id: str
    lane_key: tuple
    launch_turn: int
    launch_impulse: int
    launch_hex: HexCoord
    torpedo_heading: int
    speed_cycle: tuple[int, ...]
    range: int
    salvo_count: int
    position_by_pulse: dict[tuple[int, int], HexCoord]
    distance_by_pulse: dict[tuple[int, int], int]
    removed_at: tuple[int, int] | None

    @classmethod
    def from_lane(
        cls, lane: Lane, track_id: str, attacker_id: str, launcher_id: str,
        lane_key: tuple, launch_turn: int, salvo_count: int,
        speed_cycle: tuple[int, ...], rng: int,
    ) -> "TrackState":
        return cls(
            track_id=track_id, attacker_id=attacker_id, launcher_id=launcher_id,
            lane_key=lane_key, launch_turn=launch_turn,
            launch_impulse=min(key[1] for key in lane.positions),
            launch_hex=lane.path[0], torpedo_heading=lane.torpedo_heading,
            speed_cycle=tuple(speed_cycle), range=int(rng), salvo_count=int(salvo_count),
            position_by_pulse=dict(lane.positions), distance_by_pulse=dict(lane.distances),
            removed_at=lane.removed_at,
        )

    # -- state queries -------------------------------------------------------
    def pulses(self) -> list[tuple[int, int]]:
        return sorted(self.position_by_pulse)

    def is_live(self, turn: int, impulse: int) -> bool:
        """Live at the START of pulse (turn, impulse): launched, not expired."""
        if (turn, impulse) < (self.launch_turn, self.launch_impulse):
            return False
        if self.removed_at is not None and (turn, impulse) >= self.removed_at:
            return False
        return True

    def hex_at(self, turn: int, impulse: int) -> HexCoord | None:
        if not self.is_live(turn, impulse):
            return None
        return self.position_by_pulse.get((turn, impulse))

    def lifetime_pulses(self) -> int:
        return len(self.position_by_pulse)


@dataclass
class DelayedTorpedoState:
    """z_t = (s_t, q_t): decision-time world snapshot plus live-track set."""

    decision_turn: int
    tracks: list[TrackState] = field(default_factory=list)

    def live_tracks(self, turn: int, impulse: int) -> list[TrackState]:
        return [track for track in self.tracks if track.is_live(turn, impulse)]

    def pulses(self) -> list[tuple[int, int]]:
        keys: set[tuple[int, int]] = set()
        for track in self.tracks:
            keys.update(track.position_by_pulse)
        return sorted(keys)


class HazardField:
    """Spatio-temporal threat field H(x, t) built from q_t.

    grid maps (turn, impulse) -> {hex.label: (hazard, [track ids])} where
    hazard = 1 - prod(1 - p_k) over tracks occupying the hex at that pulse.
    """

    def __init__(
        self, engine: IronBottomEngine, state: GameState,
        ref_target: ShipState, tracks: list[TrackState],
    ):
        self.tracks = tracks
        self.grid: dict[tuple[int, int], dict[str, tuple[float, list[str]]]] = {}
        self.p_hit_by_track: dict[str, dict[tuple[int, int], float]] = {}
        for track in tracks:
            attacker = state.ships[track.attacker_id]
            pulse_p: dict[tuple[int, int], float] = {}
            for pulse, hex_coord in track.position_by_pulse.items():
                distance = max(1, track.distance_by_pulse[pulse])
                # Reference-target convention: broadside aspect (worst case for
                # the target), reference target nominal speed; modifier from the
                # ENGINE's own range/speed/roll tables.
                try:
                    modifier = engine._torpedo_modifier(state, attacker, ref_target, distance)
                except TypeError:  # legacy engine API
                    modifier = engine._torpedo_modifier(attacker, ref_target, distance)
                p_hit = engine.torpedo_hit_probability("broadside", modifier)
                pulse_p[pulse] = p_hit
                cell = self.grid.setdefault(pulse, {})
                hazard, track_ids = cell.get(hex_coord.label, (0.0, []))
                combined = 1.0 - (1.0 - hazard) * (1.0 - p_hit)
                cell[hex_coord.label] = (combined, track_ids + [track.track_id])
            self.p_hit_by_track[track.track_id] = pulse_p

    # -- field queries -------------------------------------------------------
    def pulses(self) -> list[tuple[int, int]]:
        return sorted(self.grid)

    def hazard(self, hex_label: str, turn: int, impulse: int) -> float:
        entry = self.grid.get((turn, impulse), {}).get(hex_label)
        return entry[0] if entry else 0.0

    def hot_cells(self, turn: int, impulse: int) -> dict[str, float]:
        return {label: value for label, (value, _) in self.grid.get((turn, impulse), {}).items()}

    def threat_mass(self, turn: int | None = None, impulse: int | None = None) -> float:
        """Sum of H over cells at one pulse, or over the whole field."""
        if turn is not None:
            return sum(value for value, _ in self.grid.get((turn, impulse), {}).values()) \
                if impulse is not None else \
                sum(value for cell in
                    (self.grid.get((turn, i), {}) for i in self.impulses_of_turn(turn))
                    for value, _ in cell.values())
        return sum(value for cell in self.grid.values() for value, _ in cell.values())

    def impulses_of_turn(self, turn: int) -> list[int]:
        return sorted({key[1] for key in self.grid if key[0] == turn})

    def hot_hex_labels(self) -> set[str]:
        return {label for cell in self.grid.values() for label in cell}

    def hex_time_series(self, hex_label: str) -> dict[tuple[int, int], float]:
        return {
            pulse: self.hazard(hex_label, pulse[0], pulse[1])
            for pulse in self.pulses()
            if self.hazard(hex_label, pulse[0], pulse[1]) > 0.0
        }

    # -- aggregate descriptors ----------------------------------------------
    def summary(self) -> dict:
        per_pulse = {
            pulse: {"hot_cells": len(self.hot_cells(*pulse)),
                    "threat_mass": self.threat_mass(*pulse)}
            for pulse in self.pulses()
        }
        hot = self.hot_hex_labels()
        lifetimes = [track.lifetime_pulses() for track in self.tracks]
        total_mass = self.threat_mass()
        future_mass = sum(
            value for pulse, cell in self.grid.items()
            if pulse[0] > self.tracks[0].launch_turn
            for value, _ in cell.values()
        ) if self.tracks else 0.0
        return {
            "n_tracks": len(self.tracks),
            "n_pulses": len(self.pulses()),
            "n_hot_hexes_total": len(hot),
            "n_hot_cells": sum(len(cell) for cell in self.grid.values()),
            "threat_mass_total": total_mass,
            "threat_mass_by_turn": {
                str(turn): sum(
                    cell_stats["threat_mass"]
                    for pulse, cell_stats in per_pulse.items()
                    if pulse[0] == turn
                )
                for turn in sorted({pulse[0] for pulse in self.pulses()})
            },
            "mean_track_lifetime_pulses": (sum(lifetimes) / len(lifetimes)) if lifetimes else 0.0,
            "max_track_lifetime_pulses": max(lifetimes, default=0),
            "tracks_outliving_launch_turn": sum(
                1 for track in self.tracks
                if track.removed_at is None or track.removed_at[0] > track.launch_turn
            ),
        }


def build_delayed_state(
    engine: IronBottomEngine, state: GameState,
    lanes: list[tuple[str, str, str, tuple, Lane, int, tuple[int, ...], int]],
    decision_turn: int,
) -> DelayedTorpedoState:
    """Wrap already-built lanes into explicit track states.

    Each item: (track_id, attacker_id, launcher_id, lane_key, lane,
    salvo_count, speed_cycle, range).
    """
    tracks = [
        TrackState.from_lane(lane, track_id, attacker_id, launcher_id,
                             lane_key, decision_turn, salvo_count, cycle, rng)
        for track_id, attacker_id, launcher_id, lane_key, lane, salvo_count, cycle, rng in lanes
    ]
    return DelayedTorpedoState(decision_turn=decision_turn, tracks=tracks)
