"""Narrate a script with an open-source TTS, one file per line, reproducibly.

The documentary needs a **male Chinese narrator**, offline, and a voice that does not
change between renders: a re-cut scene must not suddenly have a different man reading
it.  So the speaker embedding is generated once and kept in ``voice_spk.json``; every
later run reads it back.

Engine: ChatTTS (2noise/ChatTTS, ~35k stars).  Chosen after checking the alternatives
rather than assuming: the Mandarin voice list of Kokoro/MeloTTS/Piper is female-only,
and CosyVoice/IndexTTS/GPT-SoVITS want a reference recording to clone - which is a
rights question this project will not take on for a museum-piece battle.  ChatTTS
samples a speaker from the model itself, needs no reference, and its default timbre is
male.  The runner-up is ``edge-tts`` (zh-CN-YunjianNeural), which is a *service client*
rather than an open model, so it is only a fallback and must be labelled as such.

Usage::

    .venv_tts/bin/python research/battle_video/tts_speak.py \
        --script research/battle_video/audio/script.json --out research/battle_video/audio/vo
    .venv_tts/bin/python research/battle_video/tts_speak.py --engine edge --dry-run

``script.json`` is ``{"lines": [{"id": "t1_intro", "text": "…", "speed": 1.0}, …]}``.
Outputs ``vo/<id>.wav`` plus ``vo/manifest.json`` with the real duration of every line
(measured with ffprobe), which is what the subtitle timeline is built from.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHATTTS_SRC = Path("/Users/Zhuanz1/Desktop/code/seawar/.tts_src/ChatTTS")
SPK_FILE = HERE / "voice_spk.json"


def _load_chattts():
    sys.path.insert(0, str(CHATTTS_SRC))
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "0")
    import torch
    import ChatTTS

    chat = ChatTTS.Chat()
    if not chat.load(source="huggingface", compile=False):
        raise SystemExit("ChatTTS failed to load")
    return chat, torch


def _speaker(chat, torch, *, fresh: bool = False) -> list[float]:
    if SPK_FILE.exists() and not fresh:
        return json.loads(SPK_FILE.read_text(encoding="utf-8"))["spk_emb"]
    torch.manual_seed(20260924)  # a fixed seed means a fixed narrator
    spk = chat.sample_random_speaker()
    SPK_FILE.write_text(
        json.dumps({"spk_emb": spk, "note": "fixed narrator embedding for the documentary",
                    "engine": "ChatTTS", "seed": 20260924}, ensure_ascii=False),
        encoding="utf-8",
    )
    return spk


def _relative(path: Path) -> str:
    """Path for the manifest: relative to this package when it is inside it."""
    try:
        return str(path.resolve().relative_to(HERE))
    except ValueError:
        return str(path.resolve())


def _duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return round(float(out), 3)


def synth_chattts(lines: list[dict], out_dir: Path, *, fresh_voice: bool = False,
                  temperature: float = 0.25, top_p: float = 0.65) -> list[dict]:
    import numpy as np
    import soundfile as sf

    chat, torch = _load_chattts()
    spk = _speaker(chat, torch, fresh=fresh_voice)
    params = chat.InferCodeParams(spk_emb=spk, temperature=temperature, top_P=top_p, top_K=20)
    manifest: list[dict] = []
    for index, line in enumerate(lines, 1):
        text = str(line["text"]).strip()
        if not text:
            continue
        started = time.monotonic()
        wavs = chat.infer([text], params_infer_code=params, use_decoder=True)
        audio = np.asarray(wavs[0], dtype="float32")
        path = out_dir / f"{line['id']}.wav"
        sf.write(path, audio, 24000)
        record = {
            "id": line["id"],
            "text": text,
            "path": _relative(path),
            "seconds": _duration(path),
            "synth_seconds": round(time.monotonic() - started, 2),
            "sample_rate": 24000,
            "engine": "ChatTTS",
            "rms": round(float(np.sqrt(np.mean(audio ** 2))), 4),
        }
        manifest.append(record)
        print(f"[{index}/{len(lines)}] {record['id']:<22} {record['seconds']:>6.2f}s "
              f"rms={record['rms']:.3f} synth={record['synth_seconds']}s", flush=True)
    return manifest


def synth_edge(lines: list[dict], out_dir: Path, *, voice: str = "zh-CN-YunjianNeural",
               rate: str = "-8%") -> list[dict]:
    """Fallback: Microsoft's service voices via the edge-tts client.

    Labelled everywhere it is used: this is a networked **service**, not an open model,
    and it is only here so a documentary can still ship if a local model will not run.
    """
    import asyncio

    import edge_tts

    manifest: list[dict] = []
    for index, line in enumerate(lines, 1):
        text = str(line["text"]).strip()
        if not text:
            continue
        path = out_dir / f"{line['id']}.wav"
        mp3 = path.with_suffix(".mp3")
        asyncio.run(edge_tts.Communicate(text, voice, rate=rate).save(str(mp3)))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3),
                        "-ar", "24000", "-ac", "1", str(path)], check=True)
        mp3.unlink()
        record = {
            "id": line["id"], "text": text, "path": _relative(path),
            "seconds": _duration(path), "sample_rate": 24000,
            "engine": f"edge-tts:{voice}", "service": True,
        }
        manifest.append(record)
        print(f"[{index}/{len(lines)}] {record['id']:<22} {record['seconds']:>6.2f}s "
              f"({record['engine']})", flush=True)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", type=Path,
                        default=HERE / "audio" / "script.json")
    parser.add_argument("--out", type=Path, default=HERE / "audio" / "vo")
    parser.add_argument("--engine", default="chattts", choices=["chattts", "edge"])
    parser.add_argument("--fresh-voice", action="store_true",
                        help="draw a new narrator embedding (default: reuse voice_spk.json)")
    parser.add_argument("--voice", default="zh-CN-YunjianNeural")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    script = json.loads(args.script.read_text(encoding="utf-8"))
    lines = script["lines"] if isinstance(script, dict) else script
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    print(f"engine={args.engine} lines={len(lines)} out={args.out}")
    if args.dry_run:
        for line in lines[:3]:
            print("  ", line["id"], "->", str(line["text"])[:60])
        return 0

    manifest = (
        synth_chattts(lines, args.out, fresh_voice=args.fresh_voice)
        if args.engine == "chattts" else synth_edge(lines, args.out, voice=args.voice)
    )
    (args.out / "manifest.json").write_text(
        json.dumps({"engine": args.engine, "lines": manifest}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    total = sum(item["seconds"] for item in manifest)
    print(f"\nnarrated {len(manifest)} lines, {total/60:.1f} min total -> {args.out}/manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
