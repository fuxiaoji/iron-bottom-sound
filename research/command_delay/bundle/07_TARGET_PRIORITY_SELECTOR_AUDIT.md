# 07_TARGET_PRIORITY_SELECTOR_AUDIT.md

审计对象：目标优先级是否只改变选择器**偏好**，绝不改变合法性、射界、修正、命中或炮位分配（验收 6、7）。

- 代码：`target_priority.py`、`backend/src/iron_bottom_sound/engine.py`（GUNNERY 分派）
- 规则号：`IBS-R-CD-06`
- 审计记录：`audits/audit_gunnery_authority.json`
- 测试：`tests/test_command_delay_formation_agent.py`、`tests/test_command_delay_communications.py`

## 1. 权限边界（§3.1）

编队代理**禁止**直接生成：`GunneryOrder`、mount allocation、firing solution、hit modifier、expected-hit calculation。实现上有四道互相独立的闸门：

1. **类型层**：`FormationDecision` 没有炮击字段（审计记录该字段列表，禁止项交集为空）。
2. **结构守卫**：`target_priority.validate_agent_decision_shape` 对任何带炮击机制的对象返回错误——实测 `["a formation agent may not emit gunnery machinery: mounts"]`。
3. **引擎层**：命令延迟模式下 `validate_orders` / `submit_orders` 收到**原始炮击批次**时直接拒绝（`Command Delay generates gunnery through the engine selector; submit target priority directives instead of gunnery orders`），而不是忽略后继续。审计在对局中的每个 GUNNERY 阶段都真的尝试提交一次，结果是 `every raw gunnery batch was refused`。
4. **数据层**：`OrderBatch.target_priorities` 是代理与舰队命令唯一能提供的炮击输入；该字段里能装的只有 `TargetPriorityDirective`（有界权重 + 目标/舰级/标签）。

## 2. 选择器做什么、不做什么

```text
priority_bonus(target) = fleet_priority + bounded_local_priority + doctrine_priority
final_score(target)    = base_fire_objective + LAMBDA_PRIORITY * priority_bonus
```

- `base_fire_objective` 来自引擎的 `expected_gunnery_hits`（`_gunnery_candidates` 下发），**公式只存在于引擎**，本模块不复制；
- `legal` 完全由 `_gunnery_candidates` 决定（可见性、射界、炮位是否可用、想定限制）；
- 选中的炮位列表**直接复制**自该候选记录，所以生成的 `GunneryOrder` 天然合法；
- 本地项被 `clamp_local` 夹到 ±0.5，舰队项夹到 ±1.0，因此本地代理**无法**压倒舰队命令的相反权重；
- 没有任何指令时 `priority_bonus = 0`，得分等于基础目标函数（`DOCTRINE_CLASS_PRIORITY` 只在存在指令时作为同向补充参与，此项由测试 `test_doctrine_supplies_a_fallback_hierarchy_only_when_directives_exist` 断言）。

`selection_trace()` 是只读审计面：它把每一条 (舰, 目标) 合法配对的 `base_fire_objective` / `priority_bonus` / `score` 列出来，因此"指令只重排了合法选项"可以被直接看见，而不是靠信任。

## 3. 实测

| 检查 | 结果 |
|---|---|
| 封存的炮击命令数 | **54** |
| 其中相对**当回合**候选集非法的 | **0** |
| 非法示例 | `[]` |
| 抵达选择器的优先级指令 | **222** 条 |
| 越界本地权重 | 0（`local_weights_within_limit: true`） |
| 代理决策中带炮击字段的 | 0（扫描 19 条决策及其调整项） |
| 对不可见目标的指令 | 回退到其余合法目标，生成 0 条越权订单（`invisible_target_fallback_legal: true`） |

合法性在**每个 GUNNERY 阶段当场**用该时刻的候选集判定，并在批次被接受后立即复核（引擎在 `advance` 内才封存，因此读的是刚被接受的 `submitted_orders`）。这一测量位置是刻意的：若拿第 7 回合的棋盘去判第 3 回合的订单，54 条会全部"非法"，那什么也证明不了——审计的第一版就是这么错的，见 `BUG_AND_RERUN_LOG.md` 的 CD5-F2。

## 4. 偏好确实会变、合法性不会

`test_a_directive_only_reranks_legal_targets` 是对照实验：在同一次 GUNNERY 阶段取一艘有 ≥2 个合法目标的舰，比较无指令与有指令两次选择，断言

- 两边的舰集合完全相同；
- 每条产出的订单 `(ship_id, primary_target)` 都在这艘舰的合法配对集合里；
- 选中目标的炮位集合与该候选记录的 `mount_ids` **完全相同**（炮位不是另行挑的）；
- 在被观测到差异的样本中，选择确实翻转到了被加权目标。

审计要求至少发生一次真实翻转（`comparisons >= 1`），否则测试失败——避免"指令没生效也算通过"。

## 5. 回退语义

"若指定重点目标当前不可见/不可射，selector 自动回退到其余合法目标"（§3.2）不是错误路径，而是**没有这条路径**：不可见的目标根本不存在于候选集里，因此没有任何代码分支可能产出一条非法订单。测试与审计各自用"指向 `IBS-U-NOT-A-SHIP` 的权重 1.0 指令"验证这一点。
