# “二马·大舰队指挥学院”教学脚本审计

## 权威边界

本教学使用可玩想定 `IBS-S-EM-01` 和真实模式 `IBS-R-RC-01` 至 `IBS-R-RC-07`。舰船移动、炮击、穿甲、损伤、鱼雷、火灾与胜负仍由正式规则引擎裁决。

`IBS-TUT-EM-*` 不是《铁底湾的回响 IV》原版规则，也不是二马想定特例。它只用于把某个学习机制稳定地呈现给第一次游玩的玩家；正式热座、人机、LLM 和状态机 AI 对局不得触发。

## IBS-TUT-EM-05：共同航速危机

- 触发条件：`mode=tutorial`、`tutorial_script=erma_grand_fleet`、想定为 `IBS-S-EM-01`、真实模式开启，且第一回合起火/回合结束阶段首次完成。
- 固定战情：石狩的第二回合速度轨从 5 MF 上限划至 3 MF 上限。
- 事件：`tutorial_speed_crisis`，公开记录目标舰、速度轨前后值、第二回合最大航速前后值和教学选择。
- 玩家决策：第二回合移动阶段的半自动草稿保留战列线原 5 MF 意图，并显式填写 `speed_decision=reduce, speed=3`。玩家可直接提交全队降速，也可在相同正式表单中改为 `detach` 并永久脱离石狩。
- 裁决边界：脚本只制造已标注的速度轨状态；编队订单展开、共同速度合法性、脱队、撤退航路和退出地图全部继续由 `realistic_command.py` 与通用移动引擎裁决。

## 四向审计

- Source：项目教学设计；无原版来源页，事件正文明确标注“教学战情”。
- Data：`GameOptions.tutorial_script`、`GameState.tutorial_flags`、`IBS-TUT-EM-05` 事件载荷。
- Execution：`tutorials.apply_checkpoint` 是唯一固定事件入口；`tutorials.coach_suggested_orders` 只生成可编辑建议，不提交订单。
- Tests：`tests/test_tutorials.py` 覆盖触发时点、正式局隔离、错误组合拒绝、回放等价和显式降速草稿合法性。
