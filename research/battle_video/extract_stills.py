"""Extract the report's figures from the finished film.

The report and the documentary must not drift apart, so the report's figures are the
film's own frames: extracted at the start of each turn's comparison beat (where the god's
eye map sits next to both commanders' pictures) plus the chapter cards.  Timestamps come
from the beat durations, so a re-cut film re-cuts the figures.

Usage::

    .venv/bin/python research/battle_video/extract_stills.py --battle battle_em01
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--props", type=Path, default=HERE / "data" / "render_props.json")
    parser.add_argument("--video", type=Path, default=HERE / "out" / "documentary.mp4")
    parser.add_argument("--out", type=Path, default=HERE / "stills")
    parser.add_argument("--width", type=int, default=1280)
    args = parser.parse_args()

    if not args.video.exists():
        print(f"no video at {args.video}")
        return 2
    beats = json.loads(args.props.read_text(encoding="utf-8"))["beats"]
    args.out.mkdir(parents=True, exist_ok=True)

    def still(at: float, name: str) -> None:
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{at:.2f}", "-i", str(args.video),
             "-frames:v", "1", "-vf", f"scale={args.width}:-2", str(args.out / name)],
            check=True,
        )

    clock = 0.0
    taken: list[str] = []
    chapter_stills = {"title": "01_title.png", "rules_basics": "02_rules.png",
                      "oob": "03_oob.png"}
    for beat in beats:
        start = clock
        clock += float(beat.get("seconds") or 0)
        beat_id = beat["id"]
        if beat_id in chapter_stills:
            still(start + min(1.5, float(beat["seconds"]) / 3), chapter_stills[beat_id])
            taken.append(chapter_stills[beat_id])
        elif beat_id.endswith("_compare"):
            turn = beat_id.split("_")[0].lstrip("t")
            name = f"turn-{int(turn):02d}.png"
            # +2.5s: past the caption fade-in, on the settled three-up
            still(start + min(2.5, float(beat["seconds"]) / 2), name)
            taken.append(name)
    analysis = next((beat for beat in beats if beat["id"] == "analysis_delay"), None)
    if analysis is not None:
        at = sum(float(beat["seconds"]) for beat in beats[:beats.index(analysis)]) + 1.5
        still(at, "04_analysis.png")
        taken.append("04_analysis.png")
    print(f"stills: {len(taken)} -> {args.out}")
    for name in taken:
        print("  ", name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
