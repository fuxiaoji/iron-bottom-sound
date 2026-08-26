"""从已跑完的对局重建战报：用封存的订单确定性重放，重拍 UI 截图，重嵌 markdown。

适用场景：对局已完成但截图/报告体积过大（base64 PNG 撑到 100MB+），或截图需要重拍。
不需要再调 LLM：订单来自最终状态的 sealed_orders，引擎 RNG 由 (seed, rng_counter)
确定性推进 → 重放事件与原始对局逐条一致，叙事/思考/计划表条目原样保留在 DB 中。

用法：
  python -m backend.scripts.regen_report_screenshots --db backend/reports/vs-llm-*.sqlite3

重建后战报：backend/reports/<game_id>-battle-report.md（压缩截图内嵌）。
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "backend" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

_REPORT_DIR = _ROOT / "backend" / "reports"

# —— 必须在 import api 之前设置：api.repository / api.reports_root 在模块级读取这些
# 环境变量（api.py:49）。argparse 在 main() 里才跑，故此处用最小的 argv 解析先拿 --db。
if __name__ == "__main__":
    _db_arg: str | None = None
    for _i, _token in enumerate(sys.argv):
        if _token == "--db" and _i + 1 < len(sys.argv):
            _db_arg = sys.argv[_i + 1]
        elif _token.startswith("--db="):
            _db_arg = _token.split("=", 1)[1]
    if _db_arg:
        os.environ["IBS_DB_PATH"] = str(Path(_db_arg).resolve())
    os.environ["IBS_REPORTS_DIR"] = str(_REPORT_DIR)

from _ui_common import UIScreenshotRenderer, start_server  # noqa: E402

from iron_bottom_sound import api  # noqa: E402
from iron_bottom_sound.battle_report import (  # noqa: E402
    build_report_data,
    build_report_markdown,
    capture_phase_snapshot,
)
from iron_bottom_sound.engine import ORDER_PHASES  # noqa: E402
from iron_bottom_sound.models import GameState, OrderBatch, Phase, Side  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="重放已跑完对局，重拍截图并重建战报")
    parser.add_argument("--db", required=True, type=Path, help="该局 sqlite（vs-llm-*.sqlite3）")
    parser.add_argument("--port", type=int, default=8199)
    args = parser.parse_args()

    db = args.db.resolve()
    if not db.is_file():
        print(f"找不到数据库: {db}", file=sys.stderr)
        return 2

    # 原局 DB 战报条目由 api.repository 读取（env 已在模块级指向本库）；重放只写 PNG。
    con = sqlite3.connect(str(db))
    row = con.execute("SELECT state_json FROM games").fetchone()
    con.close()
    final = GameState.model_validate_json(row[0])
    game_id = final.game_id
    sealed = final.sealed_orders
    print(f"对局 {game_id} · {final.scenario_id} seed={final.seed} · sealed 订单 {len(sealed)} 组")

    # 复用模块级 engine：uvicorn 线程里的 API 从 api.engine 读状态（见 get_game），
    # 与原始 run_vs_llm_report 一致 —— 否则服务器读不到重放中的对局。
    engine = api.engine
    state = engine.reset(final.scenario_id, final.seed, final.options, game_id=game_id)

    server = start_server(api.app, args.port)
    renderer = UIScreenshotRenderer(f"http://127.0.0.1:{args.port}")
    try:
        capture_phase_snapshot(
            None, api.reports_root, state, engine, state.turn, state.phase.value,
            renderer=renderer,
        )
        steps = 0
        while state.phase != Phase.COMPLETE and steps < 200:
            steps += 1
            if state.phase in ORDER_PHASES:
                key = f"{state.turn}:{state.phase.value}"
                batches = sealed[key]
                for side in Side:
                    batch = OrderBatch.model_validate(batches[side.value])
                    result = engine.submit_orders(game_id, batch)
                    if not result.valid:
                        raise RuntimeError(
                            f"重放失败：{side.value} 在 {key} 的封存订单被拒: {result.errors}"
                        )
            prev_phase = state.phase
            engine.advance(game_id)
            state = engine.get(game_id)
            label = prev_phase.value
            turn = state.turn
            if prev_phase == Phase.FIRE_END:
                label = "fire_end"
                turn = state.turn - 1 if state.phase == Phase.REINFORCEMENT else state.turn
            capture_phase_snapshot(
                None, api.reports_root, state, engine, turn, label, renderer=renderer
            )
            print(f"[{steps}] {prev_phase.value} → {state.phase.value}（回合 {state.turn}）",
                  flush=True)

        # 确定性校验：重放终态须与原始对局一致（回合数/胜负）；事件数须与 DB 事件审计一致。
        orig_winner = final.winner.value if final.winner else None
        replay_winner = state.winner.value if state.winner else None
        events_match = len(state.events) == len(api.repository.events(game_id))
        match = (
            state.phase == Phase.COMPLETE
            and state.turn == final.turn
            and replay_winner == orig_winner
            and events_match
        )
        print(f"完成：{state.phase == Phase.COMPLETE} · 重放与原始对局一致: {match} "
              f"(回合 {state.turn}，胜负 {replay_winner or '—'}，"
              f"事件 {len(state.events)}/{len(api.repository.events(game_id))})")

        data = build_report_data(state, engine, api.repository.battle_entries(game_id))
        md = build_report_markdown(api.reports_root, data, game_id)
        out = _REPORT_DIR / f"{game_id}-battle-report.md"
        out.write_text(md, encoding="utf-8-sig")
        print(f"战报：{out}（{out.stat().st_size // (1024*1024)} MB）")
        return 0
    finally:
        renderer.close()
        server.should_exit = True


if __name__ == "__main__":
    raise SystemExit(main())
