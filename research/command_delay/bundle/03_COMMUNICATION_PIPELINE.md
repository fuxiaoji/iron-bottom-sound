# 03_COMMUNICATION_PIPELINE.md

审计对象：通信延迟是否按"处理/编码/转报/排队"建模，是否**没有**被写成无线电传播，是否**没有**捏造历史概率。

- 代码：`backend/src/iron_bottom_sound/communications/`（`models` / `processing` / `routing` / `queue` / `integrity`）+ `command_delay.py` 的收发与投递
- 规则号：`IBS-R-CD-03`（处理链）、`IBS-R-CD-05`（拥塞）
- 审计记录：`audits/audit_communication.json`
- 测试：`tests/test_command_delay_communications.py`（25 项，全部 PASS）

## 1. 处理链与传播

历史过程（v2.2 §5）被实现为一条消息必须依次经过的抽象流程：

```text
指挥决策 → 拟稿/制式信号 → 加密/编码 → 发送 → 转报/再加密
        → 抄收/转录 → 译码/解释 → 消息中心/CIC/舰桥分发 → 确认/澄清 → 执行
```

**传播延迟固定为 0**：`MediumProfile.propagation_turns = 0.0`，且 `processing.abstraction_note()` 明确写出"在游戏尺度上按 0 建模；距离只决定用哪种媒介"。审计断言表中每个媒介的 `propagation_turns == 0`。

## 2. 媒介抽象表（实测量见审计）

| medium | 基础回合 | 每中继级 | 中继上限 | 需加密 | 抽象含义 |
|---|---|---|---|---|---|
| TBS_SHORT | 0 | +1 | 2 | 否 | 短距战术；信道空闲则同回合送达 |
| BLINKER | 0 | +1 | 4 | 否 | 直接视觉/逐舰下传 |
| WT_CODED | 1 | +1 | 2 | 是 | 编码无线电报经消息中心 |
| WT_REENCIPHER_RELAY | 1 | +1 | 3 | 是 | 转报/再加密 |
| MULTI_HOP | 1 | +1 | 4 | 是 | 复合路由，合计可达 t+2 |
| BLACKOUT | — | — | 0 | 否 | 无通路，不发送 |

`delay_samples` 实测（审计记录原样）：

```json
{"tbs_short_sitrep": 0, "tbs_short_amendment": 1, "wt_coded": 1,
 "wt_reencipher_relay_1hop": 2, "multi_hop_1hop": 2, "blinker_2hops": 2}
```

即 TBS 短报文同回合可达；复杂任务修正案在 TBS 上 +1；编码 W/T +1；转报/再加密再 +1；视觉信号每级 +1。

**每个回合值都带 `label = SIMULATION_ABSTRACTION` 与一条 `source` 说明**，并在 `abstraction_note()` 中声明"不主张任何历史实测平均值"。玩家规则文档 `docs/rules/command-delay.md` 以同样措辞公布这些数值。

## 3. 距离只选媒介

`routing.select_medium` 是确定性规则序列，每条返回带 `reason`：

1. 无视距且无密码机 → BLACKOUT
2. 视距内且战术范围内 → TBS_SHORT
3. 视距内但超范围 → BLINKER（递次下传，1 个中继级）
4. 无视距但有密码机 → 若两端处于不同密码体系 → WT_REENCIPHER_RELAY，否则 WT_CODED
5. 否则 BLACKOUT

**距离不参与延迟计算**，只参与选择。战术范围直接复用想定自身给出的视距（`state.visibility[side]`），因此没有为通信另造第二个射程常量。

## 4. 拥塞：确定性、可解释、无随机

- 每条信道每回合固定容量（`CHANNEL_CAPACITY`：TBS 4、BLINKER 3、编码 W/T 2、转报 1、复合 1、BLACKOUT 0）。
- 排序键完全有序：`(优先级, 发出回合, 发出阶段序, message_id)`，因此不依赖 dict/set 迭代顺序。
- 优先级 `URGENT > OPERATIONAL > ROUTINE`；同优先级按发出顺序。
- 超过 TTL（默认 3 回合）的排队报文被丢弃并记录原因，发 `command_message_dropped` 事件。
- **无 `p_drop`/`p_garble`**：`integrity.py` 的默认策略是显式空操作；若传入带概率的策略但 `source` 为空，则**拒绝执行**并把 `unsourced probability refused` 写进报文原因。审计以源码扫描确认 `processing.py` 中不存在概率常量。

## 5. 完整一局的通信台账（IBS-S-01，7 回合）

```json
"messages_total": 77,
"statuses": {"delivered": 65, "queued": 12},
"mediums": {"tbs_short": 65, "wt_reencipher_relay": 11, "blackout": 1},
"handling_delays": {"0": 64, "1": 2, "2": 11},
"link_statuses": {"blackout": 2, "direct": 1, "relayed": 1},
"report_ages": [1, 2, 6, 6],
"issued_delivered_observed_all_set": true,
"delivered_never_before_issued": true
```

含义：

- 信道确实按媒介分层：TBS 同回合送达、转报需要 2 回合（11 条）、1 条因无通路（BLACKOUT）从未发出。
- **发出/送达/观察到三个回合字段齐备**，且 `delivered ≥ issued`（验收标准 8）。
- 报告年龄 `[1, 2, 6, 6]`：舰队对远端编队的认知确实在退化；链路状态出现 `relayed` 与 `blackout`（`direct` 是被搭载编队的物理链路），说明报告管线真的在跑。
- `link_status` 是**投递台账的函数**：只有真正收到更新的报告才会改善（`refresh_link_status` 只读 `reported_turn`）。

## 6. 两个在实现中修掉的缺陷

| 编号 | 缺陷 | 处置 |
|---|---|---|
| CD3-F1 | 航程会交叉：同回合的 TBS 报告可以超过更早发出的编码报告，于是**到达顺序 ≠ 新鲜度顺序**，旧报告会覆盖舰队更新的认知 | 报告与订单统一按**发出时间**判定（同回合用阶段序打破平局），被取代者标记 `SUPERSEDED` 并记录原因；`test_a_late_superseded_order_cannot_overwrite_a_newer_one` 与 `test_coded_reports_arrive_after_they_were_drafted` 覆盖 |
| CD2-F1 | `command_delay_initialised` 事件载荷含**双方**指挥链 | 改为每方一条事件并带 `secret_side`；泄漏审计把"命令延迟类事件必须带 `secret_side`"写成硬检查 |

## 7. 明确不做的事

- 不以"海里/公里直接换算回合延迟"。
- 不定义丢包率或错码率，也不给它们任何默认数值。
- 不在本阶段引入 `clarification_delay` 的独立概率模型：澄清走的是"再发一条报文"的同一队列（复杂任务修正案 +1 已体现拟稿与澄清成本）。
