# 已完成工作

本文件只追加完成记录；每次发布前补充对应提交哈希。

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
