"""Crop the battle board screenshots down to the action for the after-action report.

The captured boards are the whole scenario grid - ships occupy a few percent of the
frame - so an embedded figure is unreadable without zooming.  This writes a cropped
copy of each board: the extent of the ship markers (found by colour, since the empty
hex grid and the ruler text are both near-greys) plus a margin.  The hex rulers are
copied into the cropped frame's top and left edges, because the report's prose names
hexes ("V14", "R16") and a figure without rulers cannot be checked against it.

Originals are never modified; crops are written as ``crop-<name>.png`` beside them,
so the report is always rebuildable from the raw captures alone.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

DEFAULT_IMAGES = Path(__file__).resolve().parent / "battle" / "images"
MARGIN = 120
RULER_X = 150   # the hex-number ruler is wider than the letter row
RULER_Y = 100
BOARD_FILL = (16, 40, 62)
MIN_SIDE = 460
BOTTOM_BAND = 0.10      # the on-image legend lives here; it is not the action
LEFT_BAND = 0.05        # the hex-number ruler column
TOP_BAND = 0.03         # the hex-letter ruler row


def marker_mask(image: Image.Image) -> tuple[list[int], list[int]]:
    """Pixel coordinates of ship markers: saturated inks, or near-white hulls."""
    width, height = image.size
    left_limit = int(width * LEFT_BAND)
    top_limit = int(height * TOP_BAND)
    bottom_limit = int(height * (1.0 - BOTTOM_BAND))
    pixels = image.load()
    xs: list[int] = []
    ys: list[int] = []
    for y in range(top_limit, bottom_limit, 2):
        for x in range(left_limit, width, 2):
            red, green, blue = pixels[x, y][:3]
            saturation = max(red, green, blue) - min(red, green, blue)
            if saturation > 100 or min(red, green, blue) > 230:
                xs.append(x)
                ys.append(y)
    return xs, ys


def crop(path: Path, out: Path, margin: int = MARGIN) -> tuple[int, int, int, int]:
    image = Image.open(path).convert("RGB")
    xs, ys = marker_mask(image)
    if not xs:
        image.save(out, optimize=True)
        return (0, 0, *image.size)

    left = max(RULER_X, min(xs) - margin)
    top = max(RULER_Y, min(ys) - margin)
    right = min(image.width, max(xs) + margin)
    bottom = min(image.height, max(ys) + margin)
    if right - left < MIN_SIDE:
        right = min(image.width, left + MIN_SIDE)
    if bottom - top < MIN_SIDE:
        bottom = min(image.height, top + MIN_SIDE)

    content = image.crop((left, top, right, bottom))
    top_ruler = image.crop((left, 0, right, RULER_Y))
    left_ruler = image.crop((0, top, RULER_X, bottom))
    composed = Image.new("RGB", (RULER_X + content.width, RULER_Y + content.height),
                         BOARD_FILL)
    composed.paste(top_ruler, (RULER_X, 0))
    composed.paste(left_ruler, (0, RULER_Y))
    composed.paste(content, (RULER_X, RULER_Y))
    composed.save(out, optimize=True)
    return (left, top, right, bottom)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=Path, default=DEFAULT_IMAGES)
    parser.add_argument("--force", action="store_true", help="rewrite existing crops")
    args = parser.parse_args()

    written = 0
    for path in sorted(args.images.rglob("turn-*.png")):
        out = path.with_name(f"crop-{path.name}")
        if out.exists() and not args.force and out.stat().st_mtime >= path.stat().st_mtime:
            continue
        box = crop(path, out)
        written += 1
        print(f"{path.name}: {box} -> {out.name}")
    print(f"cropped {written} boards under {args.images}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
