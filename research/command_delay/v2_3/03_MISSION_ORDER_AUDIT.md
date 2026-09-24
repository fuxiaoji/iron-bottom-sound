# 03 · 持久任务命令（IR-4）

## 1. 问题（计划 §7）

v2.2 的舰队总指挥**每回合重下一遍命令**：CD-13 那局 11 个回合发出 **63 封任务命令**，
其中绝大多数是把"继续保持当前任务"换个说法再说一遍。命令不是持久对象，而是每回合的提示词。

## 2. 修法

`MissionOrder` 增加**修订线与命令事件**：

```text
order_event = NEW_ORDER | AMEND_ORDER | CANCEL_ORDER | ACTIVATE_PREBRIEFED_BRANCH | NO_NEW_ORDER
revision, amends_order_id, cancelled_turn
```

规则（全部落在 `command_delay.draft_natural_order` 与 `_apply_delivery`）：

1. **现行命令持久**：`active_mission_order()` 返回最新未撤销、未过期的命令，跨回合有效；
2. **重述不产生修订**：新命令文本与现行命令在**忽略空白与标点**后相同 → 不发报文，
   记一条 `mission_order_restated` 事件（`NO_NEW_ORDER`）。显式 `NO_NEW_ORDER` 同样不下令；
3. **修正即修订**：有现行命令时新命令自动成为 `AMEND_ORDER`，`revision = 现行 + 1`，
   `amends_order_id` 指向现行命令；`order_id` 带修订号后缀，避免同回合两令撞号
   （第一版就是撞号：撤销令被解析回原令，撤销无效）；
4. **迟到的旧令不能覆盖新修订**：投递时先按 `issued_turn` 拒绝更旧的令，
   再按**修订线**拒绝同线但 `revision ≤ 现行` 的令，记 `SUPERSEDED` 与原因；
5. **撤销**：`CANCEL_ORDER` 投递时把现行命令标记 `cancelled_turn` 并清空该编队的
   `active_order_id`，发 `mission_order_cancelled` 事件；
6. **预案激活**：`ACTIVATE_PREBRIEFED_BRANCH` 投递时写入该编队记忆（`contingency` 类）
   并发 `contingency_branch_activated` 事件——上级可以选择"激活第 2 号预案"而不是重写命令；
7. 自由文本仅描述性：结构化字段（mission/intent/task/priority_classes/roe/deadline/
   contingencies）才是权威，这一条在模型侧由 `fleet_llm` 的 schema 呼应。

## 3. 模型侧

`fleet_llm.FLEET_RESPONSE_SCHEMA` 的每条命令新增 `order_event`；指令里明确：
**现行命令会持续有效，不必重复下达；只有战局变化才发 `NEW_ORDER`，调整用 `AMEND_ORDER`，
撤销用 `CANCEL_ORDER`；把同一道命令换个说法重发不会生效**。
解析器校验事件名，未知事件判为非法回复。

## 4. 测试（`tests/test_command_delay_mission_order_v23.py`）

计划要求的六回合情形：

| 回合 | 情形 | 断言 |
|---|---|---|
| T1 | 下达命令 | `NEW_ORDER`、`revision=1`、投递后成为现行命令 |
| T2–T4 | 无新令 | 命令**跨回合仍在生效**（`active_mission_order` 同 id、未撤销） |
| （T2–T4 间） | 重述同一命令 | 不产生新命令、无新报文、留 `mission_order_restated` 事件；显式 `NO_NEW_ORDER` 同样不下令 |
| T5 | 迟到的修正令 | `AMEND_ORDER`、`revision=2`、`amends_order_id` 指向原令、投递后成为现行命令 |
| T6 | 旧的同线命令迟到 | 记 `SUPERSEDED`、原因含修订号、现行命令不变、命令总数不变 |

另有一项撤销测试：`CANCEL_ORDER` 投递后 `active_order_id` 清空、原令被标 `cancelled_turn`、
发 `mission_order_cancelled` 事件。

## 5. 与冻结面的关系

命令语义只影响命令延迟模式；8/8 审计 PASS，Classic/Realistic 七行未变
（`cd_s01` 的行为变化已在 `GOLDEN_INDEX.json` 的 `refreeze` 记录中归因）。
