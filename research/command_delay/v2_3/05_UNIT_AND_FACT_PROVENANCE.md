# 05 · 单位与事实出处（IR-6）

## 1. 单位：引擎负责换算，模型不得自己换算（`claims.range_prose` / `range_units`）

CD-13 战报里出现过把 **12–15 格**写成 **12–15 海里**的句子（真实值约 3.55–4.44 海里，
差约 3.4 倍）。修法不是"提醒模型注意单位"，而是**不给它换算的机会**：

- `local_contacts[*]` 现在同时带 `range_hex` / `range_yards` / `range_nmi`，三者由
  `communications.processing.range_units()` 用权威量纲（600 yd/格）一次算出；
- 任何要写进报告的距离，先从结构化字段取，再由 `range_prose()` 渲染成
  `"12 格（约 3.55 海里）"`；
- 回归测试 `test_the_old_twelve_hex_twelve_miles_error_is_caught`：
  旧句 `"距离 12 至 15 海里"` 被判为**单位错误**；正确渲染 `"12 格（约 3.55 海里）"` 不误报；
  短距（<5 格，两单位数值本就接近）明确不追究，避免噪声。

## 2. 事实出处：断言的可信度由来源决定，不由措辞决定（`claims.py`）

```text
CONFIRMED  本编队自己的目视/观测确立
REPORTED   由投递给本编队的报文带来（带 message_id）
INFERRED   由本编队已持有的事实推出
SUSPECTED  没有来源支撑，只是说话人的判断
```

- `claims.grade()` 从**知识账本**（IR-3 的 `KnowledgeItem`）取来源，句子里的"确认"二字
  不能把等级抬上去；
- `claims.unsupported_confirmed()` 找出"说了 CONFIRMED 但没有来源"的句子——
  这正是 PI 点名的 "Iowa confirmed sunk" 情形；
- 回归测试：
  - 空账本 + `"衣阿华已被确认击沉。"` → **判定为无据**（等级落到 SUSPECTED）；
  - 账本里有本编队亲眼所见（`LOCAL_OBSERVATION` 的 SUNK）→ 允许；
  - 账本里只有投递报文带来的 SUNK（`DELIVERED_MESSAGE`）→ **不再是"无据"**，
    但等级被降为 **REPORTED**（句子写的"确认"无效）——这就是计划里 A/B 两条分支的具体形态；
  - 措辞与等级无关：`"确认击沉！"`（无账本）→ SUSPECTED；`"可能已经沉没"`（有目视）→ CONFIRMED。

## 3. 与 IR-9 的关系

IR-9 的对局报告必须断言 **zero unit conversion violations** 与
**zero unsupported CONFIRMED enemy-state claims**；本模块的
`claims.miles_claimed_for_hexes()` 与 `claims.unsupported_confirmed()` 就是那两条断言的执行体。

## 4. 边界

- 断言抽取是**关键词级**的（击沉/重创 + 舰名/id），不是通用自然语言理解：它只覆盖本模式
  关心的敌情断言，未覆盖的措辞不计入统计（宁可少报也不误报，且这一取舍写在这里）。
- `INFERRED` 目前只在"句子含推断连接词"时给出；完整的推断链重建不在本批次范围。
