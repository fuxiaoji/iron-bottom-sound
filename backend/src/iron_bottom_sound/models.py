from __future__ import annotations

import re
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class Side(StrEnum):
    AXIS = "axis"
    ALLIES = "allies"

    @property
    def opponent(self) -> "Side":
        return Side.ALLIES if self == Side.AXIS else Side.AXIS


class Phase(StrEnum):
    REINFORCEMENT = "reinforcement"
    MOVEMENT_PLANNING = "movement_planning"
    TORPEDO_PLANNING = "torpedo_planning"
    MOVEMENT_RESOLUTION = "movement_resolution"
    GUNNERY = "gunnery"
    TORPEDO_EFFECTS = "torpedo_effects"
    FIRE_END = "fire_end"
    COMPLETE = "complete"


class FiringArc(StrEnum):
    BOW = "bow"
    PORT = "port"
    STARBOARD = "starboard"
    STERN = "stern"


class MountPosition(StrEnum):
    BOW = "bow"
    MIDSHIPS = "midships"
    PORT = "port"
    STARBOARD = "starboard"
    STERN = "stern"


def column_to_index(label: str) -> int:
    normalized = label.upper()
    if len(normalized) == 1 and "A" <= normalized <= "Z":
        return ord(normalized) - 65
    if len(normalized) == 2 and normalized[0] == normalized[1] and "A" <= normalized[0] <= "H":
        return 26 + ord(normalized[0]) - 65
    raise ValueError(f"Invalid map column {label!r}; expected A-Z or AA-HH")


def index_to_column(index: int) -> str:
    if 0 <= index <= 25:
        return chr(65 + index)
    if 26 <= index <= 33:
        character = chr(65 + index - 26)
        return character * 2
    raise ValueError("Map column index must be 0 through 33")


class HexCoord(BaseModel, frozen=True):
    q: int = Field(ge=0, le=33)
    r: int = Field(ge=-40, le=40)

    @classmethod
    def from_label(cls, label: str) -> "HexCoord":
        match = re.fullmatch(r"([A-Za-z]{1,2})(\d{1,2})", label.strip())
        if not match:
            raise ValueError(f"Invalid hex label {label!r}")
        column = column_to_index(match.group(1))
        display_row = int(match.group(2)) - 1
        axial_row = display_row - (column - (column & 1)) // 2
        return cls(q=column, r=axial_row)

    @property
    def label(self) -> str:
        display_row = self.r + (self.q - (self.q & 1)) // 2
        return f"{index_to_column(self.q)}{display_row + 1}"

    def neighbor(self, heading: int) -> "HexCoord":
        directions = {1: (0, -1), 2: (1, -1), 3: (1, 0), 4: (0, 1), 5: (-1, 1), 6: (-1, 0)}
        if heading not in directions:
            raise ValueError("Heading must be 1 through 6")
        dq, dr = directions[heading]
        candidate = HexCoord(q=self.q + dq, r=self.r + dr)
        display_row = candidate.r + (candidate.q - (candidate.q & 1)) // 2
        if not 0 <= display_row <= 26:
            raise ValueError("Movement leaves the map")
        return candidate

    def distance(self, other: "HexCoord") -> int:
        return (abs(self.q - other.q) + abs(self.r - other.r) + abs((-self.q - self.r) - (-other.q - other.r))) // 2


class OptionalRules(BaseModel):
    hidden_contacts: bool = False
    radar: bool = False
    star_shells: bool = False
    searchlights: bool = False
    malfunction_66: bool = False
    squalls: bool = False
    smoke: bool = False
    silhouettes: bool = False
    hidden_damage: bool = False
    blind_torpedoes: bool = False


class GameOptions(BaseModel):
    mode: Literal["hotseat", "llm"] = "hotseat"
    optional_rules: OptionalRules = Field(default_factory=OptionalRules)


class WeaponMount(BaseModel):
    kind: Literal["primary", "secondary", "torpedo"]
    firepower: int = Field(default=0, ge=0)
    caliber: float = Field(default=0, ge=0)
    ammo: int | None = Field(default=None, ge=0)
    destroyed: bool = False


class GunMountRecord(BaseModel):
    id: str
    kind: Literal["primary", "secondary"]
    position: MountPosition
    firepower: int = Field(gt=0)
    caliber: float = Field(gt=0)
    arcs: frozenset[FiringArc]
    armour: float | None = Field(default=None, ge=0)


class GunMountState(GunMountRecord):
    destroyed: bool = False
    fired_this_phase: bool = False


class TorpedoLauncherRecord(BaseModel):
    id: str
    position: MountPosition
    arcs: frozenset[FiringArc]
    torpedoes: int = Field(gt=0)
    reloads: int = Field(default=0, ge=0)


class TorpedoLauncherState(TorpedoLauncherRecord):
    loaded: int = Field(ge=0)
    reloads_remaining: int = Field(ge=0)
    reload_turns_remaining: int = Field(default=0, ge=0)
    destroyed: bool = False


class ArmourRecord(BaseModel):
    primary: float | None = Field(default=None, ge=0)
    secondary: float | None = Field(default=None, ge=0)
    belt: float | None = Field(default=None, ge=0)
    bridge: float | None = Field(default=None, ge=0)


class ShipRecord(BaseModel):
    id: str
    name: str
    ship_type: str
    displacement_band: Literal["A", "B", "C", "D", "E", "F", "G", "H", "I"]
    hull_rows: tuple[int, int, int]
    speed_damage_track: tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]
    guns: tuple[GunMountRecord, ...]
    torpedo_launchers: tuple[TorpedoLauncherRecord, ...] = ()
    torpedo_type: str | None = None
    armour: ArmourRecord = Field(default_factory=ArmourRecord)
    fire_control: bool = True
    radar: bool = False
    aircraft: bool = False
    vp: int = Field(ge=0)
    special_rules: tuple[str, ...] = ()
    source_page: int = Field(gt=0)

    @property
    def hull_boxes(self) -> int:
        return sum(self.hull_rows)

    @property
    def maximum_speed_cycle(self) -> tuple[int, int, int]:
        return tuple(row[0] for row in self.speed_damage_track)

    @field_validator("speed_damage_track")
    @classmethod
    def descending_speed_rows(cls, value: tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]):
        if any(not row or any(left <= right for left, right in zip(row, row[1:])) for row in value):
            raise ValueError("Each speed-damage row must be non-empty and strictly descending")
        return value


class ShipState(BaseModel):
    id: str
    name: str
    side: Side
    ship_type: str
    displacement_band: Literal["A", "B", "C", "D", "E", "F", "G", "H", "I"] = "A"
    position: HexCoord | None
    heading: int = Field(ge=1, le=6)
    speed_track: tuple[int, int, int]
    initial_max_speed: int = Field(gt=0)
    current_speed: int = Field(ge=0)
    previous_speed: int = Field(ge=0)
    hull: int = Field(ge=0)
    max_hull: int = Field(gt=0)
    primary: WeaponMount
    secondary: WeaponMount | None = None
    torpedo: WeaponMount | None = None
    torpedo_type: str | None = None
    belt_armor: float = 0
    primary_armor: float = 0
    secondary_armor: float = 0
    bridge_armor: float = 0
    aircraft: bool = False
    gun_mounts: list[GunMountState] = Field(default_factory=list)
    torpedo_launchers: list[TorpedoLauncherState] = Field(default_factory=list)
    vp: int = 0
    asset: str | None = None
    fire_markers: int = Field(default=0, ge=0)
    mfc_destroyed: bool = False
    radar_destroyed: bool = False
    fired: bool = False
    smoke: bool = False
    sunk: bool = False
    reinforcement_turn: int | None = None

    def max_speed_for_turn(self, turn: int) -> int:
        return self.speed_track[(turn - 1) % 3]


class MovementCommand(BaseModel):
    action: Literal["advance", "turn_port_60", "turn_starboard_60", "turn_port_120", "turn_starboard_120"]


class MovementOrder(BaseModel):
    ship_id: str
    plan: str = "0"
    speed: int | None = Field(default=None, ge=0)
    commands: list[MovementCommand] = Field(default_factory=list)


class ReinforcementOrder(BaseModel):
    ship_id: str
    entry_hex: HexCoord
    heading: int = Field(ge=1, le=6)
    speed: int = Field(ge=0)


class GunMountOrder(BaseModel):
    mount_id: str
    target_id: str


class GunneryOrder(BaseModel):
    ship_id: str
    primary_target: str | None = None
    secondary_target: str | None = None
    searchlight_target: str | None = None
    mounts: list[GunMountOrder] = Field(default_factory=list)


class IlluminationOrder(BaseModel):
    ship_id: str
    target_hex: HexCoord


class SearchlightOrder(BaseModel):
    ship_id: str
    target_id: str | None = None
    active: bool = True


class SmokeOrder(BaseModel):
    ship_id: str
    deploy: bool = True


class TorpedoOrder(BaseModel):
    ship_id: str
    target_id: str | None = None
    count: int = Field(default=1, ge=0, le=9)
    speed: Literal["fast", "medium", "slow"] = "fast"
    launcher_id: str | None = None
    launch_at_mf: int = Field(default=0, ge=0)
    launch_hex: HexCoord | None = None
    bearing: int | None = Field(default=None, ge=1, le=6)
    setting_index: int = Field(default=0, ge=0)


class PhaseConfirmation(BaseModel):
    ready: bool = True


class OrderBatch(BaseModel):
    side: Side
    phase: Phase | None = None
    reinforcements: list[ReinforcementOrder] = Field(default_factory=list)
    movement: list[MovementOrder] = Field(default_factory=list)
    gunnery: list[GunneryOrder] = Field(default_factory=list)
    torpedoes: list[TorpedoOrder] = Field(default_factory=list)
    smoke_ships: list[str] = Field(default_factory=list)
    smoke: list[SmokeOrder] = Field(default_factory=list)
    illumination: list[IlluminationOrder] = Field(default_factory=list)
    searchlights: list[SearchlightOrder] = Field(default_factory=list)
    confirmation: PhaseConfirmation = Field(default_factory=PhaseConfirmation)

    @field_validator("smoke_ships")
    @classmethod
    def unique_smoke_ships(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("Duplicate smoke ship")
        return value


class RuleReference(BaseModel):
    rule_id: str
    document: str
    pdf_page: int | None = None
    section: str | None = None


class DiceRoll(BaseModel):
    dice: list[int]
    notation: str
    raw: int
    adjusted: int | None = None


class GameEvent(BaseModel):
    sequence: int
    turn: int
    phase: Phase
    type: str
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)
    rule: RuleReference | None = None
    dice: DiceRoll | None = None


class TorpedoTrack(BaseModel):
    id: str
    side: Side
    launcher_ship_id: str
    torpedo_type: str
    position: HexCoord
    heading: int = Field(ge=1, le=6)
    speed_cycle: tuple[int, int, int]
    range_remaining: int = Field(ge=0)
    launched_turn: int = Field(gt=0)
    hidden: bool = False


class WreckState(BaseModel):
    id: str
    position: HexCoord
    source_ship_id: str


class MarkerState(BaseModel):
    id: str
    kind: Literal["fire", "smoke", "star_shell", "searchlight", "torpedo_hit", "sunk"]
    position: HexCoord | None = None
    ship_id: str | None = None
    expires_turn: int | None = None
    secret_side: Side | None = None


class GameState(BaseModel):
    game_id: str
    scenario_id: str
    scenario_title: str
    turn: int = 1
    max_turns: int
    phase: Phase = Phase.REINFORCEMENT
    seed: int
    rng_counter: int = 0
    options: GameOptions
    visibility: dict[str, int]
    ships: dict[str, ShipState]
    submitted_orders: dict[str, OrderBatch] = Field(default_factory=dict)
    sealed_orders: dict[str, dict[str, OrderBatch]] = Field(default_factory=dict)
    torpedo_tracks: list[TorpedoTrack] = Field(default_factory=list)
    wrecks: list[WreckState] = Field(default_factory=list)
    markers: list[MarkerState] = Field(default_factory=list)
    events: list[GameEvent] = Field(default_factory=list)
    score: dict[str, int] = Field(default_factory=lambda: {Side.AXIS.value: 0, Side.ALLIES.value: 0})
    winner: Side | None = None
    victory_reason: str | None = None


class PublicShip(BaseModel):
    id: str
    name: str
    side: Side
    ship_type: str
    position: HexCoord | None
    heading: int
    current_speed: int
    hull: int | None
    max_hull: int | None
    fire_markers: int
    fired: bool
    sunk: bool
    asset: str | None


class PlayerObservation(BaseModel):
    game_id: str
    scenario_id: str
    scenario_title: str
    side: Side
    turn: int
    max_turns: int
    phase: Phase
    ships: list[PublicShip]
    score: dict[str, int]
    recent_events: list[GameEvent]
    winner: Side | None
    victory_reason: str | None


class LegalAction(BaseModel):
    kind: str
    ship_id: str | None = None
    schema_hint: dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
