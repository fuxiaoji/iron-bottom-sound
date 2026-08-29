"""战报系统：每阶段双视角 PNG 地图截图 + 每回合中立 LLM 叙事 + 自包含 MD 战报。

对引擎状态**只读**（只用 `observe`/`get`/`engine.event_visible_to`，绝不改状态/裁决）。
全部地图渲染只从 `engine.observe` 可见集派生（战争迷雾一致）：敌方 hidden_damage →
hull=None 不画残血星、超视距敌舰根本不出现。规则常量不复制；地图几何投影复刻前端
`hexGeometry`（odd-q 平顶，HEX_SIZE=24 为外接圆半径）。

LLM 叙事只从 `DEEPSEEK_API_KEY` 环境变量读取密钥（调用时读，不写文件）；任何叙事
失败/无密钥 → 确定性事实摘要，绝不影响对局。
"""

from __future__ import annotations

import base64
import html as _html
import json
import math
import os
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .engine import IronBottomEngine
from .models import GameEvent, GameState, HexCoord, MAP_COLUMNS, MAP_ROWS, Phase, Side, index_to_column
from .state_export import _board_cells

# ---------------------------------------------------------------------------
# 地图几何（与前端 hexGeometry.ts / HexMap.tsx 完全一致：flat-top odd-q）。
# HEX_SIZE=24 是外接圆半径，不是宽度；同排格心距 1.5*24=36，相邻格心距 √3*24≈41.57。
# ---------------------------------------------------------------------------
HEX_SIZE = 24
HEX_ROW_HEIGHT = HEX_SIZE * math.sqrt(3)  # ≈41.569

COLUMN_COUNT = MAP_COLUMNS
ROW_COUNT = MAP_ROWS
# 左/上边距（56=行号区，44=列标区）加前端 hexGeometry 的基准偏移 (38, 35)。
ORIGIN_X = 56 + 38
ORIGIN_Y = 44 + 35
IMAGE_WIDTH = int(ORIGIN_X + (COLUMN_COUNT - 1) * HEX_SIZE * 1.5 + 72)
LEGEND_TOP = int(ORIGIN_Y + (ROW_COUNT + 0.5) * HEX_ROW_HEIGHT + 36)
IMAGE_HEIGHT = LEGEND_TOP + 180

# 呈现色（非规则常量）。
OCEAN = (16, 40, 62)
LAND = (52, 88, 52)
COAST = (64, 96, 104)
HEX_BORDER = (30, 58, 88)
AXIS_COLOR = (178, 60, 46)
ALLIES_COLOR = (48, 94, 182)
TEXT_COLOR = (225, 232, 240)
DIM_TEXT = (150, 165, 180)


def hex_center(q: int, r: int) -> tuple[float, float]:
    """轴向格 (q, r) → 像素中心。逐字复刻前端 hexGeometry.hexCenter
    （第二个参数是轴向行 r，不是显示行；显示行 = r + floor(q/2)）。"""
    x = ORIGIN_X + q * HEX_SIZE * 1.5
    y = ORIGIN_Y + (r + q / 2) * HEX_ROW_HEIGHT
    return x, y


def hex_vertices(q: int, r: int) -> list[tuple[float, float]]:
    cx, cy = hex_center(q, r)
    return [
        (cx + HEX_SIZE * math.cos(math.radians(60 * i)), cy + HEX_SIZE * math.sin(math.radians(60 * i)))
        for i in range(6)
    ]


def heading_direction(heading: int) -> tuple[float, float]:
    """航向 1-6（IBS 罗盘）→ 该航向相邻格心的单位像素方向。"""
    dq, dr = HexCoord.direction_delta(heading)
    dx = dq * HEX_SIZE * 1.5
    dy = (dr + dq / 2) * HEX_ROW_HEIGHT
    norm = math.hypot(dx, dy)
    return dx / norm, dy / norm


def _column_labels() -> list[str]:
    return [index_to_column(q) for q in range(COLUMN_COUNT)]


# ---------------------------------------------------------------------------
# 中文字体（多候选 + IBS_REPORT_FONT 覆盖；全失败退化 ASCII，不影响对局）。
# ---------------------------------------------------------------------------
_FONT_CACHE: dict[int, ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}


def _cjk_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if size in _FONT_CACHE:
        return _FONT_CACHE[size]
    override = os.environ.get("IBS_REPORT_FONT")
    names = [override] if override else []
    names += ["msyh.ttc", "simhei.ttf", "simsun.ttc", "Deng.ttf", "PingFang.ttc",
              "NotoSansCJK-Regular.ttc", "wqy-microhei.ttc"]
    directories = ["C:/Windows/Fonts", "/System/Library/Fonts",
                   "/usr/share/fonts", "/usr/local/share/fonts"]
    for name in names:
        if not name:
            continue
        for directory in directories:
            path = Path(directory) / name
            if path.is_file():
                try:
                    font = ImageFont.truetype(str(path), size)
                    _FONT_CACHE[size] = font
                    return font
                except OSError:
                    continue
    font = ImageFont.load_default()
    _FONT_CACHE[size] = font
    return font


# ---------------------------------------------------------------------------
# 地图渲染（全从观察可见集 + 公开地形）。
# ---------------------------------------------------------------------------
def _draw_terrain(draw: ImageDraw.ImageDraw, state: GameState) -> None:
    for row in range(ROW_COUNT):
        for q in range(COLUMN_COUNT):
            # row 是显示行；hex_vertices 现在收轴向行（与 HexCoord.r 一致）。
            draw.polygon(hex_vertices(q, row - q // 2), fill=OCEAN, outline=HEX_BORDER)
    for label in state.land_hexes:
        coord = HexCoord.from_label(label)
        draw.polygon(hex_vertices(coord.q, coord.r), fill=LAND, outline=HEX_BORDER)
    for label in state.coast_hexes:
        coord = HexCoord.from_label(label)
        draw.polygon(hex_vertices(coord.q, coord.r), fill=COAST, outline=HEX_BORDER)


def _draw_markers(draw: ImageDraw.ImageDraw, observation: Any) -> None:
    for marker in observation.markers:
        if marker.position is None:
            continue
        cx, cy = hex_center(marker.position.q, marker.position.r)
        kind = marker.kind
        if kind == "contact":
            draw.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], outline=TEXT_COLOR, width=2)
            draw.text((cx, cy), "?", fill=TEXT_COLOR, font=_cjk_font(14), anchor="mm")
        elif kind == "fire":
            draw.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=(255, 120, 0))
        elif kind == "smoke":
            draw.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=(140, 140, 148))
        elif kind == "star_shell":
            draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=(255, 250, 200))
        elif kind == "searchlight":
            draw.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], outline=(190, 235, 255), width=2)
        elif kind == "squall":
            draw.ellipse([cx - 10, cy - 6, cx + 10, cy + 6], fill=(150, 155, 162))


def _draw_torpedoes(draw: ImageDraw.ImageDraw, observation: Any) -> None:
    for track in observation.torpedo_tracks:
        cx, cy = hex_center(track.position.q, track.position.r)
        dx, dy = heading_direction(track.heading)
        x0, y0 = cx - dx * 10, cy - dy * 10
        x1, y1 = cx + dx * 10, cy + dy * 10
        draw.line([(x0, y0), (x1, y1)], fill=TEXT_COLOR, width=2)
        px, py = -dy, dx
        head = (x1 + dx * 5, y1 + dy * 5)
        draw.polygon([(x1, y1), (head[0] - px * 4, head[1] - py * 4), (head[0] + px * 4, head[1] + py * 4)],
                     fill=TEXT_COLOR)


def _draw_wrecks(draw: ImageDraw.ImageDraw, observation: Any) -> None:
    for wreck in observation.wrecks:
        cx, cy = hex_center(wreck.position.q, wreck.position.r)
        draw.text((cx, cy), "xx", fill=(105, 112, 122), font=_cjk_font(13), anchor="mm")


def _draw_ships(
    draw: ImageDraw.ImageDraw, observation: Any, ship_index: dict[str, str]
) -> None:
    for ship in observation.ships:
        if ship.position is None:
            continue
        cx, cy = hex_center(ship.position.q, ship.position.r)
        dx, dy = heading_direction(ship.heading)
        px, py = -dy, dx
        color = AXIS_COLOR if ship.side == Side.AXIS else ALLIES_COLOR
        bow = (cx + dx * 14, cy + dy * 14)
        stern = (cx - dx * 12, cy - dy * 12)
        draw.polygon(
            [bow, (stern[0] + px * 7, stern[1] + py * 7), (stern[0] - px * 7, stern[1] - py * 7)],
            fill=color, outline=(255, 255, 255),
        )
        token = ship_index.get(ship.id, "")
        draw.text((cx - dx * 2, cy - dy * 2), token, fill="white",
                  font=_cjk_font(12), anchor="mm")
        if ship.fire_markers > 0:
            for i in range(min(ship.fire_markers, 3)):
                fx, fy = cx + dx * (14 - i * 5), cy + dy * (14 - i * 5)
                draw.ellipse([fx - 3, fy - 3, fx + 3, fy + 3], fill=(255, 150, 40))
        if ship.hull is not None and ship.max_hull and ship.hull / ship.max_hull < 0.35:
            sx, sy = cx - dx * 12 + px * 11, cy - dy * 12 + py * 11
            draw.text((sx, sy), "*", fill=(255, 225, 60), font=_cjk_font(15), anchor="mm")


def _draw_annotations(
    draw: ImageDraw.ImageDraw, state: GameState, observation: Any,
    legend_parts: list[str],
) -> None:
    title_font = _cjk_font(16)
    label_font = _cjk_font(12)
    legend_font = _cjk_font(14)
    draw.text((ORIGIN_X, 20), f"{state.scenario_title} · {observation.side.value} 视角",
              fill=TEXT_COLOR, font=title_font, anchor="lm")
    columns = _column_labels()
    for q, label in enumerate(columns):
        x = ORIGIN_X + q * HEX_SIZE * 1.5
        draw.text((x, 46), label, fill=DIM_TEXT, font=label_font, anchor="mm")
    for row in range(ROW_COUNT):
        y = ORIGIN_Y + (row + 0.25) * HEX_ROW_HEIGHT
        draw.text((ORIGIN_X - 26, y), str(row + 1), fill=DIM_TEXT, font=label_font, anchor="rm")

    score = observation.score
    score_text = (
        f"第 {observation.turn}/{observation.max_turns} 回合 · {observation.phase.value} · "
        f"比分 轴心{score.get(Side.AXIS.value, 0)} : {score.get(Side.ALLIES.value, 0)} 盟军"
    )
    y = LEGEND_TOP
    draw.text((ORIGIN_X, y), score_text, fill=TEXT_COLOR, font=legend_font, anchor="lm")
    y += 26
    legend = " | ".join(legend_parts)
    for line in _wrap_text(draw, legend, legend_font, IMAGE_WIDTH - ORIGIN_X - 48):
        draw.text((ORIGIN_X, y), line, fill=DIM_TEXT, font=legend_font, anchor="lm")
        y += 22


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in text:
        if draw.textlength(current + char, font=font) > max_width and current:
            lines.append(current)
            current = char
        else:
            current += char
    if current:
        lines.append(current)
    return lines


def render_map_image(state: GameState, engine: IronBottomEngine, side: Side) -> Image.Image:
    """单侧固定扩展海图截图。只画该侧观察可见集 + 公开地形。"""
    observation = engine.observe(state.game_id, side)
    image = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), OCEAN)
    draw = ImageDraw.Draw(image)
    _draw_terrain(draw, state)
    _draw_markers(draw, observation)
    _draw_torpedoes(draw, observation)
    _draw_wrecks(draw, observation)
    _, legend_parts, ship_index = _board_cells(state, engine, side)
    _draw_ships(draw, observation, ship_index)
    _draw_annotations(draw, state, observation, legend_parts)
    return image


# ---------------------------------------------------------------------------
# 公开事件并集 + 叙事。
# ---------------------------------------------------------------------------
EXCLUDED_EVENT_TYPES = {"orders_submitted", "phase_changed", "game_created"}

PHASE_ORDER = [
    "contact_setup", "reinforcement", "movement_planning", "torpedo_planning",
    "movement_resolution", "gunnery", "torpedo_effects", "fire_end",
]

# 阶段显示名（呈现层，非规则）。
PHASE_NAMES = {
    "contact_setup": "隐蔽标记部署",
    "reinforcement": "增援",
    "movement_planning": "移动计划",
    "torpedo_planning": "鱼雷计划",
    "movement_resolution": "同步移动",
    "gunnery": "炮击",
    "torpedo_effects": "鱼雷效果",
    "fire_end": "起火与回合结束",
    "summary": "回合总结",
    "complete": "想定结束",
}

# 战报条目主键是 (game_id, sequence, side)。事件 sequence 很小，与 capture 同侧会冲突，
# 故 ai_action / 每阶段叙事用高位段稳定序号：1e9 + turn*1000 + 阶段序*10 + 侧序。
_SIDE_INDEX = {"axis": 0, "allies": 1, "both": 2}


def _report_sequence(turn: int, phase: str, side: str) -> int:
    phase_index = PHASE_ORDER.index(phase) if phase in PHASE_ORDER else 99
    return 1_000_000_000 + turn * 1000 + phase_index * 10 + _SIDE_INDEX.get(side, 2)


NARRATIVE_SYSTEM_PROMPT = (
    "你是一位太平洋夜战编年史官，正为一场海战撰写中立战报的回合总结。\n"
    "纪律：\n"
    "- 只依据下方给出的【本回合公开事件】与【双方公开态势】写作，不虚构、不推测、"
    "不提及任何一方的订单、计划或未公开信息。\n"
    "- 不偏向任何一方，不使用任何一方的内部视角词（如“我舰”“我军计划”）。\n"
    "- 用叙事化、克制的编年史笔法，写 250-400 字，分 3-4 段，按此结构："
    "① 本回合双方的行动与关键交锋；② 此刻双方的阵位与损失；③ 对后续战局的影响或悬念。\n"
    "- 只输出正文本身，不要标题、不要“战报：”前缀、不要引用事件编号。"
)

_PHASE_NARRATIVE_SYSTEM_PROMPT = (
    "你是一位太平洋夜战编年史官，正为一场海战撰写中立战报中【本阶段】的叙述。\n"
    "纪律：\n"
    "- 只依据下方给出的【本阶段公开事件】与【双方公开态势】写作，不虚构、不推测、"
    "不提及任何一方的订单、计划或未公开信息（包括尚未公开的航迹与秘密计划）。\n"
    "- 不偏向任何一方，不使用任何一方的内部视角词（如“我舰”“我军计划”）。\n"
    "- 用叙事化、克制的编年史笔法，写 200-350 字，分 2-3 段，按此结构："
    "① 本阶段双方的行动与交战；② 此刻双方的态势（阵位、损失）；③ 对后续战局的影响或悬念。\n"
    "- 只输出正文本身，不要标题、不要“战报：”前缀、不要引用事件编号。"
)


def public_events_for_turn(
    state: GameState, engine: IronBottomEngine, turn: int
) -> list[GameEvent]:
    """该回合「至少一侧可见」的公开事件并集。orders_submitted/phase_changed/
    game_created 一律排除（orders_submitted 携带完整私有 order_batch）。"""
    result: list[GameEvent] = []
    for event in state.events:
        if event.turn != turn or event.type in EXCLUDED_EVENT_TYPES:
            continue
        if any(engine.event_visible_to(state, event, side) for side in Side):
            result.append(event)
    return result


def _describe_event(event: GameEvent) -> str:
    text = event.message
    if event.dice is not None:
        rolled = event.dice.adjusted if event.dice.adjusted is not None else event.dice.raw
        text += f"（骰子 {event.dice.notation} → {rolled}）"
    return text


def _public_score(state: GameState, engine: IronBottomEngine) -> dict[str, int]:
    """双方公开比分（hidden_damage 局内双方观察都归零；用任一侧观察）。"""
    return engine.observe(state.game_id, Side.AXIS).score


def build_narrative_prompt(
    state: GameState, engine: IronBottomEngine, turn: int, phase: str | None = None
) -> tuple[str, str]:
    """(system, user)：中立战史提示词。事件只带引擎 message+公开骰子，不传 payload。

    phase 为空 → 回合总结（全回合事件）；否则只给该阶段事件 + 阶段专用提示词。
    """
    events = public_events_for_turn(state, engine, turn)
    if phase is not None:
        events = [event for event in events if event.phase.value == phase]
    by_phase: dict[str, list[str]] = {}
    for event in events:
        by_phase.setdefault(event.phase.value, []).append(_describe_event(event))
    if phase is not None:
        lines = [
            f"【回合 {turn}/{state.max_turns}】",
            f"【阶段：{PHASE_NAMES.get(phase, phase)} · 本阶段公开事件】",
        ]
        for item in by_phase.get(phase, []):
            lines.append(f"  - {item}")
    else:
        lines = [f"【回合 {turn}/{state.max_turns}】", "【本回合公开事件（按阶段）】"]
        for phase_name in PHASE_ORDER:
            if phase_name not in by_phase:
                continue
            lines.append(f"· {phase_name}")
            for item in by_phase[phase_name]:
                lines.append(f"  - {item}")
    lines.append("【双方公开态势】")
    for side in Side:
        obs = engine.observe(state.game_id, side)
        ships = "; ".join(
            f"{ship.name}@{ship.position.label if ship.position else '—'}（航向{ship.heading}）"
            for ship in obs.ships
        ) or "无可见舰船"
        lines.append(f"- {side.value}: {ships}  比分={obs.score}")
    system = NARRATIVE_SYSTEM_PROMPT if phase is None else _PHASE_NARRATIVE_SYSTEM_PROMPT
    return system, "\n".join(lines)


def deterministic_fallback_narrative(
    state: GameState, engine: IronBottomEngine, turn: int, phase: str | None = None
) -> str:
    """无密钥/叙事失败时的事实摘要（确定性、不联网、只列公开事件）。"""
    events = public_events_for_turn(state, engine, turn)
    if phase is None:
        lines = [f"第 {turn} 回合（共 {state.max_turns} 回合）",
                 "叙事模型未配置，以下为本回合公开事件事实摘要："]
    else:
        events = [event for event in events if event.phase.value == phase]
        lines = [f"第 {turn} 回合 · {PHASE_NAMES.get(phase, phase)}",
                 "叙事模型未配置，以下为本阶段公开事件事实摘要："]
    current_phase = None
    for event in events:
        if event.phase != current_phase:
            current_phase = event.phase
            lines.append(f"· {current_phase.value}")
        lines.append(f"  - {_describe_event(event)}")
    score = _public_score(state, engine)
    lines.append(f"比分：轴心 {score.get(Side.AXIS.value, 0)} : "
                 f"{score.get(Side.ALLIES.value, 0)} 盟军")
    if state.winner is not None:
        lines.append(f"胜负：{state.winner.value} 获胜（{state.victory_reason or '—'}）")
    return "\n".join(lines)


def write_turn_narrative(
    state: GameState, engine: IronBottomEngine, turn: int,
    commander: Any = None,
) -> str:
    """回合总结叙事（全回合事件）；失败 → 确定性摘要。战报失败绝不影响对局。"""
    return write_phase_narrative(state, engine, turn, None, commander)


def write_phase_narrative(
    state: GameState, engine: IronBottomEngine, turn: int, phase: str | None,
    commander: Any = None,
) -> str:
    """按阶段（phase 为空=全回合总结）生成中立叙事：LLM 成功用 LLM，否则确定性摘要。"""
    if commander is not None:
        try:
            system, user = build_narrative_prompt(state, engine, turn, phase)
            return commander.write_narrative(system, user)
        except Exception:
            pass
    return deterministic_fallback_narrative(state, engine, turn, phase)


# ---------------------------------------------------------------------------
# 捕获编排（api 与 match 共用；repository=None 只落 PNG 不写库）。
# ---------------------------------------------------------------------------
def _image_dir(root, game_id: str) -> Path:
    directory = Path(root) / game_id
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def capture_phase_snapshot(
    repository, root, state: GameState, engine: IronBottomEngine,
    turn: int, phase: str, sequence: int | None = None, renderer: Any = None,
) -> list[dict[str, Any]]:
    """双侧 PNG + DB 行（幂等：同 (game_id, sequence, side) INSERT OR REPLACE）。
    返回条目字典列表（match.py 累积用）。

    renderer 可选：`(state, engine, side, save_path) -> None`，替换默认 PIL 渲染
    （runner 传真实 UI 截图回调）；缺省行为不变。
    """
    if sequence is None:
        sequence = state.events[-1].sequence if state.events else 0
    entries: list[dict[str, Any]] = []
    for side in Side:
        rel = f"turn-{turn}-{phase}-{side.value}-{sequence}.png"
        save_path = Path(root) / state.game_id / rel
        save_path.parent.mkdir(parents=True, exist_ok=True)
        if renderer is not None:
            renderer(state, engine, side, save_path)
        else:
            render_map_image(state, engine, side).save(save_path, format="PNG")
        entry = {
            "game_id": state.game_id, "sequence": sequence, "turn": turn,
            "phase": phase, "side": side.value, "kind": "capture", "image_path": rel,
        }
        if repository is not None:
            repository.save_battle_entry(
                state.game_id, sequence, turn, phase, side.value, "capture", image_path=rel
            )
        entries.append(entry)
    return entries


def capture_after_advance(
    repository, root, state: GameState, engine: IronBottomEngine,
    prev_phase, commander: Any = None, renderer: Any = None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """`engine.advance` 之后调用（state 已是结算后）。label=prev_phase（结算后快照）。

    返回 (条目列表, 回合总结条目或 None)。条目列表 = 双视角截图 + **每阶段叙述**；
    FIRE_END 额外触发**回合总结**（幂等：有库时靠 battle_narrative_exists）。任何异常由
    调用方吞掉。
    """
    turn = state.turn
    label_phase = prev_phase.value
    narrative_turn = state.turn
    if prev_phase == Phase.FIRE_END:
        label_phase = "fire_end"
        narrative_turn = state.turn - 1 if state.phase == Phase.REINFORCEMENT else state.turn
        turn = narrative_turn
    entries = capture_phase_snapshot(
        repository, root, state, engine, turn, label_phase, renderer=renderer
    )
    # 每阶段一段叙述（幂等：高位段稳定序号 INSERT OR REPLACE）。
    phase_narrative = write_phase_narrative(state, engine, narrative_turn, label_phase, commander)
    phase_sequence = _report_sequence(narrative_turn, label_phase, "both")
    phase_entry: dict[str, Any] = {
        "game_id": state.game_id, "sequence": phase_sequence, "turn": narrative_turn,
        "phase": label_phase, "side": "both", "kind": "narrative",
        "image_path": None, "content": phase_narrative,
    }
    if repository is not None:
        repository.save_battle_entry(
            state.game_id, phase_sequence, narrative_turn, label_phase, "both",
            "narrative", content=phase_narrative,
        )
    entries.append(phase_entry)
    narrative_entry: dict[str, Any] | None = None
    if prev_phase == Phase.FIRE_END:
        if repository is None or not repository.battle_narrative_exists(state.game_id, narrative_turn, "summary"):
            narrative = write_turn_narrative(state, engine, narrative_turn, commander)
            sequence = state.events[-1].sequence if state.events else 0
            narrative_entry = {
                "game_id": state.game_id, "sequence": sequence, "turn": narrative_turn,
                "phase": "summary", "side": "both", "kind": "narrative",
                "image_path": None, "content": narrative,
            }
            if repository is not None:
                repository.save_battle_entry(
                    state.game_id, sequence, narrative_turn, "summary", "both",
                    "narrative", content=narrative,
                )
    return entries, narrative_entry


def capture_ai_action(
    repository, game_id: str, turn: int, phase: str, side: str,
    plan: Any, reasoning: str | None = None, audits: list[Any] | None = None,
    state: GameState | None = None,
) -> dict[str, Any] | None:
    """AI 订单捕获：AIPlanSheet + LLM 思考全文 → kind='ai_action' 的 JSON 行。

    幂等（高位段稳定序号）；失败由调用方吞掉，绝不影响对局。返回条目字典或 None。
    """
    try:
        plan_data = plan.model_dump(mode="json") if plan is not None else {}
        if state is not None:
            intents = plan_data.get("unit_intents", {})
            plan_data["unit_intents"] = {
                _unit_label(state, key): value for key, value in intents.items()
            }
        model = audits[-1].model if audits else "unknown"
        audits = audits or []
        elapsed_ms = sum(int(audit.elapsed_ms) for audit in audits)
        input_tokens = sum(int(audit.input_tokens) for audit in audits)
        output_tokens = sum(int(audit.output_tokens) for audit in audits)
        content = json.dumps({
            "plan": plan_data,
            "reasoning": reasoning,
            "model": model,
            "elapsed_ms": elapsed_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }, ensure_ascii=False)
        sequence = _report_sequence(turn, phase, side)
        entry = {
            "game_id": game_id, "sequence": sequence, "turn": turn,
            "phase": phase, "side": side, "kind": "ai_action",
            "image_path": None, "content": content,
        }
        if repository is not None:
            repository.save_battle_entry(
                game_id, sequence, turn, phase, side, "ai_action", content=content
            )
        return entry
    except Exception:
        return None


def _unit_label(state: GameState, key: str) -> str:
    """unit_intents 的键（ship/marker id）→ 可读名；找不到则原样返回。"""
    ship = state.ships.get(key)
    if ship is not None:
        return f"{ship.name}（{key}）"
    if any(marker.id == key for marker in state.markers):
        return f"接触标记 {key}"
    return key


# ---------------------------------------------------------------------------
# 战报数据 / Markdown。
# ---------------------------------------------------------------------------
def build_report_data(
    state: GameState, engine: IronBottomEngine, entries: list[dict[str, Any]] | list[Any],
) -> dict[str, Any]:
    """中立战报 JSON（api 端点与 match json 共用）。captures/narratives/ai_actions 按
    (turn, phase) 归组；回合总结叙事单独存 turn.narrative。"""
    captures: dict[tuple[int, str], list[dict[str, str]]] = {}
    narratives: dict[tuple[int, str], str] = {}
    summaries: dict[int, str] = {}
    ai_actions: dict[tuple[int, str], dict[str, Any]] = {}
    # 兼容 dict（api._report_entries / match 累积）与 BattleReportEntry 对象。
    normalized = [entry if isinstance(entry, dict) else entry.model_dump(mode="json")
                  for entry in entries]
    for entry in normalized:
        kind = entry["kind"]
        if kind == "capture":
            captures.setdefault((entry["turn"], entry["phase"]), []).append(
                {"side": entry["side"], "image_path": entry["image_path"]}
            )
        elif kind == "ai_action":
            try:
                payload = json.loads(entry["content"]) if entry.get("content") else {}
            except (ValueError, TypeError):
                payload = {}
            # Counterfactual doctrine details remain side-private until the game ends.
            # Existing high-level plan capture behaviour is preserved for compatibility.
            if state.phase != Phase.COMPLETE:
                plan = payload.get("plan") or {}
                plan.pop("tactical_analysis", None)
            ai_actions.setdefault((entry["turn"], entry["phase"]), {})[entry["side"]] = payload
        elif entry["phase"] == "summary":
            summaries[entry["turn"]] = entry["content"]
        else:
            narratives[(entry["turn"], entry["phase"])] = entry["content"]
    turns: list[dict[str, Any]] = []
    for turn in range(1, state.turn + 1):
        phases = [
            {
                "phase": phase,
                "captures": captures.get((turn, phase), []),
                "narrative": narratives.get((turn, phase)),
                "ai_actions": ai_actions.get((turn, phase), {}),
            }
            for phase in PHASE_ORDER
            if (turn, phase) in captures or (turn, phase) in narratives or (turn, phase) in ai_actions
        ]
        turns.append({
            "turn": turn,
            "narrative": summaries.get(turn),
            "phases": phases,
            "events": [
                {"sequence": event.sequence, "phase": event.phase.value,
                 "type": event.type, "message": event.message}
                for event in public_events_for_turn(state, engine, turn)
            ],
        })
    return {
        "meta": {
            "game_id": state.game_id,
            "scenario_id": state.scenario_id,
            "scenario_title": state.scenario_title,
            "mode": state.options.mode,
            "seed": state.seed,
            "turn": state.turn,
            "max_turns": state.max_turns,
            "phase": state.phase.value,
            "winner": state.winner.value if state.winner else None,
            "victory_reason": state.victory_reason,
            "score": state.score,
        },
        "turns": turns,
    }


def _read_image_b64(root, game_id: str, rel: str) -> str:
    path = Path(root) / game_id / rel
    if not path.is_file():
        return ""
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _plan_table(ai_action: dict[str, Any]) -> list[str]:
    """一个 AI 的计划表（Markdown 表格）。"""
    plan = ai_action.get("plan") or {}
    lines = ["| 项目 | 内容 |", "| --- | --- |"]
    lines.append(f"| 态势判断 | {plan.get('situation_summary', '—')} |")
    lines.append(f"| 阶段目标 | {plan.get('phase_goal', '—')} |")
    intents = plan.get("unit_intents") or {}
    intent_text = "；".join(f"{k}→{v}" for k, v in intents.items()) or "—"
    lines.append(f"| 单元意图 | {intent_text} |")
    contingency = plan.get("contingency") or []
    lines.append(f"| 应变预案 | {'；'.join(contingency) or '—'} |")
    orders = plan.get("orders") or {}
    counts = [f"{key}×{len(value)}" for key, value in orders.items()
              if isinstance(value, list) and value]
    lines.append(f"| 订单 | {('，'.join(counts)) or '无'} |")
    movement_details = []
    for item in orders.get("movement", []):
        if not isinstance(item, dict):
            continue
        ship_id = item.get("ship_id", "未知舰")
        plan_text = item.get("plan") or "0"
        movement_details.append(f"{ship_id}：{plan_text}")
    if movement_details:
        lines.append(f"| 移动明细 | {'；'.join(movement_details)} |")
    tactics = plan.get("tactical_analysis") or {}
    if tactics:
        doctrine_names = {
            "direct_attack": "直接雷击", "area_denial": "区域封锁",
            "break_crossing_t": "破坏 T 头", "formation_split": "切割编队",
            "crossfire": "交叉雷幕", "cover_withdrawal": "掩护撤退", "reserve": "保留鱼雷",
        }
        doctrine = doctrine_names.get(tactics.get("doctrine"), tactics.get("doctrine", "—"))
        lines.append(f"| 鱼雷战术 | {doctrine}；{tactics.get('situation', '')} |")
        if tactics.get("reserve_reason"):
            lines.append(f"| 保雷原因 | {tactics['reserve_reason']} |")
        reviews = []
        for candidate in (tactics.get("top_candidates") or [])[:3]:
            response = candidate.get("response") or {}
            changed = "改道" if response.get("route_changed") else "未改变航路"
            reviews.append(
                f"{candidate.get('option_id', '候选')}：{changed}，偏航 {response.get('forced_deviation', 0)} 格，"
                f"减速 {response.get('speed_loss', 0)} MF，预期命中 {candidate.get('expected_hits', 0):.2f}"
            )
        if reviews:
            lines.append(f"| 反事实复盘 | {'；'.join(reviews)} |")
    return lines


def _ai_action_markdown(side_label: str, ai_action: dict[str, Any]) -> list[str]:
    """一侧的 AI 行动小节：计划表 +（LLM 时）思考过程。"""
    lines = [f"**{side_label}计划表**（{ai_action.get('model', '—')}）", ""]
    lines.extend(_plan_table(ai_action))
    reasoning = ai_action.get("reasoning")
    if reasoning:
        lines.extend([
            "",
            f"**{side_label}思考过程**（LLM）",
            "",
            "> " + reasoning.replace("\n", "\n> "),
        ])
    return lines


def build_report_markdown(root, data: dict[str, Any], game_id: str) -> str:
    """自包含 MD：截图以 data:image/png;base64 内嵌，可直接分享。每个阶段都有
    文字叙述 + 双视角地图 + AI 计划表（含 LLM 思考过程）。"""
    meta = data["meta"]
    score = meta["score"] or {}
    lines = ["# 铁底湾的回响 IV · 战报", ""]
    lines.append(f"- **想定**：{meta['scenario_title']}（{meta['scenario_id']}）")
    lines.append(f"- **模式**：{meta['mode']}　**种子**：{meta['seed']}")
    lines.append(f"- **进度**：第 {meta['turn']}/{meta['max_turns']} 回合 · "
                 f"{PHASE_NAMES.get(meta['phase'], meta['phase'])}")
    lines.append(f"- **比分**：轴心 {score.get(Side.AXIS.value, 0)} : "
                 f"{score.get(Side.ALLIES.value, 0)} 盟军")
    if meta["winner"]:
        lines.append(f"- **胜负**：{meta['winner']} 获胜（{meta['victory_reason']}）")
    lines.append("")
    for turn_data in data["turns"]:
        turn = turn_data["turn"]
        lines.append(f"## 第 {turn} 回合")
        narrative = turn_data.get("narrative")
        if narrative:
            lines.append("")
            lines.append("### 回合总结")
            lines.append("")
            lines.append(narrative)
        for phase_data in turn_data.get("phases", []):
            phase = phase_data["phase"]
            phase_label = PHASE_NAMES.get(phase, phase)
            lines.extend(["", f"### {phase_label}（第 {turn} 回合）"])
            phase_narrative = phase_data.get("narrative")
            if phase_narrative:
                lines.extend(["", phase_narrative])
            captures = phase_data.get("captures") or []
            if captures:
                lines.extend(["", "**双方视角地图**", ""])
                for cap in captures:
                    side_label = "轴心" if cap["side"] == Side.AXIS.value else "同盟"
                    lines.append(
                        f"![第{turn}回合 {phase_label} {side_label}视角]"
                        f"(data:image/png;base64,{_read_image_b64(root, game_id, cap['image_path'])})"
                    )
            ai_actions = phase_data.get("ai_actions") or {}
            for side_key in ("axis", "allies"):
                if side_key in ai_actions:
                    side_label = "轴心" if side_key == Side.AXIS.value else "同盟"
                    lines.extend(["", *_ai_action_markdown(side_label, ai_actions[side_key])])
        if turn_data.get("events"):
            lines.extend(["", "### 公开事件"])
            for event in turn_data["events"]:
                lines.append(f"- {event['message']}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 轻量战报：不内嵌 base64，引用本地图片（浏览器/编辑器秒开）。
# 产物须与图片目录同级（backend/reports/），相对路径 {game_id}/{image_path} 才有效。
# ---------------------------------------------------------------------------
def build_report_markdown_lite(data: dict[str, Any], game_id: str) -> str:
    """轻量 MD：图片用相对路径引用（非 base64），文件仅几十 KB。"""
    meta = data["meta"]
    score = meta["score"] or {}
    lines = ["# 铁底湾的回响 IV · 战报", ""]
    lines.append(f"- **想定**：{meta['scenario_title']}（{meta['scenario_id']}）")
    lines.append(f"- **模式**：{meta['mode']}　**种子**：{meta['seed']}")
    lines.append(f"- **进度**：第 {meta['turn']}/{meta['max_turns']} 回合 · "
                 f"{PHASE_NAMES.get(meta['phase'], meta['phase'])}")
    lines.append(f"- **比分**：轴心 {score.get(Side.AXIS.value, 0)} : "
                 f"{score.get(Side.ALLIES.value, 0)} 盟军")
    if meta["winner"]:
        lines.append(f"- **胜负**：{meta['winner']} 获胜（{meta['victory_reason']}）")
    lines.append("")
    lines.append("> 轻量版：图片为相对路径引用，需与本文件同级的图片目录一起打开；"
                 "完整自包含版见 `<game_id>-battle-report.md`。")
    lines.append("")
    for turn_data in data["turns"]:
        turn = turn_data["turn"]
        lines.append(f"## 第 {turn} 回合")
        narrative = turn_data.get("narrative")
        if narrative:
            lines.extend(["", "### 回合总结", "", narrative])
        for phase_data in turn_data.get("phases", []):
            phase = phase_data["phase"]
            phase_label = PHASE_NAMES.get(phase, phase)
            lines.extend(["", f"### {phase_label}（第 {turn} 回合）"])
            phase_narrative = phase_data.get("narrative")
            if phase_narrative:
                lines.extend(["", phase_narrative])
            captures = phase_data.get("captures") or []
            if captures:
                lines.extend(["", "**双方视角地图**", ""])
                for cap in captures:
                    side_label = "轴心" if cap["side"] == Side.AXIS.value else "同盟"
                    rel = f"{game_id}/{cap['image_path']}"
                    lines.append(
                        f"![第{turn}回合 {phase_label} {side_label}视角]({rel})"
                    )
            ai_actions = phase_data.get("ai_actions") or {}
            for side_key in ("axis", "allies"):
                if side_key in ai_actions:
                    side_label = "轴心" if side_key == Side.AXIS.value else "同盟"
                    lines.extend(["", *_ai_action_markdown(side_label, ai_actions[side_key])])
        if turn_data.get("events"):
            lines.extend(["", "### 公开事件"])
            for event in turn_data["events"]:
                lines.append(f"- {event['message']}")
        lines.append("")
    return "\n".join(lines)


def _plan_table_html(ai_action: dict[str, Any]) -> list[str]:
    """一侧 AI 计划表的 HTML 表格。"""
    plan = ai_action.get("plan") or {}
    orders = plan.get("orders") or {}
    movement_details = []
    for item in orders.get("movement", []):
        if isinstance(item, dict):
            movement_details.append(
                f"{item.get('ship_id', '未知舰')}：{item.get('plan') or '0'}"
            )
    rows = [
        ("态势判断", plan.get("situation_summary") or "—"),
        ("阶段目标", plan.get("phase_goal") or "—"),
        ("单元意图",
         "；".join(f"{k}→{v}" for k, v in (plan.get("unit_intents") or {}).items()) or "—"),
        ("应变预案", "；".join(plan.get("contingency") or []) or "—"),
        ("订单",
         "，".join(f"{k}×{len(v)}" for k, v in orders.items()
                   if isinstance(v, list) and v) or "无"),
    ]
    if movement_details:
        rows.append(("移动明细", "；".join(movement_details)))
    lines = ["<table>", "<thead><tr><th style='width:80px'>项目</th><th>内容</th></tr></thead>",
             "<tbody>"]
    for key, value in rows:
        lines.append(f"<tr><td>{_html.escape(key)}</td><td>{_html.escape(str(value))}</td></tr>")
    lines.append("</tbody></table>")
    return lines


def build_report_html(data: dict[str, Any], game_id: str) -> str:
    """轻量 HTML 战报：<img src> 相对路径引用本地截图，浏览器双击秒开。"""
    meta = data["meta"]
    score = meta["score"] or {}
    o = []
    o.append("<!DOCTYPE html>")
    o.append('<html lang="zh-CN"><head><meta charset="utf-8">')
    o.append("<title>铁底湾的回响 IV · 战报</title>")
    o.append("<style>"
             "body{font-family:'Microsoft YaHei',system-ui,sans-serif;max-width:880px;margin:0 auto;"
             "padding:24px;line-height:1.7;color:#222;background:#fafafa}"
             "h1{border-bottom:2px solid #34495e;padding-bottom:8px}"
             "h2{margin-top:42px;border-left:4px solid #34495e;padding-left:10px}"
             "h3{margin-top:30px;color:#34495e}"
             "img{max-width:100%;display:block;margin:6px auto;border:1px solid #ccc;"
             "background:#eee}"
             "figure{margin:10px 0;text-align:center}"
             "figcaption{font-size:13px;color:#666;margin-top:2px}"
             "table{border-collapse:collapse;margin:8px 0;width:100%;font-size:14px}"
             "th,td{border:1px solid #bbb;padding:4px 8px;text-align:left;vertical-align:top}"
             "th{background:#eef2f7}"
             ".reasoning{background:#f4f4f4;border-left:3px solid #999;padding:8px 12px;"
             "white-space:pre-wrap;font-size:13px;color:#333;margin:8px 0;border-radius:4px}"
             ".summary{background:#fff;padding:12px 16px;border-radius:6px;"
             "box-shadow:0 1px 3px rgba(0,0,0,.08)}"
             ".meta{color:#555;font-size:14px;margin-bottom:8px}"
             "ul.events{font-size:13px;color:#444}"
             ".plan{font-size:13px;color:#666;margin:6px 0 0}"
             ".toc{font-size:14px;columns:2;line-height:1.9}"
             "</style></head><body>")
    o.append("<h1>铁底湾的回响 IV · 战报</h1>")
    o.append("<div class='meta'>"
             f"想定：{_html.escape(meta['scenario_title'])}（{_html.escape(meta['scenario_id'])}）　"
             f"模式：{_html.escape(meta['mode'])}　种子：{meta['seed']}<br>"
             f"进度：第 {meta['turn']}/{meta['max_turns']} 回合 · "
             f"{_html.escape(PHASE_NAMES.get(meta['phase'], meta['phase']))}　"
             f"比分：轴心 {score.get(Side.AXIS.value, 0)} : {score.get(Side.ALLIES.value, 0)} 盟军")
    if meta["winner"]:
        o[-1] += f"　<strong>胜负：{_html.escape(meta['winner'])} 获胜"
        if meta["victory_reason"]:
            o[-1] += f"（{_html.escape(meta['victory_reason'])}）"
        o[-1] += "</strong>"
    o.append("</div>")
    if data["turns"]:
        o.append("<ul class='toc'>")
        for turn_data in data["turns"]:
            o.append(f"<li><a href='#turn-{turn_data['turn']}'>第 {turn_data['turn']} 回合</a></li>")
        o.append("</ul>")
    for turn_data in data["turns"]:
        turn = turn_data["turn"]
        o.append(f"<h2 id='turn-{turn}'>第 {turn} 回合</h2>")
        narrative = turn_data.get("narrative")
        if narrative:
            o.append("<div class='summary'>" + _html.escape(narrative).replace("\n", "<br>")
                     + "</div>")
        for phase_data in turn_data.get("phases", []):
            phase = phase_data["phase"]
            phase_label = PHASE_NAMES.get(phase, phase)
            o.append(f"<h3>{_html.escape(phase_label)}（第 {turn} 回合）</h3>")
            phase_narrative = phase_data.get("narrative")
            if phase_narrative:
                o.append("<p>" + _html.escape(phase_narrative).replace("\n", "<br>") + "</p>")
            for cap in phase_data.get("captures") or []:
                side_label = "轴心" if cap["side"] == Side.AXIS.value else "同盟"
                rel = f"{game_id}/{cap['image_path']}"
                o.append(f"<figure><img src='{_html.escape(rel)}' "
                         f"alt='第{turn}回合 {_html.escape(phase_label)} {side_label}视角' "
                         f"loading='lazy'><figcaption>{side_label}视角</figcaption></figure>")
            ai_actions = phase_data.get("ai_actions") or {}
            for side_key in ("axis", "allies"):
                if side_key in ai_actions:
                    side_label = "轴心" if side_key == Side.AXIS.value else "同盟"
                    action = ai_actions[side_key]
                    model = _html.escape(action.get("model") or "—")
                    o.append(f"<div class='plan'><strong>{side_label}计划表</strong>"
                             f"（{model}）</div>")
                    o.extend(_plan_table_html(action))
                    reasoning = action.get("reasoning")
                    if reasoning:
                        o.append("<div class='reasoning'><strong>" + side_label
                                 + "思考过程</strong>\n\n" + _html.escape(reasoning)
                                 + "</div>")
        if turn_data.get("events"):
            o.append("<h4>公开事件</h4><ul class='events'>")
            for event in turn_data["events"]:
                o.append("<li>" + _html.escape(event["message"]) + "</li>")
            o.append("</ul>")
    o.append("</body></html>")
    return "\n".join(o)
