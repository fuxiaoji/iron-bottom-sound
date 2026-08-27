import pytest

from iron_bottom_sound.models import HexCoord


@pytest.mark.parametrize("label", ["A1", "O14", "Z27", "AA1", "HH27", "II28", "TT39"])
def test_hex_label_round_trip(label: str) -> None:
    assert HexCoord.from_label(label).label == label


def test_neighbor_rejects_map_edge() -> None:
    with pytest.raises(Exception):
        HexCoord.from_label("A1").neighbor(1)


def test_printed_south_edge_opens_into_fixed_sea_buffer() -> None:
    assert HexCoord.from_label("R27").neighbor(4).label == "Q28"


def test_final_expanded_south_edge_rejects_exit() -> None:
    with pytest.raises(ValueError, match="Movement leaves the map"):
        HexCoord.from_label("R39").neighbor(4)
