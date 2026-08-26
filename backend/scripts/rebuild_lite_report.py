"""从已跑完的对局重建「轻量战报」：不内嵌 base64，图片用相对路径引用。

背景：自包含 MD（92 张 base64 内嵌）约 28MB，编辑器/预览器打不开。轻量版 HTML/MD
只有几十 KB，浏览器/VS Code/Typora 双击即开，图片从同级目录即时加载。

用法：
  python -m backend.scripts.rebuild_lite_report --db backend/reports/vs-llm-*.sqlite3

产物（均在 backend/reports/ 下，与图片目录 <game_id>/ 同级）：
  <game_id>-battle-report.html     轻量 HTML（浏览器秒开，含目录锚点）
  <game_id>-battle-report-lite.md  轻量 MD（相对路径引用）
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "backend" / "src"))

_REPORT_DIR = _ROOT / "backend" / "reports"

# —— 必须在 import api 之前设置（api.repository/reports_root 在模块级读取）。——
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

from iron_bottom_sound import api  # noqa: E402
from iron_bottom_sound.battle_report import (  # noqa: E402
    build_report_data,
    build_report_html,
    build_report_markdown_lite,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="重建轻量战报（相对路径引用本地图片）")
    parser.add_argument("--db", required=True, type=Path, help="该局 sqlite（vs-llm-*.sqlite3）")
    args = parser.parse_args()

    db = args.db.resolve()
    if not db.is_file():
        print(f"找不到数据库: {db}", file=sys.stderr)
        return 2

    game_ids = api.repository.game_ids()
    if len(game_ids) != 1:
        print(f"期望该库只有一局，实际 {len(game_ids)} 局: {game_ids}", file=sys.stderr)
        return 2
    game_id = game_ids[0]
    state = api.repository.load(game_id)
    api.engine.games[game_id] = state  # 让 engine.observe / 公开事件可见性可算

    data = build_report_data(state, api.engine, api.repository.battle_entries(game_id))
    html = build_report_html(data, game_id)
    html_path = Path(api.reports_root) / f"{game_id}-battle-report.html"
    html_path.write_text(html, encoding="utf-8")
    md = build_report_markdown_lite(data, game_id)
    md_path = Path(api.reports_root) / f"{game_id}-battle-report-lite.md"
    md_path.write_text(md, encoding="utf-8-sig")

    print(f"HTML: {html_path}（{html_path.stat().st_size // 1024} KB）")
    print(f"MD  : {md_path}（{md_path.stat().st_size // 1024} KB）")
    print(f"比分：轴心 {data['meta']['score']['axis']} : 同盟 {data['meta']['score']['allies']}"
          f" · 回合 {data['meta']['turn']} · 阶段 {len([p for t in data['turns'] for p in t['phases']])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
