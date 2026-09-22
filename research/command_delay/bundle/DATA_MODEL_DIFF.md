# DATA_MODEL_DIFF.md

命令延迟模式对数据模型的全部改动。原则：**纯新增**——新模型、新枚举、以及**带默认值的新字段**，因此旧存档、旧调用与既有模式逐位兼容。

- 审计记录：`audits/audit_data_model.json`、`audits/audit_freeze.json`
- 验证方式：黄金回放的**冻结投影**比较（`golden_replay.py`）

## 1. 新增枚举（6）

| 枚举 | 取值 | 用途 |
|---|---|---|
| `FormationMovementStyle` | `follow_wake` / `move_together` | 编队机动方式，默认 `follow_wake` |
| `FormationGeometryKind` | `column` / `straight_line` | 编队声明几何 |
| `AuthorityLevel` | `fleet_directed` / `delegated` / `local_autonomy` | 权限状态 |
| `LinkStatus` | `direct` / `relayed` / `stale` / `blackout` | 链路状态 |
| `CommunicationMedium` | `tbs_short` / `blinker` / `wt_coded` / `wt_reencipher_relay` / `multi_hop` / `blackout` | 通信媒介 |
| `MessagePrecedence` | `urgent` / `operational` / `routine` | 队列优先级 |
| `MessageKind` | `mission_order` / `amendment` / `sitrep` / `contact_report` / `acknowledgement` / `clarification` / `deviation_report` | 报文类型 |
| `MessageStatus` | `queued` / `delivered` / `dropped` / `superseded` | 报文状态 |
| `ContingencyBranch` | `explicit_signal_branch` / `local_condition_branch` / `loss_of_comm_branch` | 三类备选方案 |

## 2. 新增模型

**编队与命令**
`CommandAuthority`、`FormationCommandState`、`CommandDelayState`

**通信与命令**
`CommandMessage`、`MissionOrder`、`Contingency`、`TargetPriorityDirective`

**CD-6 研究接口**
`ContractTerm`、`ContractState`、`LedgerEntry`

`CommandDelayState` 的 `decisions` 存 `list[dict]`（决策的 `model_dump`）而非代理类型本身：账本是审计记录，且这样做避免了 `models → formation_agents` 的导入环（详见 `BUG_AND_RERUN_LOG.md` 的 CD6-F1）。

## 3. 既有模型的新字段（全部有默认值）

| 模型 | 新字段 | 默认 | 谁读它 |
|---|---|---|---|
| `GameOptions` | `command_delay_mode: bool` | `False` | `build_initial_state`、`engine.advance` 的单钩子、各 API 入口 |
| `FormationState` | `movement_style: FormationMovementStyle` | `FOLLOW_WAKE` | `expand_movement_orders` 的分派与闸门 |
| | `geometry_kind: FormationGeometryKind` | `COLUMN` | 同上（`FOLLOW_WAKE` 闸门） |
| | `line_axis: int \| None` | `None` | 审计与展示 |
| `FormationMovementOrder` | `movement_style: ... \| None` | `None` | 分派（`None` 表示沿用编队声明样式） |
| | `reform_column: bool` | `False` | 分派（`REFORM_COLUMN` 请求） |
| `OrderBatch` | `target_priorities: list[TargetPriorityDirective]` | `[]` | `target_priority.auto_gunnery`；命令延迟模式下**唯一**的炮击输入 |
| `GameState` | `command_delay: CommandDelayState \| None` | `None` | 模式状态；旧模式恒为 `None` |

## 4. 信封增长（实测）

`models.py` 的字段新增会让 `model_dump(mode="json")` 多出键，从而出现在 `orders_submitted` / `game_created` 等事件载荷里。冻结投影把这部分单独报告，当前**恰好 4 个叶子键**：

| 叶子键 | 出现位置 | 出现次数（7 行合计） |
|---|---|---|
| `command_delay_mode` | `events[].payload.options` | 7 |
| `movement_style` | `events[].payload.order_batch.formation_movement[]` | 54 |
| `reform_column` | 同上 | 54 |
| `target_priorities` | `events[].payload.order_batch` | 391 |

**冻结键无一变化、无一消失、无列表长度变化**（`audit_freeze.json` → `n_drift: 0`）。

## 5. 未做的事

- **未**把命令延迟状态放进 `PlayerObservation`：审计断言 Classic 与 Realistic 的玩家观察中不存在 `command_delay` 字段。舰队/编队视图是独立的、由模式门控的接口。
- **未**删除或重命名任何既有字段/枚举值。
- **未**改动 `GameOptions.realistic_command` 的语义：`command_delay_mode=True` 而 `realistic_command=False` 时**建局失败**（fail closed），不做静默强制。

## 6. 需要 PI 裁决的两处

| 编号 | 事项 | 现状 |
|---|---|---|
| CD0-Q1 | 编队数量上限：玩家规则文档 `docs/rules/realistic-command.md` §三 写"一至四个编队"，代码 `MAX_FORMATIONS_PER_SIDE = 8`（注释为用户裁定） | 本轮**不改动任何一侧**：改代码会动冻结文件，改文档需要确认该裁定是否仍然有效 |
| CD0-Q2 | 两项既有哈希种子确定性测试因未传 `PYTHONPATH` 而从未真正运行 | 未修（超出授权范围）；已有替代验证手段（见 `08_REPLAY_DETERMINISM_AUDIT.md` §4） |
