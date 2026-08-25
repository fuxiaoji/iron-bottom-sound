# 存档/状态表示设计：一个真相源 + 两种投影

> 目标：让一局铁底湾的状态**既易读、LLM 无需多模态即可解析空间关系**，又**便于直接进入 GPU 做 CNN/Transformer 训练**。本批只出设计方案，不实现导出代码。

## 0. 结论摘要

- **真相源不动**：现有 SQLite（`games` 全量 state_json / `events` append-only / `snapshots` 每序列全量）继续作为唯一事实来源。见 [backend/src/iron_bottom_sound/storage.py](../../backend/src/iron_bottom_sound/storage.py)。
- **投影一（LLM / 人可读）**：JSONL 世界态 + **cell-aligned ASCII/整数棋盘**（918 格矩形 + 坐标表头 + 图例）。LLM 文本空间推理（TopoBench 实证 cell-aligned 整数表示提升 30–40pp）依赖"每格一个 token + 坐标表头 + 图例"，不要用字符画/ASCII art 风格。
- **投影二（GPU CNN/Transformer）**：918 格多通道特征张量 `.npz`。以 `field_of_fire_heatmap`（[engine.py:683](../../backend/src/iron_bottom_sound/engine.py#L683) 扫 34×27 格 → 数值层）为网格量化模板，配**动作合法掩码**与**静态/动态切分**。
- **推荐路线**：本批文档 → 下一步最小导出（JSONL + ASCII，LLM 可读优先）→ 再下一步张量导出 + 离线收集对局数据训练。

---

## 1. 现状盘点（已核实）

- **存储**：SQLite WAL，三表——`games(game_id, state_json 全量)`、`events(game_id, sequence, event_json)`（append-only 审计）、`snapshots(game_id, sequence, state_json)`（每 sequence 全量盘面）。全部 pydantic `model_dump_json()`，**无 diff、无二进制**。`snapshots` 按 `sequence` 标定连续盘面，`events` 给中间动作 → 天然构成 `(state_t, action_t, state_{t+1})` 训练元组来源。
- **空间数据齐备**：船 / 鱼雷轨 / 沉船 / 标记都有轴向 `HexCoord{q,r}` 或 hex 标签。棋盘 **34 列 × 27 行 = 918 格**（`q ∈ [0,33]`，`row ∈ [0,26]`，轴向矩形量化见 [engine.py:708-712](../../backend/src/iron_bottom_sound/engine.py#L708-L712)）。
- **现成数值层模板**：`field_of_fire_heatmap`（engine.py:683）已实现"扫 918 格 → 每格热值"的只读网格化，是张量投影的扫描逻辑蓝本。
- **事件双轨**：`GameEvent{sequence, turn, phase, type, message(中文), payload(结构化), rule(RuleReference 页码/章节), dice}`（[models.py:402](../../backend/src/iron_bottom_sound/models.py#L402)）。既是人读叙事（message），又是可机器消费的动作/骰子/修正流（payload + rule_id），供 LLM 检索验证。
- **现状的不足**：
  1. 全量 JSON 静态字段逐帧冗余（`speed_track`/`speed_damage_track`/`gun_mounts` 全量/装甲浮点/vp/asset/name 每帧重复）→ 直接喂张量是噪声。
  2. 空间关系藏在嵌套 JSON 的 `position: {q, r}` 里，LLM 需自行坐标换算（正是多模态之外的痛点）。
  3. 坐标双轨（轴向整数 vs 标签字符串 `A1..HH27`）没有统一规范。
  4. 地形通道全空（`land/coast/radar_blocking_hexes` 为空、overlays `geometry_pending`）→ CNN 地形通道需先补地形数据。

---

## 2. 核心原则：一个真相源 + 两种投影

```text
                      SQLite（真相源：GameState 全量 + events）
                                     │
              ┌──────────────────────┴──────────────────────┐
       投影一（LLM/人可读）                        投影二（GPU 训练）
   JSONL 世界态 + cell-aligned ASCII 棋盘        918 格多通道特征张量 .npz
   （显式坐标 + 表头 + 图例）                    （地形/存在/hull/航向/热力 + 动作掩码）
```

- 两种投影都从同一真相源派生，**互不互相转化**（不把 JSONL 再解析成张量，避免二次编码误差）。
- 规则常量（命中公式、射程修正、胜利条件）只在引擎内存在，导出层只抄**盘面字段**、不复制规则公式；`field_of_fire_heatmap` 这类"引擎算好的一层数值"直接下发，AI 侧不重算。

---

## 3. 投影一：JSONL 世界态 + cell-aligned 棋盘（LLM 可读）

### 3.1 JSONL 世界态（一阶段一行 = 一帧盘面）

每帧字段全显式坐标，避免嵌套换算：

```jsonl
{"game":"IBS-S-03","seed":3,"turn":1,"phase":"GUNNERY","sequence":17,
 "ships":[{"id":"IBS-U-KM-HANS-LODY","side":"axis","hex":"F14","q":8,"r":-1,"heading":3,
           "hull":6,"max_hull":6,"vp":4,"guns_usable":4,"guns_total":5,
           "status":["fire:1"],"speed":4,"torpedoes_ready":3},
          {"id":"IBS-U-RN-JERSEY","side":"allies","hex":"J18","q":12,"r":-3,"heading":1,
           "hull":5,"max_hull":5,"vp":3,"guns_usable":3,"guns_total":3,"status":[]}],
 "torpedoes":[{"id":"TT-3","hex":"H15","q":9,"r":-2,"bearing":4,"side":"axis","speed":3}],
 "markers":[],"wrecks":[],"score":{"axis":0,"allies":0}}
```

要点：
- **hex 标签 + 轴向整数双写**（`hex:"F14", q:8, r:-1`）→ 人类看标签、机器/LLM 换算用轴向整数，一次给出。
- `guns_usable` 是引擎算好的"本阶段可用炮门数"（排除 destroyed/fired_this_phase），LLM 不必读炮位数组自己数。
- `status` 只列非默认状态（起火/炮禁用/被迫机动/速度损伤），满血干净舰不列——保持行短、噪声小。
- 鱼雷轨/沉船/标记同构：id + 标签 + 轴向 + 方向 + 归属。

### 3.2 cell-aligned ASCII/整数棋盘（关键推荐）

918 格矩形画成**带表头的字符/整数网格**：

```text
     A  B  C  D  E  F  G  H  I  J  K  L  M  N  O  P  Q  R  S  T  U  V  W  X  Y  Z AA AB AC AD AE AF AG AH
  1  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .
  2  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .
  ...
  5  .  .  .  .  .  .  .  .  .  .  .  A  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .
  6  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  E  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .
  7  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .
  ...
```

图例（紧随棋盘，必须给出，否则 LLM 只能猜符号含义）：

```text
图例: . 海  |  A 轴心舰(1..6 该舰剩余炮门)  |  E 盟军舰  |  t 鱼雷轨(朝向: > v < ^)  |  X 沉船
       ! 残血舰(hull 分数<0.35，加后缀血量)  |  ~ 火情  |  # 不可通行/岸
```

设计依据：
- **cell-aligned**：每格一个 token、按棋盘行列对齐 → LLM 做距离/邻接/拓扑推理时"数格子"即可，不需要多模态视觉；TopoBench 实证该表示比自由文本/字符画提升 30–40pp。
- **表头 + 图例**：任何格用坐标定位（`G14 附近`），可跨帧核对同一格。
- **符号尽量单字符**，避免被 BPE 拆词；舰型/数量等富信息走 JSONL，棋盘只放"位置+少数字段"。

### 3.3 事件语言化

`recent_events` / `combat_history` 作为单帧上下文，把 `message`（中文）与 `payload`（坐标/骰子/修正）+ `rule_id→pdf 页/章节` 一并给 LLM，使其能对具体裁决检索验证（现有 GameEvent 结构已满足，无需改动）。

---

## 4. 投影二：特征张量（GPU CNN/Transformer）

### 4.1 网格基准

34×27=918 格轴向矩形量化（复用 engine.py:708-712 的 `HexCoord(q, row - (q - (q & 1)) // 2)` 扫格逻辑）。张量形状 `H×W×C = 27×34×C`。

### 4.2 通道设计（首版 8–12 通道，全部 `float32`，未知/不存在显式区分）

| # | 通道 | 含义 | 未知值 |
|---|------|------|--------|
| 1 | terrain | 海=0 / 岛=1 / 岸=2（当前全海，预留） | 0 |
| 2 | own_presence | 己方舰存在=1 | 0 |
| 3 | enemy_presence | 敌方舰存在=1 | 0 |
| 4 | hull_frac | hull/max_hull，hidden_damage 下敌=0 | 0（与"不存在"同值，靠 presence 通道区分） |
| 5 | heading_sin | sin(heading·60°) | 0 |
| 6 | heading_cos | cos(heading·60°) | 0 |
| 7 | fire_markers | 火情标记数 | 0 |
| 8 | torpedo_presence | 鱼雷轨存在=1（或分朝向 6 通道） | 0 |
| 9 | wreck | 沉船=1 | 0 |
| 10 | visibility | 该格对本方可见（observe 视角）=1 | 0 |
| 11 | field_of_fire | 射界热力层（复用 `field_of_fire_heatmap` engine.py:683，逐格数值，本方/敌方已由引擎区分） | 0 |

- 舰型 one-hot、装甲、vp、name、`speed_track` 全量等**静态属性不进通道**，走旁路表（见 §5）。
- 敌方 `hull_frac` 在 hidden_damage 下填 0，与"未知"同值，靠 presence + visibility 通道消歧——不泄漏引擎不肯给的信息。
- 数值层（通道 4/5/6/11）跨样本做 min-max 或 log 归一，避免梯度爆炸；同一局内保持一致。

### 4.3 动作空间 + 合法掩码

- 决策目标（监督）在**旁路流**，不进盘面通道：`submitted_orders` / `sealed_orders`（含 plan 字符串）是"策略标签"。
- 动作掩码：舰 ID × 目标 ID 的 0/1 合法掩码（射界/距离/已毁炮位/想定禁射），由引擎 `gunnery_target_options` / `movement_candidates` 一次性导出，喂给 softmax 前的 mask（参考 antiyoy-ai 的 action masking）。
- 移动动作：舰 ID × 目标格（918）稀疏；也可先跑 `movement_candidates` 缩到每舰实际可达集再 index。

### 4.4 存储

- 每局一个 `.npz`：`{tensors: (T,27,34,C), meta: {seed, scenario, options, game_id}, actions: (T, …), masks: (T, …)}`。
- 大批量训练时用 numpy memmap 或按局流式加载，避免一次性载入全部。

---

## 5. 数据切分（张量友好化）

1. **静态/动态切分**：舰型记录（`speed_track` / `speed_damage_track` / `gun_mounts` 全量 / 装甲 / vp / asset / name）抽成旁路表 `ship_id → 静态属性`；逐帧张量只留动态位（destroyed/fired/ammo/hull/speed_damage_crossed/火情/位置）。
2. **意图/簿记单独成流**：玩家与 AI 提交的订单是"策略标签"，独立导出为监督目标，不作张量通道。
3. **事件 schema 化**：异构 `payload: dict[str, Any]` 按 `type` 定 schema（碰撞/命中/进水/火情各一）后再 tensorize 或入表格，供动作级监督。

---

## 6. 文献 / GitHub 推荐清单

### LLM 空间推理（为何 cell-aligned 整数 + 表头 + 图例）
- **GVGAI-LLM**（arXiv:2508.08501）：LLM 纯文本空间推理仍弱（约 10% 胜率），结构化/多分辨率表示是解法方向。
- **TopoBench**：cell-aligned 整数表示使 LLM 拓扑推断准确率 +30–40pp。
- **Megacity 数据卡 spec**：降采样总览 + 细节图 + 图例 + 坐标表头，是"LLM 可读地图"的工业级模板。

### Hex / 棋盘 Transformer
- **ResTNet**（arXiv:2410.05347）：残差 + Transformer 混合，19×19 Hex 胜率 50.4%→58.0%。
- **Pais 硕士论文**：2D hex 位置编码、每 tile token + 全局标量广播。
- **Vasiljević 硕士论文**：六边形国际象棋相对位置嵌入。
- **Haivoronskyi**：GPT 式 transformer 按序生成 Hex 走子。

### Hex 网格 RL/强化学习环境（特征通道 + 动作掩码现成范例）
- **antiyoy-ai**（GitHub）：完整 hex 策略 RL 管线——PettingZoo AEC、28 通道 8×8 特征图、action masking、PPO 自博弈，与铁底湾最贴近的通道设计蓝本。
- **NuZero / RL-SCS**（GitHub）：AlphaZero + DeepThinking 的 hex-and-counter 战棋。
- **minihex / gym-catan**：hex gym 环境（观测平面）。
- **Panopticon**：战棋 RL agent 平台。

### 六边形卷积 + 战争迷雾
- **AlphaSCS**：HexagDLy 六边形卷积核。
- **SMAC / CN114880955**：掩码观测 + DRQN/GRU。
- **Dec-POMDP + GNN 战棋**（arXiv:2009.08922）。

---

## 7. 实施路线（分步、可独立交付）

1. **本批（已完成）**：本设计文档。
2. **下一步**：最小导出模块 `export_worldstate(game_id)` → JSONL 帧 + cell-aligned 棋盘；先服务"把一局塞进 LLM prompt"。
3. **再下一步**：`.npz` 张量导出（复用 `field_of_fire_heatmap` 扫格 + 静态/动态切分）+ 离线批量收集对局（AI 对 AI / 人类对局）→ 训练 CNN/Transformer 基线。

## 8. 与既有治理约束的关系

- 引擎唯一裁决不变：导出层只读 `engine.observe` / `gunnery_target_options` / `movement_candidates` / `field_of_fire_heatmap`，不重算规则、不改状态。
- 规则常量不复制：期望命中/修正/射程表只从引擎结果字段取值，投影二通道 11 直接下发引擎热力层。
- 隐藏损伤不泄漏：敌方 `hull_frac` 通道按 `PublicShip.hull is None` 填 0，可见性通道与 observe 同源。
