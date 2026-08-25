"""Bearing regression tests for the gunnery-line fix (rules 8.1a centre-line bearing).

The old _bearing_between used a "nearest neighbour hex" heuristic that, on the odd-q
staggered board, misclassified ~30-40% of non-adjacent pairs — a target visually
dead-ahead of the bow could be classified as 60° on the port bow, opening every
port-arc mount onto it. The fix computes the bearing in screen space (the line
connecting the two hex centres) and picks the closest of the six hex directions,
matching what the player sees on the map.

The anchor case is the user report on IBS-S-01 turn 1: DUNCAN (X8, heading 4) vs
FUBUKI (P14). The old code gave bearing 3 / rel 5 (PORT) → all five DUNCAN mounts
could bear. The fixed code gives bearing 4 / rel 0 (BOW) → only the two bow mounts.
"""

import math

from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import FiringArc, Phase, Side

# ship headings 1..6 map to these screen angles (flat-top odd-q, same as the renderer)
_HEADING_ANGLE = {1: 330, 2: 30, 3: 90, 4: 150, 5: 210, 6: 270}


def _screen_angle(origin, target) -> float:
    """Angle of the origin→target hex-centre line, in the renderer's screen space."""
    dq = target.q - origin.q
    dr = target.r - origin.r
    return math.degrees(math.atan2((dr + dq / 2.0) * math.sqrt(3.0), dq * 1.5))


def _reference_bearing(origin, target) -> int:
    """Rule 8.1a: the hex direction whose heading is closest to the centre line."""
    angle = _screen_angle(origin, target)
    return min(
        range(1, 7),
        key=lambda h: abs((_HEADING_ANGLE[h] - angle + 180) % 360 - 180),
    )


def _ibss01_engine():
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-01", seed=1, game_id="bearing-regr")
    state.phase = Phase.GUNNERY
    return engine, state


def test_bearing_matches_rule_reference_for_adjacent_hexes() -> None:
    """Adjacent hexes: bearing equals the neighbour direction exactly."""
    from iron_bottom_sound.models import HexCoord

    origin = HexCoord.from_label("G8")
    for heading in range(1, 7):
        neighbour = origin.neighbor(heading)
        assert IronBottomEngine._bearing_between(origin, neighbour) == heading


def test_bearing_matches_rule_reference_across_the_board() -> None:
    """Non-adjacent pairs: bearing is the screen-space line's nearest hex direction."""
    engine, state = _ibss01_engine()
    pairs = [
        (a.position, b.position)
        for a in state.ships.values() if a.position
        for b in state.ships.values() if b.position
        if a is not b
    ]
    assert len(pairs) >= 90
    for origin, target in pairs:
        assert IronBottomEngine._bearing_between(origin, target) == _reference_bearing(origin, target)


def test_duncan_fubuki_dead_ahead_is_bow_not_port() -> None:
    """User report: DUNCAN must not bring all guns onto a target dead ahead of the bow.

    DUNCAN at X8 heading 4 → FUBUKI at P14 lies ~11° off the bow. The old
    neighbour-distance code classified it as rel 5 (PORT), so all five mounts
    (every one with a port arc) could fire. The fix classifies it rel 0 (BOW);
    only the two bow mounts (P1/P2) may bear, and port mounts may not.
    """
    engine, state = _ibss01_engine()
    duncan = state.ships["IBS-U-USN-DUNCAN"]
    fubuki = state.ships["IBS-U-IJN-FUBUKI"]
    bearing = IronBottomEngine._bearing_between(duncan.position, fubuki.position)
    assert (bearing - duncan.heading) % 6 == 0  # dead ahead, not abeam/quarter
    assert engine._mount_can_bear(duncan, fubuki, [FiringArc.BOW])
    assert not engine._mount_can_bear(duncan, fubuki, [FiringArc.PORT])
    bearing_mounts = [m.id for m in duncan.gun_mounts if engine._mount_can_bear(duncan, fubuki, m.arcs)]
    assert bearing_mounts == ["P1", "P2"]


def test_duncan_hatsuyuki_broadside_keeps_full_mounts() -> None:
    """A genuine beam target still exposes every arc the mounts actually have."""
    engine, state = _ibss01_engine()
    duncan = state.ships["IBS-U-USN-DUNCAN"]
    hatsuyuki = state.ships["IBS-U-IJN-HATSUYUKI"]
    bearing = IronBottomEngine._bearing_between(duncan.position, hatsuyuki.position)
    assert (bearing - duncan.heading) % 6 in {1, 5}  # abeam
    bearing_mounts = [m.id for m in duncan.gun_mounts if engine._mount_can_bear(duncan, hatsuyuki, m.arcs)]
    assert bearing_mounts == ["P1", "P2", "P3", "P4", "P5"]


def test_target_aspect_uses_corrected_line_bearing() -> None:
    """FUBUKI faces SE (heading 2) and DUNCAN attacks it from behind its beam, so the
    longitudinal modifier must NOT apply (it is a broadside aspect, not bow/stern)."""
    engine, state = _ibss01_engine()
    duncan = state.ships["IBS-U-USN-DUNCAN"]
    fubuki = state.ships["IBS-U-IJN-FUBUKI"]
    assert engine._target_aspect(duncan, fubuki) != "bow_stern"
