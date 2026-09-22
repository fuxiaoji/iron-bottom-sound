# 02_MOVEMENT_STYLE_AUDIT.md

审计对象：`MOVE_TOGETHER` 是否**新增**、可选、默认关闭，且不改变既有 `FOLLOW_WAKE` 行为。

- 代码：`backend/src/iron_bottom_sound/formation_maneuver.py`
- 规则号：`IBS-R-RC-08`
- 审计记录：`audits/audit_movement_style.json`
- 测试：`tests/test_command_delay_movement_style.py`（20 项，全部 PASS）

## 1. 数据模型

```text
FormationMovementStyle = FOLLOW_WAKE | MOVE_TOGETHER     # 默认 FOLLOW_WAKE
FormationGeometryKind  = COLUMN | STRAIGHT_LINE          # 默认 COLUMN
FormationState        += movement_style, geometry_kind, line_axis
FormationMovementOrder += movement_style: ... | None = None, reform_column: bool = False
```

`movement_style=None` 表示沿用编队当前声明样式；因为声明样式默认 `FOLLOW_WAKE`，旧订单（该字段不存在）逐位展开为冻结的后舰行为。

## 2. 资格条件（§4.2 全部实现，逐条失败即拒绝）

| 条件 | 实现 | 对应测试 |
|---|---|---|
| 全部在编成员位于同一条六角直线上 | `measure_line` 用**轴向** `direction_delta` 整数判线（不是射界用的屏幕空间 `_bearing_between` 近似） | `test_body_movement_requires_one_hex_line` |
| 间距统一 | 相邻成员步数集合大小为 1 | `test_body_movement_requires_uniform_spacing` |
| 当前同航向 | 全员 heading 相同 | `test_body_movement_requires_one_heading` |
| 共同速度交集非空 | `common_speed_interval` 交集为空即拒绝 | `test_body_movement_requires_common_speed_interval` |
| 无指挥中断 | `formation.disruption_turn == state.turn` 即拒绝 | `test_body_movement_requires_no_disruption` |
| 同一领舰方案对每舰自身位置均合法 | 逐舰 `engine.movement_preview(plan).commitable`（该边界已含损伤强制、转向限制、地形与地图边界） | `test_body_movement_requires_every_member_to_commit_the_same_program` |
| 整批次同脉冲同格/换位检定通过 | `simultaneous_conflicts` 逐脉冲检查友军同格与换位 | `test_body_movement_refuses_friendly_same_pulse_conflict` |

审计中的实测（IBS-S-03，`axis-active-light`）：

```json
"geometry": {"axis": 1, "heading": 4, "spacing": 1, "straight": true,
             "uniform_spacing": true, "same_heading": true},
"common_speed_interval": [0, 6],
"valid_orders": 3, "valid_errors": [],
"shared_token_sequence": ["2"],
"copies_no_hexes": true,
"off_line_refused": ["members are not on one hex line: consecutive members do not lie on one axis"]
```

## 3. 执行语义

- 每个全局 MF 脉冲，所有舰执行与领舰**相同的机动指令记号**：审计中 `valid_orders = 3`、`shared_token_sequence = ["2"]`（三舰同一记号）。
- **不复制领舰经过的地理格**：`copies_no_hexes = true`，逐舰轨迹数组不同。
- 航速声明与记号序列一致（`speed = movement_cost(plan, tokens)`），因此经典校验的 `declared speed` 检查同样成立。

## 4. 几何状态与 `REFORM_COLUMN`

同时转向只旋转航向、不旋转舰列轴线，因此编队可能由 `COLUMN` 变 `STRAIGHT_LINE`。`geometry_kind` 是**声明状态**而非实时测量：只在
(a) 本回合封存的订单请求了 `MOVE_TOGETHER`/`REFORM_COLUMN`（`commit_sealed_style_transitions`，在移动结算后调用），或
(b) `REFORM_COLUMN` 成功对齐时
发生变化。这一点很关键：`FOLLOW_WAKE` 编队在转向过程中本就会暂时不在一条线上，若用实时测量当闸门，冻结行为会被破坏。

`REFORM_COLUMN` 的真实语义是**可检验的成功/失败**：本回合继续整队机动，只有回合结束时 `column_aligned` 为真才恢复 `FOLLOW_WAKE`（发 `formation_reformed`）；未对齐则发 `formation_reform_rejected`，保持斜队，`FOLLOW_WAKE` 继续被拒。审计中闸门方向被显式验证：`declared_geometry_gate: false` 表示"声明非 COLUMN 时 `follow_wake_allowed` 返回 False"。

## 5. 默认路径未变

```json
"default_style_follow_wake": true,
"default_geometry_column": true
```

- 所有编队初始 `FOLLOW_WAKE` / `COLUMN`，因此 `expand_movement_orders` 中的分派与闸门都不会触发，走的是冻结路径。
- `commit_sealed_style_transitions` 在没有订单请求整队机动时**在触碰任何状态之前返回**。
- `tests/test_command_delay_movement_style.py::test_default_order_expands_into_the_frozen_follower_plans` 断言默认订单仍然生成"首命令必须是 advance"的后舰方案。
- CD-0 黄金回放给出最终证明：7 行 Realistic/Classic 回放 0 漂移。

## 6. turn-together 的扩展位

`ALLOW_TURN_TOGETHER = True`（模块常量，非每单标志，避免同一 profile 的两份订单含义不同）。置为 `False` 即退化为 v2.2 允许的"仅同时平移"低风险版本，资格检查会以 `turn-together is disabled in this build` 拒绝含转向记号的方案。审计记录该值以便复核。
