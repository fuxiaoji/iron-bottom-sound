from __future__ import annotations

import re
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


# IBS-M-MAIN is the 34×27 printed map.  The engine uses a fixed 12-column /
# 12-row sea buffer to the east and south so no live counter ever changes its
# coordinate frame.  This is project extension IBS-R-MAP-01, not source map
# data; terrain overlays still exist only inside PRINTED_*.
PRINTED_MAP_COLUMNS = 34
PRINTED_MAP_ROWS = 27
MAP_COLUMNS = 46
MAP_ROWS = 39
# Largest playable board a scenario may declare (the "大战场" 92×78 fits well
# below these).  The column label codec and HexCoord caps must never approach
# this ceiling, so it can stay a global sanity bound independent of the active
# scenario's declared map size.
MAX_MAP_COLUMNS = 128
MAX_MAP_ROWS = 128


class Side(StrEnum):
    AXIS = "axis"
    ALLIES = "allies"

    @property
    def opponent(self) -> "Side":
        return Side.ALLIES if self == Side.AXIS else Side.AXIS


class Phase(StrEnum):
    FORMATION_SETUP = "formation_setup"
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
    # Repeated-letter scheme, length grows every 26 columns: A..Z (0..25),
    # AA..ZZ (26..51), AAA..ZZZ (52..77), AAAA.. (78..).  Keeps the legacy
    # AA/II/KK/TT labels that existing boards and tests rely on.
    normalized = label.upper()
    first = normalized[0] if normalized else ""
    if not first or not ("A" <= first <= "Z") or any(ch != first for ch in normalized):
        raise ValueError(f"Invalid map column {label!r}; expected repeated letters like A-Z, AA-TT, ...")
    index = (len(normalized) - 1) * 26 + (ord(first) - 65)
    if index >= MAX_MAP_COLUMNS:
        raise ValueError(f"Map column {label!r} exceeds the {MAX_MAP_COLUMNS}-column ceiling")
    return index


def index_to_column(index: int) -> str:
    if not 0 <= index < MAX_MAP_COLUMNS:
        raise ValueError(f"Map column index must be 0 through {MAX_MAP_COLUMNS - 1}")
    character = chr(65 + (index % 26))
    return character * (1 + index // 26)


class HexCoord(BaseModel, frozen=True):
    # Structural ceilings only (see MAX_MAP_COLUMNS/MAX_MAP_ROWS); the active
    # scenario's map size is enforced where the hex is used (neighbor bounds,
    # engine _coord_on_map, movement edge stops), not here.
    q: int = Field(ge=0, le=MAX_MAP_COLUMNS - 1)
    r: int = Field(ge=-MAX_MAP_ROWS, le=MAX_MAP_ROWS)

    @classmethod
    def from_label(cls, label: str) -> "HexCoord":
        match = re.fullmatch(r"([A-Za-z]+)(\d{1,3})", label.strip())
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

    def neighbor(
        self,
        heading: int,
        *,
        columns: int = MAP_COLUMNS,
        rows: int = MAP_ROWS,
    ) -> "HexCoord":
        dq, dr = self.direction_delta(heading)
        candidate = HexCoord(q=self.q + dq, r=self.r + dr)
        display_row = candidate.r + (candidate.q - (candidate.q & 1)) // 2
        if not (0 <= candidate.q < columns and 0 <= display_row < rows):
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
    # 项目扩展：编队指挥链。默认关闭，保证旧存档和经典模式逐位兼容。
    realistic_command: bool = False
    # 命令延迟模式（新增模式，不改变 realistic_command 语义；见 command_delay.py）。
    # 三个互斥入口：Classic(F,F) / Realistic(T,F) / Command Delay(T,T)。
    command_delay_mode: bool = False
    # 教学脚本只负责可审计的预置/固定事件；所有玩家命令仍走正式引擎。
    tutorial_script: Literal["classic_night", "erma_grand_fleet"] | None = None


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
    formation_id: str | None = None
    command_status: Literal["attached", "detaching", "retreating", "withdrawn"] = "attached"
    withdrawal_edge: Literal["north", "east", "south", "west"] | None = None

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
    formation_emergency_stop: bool = False


class FormationSetupOrder(BaseModel):
    formation_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=40)
    ship_ids: list[str] = Field(min_length=2)
    leader_id: str
    flagship_id: str
    reserve_flagship_id: str
    spacing: Literal[1, 2] = 1
    heading: int | None = Field(default=None, ge=1, le=6)


class FormationSpeedDecision(BaseModel):
    formation_id: str
    action: Literal["reduce", "detach"]
    speed: int | None = Field(default=None, ge=0, le=8)
    detach_ship_ids: list[str] = Field(default_factory=list)
    emergency_stop: bool = False


class FormationMovementOrder(BaseModel):
    formation_id: str
    leader_plan: str = "0"
    spacing: Literal[1, 2] | None = None
    speed_decision: FormationSpeedDecision | None = None
    # ``None`` keeps the formation's declared style, which defaults to
    # FOLLOW_WAKE, so an order written before this field existed still expands
    # into the exact frozen follower behaviour.
    movement_style: FormationMovementStyle | None = None
    # Explicit IBS-R-RC-08 transition: move as a body this turn and return to
    # FOLLOW_WAKE only if the formation ends the turn genuinely column-aligned.
    reform_column: bool = False


class FormationMovementStyle(StrEnum):
    """How a formation moves as a body (project extension, IBS-R-RC-02/08).

    ``FOLLOW_WAKE`` is the existing successive / follow-the-leader movement and
    stays the default for every formation, so Realistic semantics are unchanged
    unless a player explicitly selects the other style.
    """

    FOLLOW_WAKE = "follow_wake"
    MOVE_TOGETHER = "move_together"


class FormationGeometryKind(StrEnum):
    """Declared geometry of a formation's ship line.

    A ``COLUMN`` is line-ahead: the line axis is the leader's stern direction, so
    the guide trail is a legal wake.  ``STRAIGHT_LINE`` means the ships are still
    on one hex line with uniform spacing, but the axis is no longer parallel to
    the bow-stern direction (line-abreast or oblique).  A simultaneous turn
    rotates headings without rotating the axis, so ``MOVE_TOGETHER`` can leave a
    formation oblique; it must not keep being treated as a column.
    """

    COLUMN = "column"
    STRAIGHT_LINE = "straight_line"


class FormationState(BaseModel):
    id: str
    name: str
    side: Side
    ship_ids: list[str]
    leader_id: str
    flagship_id: str
    reserve_flagship_id: str
    succession_order: list[str] = Field(default_factory=list)
    spacing: Literal[1, 2] = 1
    heading: int = Field(ge=1, le=6)
    speed: int = Field(default=0, ge=0, le=8)
    status: Literal["formed", "assembling", "command_disrupted", "dissolved"] = "formed"
    disruption_turn: int | None = None
    locked_heading: int | None = Field(default=None, ge=1, le=6)
    locked_speed: int | None = Field(default=None, ge=0, le=8)
    guide_trail: list[HexCoord] = Field(default_factory=list)
    # Command Delay extension (CD-1).  Defaults reproduce the frozen Realistic
    # behaviour exactly; these fields are declared state, not live measurements,
    # and only change through an explicit MOVE_TOGETHER / REFORM_COLUMN action.
    movement_style: FormationMovementStyle = FormationMovementStyle.FOLLOW_WAKE
    geometry_kind: FormationGeometryKind = FormationGeometryKind.COLUMN
    line_axis: int | None = Field(default=None, ge=1, le=6)


class CommandSuccession(BaseModel):
    formation_id: str
    previous_flagship_id: str
    new_flagship_id: str
    effective_turn: int


class WithdrawalState(BaseModel):
    ship_id: str
    edge: Literal["north", "east", "south", "west"]
    status: Literal["retreating", "withdrawn"] = "retreating"


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
    formation_setup: list[FormationSetupOrder] = Field(default_factory=list)
    formation_movement: list[FormationMovementOrder] = Field(default_factory=list)
    formation_speed_decisions: list[FormationSpeedDecision] = Field(default_factory=list)
    # Command Delay: the only gunnery input a formation agent or a fleet order may
    # supply.  The engine's selector still generates every GunneryOrder, mount
    # allocation and firing solution (IBS-R-CD-06).
    target_priorities: list[TargetPriorityDirective] = Field(default_factory=list)
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
    kind: Literal["fire", "smoke", "star_shell", "searchlight", "squall", "storm", "contact", "torpedo_hit", "sunk"]
    position: HexCoord | None = None
    ship_id: str | None = None
    target_ship_id: str | None = None
    expires_turn: int | None = None
    secret_side: Side | None = None
    heading: int | None = Field(default=None, ge=1, le=6)
    movement_rate: int | None = Field(default=None, ge=0, le=8)
    contact_truth: Literal["real", "decoy"] | None = None


class AuthorityLevel(StrEnum):
    """Who currently governs a formation's execution (IBS-R-CD-02)."""

    FLEET_DIRECTED = "fleet_directed"
    DELEGATED = "delegated"
    LOCAL_AUTONOMY = "local_autonomy"


class LinkStatus(StrEnum):
    """Quality of the command link between fleet and a formation.

    ``DIRECT`` is a same-turn short tactical signal, ``RELAYED`` is a signal that
    needed a relay or re-encipherment stage, ``STALE`` means only reports older
    than the current turn are available, and ``BLACKOUT`` means nothing has been
    delivered.  The turn cost of each stage is an explicit simulation
    abstraction, never a claimed historical measurement (see
    ``communications/models.py``).
    """

    DIRECT = "direct"
    RELAYED = "relayed"
    STALE = "stale"
    BLACKOUT = "blackout"


class CommandAuthority(BaseModel):
    """Fleet-level authority for one side."""

    side: Side
    level: AuthorityLevel = AuthorityLevel.DELEGATED
    fleet_commander_ship_id: str | None = None
    fleet_formation_id: str | None = None


class RadioPolicy(StrEnum):
    """How much a formation may transmit (v2.3, IR-5).

    Silence is a decision with consequences, so it is a state the mode enforces when a
    message is drafted - not a phrase an agent writes into a report while transmitting.
    """

    NORMAL = "normal"
    CONTACT_ONLY = "contact_only"
    SCHEDULED_WINDOW = "scheduled_window"
    STRICT_SILENCE = "strict_silence"


class FormationCommandState(BaseModel):
    """Per-formation slice of the command-delay state machine."""

    formation_id: str
    commander_ship_id: str | None = None
    authority: AuthorityLevel = AuthorityLevel.DELEGATED
    link_status: LinkStatus = LinkStatus.DIRECT
    # The fleet's knowledge of this formation, as last *reported*.  Filled from
    # delivered messages; never read from the live formation during an
    # observation, which is what stops remote exact state leaking upward.
    reported_turn: int | None = None
    reported_position: HexCoord | None = None
    reported_heading: int | None = Field(default=None, ge=1, le=6)
    reported_speed: int | None = Field(default=None, ge=0, le=8)
    reported_ship_count: int | None = Field(default=None, ge=0)
    reported_geometry_kind: FormationGeometryKind | None = None
    # Phase the newest held report was drawn from: a later phase in the same turn
    # is newer knowledge than an earlier one, which matters when two reports of
    # one turn arrive out of order.
    reported_phase: Phase | None = None
    active_order_id: str | None = None
    last_report_turn: int | None = None
    # When this formation last acknowledged an order (CD-13): the mode used to
    # drop acknowledgements entirely, so the ledger could not tell a formation
    # that had confirmed from one that had merely been sent the order.
    last_ack_turn: int | None = None
    # The formation's own words in its newest delivered report (CD-13).
    reported_text: str | None = None
    # v2.3: the formation's radio policy and the bookkeeping the report triggers need.
    radio_policy: RadioPolicy = RadioPolicy.NORMAL
    last_reported_hull: float | None = None
    last_reported_contacts: int | None = None
    # Set by the formation's agent during the movement phase and consumed by the
    # trigger-driven report pass: the agent decides *what* to say, the engine decides
    # whether a report is warranted at all (IR-5).
    pending_report_text: str = ""
    pending_report_actions: list[str] = Field(default_factory=list)


class ContractTerm(BaseModel):
    """One agreed term between the fleet and a formation (CD-6 research hook)."""

    term_id: str
    description: str
    obligor: str
    beneficiary: str
    measurable: str = ""
    weight: float = 0.0


class ContractState(BaseModel):
    """A standing agreement a future incentive-aware policy would read.

    Empty by default: a game with no declared contract carries an empty contract,
    which is what keeps this stage an interface rather than a mechanic.
    """

    side: Side
    formation_id: str
    order_id: str | None = None
    terms: list[ContractTerm] = Field(default_factory=list)
    agreed_turn: int | None = None


class LedgerEntry(BaseModel):
    """One observable event a future reward could be derived from."""

    turn: int
    phase: str
    formation_id: str
    kind: str
    value: float = 0.0
    reason: str = ""
    source_message_id: str | None = None
    order_id: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)


from .formation_memory import FormationMemory  # noqa: E402  (no cycle: memory imports nothing)


class CommandDelayState(BaseModel):
    """Whole-game state for the Command Delay mode (option-gated, default off)."""

    tick: int = 0
    authorities: dict[str, CommandAuthority] = Field(default_factory=dict)
    formations: dict[str, FormationCommandState] = Field(default_factory=dict)
    # CD-3 fills these; declared here so the data model is one review.
    messages: list[CommandMessage] = Field(default_factory=list)
    mission_orders: list[MissionOrder] = Field(default_factory=list)
    # Local-agent output, kept for audit and for the gunnery selector.
    local_directives: list[TargetPriorityDirective] = Field(default_factory=list)
    # Stored as dumps, not as the agent's own type: this is an audit ledger, and
    # keeping it schema-free avoids a data-model -> agent import cycle.
    decisions: list[dict[str, Any]] = Field(default_factory=list)
    # CD-6 research hooks: declared contracts and the incentive ledger.  Both stay
    # empty until a researcher declares them; nothing in the runtime reads them
    # back into a decision.
    contracts: list[ContractState] = Field(default_factory=list)
    ledger: list[LedgerEntry] = Field(default_factory=list)
    # CD-10: one memory per formation (never shared, never side-global), and the raw
    # agent transcript for the debug view and for replaying a game without the model.
    memories: dict[str, FormationMemory] = Field(default_factory=dict)
    # Per-formation knowledge, with provenance (v2.3, IR-3).  Bounded like memory: a long
    # scenario must not grow the state without limit.
    knowledge: dict[str, list["KnowledgeItem"]] = Field(default_factory=dict)
    agent_log: list[dict[str, Any]] = Field(default_factory=list)
    # Which policy each side's formations run under, as a *label* only: the callable
    # itself is held in process memory and never persisted.
    policy_labels: dict[str, str] = Field(default_factory=dict)
    next_sequence: int = 1


class MessagePrecedence(StrEnum):
    """Deterministic queue class for the command circuit (IBS-R-CD-05)."""

    URGENT = "urgent"
    OPERATIONAL = "operational"
    ROUTINE = "routine"


class CommunicationMedium(StrEnum):
    """How a signal travels.

    The turn cost of each medium is a *simulation abstraction* constrained by
    history, not a measured average: same-navy tactical traffic is a handling /
    encoding / relay / queue problem, never electromagnetic propagation at this
    time scale.
    """

    # Same-command hand-over: the fleet commander and the formation commander are in the
    # same formation, so the order is spoken, not transmitted.  It is its own medium
    # rather than a zero-cost TBS call, because nothing about it is a radio event.
    FACE_TO_FACE = "face_to_face"
    TBS_SHORT = "tbs_short"
    BLINKER = "blinker"
    WT_CODED = "wt_coded"
    WT_REENCIPHER_RELAY = "wt_reencipher_relay"
    MULTI_HOP = "multi_hop"
    BLACKOUT = "blackout"


class MessageKind(StrEnum):
    MISSION_ORDER = "mission_order"
    AMENDMENT = "amendment"
    SITREP = "sitrep"
    CONTACT_REPORT = "contact_report"
    ACKNOWLEDGEMENT = "acknowledgement"
    CLARIFICATION = "clarification"
    DEVIATION_REPORT = "deviation_report"


class MessageStatus(StrEnum):
    QUEUED = "queued"
    DELIVERED = "delivered"
    DROPPED = "dropped"
    SUPERSEDED = "superseded"


class DelayBreakdown(BaseModel):
    """Where a message's delay came from, component by component (v2.3).

    The mode prices human and procedural work, never propagation: at a three-minute
    turn, electromagnetic travel is zero at any map distance.  Distance decides *whether
    a medium is reachable*, never how many turns a message takes - that rule is why this
    breakdown exists as separate numbers instead of one opaque delay.
    """

    propagation: int = 0            # zero at game scale, stated rather than implied
    handling: int = 0               # drafting / transcription / distribution
    encoding: int = 0               # encipher, transmit, decipher
    relay: int = 0                  # each actual relay stage
    reencipher: int = 0             # each actual cryptographic-domain transition
    queue: int = 0                  # channel capacity: waiting for a free slot
    clarification: int = 0          # acknowledged clarification round trips

    @property
    def total(self) -> int:
        return (self.propagation + self.handling + self.encoding + self.relay
                + self.reencipher + self.queue + self.clarification)

    def as_dict(self) -> dict[str, int]:
        return {
            "propagation": self.propagation, "handling": self.handling,
            "encoding": self.encoding, "relay": self.relay,
            "reencipher": self.reencipher, "queue": self.queue,
            "clarification": self.clarification, "total": self.total,
        }


class KnowledgeItem(BaseModel):
    """One fact a formation is entitled to hold, with where it came from (v2.3).

    The rule this exists to enforce: a formation may know an enemy fact only if **it**
    observed it or **it** received a message carrying it, by the current turn.  Sibling
    reports do not become visible to a formation just because the fleet holds them - that
    was the v2.2 leak (``_external_reports`` read the fleet's copies and handed every
    formation its siblings' positions).
    """

    subject_id: str                  # enemy ship id, or a formation id for own-side facts
    field: str                       # POSITION | HEADING | SPEED | SHIP_TYPE | SHIP_COUNT
    value: str | int | None = None
    observed_turn: int = 0           # when the fact was true
    received_turn: int | None = None # when this holder learned it
    source_kind: str = "LOCAL_OBSERVATION"   # LOCAL_OBSERVATION | DELIVERED_MESSAGE
    source_id: str = ""              # the observing formation, or the reporting one
    message_id: str | None = None
    # v2.3 keeps two levels here; the operational claim schema (CONFIRMED / REPORTED /
    # INFERRED / SUSPECTED) is IR-6 and builds on this.
    confidence: str = "OBSERVED"

    @property
    def age_turns(self) -> int | None:
        if self.received_turn is None:
            return None
        return max(0, self.received_turn - self.observed_turn)


class RouteProvenance(BaseModel):
    """Why this message took this route (v2.3).

    A relay or re-enciphered route is only legal with an explicit node list and a reason;
    without them the route is invalid and the audit flags it.  ``distance_hex`` and
    ``tbs_range_hex`` are recorded so a reader can check reachability directly rather
    than trusting the medium's name.
    """

    sender_hex: str | None = None
    recipient_hex: str | None = None
    distance_hex: int | None = None
    tbs_range_hex: int = 0
    direct_tbs_available: bool = False
    direct_visual_available: bool = False
    same_command_location: bool = False
    radio_policy: str = "NORMAL"
    channel_state: str | None = None
    selected_medium: str = ""
    route_nodes: list[str] = Field(default_factory=list)
    why_relay_required: str | None = None
    why_reencipher_required: str | None = None
    blockers: list[str] = Field(default_factory=list)


class CommandMessage(BaseModel):
    """One signal, with issued / delivered / observed turns kept separate."""

    message_id: str
    side: Side
    origin: str                      # ship or formation id that drafted it
    destination: str                 # formation id (fleet traffic is addressed)
    kind: MessageKind
    precedence: MessagePrecedence = MessagePrecedence.OPERATIONAL
    medium: CommunicationMedium = CommunicationMedium.TBS_SHORT
    issued_turn: int
    issued_phase: Phase
    # Abstracted handling budget, in turns, as declared by the medium profile.
    handling_delay: int = 0
    relay_hops: int = 0
    delivered_turn: int | None = None
    delivered_phase: Phase | None = None
    observed_turn: int | None = None
    acknowledged_turn: int | None = None
    status: MessageStatus = MessageStatus.QUEUED
    reason: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    superseded_by: str | None = None
    # v2.3: where the delay came from, and why this route was chosen.  Both are filled
    # when the message is drafted and completed when it is delivered (the queue
    # component is only known then).
    delay: DelayBreakdown = Field(default_factory=DelayBreakdown)
    route_provenance: RouteProvenance | None = None


class ContingencyBranch(StrEnum):
    EXPLICIT_SIGNAL_BRANCH = "explicit_signal_branch"
    LOCAL_CONDITION_BRANCH = "local_condition_branch"
    LOSS_OF_COMM_BRANCH = "loss_of_comm_branch"


class TargetPriorityDirective(BaseModel):
    """A bounded priority weight. It can never make an illegal shot legal."""

    formation_id: str
    source: Literal["FLEET_ORDER", "LOCAL_AGENT", "DOCTRINE"]
    target_id: str | None = None
    target_class: str | None = None
    objective_tag: str | None = None
    weight: float = Field(default=0.0, ge=-1.0, le=1.0)
    expires_turn: int | None = None
    hard_restriction: bool = False


class Contingency(BaseModel):
    """A pre-briefed branch: three kinds only, never an arbitrary if/else."""

    branch: ContingencyBranch
    description: str = ""
    trigger_condition: str | None = None
    trigger_message_kind: MessageKind | None = None
    requires_local_check: bool = False
    fallback_task: str | None = None


class MissionOrder(BaseModel):
    """Mission Command order (IBS-R-CD-04), following the battle-plan structure."""

    order_id: str
    formation_id: str
    side: Side
    issued_turn: int
    issued_by: str
    mission: str
    assumptions: list[str] = Field(default_factory=list)
    trigger_conditions: list[str] = Field(default_factory=list)
    commander_intent: str = ""
    task_to_formation: str = ""
    coordination_measures: list[str] = Field(default_factory=list)
    operating_area: str | None = None
    waypoint: HexCoord | None = None
    deadline_turn: int | None = None
    target_priority_directives: list[TargetPriorityDirective] = Field(default_factory=list)
    roe: list[str] = Field(default_factory=list)
    risk_constraints: list[str] = Field(default_factory=list)
    report_requirements: list[str] = Field(default_factory=list)
    # A periodic report happens only if the order asks for one; the window names the turns
    # ("report at dusk"), which is how a staff cycle is expressed without a probability.
    report_window_turns: list[int] = Field(default_factory=list)
    communications_plan: list[str] = Field(default_factory=list)
    commander_location: str | None = None
    rendezvous: str | None = None
    loss_of_comm_plan: list[str] = Field(default_factory=list)
    contingencies: list[Contingency] = Field(default_factory=list)
    valid_from_turn: int | None = None
    expiry_turn: int | None = None
    confirmed_turn: int | None = None
    # v2.3 (IR-4): an order is a persistent object with a revision lineage, not a per-turn
    # prompt.  ``order_event`` says what this message does to the order book; the engine
    # refuses to create a new revision merely because a commander restated the mission.
    order_event: str = "NEW_ORDER"
    revision: int = 1
    amends_order_id: str | None = None
    cancelled_turn: int | None = None

    @property
    def is_active(self) -> bool:
        return self.cancelled_turn is None


class GameState(BaseModel):
    game_id: str
    scenario_id: str
    scenario_title: str
    turn: int = 1
    max_turns: int
    phase: Phase = Phase.REINFORCEMENT
    seed: int
    # Active map size for this game (defaults to the fixed IBS-R-MAP-01 board).
    # printed_* may be smaller than map_* (a "printed" inner region the rest of
    # the board is sea buffer around); None means the whole map is the printed
    # region (no separate buffer shading).
    map_columns: int = MAP_COLUMNS
    map_rows: int = MAP_ROWS
    printed_columns: int | None = None
    printed_rows: int | None = None
    rng_counter: int = 0
    options: GameOptions
    tutorial_flags: set[str] = Field(default_factory=set)
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
    formations: dict[str, FormationState] = Field(default_factory=dict)
    formation_resume_phase: Phase | None = None
    command_successions: list[CommandSuccession] = Field(default_factory=list)
    withdrawals: dict[str, WithdrawalState] = Field(default_factory=dict)
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
    # 想定特例的运行期容器（警戒状态、鱼雷消耗计分等）；键结构由各想定的
    # special_rule_kinds 定义，引擎不在此处复制规则常量。
    scenario_state: dict[str, Any] = Field(default_factory=dict)
    winner: Side | None = None
    victory_reason: str | None = None
    # Command Delay mode state; ``None`` for Classic and Realistic, so those
    # modes carry no extra state and their replays are unaffected.
    command_delay: CommandDelayState | None = None


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
    # 装甲（英寸，静态舰级数据，双方可见；穿透判定用）
    primary_armor: float = 0
    secondary_armor: float = 0
    belt_armor: float = 0
    bridge_armor: float = 0
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
    formation_id: str | None = None
    command_status: Literal["attached", "detaching", "retreating", "withdrawn"] | None = None


class PlayerObservation(BaseModel):
    game_id: str
    scenario_id: str
    scenario_title: str
    side: Side
    turn: int
    max_turns: int
    phase: Phase
    visibility: int
    map_columns: int = MAP_COLUMNS
    map_rows: int = MAP_ROWS
    printed_columns: int | None = None
    printed_rows: int | None = None
    ships: list[PublicShip]
    torpedo_tracks: list[TorpedoTrack] = Field(default_factory=list)
    markers: list[MarkerState] = Field(default_factory=list)
    wrecks: list[WreckState] = Field(default_factory=list)
    formations: list[FormationState] = Field(default_factory=list)
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
    # Optional side-private state-machine analysis; old saves and LLM plans omit it.
    tactical_analysis: dict[str, Any] | None = None


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
