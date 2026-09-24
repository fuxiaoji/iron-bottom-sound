# 02 · 逐收件人的因果信息边界（IR-3）

**结论**：v2.2 的「编队 can see 兄弟编队报告」是一条真实的因果泄露，已在代码里关闭；
新机制是**带出处的知识账本**（`KnowledgeItem`），并有 4 项针对性测试与审计判据加固。

---

## 1. 缺陷（PI 判定的 `CAUSAL_INFORMATION = FAIL`）

`command_observation._external_reports()` 把**兄弟编队的最近报告位**直接塞进每个编队的视图：

```python
for other in command_delay.active_formations(state, side):
    if other.id == formation_id: continue
    entry = mode.formations.get(other.id)      # ← 舰队的知识副本
    if entry is None or entry.reported_position is None: continue
    found.append(FormationReport(..., guide_position=entry.reported_position, ...))
```

`mode.formations[x].reported_*` 是**舰队**收到并记下的知识。于是编队 A 能读到兄弟 B 的
位置/航向/舰数，而**没有任何报文投递给 A**。原测试
`test_formation_view_records_stale_external_reports_for_other_formations` 把这条泄露
当作预期行为断言下来——这正是判据本身在保护缺陷的例子。

## 2. 修法

1. **删除** `_external_reports` 与视图字段 `stale_external_reports`（视图不再有这条窗户）。
2. 新增**知识账本** `CommandDelayState.knowledge: dict[formation_id, list[KnowledgeItem]]`：

```text
KnowledgeItem: subject_id, field, value, observed_turn, received_turn,
               source_kind(LOCAL_OBSERVATION | DELIVERED_MESSAGE),
               source_id, message_id?, confidence
```

3. **写入口只有两个**（`formation_knowledge.py`）：
   - `record_local_observation(...)`：本编队**自己的**目视接触（每个机动阶段，对每个在役编队，
     无论是否由模型指挥——账本是状态事实，不是有模型的副产品）；
   - `record_delivered_report(state, message)`：**只对收件人**记账：报告的结构化事实
     （报告方自身的位置/航向/航速/舰数与亲笔正文），`observed_turn` 取**签发回合**、
     `received_turn` 取**送达回合**，并记下 `message_id`。
4. 视图改带 `knowledge`（本编队自己的事实），提示词同步（`formation_llm.build_prompt`）。
5. 研究钩子的通信特征块从"兄弟报告最大年龄"改为"本编队知识的最大年龄"。

## 3. 测试（`tests/test_command_delay_causal_information_v23.py`）

| # | 计划要求 | 测试 |
|---|---|---|
| 1 | 注入未见过的敌方 ID → 必须失败 | 敌对主体必须**全部**落在本编队可见接触内；学习类事实必须带 `message_id`（正对照见 IR-9 的注入测试） |
| 2 | 兄弟 T4 发现敌情、T6 报到舰队；未转投给 C → C 在 T4/T5/T6 不得知道 | 兄弟报告投给舰队后，**兄弟编队自身视图不含该事实**；再投递给它后才允许 |
| 3 | 在 T7 投递给 C → C 可以知道 | 同一测试的后半段（压缩到 T5 投递；机制按 `delivered_turn` 记账，与具体回合无关） |
| 4 | 延迟报告带旧位置：暴露 `observed_turn` 与年龄 | 舰队视图 `reported_turn=3 / age=2`；知识条目 `observed_turn=3, received_turn=5, age=2` |
| 5 | 舰队在投递前不得知道 | 舰队对**他队**的事实必须全部是 `DELIVERED_MESSAGE` 且有 `message_id`；舰队从不在账本里持有"自己的敌情目视"（那属于随队编队） |

## 4. 审计判据加固（`run_audits.audit_leakage`）

- 编队视图的敌舰 ID 扫描新增对 `knowledge` 的**收紧判据**（不是豁免）：
  `LOCAL_OBSERVATION` 主体必须在该编队**曾**目视过的集合内（知识天然是累积的——T4 时
  仍持有 T2 见过的舰，这是账本的意义），`DELIVERED_MESSAGE` 主体必须带 `message_id`；
- 其余字段仍按原判据（除 contacts / priority options / knowledge 外不得出现敌舰 ID）。

修完后 8/8 审计 PASS；`cd_s01` 黄金行未变（知识账本只影响视图，不影响确定性决策路径）。

## 5. 边界声明

- 账本**有界**（每编队 400 条，超出丢最旧），与记忆同规格。
- 本批次只做到"事实级出处"；**敌情断言的可信度分级**（CONFIRMED / REPORTED / INFERRED /
  SUSPECTED）是 IR-6，它在 `KnowledgeItem.confidence` 之上继续建。
- 舰队级视图仍按 `mode.formations[x].reported_*`（投递给舰队的报告）呈现他队——
  这是**合法**的：那些报告确实投递给了舰队。
