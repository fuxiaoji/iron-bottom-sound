import pytest

from iron_bottom_sound.models import HexCoord


@pytest.mark.parametrize("label", ["A1", "O14", "Z27", "AA1", "HH27"])
def test_hex_label_round_trip(label: str) -> None:
    assert HexCoord.from_label(label).label == label


def test_neighbor_rejects_map_edge() -> None:
    with pytest.raises(Exception):
        HexCoord.from_label("A1").neighbor(1)
