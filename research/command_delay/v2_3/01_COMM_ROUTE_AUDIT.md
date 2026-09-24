# 01 · 通信路由与延迟出处审计（IR-1）

**对象**：`research/command_delay/battle_em01/`（CD-13 二马剧本对局，v2.2 路由规则），
原始证据已按 IR-0 复制到 `raw/battle_em01/`，未移动、未覆盖。
**产出**：`raw/old_message_route_audit.csv`（逐条报文）、`raw/ir1_route_audit_summary.json`。

---

## 1. 先测量，不引用记忆值

| 量 | 值 | 出处 |
|---|---|---|
| 标准棋盘尺寸 | 46 × 39 hex | `models.MAP_COLUMNS/ROWS`（S-01 与 EM-01 相同） |
| **棋盘最大合法六角距离** | **83 hex**（(0,0) → (45,38)） | 本次枚举全部格对计算 |
| 历史 TBS 标称射程 | ≈ 25 法定英里 @ 600 yd/hex ≈ **73 hex** | 计划 §1 的来源约定 |
| 本局实际报文距离 | 最小 0 / 均值 15.0 / **最大 42** hex | 逐条重算（`raw/old_message_route_audit.csv`） |
| 落在 73 hex 以内的报文 | **137 / 141** | 同上 |

**结论（须如实记录）**：标准棋盘的**极端对角**（83 hex）确实超出 73 hex 的标称 TBS 射程，
所以"距离永远不会影响可达性"并不成立——但它是病态几何（两舰分居对角），
本局没有任何一条报文接近该量级：实际最大 42 hex，均值 15 hex，**全部在 TBS 射程内**。
因此"距离导致回合延迟"在本局中**没有任何一条**是成立的。

---

## 2. v2.2 的路由实现（代码证据）

`backend/src/iron_bottom_sound/command_delay.py::route()`

```python
return select_medium(
    distance=distance,
    tactical_range=int(state.visibility[origin.side.value]),   # ← 光学地平线，不是 TBS 射程
    line_of_sight=line_of_sight,
    coded_available=True,
    relay_available=not same_command,                            # ← 只要不是同一编队就是 True
)
```

`communications/routing.py::select_medium()` 的规则（逐条有 reason 记录）：

1. 无视线且无编码能力 → `BLACKOUT`；
2. 有视线且距离 ≤ `tactical_range` → `TBS_SHORT`；
3. 有视线但超出 `tactical_range` → `BLINKER`（`relay_available` 时 1 跳）；
4. **无视线但有编码能力**：`relay_available` → `WT_REENCIPHER_RELAY`（1 跳），
   否则 `WT_CODED`；
5. 其余 → `BLACKOUT`。

`communications/processing.py::delay_for()`：`WT_REENCIPHER_RELAY` 基础 +1、每跳 +1 → **+2**；
`TBS_SHORT` 对 `MISSION_ORDER/AMENDMENT/CLARIFICATION` 额外 +1（"复杂任务"）。

### 两个缺陷，逐字对应 PI 的更正

- **缺陷 A（距离规则用错了射程）**：传入的 `tactical_range` 是**想定的光学能见度**
  （本局实测为 **13 或 15 hex**），被当作 TBS 射程使用。于是 14–42 hex 的报文一律被判"超出战术范围"。
- **缺陷 B（无依据的转报再加密）**：`relay_available = not same_command` 使**任何跨编队报文**
  在失去视线时进入 `WT_REENCIPHER_RELAY`，理由字符串写作
  `"coded set but the ends are under different ciphers"`。本模式**根本没有密码域模型**：
  两端的"密码不同"仅仅因为它们属于不同编队。这正是计划 §2.4 明令禁止的那种选择。

---

## 3. 逐条审计结果（141 封报文）

| 指标 | 值 |
|---|---|
| 报文总数 | 141 |
| 按媒介 | `tbs_short` 84 · `wt_reencipher_relay` **55** · `blackout` 2 |
| 按阵营 × 媒介 | 轴心：TBS 61 + 断路 2（**无一封转报**）；同盟：TBS 23 + **转报再加密 55** |
| 距离（hex） | 最小 0 · 均值 15.0 · 最大 42 · 位置无法解析 4 |
| 落在 TBS 射程（73 hex）内 | 137 / 141 |

**标记统计**

| 标记 | 条数 | 含义 |
|---|---|---|
| `UNJUSTIFIED_REENCIPHER` | **55** | 全部转报再加密报文：无密码域转换依据 |
| `UNJUSTIFIED_RELAY` | **55** | 同上：`relay_hops=1` 但路由里不存在任何中继节点 |
| `MISSING_RELAY_OR_CRYPTO_PROVENANCE` | **55** | 缺少 v2.3 要求的 `relay_nodes[]` / `why_relay_required` / `why_reencipher_required` |
| `DIRECT_TBS_AVAILABLE_BUT_NOT_USED` | **51** | 距离在 TBS 射程内却未走直连 TBS（另 4 条因位置不可解析未计入） |
| `DISTANCE_DELAY_BUG` | **49** | 距离 > 光学能见度、但 ≤ TBS 射程、且被计了延迟 → 延迟来自错误的射程规则 |
| `MISSING_ROUTE_PROVENANCE` | 0 | 每条都有 reason 字符串（但见下：部分是**不成立的理由**） |

---

## 4. 逐条解释 PI 点名的两类报文

### 4.1 所有 55 封"转报再加密 +2"的报文

| 类型 | 条数 |
|---|---|
| `mission_order`（总指挥命令） | 18 |
| `acknowledgement`（编队确认） | 18 |
| `contact_report`（接触报告） | 12 |
| `sitrep`（态势报告） | 6 |
| `deviation_report`（偏离报告） | 1 |

距离分布：10–19 hex 6 条、20–29 hex 32 条、30–39 hex 6 条、40+ 7 条、位置不可解析 4 条。
理由字符串只有两种，且都指向同一个不存在的实体：
`"coded set but the ends are under different ciphers"`（以及偏离报告的同句变体）。

**判定：这 55 条全部是 `UNJUSTIFIED_REENCIPHER`（实现缺陷，不是历史条令）。**
理由：模式内不存在密码域概念，也不存在任何中继节点；"跨编队"被错当成了"跨密码体系"。
按更正的规则，它们的目标距离（≤42 hex < 73 hex）**全部具备直连 TBS 条件**，
正确的媒介是 `TBS_DIRECT`，正确的基础延迟是 **0**（复杂任务的 +1 另见 §5）。

### 4.2 为什么轴心的远程编队电报多为 TBS +1，而同盟却掉进 +2？

**不是国别差异，是位置与时机的差异。** 逐条重算给出三个事实：

1. 轴心 61 封走 TBS 的报文，都满足"有视线且距离 ≤ 光学能见度"（13/15 hex）这一条旧规则；
2. 同盟那 55 封，相当一部分距离落在 14–42 hex——**超出的不是 TBS 射程，而是光学能见度**；
3. 旧规则里"失去视线"是进入编码/转报分支的唯一入口，而 `relay_available` 对跨编队恒为真，
   于是一旦失去视线就必然落到 `WT_REENCIPHER_RELAY`。

换句话说：**同盟舰队当时队形更散、报告链路更长**（其上报最长跨 42 hex），
而轴心的报文恰好更多落在自家 13/15 hex 的光学圈内。国别（`side`）在代码里
从未参与选路——这本身就是"不得发明国别不对称"的正面证据，但也说明
**当时的"不对称"完全是射程常量用错造成的副产品**。按更正的 TBS 射程（73 hex），
本局 137 条报文全部具备直连条件，国别差异随即消失。

---

## 5. 连带发现：'长命令 +1' 也违例

`processing.delay_for()` 对 `TBS_SHORT` 且类型属于 `MISSION_ORDER/AMENDMENT/CLARIFICATION`
的报文**额外 +1**，理由是"复杂任务需要额外汇编与澄清"。这正是计划 §2.2 禁止的
"long/complex mission text must NOT automatically get +1 just because it is long"。
本局 63 封任务命令中，凡走 TBS 的都吃了这 +1。

**修法（IR-2）**：删除该种类规则，把溢出改为**有限信道容量 / 排队 / 确认 / 澄清**的结果，
并且每一处都必须在报文的 `queue_delay` / `clarification_delay` 分量里可见。

---

## 6. 审计判据自身的边界（如实声明）

- 位置取自 `battle_data.json` 内嵌的上帝视角快照（签发回合 + 阶段），
  同回合内按阶段序取"不晚于签发阶段"的最近快照；**4 条报文的位置无法解析**
  （签发阶段在该回合快照集中不可定位），已在 CSV 中标为空并在统计里单列，未做插值。
- 视线（line of sight）的**真假**不由本审计重算：本审计只报告距离与旧规则的分支结果，
  视线事实取自 v2.2 代码路径的**分支含义**（进入编码分支即意味着当时判定为无视线）。
  逐条视线重算需要引擎重放，属 IR-2 的回归测试范围。
- 本审计读的是**旧记录**，不修改任何旧产物；
  v2.3 的路由与延迟分解在 IR-2 实现，并在 IR-9 的对局里以新字段复验。
