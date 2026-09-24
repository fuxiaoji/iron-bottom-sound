# 04 · 事件驱动上报与通信政策（IR-5）

## 1. 问题

v2.2 的默认条令要求**每回合一份态势报告**（`mission_order_template` 的
`report_requirements` 里写着 `"sitrep each turn the link supports it"`），加上引擎在每个阶段边界
为每个编队起草报告：CD-13 那局 141 封报文里绝大多数是"无变化"，`cd_s01` 黄金行 77 封报文、
其中 75 封是这类例行通报。无信息的报文同样占信道、同样排队，并且让指挥官的态势图**看起来**
比实际更新——这是"上报"本身在制造错误认知。

## 2. 修法

### 2.1 触发式上报（`reporting.py` + `command_delay.draft_reports`）

只有**发生了什么**才起草报告，优先级从高到低：

```text
FLAGSHIP_LOSS       -> 紧急（旗舰沉没）
MAJOR_DAMAGE        -> 紧急（一个阶段内编队完好的 20% 以上被打掉）
NEW_CONTACT         -> 紧急（接触数增加）
MISSION_COMPLETE    -> 例行（命令期限已到）
PERIODIC_DUE        -> 例行（现行命令明确要求定期报告）
MISSION_DEVIATION / CLARIFICATION_NEEDED -> 由编队 agent 主动发出（不是例行）
```

- **没有触发就不发报**，并且不发的原因不是"静默"，而是"无事可报"；
- **默认条令不再要求逐回合报告**（`mission_order_template` 删掉该条），定期报告必须由命令
  显式请求（`PERIODIC_SITREP` 等标记）；`report_window_turns` 表示"在指定回合报告"；
- 引擎决定**要不要报**，agent 决定**报什么**：agent 在机动阶段把正文与动作写入
  `pending_report_text/pending_report_actions`，触发通过时由 `draft_reports` 附上并发出；
  agent 显式选择的偏离报告/澄清请求属于信号而非例行，当场发出（同样过政策闸门）。

### 2.2 通信政策（`RadioPolicy`）

```text
NORMAL            全部可发
CONTACT_ONLY      只发接触/紧急，不发例行态势
SCHEDULED_WINDOW  例行只在窗口回合发
STRICT_SILENCE    例行一律不发；只有"遇袭/旗舰损失"这类编队无权隐瞒的紧急例外
```

- 政策在**起草之前**判定，被拦下的报文**不会产生**——所以不可能出现"本回合发着例行报文，
  同时在报文中声称正在无线电静默"这种自相矛盾（计划 §8 的明确要求）；
- 拦截会记 `report_suppressed` 事件（含触发类型、政策、原因），沉默是**被记录的**；
- 政策随 `FormationCommandState.radio_policy` 存储，并写入 agent 提示词（`policy_note`），
  让模型知道自己的通信约束。

## 3. 测试（`tests/test_command_delay_reporting_v23.py`，4 项）

| # | 计划要求 | 测试 |
|---|---|---|
| 1 | 无变化的 5 回合任务不产生例行报文，除非命令要求 | 3 回合无接触无损伤 → **零报文**；附上要求定期报告的命令（含窗口）→ 产生且 `trigger=PERIODIC_DUE`；去掉该要求后同样几何**又回到零报文** |
| 2 | 新接触能正确突破 CONTACT_ONLY | 无接触时静默；出现接触 → 只发接触报告（URGENT）；例行条目在同一政策下被拒并给出原因 |
| 3 | 严格静默拦住例行报告 | 被静默的编队**一条都没发出**（无同回合"边说静默边发报"），且留下 `report_suppressed` 事件；遇袭时政策让路 |
| 4 | 排队的紧急接触优先于例行 | 填满信道后，URGENT 接触拿到最后一个时隙，被留下等待的是例行报文 |

## 4. 实测效果（黄金行 `cd_s01`，同一想定同一 seed）

| 指标 | 修前 | 修后 |
|---|---|---|
| 报文总数 | 77 | **6** |
| 其中跨回合延迟 | 10 | 0 |
| 事件总数 | 714 | 570 |
| 代理决策数 | 19 | 19（**不变**：仍然每回合决策，只是不再每回合发报） |
| 终局 | T7 complete / passed | T7 complete / passed |

连带可归因的变化：`gunnery_result 102→101`、`ship_sunk 6→5`、`rng_counter 228→226`。
原因明确：火力优先级指令由**已投递的命令与报告**构成，上报量变化会改变进入选择器的
指令集合，于是有一处交战不再发生（两次骰点即该次结算）。已记入
`GOLDEN_INDEX.json` 的 `refreeze` 归因（含前后 digest 与七行未变的 sha256）。

## 5. 边界

- `PERIODIC` 的默认周期（命令未给窗口时）写成固定的"每三回合"，标注为**仿真抽象**，不是史料值。
- 报告是否"有价值"由触发器定义，不由模型判断；模型仍可**主动**发偏离/澄清信号。
