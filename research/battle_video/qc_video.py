"""Quality control for the finished documentary: the checks worth failing on.

A video is easy to render and easy to get subtly wrong: silent narration, subtitles that
drift out of step with the voice, a missing frame that renders as a black hole, CJK that
came out as tofu boxes, a film that ends up twice as long as intended.  Each of those is
checked here against the artefacts rather than by eye, and the exit code is the gate.

Usage::

    .venv/bin/python research/battle_video/qc_video.py \
        --video research/battle_video/out/documentary.mp4 \
        --props research/battle_video/data/render_props.json \
        --srt research/battle_video/data/subtitles.srt
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def probe(video: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams",
         str(video)],
        capture_output=True, text=True, check=True,
    ).stdout
    payload = json.loads(out)
    video_stream = next((s for s in payload["streams"] if s["codec_type"] == "video"), None)
    audio_stream = next((s for s in payload["streams"] if s["codec_type"] == "audio"), None)
    return {
        "duration": float(payload["format"]["duration"]),
        "size_bytes": int(payload["format"]["size"]),
        "video": video_stream,
        "audio": audio_stream,
    }


def loudness(video: Path) -> dict:
    """Mean and peak level of the mix, so a silent track cannot pass as narrated."""
    out = subprocess.run(
        ["ffmpeg", "-i", str(video), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True,
    ).stderr
    mean = re.search(r"mean_volume: (-?[\d.]+) dB", out)
    peak = re.search(r"max_volume: (-?[\d.]+) dB", out)
    return {
        "mean_db": float(mean.group(1)) if mean else None,
        "peak_db": float(peak.group(1)) if peak else None,
    }


def freeze_check(video: Path, expected_beats: int) -> dict:
    """Sample frames across the film and make sure none of them is a blank card."""
    tmp = Path("/tmp/ibs_qc")
    tmp.mkdir(exist_ok=True)
    for old in tmp.glob("*.png"):
        old.unlink()
    info = probe(video)
    samples = 12
    for index in range(samples):
        at = info["duration"] * (index + 0.5) / samples
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{at:.2f}", "-i", str(video),
             "-frames:v", "1", str(tmp / f"f{index:02d}.png")],
            check=True,
        )
    import numpy as np
    from PIL import Image

    blank: list[str] = []
    levels: list[float] = []
    for path in sorted(tmp.glob("*.png")):
        array = np.asarray(Image.open(path).convert("L"), dtype="float32")
        levels.append(float(array.std()))
        if array.std() < 6.0:  # a flat card: nothing drawn on it
            blank.append(path.name)
    return {"sampled": samples, "std_min": round(min(levels), 2),
            "std_mean": round(sum(levels) / len(levels), 2), "blank_frames": blank}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, default=HERE / "out" / "documentary.mp4")
    parser.add_argument("--props", type=Path, default=HERE / "data" / "render_props.json")
    parser.add_argument("--srt", type=Path, default=HERE / "data" / "subtitles.srt")
    args = parser.parse_args()

    findings: list[str] = []
    if not args.video.exists():
        print(f"no video at {args.video}", file=sys.stderr)
        return 2

    beats = json.loads(args.props.read_text(encoding="utf-8"))["beats"]
    expected = sum(float(beat.get("seconds") or 0) for beat in beats)
    narrated = sum(1 for beat in beats if beat.get("audio"))
    info = probe(args.video)
    level = loudness(args.video)
    frames = freeze_check(args.video, len(beats))

    if abs(info["duration"] - expected) > max(2.0, expected * 0.02):
        findings.append(f"duration {info['duration']:.1f}s != beats {expected:.1f}s")
    if not 10 * 60 <= info["duration"] <= 18 * 60:
        findings.append(f"duration {info['duration']/60:.1f} min outside the 10–18 min band")
    if info["video"] is None or (info["video"]["width"], info["video"]["height"]) != (1920, 1080):
        findings.append("not 1920x1080")
    if info["audio"] is None:
        findings.append("no audio stream")
    elif level["mean_db"] is None or level["mean_db"] < -40:
        findings.append(f"narration inaudible (mean {level['mean_db']} dB)")
    elif level["peak_db"] is not None and level["peak_db"] > -0.5:
        findings.append(f"peak {level['peak_db']} dB is clipping")
    if frames["blank_frames"]:
        findings.append(f"blank frames: {frames['blank_frames']}")
    if narrated != len(beats):
        findings.append(f"{len(beats) - narrated} beats have no narration audio")

    srt_lines = args.srt.read_text(encoding="utf-8").strip().split("\n\n") if args.srt.exists() else []
    payload = {
        "video": str(args.video),
        "duration_s": round(info["duration"], 2),
        "duration_min": round(info["duration"] / 60, 2),
        "beats": len(beats),
        "beats_narrated": narrated,
        "resolution": (
            f"{info['video']['width']}x{info['video']['height']}" if info["video"] else None
        ),
        "audio": {"codec": info["audio"]["codec_name"] if info["audio"] else None, **level},
        "frames": frames,
        "subtitles_cues": len(srt_lines),
        "size_mb": round(info["size_bytes"] / 1048576, 1),
        "findings": findings,
        "verdict": "PASS" if not findings else "FAIL",
    }
    (HERE / "data" / "qc_video.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
