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

前三项见 `BUG_AND_RERUN_LOG.md` 的完整时间线。

## 未越界的事项

- **未**开始任何科研实验；**未**实现 RL/GNN/Transformer；**未**调用任何付费 LLM（CD-5 全部用 stub/录播策略）。
- **未**改动 `realistic_command.py` 的既有语义：该文件仅有 4 处插入（2 处 import、1 处分派+闸门、1 处 `after_movement` 调用、1 处 `choose_plan` 分支），全部由新模式或新样式启用，默认路径由黄金回放证明逐字节不变。
- **未**手工改写任何来源文件。
- **未**新增任何历史概率数值；媒介回合值全部标注 `SIMULATION_ABSTRACTION`。
