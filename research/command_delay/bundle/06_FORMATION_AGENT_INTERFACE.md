# 06_FORMATION_AGENT_INTERFACE.md

审计对象：编队代理接口是否对确定性 / LLM / 未来 ML 三者统一，是否只输出授权范围内的东西，是否可审计可重放。

- 代码：`formation_agents.py`（协议 + 确定性代理）、`formation_llm.py`（LLM 适配器）、`command_delay.py`（运行与账本）
- 规则号：`IBS-R-CD-02`（自主权）、`IBS-R-CD-04`（任务式命令）
- 测试：`tests/test_command_delay_formation_agent.py`（18）、`tests/test_command_delay_formation_llm.py`（16）

## 1. 统一协议（§13）

```python
class FormationPolicy(Protocol):
    name: str
    def act(local_observation, mission_order, comm_state,
            legal_action_mask, target_priority_space, contract_state) -> FormationDecision: ...
```

`DeterministicFormationAgent` 与 `FormationLLMAgent` 都满足它（`isinstance(..., FormationPolicy)` 由 `runtime_checkable` 协议在测试中断言）。`contract_state` 是 CD-6 的接口槽：现在传 `{}`，未来激励感知策略无需改签名。

## 2. 输出（`FormationDecision`）

```text
formation_id / turn / phase
selected_movement_action_id     来自引擎枚举清单，非自创
selected_movement_plan          从该 action 复制，非合成
selected_contingency_branch     三类之一
target_priority_adjustments[]   有界权重，仅本地目视目标
report_actions[]                允许清单子集
acknowledgement
rationale_summary               仅供审计
audit                           拒绝项、激活分支、hull 比例、是否收到命令
```

**字段里没有** `gunnery` / `gunnery_orders` / `mounts` / `mount_ids` / `firing_solution` / `hit_modifier` / `expected_hits`——审计把这份字段列表原样记录，并断言禁止项交集为空。

## 3. 确定性代理

- 机动选择：`_choose_action` 在引擎枚举的合法动作上按显式评分键取最大，打分项为"向目标推进 / 接敌距离 / 保持队位（与编队当前航速差）"。**方案字符串从 action 复制**，代理不合成航路。
- 目标：优先订单航路点；本地条件分支下取最近的本地接触；两者皆无则保持队位（不自行指定目的地）。
- 撤退：当激活分支的 fallback 含 "withdraw" 时目标项**取反**（拉开距离），这是"撤退并会合"对本地代理最诚实的读法。
- 权重：只对本地目视接触给权重，匹配舰队优先级舰级者 +0.05…+0.2，其余 −0.1，全部在 ±0.5 声明上限内。
- 报告：未确认订单 → `ACKNOWLEDGEMENT`；有接触 → `CONTACT_REPORT`，否则 `SITREP`；激活非失联分支 → `DEVIATION_REPORT`；链路 `BLACKOUT` 时**不要求**偏离报告（无人可报）。
- 未收到已确认命令时执行 `delegation.standing_plan()`（预令），审计记 `order_received: false`，而不是自创任务。

纯函数性质由测试断言：同一 observation 两次调用得到逐字段相同的 decision。审计中 19 条真实决策的分支分布为 `local_condition_branch 11 / loss_of_comm_branch 7 / 无 1`，说明三类分支在真实对局中都被走到。

## 4. LLM 适配器（CD-5）

**看什么**：`build_prompt` 只从 `FormationObservation` 组装（绝不从引擎状态读），内容严格等于 v2.2 §12 清单：本地编队状态、本地地图、**本地**接触、生效命令、已收报文、通信状态、外部陈旧报告、合法动作清单、合法优先级选项、允许的报告动作。测试断言提示词中**不含** `expected_hits` / `D66` / `modifier` / `firepower` / `caliber` / `gunnery_assist` / `hit_table` 等规则公式——"LLM 不得知道或复制规则公式"（§3.2）由此成为可检验项。

**能做什么**：只能选一个 `action_id`、指定一个分支、给有界权重、要求报告。解析器是严格的，逐项拒绝：

| 拒绝情形 | 错误信息要点 |
|---|---|
| 自创 action id | `not in the legal action list (N options)` |
| 原始机动方案（`movement_plan`） | `may not decide: movement_plan` |
| 任何炮击字段 | `may not decide: gunnery/mounts/...` |
| 越界权重 | `exceeds the local limit 0.5` |
| 未见过的目标 | `not a locally visible contact` |
| 未知报告动作 | `unknown report actions` |
| 非 JSON | `response is not valid JSON` |

**重试与回退**：拒绝后重试，重试提示词带上拒绝原因；用尽重试预算后回退到确定性代理，并把 `llm_fallback: true`、`llm_errors`、`llm_attempts` 写进 decision 审计。**每一次尝试都记录**（prompt、原始回复、错误、是否接受、是否回退），因此坏回复不会让对局卡住，也不会消失。

**重放**：策略是注入的可调用对象。`RecordedPolicy` 按 `(formation_id, turn)` 回放录制的回复，因此一局 LLM 对局可以在**零成本、逐字节相同**的条件下复跑——这是"每个本地 agent 决策可复现/可审计"（验收 10）在 LLM 路径上的落地方式。

**本阶段没有调用任何付费 LLM**：全部测试与审计使用 stub 策略与录播策略。

## 5. 运行与账本

`command_delay.run_formation_agents` 在每回合 MOVEMENT_PLANNING 边界为每个编队构建本地视图、运行代理、写 `formation_agent_decision` 事件（带 `secret_side`），并把决策存进 `CommandDelayState.decisions`（存 `model_dump`，避免数据模型 → 代理的导入环）与有界权重存进 `local_directives`。`formation_plan(state, formation_id)` 是 `RealisticCommander` 读取本回合方案的唯一入口。

## 6. CD-6 研究接口

`contracts.py`（契约状态 + 激励账本）与 `research_hooks.py`（张量 + 回合导出）只暴露接口，`implemented_learning = False`：

- 契约由 `contract_from_order` 从订单结构派生，**每条 term 的 weight 保持 0.0**，直到研究者显式声明——未标注来源的权重不会被编出来；
- 契约未确认（`agreed_turn is None`）即"未生效"，校验直接报错；
- `policy_observation` / `episode_records` 是策略安全形态（`POLICY_SAFE: true`），只含单个编队的本地视图；
- `episode_export` 是研究回放形态，**显式写 `POLICY_SAFE: false`** 并附警告（含双方订单与全部报文），使"把回放记录当观察喂给策略"这个错误不可能被静默犯下；
- 张量形状由 `TENSOR_SPEC`（`cd-tensor-v1`）声明，测试逐块断言宽度；数值是普通嵌套列表，`to_numpy()` 才按需引入 numpy，因此模块在无 numpy 环境下也能导入；
- 账本写入**不改变任何决策**：测试断言写一条账本条目后事件流不变，且对局仍能正常终局。
