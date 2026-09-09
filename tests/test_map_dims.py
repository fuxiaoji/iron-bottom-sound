"""大地图（92×78 等声明尺寸）编解码与边界单测。

- 列标签编码推广到任意列数（保留重复字母制：AA/II/KK/TT 等既有标签不变）。
- HexCoord.neighbor 可收 columns/rows，默认仍按 46×39 常量（既有测试逐字节不变）。
- 剧本 map_columns/map_rows 解析与越界拒绝。
"""

import pytest

from iron_bottom_sound.data import _scenario_map_dims
from iron_bottom_sound.custom_scenarios import CustomScenarioInput
from iron_bottom_sound.models import (
    MAX_MAP_COLUMNS,
    HexCoord,
    column_to_index,
    index_to_column,
)


# ── 编解码断点往返 ────────────────────────────────────────────────────────
@pytest.mark.parametrize("index,label", [
    (0, "A"), (25, "Z"), (26, "AA"), (33, "HH"), (34, "II"),
    (36, "KK"), (45, "TT"), (51, "ZZ"), (91, "NNNN"),
])
def test_column_codec_breakpoints_round_trip(index: int, label: str) -> None:
    assert index_to_column(index) == label
    assert column_to_index(label) == index


def test_column_codec_exceeding_ceiling_rejected() -> None:
    with pytest.raises(ValueError):
        index_to_column(MAX_MAP_COLUMNS)
    with pytest.raises(ValueError):
        column_to_index("M" * 7)  # (len-1)*26 + 12 → far past the 128 ceiling


# ── 大战场标签 from_label/label 往返（列超过 46）─────────────────────────
@pytest.mark.parametrize("label", ["AA1", "HH27", "III21", "NNNN1", "NNNN78"])
def test_big_map_label_round_trip(label: str) -> None:
    assert HexCoord.from_label(label).label == label


# ── neighbor 尺寸感知 ─────────────────────────────────────────────────────
def test_big_map_columns_allows_far_east_hex() -> None:
    # q=60 在 92 列内、46 列外：给 columns=92 才可东进一步。
    coord = HexCoord(q=60, r=-30)
    with pytest.raises(ValueError):
        coord.neighbor(2)  # 默认 46 列：出界
    stepped = coord.neighbor(2, columns=92, rows=78)
    assert stepped.q == 61


def test_big_map_east_edge_rejects_exit() -> None:
    # q=91 是 92 列最后一列；q=91/r=32 显示行 77。向东一步越出 92 列。
    coord = HexCoord(q=91, r=32)
    assert coord.label == "NNNN78"
    with pytest.raises(ValueError, match="Movement leaves the map"):
        coord.neighbor(2, columns=92, rows=78)


def test_big_map_south_edge_rejects_exit() -> None:
    # 底行（显示行 77）向南（heading 3, dr+1）越出 78 行。
    coord = HexCoord(q=46, r=54)  # 显示行 = 54 + 46//2 = 77
    assert coord.label == "UU78"
    with pytest.raises(ValueError, match="Movement leaves the map"):
        coord.neighbor(3, columns=92, rows=78)


def test_default_neighbor_parity_is_unchanged() -> None:
    # 默认路径与既有 test_coordinates.py 完全一致：R39 南缘仍拒绝。
    with pytest.raises(ValueError, match="Movement leaves the map"):
        HexCoord.from_label("R39").neighbor(4)


# ── 剧本声明尺寸解析 ──────────────────────────────────────────────────────
def test_scenario_map_dims_defaults_to_fixed_board() -> None:
    assert _scenario_map_dims({}) == (46, 39, 34, 27)


def test_scenario_map_dims_declared_big_map_prints_full_board() -> None:
    definition = {"map_columns": 92, "map_rows": 78}
    assert _scenario_map_dims(definition) == (92, 78, 92, 78)


def test_scenario_map_dims_rejects_oversized_or_oversized_printed() -> None:
    with pytest.raises(ValueError):
        _scenario_map_dims({"map_columns": MAX_MAP_COLUMNS + 1})
    with pytest.raises(ValueError):
        _scenario_map_dims({"map_columns": 92, "map_rows": 78, "printed_columns": 120})


def test_custom_input_rejects_ship_outside_declared_map() -> None:
    # q=60（"III" 列）在 46 列外，声明 46×39 时必须被拒。
    with pytest.raises(ValueError, match="outside"):
        CustomScenarioInput(
            title="太宽", turns=6,
            ships=[
                {"id": "A", "side": "axis", "position": "III21", "heading": 1, "speed": 0,
                 "asset": "s.png"},
                {"id": "B", "side": "allies", "position": "A1", "heading": 1, "speed": 0,
                 "asset": "s.png"},
            ],
        )
    # 声明 92×78 后，同样坐标合法。
    CustomScenarioInput(
        title="大战场", turns=6, map_columns=92, map_rows=78,
        ships=[
            {"id": "A", "side": "axis", "position": "III21", "heading": 1, "speed": 0,
             "asset": "s.png"},
            {"id": "B", "side": "allies", "position": "NNNN78", "heading": 1, "speed": 0,
             "asset": "s.png"},
        ],
    )
