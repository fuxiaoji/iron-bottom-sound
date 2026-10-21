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

## 2026-10-11：最新真实模式协同状态机 AI（未提交，基线 b508bd9）

- **新风格**：`rc_coordinated` 协同舰队、`rc_t_hunter` T 头猎手、`rc_torpedo_wings` 雷击双翼、`rc_screen` 护航屏卫、`rc_pincer` 分进合击；首页、剧本工坊与教练风格标签共用前端配置。真实模式默认推荐协同舰队，切回经典则恢复经典 AI。旧对局不会自动更换对手。
- **状态机与编队配合**：新增 `formation_tactics.py`，根据当前本方观察与舰况分配炮战纵队、雷击翼队、掩护支队及共同目标/侧翼阵位/主力协同关系；搜索、接敌、T 头、雷击、避雷、掩护、指挥中断、撤退由公开状态重新推导，不依赖额外隐藏记忆。所有机动先交给现有引擎展开领舰与跟从舰，再逐脉冲预约友军格位、交换格位和停船终点，联合优化编队并检查下一回合首脉冲，防止主动停车堵住友舰舰首。
- **鱼雷与规则边界**：沿现有 `torpedo_tactical_combos` 与战术雷击规划器选合法发射时机、方向、雷种档位及分批齐射数量，避开已封存己方航路；移动规避同时包含本方及可见敌方现存鱼雷的速度周期、射程、逐脉冲中途接触与静止雷位。修正雷击预测写死 34×27 的地图边界，改读当前想定尺寸。未修改炮击、碰撞、鱼雷命中或损伤裁决；受损脱队与指挥中断仍由既有真实模式机制约束，剩余风险写入计划而非伪造无风险。
- **安全与性能修复**：撤退方向/路线只参考本方可见敌舰及公开炮位，不再借隐藏位置或隐藏损伤评分。候选编队路线复用受损舰的权威撤退订单，避免每个候选重复跑撤退路径搜索；新增缓存次数回归与整编队强制脱离测试。S-08/S-09 的历史默认初设重叠通过合法可编辑订单调整己方领舰/航向/间距，保留编制与旗舰，不改来源坐标或绕过初设验证。
- **自动测试**：`tests/test_cooperative_formations.py` 最终 **44 passed**，覆盖 16 想定合法初设、两翼配合、实际 T 头改善、交叉纵队避让、静止尾舰/交换格、己方与敌方鱼雷中途规避、隐藏鱼雷/封存订单/隐藏敌舰位置不干预决策、五风格实际安全发雷、指挥中断、撤退缓存、全队脱离，以及五风格玩家 API 完整首回合和完整对局回放。相关回归本次 163 项通过；全量回归在新增补充用例前采集 **511 项全部通过**，后续补充/扩展用例由最终 44 项专项覆盖（当前总采集 529）。仅既有 Starlette 弃用警告。`tsc -b`、Vite 生产构建、Python 编译与 `git diff --check` 通过；构建使用 `--configLoader runner` 避开沙箱中配置打包工具读取项目上级目录的权限限制。
- **离线实战证据**：新增 `scripts/evaluate_realistic_ai.py`，只用独立引擎、不触碰玩家 SQLite。`population-final-20261011.json` 为五风格 × 双方的通道行动 10 局；`erma-lookahead-20261011.json` 为协同舰队/雷击双翼 × 双方的二马 4 局。合计 **14/14 完整结束、0 驳回/异常、全部回放相等、175 次实际鱼雷齐射、0 友舰碰撞伤害、0 误雷友舰**；仍有 14 艘次紧急停车，报告保留受损自主撤退、指挥中断等剩余风险。这是行为验收，不能当作官方胜率或绝对不遇险保证。
- **全想定适配**：`scenario-acceptance-20261011.json` 为 IBS-S-01–14、EM-01、FM-01 × 双方，共 **32/32 前两回合冒烟通过**，全部回放相等，友舰碰撞伤害/误雷友舰 0；91 舰 92×78 想定同样通过，只是冒烟，不声称完整巨局已经验收。
- **界面与交付**：独立本地生产预览实测首页的五种新选项、推荐项、各风格简介及真实→经典→真实回切；`artifacts/realistic-ai/ai-selector.jpg` 为实际界面截图。README 补充启动选择、行为边界与离线验收命令。临时预览关闭；未部署、未重启/替换玩家已有 5173/8000 服务、未更改已有存档或其他工作目录内容。加载新代码需要用户重启本项目服务。

## 2026-10-11：多编队 AI 强度联赛与改进（未提交，基线 b508bd9）

- **协议与公平性**：新增 `scripts/benchmark_realistic_strength.py`，调参部署/种子与验证集分离，完整跑到引擎胜负裁决；每个想定/种子双方换边，天然强势阵营双方各赢一局计中性。预设通用至少 30 对、实际自定义两剧本至少 20 对，胜 1 平 0.5 得分率 ≥60%、单侧精确配对符号 p<0.05、无无效局、回放一致。每组先冻结定义、参数、代码 SHA-256，工作进程核对版本；不将失败、未完成、旧版本或重复的探索局算进正式胜率。
- **战术改进**：按局部战区选择敌舰和最近主力搭档，整条纵队评估实际射界、公开直航假设及己方航速下的受击风险；未公布部署区时按地图几何搜索，炮击采用引擎既有舰队目标分配。共同的鱼雷反事实、投影、公开火力热区与自主撤退计算优化均有新旧结果等价测试，旧风格参数和独立选靶策略保留。
- **共同正确性修复**：沉没旧领舰不再污染重建尾迹；同脉冲重叠避碰组稳定排序，已停舰不能使另一冲突组的友舰漏停；大舰队的脱队/降速修复单调推进，不能反复重新挂接已识别故障舰。局部候选保留完整成员和原脱队决策，只缓存权威自主撤退订单，新增局部/完整展开等价检查。修复对新旧双方一致生效，未改原版表格值；IBS-R-RC-02/03 审计补充边界测试。
- **通用主要验证**：`strength-v5-holdout.json` 为 6 部署 ×5 种子 ×换边 60 局，协同舰队对旧 adaptive **50 胜 10 负，83.33%，20 正/0 负/10 中性对，p=9.536743e-7**；全部合法结束、回放一致。每个部署分别 9/8/9/7/8/9 个胜场；按种子聚合五组均正向，保守 p=0.03125。发雷 1,810 次，友舰碰撞伤害与误雷友舰均 0，135 舰次紧急停车。
- **实际大舰队验收**：仅只读本机 `backend/iron-bottom-sound.sqlite3` 中两份原始定义，未重新平衡舰船属性：`IBS-CUSTOM-21E8908FE969` 111 舰/16 编队/30 回合，`IBS-CUSTOM-BIG-GRAND` 111 舰/14 编队/92×78/30 回合。种子 211/223/227/229/233/239/241/251/257/263 ×换边，共 **40/40 完整合法结束、回放一致，32 胜 8 负，80%，13 正/1 负/6 中性对，p=0.000915527，预设验收通过**。两剧本各 16 胜 4 负，分层名义 p=0.015625/0.03515625；种子聚合 8 正/0 负/2 中性，p=0.00390625。实际发雷 2,970 次，友舰碰撞伤害/误雷友舰均 0；8,611 舰次紧急停车仍保留，不宣称完全无停航风险。完整证据 `artifacts/realistic-ai/strength-v5-grand.json`。
- **其他旧对照及边界**：balanced、brawl 各 6 部署 ×5 种子 ×换边 60 局，分别 **42 胜 18 负，70%，p=0.000915527**；**38 胜 21 负 1 平，得分率 64.17%，p=0.024520874**，全局合法/回放一致。二者属于次要比较，p 未多重校正。其他四个新风格各 12 局合法/回放一致，但不足以证明显著更强（猎手 9/3、双翼 7/5、屏卫 9/3、合击 7/5）。16 内置想定尝试 32 局，31 完赛；S-02 同盟种子 19 的自主撤退与 DD–CL 邻接校验仍冲突，整个换边对无效，兼容验收不通过；剔除后 19 胜 6 负 5 平，不冒充全部历史场景通过。>25 格穿甲缺失登记 IBS-Q-021，未猜测或补齐裁决值。
- **测试与交付**：冻结 AI 版本全量 **564 passed**；TypeScript/Vite 生产构建、Python 编译、`git diff --check` 通过，四个正式报告共 220 局的代码哈希均与当前核心源码一致。未重启现有玩家服务；新对局推荐「协同舰队」，旧风格不能套用其胜率。改进中旧版报告保留但不汇入最终统计。
- **测试存储副作用与补救**：收尾核查发现仓库原有 pytest API 全局 repository 使用默认玩家数据库，接口测试会新增测试对局；此前「玩家库不改动」仅对离线联赛成立，不能涵盖原测试套件。已将 API 测试 repository 隔离至每项临时目录，新增真实端点落库位置回归 **1/1 通过**；此后玩家库修改时间仍为 15:26:12，未擅自批量删除旧库条目。隔离后的全量回归结果另补；既有玩家记录与来源资料不做清理。
- **收尾复核**：隔离后全量 **565 passed，1 个既有 Starlette 弃用警告，537.35 秒**；四个正式报告的 220 局仍全部合法/回放一致且源码哈希匹配。SQLite 主文件修改时间会因 WAL 检查点变化，不能作为唯一的写入证据；隔离后直接只读查询实际 games.updated_at，最新为 `2026-10-11 07:35:27 UTC`（早于隔离后的回归），没有本次隔离回归新增的玩家库对局。所有本轮联赛和 pytest 进程已结束；未停止现有玩家服务或其他项目进程，未删除玩家记录，`git diff --check` 通过。

## 2026-10-11：固定弱势方的旧失衡想定复核（未提交，基线 b508bd9）

- **协议**：新脚本 `benchmark_weak_side.py` 预先固定 12 想定及弱方；强方一直 balanced，弱方 balanced / rc_coordinated 按相同初始种子成对比较。每剧本 30 全新种子，各剧本种子块互不重叠，共 360 对/720 次尝试；不换边、不调参、不改装备/规则/胜利条件。旧 10 局记录仅用于选弱方，不作为新基线或结构性失衡的证据；S-03 的旧一边倒印象明确复核，而不是照搬。
- **统计与有效性**：主指标弱方引擎裁决胜率，平局不算胜；单侧精确配对二项/McNemar 检验，12 项 Holm 校正；至少 30 有效对、无异常、胜率增加、校正 p<0.05 才称显著。720 记录唯一，无重复；684 局合法终局且确定性回放一致；36 个异常使 27 对整体无效，333 对进入分剧本计数。失败不算输赢，不用补种子掩盖异常。
- **显著改善**：奥古斯塔皇后湾 S-11 固定轴心 **2/30→13/30（6.7%→43.3%）**，11 正/0 负，Holm p=0.005371；霍腊纽 S-14 固定轴心 **5/30→19/30（16.7%→63.3%）**，15 正/1 负，Holm p=0.003113；91 舰午夜舰队决战 FM-01 固定轴心 **3/30→16/30（10%→53.3%）**，14 正/1 负，Holm p=0.005371。三项各 60 次对局全部合法、回放一致，更保守的 12 倍 Bonferroni 也均 p<0.006。
- **不能泛化的结果**：S-01 0→0 胜但平局 8→15；S-03 9→19 胜但 Holm p=0.051758；S-04 11→15，S-05 3→5，S-06 9→17，S-12 13→17，EM-01 1→8，均未达到多重校正门槛。S-05 的 16 个旧平局变为新 0 平，得分率 36.7%→16.7%，不能只突出多赢两局。
- **兼容缺陷**：S-02 的 DD–CL 邻接旧/新分别异常 8/9 局，剩 18 有效对（弱方 2→8 胜）；S-10 的提速约束旧/新分别异常 7/12 局，剩 15 对（3→14 胜）。两者不标记通过，剩余样本可能有选择偏差；未删除想定特例或绕过校验。本轮全部合法终局的弱方新/旧分别实际雷击齐射 6,579/333 次，友舰碰撞伤害和误雷友舰均 0；仍有新 1,726 / 旧 3,784 舰次紧急停车，不宣称所有航路风险消失。
- **证据与恢复**：`weak-side-frozen-720.json`、逐局 `.jsonl`、`pre-resume.json` 保留完整定义、旧参考、参数、71 个输入哈希、失败栈及行为。进程中断时 journal 已有 717 条结果（JSON 尚为 708）；全部恢复且不重跑，只按原登记补跑 FM-01 2128/2129/2130 三个 new 样本。`resume_weak_side.py` 校验原输入哈希、拒绝重复样本并记录恢复审计；最终全部 71 哈希及此前 v5 五个核心文件一致，未改 AI 或裁决。统计/恢复回归 **34 passed**，1 个既有弃用警告，测试数据库显式隔离。

## 2026-10-11：本地服务同步与状态机类型入口（未提交）

- **现场与同步**：用户另行授权同步本地前端/服务器。检查时 5173/8000 均没有监听；使用项目启动器加载最新工作区，前端 PID 45120、后端 PID 14688，首页与场景 API HTTP 200。没有停止无关进程或删除/覆盖玩家存档。
- **原因与交互修复**：原 AI 下拉位于完整战场列表后第三步（1440×960 实测约 y=1803），只有状态机模式显示；真实新风格还被经典模式隐藏。新增共用 `AIProfilePicker`，移至首页“选择对手”面板，点击状态机后聚焦显示；新旧分组始终可见，选择新 AI 自动切真实。`useAIProfile` 记住真实/经典各自风格，同机双人往返保留选择；工坊共用组件，资格不足时禁用新类型并说明编队门槛，视觉模式也跟随实际资格。不擅自替换旧对局的对手。
- **功能与视觉验收**：五个新类型逐个可选；真实/经典及同机双人往返保持预期；通道行动实际创建、协同舰队 AI 初设提交返回 200，刷新仍显示协同舰队并进入增援阶段。工坊载入模板后雷击双翼可选，模式往返恢复；单舰/阵营导入边界提示正确，新 option 原生 disabled=true、键盘 Home/上键跳过新类型，旧 balanced 仍可选。桌面 1440×960、手机 390×844 均无横向溢出，入口/说明未遮挡；工坊和资格边界截图也已回看。证据 `ai-picker-synced-desktop/mobile/workshop/locked.jpg`。
- **存储与收尾**：交互验收通过 8011 临时后端和 `sync-ui-qa.sqlite3`，真实玩家服务只做读取。测试 game_id `a9c83393-802d-4b2c-8570-7c0c442f0d10` 在隔离库存在、正式玩家库不存在；未把本轮测试对局写进玩家库。独立浏览器与临时 8011 服务关闭，正式 5173/8000 保持运行；TypeScript、Vite 构建、Python 编译及 `git diff --check` 通过。前端设计技能用于沿用现有海军色和定位层级，Playwright 交互技能覆盖实际选择、模式循环、资格边界和布局；未改规则或后台 AI 数值。
- **输出归档补记**：临时 API 默认战报仍生成在 `backend/reports/<上述测试 ID>`，收尾已核对该精确 UUID 的所有权并移动至 `artifacts/realistic-ai/qa-reports-20261011/`；没有移动任何玩家战报。本轮三个显式 pytest 临时目录也移到 `qa-cache-20261011/`，均可恢复，不删除记录。720 条 journal 与报告逐局完全一致，71 输入哈希最终仍一致，最新选择器已从正式 5173 实际提供。

## 2026-10-11：想定 AI 适配继续、源证增援修复与独立验证（未提交）

- **来源核验**：使用铁底湾规则核验技能及 PDF 只读渲染，回看想定手册 PDF 2/5/10（印刷3/6/11），SHA-256 与 manifest 一致。S-10直航/提速规则保持原值；S-05原文第二回合三舰必达，原“全成功骰”在封存入场命令后才判断导致漏入场。新增数据条目 IBS-S-05-R4 guaranteed_reinforcement，在入场计划前发布可用事件并经正常命令入场，无模拟骰；经典及真实模式、新旧AI均使用同一修复。未改船表、胜利条件或隐藏信息边界。
- **规划接口**：引擎 movement_speed_range 为候选、路径、预览、观察、共同航速、编队展开/修复及撤退提供想定边界；未警戒搜索禁止转向，终点候选和预览复用原校验。空可行域不绕过；最终修复识别舰ID前缀特例错误，先尝试合法纵队航迹，再单调脱队。协同规划允许合法替代路线作为起点，最终完整批次仍验证；整队无法炮击时机动掩护，不用不可执行的炮击火力鼓励逼近。
- **剩余规则边界**：IBS-Q-022登记库拉湾“始终相邻”与现行终点/回合初锚点、距离校准和受损撤退之间的差异，连续邻接未完整实现；IBS-Q-023登记同回合概率增援时序，S-05确定性到达修复不冒充其已实现。新增无合法撤退阻断回归，不把失败计作战败。旧36个失败作开发复测：31合法终局/回放一致，其中S-10 19/19、S-02 12/17；其余5局明确保留。
- **开发/验证分离**：S-05开发种子2401–2406，禁炮掩护及入场修复的三个版本分文件保留，不能计正式强度。新固定弱方三个想定各30对（3001–3030 /3101–3130 /3201–3230），强方balanced，预登记后冻结72输入；180次尝试、168合法结束/回放一致、80有效对，12局S-02异常排除10整对。S-10同盟旧12胜18负→新26胜4负，40%→86.7%，14正向0负向，三项Holm p=0.000183通过。S-05轴心旧5胜7负18平→新4胜12负14平，得分率46.7%→36.7%，未改善；S-02只有20有效对，未验收。证据 constraint-holdout-180.json/.jsonl，逐局一致；不能合并旧12项报告。
- **多编队独立验证**：六种24–48舰自定义部署、3301–3305五新种子、双方换边60局，coordinated对旧adaptive为42胜18负、70%；30对15正向/3负向/12中性，单侧配对符号检验p=0.003769达到预设门槛。各部署胜局7/5/7/5/9/9，不扩大为逐部署显著；60局全合法/回放一致，发雷1809次、友舰碰撞伤害/误雷友舰0，紧急停车82舰次。三个问题想定168合法局发雷660次、上述友伤0、停车749舰次。证据 constraint-fleet-holdout-60.json，5核心哈希与现行代码一致。
- **测试与保存**：新增状态机约束、来源自动入场/事件、五新风格、禁炮掩护、失败阻断及预登记种子隔离回归。全量599项通过，随后新增3项纳入21项专项通过，当前602用例均覆盖；有Starlette弃用警告，无失败。测试数据库与战报目录均显式隔离到artifacts；TypeScript/Vite（53模块）、Python编译、git diff --check通过。旧报告不可覆盖，README区分修复前后；基本提交 b508bd9，本批未提交。
- **服务同步限制**：已验证正式服务为后端14688/前端45120，准备仅重启后端的命令在创建进程前被执行策略拦截，未执行停止操作。再次核对两端仍监听原PID；本批未成功加载新后端，不谎称同步完成。玩家库只读：games4660、events54760、snapshots20161、custom_scenarios3、battle_report8741；存档内容摘要 SHA-256 7e833ccedbbdb7c2ca1e5159eb546f481cb94597afa9bde443e1c2ec407f23cb，自定义剧本摘要 cfd6da8c244e41ea9ec2ea38e02955a16e994947a07d24ee3a6d46d5ea4cd529。提供现有 stop-game/start-game 手动重启命令；未清理任何玩家记录。

## 2026-10-11 — 修复游玩 500，恢复完整命令延迟模式

- 来源提交：command-delay-run 的 8f9598e；当前 HEAD b508bd9，工作区未提交。仅移植游戏运行模块、三模式 UI、扩展规则说明与对应测试，不合入研究论文或产物，不切换/覆盖新 AI 与既有脏改动。
- 500 原因：正式后端旧 IronBottomEngine 缺少 movement_speed_range，懒加载的新版 formation_tactics 调用了该接口。已完整重启本项目后端；启动器校验端口、PID 创建时间与父子链，复用现有前端，后端自动重载并以 /health 源码摘要判定是否就绪。修复 PowerShell 5/7 日期反序列化差异；错误归属拒绝而不停止。
- 延迟扩展：保留任务命令、TBS/视觉/编码报文/中继、容量与 TTL、三类预案、本地代理和独立记忆、优先级炮击选择器、可选整队机动/重整。默认关闭，限 S-01/S-03/EM-01，不扩展为全局一回合延迟，不改经典/真实模式含义。新增 structured/rules/command-delay.yaml、RC-08 与覆盖表，明确项目扩展和 SIMULATION_ABSTRACTION 边界。
- 合并审查修复：模型策略按 game_id 和 side 隔离，导入/重启不继承其他对局密钥；实际 auto_gunnery 过滤另一侧权重；局部地图加入本编队已发现的雷达/照明接触格，不引入另一编队视野。延迟对手提交采用已有本地代理决策，不绕过本地观察去调用全局 LLM 指挥官。无密钥的教条回退在 UI 明示，不冒充模型输出。
- 续局与 UI：存档卡片/导入/观察携带权威模式标记；本方已封存后可重试对手并继续，避免重复封存。载单/执行中防重复点击，代理方案提交刷新封存状态。保留五新状态机类型和经典/真实各自选择；命令延迟是原有 LLM 代理模式，独立入口及不支持剧本门控。海军主题沿用，规则预览补齐表格、代码块、强调与小屏换行。
- 测试：首次全量 739 passed / 3 failed / 2 skipped（744 用例），3 项仅为新测试夹具问题，已修正；最后合并/旧真实模式专项 43 passed；新增导入与旧格式兼容后合并/规则预览专项 12 passed。带失败的全量运行没有伪报单次全绿。TypeScript、Vite 55 模块、compileall、git diff --check 通过；Starlette 弃用警告保留。模型通信只用离线替身，不声称真实外部 LLM 已测试。
- 浏览器验收：1440×960 与 390×844；真实/经典风格往返、新 AI 建局/阶段提交、模拟 500 文案及封存后刷新重试；延迟模式切换、无密钥校验、支持范围、规则/目录；S-01 任务电报按 +1 回合送达、编队接收命令/记忆/陈旧外部报告、引擎炮击与双侧战果弹窗、链路刷新/本地编队切换/折叠再展开。无页面脚本异常，命令/规则面板稳定可读、无页面横向溢出；截图 artifacts/cd-integration/desktop-{modes,rules,command}.png 和 mobile-{modes,rules,command,chain}.png。测试浏览器与 8011 隔离服务在交付前关闭。
- 正式服务：前端 45120（5173）保留，后端重载父 28196、worker 51600（8000）；/health ready，loaded_revision = source_revision = 8345a36577f8225ff1e9cfd318c7862f6030061fd138b12b91f6c7a0816811b4，延迟规则 HTTP 200。本批结束仍保留正式服务供用户测试。
- 数据保护：正式库仅只读核验；games 4661，内容 SHA-256 d50dec5c613ac3365174559befdee3e772cf01be2196ce4e589d6f10efd26982；custom_scenarios 3，SHA-256 d840587c674a3239afeaadf239c217a1a1398bf3bd72036faed75f6a640f4744。两个摘要与本批重启前一致；所有 API 测试、截图对局和战报都使用 artifacts 下隔离库。未删除任何玩家存档或旧强度报告；先前同步受阻在本批已解决，旧报告仍只代表其冻结源码版本。


## 2026-10-11：二马战局视频制作完成（未提交）

- **真实来源与保护**：读取用户指定微信目录内《舰队视频制作包-20261011.zip》，730 个文件哈希校验通过；来源包与原规则资料保持只读。只读提取最新完成 EM-01 存档 f5f74b17-f8f7-4d89-a623-d75a1254d1d0：174 快照、1788 事件、12 回合、13 艘沉舰。源存档 SHA-256 前后相同；不重跑战斗，不写玩家 SQLite，不改规则、AI 或正式服务。新增 scripts/export_erma_video.py 为离线只读导出器。
- **模型与演绎**：用户授权的日方官方 deepseek-flash 实际生成七条公开说明，美方指定 gpt-6-sol 子代理生成七条、选用六条。只发送/读取本方当时过滤观察和已封存本方命令，不让未来战果回流当前解说；公开意图按角色演绎标注，未收集私有思维链。移动点措辞审订前版本、公开请求收据及来源锚保留；未把状态机原局宣称成模型自主对战，未把密钥写入仓库、环境文件或制作日志。
- **内容与画面**：用户授权虚构 1944 夏补给航路/诱饵背景，战况依实存档。复用成熟 ds-pro 立绘但标 DeepSeek Flash，Sol 海军立绘标美方；左真实前端海图、右角色，配六编队标签、实际炮击关系、实际鱼雷轨迹、舰表与大和记录。强调岛风雷击与鞍马造成得梅因最后沉没分开；最终 62:42、领先20未达25判平局，来源原页已回看，12回合为既有用户扩展。
- **声音与时间线**：Windows 无包内 MLX/Qwen3 克隆环境，改用 Edge 云配音：Yunxi 旁白、Xiaoxiao 成熟女声、Xiaoyi Sol；原始 MP3、处理后48k双声道PCM和词时均保留，旁白仅一次1.18保音高。32镜头、148语义字幕、13,207帧/440.233秒；原生30fps活动镜头与稳定状态定帧统一BT.709/SAR1/1:15360拼接，字幕在舰船区之外。
- **验收**：TypeScript、Python编译、git diff --check；全部使用帧SHA、音频边界、字幕最多2行且每行28字、声音不重叠；完整H.264/AAC解码、每帧PTS精确连续、AAC无削波通过。首版AAC峰值-1.48 dBTP，保留首版后仅降低最终音轨0.4dB，复验-16.25 LUFS/-1.76 dBTP；最终视频与源包哈希更新。已抽看32场景、24帧真正成片、两组完整动作表、实际字幕、开头及最后一帧；未声称全帧人工检查/逐句听审或剪映原生导出。早期兼容错误已修复并保留工件，不以早期样片冒充成片。
- **交付**：artifacts/video/em01-20261011/delivery/二马_DeepSeekFlash对GPTSol_指挥演绎.mp4；captions.srt/ass、QUALITY/LOUDNESS、成片抽帧；二马_可编辑制作源包.zip约51.37MiB、193文件、CRC/逐文件SHA及使用资源依赖闭包通过。40秒带声样段单独保留。可编辑工程不含node_modules、密钥、旧示例音画或无关素材。基线提交 b508bd9；本批未提交，既有用户未提交改动完整保留。

## 2026-10-11 二马视频：完整舰娘参战序列与 Q 版指挥官

状态：已完成（未提交；HEAD b508bd9）。按用户追加要求，在原成片开头展示六支编队、双方各12舰的完整参战序列；优先同名舰娘，5舰使用经想定舰卡 family 核实的同级代用，6舰使用用户明确批准的近型代用，均标出代用原角色。24舰全部使用小人，实际舰名、舰种、顺序和旗舰保留；信浓仍按本想定 BB 战列舰标注。

- 从用户指定 `https://ww-rm.top/azurlane_char/` 下载17个角色的51个原始 Spine 文件，保存索引、来源 URL 与 SHA-256；使用 pixi.js7.4.3 / pixi-spine4.0.6 渲染透明 stand 姿态。
- 用 imagegen 内置工具生成 DeepSeek Flash 深蓝海军御姐、GPT Sol 白色海军指挥官两张透明 Q 版 PNG，沿用制作包立绘身份；提示词、原参考边界、透明背景检查和输出哈希均在证据目录。
- 修订指挥官登场及六队序列镜头，并让片头右侧指挥席显示对应分队及 Q 版角色；后续实际战局和双方已生成的公开命令解说沿用首版。
- 最新交付目录：`artifacts/video/em01-20261011/delivery-v4/`。完整视频 `二马_DeepSeekFlash对GPTSol_指挥演绎.mp4` 为1920×1080、30fps、478.9667秒（7分59秒）、H.264/AAC；36镜头、163条字幕、14369帧。同步更新 SRT、ASS 与70.16MiB可编辑源包。
- 验证：TypeScript typecheck、Python语法、`git diff --check` 通过；24舰全覆盖，6队顺序和旗舰准确，5个同级映射的舰卡 family 一致；所有源帧、音频和下载/生成素材哈希通过，所选玩家存档原状态 SHA 未变。整片完整解码、每帧 PTS 连续、音频无重叠/削波；实测-15.72LUFS、-1.78dBTP；294文件源包CRC和全部SHA通过。
- 视觉证据：实际成片抽帧检查包含两位指挥官、六队名册、接回战斗及最后一帧；另检查透明角色和镜头入场。没有宣称全帧人工检查或逐句全片听审。原游戏服务、资料、存档与裁决未修改；原始成片保留，未发布。

## 2026-10-11 二马视频：清理制作标签与精简对战呈现

状态：已完成（未提交；HEAD b508bd9）。按用户要求删除影片中的“战局旁白 / 非实时对局 / 预录 / 读取既定命令 / 公开说明”等重复制作标签；按用户进一步明确要求，片尾也不放存档演绎说明。

- 全片侧栏改为 DeepSeek Flash VS GPT Sol、海战名称和当前分队；片头 Q 版指挥官只显示模型与阵营，参战序列去掉制作脚注，舰名、舰种、旗舰、同级/近型代用标签保留。
- 重写7段制作过程较多的旁白并合成新配音，重编同步字幕与时间线。双方模型的13段原公开解说、已完成战局的18个实际快照绑定、鱼雷/炮击轨迹与24舰顺序保持一致。来源与真实制作方式只留在源包审计资料，不宣称模型自主操舰实测。
- 36镜头全部重新渲染，不复用带旧标签的画面。最新交付为 `artifacts/video/em01-20261011/delivery-v5/二马_DeepSeekFlash_vs_GPTSol.mp4`，454.2秒（7分34秒）、1920×1080/30fps、H.264/AAC，13626帧、160条字幕；字幕与295文件可编辑源包已同步更新。
- 验证：TypeScript typecheck、Python语法、`git diff --check`；原所选存档SHA未变，实际快照/音频/角色素材哈希通过。完整视频解码、全部PTS连续、音频不重叠无削波通过；实测-15.68LUFS、-1.92dBTP；源包CRC及所有SHA通过，67.98MiB。
- 视觉检查：14个实际成片抽帧覆盖指挥官登场、六队序列、双方解说、指挥继承、复盘、战果、收尾与最后一帧；片尾仅显示比分和平局结果，无附加制作说明。配音/字幕与显示组件文本检查无残留上述制作标签。未声称全帧人工检查或全片逐句听审。原游戏服务、裁决及玩家存档未改，旧版成片保留，未发布。

## 2026-10-12 二马视频 v6：加快语速、碧蓝军官语音、炮击全过程与原生2K

已完成，未提交。成片：`artifacts/video/em01-20261011/delivery-v6/二马_DeepSeekFlash_vs_GPTSol.mp4`；字幕和可编辑源包同目录，旧v5保留。

- 旁白处理1.18→1.36（约15.25%加快），DeepSeek/GPT角色1.16倍保音高；原模型台词保持一致。
- 根据用户后续指定改用D盘吾妻/新泽西WAV，分别承担日军/美军下级军官，42段不同录音、68次穿插；同一时刻只播放一段讲话。日语small/medium两轮本地ASR和中文译文保留；排除金刚指名台词与友军误沉。场景文件名没有冒充台词。原始WAV/XML/哈希及全部使用节点附源包。
- 在2:43–3:54展示第二回合衣阿华→岛风：GF76、修正0、D66=23→4发命中；56/64/55/54逐发损伤，船体7→5、P1摧毁、雷达失效、火灾1；回合末9点灭火。使用原典命中/结果/装甲表截图及原前端舰船状态。旧55号火灾记录与原典星号适用范围差异已登记`docs/rules/open_questions.md`，本批不重裁、不改存档、不将其推广为通用规则。
- 原生2560×1440、30fps，40镜头全部重新渲染；H.264 CRF16、BT.709、AAC48k立体声256k。角色登场、24舰/6分队及代用标识保留，片尾无存档演绎说明。
- 验证：TypeScript无错误；247字幕至多2行/28字；8处插话的PCM分割保留每一个原音样本；全部原始帧/音频/小人哈希通过；最终对局数据库只读SHA不变。全片20,099帧PTS逐个校验，完整解码通过，峰值0.804977，响度−16.07LUFS/真峰−1.86dBTP。实际编码24抽帧；人工抽看命中表高亮、损伤表、火灾前后状态、美日军官字幕、平局及片尾，不声称全帧人工检查或全片人工听审。
- 源包：531文件，120655083字节，CRC及每个文件SHA通过，使用20个舰船帧；无node_modules/密钥。视频SHA：6786f7ad3754a16bf30e61fc1f90ee01e12c72a24f5e269f289da443a132543b；源包SHA：38d787e49ea92f66c29de3b705139197874bbf4bf1ff8ddb24899b256cda8aa8。证据：INPUT_QA、QUALITY、LOUDNESS、AUDIO_MASTERING、SOURCE_PACKAGE_QA、translation-audit、selected-event-chain。
- 本批未创建提交；基准HEAD：`b508bd92a58a15a86bd9f34ba4648798af0fb775`。未改动规则引擎、玩家存档或其他既有工作。


## 2026-10-12 二马视频 v7：混合军官台词去重与连续脉冲机动

已完成（未提交；本批验证时 HEAD `b508bd92a58a15a86bd9f34ba4648798af0fb775`）。保留 v6；最新交付在 `artifacts/video/em01-20261011/delivery-v7/`。

- 68次呼叫，68段不同源WAV、68条标点归一后不同台词；吾妻/新泽西26条，原美日军官电台42条。日方15+16、美方11+26，两侧均混用两库。修整4段边界、替换不完整句子；当前42段电台全部有独立medium ASR及精确音频哈希，字幕按实际话语校正。未声称全片人工逐句听审。
- 第2–12回合覆盖11轮机动、12个连续运动镜头；读取封存计划和实际事件，通过已有引擎几何程序只读生成位置/航向。179条舰船终点、提前停车与10次鱼雷接触吻合；695个舰船相邻步和384个鱼雷相邻步检查通过。鱼雷按发射MF出现、沿实际经过格推进，射程耗尽移除；关岛在记录的南侧终点淡出。两个原鱼雷镜头单独改为固定视口并替换，非运动内容不改。
- 原生2560×1440/30fps，21,501帧、716.7秒（11分56.7秒）、50镜头、247字幕。保留原快语速、完整实际炮击演示、24舰序列及两位指挥官；原模型解说不改。6处分段主解说PCM拼接与原完整音频完全一致，所有声音不重叠，字幕最多2行/28字；无片尾演绎说明。
- 验证：TypeScript通过；输入、原存档状态SHA、来源WAV、路径/接触及连续帧检查通过。第2/3/4回合实际编码的活动脉冲区间，所有相邻地图帧变化；整片全解码与21,501帧PTS检查通过。最终响度-16.17 LUFS、-1.86 dBTP，解码峰值0.803307。42个实际成片抽帧，最终人工抽看炮击、两侧字幕、T3移动、T12撤离与终帧。
- 源包673文件、34使用中原帧，135,435,672字节；CRC与全部文件SHA通过，包含代码、使用中原WAV/处理音频、字幕、路径、表格、字体、素材和审计；无依赖目录或凭据。
- 证据：`evidence/officers-v7/AUDIO_DIALOGUE_QA.json`、`evidence/movement-v7/path-audit.json`、`MOTION_QA.json`、`ENCODED_MOTION_QA.json`，以及交付目录的QUALITY/LOUDNESS/SOURCE_PACKAGE_QA与42帧接触表。
- 成片SHA256：`6fd59bf7c4d918e2d9de454dcf36eef5e13e23ba248feede3f13b47afa9dc7e7`；源包SHA256：`dcc02ecc0d891784a8cb6ce3d28c7e21c8c7d56a044a550bf34fd2caf28c37cb`。未改规则引擎、原始规范来源或原游戏存档；既有55点火灾结果的原典差异继续保留在前批审计中。

## 2026-10-12 二马视频横竖封面与发布标题

已完成（未提交；验证HEAD `b508bd92a58a15a86bd9f34ba4648798af0fb775`）。交付位于 `artifacts/video/em01-20261011/delivery-v7/covers-v1/`。

- 发布标题：**舰沉了，鱼雷还在追杀！DeepSeek Flash VS GPT Sol｜二马海战**。封面大字“舰沉了 / 雷还在！”，对应已发射鱼雷在驱逐舰沉没后继续航行的实际战局；不添加胜负断言。
- imagegen内置生成，以既有DeepSeek/GPT立绘为身份参考；横竖分别构图，竖版额外引用横版视觉。保留原生PNG，无裁切或放大。横版1672×941、3,386,862字节；竖版941×1672、3,225,787字节。比例约16:9和9:16，工具原生尺寸存在约0.053%的整数取整偏差。
- 人工检查两位成年指挥官脸、发色、海军服及全部六项文字；标题清晰、竖版角色帽子留白、炮战和鱼雷元素可见。PNG签名、尺寸、SHA通过，标题与提示词一致。封面包7文件全部CRC及原文件字节一致性通过；不涉及规则变更，未运行游戏测试。v7成片重新计算SHA一致。
- 证据：`covers-v1/prompts.json` 完整提示词，`manifest.json` 引用来源/输出尺寸/哈希/视觉核对，`发布标题.txt`，`README.txt`。角色源SHA：DeepSeek `45c13198fc1b371b98b2ad2a427b2ca38dcd315743b4e1bb904ef10438137b9c`，GPT `590abee7fe15b0e89f325bd6953a7c5869ca880f667edecb2e1f09f630fc7e69`。
- 输出SHA256：横版 `de21eeb309e53e37ebccf39ddbffd235e302095fe37dc6528717794de726be68`；竖版 `8246287aba0a6ef1af0698c7c99a700689f01ddc6c6d6bdcdc37a56acd7e35bf`；`二马海战_横竖封面与标题.zip` 为 `2c06a62caa642a7022e50b56d50ad41afc3e534cbd892ae0dcd3175f631d5d38`。

## 2026-10-12 追击大和号封面 v3：舰娘持刀贴脸对决

已完成（未提交；HEAD `b508bd92a58a15a86bd9f34ba4648798af0fb775`）。用户先要求去除旭日旗、突出大和级对衣阿华级、AI人物对视和更多小人，后追加以武藏/新泽西舰娘刀剑对决替换大型战舰；最新交付为 `artifacts/video/em01-20261011/delivery-v7/covers-v3/`，舰船构图v2仅留作草稿。

- 新发布片名“追击大和号”；标题“追击大和号！大和级 VS 衣阿华级｜DeepSeek Flash 对战 GPT Sol”。横竖封面保留AI角色对视、级别对决与清晰文案，移除旗帜和大型船体，增加武藏/新泽西贴近瞪视与紫/蓝刀刃交叉。两位主角加六位配角共8位舰娘，竖版一次修订清理重复主角，并用吾妻原图核对深色头发配角；早期提示词对该配角的伊吹称呼在最终提示词注释/来源中明确纠正。
- 使用imagegen内置工具。横版和竖版均直接传入武藏 `wuzang.png`、新泽西 `xinzexi.png` 原始600×600小人参考，不仅文字描述。后续竖版编辑另输入吾妻 `wuqi.png`。原图和联系图随12文件封面包保存；实际调用提示词与路径见 `完整提示词.json` 和最终修订提示词。
- 横PNG1672×941、3,364,590字节；竖PNG941×1672、3,430,501字节，约16:9和9:16，保留工具原生像素。人工查看两张最终图：全部六项文案正确、无旗帜/旭日图案、对视/持刀与8角色可见。5张PNG签名/尺寸/SHA通过；两张生成原图及三张小人源图逐字节一致，直接输入与五图上限核对通过。
- 封面包 `追击大和号_横竖封面_持刀对决.zip`，12文件、7,947,740字节，CRC与逐文件原始字节一致检查通过。`QUALITY.json`、`manifest.json` 保存验证和来源。v7视频重新计算SHA仍为 `6fd59bf7c4d918e2d9de454dcf36eef5e13e23ba248feede3f13b47afa9dc7e7`；本批只改发布命名及封面，未改原存档/规则/既有视频，不涉及游戏测试。
- 横SHA256 `1c95f8e1764ae86f0c07b23fe28d52b39e45ac7d3b94b0170d108990e3bbc1a9`；竖SHA256 `98b0e02c584d4aefca0808fa8634d6149dd729293ea58ca494ffa5fff5c12f6f`；封面包SHA256 `45f2684837546ee353a65a94018013da832b427e12a2d44feb33a04474b4014e`。

## 2026-10-12：Windows 一键启动 EXE

制作及隔离验收已完成（未提交；基线 HEAD `b508bd9`），正式启动待用户双击。根目录 `一键启动游戏.exe` 为 .NET Framework 4 GUI PE，14,336 字节，SHA256 `42876963044c85523a58c982ba48f3c2b6b3e228e044441ab8e997f2de09bcae`。源码 `scripts/launcher/GameLauncher.cs`，构建脚本 `scripts/build-launcher.ps1`；生成 EXE 忽略入库，源代码及验证文件普通 Git 管理。它是启动器而非独立游戏安装包，不含密钥或玩家数据，未签名，不申请管理员权限或改变系统执行策略。

- 相对 EXE 位置查找项目，绝对路径调用 Windows PowerShell 与现有安全启动脚本，启动后打开浏览器；保留端口身份/源码健康检查。SHA 派生的本地互斥防止重复点击多开；支持 `--quiet`、`--no-browser`、`--restart-backend`。启动状态、失败指导和日志目录按钮沿用既有海军配色；失败返回实际脚本状态码，日志在 `tmp/runtime/launcher.log`。只超时停止本次包装脚本，不强杀游戏进程树。
- 首次 PS5 构建遇到无 BOM 的中文文件名解析，已修正。初次测试环境目录缺失和 PS7 模块路径污染导致夹具失败，改用 Framework SHA 并隔离子进程模块路径。GUI 无控制台时 `Console.OutputEncoding` 引发异常，改为 UTF-8 标准流 writer；修正后 `tests/test_windows_launcher.py` **10 passed / 8.06s**。覆盖 PE 子系统、中文/空格路径与不同工作目录、默认/显式参数、失败与日志、未知端口提示、移动 EXE 拒绝、重复点击、构建拒绝覆盖、帮助/未知参数、GUI 成功关闭/失败按钮。GUI 截图为隔离桩项目真实窗体，人工检查文字和按钮无裁切；证据在 `artifacts/launcher/pytest-final/test_gui_error_state_and_close0/screenshots/`。构建和最终差异检查通过，不宣称游戏全量测试或复盘修复。
- 用户明确授权切换服务；再次核验手动后端 PID 63692 创建时刻 2026-10-12 15:00:46.516306 +08:00、前端 PID 67380 为 15:00:48.045892 +08:00，命令与监听端口一致后仅停止这两者。随后调用正式 EXE 的 `Start-Process` 请求被执行环境 policy 拒绝、未执行；不换工具/命令绕过限制。最终 8000/5173 未监听，需要用户双击 EXE；未声称正式健康、二次复用或浏览器实际打开已验收。
- 切换前后以 SQLite `mode=ro` 按行 SHA 校验六表完全相同：games 4662（`fa91dcf08b1e54bfd6db17fe69949f9efa8c3c88c7e643e9a95c589403a8fddc`）、events 56567（`9f95af709e3bf3df6b0bcf85c736de3f00bbbe84a1f02d44ae861f0cbfe72f6b`）、snapshots 20348（`dca0b8d05da4391d2486d4860b3b988a105ca84f1a924f01d0b2344c842123fc`）、custom_scenarios 3（`d840587c674a3239afeaadf239c217a1a1398bf3bd72036faed75f6a640f4744`）、battle_report 9065（`3eda4d03f9a7662801d8377273190bb593773164a13cc70a64faa9c1f2714897`）、research_consent 21（`9ffb5d07565b5e81afadcf71bd682249293255360907f000c39b957f1c1c9dc4`）。API 导入测试使用隔离路径，未新建正式测试局；存档、战报及无关脏改动保留。

## 2026-10-12：状态机整管鱼雷齐射修复

已完成（未提交；基线 HEAD `b508bd9`）。仅更改 AI 发射策略，不更改引擎裁决、合法部分齐射或玩家存档。

- 根因：自适应评分对同一雷道的封锁收益不随齐射枚数增长，但弹药机会成本按数量扣分，故除高命中组合外经常偏好单枚。S-03 seed44真实模式复现：协同、T头、雷击双翼、护航、分进合击及adaptive均有4具装2枚的管只射1枚，6管共8枚；修复后6管均2枚，共12枚，原引擎校验合法。
- `AdaptiveTorpedoPlanner.analyze` 在评分前依据己方每管当前 `loaded` 筛掉部分候选，保留原引擎提供的满管合法/友军安全雷道；排名备选、期望命中、所选订单和审计使用同一枚数，不在选单后强改。各管独立，未选管可以保留，真剩1枚则1枚；空管/损毁/装填中不射。不读取敌方库存，经典旧策略本来已满管，五个新类型与自适应/专项风格共享修复入口。
- 按规则技能检索后回看原规则 PDF 11页8.2“发射鱼雷”：玩家可发射部分或全部，装填完成后再发射；沿用 `IBS-R-08.2.2`、现有库存和发射事件。整管是本次用户要求的AI策略，不伪称原规则禁止小齐射。原文件/表格不改，来源页截图 `artifacts/full-salvo/rules-page11.png`。
- 新增 `tests/test_full_salvo_ai.py`，覆盖12个非legacy风格×经典/真实×双方、现装1枚/空/毁/装填、审计一致、只给部分候选时拒绝而非硬放大、无安全候选保留、敌库存无影响、合法玩家小齐射、API实际对手封存且不回传秘密订单、经典/真实完整对局回放；另用二马岛风原3枚管实测整管3枚合法。原5新类型发射测试新增实际事件枚数/耗尽断言。
- 首次新测试24失败均因把排名备选当同时提交订单、错误要求备选中每管唯一；实际订单满管检查及10项其它检查已通过。修正仅该备选唯一性断言、保留每个备选满管检查后，**263 passed / 233.48秒**（整管、adaptive、协同、旧tactical、鱼雷助手、引擎、裁决表与基本规则）；另 **19 passed / 5.52秒**（追加三枚管与18项想定特例），合计282项不同用例。完整对局/确定性回放通过，相关对局无误雷己方；仅 Starlette 既有弃用警告。Python 编译/差异检查通过，不声称全仓测试或新胜率已验收。
- 正式服务自动重载，无需另行强制重启；父PID47660、工作PID9784、前端PID66392。health ready且 loaded/source均 `18045c1c8a6a4d080026bcec9d217a9c886b525ed9bbd1b5420066da739b97ec`，前端HTTP200。API测试显式隔离至 `artifacts/full-salvo/test-api.sqlite3`，正式服务只读健康检查；已封存旧订单和历史记录不改，下次未封存AI计划采用修复。README注明所有旧强度结果为此策略修复前冻结版本。

## 2026-10-13：恢复完整新版并保留 zcode 船体射界图

已完成（未提交；当前 HEAD `4a7f5e2`、分支 `glm/rtt-port`）。用户首先要求重启前端，查明原因后明确授权恢复新版、保留射界图并重启前后端。

- 根因不是射界图删剧本：reflog显示从 `glm/rtt-port` 的完整检查点切到旧 `codex/phase1-engine` / fc77a65，其 `StartScreen` 固定仅3个剧本，随后 zcode 提交92ced8c射界图、e38557a文档。新AI/命令延迟/整管鱼雷/完整剧本均保存在4a7f5e2中，未丢失。两分支/提交保留，不reset/rebase，不推送或创建额外提交。
- 按授权切回新版，在 `ShipStatusCard.tsx` / `style.css` 移植92ced8c的实际布局差异：舰艏朝上，炮位按前/后/左/右/中分组，同侧多炮两列，四向射界点亮与可用/已射击/摧毁状态、悬停与图例保留。同时保留新版已有装甲分布行及主/副炮来源字段；不以旧文件覆盖新版命令延迟/AI/规则面板样式，不改裁决。当前卡源码SHA256 `c46d8ffffb2dbc4390d0c704204c04c70fd4885596da3b0770ac12c20f526638`。
- 旧8000/5173服务PID25980/25416的目录（根目录/frontend）、命令、创建时刻2026-10-13 08:55:42.528223 / .558356 +08:00与端口核验后，仅停止这两者。恢复安全启动脚本后启动正式后端父54408/工作55256及前端48972；两端HTTP200，health ready且loaded/source均 `0cb8439be292578318812f141fef53e26164e5704da54100bcc80159260574ae`。再次运行 `start-game.ps1 -NoBrowser` 复用上述PID，未新增重复服务。
- 正式API和真实桌面/手机界面均 **16内置+3自定义**。Playwright普通点击覆盖自由对战、五新AI选择/启用真实、经典↔真实、命令延迟强制LLM/不支持剧本门控，旧二马炮击存档续玩、刷新与大和/吾妻/岛风切换。大和实测17炮位（非旧zcode文档误写的16），每个点亮射界与状态逐项匹配本方观察数据；图宽桌面491/491、手机332/332，手机viewport390/390，无横向溢出或JS错误。截图在 `artifacts/restore-20261013/`。浏览器拦截所有非GET请求，没有正式库写入；验收浏览器已关闭，游戏服务保留运行。
- TypeScript/Vite生产构建 **55 modules**通过；存档、整管鱼雷及命令延迟集成 **49 passed / 56.99秒**，仅既有Starlette弃用警告，API测试库显式隔离。差异检查通过。浏览器脚本一次按钮正则误匹配存档卡、一次存档列表尚在加载导致超时，修正作用域/等待后真实流程通过，不把脚本错误说成游戏故障。
- 切换前后SQLite六表只读行摘要完全相同：games4667 `b7402f33c5eaf2f64b208fad0dc250202d16de2d4984dbc7416aa52232ab77ea`；events66069 `597a3f84cccaef242e9ef3361d5cb7f07ce487def110e426d5a62185ea8becd1`；snapshots20934 `697313846d0a53cd392bcc4a0e87d4bae9fc37bbfd5bcaa6dfa731a206dd7d71`；custom_scenarios3 `d840587c674a3239afeaadf239c217a1a1398bf3bd72036faed75f6a640f4744`；battle_report10073 `378a7c5c3fb3fc54586f6988357c6b13c8127d9c5c437ea303d5991b661a8a05`；research_consent25 `be31fac3ab0b4d3289e672adaa6db11ed059161f355b4060d816d0aebf6545e9`。玩家存档/战报/密钥边界未改。
- Git切分支提示241个RTT计数器文件应是LFS指针但历史提交是普通图片，使过滤后status显示修改；只在只读diff命令临时关闭过滤验证，素材实际字节与HEAD一致。未修改/删除素材、不改持久LFS配置、不把这些过滤差异纳入本批源码修改。

## 2026-10-13：桌面一键启动快捷方式

已完成（未提交；本批 HEAD `4a7f5e2`）。按用户请求在实际桌面创建 `D:\desktop\铁底湾的回响 IV.lnk`，目标为 `C:\Users\fwj\Documents\ChatGPT\铁底湾\一键启动游戏.exe`，工作目录为项目根目录，参数为空，使用启动器自身图标；双击调用现有启动器的默认自动打开浏览器流程。

验证：通过 WScript.Shell 重新打开已保存的 .lnk，目标、工作目录、空参数、图标和目标存在性全部一致；快捷方式 1672 字节，启动器 SHA256 `42876963044c85523a58c982ba48f3c2b6b3e228e044441ab8e997f2de09bcae`。未触发正式游戏启动，本批验证范围为快捷方式配置及文件存在性；复用原启动器，无新源码或规则变更，无需游戏回归测试。

## 2026-10-13：萨沃岛／夜战／同局 AI 记忆续接完成

本轮实现与可核实范围验收完成，未提交。分支 `glm/rtt-port`，基础提交 `4a7f5e24abfd269ee41e0c07f59fefb4843f79ce`。保留恢复的新版、新状态机、整管鱼雷、命令延迟和船体射界图；没有更改原始 PDF、地图图片或玩家对局。S04/S10 完整原典实战尚未完成，来源缺口保留为显式阻断。

- 新局默认 night-v2，十可选规则默认不变；参数、裁决表、舰船和开局状态冻结入局。五岛屿锚点及萨沃岛已知特例接入引擎；照明延迟与整炮组占用、探照灯暴露、雨飑统一骰、实际航迹烟幕、雷达权限与岸线、已执行炮击剪影、确认战损、玩家揭示隐蔽鱼雷均有边界验证。四向审计在 `docs/rules/night-v2-audit.md`，来源页为规则 PDF13/14、萨沃岛想定 PDF10/11、穿甲表 PDF4。
- 普通观察及事件按事件时刻的已知舰过滤；未确认残骸、未知攻击舰、嵌入发射舰名的鱼雷编号和私有检查点不泄漏。新版完整战报限对局结束后；debug 观察、敌方封存航迹、AI 记录及记忆导出需显式本地调试。接受决策后才更新阵营私有记忆，结果取正式观察；失败/建议不写入。记忆和长日志随存档、导入、重启及事件回放恢复，新局不继承；公开输出/解析/校验/耗时/重试可审计，私有推理和真实密钥丢弃。
- 旧局保持 legacy-v1，安全边界另存升级副本；保留 RNG、历史事件与原局编号，新局/升级回放检查点随导入改写新编号。正式萨沃岛旧局 T4/30 只读加载、简报和刷新均通过；新版 S10 顶栏及保存列表按服务提供的无限回合标志显示 ∞，旧局简报明确旧增援流程和回合上限。
- 传统 AI 的三舰首步死端增加本方下一轮合法首步可行性检查；友舰路线冲突在封存前解开。一次规划内缓存重复航迹/必走格，每次清空，不改变规则与候选评分。S06 rc_coordinated seed1 allies 两回合相同用例从缓存前 83.77 秒到缓存后 2.30 秒；FM-01 相应用例也继续通过。测试仅验证合法性、流程和确定性，不把性能数值或两回合矩阵解释成整局强度。
- 全量回归 `full-final.xml` **877 passed / 2 skipped，1135.84 秒**。全量后的补充信息边界、同局记忆、存档/回放和整管鱼雷 **139 passed / 81.07 秒**；最终缓存/编队/匹配/夜战 **212 passed / 134.80 秒**；最终无限回合简报与存档 API **4 passed / 3.03 秒**。这些集合有交叉，不累计成总数。仅既有 Starlette 弃用警告；早期失败保留为修复前证据，最终以上产物均无失败。所有测试使用隔离数据库与战报目录。
- 五新风格、双方、seed1/13、S04/S06/S08/S10/FM-01、传统/真实两模式 **200 唯一组合**：每种模式 60 passed、40 source_blocked；合计 **120 passed / 80 source_blocked / 0 failed / 0 友舰碰撞**。夜战订单计数为照明7865、探照灯1227、鱼雷510。开局两回合没有触发重伤烟幕；另有五风格重伤且火炮失效的合成烟幕策略测试通过，不能把0次烟幕计数说成覆盖了该策略。最终矩阵与 `ai-matrix-summary.json` 在 `artifacts/night-20261013/`；缓存前慢用例的未完成矩阵单独保留。真实联网 LLM 未执行，LLM 重试/超时/记忆/普通与真实模式由受控 MockTransport 验证，不宣称付费模型验收。
- TypeScript/Vite **56 modules**生产构建通过，`git diff --check`通过。Playwright实际点击覆盖十开关/预设、非法雨飑与清空、夜战订单编辑及调试切换不覆盖草稿、按阶段筛选和记忆下载、存档下载/导入/刷新、复盘、简报与确认敌损、80陆地格与29岸线格。1440×1000桌面与390×844手机无JS错误/横向溢出；船体图宽分别491.4/332，SHA256仍为 `c46d8ffffb2dbc4390d0c704204c04c70fd4885596da3b0770ac12c20f526638`。手机弹窗层级修复后完整覆盖底部导航；正式页面最终只读加载，没有触发写入。截图和实际下载文件在同一证据目录，浏览器和临时服务已关闭。
- 正式服务最后用已核验的项目启动/停止脚本重启，端口8000/5173就绪；健康检查 loaded/source revision同为 `c21b0e4bd8ae8b4bb4c15c3fa1304f6381c4410b8b845204b0f0908e69abb8fc`；API 16内置+3自定义，前端HTTP200。正式库按原始字节只读逐行摘要检查，启动前、重启后及最终均完全相同：games4669、events67060、snapshots21067、battle_report10304、custom_scenarios3、research_consent27、ai_debug0。摘要在 `player-db-before-restart.json` / `player-db-final.json`，源码和四份原始资料哈希在 `source-sha256.json`。未改玩家存档、战报或科研授权。

剩余来源问题：IBS-Q-024 古鹰格位/后续舰图外入场时机；IBS-Q-025 S04/S10 现有岛屿校准与原典初始舰位冲突；IBS-Q-026 SAN-JUAN/HOBART 未核实记录。历史资料支持古鹰纵队位置，但不能换算游戏坐标；未擅自补坐标、搬船或套用记录。IBS-Q-021 穿甲表只到25格，超出时保留雷达接触并阻断自动炮击，25不是新设物理射程。已登记 `docs/rules/open_questions.md`，阻断不算通过。

## 2026-10-13：阻断所需资料说明更正

应用户追问复核 Q024/025/026 与真实 LLM 验收条件，基础提交仍为 `4a7f5e24abfd269ee41e0c07f59fefb4843f79ce`，未提交。重新执行规则检索并视觉回看想定 PDF4/10、舰船记录 PDF17、原主地图和岛图。**两艘增援舰并不缺原始舰卡**：圣胡安、霍巴特都在记录手册 PDF17/印刷17的东方部队；圣胡安还已以 `IBS-U-USN-UNNAMED-T01-R25` 建档。上一轮将程序编号映射/转录缺口笼统写成舰船资料缺失，核对不充分，已更正 plan、开放问题与规则审计。霍巴特原卡需转录，圣胡安需核对专用卡并映射；在实现与测试前运行 Q026 阻断仍保留，无须用户补发这两张卡。

来源验证：`ship-record-manual-1.1-zh.pdf` SHA256 `eeff020db4a7f491def219335404996d4b204035923be2b5bd925f65dfdac210`；原页渲染 `tmp/pdfs/blockers-20261013/record-17.png`。地形冲突目前是现有转换/配准结果，尚不能认定原典部署错误，应先利用已有图片继续核对。确实未列的古鹰坐标/到达时机与后续队列入场参数，需原典勘误或明确标记的用户部署约定。当前工具进程仅检查了密钥是否存在：DEEPSEEK_API_KEY/ZHIPU_API_KEY均未配置，不读取或输出密钥值；游戏内临时密钥不持久化，不能据此声称玩家从未配置过。

本次变更范围为来源说明文档；无引擎修改、无网络模型调用、无正式数据库写入。验证为原页视觉复核、已加载舰船记录编号核对及差异检查，未重复运行游戏回归，也没有把来源定位算成运行阻断解除。
# 2026-10-13：GPT-6 Luna真实实测、萨沃岛舰卡和历史部署草案

- 用户授权：指定GPT Luna实测，询问调试决策过程，从历史资料补充萨沃岛部署。读取agent.md，应用openai-docs与iron-bottom-sound-rules的来源核验流程；没有替换成其他模型，没有读取/复制登录令牌。
- `scripts/test_luna_live.py`通过官方Codex CLI已有登录调用`gpt-6-luna`，禁用模型工具、多代理、会话落盘；只接收最终公开JSON与用量，私有推理事件直接丢弃。CLI没有继承Windows系统代理，测试子进程加入现有代理后连通。无OPENAI_API_KEY，故这是CLI桥接正式JSON/API校验测试，公共OpenAI HTTP API尚未测试；游戏提供商菜单仍是既有DeepSeek/GLM，不能把测试桥接称为GPT已加入正式菜单。
- 实际10次决策请求，7个首轮通过、3个120秒连接超时；传统S03完整一回合（增援、移动、鱼雷、炮击），真实S03编队部署、增援、编队移动。已成功响应耗时11.01–55.75秒。最初报告/续测报告保留失败事实，最终核验为`artifacts/night-20261013/luna-live/final-verification.json`，公开审计JSON位于同目录。传统记忆revision4、真实revision3；正常观察不包含私有记忆，存档记忆及game_id回放一致。未宣称真实模式完整回合、完整对局胜率或AI强度。
- 实测定位并修复超时审计回放遗漏：新增`ai_decision_rejected`私有检查点；失败不提交记忆。早期night-v2存档用game_id回放可保留已有拒绝审计缓存，不伪造旧事件；仅事件日志无法恢复旧日志中不存在的拒绝记录，文档明确此限度。
- 原记录手册PDF17专用圣胡安/霍巴特已独立逐格转录至`savo-cards.yaml`，包含伤害轨、箭头射界、炮位类别、装甲、雷达/飞机格、鱼雷与VP。圣胡安中央0炮力排除且有效水面火力为副炮，`make_ship`支持无有效主炮记录，旧通用圣胡安编号保留。原增援ID及棋子接通；图拉吉护航使用Hull II，禁止借Hull I。来源PDFSHA核验，实际东方组入场及R21事件测试通过；Q026解除，合成测试不解除Q024/Q025。
- 调试窗口直接显示模型/公开态势/目标/逐舰意图/预案，可展开JSON与校验、重试、记忆。旧战报reasoning读取屏蔽、捕获丢弃，Markdown/HTML/UI不显示私有推理；原数据库旧内容不重写。桌面1440×1000、手机390×844，空阵营/不存在回合、展开JSON、关闭重开均验证，页面无横向溢出/浏览器异常。截图`luna-debug-desktop.png`、`luna-debug-mobile.png`；手机标题和关闭按钮保持完整。
- 下载1950海军战争学院原分析扫描PDF并回看印刷106/110/115/118（PDF160/164/169/174），记录八舰列序、古鹰第五、约1300码间距、5200码纵深与六分钟时差。规则原页1.2为600码/格、3分钟/回合；历史草案以9格取整、古鹰及后三舰T2第2/3/4/5MF从A27进入，并明确该方案不让古鹰首回合射击、后三舰一格不复现历史统一间距、引擎尚无虚拟队列MF入场。不是勘误或已可玩的历史版。主图/岛图同为平顶奇数列下错；同向平移仍有陆地冲突，历史报告不能确定覆盖图唯一旋转角。具体方案及所需第二锚点/朝向见`docs/rules/savo-historical-supplement-20261013.md`。
- 验证：157 passed（`luna-savo-final-tests.xml`，来源、夜战边界、失败/成功回放、LLM/API、记忆、保存、旧战报私有字段屏蔽）；`npm run build`通过56模块；`git diff --check`通过；原始来源Git无改动。前批次877 passed / 2 skipped不冒充本批次重新全量运行。
- 玩家库保护：本批次Luna只操作临时`ibs-luna-live-*`库，UI代理只读8015隔离服务。相比前批次摘要，正式库运行期间新增S06状态机AI对局到T4，不能声称跨整批次库完全不变，也不回滚这项现场写入。最新正式库基线4670局/67386事件/21116快照/10388战报/3自定义/28同意/13调试，连续只读原始字节摘要一致（`player-db-luna-after.json`、`player-db-before-luna-restart.json`）；继续保留该数据。隔离浏览器关闭、8015服务停止；正式8000/5173保留，health loaded/source一致。
- Git基线提交：`4a7f5e24abfd269ee41e0c07f59fefb4843f79ce`，本批次与前批次工作仍未提交。

## 2026-10-13 夜战实战反馈、AI照明协同与直线灯光

- 读取agent.md并按iron-bottom-sound-rules检索/回看规则书PDF13、玩家辅助表PDF2、S06想定PDF6。实际玩家S06（68116b66-159e-480f-8334-27ab1da00423）视程日21/盟19，雨飑已开但中心为空，照明弹无计划。原T1日方五灯照沃克、美方四灯照长良；鱼雷T2长良→沃克1命中、T3本汉姆→长良2命中，已发生鱼雷Sunk效果。
- 状态机按照明占炮后实际射击目标配灯，一目标优先一束、同一发射舰只用一次；本方下一回合照明区域去重，避免整队重复占炮。仍允许玩家合法多束同目标，未改修正叠加或原典裁决。辅助表/规则书关于开灯舰−3的文句差异按优先级记录于night-v2-audit，保留既有辅助表语义与历史回放。
- 探照灯改为端点直线、箭头、目标圈及预览虚线，短标签避免与炮击线长舰名重叠。夜战态势显示真实光学视程、雷达接触、雨区中心、已生效/未来计划照明、可见鱼雷位置/齐射/余程、最近命中/损伤、已应用夜战修正及D66值；值来自引擎上下文或已过滤正式事件，不在UI复制规则参数。
- 未来照明仅下发本方可见舰计划，19格虚线计划不会提前照亮光学掩码；雨区加七格斜纹与中心标记。空雨飑中心明确提示“这局将没有雨”，恢复默认清空，原局不补随机雨。发现并修正移动编辑器和回放漏传夜战/地形观察，保留逐格可达/当前/下一步高亮。
- 测试：140 passed / 1第三方弃用警告，范围test_night_feedback、night_v2、night_llm_memory、savegame_api、adaptive_torpedo_ai、torpedo_assist、savo_source_cards；生产TypeScript/Vite 56模块通过；git diff --check通过。新增策略测试使用合成接触，原典未接触开局不会强行开灯，不宣称AI强度或S04/S10完整对局通过。
- Playwright：1600×1000桌面、390×844手机；实际玩家副本显示5组可见鱼雷、T3两枚命中与零雨区；合成引擎夹具验证1条直线/0折线、雨区7格、实际照明19格、计划19格、取消灯光/计划、空中心/输入/恢复默认、回放夜色、移动编辑夜色与高亮。无JS错误/横向溢出；截图及ui-verification.json在artifacts/night-feedback-20261013。船体射界卡SHA256仍为c46d8ffffb2dbc4390d0c704204c04c70fd4885596da3b0770ac12c20f526638。
- 数据保护结果如实分开：games/events/ai_debug/battle_report/custom_scenarios/research_consent六表原始字节摘要不变，七表行数不变；snapshots整表摘要发生未归因变化（不能声称全库不变）。当前玩家GameState与隔离只读副本一致，最新326号快照与该状态一致，326事件新版回放完全一致。已记录player-preservation-detail.json及before/after摘要，不覆盖正式库或擅自修复未知快照差异。工作期间另有worldcup.py更新，不纳入本批修改或测试结论。
- 8000/5173服务已加载当前源码，health ready；8016隔离验收服务及浏览器关闭。Git基线4a7f5e24abfd269ee41e0c07f59fefb4843f79ce，本批未提交。


## 2026-10-13 AI舰队世界杯：32席正式二马实测与直播

本批已启动，赛事尚未完赛，无冠军结论。按用户修订纳入全部19种状态机（18种PROFILES+进化冠军），加13个模型，共32席、31场、单场淘汰、无轮空，固定抽签与阵营/骰种。使用项目现行IBS-S-EM-01「第二次马里亚纳海战」，24舰、12回合，真实指挥链与night-v2开启，可选规则默认关闭；未修改原舰艇、初设、计分或25分胜差。原页8回合与项目既有12回合扩展在赛制栏明确说明。

- 模型：GPT-6.1 Sol、GPT-6 Astra、GPT-6 Luna（已登录Codex CLI，禁用工具、隔离临时目录、medium）、DeepSeek V4 Pro、deepseek-flash（当前官方V4.1 Flash）、GLM-5.3与5.3 Flash（Coding Plan）、MiniMax-M3.1-Flash-Preview、本地Qwen2.5 7B Q3_K_M/32K、免费GLM-4.5 Flash、4.6V Flash、4.1V Thinking Flash、4 Flash 250414。请求/返回型号、路线、时延、用量和最终输出哈希独立留痕。glm-5.3系列使用官方支持的low设置；免费型号90秒超时，其余240秒。
- 本地Ollama已实际启动并加载成功；使用ASCII模型目录D:/OllamaData/models及便携0.33.3，避免中文路径底层加载故障。完整Q3原始GGUF保留；只清理本批生成且核验绝对路径的失败重复blob，未动用户其他模型。
- 当前接入：31/32有实际响应，29/32初设命令合法（含19状态机）。GLM-4.6V Flash返回HTTP429，保留席位并退避重试；GLM-4.1V Thinking Flash、4 Flash 250414实际有响应但预检命令非法，正式对局继续评估，页面显示此区别。网络/限流/引擎故障暂停，不用状态机代打；连续3次实际非法命令为独立标注的技术淘汰，不能作为战术胜利。未预造赛果。
- 赛事实际运行：http://127.0.0.1:8765/ 。两场已正常打完并回放一致：R32-2猥琐保守按赛事平局附加判定以18:17晋级；R32-7 T头猎手以31:27晋级（原引擎均判平局）。当前进行中：[('R32-6', 4, 'torpedo_planning', 12)]。大模型对局继续后台执行，直播可逐场选择、切换本方观察、展开已结算命令和下载终场记录。
- 冻结：artifacts/worldcup-erma-20261013/frozen/复制Python包、结构化规则及全部来源；406文件复制前/后/目标SHA256相等，运行后再次核验0差异。比赛只加载冻结包，避开其他聊天对实时工作区的改动。冻结清单、公开赛程、侧别直播、私有断点和赛后战报全部保存；旧worldcup-20261013同级驱逐舰试运行保留但不计正式成绩。
- 安全边界：密钥仅在仓库外当前用户私有配置，无密钥入库；不保存供应商reasoning字段、CLI推理/工具流或原始供应商错误体。保留最终公开简短决策说明和命令。直播本方观察/决策隔离；未完赛完整战报409、私有checkpoint路由404；未使用玩家数据库。
- 修复：Windows发布与读取短暂锁分别退避重试；YAML日期转换ISO字符串；统一提示orders.side/phase必填并反馈具体结构错误，不替模型选命令。实际失败调用计入调用/用量统计并可断点恢复。广播进程重启先恢复原进行中比赛，修复读取后错误日志0字节。
- 验证：冻结包test_worldcup.py 17 passed；test_erma_extension.py + test_night_llm_memory.py + test_llm_prompt.py 20 passed；读取锁回归追加1 passed。此前相关65项因二马YAML日期序列化出现2项失败，已定位修复并通过以上复测。JS语法检查通过。Playwright实际验证32席/31场、每侧12舰、终场46条本方决策、比分、侧别切换、命令/赛制展开和战报下载；桌面1600/1600、手机390/390无横溢出、浏览器错误0，截图已人工检查。来源二马原始2页已视觉核对。

证据：artifacts/worldcup-erma-20261013/{competition.json,freeze-manifest.json,roster-sources.json,qa-summary.json,dashboard-desktop.png,dashboard-mobile.png,matches/,preflight/}；scripts/start-worldcup.ps1可从冻结引擎恢复；scripts/freeze_worldcup.py禁止覆盖已开赛的冻结包。当前HEAD：4a7f5e24abfd269ee41e0c07f59fefb4843f79ce，本批未提交，保留其他已有未提交改动；无视频制作。


### 2026-10-13 世界杯输入模态澄清

按用户问询核对冻结代码与Astra当前本方命令：本轮所有大模型均只有文字棋盘、结构化战况、合法动作和同局记忆；vision_enabled默认False，Codex桥只转发文本，未发送图片。Astra第3至6回合多次明确沿用引擎安全建议，其中第3、4回合主力/巡洋队分向西南/东北；提示词有先照抄安全机动建议的指令，可能影响自主战术选择，但不能据此证明图片一定改善表现。已在直播引导及赛制栏明确标注纯文本配置；未中途变更冻结模型参数或重算赛果。

验证：JS语法检查通过，实际8765返回HTML包含纯文本/未发图说明；406个冻结文件SHA256再次全部一致。证据：artifacts/worldcup-erma-20261013/astra-input-audit.json（仅Astra已发布的本方决策）。HEAD：4a7f5e24abfd269ee41e0c07f59fefb4843f79ce；未提交。


## 2026-10-13 OpenCode免费模型接入与多模态世界杯重赛

按用户要求暂停旧纯文本赛事并保留全部存档。本批实际接通OpenCode：用户桌面版为1.18.33，禁用所有工具的自定义代理被免费档403拒绝；官方项目issue50081有同类现象。调用已安装官方桌面程序自带后端的标准build会话、采用文档session/message接口；每次使用独立临时数据/配置/缓存目录，只发送比赛资料，工具均需许可，由桥拒绝执行。真实工具验证出现1次拒绝、工具状态error、无completed工具；要求调用工具的探针没有最终文本，明确保留接入故障，不编造回答。运行后清理该独立数据库；不修改玩家OpenCode原有会话。没有伪造供应商身份或工具表。

- 免费模型：当前文档加实时目录15项，逐一核验。正式新增8个实际返回型号：Big Pickle、Ling3.1Flash、LongCat2.5Preview、MiMoV2.6Flash、Nemotron3.5Lightning、Nemotron3Ultra、SpaceBunny、Step5Preview。CatJam/Muse1.3返回403、Muse1.2/旧MiMo2.5本地接口500、Exo410、Ling3.0FlashFin400；Jev专用问题分类接口不适合舰队JSON生成，单列排除。保留分次探针与失败原因，未把未接通的型号冒充参赛。匿名HTTP/官方CLI禁工具路线失败不代表桌面免费型号不可用。
- 总阵容40席/39场/8场附加赛，保留全部19状态机及原13模型。仍使用IBS-S-EM-01「第二次马里亚纳海战」、24舰、项目12回合扩展、真实指挥链/night-v2；原舰艇、部署、计分和25分原引擎胜差未修改。新目录不继承旧成绩。
- 视觉：Sol/Astra/Luna、MiniMaxM3.1、GLM4.1V与新增LongCat/MiMo2.6/SpaceBunny/Step5共9个型号，通过仅图片含随机码识别。GLM4.6V仍429，标记未验证、保留等待。Codex以--image发送PNG，OpenCode以原生file parts发送；视觉参赛者缺图直接拒绝，禁止静默降级。实际二马Sol/Astra初设已带100046字节本方战局图，实际命令校验通过。
- 直播新增模型输入标记、每条已结算命令的实际图片数量/原图/SHA256。图片路由仅允许该侧已发布决策引用的哈希文件；未发布、另一侧、路径穿越均404。只渲染本方已知单位与同源结构化数据，公开最终简短说明、合法命令、时延/用量；不保留私有推理、供应商reasoning或工具原文。额外过滤只有闭合think标签的孤立推理前缀。
- 战术提示取消强制先照抄安全航迹及不得比较方案；统一自主战术、舰队协同和剧本胜利目标，合法参考仍保留，引擎继续校验。
- 冻结408文件复制前后SHA256相等；运行后0差异，桥mjs也计入源码哈希。OpenCodeASAR与model.dev目录另有固定SHA256，变化时暂停。旧只读直播PID/脚本/8765所有者核验后停止，新后台赛事同地址启动，未使用玩家数据库。
- 检查45项通过（worldcup、multimodal、night_llm_memory、erma_extension、llm_prompt），冻结赛事追加20项通过。最初共享.pytest-tmp拒绝访问，改用本批专用basetemp重跑；输入标记和孤立think过滤回归失败已修正后通过。Python/两段JS语法、git diff --check通过。实际Cua浏览器40席/39场、24舰/12回合/多模态标记正确，1070宽页面1055无横溢出、控制台错误0，截图已视觉检查。
- Edge指定控制台在重新连接后仍返回扩展fetch失败，未声称已读取该账号网页；官方文档确认API入口为Keys→AddServiceAccount→AddAPIKey，使用已有桌面后端完成接入，没有新建密钥、购买或充值。

当前赛事运行中，未宣称冠军、未制作视频。直播：http://127.0.0.1:8765/ 。证据：artifacts/worldcup-multimodal-20261013/{competition.json,freeze-manifest.json,roster-sources.json,entrants-extra.json,opencode-discovery.json,opencode-auth-reprobe.json,opencode-documented-reprobe.json,opencode-permission-verification.json,vision-verification.json,qa-summary.json,dashboard-restarted.jpg,preflight/,matches/}。基线HEAD：4a7f5e24abfd269ee41e0c07f59fefb4843f79ce，本批未提交，保留其他聊天未提交改动。

## 2026-10-13 夜战发现与识别分层、敌舰/光源算子

- 按agent.md及iron-bottom-sound-rules核验规则书PDF13的9.2–9.4。检索美国海军历史部门的ONI萨沃岛/瓜岛战斗叙事；历史支持发现与确认身份分离，但不能证明统一距离。IBS-R-NIGHT-ID选3格/1800码为用户授权、可调整、逐局冻结的补充参数，明确不是原典数值或现实保证。用户确认识别后完整舰名/舰型，最新修正要求雷达与目视未识别一律用“敌舰”，不使用“隐藏”。四向审计：docs/rules/night-identification-20261013.md。
- 引擎以近距、有效照明、光学视线及雨/陆地条件识别；雷达全图发现但不识别，原陆面4格/岛屿遮挡仍保留。连续跟踪保留已识别身份，失去接触后重新识别；已确认且曾识别的沉没舰保留战损身份。10张用户图片与规范来源SHA256相等，直接用原件；已识别舰优先对应国家/舰种算子，缺对应类型仍用原命名算子；光源用于直线探照灯和照明弹中心。
- 私有盐派生接触代号贯穿观察、合法目标、命令、炮击/鱼雷辅助、事件、记忆及模型输入，实际命令仅在引擎边界还原。未知舰不下发舰名/舰型/装甲/船体/VP/武器，未知舰型修正仅显示可见项估计，裁决仍使用完整规则。状态机未知能力不能影响移动/攻击选择；模型不进入可信状态机内部范围。事件记录发生时身份，后识别不反向揭露旧日志。Command Delay本地观察独立，旧优先级可以记忆但不能令当前非法目标可射。
- UI未识别记录、名册、敌舰点击区和说明接入；灯光预览保留识别说明/光源但不识别，取消仍匿名。高级JSON省略空数组不会崩溃；未公开鱼雷记录不显示成“无发射器”。探照灯仍为直线，不沿六角转弯；状态机保留同目标单灯协同，不改变玩家合法多灯规则。
- 验证：全量初跑（排除另一个工作批次的test_worldcup）927项中914通过/2跳过，11项失败定位后全部修复复测（命令延迟旧接触优先级、协同AI应急说明条数及改用公开目标代号的辅助接口期望）。相关批177项通过；新增识别/隐私/近距2/3/4格、雷达岸4/5格、雨/岛屿、照明、旧日志、AI未知能力不变性、模拟模型提示、保存/导入/回放、已识别与未知沉没统计及缺少接触信息拒绝导入，最终25项全部通过。CD失败项与新增规则联合复测25通过。保留各批日志，不累加成单次全量通过；模拟响应不冒充新的联网Luna验收。
- TypeScript/Vite生产构建56模块通过，git diff --check通过。Playwright真实按钮/JSON/交接：敌舰→单灯预览→取消仍敌舰→双方封存/执行→标枪/DD，同一接触代号；预览2直线/0折线、光源图片；桌面1440×1000和手机390×844均无横向溢出、JS错误0，手机舰队/海图/命令切换通过。截图、ui-result.json及viewport-fit.json在artifacts/night-identification-20261013/。
- 玩家保护：全部QA在隔离库8017；正式玩家库七表原始字节摘要与开工前完全一致（4672局/67806事件/21183快照，其余表也未变）。实际S06玩家68116b66-159e-480f-8334-27ab1da00423仍T4增援/326事件、night_recognition=False，整状态确定性回放相等。新API夜战局默认开启，旧存档缺开关则保留旧知识规则，旧事件target_id元数据也保持原版本。既有想定阻断不擅自解除，未重写原始来源。
- 8017隔离服务及本批浏览器已关闭；正式8000/5173保留，health为ready且loaded/source一致（service-health.json）。来源/资产/数据库哈希证据已保存。当前Git HEAD 4a7f5e24abfd269ee41e0c07f59fefb4843f79ce，本批未提交，其他批次已有变更保留。

补充实战验收：P5已在Sol同盟视角发布实际图片收据，真实PNG下载SHA256匹配；另一侧同名图片404，仍未公布的当前秘密阶段图片404。浏览器展开原图/哈希入口后截图保存为dashboard-sol-image-proof.jpg，哈希换行修复后决策栏clientWidth/scrollWidth均257。该UI修改不影响冻结引擎，未增加规则或模型调用。当前{"at": "2026-10-13 23:34:13", "ready": 36, "failed": ["glm_46v_free"], "running": [["P5", 3, "torpedo_planning"]], "finished": 3}。

## 2026-10-13 OpenCode Go零额度通道与战局图验收

用户明确只加入不消耗Go额度的免费型号。再次核对官方Go用量表：https://opencode.ai/v2/docs/console/go/ 。LongCat2.5PreviewFree、Step5PreviewFree标为Free/Unlimited（限时），其余Go套餐型号不能据订阅可用便视为免费。本批只对这两个型号发送Go请求，没有发送任何Go收费型号探针，没有充值或开启按量回退。SpaceBunnyFree保持既有公共免费入口，避免误用Go计费SpaceBunny。

- 桥使用已安装官方桌面后端的原生opencode-go提供商，从仓库外本机auth读取认证；独立临时数据目录，不修改用户会话。Python与mjs双重允许名单，Go收费型号在读取凭据、创建运行时或调用网络之前拒绝；辅助small_model也绑定同一免费型号，避免后台转用收费型号。原默认公共免费路线保持不变。
- 两款都通过图片随机码识别；随后独立加载正式赛事的冻结引擎/规则，在IBS-S-EM-01真实指挥模式初设发送100046字节本方战局PNG（SHA256：82a4847aab9b45a80152d24b7c185f0acf297d14196899bdd45b1fb5f7dedcca）。实际Go返回精确型号、请求ID和三编队命令，均经引擎验证合法；LongCat82.476秒、Step558.326秒。仅保存最终简短决策/订单和图片收据，验收不计正式成绩。
- 两款已经在40席阵容中，保留原席位，不按渠道重复登记。正式冻结赛程仍走原公共免费通道，未中途改接Go、重抽签或继承旧纯文本成绩；其本方战局图输入已启用、视觉已验证、状态就绪。23:51:08直播40席/39场，3场结束，P5 Sol对切割专家正在第6回合鱼雷规划；408个冻结文件SHA256再次0差异。
- 工作区孤立think前缀过滤误回退被回归检查发现并恢复，运行中的冻版原本已正确，不受影响。5项相关回归全部通过，覆盖收费拦截/免费认证隔离/图像转发/私有推理过滤/阵容模态；mjs语法及git diff --check通过。只声明本批相关检查，没有重新声明全量引擎测试。

证据：artifacts/worldcup-go-audit-20261013/{models-catalogue.json,go-free-verification.json,go-battle-verification.json,longcat-2.5-preview-free-battle-verification.json,step-5-preview-free-battle-verification.json,battle-inputs/,live-and-freeze-verification.json,qa-summary.json}。直播：http://127.0.0.1:8765/ 。HEAD：4a7f5e24abfd269ee41e0c07f59fefb4843f79ce，本批未提交，其他聊天改动保留；赛事继续运行，未宣称冠军，未制作视频。

## 2026-10-14 多模态世界杯恢复续赛

用户要求继续。检查时旧PID48404已不存在，8765与11434均未监听；比赛存档仍为40席/39场、3场结束，P5切割专家（轴心）对GPT-6.1Sol（同盟）保存于第8回合移动规划、54条已接受决策，未从空局重开。408冻结文件、OpenCode1.18.33 ASAR及模型目录SHA256均与赛前记录一致。

使用既有scripts/start-worldcup.ps1隐藏启动Ollama和冻结赛事，比赛新PID44860。Ollama列出原ibs-qwen2.5-7b-q3-32k:latest；直播首页/状态/本方战局图均HTTP成功。11:07:37（北京时间）同一game_id 3aec6404-e8d9-46a0-9b19-93012342e670决策54→56、移动规划→鱼雷规划，确认后台实际推进。前54条决策摘要与恢复基线一致，原3场winner/reason/replay_equal等结果完全保留。Sol已发布图像下载SHA256匹配（34b933a01045259a1a5ccdd477b62fd2613a9a0e808b8d2a89024da081523450），没有改为纯文本。runner错误日志为空。

本批只恢复服务及记录审计，没有改引擎/规则/模型/阵容或旧赛果，沿用公共免费通道及Go零额度限制；未增加Go收费请求，未修改玩家数据库。相关检查采用冻结哈希、实际HTTP与决策推进/前缀保留校验，无源码变更故未重复运行全量测试。Codex打开直播请求返回queued，不声称已完成浏览器UI验收。

证据：artifacts/worldcup-resume-20261014/{before.json,after.json,live-input.json}。直播：http://127.0.0.1:8765/ 。HEAD：4a7f5e24abfd269ee41e0c07f59fefb4843f79ce；本批未提交，其他聊天改动保留。赛事继续运行，未完成39场、未宣称冠军，未制作视频。

## 2026-10-14 夜战更新提交GitHub、Git树维护与线上部署

用户授权提交GitHub、维护Git树并更新服务器。功能提交 **2befb473346ab595ef78a7a5b9b80f4c8a786837**（60文件、4401新增/198删除）已推送 `origin/glm/rtt-port`；此前4a7f5e2检查点一并保留。射界图分支 `codex/phase1-engine` 的两项本地提交同步到远端e38557a77d775ec087a9b8889cd359b9ba1479a9，未重写历史或强推，main仍保留原状态。

- 发布范围：夜战版本快照、发现/识别与敌舰/光源算子、直线探照灯、照明协同AI、同局阵营私有记忆及公开决策调试、萨沃舰卡与历史补充、旧存档兼容和射界图恢复。并行世界杯的9个实验文件未纳入发布；其运行冻结包不改。`tmp/command-delay` 工作树的6项未提交修改及本地分支保留（其远端后来有26个新提交），不在脏工作树中强行拉取或删除。fetch/prune及worktree prune完成，没有过期工作树引用；Git连通性检查通过，悬空恢复对象保留。
- 验证：931个非世界杯节点；首批因会话中断停在576节点，记录574通过/2跳过；按同一集合续跑剩余355节点并交叉复跑1节点，356 passed / 437.56s，去重为 **929 passed / 2 skipped**，不是单次完整pytest进程的结果。来源、引擎、识别隐私、API、记忆、存档与确定性回放均在隔离库运行。TypeScript/Vite生产构建56模块通过，base=/tiedi/；最终差异与拟提交文本密钥扫描通过。沿用上一批实际桌面/手机夜战交互证据，本次未增加联网LLM调用。
- 部署包由Git功能提交制作，449文件、92,759,528字节，SHA256 `da4185b2a0580ee81c99ccaab5d435aebbb6e77d1621523eab07d865d7e715d6`，不含数据库、战报、依赖目录、凭据或世界杯实验。现有素材在历史Git对象中为原始二进制，包内0个待还原LFS指针；本批未新增或改写二进制来源，未迁移历史过滤格式。上传后逐文件检查，隔离导入/夜战建局/6个既有存档格式预检通过；原服务器Python3.11.13依赖和环境文件保留。
- 线上 `/opt/tiedi` 的 `tiedi.service` 已更新为该功能提交，PID3175596，状态active/ready。后端loaded/source及部署包摘要同为 `b8ee6a0bd93a2ed256849bfcf21361f08f8038e1beda15b59f120ab1b3f50f58`；部署后449个文件再次核验0差异。根目录保存release-manifest.json与deployment-result.json，仅含版本、文件摘要和行数摘要。
- 数据保护：停服时253局、26,676事件、5,049快照、7,817战报、242科研同意、4自定义剧本；SQLite完整性ok。SQLite Backup API一致性备份及逐表原始字节摘要核验通过，备份位于 `/opt/tiedi/backups/pre-night-2befb473346a-20261014-111522/iron-bottom-sound.sqlite3`，旧运行目录存于同目录code/。重启后原六表行数及字节摘要完全一致，仅新增0行ai_debug表；没有以本机库覆盖线上库，不删除战报，不修改密钥文件。发布前的只读在线采样为248局，后续玩家活动增加到253局，所以保护结论以停服备份时的基线为准。
- 公网验证：`https://fuwenji.asia/tiedi/`、新JS/CSS、20想定及全部10张用户算子均HTTP200；每张PNG与本地原件SHA256一致。最早与最近各2个旧局的双方视图8次GET全部200并保留legacy-v1；远程私有调试403，公共首页586字节SHA256保持 `d4dd28a2ca2e046108ee1fd53cd00a185fb6dccf982eb8bb20fd28a2fd5122e5`，没有修改nginx或首页作品集。未向线上创建测试局或提交测试订单。
- 本地正式库仅作只读摘要采样；两次采样之间games数量4675不变、事件/战报等存在活动变化，未把这一段宣称为全库不变，也没有回写修复。测试显式指定独立IBS_DB_PATH/报告目录且每项API夹具隔离。线上与本地保护证据分开，不混用两台机器的行数。
- 范围限度：新版新局生效，原局规则快照及识别开关保留。IBS-Q-024/025原典地形/部署仍开放，3格识别仍是用户授权的历史补充参数；以前Luna有限实测不等于整局或公共HTTP API模型验收。源码发布没有改变这些结论。

证据：`artifacts/publish-20261013/{pytest-all.log,pytest-collection.log,pytest-resume.json,pytest-resume.log,release.json,remote-before.json,remote-deployment.json,remote-verification.json,public-before.json,public-after.json,db-before.json,db-after-tests.json}`；发布开始于10月13日、完成于10月14日，目录名保留原批次日期。部署说明已更新到deploy/README.md。


## 2026-10-21 Greg Courter共同8段时钟及状态机集成
原规则PDF14页已目视核验，用户裁定3速2/5/8段、途中发射按发射区间后的剩余时间。结构化movement-impulses.yaml/IBS-R-06-GC8成为共同时间表；舰船/隐蔽标记/鱼雷同步、同格与对穿接触、最后射程及接触航向/速度快照、炮击后鱼雷损伤和旧日志双版本回放已接入。战术AI/真实编队解冲突、可见雷同段避让、自适应压制与拦截共用时间表，不读敌方封存计划。以服务器逐文件匹配的1c02581为集成基线，保留night-v2快照/识别/编队与性能缓存，不覆盖为旧main。当前集成核心268项通过（E:/AI舰队世界杯/gc8-live-core.xml），包含原规则、边界、旧日志、夜战/识别/存档和真实模式整局回放；全状态机/API补充回归及线上部署继续，不将本条冒称已部署。主工作区原131项核心与28项新增边界通过。基线HEAD 1c02581126633cec971bcdf47e6d6576e3bba7a5。

## 2026-10-13：舰船记录表炮位射界图（提交 `92ced8c`）

- **改动**：舰船记录表里平铺一条的炮位横排（旧 `.mount-line`）改为舰艏朝上的船体射界图——艏炮在上、艉炮在下、左舷/右舷分列两侧（超过 3 座自动折成两列）、舯部炮位居中，复刻原版舰卡的炮位布局。每个炮位 token 顶部以 ↑艏 ←左舷 →右舷 ↓艉 四向箭头按 `arcs` 点亮射界，并保留可用/已射击/摧毁状态、口径/装甲文本、悬停说明与图例；图下附一行射界读法提示。`position` 缺失时按 `arcs` 推断分组（数据侧 `MountPosition` 枚举始终有效，仅防御）。
- **边界**：纯前端显示改动（`ShipStatusCard.tsx` + `style.css`），不改规则、数值、API、引擎与炮击计划表的炮位勾选列表。
- **验证**：`npx tsc -b` 0 错误；`npx vite build` 通过（50 modules）。真实浏览器打开本地局（IBS-S-EM-01 炮击阶段）：大和极端案例（2 前主炮 + 1 前副炮 + 左右舷各 6 座高炮 + 1 艉主炮 + 1 艉副炮，共 16 炮位）桌面 1280×720 与吾妻（左右舷副炮各 3 座）布局与箭头均正确；手机竖屏 390×844 完整放下且无横向溢出（`aside 375/375`、`.ship-diagram 318/318`、`.mount-diagram 302/302`）。


## 2026-10-21 最新主线统一及发布前验收
用户追加要求本地/线上/GitHub保持最新，已汇合已发布night-v2/识别/真实编队/指挥延迟主干与炮位图分支，保留新版装甲显示。8段修复提交788a9e3，合并e673ab3；旧RTT导入的241张图片按既有gitattributes规范化为LFS指针（5e349da，素材像素字节不改）。主工作目录main已快进到该树，原视频/赛事文档未提交改动通过哈希备份后按原插入块保留，其他分支/独立成果不重置。
线上基线集成268核心+107战术/真实编队/指挥延迟/API共375项全部通过，0失败/跳过；E:/AI舰队世界杯/gc8-live-core.xml、gc8-live-ai.xml。涵盖源表九行、途中发射、静止/同格/对穿/尾随/最后射程/接触快照及隐私、新旧存档/回放、夜战与各profile整局。旧main另131核心+100AI整局及28新边界通过，证据artifacts/gc8-20261021。前端npm生产构建/TypeScript通过（/tiedi/）。部署仍在进行：检测服务器磁盘已满，先仅清理可再生npm/pip缓存，保留3GB数据库、战报及备份，再核验Git源码与逐文件SHA；本条不冒称已部署。
