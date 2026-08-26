"""想定一 状态机（进化冠军）vs DeepSeek LLM 演示局 + 改进战报。

用法：
  # 真局（轴心=进化冠军，同盟=DeepSeek pro，含 LLM 思考与每阶段叙事）
  DEEPSEEK_API_KEY=<key> DEEPSEEK_MODEL=deepseek-v4-pro python -m backend.scripts.run_vs_llm_report \
      --scenario IBS-S-01 --seed 7 --axis-profile evolved --llm-side allies

  # 冒烟局（不调 LLM，双方战术风格；验证管线 + UI 截图 + 战报 MD）
  python -m backend.scripts.run_vs_llm_report --scenario IBS-S-01 --dry

产物：
  backend/reports/<game_id>-battle-report.md  自包含战报（截图 base64 内嵌）
  backend/reports/<game_id>/turn-*.png        真实 UI 截图（报告视图）
  backend/reports/vs-llm-*.sqlite3            本局 SQLite（战报条目/事件）

安全：DEEPSEEK_API_KEY 只从环境变量读取，绝不落盘/落库/进仓库。
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from pathlib import Path

# —— 必须在 import api 之前设置：api 模块级 engine/repository/reports_root 启动时读取。 ——
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "backend" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

_REPORT_DIR = _ROOT / "backend" / "reports"
# 每局独立 sqlite：api 模块 import 时即打开文件（Windows 不允许随后删除），故按局命名。
_DB_PATH = _REPORT_DIR / f"vs-llm-{uuid.uuid4().hex[:8]}.sqlite3"

os.environ["IBS_DB_PATH"] = str(_DB_PATH)
os.environ["IBS_REPORTS_DIR"] = str(_REPORT_DIR)

from _ui_common import UIScreenshotRenderer, start_server  # noqa: E402

from iron_bottom_sound import api  # noqa: E402
from iron_bottom_sound.battle_report import (  # noqa: E402
    build_report_data,
    build_report_markdown,
    capture_after_advance,
    capture_ai_action,
    capture_phase_snapshot,
)
from iron_bottom_sound.champions import CHAMPIONS  # noqa: E402
from iron_bottom_sound.engine import ORDER_PHASES  # noqa: E402
from iron_bottom_sound.llm import OpenAICompatibleCommander  # noqa: E402
from iron_bottom_sound.models import GameOptions, Phase, Side  # noqa: E402
from iron_bottom_sound.tactical import PROFILES, TacticalCommander  # noqa: E402


def _resolve_profile(name: str):
    return CHAMPIONS.get(name) or PROFILES.get(name) or PROFILES["balanced"]


def main() -> int:
    parser = argparse.ArgumentParser(description="状态机 vs LLM 演示局 + 改进战报")
    parser.add_argument("--scenario", default="IBS-S-01", choices=("IBS-S-01", "IBS-S-03"))
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--axis-profile", default="evolved",
                        help="状态机侧风格（默认进化冠军 CHAMPIONS['evolved']）")
    parser.add_argument("--allies-profile", default="balanced")
    parser.add_argument("--llm-side", default="allies", choices=("axis", "allies"))
    parser.add_argument("--model", default=None,
                        help="LLM 模型（缺省取环境变量 DEEPSEEK_MODEL，再缺省 deepseek-v4-pro）")
    parser.add_argument("--port", type=int, default=8199)
    parser.add_argument("--dry", action="store_true",
                        help="冒烟局：双方战术风格、不调 LLM（叙事走确定性回退）")
    args = parser.parse_args()

    model = args.model or os.environ.get("DEEPSEEK_MODEL") or "deepseek-v4-pro"
    llm_side = Side(args.llm_side)
    profile_side = llm_side.opponent

    if args.dry:
        commander_for = {
            Side.AXIS: TacticalCommander(profile=_resolve_profile(args.axis_profile)),
            Side.ALLIES: TacticalCommander(profile=_resolve_profile(args.allies_profile)),
        }
        narrative_commander = None
    else:
        commander_for = {
            Side.AXIS: TacticalCommander(profile=_resolve_profile(args.axis_profile)),
            Side.ALLIES: TacticalCommander(profile=_resolve_profile(args.allies_profile)),
        }
        commander_for[llm_side] = OpenAICompatibleCommander(
            model=model, thinking_enabled=True, timeout=90
        )
        narrative_commander = OpenAICompatibleCommander(model=model, timeout=30, max_tokens=800)

    # 建局（与 api.create_game 一致：reset → save → 开局快照）。
    options = GameOptions(mode="llm", battle_report=True, ai_profile=args.axis_profile)
    state = api.engine.reset(args.scenario, args.seed, options)
    game_id = state.game_id
    api.repository.save(state)

    server = start_server(api.app, args.port)
    base_url = f"http://127.0.0.1:{args.port}"
    renderer = UIScreenshotRenderer(base_url)
    try:
        if options.battle_report:
            capture_phase_snapshot(
                api.repository, api.reports_root, state, api.engine,
                state.turn, state.phase.value, renderer=renderer,
            )

        started = time.perf_counter()
        steps = 0
        while state.phase != Phase.COMPLETE and steps < 200:
            steps += 1
            if state.phase in ORDER_PHASES:
                for side in Side:
                    plan, batch, audits = commander_for[side].choose_plan(api.engine, game_id, side)
                    result = api.engine.submit_orders(game_id, batch)
                    if not result.valid:
                        raise RuntimeError(f"{side.value} 订单被引擎拒绝: {result.errors}")
                    if options.battle_report:
                        reasoning = audits[-1].reasoning_content if audits else None
                        capture_ai_action(
                            api.repository, game_id, state.turn, state.phase.value,
                            side.value, plan, reasoning, audits, state,
                        )
            prev_phase = state.phase
            api.engine.advance(game_id)
            state = api.engine.get(game_id)
            if options.battle_report:
                capture_after_advance(
                    api.repository, api.reports_root, state, api.engine,
                    prev_phase, commander=narrative_commander, renderer=renderer,
                )
            api.repository.save(state)
            print(f"[{steps}] {prev_phase.value} → {state.phase.value}（回合 {state.turn}）",
                  flush=True)

        elapsed = time.perf_counter() - started
        data = build_report_data(state, api.engine, api.repository.battle_entries(game_id))
        md = build_report_markdown(api.reports_root, data, game_id)
        out = _REPORT_DIR / f"{game_id}-battle-report.md"
        # utf-8-sig：带 BOM，中文 Windows 编辑器/VS Code 才不误判 GBK 乱码。
        out.write_text(md, encoding="utf-8-sig")
        score = data["meta"]["score"] or {}
        axis_side_desc = "进化冠军" if not args.dry else "战术风格"
        llm_desc = "DeepSeek LLM" if not args.dry else "战术风格"
        print("=" * 60)
        print(f"想定：{state.scenario_title}（{state.scenario_id}） seed={args.seed}"
              f"{' · 冒烟局(无 LLM)' if args.dry else ''}")
        print(f"轴心：{axis_side_desc if profile_side == Side.AXIS else llm_desc}"
              f"　同盟：{llm_desc if profile_side == Side.AXIS else axis_side_desc}")
        print(f"完成：{state.phase == Phase.COMPLETE}"
              f"（模型 {model if not args.dry else '—'}）")
        print(f"比分：轴心 {score.get('axis', 0)} : 同盟 {score.get('allies', 0)}")
        print(f"耗时：{elapsed:.1f}s · 阶段推进 {steps} 步")
        print(f"战报：{out}")
        return 0
    finally:
        renderer.close()
        server.should_exit = True


if __name__ == "__main__":
    raise SystemExit(main())
