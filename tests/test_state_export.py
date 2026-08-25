"""投影一状态导出测试：JSONL 世界态帧 + cell-aligned ASCII 棋盘。

全部只从 `engine.observe` 可见集派生（战争迷雾一致）。验证点：
- 帧键齐全、坐标 O14→q14/r6 往返一致；
- 超视距敌舰不进帧/棋盘；
- hidden_damage 敌舰 hull/炮/雷 全 None（不是 0），己方为 int；
- wrecks 双方公共可见；sequence 与 events 末条一致；
- 棋盘 27 行×34 格、表头 A..AH、图例带真实 id、船按 label 落位；
- 火/残血后缀；同格冲突优先级 船 > 沉船 > 鱼雷 > 接触。
"""

from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import (
    GameOptions,
    HexCoord,
    OptionalRules,
    Side,
    TorpedoTrack,
    WreckState,
)
from iron_bottom_sound.state_export import _display_row, export_frame, render_board

AXIS_O14 = ("O14", 14, 6)  # IBS-S-03 seed=1 卡尔加尔斯特的已知落位


def _fresh_engine(scenario="IBS-S-03", seed=1, options=None):
    engine = IronBottomEngine()
    state = engine.reset(scenario, seed, options or GameOptions(mode="llm"))
    return engine, state


def _allied_ship(state):
    return next(s for s in state.ships.values() if s.side == Side.ALLIES and not s.sunk and s.position)


def _karl_id(state) -> str:
    return next(s.id for s in state.ships.values() if s.position and s.position.label == "O14")


def _board_content_lines(board: str) -> list[str]:
    return [ln for ln in board.splitlines() if ln[:2].strip().isdigit()]


def _board_cell(board: str, column: int, display_row: int) -> str:
    line = _board_content_lines(board)[display_row]
    return line[3:].split(" ")[column]


# ── 帧 ──────────────────────────────────────────────────────────────


def test_export_frame_keys_and_karl_coordinates():
    engine, state = _fresh_engine()
    frame = export_frame(state, engine, Side.AXIS)
    assert set(frame) >= {
        "game", "scenario", "seed", "turn", "max_turns", "phase", "sequence",
        "side", "visibility", "score", "ships", "torpedoes", "markers", "wrecks",
        "recent_events",
    }
    assert frame["side"] == "axis"
    label, q, r = AXIS_O14
    karl = next(s for s in frame["ships"] if s["id"] == _karl_id(state))
    assert karl["hex"] == label and karl["q"] == q and karl["r"] == r
    assert karl["side"] == "axis"
    assert 1 <= karl["heading"] <= 6
    assert karl["hull"] is not None and karl["max_hull"] is not None
    assert isinstance(karl["guns_usable"], int) and karl["guns_total"] >= karl["guns_usable"]
    # O14 → q14/r6 → 往返回 label
    assert HexCoord(q=q, r=r).label == label
    assert _display_row(q, r) == 13


def test_export_frame_fog_hides_enemy_ship():
    engine, state = _fresh_engine()
    enemy = _allied_ship(state)
    enemy.position = HexCoord(q=0, r=0)  # A1，距轴心 O14 20 格 > 视距 4
    axis_frame = export_frame(state, engine, Side.AXIS)
    assert enemy.id not in {s["id"] for s in axis_frame["ships"]}
    allies_frame = export_frame(state, engine, Side.ALLIES)
    assert enemy.id in {s["id"] for s in allies_frame["ships"]}


def test_export_frame_hidden_damage_enemy_all_none():
    options = GameOptions(mode="llm", optional_rules=OptionalRules(hidden_damage=True))
    engine, state = _fresh_engine(options=options)
    frame = export_frame(state, engine, Side.AXIS)
    own = [s for s in frame["ships"] if s["side"] == "axis"]
    enemy = [s for s in frame["ships"] if s["side"] == "allies"]
    assert own and enemy
    for s in enemy:
        assert s["hull"] is None and s["max_hull"] is None
        assert s["guns_usable"] is None and s["guns_total"] is None and s["torpedoes_ready"] is None
    for s in own:
        assert isinstance(s["hull"], int) and s["max_hull"] > 0
        assert isinstance(s["guns_usable"], int)


def test_export_frame_wrecks_public_to_both_sides():
    engine, state = _fresh_engine()
    state.wrecks.append(
        WreckState(id="WRK-1", position=HexCoord(q=14, r=6), source_ship_id=_karl_id(state))
    )
    for side in (Side.AXIS, Side.ALLIES):
        frame = export_frame(state, engine, side)
        wreck = next(w for w in frame["wrecks"] if w["id"] == "WRK-1")
        assert wreck["hex"] == "O14"
        assert wreck["source_ship_id"] == _karl_id(state)


def test_export_frame_sequence_matches_events():
    engine, state = _fresh_engine()
    frame = export_frame(state, engine, Side.AXIS)
    expected = state.events[-1].sequence if state.events else 0
    assert frame["sequence"] == expected


# ── 棋盘 ────────────────────────────────────────────────────────────


def test_render_board_dimensions_header_and_legend():
    engine, state = _fresh_engine()
    board = render_board(state, engine, Side.AXIS)
    header_cells = board.splitlines()[0].split()
    assert header_cells[0] == "A" and header_cells[25] == "Z" and header_cells[33] == "AH"
    assert len(header_cells) == 34
    content = _board_content_lines(board)
    assert len(content) == 27
    for line in content:
        assert len(line[3:].split(" ")) == 34
    karl = _karl_id(state)
    assert karl in board  # 图例带真实 id
    assert "..=海" in board


def test_render_board_places_ship_at_label():
    engine, state = _fresh_engine()
    board = render_board(state, engine, Side.AXIS)
    label, q, r = AXIS_O14
    frame = export_frame(state, engine, Side.AXIS)
    axis_ships = [s for s in frame["ships"] if s["side"] == "axis"]
    karl = next(s for s in axis_ships if s["id"] == _karl_id(state))
    expected_token = f"a{axis_ships.index(karl) + 1}"
    assert _board_cell(board, q, _display_row(q, r)) == expected_token
    # 表头列 O ↔ q=14 对齐
    assert board.splitlines()[0].split()[q] == label[0]


def test_render_board_fire_and_damage_suffixes():
    engine, state = _fresh_engine()
    karl = state.ships[_karl_id(state)]
    label, q, r = AXIS_O14
    karl.hull = 1  # 1/6 < 0.35
    board = render_board(state, engine, Side.AXIS)
    assert _board_cell(board, q, _display_row(q, r)) == "a1*"
    karl.hull = 6
    karl.fire_markers = 1
    board = render_board(state, engine, Side.AXIS)
    assert _board_cell(board, q, _display_row(q, r)) == "a1~"


def test_render_board_fog_no_enemy_token():
    engine, state = _fresh_engine()
    for ship in state.ships.values():
        if ship.side == Side.ALLIES and not ship.sunk and ship.position:
            ship.position = HexCoord(q=0, r=0)  # 全部搬到 A1 远角，> 轴心视距
    board = render_board(state, engine, Side.AXIS)
    content_tokens = []
    for line in _board_content_lines(board):
        content_tokens.extend(line[3:].split(" "))
    assert not any(token.startswith("e") for token in content_tokens)
    assert "e1=" not in board  # 图例也不含盟军 token


def test_render_board_cell_priority():
    engine, state = _fresh_engine()
    # 沉船压在卡尔加斯特同格 → 船 token 顶掉 xx
    state.wrecks.append(
        WreckState(id="WRK-1", position=HexCoord(q=14, r=6), source_ship_id=_karl_id(state))
    )
    # 鱼雷在空格 A1 → t0
    state.torpedo_tracks.append(
        TorpedoTrack(
            id="TT-1", side=Side.AXIS, launcher_ship_id=_karl_id(state),
            torpedo_type="G7a", position=HexCoord(q=0, r=0), heading=3,
            speed_cycle=(3, 3, 3), range_remaining=8, launched_turn=1,
        )
    )
    board = render_board(state, engine, Side.AXIS)
    label, q, r = AXIS_O14
    assert _board_cell(board, q, _display_row(q, r)) == "a1"  # 船 > 沉船
    assert _board_cell(board, 0, 0) == "t0"  # 鱼雷在空格
    # 被顶掉的实体仍在帧里（棋盘只画赢家，帧全量）
    frame = export_frame(state, engine, Side.AXIS)
    assert any(w["id"] == "WRK-1" for w in frame["wrecks"])
    assert any(t["id"] == "TT-1" for t in frame["torpedoes"])
