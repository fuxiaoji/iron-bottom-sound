---
name: command-delay-mode-v2-2
description: 命令延迟模式 v2.2 实施（CD-0…CD-7）的结构与关键坑：冻结投影比较、MOVE_TOGETHER 声明几何、通信抽象边界、炮击权限四道闸门、CD0-F1 哈希顺序缺陷
metadata:
  type: project
---

命令延迟模式 v2.2 已实施完毕（2026-09-22），入口与结构：

- 冻结 tag `realistic-command-v1-frozen`（commit `d432a975…`）；黄金回放 harness 是 `research/command_delay/golden_replay.py`，八项审计是 `research/command_delay/run_audits.py`（退出码非零即 FAIL）。**基线行在固定 `PYTHONHASHSEED` 的子进程中运行**，否则不可复现。
- 比较用**冻结投影**：只忽略冻结时不存在的 dict 键，已存在键的值必须逐字节一致。这不是洁癖——朴素字节 diff 会把"新增可选字段"误报成语义漂移（见 [[iron-bottom-sound-research]] 的引擎坑位清单）。
- 新模块：`formation_maneuver.py`（IBS-R-RC-08 `MOVE_TOGETHER`）、`command_delay.py`、`command_observation.py`、`communications/`、`delegation.py`、`target_priority.py`、`formation_agents.py`、`formation_llm.py`、`contracts.py`、`research_hooks.py`。

**Why**：这些坑都不是能从代码一眼看出的，而是实现中真实踩到并修掉的。

**How to apply**（改动本模式前先记住）：

1. **`FormationState.geometry_kind` 是声明状态，不是实时测量**。`FOLLOW_WAKE` 编队转向过程中本就会暂时不在一条线上；若用实时几何当闸门，冻结的 Realistic 行为会被破坏。它只在"本回合封存订单请求了整队机动/重整"时更新。
2. **炮击权限有四道闸门**，改动任一条都要保持其余三条：决策类型无炮击字段、`target_priority.validate_agent_decision_shape`、引擎拒绝原始炮击批次、`OrderBatch.target_priorities` 是唯一输入。审计会在每个 GUNNERY 阶段**当场**用当时候选集复核订单合法性——用终局棋盘判历史订单会得出全部非法的假结论。
3. **通信延迟只由媒介配置给出**（处理/编码/转报/队列），传播固定 0；距离只选媒介不换算延迟；任何丢包/错码概率无来源即拒绝执行。不要为了"更真实"塞进未标注来源的数值。
4. **报告与订单都按发出时间判新鲜度**（同回合按阶段序）：报文航程会交叉，到达顺序 ≠ 新鲜度顺序，否则旧报告会覆盖更新认知。
5. **命令延迟类事件必须带 `secret_side`**：初始化事件曾一次性泄漏双方指挥链。
6. **`engine.py` 里 `set[frozenset]` 的遍历是既有雷区**（CD0-F1）：同函数内骰点路径已修、友舰解冲突路径曾漏修。新增任何碰撞/分组逻辑都要用规范排序键。
7. 本地视图的接触必须来自**本编队自身舰只**的可见性；地平线取请求方自身视距（曾误取双方较小值）。
