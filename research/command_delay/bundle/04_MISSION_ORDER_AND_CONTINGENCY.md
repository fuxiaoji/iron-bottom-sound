# 04_MISSION_ORDER_AND_CONTINGENCY.md

审计对象：任务式命令是否符合"做什么/为什么/与谁协调"的历史结构，备选方案是否为**三类**而非任意 if/else。

- 代码：`backend/src/iron_bottom_sound/delegation.py`
- 规则号：`IBS-R-CD-04`
- 审计记录：`audits/audit_mission_order.json`
- 测试：`tests/test_command_delay_communications.py`（结构、三类分支、自主权次序）、`tests/test_command_delay_formation_agent.py`（分支激活与偏离报告）

## 1. `MissionOrder` 结构（§8 全字段）

```text
order_id / formation_id / side / issued_turn / issued_by
mission                       任务（做什么＋为什么）
assumptions                   假设
trigger_conditions            触发条件
commander_intent              上级意图
task_to_formation             编队任务
coordination_measures         协同措施
operating_area / waypoint / deadline_turn
target_priority_directives    目标优先级（只给权重）
roe                           交火规则/火力限制
risk_constraints              风险与保舰约束
report_requirements           报告要求
communications_plan           通信计划
commander_location / rendezvous
loss_of_comm_plan             失联预案
contingencies                 备选方案
valid_from_turn / expiry_turn / confirmed_turn
```

审计断言：完整订单的 `validate_mission_order` 返回空错误列表；缺任一必备块或任一分支类型都会被逐条报出。原则落在实现里——上级只给任务、意图与协同，**不给逐步微操**。

`mission_order_template` 生成的就是 `docs/rules/command-delay.md` §五与 v2.2 §10 的 Cape Esperance 式结构（MISSION / INTENT / TASK / COORDINATION / FIRE PRIORITY / COMM PLAN / LOSS OF COMM / FALL-OUT / REJOIN / RENDEZVOUS）。

## 2. 目标优先级只给权重

模板为每个优先级舰级生成一条 `TargetPriorityDirective`，权重按序递减（1.00 / 0.75 / 0.50 / 0.25），`source = FLEET_ORDER`。订单里**没有任何**炮位、射击解或命中量；最终分配见 `07_TARGET_PRIORITY_SELECTOR_AUDIT.md`。

## 3. 三类备选方案（§9）

| 类型 | 激活条件 | 实现 |
|---|---|---|
| `EXPLICIT_SIGNAL_BRANCH` | 收到指定种类的报文（`trigger_message_kind`，标准模板取 `AMENDMENT`） | `delivered_kinds` 含该种类才激活；缺 `trigger_message_kind` 则订单校验直接报错 |
| `LOCAL_CONDITION_BRANCH` | 本地可验证条件 | "优势之敌"与"发现目标"两项；必须声明 `requires_local_check=True`，否则订单校验报错 |
| `LOSS_OF_COMM_BRANCH` | 链路 `STALE` 或 `BLACKOUT` | 打开预令：继续当前任务、按时间地点会合、失去最低能力则撤退 |

"优势之敌"判据只用本地可见信息，两条都预先声明：

1. 本地接触数 ≥ 编队自身舰数 × `SUPERIOR_FORCE_RATIO`（1.5）；
2. 目视到的舰级比自身任何一舰都重（`CLASS_RANK` 比较）。

未见过的敌舰不贡献任何信息，因此本地代理**无法**获得它从未观测到的敌方实力。另有一条"最低能力"判据：本编队 `hull_fraction < 0.4` 时加入"撤退并会合"分支。

`activate_branches` 是纯函数：同一订单 + 同一本地态势必然激活同一组分支，每条都带 `reason`，因此回放可逐条审计。

## 4. 自主权次序（§11）

`delegation.autonomy_priority_list()` 固定返回：

```text
1 引擎合法性
2 最新有效命令
3 上级意图
4 协同约束
5 已授权备选方案
6 本地战术最优化
7 仅在任务与风险约束内保全兵力
8 恢复通信后报告偏离
```

审计断言其首项为 `engine legality`——即"合法"永远优先于"命令"，本地代理不能以任何命令为由绕过引擎裁决。

## 5. 无命令时的预令

`delegation.standing_plan()` 生成一条完整预令（"尚无上级命令：继续当前任务并按预令行动"），并把三类分支一并带上。代理在未收到已确认订单时执行它，而不是自创任务；决策审计里以 `order_received: false` 记录。这样"任务式命令"的边界在通信尚未建立时同样成立。

## 6. 偏离报告

`delegation.deviation_report(order, turn, reason, origin)` 产出：订单号、编队、回合、来源、以及一句**与 intent 的一致性说明**（`intent_consistency`）。代理在激活非失联类分支时自动要求 `DEVIATION_REPORT`；链路为 `BLACKOUT` 时不要求——此时无人可报，这也正是 `test_agent_reacts_to_the_loss_of_communication_branch` 断言的行为。

## 7. 实测

完整一局（IBS-S-01，7 回合）中：

- 双方各发出 1 条常设任务式命令，经通信管线投递并确认（`mission_orders: 2`，`audits/audit_communication.json`）。
- 19 次本地代理决策中，激活 `local_condition_branch` 11 次、`loss_of_comm_branch` 7 次、无 1 次；报告动作为 `ACKNOWLEDGEMENT` 19、`CONTACT_REPORT` 17、`DEVIATION_REPORT` 11、`SITREP` 2。
- 三类分支在真实对局中都被触发过，不是纸面功能。
