# 缺陷与重跑日志（v2.3 批次）

只记**真实发生**的问题，含成因、修法与证据。

## 审计/判据侧（本项目的高发区）

### IR1-F1 · 旧泄漏判据的"看见兄弟编队"窗口（已修，属被测系统）
`command_observation._external_reports()` 把舰队持有的兄弟编队报告位直接给每个编队。
修法见 `02_CAUSAL_INFORMATION_AUDIT.md`；原测试把该行为当作预期断言，已重写。

### IR2-F1 · 我的重演脚本删掉了两个辅助函数
重写 `draft_reports` 时用切片替换，把夹在锚点之间的 `_encode_snapshot` / `_decode_snapshot`
一并删掉，直到测试报 `NameError` 才发现。已恢复（它们负责 HexCoord/枚举的 JSON 往返）。

### IR3-F1 · 泄漏审计判据过严（假阳性）
新知识账本天然**累积**：编队 T4 仍持有 T2 见过的舰。审计若按"当前可见"比对就会误报。
改为按**曾目视集合**判定（`ever_sighted`），并把 `knowledge` 纳入收紧判据而非豁免。

### IR5-F1 · 默认条令自己在要求逐回合报告
`mission_order_template` 的 `report_requirements` 里写着 `"sitrep each turn the link supports it"`——
这正是 IR-5 要删除的教条，而它藏在**模板默认值**里，不在触发逻辑里。删除该条，
并让 `periodic_due` 只认显式标记（PERIODIC / 定期 / SCHEDULED / EACH TURN）。

### IR5-F2 · 一条旧断言只在"上报很啰嗦"时成立
`test_link_and_authority_degrade_and_recover_from_the_ledger` 要求 `local_autonomy ⇒ BLACKOUT`。
CD8-F3 之后 `STALE` 同样降级为自主，但 v2.2 的啰嗦上报让链路**从不**变 STALE，
所以旧断言一直"通过"——它不是对的，只是够不着。事件驱动上报让它可达，断言随之修正为
`STALE 或 BLACKOUT`。

### IR4-F1 · 同回合两令撞号（撤销静默失效）
`order_id = f"{side}-nl-{turn}-{formation}"` 在同一回合下达"命令 + 撤销"时重复，
投递时按 id 解析回**原令**，于是撤销令被当成原令的重发、`active_order_id` 未被清空。
修法：`revision > 1` 时 id 带修订后缀。

### IR8-F1 · "棋盘边界拒绝"与引擎实际语义不一致（登记待裁）
计划要求测试 `board-edge rejection`。实测：`movement_preview()` 对"会走出棋盘"的程序
**返回 commitable=True**（它校验命令/程序/航速，不校验逐格落点），边界由**结算**保证——
`HexCoord.neighbor()` 越界抛 `ValueError("Movement leaves the map")`，该步按障碍处理
（引擎内 `obstacle = "edge"`）。也就是说**不存在"非法"这一档**。
把它改成下令即拒绝会改动**真实模式**语义，而本批次的硬约束是真实模式冻结（7 行逐字节未变），
故只登记、不改，测试改为断言引擎真正保证的不变量（结算后没有舰只在棋盘外）。

### CD12-F5/F6/F7（前批，仍适用）
判据不可失败 / 检查从未执行 / 只数条数不问归属——本批次所有新判据都配了正对照或负对照，
见各自文档与 `raw/` 下的证据文件。

## 被测系统侧（v2.2 的实质缺陷）

| 编号 | 缺陷 | 证据 | 状态 |
|---|---|---|---|
| CD12-F2a | `formation_orders()` 未按阵营过滤 → 每回合整批被拒、静默回退教条 | `battle_contaminated_run1/` 12 条记录 | 已修（CD-12） |
| CD12-F2b | `gunnery_batch()` 未过滤 `local_directives` → 一方火力权重进对手选择器 | 同上 | 已修（CD-12），并加"必须由本方签发"不变量 |
| IR2-F2 | TBS 射程误用光学能见度 → 55 条虚假转报 +2 | `raw/old_message_route_audit.csv` | 已修（IR-2） |
| IR2-F3 | 跨编队被当作跨密码体系 → `WT_REENCIPHER_RELAY` | 理由字符串只有一种，且指向不存在的密码域 | 已修（IR-2） |
| IR2-F4 | "长命令 +1" | 63 封任务命令都吃了这 +1 | 已修（IR-2），改为槽位/排队 |
| IR3-F2 | 兄弟编队报告越权可见 | 原测试断言了它 | 已修（IR-3） |
| IR4-F2 | 命令每回合重发（11 回合 63 封） | battle_em01 记录 | 已修（IR-4） |
| IR5-F3 | 每阶段每编队一份报告（77 封/6 封） | `cd_s01` 前后对比 | 已修（IR-5） |
| IR6-F1 | 12–15 格被写成 12–15 海里 | CD-13 战报正文 | 已修（IR-6），有回归测试 |
| IR6-F2 | "衣阿华确认击沉"式无据断言 | CD-13 战报 | 已修（IR-6），有回归测试 |
