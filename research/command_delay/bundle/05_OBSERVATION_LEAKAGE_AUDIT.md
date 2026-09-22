# 05_OBSERVATION_LEAKAGE_AUDIT.md

审计对象：命令延迟模式是否向舰队总指挥泄漏远端编队精确状态（验收 4），以及本地代理是否获得了本方全局真值（验收 5）。

- 代码：`backend/src/iron_bottom_sound/command_observation.py`、`command_delay.py`
- 审计记录：`audits/audit_leakage.json`
- 测试：`tests/test_command_delay_mode_shell.py`（16 项）、`tests/test_command_delay_formation_agent.py` 的相关项

## 1. 采样方式

审计**在对局进行中**采样（第 1–5 回合的 GUNNERY 阶段，双方都还有编队在水面上），而不是只在终局采一次：终局常常一方已无编队，那样"恰好一个精确编队"的检查会**空洞通过**。实测采样点 `[1, 2, 3, 4, 5]`，10 条舰队视图记录 + 19 条编队视图记录。

## 2. 舰队总指挥视图：只有被搭载编队是精确状态

| 回合 | 方 | 被搭载编队 | 精确编队 | 报告数 | 报告年龄（远端编队） |
|---|---|---|---|---|---|
| 1 | axis / allies | axis-active-heavy / allies-active-light | 恰为被搭载者 | 2 | [0, 0] |
| 2 | 同上 | 同上 | 恰为被搭载者 | 2 | [0, 1] |
| 3 | 同上 | 同上 | 恰为被搭载者 | 2 | [0, 2] |
| 4 | 同上 | 同上 | 恰为被搭载者 | 2 | [0, 3] |
| 5 | axis | axis-active-heavy（已不在水面） | `[]` | 1 | [0] |
| 5 | allies | allies-active-light | `["allies-active-light"]` | 2 | [0, 4] |

远端编队的报告年龄随回合**单调递增**（0→1→2→3→4），说明舰队对它的认知确实在退化，而不是每回合被刷新一次——这正是命令延迟模式存在的意义。

规则与判定：

- 被搭载编队在水面上时，**恰好**它是唯一 `is_source_of_truth` 的条目；不在水面上时（t5 轴心旗舰编队已沉），**没有任何**编队是精确的——不因为"没有精确来源"而回退成别的编队。
- 远端编队只以 `FormationReport` 出现，字段仅：引导舰位置/航向/航速、舰数、声明几何、报告回合、年龄、链路/权限、指挥官舰 id。**没有**逐舰明细、没有舰体值、没有编队内每舰位置。
- 实测报告年龄从 `[0, 0]`（TBS 同回合可达，符合 §6 规则）单调升到 `[0, 4]`（编码/转报路径 + 编队分离）——年龄字段是真实退化，不是装饰。

`contacts` 块是舰队**自己的目视图**：审计把它的内容与"被搭载编队自身舰只可见性"（引擎 `_visible_to`）逐一比对，必须完全相等；并断言每条接触只带 `ship_id/name/ship_type/position/heading/sunk` 六个键（`extra` 为空），因此不会顺带泄漏舰体、修正或火力信息。**接触块之外**，对方舰船 id 出现次数为 0。

## 3. 编队本地视图：无本方全局真值

19 条编队视图记录的顶层键固定为：

```text
active_mission_order, authority, comm_state, formation_id, formation_name,
formation_state, game_id, legal_formation_actions, legal_target_priority_options,
link_status, local_contacts, local_map, local_priority_weight_limit,
map_columns, map_rows, phase, received_messages, report_actions, side,
stale_external_reports, turn, visibility
```

`score`、`sealed_orders`、`submitted_orders`、`wrecks`、`torpedo_tracks`、`winner`、`victory_reason`、`ships` 全部不在其中（`FORBIDDEN_LOCAL_KEYS` 硬检查，0 命中）。

对方舰船 id 允许出现的块只有两个，且都派生自**本编队自己的目视集**：

- `local_contacts`：本编队自身舰只可见性算出的接触；
- `legal_target_priority_options`：可加权的目标 id。

审计逐采样点断言：

- `local_contacts == engine._visible_to(...)` 用**本编队自身舰只位置**算出的可见集（不是本方全集）；
- `legal_target_priority_options` 的 target id ⊆ `local_contacts`，即不能对从未目视过的目标加权重；
- 除这两块之外，对方舰船 id 出现次数为 0。

## 4. 事件流

命令延迟相关事件共 **175** 条（`command_delay_initialised` / `command_delay_turn_state` / `command_message_queued` / `command_message_delivered` / `formation_agent_decision`），**全部带 `secret_side`**，因此引擎既有的事件过滤（`observe` 按 `secret_side` 过滤）对它们生效。

这一条是审计**直接抓出并修掉**的缺陷（CD2-F1）：最初的 `command_delay_initialised` 载荷包含双方指挥链，且不带 `secret_side`，会把对手的编队、旗舰与总指挥舰一次性交出去。修复为每方一条带 `secret_side` 的事件；审计现在把"命令延迟类事件必须带 `secret_side`"写成硬条件。

## 5. Classic / Realistic 不含模式状态

```json
{"classic_has_command_delay_field": false,
 "realistic_has_command_delay_field": false}
```

即两种旧模式的玩家观察中**不存在** `command_delay` 字段：模式状态既不进 `PlayerObservation`，也不进任何旧模式载荷。舰队/编队视图是独立的、由 `command_delay_mode` 门控的接口（`/games/{id}/command-delay/fleet-view`、`.../formation-view/{id}`，且编队必须属于请求方）。

## 6. HTTP API 层的透明性（交付评审补测）

引擎层干净不代表传输层干净：API 可能把引擎过滤掉的东西加回来。判定方式不是"看有没有出现敌舰"（被发现的敌舰本来就该出现），而是**逐次比对**：

```
GET /games/{id}/view  ==  engine.observe(game_id, side)   ?
```

用 FastAPI `TestClient` 跑完整一局（IBS-S-03 + 命令延迟模式），**双方各比一次、共 58 次比较，0 处不一致**。即 API 既不增也不减引擎自己的迷雾视图。

同时对 `/games/{id}/advance` 与 `/games/{id}/events` 逐条检查事件的 `secret_side`：到达轴心玩家的每一条命令延迟事件都属于轴心（或为公开事件），未出现任何发给对方的条目。

## 7. 中立战报的私有信息（交付评审发现并修复）

战报是**双方都能打开的中立文档**，其事件规则是"至少一侧可见的并集"（`public_events_for_turn`），而命令延迟事件各自只属于一方。实测该并集把 `command_delay_initialised`（2 条）、`command_delay_turn_state`（8 条）、`formation_agent_decision`（8 条）**全部**带进了战报——等于把双方的指挥链、代理决策与激活的备选分支印在同一份文档里。

修复：`battle_report.PRIVATE_EVENT_PREFIXES` 按前缀排除整个命令延迟事件族（与既有 `orders_submitted` 的排除理由相同）。修复后该检查 0 项发现，且既有 22 项战报测试全部通过。

**同类既有问题（非本轮引入，需 PI 裁决）**：Realistic 模式下的 `formation_created` 与 `movement_plan_resolved` 同样带 `secret_side` 却会被并集收进中立战报（实测 2 + 27 条）。规则文档明说"己方编队关系、旗舰和继承顺序是秘密信息"，因此这两类事件在战报中出现是同一类缺陷；但修它会改变既有战报内容，故未擅动，列为裁决项 CD8-Q1。

## 8. 判定

```
INFO_LEAKAGE = PASS      (引擎层 findings = []；API 层 58/58 与引擎视图一致；战报 0 项私有事件)
```

0 项发现。审计在收紧过程中先失败三次（检查过宽会漏、过严会误报），最终形态是：**允许"自己看到的东西"，禁止一切"没看到却知道的东西"**。
