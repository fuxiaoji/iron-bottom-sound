# 09 · 实机 LLM 对 LLM 对战与泄漏核验（CD-12）

**性质**：本文件记录 CD-12 批次——把命令延迟模式交给真实模型指挥打满一局，并把
"没有信息泄露"从口头断言变成可失败的检查。所有数字都能在仓库产物里逐条核对。

## 1. 对局事实

| 项 | 值 | 出处 |
|---|---|---|
| 想定 / seed | IBS-S-01 / 20270830 | `battle/battle_data.json` |
| 指挥方式 | 每个编队一个独立子代理（带本地记忆）+ 舰队总指挥子代理 | `battle/requests/`、`battle/responses/` |
| 子代理调用 | 25 次（23 次编队 + 2 次舰队总指挥），**0 超时** | `battle/driver.log` |
| 结果 | 7 回合，平局（轴心 8 / 同盟 5 胜利点，差 < 4），友军碰撞 0，沉没 3 | `battle_data.json: final` |
| 战报 | `battle/REPORT.md`，1082 行，28 张嵌入棋盘图 | `generate_battle_md.py` |

## 2. 命令延迟的实证（本模式要建模的东西真的发生了）

| 报文 | 发信人 | 媒介 | 拟制 | 送达 | 链路开销 |
|---|---|---|---|---|---|
| `MSG-00009` / `MSG-00010` | 引擎初始委派 | TBS | T2 | T3 | +1 回合 |
| `MSG-00027` / `MSG-00028` | **舰队总指挥（子代理）** | TBS | T3 | T4 | +1 回合 |

舰队总指挥 T3 写下的自然语言命令，编队**在 T4 才读到**——写命令的同一回合里无法据此行动。
编队自身的接触报告走 TBS 时 +0（同回合）、被排到再加密转报队列时 +2。全 72 条报文中
55 条同回合送达、13 条跨回合、4 条停战时仍在队列。

## 3. 代理自主性：必须打折扣（本批最重要的诚实项）

| 项 | 值 |
|---|---|
| 「回合×阵营」机动批次 | 12 |
| **执行的是代理自己的方案** | **7** |
| 被引擎整批驳回后回退确定性指挥官 | 5 |
| 首次回复即被采纳 / 首次被拒后重发获采纳 | 15 / 4 |

驳回原因是引擎的合法性闸门，不是战术分歧：`cannot follow guide trail before advancing`、
`speed N is outside member limits`、`cannot reverse 180 degrees`、
`forced movement prevents formation following`。

**含义**：任何"多智能体协作指挥"的结论只能按 7/12 记功。被驳回的阵营回合里，编队的动作
出自教条，代理的机动意图没有执行。回退**不改变信息边界**（确定性指挥官与代理读同一侧
过滤视图），所以它影响的是自主性结论，不是泄漏结论。

## 4. 泄漏核验：旧判据是空转的（审计缺陷，已重写）

**旧判据**：提示词里是否出现"读方尚未目视过的敌方舰名"。

**为什么它是空转的**：IBS-S-01 双方自第 1 回合起就在光学距离内——轴心可见全部 9 艘美舰、
同盟可见全部 5 艘日舰（`battle/leakage_scan.json: identity.first_sighting_turn` 逐舰可查，
`vacuous_in_this_scenario: true`）。该检查**永不可能 FAIL**。更糟的是它遍历的
`battle_data.json: agent_log` 条目里根本没有 `prompt` 字段，实际在扫空字典——却报了 PASS。
（同类的 CD8-F5 已经踩过一次"判据过宽/过窄"，这次是第三种错法：**判据不可失败**。）

**新判据（内容出处）**：提示词里的每个特征串都必须对它的读者有合法出处——读者自己编队
更早回合写下的内容，或已投递给它的一封舰队命令。非法来源有三类，一次覆盖：
敌方的文字、友邻编队的决策文字、**任何晚于当时的回合**的文字（第三类同时抓"敌方计划泄露"
与"读到明天的报纸"）。

**第二条判据（报文台账，精确、不需重放）**：提示词里每条
`received_messages[*].message_id` 都必须存在于引擎台账、属于同一阵营、收件人正确。
CD12-F2a/F2b 这类"跨阵营混入"正是它会拦下的。

**结果**：25 条传输记录（`requests/` 下每一份实际交给子代理的请求）、4760 个特征串、
其中 452 个有出处可溯、**0 违规 PASS**。

**正对照（PASS 之所以算证据，`scan_battle_leakage.py --self-test`）**：把**本局真实存在**
的字符串注入一份真实轴心请求，扫描器必须报错——敌方舰队命令原文、敌方编队决策理由原文、
敌方报文台账条目，三项全部被抓（`battle/self_test.json`），未注入基线为 0。

**本核验未覆盖的范围**：审计对象是传输面（代理"推断"出什么不在范围内）；可见包子项靠
确定性指挥官重放近似（内容出处与台账两项不依赖重放）；本局**不可逐位重放**（驱动未持久化
被采纳的指令批次），因此这是记录审计而非可复现实验；`REPORT.md` 本身含双方视角，
**不得作为代理输入**。

## 5. 两处「记录得到、但没接线」（未修，待 PI 裁决）

| 编号 | 事实 | 代码位置 |
|---|---|---|
| **CD12-F3** | 代理确认不进报文台账：`MessageKind.ACKNOWLEDGEMENT` 分支直接 `return`；`CommandMessage.acknowledged_turn` **全仓库无写入点**；`MissionOrder.confirmed_turn` 在送达时即写送达回合（"送达"被当成"确认"）。本局 0 条确认记录，尽管代理 5 次决策明确确认、2 次选择发出 ACKNOWLEDGEMENT | `command_delay.py:_apply_delivery`、`models.py` |
| **CD12-F4** | 代理的 `report_actions`（SITREP / CONTACT_REPORT / ACKNOWLEDGEMENT）只落到本地记忆 `report_sent` 条目与决策记录，**不生成也不改变任何报文**；台账 68 条接触报告全由 `draft_reports` 在阶段边界自动起草。即下级上报目前是引擎的自动参谋作业，代理不能决定何时/向谁/报告什么 | `command_delay.py:_record_memory`、`draft_reports` |

两者都属**冻结模式的语义**：改动会使命令延迟模式的黄金回放基线漂移，需先在
`GOLDEN_INDEX.json` 记录归因并重冻结，故本批只登记、不自行修改。CD12-F3 的修法是明确的
（代理回复带 `acknowledgement=True` 时回写台账确认回合并发事件）；CD12-F4 属新机制，
建议单列一批。

## 6. 复现

```bash
# 重画配图（从原始截图裁剪 + 拼回六角标尺）
.venv/bin/python research/command_delay/crop_battle_images.py --force
# 由 battle_data.json 重生成战报
.venv/bin/python research/command_delay/generate_battle_md.py
# 泄漏核验 + 正对照
.venv/bin/python research/command_delay/scan_battle_leakage.py
.venv/bin/python research/command_delay/scan_battle_leakage.py --self-test
```

对局本身无法从产物重跑（子代理回复需真实模型 + 桥接服务循环
`.zcode/workflow-drafts/命令延迟模式-LLM-对战.dwf.ts`）；`battle/requests|responses/`
里保留了每一次调用的原文与回执，供逐条复核。
