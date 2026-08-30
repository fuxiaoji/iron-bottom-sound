# 阶段 1 实施计划

## 当前批次：多模态 LLM 可见地图接入（2026-08-27）

状态：实现与离线验收完成；真实供应商调用待运行时授权

目标与边界：

1. 将 LLM 对手配置从固定 DeepSeek 解耦为请求级 `provider / endpoint / model / api_key`；玩家在首页手动选择供应商与模型，密钥只保存在浏览器当前内存和后端进程内存，不进入游戏状态、SQLite、战报、事件或日志。
2. 每个需要 LLM 下令的阶段，把该 LLM 阵营的 `PlayerObservation`、合法行动、Schema、文字棋盘以及由同一观察服务端渲染的 PNG 地图一并发送；禁止使用浏览器全屏截图，避免秘密计划、调试态或另一方观察泄漏。
3. 通用 OpenAI-compatible 适配器支持纯文本与 `image_url` 混合内容；不同供应商的可选字段由能力配置控制，不能把 DeepSeek 专属 `thinking` 参数强塞给其他端点。
4. 首个预设为智谱 BigModel。按用户指定尝试 `GLM-5.3-Flash`，但模型名及视觉能力须以端点实测为准；不静默改成其他模型。官方当前多模态示例使用 `glm-5v-turbo`，UI 同时提供可编辑模型名。
5. 增加脱敏连通性端点：仅返回模型名、是否支持图像、延迟、请求 ID 与错误摘要，绝不回显密钥、Authorization、完整请求或模型私有推理。

验收：模拟客户端断言图像为 `data:image/png;base64`、图像像素只来自阵营过滤观察；轴心/同盟输入图不同且隐藏敌舰不进入图像；API 与 UI 可手选模型；既有 DeepSeek 路径保持兼容；前端构建与相关 Python 测试通过。真实测试只允许密钥经运行时内存注入，测试工件及 Git 全仓扫描不得出现密钥。

批次结果：后端新增 `deepseek/zhipu` 两个供应商预设与手填模型 ID，智谱走官方 `https://open.bigmodel.cn/api/paas/v4`；多模态命令把阵营过滤的世界态、合法动作和服务端 PNG 放入同一 OpenAI-compatible 消息，智谱路径不发送 DeepSeek 专属 thinking 字段。首页已提供供应商、模型、密钥和“发送可见地图”控件，浏览器实测切换供应商会在 `glm-5.3-flash` / `deepseek-v4-flash` 间更新默认值。LLM/战报相关 `61 passed`，TypeScript 与 Vite 生产构建通过。全量套件仅有用户并行“二马”扩展引入的旧断言失败（记录数从 30 增到 54），与本批次无关且未回退。真实密钥未写入命令、文件或浏览器，真实 `glm-5.3-flash` 调用仍需在发送密钥与阵营地图前取得即时确认。

更新时间：2026-08-24

## 当前执行批次：P3 确定性原版规则引擎

状态：已完成。二马默认部署已整理为六支长纵队；状态机 AI 已加入整批逐脉冲去冲突、编队共同机动、边缘净空和一步回溯；鱼雷辅助已标注并过滤友舰航路风险；6.1.8 世界平移已改为完整预检后的原子操作。

本批次目标：

1. 将订单拆为增援、移动、鱼雷、炮击、照明、探照灯、烟幕和阶段确认，双方逐阶段独立提交、验证和封存。
2. 以 MF 脉冲同步执行移动和鱼雷，精确处理转向、加减速、碰撞回溯、船骸、地图边缘和地形阻挡。
3. 用逐炮位状态执行射界、GF、同时炮击、穿甲、特殊损伤、火灾、故障、雷达/MFC、沉没漂移和 VP。
4. 完整执行 9.1–9.10，每项均产生 `rule_id`、来源页、修正明细和启用/关闭事件证据。
5. 实现想定 1 的首回合、日军开火/鱼雷限制、增援和 VP，以及想定 3 的分级胜负条件。
6. `replay(event_log)` 必须从创建事件重建，不依赖内存中的初态副本或数据库快照。

本批次来源范围：规则手册 PDF 6–14 页；玩家辅助表 1–4 页；舰船记录手册 2–5 页；想定手册 1、3 页；P2 已核验 YAML/CSV。

本批次验收：规则示例和边界金标通过；相同种子/命令产生字节等价事件流；事件回放状态一致；十项可选规则关闭、开启及组合分支均通过。禁止为让对局继续而静默修复非法命令或直接修改状态。

| 里程碑 | 状态 | 验收门槛 |
|---|---|---|
| M0 治理、资料、规则技能 | 进行中 | 原始资料去重导入；来源清单、RAG、技能校验通过；扫描页 OCR 补齐 |
| M1 结构化数据 | 进行中 | 14 个想定入库；想定 1/3 可加载；规则审计可查询 |
| M2 确定性引擎 | 进行中 | 七阶段、命令事件、回放和核心裁决测试通过 |
| M3 API、UI、热座 | 进行中 | 双方秘密计划不泄漏；地图和计划界面可操作 |
| M4 两想定验收 | 进行中 | 想定 3、1 均可运行到自动胜负 |
| M5 LLM | 进行中 | 假模型与 OpenAI 兼容适配器只提交合法命令 |
| M6 审计发布 | 待办 | 审计、测试、文档和本地标签完成 |

## 当前下一步

1. 依据分支覆盖报告补齐阶段验证拒绝、增援边界、碰撞回溯、鱼雷多目标/再装填和特殊损伤全部 D66 效果测试。
2. 完成火控、雷达、舰桥、舵损伤持续期与装甲恰好穿透组合金标；消除 `IBS-T-SPECIAL` 的 `partial` 状态。
3. 为 9.1–9.10 建立统一的关闭、开启、两两关键组合参数化测试，重点验证隐藏观察和秘密事件不泄漏。
4. 将规则核心与总覆盖率提升到发布门槛后进入 P4 API/UI/SQLite 文件持久化；禁止用排除文件的方式虚增覆盖率。

## 紧急可玩链路批次：P4/P5 纵向闭环

状态：进行中（不得据此宣称 P3 或阶段 1 已完成）

目标：在继续补 P3 覆盖的同时，优先消除“无法从 UI/LLM 完整推进想定”的集成阻断；所有裁决仍只由规则引擎完成。

1. `legal_actions` 返回当前阵营、当前阶段可直接验证的订单 JSON Schema、己方可用单位/炮位/发射器和必要枚举，不包含敌方秘密计划。
2. 新增完全隔离的 `LLMPlayerSession`、`AIPlanSheet`、`LLMCallAudit`、`MatchReport`；每阶段一张私有计划书，不保存思维链。
3. 新增相位感知确定性假模型和自动比赛运行器；先要求想定 1/3 无人工改状态、无回退地跑到引擎胜负。
4. 热座 UI 在增援、移动、鱼雷、炮击各阶段均能提交订单和交接；在专用编辑器完成前提供严格 Schema 校验的 JSON 订单编辑器作为完整功能入口。
5. DeepSeek 只从新的 `DEEPSEEK_API_KEY` 环境变量读取；已公开密钥禁止写入文件或调用。完成离线 E2E 后再执行脱敏连通性、双方单阶段、两想定完整对局三级验收。

本批次测试：双会话上下文隔离、请求上限、非法 JSON 两次重试、正式模式零回退、秘密计划不进入公共观察/API/WebSocket/观战视图、两想定自动终局、前端构建与浏览器热座流程。

### 2026-08-23 批次结果

- P4 可玩纵向链路完成：全阶段热座订单、服务端推荐合法起始订单、交接清屏、SQLite 文件持久化、一键启动与前端生产构建通过。
- P5 离线门禁完成：想定 1/3 在默认规则及 9.1–9.10 全开四种组合下，两个隔离确定性会话均无回退、无人工状态修改运行至引擎终局。
- 当前自动测试 `100 passed`，总覆盖率 `90%`；规则引擎 `87%`，尚未满足关键状态机/隐藏信息分支 100% 的发布门槛。
- 真实 DeepSeek 三级验收仍待新的、未公开 `DEEPSEEK_API_KEY`；旧公开密钥禁止写入与调用。
- 应用内浏览器安全策略禁止回环地址交互；本地 API/UI 端口已分别验证 HTTP 200，UI 点击验收需在用户本机浏览器或后续允许 localhost 的测试环境完成。

## UI 可玩性修正批次：六角布局与玩家计划表

状态：已提交并完成稳定服务验证

来源与约束：`IBS-M-MAIN`（`resources/originals/assets/images/铁底湾-地图.jpg`，6961×6689）经原图回看确认采用 `flat_top_odd_q`，奇数列相对偶数列下移半个六角高度；UI 坐标必须与后端 `HexCoord` 的轴向/显示行换算一致，不改变规则核心坐标。

1. 修复 SVG 六角中心公式，确保 A/C/E 与 B/D/F 两组列交错，舰船算子与格心使用同一投影函数。
2. 新增坐标标签及前端投影断言，覆盖 A1、B1、A27、HH27 与奇偶列半格差。
3. 将秘密订单 JSON 改为玩家可编辑计划表：按阶段显示己方单位、移动计划、增援、隐蔽接触、鱼雷和炮击行；每次编辑同步生成同一个 `OrderBatch`。
4. 高级 JSON 折叠保留，用于审计和特殊命令；提交仍由后端规则引擎验证，前端不复制裁决常量。

验收：前端生产构建、Python 全量测试、浏览器中奇偶列视觉核对、计划表编辑后订单 JSON 同步及双方交接流程通过。

批次结果：原图与结构化元数据统一修正为 `flat_top_odd_q`；浏览器实测 A1=`(38,35)`、B1=`(74,55.7846)`、C1=`(110,35)`，奇数列下移 `20.7846px`、偶数列误差为 0。增援与移动阶段已显示指挥意图、逐舰计划字段和折叠高级 JSON，双方交接可推进至移动计划。己方观察新增最大速度、炮位与鱼雷发射器，敌方对应字段保持空值并有泄漏测试。`101 passed`，前端生产构建通过。

## 教学关与舰船状态批次

状态：实现与自动验收完成，待用户浏览器体验反馈

规则范围：复用 `IBS-S-03` 想定和正式七阶段引擎；教学关不得使用另写的简化裁决。教官方只能通过 `DeterministicCommander → submit_orders` 提交合法命令，不直接修改状态。来源为想定手册 PDF 第 3 页、规则手册第 6–12 页、想定 3 逐舰记录和 `IBS-M-MAIN`。

1. 首页增加“教学关”，玩家固定控制德方三艘驱逐舰，教官自动控制英方；不显示交接锁屏。
2. 右侧教学卡按阶段解释目标、操作、规则要点和完成条件，引导至少走完增援确认、移动、鱼雷、同步移动、炮击和回合结束。
3. 右侧新增舰船状态表：使用原始棋子图片，显示舰体、当前/最大速度、火灾、炮位 GF/口径/损坏和鱼雷发射器装填/备雷。
4. 地图使用 `resources/originals/assets/images/` 的规范棋子副本；已抽查卡尔加尔斯特，和 `D:\desktop\铁底湾\images` SHA-256 完全一致。素材由后端只读静态路由提供，不复制规则数据。
5. 地图点击舰船即选中状态表；教学提示可聚焦计划字段。普通热座模式保持不变。

验收：教官端点仅限 tutorial 模式、敌方私密订单不返回；教程从开局推进到至少第二回合；棋子素材加载；状态表与引擎观察一致；全量 Python 测试和前端生产构建通过。

批次结果：新增正式想定 3 教学入口、六阶段教学卡、仅通过合法命令行动的教官端点、地图原版棋子和右侧逐舰状态表。教程 API 自动走到第二回合；静态素材与原始卡尔加尔斯特棋子 SHA-256 一致。`103 passed`，TypeScript 检查和 Vite 生产构建通过；本地前后端及棋子静态路由均返回 HTTP 200。应用内浏览器安全策略仍禁止自动操作回环地址，因此保留用户侧交互体验反馈作为下一轮 UI 调整输入。

## 教学交互与船表可视化修正批次

状态：实现与自动验收完成，待用户视觉反馈

来源与边界：继续使用 `IBS-R-06` 移动/转向规则和想定 3 已核验逐舰记录；本批次只修正显示投影与教学交互，不在前端新增或猜测裁决常量。平顶六角的六个合法邻格方向必须穿过边中心，原版棋子长轴与航向指示统一偏转 30°。

1. 将地图棋子旋转封装为可断言的航向投影，六个舰首方向指向六角边而非顶点，并增加可见舰首标记。
2. 将舰船状态表改为仿原版船表的记录带：舰体格、航速格、舰体轮廓、沿舰位排列的炮位、射界徽标、鱼雷装填与损坏状态；全部数值仅来自 `PlayerObservation`。
3. 教学关在计划表内提供逐字段编号说明、示例填充、跳过可选鱼雷提示和提交前检查清单；把后端验证错误翻译为可操作的中文提示，保留原始错误供审计。
4. 验收：航向 1–6 相邻方向几何断言；教程移动示例生成合法订单；鱼雷发射时点错误能明确提示；敌方隐藏数据仍为空；全量 Python、TypeScript 与生产构建通过。

批次结果：原版横向棋子由顶点方向整体修正为平顶六角边中心方向，并叠加金色舰首箭头；六个航向的 30° 偏转加入运行时几何断言。舰船状态改为图形化记录带，显示舰体/航速方格、舰体轮廓上的炮位、射界、鱼雷装填和三态图例。教学计划表加入逐字段编号、一键移动示例、空鱼雷计划合法提示和针对“发射 MF 超过航路”的中文纠错。`103 passed`，TypeScript 与 Vite 生产构建通过，本地开发服务已确认加载新版三个组件。

## 航向罗盘与速度语义纠错批次

状态：实现与自动验收完成，待用户视觉复核

来源核验：主地图 `IBS-M-MAIN` 左下角原生罗盘逐向视觉核验为 `1=右上、2=右下、3=下、4=左下、5=左上、6=上`；规则书 PDF 第 7 页 `IBS-R-06` 逐段回看确认速度数字是本回合最大 MF，非 BB/BC 可较上回合少消耗最多 5 MF，且第 8 页允许以计划 `0` 停船。

1. 将 `HexCoord.neighbor()` 的航向 1–6 修正为地图罗盘定义；同步鱼雷、射界、碰撞、漂移和世界平移等所有复用邻格函数的规则路径。
2. 原版棋子自身左侧白箭头代表舰首；UI 旋转必须使该箭头与引擎邻格向量一致，移除方向相反的叠加提示。
3. `PlayerObservation` 增加由规则核心计算的本回合最小/最大合法 MF；状态表和计划表分别标明“上回合实际速度”“速度循环上限”“本回合合法消耗”，禁止 UI 重算加减速常量。
4. 教学示例不再用含混的 `1/0` 指令，逐舰填写合法范围内的明确示例并解释“最大值不是强制值”；航向 4 从 O14 直航 1 格的金标必须为 N14。
5. 验收：地图六向金标、显示旋转与坐标向量一致、0 MF 的 DD 合法而 BB/BC 越界减速被拒、回放确定性及两想定自动终局复验。

批次结果：修正领域模型和世界平移中的航向表，统一为主地图印刷罗盘；航向 4 的 O14 直航金标由错误 O15 改为 N14。原版棋子左侧白箭头与金色舰首标记现共同指向引擎前进方向。观察接口由规则核心提供 `min_legal_speed/max_legal_speed`，界面明确区分上回合实际 MF、速度循环上限和本回合合法消耗。规则页视觉核验确认 DD 从 5 MF 可合法减至 0，BB/BC 只能最多减 3 MF。`105 passed`，TypeScript 和 Vite 生产构建通过，重启后真实 API 返回想定 3 德舰合法范围 `0–6 MF`。

## 教学接触保持与能见度解释批次

状态：实现与自动验收完成，待用户视觉复核

来源：想定 3 原页 `IBS-S-03` 明定双方能见度均为 4 格；敌舰超出光学视距后必须由阵营观察过滤，不能为教学便利破坏战争迷雾。

1. 教学移动示例改为保持接触的合法 `1/0/0` 航路，不再把三艘德舰全速带离英舰 4 格视距。
2. `PlayerObservation` 公布本方当前能见度数值；教学地图用淡色范围格显示至少一艘己舰可观察的区域，数值仍由引擎/想定提供。
3. 炮击教学在没有可见敌舰时明确说明“敌舰未被删除，而是超出能见度”，禁止生成无目标齐射。
4. 验收：保持接触示例结算后至少一艘英舰仍在德方观察；全速脱离后英舰字段不泄漏；前后端测试和生产构建通过。

批次结果：确认截图中的英舰未被删除，而是教学全速航路使德舰驶出想定 3 的 4 格视距。示例修正为卡尔 1 MF、其余 0 MF，正式引擎结算至炮击阶段后仍存在可见英舰。观察接口新增想定能见度，教学地图以淡色六角显示己方光学覆盖；无敌舰可见时显示战争迷雾解释。`106 passed`，TypeScript 和 Vite 构建通过；规则服务重启后真实 API 返回 `visibility=4`。

## 教学逐舰齐射编排批次

状态：实现与自动验收完成，待用户浏览器视觉复核

来源与边界：规则手册炮击阶段 `IBS-R-05` 与炮击程序 `IBS-R-08.1` 要求符合条件的舰船分别指定目标和炮位，炮击效果同时生效。前端只能帮助玩家为每艘己舰编写订单，不得自行复制射界、视线或命中裁决；最终合法性仍由规则引擎逐炮位验证。

1. 将单一“添加齐射”改为逐舰炮击名册，三艘德舰分别显示已安排、无可见目标、无可用炮位或可安排状态。
2. 每艘舰可独立添加/删除齐射、选择主目标和勾选炮位；禁止重复添加同一舰船，并提供“安排全部可射舰”快捷操作。
3. 教学说明明确要求逐舰填表，并解释“同时结算”不等于只有一艘舰能开火；射界不合法时显示可操作的中文纠错。
4. 验收：TypeScript、生产构建、全量 Python 测试通过；开发服务实际源码包含逐舰炮击名册，现有卡尔订单之外可继续添加另外两舰。

批次结果：规则书第 6 页和第 9 页原图复核确认“所有炮击同时进行”且各炮位目标由玩家决定。炮击计划改为逐舰名册，既可分别为每舰添加齐射，也可一键为全部有可用炮位的舰建单；已有卡尔订单时，里夏德和汉斯仍各自显示可添加按钮。重复舰船订单被 UI 阻止，射界继续由引擎逐炮位裁决并提供中文纠错。`106 passed`，TypeScript 和 Vite 生产构建通过，开发服务返回新版逐舰界面源码。

## 全模式回合结算战报批次

状态：实现与自动验收完成，待用户浏览器视觉复核

范围与边界：这是热座、人类对 LLM、双 LLM 观战及教学关共用的游戏 UI，不是教学专属功能。战报只能读取当前阵营经过战争迷雾过滤的引擎事件；不得展示另一方秘密订单、隐藏损伤或私有计划书。规则来源沿用 `IBS-R-05` 七阶段流程、`IBS-R-08.1` 炮击/火灾和 `IBS-R-08.2` 鱼雷事件。

1. 在起火与回合结束裁决完成后自动弹出上一回合完整战报，并在顶栏保留“查看战报”入口。
2. 战报按移动与接触、炮击、鱼雷、损伤/火灾/沉没、回合结果分组；每条显示引擎原文、骰子、调整值、规则编号和来源页。
3. 摘要显示可公开的命中、鱼雷效果、火灾检定、沉没数量、双方分数和胜负；不从 UI 复算命中或损伤。
4. 通过阵营化 `/events` 接口拉取该回合完整事件，忽略未过滤的推进响应；新增信息泄漏边界测试，并验证弹窗键盘/遮罩关闭和移动端布局。
5. 验收：全量 Python、TypeScript、Vite 生产构建通过；开发服务包含通用战报组件，教学与普通模式均走同一触发路径。

批次结果：新增全模式共用的回合结算战报。起火与回合结束裁决后自动弹出，并可从顶栏再次打开；按航行/碰撞、炮击、鱼雷、损伤/火灾/沉没和胜负分组展示引擎消息、骰子修正、规则编号与来源页，同时汇总齐射、命中、鱼雷效果、火灾检定、沉没和公开 VP。推进 API 现强制阵营头并过滤返回事件，前端另从阵营化 `/events` 获取完整本回合记录；热座交接会销毁战报缓存。`106 passed`，TypeScript 与 Vite 37 模块生产构建通过，更新后的后端和开发前端均已启动。

## 合法武器筛选与 UI 完整对局批次

状态：实现并完成实际浏览器全局验收

来源与边界：规则书第 9–12 页 `IBS-R-08.1/08.2` 和逐舰记录的炮位/鱼雷射界。UI 不复制射界算法，只消费引擎 `legal_actions` 返回的当前阶段候选；候选必须按阵营观察过滤。

1. 炮击合法行动细化到“舰船—可见目标—可用炮位”；添加齐射和更换目标时自动只勾选能指向该目标的炮位，不合法炮位禁用并解释原因。
2. 鱼雷合法行动细化到逐舰、逐发射器、合法舷侧/发射角、速度设定和按已封存移动计划计算的发射 MF/格；UI 建立逐舰鱼雷名册，允许多舰、多发射器分别建单。
3. 合法行动与最终 `validate_orders` 共用引擎方法；增加能见度、炮位射界、发射器重复、零 MF 航路和多舰鱼雷边界测试。
4. 使用实际浏览器 UI 从想定 3 教学开局完整操作至引擎胜负；不得通过高级 JSON、数据库或直接状态修改绕过 UI。每个阻断必须修复后重跑。
5. 复验想定 1/3 自动终局、战争迷雾、全量 Python、TypeScript 和生产构建；完成后追加逐阶段 UI 验收证据。

批次结果：`legal_actions` 现按阵营提供逐舰炮击目标/炮位，以及逐舰鱼雷发射器、MF/格、舷侧/角度和速度设定。UI 不再默认全勾炮位；添加或更换目标时仅勾选引擎判定射界合法的炮位，射界外炮位灰显禁用。鱼雷名册可为多舰和多个发射器分别建单，并自动填入封存移动轨迹上的合法发射格。实际应用内浏览器从新建想定 3 教学局开始，仅使用 UI 控件完成 4 回合：第 1 回合三舰各航行 1 MF，卡尔和里夏德分别由 TT1 发射鱼雷，三舰各自齐射；随后逐阶段推进，四份回合战报均弹出，最终由引擎判定轴心小型战略胜利。全程未使用高级 JSON、数据库或直接状态修改，最终 `errorCount=0`。验收中修复无调整值显示 `null` 和终局仍可推进的问题。`107 passed`，TypeScript 与 Vite 37 模块生产构建通过。

## 双舷鱼雷 ABXY 发射方向纠错批次

状态：实现、回归与运行中 API 验收完成

来源：规则书第 11 页 `IBS-R-08.2` 的鱼雷发射方向图及红字要点；原图明确规定左舷、右舷各有 `A/B/X/Y` 四条轨迹，共八种“舷侧—方向”组合。禁止沿用现有“左舷仅 A/B、右舷仅 X/Y”的错误推断。

1. 将八种组合及相对舰首方向结构化到规则数据，由引擎加载，UI 不复制常量。
2. 后端允许发射器自身射界支持的任一舷选择 `A/B/X/Y`，并以“舷侧 + 字母”共同计算鱼雷航向。
3. `legal_actions` 为每个发射器返回合法方向，UI 两舷均显示四个字母；切换舷侧不得擅自改变已合法的字母。
4. 验收：左右舷八组合航向金标、规则书青叶“左舷 X”范例、非法发射器舷侧、鱼雷专项、全量 Python、TypeScript 与生产构建全部通过。

批次结果（后续勘误）：移除错误的“左舷仅 A/B、右舷仅 X/Y”约束这一 UI 结论仍有效，但当时对原图八条轨迹的相对方向转录错误，旧金标也因此错误。2026-08-24 重新回看规则书第 11–12 页后，正确值为左舷 `A/B/X/Y = -1/-2/-3/-4`、右舷 `A/B/X/Y = +1/+2/+3/+4`；舰首 2 的左舷结果应为 `1/6/5/4`、右舷为 `3/4/5/6`，青叶“左舷 X”为方向 5。以本轮纠错批次的测试和提交为准。

## 停留格鱼雷发射与地图方向标批次

状态：实现、回归与运行中 API 验收完成

来源：规则书第 11–12 页 `IBS-R-08.2`；发射订单记录本回合舰船所在的发射格，鱼雷在移动执行中随 MF 脉冲航行。用户已纠正规则解释：未移动舰船可在当前停留格发射，不得把 `0 MF` 当作无发射资格。地图方向沿用已核验的主地图罗盘 `1=右上、2=右下、3=下、4=左下、5=左上、6=上`。

1. `legal_actions` 对所有有封存移动计划的舰船加入 `MF 0 / 当前停留格 / 当前舰首` 发射点；移动舰仍保留 MF 1…N 的途中发射点。
2. 订单模型与验证允许 `launch_at_mf=0`，并严格要求发射格等于当前停留格；负数和超过航路的 MF 继续拒绝。
3. 同步移动开始前生成 MF 0 鱼雷航迹，使其从第一个全局 MF 脉冲开始移动；发射、弹药、接触、命中和回放事件保持一致。
4. 在全模式地图左下角增加六向方向标，直接复用前端唯一航向投影函数；不得另建一套方向常量。
5. 验收：静止英/德驱逐舰发射、MF 0 错格、首脉冲轨迹、八方向组合、确定性回放、全量 Python、TypeScript 与生产构建通过。

批次结果：订单模型和引擎现将 `MF 0` 作为当前停留格的合法发射时点；移动舰还可继续选择 MF 1…N。静止发射在同步移动开始前生成航迹，并从第一个全局 MF 脉冲开始按设定速度前进。真实 API 已验证想定 3 五艘英舰在 `0 MF` 航路下均返回 `[0]` 发射点。地图左下角新增全模式六向舰首方向标，箭头与棋子共用 `headingRotation/headingVector`。全量 `109 passed`，TypeScript 与 Vite 37 模块生产构建通过，后端已重启。

## 玩家地图格号显示纠错批次

状态：实现、构建与运行中开发服务验收完成

问题与来源：原版主地图 `IBS-M-MAIN` 使用 `A–HH / 1–27` 格号。后端为六角运算使用轴向 `q/r`，例如内部 `q17,r7` 正确对应玩家地图 `R16`；鱼雷计划 UI 误把内部坐标直接显示给玩家，造成发射格错误的观感。

1. 在前端坐标模块增加轴向坐标到原版地图格号的唯一投影函数，与地图绘制使用同一 odd-q 行偏移。
2. 鱼雷发射点下拉框只显示 `MF / 原版格号`，不再暴露 q/r；订单提交仍保留轴向 JSON，不改变裁决坐标。
3. 加入 `q17,r7 → R16`、`q16,r7 → Q16` 与 A1/HH27 边界断言；复验 MF 0 和移动后发射格与地图棋子位置一致。
4. 验收：TypeScript、Vite 生产构建、全量 Python 与真实开发服务源码检查通过。

批次结果：新增 `hexLabel()`，按与地图一致的 odd-q 投影把轴向坐标转换为玩家格号；鱼雷下拉框现显示 `MF 0 · R16`、`MF 1 · Q16`，订单 JSON 与引擎仍使用精确 q/r。运行时断言覆盖 R16、Q16、A1、HH27。全量 `109 passed`，TypeScript 与 Vite 37 模块生产构建通过，开发服务已确认不再输出 q/r 文案。

## 逐舰战果账本、结算叙事与战术标志批次

状态：实现、自动回归与运行中 API 验收完成，待用户浏览器视觉复核

来源与边界：炮击、鱼雷、碰撞、火灾及沉没均以 `IBS-R-08.1/08.2` 和对应裁决表生成的引擎事件为唯一事实来源。逐舰记录、回合战报和地图标志只能消费按当前阵营过滤后的事件与状态；禁止由前端猜测伤害、泄露敌方隐藏损伤、秘密计划或不可见鱼雷。

1. 核验用户指定的鱼雷、起火和沉没棋子与规范资料副本哈希；直接复用 `resources/originals/assets/images/`，不另造近似素材。
2. 为阵营观察增加不可变的逐舰战斗账本，分别记录“本舰造成的战果”和“本舰受到的攻击/损伤来源”，包含回合、阶段、来源舰、目标舰、裁决原文、骰子与规则出处。
3. 舰船记录表增加战果与受伤来源双栏时间线；隐藏损伤启用时，敌舰记录不得出现受限明细。
4. 全模式结算弹窗改为逐舰叙事战报：先显示攻击舰、目标、命中与最终效果，再保留完整裁决流水和规则出处；火灾、沉没和鱼雷使用规范状态棋子强化辨识。
5. 地图显示当前阵营可见的鱼雷航迹，并按阵营及齐射枚数使用鱼雷棋子；舰船起火和沉没状态使用对应棋子，方向和位置仍由引擎状态决定。
6. 验收：素材哈希、事件归因、隐藏信息、逐舰账本、鱼雷/状态标志、TypeScript、Vite 生产构建和全量 Python 测试通过；更新 `havedone.md` 并提交版本证据。

批次结果：用户给出的 7 张鱼雷/起火/沉没图片与仓库规范素材逐个 SHA-256 完全一致，直接复用而未生成副本。炮击结果、鱼雷结果和特殊损伤事件补全攻击者归因；观察接口按阵营过滤全部事件后，为每艘可见舰生成“本舰战果/受伤与攻击来源”账本。舰船记录表显示回合、阶段、对手、裁决原文、骰子和规则页。全模式战报新增逐舰攻击卡，明确齐射、命中、最终损伤、火灾与沉没；地图显示鱼雷齐射棋子、航向/枚数、起火和沉没状态。新增隐藏损伤账本测试，全量 `110 passed`，TypeScript 与 Vite 37 模块生产构建通过；重启后真实 API 返回 `combat_history`、`torpedo_tracks` 和 `markers`。

## 鱼雷发射器横线数量与齐射枚数纠错批次

状态：实现、来源核验、回归与运行中 API 验收完成，待用户浏览器复核

来源：规则书 `IBS-R-08.2.2` 印刷第 11 页明确“鱼雷发射器符号中的横线数量为其可用的鱼雷数，玩家可发射部分或全部”；舰船记录手册第 2–5 页逐舰鱼雷符号为更高优先级数据。OCR 只用于定位，数量必须回看原页横线。

1. 逐舰核验两个可玩想定全部鱼雷发射器：想定 3 德英 DD、想定 1 日美 CA/DD；禁止继续使用“每个发射器统一 1 枚”的模板假设。
2. 结构化每个发射器的可用鱼雷数，保留发射器舷侧、再装填和鱼雷型号；引擎初始 `loaded`、合法行动上限、弹药消耗和航迹 `salvo_size` 必须来自同一舰船记录。
3. UI 新建发射订单时默认选择该发射器当前全部装填量，同时保留 1…装填量的手工调整能力；名册和状态表明确显示“已装填/容量”。
4. 地图按实际 `salvo_size` 选择 1/2/3 枚鱼雷棋子，不得把两枚齐射显示成一枚。
5. 验收：德英 DD 两枚发射器、日美逐舰差异、部分齐射、全齐射、弹药扣除、航迹枚数、地图素材选择、确定性回放、全量 Python、TypeScript 与 Vite 构建通过。

批次结果：视觉核验规则书第 11 页及舰船记录手册第 2–5 页。纠正想定 3 德英 DD 为每座 `2+2`，想定 1 美 DD 为 `2+1`、日军重巡为 `2+2`、吹雪系为 `2+2`、朝云为 `3+3`、秋月为单座 `2`。新建 UI 订单默认发射该座全部装填量，玩家仍可降为部分齐射；引擎按实际枚数扣弹并写入航迹 `salvo_size`，地图分别选择 1/2/3 枚棋子。部分发射后剩余 1 枚和两枚全齐射测试均通过。全量 `110 passed`，TypeScript 与 Vite 37 模块生产构建通过；真实新局 API 返回卡尔 `2,2`、标枪 `2,2`、法伦霍尔特 `2,1`、青叶 `2,2`、朝云 `3,3`、秋月 `2`。

## 鱼雷棋子航向与逐格航迹可读性纠错批次

状态：实现、回归与运行中 API 验收完成，待用户新局视觉复核

问题与证据：用户当前想定 3 第 1 回合事件库显示，卡尔加尔斯特 TT1 从 O14、舰首 4、左舷 A 角发射，但错误规则数据把绝对航向算成 1 并送至 W10。规则书第 11–12 页 `IBS-R-08.2` 原图复核确认左舷 A 是相对舰首 -1，因此正确绝对航向为 3，应沿 O 列前进。另有鱼雷 PNG 未随航向旋转、日志未记录逐格航迹的可读性缺陷。地图方向沿用已核验 `IBS-M-MAIN` 六向罗盘。

1. 纠正八种轨迹为左舷 `-1/-2/-3/-4`、右舷 `+1/+2/+3/+4`；增加舰首 4 + 左舷 A = 3 和青叶舰首 2 + 左舷 X = 5 金标。
2. 将鱼雷素材的固有箭头方向标定为地图方向 5，并只旋转图片到引擎 `heading`；方向线、棋子图案和地图罗盘必须重合。
3. `TorpedoTrack` 保存发射格、舷侧、发射角和已穿越格；同步移动逐格追加航迹，不从 UI 反推。
4. 发射事件补充可审计的舷侧、角度、发射格、绝对航向和齐射枚数；每轮同步移动生成一条鱼雷航迹事件，列出起点、逐格路径、终点和剩余射程。
5. 地图悬停文案使用原版格号显示“发射格 → 当前格、舷侧/角度、航向、已走格数、剩余射程”；旧存档缺少新字段时保持兼容。
6. 验收 O14 沿 O 列方向 3 金标、六方向图片旋转、逐格航迹、事件回放、全量 Python、TypeScript 和 Vite 生产构建；浏览器自动读取若仍受本机 URL 策略阻止，则以运行中 API/数据库和用户视觉复核作为证据。

批次结果：规则书第 11 页八轨迹图和第 12 页青叶范例重新视觉核验，纠正旧 YAML 为左舷 `-1/-2/-3/-4`、右舷 `+1/+2/+3/+4`。卡尔舰首 4、左舷 A 现得到方向 3；真实新局从 O14 航行 8 格后为 O22，事件逐格保存 O14→O15→…→O22。青叶舰首 2、左舷 X 金标同步改为方向 5。鱼雷棋子按素材固有方向 5 旋转到引擎航向，悬停显示发射格、舷侧/角度、航向、航迹、已走格数和剩余射程。全量 `110 passed`，TypeScript 与 Vite 37 模块生产构建通过；运行中 API 验证局 `fa63c499-ec4d-45f8-8333-7bdc0d54a35a` 返回航向 3 和 O 列完整航迹。旧局已产生的错误航迹不做静默状态改写，新局使用修正规则。

## 鱼雷计划逐 MF 舰首标注与发射航向回验批次

状态：实施中

来源与边界：`IBS-R-08.2`（规则书第 11–12 页）定义鱼雷射角相对舰首，发射方向 = 发射时点舰首 + 左/右舷 `A/B/X/Y` 相对偏移。同步移动按 MF 脉冲推进，舰首可能在发射 MF 之前转向，因此发射时点的舰首必须取密封移动轨迹在该 MF 的记录值，而非计划阶段的恒定初始舰首。

1. 复核引擎结算：发射 MF 的 `launch_heading` 必须来自 `paths[ship.id][impulse][1]`（该 MF 舰首）；新增金标验证 60° 中途转向与 120° 原地转向脉冲两种情形，禁止回退到恒定舰首。
2. 计划标注：鱼雷发射 MF 下拉与已编排发射行显示 `MF k · 原版格号 · 舰首 h`；已编排行按引擎提供数据展示 `舰首 h + 舷侧/角度 → 绝对航向 x`。
3. 前端不得复制 `relative_heading` 常量；由 `legal_actions` 把 `relative_heading` 作为结构化规则数据下发，UI 只做展示换算。
4. 验收：逐 MF 舰首标注、转向后发射航向金标、全量 Python、TypeScript 与 Vite 生产构建通过。

## 移动逐格交互·战报损伤摘要·鱼雷辅助批次

状态：实施中

来源与边界：三项 UI/交互改进以引擎既有裁决为唯一事实来源——可达格/移动预览/鱼雷命中推荐全部由引擎只读计算下发，前端只画线、只提交 `plan`/`commands`，禁止复制规则常量。移动命令合法性与 `_movement_program` 语义一致（首命令 advance、转后必接 advance、末仅免费 60°、120° 计 1 MF、费用落合法区间）。战报损伤摘要来自引擎结算点 payload 的归一化快照 diff，不新建事件类型、不改消息文本；隐藏损伤过滤沿用 `_hidden_damage_event`，字段随事件一起被过滤。鱼雷推荐器仅用可见目标信息（当前航向/航速匀速外推），命中阈值与 `_resolve_torpedoes` 共用 `torpedo_hit_count` 防漂移；`target_aspect_modifier.torpedo_bow_stern` 引擎未用则推荐器亦不用。

1. 陆地只保留接口、不接线：`state.land_hexes`/`_terrain_impassable` 原样保留（当前想定无陆地，数据恒空）；不接入 terrain-overlays.yaml，不做主图对齐 QA。可达格/移动预览/鱼雷触陆按全海图处理，与既有结算一致。
2. 移动逐格交互：`movement_candidates`（可达格 BFS）、`movement_preview`（前缀推进+下一步枚举）、`path_to_commands`（拖拽路径→命令）、`commands_to_plan`；`POST /games/{id}/movement-preview` 只读端点；MOVEMENT_PLANNING schema_hint 增 `movement_candidates`；观察增本方 forced 约束字段（陆地展示字段不新增）。前端 HexMap 格点击/拖拽/高亮 + 新建 HexMoveEditor 逐格推进（点击=1 MF、Q/E=±60°、A/D=±120°、Backspace 回退、Esc 退出），PlanSheet 逐舰开关与文本模式共存，只写现有 `plan`+`speed`。
3. 战报损伤摘要：`_damage_snapshot`/`_damage_delta` 在 gunnery_result/torpedo_result/special_damage/fire_check/ship_sunk 五个结算点并入归一化损伤字段与 `attacker_name/target_name`；`_damage_hull`/`_lose_speed` 返回实际值；`_add_fire` 记录 `fire_source_attacker` 使火灾沉没可追溯点火者；`ShipCombatEntry` 增 `payload`。前端战报弹窗、实时日志、逐舰船表渲染损伤摘要。
4. 鱼雷辅助：`torpedo_hit_count`（从结算提取，共用防漂移）、`expected_torpedo_hits`（2D6 穷举期望）、`_project_torpedo_path`（与 `_resolve_movement` 鱼雷循环一致）、`_project_target_position`（可见信息外推）、`torpedo_assist`（按期望命中降序推荐+预测航迹）；`POST /games/{id}/torpedo-assist` 只读端点。前端目标下拉→Top-N 推荐→"采用"自动填鱼雷订单 + 地图预测航迹叠加。
5. 验收：可达格/移动预览/陆地/结算 payload/沉没追溯/鱼雷概率与引擎一致性测试；想定 1/3 自动终局不回退；回放字节等价；TypeScript 与 Vite 生产构建通过。

批次结果（批次 C 功能2后端，2026-08-25）：五结算点 gunnery_result/torpedo_result/special_damage/fire_check/ship_sunk 在损伤前取 `_damage_snapshot`、事件前并入 `_damage_delta` 归一化损伤字段（hull_lost/speed_lost/fire_added/fire_remaining/gun_mounts_destroyed/torpedo_launchers_destroyed/sank/flags）与 `attacker_name/target_name`；`_damage_hull`/`_lose_speed` 返回实际扣格/跨速；`_add_fire` 统一加火源并记录首次点火者 `fire_source_attacker`，`cause=='fire'` 沉没可追溯到点火者；`ship_sunk` payload 增 `attacker/attacker_name/position`；`ShipCombatEntry.payload` 携带损伤字段（隐藏损伤字段随事件过滤，无泄漏）。新增 `tests/test_damage_payload.py` 12 例：五事件 delta 与真实状态差一致、沉没归属、火灾追溯、首发点火不被覆盖、船表 payload、隐藏损伤无泄漏、回放字节等价。全量 `147 passed`。

批次结果（批次 D 功能2前端，2026-08-25）：`types.ts` `ShipCombatEntry` 增 `payload?`；新建 `damageSummary.tsx` 共享 `damageChips`/`DamageChips`（只读引擎下发的归一化损伤，不复制裁决常量），战报弹窗 `EventRow` 与逐舰攻击结算卡片、实时日志、舰船记录表 CombatColumn 全部渲染损伤 chips（-X 船体 / 失速 / 起火 / 余火 / -X 炮位 / -X 鱼雷管 / 沉没 / 特殊 flags：射击指挥仪、雷达、舰桥、舵机、舰长阵亡/负伤、炮塔卡死、极限转向、被迫直行/旋回、限制速度）；战报汇总新增"损伤船体"统计（6 列）。`tsc -b` 通过，Vite 生产构建 39 模块通过。

批次结果（批次 E 功能3后端，2026-08-25）：引擎新增 `torpedo_hit_count`（从 `_resolve_torpedoes` 提取，引擎与推荐器共用防漂移，结算行为不变）、`expected_torpedo_hits`/`torpedo_hit_probability`（2D6 36 结果穷举）、`_project_torpedo_path`（与 `_resolve_movement` 鱼雷循环一致的纯几何直线投影，含射程/触界截停）、`_project_target_position`（可见信息匀速外推+触界钳制）、`_assist_intercept`/`_assist_launch_combos`/`_assist_launch_from_dict`/`_assist_evaluate`（逐 impulse 交点/距离/舷侧/修正/概率期望）、`torpedo_assist`（合法组合按期望命中降序返回 Top12+预测航迹，仅用可见目标信息，不读敌方封存计划）；`TorpedoAssistRequest` 模型 + `POST /games/{id}/torpedo-assist` 只读端点（TORPEDO_PLANNING 外 409）。新增 `tests/test_torpedo_assist.py` 10 例：阈值与规则书一致、期望/概率与 36 穷举相等、直线/射程/南缘触界投影（A10→A20 10 格、A22 触界 A27 余 5）、目标恒速外推与钳制、拦截组合推荐（KARL 舰首 1 左舷 A 北向直达 M8 距离 4 舷侧 bow_stern 修正 7）、组合可被 TorpedoOrder 采用并通过引擎校验、单发射叠加路径、IBS-S-01 轴心第 4 回合前禁射、API 形状/只读/错误阶段 409。全量 `157 passed`。

批次结果（批次 F 功能3前端，2026-08-25）：`hexGeometry.ts` 新增 `hexFromLabel`（引擎格号→轴向坐标的纯几何逆变换，含往返不变量）；`types.ts` 增 `TorpedoAssistCombo`/`TorpedoAssistResponse`；`api.ts` 增 `torpedoAssist`；PlanSheet 鱼雷分支新增"鱼雷辅助·可见信息推演"区块——目标下拉（敌方在位舰）→ 进入鱼雷计划阶段自动加载 → 引擎只读 torpedo-assist → Top-8 推荐表（发射组合/MF/格/鱼雷航向/距离/舷侧/命中率/期望命中），点行叠加预测航迹与拦截点，"采用"按组合覆盖或新建该发射器 TorpedoOrder（launch_hex/bearing/launch_side/angle/setting_index 全部来自引擎，speed 映射 setting_index，不复制规则常量）；App 持有叠加状态并把 `torpedoAssistPaths` 传给 HexMap（仅鱼雷计划阶段），HexMap 用 headingVector 同构几何绘制青色虚线航迹 + 终点 + 红色拦截点。`tsc -b` 通过，Vite 生产构建 39 模块通过。

## 射击安排优化·船表火控/火炮/装甲批次

状态：已完成

批次结果（批次 G，2026-08-25）：引擎 `_gunnery_candidates` 目标增 `range`/`modifier`（单人单目标固有修正，不含集火/多目标惩罚），新增只读 `gunnery_assist(state, side, assigned=None)`（越受限先分配 → 每舰炮位最多档 → 档内修正最佳 → `GUNNERY_ASSIST_BAND`(3) 带内选负载最小目标分散火力；assigned 排除已编排舰并计入负载）+ `GunneryAssistRequest` + `POST /games/{id}/gunnery-assist` 只读端点；`PublicShip` 增 owner-only `mfc_destroyed/radar_destroyed/bridge_destroyed/rudder_destroyed/captain_status`。前端 PlanSheet 逐舰/全舰齐射自动选择升级（全舰走引擎推荐并回退逐舰最优）、名册显示首选目标与修正；ShipStatusCard 炮位补装甲 `装 X"`、新增"火控情况"行。新增 `tests/test_gunnery_assist.py` 9 例，全量 `166 passed`；`tsc -b` 与 Vite 生产构建 39 模块通过；8000 后端已重启，端点经 5173 代理可达。

来源与边界：用户要求"为全部安排齐射计划"按钮自动选择可开火炮最多、修正最佳（距离+各类修正）的目标，并在质量相近时尽量分散避免多舰集火同一目标；同时船表缺少火控情况、火炮尺寸、装甲尺寸。炮击命中修正的计算（距离/目标速度/纵射/口径对目标/射击指挥仪损毁/起火/雷达或照明弹/探照灯/烟幕）由引擎 `_gunnery_modifiers` 唯一裁决，**不复制到前端**：`_gunnery_candidates` 目标增 `range`/`modifier`（集火附加射手、多目标惩罚两项分配相关修正除外，按单人单目标 1/1 计算），并由引擎只读 `gunnery_assist` 推荐全舰分配。火控/损伤字段沿用 PublicShip 仅本方 owner-only 模式（敌方 None），炮位口径/装甲经既有 `gun_mounts` 下发，前端只渲染。

1. 后端：
   - `_gunnery_candidates` 每个目标增 `range`（格距）与 `modifier`（`_gunnery_modifier(..., attackers=1, caliber=max(可射炮位口径), target_count=1)`）。
   - 新增 `gunnery_assist(state, side, assigned=None)`：`assigned` 为草稿中既有齐射 `{ship_id,target_id}`（排除已编排舰并计入目标负载）。分配算法：越受限越先（目标少者先），每舰取射界炮位最多档 → 该档内修正最佳者 → 与最佳修正差 ≤ `GUNNERY_ASSIST_BAND`（3，UI 偏好非规则常量）的档位内选负载最小（其次修正、再最近），返回 `{recommendations:[{ship_id,target_id,mount_ids,range,modifier}], excluded:[{ship_id,reason}]}`。
   - `GunneryAssistRequest{assigned?:[{ship_id,target_id}]}` 模型 + `POST /games/{id}/gunnery-assist` 只读端点（GUNNERY 外 409，只可查询本方舰）。
   - `PublicShip` 增 owner-only 火控/损伤字段 `mfc_destroyed/radar_destroyed/bridge_destroyed/rudder_destroyed/captain_status`（`observe` 以 `ship.side == side` 过滤，敌方 False/None）。
2. 前端：
   - `types.ts`：`GunMount` 已有 `caliber/armour`；`Ship` 增五个火控字段；`GunneryCandidate` 目标增 `range/modifier`；增 `GunneryAssistResponse/Recommendation/Request`。
   - `api.ts` 增 `gunneryAssist`；PlanSheet："为该舰安排齐射"改选炮位最多档内修正最佳目标；"为全部安排齐射"调 gunnery-assist（把草稿既有齐射作为 assigned）填入选入推荐的全部舰，加载/错误提示，失败回退到逐舰最优选择。
   - ShipStatusCard：炮位 token 补装甲 `装 X"`（口径已显，保持醒目）；新增"指挥与损伤"行按 owner-only 字段显示火控/雷达/舰桥/舵机/舰长状态（复用 damageSummary 的旗标文案，未知/未公开不显示）。
3. 验收：`gunnery_assist` 单测（多舰不集火、最受限先分配、修正带内分散、assigned 排除与负载、blocked 排除）；PublicShip 火控字段本方可见敌方隐藏；炮击端到端回放不漂移；全量 Python + TypeScript + Vite 生产构建通过。

## 射界方位判定修正批次（用户报告：IBS-S-01 第 1 回合）

状态：已完成

批次结果（2026-08-25）：`_bearing_between` 由"最近邻格方向"近似改为**规则 8.1a 中心连线屏幕角度**最近六方向。旧算法在 flat-top odd-q 错位网格上误判约三成方位（种子 1 全盘 91 对中 29 对，31.9%），典型病例即用户报告的邓肯（X8，舰首 4）→ 吹雪（P14）：视觉上目标仅偏舰首 11°（正前方），旧算法判为 bearing 3 / rel 5（左舷），使全部 5 个带左舷射界的炮位都能射击；修正后判为 rel 0（舰艏），仅 P1/P2 两门舰艏炮可射，初雪（舷侧）仍全 5 门。方位同时影响 `_mount_can_bear`（射界）与 `_target_aspect`（纵射判定），修正后纵射判定随之纠偏（邓肯对吹雪为 broadside，不再误加纵射修正）。**不是**改任何规则常量——只是把方位几何从错误近似换成规则书定义（中心连线），相邻格方位两种算法完全相同，逐格移动不受影响。另确认第二个投诉"为何都选衣笠而不选最近的青叶"不是 bug：修正忠实来自已验证规则表（6-9 格射程 -6、10-15 格 0；纵射 6-9 格 -6、10-15 格 -4），博伊西对青叶(7 格)=-12、衣笠(11 格)=-4，远处目标确实更好；规则第 9 页正文"距离越近越容易命中"与表格/示例矛盾，已记入 `docs/rules/open_questions.md`（IBS-Q-004），不静默改表。新增 `tests/test_bearing.py` 5 例（相邻格精确、全盘与 8.1a 参考一致、邓肯-吹雪舰艏仅 2 炮、邓肯-初雪舷侧全 5 炮、纵射修正不误加），全量 `171 passed`；仅后端改动，前端无规则常量复制。

来源与边界：用户测试埃斯佩兰斯角海战第 1 回合报告两点——(1) 邓肯为什么能用全部火炮攻击"只在正前方"的吹雪；(2) 为什么齐射计划都选衣笠而不选最近的青叶，"你真的计算过修正吗"。第 1 点确认为真实几何 bug（旧"最近邻格"方位在错位网格误判正前方为左舷 60°），第 2 点为规则表如实执行（远处修正更好，见上）。边界：方位几何仅影响射界（`_mount_can_bear`）与纵射（`_target_aspect`）两条判定，不触碰命中阈值/修正值本身；`_path_to_commands`（line ~1409）只处理相邻格，两种算法一致不受影响。

1. 后端：
   - `_bearing_between`（engine.py ~3111）改为：由 two-hex 中心连线在渲染屏幕空间的角度（`atan2`，与前端 flat-top odd-q 同构），选 6 个舰首方向角（330/30/90/150/210/270）中最接近者；相邻格时与旧算法逐格一致。`import math`。
   - 不改 `_mount_can_bear`/`_target_aspect` 的射界表与纵射逻辑本身（它们只是消费修正后的方位）。
2. 前端：无改动（射界/方位由引擎裁决，前端不复制几何）。
3. 验收：新增 `tests/test_bearing.py` 5 例；全量 `171 passed`；想定 1/3 自动终局不回退。

## 齐射推荐修正方向纠错批次（用户确认 D66 骰点越小越好）

状态：已完成

批次结果（2026-08-25）：用户纠正"炮击命中表骰点越小越好、骰点是六进制 D66"——核对了命中表（玩家辅助 2 页：火力 1 时骰点 11→1 发命中、13+→0，低段命中更多）与 `d66_adjust`（修正沿 36 档 D66 阶梯移动，负修正移向 11 = 更容易命中），**引擎裁决方向本来正确**（`_resolve_gunnery`：`d66_adjust(raw, modifier)` 后查 `hit_count`，负修正 = 更容易）。但齐射推荐器的"修正最佳"方向取反了：`gunnery_assist` 与前端 `pickBestTarget` 都用 `max`（修正越大越好），而 D66 是**越小越好、修正为负更好**，导致推荐选了修正更差的目标（如博伊西被推荐 11 格的衣笠 mod -4，而 7 格的青叶 mod -12 才是最佳）。修正：引擎 `gunnery_assist` 最佳修正改 `min`、带内判定改 `<= best+BAND`、并列改按 `t["modifier"]` 升序；前端 `pickBestTarget` 同样改 `modifier<best`。修复后 IBS-S-01 第 1 回合盟军：博伊西 → 青叶（7 格 -12）、海伦娜 → 青叶、盐湖城 → 初雪、旧金山 → 古鹰，DD（法伦霍尔特/拉菲/布坎南/麦卡拉）因只有初雪为 -12 档而集火初雪（无法在不牺牲质量下分散，符合"修正最好前提下分散"）。IBS-S-03：德舰三 DD 在 -20 档内分散到标枪/克什米尔/泽西。**同时更正上一条目结论**："衣笠更好"与"IBS-Q-004 射程修正矛盾"均为高骰点更好误读的产物；低骰点更好下射程表与正文一致，IBS-Q-004 已 resolved。

来源与边界：用户指出"在炮击命中表里骰点越小越好，还有其他修正引擎做了吗，还有航速修正，这里骰点是六进制"。核对结论：命中表低段命中更多（低骰点更好）✓；骰子为 D66（两枚 d6 十位+个位）✓；`_gunnery_modifiers` 已实现全部 11 项修正（射程、目标航速 0/-4/-9/-18、纵射、口径对目标、射击指挥仪损毁、集火附加射手、多目标、目标起火、雷达/照明弹、探照灯、烟幕），并全部并入裁决 `modifier=sum(...)` ✓；目标航速修正确实生效 ✓。仅推荐器的"最佳修正"比较方向错误（把负修正当差、实际是奖励）。边界：不改任何修正常量与裁决路径；鱼雷为独立 2D6 高骰点系统（≥11/≥13），无此方向问题，不动。

1. 后端：`gunnery_assist`（engine.py ~551）最佳修正 `max→min`、带内 `>= best-BAND → <= best+BAND`、并列键 `-t["modifier"] → t["modifier"]`；docstring 注明 D66 低骰点更好。
2. 前端：PlanSheet.tsx `pickBestTarget` `target.modifier>best.modifier → <`（逐舰齐射与"首选目标"提示共用）。
3. 验收：`tests/test_gunnery_assist.py` 方向断言改 `min`/带内 `<=`，LODY 断言改为取 -20 档泽西（不再取更差的 -12 标枪）；全量 `171 passed`；`tsc -b` 与 Vite 生产构建通过；8000 后端重启，live `gunnery-assist` 返回博伊西→青叶。

## 增援入场 + 移动计划航迹批次（用户改进点 1/2）

状态：已完成

批次结果（2026-08-25）：用户报告两个改进点——(1) 埃斯佩兰斯角海战想定有增援却一直没有出现；(2) 移动计划阶段，舰船移动后应在目标格留下一个浅色算子、沿途留下连线。根因：(1) **引擎增援机制完整且工作正常**（第 3 回合 REINFORCEMENT 阶段推进时掷 1D6 检定、`succeeds_on=[1]` 约 1/6 成功率、第 4 回合入场、E17–U27 51 格最短六角边走廊 `_reinforcement_entry_legal`、校验要求全部 8 舰且入口格互不重复）——"一直没有"是**前端缺口**：增援分支永远显示"本阶段没有可用增援"，没有入场表、没有检定结果显示，玩家无法提交增援订单，于是增援从未入场。(2) 引擎 `movement_preview` 本就计算逐舰航迹，但无批量接口，前端无法把草稿全部移动计划一次画到地图上。

修复（后端只读、前端只画线/只提交订单，规则常量不复制）：
- `_reinforcement_candidates(state, side)`（engine.py ~570）：只列本方 `reinforcement_turn == 当前回合` 且未入场的舰，按 `_reinforcement_entry_legal` 枚举入口走廊格，取最后一条 `reinforcement_roll` 事件作为检定结果 → `{group_available, arrival_turn, trigger_turn, succeeds_on, roll_result, entry_range, entry_hexes, ships:[{ship_id,name,asset,max_speed}]}`。接入 `legal_actions` REINFORCEMENT 的 schema_hint（~449）。
- `movement_plan_trajectories(state, side, plans)`（engine.py ~617）：逐舰复用 `movement_preview`，非本方/沉没/无位舰返回 invalid 条目而不抛错（批量草稿宽容），→ `{trajectories:[{ship_id,plan,cost,valid,commitable,errors,trajectory,end_hex,end_heading}]}`。新增 `MovementTrajectoriesRequest` + `POST /games/{id}/movement-trajectories` 只读端点（MOVEMENT_PLANNING 外 409）。
- 前端：types/api 增 `MovementTrajectory/MovementTrajectoriesResponse/ReinforcementCandidates` 与 `movementTrajectories`；App 在 movement_planning 阶段对草稿 250ms 防抖批量拉取航迹；HexMap 画"浅色连线"（去重连续同格后的起点→各中间格 polyline，虚线 65% 透明度）+ 目标格"浅色算子"（舰船素材 42% 透明度、按 end_heading 旋转、带舰名）；PlanSheet 增援分支改为完整入场表——检定结果状态条（成功/失败/骰点）、入口走廊说明、"自动分配互不重复入口格"按钮、逐舰入口格下拉（走廊 51 格）+ 舰首 + 速度，入口格重复时标红提示；检定失败时提示"本回合无增援入场，提交确认即可"，无增援想定/回合保持原"没有可用增援"文案。

来源与边界：用户"埃斯佩兰斯角海战剧本不是有增援吗，一直没有呀"（增援 UI 缺口）与"移动计划一艘船移动完在目标点留下一个浅一点的算子，在走过各自留下连线"（航迹叠加）。边界：增援检定与入场校验完全由引擎 `_resolve_reinforcements`/`submit_orders` 裁决，前端只提交 `{ship_id, entry_hex, heading, speed}` 订单；入口走廊/检定结果由 `_reinforcement_candidates` 下发，前端不复制 51 格走廊坐标与 `succeeds_on`；航迹由 `movement_preview` 计算，前端只画 polyline 与目标算子。移动计划批接口与逐舰 `movement-preview` 同属只读，不落库、不改裁决路径。

1. 后端：
   - `_reinforcement_candidates` + `movement_plan_trajectories`（如上）；`legal_actions` REINFORCEMENT schema_hint 增 `reinforcement_candidates`。
   - `models.py` 增 `MovementTrajectoryEntry/MovementTrajectoriesRequest`；`api.py` 增 `POST /games/{id}/movement-trajectories`（只读、MOVEMENT_PLANNING 外 409、非本方舰返回 invalid 条目）。
2. 前端：
   - `types.ts` 增三类型；`api.ts` 增 `movementTrajectories`；App 防抖拉取 + 交接/开局清空；HexMap 增 `plannedTrajectories` 渲染；PlanSheet 增援入场表。
3. 验收：新增 `tests/test_reinforcement_candidates.py` 6 例（成功种子 3：group/roll/corridor 51 格/8 舰、失败种子 1、触发前空、仅本方、legal_actions 嵌入、API 序列化）+ `tests/test_movement_trajectories.py` 5 例（与 movement_preview 一致、stationary、非本方 invalid、无位舰 invalid、API 形状/敌方 invalid/错误阶段 409）；全量 `182 passed`；`tsc -b` 通过；Vite 生产构建 39 模块通过；8000 后端重启，live HTTP 驱动种子 3 到第 4 回合增援成功入场（轴心地图 5+8=13 舰）、`movement-trajectories` 返回 KARL GALSTER `1S1` 航迹。


## 射界热力图批次（用户：两方射界图开关）

状态：已完成（计划先行 → 后端 + 前端 + 验收均完成）；追加"选舰"子模式（用户："选中哪个就展示那个船的火力热力"，已完成）

目标：地图上加一个"两方射界图"开关，对地图每格汇总两方各舰每门火炮的"射界 + 射程范围"，按火炮强度与该格距离修正加权生成热力图；热力跨舰/跨炮叠加，两方可同时叠加显示。

设计要点（治理：热值/命中表/距离修正全部由引擎唯一计算，前端只渲染颜色与开关）：
- 引擎新增只读 `field_of_fire_heatmap(state, viewer, ship_id=None, target_speed=4)`：对双方分别算 `{hex_label: heat}`，只含 heat>0 的格。**热值 = Σ 可指向该格的炮位 firepower × 该格 D66 期望命中数**（期望命中 = `range_modifier("gunnery", distance)` + `target_speed_modifier("gunnery", target_speed)` 移档后对 36 档 D66 全举 `hit_count` 求均值——包含"火炮强度"与"那格的距离修正"；默认目标航速 4，其修正按已验证表取 0（0→-18、1→-9、2-3→-4、4+→0），近格修正更负 → 期望命中更高 → 更热）。
- 修复（用户演示核对发现）：初版实现只加期望命中数、**漏乘 firepower**，与公式不符；`_ship_fire_heat` 改 `heat[label] += mount.firepower * expected_hits(...)`，测试对照助手同步补乘。
- 射界几何：抽取 `_relative_aspect(origin, heading, target)` 静态助手（bearing 取六方向 + 舰首方位 rel → BOW/STARBOARD/STERN/PORT，与 `_mount_can_bear` 完全同源），`_mount_can_bear` 改为复用它，防两处漂移。
- 本方：真实状态，已毁炮位剔除；敌方：按记录全炮位（**不泄漏隐藏损伤**），且只含 `_visible_to` 可见的敌舰（**不泄漏隐蔽舰船位置**）。
- 端点 `POST /games/{id}/field-of-fire`（viewer 走 `X-Player-Side` header），任意阶段可用（战术叠加层），返回 `{viewer, sides:{axis:{hexes,max_heat,ships}, allies:{hexes,max_heat,ships}}}`；可选 body `{ship_id}` → 只算该舰（所属侧填充、另一侧为空；本方真实炮位、敌方记录炮位、敌方舰仍须可见）。
- 前端：地图区开关"射界热力图：关 / 轴心 / 同盟 / 双方 / 选舰"；HexMap 增 `fireHeatmaps` prop——**双方统一红色**（用户要求），"双方"模式合并两侧热值；每个有热值的六角格**显示热值数字**（覆盖坐标标注，`heatData` 合并 map + `heat-value` 文字样式）。"选舰"模式选中哪艘展示哪艘（`_ship_fire_heat` 复用同一公式），左上角显示当前舰名。

来源与边界：用户原话"做一个两方射界图开关，举个例子，每个船的每一门炮的射界射程范围，按照火炮强度，那格的距离修正，做一个热力图，热力可叠加"。边界：热力图是可见信息推演类战术辅助（舰船身份/位置/航向均公开，敌方炮位按记录值），不泄漏隐蔽舰位置与隐藏损伤；引擎无硬性炮射程上限（距离修正表 21+ 收 +4），远格期望命中自然衰减近零，归一化后几乎不可见，符合规则裁决（远距仍可射击但极难命中）。

1. 后端：抽取 `_relative_aspect`（`_mount_can_bear` 复用）；新增 `field_of_fire_heatmap` + `POST /games/{id}/field-of-fire` 端点。
2. 前端：App 开关状态 + 防抖拉取；HexMap 热力色块渲染。
3. 验收：新测试（36 档穷举与期望命中一致、射界与 `_mount_can_bear` 同源、隐蔽敌舰排除、隐藏损伤不泄漏、API 形状/只读）；全量 pytest；`tsc -b` + Vite 构建。

## 战报火灾图标纠错 · 失速循环条 · 逐舰攻击结算分栏批次

状态：已完成（用户报告"战报上怎么成功命中都是用火灾的棋子"，并顺带提出"失速的血条也在状态那显示"与"逐舰攻击结算最好左边显示轴心战果，右边显示同盟战果"）

批次结果（2026-08-25）：根因——`BattleReportModal.resultIcon` 用 `/fire|火/.test(JSON.stringify(payload))` 字符串匹配 payload，命中表键名 `fire_added/fire_remaining`（即使值为 0 也存在）导致每次命中都渲染 `起火.png`。修复为只读引擎下发的 `damage` 对象：`fire_added + fire_remaining > 0` 才显示起火、`damage.sank` 或 `ship_sunk` 显示沉没，不再匹配键名。失速条：`PublicShip` 增 owner-only `speed_damage_crossed`/`speed_damage_track`（引擎 `_damage_snapshot` 同源），舰船状态表新增"失速循环"整宽行——按三回合循环逐行渲染速度损伤轨，已划去格（`index < crossed`）标红 ×；敌舰两字段保持 `null`（与 `max_speed` 同规则）。逐舰攻击结算：`gun_mount_attack`/`torpedo_attack` payload 增 `attacker_side`/`target_side`，战报"逐舰攻击结算"改为左"轴心战果"/右"同盟战果"双栏（无该侧攻击时显示空提示，未归类事件单列"其他攻击"），卡片复用同一渲染器。全量 `197 passed`（新增 3 例：炮击/鱼雷攻击事件 side 字段、观察本方暴露失速/敌方隐藏）；`tsc -b` 通过；Vite 生产构建 39 模块通过；8000 后端重启，live `observe` 返回本方 `speed_damage_crossed/track`、敌方 `null`，live 炮击 `gun_mount_attack` 返回 `attacker_side=axis`，`gunnery_result` 的 `fire_added/fire_remaining` 均为 0（修复后不再显示起火图标）。

来源与边界：图标/失速/分栏全部只消费引擎下发数据——损伤 `damage`、速度损伤轨、攻击 side 字段，前端不复制任何裁决常量。速度损伤轨数值来自想定逐舰记录（`speed_damage_track`）与引擎 `_lose_speed` 结算结果，前端只画格。敌舰速度损伤沿用隐藏损伤边界不外泄。`attacker_side` 只标注双方都已可见的"谁攻击谁"，不新增信息。

1. 后端：`gun_mount_attack`/`torpedo_attack` payload 增 `attacker_side/target_side`；`PublicShip` 增 `speed_damage_crossed`/`speed_damage_track`（本方，敌方 None）。
2. 前端：`resultIcon` 改读 `damage.fire_added/fire_remaining/sank`；ShipStatusCard 增"失速循环"整宽行；BattleReportModal 逐舰攻击结算改轴心/同盟双栏。
3. 验收：新 3 测试 + 全量 pytest；`tsc -b` + Vite 构建；live API 观察与炮击事件核对。

## 鱼雷射角方向映射修正批次（用户权威规则 + 报告的 AA12 金例）

状态：已完成（用户给出权威规则 → 改映射 → 更新/新增测试 → 全量验收 → live 核对）

目标：修复鱼雷辅助的发射方向。用户报告：AA12（航向 4）舰左舷 B 应朝向 AA13-AA14（方向 3），左舷 X 应朝向 AA13-HH16 的东南斜线（方向 2），引擎此前给出 B→2、X→1。用户给出权威规则：假设船头朝向 m，左舷 A=所在格方向 m-1、B=所在格朝船头反方向一格方向 m-1、X=所在格朝船头方向前进一格方向 m-2、Y=所在格方向 m-2（减到 0 变成 6）；右舷镜像为 m+1/m+1/m+2/m+2（加到 7 变成 1）。

设计要点（治理：方向映射唯一存放在 `torpedo-launch-directions.yaml`，引擎 `_torpedo_launch_heading` 读取，前端只消费引擎下发的 `relative_heading`/`torpedo_heading`，不复制常量）：
- 来源：规则书 8.2.3 b（PDF 11 页）"两个方位共 8 种鱼雷发射轨道（每个舷侧 4 种）"；规则文本与用户权威规则一致 → 映射修正为 `port {A:-1,B:-1,X:-2,Y:-2}`、`starboard {A:+1,B:+1,X:+2,Y:+2}`（此前 `A:-1,B:-2,X:-3,Y:-4`/`+1,+2,+3,+4` 是错误推导）。
- **只修方向、不改锚点**：全部鱼雷轨仍以舰所在发射格为起点。用户规则中"朝船头反方向一格/朝船头方向前进一格"若按字面实现为 B/X 锚点外移 1 格，将与用户自己报告的金例矛盾（B 线从船格起穿过 AA13-AA14）——方向映射已完全满足报告症状；锚点偏移作为开放问题记录（见 open_questions.md IBS-Q-005），待用户澄清。
- 收敛的派生核对：舰首 4 时 左B→3（AA12→AA13→AA14）、左X→2（AA12→BB12→CC13→DD13→EE14→…东南斜线）；规则书 Aoba 例（舰首 2、左X）= m-2=0→6，旧注释"port-X=5"基于错误旧表，已修正。

1. 后端：`resources/derived/structured/rules/torpedo-launch-directions.yaml` 改 `relative_heading`（含注释）；引擎 `_torpedo_launch_heading`/`_project_torpedo_path`/`_resolve_movement` 鱼雷循环零改动（全部读 yaml）。受影响测试同步更新：`test_engine.py` ABXY 全表、`relative_heading` 断言、两处 120° 转向发射航向断言、starboard-X 接触几何测试（Javelin 由 O14 改 N14，因新方向 m+2=5 走 O15→N14）。
2. 测试：新增 `test_torpedo_launch_headings_match_authoritative_abxy_rule`——6 舰首 × 8 (side,angle) 全表对照权威规则参考式 + 用户金例（舰首 4：左B=3、左X=2、AA12→AA14 沿线）。
3. 验收：全量 `198 passed`；`tsc -b` 通过；Vite 生产构建 39 模块成功；live：torpedo-assist 对舰首 4 舰返回左A/B=heading 3；`_project_torpedo_path` 从 AA12 投影 左B→`['AA12','AA13','AA14',…]`、左X→`['AA12','BB12','CC13','DD13',…]`，与用户报告一致。

## 鱼雷锚点偏移 · 调试模式 · 鱼雷阶段航迹保留 · 鱼雷历史轨迹 · 船表完整战果批次

状态：已完成（实现、回归、构建与测试全部通过，待用户浏览器视觉复核）

来源与边界：用户两条指令——(1)"锚点按我说的改，加一个调试模式可以看到两边，船的运动轨迹在后面的鱼雷计划阶段保留"；(2)"鱼雷要加入鱼雷历史轨迹，在哪里发射的，船状态表的日志战果我希望展示完整"。锚点为用户权威规则（`IBS-R-08.2` b 项"朝船头反方向/前进一格"）字面实施，覆盖 IBS-Q-005 开放问题；调试模式只解锁观察（双方全可见）不参与任何裁决路径；鱼雷阶段航迹从已封存移动计划只读重放，敌方计划默认不泄漏；鱼雷历史轨迹/发射点/完整战果全部只消费引擎下发数据，前端不复制规则常量。

1. 后端锚点：`torpedo-launch-directions.yaml` 增 `launch_anchor {A:0, B:-1, X:1, Y:0}`（左右舷共用，B 船尾外 1 格、X 船头外 1 格）；引擎新增 `_torpedo_anchor_hex(launch_hex, 发射时舰首, angle)`（锚点越界退回舰格），`_launch_torpedo_order` 的 `position/launch_position/traversed_hexes` 与 `_project_torpedo_path`/`_assist_intercept` 的起点统一经它计算；`_assist_evaluate` 传入 `launch_angle` 与舰首。方向（`relative_heading`）不变。
2. 后端调试模式：`observe(game_id, side, debug=False)`——debug 时全舰可见、隐藏损伤与规划硬件全展示、鱼雷轨/事件/标记/比分不隐藏；`GET /games/{id}/view?debug=true` 透传。
3. 后端鱼雷阶段航迹：新增 `sealed_movement_trajectories(state, side, debug=False)` 从 `_sealed_batches(MOVEMENT_PLANNING)` 只读重放逐舰 `movement_preview`（默认仅本方，debug 含敌方）；`GET /games/{id}/sealed-trajectories`（仅 TORPEDO_PLANNING，debug 可选）。
4. 前端：App 增"调试"开关（header，切换即带 `debug` 重拉 view）；plannedTrajectories effect 增鱼雷计划阶段分支（`sealedTrajectories`，debug 透传）；HexMap 航迹区分敌我（敌方红线 85% 透明度 + 目标算子 60%）；鱼雷轨叠加历史航迹虚线（`torpedo-trail`）与发射点标记（`torpedo-launch-marker` 金色圆圈 + 角度字母）；ShipStatusCard 战果/受伤双栏去掉 `.slice(-8)` 截断、完整倒序展示并加 `max-height` 滚动。
5. 验收：新增 3 测试（锚点全角度金标 AA12 舰首 4：B→BB11、X→Z12、A/Y→AA12；debug 观察全舰/隐藏损伤/比分；sealed 航迹仅本方/调试含敌方）+ 更新 2 接触几何测试（starboard-X 锚点 O16→N15、launch_position=锚点）；全量 `201 passed`；`tsc -b` 通过；Vite 生产构建 39 模块成功。`docs/rules/open_questions.md` IBS-Q-005 由 open 改 resolved 并记录用户裁决与金例说明。

## 简单战术 AI（TacticalCommander）批次

状态：已完成

批次结果（2026-08-25）：按用户三要素实现确定性启发式战术 AI——(1) 炮击采纳 `gunnery_assist` 齐射推荐；(2) 移动打分为"去敌方火力热力小处 + 让敌方处于我方火力覆盖内"；(3) 鱼雷仅当距离较近且自动鱼雷系统 `expected_hits` 置信度高时才发射。接入范围＝教程对手 + 命令行（用户已确认"都接"）。研究依据（塔萨法隆加夜战"超射程乱射无益、近距才有效"；crossing the T 抢占 T 字横头；ATLATL/AlphaSCS/Panopticon/WarAgent）只用于定权重量纲，未引入训练模型。

引擎只读/等价重构（规则常量唯一留在引擎，命中公式仍只在 `expected_gunnery_hits`）：
- 新增 `expected_gunnery_hits(firepower, distance, target_speed=4)`——把热力闭包内 D66 36 档命中期望公式提为方法，闭包委托、记忆化保留，行为逐位不变（现有 heatmap 测试即回归护栏）。
- 新增 `ship_gun_pressure(state, ship, position=None, heading=None, target_hexes=None)`——假想位/航向下单舰火力压力＝Σ 未毁炮位（`_relative_aspect` 在射界内）× firepower × 期望命中；默认目标格＝`_visible_to` 可见敌舰格（与 observe 同源，不泄漏隐蔽舰）。
- 抽出共享枚举器 `_movement_expand`（首命令 advance、转后必 advance、末 60° 免费、120° 计 1MF、forced/界/陆约束），`_movement_reachable` 主循环改从它取转移（遍历顺序逐位不变）。
- 新增 `movement_path(state, ship, target_hex, heading=None)`——用 `_movement_expand` 做 **0-1 BFS**（0 成本转向边 appendleft、1 成本推进边 append、dist 不含 cost 的键）带 parent 还原，返回 `{valid, commands, plan, cost, end_hex, end_heading}`；与 `movement_candidates` 同源，候选格必可达。

新模块 `tactical.py`：`TacticalCommander(DeterministicCommander)`（复用父类 CONTACT_SETUP/REINFORCEMENT），`model="tactical-v1"`。顶部可调启发式权重/阈值（非规则常量）：`W_ENEMY_HEAT=1.0`、`W_FIRE_PRESSURE=1.0`、`W_APPROACH=0.5`、`APPROACH_RANGE=12`、`TORPEDO_MAX_RANGE=10`、`TORPEDO_MIN_EXPECTED=0.30`、`TOP_K_CANDIDATES=5`。`_plan_movement` 覆盖全部在位本方舰（满足 submitted==expected），敌方信息一律经 observe；对 `movement_candidates` 每个可达 (格, 末航向) 打分 `score = -W_ENEMY_HEAT·(敌热力/敌方max) + W_FIRE_PRESSURE·(本舰压力/候选空间max压力)`＋炮射程外接近项，确定性排序后对 TOP_K 候选逐个 `movement_path`→`movement_preview` 复核取合法计划，失败走回退链 `"0" → 直行 max_cost → 首个可达格`。`_plan_torpedoes` 对最近可见敌舰调 `torpedo_assist`，仅取 `distance ≤ 10` 且 `expected_hits ≥ 0.30` 且未 blocked 的组合，每发射器一条订单（launch_hex 经 `HexCoord.from_label`，天然匹配封存轨迹校验）。`_plan_gunnery` 直接采纳 `gunnery_assist["recommendations"]`。

接线：`match.py` `make_session` 加 `"tactical"` 分支、CLI `--axis/--allies` choices 扩为 `("deterministic","tactical","deepseek")`；`api.py` 的 `suggested_orders` 与 `tutorial_opponent` 换用 `TacticalCommander()`（教程对手＝可对打的 AI，suggested-orders 仍是只读建议）。

顺带修复的引擎 bug（AI 对 AI 压出）：
- **同格 distance=0 三处 StopIteration**：碰撞检定失败的两舰合法同格 → 射程表/纵射表/穿透表查表越界。`_range_value` 下限钳到 `max(1, distance)`（单点覆盖全部射程表查表）、`penetration` 顶部 `max(1, distance)`。
- **`movement_path` 原 FIFO 非最短**：0 成本转向边使 FIFO 可能返回非最短路径（实测 cost 6 vs 候选最小 4），改 0-1 BFS。
- **确定性对手 `"0"` 计划对强迫舰非法**（桥楼/舵损伤 forced_circle/forced_speed）：新增 `_stationary_plan` 回退链 `"0" → 直行 max_cost → 首个可达格路径`，`DeterministicCommander` MOVEMENT 改用之（此前战术 AI 引发更多战斗→损伤态→6/36 压出该失败）。
- **移动打分曾被火力压力项主导**（敌方热力归一 [0,1]、压力未归一 0–40，KARL-GALSTER 冲进更高敌热）：压力项按本舰候选空间最大压力归一，两项同量纲各权重 1.0。修复后种子扫掠 `mean_delta=-1.0`、16/24 not_worse。

来源与边界：用户"火炮发射就按之前做的自动，移动尽量去敌方火力热力图小的地方同时保持敌方处于我方火力热力图大的地方，鱼雷距离较近、置信度高的时候发射"；接线范围按用户确认"教程对手 + 命令行都接"。边界：AI 只产订单不裁决，命中公式/规则常量唯一在引擎；敌方信息只经 `observe`/`_visible_to` 守卫的只读方法（不泄漏隐蔽舰位置与隐藏损伤）；权重/阈值为 tactical.py 顶部启发式常量，可调不触裁决；IBS-S-01 想定禁射（turn1 无炮击、turn4 前无鱼雷）由引擎 `blocked_reason`/推荐器自动覆盖，AI 不做绕过。

1. 后端：引擎 `expected_gunnery_hits`/`ship_gun_pressure`/`_movement_expand`/`movement_path`（0-1 BFS）；`tactical.py` `TacticalCommander`；`llm.py` `_stationary_plan` 回退链；`match.py`/`api.py` 接线；同格 distance=0 三处钳制。
2. 前端：本批次无前端改动（AI 产出与既有建议订单/教程对手共用同一前端提交路径）。
3. 验收：新增 `tests/test_tactical_ai.py` 26 例（引擎新方法、AI 各阶段、集成）；全量 `227 passed`（`--basetemp=.pytest-verify`）；AI 对 AI 多 seed 终局 6 组合 × 6 seed＝36/36 COMPLETE 且确定（同 seed 两次一致）；CLI `python -m iron_bottom_sound.match --scenario IBS-S-03 --axis tactical --allies deterministic --seed 9` → passed=True、completed=True、winner=axis、request_count=32；`--scenario IBS-S-01` 双方向同样终局完成。

## 人机大战 · AI 对抗评分 · 六风格 profile 批次

状态：已完成

用户两项请求：(1) UI 可以选择人机大战（玩家选一方 + 选对手 AI 风格，标准想定对打）；(2) AI 状态机改进——做决定时考虑对手下一回合也会动（对抗评分，默认开启），并培养不同风格（均衡/大舰队编队/长纵队/乱阵近战/鱼雷专精/猥琐保守）。

来源与边界：AI 只产订单、走 `submit_orders`，引擎仍唯一裁决，规则常量不复制到前端；对抗评分为 1-ply——预测每艘可见敌舰下一回合最优落点（敌视角，只依赖敌当前可见信息、剥 `forced_*` 隐藏损伤、用 `_visible_to` 过滤我方可见舰，不泄漏隐蔽信息），我方威胁＝Σ 敌在其预测落点对我格的 `ship_gun_pressure`、压力＝我对敌预测落点集合的压力；`w_predict_opponent<=0` 退化为"预测=敌当前位置"静态语义（可关）。风格经 `TacticalProfile` 七个现有超参 + `w_formation/formation_spacing/line_ahead/w_predict_opponent` 表达，6 预设；模块级常量保留为 balanced 别名兼容既有 import，实现一律读 `self.profile.*`。`expected_gunnery_hits` 加实例级缓存（对抗后每次决策约 60k 次命中查表，无缓存 2-3s、缓存后 <100ms，行为纯等价）。

1. 后端：`GameOptions.mode` 增 `"vs_ai"` + `ai_profile` 字段；`tactical.py` 新增 `TacticalProfile`/`PROFILES`（6 预设）与 `_MovementContext`/`_build_movement_context`/`_predict_enemy_move`/`_enemy_move_score`/`_formation_factor`，`_movement_order_for`/`_score_hex`/`_plan_torpedoes` 读 `self.profile.*`；`engine.py` `expected_gunnery_hits` 缓存；`api.py` 新增通用 `POST /games/{id}/ai-opponent`（X-Player-Side + body.profile，幂等，不含订单）；`match.py` `make_session`/CLI 加 `--axis-profile/--allies-profile`。
2. 前端：`api.ts` `createGame` mode 扩 `"vs_ai"` + 可选 aiProfile、新增 `aiOpponent`；`App.tsx` mode 三态、Landing 增人机大战入口（想定+玩家阵营+对手风格）、`act()` 增 vs_ai 分支（submit → aiOpponent → advance → refresh，无交接屏）、header 显示「对手：{风格}」。
3. 测试：重写 `test_tactical_ai.py` 5 例（13/14/15/16/22，签名/语义随对抗化变化，22 改 profile copy 替代 monkeypatch 常量）+ 新增（预测合法性与确定性、敌规避我方热力、队形间距、长纵队共线、多 profile 移动差异、多 profile run_match 确定性、ai-opponent 端点 409/幂等/422/推进、现有 tutorial/hotseat/match 用例实证跑通）。
4. 验收：全量 pytest、`tsc -b`、Vite 生产构建、CLI 多 profile 确定性（同 seed 两次 match-report.json 一致）、浏览器人机大战逐阶段推进 + 6 风格阵型差异肉眼核对；完成后向 `havedone.md` 追加。

## AI 态势感知（残血/血量/状态/火炮/VP）+ 随机射击 + 存档格式设计批次

状态：实现、测试、CLI 验证与设计文档完成；git 提交待用户决定（分支存在大块未提交基准）

批次结果（2026-08-25）：用户四项改进——① 残血时应远离；② 决策考虑血量/状态/剩余炮门/VP；③ 炮击+移动落点评分归一化 softmax 抽样加随机（种子化可复现）；④ 存档/状态表示设计（本批只出文档）。引擎只读增量：`PublicShip.vp`、`_gunnery_candidates` 每目标 `expected_hits`（命中公式唯一在引擎，AI 不复制）、`gunnery_assist` 透传、薄封装 `gunnery_target_options`。`tactical.py`：`TacticalProfile` 增 8 个可调字段（产品默认 `retreat_hull_threshold=0.35/w_retreat=1.0/w_protect_own=0.5/w_vp=0.3/w_finish=0.5/w_self_status=0.3/temperature=0.5/rng_seed_off=0`）；`_value_factor`（VP+补刀加权）、`_own_value`（残血/高价值/带伤→退避强度，满血=0）、`_value_pressure`（逐候选价值加权火力压力）、残血退避项（`own_value·w_retreat·Δdist/approach_range`）、`_sample_weighted` softmax 抽样（temp≤0→argmax 不耗 RNG）；AI 独立种子化 RNG `Random(seed·1000003+turn·10007+side·101+phase·11+off)`，纯整数派生、与引擎骰子流隔离、不用 game_id/hash()/set 序。炮击改为逐舰对全部候选目标按 `expected_hits×价值` softmax 抽一个（可多舰集火），敌情一律走 observe() 不泄漏隐藏损伤。全量 `254 passed`；CLI 复验同 seed 两遍逐位一致、temperature 0/0.5/2.0 下 MOVEMENT/GUNNERY 均不同、残血 GALSTER 距敌预测格 1.0→8.5 显著退避（BEITZEN/LODY 因火力优势位留守＝打分决策，调参留后续）。设计文档 `docs/architecture/state-representation.md`：一个真相源（SQLite）+ 两投影——投影一 JSONL 世界态 + cell-aligned ASCII/整数棋盘（918 格、坐标表头+图例，TopoBench +30-40pp），投影二 918 格多通道特征张量 .npz（11 通道复用 `field_of_fire_heatmap` 扫格 + 动作合法掩码），静态/动态切分，文献/GitHub 清单（TopoBench/GVGAI-LLM/ResTNet/antiyoy-ai/NuZero/SMAC 等），分步实施路线；本批不写导出代码。

## 存档导出（投影一）+ LLM 模式对接 + 提示词工程 + 实况验证批次

状态：已完成（7 提交，CLI 与 API 实况均收敛）

批次结果（2026-08-26）：用户四项改进全部落实并实况验证——① **投影一存档按时装**：state_export.py `export_frame`/`render_board` 全从 `observe()` 可见集派生（敌隐藏损伤 hull/guns/torpedoes 全 None、超视距敌不出现），JSONL 帧 + cell-aligned ASCII 棋盘（918 格、表头 A..AH+行号+图例、label 定位、符号不变式「小写=token 大写=坐标」、同格优先级 船>沉船>鱼雷轨>接触标记），`PlayerObservation` 增公开 wrecks，`GET /games/{id}/export` 只读，run_match 逐阶段对双方累积 `-frames.jsonl` + `-board-{side}.txt`。② **LLM 模式对接**：`POST /games/{id}/llm-opponent`（同步 def、守卫 404→403→503→409→幂等短路、`submit_orders` 引擎裁决非法不静默、返回公开 audits 不含私有订单）+ 前端 mode=llm 完整接入（Landing 入口/header 徽标/`llmBusy` 防双发/503 中文提示）。③ **提示词工程**：按阶段 few-shot（`SAMPLE-` 占位符防照抄、turn/phase 调用时注入）、【思考纪律】反过度思考（禁候选枚举/自我怀疑/重复推导、以 `{` 开头即停）、附 hex 轴向距离公式；`reasoning_content` → `LLMCallAudit.reasoning_preview`（`thinking_enabled` 可开关，max_tokens disabled=2400/enabled=6000）。④ **实况收敛两处问题**——(a) TorpedoOrder.bearing 必须直接取 `launch_positions[i].heading`（发射瞬间舰船航向）而非由 launch_side/launch_angle 的 relative_heading 换算（对局 2 卡死，修后对局 3 重试=0）；(b) 地图边缘世界平移病理情形（对侧边缘已有算子无法平移）由「整局中止」改为「该舰停靠边缘格 + `movement_blocked_by_edge` 事件（IBS-R-06.1.8）、对局不中止」（对局 3/4 中止，修后对局 5 完成；处理方案经用户"继续"确认按推荐项停靠边缘实施）。CLI 实况：`completed=True/winner=axis/turns=4/deepseek_calls=16/retries=0/timeouts=0/failures=0`，单次最长 44.1s<90s，16 个 reasoning 样本无死循环标记。API 实况：完整 4 回合 16 次真实 llm-opponent 调用全 200/valid（1 次自纠重试，单阶段合计 67.1s<90s）、幂等短路 16×、503 守卫、audits 无私有订单泄漏。全量 `144 passed`；本机无 node，前端提交前人工审查（tsc/Vite 待有 node 环境补跑）。**提醒**：贴出的 DeepSeek 密钥已仅随验证命令环境变量内存使用、未写入任何文件，请轮换。下一步：投影二（918 格多通道特征张量 .npz）导出与训练管线。

## 战报系统（每阶段双视角截图 + 每回合 LLM 叙事 + 随时调出 + 下载 MD）批次

状态：已完成（本批次尚未提交，提交哈希待补）

批次结果（2026-08-26）：用户战报系统需求全量落地并验证——**引擎唯一裁决、战报层只读**：只用 `observe`/`get`/`engine.event_visible_to`，规则常量不复制，DeepSeek 只从 `DEEPSEEK_API_KEY` 环境变量读取。**截图**：Pillow 服务端渲染（1330×1359），几何与前端 `hexGeometry` 完全一致（odd-q 平顶、HEX_SIZE=24=外接圆半径）；create/advance 钩子每阶段结算后保存双方视角 PNG（`prev_phase` 先记后推、sequence 后缀防重名），只画各侧 `observe` 可见集（hidden_damage 敌不画残血星、超视距敌不出现），`_board_cells` 从 state_export 抽出与 ASCII 棋盘同源。**叙事**：每回合末（FIRE_END 门控）生成中立战史一篇——`public_events_for_turn` 取「至少一侧可见」并集、排除 orders_submitted（携私有订单）；LLM 纯文本 `write_narrative`（无 response_format/thinking disabled/0.7/800）；无密钥或失败→确定性事实摘要；幂等（`battle_narrative_exists`）；失败绝不影响对局。**持久化**：DB 第 4 张表 `battle_report` PK(game_id, sequence, side) INSERT OR REPLACE + 磁盘 PNG；三端点 `GET /battle-report`（JSON）/`/image/{rel}`（路径穿越守卫）/`.md`（自包含 base64、attachment）。**三种模式适配**：hotseat/vs_ai/llm 经前端 createGame `options.battle_report`（Landing 全局勾选默认开）；AIvsAI 经 match.py `--battle-report`（repository=None 只落文件）。**前端**：header 常驻「战报」按钮随时调出、回合末自动弹窗（服务器为唯一事实源，替换客户端组装）；modal＝回合 tabs + 叙事纯段落 + 每阶段双视角缩略图（lightbox）+ 分组公开事件 + 比分/胜负 + 下载按钮（隐藏 `<a download>`）+ 「含双方视角」公平性注记。**验证**：全量 `300 passed`（新增 16 例：几何/迷雾/捕获持久化/叙事门控/LLM 路径无泄漏/Markdown 自包含 base64 计数==截图数/API+image+路径穿越/match on+off）；CLI 实况 `--battle-report` 4 回合 56 张 PNG、MD 5.7MB 内嵌 56 图、`passed=true`。本机无 node，前端提交前人工审查（tsc/Vite 待有 node 环境补跑）。下一步：投影二（918 格多通道特征张量 .npz）导出与训练管线；战报可选项——异步叙事（消除回合末 +2-8s）、截图降采样控 md 体积、多局战报汇总页。

## LLM(DeepSeek) vs 状态机 AI 实况对局 + 战报全量验证批次

状态：已完成（本批次尚未提交，提交哈希待补）

批次结果（2026-08-26）：用户「用 LLM 对战状态机 AI 打一局、输出战报验证」——想定7 仅 catalogued 无数据文件（经询问选想定1，正好 7 回合）。**实况压出一个真引擎 bug 并修复**：`legal_actions.movement_candidates` 过滤漏 `not ship.sunk`，沉没但仍占格的舰（漂移未结算）被当可动舰候选，与校验 `owned` 不一致 → LLM 三连败规划沉船（T7）。修法与 `_gunnery_candidates`/`_torpedo_candidates`/确定性指挥官一致。**结构性改进**：`movement_candidates` 每个可达格附引擎 `movement_path` 算好的精确 `plan` 串（`include_plans` 参数，确定性/战术指挥官传 False 免开销）——AI 只挑目标格照抄 plan，强制转弯/首动 advance 由引擎保证。**提示词纪律 4 处**：沉没舰不入 movement 且不覆盖；gunnery 只对 targets 非空候选开火、mount_id 取自候选（LLM 曾自造 KINUGASA-M1/M2）；reinforcement 只增援 candidates.ships、入口取自 entry_hexes；movement 照抄候选 plan、reachable 无 cost0 则必须移动。**--model CLI**（默认仍 deepseek-v4-flash，deepseek-chat/reasoner 均可用但用户指示用 flash）。**对局收敛（5 局）**：T7 沉船→T6 自造炮位→T4 自造增援→T5 强制转弯→第 5 局成功 `passed=true, completed=true, winner=allies`（想定1 第7回合）、50 请求、轴/盟各 25 plan、121.6s。**战报全量验证**：7 回合全叙事、90 张 PNG（turn1=6 开局局部、turn2-7=14/回合）、MD 10.5MB 自包含 90 base64、meta 完整（winner=allies、score{axis:4, allies:11}、phase=complete）。全量 `301 passed`。**提醒**：本次贴出的 DeepSeek 密钥仅内存注入未写文件，请轮换。下一步：投影二导出与训练管线；战报异步叙事/降采样/多局汇总。
# 二马扩展想定、状态机 AI 接入与模块瘦身批次（2026-08-27）

状态：已完成。规范来源与剪影素材已导入并登记；24 艘船表完成结构化；想定已进入统一引擎/UI/状态机 AI；想定例外已从通用引擎抽出；全局回归、确定性回放、前端构建及状态机 AI 完整终局均通过。

范围：只读导入 `D:\desktop\铁底湾\二马` 中的规范来源，提取想定初设、特殊规则、双方船表及非“舰娘”版棋子剪影；识别并接入用户近期实现的状态机/战术 AI。现有用户提交 `596694f` 及其前序改动视为基线，不回退、不覆盖。通用规则继续由现有结构化规则权威裁决；本想定特例优先级高于通用规则。

1. 建立来源清单：记录 PDF/PNG/JPG 的 SHA-256、尺寸、规范路径、重复素材和用途；PDF、船表、想定图逐页/逐图视觉核验，OCR 只用于定位。
2. 为扩展想定分配稳定 `IBS-S-*` 标识；结构化标题、回合、初始阶段、地图、能见度、双方编成、初始格/舰首/速度、增援、退出、VP、胜负及全部特殊规则。不确定字段进入 `docs/rules/open_questions.md` 并阻止发布为 playable。
3. 从双方船表逐舰录入舰体、速度循环、装甲、炮位/GF/口径/射界、鱼雷、雷达、火控、特殊能力、摧毁顺序和 VP；复用已有舰型字段，不在引擎或 UI 写想定常量。
4. 只导入规范“国家-舰种-舰名.png”棋子剪影；“舰娘”图作为未启用别名保留来源记录，不进入默认 UI。复用已有状态、鱼雷、地图素材时以哈希去重。
5. 识别 `tactical.py`、随机 AI、LLM 适配、API/UI 新入口及状态导出链，定义统一 AI 玩家协议；让新想定经相同 `observe/legal_actions/submit_orders/advance` 接口进入状态机 AI，不给 AI 私有状态写权限。
6. 以职责和测试为依据拆分臃肿文件，优先拆解规则裁决、合法行动提示、想定特例和前端计划编辑；保持公共 API、事件格式、存档兼容与现有测试不变。
7. 验收：来源/数据完整性、船表边界、初设加载、特殊规则、确定性回放、状态机 AI 至少完整终局一盘、API/UI 想定选择、隐藏信息、全量 Python、TypeScript、Vite 构建；完成后追加 `havedone.md`、提交哈希和运行证据。

验收摘要：`IBS-S-EM-01` 以合法默认部署从第 1 回合炮击阶段运行至第 8 回合自动结算；双方 `TacticalCommander` 共 58 次阶段决策、0 回退、0 人工改状态，最终轴心 42：同盟 13，轴心以 29 分差获胜。默认部署仅是 UI 立即开局便利数据，来源规定的自由部署区域与交替部署顺序仍独立保存在想定结构中。

# 状态机 AI 编队与友军安全修复批次（2026-08-27）

状态：已完成（单一正文、API、开始页/对局内预览、自动测试与浏览器实测通过）

问题证据：战术 AI 当前逐舰独立评分，整批订单没有逐脉冲友舰航迹去冲突；`line_ahead` 只奖励候选格附近的任意友舰，不绑定固定纵队，也不协调同一机动；鱼雷辅助只计算敌舰截获，没有向 AI 暴露己方当前格/封存航路的安全风险。二马默认部署虽然位于双方部署区内，但不是若干明确、同向、等速的长纵队。

1. **来源边界**：碰撞与鱼雷接触继续由 `IBS-R-06.1`、`IBS-R-08.2.3` 原规则独立裁决；本批次只改 AI 的计划安全和扩展想定的便利默认部署，不把 AI 偏好伪装成规则，也不改变玩家可提交的合法订单。
2. **二马默认部署**：在来源允许的自由部署区内，把双方 12 艘舰分别编为主力舰、巡洋舰、驱逐舰三支长纵队；每队同航向、同航速、成员有稳定顺序，并把 `engine_default_formations` 保存到想定数据。来源规定的掷骰决定先手、大小舰交替部署仍为权威。
3. **友舰航迹去冲突**：状态机 AI 生成整批移动计划时逐舰保留已选航迹；候选计划若在同一移动脉冲与友舰进入同格，或与友舰交换格位，则跳过并尝试下一候选。只使用己方可知订单，不窥视敌方秘密计划。
4. **长纵队协调**：`line_ahead` 风格读取想定默认编队，同一队由队首选择机动，未受损且合法的跟随舰复制同一计划，从而保持相对格位和共同航向；受损/受迫舰无法执行共同机动时，回退到航迹安全的独立计划。
5. **鱼雷友军安全**：鱼雷辅助为每个组合标注其预测路径与己方当前/封存移动航路的交集；状态机 AI 过滤任何有友舰风险的组合。此项是 AI 射击纪律，不改变引擎按原规则进行的鱼雷接触裁决。
6. **验收**：新增默认纵队结构、同脉冲同格/交换格、纵队共同机动、鱼雷友军走廊和损伤回退测试；二马 `line vs line` 完整终局不得出现同阵营碰撞事件；运行全量 Python 测试、前端类型/生产构建，完成后追加 `havedone.md` 与提交哈希。

验收结果：二马 `line vs line`、seed 23 完整运行 8 回合，58 次阶段决策、0 回退、0 同阵营舰船碰撞；普通 tactical 双方同样完整终局且事件回放一致。全量 `352 passed`；TypeScript 与 Vite 生产构建通过（40 modules transformed）。

# 真实模式：编队指挥链与专用状态机 AI（2026-08-27）

状态：已完成（引擎、专用 AI、UI、审计、三想定终局与本地浏览器操作验收通过）

规则边界：原版特殊损伤表 31/42 的舰长伤亡继续由 `IBS-T-SPECIAL-DAMAGE` 裁决；编队、旗舰继承、指挥中断、受损舰撤退均使用项目扩展编号 `IBS-R-RC-01` 至 `IBS-R-RC-07`，不得混入经典模式。历史资料仅为扩展设计依据，不高于原版规则、玩家表和想定特例。

1. **模型与兼容**：新增 `realistic_command` 开关、`formation_setup` 阶段、编队/继承/撤退状态和编队订单；旧存档缺省关闭，经典模式事件流与 AI 保持不变。
2. **初设**：每方 1–4 个编队，全部初始舰和预定增援舰唯一归属；每队至少两舰，指定领舰、旗舰、备用旗舰和 1/2 格间距。固定想定以领舰原始格为锚点重新纵队化，自由部署想定使用原部署区。
3. **移动**：只提交领舰航路；引擎逐 MF 生成后舰尾随航迹，联合验证地形、碰撞、转向和速度。速度无共同合法值时强制整体降速或永久脱队。
4. **指挥链**：旗舰舰长阵亡、沉没或退出后按备用旗舰、编队顺序继承；下一回合整队锁定上轮最终航向和实际 MF，直航重复执行。
5. **撤退**：脱队舰进入确定性自动撤退控制器，避敌方火力、友舰、地形和鱼雷，自动合法炮击但不发射鱼雷；安全出界后标记撤退，不额外计沉没 VP。
6. **解耦**：新增独立 `realistic_command.py` 与 `RealisticCommander`，经典 `engine`/`TacticalCommander` 只通过窄接口调用；前端拆出真实模式初设、移动和危机处理组件。
7. **验收**：经典全量回归；真实模式来源、初设、尾随、间距、航速、继承、撤退、隐藏信息、存档回放测试；两个真实状态机 AI 完整打完想定 1、3、二马且无友军碰撞/友军鱼雷命中；TypeScript 与 Vite 构建通过。

验收结果：想定 3（seed 3/9）、想定 1（seed 5）和二马（seed 5）真实模式状态机双方均自动运行至 `complete`，无确定性回退、无人工改状态、无友军碰撞或友军鱼雷命中。想定 1 发生 9 次 `IBS-R-RC-03` 确定性紧急停车，未进入友舰碰撞骰表。专项 `8 passed`；全量 pytest 通过；TypeScript `tsc -b` 与 Vite 生产构建通过（42 modules transformed）。本地浏览器实际完成“开关 → 双方编队初设 → 热座交接 → 双方增援确认 → 领舰移动表 → 展开后舰地图预览 → 合法提交”。

# 固定扩展海图与编队状态栏（2026-08-27）

状态：已完成（固定坐标引擎、扩展地图、AI/战报/导出、编队状态栏及浏览器验收通过）

规则边界：印刷地图 `IBS-M-MAIN` 的 A–HH、1–27 坐标和岛屿/海岸资料保持不变；取消 6.1.8 的运行时世界坐标平移，改用项目稳定性扩展 `IBS-R-MAP-01`。扩展区域是无地形覆盖的纯海缓冲区，不伪装成原版印刷地图；舰船到达扩展区最终边缘时停止，不移动其他算子。

1. **统一地图配置**：新增单一后端/前端地图尺寸定义，将印刷区 34×27 与可玩区 46×39 分开；更新坐标模型、合法行动、AI、鱼雷、战报和状态导出，清除参与裁决的散落硬编码。
2. **取消世界平移**：同步移动不再调用世界平移函数、不生成 `world_shifted` 事件，也不修改其他舰船、鱼雷、残骸、标记、历史航迹或封存计划坐标；扩展区边缘生成确定性停车事件。
3. **远离边缘**：状态机 AI、真实编队 AI 和默认候选以扩展区边缘计算安全距离；原想定坐标保持不变，原先位于 R27、U27 等印刷地图南缘的单位现在位于可玩区内部。
4. **地图呈现**：SVG 扩展为 A–TT、1–39，可缩放/平移；原 A–HH、1–27 区域保留视觉边界，缓冲海域使用不同底色和说明。
5. **编队状态栏**：左侧我方舰船按编队分组，显示编队名称、领舰/旗舰/备用旗舰、间距和指挥状态；脱队/撤退舰单列。敌方仍只显示战争迷雾允许的可见舰船，不泄露敌方编队关系。
6. **验收**：更新世界平移旧测试为固定坐标/边缘停车测试；补充扩展坐标往返、鱼雷直线、战报/导出尺寸、编队分组组件测试；运行全量 pytest、TypeScript、Vite，并在浏览器检查扩展地图和编队状态栏。

验收结果：A–TT、1–39 固定可玩区生效；R27→Q28 可正常进入缓冲海域，R39 最终边缘确定性停车，船、鱼雷、残骸、标记、历史航迹与封存计划均不平移，新对局不生成 `world_shifted`。全量 `366 tests passed`；TypeScript `tsc -b` 与 Vite 生产构建通过（42 modules transformed）。浏览器确认默认“交战区”视图、可切换“全图”，我方从编队初设草稿开始即按编队分组显示，敌方不显示私有编队关系。

# 真实模式玩家规则书与前端预览（2026-08-27）

状态：已完成（单一正文、API、开始页/对局内预览、自动测试与浏览器实测通过）

1. **单一正文**：新增完整中文 Markdown 玩家规则书，明确原版特殊损伤 31/42 与 `IBS-R-RC-01` 至 `IBS-R-RC-07` 项目扩展的边界；覆盖开局、编队、移动、航速危机、继承、撤退、战斗、隐藏信息、胜负及示例。
2. **服务端读取**：FastAPI 提供只读规则正文接口，从 `docs/rules/` 读取同一 Markdown 文件；不在 UI、API 或 LLM 中复制规则正文或裁决常量。
3. **前端预览**：开始页真实模式区域提供“预览完整规则”，游戏内标题栏提供随时查看入口；弹窗含目录、原版/扩展醒目标识、滚动正文、关闭和打印功能。
4. **验证**：测试接口正文、内容类型、关键规则编号和无路径注入；TypeScript/Vite 构建；浏览器实测开始页和对局内预览、目录跳转、关闭及移动端滚动。

验收结果：规则正文由 `docs/rules/realistic-command.md` 单一维护，接口返回完全相同的 UTF-8 Markdown；开始页和真实模式对局标题栏均可打开带目录、打印与关闭功能的安全 React 预览。专项 `11 passed`；全量 `369 passed`；TypeScript `tsc -b` 与 Vite 生产构建通过（43 modules transformed）。浏览器确认正文包含特殊损伤 31/42 的原版边界、`IBS-R-RC-01` 至 `07`、编队初设、速度危机、旗舰继承、撤退、战争迷雾和示例。

# 二马想定延长为 12 回合（2026-08-27）

状态：已完成（结构化覆盖、12 回合 AI 终局、全量回归与浏览器验收通过）

1. **来源边界**：保留二马原扩展资料“8 回合、第 8 回合结束计分”的来源记录；新增 `IBS-S-EM-01-R5` 用户指定项目扩展，明确只把实际回合上限和终局计分时点延后到第 12 回合。
2. **结构化数据**：统一更新想定定义与目录的 `turns=12`，胜负结算改为 `end_of_turn_12`；不得在 UI 或引擎另写二马回合常量。
3. **验证**：更新来源边界测试；检查 reset/observe/API 均返回 12；状态机 AI 从第 1 回合运行至第 12 回合自动终局且回放一致；运行全量测试并浏览器新建二马确认标题栏显示 `/12`。

验收结果：二马当前 `turns=12`、终局计分时点 `end_of_turn_12`，同时保留来源 `source_turns=8` 与 `IBS-S-EM-01-R5` 用户扩展标记。两个状态机 AI 完成 90 次阶段决策并自动运行至第 12 回合，无回退，纯事件回放一致；二马专项 `7 passed`，全量 `369 passed`。本地浏览器新建二马后显示“第 1/12 回合”，仍按想定从炮击阶段开始。

# 鱼雷航迹世界平移折线修复（2026-08-27）

状态：已完成

1. 依据规则手册 PDF 第 12 页 8.2 鱼雷攻击范例确认：鱼雷按既定 P-X 等发射路线直线移动，不允许途中转向。
2. 复现截图中多条鱼雷航迹同步折弯；核对 `world_shifted` 事件与 `TorpedoTrack.traversed_hexes`，区分引擎实际航向错误和显示历史坐标系错误。
3. 世界平移必须对鱼雷的当前位置、发射锚点和全部仍在新坐标视窗内的已遍历格执行同一个原子平移；活算子预检失败时不得产生半平移状态，平移后落出纸图的纯历史尾迹只裁去显示、不反向阻止合法平移。
4. 增加世界平移后的鱼雷共线、相邻格、固定航向、发射标记同步和事件路径测试；运行规则引擎、观察/API、前端构建与浏览器复现验收。
5. 封存移动预览继续只显示本方原计划，避免在同步裁决前借世界平移或碰撞结果泄露敌方秘密计划；结算后为本方逐舰生成“起点、计划串、原计划终点、世界平移修正、实际终点、是否受阻”的私有核对事件。
6. 战报的移动计划不再只显示 `movement×N`，逐舰列出计划串；公开事件明确列出世界平移及最终 `ship_moved` 位置，使原计划、坐标系变化和实际终点可以逐项核对。

# GLM 对战兼容、真实模式二马实况与无损部署（2026-08-28）

状态：代码与本地回归已完成；正式 GLM 12 回合复验被供应商 HTTP 429（余额不足或无可用资源包）阻塞，补充额度后须从第 1 回合重新执行，不得把中断局计为通过。

1. **脱敏复现**：用户提供的智谱密钥只注入当前进程环境，绝不写入源码、配置、日志、战报、Git 或服务器文件；分别验证现有默认模型、文本 JSON 模型及视觉模型，记录脱敏 HTTP 状态、请求 ID 和错误类别。
2. **供应商能力解耦**：依据智谱官方当前模型清单修正失效默认模型；把文本、视觉、结构化输出和 thinking 能力拆成明确配置。文本模型不得接收地图图片，视觉模型才启用截图；前后端均给出可理解的模型/能力错误。
3. **统一比赛入口**：让 CLI 比赛运行器支持 `zhipu` 对阵现有状态机 AI，复用 `observe/legal_actions/submit_orders/advance`，真实模式只允许编队层合法订单；正式实况禁止人工改状态和确定性回退，非法行动只允许模型在限定次数内自纠。
4. **二马重点验收**：以 `IBS-S-EM-01`、12 回合、真实模式运行一场 GLM vs `RealisticCommander` 完整对局；生成事件回放、双方可见状态、LLM 调用脱敏审计、编队/碰撞/鱼雷友伤检查和自包含 Markdown 战报。
5. **战报审计**：逐回合检查是否自动终局、编队是否异常解散、是否发生友舰碰撞/友军鱼雷命中、旗舰继承与撤退是否一致、比分与胜负是否可由事件重建；发现缺陷先补测试再修复并重跑。
6. **无损同步**：本地全量 Python、TypeScript、Vite 和实况验收通过后提交；服务器部署前以 SQLite Backup API 创建新备份，只增量同步代码/静态资源并运行迁移，绝不覆盖现有 SQLite、存档、战报或用户配置；重启后验证公开站点和旧存档可读。
# 自适应鱼雷战术 AI 与 PSRO-lite 训练（2026-08-29）

状态：运行时、UI、PSRO-lite、断电恢复与烟雾验收已完成；正式多小时训练待在固定提交上启动。规则核心保持不变；本批只增加基于阵营观察的 AI 战术预测、解释、训练与评估层。

1. **来源与边界**：鱼雷发射、航迹、命中、弹药和隐藏鱼雷继续唯一服从 `IBS-R-08.2` 及结构化表。AI 不复制规则常量，不读取敌方封存移动、隐藏损伤或未公开鱼雷；反事实指标是 AI 评估，不得伪装成规则裁决。
2. **运行时战术层**：从 `PlayerObservation` 生成每艘可见敌舰最多 24 条公开航路假设；实现直接攻击、区域封锁、破 T、编队切割、交叉雷幕、撤退掩护和保雷七种意图；每发射器保留 8 个候选，以宽度 32 束搜索联合选单。
3. **反事实与安全**：比较无雷幕/有雷幕时敌方最佳公开响应，量化偏航、降速、火力损失、T 头损失与编队分裂；友舰当前格、封存航路和真实模式跟随路线相交时硬排除，最终订单仍经 `validate_orders`。
4. **鱼雷规避**：移动阶段仅依据阵营观察中可见航迹构建逐 MF 威胁图；经典模式逐舰、真实模式整编队规避。盲雷未公开时不得影响 AI。
5. **接口与展示**：增加按阵营过滤的只读战术分析接口、结构化战术审计和终局复盘；对局中敌方计划保持私有。新增 `adaptive`，保留全部旧风格并作为新建人机局默认。
6. **训练**：在现有 GA 外实现三轮 PSRO-lite，策略池含旧风格、六个专家和名人堂；本机 20 进程、种群 32、6 代。真实模式二马为 1.5 倍主要适应度槽位且每个对手槽位重复两次，经典想定 1/3 用于防过拟合。逐局 SQLite/WAL 提交、JSONL fsync、原子阶段检查点、信号中断和 --resume 共同保证断电恢复。
7. **实时可视化**：训练输出目录生成独立 dashboard.html 与每局更新的 status.json，本地 HTTP 面板每秒显示阶段、轮次、完成局数、ETA、策略混合、当前最佳响应和错误；运行手册固定在 rl/PSRO.md。
8. **验收**：金标覆盖六类战术、主动保雷、可见/隐藏鱼雷规避；订单合法率和回放确定性 100%，友舰碰撞/鱼雷友伤/泄漏为 0；fresh-seed 以真实模式二马为主要门槛，并覆盖三个想定双模式双阵营。只有统计门槛通过才注册冠军并无损部署。

预检证据：真实模式二马烟雾联赛 2/2 完成，0 友军碰撞、0 鱼雷友伤；断点恢复从 SQLite 还原 2 场结果并保持 stage=complete。自适应真实二马 seed 47 完整运行至第 12 回合，0 回退、0 友军事故且纯事件回放一致。正式矩阵首批缺陷已固化为 7 组 seed 20280829–20280832 真实二马终局和 2 组 seed 20270831/20270832 经典防过拟合终局；覆盖编队解散、强制直航撤退、速度区间断裂、领舰交叉和多舰移动死端。当前全量 400 项 pytest 通过，TypeScript/Vite 生产构建通过（43 modules transformed）。

# 正式训练停滞修复与断点续跑（2026-08-29）

状态：代码修复和 410 项全量回归通过；正式训练已从 636 个 SQLite 完成结果断点恢复，首次复核已推进到 644/1452、invalid=0、stalled=false，正在固定提交 5db6eac 上继续运行。

1. **停滞判据**：20 个工作进程持续满 CPU、完成数约两小时不变且 SQLite 无新增完成行，判定为移动规划计算活锁；不得继续用 ETA 掩盖无进展。
2. **真实模式解耦**：真实指挥器的领舰草案不得进入经典逐舰全舰队 CSP；简单候选失败后立即返回编队层，由共同速度、尾随展开、脱队和同步紧急停车统一裁决。
3. **经典模式边界**：经典规则保留碰撞裁决。AI 只做有限的末两舰局部修复；若已封存前缀确实堵死全部无冲突路线，则提交逐舰合法且冲突数最少的航路，由原版碰撞流程裁决，不得为追求零碰撞无限穷举。
4. **有界诊断**：保留轨迹缓存版应急 CSP 作为诊断工具，单次最多 5000 节点；正常运行路径不再调用整舰队穷举。
5. **实时面板**：训练中每两秒独立刷新心跳；连续 300 秒无新对局完成时，status.json 标记 stalled 并显示 progress_age_seconds 和 running_jobs，面板醒目标注“疑似停滞”。
6. **续跑门槛**：全量回归、精确卡死种子、真实模式二马 12 回合友伤检查均通过后提交；随后以 --resume 复用既有 SQLite 行，确认完成数越过 636 且 invalid=0，再恢复隔夜训练。

## Windows 状态文件共享冲突补丁

状态：训练已推进至 1077/1452 后因 status.json 原子替换瞬时 WinError 5 退出；SQLite 1077 个完成结果安全，当前先修复再从同一断点恢复。

1. status.json 是可丢弃的观测投影，不得因浏览器/杀毒软件短暂占用而终止规则训练；原子替换须对 Windows PermissionError 做有界退避重试，重试耗尽时跳过本次状态刷新并保留旧文件。
2. checkpoint.json 仍是阶段权威检查点：同样重试瞬时共享冲突，但持续写入失败必须抛错，禁止伪装成已持久化。
3. 心跳线程不得因单次面板写入异常永久退出；增加瞬时失败恢复、持续状态写失败非致命和原子文件完整性测试。
4. 修复提交、聚焦测试和全量回归通过后，以 --resume 从 1077 恢复，确认面板心跳、完成数增长、invalid=0 和 stalled=false。

## 全真实模式联赛修订

状态：已在提交 46006a9 切换为三个想定全部真实模式，并以 c4e69ed 修复想定 1 预备增援编队误解散；新联赛已恢复至 493/1452、invalid=0、stalled=false。

1. 想定 1、想定 3、二马的收益矩阵、最佳响应和 fresh-seed 均设置 realistic_command=true；经典模式只保留独立回归测试，不进入策略适应度。
2. 新训练规则集固定为 realistic-v1，任务键、结果行和矩阵过滤均携带 ruleset，禁止混用旧经典结果。
3. 新输出目录为 rl/results/psro-realistic-v1；旧 psro-torpedo-v1 完整保留作审计。只迁移其中 scenario=IBS-S-EM-01、ok=true 的真实二马结果，想定 1/3 必须按真实模式重跑。
4. 面板继续使用 127.0.0.1:8765；expected_games 只统计新规则集任务。正式启动前分别测量三个想定的真实状态机单局耗时，并在面板说明总时长来自约 1452 局矩阵加三轮、六代、32 个体的数万场联赛，而非 LLM 等待。

## GA 极端参数编队合法性收口

状态：初始 1452 局矩阵 100% 合法；第 0 轮前两代 3064 个最佳响应任务中出现 12 个非法结果，训练已暂停并保留 4516 行检查点。

1. 将降速非法、脱队后区间不兼容、舵损撤退 120°、尾舰速度超限四类错误作为同一编队恢复问题处理；不得用失败惩罚掩盖规则非法。
2. 每次脱队后，从未强制脱队成员中确定性选择成员数最多、包含原领舰优先、接近原编队速度优先的共享合法速度群；其他舰永久进入撤退控制器。
3. follower speed、脱离引导航迹和强制移动冲突直接触发脱队重算，不再先盲目逐级降速；普通路线冲突仍允许有界降速/紧急停车。
4. 撤退候选在 movement_preview 之外显式过滤舵损禁止的 120° 和强制直航禁止的转向；最终仍由 validate_orders 独立复核。
5. 重跑现有完整真实模式种子和最大合法成员群单元测试；提交后 --resume 只重跑 12 个 ok=false 键与中断键。invalid 清零后继续全部 PSRO 训练，最终运行冠军对局测试与鱼雷战术复盘。

# 大厅新手动线与“二马”大舰队真实模式教学（2026-08-30）

状态：已完成。本批次只改造用户入门、教学编排和教学专用确定性事件，不更改原版裁决表。编队、继承、共同航速和自动撤退属于 `IBS-R-RC-*` 项目扩展；教学预置事件使用独立 `IBS-TUT-EM-*` 标识，不伪装成原版随机战果。

1. **大厅三步入门**：首屏先选择“先学会 / 立即对战”，再选经典或真实模式，最后选想定、阵营和对手。每张卡写明学习内容、时长、难度及唯一主操作；尚未选择 LLM 时隐藏 API 高级配置。
2. **双教学路线**：保留想定 3 经典夜战入门并同步当前图形化移动、引擎建议和半自动填单；新增“二马·大舰队指挥学院”，固定 `IBS-S-EM-01 + realistic_command=true`，日方玩家与隔离教官使用同一合法行动接口。
3. **手把手教练**：教学卡按回合/阶段展示“为什么、现在点哪里、完成检查、下一步结果”，提供一键填入引擎合法示范、自由修改和检查清单，不再只用六张静态阶段卡。
4. **大炮巨舰节奏**：依次覆盖六队初设、战列线与指挥链、主力舰齐射、领舰航路、共同航速危机、全队降速/受损舰脱队、脱离撤退及终局评分；地图、舰船记录表和战报同步解释状态变化。
5. **可审计固定事件**：仅在二马教学生效。首轮火力演示后通过确定性可回放事件安排一艘队列舰轮机战损，迫使玩家在下一移动阶段选择全队降速或受损舰脱队；记录脚本 ID、目标舰及速度轨损失前后值，正式对局不得触发。
6. **验收**：经典教学可一键进入并完成至第二回合；二马教学可完成编队初设、主炮齐射、速度危机和降速/脱队分支；回放一致、正式局无脚本污染、隐藏计划不泄露。运行专项、全量 pytest、TypeScript、Vite 与浏览器新手动线验收。

## 教学隔离与强制交互教练修订

状态：已完成（提交 `344ca65`）。本批只改教学编排和可访问性交互，不改规则核心、想定数据或裁决常量。

1. 教学类型由布尔值改为显式 `classic/grand`，并以游戏、想定、回合和阶段组成独立进度键；二马永远不得渲染通道行动的旧填单提示。
2. 用强制交互教练替代长篇教学计划：每次只提示一个动作，自动滚动并高亮真实控件，遮挡和拦截其他点击；完成指定点击后才进入下一步。
3. 编队初设、移动、鱼雷、炮击、同步裁决和战报分别绑定当前 UI 的实际按钮或输入控件；控件尚未出现时显示等待状态，不允许跳到错误的旧步骤。
4. 提供明确的“当前动作/完成反馈/规则出处”，但不展示思维链；键盘焦点、Esc 暂停及小屏幕定位必须可用。
5. 验收包括：二马首阶段无经典提示、两条教学路线状态互不污染、错误区域点击被阻止、目标点击推进、阶段变化自动换课，以及 TypeScript/Vite 构建和相关测试通过。
