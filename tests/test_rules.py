import pytest

from iron_bottom_sound.engine import IronBottomEngine, d66_adjust, parse_effect


def test_d66_uses_base_six_steps() -> None:
    assert d66_adjust(26, -6) == 16
    assert d66_adjust(11, -99) == 11
    assert d66_adjust(66, 99) == 66


def test_gunnery_hit_table_boundaries() -> None:
    rules = IronBottomEngine().rules
    assert rules.hit_count(1, 11) == 1
    assert rules.hit_count(1, 66) >= 0
    assert rules.hit_count(99, 66) >= rules.hit_count(1, 66)


@pytest.mark.parametrize(
    ("effect", "expected"),
    [("Miss", (0, 0, False, False)), ("Sunk", (999, 0, True, False)), ("3H/-2MF*", (3, 2, False, True))],
)
def test_effect_parser(effect: str, expected: tuple[int, int, bool, bool]) -> None:
    assert parse_effect(effect) == expected
