# 07 · MOVE_TOGETHER 与模式隔离（IR-8）

## 1. MOVE_TOGETHER 的既有覆盖（22 项测试，`tests/test_command_delay_movement_style.py`）

计划列出的情形里，以下**已由既有测试覆盖**（本批次未重写，只做核对）：

| 计划要求 | 既有测试 |
|---|---|
| 直线同时平移 | `test_simultaneous_advance_keeps_the_column_and_marks_it_column` |
| 同时转向 | `test_turn_together_makes_the_line_oblique_and_says_so` |
| 友军同脉冲冲突拒绝 | `test_body_movement_refuses_friendly_same_pulse_conflict` |
| 速度不一致拒绝 | `test_body_movement_requires_common_speed_interval` |
| 指挥混乱拒绝 | `test_body_movement_requires_no_disruption` |
| 几何状态更新 | `test_turn_together_makes_the_line_oblique_and_says_so`、`classify_geometry` 相关 |
| REFORM_COLUMN | `test_reform_column_restores_follow_wake_when_the_turn_ends_aligned`、`test_follow_wake_is_refused_while_oblique_and_reform_only_after_alignment` |
| 资格条件（一线/等距/同航向/同程序/两舰起） | `test_body_movement_requires_*` 系列 |
| 哈希种子无关 | `test_body_movement_is_hash_seed_independent` |
| Classic/默认 Realistic 回放不变 | `test_body_movement_leaves_classic_and_default_realistic_replays_alone` |

## 2. 本批次新增（`tests/test_command_delay_move_together_v23.py`）

| 情形 | 结论 |
|---|---|
| **棋盘边界** | **见 §3 的实测发现**；测试断言的是引擎真正保证的不变量 |
| **强制移动交互** | 成员带 `forced_circle_turns` 时，共同程序不再资格成立（`eligibility` 报错）；`follow_wake_allowed` 也给出拒绝理由——这与 CD-13 对局里引擎驳回 `forced movement prevents formation following` 是同一条规则 |
| **Realistic 模式对等** | 关闭命令延迟模式后，`movement_style_options` 仍报告 `move_together_eligible`，资格判定同样只给几何理由、不给模式理由——机动风格是**真实模式编队核心**的能力，不是命令延迟模式的附加物 |

## 3. 实测发现：棋盘边界是"结算时截断"，不是"下令时拒绝"

计划把 `board-edge rejection` 列为必须有测试的情形。实测结果与措辞不同，如实记录：

1. 把编队摆在**最后一行显示行**（该六角布局的显示行 = `r + q//2`，所以贴边的 raw `r` 取决于 `q`——第一版测试把 `r` 写成 `rows-1`，那本身就已在棋盘外）并朝界外航向；
2. `engine.movement_preview()` 对"会走出棋盘"的程序**返回 commitable = True**（它校验命令、程序与航速，不校验逐格落点）；
3. `HexCoord.neighbor()` 在越界时抛 `ValueError("Movement leaves the map")`，**结算**时把该步视为障碍（同文件中 `obstacle = "edge"`）。

**判定**：边界由**结算截断**保证，不存在"非法"这一档。把它改成下令即拒绝，会改变**真实模式**语义，而本批次的硬约束是真实模式冻结（七行黄金回放逐字节未变即证据）。因此：

- 测试断言的不变量是引擎真正保证的那一条：**任何机动结算之后，没有舰只停在棋盘之外**；
- 该差异登记在 `BUG_AND_RERUN_LOG.md`（IR8-F1），供 PI 决定是否要一个真正的"越界拒绝"闸门（那属于真实模式语义变更）。

## 4. 冻结与隔离（另见 08_MODULE_DECOUPLING_AUDIT.md）

- Classic 三行、Realistic 四行**逐字节未变**（`golden_replay --check` + `run_audits.audit_freeze` 的 sha256 证据）；
- 命令延迟模式仍是**独立模式**：`command_delay_mode` 关闭时，`draft_reports`/`route`/机动风格扩张等路径都不执行；
- `engine.py` 与 `realistic_command.py` 的改动只有薄钩子（见 08）。
