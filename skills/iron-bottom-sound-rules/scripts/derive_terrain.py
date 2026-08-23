#!/usr/bin/env python3
"""Derive auditable local terrain cells from the printed X/Y/Z overlays.

The colour pass only creates candidates.  ``verification`` remains ``draft``
until the generated labelled QA images have been compared with the originals.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
import yaml


ROOT = Path(__file__).resolve().parents[3]
IMAGES = ROOT / "resources" / "originals" / "assets" / "images"
OUTPUT = ROOT / "resources" / "derived" / "structured" / "maps" / "terrain-overlays.yaml"
OVERLAYS = {
    "savo_island": {
        "file": "岛屿.jpg",
        "origin": (55.0, 192.0),
        "step": (199.5, 229.0),
        "anchors": {"X": [4, 0], "Y": [6, 13]},
    },
    "guadalcanal_coast": {
        "file": "海岸.jpg",
        "origin": (44.0, 218.0),
        "step": (199.5, 229.0),
        "anchors": {"Z": [7, 9]},
    },
}


def read_image(path: Path) -> np.ndarray:
    return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)


def hex_mask(shape: tuple[int, int], center: tuple[float, float]) -> np.ndarray:
    x, y = center
    radius = 122
    half_height = 105
    points = np.array(
        [[x - radius, y], [x - radius / 2, y - half_height], [x + radius / 2, y - half_height],
         [x + radius, y], [x + radius / 2, y + half_height], [x - radius / 2, y + half_height]],
        dtype=np.int32,
    )
    mask = np.zeros(shape, dtype=np.uint8)
    cv2.fillPoly(mask, [points], 255)
    return mask


def derive(name: str, spec: dict, qa_dir: Path | None) -> dict:
    image = read_image(IMAGES / spec["file"])
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    height, width = image.shape[:2]
    origin_x, origin_y = spec["origin"]
    step_x, step_y = spec["step"]
    cells = {"land": [], "coast": [], "sea": []}
    fractions: dict[str, float] = {}
    qa = image.copy()
    for q in range(13):
        for r in range(14):
            center = (origin_x + step_x * q, origin_y + step_y * r + (q % 2) * step_y / 2)
            x, y = center
            if not (0 <= x < width and 0 <= y < height):
                continue
            mask = hex_mask((height, width), center)
            pixels = hsv[mask > 0]
            land_fraction = float(np.count_nonzero(pixels[:, 0] < 80) / len(pixels))
            label = f"{q},{r}"
            fractions[label] = round(land_fraction, 3)
            terrain = "land" if land_fraction >= 0.5 else ("coast" if land_fraction >= 0.08 else "sea")
            cells[terrain].append(label)
            colour = {"land": (0, 0, 255), "coast": (0, 220, 255), "sea": (0, 200, 0)}[terrain]
            cv2.circle(qa, (round(x), round(y)), 13, colour, -1)
            cv2.putText(qa, label, (round(x) - 28, round(y) - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, colour, 2)
    if qa_dir:
        qa_dir.mkdir(parents=True, exist_ok=True)
        cv2.imencode(".png", qa)[1].tofile(qa_dir / f"{name}-qa.png")
    return {
        "asset": f"resources/originals/assets/images/{spec['file']}",
        "verification": "draft",
        "grid": {"orientation": "flat_top", "origin_center_px": list(spec["origin"]), "column_step_px": step_x,
                 "row_step_px": step_y, "odd_column_y_offset_px": step_y / 2},
        "anchors": spec["anchors"],
        "cells": cells,
        "land_fraction_by_cell": fractions,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qa-dir", type=Path)
    arguments = parser.parse_args()
    document = {
        "schema_version": 1,
        "source": {"documents": ["岛屿.jpg", "海岸.jpg"], "status": "visual_source"},
        "classification": {"land_min_fraction": 0.5, "coast_min_fraction": 0.08},
        "overlays": {name: derive(name, spec, arguments.qa_dir) for name, spec in OVERLAYS.items()},
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
