# 数据模型变更（v2.3 相对 v2.2）

只列**语义性**新增/变更；纯注释不计。

## 新增枚举与取值

| 名称 | 取值 | 用途 |
|---|---|---|
| `CommunicationMedium.FACE_TO_FACE` | `face_to_face` | 当面交办成为独立媒介（容量 0，不占信道） |
| `RadioPolicy` | `normal` / `contact_only` / `scheduled_window` / `strict_silence` | 编队通信政策（IR-5） |

## 新增模型

| 模型 | 字段要点 | 用途 |
|---|---|---|
| `DelayBreakdown` | `propagation, handling, encoding, relay, reencipher, queue, clarification`（+`total` 计算属性） | 报文延迟分解（IR-2） |
| `RouteProvenance` | `sender_hex, recipient_hex, distance_hex, tbs_range_hex, direct_tbs_available, direct_visual_available, same_command_location, radio_policy, channel_state, selected_medium, route_nodes[], why_relay_required, why_reencipher_required, blockers[]` | 路由出处（IR-2） |
| `KnowledgeItem` | `subject_id, field, value, observed_turn, received_turn, source_kind, source_id, message_id, confidence`（+`age_turns`） | 逐收件人知识账本（IR-3） |

## 字段变更

| 模型 | 变更 |
|---|---|
| `CommandMessage` | 新增 `delay: DelayBreakdown`、`route_provenance: RouteProvenance \| None`；`*_delay` 事件负载新增 `delay_components` / `route_reason` / `distance_hex` / `tbs_range_hex` / `direct_tbs_available` |
| `MissionOrder` | 新增 `order_event`、`revision`、`amends_order_id`、`cancelled_turn`、`report_window_turns`；`is_active` 计算属性（IR-4） |
| `FormationCommandState` | 新增 `radio_policy`、`last_reported_hull`、`last_reported_contacts`、`pending_report_text`、`pending_report_actions`（IR-4/IR-5） |
| `CommandDelayState` | 新增 `knowledge: dict[str, list[KnowledgeItem]]`（IR-3） |
| `PlayerObservation`（编队视图） | **删除** `stale_external_reports`（那条能看见兄弟编队的窗户）；**新增** `knowledge`；`local_contacts[*]` 新增 `range_hex/range_yards/range_nmi`（IR-3/IR-6） |

## 冻结面影响

`models.py` 的改动全部是**追加**：没有字段被删除或改变类型（唯一删除的是**编队视图**上的
`stale_external_reports`，它是命令延迟模式的视图字段，不在黄金回放比对的四个树里）。
7 行 Classic/Realistic 黄金行逐字节未变。
