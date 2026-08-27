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
    CONTACT_SETUP = "contact_setup"
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
        dq, dr = self.direction_delta(heading)
        candidate = HexCoord(q=self.q + dq, r=self.r + dr)
        display_row = candidate.r + (candidate.q - (candidate.q & 1)) // 2
        if not 0 <= display_row <= 26:
            raise ValueError("Movement leaves the map")
        return candidate

    @staticmethod
    def direction_delta(heading: int) -> tuple[int, int]:
        # IBS-M-MAIN printed compass: 1 NE, 2 SE, 3 S, 4 SW, 5 NW, 6 N.
        directions = {1: (1, -1), 2: (1, 0), 3: (0, 1), 4: (-1, 1), 5: (-1, 0), 6: (0, -1)}
        if heading not in directions:
            raise ValueError("Heading must be 1 through 6")
        return directions[heading]

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


class ResearchConsent(BaseModel):
    """开局时用户主动声明的科研用途同意（允许保留对战记录；可留称呼）。

    仅经 create_game 请求体传入、落库到 research_consent 表；不进入 GameState。
    """
    allow: bool = False
    handle: str | None = Field(default=None, max_length=40)


class GameOptions(BaseModel):
    mode: Literal["hotseat", "tutorial", "llm", "vs_ai"] = "hotseat"
    # 人机大战时对手 AI 的风格 profile（tactical.PROFILES 或 champions.CHAMPIONS 键）；其余模式恒为 None。
    ai_profile: str | None = None
    optional_rules: OptionalRules = Field(default_factory=OptionalRules)
    # 战报系统开关（默认关：既有测试/无头调用保持 hermetic；前端起始勾选默认开→发 True）。
    battle_report: bool = False


class WeaponMount(BaseModel):
    kind: Literal["primary", "secondary", "torpedo"]
    firepower: int = Field(default=0, ge=0)
    caliber: float = Field(default=0, ge=0)
    ammo: int | None = Field(default=None, ge=0)
    destroyed: bool = False


class GunMountRecord(BaseModel):
    id: str
    kind: Literal["primary", "secondary", "tertiary"]
    position: MountPosition
    firepower: int = Field(gt=0)
    caliber: float = Field(gt=0)
    arcs: tuple[FiringArc, ...]
    armour: float | None = Field(default=None, ge=0)


class GunMountState(GunMountRecord):
    destroyed: bool = False
    fired_this_phase: bool = False


class TorpedoLauncherRecord(BaseModel):
    id: str
    position: MountPosition
    arcs: tuple[FiringArc, ...]
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
    hull_rows: tuple[int, ...]
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

    @field_validator("hull_rows")
    @classmethod
    def positive_hull_rows(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if not value or any(boxes <= 0 for boxes in value):
            raise ValueError("Hull rows must be non-empty and contain only positive box counts")
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
    speed_damage_track: tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]
    speed_damage_crossed: tuple[int, int, int] = (0, 0, 0)
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
    radar: bool = False
    gun_mounts: list[GunMountState] = Field(default_factory=list)
    torpedo_launchers: list[TorpedoLauncherState] = Field(default_factory=list)
    vp: int = 0
    asset: str | None = None
    fire_markers: int = Field(default=0, ge=0)
    fire_source_attacker: str | None = None
    fire_source_turn: int | None = None
    mfc_destroyed: bool = False
    radar_destroyed: bool = False
    fired: bool = False
    smoke: bool = False
    sunk: bool = False
    sinking_turn: int | None = None
    sinking_drift_pending: bool = False
    reinforcement_turn: int | None = None
    rudder_destroyed: bool = False
    bridge_destroyed: bool = False
    captain_status: Literal["fit", "wounded", "killed"] = "fit"
    turn_limit_degrees: int | None = None
    forced_straight_turns: int = Field(default=0, ge=0)
    forced_circle_turns: int = Field(default=0, ge=0)
    forced_turn_side: Literal["port", "starboard"] | None = None
    forced_speed: int | None = Field(default=None, ge=0)
    forced_speed_turns: int = Field(default=0, ge=0)
    guns_disabled_turns: int = Field(default=0, ge=0)

    def max_speed_for_turn(self, turn: int) -> int:
        row_index = (turn - 1) % 3
        row = self.speed_damage_track[row_index]
        crossed = self.speed_damage_crossed[row_index]
        return row[crossed] if crossed < len(row) else 0


class MovementCommand(BaseModel):
    action: Literal["advance", "turn_port_60", "turn_starboard_60", "turn_port_120", "turn_starboard_120"]


class MovementOrder(BaseModel):
    ship_id: str
    plan: str = "0"
    speed: int | None = Field(default=None, ge=0)
    commands: list[MovementCommand] = Field(default_factory=list)


class MovementPreviewRequest(BaseModel):
    ship_id: str
    commands: list[str] = Field(default_factory=list)
    plan: str | None = None
    hexes: list[HexCoord] = Field(default_factory=list)


class MovementTrajectoryEntry(BaseModel):
    ship_id: str
    plan: str = "0"


class MovementTrajectoriesRequest(BaseModel):
    plans: list[MovementTrajectoryEntry] = Field(default_factory=list)


class TorpedoAssistRequest(BaseModel):
    target_id: str | None = None
    launch: dict[str, Any] | None = None


class GunneryAssistRequest(BaseModel):
    assigned: list[dict[str, Any]] = Field(default_factory=list)


class ContactSetupOrder(BaseModel):
    marker_id: str
    entry_hex: HexCoord
    heading: int = Field(ge=1, le=6)
    speed: Literal[4, 5]
    ship_ids: list[str] = Field(default_factory=list)


class ContactMovementOrder(BaseModel):
    marker_id: str
    plan: str


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
    mount_id: str | None = None
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
    launch_at_mf: int = Field(default=1, ge=0, le=8)
    launch_hex: HexCoord | None = None
    bearing: int | None = Field(default=None, ge=1, le=6)
    launch_side: Literal["port", "starboard"] | None = None
    launch_angle: Literal["A", "B", "X", "Y"] | None = None
    setting_index: int = Field(default=0, ge=0)


class PhaseConfirmation(BaseModel):
    ready: bool = True


class OrderBatch(BaseModel):
    side: Side
    phase: Phase | None = None
    reinforcements: list[ReinforcementOrder] = Field(default_factory=list)
    contacts: list[ContactSetupOrder] = Field(default_factory=list)
    contact_movement: list[ContactMovementOrder] = Field(default_factory=list)
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


class BattleReportEntry(BaseModel):
    """战报条目（捕获截图或回合叙事），与 battle_report 表行一一对应。"""
    game_id: str
    sequence: int
    turn: int
    phase: str
    side: str  # 'axis'|'allies'（capture）| 'both'（narrative）
    kind: str  # 'capture'|'narrative'
    image_path: str | None = None
    content: str | None = None
    created_at: str | None = None


class ShipCombatEntry(BaseModel):
    sequence: int
    turn: int
    phase: Phase
    direction: Literal["inflicted", "received"]
    event_type: str
    message: str
    related_ship_id: str | None = None
    related_ship_name: str | None = None
    rule: RuleReference | None = None
    dice: DiceRoll | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class TorpedoTrack(BaseModel):
    id: str
    side: Side
    launcher_ship_id: str
    torpedo_type: str
    position: HexCoord
    heading: int = Field(ge=1, le=6)
    speed_cycle: tuple[int, int, int]
    range_remaining: int = Field(ge=0)
    distance_travelled: int = Field(default=0, ge=0)
    launched_turn: int = Field(gt=0)
    salvo_size: int = Field(default=1, ge=1)
    launch_position: HexCoord | None = None
    launch_side: Literal["port", "starboard"] | None = None
    launch_angle: Literal["A", "B", "X", "Y"] | None = None
    traversed_hexes: list[HexCoord] = Field(default_factory=list)
    contact_ship_ids: list[str] = Field(default_factory=list)
    hidden: bool = False


class WreckState(BaseModel):
    id: str
    position: HexCoord
    source_ship_id: str


class MarkerState(BaseModel):
    id: str
    kind: Literal["fire", "smoke", "star_shell", "searchlight", "squall", "contact", "torpedo_hit", "sunk"]
    position: HexCoord | None = None
    ship_id: str | None = None
    target_ship_id: str | None = None
    expires_turn: int | None = None
    secret_side: Side | None = None
    heading: int | None = Field(default=None, ge=1, le=6)
    movement_rate: int | None = Field(default=None, ge=0, le=8)
    contact_truth: Literal["real", "decoy"] | None = None


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
    land_hexes: set[str] = Field(default_factory=set)
    coast_hexes: set[str] = Field(default_factory=set)
    radar_blocking_hexes: set[str] = Field(default_factory=set)
    resume_phase: Phase | None = None
    contact_reserve_positions: dict[str, HexCoord] = Field(default_factory=dict)
    contact_formations: dict[str, list[str]] = Field(default_factory=dict)
    contact_offsets: dict[str, dict[str, tuple[int, int]]] = Field(default_factory=dict)
    reinforcement_trigger_turn: int | None = None
    reinforcement_arrival_turn: int | None = None
    reinforcement_succeeds_on: tuple[int, ...] = ()
    reinforcement_roll_done: bool = False
    reinforcement_available: bool = False
    reinforcement_entry_start: HexCoord | None = None
    reinforcement_entry_end: HexCoord | None = None
    events: list[GameEvent] = Field(default_factory=list)
    score: dict[str, int] = Field(default_factory=lambda: {Side.AXIS.value: 0, Side.ALLIES.value: 0})
    hull_damage_taken: dict[str, int] = Field(
        default_factory=lambda: {Side.AXIS.value: 0, Side.ALLIES.value: 0}
    )
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
    vp: int = 0
    max_speed: int | None = None
    speed_damage_crossed: list[int] | None = None
    speed_damage_track: list[list[int]] | None = None
    min_legal_speed: int | None = None
    max_legal_speed: int | None = None
    torpedo_type: str | None = None
    gun_mounts: list[GunMountState] = Field(default_factory=list)
    torpedo_launchers: list[TorpedoLauncherState] = Field(default_factory=list)
    turn_limit_degrees: int | None = None
    forced_straight_turns: int = 0
    forced_circle_turns: int = 0
    forced_turn_side: Literal["port", "starboard"] | None = None
    forced_speed: int | None = None
    mfc_destroyed: bool = False
    radar_destroyed: bool = False
    bridge_destroyed: bool = False
    rudder_destroyed: bool = False
    captain_status: Literal["fit", "wounded", "killed"] | None = None
    combat_history: list[ShipCombatEntry] = Field(default_factory=list)


class PlayerObservation(BaseModel):
    game_id: str
    scenario_id: str
    scenario_title: str
    side: Side
    turn: int
    max_turns: int
    phase: Phase
    visibility: int
    ships: list[PublicShip]
    torpedo_tracks: list[TorpedoTrack] = Field(default_factory=list)
    markers: list[MarkerState] = Field(default_factory=list)
    wrecks: list[WreckState] = Field(default_factory=list)
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


class AIPlanSheet(BaseModel):
    turn: int = Field(gt=0)
    phase: Phase
    situation_summary: str = Field(max_length=400)
    phase_goal: str = Field(max_length=120)
    unit_intents: dict[str, str] = Field(default_factory=dict)
    orders: dict[str, Any]
    contingency: list[str] = Field(default_factory=list, max_length=2)


class LLMCallAudit(BaseModel):
    side: Side
    turn: int = Field(gt=0)
    phase: Phase
    attempt: int = Field(ge=1, le=3)
    model: str
    request_id: str | None = None
    elapsed_ms: int = Field(ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cache_hit_tokens: int = Field(default=0, ge=0)
    valid: bool
    validation_errors: list[str] = Field(default_factory=list)
    reasoning_preview: str | None = Field(default=None, max_length=600)
    # LLM 思考全文（只进战报 DB / 本地 match 存档，不进公共 API 响应）。
    reasoning_content: str | None = Field(default=None)


class MatchReport(BaseModel):
    game_id: str
    scenario_id: str
    seed: int
    winner: Side | None
    victory_reason: str | None
    completed: bool
    request_count: int = Field(ge=0)
    fallback_count: int = Field(default=0, ge=0)
    manual_state_changes: int = Field(default=0, ge=0)
    axis_plan_count: int = Field(default=0, ge=0)
    allies_plan_count: int = Field(default=0, ge=0)
    total_input_tokens: int = Field(default=0, ge=0)
    total_output_tokens: int = Field(default=0, ge=0)
    elapsed_ms: int = Field(default=0, ge=0)
    passed: bool
    failure_reason: str | None = None
