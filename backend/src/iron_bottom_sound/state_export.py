"""投影一：JSONL 世界态帧 + cell-aligned ASCII 棋盘（LLM 可读，无需多模态）。

实现 docs/architecture/state-representation.md 的投影一。全部只从
`engine.observe` 派生的可见集构建（战争迷雾一致），绝不读 `state.ships[敌]`
的隐藏字段。规则常量不复制；棋盘符号遵守「小写=格子 token、大写=坐标」不变式。

格子符号：
- `..` 海
- `a1..a9` 轴心舰（按该侧可见舰顺序编号）、`e1..e9` 盟军舰
- 后缀 `*`=残血（hull<0.35，己方已知时）、`~`=起火
- `t0..` 鱼雷轨、`xx` 沉船、`cN` 隐蔽接触标记
同格冲突优先级：船 > 沉船 > 鱼雷轨 > 接触标记（被顶掉的实体仍在帧里）。
"""

from __future__ import annotations

from typing import Any

from .engine import IronBottomEngine
from .models import GameState, MAP_COLUMNS, MAP_ROWS, PublicShip, Side, index_to_column


def _display_row(q: int, r: int) -> int:
    """轴向坐标 → 显示行（与 HexCoord.label / 前端 hexGeometry 同源，odd-q 平顶）。"""
    return r + (q - (q & 1)) // 2


def _ship_status(ship: PublicShip) -> list[str]:
    """只列非默认状态，全部从 PublicShip 可见字段派生（不猜敌方隐藏损伤）。"""
    status: list[str] = []
    if ship.fire_markers > 0:
        status.append(f"fire:{ship.fire_markers}")
    if ship.forced_speed is not None:
        status.append(f"forced_speed:{ship.forced_speed}")
    if ship.forced_circle_turns > 0:
        status.append(f"circle:{ship.forced_circle_turns}")
    if ship.forced_straight_turns > 0:
        status.append(f"straight:{ship.forced_straight_turns}")
    if ship.forced_turn_side:
        status.append(f"forced_turn:{ship.forced_turn_side}")
    if ship.mfc_destroyed:
        status.append("mfc_down")
    if ship.radar_destroyed:
        status.append("radar_down")
    if ship.bridge_destroyed:
        status.append("bridge_down")
    if ship.rudder_destroyed:
        status.append("rudder_down")
    if ship.captain_status and ship.captain_status != "fit":
        status.append(f"captain:{ship.captain_status}")
    if ship.sunk:
        status.append("sunk")
    return status


def _armament(ship: PublicShip) -> tuple[int | None, int | None, int | None]:
    """(guns_usable, guns_total, torpedoes_ready)。

    只从 PublicShip 的公开炮位/发射器数组派生：敌方 hidden_damage 下 observe 把
    两数组置空 → 三项一律 None（不是 0，0 会暗示敌方无炮）。己方（或隐藏损伤关闭）
    数组齐全，正常计算。
    """
    if not ship.gun_mounts and not ship.torpedo_launchers:
        return None, None, None
    guns_total = sum(1 for mount in ship.gun_mounts if not mount.destroyed)
    guns_usable = sum(
        1 for mount in ship.gun_mounts if not mount.destroyed and not mount.fired_this_phase
    )
    torpedoes_ready = sum(launcher.loaded for launcher in ship.torpedo_launchers)
    return guns_usable, guns_total, torpedoes_ready


def export_frame(
    state: GameState, engine: IronBottomEngine, side: Side, recent_limit: int = 10
) -> dict[str, Any]:
    """一帧 JSONL 世界态（投影一）。全从 `engine.observe` 可见集派生。"""
    observation = engine.observe(state.game_id, side)
    ships: list[dict[str, Any]] = []
    for ship in observation.ships:
        guns_usable, guns_total, torpedoes_ready = _armament(ship)
        ships.append({
            "id": ship.id,
            "name": ship.name,
            "side": ship.side.value,
            "hex": ship.position.label if ship.position else None,
            "q": ship.position.q if ship.position else None,
            "r": ship.position.r if ship.position else None,
            "heading": ship.heading,
            "current_speed": ship.current_speed,
            "hull": ship.hull,
            "max_hull": ship.max_hull,
            "vp": ship.vp,
            "fire_markers": ship.fire_markers,
            "guns_usable": guns_usable,
            "guns_total": guns_total,
            "torpedoes_ready": torpedoes_ready,
            "status": _ship_status(ship),
        })
    torpedoes = [
        {
            "id": track.id,
            "hex": track.position.label,
            "q": track.position.q,
            "r": track.position.r,
            "heading": track.heading,
            "side": track.side.value,
            "speed_cycle": list(track.speed_cycle),
            "salvo_size": track.salvo_size,
            "range_remaining": track.range_remaining,
        }
        for track in observation.torpedo_tracks
    ]
    markers = [
        {
            "id": marker.id,
            "kind": marker.kind,
            "hex": marker.position.label if marker.position else None,
            "heading": marker.heading,
            "movement_rate": marker.movement_rate,
        }
        for marker in observation.markers
    ]
    wrecks = [
        {"id": wreck.id, "hex": wreck.position.label, "source_ship_id": wreck.source_ship_id}
        for wreck in observation.wrecks
    ]
    sequence = state.events[-1].sequence if state.events else 0
    return {
        "game": state.game_id,
        "scenario": state.scenario_id,
        "seed": state.seed,
        "turn": state.turn,
        "max_turns": state.max_turns,
        "phase": state.phase.value,
        "sequence": sequence,
        "side": side.value,
        "visibility": observation.visibility,
        "score": observation.score,
        "ships": ships,
        "torpedoes": torpedoes,
        "markers": markers,
        "wrecks": wrecks,
        "recent_events": [
            event.model_dump(mode="json") for event in observation.recent_events[-recent_limit:]
        ],
    }


def _column_labels() -> list[str]:
    return [index_to_column(q) for q in range(MAP_COLUMNS)]


def _board_cells(
    state: GameState, engine: IronBottomEngine, side: Side
) -> tuple[list[list[str]], list[str], dict[str, str]]:
    """固定扩展海图 token 网格 + 图例 + 舰→token 映射（呈现层，非规则）。

    render_board 与 PIL 战报渲染共用，保证符号/编号完全一致。全从
    `engine.observe` 可见集派生（战争迷雾一致）。
    """
    observation = engine.observe(state.game_id, side)
    height = MAP_ROWS
    grid: list[list[str]] = [[".."] * MAP_COLUMNS for _ in range(height)]
    legend_parts: list[str] = []

    def put(coord, token: str) -> None:
        if coord is None:
            return
        row = _display_row(coord.q, coord.r)
        if 0 <= row < height and 0 <= coord.q < MAP_COLUMNS:
            grid[row][coord.q] = token

    # 船（优先级最高）：轴心 a1..、盟军 e1..，按各自可见顺序编号。
    ship_index: dict[str, str] = {}
    per_side_index: dict[str, int] = {}
    for ship in observation.ships:
        if ship.position is None:
            continue
        idx = per_side_index.get(ship.side.value, 0) + 1
        per_side_index[ship.side.value] = idx
        letter = "a" if ship.side == Side.AXIS else "e"
        token = f"{letter}{idx}"
        if ship.fire_markers > 0:
            token = f"{token}~"
        elif ship.hull is not None and ship.max_hull and ship.hull / ship.max_hull < 0.35:
            token = f"{token}*"
        ship_index[ship.id] = token
        put(ship.position, token)
    for ship in observation.ships:
        if ship.id in ship_index:
            legend_parts.append(
                f"{ship_index[ship.id]}={ship.name}({ship.id})"
            )

    # 沉船（仅由 wrecks 渲染；sunk 未生成 wreck 的舰已按普通 token 画在上面）。
    for wreck in observation.wrecks:
        row = _display_row(wreck.position.q, wreck.position.r)
        if grid[row][wreck.position.q] == "..":
            grid[row][wreck.position.q] = "xx"
    legend_parts.append("xx=沉船")

    # 鱼雷轨。
    torpedo_tokens: dict[str, str] = {}
    for index, track in enumerate(observation.torpedo_tracks):
        token = f"t{index}"
        row = _display_row(track.position.q, track.position.r)
        if grid[row][track.position.q] == "..":
            grid[row][track.position.q] = token
        torpedo_tokens[track.id] = token
    for track in observation.torpedo_tracks:
        legend_parts.append(f"{torpedo_tokens[track.id]}={track.id} 航向{track.heading}")

    # 接触标记。
    for index, marker in enumerate(observation.markers):
        if marker.kind != "contact" or marker.position is None:
            continue
        row = _display_row(marker.position.q, marker.position.r)
        if grid[row][marker.position.q] == "..":
            grid[row][marker.position.q] = f"c{index}"
    if any(marker.kind == "contact" for marker in observation.markers):
        legend_parts.append("cN=隐蔽接触标记")

    legend_parts.append("..=海  残血*  起火~")
    # 罗盘：与 models.direction_delta 一致，供 AI 把图内方位换算成航向。
    legend_parts.append("航向:1=东北 2=东南 3=南 4=西南 5=西北 6=北")
    return grid, legend_parts, ship_index


def render_board(state: GameState, engine: IronBottomEngine, side: Side) -> str:
    """固定扩展海图 ASCII 棋盘（投影一）。按 label 定位，只画可见集。"""
    grid, legend_parts, _ = _board_cells(state, engine, side)
    columns = _column_labels()
    header = "   " + " ".join(label.rjust(2) for label in columns)
    lines = [header]
    for display_row in range(MAP_ROWS):
        cells = " ".join(grid[display_row])
        lines.append(f"{display_row + 1:>2} {cells}")
    return "\n".join(lines) + "\n\n图例: " + " | ".join(legend_parts)
