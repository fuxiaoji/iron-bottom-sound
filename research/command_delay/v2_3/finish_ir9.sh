#!/usr/bin/env bash
# Wait for the IR-9 battle to finish, then run its three post-processing steps.
# Written so the batch completes without a human (or an agent) sitting on it:
# the driver writes "DONE turns=" as its last line, and everything after that is
# deterministic post-processing.
set -euo pipefail
# three levels up: v2_3 -> command_delay -> research -> the repository root
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."
LOG=research/command_delay/v2_3/logs/ir9_battle.log
BATTLE=battle_v2_3

until grep -q "^DONE turns=" "$LOG" 2>/dev/null; do sleep 60; done
echo "battle finished at $(date +%H:%M:%S)" >> research/command_delay/v2_3/logs/ir9_postprocess.log

{
  echo "== replay verification =="
  IBS_REPORT_FONT="/System/Library/Fonts/Supplemental/Songti.ttc" \
    /Users/Zhuanz1/Desktop/code/seawar/iron-bottom-sound/.venv/bin/python \
    research/battle_video/replay_battle.py --battle "$BATTLE" --verify
  echo "== leak scan =="
  /Users/Zhuanz1/Desktop/code/seawar/iron-bottom-sound/.venv/bin/python \
    research/battle_video/scan_provider_battle.py --battle "$BATTLE"
  echo "== leak positive control =="
  /Users/Zhuanz1/Desktop/code/seawar/iron-bottom-sound/.venv/bin/python \
    research/battle_video/scan_provider_battle.py --battle "$BATTLE" --self-test
  echo "== IR-9 report and assertions =="
  /Users/Zhuanz1/Desktop/code/seawar/iron-bottom-sound/.venv/bin/python \
    research/command_delay/v2_3/ir9_battle_report.py --battle "$BATTLE"
  echo "== done $(date +%H:%M:%S) =="
} >> research/command_delay/v2_3/logs/ir9_postprocess.log 2>&1
