# 命令延迟 v2.3 · 实机对局战报（IR-9）

- 想定 / seed：`IBS-S-EM-01` / 19440619
- 模型：编队级 `llm:zhipu/glm-4.5-flash`，舰队级 `llm-fleet:zhipu/glm-4.5-flash`，思维链开启
- 结果：12 回合 · 平局：损伤分差 6，未达到 25 分；比分 轴心 30 : 24

## 断言

| 断言 | 结果 | 证据 |
|---|---|---|
| 零因果信息泄漏 | PASS | 扫描 76 条提示词，0 处发现 |
| 零单位换算违规 | FAIL | 5 处 |
| 零无据 CONFIRMED 敌情断言 | PASS | 0 处 |
| 零下级提交炮击令 | PASS | 0 处 |
| 无重复下达同一命令 | FAIL | 命令 32 条、修订 [1, 2, 3, 4, 5, 6, 7, 8]、重述 1 |
| 重演一致 | PASS | 80 阶段 / 0 不一致 |

## 报文台账（逐条含路由出处与延迟分解）

| 报文 | 类型 | 阵营 | 媒介 | 距离(格) | TBS可达 | 延迟分解 h/e/r/re/q/c | 合计 | 发出 | 送达 | 路由理由 |
|---|---|---|---|---|---|---|---|---|---|---|
| `MSG-00001` | mission_order | 日方 | TBS 直连 | 3 | 是 | 0/0/0/0/0/0 | 0 | T2 | T2 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00002` | mission_order | 日方 | TBS 直连 | 9 | 是 | 0/0/0/0/0/0 | 0 | T2 | T2 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00003` | mission_order | 美方 | TBS 直连 | 4 | 是 | 0/0/0/0/0/0 | 0 | T2 | T2 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00004` | mission_order | 美方 | TBS 直连 | 6 | 是 | 0/0/0/0/0/0 | 0 | T2 | T2 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00005` | acknowledgement | 日方 | TBS 直连 | 3 | 是 | 0/0/0/0/0/0 | 0 | T2 | T2 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00006` | acknowledgement | 日方 | TBS 直连 | 9 | 是 | 0/0/0/0/0/0 | 0 | T2 | T2 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00007` | acknowledgement | 美方 | TBS 直连 | 4 | 是 | 0/0/0/0/0/0 | 0 | T2 | T2 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00008` | acknowledgement | 美方 | TBS 直连 | 6 | 是 | 0/0/0/0/0/0 | 0 | T2 | T2 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00009` | acknowledgement | 日方 | TBS 直连 | 3 | 是 | 0/0/0/0/0/0 | 0 | T3 | T3 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00010` | acknowledgement | 日方 | TBS 直连 | 10 | 是 | 0/0/0/0/0/0 | 0 | T3 | T3 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00011` | acknowledgement | 美方 | TBS 直连 | 4 | 是 | 0/0/0/0/0/0 | 0 | T3 | T3 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00012` | acknowledgement | 美方 | TBS 直连 | 6 | 是 | 0/0/0/0/0/0 | 0 | T3 | T3 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00013` | contact_report | 日方 | TBS 直连 | 10 | 是 | 0/0/0/0/0/0 | 0 | T3 | T3 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟）；触发：接触数 0 → 2 |
| `MSG-00014` | mission_order | 日方 | 当面交办 | 0 | 是 | 0/0/0/0/0/0 | 0 | T4 | T4 | 同编队当面下令：当面交办，不占用通信链路 |
| `MSG-00015` | mission_order | 日方 | TBS 直连 | 10 | 是 | 0/0/0/0/0/0 | 0 | T4 | T4 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00016` | mission_order | 美方 | 当面交办 | 0 | 是 | 0/0/0/0/0/0 | 0 | T4 | T4 | 同编队当面下令：当面交办，不占用通信链路 |
| `MSG-00017` | acknowledgement | 日方 | TBS 直连 | 6 | 是 | 0/0/0/0/0/0 | 0 | T4 | T4 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00018` | acknowledgement | 日方 | TBS 直连 | 10 | 是 | 0/0/0/0/0/0 | 0 | T4 | T4 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00019` | acknowledgement | 美方 | TBS 直连 | 4 | 是 | 0/0/0/0/0/0 | 0 | T4 | T4 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00020` | acknowledgement | 美方 | TBS 直连 | 6 | 是 | 0/0/0/0/0/0 | 0 | T4 | T4 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00021` | contact_report | 日方 | TBS 直连 | 6 | 是 | 0/0/0/0/0/0 | 0 | T4 | T4 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟）；触发：接触数 0 → 11 |
| `MSG-00022` | contact_report | 日方 | TBS 直连 | 9 | 是 | 0/0/0/0/0/0 | 0 | T4 | T4 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟）；触发：接触数 2 → 12 |
| `MSG-00023` | contact_report | 美方 | TBS 直连 | 4 | 是 | 0/0/0/0/0/0 | 0 | T4 | T4 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟）；触发：接触数 0 → 3 |
| `MSG-00024` | contact_report | 美方 | TBS 直连 | 6 | 是 | 0/0/0/0/0/0 | 0 | T4 | T4 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟）；触发：接触数 0 → 3 |
| `MSG-00025` | contact_report | 日方 | TBS 直连 | 6 | 是 | 0/0/0/0/0/0 | 0 | T4 | T4 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟）；触发：编队损伤 1.0 → 0.5 |
| `MSG-00026` | mission_order | 日方 | TBS 直连 | 9 | 是 | 0/0/0/0/0/0 | 0 | T5 | T5 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00027` | mission_order | 美方 | 当面交办 | 0 | 是 | 0/0/0/0/0/0 | 0 | T5 | T5 | 同编队当面下令：当面交办，不占用通信链路 |
| `MSG-00028` | acknowledgement | 日方 | TBS 直连 | 6 | 是 | 0/0/0/0/0/0 | 0 | T5 | T5 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00029` | acknowledgement | 日方 | TBS 直连 | 9 | 是 | 0/0/0/0/0/0 | 0 | T5 | T5 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00030` | acknowledgement | 美方 | TBS 直连 | 4 | 是 | 0/0/0/0/0/0 | 0 | T5 | T5 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00031` | acknowledgement | 美方 | TBS 直连 | 6 | 是 | 0/0/0/0/0/0 | 0 | T5 | T5 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00032` | mission_order | 日方 | 当面交办 | 0 | 是 | 0/0/0/0/0/0 | 0 | T6 | T6 | 同编队当面下令：当面交办，不占用通信链路 |
| `MSG-00033` | mission_order | 美方 | TBS 直连 | 4 | 是 | 0/0/0/0/0/0 | 0 | T6 | T6 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00034` | acknowledgement | 美方 | TBS 直连 | 4 | 是 | 0/0/0/0/0/0 | 0 | T6 | T6 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00035` | acknowledgement | 美方 | TBS 直连 | 6 | 是 | 0/0/0/0/0/0 | 0 | T6 | T6 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00036` | mission_order | 日方 | 当面交办 | 0 | 是 | 0/0/0/0/0/0 | 0 | T7 | T7 | 同编队当面下令：当面交办，不占用通信链路 |
| `MSG-00037` | mission_order | 美方 | TBS 直连 | 7 | 是 | 0/0/0/0/0/0 | 0 | T7 | T7 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00038` | mission_order | 美方 | TBS 直连 | 9 | 是 | 0/0/0/0/0/0 | 0 | T7 | T7 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00039` | acknowledgement | 美方 | TBS 直连 | 7 | 是 | 0/0/0/0/0/0 | 0 | T7 | T7 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00040` | acknowledgement | 美方 | TBS 直连 | 9 | 是 | 0/0/0/0/0/0 | 0 | T7 | T7 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00041` | mission_order | 日方 | 当面交办 | 0 | 是 | 0/0/0/0/0/0 | 0 | T8 | T8 | 同编队当面下令：当面交办，不占用通信链路 |
| `MSG-00042` | mission_order | 美方 | TBS 直连 | 7 | 是 | 0/0/0/0/0/0 | 0 | T8 | T8 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00043` | mission_order | 美方 | TBS 直连 | 9 | 是 | 0/0/0/0/0/0 | 0 | T8 | T8 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00044` | mission_order | 美方 | 当面交办 | 0 | 是 | 0/0/0/0/0/0 | 0 | T8 | T8 | 同编队当面下令：当面交办，不占用通信链路 |
| `MSG-00045` | acknowledgement | 美方 | TBS 直连 | 7 | 是 | 0/0/0/0/0/0 | 0 | T8 | T8 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00046` | acknowledgement | 美方 | TBS 直连 | 9 | 是 | 0/0/0/0/0/0 | 0 | T8 | T8 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00047` | mission_order | 日方 | 当面交办 | 0 | 是 | 0/0/0/0/0/0 | 0 | T9 | T9 | 同编队当面下令：当面交办，不占用通信链路 |
| `MSG-00048` | mission_order | 美方 | 当面交办 | 0 | 是 | 0/0/0/0/0/0 | 0 | T9 | T9 | 同编队当面下令：当面交办，不占用通信链路 |
| `MSG-00049` | mission_order | 美方 | TBS 直连 | 7 | 是 | 0/0/0/0/0/0 | 0 | T9 | T9 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00050` | mission_order | 美方 | TBS 直连 | 9 | 是 | 0/0/0/0/0/0 | 0 | T9 | T9 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00051` | acknowledgement | 美方 | TBS 直连 | 7 | 是 | 0/0/0/0/0/0 | 0 | T9 | T9 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00052` | acknowledgement | 美方 | TBS 直连 | 9 | 是 | 0/0/0/0/0/0 | 0 | T9 | T9 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00053` | mission_order | 日方 | 当面交办 | 0 | 是 | 0/0/0/0/0/0 | 0 | T10 | T10 | 同编队当面下令：当面交办，不占用通信链路 |
| `MSG-00054` | mission_order | 美方 | TBS 直连 | 7 | 是 | 0/0/0/0/0/0 | 0 | T10 | T10 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00055` | mission_order | 美方 | TBS 直连 | 8 | 是 | 0/0/0/0/0/0 | 0 | T10 | T10 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00056` | acknowledgement | 美方 | TBS 直连 | 7 | 是 | 0/0/0/0/0/0 | 0 | T10 | T10 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00057` | acknowledgement | 美方 | TBS 直连 | 8 | 是 | 0/0/0/0/0/0 | 0 | T10 | T10 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00058` | mission_order | 美方 | 当面交办 | 0 | 是 | 0/0/0/0/0/0 | 0 | T11 | T11 | 同编队当面下令：当面交办，不占用通信链路 |
| `MSG-00059` | mission_order | 美方 | TBS 直连 | 7 | 是 | 0/0/0/0/0/0 | 0 | T11 | T11 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00060` | mission_order | 美方 | TBS 直连 | 7 | 是 | 0/0/0/0/0/0 | 0 | T11 | T11 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00061` | acknowledgement | 美方 | TBS 直连 | 7 | 是 | 0/0/0/0/0/0 | 0 | T11 | T11 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00062` | acknowledgement | 美方 | TBS 直连 | 7 | 是 | 0/0/0/0/0/0 | 0 | T11 | T11 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00063` | mission_order | 日方 | 当面交办 | 0 | 是 | 0/0/0/0/0/0 | 0 | T12 | T12 | 同编队当面下令：当面交办，不占用通信链路 |
| `MSG-00064` | mission_order | 美方 | 当面交办 | None | 否 | 0/0/0/0/0/0 | 0 | T12 | T12 | 同编队当面下令：当面交办，不占用通信链路 |
| `MSG-00065` | mission_order | 美方 | TBS 直连 | None | 否 | 0/0/0/0/0/0 | 0 | T12 | T12 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00066` | mission_order | 美方 | TBS 直连 | None | 否 | 0/0/0/0/0/0 | 0 | T12 | T12 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00067` | acknowledgement | 美方 | TBS 直连 | 6 | 是 | 0/0/0/0/0/0 | 0 | T12 | T12 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |
| `MSG-00068` | acknowledgement | 美方 | TBS 直连 | 6 | 是 | 0/0/0/0/0/0 | 0 | T12 | T12 | 在直连 TBS 射程内（视距语音；射程是配置值，不换算出延迟） |

### 单位违规明细

- formation allies: 把 [8, 10] 格写成海里：「8-10海里」
- formation allies: 把 [8, 10] 格写成海里：「8-10海里」
- formation allies: 把 [8, 10] 格写成海里：「8-10海里」
- formation allies: 把 [8, 10] 格写成海里：「8-10海里」
- formation allies: 把 [10] 格写成海里：「8-10海里」

## 命令修订线

| 命令 | 编队 | 事件 | 修订 | 修订自 | 签发回合 |
|---|---|---|---|---|---|
| `axis-order-2-axis-cruiser-line` | axis-cruiser-line | None | None | — | T2 |
| `axis-order-2-axis-destroyer-line` | axis-destroyer-line | None | None | — | T2 |
| `allies-order-2-allies-cruiser-line` | allies-cruiser-line | None | None | — | T2 |
| `allies-order-2-allies-destroyer-line` | allies-destroyer-line | None | None | — | T2 |
| `axis-nl-4-axis-battle-line` | axis-battle-line | NEW_ORDER | 1 | — | T4 |
| `axis-nl-4-axis-destroyer-line-r2` | axis-destroyer-line | AMEND_ORDER | 2 | axis-order-2-axis-destroyer-line | T4 |
| `allies-nl-4-allies-battle-line` | allies-battle-line | NEW_ORDER | 1 | — | T4 |
| `axis-nl-5-axis-destroyer-line-r3` | axis-destroyer-line | AMEND_ORDER | 3 | axis-nl-4-axis-destroyer-line-r2 | T5 |
| `allies-nl-5-allies-battle-line` | allies-battle-line | NEW_ORDER | 1 | — | T5 |
| `axis-nl-6-axis-battle-line` | axis-battle-line | AMEND_ORDER | 1 | — | T6 |
| `allies-nl-6-allies-cruiser-line-r2` | allies-cruiser-line | AMEND_ORDER | 2 | allies-order-2-allies-cruiser-line | T6 |
| `axis-nl-7-axis-battle-line` | axis-battle-line | AMEND_ORDER | 1 | — | T7 |
| `allies-nl-7-allies-cruiser-line-r3` | allies-cruiser-line | AMEND_ORDER | 3 | allies-nl-6-allies-cruiser-line-r2 | T7 |
| `allies-nl-7-allies-destroyer-line-r2` | allies-destroyer-line | AMEND_ORDER | 2 | allies-order-2-allies-destroyer-line | T7 |
| `axis-nl-8-axis-battle-line` | axis-battle-line | AMEND_ORDER | 1 | — | T8 |
| `allies-nl-8-allies-cruiser-line-r4` | allies-cruiser-line | AMEND_ORDER | 4 | allies-nl-7-allies-cruiser-line-r3 | T8 |
| `allies-nl-8-allies-destroyer-line-r3` | allies-destroyer-line | AMEND_ORDER | 3 | allies-nl-7-allies-destroyer-line-r2 | T8 |
| `allies-nl-8-allies-battle-line` | allies-battle-line | NEW_ORDER | 1 | — | T8 |
| `axis-nl-9-axis-battle-line` | axis-battle-line | AMEND_ORDER | 1 | — | T9 |
| `allies-nl-9-allies-battle-line` | allies-battle-line | AMEND_ORDER | 1 | — | T9 |
| `allies-nl-9-allies-cruiser-line-r5` | allies-cruiser-line | AMEND_ORDER | 5 | allies-nl-8-allies-cruiser-line-r4 | T9 |
| `allies-nl-9-allies-destroyer-line-r4` | allies-destroyer-line | AMEND_ORDER | 4 | allies-nl-8-allies-destroyer-line-r3 | T9 |
| `axis-nl-10-axis-battle-line` | axis-battle-line | AMEND_ORDER | 1 | — | T10 |
| `allies-nl-10-allies-cruiser-line-r6` | allies-cruiser-line | AMEND_ORDER | 6 | allies-nl-9-allies-cruiser-line-r5 | T10 |
| `allies-nl-10-allies-destroyer-line-r5` | allies-destroyer-line | AMEND_ORDER | 5 | allies-nl-9-allies-destroyer-line-r4 | T10 |
| `allies-nl-11-allies-battle-line` | allies-battle-line | AMEND_ORDER | 1 | — | T11 |
| `allies-nl-11-allies-cruiser-line-r7` | allies-cruiser-line | AMEND_ORDER | 7 | allies-nl-10-allies-cruiser-line-r6 | T11 |
| `allies-nl-11-allies-destroyer-line-r6` | allies-destroyer-line | AMEND_ORDER | 6 | allies-nl-10-allies-destroyer-line-r5 | T11 |
| `axis-nl-12-axis-battle-line` | axis-battle-line | AMEND_ORDER | 1 | — | T12 |
| `allies-nl-12-allies-battle-line` | allies-battle-line | AMEND_ORDER | 1 | — | T12 |
| `allies-nl-12-allies-cruiser-line-r8` | allies-cruiser-line | AMEND_ORDER | 8 | allies-nl-11-allies-cruiser-line-r7 | T12 |
| `allies-nl-12-allies-destroyer-line-r7` | allies-destroyer-line | AMEND_ORDER | 7 | allies-nl-11-allies-destroyer-line-r6 | T12 |
