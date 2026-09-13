# B0 审计 1/6：目标语义（objective_semantics.md）

审计对象：`research/geometry/committed_game.py::simulate`、
`research/experiments/e02_crossing_t_phase.py`、
`research/experiments/e06_engine_validation.py`。

## 逐项结论（v4 计划 B0 必查 1-3）

### 1. payoff 是否逐时刻累积？
**是（带折扣）**。`simulate` 每步 `cum += disc * L`，折扣 γ=0.96（策略层 0.9）。
40 步承诺方案的 rollout 是真正的路径积分目标，**非 endpoint-only**。
e02 扫描、e06 验证、e07 历史对照全部经由同一 `simulate`/`open_loop_minimax`
管线 → 语义一致。

### 2. 是否存在 endpoint-only / terminal-only 评分？
**无**。未发现任何只取 `L(s_T)` 或单点快照的评分路径。
（Φ(s_T) 终端项：不存在，λ=1 纯火力差——v4 §2 允许。）

### 3. TacticalCommander 移动评分是否 endpoint-only？
TacticalCommander（引擎 AI，基线用）的 `_score_hex` 是**单点评分**
（对候选终点打分），不做路径积分。影响：E06/E07 中作为对手/基线的
doctrine AI 是 snapshot 评分者。这不是研究层缺陷（AI 是被比较的基线），
但必须在论文中声明：**基线 AI 为 snapshot 评分者，几何策略为路径积分
评分者**——两者的比较因此同时检验"路径积分目标是否产生更好行为"
（这正是 v4 B2 的问题）。

### 审计中发现的偏差（需修复或声明）
- **开火-机动时序偏移**：`simulate` 在每步先以当前几何开火、后执行该步
  机动；而引擎顺序是 MOVEMENT_RESOLUTION → GUNNERY（先机动后炮击）。
  即代理的 L(t) 比引擎语义滞后一个回合。影响：几何一阶正确、时序差一拍；
  对斜对称结构无影响（两侧同序）。**处置：B2 中同时实现 fire-after-move
  版本并对照**（B2 实验的一部分）。

## B0 Gate 判定
目标语义总体清楚：主模型已是路径积分。**PASS**，允许进入 B1/B2。
