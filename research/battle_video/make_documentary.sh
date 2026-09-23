#!/usr/bin/env bash
# Build the whole documentary from a finished battle record, in one command.
#
#   1. replay the recorded orders and verify the replay reproduced the battle
#   2. render a still per phase per viewpoint (god / axis / allies)
#   3. compose the beats and the narration from the record
#   4. narrate them (ChatTTS, pinned voice)
#   5. fold the measured durations in and render with Remotion
#   6. emit the report, the shooting script and the subtitles
#
# Every step is idempotent, and step 1 is a *check*: if the replay does not reproduce
# the battle, the frames would be fiction, so the script stops rather than rendering
# a video about a battle that never happened.
#
# Usage: research/battle_video/make_documentary.sh [battle_dir_name]
set -euo pipefail

BATTLE="${1:-battle_em01}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
PY="$ROOT/.venv/bin/python"
TTS_PY="/Users/Zhuanz1/Desktop/code/seawar/.venv_tts/bin/python"
FONT="/System/Library/Fonts/Supplemental/Songti.ttc"   # CJK without tofu boxes

cd "$ROOT"
echo "== 1/6 重演并核验 $BATTLE =="
IBS_REPORT_FONT="$FONT" "$PY" research/battle_video/replay_battle.py \
  --battle "$BATTLE" --verify --render --out "$HERE/frames" | tail -12

echo "== 2/6 三视图帧已生成：$(ls "$HERE/frames"/*.png | wc -l | tr -d ' ') 张 =="

echo "== 3/6 合成时间线与解说词 =="
"$PY" research/battle_video/build_timeline.py --battle "$BATTLE" \
  --audio-manifest "$HERE/audio/vo/manifest.json"

echo "== 4/6 配音（ChatTTS，固定音色） =="
"$TTS_PY" research/battle_video/tts_speak.py \
  --script "$HERE/audio/script.json" --out "$HERE/audio/vo"

echo "== 5/6 折叠实测时长并渲染 =="
"$PY" research/battle_video/build_timeline.py --battle "$BATTLE" \
  --audio-manifest "$HERE/audio/vo/manifest.json"
mkdir -p "$HERE/out"
(cd "$HERE/remotion" && npx remotion render Documentary "$HERE/out/documentary.mp4" \
   --props="$HERE/data/render_props.json" --public-dir="$HERE" --log=error)

echo "== 6/6 战报 / 解说词 / 字幕 =="
"$PY" research/battle_video/build_report.py --battle "$BATTLE" --props "$HERE/data/render_props.json"
"$PY" research/battle_video/qc_video.py --video "$HERE/out/documentary.mp4" \
  --props "$HERE/data/render_props.json" --srt "$HERE/data/subtitles.srt"

echo
echo "完成："
echo "  视频   $HERE/out/documentary.mp4"
echo "  战报   research/command_delay/$BATTLE/REPORT.md"
echo "  解说词 $HERE/data/narration_script.md"
echo "  字幕   $HERE/data/subtitles.srt"
