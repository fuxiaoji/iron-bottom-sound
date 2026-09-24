# 已完成工作

本文件只追加完成记录；每次发布前补充对应提交哈希。

## 2026-09-03：修复真实模式“友军编队相撞并受伤”漏洞（敌方同格时友军仍该急停）

- **需求（用户）**：「我记得之前改进过状态机的逻辑，怎么还是会发生移动阶段不动和移动阶段和其他编队相撞的情况」，进一步确认「会有友军编队相撞情况」。经 AskUserQuestion 拍板本轮范围：**① 修友军碰撞漏洞（本轮）+ ② 计划期纵队解冲突（留后续轮，不做）**，未勾③/④。
- **复现与根因**：引擎 `_resolve_movement`（engine.py:3039-3058）的真实模式友军保护是**按整格分组“全同侧”才生效**——只要同一脉冲同落一格的几艘船里混入一艘敌舰，`len({side}) != 1 → continue` 整组失去保护；随后伤害循环（3059-3066）不区分阵营，仍把组内友军×友军掷 `_resolve_ship_collision`（4063）并结算 `collision_result` 伤害。复现（想定 3 真实模式 seed 1）：轴军 `卡尔·加尔斯德`+`理夏德·拜岑` 与一艘同盟舰同落 D5 → `collision_check`（真检定）+ 两条 `collision_result`（1H/-4MF）落在两友军身上。
- **修复（engine.py 一处）**：把“整组同侧才保护”改为**按同侧成组保护**——对每个同落格集合按阵营分组，任一阵营本格 ≥2 艘且尚未被停时，该阵营成员一律原地急停（回写 `destinations`+`stopped`+发 `formation_emergency_stop` IBS-R-RC-03）。语义：纯友军同格 {A,B} 照旧双双急停；**混入敌舰 {A,B,E}（漏洞场景）A/B 急停、E 单独进格，友军绝不被掷碰撞**；单友+单敌 {A,E} 无同侧对、敌我碰撞照旧保留；纯敌舰照旧。
- **回归测试**：`tests/test_realistic_command.py` 新增 `test_friendly_collision_never_damages_when_enemy_shares_the_hex`——IBS-S-03 真实模式 seed 1 取轴两舰+同盟一舰放同一空白格相邻格各朝向它，分轴/盟两个 batch 各发 `plan="1"`，直接 `_resolve_movement(state)`；断言全程无同侧 `collision_check`/`collision_result`、A/B 留在起点、E 进目标格（该断言与骰子无关）。**fail-first 实证**：`git stash push -- engine.py` 复跑新用例 → 失败在 `collision_check 卡尔·加尔斯德与理夏德·拜岑碰撞检定 5`（友军真检定）；`git stash pop` 还原后通过。复现脚本 `C:/tmp/repro_friendly.py` 同证：修复前友军 `collision_result` 2 条 → 修复后消失，换 `formation_emergency_stop`，A/B 停短在起点 C6/D4、E 单舰进 D5。
- **验证**：真实模式文件其余既有关键断言绿（18 passed，含全程无友军碰撞的 seed 回归系列；全剧本 legality 重用例在跑）。未部署（沿用「先做本地自查」）。**② 计划期纵队航迹解冲突**（治“本方两队挤停/整回合不推进”）作为后续轮待定。

## 2026-09-03：编队上限放开到 8 + 建立《铁底湾大决战》美日全主力自定义剧本

- **需求（用户）**：「帮我建立一个自定义剧本，包含美日双方所有战舰，提升编队数量为8个，根据历史建立战列线，雷击大队，屏卫大队，双方距离远一点」。经 AskUserQuestion 拍板：**重型全上、DD 每边 30**；**每侧 8 队（全剧 16 队）**；**全局放开到 8 队**；交付方式 = **先做本地自查，不上线**。
- **上限放开**：`realistic_command.MAX_FORMATIONS_PER_SIDE` 4 → 8（`validate_setup` 文案同步），前端 `scenario.MAX_WELLS_PER_SIDE=8`、工坊「新建分队」与超限提示随动；`tests/test_realistic_command.py` 两条断言改为按常量（目标用例 3 passed，含 8 队上限拒绝），`tsc` 0 错误。
- **剧本内容（111 艘 = 轴 54 / 同盟 57）**：轴（IJN）BB5 战列线「第一战列战队」（大和/武藏/信浓/长门/陆奥）+ CB2·CA4 巡洋战队 + 两组重巡战队 + 轻巡屏卫 + 三支「水雷战队」各 CL1+DD10；同盟（USN）两列战列线（衣阿华级 4 + 华盛顿/南达科塔/科罗拉多/西弗吉尼亚）+ CB2·CA4 重巡本队 + CA7 重巡前卫 + 轻巡屏卫 + 三支驱逐雷击大队各 CL1+DD10。DD 按 vp 降序取每边前 30。
- **布阵（历史纵队 × 拉开初距）**：两军各自 8 支纵队并排占海，纵队间距 2 hex、队内纵队间距 1~2（战列线/重巡大队 sp2，驱逐大队 sp1）；轴在西南（领舰锚点 q=13，r=10..24，朝 2 东南接近）、同盟在东北（q=31，r=2..16，朝 5 西北接近），**两军前沿直线距离 18 hex**，全部落位在 46×39 海图内、无重叠（逐舰 label 用引擎同套 `HexCoord.neighbor(尾向)×间距` 推导）。
- **本地验证（全程未上线）**：离线 `validate_definition` 0 错；重启本地 :8000 后 POST `/custom-scenarios` **201**（`IBS-CUSTOM-21E8908FE969`），GET 详情 111 艘、`setup.engine_default_formations` 轴/盟各 8 队且恰好覆盖全舰各一次；`POST /games` 真实模式热座建局成功，`suggested-orders` 每侧返回作者 8 队、无重复无遗漏；提交双方编队订单 `valid=true` 后推进开局，事件流生成 `axis-grand-1..8` 等 8+8 个 `formation_created`，阶段进入 `reinforcement`——**8 队/16 队真实模式在引擎内完整可玩**。未部署（沿用「先做本地自查」）。

## 2026-09-03：修复剧本工坊「不能创建分队」与「选船未按舰种排序」

- **需求（用户）**：「编组分队哪里不能创建分队，选船哪里按舰种排序，修复一下」。
- **根因（编队）**：`editor/scenario.ts` 的 `moveShipInto`/`changeShipSide` 原先调 `dropShip`——摘出纵队时连 `ships` 名单一起删掉，拖拽"搬动"会静默删舰，导致只能在已有井里归队、无法新开编队。新增仅摘纵队的 `detachShip`（保留名单），`moveShipInto`/`changeShipSide` 改用它；`dropShip` 仅保留给「取消选择」。
- **新增分队能力**：新增 `pairSolosIntoWell(state,side,leadId,followerId)`——取两艘散舰开一列新编队（先落者为领舰，index0），受「每侧 ≤4 队 ≥2 舰编队」上限约束。`FormationAssignStep` 头栏新增「＋ 新建分队」按钮（散舰 ≥2 且编队 <4 时可用，取最先两艘散舰）；散舰芯片本身也可作投放目标——把一艘散舰拖到另一艘上即开新队（`stopPropagation` 避免同时落到托盘空投区）。
- **次要隐患（顺带修复）**：新列 id 原为 `{side}-col-{序号}`，拆分/配对后列序乱掉、序号复用会撞出两列同 id（丢舰）。`makeColumn` 改发全局自增唯一 id（名字与默认锚点仍按 ordinal），配对、拾取、托盘等追加路径全部安全；用 Vite SSR 跑断言验证：搬动/配对全程名单 5→8 不丢、无重复 columnId、配对后 `realisticCapable` 正确翻转、默认锚点纵队无布局错误。
- **选船排序（按舰种）**：第 1 步「挑选舰船」列表排序从「可选用在前 + id」改为**按舰种分组**：BB→BC→CB→CA→CL→DD→APD→AV（主力舰在前，目录未收录的类型兜底排后），同型内可选舰（完整档案）在前、未建档在后，id 作稳定次序。
- **验证**：`tsc -p tsconfig.json` 0 错误；Vite dev（:5173）对改动的 `CustomScenarioEditor.tsx`/`FormationAssignStep.tsx`/`scenario.ts` 转换均 200。未部署（沿用「先不上，我自查后再部署」）。

## 2026-09-03（同日补充）：剧本工坊入口提供「导入剧本」选项（他人 .json / 服务器存档）

- **需求（用户）**：「自定义剧本点进后应该提供一个导入剧本选项，可以导入其他人的json剧本或者在服务器上保存的剧本」。
- **问题**：导入能力原本只在第 5 步（导出/导入/启动）卡片里，而顶栏步骤导航只允许回跳、不允许前跳，必须先从 0 步一路挑满舰船才够到第 5 步——点进工坊想导入根本没有入口。
- **改动（前端 `CustomScenarioEditor.tsx` + `style.css`）**：
  - 在步骤进度条下方加常驻工具条按钮「⇪ 导入剧本（他人 .json / 服务器存档）」，进入工坊即见，任一步骤可用。
  - 点开为导入弹窗（`.editor-modal`，backdrop 点击/Esc 语义关闭）：① 选择他人导出的《铁底湾剧本-*.json》文件载入（复用现有 `onImportFile` 解析/校验）；② 载回服务器上已保存的剧本（列表即开即删，沿用 `customScenarios`/`loadSaved`/`deleteCustomScenario`）；③ 附带仍提供「以内置想定为模板改编」。
  - `loadBuiltin`/`onImportFile` 改为返回成功布尔；载入成功即回到第 1 步回填编辑状态（`applyBodyWithMeta`），失败留在原页内联报错；已有选舰时导入前 `confirm` 提示会替换当前未保存内容。
- **验证**：`tsc -p tsconfig.json` 0 错误；Vite dev 对 `CustomScenarioEditor.tsx` 转换 200。未部署。


## 2026-08-26（批次 5）：人类下订单可选状态机 AI 半自动指导 + 部署线上

- **需求（用户）**：「我希望在人类对战时可以选择不同风格的状态机ai做半自动指导，就是自动选择，完成后同步服务器」。经 AskUserQuestion：**选择器范围 = 所有人类下订单的模式**（hotseat 双人 + vs_ai 人机 + llm 人类一方，教程关除外），每方各自选风格。
- **后端（`api.py` suggested-orders，1 处改动）**：新增 `profile: str = "balanced"` query 参数，解析 `CHAMPIONS.get(profile, PROFILES.get(profile))`（与 ai-opponent 完全一致，未知名 `HTTPException(422)`），`TacticalCommander(profile=style).choose_orders(...)` 按所选风格返回引擎已校验的可编辑 OrderBatch → 人类在编辑器确认/手改后提交。半自动=AI 只预填草稿，最终仍人类确认、引擎唯一裁决；建议不进战报 ai_action。
- **前端**：`api.ts` suggestedOrders 带 `?profile=`；`App.tsx` 加 `guideProfiles: Record<Side,string>`（每方独立记忆），订单编辑器内、PlanSheet 上方加「自动指导风格」bar（`mode!=="tutorial"` 显示，AI_PROFILES optgroup 分「内置风格/进化冠军」，切换即 `suggestedOrders` 自动重填本阶段草稿 + 显示所选风格 intro 一行「仅建议可手改」）；`style.css` 加 `.guide-bar/.guide-intro`。
- **测试**：`test_api_ai_opponent.py` 新增 `test_suggested_orders_profile_selects_ai_style`（`?profile=evolved` 返回 batch 且 `POST /orders` 200；`?profile=torpedo` 同；`?profile=nope` → 422）。全量 **336 passed**（含批次 4 之前的 335 + 新增 1）。
- **部署**（沿用批次 4 paramiko 流 + 记忆两个坑）：打包排除 `.git/tmp/node_modules/artifacts/dist/backend/reports/__pycache__/.venv/.pytest-*/.pt-run-*/.env` 及 `*.sqlite3*`（101MB/475 项，资源 PDF 未变但随包重传，安全第一）；服务器 `.venv/bin/python` 导入检查 OK；`npm install && npm run build -- --base=/tiedi/` → 新 bundle `index-CNZdkanC.js`（含「guide-bar」「自动指导风格」）；`systemctl restart tiedi` active；验证局 `e3191f1f-...`（seed 31，hotseat）写入线上 DB（无科研同意，不碍事）。
- **线上验证**：三端点 200（scenarios/root/counter，127.0.0.1:8001 直测）+ 公共域名 `https://fuwenji.asia/tiedi/` 200；`suggested-orders?profile=torpedo` → **200**、`?profile=nope` → **422**（风格解析真上线）；grep 服务器 `api.py:173` 新分支 + bundle 新字符串确认新代码。
- **部署脚本**：`/tmp/ibs_deploy.py`（打包→SFTP→解包→导入检查→npm build→restart→curl/grep，支持 `dry`/`deploy`/`verify` 三模式），未入库。

## 2026-08-23

- 完成全部来源的只读盘点、哈希核验与逐页首轮视觉检查。
- 确认两份舰船记录手册为完全相同的重复文件。
- 确认资料包含 14 个想定、241 个地图/单位/UI 素材、38 张舰级记录图。
- 锁定技术路线、规则权威顺序、首批想定、热座模式、可选规则与 LLM 边界。
- 建立 `main` 治理/语料基线提交 `6d8c42f`，并创建本地标签 `v0.1.0-corpus`。
- 只读导入 285 个规范文件，对应 286 条原始路径；所有 PDF、DOCX、XLSX、JPG、PNG 均由 Git LFS 跟踪。
- 生成 SHA-256 来源清单、345 页/条目的语料索引、362 个检索块、17 个表格候选和 SQLite FTS5 数据库。
- 创建并通过校验 `iron-bottom-sound-rules` 项目技能，已同步安装到 `C:\Users\fwj\.codex\skills\iron-bottom-sound-rules`。
- 结构化录入 14 个想定目录、想定 1/3、首批舰船模板、主地图坐标、炮击命中/结果及鱼雷碰撞表。
- 实现 Python 领域模型、七阶段基础状态机、确定性骰子、阵营过滤观察、合法行动、SQLite 存储、REST/WebSocket 和 LLM 适配层基础。
- 实现 React/TypeScript 六角地图、想定选择、单位面板、规则事件日志和热座交接清屏基础 UI；TypeScript 检查及 Vite 生产构建通过。
- 后端自动化验证：`19 passed`；当前代码覆盖率 `60%`。覆盖率尚未达到阶段门槛，不创建阶段完成标签。
- 保留三个明确阻塞项：想定 1 增援顺序、特殊损伤表完整分段、X/Y/Z 岛屿陆地格；详见 `docs/rules/open_questions.md`。
- 阶段 1 可运行基础提交：`9bdd89d`（分支 `codex/phase1-engine`）；该提交不是 `v0.1.0-phase1` 完成发布。
- 语料复核发现 49 个扫描页尚无 OCR 文本（舰船记录 28、想定 15、玩家表 4、规则 2）；FTS 已构建但 M0 保持“进行中”，`v0.1.0-corpus` 仅表示首个可追踪语料基线。
- P1 来源闭环提交 `b4c019a`：为 50 个扫描页生成可重复的 RapidOCR 草稿（48 页有文字），语料更新为 345 页、372 块、38 个表格候选；OCR 明确保持 `draft`，不冒充人工核验。
- 修复 FTS 对 `9.1`、`9.10` 等标点查询的解析；项目技能已再次同步到个人技能目录。
- 将主地图修正并测试为 `A-Z、AA-HH` 共 34 列；远端角 `HH27` 坐标往返通过。
- 逐格回看玩家表第 4 页并结构化特殊损伤表 44–65；想定 1 已按原页修正为 14 艘初始舰、8 艘条件增援及六条特例，删除误录的轰岸规则。
- P1 验证：`24 passed`，总覆盖率仍为 `60%`；特殊损伤表和想定 1 增援两个阻塞项关闭，X/Y/Z 覆盖边界继续保留为开放问题。
- P2 逐舰数据提交 `5c11fad`：从舰船记录手册 2–5 页录入想定 1/3（含增援）共 30 艘逐舰记录，包含炮位 GF/射界、舰体格、完整航速损失轨、鱼雷发射器/备雷、装甲、雷达、舰载机和 VP；引擎初态不再使用泛化舰种耐久。
- P2 裁决表提交 `2a262e2`：逐格核验并结构化 27 行装甲穿透表、10 型鱼雷特性、炮击结果、特殊损伤、火灾、66 故障、碰撞和全部基础/可选修正；关键查表已接入规则数据加载器。
- P2 地形与想定提交 `6ef306c`：标定 X=`4,0`、Y=`6,13`、Z=`7,9`，生成并人工回看 364 个局部覆盖格；想定 1/3 均确认使用纯海主图。三项开放问题现已全部关闭。
- 修正想定 1 不应强制开启雷达、照明弹、探照灯；9.1–9.10 现均为显式开局选项，默认关闭，全规则验收由配置显式开启。
- P2 验证：`39 passed`；当前总覆盖率 `62%`。数据四向闭环已进入 `tested`，但引擎分支覆盖未达门槛，P3 不得跳过。
- P3 阶段命令提交 `799931e`：增援/移动/鱼雷/炮击分阶段独立封存，移动命令按 MF 脉冲同步执行。
- P3 增援与逐炮位提交 `e293992`：想定 1 第三回合唯一增援检定、第四回合边界入场；独立炮位 GF/射界/口径与同时炮击。
- P3 鱼雷与碰撞提交 `73ee225`：鱼雷按发射 MF、舷侧 A/B/X/Y、三回合速度循环和射程移动；碰撞按 1D6 确认后查表，生成船骸；海伦娜 7MF 损失金标复现为 `3-3-3`。
- P3 胜负/重放/可选效果提交 `7b1f4b6`：想定 1/3 使用原版阈值自动判胜；`replay(event_log)` 仅由初始事件与命令事件重建字节等价状态。
- P3 隐蔽标记提交 `f49d81c`：9.1 每方 2 真 2 假标记、秘密编队分配、边缘部署、4/5MF 移动、能见度揭示和真编队还原已执行。
- P3 当前验证：`63 passed`；未声称 P3 完成，剩余阻断项为炮击修正/损伤优先级、沉没漂移、地图边缘/地形以及可选规则组合边界。
- P3 损伤与边缘规则提交 `2613a08`：补齐炮击距离/纵射/目标航速/口径舰型/多舰/多目标/MFC/火灾及可选修正明细；特殊损伤落实逐炮位、鱼雷发射器、舰桥、舵、雷达、舰长和全炮停火状态。
- 地图边缘按规则 6.1 第 8 条执行：越界舰留在边缘，其余舰船、鱼雷、船骸、标记和后续计划路径反向平移，并产生可重放 `world_shifted` 事件。
- 沉没按规则页 10 执行：航行舰下一回合沿舰首漂移一格后放置船骸；回合初速度 0 的舰只原地沉没。
- 修正火灾表“未开火 +1、结果 7/12 无效”，以及 66 故障停电应为全部火炮临时停火而非永久摧毁 MFC；9.4 探照灯、9.8 炮击剪影、9.9 隐藏损伤均补充开关边界测试。
- P3 当前验证：`75 passed`、`git diff --check` 通过；P3 仍未完成，下一阻断项为结构化地形/视线、特殊损伤剩余组合金标和关键分支覆盖。
- P3 地形与规则金标提交 `d0baf44`：结构化陆地在验证与执行阶段阻止舰船，鱼雷撞陆移除；光学视线受陆地阻挡，雷达同时执行岛屿中间遮挡与目标距陆地 4 格限制。想定 1/3 继续使用经来源核验的纯海主图。
- 修正炮击基本裁决：同舰同类炮位对同一目标先合并 GF 再进行一次命中检定；青叶三座主炮现以 GF 16 复现手册 `26 → -6 → 16 → 2 命中`。
- 按手册青叶—海伦娜鱼雷例将青叶更正为 24 英寸九三式；复现 `8+3=11` 命中、`7+1=8` 得到 `5H/-7MF`，海伦娜航速降为 `3-3-3`。亚特兰大 `3PP2` 六 MF 移动例同步通过。
- P3 当前验证：`80 passed`；分支覆盖率审计为总计 `76%`，未达到 90% 发布门槛，状态机/损伤分支及后续 API、LLM 测试必须继续补齐。
- P3 特殊损伤闭环提交 `5e33a8a`：36 个合法 D66 结果全部经过引擎执行与事件断言；修正 33–36/41 为“无舰载机则忽略甲板起火”，并验证装甲值恰好相等视为穿透、31 雷达与舰桥装甲效果分离。
- `IBS-T-SPECIAL` 已由 `partial` 提升至 `executable/tested`；当前 `84 passed`，规则引擎分支覆盖 `77%`，仍不满足发布门槛。
- P3 表格与保密分支提交 `27185e5`：火灾表覆盖 2–12 在已开火/未开火两种路径，66 故障表覆盖 2–12 全部执行效果；隐藏损伤模式未完局时隐藏双方胜利点，防止由分数反推秘密损伤，敌方命令批次不进入观察事件。
- 当前验证：`87 passed`；仍继续补状态机、碰撞/鱼雷与可选规则组合分支。
- 可玩热座与双 LLM 纵向链路提交 `440e08b`：新增全阶段秘密订单编辑、引擎验证的推荐起始订单、交接清屏、文件 SQLite 恢复、一键启动/停止脚本、隔离 `LLMPlayerSession`、阶段私有 `AIPlanSheet`、脱敏审计与自动比赛运行器。
- DeepSeek 适配器按官方兼容接口使用 `deepseek-v4-flash`、关闭 thinking、JSON object、45 秒超时、最多两次自纠；不保存思维链、不回退、不读取敌方观察，密钥仅允许来自 `DEEPSEEK_API_KEY`。已公开旧密钥未写入仓库、环境或测试工件。
- 离线双会话验收：想定 3 默认/全可选分别 32/34 次调用，想定 1 默认/全可选分别 50/52 次调用；四局均运行至引擎胜负，无回退、无人工状态修改，双方私有计划书分别落盘且不进入公共报告。
- 前端依赖只对白名单 `esbuild` 开放安装脚本；TypeScript 与 Vite 生产构建通过。后端、前端本地端口均返回 HTTP 200；应用内浏览器因安全策略禁止回环地址，未声称完成浏览器点击验收。
- API/命令边界提交 `574ecc5` 后达到 `100 passed`，总覆盖率 `90%`；API `98%`、LLM `93%`、比赛运行器 `97%`、规则引擎 `87%`。阶段发布仍被关键分支 100% 和两场真实 DeepSeek 完整对局阻断。
- 一键启动兼容修复 `01e3b30`：优先使用系统 Node，缺失时自动定位 Codex 内置 Node；启动/停止脚本均通过 PowerShell 语法解析。

## 2026-08-24

- 教学关、计划表、六角格与舰船状态 UI 提交 `e8b174d`：首页可创建正式想定 3 教学局，玩家控制德方，教官通过 `DeterministicCommander → submit_orders` 控制英方，不直接修改状态，也不向玩家返回敌方秘密订单。
- 教学卡覆盖增援确认、移动计划、鱼雷计划、同步移动、炮击及损伤/回合结束；自动教程使用正式七阶段引擎推进到第二回合，不维护简化裁决分支。
- 右侧舰船状态表显示原版棋子、舰体格、当前/最大速度、火灾、逐炮位 GF/口径/射界/损坏，以及鱼雷发射器装填、备雷和再装填状态；敌方敏感字段继续由观察层过滤。
- 地图棋子改用 `resources/originals/assets/images/` 的只读规范素材。卡尔加尔斯特棋子与 `D:\desktop\铁底湾\images` 原文件 SHA-256 均为 `918196C7A6450F13AED798A47F48DD90F659611C49F6677D343878C871714EB6`。
- 六角地图统一为 `flat_top_odd_q`，奇数列下移半格；玩家计划表按当前阶段提供逐舰字段，同时保留折叠高级 JSON 审计入口。
- 本批次验证：`103 passed`；TypeScript `tsc -b` 通过；Vite 生产构建 36 模块成功；前端、后端、教程 OpenAPI 路由和棋子静态资源均经本地 HTTP 200 验证。
- 应用内浏览器安全策略拒绝自动操作 `127.0.0.1`，未绕过安全限制；服务已启动供用户直接刷新体验，下一轮根据用户交互反馈继续修正。
- 舰首、船表与逐字段教学修正提交 `e9b1c8e`：平顶六角地图的原版横向棋子统一偏转 30°，航向 1–6 均指向相邻六角边中心，并增加独立金色舰首箭头和运行时几何断言。
- 舰船状态表重排为仿原版记录带：舰体/航速方格、舰体轮廓上的逐炮位 GF/口径/射界、可用/已射击/摧毁图例、鱼雷装填点和备雷状态均由阵营过滤后的 `PlayerObservation` 生成。
- 教学计划表增加当前阶段逐字段编号、一键填入合法移动示例、空鱼雷计划提示和提交前操作顺序；`launch MF exceeds movement plan` 等引擎拒绝会显示可执行的中文修正方法并保留裁决原文。
- 本批次复验：`103 passed`；TypeScript `tsc -b` 通过；Vite 生产构建 36 模块成功；本地服务确认已加载航向投影、图形化记录表和教学示例组件。
- 航向罗盘与速度语义纠错提交 `dc701aa`：逐像素回看 6961×6689 主地图左下角印刷罗盘，确认 `1=右上、2=右下、3=下、4=左下、5=左上、6=上`；领域邻格、世界平移、教官边缘入场和前端棋子旋转统一使用该定义。
- 新增航向 1–6 标签金标，想定 3 卡尔加尔斯特从 O14、方向 4 直航 1 MF 的结果由错误 O15 修正为 N14；原版棋子自身左侧白箭头和叠加舰首标记均与引擎轨迹一致。
- 视觉复核规则书 PDF 第 7–8 页：速度数字为本回合最大 MF 而非强制消耗；非 BB/BC 可比上回合少消耗最多 5 MF，BB/BC 最多 3 MF，计划 `0` 明文合法。观察接口新增引擎计算的 `min_legal_speed/max_legal_speed`，UI 不复制加减速常量。
- 本批次验证：`105 passed`；六向、DD/BB 减速边界、地形、鱼雷、碰撞、射界、隐蔽接触、确定性回放和两想定自动终局均通过；TypeScript 与 Vite 生产构建通过。规则服务已重启，真实 API 返回想定 3 德舰上回合 5 MF、循环上限 6 MF、本回合合法 `0–6 MF`。
- 教学能见度修正提交 `cbeb616`：想定 3 原页确认双方视距 4 格；此前全速教学示例使德舰合法但不适合教学地脱离接触，英舰由服务端战争迷雾过滤，并非状态丢失。
- 移动示例改为卡尔 1 MF、里夏德 0 MF、汉斯 0 MF；正式阶段结算至炮击后仍至少观察到一艘英舰。观察接口新增阵营能见度，教学地图显示淡色视距覆盖，无可见目标时明确解释敌舰仍在对局但不可指定。
- 本批次验证：`106 passed`；TypeScript 与 Vite 36 模块生产构建通过；后端重启后真实 HTTP 观察返回 `visibility=4`，开局五艘英舰均按规则可见。

## 2026-08-24：教学逐舰齐射编排

- 提交：`aacced6`（`fix: support per-ship gunnery planning`）。
- 来源证据：视觉复核规则书第 6 页 `IBS-R-05`“所有炮击同时进行”，以及第 9 页 `IBS-R-08.1` 关于玩家决定参射炮位、炮位分别指定目标和效果同时生效的原文。
- 完成：把总是选择己方第一艘舰的单一按钮改为逐舰炮击名册；每舰可独立添加、删除、选目标和勾炮位，并提供全舰快捷编排。已有卡尔订单不会阻止里夏德或汉斯建单；同舰重复订单由 UI 阻止。
- 教学与纠错：教学卡逐步要求为三舰分别填表；射界继续由规则核心裁决，`cannot bear` 错误会指导玩家取消对应炮位或更换目标。
- 验证：`python -m pytest -q` 为 `106 passed`；`tsc -b` 通过；`vite build` 通过（36 modules）；开发服务 `http://127.0.0.1:5173/src/PlanSheet.tsx` 返回 HTTP 200，并包含逐舰、单舰及全舰三个新入口。

## 2026-08-24：全模式回合结算战报

- 提交：`cf6c521`（`feat: add filtered end-of-turn battle reports`）。
- 来源证据：视觉复核规则书第 10–12 页 `IBS-R-08.1/08.2` 的炮击损伤、沉没、特殊损伤与鱼雷裁决流程；战报只呈现引擎事件，不复算裁决。
- 完成：热座、人类对 LLM、双 LLM 观战和教学关共用回合战报；起火/回合结束后自动弹出，顶栏可重开。内容按航行与碰撞、炮击、鱼雷、损伤/火灾/沉没、胜负分组，并显示摘要、公开 VP、骰子、修正、规则号及页码。
- 信息安全：`POST /advance` 强制 `X-Player-Side`，返回事件执行秘密阵营和隐藏损伤过滤；完整战报从阵营化 `/events` 获取，热座交接销毁上一方战报缓存。
- 验证：`python -m pytest -q` 为 `106 passed`；`tsc -b` 通过；`vite build` 通过（37 modules）；更新后本地 API 对缺少阵营头返回 400、未提交订单返回 409，前端战报组件 HTTP 200。

## 2026-08-24：合法武器筛选、多舰鱼雷与 UI 完整对局

- 提交：`91f2e09`（`feat: filter legal weapons in order UI`）。
- 来源证据：视觉复核规则书第 9–12 页 `IBS-R-08.1/08.2` 的炮位射界、炮击计划、鱼雷发射舷侧/角度、轨迹和效果流程；逐舰射界继续取结构化舰船记录。
- 引擎与 UI：`legal_actions` 返回按阵营过滤的逐舰合法炮击目标/炮位和鱼雷发射器/MF/格/舷侧/角度/速度设定。换炮击目标会重新勾选合法炮位，射界外炮位灰显；鱼雷可按多舰、多发射器分别建单，并自动使用封存移动轨迹上的发射位置。
- 实际 UI 验收：在应用内浏览器中新建想定 3 教学局，全程仅使用可见 UI 控件走完 4 回合。第 1 回合三艘德舰各航行 1 MF；卡尔与里夏德分别由 TT1 发射鱼雷；三艘德舰分别建立并提交齐射。随后逐阶段完成四回合、四份战报和引擎胜负，最终为“轴心小型战略胜利”，`errorCount=0`。未使用高级 JSON、数据库或直接状态修改。
- 附带修复：战报/日志不再把缺失调整值显示为 `null`；终局按钮改为禁用的“对局已结束”。
- 自动验证：`107 passed`；`tsc -b` 通过；Vite 生产构建 37 模块成功；炮击候选逐炮位金标和三舰鱼雷候选/发射轨迹测试通过。

## 2026-08-24：双舷鱼雷 ABXY 发射方向纠错

- 提交：`9c2503a`（`fix: implement eight torpedo launch directions`）。
- 来源证据：逐格视觉核验规则书第 11 页 `IBS-R-08.2.3 b` 的发射方向图与红字要点；原文明确为左舷 `A/B/X/Y`、右舷 `A/B/X/Y`，共八种舷侧—方向组合。旧实现将 A/B 与 X/Y 错误地分别绑定到左右舷。
- 结构化与执行：新增 `torpedo-launch-directions.yaml`，记录左右舷四方向的相对舰首航向。后端取消错误的字母—舷侧互斥校验，仍严格验证发射器自身允许的舷侧，并用“舷侧 + 字母”共同生成鱼雷轨迹。
- UI：`legal_actions` 为每个发射器返回 `angles: [A, B, X, Y]`；计划表直接消费引擎候选，切换左右舷后均保留四个发射角，不在前端复制规则常量。
- 验证：八组合航向金标、规则书青叶舰首 2/左舷 X → 方向 1、错误发射格、发射器舷侧、鱼雷轨迹及效果均通过；全量 `108 passed`，`tsc -b` 通过，Vite 生产构建 37 模块成功。重启后的真实 API 对想定 3 三舰六个发射器全部返回四方向。

## 2026-08-24：停留格鱼雷发射与地图方向标

- 提交：`c5cb7cb`（`fix: allow stationary torpedo launches`）。
- 规则纠正：未移动舰船可在当前停留格发射鱼雷。`TorpedoOrder.launch_at_mf` 现允许 0；引擎合法行动对所有已有封存移动计划的舰船提供 `MF 0 / 当前格 / 当前舰首`，移动舰另保留 MF 1…N 的途中发射点。
- 执行：MF 0 发射在同步移动开始前创建航迹、消耗发射器装填并生成带 `IBS-R-08.2.2` 来源的事件；航迹从第一个全局 MF 脉冲开始移动。错误停留格、超出航路 MF、不可用发射器和不支持舷侧仍由后端拒绝。
- UI：全模式六角地图左下角增加六向“舰首方向”标识，方向仍为 `1=右上、2=右下、3=下、4=左下、5=左上、6=上`；方向标与棋子旋转共用同一 `headingRotation/headingVector` 投影，避免显示与裁决分叉。
- 验证：静止“标枪”MF 0 发射金标通过，错误格被拒，鱼雷首回合航行完整速度且 TT1 正确消耗；全量 `109 passed`，`tsc -b` 通过，Vite 生产构建 37 模块成功。重启后的真实 API 已确认五艘英舰在 0 MF 航路下全部返回 `[0]` 发射点。

## 2026-08-24：鱼雷发射格改用原版地图格号

- 提交：`ea2d449`（`fix: show board labels for torpedo launch hexes`）。
- 原因：鱼雷计划把内部轴向坐标直接显示为 `q17,r7`，玩家会误认为发射格与地图不一致；该坐标实际对应原版格号 `R16`，移动后的 `q16,r7` 对应 `Q16`。
- 完成：前端坐标模块新增与地图绘制共用 odd-q 偏移的 `hexLabel()`；鱼雷发射点改为显示 `MF / A–HH、1–27` 原版格号，内部订单和引擎坐标保持不变。
- 验证：运行时边界断言覆盖 `q17,r7 → R16`、`q16,r7 → Q16`、`A1` 与 `HH27`；全量 `109 passed`，`tsc -b` 通过，Vite 生产构建 37 模块成功。运行中的开发服务源码包含 `hexLabel(position.hex)`，且不再包含旧 q/r 显示模板。

## 2026-08-24：逐舰战果账本、生动结算战报与战术标志

- 提交：`bb1b3ec`（`feat: add ship combat ledgers and tactical markers`）。
- 素材证据：用户指定的 `沉没中.png`、`起火.png`、日方 1/2/3 枚鱼雷和美方 1/2 枚鱼雷，与 `resources/originals/assets/images/` 规范副本逐个 SHA-256 完全相同；直接复用原始棋子，没有生成近似图或重复文件。
- 事件归因：炮击结果、鱼雷效果和特殊损伤事件补全攻击舰字段。后端先执行秘密阵营与隐藏损伤过滤，再从完整安全事件流生成逐舰不可变账本；攻击舰记录战果，目标舰记录受攻/受伤来源，均附回合、阶段、对手、骰子、规则号及来源页。
- 舰船记录表：新增“本舰战果”和“受伤与攻击来源”双栏时间线；普通模式和教学模式共用，刷新状态后保持选中舰并更新记录。
- 结算战报：回合末自动弹窗新增逐舰攻击结算卡，按齐射说明攻击者、目标、命中、伤害、特殊损伤、火灾与沉没；保留原始事件流水用于审计，未命中会明确写为目标未受损。
- 地图标志：当前阵营可观察的鱼雷航迹按阵营和齐射枚数显示规范鱼雷棋子，并标出航向、枚数和剩余射程；舰船起火显示 `起火.png` 与火灾数，沉没漂移阶段显示 `沉没中.png`，其他公开地图标志继续显示。
- 信息安全：新增金标验证同一结果在攻击舰/目标舰的双向归因，并证明可选规则 9.8 隐藏损伤开启后不会通过攻击方战果账本泄露敌舰损伤。
- 验证：全量 `110 passed`；TypeScript `tsc -b` 通过；Vite 生产构建 37 模块成功。后端重启后真实 HTTP 观察确认返回 `combat_history`、`torpedo_tracks` 与 `markers`。

## 2026-08-24：逐发射器鱼雷枚数与齐射棋子纠错

- 提交：`5b3dfb0`（`fix: honor per-launcher torpedo salvos`）。
- 来源证据：视觉核验规则书印刷第 11 页 `IBS-R-08.2.2`，原文规定鱼雷发射器符号内横线数量就是可用鱼雷数，并允许发射部分或全部；逐舰视觉核验舰船记录手册第 2–5 页的所有想定 1、3 鱼雷符号。
- 数据纠正：德英 DD 每舰两座 `2+2`；美 DD 两座 `2+1`；日军重巡左右舷 `2+2`；吹雪系 `2+2`；朝云 `3+3`；秋月单座 `2`。舰船记录不再把每座统一录为一枚。
- UI 与执行：添加鱼雷订单时默认采用发射器当前全部装填量，枚数字段仍可在 `1…loaded` 内调整。引擎继续独立校验上限、按实际枚数扣弹，并把枚数写入 `TorpedoTrack.salvo_size`；地图由该字段选择 1/2/3 枚原版鱼雷棋子。
- 边界验证：一座两枚发射器只射一枚后保留一枚；两枚全齐射产生 `salvo_size=2` 并清空该座；发射器损毁按其实际剩余枚数更新总弹药。
- 自动验证：全量 `110 passed`；TypeScript 通过；Vite 37 模块生产构建成功。真实新局 API 返回卡尔 `2,2`、标枪 `2,2`、法伦霍尔特 `2,1`、青叶 `2,2`、朝云 `3,3`、秋月 `2`。

## 2026-08-24：鱼雷八方向规则与航迹显示纠错

- 实现提交：`78d4b26`（`fix: correct torpedo launch bearings`）。
- 来源复核：重新视觉核验 `iron-bottom-sound-iv-rules-zh.pdf` 印刷第 11 页八条鱼雷发射轨迹图和第 12 页青叶鱼雷范例。此前 `9c2503a` 虽正确开放左右舷各 `A/B/X/Y`，但相对方向转录及其测试金标错误；本记录明确作废旧结论“青叶左舷 X 为方向 1”。
- 规则纠正：左舷 `A/B/X/Y` 相对舰首为 `-1/-2/-3/-4`，右舷为 `+1/+2/+3/+4`。卡尔加尔斯特舰首 4、左舷 A 得到方向 3；从 O14 以 8 格航速沿 O 列到 O22。青叶舰首 2、左舷 X 得到方向 5。
- 审计与显示：`TorpedoTrack` 保存发射格、舷侧、角度和逐格航迹；发射事件补齐上述字段及齐射枚数，同步移动新增 `torpedo_moved` 事件。鱼雷 PNG 以素材固有方向 5 为基准旋转到引擎航向，悬停显示原版格号完整航迹。
- 兼容边界：旧存档缺失新字段时按空值加载，不崩溃；已经按错误规则走完的旧局不静默改写，避免破坏事件回放一致性，新建对局使用修正数据。
- 验证：全量 `110 passed`；TypeScript `tsc -b` 通过；Vite 生产构建 37 模块成功。运行中真实 API 验证局 `fa63c499-ec4d-45f8-8333-7bdc0d54a35a` 返回 `heading=3`、`launch_position=O14` 和 O14→O15→…→O22，日志为“从 O14 沿方向 3 移动至 O22”。

## 2026-08-25：鱼雷计划逐 MF 舰首标注与发射航向回验

- 来源复核：`IBS-R-08.2`（规则书第 11–12 页）定义鱼雷射角相对舰首；`torpedo-launch-directions.yaml` 已结构化左/右舷 `A/B/X/Y` 相对偏移。
- 引擎复核：发射时点舰首取自密封移动轨迹在该 MF 的记录值（`paths[ship.id][impulse][1]`），非恒定初始舰首。复现验证：计划 `1S1`（中途免费转 60°）在 MF2 舰首 4，右舷 X 鱼雷航向 `(4-1+3)%6+1=1`，而非按初始舰首 3 算出的 6；计划 `1SS1`（MF2 为 120° 原地转向脉冲）舰首 5，鱼雷航向 2。
- 计划标注：发射 MF 下拉选项显示 `MF k · 原版格号 · 舰首 h`；已编排发射行新增注记 `发射时点舰首 h；左/右舷 角度 → 鱼雷航向 x`。`relative_heading` 由 `legal_actions` 作为结构化规则数据下发，前端只做展示换算、不复制规则常量。
- 一致性回验：`validate_orders` 在订单带 `bearing` 时回验其必须等于该发射 MF 的舰首，不一致拒绝；`bearing` 缺省（LLM/高级 JSON）时跳过。
- 新增金标：60° 中途转向发射、120° 原地转向脉冲发射、候选逐 MF 舰首与 `relative_heading` 下发、错误 bearing 拒绝/正确 bearing 接受。
- 验证：全量 `114 passed`（`--basetemp=.pytest-verify`）；TypeScript `tsc -b` 通过；Vite 生产构建 37 模块成功。默认 `.pytest-tmp` 下 3 个 teardown 环境错误为 Windows 文件锁（运行中 `run_dqa30_gold_baseline_fair.py` 持锁），`git stash` 验证为改动前已存在，与本次无关。

## 2026-08-25：战报损伤摘要（批次 C 后端）

- 结算点 payload：gunnery_result/torpedo_result/special_damage/fire_check/ship_sunk 五个结算点在损伤前取 `_damage_snapshot`（船体/跨速/火源/炮位/鱼雷管/沉没/各旗标），事件前并入 `_damage_delta` 归一化摘要（hull_lost、speed_lost、fire_added、fire_remaining、gun_mounts_destroyed、torpedo_launchers_destroyed、sank、flags），并补 `attacker_name/target_name`。不改事件类型与消息文本，不改 `_apply_gunnery_result` 签名（特殊分支损伤由 diff 覆盖，special_damage 自带独立 delta）。
- 实际值返回：`_damage_hull` 返回实际扣格 `-> int`、`_lose_speed` 返回实际跨速 `-> int`，7 处调用点忽略返回值即全兼容。
- 沉没追溯：`_add_fire(state, ship, attacker, count)` 统一替换全部 `fire_markers += 1`（鱼雷/炮击/特殊损伤/碰撞/故障），首次点火者记入 `ShipState.fire_source_attacker/fire_source_turn`；`ship_sunk` 增 `attacker/attacker_name/position`，`cause=='fire'` 时用点火者，其余由调用点透传 attacker。
- 船表与过滤：`ShipCombatEntry` 增 `payload`，`_ship_combat_history` 传 `event.payload`；隐藏损伤按既有 `_hidden_damage_event` 过滤，payload 字段随事件一起过滤，无泄漏。
- 测试：新增 `tests/test_damage_payload.py` 12 例（五事件 delta 与真实状态差一致、沉没归属、火灾追溯到点火者、首发点火不被覆盖、船表 payload、隐藏损伤无泄漏、回放字节等价）。全量 `147 passed`（`--basetemp=.pytest-verify`）。

## 2026-08-25：战报损伤摘要前端（批次 D）

- 类型：`types.ts` `ShipCombatEntry` 增 `payload?`；`Event` 沿用现有 `payload?:Record<string,unknown>`，attacker/target 名称与 damage 直接从 payload 读取，不加后端不填写的顶层字段。
- 共享渲染：新建 `damageSummary.tsx` 导出 `damageChips(damage)` 与 `DamageChips` 组件——只读引擎下发的归一化损伤（hull_lost/speed_lost/fire_added/fire_remaining/gun_mounts_destroyed/torpedo_launchers_destroyed/sank/flags），翻译成中文 chips（-X 船体 / 失速 X / 起火 / 余火 X / -X 炮位 / -X 鱼雷管 / 沉没 / 特殊 flags：射击指挥仪·雷达·舰桥·舵机损毁、舰长阵亡/负伤、炮塔卡死 X 回合、极限转向 X°、被迫直行/旋回 X 回合、限制速度 X MF），前端不复制任何裁决常量。
- 战报弹窗：`EventRow` 与逐舰攻击结算卡片（attack-outcome）均渲染损伤 chips；战报汇总新增"损伤船体"统计（6 列），`damageHullLost` 由引擎下发值汇总。
- 实时日志（App.tsx）与舰船记录表（ShipStatusCard CombatColumn）同步渲染 damage chips；隐藏损伤过滤后对应事件不出现，chips 自然不显示。
- 验证：`tsc -b` 通过；Vite 生产构建 39 模块成功（`dist/index-*.js`）。

## 2026-08-25：鱼雷辅助系统后端（批次 E）

- 共用阈值：`torpedo_hit_count(aspect, adjusted)` 从 `_resolve_torpedoes` 硬编码提取，引擎与推荐器共用防漂移（结算行为不变）；`expected_torpedo_hits`/`torpedo_hit_probability` 为 2D6 36 结果穷举。
- 投影与外推：`_project_torpedo_path` 与 `_resolve_movement` 鱼雷循环一致的纯几何直线投影（逐格直行、speed_cycle[(回合-发射)%3] 推进、首回合扣 launch_at_mf、射程/触界截停）；`_project_target_position` 按目标当前航向/航速匀速直线外推并触界钳制——推荐器只用可见信息，不读敌方封存计划。
- 拦截与评估：`_assist_intercept` 逐 impulse 同时推进鱼雷与目标外推（发射回合目标领先 launch_at_mf 步，同格即接触），返回交点/距离/截停原因/回合；`_assist_launch_combos` 复用 `_torpedo_candidates`（含想定禁射等 blocked_reason）枚举 (launcher, mf, side, angle, setting) 组合；`_assist_evaluate` 算舷侧（`_torpedo_track_aspect` 同逻辑）/距离修正/命中率/期望命中。
- API：`TorpedoAssistRequest` + `POST /games/{id}/torpedo-assist` 只读端点（TORPEDO_PLANNING 外 409），返回 `{target_id, target_name, projected_target, combos:[{...组合, torpedo_heading, distance, aspect, modifier, hit_probability, expected_hits, intercept_hex, predicted_path, predicted_end, blocked_reason}]}`，按期望命中降序 Top12。
- 测试：新增 `tests/test_torpedo_assist.py` 10 例——阈值与规则书一致、期望/概率与 36 穷举相等、直线/射程/南缘触界投影（A10→A20 10 格、A22 触界 A27 余 5）、目标恒速外推与钳制、拦截组合推荐（KARL 舰首 1 左舷 A 北向直达 M8 距离 4 舷侧 bow_stern 修正 7）、组合可被 TorpedoOrder 采用并通过引擎校验、单发射叠加路径、IBS-S-01 轴心第 4 回合前禁射、API 形状/只读/错误阶段 409。全量 `157 passed`（`--basetemp=.pytest-verify`）。

## 2026-08-25：鱼雷辅助系统前端（批次 F）

- 格号解析：`hexGeometry.ts` 新增 `hexFromLabel`（引擎格号 "R16"/"HH27" → 轴向坐标的纯几何逆变换，含往返不变量），不复制规则数据。
- 类型与 API：`types.ts` 增 `TorpedoAssistCombo`/`TorpedoAssistResponse`；`api.ts` 增 `torpedoAssist`。
- 推荐 UI（PlanSheet 鱼雷分支）：新增"鱼雷辅助·可见信息推演"区块——敌方在位舰目标下拉，进入鱼雷计划阶段自动加载；Top-8 推荐表显示发射组合/MF/格、鱼雷航向/距离、舷侧/修正、命中率、期望命中；点行在地图叠加预测航迹与拦截点；"采用"按组合覆盖或新建该发射器 TorpedoOrder（launch_hex/bearing/launch_side/launch_angle/setting_index 全部来自引擎响应，speed 由 setting_index 映射，不复制规则常量）。
- 航迹叠加（HexMap/App）：App 持有叠加状态并在鱼雷计划阶段以 `torpedoAssistPaths` 传给 HexMap；HexMap 复用 hexCenter 绘制青色虚线预测航迹 + 终点圆点 + 红色拦截点标记。
- 验证：`tsc -b` 通过；Vite 生产构建 39 模块成功（`dist/index-*.js`）。

## 2026-08-25：射击安排自动齐射优化 · 船表火控/口径/装甲（批次 G）

- 引擎只读推荐器：`_gunnery_candidates` 每个目标增 `range`（格距）与 `modifier`（`_gunnery_modifier(..., attackers=1, target_count=1)` 固有修正，含距离/目标速度/纵射/口径对目标/射击指挥仪损毁/起火/雷达或照明弹/探照灯/烟幕；不含集火附加射手、多目标惩罚两项分配相关项）。新增 `gunnery_assist(state, side, assigned=None)`：越受限越先分配（目标少者先选），每舰取射界炮位最多档 → 档内修正最佳 → 与最佳修正差 ≤ `GUNNERY_ASSIST_BAND`(3，UI 偏好非规则常量) 的档内选负载最小（其次修正、再最近）→ 返回 `{recommendations:[{ship_id,target_id,mount_ids,range,modifier}], excluded}`；`assigned` 为草稿既有齐射（已编排舰排除、其目标计入负载）。`GunneryAssistRequest` + `POST /games/{id}/gunnery-assist` 只读端点（GUNNERY 外 409）。
- 火控情况：`PublicShip` 增 owner-only 字段 `mfc_destroyed/radar_destroyed/bridge_destroyed/rudder_destroyed/captain_status`（`observe` 以 `ship.side==side` 过滤，敌方一律 False/None）。
- 前端：`types.ts` `Ship` 增五火控字段 + `GunneryAssist*` 类型；`api.ts` 增 `gunneryAssist`；PlanSheet "为该舰安排齐射"按"炮位最多→修正最佳（引擎下发）"选目标并显示首选目标与修正，"为全部可射舰安排齐射"调用 gunnery-assist（草稿已编排齐射作为 assigned）填入推荐，加载/错误提示、失败回退逐舰最优，名册提示文案说明分散逻辑；ShipStatusCard 炮位 token 补装甲 `装 X"`（口径保持醒目），新增"火控情况"行（射击指挥仪/雷达/舰桥/舵机/舰长状态，仅本方可见，无损毁时显示完好，敌方不渲染）。
- 验证：新增 `tests/test_gunnery_assist.py` 9 例（candidates range/modifier 与固有修正一致且排除集火惩罚、炮位最多+修正带内、等质目标分散、越受限先分配、assigned 排除与负载、blocked 排除、推荐合法、API 形状/只读/错误阶段 409、PublicShip 火控本方可见敌方隐藏）。全量 `166 passed`；`tsc -b` 通过；Vite 生产构建 39 模块成功。已重启 8000 后端，`/api/games/{id}/gunnery-assist` 通过 5173 代理可达。

## 2026-08-25：射界方位判定修正（IBS-S-01 第 1 回合用户报告）

- 根因：`_bearing_between` 旧实现用"最近邻格方向"近似方位，在 flat-top odd-q 错位网格上误判约三成方位（种子 1 全盘 91 对中 29 对 = 31.9%）。典型病例 = 用户报告：邓肯（X8，舰首 4）→ 吹雪（P14）视觉上仅偏舰首 11°，旧算法判 bearing 3 / rel 5（左舷），全部 5 个带左舷射界的炮位都能射击（用户问"为什么正前方的目标能用全部火炮"）。
- 修复：`_bearing_between` 改为规则 8.1a 中心连线——两格中心连线在渲染屏幕空间的角度（`atan2`，flat-top odd-q 与前端同构），取 6 个舰首方向角中最接近者；相邻格与旧算法逐格一致（`_path_to_commands` 不受影响）。仅改方位几何，不改射界表/纵射逻辑/任何修正常量。修复后邓肯对吹雪 = rel 0（舰艏），仅 P1/P2 可射；对初雪 = rel 1（舷侧），全 5 门。
- 第二个投诉核实（非 bug）："为何都选衣笠、青叶最近"——修正忠实来自已验证规则表。博伊西（W14）对青叶（7 格）射程 -6 + 纵射 -6 = **-12**；对衣笠（11 格）射程 0 + 纵射 -4 = **-4**。规则表本身远处修正更好（6-9 格 -6、10-15 格 0；纵射 6-9 格 -6、10-15 格 -4），已用 OCR 坐标 + 第 11 页示例（距离 9 → -6）双验证。规则第 9 页正文"距离越近越容易命中"与表格/示例矛盾，按治理不改表，记入 `docs/rules/open_questions.md`（IBS-Q-004）待规则确认。
- 验证：新增 `tests/test_bearing.py` 5 例（相邻格精确、全盘方位与 8.1a 参考一致、邓肯-吹雪舰艏仅 P1/P2、邓肯-初雪舷侧全 5 门、纵射不误加）；全量 `171 passed`（`--basetemp=.pytest-verify`）。前端无改动（方位/射界由引擎裁决）。已重启 8000 后端使用修复后引擎。

## 2026-08-25：齐射推荐修正方向纠错（用户确认 D66 骰点越小越好）

- 用户纠正：炮击命中表骰点越小越好、骰子是六进制 D66。核对命中表（玩家辅助 2 页，火力 1：11→1 发命中、13+→0）与 `d66_adjust`（沿 36 档 D66 阶梯移动，负修正向 11 移动）——**引擎裁决方向本来就对**（`_resolve_gunnery`：`d66_adjust(raw, modifier)` 查 `hit_count`；负修正=更容易）。上一轮"衣笠 mod -4 好于青叶 -12"、"射程修正正文与表格矛盾"都是"高骰点更好"的误读。
- 真实 bug：齐射推荐器"修正最佳"方向取反。`gunnery_assist` 与前端 `pickBestTarget` 均用 `max`（修正越大越好），而 D66 低骰点更好、修正为负更好，于是推荐了修正更差的目标（博伊西被推荐 11 格衣笠 -4，而 7 格青叶 -12 才是最佳）——用户"为什么都选衣笠、明明青叶最近"是**正确的**。
- 修复：引擎 `gunnery_assist` 最佳修正 `max→min`、带内 `>= best-BAND → <= best+BAND`、并列键 `-t["modifier"] → t["modifier"]`；前端 PlanSheet `pickBestTarget` `modifier>best → modifier<best`（逐舰齐射与"首选目标"提示共用）。
- 修复后 IBS-S-01 第 1 回合：博伊西→青叶（7 格 -12）、海伦娜→青叶、盐湖城→初雪、旧金山→古鹰；DD 因仅初雪为 -12 档集火初雪（不牺牲质量前提下无法更分散，符合"修正最好前提下分散"）。IBS-S-03：三德 DD 在 -20 档分散到标枪/克什米尔/泽西。
- 修正核实用户其余疑问：`_gunnery_modifiers` 已实现全部 11 项修正并全部并入 `modifier=sum(...)`（射程、**目标航速 0/-4/-9/-18**、纵射、口径对目标、射击指挥仪损毁、集火附加射手、多目标、目标起火、雷达/照明弹、探照灯、烟幕）；骰子 D66（两枚 d6 十位+个位）。鱼雷为独立 2D6 高骰点系统（≥11/≥13），无方向问题，未动。
- 文档：`docs/rules/open_questions.md` IBS-Q-004 由 open 改 **resolved**（射程表与正文一致）；plan.md 增纠错批次条目；IBS-S-03 命中方向断言改 min/带内 <=，LODY 断言改取 -20 档泽西。
- 验证：全量 `171 passed`；`tsc -b` 通过；Vite 生产构建通过；8000 后端重启，live `gunnery-assist` 返回博伊西→青叶（-12）。

## 2026-08-25：增援入场 UI + 移动计划航迹叠加（用户改进点 1/2）

- 根因核实：埃斯佩兰斯角海战想定增援机制**引擎完整**（第 3 回合 REINFORCEMENT 推进掷 1D6 检定、`succeeds_on=[1]`、第 4 回合入场、E17–U27 51 格走廊、校验要求全部 8 舰且入口格互不重复），"一直没有"是**前端缺口**——增援分支永远显示"没有可用增援"，无入场表、无检定结果、玩家无法提交增援订单。
- 后端：新增 `_reinforcement_candidates(state, side)`（只列本方 `reinforcement_turn==当前回合` 未入场舰；按 `_reinforcement_entry_legal` 枚举 51 格入口走廊；取最后 `reinforcement_roll` 事件作为检定结果 → `{group_available, arrival_turn, trigger_turn, succeeds_on, roll_result, entry_range, entry_hexes, ships}`），接入 `legal_actions` REINFORCEMENT schema_hint；新增 `movement_plan_trajectories(state, side, plans)`（逐舰复用 `movement_preview`；非本方/沉没/无位舰返回 invalid 条目）→ `{trajectories:[{ship_id,plan,cost,valid,commitable,errors,trajectory,end_hex,end_heading}]}`；新增 `MovementTrajectoriesRequest` + `POST /games/{id}/movement-trajectories` 只读端点（MOVEMENT_PLANNING 外 409）。校验/入场仍由引擎 `submit_orders`/`_resolve_reinforcements` 唯一裁决。
- 前端：types/api 增 `MovementTrajectory/MovementTrajectoriesResponse/ReinforcementCandidates` 与 `movementTrajectories`；App 在 movement_planning 对草稿 250ms 防抖批量拉取航迹（交接/开局清空）；HexMap 增 `plannedTrajectories`——"走过各自留下连线"（起点→逐格 polyline，去重连续同格，虚线 65%）+ "目标点留下一个浅一点的算子"（舰船素材 42% 透明度、按 end_heading 旋转、带舰名）；PlanSheet 增援分支改为完整入场表（检定状态条、入口走廊说明、自动分配互不重复入口格、逐舰入口格下拉+舰首+速度、入口格重复标红、检定失败提示"本回合无增援入场"），无增援想定/回合保持原文案。
- 验证：新增 `tests/test_reinforcement_candidates.py` 6 例 + `tests/test_movement_trajectories.py` 5 例；全量 `182 passed`（`--basetemp=.pytest-verify`）；`tsc -b` 通过；Vite 生产构建 39 模块成功；8000 后端重启；live HTTP 驱动 IBS-S-01 种子 3 到第 4 回合：增援检定成功（roll 1）、`legal-actions` 返回 51 格走廊 + 8 舰，提交全部 8 舰入场订单后轴心地图 5+8=13 舰；`movement-trajectories` 返回 KARL GALSTER `1S1` → N14/M14、end M14 航向 5。

## 2026-08-25：两方射界热力图（用户：两方射界图开关）

- 目标：地图加"两方射界图"开关，对每格汇总两方各舰每门火炮的射界 + 射程范围，按火炮强度与"那格的距离修正"加权成热力图；热力跨舰/跨炮叠加，两方可同时叠加显示。
- 后端：抽取 `_relative_aspect(origin, heading, target)` 静态助手（六方向 bearing + 舰首方位 rel → BOW/STARBOARD/STERN/PORT，与 `_mount_can_bear` 同源防漂移）；新增只读 `field_of_fire_heatmap(state, viewer)`——**热值 = Σ 可指向该格的炮位 firepower × 该距离 D66 期望命中数**（36 档全举 `d66_adjust(roll, range_modifier("gunnery", distance))` 查 `hit_count` 取均值，`{(fp,distance)}` 缓存），对双方分别算 `{hex_label: heat>`0}`、`max_heat`、`ships`；本方用真实状态（已毁炮位剔除），敌方按记录全炮位（不泄漏隐藏损伤）且只含 `_visible_to` 可见敌舰（不泄漏隐蔽舰位置）；命中表/距离修正是规则常量，全部由引擎唯一计算，前端只渲染颜色。新增 `POST /games/{id}/field-of-fire`（viewer 走 `X-Player-Side`），任意阶段可用，只读不落库。
- 前端：types/api 增 `FireHeatmapSide/FireHeatmapResponse/FireHeatmapMode` 与 `fieldOfFire`；App 增 `fireHeatmapMode`（关/轴心/同盟/双方）开关组（绝对定位叠于地图左上）+ 按 `[game,side,view,mode]` 拉取（off 时清空，开局/交接重置）；`.map-column` 包住地图与开关；HexMap 增 `fireHeatmaps`/`fireHeatmapMode` props，按每侧 `max_heat` 归一化 `fillOpacity = 0.12 + t*0.5` 画半透明六角格色块（axis 暖色 `#e05c3a`、allies 冷色 `#3a7bd8`），渲染在 hexes 层之下（坐标文字/高亮/算子清晰，`pointer-events:none`），"双方"模式两色叠加即热力叠加。
- 验证：新增 `tests/test_field_of_fire_heatmap.py` 7 例（36 档穷举与期望命中逐炮逐格一致、已毁本方炮位精确扣除其贡献（容差 2e-4）、敌方热力图不因隐藏损伤变化、各视角本方已毁剔除、可见→超视距敌舰被排除且热值消失、API 形状/只读、`_relative_aspect` 与 `_mount_can_bear` 全盘一致）；全量 `189 passed`（`--basetemp=.pytest-verify`）；`tsc -b` 通过；Vite 生产构建 39 模块成功；8000 后端重启；live HTTP：IBS-S-03 轴心 764 格 max 14.28 / 同盟 889 格 max 15.11，热点 O13/P14/Q14，经 5173 代理端到端 200。

## 2026-08-25：射界热力图"选舰"子模式（用户：选中哪个就展示那个船的火力热力）

- 目标：开关新增"选舰"模式——在地图上选中哪艘舰，就展示那艘舰的火力热力（其各门火炮射界 × 射程 × 距离修正的期望命中热值），随选中舰切换实时更新。
- 后端：抽取 `_ship_fire_heat(ship, viewer, expected_hits, cells)` 单舰热值助手（本方真实炮位剔除已毁、敌方记录全炮位不泄漏隐藏损伤，与全方模式同公式）；`field_of_fire_heatmap` 增可选 `ship_id`——只算该舰，所属侧填充热值、另一侧空，敌方舰仍须 `_visible_to` 可见（兜底）；`POST /games/{id}/field-of-fire` 增可选 body `{ship_id}`。
- 前端：types `FireHeatmapMode` 增 `"ship"`；`fieldOfFire(id, side, shipId?)` 带 body；App 开关组增"选舰"（按钮带悬停提示），effect 在 ship 模式携带 `selected.id`（无选中/无位置则清空，随 `selected` 变化重拉）；HexMap 对 `"ship"` 模式按 both 迭代（响应只填充一侧）；地图左上角叠加当前舰名标签 `.heatmap-ship-label`。
- 验证：新增 4 例（单舰热值与 36 档穷举逐格一致且另一侧为空、本方已毁炮位扣除/敌方记录保留、非法 id 与超视距敌舰返回空、API 带 ship_id 只填所属侧且不带 ship_id 仍全方）；全量 `193 passed`；`tsc -b` 通过；Vite 生产构建成功；8000 后端重启；live HTTP：选中 KARL GALSTER（O14）→ 轴心 688 格 max 6.39、热点 N13/O13，同盟侧为空。

## 2026-08-25：射界热力图显示修正 + 目标航速修正（用户核对演示 + 改进）

- 用户要求：双方热力统一红色；每个热力格显示热值数字；格内命中期望要计算"航速为 4 的船"的修正，并给出公式"热值 = Σ 每门炮 firepower × 该距离的 D66 期望命中数"。
- **修复漏乘 firepower 的 bug（用户核对公式时发现）**：初版引擎只累加期望命中数（N13=6.39），漏乘火力权重；`_ship_fire_heat` 改 `heat[label] += mount.firepower * expected_hits(...)`，测试对照助手 `expected_heat_for_ship`/已毁炮位扣减贡献同步补乘。修正后 KARL GALSTER 邻格 N13=12.06（5 门全指向：4×2×1.4167 + 1×0.7222）。
- **目标航速修正进公式**：`field_of_fire_heatmap` 增 `target_speed=4` 参数，格内期望命中 = `d66_adjust(roll, 距离修正 + target_speed_modifier("gunnery", target_speed))` 36 档均值；已验证目标航速表 **0→-18、1→-9、2-3→-4、4+→0**，故航速 4 修正 = 0（-4 是航速 2-3），演示按此表取 0；API body 增 `target_speed`（默认 4）。前端不传即用默认 4。
- 前端：HexMap 双方统一红色 `#e05c3a`（"双方"模式合并两侧热值到一格一数）；每个有热值格以 `heat-value` 文字显示热值数字（覆盖坐标标注，白色描边）；新增 `.heat-value` 样式。
- 演示（KARL GALSTER O14、航向4、P1-P5=2/2/1/2/2，目标航速4 修正0）：N13(1格,舷侧,修正-24)=12.0556、M14(2格,舰艏,修正-15)=3.6667、K14(4格,-12)=3.0、G15(8格,-6)=1.6667、B14(13格,0)=0.3333；引擎单舰热力图 max 12.0556 与手工逐门炮演算一致。
- 验证：新增 `test_target_speed_4_uses_verified_zero_modifier_and_parameter_applies`（航速4→0、航速3→-4 且逐格与 36 档穷举一致）；全量 `194 passed`；`tsc -b` 通过；Vite 生产构建成功；8000 后端重启；live HTTP：KARL 单舰 688 格 max 12.0556（N13/O13/O15/P14），全图轴心 max 27.11 / 同盟 max 35.92。

## 2026-08-25：战报火灾图标纠错 + 失速循环条 + 逐舰攻击结算分栏（用户：战报为什么命中都用火灾棋子 / 失速血条也显示 / 结算左轴心右同盟）

- **战报火灾图标 bug**：`BattleReportModal.resultIcon` 用 `/fire|火/.test(JSON.stringify(payload))` 字符串匹配，命中表键名 `fire_added/fire_remaining`（即使值 0）导致每次成功命中都渲染 `起火.png`。修复为只读引擎下发的 `damage`：`fire_added + fire_remaining > 0` 显示起火、`damage.sank`/`ship_sunk` 显示沉没，不再匹配键名。
- **失速循环条**：`PublicShip` 增 owner-only `speed_damage_crossed`/`speed_damage_track`（`observe` 以 `ship.side == side` 过滤，敌方 None，与 `max_speed` 同规则）；舰船状态表 `.record-tracks` 新增整宽"失速循环"行——按三回合速度循环逐行渲染轨道格，`index < crossed` 的格标红 ×，数值全部来自引擎/想定逐舰记录，前端只画格。
- **逐舰攻击结算分栏**：`gun_mount_attack`/`torpedo_attack` payload 增 `attacker_side`/`target_side`；战报"逐舰攻击结算"改左"轴心战果"/右"同盟战果"双栏（`.engagement-columns`，无该侧攻击显示空提示，未归类单列"其他攻击"），卡片渲染器 `renderStoryCard` 复用。
- 验证：新增 3 例（炮击/鱼雷攻击事件带 `attacker_side/target_side`、观察本方暴露失速轨/敌方隐藏）；全量 `197 passed`；`tsc -b` 通过；Vite 生产构建 39 模块成功；8000 后端重启；live：`observe` 本方 `speed_damage_crossed=[0,0,0]`、`speed_damage_track=[[6,5,4,3,2,1]×3]`，敌方 `null`；live 炮击 `gun_mount_attack` `attacker_side=axis`，`gunnery_result` 的 `fire_added/fire_remaining` 均为 0（修复后不再显示起火图标）。

## 2026-08-25：鱼雷射角方向映射修正（用户权威规则 + AA12 金例）

- **根因**：`torpedo-launch-directions.yaml` 的 `relative_heading` 错误——旧表 `port {A:-1,B:-2,X:-3,Y:-4}`、`starboard {+1,+2,+3,+4}` 是错误推导，导致舰首 4 的鱼雷辅助给左B→方向2、左X→方向1。用户报告金例：AA12（航向4）左B应朝向 AA13-AA14（方向3）、左X应朝向 AA13-HH16 东南斜线（方向2）。
- **权威规则（用户原话）**：船头朝向 m，左舷 A=所在格方向 m-1、B=所在格朝船头反方向一格方向 m-1、X=所在格朝船头方向前进一格方向 m-2、Y=所在格方向 m-2（减到 0 变成 6）；右舷镜像 m+1/m+1/m+2/m+2（加到 7 变成 1）。规则书 8.2.3 b（11 页）"两个方位共 8 种鱼雷发射轨道（每个舷侧 4 种）"与之吻合。
- **改动**：yaml `relative_heading` 修正为 `port {A:-1,B:-1,X:-2,Y:-2}`、`starboard {A:+1,B:+1,X:+2,Y:+2}`（含规则注释）；引擎与前端零改动（引擎 `_torpedo_launch_heading` 读 yaml，前端只消费下发的 `relative_heading`/`torpedo_heading`）。只修方向不改锚点——全部鱼雷轨以舰发射格为起点，满足报告金例；"朝船头反方向一格/朝船头方向前进一格"的锚点偏移解读记为开放问题 IBS-Q-005。
- 测试：更新 `test_engine.py` ABXY 全表（舰首 2：左A/B=1、左X/Y=6，右A/B=3、右X/Y=4）、`relative_heading` 断言（右X=2、左Y=-2）、两处 120° 转向发射航向（4+右X→6、5+右X→1）、starboard-X 接触几何（Javelin O14→N14，因新方向 3+右X=m+2=5 走 O15→N14）；新增 `test_torpedo_launch_headings_match_authoritative_abxy_rule`（6 舰首 × 8 组合对照权威参考式 + 金例 舰首4 左B=3/左X=2、AA12→AA14 沿线）。
- 验证：全量 `198 passed`（新增 1 例）；`tsc -b` 通过；Vite 生产构建 39 模块成功；8000 后端重启；live：torpedo-assist 对舰首 4 舰返回左A/B=heading 3；`_project_torpedo_path` 从 AA12 投影 左B→`['AA12','AA13','AA14',…]`、左X→`['AA12','BB12','CC13','DD13',…]`，与用户报告一致。

## 2026-08-25：鱼雷锚点偏移 + 调试模式 + 鱼雷阶段航迹保留 + 鱼雷历史轨迹 + 船表完整战果

- **锚点偏移（用户权威规则，IBS-Q-005 resolved）**：`torpedo-launch-directions.yaml` 增 `launch_anchor {A:0, B:-1, X:1, Y:0}`（左右舷同角度共用；B=朝船头反方向/船尾外 1 格，X=朝船头方向外 1 格，A/Y=舰格）。引擎新增 `_torpedo_anchor_hex(launch_hex, 发射时舰首, angle)`（锚点越界退回舰格）；`_launch_torpedo_order` 的 `position/launch_position/traversed_hexes` 与 `_project_torpedo_path`/`_assist_intercept` 起点统一经它计算；`_assist_evaluate` 传 `launch_angle` + 舰首。金例（AA12 航向4）：左B 起点 BB11、左X 起点 Z12，方向维持 m-1/m-2（左B=3、左X=2）。注意用户原报告"左B 穿过 AA13-AA14"描述的是方向线，锚点外移后实际起点为船尾格——按用户"锚点按我说的改"以字面锚点为准。
- **调试模式**：`observe(game_id, side, debug=False)`——debug 时全舰可见、隐藏损伤与规划硬件全展示、鱼雷轨/事件/标记/比分不隐藏；`GET /games/{id}/view?debug=true`。前端 header 增"调试"开关（切换即带 debug 重拉）。
- **鱼雷阶段航迹保留**：`sealed_movement_trajectories(state, side, debug=False)` 从 `_sealed_batches(MOVEMENT_PLANNING)` 只读重放逐舰航迹（默认仅本方，debug 含敌方）；`GET /games/{id}/sealed-trajectories`（仅 TORPEDO_PLANNING）。前端 plannedTrajectories effect 增鱼雷阶段分支，HexMap 敌方轨迹画红线。
- **鱼雷历史轨迹 + 发射点**：HexMap 鱼雷轨叠加历史航迹虚线（`torpedo-trail`）与发射点金色标记（`torpedo-launch-marker`，圆圈 + 角度字母）。
- **船表完整战果**：ShipStatusCard 战果/受伤双栏去掉 `.slice(-8)` 截断、完整倒序展示并加 `max-height` 滚动，标题由"最近 N 项"改"共 N 项"。
- 验证：新增 3 测试（`test_torpedo_launch_anchor_offset_per_authoritative_rule` 锚点全角度金标、`test_debug_observe_reveals_both_sides_and_planning_hardware`、`test_sealed_movement_trajectories_retained_during_torpedo_planning`）+ 更新 2 接触几何测试（starboard-X 锚点 O16→N15、launch_position=锚点）；全量 `201 passed`（`--basetemp=.pytest-verify`）；`tsc -b` 通过；Vite 生产构建 39 模块成功；`docs/rules/open_questions.md` IBS-Q-005 改 resolved。

## 2026-08-25：简单战术 AI（TacticalCommander）

- **目标**：按用户三要素实现确定性启发式战术 AI——炮击采纳自动齐射（`gunnery_assist`）；移动"去敌方火力热力图小处 + 保持敌方在我方火力覆盖内"；鱼雷"距离较近 + 自动鱼雷系统置信度高才发射"。接线＝教程对手 + 命令行都接（用户确认）。研究依据（塔萨法隆加夜战"超射程乱射无益、近距才有效"；crossing the T 抢占横头；ATLATL/AlphaSCS/Panopticon/WarAgent）只用于定权重量纲，不引入训练模型。
- **引擎只读/等价重构（命中公式与规则常量唯一留在引擎）**：新增 `expected_gunnery_hits(firepower, distance, target_speed=4)`（热力闭包 D66 36 档命中期望公式提为方法，闭包委托、行为逐位不变）；新增 `ship_gun_pressure(state, ship, position=None, heading=None, target_hexes=None)`（Σ 未毁炮位在射界内 × firepower × 期望命中，默认目标格＝`_visible_to` 可见敌舰，不泄漏隐蔽舰）；抽出共享枚举器 `_movement_expand`（`_movement_reachable` 主循环改从它取转移，遍历顺序不变）；新增 `movement_path(state, ship, target_hex, heading=None)`（**0-1 BFS**：0 成本转向边 appendleft、1 成本推进边 append，带 parent 还原，返回合法 commands/plan/cost）。
- **新模块 `tactical.py`**：`TacticalCommander(DeterministicCommander)`（复用 CONTACT_SETUP/REINFORCEMENT），`model="tactical-v1"`；顶部可调启发式权重/阈值 `W_ENEMY_HEAT=1.0 / W_FIRE_PRESSURE=1.0 / W_APPROACH=0.5 / APPROACH_RANGE=12 / TORPEDO_MAX_RANGE=10 / TORPEDO_MIN_EXPECTED=0.30 / TOP_K_CANDIDATES=5`。`_plan_movement` 覆盖全部在位本方舰，对每个可达 (格,末航向) 打分 `score = -W_ENEMY_HEAT·(敌热力/max) + W_FIRE_PRESSURE·(本舰压力/候选空间max压力)`＋炮射程外接近项；确定性排序后对 TOP_K 候选逐个 `movement_path`→`movement_preview` 复核取合法计划，失败回退链 `"0" → 直行 max_cost → 首个可达格`。`_plan_torpedoes` 对最近可见敌舰调 `torpedo_assist`，仅取 `distance ≤ 10` 且 `expected_hits ≥ 0.30` 且未 blocked 组合，每发射器一条（launch_hex 经 `HexCoord.from_label`，天然匹配封存轨迹）。`_plan_gunnery` 采纳 `gunnery_assist["recommendations"]`。
- **接线**：`match.py` `make_session` 加 `"tactical"` 分支、CLI `--axis/--allies` choices 扩为 `("deterministic","tactical","deepseek")`；`api.py` `suggested_orders` 与 `tutorial_opponent` 换用 `TacticalCommander()`。
- **引擎 bug 修复（AI 对 AI 压出）**：① 同格 distance=0 三处 StopIteration（碰撞检定失败同格 → 射程/纵射/穿透表越界）：`_range_value` 下限钳 `max(1, distance)`（单点覆盖全部射程表）、`penetration` 顶部 `max(1, distance)`；② `movement_path` 原 FIFO 非最短（0 成本转向边），改 0-1 BFS；③ 确定性对手 `"0"` 计划对强迫舰非法（桥楼/舵损伤 forced_circle/forced_speed），新增 `_stationary_plan` 回退链 `"0" → 直行 max_cost → 首个可达格路径`；④ 移动打分曾被火力压力项主导（敌方热力归一 [0,1]、压力未归一 0–40，KARL-GALSTER 冲进更高敌热 16.25→30.08），压力项按候选空间最大压力归一、两项同量纲各权重 1.0——修复后 HANS-LODY -4.67、BEITZEN 0、KARL +1.67，种子扫掠 `mean_delta=-1.0`、16/24 not_worse。
- **验证**：新增 `tests/test_tactical_ai.py` 26 例（引擎新方法、AI 各阶段、集成）；全量 `227 passed`（`--basetemp=.pytest-verify`）；AI 对 AI 多 seed 终局 6 组合 × 6 seed＝**36/36 COMPLETE** 且确定性（同 seed 两次一致）；CLI `--scenario IBS-S-03 --axis tactical --allies deterministic --seed 9` → passed=True、completed=True、winner=axis、request_count=32；`--scenario IBS-S-01` 双方向同样终局完成。

## 2026-08-25：人机大战 · AI 对抗评分 · 六风格 profile 批次

- **目标**（用户两项请求，均已确认范围"全做 + 对抗默认开启"）：(1) UI 可开人机大战——玩家选一方（轴心/同盟）+ 选对手风格，标准想定对打、无交接屏；(2) AI 做决定时考虑对手下一回合也会动（对抗评分，1-ply），并培养六种风格（均衡/大舰队编队/长纵队/乱阵近战/鱼雷专精/猥琐保守）。
- **对抗评分（1-ply，无递归）**：对每艘可见敌舰先预测其下一回合最优落点（敌视角：规避「我方热力」+ 敌对我可见舰压力 + 敌风格接近项；只依赖敌当前可见信息、经 `model_copy` 剥 `forced_*`/`speed_damage_crossed`/`gun_mounts.destroyed` 等隐藏损伤字段、用 `engine._visible_to` 过滤我方可见舰，不泄漏隐蔽信息）；我方 `_score_hex` 威胁＝Σ 敌在其**预测落点**对我格的 `ship_gun_pressure`（惰性 memo，`_MovementContext.enemy_threat_of`）、压力＝我对**敌预测落点集合**的压力、接近项用预测落点最近点。`w_predict_opponent<=0` 退化为「预测＝敌当前位置」静态语义（对抗可关、回归抓手）。引擎只读方法全部现成复用，零新增引擎移动/可见性方法。
- **TacticalProfile + 六预设**：`TacticalProfile`（pydantic）＝既有 7 超参 + `w_formation/formation_spacing/line_ahead/w_predict_opponent`；`PROFILES`＝balanced(默认)/fleet(`w_formation=2.0` 抱团)/line(`line_ahead=2.0` 长纵队)/brawl(`w_approach=1.5, w_enemy_heat=0.2` 乱阵近战)/torpedo(`torpedo_max_range=14, torpedo_min_expected=0.10` 鱼雷专精)/cautious(`w_approach=-0.6, w_enemy_heat=2.0` 猥琐保守)；模块级常量 `W_ENEMY_HEAT` 等保留为 balanced 别名，实现一律读 `self.profile.*`。`_formation_factor`：间距带（spacing 内外 1→0 线性）+ `line_ahead` 最近友舰共线且在前、距离 1-3 加分。
- **人机大战接线**：`GameOptions.mode` 增 `"vs_ai"` + `ai_profile`；`api.py` 新增通用 `POST /games/{id}/ai-opponent`（X-Player-Side 求对侧、body.profile 校验 ∈ PROFILES 否则 422、玩家须先提交否则 409、AI 侧已提交则幂等 true、不返回私有订单；`TacticalCommander(profile).choose_orders → submit_orders → repository.save`，订单仍由引擎校验、AI 不直接改状态）；`match.py` `make_session/run_match/CLI` 加 `--axis-profile/--allies-profile`。前端：`api.ts` `createGame` mode 扩 `"vs_ai"` + `aiProfile`、新增 `aiOpponent`；`App.tsx` Landing 增「人机大战」入口（想定 + 我指挥轴心/同盟 + 对手风格下拉）、`act()` vs_ai 分支（submit → aiOpponent → advance → refresh，复用教程三连、无交接屏）、header 显示「对手：{风格}」、按钮文案三态。
- **引擎性能**：`expected_gunnery_hits` 加实例级 `_gunnery_expect_cache`，键 `(firepower, distance, target_speed)`，行为纯等价（对抗后每次决策约 60k 次命中查表，无缓存 2-3s、缓存后 <100ms）。
- **引擎确定性 bug（根因分析，对抗测试压出）**：`advance` 移动解析的碰撞组用 `collision_sets = {frozenset(ids) ...}` 且 `for collision_set in collision_sets` 迭代——`set[frozenset[str]]` 迭代顺序随 PYTHONHASHSEED 随机化，而每次碰撞检定消耗种子化 RNG 骰子（`_roll_d6`/`_roll_2d6` 推进 `rng_counter`）→ 骰子错配到不同碰撞 → 同 seed 跨进程战果分叉（实测 cautious vs fleet seed 9：seed 2/8 一局「英军战术胜利/一艘德舰」、其余「英军战略胜利/多艘德舰」）。修复：`sorted(collision_sets, key=lambda group: sorted(group))` 按组成员确定性迭代（组内本来就 `sorted`）；另排查全引擎，字符串 set 迭代仅此一处（其余 set 均为 int 元组，哈希稳定）。修复后 12 个 PYTHONHASHSEED 全部收敛同一战果。
- 测试：重写 `test_tactical_ai.py` 5 例（13/14/15/16/22，对抗化后签名/语义变化，16 改「5 seed 内预测威胁净下降」、22 改 `PROFILES["balanced"].model_copy(update={...})`）+ 新增 7 例（敌预测候选合法+确定性、敌规避我方热力、队形间距、长纵队共线、多 profile 移动差异、多 profile run_match 确定性、隐藏损伤剥离）+ 新增 `tests/test_api_ai_opponent.py` 4 例（409/幂等/422/advance 推进、双阵营各到第 2 回合）+ 新增碰撞哈希确定性回归 `test_collision_resolution_is_deterministic_across_hash_seeds`（子进程设 PYTHONHASHSEED=2/8 对跑，比较战果+碰撞序列；旧代码下实测必失败、新代码通过）。
- **验证**：全量 `239 passed`（`--basetemp=.pytest-fix`）；原偶发 `test_tactical_vs_tactical_completes_both_scenarios` 连续多跑通过；`tsc -b` 通过；Vite 生产构建 40 模块成功；CLI 多 profile `--axis tactical --allies tactical --axis-profile cautious --allies-profile fleet --seed 9` → passed/completed=True、winner=allies、32 请求、12 个 HASHSEED 全同；同 seed 两次 match-report.json 除 UUID 外全键一致；8000 后端重启后 live：`mode=vs_ai` 建局成功、同盟侧全流程 submit→ai-opponent→advance→turn 2；浏览器人机大战入口、风格差异留待用户肉眼核对。

## 2026-08-25：AI 态势感知（残血/血量/状态/火炮/VP）+ 随机射击 + 存档格式设计（用户四项改进）

- **需求**（用户四项）：① 残血时应尽量远离敌人；② 决策考虑血量、状态（火/损伤）、火炮剩余门数、VP（目标价值）；③ 炮击/移动落点不要总选最高分，用评分归一化算概率加一点随机；④ 设计易读、LLM 无需多模态即可读空间关系、便于进入 GPU 做 CNN/Transformer 训练的存档/状态表示（用户确认本批只出设计方案文档）。
- **引擎只读增量（不改裁决，全向后兼容）**：`PublicShip` 增公开字段 `vp`（船籍价值，非隐藏损伤，hidden_damage 下敌 hull=None 但 vp 照常下发）；`_gunnery_candidates` 每目标增引擎算好的 `expected_hits = Σ expected_gunnery_hits(mount.firepower, distance)`（命中公式唯一在引擎，AI 不复制）；`gunnery_assist` 推荐透传 `expected_hits`；新增薄只读封装 `engine.gunnery_target_options(state, side)`。
- **tactical.py 态势感知**：`TacticalProfile` 增 8 个可调字段（默认产品值）——`retreat_hull_threshold=0.35 / w_retreat=1.0 / w_protect_own=0.5 / w_vp=0.3 / w_finish=0.5 / w_self_status=0.3 / temperature=0.5 / rng_seed_off=0`（非规则常量、不改引擎裁决）。`_value_factor(敌)`＝`1 + w_vp·(vp/max_vp) + w_finish·(1-血量分数)`，`hull=None`（隐藏损伤）只用 VP 不猜血量；`_own_value(己舰)` 满血且无伤＝0（正常接敌不退避），残血（survival 线性升 1）/起火/炮禁用/减速 → 退避强度 >0，高 VP 己舰更惜命；`_score_hex` 新增价值加权火力项（`value_pressure/max`，逐候选 `Σ ship_gun_pressure(position, heading, 敌预测落点) × 敌价值`，空敌回落基础压力项保护旧测试）＋残血退避项（`own_value·w_retreat·(候选距最近敌预测格 − 起点距)/approach_range`，健康舰该项≈0 不与接近项打架）。
- **随机射击（种子化，确定性可复现）**：AI 独立 RNG `random.Random(seed·1_000_003 + turn·10_007 + side·101 + phase·11 + rng_seed_off)`，纯整数派生、与引擎 `rng_counter` 骰子流完全隔离、**不用 game_id/hash()/set 迭代序**（跨 PYTHONHASHSEED 可复现）；每阶段一个 RNG 实例下传该阶段全部舰。`_sample_weighted(scored, temperature, rng)`：softmax `exp((s-max)/T)` 归一化抽样（减 max 防溢出）；温度=0 或候选≤1 → argmax 且不耗 RNG；条目形如 `(score, *payload)` 通用载荷。移动：打分后温度>0 把抽中候选置首、其余保持原降序（`_path_to` 复核链不变，抽样只在 `movement_candidates` 合法可达集内）；炮击：`_plan_gunnery` 重写为对每舰全部候选目标按 `expected_hits × 价值` softmax 抽一个目标（旧＝采纳 assist 每舰一条，新＝可多舰集火同一目标），敌情一律走 observe() PublicShip（绝不读 `state.ships[敌].hull`，不泄漏隐藏损伤）。
- **新测试**：`tests/test_gunnery_assist.py` +3（`gunnery_target_options` 携带期望命中且与独立重算一致、assist 推荐透传、observe 双方 vp 下发）；`tests/test_tactical_ai.py` 更新 2（炮击改为断言"目标∈引擎合法候选集+炮位一致"、net-threat 用全零新权重+温度 0 隔离基础打分）+ 新增 12（残血 `_score_hex` 更远候选更高分且健康舰 own_value=0、`_value_factor` VP/补刀/hidden 不崩、`_value_pressure` 价值倍率线性、`_score_hex` 默认退化旧公式、抽样合法且在可达集内且 rng=None 恒 argmax、同 seed 两遍计划逐位一致、同 seed 不同 game_id 计划一致、`_sample_weighted` 温度 0 argmax 不耗 RNG/温度>0 有变化、炮击温度 0=argmax(expected_hits×价值)、可补刀目标反超被选、炮击抽样目标 ∈ 合法集、**AI 订单级跨 PYTHONHASHSEED=2/8 子进程对跑一致**——比现有"只比战果/碰撞序列"更强的 AI 序列校验）。
- **验证**：全量 `254 passed`（`--basetemp=.pytest-verify-*`）；三个确定性测试保持绿；CLI 复验——同 seed 两次 MOVEMENT+GUNNERY 订单逐位一致；temperature 0/0.5/2.0 下 MOVEMENT 与 GUNNERY 均有差异（seed=1 德舰 BEITZEN 目标 JAVELIN/KASHMIR/JERSEY）；残血退避：seed=3 卡尔加尔斯特残血后落点距敌预测格 1.0→8.5（显著退避），里夏德/汉斯因占据压倒性火力优势位（压力 60/60）选择留守——机制正确，权重调参留后续。
- **存档格式设计文档**：`docs/architecture/state-representation.md`——一个真相源（现有 SQLite `games/events/snapshots`）+ 两种投影：投影一 JSONL 世界态 + **cell-aligned ASCII/整数棋盘**（34×27=918 格、坐标表头 A..HH×1..27、图例，TopoBench 实证 +30-40pp）；投影二 918 格多通道特征张量 `.npz`（地形/存在/hull/航向 sin+cos/火情/鱼雷/沉船/可见性/射界热力层复用 `field_of_fire_heatmap`，8-12 通道）+ 动作合法掩码；静态/动态切分（舰型记录抽旁路表、订单作策略标签单独成流、事件按 type 定 schema）；文献/GitHub 清单（GVGAI-LLM/TopoBench/ResTNet/antiyoy-ai/NuZero/SMAC 等）；实施路线（本批文档 → 最小导出 JSONL+ASCII → 张量导出+训练）。本批不实现导出代码。

## 2026-08-26：存档导出（投影一）+ LLM 模式对接 + 提示词工程 + 实况验证（用户四项改进落实批次）

- **目标**（用户四项）：① 把 `docs/architecture/state-representation.md` 投影一存档按时装（JSONL 世界态帧 + cell-aligned ASCII/整数棋盘）；② LLM 模式对接接口（后端端点 + 前端接入，用户确认「后端+前端完整接」）；③ 提示词要示范输出例子、修思考过度/死循环，能观察思考过程；④ 最后实况验证——LLM 对战不超时、测试 API。密钥处理：只从 `DEEPSEEK_API_KEY` 环境变量读取，贴出的密钥仅在验证命令内存注入不写文件（验证后提醒轮换）。
- **提交（7）**：`a86bc0e`（engine: PlayerObservation 增公开 wrecks）→ `bde087d`（export: JSONL 世界态帧 + cell-aligned ASCII 棋盘，state_export.py 新建 + run_match 逐阶段累积 frames/artifacts）→ `7593643`（api: GET /games/{id}/export）→ `8ca6421`（llm: board/frame few-shot prompt + reasoning audit + 反过度思考纪律）→ `a4d2f61`（api: POST /games/{id}/llm-opponent）→ `dd5ff05`（frontend: LLM 对手模式接线）→ `c2ccbd6`（fix: torpedo bearing 指引 + 地图边缘世界平移停靠，实况收敛的两处修复）。
- **投影一导出**：`export_frame`/`render_board` 一律只从 `engine.observe()` 可见集派生——敌方隐藏损伤下 hull/guns_usable/guns_total/torpedoes_ready 全 None（不是 0），超视距敌舰不出现；棋盘按 label 定位（q∈[0,33]×display[0,26]=918 格）、表头 A..AH + 行号 1..27 + 图例，符号不变式「小写=token 大写=坐标」（a1..a9/e1..e9/t0..cN/xx），同格优先级 船>沉船>鱼雷轨>接触标记；`PlayerObservation` 增公开 wrecks（双方可见公共信息）。`GET /games/{id}/export` 只读返回 {frame, board}；run_match 逐阶段对双方各累积 export_frame 写 `-frames.jsonl` + `-board-{side}.txt`。
- **LLM 提示词重写**：prompt＝{回合/阶段、棋盘、世界态帧、legal_actions、OrderBatch/AIPlanSheet schema、按阶段 few-shot、【思考纪律】}；few-shot 全用 `SAMPLE-` 占位符（形似真 id 教格式、防照抄，turn/phase 调用时注入当前值）；【思考纪律】＝只做一件事写完整合法 JSON 即停、禁止候选枚举/自我怀疑复读/重复推导、响应以 `{` 开头正文无 JSON 外文字、situation_summary≤80 字、产出即终稿；附 hex 轴向距离公式（O14→P15=2）。reasoning 采集：`reasoning_content` → `LLMCallAudit.reasoning_preview`（截 500 字符），新增 `thinking_enabled` 构造参数 + reasoning_effort=low，max_tokens disabled=2400 / enabled=6000。
- **llm-opponent 端点**：保持同步 def（FastAPI 线程池）；守卫顺序 404→403（非 llm mode）→503（无密钥，一切调用前）→409（玩家未提交）→幂等短路（对侧已提交）→调 `OpenAICompatibleCommander(timeout 默认 90)` → `submit_orders`（引擎裁决，非法不静默修复）→ repository.save；返回 `{valid, ai_submitted, audits}`，audits 只含公开子集（side/turn/phase/attempt/elapsed_ms/tokens/valid/errors/reasoning_preview），**不含私有订单**。前端：mode 扩 "llm"、act() 分支 submit→llmOpponent→advance→refresh、Landing「对战 DeepSeek」入口、header「对手：LLM(DeepSeek)」徽标、`llmBusy` 等待遮罩防双发、503 无密钥中文提示。
- **实况压出修复 1（鱼雷 bearing）**：对局 2 失败 "bearing 5 does not match ship heading 4"——旧措辞引导模型用 launch_side/launch_angle 的 relative_heading 换算 bearing、并让模型"照抄 torpedo_candidates 的 bearing"（该字段根本不存在）。修正：领域指导明确 `TorpedoOrder.bearing = launch_positions[i].heading`（发射瞬间舰船航向 1..6，不是鱼雷行进方向），launch_at_mf=i、launch_hex=launch_positions[i].hex，launcher_id/launch_side/launch_angle/setting_index 取该舰 launchers/settings；删除"转出的相对航向"旧措辞 + 新增测试。修复后对局 3 重试=0。
- **实况压出修复 2（地图边缘世界平移中止）**：对局 3/4 DeepSeek 把 3 艘 DD 连驶 4 回合南下（O14→J16→E19→A21）压上南缘，而同盟鱼雷轨贴住南缘（F26/G26/I25）→ 引擎 `_shift_world_for_map_edge` 抛 "Map-edge world shift would move a counter beyond the opposite edge"，对局中止。隔离验证 tactical-vs-tactical 干净 → DeepSeek 特有；提示词加地图边缘纪律（对局 4）仍不够。引擎修复：`_resolve_movement` 对 `_shift_world_for_map_edge` 包 try/except ValueError → 不平移、该舰停当前边缘格（`stopped.add`）、发 `movement_blocked_by_edge` 事件（rule IBS-R-06.1.8「把出界舰留在边缘格」），其余算子照常结算、对局不中止。用户在我提问处理方案时回复"继续"，按推荐项"停靠边缘"实施并如实记录。
- **CLI 实况**：对局 5（bearing 指引 + 边缘修复）`completed=True, winner=axis, turns=4, wall=220.4s, deepseek_calls=16, retries=0, timeouts=0, failures=0, 单次最长 44.1s < 90s`；16 个 (回合,阶段) reasoning 样本全阶段覆盖、无候选枚举/自我怀疑/复读标记，鱼雷推理已正确读 launch_positions[].heading。
- **API 实况**：TestClient 驱动完整 4 回合对局——create_game(mode=llm)→view→suggested-orders→/orders→/llm-opponent（thinking_enabled=True，真实 DeepSeek）→advance；16 次真实调用全部 200/valid，1 次自纠重试（turn-2 movement_planning attempt1 失败 → attempt2 23.7s，单阶段合计 67.1s < 90s）；幂等短路核对 16×（第二次调用 audits=[] 不重复调用）；503 守卫核对（删密钥→503、未发起调用）；audits 逐条断言不泄漏私有订单/计划字段。验收中修复：/view 必须带 X-Player-Side（否则 400）、leak 断言改 JSON 键比对（reasoning_preview 合法含英文单词）。
- **测试与构建**：新增 test_state_export.py（帧键/坐标往返/迷雾隐藏超视距敌舰/hidden_damage 敌三项 None 己方 int/wrecks 双方可见/sequence==events 末条/棋盘 27×34 表头 A..AH 图例/label 落位/火与残血后缀/冲突优先级）+ test_llm_prompt.py 9 例（prompt 含棋盘表头+帧真 id+【思考纪律】、few-shot 只用 SAMPLE- 不含 IBS-U- 真 id、few-shot turn/phase 注入当前值、reasoning_preview 有/无两态、thinking disabled/enabled payload、bearing=launch_positions[i].heading、地图边缘纪律、不泄漏敌方私有损伤）+ test_api_llm_opponent.py（403/503 无请求/409/成功无私有订单/幂等/非法不静默）+ test_match.py 更新 + 引擎 `test_pathological_map_edge_stops_ship_instead_of_aborting_match`；全量 `144 passed`。本机无 node，前端提交前经人工审查确认（tsc/Vite 未能跑，待有 node 环境补构建验证）。

## 2026-08-26：战报系统（每阶段双视角截图 + 每回合 LLM 叙事 + 随时调出 + 下载 MD）批次

- **目标**（用户）：开始 UI 点击后每阶段保存双方视角地图截图、每回合 LLM 叙事战报、维护 MD 文档、对战过程随时可调出、最后可下载；适配人vs人/人vsAI/AIvsAI。用户已确认：叙事＝中立战史视角一篇/回合；下载＝单文件 .md（截图 base64 内嵌）。
- **提交**：本批次尚未提交（提交哈希待补；涉及新增 `battle_report.py`、`tests/conftest.py`、`tests/test_battle_report.py`；改 api/engine/llm/match/models/storage/state_export、前端 types/api/App/BattleReportModal/style.css、.gitignore、pyproject 补 Pillow）。
- **引擎只读边界**：战报层只用 `observe`/`get`/`engine.event_visible_to`，绝不改状态/裁决；规则常量不复制到引擎外（地图几何投影复刻前端 `hexGeometry`）；DeepSeek 只从 `DEEPSEEK_API_KEY` 环境变量读取、密钥不写文件。
- **截图（Pillow 服务端渲染，约 1330×1359）**：几何与前端 `hexGeometry` 完全一致（flat-top odd-q、HEX_SIZE=24=外接圆半径、A1=(94,79)、B1=(130,99.78)）；图层顺序 地形→标记（contact 空心圆+? 绝不画敌方 truth）→鱼雷轨（航向箭头）→沉船（xx）→舰船（侧色三角朝 heading + 与 ASCII 棋盘一致的 token、fire 点、仅当 `hull is not None 且 <0.35` 画残血星）；只画该侧 `observe` 可见集（hidden_damage 敌 hull=None 不画残血星、超视距敌舰不出现）——与 `_board_cells`（从 state_export 抽出、ASCII 棋盘与 PIL 同源）一致；标注 列 A..AH + 行 1..27 + 底部图例带含比分。
- **叙事（中立战史一篇/回合）**：`public_events_for_turn`＝该回合「至少一侧可见」事件并集，排除 orders_submitted/phase_changed/game_created（orders_submitted 携完整私有 order_batch）；`build_narrative_prompt` 只传引擎 message+公开骰子、附双方各侧 observe 态势，不传 payload；`OpenAICompatibleCommander.write_narrative`＝纯文本兄弟方法（**无** response_format、thinking disabled、temperature=0.7、max_tokens=800、无重试）；无密钥/失败→`deterministic_fallback_narrative` 事实摘要；战报任何异常被吞、绝不影响对局。
- **编排**：create 钩子开局双视角快照；advance 钩子 **`prev_phase` 在推进前记下**→推进→结算后截图（label=prev_phase，sequence 后缀避免同名）；FIRE_END 门控触发上一回合叙事（FIRE_END→REINFORCEMENT 叙事回合=turn-1、→COMPLETE=turn 不变；CONTACT_SETUP→REINFORCEMENT 回合未变只截图不叙事）；`battle_narrative_exists` 幂等；DB 第 4 张表 `battle_report` PK(game_id, sequence, side) INSERT OR REPLACE（capture side=axis/allies、narrative side=both，同 sequence 不冲突）。
- **端点（只读、无需 side 头——中立历史文档）**：`GET /games/{id}/battle-report`→JSON `{meta, turns:[{turn, narrative, phases:[{phase, captures:[{side, image_path}]}], events}]}`；`GET /battle-report/image/{rel_path}`→PNG（路径穿越守卫 `resolve().is_relative_to(base)` 否则 404）；`GET /battle-report.md`→自包含 base64 MD（`Content-Disposition: attachment`）。
- **AIvsAI**：match.py 增 `battle_report` 参数（默认关）+ `--battle-report` CLI；repository=None 只落 PNG+返回条目，FIRE_END 处同 API 路径叙事（有密钥 LLM 否则摘要）；终局写 `{game_id}-battle-report.md` + `.json`（条目索引供测试断言）。
- **前端**：types.ts 增 BattleReport 五型（Capture/Phase/Turn/TurnEvent/Meta）；api.ts `createGame` 增 battleReport → `options.battle_report`、新增 `battleReport(id)`/`battleReportImageUrl(id,path)`（encodeURIComponent）/`battleReportDownloadUrl(id)`；App.tsx Landing 增「自动记录战报」全局勾选（默认 true→传入所有 start 入口）、header 增**常驻「战报」按钮**（任何时刻调出）、回合末 fire_end 改调 `openServerReport()`（替换客户端组装 openTurnReport，服务器为唯一事实源）；BattleReportModal.tsx 改服务端数据：回合 tabs + 叙事纯段落 + 每阶段双视角缩略图（点击 lightbox 放大）+ 分组公开事件 + 比分/胜负 + 「下载战报 (.md)」用隐藏 `<a download>` 点击 + 「战报含双方视角」公平性注记。style.css 加对应样式。
- **测试**：test_battle_report.py 16 例全绿（几何 A1/B1/顶点半径=24、渲染尺寸与双视角不同、渲染纯观察驱动、hidden_damage 不画敌残血星、存储幂等、battle_narrative_exists 门控、create+advance 捕获持久化 ≥14 张+恰好 1 条叙事、battle_report 关不写、BrokenCommander 回退、无密钥抛 RuntimeError、LLM 路径无 response_format/temperature=0.7/max_tokens=800/prompt 无 orders_submitted、public_events 排除 orders_submitted、MD 自包含 base64 计数==截图数、JSON 形状+image 端点、路径穿越 404、match on+off）；conftest autouse 删 `DEEPSEEK_API_KEY` + `api.reports_root` 指 tmp。全量 `300 passed`（284 既有 + 16 新）。
- **CLI 实况**：`python -m iron_bottom_sound.match --scenario IBS-S-03 --seed 3 --artifacts tmp/br-match --battle-report` → `passed=true`（axis 胜、32 请求、2.4s）；4 回合 56 张 PNG（28 结算后阶段×2 侧）；MD 5.7MB 内嵌 56 图（base64 计数与截图数一致）、确定性叙事含「第 1 回合」、胜负行正确。API 实况由测试覆盖（TestClient 打真实端点）。本机无 node，前端提交前经人工审查（tsc/Vite 待有 node 环境补构建验证）。

## 2026-08-26：LLM(DeepSeek) vs 状态机 AI 实况对局 + 战报系统全量验证（用户要求，想定1）

- **目标**（用户）：用 LLM 对战状态机 AI 打一局、输出战报验证。想定7（库拉湾海战）在 catalog.yaml 为 catalogued 但**无 scenario-07.yaml 数据文件**（resources/derived/structured/scenarios 只有 01/03），`load_scenario` 抛 KeyError——经 AskUserQuestion 用户选想定1（IBS-S-01，正好 7 回合）。
- **实况压出的引擎 bug（真 bug，已修）**：`legal_actions` 的 `movement_candidates` 过滤条件是 `side 匹配 and position 非空`，**漏了 `not ship.sunk`**——沉没但仍占格的舰（漂移未结算成残骸、`sinking_drift_pending=True`）被列为可动舰候选，与校验 `owned`（排除 sunk）不一致。第一局 T7 movement_planning 三连败（"Movement references non-owned ship IBS-U-IJN-KINUGASA"+extra=[KINUGASA]），LLM 看到候选里有 KINUGASA(CC17) 便规划它。修复：候选过滤加 `not ship.sunk`（与 `_gunnery_candidates`/`_torpedo_candidates`/确定性指挥官 llm.py:202 一致）。诊断细节：帧/回放交叉验证——帧里 sunk 用 `status:["sunk"]`（不是 `sunk` 键）、位置用 `hex`（非 `position`），CC17==q28r2；引擎状态 sunk=True、owned 排除、observe 正确。
- **结构性改进（movement 候选附精确 plan）**：`movement_candidates` 的每个 reachable 格用 `movement_path` 附上引擎算好的精确合法 `plan` 串——AI 只挑目标格、照抄 plan（speed=其 cost），不再自己推命令序列（强制转弯/首动 advance/直航 MF 数由引擎保证）。纯只读构造辅助，裁决不变。
- **提示词纪律加固（沉船/炮击/增援/移动 4 处）**：① 沉没/倾覆舰（status 含 sunk 或棋盘带 ~）不是可动舰，不填 movement、不在「覆盖每艘活动舰」之列；② GunneryOrder 只对 gunnery_candidates 里 targets 非空的候选开火、mount_id 原样取自 targets 的 mount_ids（第二局 T6 失败：LLM 自造不存在的 KINUGASA-M1/M2 且全轴心 targets 为空仍强行开火）；③ ReinforcementOrder 只增援 reinforcement_candidates.ships、entry_hex 取自 entry_hexes、group_available=False 或 ships 空则留空（第三局 T4 失败：自造不可用增援组+错误入口）；④ movement 照抄候选 plan、reachable 不含当前格（无 cost0）则必须移动（第四局 T5 失败：Kinugasa 桥损 forced_circle_turns=2 必须 60 度转弯，模型给了不满足的命令）。
- **--model CLI**：match.py 增 `--model`（默认不变 deepseek-v4-flash，`OpenAICompatibleCommander(model=...)`）。探测 deepseek-chat / deepseek-reasoner 端点均 200；因用户指示用 flash，最终以默认 flash 完成。
- **对局实况（5 局收敛）**：① T7 movement 沉船（引擎 bug 修复）② T6 gunnery 自造炮位（纪律）③ T4 reinforcement 自造增援（纪律）④ T5 movement 强制转弯（plan 辅助）⑤ 成功：`passed=true, completed=true, winner=allies`（想定1 第7回合胜利判定）、50 请求、轴/盟各 25 plan、elapsed=121.6s、retries 全程 0 次（final：request_count=50）。产物 `tmp/br-llm-s06/`。
- **战报系统全量验证（本批核心交付）**：7 回合**全部有 LLM 叙事**（neutral 战史文风，抽查第 4 回合文本连贯）、90 张 PNG（turn1=6 张开局局部、turn2-7=14 张/回合=7 结算后阶段×2 侧）、MD 10.5MB 自包含（`data:image/png;base64,` 计数==90==PNG 数）、meta 完整（scenario IBS-S-01、mode llm、seed 7、turn 7/7、phase complete、winner allies、victory_reason「想定1 胜利：到达第 7 回合」、score{axis:4, allies:11}）。三模式战报适配 + 失败局产物（s01 到 T7 中止）均验证过。
- **测试**：新增 `test_movement_candidates_exclude_sunk_ships_even_with_pending_drift_position`（沉没占格舰不入候选、其余活动舰列全）；test_llm_prompt.py 随纪律更新；部分回归 144 通过，全量后台复跑中。待确认全量数字后补记。
- **密钥**：用户在聊天贴出新 key `sk-8758...`，全程仅命令内存注入（`DEEPSEEK_API_KEY=... python -m iron_bottom_sound.match`），**未写入任何文件**；按既有实践提醒用户轮换。
- **战报 MD 乱码修复（用户打开后反馈"完全不可读"）**：文件本身是**干净 UTF-8**（GBK 解不开、干净叙事字节都在），问题是无 BOM → 中文 Windows 编辑器/VS Code 误按 GBK 打开显示乱码。修复：match.py 写 `*-battle-report.md` 改 `encoding="utf-8-sig"`（自动 BOM），api.py `GET /games/{id}/battle-report.md` content 加 `""` 前缀；测试两处加 `response.content.startswith(b"\xef\xbb\xbf")` / `md_text.startswith("")` 断言；用既有 battle-report.json + `build_report_markdown` 重新生成了 s06 的 MD（BOM+90 图+10.5MB，确认 IDE 可读）。
- **战报地图舰船位置偏移修复（用户反馈"图里船的位置不太对"）**：根因 `battle_report.hex_center(q,row)` 把第二参当**显示行**（`(row+(q&1)*0.5)·H`），但舰/标记/鱼雷/沉船全传**轴向 r**（`HexCoord.r`，前端 `hexCenter` 同义）。东侧列差 `floor(q/2)` 行：G 列高 3 行、R 列高 8 行、CC 列高 14 行（对局常在 CC17 沉没占格）。修复：`hex_center/hex_vertices` 改为收轴向 r（`(r+q/2)·H`，与前端逐字一致），`_draw_terrain` 显示行→轴向换算（`row-q//2`）；标记/鱼雷/沉船/舰船调用无需改即正确。测试：`test_hex_geometry_matches_frontend` 扩为逐字断言前端公式于多列 + R16/CC17 标签往返。像素验证：正确格 9/18 船色、旧错位格 0/18；**301 passed (63.4s)**。
- **前端静态托管（本机无 node，用户要求"用codex自带的"但 codex 也不带 node）**：全盘检索 node.exe（C/D/E 盘、Program Files、用户目录、.codex/扩展/VS Code）均无 → vite dev 跑不了。改为后端单进程托管：`api.py` 加 `/api` 前缀剥离中间件（复刻 vite 代理 rewrite）+ 末尾 `StaticFiles(dist, html=True)` 挂载（仅接管未匹配路径）。打开 `http://127.0.0.1:8000` 即测。注意 dist 是昨晚构建，缺今天 `dd5ff05` LLM 对机接线前端提交（不影响地图/战报渲染）。备选：winget 装 node 可跑完整 dev + 重构建。
- **风格状态机对战基准框架（bench.py + tests/test_bench.py）**：`python -m iron_bottom_sound.bench --games N --workers W --profiles ... --out ...`。轮转分布到全部有序非镜像组合（6 风格×5=30 组，同组合共享连续 seed 集）；`ProcessPoolExecutor` 多进程并行（CPU 密集纯 Python，GIL 下线程无效）；每局走 `match.run_match`，只收 `MatchReport` 公开字段，引擎唯一裁决、零共享状态；聚合"作轴心/作盟军/合计"胜率 + 组合矩阵 + 结局分布，写 bench-report.json/.md。确定性：50 局复跑共享 50 局 0 分歧。**性能**：50 局 11.6s、90 局 18.0s（8 进程；串行约 0.96s/局）。**测试**：+5（组合构造/轮转分布/小规模并行/串行确定性/md 渲染）；全量 306 passed (88.9s)。
- **50 局基准结果（想定1 IBS-S-03，6 风格）**：`tmp/bench-50/`。50 局过 30 组合（20 组 2 局+10 组 1 局），各风格轴心胜率全是 40% —— 是**稀疏采样假象**（轴心风格确实生效：同 seed1 下 balanced(轴) 胜 brawl(盟) 而 fleet(轴) 败 brawl(盟)）。
- **90 局均分确认（3 局/组，`tmp/bench-90/`，轴心总体 47.8%）**：真实结构浮现 = **风格效果随阵营角色而变**（想定胜负不对称：德方"无德驱被击沉/减速=胜"，英方"击沉德驱=胜"）。作盟军（进攻使命）line/brawl 66.7%、balanced 60%、cautious 20%（不敢打不杀）；作轴心（生存使命）cautious 66.7%、line 26.7%（冲锋被击杀）。结局交叉验证：cautious 作轴心胜=全"德军战术胜利"（存活）、作盟军败=全"德军战术胜利"（不杀）；line 作盟军胜=全"英军战术胜利"（击沉）。**无全局最优风格，只有角色最优**：balanced/torpedo/brawl 全才，cautious 偏守、line/fleet 偏攻。多 seed 才稳定 → 框架默认按组合轮转 seed。

## 2026-08-26（批次 2）：用户自备 LLM 密钥 + 科研用途同意（落库 + Server酱通知），本地/线上同步（提交 `901a271`）

- **需求（用户）**：战报与 LLM 对战需要 LLM API——改为**用户主动提供自己的密钥**；开局提供「是否愿意把对战记录用于科研论文」选项，愿意可留称呼；同意保存到服务器并用服务器通知模块通知作者（用户选 **Server酱 / 微信推送**）。
- **用户密钥（内存专用，绝不落盘）**：api.py `CreateGame`/`LLMOpponentRequest` 增 `llm_api_key`/`api_key`；进程内存 `_user_llm_keys[game_id]`（重启即清、不写库/盘）；llm.py `OpenAICompatibleCommander.__init__` 增 `api_key`，`_resolve_api_key()` = 用户密钥 > `os.environ[DEEPSEEK_API_KEY]`。解析优先级：本次请求 api_key > 开局注入 > 服务器 env；全无 → 503「请先提供你自己的 LLM API 密钥」（一切 LLM 调用前短路，测试断言不发起调用）。战报叙事 advance 钩子同优先级用用户密钥（`OpenAICompatibleCommander(api_key=...)`）。
- **科研同意**：`ResearchConsent{allow, handle≤40}` 随 create_game 传入 → 新表 `research_consent(game_id PK, allow, handle, scenario, created_at)` 落库（INSERT OR REPLACE，失败吞掉不影响建局）；`allow=True` 时后台 `BackgroundTasks` 推送一条通知（异步、失败静默、绝不携带订单/损伤/密钥，只含想定/局号/是否同意/称呼）。
- **通知模块 notify.py（可插拔渠道）**：`IBS_NOTIFY_CHANNEL=serverchan|none`（默认 none，只落库不推送）、`IBS_NOTIFY_SERVERCHAN_KEY`；Server酱 `POST https://sctapi.ftqq.com/<key>.send`（title=铁底湾：新的科研用途同意，desp 含想定/局号/同意状态/称呼），`code==0`→True，任何异常吞掉返回 False。
- **前端（Landing）**：新增「LLM API 密钥」password 输入（提示仅会话内存、不上传/不落盘，可一键清除）+「科研用途同意」勾选（勾选后显示称呼输入，maxLength=40）；`createGame`/`llmOpponent` 传参（llmOpponent 请求体带 api_key，每次行动走本次密钥）。
- **测试**：新增 tests/test_research_consent.py 13 例（密钥仅内存不落库、注入/请求级/服务器 env 三优先级、advance 叙事用注入密钥、同意落库+通知、拒绝只落库不通知、未传不落、落库失败不影响建局、Server酱 URL/标题/正文、非 0 码/异常→False、channel 未配置→False）；更新 test_api_llm_opponent.py 适配 `api_key` 工厂签名与新 503 文案。全量 `334 passed`。
- **本地环境注意**：仓库路径含中文（铁底湾），pytest 默认 basetemp `.pytest-tmp` 被残留进程/ACL 锁住 → 用 `-p no:cacheprovider --basetemp=$TEMP/ibs-pytest-tmp` 规避；另残留的本地 dev server（`python -m iron_bottom_sound`）需先 `taskkill` 释放 DB 锁。前端本机无 node，构建在服务器验证。

## 2026-08-26（批次 3）：选出的状态机 AI 加入本地端 + 服务端（标注胜率、写简介）

- **需求（用户）**："现在先把这些选出来的状态机加入本地端和服务端，调各个风格的冠军，标注胜率，介绍一下"。经 AskUserQuestion：**训练规模 = 就用现在训练完的**（不跑新的 6 场风格锚定 GA）；**阵容 = 6 内置风格 + 全局进化冠军**。
- **测量赛（不训练只测量，~10 分钟）**：`rl/style_tourney.py` 扩展为多想定（--scenario 逗号分隔），跑 7 profile（6 内置 + 全局进化冠军）× 双想定（S-03+S-01）× 12 局/槽 × 双阵营 = 2016 局，`rl/results/style-tourney-final/`（games.jsonl + style-summary.json，含逐想定×阵营 + 两两矩阵）。
- **双想定综合胜率差分（288 局/风格）**：balanced **+0.018** · fleet +0.017 · brawl +0.007 · torpedo +0.003 · line −0.073 · **evolved −0.077** · cautious −0.145。S-03 全无平局（目标制、轴心侧全负）、S-01 平局 ~60%（胜利点差<4）。
- **⚠ 重要诚实结论**：**进化冠军在 7 阵容全体互殴里排倒数第二**——此前 fresh-seed 验证的 +36 Elo 只对 balanced 单独有效；对上 torpedo（两想定合成 −0.333）尤其吃亏。"进化冠军"的价值是**打法个性（防守反击：热点集火+高撤退+抢胜利点）而非更强**，胜率标注与实际对局一致。若想要各风格独立的进化冠军，需另跑 6 场风格锚定 GA（~2.5-3h）。
- **接入（后端，本地端+服务端共用）**：新建 `champions.py`（`CHAMPIONS["evolved"]`，16+3 字段代码常量自包含，不依赖 rl/ 文件，生产部署可用；附 `CHAMPION_INFO` 元数据）；`match.py make_session` 加 `_resolve_profile`（字符串先查 CHAMPIONS 再查 PROFILES，本地引擎可 `axis_profile="evolved"`）；`api.py ai-opponent` 校验/取值改 `PROFILES | CHAMPIONS`（`CHAMPIONS.get(name, PROFILES.get(name))`，未知名仍 422）；`models.py GameOptions.ai_profile` 注释更新。
- **前端（本地端 UI）**：`App.tsx` `AI_PROFILES` 改富结构 `{id,label,group,intro,win}`，下拉 `<optgroup>` 分「内置风格/进化冠军」两组，select 下方 `.vs-persona` 显示所选简介 + 胜率标注，对局徽章按 label 显示。7 个简介文案按基因+实测行为写。**本机无 node**（`npx` 不存在，全盘已检索过），tsc/vite 构建留服务器做，TSX 改动人工核对语法。
- **测试**：新增 `test_vs_ai_accepts_evolved_champion_profile`（建局 ai_profile=evolved → 玩家提交 → ai-opponent 200）；全量 **331 passed**（0 失败）。本地引擎冒烟：`run_match(axis_profile='evolved')` 一局跑通。
- **产物**：`rl/results/style-tourney-final/`（胜率表）· `backend/src/iron_bottom_sound/champions.py`（注册表）· 前端 `App.tsx`/`style.css` · 结论入 `rl/DESIGN.md §10`、`rl/README.md`。

## 2026-08-26（批次 4）：状态机 AI 阵容部署到线上（fuwenji.asia/tiedi）

- **需求（用户）**："接入服务器了吗" → 提供线上 root 凭据（密码仅瞬时环境变量传参，绝不落盘/进仓库）要求部署。
- **部署路径（无 git remote，rsync 替代）**：本机无 sshpass/rsync → `paramiko`（SFTP 传 tarball + SSH exec）。打包排除 `.git/tmp/node_modules/artifacts/backend/reports/backend/*.sqlite3*/rl/dist/__pycache__/.venv/.pnpm-store/.pytest-tmp/.pt-run-*`（88MB/460 项），SFTP 上传 59s，服务器 `tar xzf` 解到 `/opt/tiedi`，**线上 DB（3.8MB+WAL）与 .venv/密钥文件未触碰**。
- **后端**：无需重装（editable install 直接读 src），冒烟 `_resolve_profile('evolved')` → 冠军基因（w_enemy_heat 2.51 / w_retreat 3.0）就位。
- **前端（服务器构建）**：`npm install --no-audit --no-fund && npm run build -- --base=/tiedi/` → **tsc 通过** + vite 1.57s 产出 `dist/assets/index-CsaiKKjG.js`（含「进化冠军/GA 进化·防守反击/内置风格」字符串）。
- **重启 + 全链路线上验证（公共域名直测）**：`/tiedi/` 200；scenarios API 正常；建 `ai_profile=evolved` 人机局 → 玩家未提交时 `ai-opponent(profile=evolved)` **409 而非 422**（风格过校验）；玩家提交增援后冠军真出招 `{"valid":true,"ai_submitted":true}`。systemd 无启动报错。
- **线上遗留**：验证局 `5c5afda2-...`（IBS-S-03 seed 5，ai_profile=evolved）写入线上 DB（1 局，无科研同意，不碍事）。
- **部署教训**：SFTP 对某特定文件名 open 瞬时 ENOENT（同名大文件换名即好，怀疑残留/tmp 状态）→ 遇到即换名重传；大文件 SFTP 在本链路 ~1.4MB/s，59s 传 88MB，确认后删临时包。

## 2026-08-27：多模态 LLM 可见地图与智谱接口

- 提交 `d7ede17`：将固定 DeepSeek 对手解耦为请求级供应商/模型配置，新增智谱 BigModel 官方兼容端点；玩家可在首页选择 `zhipu/deepseek`、手填模型并开关可见地图。
- 每个 LLM 命令阶段发送阵营过滤的 `PlayerObservation`、合法动作 Schema、文字棋盘和服务端 PNG；图像复用战报地图渲染器，不读取浏览器 DOM、调试图层或任何一方秘密计划。智谱消息使用 `text + image_url(data:image/png;base64)`，且不发送 DeepSeek 专属 `thinking/reasoning_effort`。
- 密钥仍仅存在浏览器 React 内存与后端 `_user_llm_keys` 进程内存；新增配置也不进入 `GameState`、SQLite、事件、战报或审计。供应商错误仅保留状态码与脱敏消息摘要。
- 证据：`tests/test_llm_multimodal.py` 覆盖智谱端点、指定模型不静默替换、PNG 签名/尺寸、双阵营图像不同且同种子确定、密钥不进入审计；LLM/战报相关 `61 passed`。TypeScript 检查通过，Vite `40 modules transformed` 生产构建通过；浏览器确认默认“智谱 BigModel + glm-5.3-flash + 发送可见地图”，供应商切换会更新建议模型。
- 全量测试运行到 `335` 项时仅 `tests/test_ship_records.py::test_all_playable_and_reinforcement_ships_have_verified_records` 失败：用户并行“二马”扩展已把加载记录从 30 增为 54，旧测试仍硬编码 30；该失败不在本提交文件内，本批次未回退或改写其未提交数据。
- 真实调用状态：官方文档当前以 `glm-5v-turbo` 演示图像输入，未核实 `glm-5.3-flash`。用户密钥未写入命令或测试；真实端点调用待发送密钥及阵营地图前的即时授权。

## 2026-08-27：导入“二马”扩展想定并接入状态机 AI（提交 `3f23f69`）

- **来源与审计**：逐页核验 `二马_想定.pdf` 和日美船表图，导入规范 PDF、想定页、船表总览/分国记录图及非舰娘棋子剪影；扩展来源清单进入 `resources/originals/extensions/erma/source-manifest.yaml`，根清单更新为 **311 个规范文件 / 315 条来源路径**。同名“大和”棋子哈希冲突使用 `日本-BB-大和-二马.png` 隔离，原素材保持原哈希。
- **想定与船表**：新增可玩 `IBS-S-EM-01`（第二次马里亚纳海战，8 回合，日方能见度 15、美方 13，第 1 回合从炮击开始），完整保存自由部署区域、交替部署、101+ 炮击命中扩展、日方 3.9 英寸穿甲特例和第 8 回合计分/25 分差胜负；录入双方各 12 艘共 **24 艘**舰船的舰体行、速度、装甲、主/副/高射炮、鱼雷装载/备雷、雷达、MFC 与 VP。引擎默认编队仅用于立即开局，不改变来源规定的自由部署约束。
- **解耦与接入**：船表加载器改为基础数据 + `ships/extensions/*.yaml` 扩展发现；想定加载按 catalog 的 `definition` 解耦，不再假设纯数字 ID；新增 `scenario_rules.py`，把想定 1/3/二马的命中、穿甲和胜负例外从臃肿的通用引擎抽出。没有复制用户新 AI：新想定直接复用 `TacticalCommander` 的 `observe → legal_actions → submit_orders → advance` 接口。
- **完整终局证据**：`IBS-S-EM-01` 双方状态机 AI、seed 23 从第 1 回合炮击运行至第 8 回合自动终局；共 **58 次阶段决策、0 回退、0 人工状态修改、700 个事件**，最终轴心 42：同盟 13，轴心以 29 分差获胜；终局事件回放重建与在线状态完全一致。
- **验证**：扩展定向 **10 passed**；全量 **345 passed**（唯一提示为既有 Starlette TestClient 弃用警告）；TypeScript `tsc -b` 通过，Vite **40 modules transformed** 生产构建通过；`git diff --check` 通过；新增 PDF/PNG 均由 Git LFS 管理，未写入真实 API 密钥。

## 2026-08-27：状态机 AI 编队与友军安全修复（提交 `b8a97e9`）

- **根因**：旧 `TacticalCommander` 逐舰独立选格，整批订单没有同脉冲同格/交换格检查；`line_ahead` 只奖励任意最近友舰，不绑定纵队成员或共同舵令；鱼雷推荐不计算己方当前格和封存航路。另发现 6.1.8 世界平移只预检当前算子，剩余航路翻译失败时可能留下部分修改，制造计划阶段不存在的碰撞。
- **二马初设**：双方各 12 艘改为主力舰、巡洋舰、驱逐舰三支平行长纵队，共 6 队；每队同航向、同航速、稳定成员顺序，元数据保存于 `setup.engine_default_formations`。这只是来源自由部署区域内的便利默认值，不改变自由部署规则。
- **移动安全**：整批计划逐脉冲排除友舰同格和换位；纵队先尝试共同机动，`line` 风格让本方全部平行纵队共用舵令并保留下一回合舰首净空；损伤/边缘导致共同机动不可行时先规划约束最强舰，贪心死端会对上一艘舰与当前舰执行一步合法航路回溯。
- **鱼雷安全**：`torpedo_assist` 为每个组合返回 `friendly_risk` / `friendly_ship_ids`，风险范围包括己舰当前格和已封存移动航路；状态机 AI 过滤风险组合。玩家订单与原规则鱼雷接触裁决未被收窄。
- **规则引擎修复**：6.1.8 世界平移在修改状态前一次性预检所有当前位置、剩余舰船/隐蔽标记航路、鱼雷、船骸、烟幕及待发射格，失败则出界舰留在边缘且世界完全不变。通用规则 PDF 第 7 页已视觉复核。
- **验收**：二马 `line vs line`、seed 23 完整 8 回合，58 次阶段决策、0 回退、0 同阵营舰船碰撞；普通 tactical 双方也完整终局并通过确定性回放。全量 **352 passed**；TypeScript `tsc -b` 与 Vite生产构建通过（40 modules transformed）。

## 2026-08-27：鱼雷航迹世界平移与同步移动审计（提交 `7306339`）

- **规则核验**：回看通用规则 PDF 第 12 页 8.2 鱼雷攻击范例，确认鱼雷沿既定发射方向直线移动，途中不转向。
- **根因与修复**：6.1.8 世界平移过去只改鱼雷当前位置，没有同步改 `launch_position` 和 `traversed_hexes`；SVG 因而把两个坐标系的点连成折线。现在当前位置、发射锚点和仍在新纸图内的历史格同步平移，越出新视窗的纯历史尾迹只从显示中裁去。后续提交 `138e649` 在观察副本上按当前位置、固定航向和已航行距离重建直线尾迹，使已经保存的旧折线对局也能正确显示，且不改裁决状态或事件日志。
- **同步移动核对**：每艘舰在结算后生成仅本方可见的 `movement_plan_resolved` 事件，记录计划串、起点、原计划终点、世界平移次数/向量、实际终点及是否受阻；战报 Markdown/HTML 逐舰列出移动计划，不再只有 `movement×N`。
- **用户战报诊断**：对局 `e371d6bf-ece1-483a-8c44-2eee386a0d96` 在第 4、5、7 回合由石狩、第 8 回合由吾妻触发多次世界平移；这解释了绝对格坐标与单舰静态计划图的差异，也正是旧鱼雷尾迹产生假转弯的位置。
- **验收**：定向引擎/战报/API/移动轨迹测试通过；连同并行真实模式工作树在内全量 **362 passed**；TypeScript `tsc -b` 通过，Vite 生产构建通过（42 modules transformed）；本批次暂存差异 `git diff --cached --check` 通过。浏览器插件因本机 localhost URL 安全策略拒绝接管现有标签页，未以绕过方式继续，地图数据层回归由共线/相邻格断言覆盖。

## 2026-08-27：真实模式编队指挥链与专用状态机 AI（提交 `15a4a7d`）

- **规则边界**：新增 `IBS-R-RC-01` 至 `IBS-R-RC-07` 项目扩展规则，覆盖编队初设、领舰尾随、速度危机、旗舰继承、指挥中断和脱队撤退；原玩家表特殊损伤 31/42 的原文效果保持独立，扩展规则未伪装成原版规则。
- **引擎与数据**：`GameOptions.realistic_command` 缺省关闭；开启后插入 `formation_setup`，支持每方最多四队、领舰/旗舰/备用旗舰、1/2 格间距、领舰航路展开、整体降速或永久脱队、确定性撤退、旗舰继承及下一回合直航锁定。经典模式接口、存档缺省和原 AI 行为保持兼容。
- **AI 与安全**：新增独立 `RealisticCommander`，先做编队级规划再生成领舰订单；撤退舰由确定性控制器接管，自动合法炮击且不主动发射鱼雷。真实模式跨编队友舰同格或换位会在进入碰撞表前确定性紧急停车并写入 `IBS-R-RC-03` 事件。
- **前端**：开始界面在想定和对战类型前提供真实模式开关；新增编队初设、成员顺序、领舰/旗舰/备用旗舰、间距、编队移动和速度危机编辑器；地图预览展示由引擎展开后的逐舰目的地，敌方观察不暴露私有编队关系。
- **三想定终局**：想定 3（seed 3、9）、想定 1（seed 5）和二马（seed 5）均由两个真实模式状态机 AI 自动运行至引擎 `complete`；无人工改状态、无确定性回退、无友军碰撞或友军鱼雷命中。想定 1 的 9 次潜在编队冲突均由确定性紧急停车处理。
- **自动验证**：提交后全量 **362 tests passed**（退出码 0；仅既有 Starlette TestClient 弃用警告）；专项真实模式 **8 passed**；TypeScript `tsc -b` 与 Vite 生产构建通过（42 modules transformed）；`git diff --check` 通过。
- **浏览器实操**：本地 `http://127.0.0.1:5173/` 已实际完成“打开真实模式 → 选择想定 3 → 双方编队初设 → 热座交接 → 双方增援确认 → 轴心领舰移动 → 后舰展开预览 → 合法提交”，未出现前端或后端校验错误；页面停留在轴心移动提交后的盟军交接界面，可直接继续。
- **密钥纪律**：本批没有调用真实 DeepSeek 接口，没有把聊天中出现的任何 API 密钥写入源码、测试、配置、日志、事件或 Git。

## 2026-08-27：取消世界平移、固定扩展海图与编队状态栏（提交 `c20c0ae`）

- **固定坐标策略**：新增项目稳定性扩展 `IBS-R-MAP-01`；原 `IBS-M-MAIN` A–HH、1–27 印刷地图和地形来源保持不变，可玩区扩为 A–TT、1–39，新增区域为纯海缓冲区。该扩展明确不是原版印刷地图规则。
- **取消世界平移**：同步移动不再调用世界平移，也不生成新的 `world_shifted` 事件；最终扩展边缘只让出界舰停在当前格，事件写入 `coordinate_frame_changed=false`。舰船、鱼雷、残骸、标记、历史航迹和其他已封存计划坐标均保持不变；旧内部入口带显式禁用保护。
- **统一尺寸**：坐标模型、移动/隐蔽标记、状态机 AI、真实编队撤退、LLM 文字棋盘、火力热图、状态导出、战报图片和 SVG 地图统一使用 46×39。印刷地图第 27 行可继续进入缓冲区，例如 R27 向 4 方向移动至 Q28；R39 才是最终南缘。
- **地图 UI**：SVG 增加原印刷区/扩展纯海区视觉区分及固定坐标说明；默认“交战区”聚焦，保留缩放、拖动和“全图”按钮，避免扩图后棋子过小。
- **编队状态栏**：左侧我方从编队初设草稿开始即按编队分组，显示编队名、成员数、间距、指挥状态、领舰、旗舰、备用旗舰和逐舰角色；脱队/撤退舰单列。敌方只显示正常可见舰船，不显示私有编队结构。
- **自动验证**：全量 **366 tests passed**（退出码 0；仅既有 Starlette TestClient 弃用警告）；TypeScript `tsc -b` 通过；Vite 生产构建通过（42 modules transformed）；`git diff --check` 通过。
- **浏览器实操**：本地页面确认 A–TT、1–39 地图语义标签、原印刷区/缓冲区图例、“交战区/全图”切换以及轴心第1编队分组；敌方栏未出现领舰、旗舰、备用旗舰等关系。已将验收页面保留在本地浏览器。

## 2026-08-27：真实模式玩家规则书与前端预览（提交 `2d6f650`）

- **单一规则正文**：将 `docs/rules/realistic-command.md` 扩写为完整中文玩家规则书，覆盖权威顺序、开关、编队初设、领舰尾随、间距、共同航速、速度危机、领舰/旗舰职责、继承与指挥中断、脱队撤退、炮击/鱼雷、战争迷雾、想定胜负和四个操作示例。正文明确特殊损伤 31/42 的原版效果与 `IBS-R-RC-01` 至 `07` 项目扩展边界。
- **同源服务与安全渲染**：新增固定只读接口 `GET /rules/realistic-command`，直接返回上述 UTF-8 Markdown，不接受用户文件路径；前端弹窗从接口加载同一正文，以 React 节点渲染标题、目录、段落、列表、引用与代码编号，不使用 HTML 注入。
- **前端入口**：开始页真实模式卡片增加“预览完整规则”；进入对局后标题栏保留“真实模式规则”入口。弹窗支持目录锚点、滚动、Esc/遮罩/按钮关闭、打印及窄屏布局。
- **自动验证**：规则接口与真实模式专项 **11 passed**；全量 **369 passed**（退出码 0，仅既有 Starlette TestClient 弃用提示）；TypeScript `tsc -b` 通过；Vite 生产构建通过（43 modules transformed）；`git diff --check` 通过。
- **浏览器实操**：本地 `http://127.0.0.1:5173/` 的开始页预览成功加载 3904 字符渲染文本，确认包含原版/扩展边界、31/42、全部七个规则编号与自主撤退；随后开启真实模式并进入想定 3 编队初设，标题栏入口再次成功打开同一规则弹窗。后端已重启并保持本地运行。

## 2026-08-27：二马想定延长为 12 回合（提交 `7e836c7`）

- **来源边界**：二马原扩展资料仍记录为 8 回合、第 8 回合结束计分；新增 `IBS-S-EM-01-R5` 用户指定项目扩展，把当前可玩版本的回合上限与终局计分时点延至第 12 回合，不改损伤计分公式和 25 分胜利门槛。
- **结构化数据**：`scenario-erma.yaml` 与想定目录统一为 `turns: 12`，胜负元数据为 `end_of_turn_12`；同时保留 `source_turns: 8` 和扩展权威标记。前端继续读取观察中的 `max_turns`，没有复制二马回合常量。
- **自动终局与回放**：seed 23 的两个状态机 AI 从第 1 回合炮击运行至第 12 回合自动结束，共 90 次阶段决策、0 回退；终局 `turn=max_turns=12`，纯事件回放与在线状态一致。
- **验证**：二马专项 **7 passed**；全量 **369 passed**（退出码 0，仅既有 Starlette TestClient 弃用提示）；`git diff --check` 通过。重启本地后端后，浏览器新建二马确认显示“第 1/12 回合”且初始阶段仍为炮击。

## 2026-08-27：真实模式、二马与 12 回合补丁增量部署线上

- **增量范围**：以最后一次已记录线上部署提交 `596694f` 为基线，只上传 32 个生产运行文件（178,348 bytes），覆盖后端/前端源码、结构化规则/想定和二马棋子；未上传测试、全套原始规则资料、临时目录、SQLite、战报、`.venv` 或环境密钥。
- **存档保护**：应用补丁前使用 SQLite Backup API 将在线主库一致性备份到 `/opt/tiedi/backups/pre-5dd2965-20260827-01/iron-bottom-sound.sqlite3`；补丁归档不含 `backend/*.sqlite3*`，没有删除或覆盖旧对局。部署后只新增验证局 `fd8c5afd-bc87-4cf0-b92a-af71615b090f`（无科研同意、无战报）。
- **构建与服务**：服务器 `npm run build -- --base=/tiedi/` 通过，Vite 43 modules transformed，生成 `index-CSYto-0r.js`；后端导入断言 `ERMA_TURNS=12`，`systemctl restart tiedi` 后服务为 active。
- **公网验收**：`https://fuwenji.asia/tiedi/` 返回 200 并引用新 bundle；想定目录返回二马 `turns=12/status=playable`；验证局视图为 `turn=1/max_turns=12/phase=gunnery`。

## 2026-08-28：GLM 兼容与真实模式二马实战修复（提交 `15a4842`）

- **GLM 根因与兼容层**：复现发现原默认 `glm-5.3-flash` 为持续思考模型；未配置 thinking 时会在输出预算内只返回推理而无 JSON，显式关闭 thinking 又会被接口拒绝。新增供应商能力配置，默认改为可关闭思考并稳定输出 JSON 的 `glm-5.2`；文本模型禁止发送地图图片，只有视觉模型族允许启用视觉输入。
- **密钥纪律**：用户密钥仅作为当前测试进程的临时环境变量使用，调用后清除；源码、配置、测试、事件、战报、数据库和 Git 均未保存密钥值。提交前执行特征串扫描无命中。
- **二马真实模式修复**：未接敌时，状态机依据双方公开部署区中点生成搜索航路，不读取隐藏舰位或秘密订单；受损编队无法继续沿引导航迹时确定性永久脱队，撤退舰不再被普通战术移动规划器重复下令；`legal_actions` 为真实模式提供引擎验证过但尚未提交的编队移动建议，LLM 仍须返回订单并通过服务端校验。
- **完整状态机基线**：`IBS-S-EM-01-realistic-search-smoke-seed29-fixed2` 自动运行至第 12 回合，轴心以 50 损伤分获胜；1766 个事件、483 次炮击结果、3 次鱼雷攻击、1 次鱼雷结果、8 艘脱队、2 艘撤出，友舰碰撞 0、友军鱼雷命中 0。
- **GLM 实战证据**：`IBS-S-EM-01-zhipu-vs-realistic-seed32-accepted` 自动运行至第 5 回合，已产生 79 次炮击结果、1 次鱼雷结果和 1 次脱队，友舰碰撞 0、友军鱼雷命中 0；随后供应商返回 HTTP 429“余额不足或无可用资源包”。该中断局不计为正式 12 回合验收通过，补充额度后必须从第 1 回合重跑。
- **自动验证**：专项 35 项通过；全量 JUnit 记录为 **375 tests、0 failures、0 errors、0 skipped**；TypeScript `tsc -b` 与 Vite 生产构建通过（43 modules transformed）；`git diff --check` 通过。

## 2026-08-28：GLM/二马补丁无损增量部署线上

- **增量范围**：只上传本次 10 个生产运行文件，压缩包 104,909 bytes、SHA-256 `10df1554a7364b6ae33bea41fe689cbbcd084c859671c7849d06d11f0173eee6`；未上传 SQLite、存档、战报、测试、环境文件、API 密钥或原始资料。
- **双重回滚**：部署前使用应用 Python 3.11 的 SQLite Backup API 创建 `/opt/tiedi/backups/pre-glm-erma-20260828-01/iron-bottom-sound.sqlite3`，64,188,416 bytes，SHA-256 `bb0d5966a3a95a997793408cac445e631e83e293cbbc2fe81564b6c7689a494a`；旧运行文件另存同目录 `runtime-files.tgz`。
- **存档一致性**：部署前后均为 38 个对局、1931 个事件；最早旧对局 `6505a312-d1cd-4968-ab64-e18d542c49d0` 仍可经阵营过滤的 `/view` API 返回 HTTP 200，未新增或改写在线对局。
- **构建与公网**：服务器 Vite 构建通过（43 modules transformed），生成 `assets/index-DRlTzKX4.js`；`tiedi.service` 重启后 active，内部想定接口与 `https://fuwenji.asia/tiedi/` 均返回 HTTP 200，二马结构化回合数仍为 12。
- **本地同步**：最新本地后端与前端分别在 `127.0.0.1:8000`、`127.0.0.1:5173` 以隐藏进程运行，两个健康检查均返回 HTTP 200。

## 2026-08-29：自适应鱼雷战术、真实模式修复与断电安全 PSRO-lite（提交 8113bae）

- **真实模式优先**：训练与 fresh-seed 验收以 12 回合二马 IBS-S-EM-01 为主要槽位。修复真实指挥 AI 把附属舰逐舰规划造成的编队假冲突、撤退舰强制航向不合法，以及旗舰转移误用旧编队速度的问题；复现 seed 20260829 后完整运行至第 12 回合，0 友军碰撞。
- **自适应鱼雷战术**：基于阵营可见观察生成每艘敌舰最多 24 条公开航路假设，加入直击、封锁、破 T、切割、交叉雷幕、撤退掩护和保雷意图；比较有/无雷幕的敌方最佳响应，并用束搜索选择部分或完整齐射。最终订单仍由规则引擎严格校验，未公开鱼雷不进入规避评分。
- **接口与复盘**：增加阵营过滤的鱼雷战术分析接口、人机局默认 adaptive、计划表前三候选及终局鱼雷战术复盘；非终局战报剥离私有战术分析，避免泄露。
- **PSRO-lite**：实现三轮策略联赛、收益矩阵、regret matching、GA 最佳响应与历史策略池。真实模式二马按 1.5 倍权重计分并在最佳响应槽位加倍采样；友军碰撞或鱼雷友伤直接判无效。
- **断电恢复与面板**：每局结果提交 SQLite WAL（synchronous=FULL），同时 fsync JSONL；阶段检查点和 status 使用原子替换。主动停止写入 interrupted 且不注册未完成冠军，断电后用 --resume 从 SQLite 继续。dashboard.html 每秒显示进度、ETA、混合策略、当前最佳和错误；运行手册为 rl/PSRO.md。
- **烟雾证据**：真实模式二马烟雾联赛 2/2 完成；两局均运行到第 12 回合，无错误、无友军碰撞、无鱼雷友伤。SQLite 断点恢复重新载入 2 局并保持 complete；自适应双方 seed 47 完整终局、0 回退且事件回放一致。
- **自动验证**：最终全量 **389 tests passed**（退出码 0；仅既有 Starlette TestClient 弃用警告）；TypeScript tsc -b 与 Vite 生产构建通过（43 modules transformed）；git diff --check 与敏感信息模式扫描通过。未调用或写入聊天中出现的 API 密钥。

## 2026-08-29：正式训练首批真实模式缺陷修复（提交 d66f336）

- **训练反馈**：正式收益矩阵首批完成 75 局后，面板捕获 13 个无效结果；立即停止进程并保留 SQLite/WAL 检查点，没有让无效基线继续参与冠军选择。
- **根因修复**：编队解散时残存附属舰现在永久转入自动撤退；受强制直航影响的后舰不再追加尾部转向；安全回退在共同航速区间断裂时选择合法脱队而非非法降速；多次脱队后重新计算剩余成员共同速度。
- **续训语义**：--resume 将 ok=false 的确定性结果键视为待重跑并覆盖 SQLite 行，既保留审计历史，又不会把旧无效结果当缓存命中。
- **回归证据**：将 seed 20280829–20280832 的 balanced/balanced、balanced/torpedo、balanced/brawl 四种完整二马对局固化为测试；全部运行到真实模式第 12 回合，无友军碰撞、无鱼雷友伤。最终全量 **394 tests passed**。

## 2026-08-29：经典防过拟合槽位多舰移动死端修复（提交 97e2ac9）

- **训练反馈**：恢复收益矩阵后，真实模式无效键已由 13 个降至 3 个；新出现的两个错误均来自经典想定 1 防过拟合槽位，不是二马规则裁决。
- **安全求解**：保留原战术评分、纵队共同机动、贪心分配和单舰回溯；只有这些路径全部失败时，才对已规划前缀运行最小剩余值、前向检查的确定性多舰约束求解。搜索设 100000 节点硬上限，不允许无界拖慢训练。
- **回归证据**：balanced 对 line（seed 20270831）和 balanced 对 direct_attack（seed 20270832）均在经典想定 1 完整终局；最终全量 **396 tests passed**。

## 2026-08-29：真实撤退舰合法航路与面板修正（提交 d28b47d）

- **撤退舰修复**：受强制直航损伤的撤退舰先枚举所有合法末航向；若目标导向路径均不合法，则按当前合法速度上限到下限尝试纯直航。只有引擎确认可提交的计划才能返回，不再以未经验证的 0 MF 掩盖失败。已抵达安全边缘的舰只用显式边界停留等待同阶段撤出。
- **领舰预规划**：真实模式领舰之间出现循环预留死端时，先选各自合法路线，再交给编队展开和同步移动层执行确定性紧急停车，避免经典逐舰安全层过早否决合法编队裁决。
- **面板准确性**：无效键重跑不再重复增加 expected_games；旧无效结果被合法结果覆盖后，last_error 自动清空。专项测试验证 SQLite 唯一键仍只有一行。
- **训练回归**：七组真实二马训练种子全部第 12 回合终局，新增 torpedo 对 area_denial/crossfire 的新泽西受损撤退覆盖；两组经典防过拟合终局继续通过。最终全量 **400 tests passed**。

## 2026-08-29：真实领舰草案死端收口（提交 b5088d9）

- **层次修正**：真实指挥器的领舰预规划只是编队展开输入；极端围堵时不再调用可能抛错的经典单舰回退，而以 0 MF 草案交给共同速度、脱队和同步紧急停车层替换。未经展开验证的草案仍不可提交。
- **训练回归**：新增 brawl 对 balanced/torpedo 的 seed 20280829、20280832 三组真实二马完整终局，覆盖 Allen M. Sumner、Des Moines 领舰预留死端；三组均通过。最近一次全量仍为 400 项通过。

## 2026-08-29：正式训练计算活锁修复（提交 5db6eac）

- **现场处置**：正式矩阵停在 635/1452 约两小时，20 个工作进程持续满 CPU、SQLite 无新增完成行；安全停止父进程树后核对 SQLite 实际保存 636 个唯一结果，invalid=0，检查点、JSONL 和数据库均保留。
- **根因**：真实编队领舰草案误入经典逐舰全舰队 CSP；密集编队中的候选路径被反复调用 movement_preview，组合搜索虽有 100000 节点上限，单局仍可消耗数小时。
- **模式解耦**：真实模式在简单领舰候选失败后立即交回 RealisticCommander，由共同速度、逐 MF 尾随、脱队与同步紧急停车统一求解；不再搜索各成员独立订单。经典模式只回溯最近两舰，确无无冲突路线时提交逐舰合法且冲突最少的航路，按原版碰撞规则裁决。
- **搜索有界化**：应急 CSP 改为一次预计算候选轨迹、缓存成对冲突、5000 节点硬上限；移动计划调用内缓存各舰候选，移除重复路径计算。正常训练路径不再调用整舰队 CSP。
- **面板监控**：工作池运行时每两秒独立更新 status.json；300 秒无完成结果即写 stalled=true、progress_age_seconds 和 running_jobs，面板显示“疑似停滞”，即使主完成循环未返回也能观察活锁。
- **精确回归**：四组 evolved 对 area_denial、break_crossing_t、formation_split、crossfire 的真实模式二马卡死种子均运行至第 12 回合，0 友军碰撞、0 鱼雷友伤；balanced 对 crossfire 的经典想定 1 完整终局；PSRO 心跳/停滞/恢复测试通过。
- **全量验证**：pytest 收集并通过 410/410（退出码 0，仅既有 Starlette TestClient 弃用警告）；git diff --check 通过；真实密钥特征扫描无命中。训练尚未在本条记录时重启，下一步从同一 rl/results/psro-torpedo-v1 目录 --resume，先确认完成数越过 636。
- **断点恢复复核**：在固定实现提交 5db6eac 上以 --resume 启动 PID 20668；首次观察已从 636 推进至 644/1452，running_jobs=808、invalid=0、stalled=false、进度年龄约 4 秒，127.0.0.1:8765 面板监听正常。

## 2026-08-29：全真实模式联赛与 Windows 面板锁修复（提交 46006a9、c4e69ed）

- **第二次退出并非计算卡死**：旧混合联赛推进到 1077/1452 后，Windows 浏览器/扫描器短暂占用 status.json，os.replace 返回 WinError 5；SQLite 的 1077 行均完整。原子替换现在做 20 次有界指数退避；status.json 作为可丢弃投影，重试耗尽只保留旧完整文件，不再终止训练，checkpoint.json 持续失败仍会抛错。
- **训练域纠正**：用户确认状态机专为真实模式设计后，移除经典想定 1/3 适应度槽位；想定 1、想定 3、二马的矩阵和最佳响应任务全部写入 realistic_command=true，并以 ruleset=realistic-v1 版本化任务键和结果过滤。旧 psro-torpedo-v1 保留审计，新目录为 psro-realistic-v1。
- **安全迁移**：旧 1077 行中仅迁移 351 行本来就是真实模式的二马合法结果；365 行经典想定 3 和 361 行经典想定 1 不进入新矩阵，也不删除。
- **单局基准**：balanced 双方 seed 20260899：真实想定 3 为 1.059 秒，真实想定 1 为 2.970 秒，真实二马 12 回合为 42.109 秒；三局均自动终局、0 友军碰撞、0 鱼雷友伤。20 进程下初始 1452 局矩阵约几十分钟，数小时总耗时来自后续三轮 × 六代 × 32 个体的数万场 PSRO/GA 对局，而非 LLM 等待。
- **增援编队修复**：全真实联赛立即暴露想定 1 的纯预备增援编队在无在图舰时被 after_movement 错误标记 dissolved。现在未来增援成员仍 attached 时编队保持 assembling，入场后继续接受编队层订单。line/brawl/evolved 三个精确失败种子全部完整终局且无友军事故。
- **验证与恢复**：Windows 原子写、ruleset、任务模式、断点和面板共 8 项 PSRO 测试通过；真实模式与 PSRO 专项 37/37 通过。新联赛恢复后从 435 推进至 493/1452，三个旧无效键全部被合法结果覆盖，invalid=0、stalled=false、status_write_error 为空，面板继续监听 127.0.0.1:8765。
# 2026-08-30：大厅新手动线与二马大舰队真实模式教学（提交 `b57e2a9`）

- **大厅重构**：首屏改为“我是第一次玩 / 我想直接开战”双路径。新手先在经典夜战速成班与二马大舰队学院中二选一；熟练玩家按“对手 → 战场/指挥方式 → 席位”三步开局。LLM 密钥与模型设置仅在选择 LLM 对战后展开，战报和科研授权收进高级选项，不再与主操作争抢注意力。
- **双教学体系**：经典想定 3 教学更新为当前图形化航路、半自动教练、鱼雷预测、自动炮位筛选和分组战报；二马教学固定 `IBS-S-EM-01 + realistic_command=true`，以 8 课覆盖六队初设、战列线/指挥链、主力舰齐射、轮机战损、共同航速、降速/脱队、撤退和战损分复盘。每课明确“为什么、点哪里、完成检查、下一步”。
- **固定但可审计的机制演示**：新增独立 `IBS-TUT-EM-05` 教学事件。首轮起火/回合结束后，石狩第二回合最高航速确定性降为 3 MF；下一移动阶段的半自动草稿显式显示“战列线原计划 5 MF → 全队降速至 3 MF”，玩家可在同一正式表单改为永久脱队。正式热座、人机、LLM 和 AI 局不会触发。
- **规则边界与回放**：教学脚本不替代移动、炮击、损伤或撤退规则；玩家与教官仍通过 `legal_actions → submit_orders → advance`。新增结构化审计 YAML 和说明文档；事件记录脚本 ID、目标舰及速度轨前后值，纯事件回放重建一致。
- **实际服务验收**：本地 `127.0.0.1:8000` 以临时 SQLite 创建二马教学局，完成双方编队初设、首轮炮击、鱼雷/起火结算、第二回合增援确认和速度危机；服务返回 12 艘本方舰、3 支本方编队、`tutorial_speed_crisis=true`、石狩上限 3 MF，显式降速订单通过正式提交并推进至鱼雷计划。实际前端 bundle 含新大厅与全部教学关键文案。
- **验证**：新增 4 项教学专项全部通过；完整 Python 测试套件 100% 通过；TypeScript `tsc -b` 通过；Vite 生产构建 43 modules transformed。应用内浏览器控制进程被本机 Windows ACL 拒绝启动，未把 HTTP/bundle 核验伪装成可视点击验收。

## 2026-08-30：二马教学首轮真实巨炮接战补丁（提交 `23bfe24`）

- 补充验收发现二马正式默认部署首轮最近舰距约 24 格，超出日方 15 格能见度，半自动齐射实际为 0；拒绝用文案冒充“大炮巨舰体验”。
- 新增 `IBS-TUT-EM-01` 教学部署：只在 `erma_grand_fleet` reset 时将轴心整体平移 `+4 列/+5 行`、同盟整体平移 `-4 列/-5 行`，保持各方相对队形、航向与航速，使双方进入合法远程炮战。正式二马自由部署与所有正式对局完全不变。
- 实测编队完成后，日方半自动首轮产生 **10 艘开火舰、52 个合法炮位**；教学/API/二马扩展聚焦 **17 项测试全部通过**，新增近接部署与首轮真实齐射金标。

## 2026-08-30：想定隔离的强制交互教学（提交 `344ca65`）

- **串场根因修复**：原填单组件只接收 `tutorial=true`，导致二马也渲染通道行动的旧经典提示。现在进入教学后立即按 `scenario_id` 解析为 `classic` 或 `grand`；教学摘要、填单示范和进度键均按想定隔离。
- **从课表改为操作教练**：新增阶段化强制教练，每次只显示一个动作。点击“带我去点这个控件”后自动滚动到真实控件，四周遮罩、黄色高亮并拦截其他点击；点错区域会提示，Esc 可暂停定位。
- **真实控件闭环**：经典教学依次绑定示范航路、逐格推进、确认航路、鱼雷发射器、合法炮击和阶段提交；二马绑定舰间距、巨炮齐射、含真实速度冲突的编队选择框、同步移动、阶段裁决和最终战报。提交步骤只有引擎实际切换阶段才会进入下一课，校验失败不会假完成。
- **界面收口**：移除右栏冗长的“现在照着做”计划块，保留一段当前机制摘要和规则号；强制教练支持侧栏滚动、小屏布局及减少动画偏好。
- **验证**：教学/API 聚焦 **12 项全部通过**；TypeScript `tsc -b` 与 Vite 生产构建通过（44 modules transformed）；`git diff --check` 通过；本地 `http://127.0.0.1:8000/` 返回 HTTP 200 并提供新 bundle `index-DJydzrm4.js`。应用内浏览器控制仍被本机 Windows ACL 拒绝启动，因此明确不把静态 DOM/HTTP 检查表述为可视点击验收。

## 2026-08-30：手机/平板适配与生产无损发布（提交 `b1f827d`）

- **触控工作区**：小于等于 1100px 时改为固定底部“舰队 / 海图 / 命令”三页签，三个主区域互斥接收触控；手机阶段按钮独占一行，表单、编队、鱼雷、炮击、舰船记录和战报按可用宽度降为双列或单列，核心控件不低于 44px。
- **移动浏览器基础**：入口补齐 UTF-8、`width=device-width`、`viewport-fit=cover`、主题色和中文标题；游戏壳使用 `100dvh` 与安全区，手机横屏采用更矮底栏和侧置航路编辑器，避免地址栏与手势区遮挡。
- **教学联动**：强制教练在定位舰队、地图或命令控件前会自动切换相应移动页签；教练卡固定在底栏上方，不会把当前目标藏在不可见面板。
- **多视口实测**：使用本机 Edge/Playwright 真实点击二马教学，390×844 下三个页签均能切换且每个按钮为 126×55px，地图、舰队和命令区域互斥可见，命令区独立滚动且无横向溢出；844×390 手机横屏、820×1180 平板竖屏及 1440×900 桌面大厅均无横向溢出，首屏可见教学主入口。截图保存在系统临时目录，不纳入仓库。
- **回归**：`tests/test_tutorials.py` 与 `tests/test_api_llm_storage.py` 共 **12 项全部通过**；TypeScript 与 Vite 生产构建通过（44 modules transformed），本地产物为 `index-ChZ5GElN.js` / `index-BAYbgQbP.css`。
- **生产备份**：发布前线上 SQLite 为 46 局、1995 条事件且 `integrity_check=ok`。使用 SQLite Backup API 写入 `/opt/tiedi/backups/pre-mobile-b1f827d-20260830-2110/iron-bottom-sound.sqlite3`（66,623,320 bytes，SHA-256 `cd635cacb912cb971748ed70ef46a03dfef4b02b4db367c6a7b814d8ab04ef90`），同时保存运行文件回滚包 `runtime-files.tgz`（630,722 bytes，SHA-256 `2510a36a8feb845ec498d417afb9fe505098d8e01965e7dbe6b5d12bcbd93fc7`）；备份再次核对为 46 局、1995 事件、完整性 `ok`。
- **生产验收**：服务器从 Git 归档 `45c004284652380e22a5fdfd7701830873fbe06327ce9cb4f7da2e7722e1da7e` 构建 `/tiedi/`，生成 `index-DhJ1EQBv.js` / `index-BAYbgQbP.css`；`tiedi.service` 为 active，内部首页、想定 API 与公网 `https://fuwenji.asia/tiedi/` 均为 HTTP 200，公网入口含 `viewport-fit=cover`。发布后数据库仍为 46 局、1995 条事件、完整性 `ok`，最早旧对局经阵营过滤 `/view` 返回 HTTP 200。

## 2026-08-30：桌面双侧栏收纳与二马棋子补发（提交 `0fb22e2`）

- **桌面收纳**：舰队栏和命令栏各自增加可访问的收起/展开按钮；大于 1100px 时任一侧可缩为 44px 控制轨，两侧可同时收起，地图自动使用释放宽度。手机和平板继续使用底部三页签，不显示重复控制。
- **教学兼容**：强制教学定位舰队或命令控件时会通过现有区域事件自动展开相应桌面侧栏，同时继续切换移动端页签，避免高亮落在隐藏内容中。
- **缺图根因**：结构化想定共引用 54 张舰船棋子，发布前线上 21 张二马新增棋子返回 404；URL 基址和旧想定素材正常，根因是此前稳定部署未同步 `resources/originals/assets/images` 新文件。
- **编码纠正**：首次 ZIP 补发在 Linux 上产生 21 个乱码文件名，未把文件数增加误判为成功。随后使用经本地解包、文件名和 SHA-256 验证的 UTF-8 tar 全量同步规范目录；乱码文件被可恢复地移入备份下的 `mojibake-counters/`，正式素材目录为 262 个文件。
- **生产素材验收**：从全部结构化想定重新提取引用并逐个请求公网 `/tiedi/assets/counters/`，最终 **54/54 HTTP 200，missing=0**；大和二马与艾伦·M·萨姆纳在后端直连也分别返回 200 和正确字节数。
- **代码与服务验收**：教学/API 聚焦 12 项全部通过；TypeScript/Vite 构建 44 modules transformed。生产生成 `index-BHQPfDyw.js` / `index-CfRIcKlH.css`，公网 bundle 同时含两侧栏标签及 `fleet-collapsed`、`orders-collapsed` 样式；`tiedi.service` active，数据库发布后仍为 48 局、2084 条事件且完整性 `ok`。应用内浏览器因本地 URL 安全策略拒绝控制，未把 bundle 检查表述为可视点击验收。
- **回滚证据**：发布前 SQLite Backup API 备份位于 `/opt/tiedi/backups/pre-sidebars-assets-0fb22e2-20260830-2140/iron-bottom-sound.sqlite3`（备份 48 局、2084 事件、完整性 `ok`，SHA-256 `628e01a9817a1d73731c355401209a2aa4eff4026a765640d72d3ecaca809e40`）；旧运行文件和完整棋子目录备份为 `runtime-and-counters.tgz`（SHA-256 `3008da856e1caa869fb61814cca4b0a52c12ff677f0a4da194514f67e1e650f4`）。

## 2026-08-30：鱼雷 AI 合法性与适应度恢复（提交 `ae975f6`）

- **编队脱队修复**：真实模式先执行永久脱队，再对留队后的新领舰应用指挥中断、舰桥原速和舵损约束；旧领舰的 6 MF 强制航速不再泄漏给替代领舰或留队成员。
- **边界撤退修复**：真实模式撤退控制器已经把舰送达安全边界时，内部 `formation_emergency_stop` 可覆盖该脉冲无法继续执行的强制直航、原速及 60° 盘旋约束；经典模式与普通玩家订单不获得此豁免。
- **训练可信度修复**：任何 `ok=false` 最佳响应统一返回有限无效适应度，不再因候选位于同盟方而把 `-2` 反号成奖励。适应度版本迁移会保留 SQLite 对局账本、重置受污染的 GA/策略投影，并按完整任务载荷复用匹配结果或重算陈旧分支。
- **可视化**：8765 实时面板新增有效/无效对局分列，仍保留每两秒心跳、停滞检测和断电恢复。
- **验证**：PSRO 与真实模式专项 **42/42 通过**；隔离烟雾联赛完整执行收益矩阵、最佳响应和冠军注册；三个原失败样本（想定 1 脱队、二马强制盘旋撤退、二马舰桥原速撤退）均自动终局，友军碰撞 0、鱼雷友伤 0；`git diff --check` 通过。规则边界回看玩家辅助表特殊损伤页，真实指挥链豁免仍归属 `IBS-R-RC-*` 扩展而非原版条目。

## 2026-08-31：关机恢复后的强制损伤回归（提交 `42a14a0`）

- **现场证据**：关机前后的同一 `rl/results/psro-realistic-v1/results.sqlite3` 保留 10,944 个唯一结果，其中 10,920 个合法、24 个历史无效；SQLite `integrity_check=ok`。Windows 系统事件确认 2026-08-30 23:49 发生关机，工作池因此以 `BrokenProcessPool` 结束，不是训练账本损坏。
- **三项根因**：编队后舰尾随可生成舵损禁止的 120° 转向；地图边缘强制盘旋舰在候选搜索的中间状态被剪枝；旗舰转移锁定 0 MF 时没有向上钳制到原版强制损伤的共同最低航速。
- **规则优先级**：保留原版舵损、舰桥和强制移动的权威校验；真实指挥器在展开后再次调用核心 `validate_orders`，按舰号追溯所属编队并执行合法脱队/重算。撤退舰的 60° 盘旋直接经过权威移动预览，不用未校验的 0 MF 掩盖错误。
- **精确回放**：原第 3 代三场失败键使用完全相同的想定、seed 和双方参数复跑，均自动完成二马第 12 回合；结果分别为 41:31、49:30、56:26，三场均 `ok=true`、友军碰撞 0、鱼雷友伤 0。
- **测试证据**：修改后的既有真实模式与 PSRO 专项 42 项全部通过；新增地图边缘强制盘旋与指挥中断速度下限 2 项均通过；原版特殊损伤/强制移动聚焦 7 项通过；`git diff --check` 通过。测试第一次受仓库旧 `.pytest-tmp` Windows 锁影响，随后使用独立临时目录执行，未删除旧测试数据。

## 2026-08-31：第 0 轮第 5 代从原账本继续训练

- **恢复前核验**：`rl/results/psro-realistic-v1/results.sqlite3` 为 10,944 个唯一任务，SQLite `integrity_check=ok`；检查点停在 `best_response_round_0_generation_5`，保留 10,930 个合法结果和 14 个待同键重跑的历史失败结果。
- **精确复跑**：最后停止样本 `realistic-v1|br|0|2|22|formation_split|IBS-S-EM-01|0|allies` 使用原 seed 20783053 和双方原参数，在当前代码完整运行至二马第 12 回合，`ok=true`、友舰碰撞 0、鱼雷友伤 0，确认卷波舵损 120° 问题已由现有修复覆盖。
- **原位续训**：2026-08-31 14:46 以 `--resume` 在原目录启动 PID 40732，面板端口仍为 8765。首次观察工作队列从 1,165 降至 1,091，持续产生新合法结果，`stalled=false`；旧失败行保留到对应确定性键重跑成功后由 SQLite 原位覆盖，不参与适应度或冠军注册。
- **边界说明**：本条只记录恢复动作，不宣布训练完成或冠军可用。若出现新的 `ok=false`，训练仍按既定纪律停止并进入下一轮精确合法性收口。
# 2026-09-02 舰船列表目录迁移

状态：目录层完成；战斗参数全量迁移未宣称完成。

- 证据：外部附件与 `resources/originals/` 副本 SHA-256 一致；DOCX 7 张表共 204 条舰船目录行，PDF 共 28 页且为图像页。
- 变更：新增 `resources/derived/structured/ships/catalog.yaml`，保留舰名、英译、舰级、舰种、来源表/行及 4 条未决目录行；新增 `load_ship_catalog()` 与 204 条目录完整性测试；按 PDF 第 2–23 页逐舰视觉迁移至 `ship-records.yaml`，战斗记录从54条增至167条，重复卡按稳定 ID 去重。
- 安全边界：目录层不向引擎提供战斗数值；167 条 PDF 舰卡记录含来源页并经原页视觉核验。目录中的另外139条没有对应具体战斗卡，仍列 IBS-Q-007，不以推测值填充；PDF 第24页仅为空白记录表模板。
- 测试：`python -m pytest tests/test_ship_records.py -q --basetemp=C:\\temp\\ibs-pytest` → 6 passed；pytest 仍报告中文工作目录 `.pytest_cache` 写入警告，不影响测试结果。

## 2026-09-03：全部棋子图绑定 + 选船名录去重（未提交）

- **背景**：`D:\desktop\铁底湾\images` 的 241 张图是仓库 `resources/originals/assets/images`（262 张）的子集，棋子图早已齐全；真正缺的是「目录舰 → 棋子图」的绑定与重复项。180 条有完整记录的船本就 100% 已绑图（`validate_asset_bindings` 0 缺失）。
- **绑定**：`counter-assets.json` 增加 135 条 catalog-only（有名录、无记录）舰的绑定（180 → 315）。生成规则 = 舰名归一化（Ⅰ→1、Ⅱ→2）匹配 PNG 文件名 + 舰型 token；人工特例 15 处（比叡/雾岛 art 标 BB、Denver「丹佛 vs 丹弗」、Leander 用新西兰旗图、布里斯级 ML、KM Z 舰、Selfridge 音译、大和取原版不取二马变体）。唯一无主舰图 `美国-ML-德雷福.png`（目录无此舰名）保持孤儿；`南达科他` 等 1 艘锁定舰无对应图。
- **去重（/ship-catalog）**：名录里「同名同型已有完整记录的替身」不再单列（79 条：科罗拉多/弗莱彻/大和 → 其记录版…），只保留有档案那条；`/ship-catalog` 返回 319 → 240（180 完整 + 60 锁定）。锁定舰仍 `complete:false`，但 asset 按 catalog 绑定解析 → 有图即显示棋子预览。
- **前端**：工坊选船列表按「完整 → 锁定」排序；锁定行置灰、棋子图去饱和，标「未建档 · 名录舰暂无战力数据，暂不可选」，说明文案注明同名同型已并入完整档案。
- **保持**：不把未核验战力玩进引擎——约 60 艘真无记录的船照旧锁定（`docs/rules/open_questions.md` IBS-Q-007 已同步）；二马 24 舰 complete+asset 不变。
- **验证**：`tests/test_ship_records.py`+`test_custom_scenarios.py` **14 passed**（新增去重/锁定 asset 例）；前端 `tsc` 0 错误；重启后端后 HTTP `/api/ship-catalog` = 240，complete 舰 0 缺图，R77/YAMATO 替身已消失，ERMA 仍 24。

## 2026-09-03：大地图可选 + 巨舰剧本 92×78 副本 + 50 局真实自走统计（未部署）

- **背景**：海图长宽乘二成可选「大战场」供工坊使用；在其上对微调后的巨舰自定义剧本打 50 局观察胜率/对局。胜利条件沿用引擎既有通用分支「回合到点 VP 多者胜」（验证局 `victory_reason=想定结束时胜利点领先`）。本地自查，未上线。
- **尺寸参数化（后端）**：models/data/custom_scenarios/engine/realistic/llm/randomai/state_export/battle_report 把硬编码 46×39/34×27 推广为剧本可选 `map_columns/map_rows/printed_*`，缺省即原常量，内建剧本行为逐字节不变；列标签重复字母编解码推广到 128 列上限（q45→TT、q91→NNNN），`HexCoord` caps 放宽，`neighbor` 尺寸可选。
- **大地图副本**：由 `IBS-CUSTOM-21E8908FE969`（111 舰 / 8+8 队 / 30 回合 / 真实）生成持久副本 `IBS-CUSTOM-BIG-GRAND`，题尾「 · 大战场 92×78」，`map_columns=92/map_rows=78`、printed=92×78 整图无暗区；排布为重新适配（队形内部紧凑原间距、两军整体拉开、正面间距 G=24 列可调，非机械 ×2）。原 46×39 剧本未动。
- **前端（本轮无 node/tsc，按代码审读验证，残留风险）**：types/api/hexGeometry/HexMap/EditorDeploymentMap/editor/scenario/CustomScenarioEditor 支持按剧本尺寸渲染与工坊「地图尺寸」选择（标准 46×39 / 大战场 92×78）并往返。
- **RealisticCommander 修复**：跟从舰归队修复循环此前按「重复中文舰名」归属（axis-grand-7 纵队内两艘都叫「卷波」），把真正违规舰留在纵队导致 64 次空转修复后驳回订单；现四处跟从舰错误信息内嵌 `ship.id`，恢复循环改为 id 优先、名字兜底。真实模式专项 pytest 35/35 绿；深 10 回合冒烟 oob=0。
- **50 局自走（`sim_bigmap.py`，双 RealisticCommander 全自动）**：顺带修正 `run_match` 把非 LLM 的 RealisticCommander 点单 audit 数误当 LLM 请求、30 回合局在 ~21 回合被 `request_limit=128` 误裁 → `request_limit=100000`；`--db/--out` 相对路径改按仓库根解析。50 局（seed 1–50）10 worker 并行，单局均时 ~719 s，全程 ~1.5 h。
- **结果（50/50 完成，崩溃 0）**：同盟 32 胜（64.0%）· 轴心 18 胜（36.0%）· 平局 0；平均净分 margin=轴−盟 −52.6（min −482 / max 270）；终盘 VP 轴 252.8 / 盟 305.4；全部打到 30 回合由 VP 分胜负；首接敌回合均 1.9（min 1 / max 4）；场均击沉：轴击沉盟舰 12.8、盟击沉轴舰 15.8（总计 639 / 792）；编队纪律（50 局累计）：紧急停车轴 2412 / 盟 2357，脱队撤退轴 1508 / 盟 1559——脱队体量与此前在源 46×39 图上观测一致，属 111 舰规模下真实指挥链的系统性行为、且两图对称，非大图缺陷。
- **产物**：`backend/sim-bigmap-raw.jsonl`（50 行逐局）/ `sim-bigmap-report.json` / `sim-bigmap-report.md`（UTF-8 BOM）。

## 2026-09-03：大地图功能部署上线 fuwenji.asia/tiedi（已部署）

- **上线范围**：后端 backend/src（地图尺寸参数化 46×39/92×78 + 大战场副本生成）+ 前端（按剧本尺寸渲染 / 工坊地图尺寸选择）+ resources（catalog.yaml、counter-assets.json 等）+ 自定义剧本数据。前一日及更早批次此前均标注「未部署」，本次按用户指示正式发布。
- **部署方式**：仓库无 git remote，走 README 的增量路径——本机 tar（排除 .git/rl/artifacts/tmp/node_modules/DB/报告/训练）→ paramiko 上传 → /opt/tiedi 解压 → `.venv/bin/pip install -e . --no-build-isolation` → `npm install && npm run build -- --base=/tiedi/` → systemd 重启 tiedi。
- **服务器 DB 剧本 seed**：把本库 3 个自定义剧本（IBS-CUSTOM-21E8908FE969 天堂之战·源 / IBS-CUSTOM-BIG-GRAND 大战场 92×78 / IBS-CUSTOM-736BDFF957AB）`INSERT OR REPLACE` 进 `/opt/tiedi/backend/iron-bottom-sound.sqlite3`（新代码首连自动补建 custom_scenarios 表，schema 其余列零漂移）。
- **大地图无法游玩 bug（已修，非代码缺陷）**：工坊保存/开局 92×78 剧本报 `Invalid hex label 'PPP15'...`——本地 8000 后端进程（17:07 启动）跑的是 models.py 列编解码推广**之前**的旧模块；新代码对全 111 舰 0 解析失败。重启本地后端后 PUT /custom-scenarios/IBS-CUSTOM-BIG-GRAND 200、POST /games 201。
- **上线验证（全绿）**：`/tiedi/` 200；`/tiedi/api/scenarios` 返回 3 个自定义剧本；`/tiedi/assets/counters/1.png` 200；`POST /tiedi/api/games {scenario_id:IBS-CUSTOM-BIG-GRAND}` 201（game_id 875a2470…，phase reinforcement）；服务端 `tsc -b` 通过（前端 48 modules 构建成功，此前本地无 tsc 的前端残留风险随之消除）。

## 2026-09-04：可携式存档、刷新续玩与阶段复盘（未提交）

- **持久续玩**：首页新增 SQLite 已有对局卡片（只含想定、回合、阶段、模式和更新时间，不暴露舰船/封存订单）；当前局 id、阵营和模式写入浏览器 localStorage，刷新或后端重启后通过原 SQLite 自动恢复。
- **可携式存档**：局内随时下载版本化 `.ibs-save.json`，包含权威 `GameState`、完整事件轨迹、SQLite 历史快照及必要的自定义想定定义；SHA-256 摘要对浏览器的 `5.0 → 5` JSON 数值规范化稳定。导入会校验格式/版本/摘要/事件连续性/快照前缀/Pydantic 模型，然后以新 game_id 原子克隆，不覆盖原局；LLM 密钥仍只在进程内存，不进存档。
- **阶段复盘**：新增阵营视角复盘弹层，以滑杆/前后按钮切换真实落库快照，同屏显示当时地图、回合/阶段和裁决事件；每个历史状态都通过 `engine.observe(side)` 投影，不绕过战争迷雾。
- **自动测试**：新增导出→浏览器数值往返→导入、篡改拒绝、快照定位和阵营投影用例；存档/API 聚焦 14 项通过，完整 Python 套件 **464/464 通过**，`git diff --check` 通过；仅有既有 Starlette 弃用警告和中文工作目录 `.pytest_cache` 写入警告。
- **前端与真实交互**：TypeScript + Vite 生产构建通过（49 modules）。本地真实浏览器从首页续玩，触发下载，将实际文件重新导入并立即进局，打开复盘，返回后刷新仍恢复对局；390×844 实测存档/复盘/首页三键完整可见，`scrollWidth=clientWidth=390`，无横向溢出。损坏摘要文件在首页显示明确拒绝原因。

## 2026-09-04：完整日志、炮击目标线与双方战果弹窗（未提交）

- **完整日志**：侧栏改从阵营过滤的 `/games/{id}/events` 读取本局全部可见事件，不再受观察对象最近 40 条上限影响；显示总条数并可在“全部 / 最近 40 条”间切换，日志在侧栏内部滚动。
- **炮击目标线**：炮击阶段实时解析当前 `OrderBatch.gunnery`，地图用金色虚线箭头连接每艘己方射手与已知目标，并标示舰名和投入炮位数；切换目标或炮位后跟随草稿更新，不改裁决状态。
- **炮击战果**：炮击推进后弹出“我方取得的战果 / 敌方取得的战果”双栏摘要，列出齐射、命中、公开船体损伤及损伤 chips；严格只使用当前阵营收到的裁决事件，隐藏损伤不推测。多组炮位攻击同一目标按相邻 `gun_mount_attack` 的事件序列窗口归组，避免损伤重复计入。
- **验证**：`tsc -b` 与 Vite 生产构建通过（50 modules）。真实浏览器验证 16 条目标线、1496 条完整日志以及全部/40 条切换；隔离副本完成第 6 回合炮击后，弹窗正确汇总我方 18 次齐射/3 命中、敌方 57 次齐射/11 命中，0 命中条目无重复损伤；桌面双栏及 700px 单栏布局均无遮挡。

## 2026-09-05：Windows 双击一键启动入口（未提交）

- **入口**：项目根目录新增 `start-game.bat`；双击即可自动切换到项目目录，并用放宽当前进程执行策略的 PowerShell 调用既有 `scripts/start-game.ps1`。
- **失败反馈**：保留 PowerShell 原始退出码；失败时窗口暂停并提示查看 `tmp/runtime/backend-error.log` 与 `frontend-error.log`，避免双击后错误窗口瞬间消失。
- **验证**：从项目上级目录实际冷启动成功；`http://127.0.0.1:5173` 与 `http://127.0.0.1:8000/scenarios` 均返回 HTTP 200，PID 文件对应 Python/Node 进程存活，`git diff --check` 通过。

## 2026-09-13 v12 论文修复：第一批确定性审计（进行中）

- 基线提交：`fc77a65`（完整哈希见 research/final_v12/freeze/INPUT_MANIFEST.json）；本批新增研究文件尚未提交，既有未提交文件保留。
- 已冻结 v11 源码、稿件、结果摘要哈希和用户 v12 计划；在任何新 discovery/held-out 运行前冻结研究协议与 12-cell 验证集。
- 新增独立 causal LF scalar/vector 收益、完整 history cache fingerprint、gap 驱动 DO、失败阻断、交换耦合与几何规范化；未改动游戏裁决引擎。
- 100 个 reachable-history payoff 测试全部通过：scalar/vector 最大误差 8.17e-14、玩家交换 3.55e-15、未来 suffix 前缀不变性 0；旧代码 100/100 不一致。旧 cache 等键状态的 payoff 差 33.12。
- 初态 Grid-5 三对称控制 DO 收敛分别需要 144/109/80 次迭代；新数据在 research/final_v12/audit。200-seed Monte Carlo 和消融仍运行中，不能据此宣称 Phase A 完成。
- 新增 full-tree backward induction 与 sparse sequence form；15 项初始研究回归测试通过（包含 T=1/2/3 normal-form/DP/sequence-form 等价与单边 flexibility 单调）。更完整空间等变回归继续补充。
- 论文证明审计发现 v11 全状态 V=L 推论不成立；已给出满足其假设的反例与正确交换奇对称证明。另记录闭环旧代码 radians/degrees 缺陷，不将未证实的因果解释写成结论。
- 已通过官方 skill-installer 安装并使用 K-Dense 四项科研技能，仓库显示约 44.6k stars；具体源码哈希、版本与使用边界见 research/final_v12/skills/PROVENANCE.json。


## 2026-09-13 — v13.1 mobility/flexibility 实验停止分支完成

- 用户最新范围为读取两份 v13.1 文件、完成新实验、直到开写论文前。实验分支 codex/v13-1-mobility-flexibility；基线提交 fc77a65e970e92cca429e6c87498b0c68a70bf1e；本批次未提交、未投稿，未重写主标题/摘要/贡献/正文。
- 冻结并核验 429 个 v12/fallback 文件；原 range 假设失败标签不变，fallback 不视作二区认证稿件。未重跑完整 v12 Monte Carlo。
- 固定对手速度与策略类，完成 15 discovery +12 confirmatory 物理单元及其全部独立镜像、每单元四价值，共 216 个主价值。全部 finite matrix/DP/sequence-form，禁止旧 pose-only cache 和 receding DO 值替代。
- 首轮 parallel/.75 镜像支付失败定位到非零近接触下 ±150 度浮点射界分类。归档 209 个初次文件；原设计 hash 不改；独立实现修订 01 固定 1e-8 度边界归并并先冻结新源码，再重算所有 v13。60 个可比矩阵中 2 个改变，只有一个可用旧价值改变超过 1e-8，幅度 .0046974265。无数值对称化。
- 修订后 held-out 5/12 正、7/12 强反向，无未分辨；对手 F 的 6 个全反向。机制 0/6 物理对提高 Theta，Spearman .1696208383。按冻结 Gate 判 FAIL，停止 Grid5/7、转向率、horizon 和 rigid 扩展；未触发项不报为通过。
- 真正嵌套的 T4 绝对速度菜单能力对照 5/6 正，head-on/对手 F 为 -.5348905307；共同子矩阵误差 0、完整镜像通过；不替代主分母。27 机制单元×32 探针×6 epochs×2 alpha，共 10368 行 epoch/alpha 数据；保留负 correction、域外状态及零漂移。
- 验证：30 项目标 pytest 回归通过；主 payoff 镜像最大差 4.69e-13、主价值最大差 1.13e-13，主 M 区间最大宽度 9.08e-11，最小 |M| .348056。全部冻结 hash 及受保护 live v12/稿件匹配。git diff --check 通过。
- 交付 research/final_v13/ 中的 FINAL_V13_ADVISOR_REPORT.md、V13_Q1_GATE.md、PLAN_EXECUTION_LEDGER.md、3 轮16项记录、THEOREM_SCRATCHPAD.md、LITERATURE_NOTES.md、审稿草稿和证据表、8 组 DRAFT PNG/vector PDF 与完整数据/QA、环境/复现文档；根目录 reproduce_v13.py 提供校验和重算冻结分析入口。
- 使用已核验 GitHub K-Dense 科研批判、peer-review、scientific-visualization、scientific-writing 技能。审稿 intake、证据结构、统计披露、一致性及review lint已运行；三项一般互补/因果机制/投稿成熟度主张仍标为 unsupported，未伪报独立同行评审或一区标准认证。PNG 8 项和 PDF 8 项元数据检查通过，全部 PNG 与 PDF 渲染页已目视核验；只调整 C/D 图例布局。
- 科学结论与停止证据：research/final_v13/analysis/GATE_DATA.json、NUMERICAL_AUDIT.json、AMENDMENT_AUDIT.json；最终校验清单 FINAL_MANIFEST.json 与复现日志 VERIFICATION_FINAL.log。


## 2026-09-13 — v14 第一批：协议与核心方法实现（整体仍进行中）

- 用户批准从实验到完整稿件的v14计划；已保存MASTER_PLAN、45物理配置DESIGN、1371历史文件保护清单、技能来源和环境。分支codex/v14-budgeted-replanning；基线fc77a65，新增内容尚未提交。
- 任意固定公开日程采用完美回忆密封行动块，已实现完整序列形式、共同更新时间分解、精确历史响应定价、策略迁移/可行删点证书和预算分支定界。对称性等旧错误推论在THEORY中纠正。
- 新增核心检查：26项日程/定价/分支定界测试通过（REGRESSION_AMENDMENT_01.log），另2项行为策略重建/删点完整响应对照通过；不是一般定理的数值替代。
- 已观察v13迎头速度1实例的六项工程试运行与四个端点吻合；它不是未见验证。首开发非对称实例策略生成较慢，归档第一次执行代码/日志，固定64次定价后完整序列形式回退。物理模型/实验设计/精度未改，DEVELOPMENT_AMENDMENT_01记录。
- 已启动串行开发实验，单独进程监控8GB内存与20分钟普通任务限制；冻结测试、稳健性、消融、完整稿件和最终审阅尚未完成，不能宣称一区标准通过。


## 2026-09-18 — 论文流水线治理底座建立 + nature-skills 安装（治理/工具批次，不产生科学结论）

- **需求（用户）**：① 明确项目架构、严格按规则运行，建立 `agent.md` / havedo（仓库既有的 `havedone.md`）/ `todo.md`，每次对话按需读写，且"接下来的写入 agent.md"；② 建立长期记忆并保存在**项目文件夹下**；③ 工作时可建子 agent 分配任务，用 glm4.7 / glm4.6v 等免费模型，困难工作可用复杂模型做多 agent 协作，**主 agent 必须审计其产出**；④ 阅读粘贴文本并把提示词内容文档化；⑤ **先安装 GitHub 上的 nature skill**。
- **基线提交**：`5572b73`（`docs(v14): handoff document and copy-paste prompt for a larger machine`，分支 `codex/v14-budgeted-replanning`）。本批次**未改动**任何游戏裁决引擎、策略层、物理模型、实验设计或既有研究结论；`backend/`、`research/`、`paper_v14/`、`rl/`、`frontend/` 全部未触碰。
- **⑤ nature-skills 安装（已先做）**：源 `Yuan1z0825/nature-skills`（GitHub，约 43k★，Apache-2.0），源 commit `2375e0abdf42158ef149256f2c64b1f759a0d274`（`Merge pull request #224 ... pubmed-xxe-defusedxml`）。稳定 clone 于 `~/ai-skills/nature-skills`（保留 `.git`，可 `git pull` 更新），20 个 `skills/nature-*` 目录同步至 ZCode 用户技能目录 `~/.zcode/skills/nature-*`（约 38 MB），更新脚本 `~/ai-skills/sync-nature-skills.sh`（`--pull` 先拉后同步）。**安装方式的关键约束**：技能内部大量使用 `../../../nature-shared/core/*.md`、`../../../../nature-shared/journal-formats/*.md` 这类相对引用，因此**只能整目录复制、不能只复制 `SKILL.md`**；复制后 `../nature-shared` 恰好解析到 `~/.zcode/skills/nature-shared/`。核验证据：20/20 个 `SKILL.md` 的 frontmatter（`---` / `name:` / `description:`）合法，与既存可用技能（`citation-management`、`peer-review`、`scientific-writing`）同形状；跨技能引用 5/5 命中（`core/reader-workflow.md`、`core/terminology-ledger.md`、`core/main-text-discipline.md`、`journal-formats/nature.md`、`core/nature-abstract.md`）。已记录**非致命断裂**：`nature-paper-card/README.md` 指向 clone 的 `docs/*tutorial*.md`，复制后失效，仅影响该 README 的教程链接，不影响技能执行。另注：`nature-proposal-writer` 的 frontmatter `name:` 为 `researchwrite`（不是目录名）；`nature-shared` 是共享支持包而非独立触发技能，但必须作为同级目录存在。未改动系统 Python，未使用 `--break-system-packages`，未写入任何密钥。
- **④ 粘贴提示词文档化**：原始粘贴件 `~/.zcode/tmp/paste-attachments/2026-09-18/pasted-text-20260918-222626-3fd0cf9f.txt`。产出 `MEGA_PROMPT.md`（25 阶段 / 9 阶段组总纲；门控 5/9/20 与 `REFINE→13` / `PIVOT→8`、`REBUTTAL→13/16` 循环；阶段组职责；模板目录树与**本项目结构映射**（不另建平行目录树）；留痕机制；实验/文献/写作/页数/配图要求；共享硬约束 §9）与 `docs/pipeline/STAGE_PROMPTS.md`（**逐字照录** 24 个提示词模板 = 1 个全局 `topic_constraint` + 20 个阶段 + 3 个子提示词；`code_generation` 保留其原始 YAML 折行转义形式）。**完整性核对结论**：原文有 **6 个阶段只有名称、没有提示词模板**（8.5 `THEORETICAL_BOUNDS`、12 `EXPERIMENT_RUN`、13 `ITERATIVE_REFINE`、23 `CITATION_VERIFY`、24 `3RD_PARTY_REVIEW`、25 `REBUTTAL`），已在对应章节显式标注"原文未提供，不自行编造"。凡占位槽位未填处一律标 `⟨待定⟩`，并集中登记进 `RESTRICTS.yaml` §10 `pending_slots`。
- **①② 治理底座**：`agent.md` 扩展为治理宪法 —— 原「权威与证据」4 条、「模块边界」5 条、「变更与验证」4 条**逐字保留**（以 `git show HEAD:agent.md` 逐条比对，10/10 KEPT），新增「会话纪律（读写时序）」「长期记忆制度」「子 agent 分工、模型选型与审计」「论文流水线纪律」「红线清单 R1–R10」。新增 `RESTRICTS.yaml`（14 个顶层键；含 `compute_guard`（`TIME_ESTIMATE` pilot、条件 >100 组降种 3–5、`time_guard` 预算 80% 中断）、`authenticity_redlines`（禁随机数伪造；真实收敛 1e-8；禁 `try-except`/`np.nan_to_num` 掩盖 NaN；禁 `subprocess,os.system,eval,exec,shutil,socket`）、`writing_standards`（Introduction 800–1000、Method 1000–1500、正文 5000–6500 词、<4000 严重不足）、`evidence_redlines`（`CRITICAL_FABRICATION` 判定 + 强制 REFINE→13；试验次数一致性；`cite_key`/DOI 保真）、`environment_compat`（NumPy 2.x 四项替换）、`topic_constraint`、`pipeline_constraints`、`reporting`）。新增 `PROGRESS.md`（25 阶段台账；历史 v12/v13/v14 产物一律标 ⟨待核⟩ 而非 ✅；含 §0.1 循环版本登记表与 8 项阻塞 B-1..B-8）与 `todo.md`（滚动活动任务）。**职责划分**：`todo.md`=活动任务 / `PROGRESS.md`=阶段台账 / `plan.md`=批次计划 / `havedone.md`=只追加完成记录 —— 目的是在既有 `plan.md`（129 KB）、`havedone.md`（168 KB）基础上**补缺口，而非另建平行体系**。
- **② 长期记忆**：项目内 `memory/`（随 Git 版本化；索引 `MEMORY.md` + 6 条正文 `pipeline-governance`、`nature-skills-install`、`agent-delegation-environment`、`delegation-audit-policy`、`paper-v14-state`、`pending-user-slots`）；ZCode 自动加载层 `~/.zcode/cli/memories/projects/seawar-8a678fc43e858412/memory/` **只新增指针** `project-memory-and-governance-location.md` 并更新 `MEMORY.md` 索引，避免正文出现两份互相矛盾的副本。
- **③ 子 agent 审计纪律（已成文；并须披露一条现状）**：`agent.md` §六 定下分层委派（低风险机械活 → 免费模型；**进入论文的数值、文献条目、定理与证明、证据-主张一致性裁定、门控 verdict、PROCEED/REFINE/PIVOT 决策 → 主 agent 亲做**），以及 5 步强制审计（要可核查原始产物；主 agent 亲自重跑或抽样复核；与 `research/final_v14/` 冻结 hash 比对；**未通过项一并写入本文件**；文献保留 `cite_key`/DOI 并按 `literature_fidelity` 复核）。**现状实测（不得含糊）**：本机 `claude` CLI 已装，但 `~/.claude/settings.json` 把 `ANTHROPIC_BASE_URL` 指向 `https://api.deepseek.com/anthropic`、模型别名全部映射为 `Deepseek-v4-pro[1m]`，即它跑的是 DeepSeek 而非 Claude；`codex`/`gemini`/`ollama` **未安装**；当前 shell **没有** `OPENAI_API_BASE/KEY`、`KAGGLE_API_TOKEN`、`TAVILY_API_KEY`；`~/.zcode/cli/config.json` **只有** `plugins` 一个键，无 `providers`/`models` 映射；ZCode 内置 Agent 工具**只暴露固定 `subagent_type`**（`general-purpose`/`Explore`/`judge`），**没有** per-call 模型选择参数。**结论：在用户提供 GLM 端点、key 及客户端模型映射之前，"用 glm4.7 / glm4.6v 跑子 agent"不具备执行条件**；该前置已记入 `memory/agent-delegation-environment.md`。
- **验证**：`RESTRICTS.yaml` 经项目 `.venv`（python3.14）`yaml.safe_load` 解析通过（顶层键 14 个，门控 `[5,9,20]`，最少循环 2，红线组 5 项，`introduction` 下限 `[800,1000]`）；`agent.md` 原条款比对 10/10 KEPT；20/20 技能 frontmatter 合法；跨技能引用 5/5 命中；14 个新建/改写文件 + 工作区入口 `seawar/AGENTS.md` 全部就位且非空。**未运行**：本次为治理与工具批次，**未**运行 pytest 回归、**未**重跑任何实验、**未**编译论文，因此不产生任何科学结论，也不改变 v14 "串行开发实验仍在进行、冻结测试/稳健性/消融/整稿/终审尚未完成" 这一状态。
- **本批次提交**：`25f202c`（`docs(governance): pipeline constitution, stage-prompt registry, project memory`，15 files changed, 1850 insertions(+), 3 deletions(-)）。该提交包含本文件本节正文；由于 git 提交哈希无法自指，实际哈希由紧随其后的 `docs(governance): record batch commit hash` 提交回填。


## 2026-09-18 — M0 多主线科研验证：P0 审计 + P1 Exact Lab + A/B/C/D cheap kill tests（research/m0-validation 分支，本批未合入生产线）

- **范围**：按外部 M0 计划执行 P0（只读审计+基线）→ P1（Exact Strategic Lab）→ A0/B0/C0/D0 cheap kill tests，止步于 CHEAP_KILL_REPORT checkpoint。**未改动任何生产模块**（`backend/`、`rl/`、`frontend/` 零改动）；全部研究代码在 `research/m0/`。
- **P0**：工作树干净时从 `7ab8ac4` 建 `research/m0-validation` 分支；M0_RESEARCH_PLAN.md 仓库中不存在（计划以附件提供），已原文落库。确认 sealed orders 是真实一等结构（`engine.py:1712` 写入、`:1718` 读取、`:966` side-filtered 视图、`observe()` 不泄漏；`MOVEMENT_PLANNING→TORPEDO_PLANNING` 构成真实"已封存未执行"窗口）——A/B 前提成立。15 个 catalogued scenario 仅 3 个可 play（S-01/S-03/S-EM-01）。确定性 PASS（同配置重跑逐事件一致）；20 workers 吞吐 0.37 局/s（10 核仅 1.9×）；PSRO smoke PASS；全量 pytest 完成：1 个预存失败（`test_api_llm_storage` 教程 PNG 哈希），与研究无关。
- **P1**：`research/m0/exact_lab/`——belief-space DP + 独立穷举策略枚举双实现交叉验证（T=2–3 全族一致到 1e-12）；17/17 测试过，含 4 个必需 case。两次关键设计修正：alpha=0 时信号与 θ 无关→实验室可证退化（无 aliasing 可能）；K=2,m=2 时信号首步即识别 θ。两者均已写入 `snapshot_lossy` 防呆。
- **A0（A=WEAK，代码按预声明阈值判定）**：74 局 1573 节点全精确 Δ census；Δ 均值 0.849、随 horizon 单调（4→0.367 … 0→1.087）、同 snapshot 内 Δ 离散 1.365——信号存在。但 28/74 局 never-plan==always-plan（零 span）、55% 节点 Δ<0.1、trivial 日程在 24% 可评估点已达 (30%省,95%留) 门。
- **B0（B=PASS_TO_DISCOVERY）**：**关键度量发现**——计划原始 AliasGap（值差）在全部 72 局 sealed game 上恒为 0（假阴性！）；正确度量 snapshot-policy regret `min_a max_h[V−Q]` 下 18/72 局严格正（max 2.0，动作分歧率 0.291），Markov/negative 双对照全 0——机制特异。最小 witness：同 snapshot 下 `replan(2)` vs `continue`，Δ 差 2.0。**范围限制**：exact lab、固定对手策略、非 Nash；IBS 自然反例未做。
- **C0（C=FAIL，borderline 已上报）**：证书机器先行 6/6 单测（解析值、300 seed 覆盖、加宽不减宽）；2160 局真实校准（S-03 1080 局 13.8min 零失败 draw=0；S-01 1080 局 31.9min 零失败 draw=0.419 全 cell 为正）。模拟对比：S-03（真值+0.067 势均局）cert_sensitivity 中位 15,350 vs uniform 53,025=**省 71%**（4/5 seed，第 5 个 78k 双峰）；S-01（+0.543 一边倒局）候选 0/5 到达而 uniform 52,750。support_weighted 两场景皆永不到达（证书被支撑外 cell 支配——对"采样支撑即可"直觉的真实反例）。两个实现 bug（半矩阵轮转、未采样 cell 死锁宽度钉死 2.0）在结果入库前修复并留档。**门冲突**：文本预声明"inconsistent→SMALL"vs 代码"never-reached→FAIL"，未事后改判，登记 F12 待 PI 裁定。IBS 对局预算 2238/20000。
- **D0（D=FAIL）**：5 类缺陷 zoo（OPT/MYO/NOM/NBU/AMB；COMMITMENT-FORGETFUL 因 replan 弱支配不可表达而预先弃用）；684 测试节点。**MYO≡OPT、NBU≡NOM 在全部 684 测试上答案全同→4/5 类型原理性不可识别**（本实验室支付族不惩罚短视：coordination/anticor 平稳、delayed/pathdep 只在末轮支付）。AMB 可识别（random 中位 23–27，disagreement 11=2.3×）；greedy infogain 识别 0/5（在不可分对上死锁）——greedy 贝叶斯选择劣于随机的干净反例。POST_HOC setup 族救援探针完全退化（5 类全同 60/60），已标注不计入门。
- **产出**：`research/m0/` 下 AUDIT/BASELINE_STATUS/CHEAP_KILL_REPORT（含 verdict 表）/CHEAP_KILL_SCORECARD/EXPERIMENT_REGISTRY（17 行）/FAILURES_AND_COUNTEREXAMPLES（F1–F13）/TREE/git_info/environment + exact_lab + c0_psro + d0_diaggame + 7 图 + 全部 metrics JSON/CSV + 日志。M0_CHEAP_KILL_CHECKPOINT.zip 打包待 PI。
- **验证**：exact_lab 17/17、c0_psro 6/6 单测通过；校准 2160/2160 成功零失败；生产 pytest 1 预存失败已记录未修。**未做**：discovery/confirmatory/freeze、IBS 迁移实验、文献矩阵（B 的 PASS_TO_DISCOVERY 不构成 novelty 主张）。


## 2026-09-19 — M1 G1：IBS 自然 commitment 决策混叠门 — FAIL，按纪律停在 checkpoint（B_TOY_ONLY）

- **范围**：M1 唯一主线 Decision-Sufficient State Learning under Hidden Commitments 的 G1（IBS 自然混叠验证）。分支 `research/m1-decision-state`（基线 `7f9ed4a`）；M1 计划原文落库为 `M1_CCF-A_Decision_Sufficient_State_Learning_Plan.md`。**生产模块零改动**；禁止项全部未触碰（无 G2/OpenSpiel/神经网络/DSRL/PPO/PSRO 扩展）。
- **结构审计**：`sealed_orders` 真实一等隐藏状态（engine.py:1712 写 / :1718 读 / :966 side-filtered 视图；observe() 永不泄漏）；`MOVEMENT_PLANNING→TORPEDO_PLANNING` 是真实的"已封存未执行"窗口；`_torpedo_candidates` 只读己方封存移动、`torpedo_assist` 只用可见信息（引擎文档明示"不读敌方封存计划"）。
- **Pair 生成（全合法管线）**：预声明网格 {S-03,S-01}×seeds 1-12×turns 1-4×每节点 ≤3 近舰变体+1 远舰对照 → 273 对（200 主 + 73 对照 B），1 次生成失败。全部通过 public-obs/legal-actions/own-sealed 三重哈希相等；axis 视图哈希**不同**（干预只改隐藏状态的程序化证明）。备选承诺取自 `engine.movement_candidates`，无任何 state surgery。
- **Q 估计**：确定性脚本化续局（双方 TacticalCommander balanced），CRN dice-stream replicates。5-rep pilot：120/200 可评估但仅 8 个过任务 CI 规则（功效墙）→ 预注册的 outcome-blind 功效扩展至 15 reps（164 对，注册先于看结果）。主值=胜负结果，副值=归一化损伤差。
- **最终数字（15 reps）**：主值置信有效 20 对（S-03:12/S-01:8），**≥0.10 占 20%**（4/20，max 0.40）；副值 22 对，36%（8/22，max 0.84）；nontrivial 仅 6/11（门要求 ≥25）。对照 B：主值 22% ≥0.10 **不低于主组**（20%）；副值 10% 低于 36%。Control A 全部 273 对 bit-identical（管线确定性证明）。
- **G1_IBS_NATURALITY = FAIL**（合取门三处不过：pair 数、有效数、主值下对照分离）；**FINAL_M1_STATUS = B_TOY_ONLY**。现象真实存在且可审计（10 个强案例，board 渲染+Q 表+regret 分解），但预声明网格下的自然密度 ~1/11-20 远低于门。
- **结构性发现（给 PI）**：隐藏承诺**频繁改变价值**（65/120 对 outcome 跨分支差 ≥0.2）但**很少重排游戏自身候选集的动作**——"价值分歧 ≠ 决策混叠"的差距正是本门要测的东西，在 IBS 鱼雷窗口很大；置信与遗憾在可行预算下反相关（排名可分辨的 pair 恰是两界都有鲁棒动作的 pair）；脚本化续局 + "不发射"鲁棒候选是主要 regime-killer。若 PI 要救活：接触时刻最优续局 Q、全合法批次候选集、绑定想定胜利边际的值函数——均为 M2 规模，未执行。
- **纪律记录**：功效扩展先注册后执行（G1-POWER-002）；一个 falsy-zero 分析 bug（把 control_a_max_diff=0.0 当缺失）在读取最终数字前修复；未为过门修改任何 pair 定义/阈值；pair 密度不足时未追加网格轮次（避免 threshold-chasing）。预算：~35k/50k rollouts，0 付费 LLM，引擎 0 改动。
- **提交**：`27f23b2`（G1 全部代码+证据）；包 `research/m1/M1_G1_CHECKPOINT.zip` sha256 `7f79f8ab…`（37 文件，2.4MB→245KB）。


## 2026-09-19 — M1.5 新主线双轨 cheap-kill：E1 FAIL（不可预测）、E2 FAIL（无长期价值+因果不成立），BEST_SUPPORTED_TRACK = NONE

- **范围**：M1.5 验证两条新主线 E1（Selective Opponent Reasoning）与 E2（Strategic Influence Planning）。分支 `research/m1_5`（基线 `261482f`）；计划原文落库 `M1_5_CCF-A_New_Mainline_Cheap_Kill_Plan.md`；阈值全部**预注册**（`research/m1_5/PRE_REGISTRATION.md`）。生产模块零改动；新增 sklearn 1.9.1 到项目 .venv（可逆已记录）。
- **E1-T1（PASS）**：从 M1 G1 冻结的 15-rep Q 表重算 rho（120 可评估对，每对=一个含两个一致承诺的信息态）。CI-passing 子集：主值 83.3% 低 rho / 16.7% 高有意义 rho（floor 0.10 胜率 + norm 0.10），高 rho 的 stake 中位 **0.333**（33 个百分点胜率）；副值 90%/10%/0.045。预注册三门全过——"稀少但重大"结构成立。
- **E1-T2（FAIL，kill）**：仅用可见特征（敌距/编队展开/鱼雷就绪/损伤/比分等 13 维）预测 high-rho，5 折 CV × 3 模型族：AUROC 0.459/0.367/0.469（≤随机），预算内召回 0-31%（门 70%），**假阴性包含 76-100% 遗憾质量**。`E1_FAIL_PREDICTABILITY` 触发，E1 按计划 §15 停止（T3 的 gate 无从构建）。科学含义：criticality 藏在隐藏航路与鱼雷航道的几何关系里，公开棋盘读不出。
- **E2-T1（PASS）**：200 个可达鱼雷决策（2 场景 × 5 doctrine profiles × 40；HEAD 审计确认 9 个影响字段全部存在；legacy profile 不进反事实机器→预注册修正案换 profile）。Hybrid(λ=1) vs Direct top-1 变化 **48.5%**（非退化 55.9%），各场景 33%/30%、各 doctrine 35-62.5%；30 个强案例落盘。
- **E2-T2/T3（FAIL，kill）**：40 个变化状态 × 3 arm（direct/hybrid/shuffled）× 5 CRN reps 真实续局：hybrid vs direct **+0.02，10W/6L/24T**（S-01 恰为 0.000，S-03 +0.04，均无 ≥10% 改善）；**true ≈ shuffled**（−0.01，5W/5L/30T）且 shuffled vs direct +0.03——影响标签不携带"选个不同动作"之外的任何信号。`E2_FAIL_HEURISTIC_ONLY` + `E2_FAIL_CAUSALITY` 同时触发。
- **最终判定**：`E1_SIGNAL=PASS / E1_PREDICTABILITY=FAIL / E1_COMPUTE_VALUE=NOT_RUN(moot) / E1_NOVELTY=AMBIGUOUS(moot)`；`E2_SIGNAL=PASS / E2_LONG_HORIZON_VALUE=FAIL / E2_CAUSALITY=FAIL / E2_NOVELTY=AMBIGUOUS(moot)`；**BEST_SUPPORTED_TRACK = NONE，SECONDARY_TRACK = NONE**。按计划 §21：停止围绕 hidden commitment / torpedo 挖题，回到全系统重新选题扫描。
- **纪律记录**：修正案（profile 表、两级采样配额）全部先于结果；`Side.other()` 不存在、order 未持久化、numpy bool 序列化等 8 项失败/修复全部留档 `FAILURES_AND_COUNTEREXAMPLES.md`；"+19% 相对改善"系小分母伪影，门按原始配对差评估。预算：~760 个对局当量 / ≤15,000；0 付费 LLM。
- **提交**：`e3dc6a9`（stage-1）+ 本批（stage-2+交付）；包 `research/m1_5/M1_5_NEW_MAINLINE_CHECKPOINT.zip` sha256 `23113572945faefc…`（1.9MB，65 文件）。


## 2026-09-20 — M2-0 组织智能主线验证：A_FAIL_ORACLE / B_ORACLE_ONLY / C_MODULE → RESET_REQUIRED，Bundle 交付

- **范围**：M2-0 三条新主线（A 动态决策实体抽象 / B 失败感知指挥组织 / C 阶段自适应粒度）的第一阶段验证。分支 `research/m2-0-organizational-intelligence`（基线 `48846a9`）；计划原文落库；生产模块零改动。
- **P0（PASS）**：模式语义审计（classic=逐舰集中决策、realistic=逐编队+指挥状态机；`PlayerObservation` 无编队字段——系统本质是 side-level centralized commander，不是 MARL）；**docs 4 vs code 8 编队上限不一致只记录未修**，正式实验只用 ≤4；30/30 试跑全完成；转移→中断 1:1 链验证。
- **P1b（PASS）**：Exact Team-Abstraction Lab，双独立求解器（DP vs 显式树）1e-12 一致，4 个必需 case 全部可证构造，6/6 测试。
- **D0（PASS）**：ResearchGroupExecutor（classic 语义宏展开→真 validator）；发现并遵守"分区必须覆盖全部存活舰"的 validator 约束；no-silent-repair 用构造性反例验证。
- **Track A（A_FAIL_ORACLE）**：60 快照（2 场景×3 profile 对）× P0-P8 候选分区 × 5 CRN reps，3 次机械修正案（全在出数前）。**flat 在 71% 快照上并列最优、68% 分区评估损失恰为 0**——压缩 60-77% 真实存在但 flat 已是上限，fixed-loss 门 11.4%<20%、结构化对随机 18.4% 无优势 → oracle gap 不存在，A2 按纪律跳过，未训练任何模型。
- **Track B（B0 PASS / B1 PASS / B2 B_ORACLE_ONLY）**：B0 普查 150 局全完成——**65% 局出现指挥转移/中断**（门 5%）、226 独立案例、58 格；EM-01 达 94%。B1 paired 层级实验 12 个自然冲击案例 **25% 敏感度 ≥0.05、max 0.767**（双场景；3 个层级改变冲击时点的案例按保守方向剔除）。B2 七种组织规则：唯一非退化改进规则 low_exposure **场景反向**（EM-01 +0.252 / S-01 −0.083）；flagship_max_vp 与 default 完全相同（31/31 平）；初判 PASS 系小分母伪影，已按严格配对分析改判 **B_ORACLE_ONLY** 并留档理由。
- **Track C（C_MODULE）**：粒度由**场景而非阶段**主导（S-03 全期 K=1 / S-01 全期 K=2）；gunnery/torpedo 在 HEAD 无编组杠杆，阶段自适应主张无法跨阶段检验。
- **最终判定**：`A_VERDICT=A_FAIL_ORACLE`；`B_VERDICT=B_ORACLE_ONLY`；`C_VERDICT=C_MODULE`；**BEST_EVIDENCE_TRACK=NONE**；阶段结论 **RESET_REQUIRED**（无 MAINLINE_READY 方向；后续若重试需先换 continuation regime：对抗/搜索型对手、接触期快照、绑定胜利边际的值函数）。
- **纪律记录**：9 项 bug/失败全留档（含 `.kind/.type`、command_disrupted 非事件、succession 字段不存在、F4 全舰覆盖约束、F6 变体仅 axis、B2 小分母伪影改判）；每项阈值先于结果预注册；未跑 MAPPO/QMIX/GNN；预算在对局/续局双上限内；0 付费 LLM。
- **提交**：`0620fde`(P0)→`1702344`(P1b+D0)→`7fad588`(判定+报告)→本批；包 `research/m2_0/M2_0_ORGANIZATIONAL_INTELLIGENCE_VALIDATION_BUNDLE.zip` sha256 `d539ab28…`（47 文件）。


## 2026-09-20 — M2.1 平台杠杆审计：P0 PASS / RNG=MATCHED_INITIAL_SEEDS_ONLY / 炮击层低杠杆；movement/torpedo 未测完，按 PI 指示提前打包（PARTIAL）

- **范围**：M2.1 平台体检。分支 `research/m2-1-platform-audit`（基线 `184f605`）；计划原文落库；生产模块零改动；0 付费 LLM。
- **P0（PASS，无 blocker）**：逐条源码+探针核实（封存/观察不泄漏实测、1PP2=120° 转+1MF、S-01 鱼雷 T4 前封锁实测、S-03 qualifying=沉没或全速≤2、EM-01 erma 计分）。0 BUG/0 UNKNOWN；非法移动 fallback=接口更严（INTENTIONAL_INTERFACE_STRICTER）；编队上限 8-vs-4 记录不修。
- **P1（MATCHED_INITIAL_SEEDS_ONLY）**：引擎每次掷骰=独立 Random(seed*1e6+counter)。决定性探针：同一炮击快照 HOLD(45 draws) vs FIRE(63 draws)，第 2 个骰子事件错位——**同 seed ≠ CRN**，全阶段禁用 CRN 措辞，杠杆一律带 bootstrap CI。
- **E0 炮击层（完成，30 快照×3 场景）**：中位 λ(90-10) 0.000-0.018，**无任何状态 ≥0.05**；hold-vs-fire 差异真实（即时 U1 0.237 vs 0.20-0.23，11 检定 vs 0）但**目标分配级差异≈0**（五个 profile 的炮击批次完全相同——自动分配器即共识）。GUNNERY_LEVERAGE=LOW。
- **movement/torpedo 层（未测完）**：第一次运行 63 个 movement 快照因 dict-candidate 反序列化 bug 全失败；修复后重跑到 80/93 被 PI 指示停止，movement 层数值在进程内未落盘。**用户（游戏专家）提出关键覆盖性质疑（F8）**：候选集缺少联合战术计划（抢舷侧全火力、crossing T、鱼雷航道封锁、距离控制变速）——movement 杠杆在任何判定前必须先扩充候选并经 E2/E3（脚本续局洗平检验）重测。
- **打包**：`research/m2_1/M2_1_PLATFORM_STRATEGIC_LEVERAGE_AUDIT.zip` sha256 `4977395c…`（27 文件）。EXECUTIVE_SUMMARY 全部字段如实标注（movement/torpedo/realistic=NOT_MEASURED；E1/E2/E3=NOT_RUN；平台判定=INCOMPLETE；B=KEEP_SUSPENDED；NEXT_PI_DECISION_NEEDED 列出三条路线）。提交 `09308a7`→`014f235`。


## 2026-09-20 — M2.1-R 测量修复 + Gold Cases：GOLD_EVALUATOR_GATE = FAIL，按指令停止交 PI

- **背景**：PI 审查 M2.1 checkpoint 后判定测量 harness 有缺陷（四项），原 E0 作废（GUNNERY_LEVERAGE=INVALID_PENDING_RERUN），命令先修测量再建 5 类 Gold Cases 验证 evaluator，门 = ≥4/5 案例产生 ≥0.05 战术分离。
- **四项修复全部完成并验证**：① U1 改回冻结定义（损伤 VP/快照固定 VP 总量，sunk=1），4/4 单测过（零损伤=0/敌方全沉>0/己方全沉<0/对称=0）；② replicates 改用 sha256(snapshot|replicate) 派生 seed 重键（保留 branch-point counter），同 replicate 各 arm 同 seed，仍称 matched-seed 不称 CRN；③ gunnery 分支对手批次现在**真正 submit**（原实现只 choose_plan 未提交——正是 PI 发现的 bug，F13 确认），修复后 hold P0=0.0 vs fire P0=0.0978 可测；④ 检查点重定义 P0/T0/T1/T2/Terminal（原 H0 循环根本不执行当回合 resolution）；⑤ __baseline__ 移除，baseline=POLICY_BALANCED 走同一管线。
- **额外自找并修复两个 harness bug**：F9 gold 几何采样只 advance 一次（舰未动）；**F10 航向算术 off-by-one**（`((bearing-1)%6)+1 ≡ bearing`）导致全部战术意图坍缩为同一批次（9/9 舰计划相同）——修正后候选 9/9 分化。
- **Gold Gate 结果（GOLD_EVALUATOR_GATE = FAIL，0/5 分离）**：5 案例全部建成（reachable replay states，全部过真 validator）。T2 差距：G1 unmask +0.003、G2 cross-T +0.012、G3 range spread 0.033（最大）、G4/G5 +0.004——方向 4/5 偏战术候选但幅度全部低于 0.05 门。**E3 关键发现：G1 在对抗评估器下反号**（unmask +0.011@E0 → −0.015@E3：暴露舷侧同时暴露自己）；E3 把 E0 差距压缩 2-4 倍。G4 的鱼雷走廊价值在 movement 层不可表达（需 torpedo 层候选），已记录为案例设计缺口。
- **对 PI 的开放解读（未判定）**：(a) evaluator 家族无法为位置价值定价（位置优势需要对手多回合有意利用才兑现）→ SCRIPTED_FLATTENING 假说未被推翻；(b) intent→plan 编译器太粗（60° 六角量化 + 逐舰贪心匹配）无法表达专家战术。修复后的 harness 已足以区分两者——下一步是 PI 的决定。
- **预算与纪律**：gold 阶段约 700 次续局；所有阈值先于结果预注册；F9-F15 六项新失败/修复留档；未跑 mass census、未训练任何模型、生产引擎零改动。
- **提交**：`014f235`→`210c417`→`c8f67f7`→本批；包 `research/m2_1/M2_1R_MEASUREMENT_GOLD_CHECKPOINT.zip` sha256 `d3c77d05…`（41 文件）。


## 2026-09-21 — M2.1-R2 机制金分解：规则引擎对几何陡峭定价（3/5 PASS），失败定位到案例构建与战术假设——按门停止

- **背景**：PI 判定 M2.1-R 的端到端 Gold Gate 无法定位失败环节，命令分解为 Stage A（规则机制）/ B（编译器保真）/ C（价值兑现），本轮只做 A。状态更正：GOLD_END_TO_END_GATE=FAIL、MECHANISTIC_GOLD_GATE=NOT_TESTED、COMPILER_FIDELITY=UNRESOLVED、VALUE_REALIZATION=UNRESOLVED。
- **Stage A 结果（MECHANISTIC_GOLD_GATE = FAIL，3/5）**：
  - **MG1 BROADSIDE = PASS（+92.9%）**：hold（宽舷 3 炮位）vs 60° 转向（1 炮位）受控实验（两段式探针先学目标战后位置——同时移动使先验方位失效，F18）；公共距离期望命中 3.00 vs 1.56。关键规则事实：首 MF 必须直航（无 cost-0 转向计划）。
  - **MG2 CROSSING_T = PASS（1.68×）**：抢 T 臂 own GF 651 > enemy 486，净交换 +41.6 vs 平行臂 +24.7（≥1.25×），64 对纵向修正。反直觉记录：PARALLEL 臂总 GF 更高（736）——故事在方位角不在火力总量。
  - **MG3 RANGE_CONTROL = PASS（2.72×）**：EM-01 BB 在 d=15 vs d=17 期望命中 2.56 vs 0.94——射程修正极陡。
  - **MG4 = FAIL（CASE_CONSTRUCTION_FAIL）**：真实 TorpedoOrder 三种瞄准方案下两臂在 T+1 路由上逐 13 位小数相同——鱼雷未能约束下一回合路由。 torpedo 持久性语义需源码研究；按菜单分类为案例构建失败（非规则 bug 主张）。
  - **MG5 = FAIL（TACTICAL_ASSUMPTION_NOT_SUPPORTED）**：DISPERSE 边际反而更好（82.7 vs 56.6）——炮程 8+ hex 超过 6 hex 集群间距，局部优势在期望命中边际上无法体现。
- **科学结论（对 PI 最重要）**：**规则引擎不是问题**——航向/方位/射程在规则内有 2-3 倍级别的陡峭定价，"LOW_LEVERAGE_PLATFORM" 在规则层被杀死。此前各轮的平坦 E0 必然来自编译器（60° 量化+逐舰贪心无法把舰队摆进规则奖励的几何）或价值兑现层（脚本/对抗续局不为位置优势兑现）——Stage B/C 现在有具体的 MG 几何作为验收标准，去模糊化完成。
- **失败与修复留档**：F16（对手鱼雷批次未提交）、F17（同发射器重复订单非法）、F18（先验方位在同时移动下失效→两段式设计）、F19（D66 期望积分而非 2d6）、F20（MG3 相对差距除零伪影）。
- **提交与打包**：`c8f67f7`→`75b9f55`→本批；包 `research/m2_1/M2_1R2_MECHANISTIC_GOLD_CHECKPOINT.zip` sha256 `d2556f1b…`（49 文件）。预算：~2500 次评估；0 付费 LLM；引擎零改动；未训练模型；未跑 mass census；Stage B/C 未进入。


## 2026-09-21 — M2.1-R2.1 机制修复：F21 重复计炮 / F22 时空段错位 / F23 瞄准受限——MG4 翻转为 PASS，门仍 3/5 FAIL

- **背景**：PI 审核 M2_1R2 bundle 后指出三项测量缺陷，冻结 MG1/MG3，要求只修 MG2/MG4/MG5，门不变（≥4/5）。**禁止进入 Stage B/C**（已遵守）。
- **F21（PI 发现，已修）**：旧 `measure_side()` 对每个 (ship, target, mount) 三元组累加，同一炮位对多个可见目标**重复计数**。重写为合法分配（每炮位至多一次、每舰一个主目标），并发现另外两处保真缺陷：① 引擎的修正项用 `attackers`（集火加成）与 `target_count`（分火惩罚）而非恒为 1；② 命中表按 `(attacker, target, mount.kind)` 分组（主副炮独立查表）；③ 合法交战还要求 `_can_see`（能见度），仅 `_mount_can_bear` 会产生非法批次。所有臂批次现均通过 `validate_orders(_prepared=True)`。
- **MG2-R = FAIL（3/4 条件）**：合法计量下 CROSS 净交换 +12.44 vs PARALLEL +7.97 = **1.56×**（≥1.25 ✓）、own GF 165 > enemy 61 ✓、净 >0 ✓，但**纵向（舰首/舰尾）占比 0.44 < 0.50 ✗**。诊断（非救援）：CROSS 臂是"各舰对自身方位取横舷"，并未把本方置于敌纵列**前方**；PARALLEL 追击几何反而给出 0.89 的舷射占比。按 PI 指令如实判 FAIL——这暴露的是**占位/编译器**问题而非规则问题。
- **F22+F23（MG4，已修）**：三处缺陷叠加造成 M2.1-R2 的假阴性——① 瞄准只取自引擎的拦截式 combo API（该状态仅 2 个相同 combo）；② "安全路线"用船体伤害判定而非鱼雷接触；③ **时空段索引错位一格**（`path[allowance]` 实为回合起始格）。修复后：**持久性探针 PASS**（6/6 轨道跨回合存活、`range_remaining>0`、`distance_travelled>0`、对受害者可见——PI 的引擎解读确认）；**走廊 PASS**——288 个合法配置几何预选后实发一枚长程（range 25）合法鱼雷，覆盖受害者 **28/29 条** T+1 合法路线（接触率 0.966，唯一安全路线是"原地不动"），`RouteReduction = 0.966`（≥0.25），**时空预测与引擎 `torpedo_contact` 判定 29/29 完全一致**。
- **MG5-R = FAIL（确认）**：合法计量下 DISPERSE 仍更好（净 +19.22 vs CONCENTRATE +13.19），两臂 9 舰全开火——炮程 ≥ 舰队间距使"局部优势"在此尺度不可表达。按 PI 规则接受 `TACTICAL_ASSUMPTION_NOT_SUPPORTED`，不换场景。
- **最终门**：MG1 f`rozen PASS` / MG2 FAIL / MG3 frozen PASS / MG4 PASS / MG5 FAIL = **3/5 → MECHANISTIC_GOLD_GATE = FAIL（阈值不变）**。Stage B/C 未进入。
- **科学结论更新**：PI 的判断被证据进一步修正——不仅"炮位展开与距离控制"在规则层有强杠杆，**鱼雷海域拒止也是**（合法长程走廊剥夺 28/29 条下一回合路线，且与引擎自身接触事件逐条吻合）。Crossing-T 的失败已定位到"能否占据舷射位置"，即 Stage B 要回答的编译器问题。
- **提交与打包**：`75b9f55`→`786c925`→本批；包 `research/m2_1/M2_1R21_MECHANISTIC_REPAIR_CHECKPOINT.zip` sha256 `2874b578…`（41 文件）。预算 ~1200 次评估；0 付费 LLM；引擎零改动；阈值全部先于修复后测量预注册。


## 2026-09-21 — M2.2 战术编译器保真审计：门 FAIL，但抓到三件比门更重要的事

- **背景与纪律**：PI 指令明确"这不是把 M2.1-R2.1 的 3/5 FAIL 改成 PASS"，历史判决（MG1/MG3/MG4 = VALID PASS，MG2/MG5 = FAIL，门 3/5）**逐字保留**。禁止：为凑 4/5 重修 MG2/MG5、训练 MAPPO/QMIX/GNN/Transformer、发明论文方法、改生产规则、把研究搜索叫 optimal/oracle。全部遵守。先在 `research/m2_2/PRE_REGISTRATION_M22.md` 冻结命名纪律、机制值、保真度公式与下限、B0 门（≥2/3：SEARCH ≥0.70 且 CURRENT ≤0.40）、搜索预算（每舰 ≤8 计划 / beam 宽度 64 / 鱼雷 ≤400 配置）与 B1 门，之后才开始测量。
- **先修自己的测量工具再量**：`FIRE_SEARCH` 首版把同一炮座列表在每个 mount id 下重复累加，导致 5 炮位舰被算成 49 条目、搜索比启发式还差——**负相关就是症状**（搜索的选项集包含启发式的分配方式，不可能严格更差）。修好后 20 状态校准 Spearman(net EH) 由 −0.333 变 **+0.908**，同目标率 0.888 → `HEURISTIC_PARTIAL`，两个评估器并列报告。若沿用首版数字，整轮机制值都会是伪影。
- **B0 结果（GOLD_COMPILER_GAP = FAIL，0/3；冻结度量下仅 1/3 可计算）**：
  - **MG1 同一冻结公式在两个尺度上结论相反**：舰队级 gold −12.17 < 随机均值 −6.32（gap −5.84，按预注册"分母必须为正"不可计算）；舰对级同公式 gold +1.89 > 随机 +1.44，保真度翻为 GAP（SEARCH **+0.876**、CURRENT_POLICY **−0.178**）。展开舷射赢舰对、输舰队——把 M2.1-R 的"暴露对称"精确隔离到单舰。案例复现 **7/7 不变量精确吻合**（post_rel 1/5、距离 4/3、炮位 3/1、+92.9%）。
  - **现有意图编译器转错方向**：intent `BROADSIDE` 下 `mg_cases.intent_plans` 给焦点舰发 **`1S1P`**，与**反向臂逐字符相同**；post_rel 5、1 炮位（gold：1、3 炮位），舰对保真度 **−2.53**。表达式 `((b-1+1)%6)+1` 取错方向。任何"发意图让 AI 编译"的组织结构都会继承这个反向转向——本轮最可直接修的动作项。
  - **MG3 注册度量不可执行（M22-F4）**：冻结 PASS 的 2.56 vs 0.94 落在 15/17 格，而该状态盟军能见度 **13 格**且 radar 规则 **OFF**，两臂 `_can_see=False`（引擎会 `gunnery_rejected`；代码 l.4283-4306、l.3403）。引擎真实计量下两臂 **0.000**。注册度量只查 `_mount_can_bear`；MG3 在 R2.1 被冻结，从未拿到 MG2/MG4 的能见度修复。**历史 PASS 判决不动**，加诊断。
  - **MG4 走廊已复现且是全状态现象**：gold RouteReduction **0.966**、时空接触 **12/12** 与引擎 `torpedo_contact` 一致、预测段与 R2.1 记录逐格相同。公开信息搜索 **0.107**、当前 AI **0.000**（该状态 0 条鱼雷令；但全库 15 个 turn-2 状态中 8 个至少一方开火——声明精确化，未过度概括）。公开目标**并列主导**：argmax 并列集 RR 跨 0.00–0.97，真正最优配置公开得分最低（overlap 1 / 最大 5）→ `PUBLIC_INFORMATION_GAP = CONFIRMED`。**注意反例**：公开分与真实 RR 的 Spearman = +0.676，若只报相关系数会得出"公开信号可排序"的错误结论——并列集分解才是证据，已登记为常备反例。
- **B1 自然普查未运行**（预注册以 B0 PASS 为门；B0 非 PASS）。`NATURAL_OPPORTUNITY_RATE = NOT_MEASURED`，相关 6 项图表标注 `N/A — B1 not run`，未编造任何自然机会率。
- **失败留档**：M22-F1 混合侧秩统计伪影 / F2 搜索重复计炮 / F3 `movement_candidates` 是合法计划空间子集且 `MovementOrder.speed` 须取 `engine.movement_cost`（手算会拒合法批次）/ F4 MG3 度量缺能见度门 / F5 MG4 gold 即全状态 argmax（F=1 平凡，已声明）F6 图表曾把两个公开目标的结论混挂（已改为双面板）。全部写入 `research/m2_2/FAILURES_AND_COUNTEREXAMPLES.md`。
- **提交与打包**：包 `research/m2_2/M2_2_TACTICAL_COMPILER_FIDELITY_BUNDLE.zip` sha256 `a2ccf6d8…`（35 文件）；预算 ~450 次引擎评估；0 付费 LLM；生产引擎零改动；未训练模型；未进入价值兑现/RL/论文写作。**按指令停止，等 PI 决策**（机制值尺度 / MG3 度量 / MG4 公开信息缺口是否升为研究问题 / B1 是否重写预注册）。


## 2026-09-21 — M2.2-R / B1E：四项裁决全部执行，判定 TORPEDO_PARTIAL_OBSERVABILITY + movement MIXED

- **纪律**：历史 gate 原样保留（M2.1-R2.1 = FAIL_3_OF_5；M2.2 B0 = FAIL/BLOCKED_BY_METRIC_VALIDITY）。预注册 `PRE_REGISTRATION_B1E.md` 标注 EXPLORATORY / NOT USED TO OVERRIDE PRIOR GATES，阈值/臂/桶/判定规则全部先于测量冻结。
- **A 溯源（先于修复）**：`grep` 调用图证明 `mg_cases.intent_plans` 只被 research 脚本调用；production `_movement_order_for` 用引擎 `ship_gun_pressure` 扫描每个可达 (格,末航向)，从不把意图转成航向 → **`RESEARCH_COMPILER_BUG`**。
- **B 修复与自纠**：`mg_cases.py` 一字未改（保住 `CURRENT_INTENT_PRE_FIX` 可复现），修复 = 新模块 `REPAIRED_INTENT_BASELINE`（按本舰炮座弧表选航向）。单测 (i) 修复后 ≠ narrow arm、(iii) pre-fix 仍 == narrow arm、(iv) 合成航向扫描无首尾向，全部 PASS。**(ii) 是我自己过强的断言**（要求恢复 gold 的 3 个炮座）——实测 2（pre-fix 1）。我把它**降级为报告值并写进失败台账**，没有在看到结果后放宽判据；诊断显示修复后的期望航向在战前已取到 3 个炮座，战后只剩 2，即 F18。
- **C MG1 双尺度（复现 exact）**：pre-fixΔL0 −0.056（炮座 2→1）/ΔL1 −11.361；**修复后 +0.667 L0（41% 相对）与 −5.833 L1 → `MECHANISM_SUCCESS_BUT_NEGATIVE_EXTERNALITY`**；`RANDOM_LEGAL` 在两尺度都优于修复意图（+0.583/−1.972）——单舰意图不是战术；**只有 BEAM 双正**（+0.472/+7.417，外部性 +6.944）。
- **D MG3-E = PASS**：按 7 条冻结规则扫描**全部** MOVEMENT_PLANNING 状态（不只 turn 2），162 个状态、拒绝原因全部记录，取 EM-01 s1 t10：两臂都可见、各 8 门主炮可用，9 格 4.139 vs 12 格 2.528（相对 38.9%），净命中 2.639 vs 1.833。旧 MG3 保留 `HISTORICAL_PROXY_PASS / EXECUTABLE_GOLD_INVALID`。
- **E MG4-P**：未使用 `PUBLIC_INFORMATION_GAP`。**自查发现并修正自己的度量缺陷**：二值 per-route payoff 使 `R_shared` 在路线数大于单动作覆盖时恒为 1，测的是动作空间覆盖率而非信念冲突（三个「material」状态同时 ceiling 仅 0.071–0.316 且 R_shared 恰为 1.000 就是症状），修为 graded D 并两种并列留档（M22R-F2）。graded 下 **material 4/15 状态、跨 2 场景**（R_shared 0.500/0.667/0.333/0.333）→ `TORPEDO_PARTIAL_OBSERVABILITY`，但**效应量单场景主导**（S-01 ceiling 0.97/0.30；EM-01 0.07/0.17），且**假设 B 未被分离**：公开假设集在 R_shared 上双向移动（S-01 s1t2 公开 0.200 < 真实 0.500；S-03 s2t2 公开 0.167 > 真实 0.000）。
- **G 普查**：movement 52 状态/104 状态侧，beam 按序号奇偶单侧（n=49，不用任何臂的产出选侧）。**`damaged` 层为空、`late` 仅 16、配额缺 S-01 −4 / S-03 −4**——结构性原因（S-01 只到 turn 7、S-03 只到 turn 4；无 `mid` 桶），如实报告不回填。判定 **MOVEMENT = MIXED**：卡在冻结的「中位相对增益 ≥0.30」（实测 0.000，因中位状态机会为零），而机会率 0.375/0.235/0.125 与外部性结构相反；`LOCAL_ONLY_MECHANISM` 明确不成立。torpedo：**当前 AI 平均 RouteReduction = 0.000**（6/15 状态开火却零约束），公开臂 ≈0.010，full-state 0.020–0.316。
- **失败留档 M22R-F1..F5** + 两条常备反例。两处崩溃（Counter 键 set/tuple 不可序列化）各损失约 30 分钟算力，之后改为逐状态 JSONL 落盘，崩溃不再丢数据。
- **提交与打包**：包 `research/m2_2r/M2_2R_B1E_NATURAL_OPPORTUNITY_BUNDLE.zip` sha256 `302c9bf1…`（43 文件）。预算约 5000 次引擎评估；0 付费 LLM；生产引擎零改动；未训练模型；**未进入 RL/GNN/论文方法设计**。按指令停止。


## 2026-09-21 — M2.3 主线分歧裁决：JTC = FAIL，BARD = FAIL，MAINLINE_CANDIDATE = NONE

- **历史冻结**：M2.1-R2.1 = FAIL_3_OF_5、M2.2 B0 = FAIL/BLOCKED_BY_METRIC_VALIDITY、B1E = TORPEDO_PARTIAL_OBSERVABILITY、movement = MIXED 全部原样保留；MG3 改注为 `HISTORICAL_PROXY_PASS / EXECUTABLE_INVALID` + `SUPERSEDED_BY_MG3E_EXECUTABLE_PASS`（不改判）。另附 **M22R-F6 勘误**：B1E 的 damaged 层为空是谓词死代码（`hull_max` vs `max_hull`），不是指挥官不打损耗；旧数字不受影响（死标签不改变状态选择），已在 05/00 加 ERRATUM 块并保留原判。
- **JTC = FAIL**（无混淆不报）：多意图条款仅 I1 达标；协调条款在**同一** 35 个机会状态上 JOINT 1.048 < GREEDY 1.428 < RANDOM 1.831。**我把混淆写进判决正文**：cheap surrogate 逐舰可加 → greedy 是它的精确最优解，该臂在结构上无法检验协调（M23-F3）；真实交互项（集火/分火）不在 surrogate 内。补的三意图（Broadside / Executable Range / Raking）中 I2 在补充面板近乎不出现（0–0.167），与 MG3-E 需扫 162 个状态才找到一致。
- **BARD = FAIL**：14 个同公开历史信息集（观测哈希与合法动作集在代码里强制一致）。真实集冲突成立（11/14 crossover，5/14 无 ε-good 共享动作，R_shared 0.45–0.98），但**匹配对照把效应砍半并抹掉两个场景** → 仅 S-01 存留；公开规划器只恢复天花板的 0.611/0.226/0.086，当前 AI 全 0.000。**12/14 集 R_shared 曾恰为 0.000 是我的锚点 bug**（M23-F1）——修正后才是上面这些数字；错误锚点的运行也留档，因为它本会把结论写成 ARTIFACT。
- **MAINLINE_CANDIDATE = NONE**。按 PI 规则不强行选；两条线各自的下一步已写明（含交互项的联合 surrogate；S-01 存留信息集）。
- **补充普查（supplemental，不改写旧 prevalence）**：MID 窗口 105 行、DAMAGED 事件条件 105 行；**PI 字面 damaged 判据不具区分度**（池内 234/234 满足、217/234 连 strict 0.75·max_hull 也满足），已如实标注为条件样本、不作损伤对比主张。
- **包** `research/m2_3/M2_3_MAINLINE_DISAMBIGUATION_BUNDLE.zip` sha256 `85d3e41f…`（含 00–12 全部文档、预注册、registry/claims/failures/manifest、metrics/figures/cases/code_patch/logs）。约 3000 次引擎评估；0 付费 LLM；生产引擎零改动；**未进入 RL/GNN/Transformer/论文写作**。按指令停止。


## 2026-09-21 — M2.4 JTC 交互感知最后机会门：交互存在，协调收益不成立 → JTC 永久 kill

- **纪律**：历史 gate 与 M2.3 判定原样保留；本轮是 PI 批准的**唯一一次**重测，若 FAIL 即永久 kill。预注册先于测量冻结（φ 定义与 0.05 practical floor、24 次 engine-exact 评估等预算、六条 PASS 条件、pilot 选取规则）。
- **Gate I = PRESENT**：10 pilot / 150 舰对全部 engine-exact。median |φ|=0.000、p90 **0.556**、max **4.139**、**28%** 舰对 ≥0.05。并补了一项交互专测：用 engine-exact 的 q_i 构成的**精确可加模型**对精确联合值的一致性仅 **0.037** —— 说明「加性模型不足」是交互而非代理粗糙（原冻结判据用的是 cheap surrogate 的一致性 0.175，会把两件事混为一谈，已两种并列报告）。
- **Gate II = FAIL（六条全否）**：主集 **19** 个可评状态侧（尝试 53）**6 胜/9 平/4 负**、win rate **0.316**、中位 **+0.000**、CI [+0.000,+0.111]；逐场景 S-01 0.000 / S-03 **+0.222** / EM-01 **−4.194**；**打不过 sequential 精确坐标上升**（CI [−0.722,0.000]）；打不过等预算随机（−0.083）。**最有信息量的比较是「逐舰依次 + 精确接受」就已吃掉全部可得的协调收益**，显式建模 φ_ij 并据此搜索在该预算下不增值。
- **判定**：`INTERACTION_STRUCTURE = PRESENT`、`JTC_INTERACTION_GATE = FAIL`、`JTC_FINAL_STATUS = PERMANENTLY_KILL`、`BARD_FINAL_STATUS = ARCHIVED`、`IBS_NEXT_ROLE = APPLICATION_BENCHMARK_ONLY`。
- **kill 是有信息量的，不是预设的**：修完 bug 后首个状态 sanity check 显示 beam−greedy = **+0.972**（且出现 3.25/2.61 的交互项），S-03 中位 **+0.222** —— 符号直到整面板跑完前都是开放的；FAIL 来自平局（9/19）、EM-01 的大额亏损与打不过 sequential。
- **自身缺陷全部记录**：M24-F1 主集用了 census 全部唯一状态侧（53，超集）而非冻结 35 组合；**M24-F2 精确评估失败被 `RuntimeError` 吞掉、状态静默丢弃（53→19、~30→11）**——正是红线 R3 的形态，已在每个面板标出真实 n 并写明未来修法；M24-F3 主集意图标签退化为全 I1，故条件概率只报了可算的两项；**M24-F4 交互臂两处真 bug**（φ 的 u_j 基点错、模型只匹配首个探针）— 在 Gate I 通过后重读代码发现，修复后 Gate II 从零重跑。
- **包** `research/m2_4/M2_4_JTC_INTERACTION_LAST_GATE.zip` sha256 `5781e81a…`（35 文件，含 00–09 全部文档、预注册、registry/claims/failures/manifest、metrics/figures/cases/code_patch/logs）。0 碰撞事件、全部 gunnery 批次 `validate_orders` 通过；0 付费 LLM；生产引擎零改动；**未进入 RL/GNN/Transformer/论文写作**。按指令停止。


## 2026-09-21 — Phase A v3.0（A0 完成 + 交付 bundle，Track A/B/C 未运行）

- **新研究轴**：从 IBS 转向通用 MARL 问题（BenchMARL/VMAS）。装 BenchMARL 1.5.2 + VMAS 1.5.2 + torch 2.8.0（py3.9.6），112s；MPS 实测比 CPU 慢 2.1× → 冻结 CPU。
- **A0 全部完成**：6/6 MAPPO 训练成功（3 seeds × 2 任务 × 600k 帧，检查点齐全，中位种子规则）；500 回合干净基线；三个正对照全 PASS；`ENVIRONMENT_LOCK.json` + `PRE_REGISTRATION_PHASE_A.md` 先于测量冻结。
- **两处关键仪器发现**：(1) **预注册的原生 success 判据在本版 VMAS 失效**——终止时全 agent 已在目标半径内但 `final_rew`/`all_goal_reached` 仍为 False，照用会把能完成任务的策略报成 0% 成功；改为场景自身 `done()`。(2) **navigation 干净成功率 100% → 饱和**，按冻结规则在看 Track 前替换为 `sampling`。
- **未运行 Track A/B/C**：状态 `BLOCKED`（非 FAIL），因为没有任何 Track 数字，报 PASS/KILL 即编造。冻结设计 + 已验证仪器 + 已验证策略齐备，可立即重跑。
- **自身缺陷留档**：toy A/B/C 三处仪器缺陷（含一个同义反复的对照与一个比随机还差的结构化探针）、注册器路径 bug（6 个成功训练被写成 REJECTED）、以及我误启第二批训练（2 分钟内止损）。旧版全部保留为 `INVALID_*`。
- 包 `PHASE_A_MAINLINE_SELECTION_BUNDLE.zip` sha256 `12f0deb934967cf2…`（72 文件）。0 付费 LLM；未训练 RL/GNN/Transformer；未进入 Phase B。


## 2026-09-21 — Phase A v3.1：A0 接受（带勘误），任务对锁定，Track 未跑

- **任务对锁定**：BALANCE + SAMPLING（navigation 100% 饱和已在看 Track 前换出）；唯一后备 WIND_FLOCKING。
- **Sampling**：3/3 训练完成；验证回报 172.66 / 196.96 /（s2 进行中）；500 clean + 500 random + 四条件质量门**仍在运行**，分位数未产生 → Track B/C 语义未套用。
- **注册器硬化完成并对账通过**：261 = 259 SUCCESS + 0 REJECTED + 2 ERROR（2 个 ERROR 为我 Track A 试跑崩溃，按红线保留）。
- **Track A 运行器实现并试跑**（克隆短回滚 + 冻结随机候选 + 分离 RNG + 等预算四分配 + oracle），正式 200 状态运行未执行；**Track B/C = NOT_RUN**（≠ BLOCKED）；Track D NOT_ACTIVATED。
- 包 `PHASE_A_MAINLINE_SELECTION_BUNDLE.zip` sha256 `a57d066d6e0ad03d…`（93 文件，含 A0 分片检查点与两份新文档）。未进入 Phase B。


## 2026-09-21 — Phase A v3.1 执行完毕：A_KILL / B_KILL（含披露缺陷）/ C 部分+工程阻塞

- Sampling 质量门 PASS（d=3.43），任务对锁定 BALANCE+SAMPLING，分位数冻结。
- **Track A = A_KILL**：异质性 PASS 但 oracle−Uniform16 仅 +0.0002/+0.0022（门槛 0.08）；UNIFORM_64 反而领先 → 「重分配固定预算」无价值。
- **Track B = B_KILL**：边界非平凡 PASS，但 structure-aware 召回与 random 恰好相等（1.0/1.0）、generic 找到 0 格——因为我的 universe 仅 165 格而 K 到 200，顶端构造性饱和；已披露该缺陷并给重跑建议（2000–5000 格）。
- **Track C**：balance 侧 78.3% 唯一因果格 / 95.7% ≤3 格；200 例大跑外推 2.9h 超预算 → `C_ENGINEERING_BLOCKED` + 50 例标定交付。
- **Track D** NOT_ACTIVATED；未填 SELECTED_MAINLINE。包 `b2a947ef11aaf03c…`（112 文件）。


## 2026-09-22 — Phase A.3：B 有效重跑（首次用上称职仪器）→ B_KILL_FOR_MAINLINE；C0 生成器两任务均不可行

- **OOS 指令不匹配披露**：收到的 OOS VISIBILITY REGRESSION REPAIR 批令在本工作区无任何对应工件（D2 ledger / AaveOracle / OOS 窗口），未执行；按附件 A.3 计划执行。
- **B**：正对照 PASS（61×/46×）；正式采集在不可变标签表上完成。`B_NONTRIVIAL_BOUNDARY=FAIL`（转移线 0.24%/1.2% vs ≥20%；真实边 3/20 条）→ `B_KILL_FOR_MAINLINE`。sampling 上 structured=随机 5 倍、generic 7.6 倍（K=100）——仪器对了，但边界几乎不存在。
- **C**：C0 冻结网格 28 设定 × 100 配对全低于 10% 带（balance 最高 6.9%、sampling 0%）；均值位移诊断证明故障已应用 → `C_GENERATOR_FEASIBILITY_FAIL`（两任务）。cap 外证据表明去掉上限也不够。
- 注册器对账 **12931 = 8972 + 3957 + 2** 通过。包 `PHASE_A3_BC_DECISIVE_BUNDLE.zip` sha256 `e97f220b93f4ac68…`。未进入 Phase B；不选主线。


## 2026-09-22 — 命令延迟模式 v2.2 实施（CD-0…CD-7）：Classic/Realistic 冻结、MOVE_TOGETHER 可选、新模式与本地代理接口

- **冻结**：tag `realistic-command-v1-frozen` = `d432a975151651fa7d6746b2f92e66b1e09d8d4a`；7 行黄金回放基线（Classic/Realistic × S01/S03/EM01 + seed9）三面冻结（事件流 / 封存订单 / 终局舰船与编队）。harness 每行在**固定 `PYTHONHASHSEED` 的子进程**中运行，因此基线可复现；比较用**冻结投影**（只忽略冻结时不存在的 dict 键），把"语义漂移"与"信封增长"分开报告。
- **CD0-F1（既有缺陷，已修）**：`engine.py:3124` 遍历 `set[frozenset[str]]`，事件顺序随字符串哈希变化（`realistic_s01` 在 HS∈{0,1,2,8} 下 2 种结果）。用同函数 20 行外已有的同一规范排序键修复；修复后该行摘要 `917114fbb1dd` **与修复前逐字节相同**（0 个冻结值变化），7 行全部稳定。
- **CD0-F2（既有夹具缺陷，未修）**：`tests/test_tactical_ai.py` 两项哈希种子测试未给子进程传 `PYTHONPATH` → 比较阶段从未执行。改用 `golden_replay.py --probe-hash-seeds` 作为该契约的有效验证；列 PI 裁决项。
- **CD-1 `MOVE_TOGETHER`**：新增 `formation_maneuver.py`（IBS-R-RC-08）。七项资格条件逐条失败即拒绝；整队执行共用同一记号序列、不复制领舰格位；`geometry_kind` 为**声明状态**（否则 `FOLLOW_WAKE` 编队转向中会被误判非纵队）；`REFORM_COLUMN` 是可检验的成功/失败转换。默认仍 `FOLLOW_WAKE`，黄金回放 0 漂移。
- **CD-2 模式外壳**：`GameOptions.command_delay_mode`（新，默认关）；三入口互斥且不一致请求**fail closed**；`command_delay.py` 权限状态（仅被搭载编队 `FLEET_DIRECTED`）+ `command_observation.py` 舰队/编队视图。
- **CD-3 通信与命令**：`communications/`（媒介配置 / 路由 / 队列 / 完整性接缝）+ `delegation.py`。传播延迟**固定 0 并写明**；距离只选媒介；无任何丢包/错码概率，且带概率但无来源的策略被拒绝执行；队列确定性、优先级有序、TTL 丢弃；发出/送达/观察到三字段分离。**CD3-F1**：到达顺序 ≠ 新鲜度顺序，旧报告曾可覆盖更新认知 → 报告与订单统一按发出时间判定。**CD2-F1**：初始化事件曾含双方指挥链 → 改为每方一条带 `secret_side`。
- **CD-4 权限边界**：`target_priority.py` + `formation_agents.py`。编队代理**不能**产生炮击命令（决策类型无该字段 / 结构守卫 / 引擎拒绝原始炮击批次 / 数据层只有有界权重四道闸门）；54 条封存炮击命令对**当回合**候选集 0 条非法。**CD5-F2（我的审计缺陷）**：初版用终局棋盘判历史订单，54 条全部"非法"——已改为在各 GUNNERY 阶段当场判定。
- **CD-5 LLM 适配器**：提示词严格等于 v2.2 §12 本地清单且**不含任何规则公式**；七类越界响应被逐项拒绝；重试后回退确定性教条并保留全部尝试记录；录播策略使 LLM 对局可零成本重放。**零付费调用**。
- **CD-6 研究接口**：契约状态 + 激励账本 + 张量 + 回合导出。策略安全形态（`POLICY_SAFE: true`）与研究回放形态（`POLICY_SAFE: false` + 警告）分离；契约权重保持 0.0 直到研究者声明；`implemented_learning = False`。
- **CD-7 自审修正**（4 处）：含一处有行为影响的修正——`_optical_range` 原取双方视距较小值，改为按请求方自身视距。
- **回归**：108 项新增测试全过；`tests/test_realistic_command.py` + `test_realistic_rules_preview.py` 38 项全过；全量 637 项跑完，**失败集合与改动前基线逐字节相同**（3 项既有失败）；8 项审计全 PASS；黄金回放 0 漂移。
- 包 `COMMAND_DELAY_MODE_V2_2_IMPLEMENTATION_BUNDLE.zip` sha256 `679c0a297d6a915c…`（53 文件）。**未开始任何科研实验；未实现 RL/GNN/Transformer；未选主线。**

### 追加：交付评审（"完整打过几局 / 有泄露吗 / 子 agent 能独立执行吗 / 试过 API 吗 / 有战报吗"）

评审问题暴露了四处真实空白，全部补测、修复并固化为测试：

- **对局矩阵**：此前只跑过 2 个 (想定, seed) 组合。现 `verify_live.py` 跑 **18 局**（3 想定 × 3 seed × {命令延迟, 真实对照}），**全部 COMPLETE**，0 友军碰撞 / 0 友军鱼雷命中。
- **API 泄漏**：此前**从未**调用过 HTTP 接口。现用 FastAPI `TestClient` 打完一整局，并逐次断言 `GET /games/{id}/view == engine.observe(game_id, side)` → **58/58 完全一致**（API 不改写引擎迷雾）；`/advance`、`/events` 不返回对方私有事件；模式门控 409/404 正确。
- **CD8-F1（已修）**：中立战报的事件规则是"至少一侧可见的并集"，而命令延迟事件各自只属一方 → 战报里能读到**双方**指挥链、代理决策与激活分支。按前缀排除整个事件族（`PRIVATE_EVENT_PREFIXES`）；`formation_reformed*` 补 `secret_side`。既有 22 项战报测试全过。
- **子 agent 独立执行**：切断某编队**全部**双向通信后，该编队仍 19/19 次自主决策、每次选出合法方案、整局打完，期间为 `LOCAL_AUTONOMY`；舰队只持有其过期报告。
- **CD8-F3（已修）**：`LOCAL_AUTONOMY` 稳态下几乎不可达（只有 `BLACKOUT` 降级，而活跃编队的 `BLACKOUT` 意味着"从未收到任何报告"）；`STALE` 当时仍标 `DELEGATED`，与 agent 实际执行的失联预案矛盾。现 `STALE` 同样降级。
- **CD8-F4（已修）**：舰队总指挥**所在**编队的链路被按报告年龄算成 `STALE`（它不给自己发报告）。现恒为 `DIRECT` + `FLEET_DIRECTED`。
- **CD8-F5（我的审计缺陷，已修两轮）**：API 泄漏检查先把正常发现的接触判为泄露，又把沉没后合法留在残骸/公开事件里的舰只判为泄露；最终改为可判定问题（API 是否比 `engine.observe` 更宽）。
- 回归：114 项命令延迟测试 + 22 项战报测试全过；8/8 审计 PASS；黄金回放 0 漂移；全量 637 项失败集合与改动前**逐字节相同**。
- 包重建：`COMMAND_DELAY_MODE_V2_2_IMPLEMENTATION_BUNDLE.zip` sha256 `679c0a297d6a915c…`（61 文件）。新增裁决项 CD8-Q1（Realistic 模式下 `formation_created`/`movement_plan_resolved` 同样会被中立战报收录，属既有同类问题）。
## 2026-09-10：想定手册全量录入 + 舰级卡建档 + 剧本简报 + 虚构大决战（分支 glm/data-entry-and-briefing）

- **想定录入**：想定手册 PDF（SHA-256 与 manifest 一致）第 2–15 页逐页视觉转录，新录入 IBS-S-02、04–14 共 12 个想定（萨沃岛跨两页：PDF 第 10–11 页，盟军编制与增援骰表从第二页照录）；S-02/04/05/06/08 增援按引擎单次 1d6 模型表达（页面必达项以 1d6∈[1..6] 表达），S-13 多回合 2d6 重掷机制超出引擎表达范围，按治理只结构化“第 8 回合自动进场”并保留原文规则，S-10 盟军递进增援以原文 R20–R22 登记不建结构化块；全部 15 个想定（含 FM-01）一般模式 build_initial_state 通过。
- **真实模式**：SUPPORTED_SCENARIOS 扩到全部想定；每个新想定附 setup.engine_default_formations 历史编队提案（库拉湾输送队/塔萨法隆格田中单纵/圣乔治角 23 中队单纵/第二次瓜岛挺身攻击队/萨沃岛三川纵队/奥古斯塔皇后湾三队/瓜岛夜战李式战列等）。
- **舰级卡建档**：船表 38 张舰级通用卡（SHA-256 与 manifest 一致）经「二马船表 ↔ erma.yaml」校准符号映射后全量转录为 extensions/class-cards.yaml；解锁 34 艘目录锁定舰（比叡、雾岛、天城、赤城、尾张、高雄、爱宕、那智、长良、神通Ⅱ、白露、岚、萩风、大波、长月、望月、卯月(APD)、北卡罗来纳、列克星敦、合众国、宪法、芝加哥、休斯顿、波特兰、孟菲斯、亚特兰大、朱诺、圣胡安、克利夫兰、哥伦比亚、蒙彼利埃、丹弗、邓拉普、格里德利），记录总数 180→214；同名同型替身按（归一化舰名+舰种）去重不重复登记；0 火力高炮位与 us-21-mk14-1928（表中无此型号）分别剔除/映射为 us-21-mk11-model3-1928；绫波级（夕雾）与巴格莱/本汉姆/波特/利安德/爪哇/德·鲁伊特/哈津斯级无卡保持未建档。
- **剧本简报页**：新增 GET /scenarios/{id}/briefing（仅投影手册级公开数据：双方编制、初始布阵、援军、能见度、特殊规则、胜利条件、默认编队，不含对局秘密态）；前端新增 ScenarioBriefingModal（复刻纸质手册版式：Scenario 徽章、日红/盟蓝编制框、算子条、位置/方向/速度表、特殊规则、胜利条件、编队提案），选择想定即弹出，开战面板可重开；首页想定列表从硬编码 3 个改为动态拉取全部内置想定。tsc 0 错误、Vite 构建通过。
- **虚构大剧本**：新增 IBS-S-FM-01「铁底湾的回响·午夜舰队决战」（scripts/build_fictional_scenario.py 生成，92×78 大战场、91 舰、14 回合）：日军 8 编队（挺身夜战战队/第一游击本队/重巡战队/轻巡警戒/第一·第二雷击队/旧巡佯动/秋月殿后），盟军 8 编队（TF34 快速战列/旧战列/大巡侦察/南北重巡/轻巡纵列/DesRon23「31节伯克」/警戒驱逐队），全部使用已核验记录舰（含二马 24 舰与舰级卡解锁舰），编队注记标注历史原型。
- **测试**：test_ship_records 计数断言更新为 214；test_custom_scenarios 两处过时断言更新（全部内置想定现可玩、北卡罗来纳经舰级卡建档）；相关套件 14 passed；全量套件结果见下一条记录。
- **环境注意**：tests/test_api_llm_storage.py::test_tutorial_api_reaches_second_turn_and_serves_canonical_counter 在本机基线即失败（德国-DD-卡尔加尔斯特.png 为未拉取的 Git LFS 指针，sha256 不匹配），与本批改动无关；仓库内 resources/originals 的 PDF/PNG 多为 LFS 指针，转录均使用上级目录经 SHA-256 校验的原件。

## 2026-09-10/11：想定特例引擎强制 + 全想定 AI 自战胜率（分支 glm/data-entry-and-briefing）

- **特殊规则引擎化（special_rule_kinds 数据驱动框架）**：scenario_rules.py 扩展为通用解释器，引擎在 8 个裁决点消费想定数据——回合开火/鱼雷限制（S-01/04/05/07/09/10/12，S-01 原硬编码迁移为数据、行为不变）、鱼雷骰修正（S-04 日军 T1-3 +1）、火力系数（S-01 美军 GF 减半、S-04 美军重巡 8 吋减半向东豁免）、穿甲无效（S-09 日军 BB T1-2）、编制修改（S-09 旧金山舰尾主炮、S-11 羽黑预伤+6-5-5、S-13/S-14 盟军全员雷达）、移动约束（S-02 美军 DD 与 CL 邻接，按初始布阵校准为 ≤2 格）、能见度日程（S-10 盟军 8→10→12）、警戒状态系统（S-10：南方编队初始警戒、未警戒只能原向原速直行、4 舰每回合限提速 1MF、被炮击/被雷命中/敌舰可视/第 3 回合转警戒）、暴雨标记（S-08 四格含邻接，复用飑区判定，静态不漂移）、鱼雷消耗计分（S-10 每管 4 分计入轴心）。胜利判定新增 6 种数据驱动 kind（S-07 BC 击沉比较、S-10 分级阈值、S-11 决定性 20 分、S-12 BB 决定性条款、S-13 DD 击沉判定、S-14 两级阈值）。
- **实现边界（登记 IBS-Q-020）**：离场/返场机制（S-02 R1、S-04 R3、S-05 R3、S-10 R4/R12/R14/R22、S-11 R1、S-14 R2/R5 的离场部分）、假目标算子（S-14 R4-R6）、飞机照明弹/预写照明弹（S-10 R11、S-11 R2、S-14 R3）、秘密格逐回合 2d6 增援（S-13 R2、S-10 R20 的掷骰部分）暂无引擎机制，仍以简报文本由玩家执行；结构化增援只表达引擎可表达的确定性部分。
- **测试**：新增 tests/test_scenario_special_rules.py 18 用例（限制/修正/编制/移动/警戒/能见度/暴雨/胜利判定）；全量 pytest 通过（仅既有 LFS 指针环境用例失败）。
- **AI 自战统计**：scripts/sim_scenarios.py 双 tactical RealisticCommander（balanced）自战全部 16 想定 × 10 局（seeds 1-10，6 并行，共 160 局 0 失败），ai_stats（轴心/盟军/平局胜场、平均回合、场均击沉、说明"仅供平衡参考"）写回各想定 YAML，简报端点与简报弹窗新增「AI 自战平衡参考」栏。抽查：S-03 轴 10-0、S-13 轴1/盟1/平8、S-14 轴3/盟6/平1、EM-01 轴3/盟0/平7、FM-01 盟军 10-0（91 舰巨局盟军占优，平衡参考用）。

### 追加：PI 裁决 (b) —— 并入 data-entry 分支作为平台基线

- `git merge trial/merge-data-entry`（含 glm/data-entry-and-briefing 全部内容）：16 想定可玩、想定简报、class-cards、想定特殊规则引擎（按时期穿甲/回合开始特例/天气/额外射击判定）。
- **基线重新冻结（归因在案）**：classic_s01/classic_s03/realistic_s01/realistic_em01 四行因该分支裁决变更而漂移（单独测该分支漂移行完全相同 → 合并无自有漂移）；`GOLDEN_INDEX.json` 增 `refreeze` 字段记录授权、原因与前后摘要。重冻结后 7/7 PASS、哈希种子稳定 PASS。
- **合并暴露并修复**：S-08/S-09 默认编队建议自相交（引擎正确拒批）→ `default_setup_orders` 增加去冲突（编队顺序航向 DFS；先转后队，领舰锚点被前队穿过时转前队）。16/16 想定产出可提交初设；基线三想定不受影响（黄金回放未再冻结即 PASS）。另修 `run_audits` data_model 把"空信封"误判失败的过期前提。
- **最终状态**：全量 **683 通过 / 3 失败 / 2 跳过**，失败集合与合并前逐字节相同（3 项既有）；8/8 审计 PASS；18 局实机矩阵 PASS（9/9 命令延迟 + 9/9 真实对照全部 COMPLETE）；131 项命令延迟测试 129 过/2 跳过。
- 包更新：sha256 `7d2e3ff9…` 之后重建（见最终输出）。裁决输入存档：`research/command_delay/MERGE_DECISION_INPUT.md`。

## 2026-09-22：命令延迟模式 LLM 对 LLM 实机对战 + 战报（分支 codex/v14-budgeted-replanning）

- **需求（用户）**：「都修复好了用llm对战一把，用延迟模式，观察对局中多agent指挥协作，命令的延迟，子agent对远方命令与当前战局的平衡，一边打一边修，给我一份完整的对战战报，记录agent之间通信细节，战局态势，日志，要md格式，要有配图，测试api用我们当前zcode的子agent系统，注意不要信息泄露」。
- **对局**：想定 IBS-S-01、seed 20270830、命令延迟模式。双方每个编队各由一个 **ZCode 子代理**指挥（带本地记忆），舰队总指挥也用子代理按自然语言下达任务命令；驱动 `research/command_delay/llm_vs_llm.py` 经请求/响应文件桥接，服务循环是 `.zcode/workflow-drafts/命令延迟模式-LLM-对战.dwf.ts`。**25 次子代理调用、0 超时**，7 回合打完，平局（轴心 8 / 同盟 5 胜利点，胜利点差 <4），友军碰撞 0 次，3 艘沉没。
- **交付物**：`research/command_delay/battle/REPORT.md`（1082 行，28 张嵌入配图）由 `generate_battle_md.py` 从 `battle_data.json` 生成；同目录含 `requests/`+`responses/`（每次调用的原文与回执）、`images/<game_id>/`（92 张棋盘截图 + 92 张裁剪版）、`driver.log`、`leakage_scan.json`、`self_test.json`。
- **CD12-F1/F2a/F2b（本局边打边修，已修）**：驱动从未把各回合记录写回 `battle["turns"]`；`command_delay.formation_orders()` 未按阵营过滤，导致**每回合引擎都拒收机动批次**、静默回退确定性指挥官（代理方案全程未执行）；`gunnery_batch()` 未过滤 `local_directives`，使**一方火力优先级进入对手选择器**。修复 commit `91e2f7db`，回归用例 `test_formation_orders_and_gunnery_priorities_never_cross_sides`。污染运行留档 `research/command_delay/battle_contaminated_run1/`（12 条跨阵营 rejection 记录）。
- **泄漏核验（重写，含方法论订正）**：旧版 `scan_battle_leakage.py` 的判据是「提示词是否含未见过的敌方舰名」——**在本想定上是空转的**：双方自 T1 起就在光学距离内（轴心可见全部 9 艘美舰、同盟可见全部 5 艘日舰），该检查永不可能失败；且它扫的 `agent_log` 里根本没有 `prompt` 字段，实际扫的是空字典。已重写为**内容出处判据**（提示词里每个特征串必须对读者有合法出处；敌方文字、友邻编队决策文字、任何晚于当时的回合文字均非法，同时覆盖跨阵营泄露与"预知未来"）+ **报文台账精确检查**（`received_messages[*].message_id` 必须存在、同阵营、收件人正确，不需重放）。结果：25 条传输记录、4760 个特征串、其中 452 个有出处可溯、**0 违规 PASS**。**正对照**：把本局真实存在的敌方舰队命令原文、敌方决策理由原文、敌方台账条目分别注入一份真实轴心请求 → 三项全部被抓（`--self-test`）。
- **CD12-F3（新发现，未修，待 PI 决定）**：`MessageKind.ACKNOWLEDGEMENT` 在 `_apply_delivery` 里直接 `return`，`CommandMessage.acknowledged_turn`（`models.py`）**全仓库无任何写入点** → 台账 0 条确认记录，尽管代理 5 次决策明确确认、2 次选择发出 ACKNOWLEDGEMENT；且 `MissionOrder.confirmed_turn` 在送达时即写成送达回合，把"送达"与"确认"合并。改动会动冻结模式语义、使黄金回放基线漂移，故按纪律只登记不改。
- **CD12-F4（新发现，未修）**：代理逐次选择的 `report_actions`（SITREP/CONTACT_REPORT/ACKNOWLEDGEMENT）只落到本地记忆 `report_sent` 条目与决策记录，**不生成也不改变任何报文**；台账里 68 条接触报告全部由 `draft_reports` 在阶段边界自动起草。即下级上报目前是引擎自动参谋作业，代理还不能决定何时/向谁/报告什么。
- **代理自主性如实披露（写入战报）**：12 个「回合×阵营」机动批次中 **5 个被引擎整批驳回**并回退确定性指挥官（驳回原因：`cannot follow guide trail before advancing`、`speed 3 is outside member limits`、`cannot reverse 180 degrees`、`forced movement prevents formation following`），只有 7 个执行的是代理方案；另有 4 次首次回复因格式/非法分支名被拒后带错误原因重发并获采纳。**代理方案执行率因此为 7/12，不能按 25 次调用全额记功。**
- **命令延迟实证**：舰队总指挥（子代理）T3 拟制的两条自然语言命令经 TBS 各 +1 回合，**T4 才被编队读到**；引擎 T2 的初始委派同为 +1 回合；编队自身的接触报告走 TBS 时 +0（同回合）、被排到再加密转报队列时 +2。全 72 条报文中 55 条同回合送达、13 条跨回合、4 条停战时仍在队列。
- **验证**：8/8 审计 PASS（`run_audits.py` 退出码 0）；定向 pytest：4 个命令延迟测试文件 **71 通过 / 1 跳过**、`test_battle_report.py` **22 通过**；`REPORT.md` 28 张图链接 0 断链、锚点 0 悬空（脚本核对）。未改引擎代码（本次提交不含 `backend/`、`frontend/` 任何改动）。
- **CD12-F6（已修，测试层）**：`tests/test_tactical_ai.py` 两个跨 `PYTHONHASHSEED` 的确定性测试
  用 `subprocess.run([sys.executable, "-c", ...])` 起子进程却**未传 `PYTHONPATH`**，子进程
  `ModuleNotFoundError: No module named 'iron_bottom_sound'`，断言 `proc.returncode == 0` 失败——
  **后果不是"两个测试红了"，而是碰撞解算与 AI 订单的跨哈希种子确定性从未被检验过**（CD0-F1 那类缺陷的哨兵一直在盲跑）。
  按仓库既有惯用法补 `PYTHONPATH=backend/src` 后两测试真实执行并**通过**（22.5 s）：碰撞组跨种子同战果同事件序列；
  轴心 MOVEMENT+GUNNERY 订单序列跨种子逐字节一致。**全量重跑（修正后）：收集 687 项 → 684 通过 / 1 失败 / 2 跳过**，
  唯一失败仍是既有环境项 `test_api_llm_storage`（素材为未拉取的 Git LFS 指针，`5c54f8aa…` ≠ 硬编码 `918196c7…`）；
  改前该套件的失败集合为 {两个哈希种子项, LFS 项}，前两项即本次遮蔽项。全量日志 `research/command_delay/logs/full_pytest_cd12.log`。
- **包更新**：`COMMAND_DELAY_MODE_V2_2_IMPLEMENTATION_BUNDLE.zip` sha256 `679c0a297d6a915c…`（70 文件）；新增 `09_LIVE_BATTLE_AND_LEAKAGE_AUDIT.md`，`BUG_AND_RERUN_LOG.md` 追加 CD12-F1/F2a/F2b/F5 与未修的 F3/F4，`code_patch/research_harness.patch` 重生成（含对战驱动与战报/泄漏工具，不含 24 MB 对战数据）。

## 2026-09-23：推送 GitHub（含历史清理，已脚本化）

- **事实**：仓库 `fuxiaoji/iron-bottom-sound` 为 **public**；本地工作分支 `research/m2-2-compiler-fidelity`（HEAD `9e0ba020`）领先 `origin/codex/v14-budgeted-replanning`（`5572b73b`）**81 个提交**，含 M0/M1/M1.5/M2.0–M2.2 研究线与 CD-0…CD-12 命令延迟全部工作。
- **直接推送必被拒**：待推范围里有两个历史包袱——`.venv_phase_a/`（**616 MB / 20645 文件**，由 `acfbb4f9` 误提交；单文件 `libtorch_cpu.dylib` 就 **203.4 MB**）与 `research/m1_5/metrics/e2_t1_decisions.json`（**124 MB 与 83 MB** 两版）。GitHub 单文件硬上限 100 MB。已确证这些对象不在服务端（`origin/main` 无 `.venv_phase_a`、`acfbb4f9` 不被任何已推分支包含）。
- **处理**：在**临时克隆**里 `filter-branch` 摘除上述路径后推送；**本地仓库零修改**（不重写本地 refs、不动工作区，`.venv_phase_a` 673 MB 与那份 metrics 仍在本机）。
- **结果**：`refs/heads/research/m2-2-compiler-fidelity`（新建）与 `refs/heads/codex/v14-budgeted-replanning`（`5572b73b..eeba97c8`，纯快进）同指 `eeba97c8`；远端树含 CD-12 全部产物（`research/command_delay/battle/` 300 个文件条目、184 张图），**不含** `.venv_phase_a`。
- **代价与后续注意**：远端那 79 个提交的 SHA 与本地**不同**（本地是权威历史，含被排除的重型文件）。因此本地后续提交不能直接推；推送改走 **`scripts/push_to_github.sh`**——同一 DROP 列表 + 同一 `filter-branch` 对已发布内容确定性重建，只增量上传新提交；`--dry-run` 先报体积与超限检查（本次实测 197 MB / 2606 新对象）。
- **仅存在于本机**（未上 GitHub）：`.venv_phase_a/`、`research/m1_5/metrics/e2_t1_decisions.json`（两版）。若要上库，需装 git-lfs 或先瘦身。

## 2026-09-24：CD-13 指挥链落地 + 二马剧本 LLM 对战 + 纪录片（分支 research/m2-2-compiler-fidelity）

- **需求（用户）**：「用glm的免费模型玩一下二马剧本，用这个模式，要明确指挥链，舰队总指挥和分舰队指挥，要详细记录数据，最后拍一个视频…挑选一方的舰队总指挥的视角，拍成伪纪录片…展示有限信息，上帝视角下的信息博弈，分舰队指挥面对战局和上级命令的犹豫抉择」；追加：「总指挥是一个独立agent，他通过自然语言向其他分舰队发布命令，总指挥在的分舰队指挥接受命令不会延迟，其他的分舰队因为距离和转译可能会有延迟，分舰队指挥都要向舰队总指挥汇报战况」「之前指挥agent保留的记忆计划文件预算太少了，增加」「都需要思考，记录的时候把思维链也记录下来方便做视频」。
- **指挥链（IBS-R-CD-09，新增）**：舰队总指挥成为独立 agent（`fleet_llm.py`：自己的提示词/严格解析器/记忆/思维链），在 `on_phase_advanced` 中**先于**编队 agent 运行；给本队（总指挥所在编队）的命令**当面交办**（`handling_delay=0`、同一回合可读、台账仍记一条并注明"同编队当面交办"），给其他编队走电报（媒介/队列/延迟不变）。分舰队每回合上报：**引擎保底**态势与目击 + **agent 亲笔** `report_text`；上报按 `reporting_formation_id` 记账（信封写给舰队、知识归给上报者）。确认/偏离/澄清都是真实报文，`acknowledged_turn` 终于有写入点（落实 CD12-F3/F4）。
- **预算翻倍并修 bug**：同类条目 24→48、备忘 12→24、单条 240→400 / 400→600、渲染 4000→12000、订单文本 400→1000（memory/API/前端三处）、provider 输出 900→2000、超时 45→90。**修 `render_for_prompt` 截断方向**（原来超限时保留尾部，恰好丢掉"当前命令+备忘"，与注释和测试声称的相反；测试只因样本太小才通过）。provider 回复若被 ```json 围栏包住则先剥壳再解析，不再判为非法。
- **详细数据留档**：`calls.jsonl`（每次调用的提示词、回复、**思维链**、token 用量、延迟、传输失败）、`orders.jsonl`（引擎接受的每个指令批次）、`reports.jsonl`（每封上报的正文与延迟）、`views/`（逐阶段三视角观测 + 全状态快照）、`battle_data.json`（分层策略标签）。
- **对局**：`IBS-S-EM-01`（二马剧本）seed 19440619，`glm-4.5-flash` + 思维链开启、预算 4000。12 回合打完：**平局（损伤分差 7；轴心 13 : 同盟 20）**，0 友军碰撞。**92 次模型决策**（编队 70 + 舰队 22），827k tokens（提示 725k / 生成 102k），思维链均值约 2.1k 字；43 次传输失败全部重试成功；**3 次代理方案被引擎驳回改由教条执行**（如实入档）。台账：141 封报文、40 封上报（其中 15 封跨回合送达）、任务命令 21 次当面交办 / 42 次经电报。
- **核验（两项都做成了可失败的检查）**：
  - **重演一致性**：`replay_battle.py --verify` 从记录重演（orders.jsonl + 记录的模型回复）→ **80 个阶段快照、0 不一致**。**第一版检查失败**：只用 orders.jsonl 重演时 T5 鱼雷结算出现 3 处舰体差异（位置/航向/航速全同，只有损伤不同）——查明是**模型撰写的报文流量（命令/上报/优先级指令）本身参与战斗**，只重演指令批次会打出另一场仗；补上"重新提供模型回复"（`recorded_policies.py`）后逐阶段一致。这正是 `RecordedPolicy` 存在的理由，此前从未被这样检验过。
  - **泄漏核验**：`scan_provider_battle.py` 扫 92 条提示词 → 0 违规 PASS，判据明确为「任何一方都不会被告知该方从未目视过的敌舰」；**正对照**注入一艘轴心从未见过的美舰 id → 被抓。中途三次判据修正（把友军当成敌方、忽略后期沉没的舰、报告正文按快照而非散文扫描），全部记在脚本注释里——**判据本身出错是本项目反复出现的失败模式**（CD8-F5/CD12-F5/F7）。
- **纪录片**：`research/battle_video/out/documentary.mp4`（**12.0 分钟 1080p30**，另出 720p 32MB），QC 门 PASS（时长/分辨率/响度/无空帧/44 条字幕）。全部内容由记录生成：`replay_battle.py` 出三视角静帧（上帝/日方/美方，`render_map_image(viewpoint=…)` 新增，并修掉"viewpoint 与 side 不一致导致两侧图相同"的缺陷）；`build_timeline.py` 由记录推导解说词与屏显（**节奏按事件而非回合数**：安静回合合并成蒙太奇）；`tts_speak.py` 用 ChatTTS 固定男声（离线、无需参考音频）配音 44 段；Remotion 负责章节卡/三视图并置/下三分之一/思维链面板/字幕/混音。测试渲染与成片均通过 QC。
- **验证**：8/8 审计 PASS；新增黄金行 `cd_s01` 冻结命令链（既有 7 行逐字节未变，因它们都以 `command_delay_mode:false` 运行）；`--probe-hash-seeds 0,1,2,8` 全部稳定；新增 `tests/test_command_delay_chain_of_command.py` 7 项（舰队 agent、当面交办同回合可读、上报带亲笔正文且延迟、确认入台账、记忆预算保头）；命令延迟测试 71 通过 / 1 跳过。

## 2026-09-24：CD v2.3 修复批次（IR-0…IR-9）— 指挥链完整性、历史路由与回归修复

- **来源**：用户递交 `COMMAND_DELAY_V2_3_HANDOFF.zip`（PI 裁决 + 修复计划），要求按计划执行到最终裁决块。
- **IR-0 冻结**：旧对局证据按副本归档（原件不动），`v2_3/baseline_manifest.json` 记录提交、证据哈希、
  三个冻结面的 sha256 与 7 行黄金摘要；冻结时重跑重演核验 PASS（80 阶段 / 0 不一致）。
- **IR-1 路由审计（最重要的发现）**：141 封报文逐条重算 —— **棋盘最大合法距离 83 hex**（vs TBS 标称 73），
  但本局实际 0–42 hex（均值 15）、137/141 在射程内。**全部 55 封 `转报再加密 +2` 都在美方**，
  理由是 "the ends are under different ciphers"——而模式内**没有密码域概念**。根因两个：
  `route()` 把**光学能见度**（实测 13/15 hex）当 TBS 射程；`relay_available = not same_command` 让跨编队=跨密码体系。
  标记：55 无据再加密 / 55 无据中继 / 51 射程内未用直连 / 49 距离延迟缺陷。
  轴心/同盟的不对称是**位置性的**（`side` 从不参与选路）。
- **IR-2 路由修复**：顺序化（当面→TBS→视觉→编码→显式中继→无通路）；TBS 射程成为配置值 73 hex；
  中继/再加密必须带节点与理由；**删除"长命令 +1"**，改为按长度占 1–3 个信道槽、占不到就排队；
  报文新增 `DelayBreakdown`（7 分量）+ `RouteProvenance`；信道按阵营分开。
  **同几何重算：转报 55→0、支付基础延迟的报文 79→0、74 条改换媒介**。测试 A–F 7 项。
- **IR-3 因果边界**：删除"编队可见兄弟报告位"的窗口（舰队副本直接下发），改为带出处的知识账本
  （`KnowledgeItem`：本地观测 / 投递报文 + message_id）；4 项泄漏测试；审计判据改为按**曾目视集合**收紧。
- **IR-4 持久命令**：`order_event`（NEW/AMEND/CANCEL/ACTIVATE_PREBRIEFED_BRANCH/NO_NEW_ORDER）+ 修订线；
  重述不产生修订；迟到旧令按修订号被拒；撤销清空现行命令；六回合情形测试。
- **IR-5 事件驱动上报**：删除"每回合一份"的默认条令；触发式（旗舰损失/重创/新接触/任务到期/命令要求定期）；
  `RadioPolicy` 四档在**起草前**判定（被拦下的报文不会产生，因此不可能"边说静默边发报"）；
  拦截记 `report_suppressed`。**黄金行报文 77→6，决策数 19 不变**；连带的炮击结果 102→101、沉没 6→5
  已按"火力优先级由已投递报文构成"归因，并记入 `refreeze`。
- **IR-6 单位与断言**：引擎提供 `range_hex/range_yards/range_nmi`；`claims.py` 给出
  CONFIRMED/REPORTED/INFERRED/SUSPECTED 分级与 `unsupported_confirmed()`；回归测试覆盖
  "12 格写成 12 海里"与"无据确认击沉"。
- **IR-7 炮击权限**：五项单元级证明（决策无炮击字段、原始炮击令被拒、权重只改偏好、权重界限、
  不可见目标指令无效）；8/8 审计 PASS。
- **IR-8 机动与解耦**：补强制移动、Realistic 对等、边界不变量；解耦审计量出
  `realistic_command.py` 相对冻结 tag **+154/−1、仅两处模式门控**，13 个 CD 模块独立。
  **IR8-F1（登记待裁）**：计划要求"棋盘边界拒绝"，引擎实际是**结算时截断**（`neighbor()` 抛异常→按障碍）；
  改成拒绝会动真实模式语义，故只登记。
- **IR-9 端到端**：脚本化确定性对局（账本自洽 + 可复现）PASS；实机 LLM 对局（EM-01/seed 19440619，
  glm-4.5-flash+思维链）12 回合打完、**76 次决策、0 传输失败、8 次引擎驳回**、68 封报文 / 6 封上报。
  断言：因果泄漏 PASS（76 提示词 + 注入对照）、无据 CONFIRMED 0、下级炮击令 0、重演 PASS、
  7 行冻结 PASS；**单位违规 5 处（FAIL）** 与 **命令谱系 1 处（FAIL）**——后者查出并修复了
  "当面交办先折入后盖送达回合 → 命令永不确认 → 去重与修订线失效"的真实缺陷（含回归测试），
  修正在本局**之后**落地，故本局判定保持 FAIL、不宣称通过。
- **交付**：`COMMAND_DELAY_V2_3_INTEGRITY_REPAIR_BUNDLE.zip`（57 文件，sha256 `1de47f30d00db8bd…`，
  含 15 份具名文档 + raw/logs/tests/code_patch）；全量测试 722 通过 / 1 失败（既有 LFS 指针环境项）/ 2 跳过。
- **最终裁决**：`COMMAND_DELAY_V2_3_COMPLETE = NO`、`RESEARCH_READY = NO`（因上述两项 FAIL，修法已就位，
  需再跑一次对局验证）。

## 2026-09-24：命令延迟模式交互层（v2.4 界面批次）——「我完全不会玩」的四个真实原因

- **需求（用户）**：「可以优化一下这个模式的人机交互体验吗，我感觉目前这个前端我完全不会玩」。
  先看现场（浏览器实测 + 接口探针），再改；改完在同一个对局上验证。
- **诊断出四个原因（都不是文案问题）**：
  1. **前端读的字段后端已经删了**：v2.3 把 `stale_external_reports` 换成 `knowledge`，而
     `CommandDelayPanel.tsx` 仍在读旧字段 → 选中编队即抛异常、指挥链面板整块空白**且不报错**。
  2. **顶栏「校验、封存并交接」在命令延迟模式下提交的是状态机 AI 自动填的那一份 OrderBatch**，
     不是各编队代理选定的方案：玩家先点「按编队代理方案提交订单」再点顶栏，订单会被**静默覆盖**。
     这与该模式的设计（玩家是指挥官，不逐舰填表）正相反。
  3. **运行中的 API 服务是旧代码**（进程启动于 09-23 00:45，v2.3 提交于 09-24 15:09）：界面按 v2.3
     语义显示、后端按 v2.2 语义发报。**该对局的两封电报因此一直停在「待发」**（用户自己发的）。
  4. **玩家看不到自己按下去会发生什么**：没有本回合操作顺序、没有投递预判、两个按钮无说明；
     编队代理的决策与记忆只在「调试」里以 `link=direct, authority=…` 原始串呈现；
     「AI 未配置」只体现在调试日志里的一句 `no API key for deepseek`。
- **改动（后端，全部为增量）**：
  - `preview_order_delivery()`（`command_delay.py`）+ `POST /command-delay/order/preview`：
    用引擎自己的 `route()` 与 `breakdown_for()` 预先回答"这道命令现在发出去会怎样"——
    媒介、逐分量延迟、距离 hex/nmi、TBS 射程、时隙成本（>240 字＝2 槽）、现行命令与
    **重述警告**（`NO_NEW_ORDER`）。**只读**：不排报文、不占序号、不建命令、不写状态；
    连"指挥链尚未建立"这种边界也不调用 `state_for()` 去创建模式状态（有专门测试）。
  - `GET/POST /command-delay/agent-policy`：查看/接入/撤销模型。**已在进行的对局也能接**，
    因为策略注册表是进程内存、服务一重启就丢——这正是"看起来在玩 AI，其实在打教条"的机制来源。
    `fleet: true` 时同时注册**舰队代理**（`set_fleet_policy`，此前 web 端从未调用过）。
    密钥只进内存：测试断言存档 `state_json` 里搜不到它。
  - `storage.game_summaries()` 增加 `command_delay_mode`（首页此前认不出这类对局）。
- **改动（前端，重写两个面板）**：本回合四步流程条（写命令→发电报→看代理方案→校验交接）；
  编队卡片（精确/报告年龄、链路、权限、兵力、位置、现行命令、点卡片即换收件人）；
  投递预判卡（当面交办/TBS 直连/+N 回合/未到场，全部由引擎预判驱动）；命令正文＝权威内容，
  附任务模板、约束/期限/火力优先级逐项辅助（只拼进正文，不开暗通道）、字数计数；
  代理方案与决策说人话（引擎枚举分支译成中文，审计串不再冒充"理由"）；
  「模型」卡把"教条 vs 模型"摆在面板上并可直接接入；打法说明按钮直通规则文档（对局中此前打不开）。
  App 侧：命令延迟模式下顶栏按钮＝**取各编队代理的方案**（手改过高级 JSON 才以玩家为准），
  文案与面板按钮统一；原始 JSON 计划表收进「高级」；`command_delay_mode` 列表标记。
- **文档**：`docs/rules/command-delay.md` 新增「五之三、界面怎么用（一个回合的操作顺序）」
  ——即线上「打法说明」弹窗的正文。
- **测试**：新增 `tests/test_command_delay_ui_support_v24.py` 8 项全过（预判只读 ×2、时隙计价、
  重述警告、密钥接入/撤销/不落盘、对方读不到、列表标记、未到场分类）。
  命令延迟 + API 全套：**仅 1 项失败 = 既有 LFS 指针环境项**
  （`test_api_llm_storage.py` 的 `德国-DD-卡尔加尔斯特.png` 断言的是 LFS oid，本机未装 git-lfs，
  与本次改动无关；`git status` 不含任何资源文件）。
- **现场验证（同一对局 `aecaa4f7`，IBS-S-01 T2 移动计划）**：重启 API 至 v2.3；页面实测
  模板填充（48/1000 字）、逐项辅助拼正文、点卡片切换收件人、投递预判随收件人与正文实时变化
  （"TBS 直连：本回合可投递 距离 4 格≈1.18 海里"↔"当面交办：立即生效"）；该对局 `updated_at`
  始终是 09-22 11:49，**验证过程没有改动玩家的存档**。
