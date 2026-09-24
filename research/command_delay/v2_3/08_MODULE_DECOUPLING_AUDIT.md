# 08 · 模块解耦与冻结面审计（IR-8 之二）

## 1. 问的问题

计划要求回答：**通信/委派逻辑是否被塞进了旧的 `realistic_command.py`（超出薄钩子）？**
经典与真实模式是否真的没被动过？命令延迟是否仍是独立模式？

## 2. 量出来的答案

相对冻结 tag `realistic-command-v1-frozen`（`d432a975`）：

| 文件 | 改动 | 说明 |
|---|---|---|
| `realistic_command.py` | **+154 / −1** | 全部是薄钩子（见 §3） |
| `engine.py` | +305 / −2 | 命令延迟钩子 + 冻结面既有文件的小改（CD-0…CD-13 累积） |
| `models.py` | +456 | 新增数据模型（含 CD 的枚举/状态/知识/断言模型） |

**命令延迟相关的新逻辑全部在独立模块**（13 个文件，均不在冻结面之内）：

```text
command_delay.py        command_observation.py   communications/（routing/queue/processing/integrity）
formation_agents.py     formation_llm.py         formation_maneuver.py
formation_memory.py     formation_knowledge.py   fleet_llm.py
reporting.py            claims.py                target_priority.py
delegation.py           research_hooks.py
```

## 3. `realistic_command.py` 里的 CD 代码逐处核对

`grep -c "if state.options.command_delay_mode"` = **2**，即只有两处模式门控：

| 位置 | 内容 | 判定 |
|---|---|---|
| `choose_plan` 的 GUNNERY 分支 | `if state.options.command_delay_mode and state.phase is Phase.GUNNERY:` → `from .command_delay import gunnery_batch; batch = gunnery_batch(state, side)` | **薄钩子**：本模式不提交炮击令，改由引擎选择器生成；模式关闭时该分支不执行 |
| 机动阶段 | `if state.options.command_delay_mode:` → `from .command_delay import formation_plan; agent_plan = formation_plan(...)` | **薄钩子**：编队方案来自代理，模式关闭时走原路径 |

另有 `from .formation_maneuver import expand_move_together` 与 `style = order.movement_style or formation.movement_style`：
这是 **MOVE_TOGETHER** 的接线，属于**真实模式编队核心**的能力（IBS-R-RC-08），不是命令延迟专属——
v2.3 的 IR-8 专门用测试证明它在关闭命令延迟时同样可用（`test_move_together_is_available_with_the_command_delay_mode_off`）。

**结论：没有把通信/委派子系统塞进旧模块。** 旧模块只保留了"在某模式下改由谁产出订单"的两处门控，
以及机动风格的既有接线。

## 4. 冻结证据

- `golden_replay.py --check`：`classic_s01/s03/em01`、`realistic_s01/s03/em01/s03_seed9` **7 行逐字节 OK**；
- `run_audits.audit_freeze` 与 `GOLDEN_INDEX.json` 的 `refreeze` 条目里保存了这 7 行的 sha256，
  作为"本批次未动它们"的可核查证据（唯一变动的是命令延迟行 `cd_s01`，且逐次归因）；
- `run_audits.audit_leakage` 额外断言：**关闭模式时观察里不出现命令延迟状态**
  （`engine_games_without_mode` 检查 Classic/Realistic 观察不含 `command_delay` 字段）。

## 5. 边界

- `engine.py` 的改动多于"薄钩子"，但它承载的是**冻结面既有逻辑**（CD-0 的哈希序修复、命令延迟钩子、
  逐阶段事件），其行为由 7 行黄金回放 + 8 项审计守住；此处只报告数量，不宣称"仅钩子"。
- 本审计只做**结构性**判断（谁在哪个文件里）；"模式隔离"的行为证据由审计与测试提供，不由本文声称。
