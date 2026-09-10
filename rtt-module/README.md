# RTT 平台模块（iron-bottom-sound）

按《RTT 模块开发指南》实现的 JS 移植：经典逐舰模式，16 个想定全部可玩（含双人对战、人机 AI、撤销）。

- 部署：`title.sql` 注册 + 本目录整体放入 `server/public/iron-bottom-sound/`，重启 server。
- 数据：`data.js` 由 `scripts/export_rtt_data.py` 从仓库 YAML 导出（单一事实源），改数据后重跑导出并 bump play.html 的 `?v=`。
- 测试：`node tests/verify_engine.js`（10 用例）+ `node tests/fuzz.js`（25 局随机压测，验收线 25/0/0）。
- 本地视觉预览（脱离平台）：`python3 -m http.server 8127` 后开 `preview.html`（A 键 = AI 代打未提交一方）。
- 与 Python 引擎的差异：真实编队模式、LLM 对战、教学、隐藏接触/盲雷/烟幕/探照灯/星弹可选规则、飑区漂移、碰撞损伤掷骰未移植；离场/返场、假目标算子等同原项目边界（见 IBS-Q-020）。
