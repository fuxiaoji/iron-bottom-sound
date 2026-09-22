# 00_EXECUTIVE_SUMMARY.md · 命令延迟模式 v2.2 实施

## 结论

命令延迟模式按 `IBS_COMMAND_DELAY_MODE_V2_2_RULES_AND_IMPL.md` 分 CD-0…CD-6 七个阶段实施完毕，全部为**新增**：Classic 与既有 Realistic 语义冻结并有可复现的黄金基线，`MOVE_TOGETHER` 作为可选编队机动方式默认关闭，命令延迟模式不改变 `realistic_command` 的含义。

```
COMMAND_DELAY_MODE_V2_2_COMPLETE = YES
CLASSIC_REGRESSION               = PASS
REALISTIC_FROZEN_DEFAULT         = PASS
MOVE_TOGETHER                    = PASS
COMMAND_DELAY                    = PASS
INFO_LEAKAGE                     = PASS
GUNNERY_AUTHORITY                = PASS
PI_REVIEW_REQUIRED               = YES
```

## 分阶段交付

| 阶段 | 内容 | 关键证据 |
|---|---|---|
| CD-0 | 冻结 tag `realistic-command-v1-frozen`（`d432a975`）+ 7 行黄金回放基线（Classic/Realistic × S01/S03/EM01 + seed9）；发现并修复既有缺陷 CD0-F1 | `01_FREEZE_REGRESSION_AUDIT.md`、`audits/audit_freeze.json` |
| CD-1 | `formation_maneuver.py`：`MOVE_TOGETHER` 可选编队机动、几何/轴线索状态、`REFORM_COLUMN`；默认仍是 `FOLLOW_WAKE` | `02_MOVEMENT_STYLE_AUDIT.md`、`audits/audit_movement_style.json` |
| CD-2 | `command_delay.py` 模式外壳（选项/权限状态/逐阶段 tick）+ `command_observation.py`（舰队视图 / 编队本地视图） | `05_OBSERVATION_LEAKAGE_AUDIT.md`、`audits/audit_leakage.json` |
| CD-3 | `communications/`（媒介配置 / 路由 / 队列 / 完整性接缝）+ `MissionOrder` + 三类备选方案 | `03_COMMUNICATION_PIPELINE.md`、`04_MISSION_ORDER_AND_CONTINGENCY.md` |
| CD-4 | `target_priority.py`（优先级→引擎选择器）+ `formation_agents.py`（确定性本地代理） | `07_TARGET_PRIORITY_SELECTOR_AUDIT.md`、`audits/audit_gunnery_authority.json` |
| CD-5 | `formation_llm.py`：LLM 本地代理适配器（action id、无炮击、审计/重试/合法性） | `06_FORMATION_AGENT_INTERFACE.md` |
| CD-6 | `contracts.py` + `research_hooks.py`：契约状态、激励账本、张量接口、回合导出 | `DATA_MODEL_DIFF.md`、`06_FORMATION_AGENT_INTERFACE.md` |

## 验收标准逐条

| # | 标准 | 结果 | 证据 |
|---|---|---|---|
| 1 | Classic 回归：不变 | PASS | 黄金基线 3 行 Classic 在 CD-0…CD-6 全程 0 漂移 |
| 2 | Realistic 默认 `FOLLOW_WAKE`：冻结黄金回放不变 | PASS | 7 行 0 漂移；冻结面新增键仅 4 个、均为新增字段 |
| 3 | Realistic `MOVE_TOGETHER`：仅新增测试 | PASS | 20 项测试；默认路径未触碰 |
| 4 | 命令延迟不向舰队总指挥泄漏远端编队精确状态 | PASS | `audit_leakage`：只有被搭载编队是精确状态；远端一律为带年龄的报告 |
| 5 | 编队代理不获得本方全局真值 | PASS | 本地视图无 `score/sealed_orders/...`；接触由本编队自身舰只可见性算出 |
| 6 | 编队代理不能提交炮击命令 | PASS | 决策类型无炮击字段；结构守卫拒绝；引擎拒绝原始炮击批次 |
| 7 | 目标优先级只改偏好，不改合法性/命中规则 | PASS | 54 条封存炮击命令全部对当回合候选集合法；非法数 0 |
| 8 | 延迟报文分别保留发出/送达/观察到回合 | PASS | 每条已送达报文三字段齐备且 `delivered ≥ issued` |
| 9 | 迟到的被取代命令不能覆盖更新的已确认命令 | PASS | 订单与报告两条路径都以**发出时间**判新旧，拒绝被记录 |
| 10 | 每个消息事件与本地代理决策可复现/可审计 | PASS | 跨 `PYTHONHASHSEED∈{0,1,2,5}` 全局面板摘要一致 |
| 11 | 未捏造历史概率；任意参数标注为仿真抽象 | PASS | 传播延迟固定 0 并写明；`p_drop/p_garble` 无来源即拒绝执行 |
| 12 | 确定性模式未通过全部测试前不实现 RL/GNN/Transformer | PASS | CD-6 仅接口，`implemented_learning=False` |

## 实施期间发现并修复的缺陷

| 编号 | 缺陷 | 性质 | 处置 |
|---|---|---|---|
| CD0-F1 | `engine.py` 碰撞解冲突循环遍历 `set[frozenset]`，事件顺序随字符串哈希变化（`realistic_s01` 行 4 个种子里 2 个不同） | 既有缺陷（同函数 20 行外的骰点路径已修过同类） | 用同一规范排序键修复；修复后**0 个冻结值变化**，7 行全部哈希种子稳定 |
| CD0-F2 | 两个"哈希种子确定性"测试因未传 `PYTHONPATH` 而从未真正运行 | 既有测试夹具缺陷 | 未修（不在授权范围），改用 `golden_replay.py --probe-hash-seeds` 作为该契约的**有效**验证；列为 PI 裁决项 |
| CD3-F1 | 报文到达顺序与新鲜度顺序不同，旧报告可覆盖舰队更新的认知 | 新代码缺陷（CD-3 实现中） | 报告与订单统一按**发出时间**（同回合按阶段序）比较，拒绝并记录被取代 |
| CD2-F1 | `command_delay_initialised` 事件载荷包含**双方**指挥链 | 新代码缺陷（CD-2 实现中） | 改为每方一条事件并带 `secret_side`；泄漏审计现在直接检查该属性 |
| CD8-F1 | 中立战报把双方指挥链、代理决策与激活分支收进同一份文档（交付评审发现） | 新代码缺陷 | 按前缀排除整个命令延迟事件族；中立战报 0 项私有事件 |
| CD8-F3 | `LOCAL_AUTONOMY` 稳态下几乎不可达，权限标签与 agent 行为自相矛盾 | 新代码缺陷 | `STALE` 同样降级为 `LOCAL_AUTONOMY`，与 `activate_branches` 的既有定义一致 |
| CD8-F4 | 舰队总指挥**所在**编队的链路被按报告年龄算成 `STALE` | 新代码缺陷 | 被搭载编队链路恒为 `DIRECT`、权限恒为 `FLEET_DIRECTED` |
| CD8-F5 | 我的 API 泄漏检查两轮误报（把正常发现的接触、以及沉没后留在残骸/公开事件里的舰只当成泄漏） | 审计缺陷 | 改为可判定问题：`GET /view == engine.observe(side)`，58/58 一致 |

完整时间线（含我自己的审计脚本错误）见 `BUG_AND_RERUN_LOG.md`。

## 平台基线更新（PI 裁决 b：并入 data-entry 分支）

平台已并入 `glm/data-entry-and-briefing`：**16 个想定全部可玩**（含虚构 FM-01）、想定简报、class-cards 与想定特殊规则引擎。合并 4 处冲突均为追加型；`engine.py`/`models.py`/`realistic_command.py` 自动合并。

两处合并引出的问题已修复：
- **S-08/S-09 的默认编队建议会自相交**（两条纵队穿过同一格，引擎正确拒批）→ `default_setup_orders` 现在对提议自去冲突（按编队顺序对航向做深度优先搜索；先转后队，后队领舰锚点被前队穿过时转前队）。16/16 想定产出可直接提交的初设；基线三想定航向不变（黄金回放未再冻结即通过）。
- `run_audits` 的 data_model 审计曾把"信封为空"当失败——基线更新后信封为空恰是健康态，判定权归 freeze 审计。

重冻结归因记录在 `golden/GOLDEN_INDEX.json` 的 `refreeze` 字段（4 行因 data-entry 规则变更而变，已逐一归因：单独测该分支漂移行与合并后完全相同）。最终状态：**全量 683 通过 / 3 失败 / 2 跳过（失败集合与合并前逐字节相同）；8/8 审计 PASS；18 局实机矩阵 PASS；黄金回放与哈希种子稳定性 PASS**。

## 交付评审问答（用户直接提出的五个问题）

| 问题 | 当时的实际状态 | 现在的答案与证据 |
|---|---|---|
| 完整打过几局？ | 只跑过 2 个 (想定, seed) 组合；**没有**跨全想定矩阵 | **18 局完整对局**：3 想定 × 3 seed × {命令延迟, 真实对照}，全部 `COMPLETE`，0 友军碰撞、0 友军鱼雷命中（`logs/verify_live.log`、`verify_game_matrix.json`） |
| 有信息泄露吗？ | 引擎层审计过，**API 层从未测过**，且中立战报确实在泄漏 | 引擎层 0 发现；API 层 `GET /view == engine.observe(side)` **58/58 一致**；**修复了中立战报携带双方指挥链的泄漏**（CD8-F1） |
| 子 agent 能独立执行任务吗？ | 只有"链路正常时"的间接证据 | 切断某编队**全部**双向通信后：仍 19/19 次自主决策、每次选出合法机动、整局打完，期间 `LOCAL_AUTONOMY`（并修掉了 CD8-F3/F4 两处让该状态几乎不可达的标签缺陷） |
| 用测试 api 试过吗？ | **完全没有** | 用 FastAPI `TestClient` 通过真实端点打完一整局：创建（含模式选项）/取视图/提交订单/推进/舰队视图/编队视图/规则文档；门控 409（真实模式下无舰队视图）与 404（对方编队视图）均正确 |
| 有战报吗？ | **没有测过** | 命令延迟模式下战报管线正常（87 条记录、6.0 MB 自包含 Markdown）；并修掉其私有信息泄漏。同类既有问题（`formation_created` 等）列为裁决项 CD8-Q1 |

## CD-10 交付评审追加（用户实测后指出的四项缺口）

用户实测后指出：每个小编队应当由自己的 LLM 代理指挥**并且有记忆**；大厅里命令延迟模式不该有状态机；编发命令与收发报应在**移动阶段用自然语言**完成；调试模式应能看到每个 LLM 的思考、输出与记忆。四项当时都**确实不存在**（代理只接了确定性策略、没有任何记忆、没有自然语言命令通道、没有代理可见性），已全部实现并测试。

| 缺口 | 实现 | 验证 |
|---|---|---|
| 每编队一个 LLM 代理 | `FormationLLMAgent` + `ProviderPolicy`（复用项目既有 httpx 传输）；`command_delay.side_agent` 按侧选择；密钥只在进程内存，`policy_labels` 只记标签 | stub 客户端跑完整一局：31 次调用全部解析成功、局面终局、0 友军碰撞 |
| 记忆 | `formation_memory.py`（IBS-R-CD-08）：当前命令原文、自有备忘、见过的接触、历次决策、发出的报告；有界裁剪、只含本编队材料 | 16 项测试含"记忆不得含未见过的敌舰"与边界裁剪 |
| 大厅无状态机 | 选中命令延迟即切到 LLM 连接并禁用"状态机 AI"入口；start 校验模型名与密钥 | 浏览器实测：入口禁用且提示原因 |
| 自然语言下达命令（移动阶段） | `draft_natural_order`：命令是一项**信号**，按距离/视距选媒介、进队列、可延迟可丢失；送达后原文写入该编队记忆，并原样进入代理提示词 | 实测 T2 移动阶段发出、TBS 复杂命令 +1 回合、T3 送达，命令原文入记忆 |
| 调试可见 | `/command-delay/agent-log`（按阵营过滤）+ 面板显示提示词、每次尝试的原始回复与拒绝原因、解析后的决策、记忆与条目计数 | 浏览器实测渲染；端点跨阵营测试 |

**成本形态（用户需知）**：配置密钥后，每"编队×回合"是一次模型调用（想定 1 约 30–60 次/局，EM-01 更多）；无密钥时各编队按确定性教条行动，界面与事件都会明确标注 `deterministic-formation-v1`，不会把教条输出冒充为模型输出。

## 实机验证（交付评审补做）

评审问题"完整打过几局 / 有 API 吗 / 子代理能独立执行吗 / 有战报吗"暴露出此前的空白，均已补测并固化为测试（`verify_live.py` + `tests/test_command_delay_live_surface.py`）：

| 项目 | 结果 |
|---|---|
| 完整对局数 | **18 局**：3 想定（S-01/S-03/EM-01）× 3 seed × {命令延迟, 真实对照}，**全部到达 COMPLETE**；0 次友军碰撞、0 次友军鱼雷命中 |
| 命令延迟特有统计 | 每局 8–59 次代理决策、0–273 条报文、0–162 条投递；EM-01 达 12 回合 |
| HTTP API | 通过 `TestClient` 用真实端点打完一整局：`/view` 与引擎过滤视图 **58/58 逐次一致**；模式门控 409/404 正确；`/advance` 与 `/events` 未返回对方任何私有事件 |
| 子代理独立性 | 把某一个编队的链路**完全切断**（双向、含报告）：该编队仍 19/19 次自主决策、每次都选出合法机动方案、整局打完，期间处于 `LOCAL_AUTONOMY`；舰队只持有它的过期报告 |
| 战报 | 命令延迟模式下战报管线正常（87 条记录、Markdown 6.0 MB 自包含）；**修复了中立战报携带双方指挥链的泄漏** |

## 全量回归

`.venv/bin/python -m pytest -q`：**637** 项收集（其中本阶段新增 108 项），跑完 100%，失败集合与**改动前基线逐字节相同**（3 项既有失败）：

| 既有失败 | 性质 |
|---|---|
| `test_api_llm_storage.py::test_tutorial_api_reaches_second_turn_and_serves_canonical_counter` | 计数器素材 sha256 与硬编码期望不符（素材问题） |
| `test_tactical_ai.py::test_collision_resolution_is_deterministic_across_hash_seeds` | 测试夹具未传 `PYTHONPATH`，比较阶段从未执行（CD0-F2） |
| `test_tactical_ai.py::test_ai_orders_deterministic_across_hash_seeds` | 同上 |

即：**没有引入任何新失败**（`diff` 两份 `FAILED` 列表为空输出）。

## 待 PI 裁决项（本轮未擅动）

| 编号 | 事项 | 现状 | 为什么不由我决定 |
|---|---|---|---|
| CD0-Q1 | 编队数量上限：玩家规则文档写"一至四个编队"，代码 `MAX_FORMATIONS_PER_SIDE = 8`（注释称用户裁定） | 两侧都未改 | 改代码会动冻结文件；改文档需要确认该裁定是否仍有效 |
| CD0-Q2 | 两项既有"哈希种子确定性"测试因未传 `PYTHONPATH` 而从未真正运行 | 未修，已用 `--probe-hash-seeds` 作为有效替代验证 | 修测试夹具会改动既有测试行为，超出本轮授权 |
| CD8-Q1 | 中立战报同样收录 Realistic 模式下的 `formation_created`（2 条）与 `movement_plan_resolved`（27 条），二者都带 `secret_side`；且规则文档明说编队关系是秘密信息 | 未改，保持既有行为 | 修它会改变现有战报内容与叙事输入；这是"中立战报的信息边界"这一产品决策 |
| CD8-Q2 | 本模式下 `CommandDelayState` 含会话内全量报文台账（约 300 条上限后按最近保留） | 已做有界裁剪 | 若要做长期科研归档，需要你决定归档粒度与保留策略 |
| A-1 | 早前 Phase A 的 `SELECTED_MAINLINE` 仍为空 | 未填 | 主线选择是你的决定 |

## 未越界的事项

- **未**开始任何科研实验；**未**实现 RL/GNN/Transformer；**未**调用任何付费 LLM（CD-5 全部用 stub/录播策略）。
- **未**改动 `realistic_command.py` 的既有语义：该文件仅有 4 处插入（2 处 import、1 处分派+闸门、1 处 `after_movement` 调用、1 处 `choose_plan` 分支），全部由新模式或新样式启用，默认路径由黄金回放证明逐字节不变。
- **未**手工改写任何来源文件。
- **未**新增任何历史概率数值；媒介回合值全部标注 `SIMULATION_ABSTRACTION`。
