# 06 · 炮击权限与优先级隔离（IR-7）

**结论：验证（而非重设计）通过。** 下级无法提交炮击令；优先级权重只改偏好，不改合法性。

## 1. 四道闸门（既有设计，本批次逐条复核）

| 闸门 | 实现位置 | 复核结果 |
|---|---|---|
| 决策模型没有炮击字段 | `formation_agents.FormationDecision` | `gunnery/mounts/mount_ids/firing_solution/hit_modifier/expected_hits` 均不在字段集中 |
| 形状守卫 | `target_priority.validate_agent_decision_shape` | 带 `mounts` 的决策字典被拒 |
| 引擎拒绝原始炮击批次 | `engine.validate_orders` | 命令延迟模式下提交 `GunneryOrder` → 非法，错误信息含 "engine selector" |
| 唯一输入是优先级 | `OrderBatch.target_priorities` | 选择器只从这里读偏好 |

## 2. 本批次新增的单元级证明（`tests/test_command_delay_gunnery_authority_v23.py`）

| # | 断言 | 结果 |
|---|---|---|
| 1 | 决策模型无炮击字段；形状守卫拒绝带 `mounts` 的字典 | PASS |
| 2 | 提交原始炮击令被引擎拒绝，且理由指向"引擎选择器" | PASS |
| 3 | 权重改变偏好而不改变合法性：加权前后每条订单的 `(ship_id, target_id)` 都在引擎候选集内，且**炮位取自候选记录**（`mount_ids` 的子集） | PASS |
| 4 | 权重界限：解析层拒绝超出 ±0.5 的权重；选择器侧对越界值做夹紧 | PASS |
| 5 | 指向**不可见**目标的指令完全无效：与无指令时的选择逐条相同 | PASS |

## 3. 与审计的关系

`run_audits.audit_gunnery_authority` 在同一局实机上做同样的事，并额外断言
**每条进入选择器的优先权必须由本阵营编队签发**（CD12-F7 加的不变量，正对照在
`BUG_AND_RERUN_LOG.md` 里）。本次 8/8 审计 PASS。

## 4. 边界

- 本批次**没有**改动炮击合法性/命中/损伤规则（属于冻结语义）；测试只证明"没有被改坏"。
- 优先级对**选择顺序**的影响在测试 3 中以"被加权目标确实被某些舰选中"体现，
  未做全序比较（选择器是确定性的，但排序规则不在本批次审计范围）。
