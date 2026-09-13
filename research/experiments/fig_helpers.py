"""Small helpers for the v8 main figures."""
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))

from iron_bottom_sound.models import HexCoord  # noqa: E402


def hex_to_xy(label: str) -> tuple[float, float]:
    """Hex label -> screen-space (x, y) matching the engine's bearing convention."""
    c = HexCoord.from_label(label)
    return 1.5 * c.q, (c.r + c.q / 2.0) * math.sqrt(3.0)
