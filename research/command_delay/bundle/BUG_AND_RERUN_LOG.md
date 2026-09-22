# BUG_AND_RERUN_LOG.md

按发现顺序记录本轮实施期间发现并处置的缺陷，包含**我的审计脚本自身的错误**（它们同样会制造假结论）。每条都给出可核查的原始证据路径。

---

## CD0-F1 · 冻结面上的既有非确定性（既有缺陷，已修）

**发现方式**：CD-0 基线首次构建后立刻 `--check`，`realistic_s01` 行失败；同一工作树、同一提交，跨进程摘要不同。

**现象**：`realistic_s01` 在 `PYTHONHASHSEED=0` 下摘要 `917114fbb1dd`，在 1/2/8 下为 `10679a78338d`。其余 6 行在四个种子下稳定。

**定位**：对两棵树逐叶 diff，全文仅 12 条差异，均为：

```
events[352].payload.ship_ids[0]   HS0="IBS-U-USN-BUCHANAN"  HS1="IBS-U-USN-HELENA"
events[353].payload.ship_ids[0]   HS0="IBS-U-USN-HELENA"    HS1="IBS-U-USN-BUCHANAN"
```

即 `formation_emergency_stop` 两条事件顺序互换；`ships`/`orders`/`rng_counter`/`n_events` 全部一致。根因：`engine.py:3124` 原生遍历 `set[frozenset[str]]`。

**性质判定**：同函数 20 行外（`engine.py:3144`，骰点路径）已用规范排序键修过同类缺陷，仓库也有专门测试记录该症状——哈希种子无关性是本仓库已声明的契约，这是漏改的孪生分支。

**修复**：`engine.py:3124` 改为 `sorted(collision_sets, key=lambda group: sorted(group))`。

**验证**：修复后 `realistic_s01` 摘要仍为 `917114fbb1dd`（与修复前基线逐字节相同）→ **0 个冻结值改变**；7 行全部稳定（`logs/cd0_hash_seed_probe_postfix.log`）。

**证据**：`logs/cd0_hash_seed_probe.log`（修复前）、`logs/cd0_hash_seed_probe_postfix.log`（修复后）、`audits/cd0_hash_seed_probe.json`、`research/command_delay/cd0/CD0_FREEZE_EVIDENCE.md` §4。

---

## CD0-F2 · 两项既有确定性测试实际上从未运行（既有夹具缺陷，未修）

**发现方式**：CD-0 基线测试套件（改动前）出现 3 项失败，其中两项的名字正是"哈希种子确定性"。

**现象**：

```
AssertionError: Traceback (most recent call last):
    from iron_bottom_sound.engine import IronBottomEngine, ORDER_PHASES
ModuleNotFoundError: No module named 'iron_bottom_sound'
assert 1 == 0
```

**根因**：测试用 `sys.executable -c SCRIPT` 起子进程，未传 `PYTHONPATH=backend/src`；pytest 的 `pythonpath` 配置不继承给子进程。断言 `returncode == 0` 因此在**任何**代码状态下都失败，比较阶段从未执行。

**处置**：本轮未修（超出本任务授权范围）。改用 `golden_replay.py --probe-hash-seeds`（显式传 `PYTHONPATH` 与环境变量）作为该契约的有效验证，并在 `logs/` 留两份对照日志。列为 PI 裁决项 CD0-Q2。

**证据**：`logs/cd0_pytest_baseline.log`。

---

## CD0-F3 · 黄金基线自身不可复现（我的脚本缺陷，已修）

**发现方式**：基线构建后的第一次 `--check` 七行全部 `DRIFT`。

**现象**：`digest_events` 变化而其他面全部稳定；首个差异是 `game_created` 载荷里的 `game_id`。

**根因**：`Engine.reset` 每局生成新 UUID 并写进 `game_created` 事件。任何整树摘要都不可能复现。

**修复**：录制前递归掩码该局的 `game_id` 为 `<GAME_ID>`（不止掩码首个事件，而是走遍嵌套容器，避免未来载荷重新引入该非确定性）。

**证据**：`research/command_delay/golden_replay.py` 的 `_mask`。

---

## CD0-F4 · 冻结投影比较被引入以分离"语义漂移"与"信封增长"（方法修正）

**发现方式**：CD-1 加入两个可选订单字段后，若用朴素字节 diff，Realistic 行会立刻报"漂移"，但那只是 `model_dump` 多出两个 null 键，语义并未改变。

**修复**：改为**冻结投影**比较——递归成对，只忽略冻结时不存在的 dict 键；已存在键的值必须完全一致、列表长度必须相等。新增键单独报告为 `envelope_keys_added`。这样两类问题不再混淆，且不可能掩盖嵌套载荷内的真实变化。

**证据**：`research/command_delay/golden_replay.py` 的 `project` / `envelope_added`；`DATA_MODEL_DIFF.md`。

---

## CD1-F1 · `MOVE_TOGETHER` 的"同方案"检查位置（实现修正）

**发现方式**：CD-1 测试首轮，`test_body_movement_requires_every_member_to_commit_the_same_program` 依赖损伤强制条件，起初只用 `_legal_speed_range` 判断，漏掉了"首命令必须是 advance"、转向限制、地形与地图边界。

**修复**：资格检查改为逐舰 `engine.movement_preview(plan).commitable`——该边界已包含 `_legal_speed_range`、`turn_limit_degrees`、`forced_straight_turns`（含 `forced_speed`）、`forced_circle_turns`（含转向侧向）、地形与出界。即**复用引擎自己的合法性边界**，不在新模块里重写规则。

**证据**：`formation_maneuver.eligibility` 的注释与 `tests/test_command_delay_movement_style.py`。

---

## CD2-F1 · 初始化事件泄漏双方指挥链（新代码缺陷，已修）

**发现方式**：`audit_leakage` 首次运行即报 `command-delay events without secret_side: ['command_delay_initialised']`。

**现象**：`command_delay_initialised` 的载荷包含**双方**的 `authorities`（每方总指挥所在编队与旗舰舰 id），且不带 `secret_side`，因此引擎既有的事件过滤对它无效——对手的编队、旗舰与总指挥舰会被一次性交出。

**修复**：改为每方一条事件并带 `secret_side`（与 `command_delay_turn_state` 一致）。审计把"命令延迟类事件必须带 `secret_side`"写成硬条件，当前 175 条命令延迟事件全部通过。

**证据**：`command_delay.initialise`、`audits/audit_leakage.json` → `command_events.without_secret_side: []`。

---

## CD2-F2 · 本地地图窗口构造越界（新代码缺陷，已修）

**发现方式**：CD-2 测试 `test_formation_view_uses_local_contacts_not_the_side_plot` 报 `ValidationError: q  Input should be greater than or equal to 0`。

**现象**：`local_map_hexes` 直接用 `HexCoord(q=position.q + dq, ...)` 构造邻域，地图边缘处 q 为负，而 `HexCoord` 拒绝负列。

**修复**：在**构造之前**用原始整数做边界检查，越界即跳过；显示行同样先算后判。

**证据**：`command_observation.local_map_hexes`。

---

## CD3-F1 · 报文到达顺序被误当作新鲜度顺序（新代码缺陷，已修）

**发现方式**：CD-3 集成测试 `test_coded_reports_arrive_after_they_were_drafted` 断言"舰队持有的应是发出时间最新的报告"时失败。

**现象**：航程会交叉——同回合的 TBS 报告可以超过更早发出的编码报告，于是旧报告在到达时覆盖舰队更新的认知，舰队知识**倒退**。

**修复**：报告与订单统一按**发出时间**判定新鲜度（同回合用阶段序打破平局）；被取代者标记 `MessageStatus.SUPERSEDED`、原因写明"被第 N 回合更新的报告超过"，并保留在台账中。为此 `FormationCommandState` 增加 `reported_phase`（同回合内更晚的阶段是更新的世界）。

**证据**：`command_delay._apply_delivery`、`tests/test_command_delay_communications.py::test_a_late_superseded_order_cannot_overwrite_a_newer_one`。

---

## CD4-F1 · 未收到命令时代理崩溃（新代码缺陷，已修）

**发现方式**：CD-4 首次整局运行抛 `AttributeError: 'NoneType' object has no attribute 'contingencies'`。

**现象**：`activate_branches` 要求一个订单，但新回合开始时编队可能尚未收到已确认命令（链路延迟之下这是常态）。

**修复**：新增 `delegation.standing_plan()`——一条结构完整的预令（"尚无上级命令：继续当前任务并按预令行动"），代理对它执行同一套教条阶梯，审计记 `order_received: false`。即"没有命令"不等于"可以自创任务"。

**证据**：`delegation.standing_plan`、`formation_agents.act`。

---

## CD5-F1 · 既有 AI 在命令延迟模式下提交原始炮击（集成冲突，已修）

**发现方式**：CD-4 首次整局运行，`RealisticCommander` 经 `TacticalCommander` 在 GUNNERY 阶段提交原始 `GunneryOrder`，被新的权限闸门拒绝。

**判定**：拒绝是**正确**的（这就是验收 6），但既有 AI 因此无法驱动新模式。

**修复**：`RealisticCommander.choose_plan` 增加一条受 `command_delay_mode` 保护的分支：命令延迟模式下 GUNNERY 阶段只提交 `target_priorities` 批次，由引擎选择器生成最终炮击命令。既有模式完全不进入该分支。

**证据**：`realistic_command.choose_plan`、`command_delay.gunnery_batch`。

---

## CD5-F2 · 我自己的炮击权限审计测量位置错误（审计缺陷，已修）

**发现方式**：`audit_gunnery_authority` 首轮给出 `sealed_gunnery_orders_illegal: 54`（全部非法）与一条"原始炮击批次被接受"的错误结论。

**根因一**：在**终局**状态用 `_gunnery_candidates` 判定第 3 回合的订单——棋盘早已不同，54 条当然全部"非法"。**这是典型的用当前环境评判历史决策，会得出完全错误的科学结论。**
**根因二**：在 `state.phase == COMPLETE` 时提交原始炮击批次做对抗测试，得到的拒绝理由是"该阶段不可提交订单"，与权限边界无关。

**修复**：审计改为在**每个 GUNNERY 阶段当场**用当时候选集判定，并在批次被接受后立即复核（读 `submitted_orders`，因为封存发生在 `advance` 内）。对抗测试同样在真实的 GUNNERY 阶段发起。结果变为 `checked: 54, illegal: 0`，且每次原始炮击提交都被以正确理由拒绝。

**证据**：`research/command_delay/run_audits.py` 的 `audit_gunnery_authority`、`audits/audit_gunnery_authority.json`。

---

## CD6-F1 · 前向引用导致的 pydantic 重建失败（新代码缺陷，已修）

**发现方式**：`CommandDelayState.decisions` 起初标注为 `list[FormationDecision]`，在 `models.py` 的模块级 `model_rebuild()` 处抛 `PydanticUndefinedAnnotation`。

**根因**：`FormationDecision` 定义在 `formation_agents.py`，`models.py` → `formation_agents` 会形成导入环（后者依赖前者）。

**修复**：决策账本改存 `list[dict[str, Any]]`（`model_dump` 结果）。这同时更贴合它的性质——账本是审计记录而非活对象图。CD-6 的 `ContractState` / `LedgerEntry` 则按本仓库的既有约定直接放进 `models.py`，`contracts.py` 只做再导出与行为，彻底消除环。

**证据**：`models.CommandDelayState`、`contracts.py`。

---

## CD6-F2 · 泄漏审计自身的检查过宽与过严（审计缺陷，已修，三轮）

**发现方式**：`audit_leakage` 改写为对局中采样后连续失败三次。

**第一轮（过宽）**：把"任何地方出现对方舰 id"都当泄漏，于是把舰队视图**自己的 `contacts` 目视图**与编队视图**自己的 `local_contacts`**全判为泄漏——那正是目视的意义所在。
**修复**：把允许块（`contacts`；`local_contacts` + `legal_target_priority_options`）单独处理，并与引擎自身的 `_visible_to` 逐点比对，要求"恰好等于自己看到的东西"；同时断言接触条目不携带舰体/修正等额外键。

**第二轮（过严，且检查空洞）**：`len(exact) != 1` 硬要求"恰一个精确编队"，于是在旗舰编队已被击沉的第 5 回合报错；而在改前只在终局采样的版本里，某些行因一方已无编队而**空洞通过**。
**修复**：改为条件式规则——被搭载编队在水面上时必须是唯一精确项；不在水面上时**不得有任何精确项**；并要求至少 2 个采样点，否则审计自身判失败。

**第三轮（过严）**：加权目标块被当作泄漏。
**修复**：允许该块，并断言其 target id ⊆ 本地目视集（即不得对未目视目标加权）。

**证据**：`audits/audit_leakage.json`（当前 0 findings，5 个采样回合、10 条舰队记录、19 条编队记录）。

---

## CD7-F1..F4 · 全量测试后的自审修正（新代码缺陷，已修）

**发现方式**：全量套件（637 项）跑完后逐模块自审，共 4 处：函数签名残留未用参数、死分支、地平线取错方、张量规格与实测不符。

1. `delegation.own_hull_fraction` 保留了一个未使用的 `engine` 参数，调用方传 `None` —— 删参并改调用。
2. `target_priority.priority_bonus` 的 `if not directives: return 0.0` 是死分支（空集本来就合成 0.0）—— 删除，并把"无指令 = 基础期望命中选择、教条只能叠加在已声明偏好之上"写进 docstring。
3. **`command_observation._optical_range` 返回的是双方视距的较小值**，于是某一方视图的地平线可能取自对手的视距 —— 改为按请求方自身视距（与引擎 `_visible_to` 同一值），无方参数时保留保守回退并写明。
4. `research_hooks` 的目标块把"声明备选方案数"命名为 `active_branches`（哪一条**激活**是代理的决策，不属于观察数据）；接触块的 `bearing_sin/bearing_cos` 实际是 `sin/cos(0,0)` 占位值 —— 改名为 `declared_contingencies`，并把方位改为在**引擎同一轴向格**上算出的真实绝对罗经方位（六个方向逐一单测校验）。

第 3 条是真正有行为影响的：地平线从"min(双方)"变为"本方自身"，方向正确但此前在双方视距不同的想定上会给错半径。

修正后重跑：108 项命令延迟测试全过、8 项审计全过、黄金回放仍 0 漂移。

**证据**：提交 `e1ddd050`；`audits/audit_*.json`（修正后重新生成）。

---

## CD8-F1 · 中立战报携带双方指挥链（新代码缺陷，已修）

**发现方式**：交付评审问"有战报吗"。此前**从未**在命令延迟模式下启用过战报，于是补测：`battle_report=True` + 命令延迟模式跑完整一局，然后扫描战报 JSON 与 Markdown。

**现象**：`public_events_for_turn` 的规则是"至少一侧可见的公开事件并集"，而命令延迟事件各自只属于一方 —— 并集因此把双方的私有指挥信息全收进来：`command_delay_initialised`（2）、`command_delay_turn_state`（8）、`formation_agent_decision`（8，含激活的备选分支与本地权重调整）。即中立战报里能读到对方的指挥链状态与代理决策。

**修复**：`battle_report.PRIVATE_EVENT_PREFIXES` 按前缀排除整个命令延迟事件族（`command_delay_` / `command_message_` / `formation_agent_` / `mission_order`），理由与既有 `orders_submitted` 排除一致：战报是对双方开放的中立文档。按前缀而非逐个类型名，是为了让该族将来新增的事件不能悄悄重新引入泄漏。

**同时**：`formation_reformed` / `formation_reform_rejected` 原先不带 `secret_side`，而载荷含本编队成分配置（`measure_line().as_payload()`）——改为与 `formation_created` 一致地标记为私有。

**验证**：修复后该检查 0 项发现；既有 22 项战报测试全过。

---

## CD8-F2 · 交付评审的三个问题暴露了两处真实空白（方法缺陷，已补）

**发现方式**：用户问"完整打过几局 / 用测试 api 试过吗 / 有战报吗"。

**事实**：此前只跑过 2 个 (想定, seed) 组合；**从未**调用过 HTTP API；**从未**在本模式启用战报。这些都是真实空白，不是"已覆盖但没写下来"。

**处置**：新增 `research/command_delay/verify_live.py`，四部分：18 局完整对局矩阵（3 想定 × 3 seed × {命令延迟, 真实} 对照）、HTTP API 全流程一局、切断单编队链路的自主性探针、战报管线。另把四项固化为 `tests/test_command_delay_live_surface.py`（6 项）。

---

## CD8-F3 · `LOCAL_AUTONOMY` 在实际对局中几乎不可达（新代码缺陷，已修）

**发现方式**：自主性探针报告 `formations_in_local_autonomy: []`，而同一局里 agent 明明在按失联预案行动。

**根因**：权限标签只在 `BLACKOUT` 时降级，而 `BLACKOUT` 对"在编且未搭载"的编队意味着 `reported_turn is None` —— 即**从未收到过任何报告**。稳态下的失联是 `STALE`（报告年龄 ≥ 2），而 `STALE` 当时仍标 `DELEGATED`。于是标签与行为自相矛盾：`delegation.activate_branches` 早已把 "stale or blacked out" 都算作失联并激活 `LOSS_OF_COMM_BRANCH`，我自己的测试也这么断言。

**修复**：`STALE` 与 `BLACKOUT` 同样降级为 `LOCAL_AUTONOMY`（未搭载且仍在编时）。这与模式自身的规则一致，而不是新增规则。

---

## CD8-F4 · 被搭载编队的链路被算成 STALE（新代码缺陷，已修）

**发现方式**：逐回合打印链路状态时看到 `allies-active-light: stal/fleet_/r1` 从第 2 回合起一直不变 —— 而这正是**舰队总指挥所在**的编队。

**根因**：`draft_reports` 不给自己编队发报文（总指挥不需要向自己报告），于是该编队的 `reported_turn` 永不刷新，`refresh_link_status` 便按年龄把它算成逐级退化，最终 `STALE`。登录在旗舰上的总指挥，其指挥链是**物理的**，不需要任何通信。

**修复**：被搭载编队的链路恒为 `DIRECT` 且权限恒为 `FLEET_DIRECTED`（不再由报文年龄推导）。顺带把"编队已解散 → BLACKOUT 且保留历史权限"写成显式注释，避免与上述规则混淆。

---

## CD8-F5 · 我的 API 泄漏检查两次判错（审计缺陷，已修两轮）

**第一轮（过宽）**：把"响应里出现任何对方舰 id"当泄漏，于是把 S-03 开局就处于目视距离内的 5 艘盟军驱逐舰判为泄漏——那是正常的发现接触。
**第二轮（仍过宽）**：改成"与当前可见集比对"后，仍然误报：一艘在目视下沉没的舰会从可见集消失，却合法地留在 `wrecks` 与公开事件里。

**最终形态**：不再猜"哪些敌舰该出现"，而是问一个可判定的问题——**API 是否比引擎自己的过滤视图更宽**：逐次断言 `GET /view == engine.observe(side)`。58 次比较 0 处不一致。这比"扫描敌舰 id"既严格又不会误报。

---

## 无缺陷但需记录的两次测量

- **`test_api_llm_storage.py::test_tutorial_api_reaches_second_turn_and_serves_canonical_counter`**：计数器素材实测 sha256 `5c54f8aa…` ≠ 测试硬编码的 `918196c7…`。属素材内容问题，与引擎无关，**改动前即失败**，未处置。
- **`test_command_delay_mode_shell.py::test_command_delay_rejects_unsupported_scenarios`**：当前可玩想定恰好只有 `SUPPORTED_SCENARIOS` 三个（S-02/S-04 等已编目但不可玩），因此该闸门无法经 `engine.reset` 触发。测试改为直接调用 `command_delay.validate_mode_options`——即 `build_initial_state` 调用的同一函数——并在文档中说明原因，而不是造一个假想定来"跑通"。
