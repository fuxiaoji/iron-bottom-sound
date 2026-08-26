# 铁底湾 RL 强化学习方案参考文档（战局张量表示 + 奖励 + CNN/Transformer + GPU）

> 目标：把《铁底湾的回响 IV》的引擎裁决做成一个**通用**的 RL 环境——战局状态表示为
> `地图宽 × 地图高 × 历史帧 × 格子通道` 的张量，奖励采用「我方遭受火力热度 / 敌方遭受我方
> 火力热度」+ 引擎真值（VP/胜负/损伤），CNN 与 Transformer 双架构路线，PyTorch + GPU 训练。
> 本文档为可行性调研与引用清单，所有外部引用附链接，落地实现作为独立后续工作。
>
> 约束纪律（沿袭仓库治理）：**引擎唯一裁决**——RL 环境对引擎只读（`observe`/`legal_actions`/
> `field_of_fire_heatmap`/`export_frame`），奖励与状态全部从引擎可见集派生；规则常量绝不复制
> 到引擎外；迷雾一致（Agent 只见自己观察）；张量/奖励层任何异常不影响对局。

---

## 0. 现有资产（RL 可直接复用的接口）

| 资产 | 位置 | 对 RL 的用处 |
|---|---|---|
| `engine.observe(game_id, side)` | `engine.py` | 每侧迷雾一致的观察：ships/torpedo_tracks/markers/score/turn/phase/visibility |
| `engine.field_of_fire_heatmap(viewer, side...)` | `engine.py:695`、`_ship_fire_heat` `:613` | **每格火力热度**（`hexes:{label:heat}`、`max_heat`、`ships`），按观察者分侧——正是奖励/状态的热度来源 |
| `engine.legal_actions` | `engine.py` | 合法动作掩码（legal masking） |
| `state_export.export_frame` | `state_export.py:73` | JSONL 帧：舰船（hex/q/r/heading/speed/hull/guns/torpedoes/vp/status）+ 鱼雷 + 标记 + 沉船 + 比分——张量通道的逐字段来源 |
| `GameState.options/scenario` | `models.py` | 想定元数据（map 尺寸、turns、可选规则）→ 通用化标量 |
| `bench.py` 多进程对局框架 | `bench.py` | `ProcessPoolExecutor` 并行 rollouts 骨架（实测 50 局 11.6s / 8 进程） |
| `TacticalCommander`/`DeterministicCommander` | `tactical.py`/`llm.py` | 行为克隆（模仿学习预热）的示范数据生成器 |
| 地图几何 | `frontend/hexGeometry` 与 `state_export.render_board` | flat-top odd-q 轴向坐标 → 张量行列映射（34 列 × 27 行） |

引擎热度的确切公式（`_ship_fire_heat`）：某格热 = Σ(该炮 `firepower × expected_hits`)，即「该格如果站一艘舰会被多少火力打中」——**不是**实际伤害。这是很好的**软先验/状态特征**，但真值奖励必须以引擎裁决的 damage/VP/胜负为准（见 §3）。

---

## 1. 战局张量表示（通用设计）

### 1.1 规范网格与想定无关化

- 主图：flat-top odd-q 六角格，34 列（A..HH）× 27 行。RL 张量用**统一的规范网格**（如 `H=32 × W=36` 或直接 `34×27`），任意想定按轴向坐标 `(q, r)` 填入；格子超出想定地图 → 通道为 0。
- 地图更大/更小想定的通用化：三选一
  1. **固定上限 + 补零**（简单）：最大网格裁剪/填充，跨想定共享同一网络（AlphaViT 证明了单一模型可变棋盘尺寸）。
  2. **下采样到规范网格**（广谱）：多想定统一 `H×W`。
  3. **Ship-token 路径免地图对齐**（推荐做基线对比，见 §4）：舰船本就按坐标入格，格子只做空间归纳，token 序列长度由舰数决定——天然支持不同舰队规模。
- 标量（turn/max_turns/phase-onehot/visibility/比分/想定 id 嵌入）拼入全局面（CNN 尾接）或作为全局 token（Transformer）。

### 1.2 格子通道（每帧 ~24 层，按 `export_frame` 与 `field_of_fire_heatmap` 派生）

| # | 通道 | 来源 | 说明 |
|---|---|---|---|
| 1 | 海 / 2 岸 / 3 岛 | `state`（`observe` 派生） | 地形 |
| 4 | 我方舰占位（我方格=1） | `observe.ships` | 敌我由 `ship.side` 分 |
| 5 | 敌方舰占位（可见） | `observe.ships` | **迷雾：只填"可见"，不填敌方 hull 数值** |
| 6 | 敌方舰 hull%（公开） | `observe.ships.hull/max_hull` | 隐藏损伤下敌方为 None → 0 |
| 7 | 航向 one-hot（4 或 8 个桶） | `observe.ships.heading` | 舰格值 = 桶号 |
| 8 | 航速归一化 | `current_speed/max_speed` | |
| 9 | 起火标记 | `fire_markers` | |
| 10 | 可用炮数归一化 | `export_frame` 的 `guns_usable` | 隐藏损伤对敌方为 None→0 |
| 11 | 鱼雷就绪数 | `torpedoes_ready` | |
| 12 | VP（我方） | `observe.score` | 每格同值广播 |
| 13-16 | 鱼雷轨：存在/航向/余程/齐射数 | `observe.torpedo_tracks` | 沿轨各格 |
| 17-20 | 标记：烟/照明/探照灯/接触 | `observe.markers` | 各一格 |
| 21 | 我方对敌火力热度 | `field_of_fire_heatmap`（viewer=我方，看敌方一侧的 `hexes`） | **奖励/软先验** |
| 22 | 敌对我方火力热度 | 同上，看我方一侧 | |
| 23 | 上次伤害（本格收到的 damage） | `observe.recent_events` 公开 payload | 真值事件 |
| 24 | 沉船/残骸 | `export_frame` 的 `wrecks` | |

> 舰船特征向量（可选，AlphaStar 风格）：在舰占位格上附一个 `entity_vector`（如 32 维：舰型 id、hull、guns、torpedoes、heading、speed、vp、状态…），供 Transformer 的 ship-token 使用——**不同想定的不同舰型/数量都成立**（参考 §4.2）。

### 1.3 历史堆叠（`地图×历史×格子信息`）

- **CNN 路线**：把最近 `K` 帧沿通道维堆叠（K=4/8/16），形如 AlphaGo Zero / AlphaZero 的 `N×N×(历史×特征)` 输入。帧间距离 = 一个阶段或一个回合。参考 [AlphaZero（Silver et al. 2018）](https://www.science.org/doi/10.1126/science.aar6404)、[OpenAI Five 的最近 5 帧堆叠（Berner et al. 2019）](https://arxiv.org/abs/1912.06680)。
- **Transformer 路线**：不做通道堆叠，而让注意力跨时间——[Chess Transformer（cross-temporal attention over 8 successive board states）](https://huggingface.co/Angelotxx271/chess-transformer) 直接把「演变历史」交给注意力，效果明确。这一设计对"隐蔽目标从视野消失后再次出现"（迷雾记忆）尤其关键。
- **迷雾（部分可观测）**：这不是 MDP 而是 POMDP。AlphaStar 用 **RNN 隐状态**消化历史与迷雾（[Vinyals et al. 2019](https://arxiv.org/abs/1902.01724)；[中文解读](https://raw.githubusercontent.com/datawhalechina/easy-rl/master/docs/chapter13/chapter13.md)）；Transformer 路线用 cross-temporal 注意力替代 RNN 的隐状态。训练采用 **CTDE（集中训练、分散执行）** 或对每侧独立训练一个 POMDP 策略（每侧只看自己观察，天然满足"AI 只见自己观察"纪律）。

---

## 2. 为什么热度图是好特征/奖励（但真值在引擎）

- `field_of_fire_heatmap` 已按观察者返回每格热度，且迷雾一致（隐藏损伤不泄漏）。它同时天然编码了**射界、距离、炮线遮挡**——这是 CNN 很难从原始棋面自己快速学到的高层战术先验。
- **但热度是"概率性射界"，不是命中**：引擎实际伤害在 `events`（带 `hidden_damage` 过滤）与 `score` 里。正确分工：
  - **状态特征**：热度图（第 21/22 通道）+ 事件伤害。
  - **奖励**：以引擎真值（VP/胜负/公开 damage）为主，热度只做**势函数塑形**（见 §3），保证最优策略不被塑形改变。

---

## 3. 奖励设计（用户核心诉求：火力热度）

### 3.1 稀疏真值奖励（必须，引擎唯一裁决）

```
R_终局 = 胜负大项（+1/-1/0）+ VP 差（axis.score - allies.score，或归一化）
r_t    = (score_t - score_{t-1})          # 回合 VP 增量，引擎真值
       + 击沉/命中事件奖励（从公开 events 的 damage payload 累计，区分敌我）
```

### 3.2 密集塑形奖励（用火力热度做势能，保证策略不变）

采用 **Ng, Harada & Russell 1999 势函数塑形**（policy-invariance 保证，是最安全的热度用法）：

```
r'_t = r_t + γ·Φ(s_{t+1}) − Φ(s_t)          # Φ = 势能函数
Φ(s) = α·(敌方格子所受我方火力热度之和) − β·(我方格子所受敌方火力热度之和)
```

- 参考：[Ng et al. 1999, "Policy invariance under reward transformations: Theory and application to reward shaping"](https://www.sciencedirect.com/science/article/pii/S0004370299000592)（即 `γΦ(s')−Φ(s)` 形式）；[Wiewiora 2003 证明势函数塑形等价于 Q 值初始化](https://mlanthology.org/jair/2003/wiewiora2003jair-potentialbased/)。
- 系数 `α/β` 建议先小（0.1 量级）再调；热度直接取 §0 引擎接口，零额外实现。
- 若担心势函数不平滑，可把「对敌 heat − 受敌 heat」做成**逐阶段差分**（同一潜在语义、更稳）。
- 可选进阶：用学习到的奖励预测器做势函数（[arXiv 2208.12525](https://ar5iv.labs.arxiv.org/html/2208.12525#10)）。

### 3.3 奖励实现纪律

- 只在**回合末/终局**给奖励（阶段内热度的变化噪声大），或至少给稀疏奖励 + 每阶段差分塑形。
- 热度奖励只在「引擎真值」缺失/延迟时当软先验；**绝不与引擎裁决冲突**——引擎说没命中就没命中。
- 避免奖励黑客：不把"热度"当"伤害"算，否则 Agent 会去刷射界而不是赢。

---

## 4. 架构：CNN vs Transformer

### 4.1 CNN 路线（基线，成熟、快）

- **AlphaZero 风格残差 CNN**：输入 `34×27×K×24` 张量 → 若干残差块（3×3 卷积、无池化——池化破坏格坐标，[Hex 研究明确不用池化](https://www.semanticscholar.org/paper/Reinforcement-Learning-for-Creating-Evaluation-in-Takada-Iizuka/10750342293aa0804365a4a0618e07581b3912d5)）→ policy head（合法动作掩码 softmax）+ value head（scalar）。
- 六角格直接用 3×3 方阵卷积近似（邻域近似），或实现六角卷积核。
- 直接先例：
  - [NeuroHex（Young et al. 2016）](https://ar5iv.labs.arxiv.org/html/1604.07097)：6 通道 CNN DQN，监督 mentor 预热解决稀疏奖励。
  - [HexHex（AlphaGo Zero 六角格移植）](https://github.com/harbecke/HexHex)：18 层×64 通道残差 CNN，**无 MCTS** 也训出强 agent。
  - [muzero-general（PyTorch 多 GPU 自博弈）](https://gitcode.com/gh_mirrors/mu/muzero-general)：残差网络 + Ray 异步 self-play，现成脚手架。
  - [NuZero（AlphaZero + DeepThinking，SCS 兵棋，六角格）](https://github.com/guilherme439/NuZero)：**最贴近本项目**——兵棋（Standard Combat Series）、六角格、PyTorch + Ray 自博弈、已实现六角/正交网格网络。
  - [Zerov3（generals.io，37 通道 24×24 棋盘张量 + PPO 自博弈）](https://openi.pcl.ac.cn/john9081/Zerov3)：行为克隆预热 → PPO 自博弈的完整管线范本。

### 4.2 Transformer 路线（推荐做对比）

三种 token 化：
1. **格 token（cell-as-token）**：`34×27=918` token 偏大，可采样/降采样。先例：[AlphaViT（AlphaZero+ViT，可变棋盘尺寸单一模型）](https://ar5iv.labs.arxiv.org/html/2408.13871)、[Robot Master（格 token + Chessformer 2D 注意力偏置 + 逐格 policy head）](https://github.com/valeratrades/robot_master)。
2. **舰船 token（ship-centric，推荐）**：每艘可见舰 = 1 token（entity_vector + 位置嵌入）。舰数少（本作 ~10-14/侧），token 少、注意力做**长程交互**（炮击 20+ 格、鱼雷轨、跨图支援）比 CNN 高效，且**跨想定变长天然支持**。参考 AlphaStar 的 entity transformer（[Vinyals et al. 2019](https://arxiv.org/abs/1902.01724)）。
3. **历史 token**：全局 token 带 turn/phase/score，另加 cross-temporal 注意力窗口（[Chess Transformer](https://huggingface.co/Angelotxx271/chess-transformer)）。

### 4.3 混合与搜索

- **混合**：CNN trunk 提空间特征 → 舰船 token Transformer（AlphaStar 主架构就是这条路）。
- **搜索增强**：`AlphaZero/Gumbel MCTS`（可 GPU 批量，[Robot Master](https://github.com/valeratrades/robot_master) 用 Gumbel MCTS），或 **MuZero 学模型**避免写规则——但本作规则已引擎化，MuZero 收益主要在同构迁移，[参考](https://deepmind.google/blog/muzero-mastering-go-chess-shogi-and-atari-without-rules/)。

### 4.4 动作空间（最容易卡死的点）

`OrderBatch` 是复杂结构化 JSON（movement plan 串、gunnery assignment、torpedo 设置、增援、烟雾/照明…）。方案（由易到难）：

1. **行为克隆预热**：用 `TacticalCommander`/`DeterministicCommander`/bench 生成海量 `(张量, OrderBatch)` 数据 → 监督预训练（AlphaStar 用 20-50 万局人类回放初始化，[参考](https://raw.githubusercontent.com/datawhalechina/easy-rl/master/docs/chapter13/chapter13.md)；Zerov3 同样 BC→PPO）。
2. **Autoregressive 动作解码**：策略头逐 token 输出 OrderBatch 的 JSON 结构（复用 LLM commander 已验证的 prompt 纪律/合法顺序），用 `engine.legal_actions` 做掩码，非法即拒绝/重采样——**引擎唯一裁决保证合法**。
3. **分层**：先选"战术意图"（如：进抵射程/侧翼/保命）→ 再细化订单；或直接学"目标格+意图"，plan 串交给现有确定性规划器补全（类似 movement_candidates 已附精确 plan 的做法）。

---

## 5. GPU 加速与训练基础设施

**瓶颈不是网络，是环境**：引擎是纯 Python + SQLite，单局约 0.96s 串行、8 进程并行约 0.23s/局（bench 实测）。RL 需要数十万到百万步，必须先解决吞吐。

| 路径 | 方案 | 吞吐 | 工作量 |
|---|---|---|---|
| A（推荐先做） | 保留引擎，**多进程并行 rollouts**（bench 的 `ProcessPoolExecutor` 骨架直接改造成 vectorized env），obs 在进程内组装成 GPU 张量，网络在 GPU 前向/反向 | 数百步/s | 小 |
| B（高吞吐） | 把裁决核心**张量化到 PyTorch**（GPU 批环境仿真，同 VMAS/IsaacGym 思路） | 数十万步/s | 大，需重写裁决 |
| C（中间） | 引擎换成 C++/Rust 扩展或 uvloop/线程池 + 无锁观察 | 数千步/s | 中 |

训练框架（现成、GPU 优先）：

- **[SampleFactory](https://github.com/alex-petrenko/sample-factory)**：PPO/APPO、self-play、PBT，专为高吞吐与 GPU 环境设计（`--device gpu`、`--env_gpu_observations`），[官方 PettingZoo 多智能体示例](https://github.com/facebookresearch/sol/blob/main/sf_examples/train_pettingzoo_env.py)。
- **[TorchRL](https://pytorch.org/rl/)**：PyTorch 原生、MARL 一等公民（PettingZoo 包装、VMAS GPU 向量环境、集中/分散 critic），[多智能体竞争教程](https://pytorch.org/rl/0.5/tutorials/multiagent_competitive_ddpg.html)。
- **[PettingZoo](https://pettingzoo.farama.org/)**：MARL 环境标准（本作做成 `ParallelEnv` 两智能体零和），[Parallel API 提吞吐的实践建议](https://thelinuxcode.com/pettingzoo-for-multi-agent-reinforcement-learning-marl-a-practical-reproducible-playbook/)。
- **[muzero-general](https://gitcode.com/gh_mirrors/mu/muzero-general)** / **[NuZero](https://github.com/guilherme439/NuZero)**：自博弈 + 多 GPU + Ray 异步，兵棋/棋盘现成样板。
- 轻量起步：**[CleanRL](https://github.com/vwxyzjn/cleanrl)**（单文件 PPO，易读易改）。

**硬件**：本机 Python 3.13、无 GPU；训练需单独 GPU 机器（单卡 3090/A100 起）。现有 bench 的种子确定性设计可直接迁移到训练复现。

---

## 6. 推荐落地路线（基线 → 泛化）

1. **V1 环境**：把 `engine.observe`/`field_of_fire_heatmap`/`export_frame` 包成 PettingZoo `ParallelEnv`（axis/allies 两 agent，回合制同步阶段），奖励按 §3 实现，输出 `34×27×K×24` 张量。跑通 **CNN + PPO** 基线，先固定想定 IBS-S-03（4 回合）验证学习曲线。
2. **V2 预热**：用 `TacticalCommander`/bench 生成 `(张量, OrderBatch)` 监督预训练（行为克隆），再 PPO 微调——稀疏奖励下必做。
3. **V3 架构对比**：Ship-token Transformer（含 cross-temporal 历史）对 CNN；MCTS 增强（Gumbel MCTS）可选。
4. **V4 通用化**：多想定联合训练（规范网格 + ship-token 变长 + 想定元数据嵌入），验证"不只会一个副本"。
5. 全程保持**引擎唯一裁决**：RL 层只读，动作非法由引擎拒绝并重采样，奖励只认引擎真值。

---

## 7. 参考文献

### 状态表示与历史堆叠
- AlphaZero: Silver et al., *Science* 2018 — `https://www.science.org/doi/10.1126/science.aar6404`
- OpenAI Five 历史帧堆叠: Berner et al. 2019 — `https://arxiv.org/abs/1912.06680`
- AlphaStar（地图/实体张量 + RNN 迷雾 + 自博弈）: Vinyals et al. 2019 — `https://arxiv.org/abs/1902.01724`；中文解读（easy-rl 第13章）— `https://raw.githubusercontent.com/datawhalechina/easy-rl/master/docs/chapter13/chapter13.md`

### 六角格 CNN / 棋类
- NeuroHex（6 通道 CNN DQN + 监督预热）: Young et al. 2016 — `https://ar5iv.labs.arxiv.org/html/1604.07097`
- HexHex（AlphaGo Zero 六角格移植，18 层无 MCTS）: `https://github.com/harbecke/HexHex`
- Hex CNN 评估函数（无池化、3×3+PReLU、128 通道）: Takada et al. — `https://www.semanticscholar.org/paper/Reinforcement-Learning-for-Creating-Evaluation-in-Takada-Iizuka/10750342293aa0804365a4a0618e07581b3912d5`

### Transformer
- AlphaViT（AlphaZero + ViT，可变棋盘尺寸单一模型）: `https://ar5iv.labs.arxiv.org/html/2408.13871`
- Othello-GPT（move-token 自回归 + 世界模型涌现）: `https://www.emergentmind.com/topics/othello-gpt`
- Chess Transformer（75 token 编码 + 跨时间 8 态注意力 + PPO/MCTS）: `https://huggingface.co/Angelotxx271/chess-transformer`
- Robot Master（格 token + Chessformer 2D 偏置 + Gumbel MCTS）: `https://github.com/valeratrades/robot_master`
- Transformer 用于决策的综述: `https://ieeexplore.ieee.org/abstract/document/11292991`

### 兵棋 / 海军战术 RL
- Applying Deep RL to Wargaming Framework (IEEE 2024, 美军 COA) — `https://ieeexplore.ieee.org/abstract/document/10500249`
- Naval Movement Simulation with RL（NPS 2023，DQN/MCTS/AlphaStar，DQN 超人类）— `https://hdsdev.hebis.de/main/ubffm/EdsRecord/edsbas%252Cedsbas.941DFDF4`
- AI-Enabled Wargaming Agent Training（USACE ERDC 2024，DQN > A2C/PPO）— `https://erdc-library.erdc.dren.mil/items/9cec2ba0-cf67-4035-b7e1-e57919f5dee1/full`
- MADDPG 海战场对抗（LSTM+AC+模仿，胜率~90%）— `https://katalog.fid-bbi.de/Record/ai-68-OLC2145563881`
- Littoral 海军战术 RL（DDQN/MAPPO，Aalto）— `https://aaltodoc.aalto.fi/server/api/core/bitstreams/4ec26c9b-1e2e-45b2-9cfc-fb11525bf606/content`
- 海空跨域兵棋 AI 架构（分层多智能体）— `https://www.zhkzyfz.cn/EN/10.3969/j.issn.1673-3819.2024.02.006`
- 兵棋离线到在线 RL（Decider）— `http://cea.ceaj.org/EN/abstract/abstract43353.shtml`
- 兵棋 AI 训练（4Hammer，战锤 40k，headless+序列化优化）— `https://github.com/rl-language/4Hammer`
- NuZero（SCS 兵棋 AlphaZero+DeepThinking，六角格+Ray）— `https://github.com/guilherme439/NuZero`
- Zerov3（generals.io 37 通道张量 + BC→PPO 自博弈）— `https://openi.pcl.ac.cn/john9081/Zerov3`

### 奖励塑形
- Potential-based shaping（最优策略不变性保证）: Ng, Harada & Russell 1999 — `https://www.sciencedirect.com/science/article/pii/S0004370299000592`
- 势函数塑形 ⇔ Q 值初始化: Wiewiora 2003 — `https://mlanthology.org/jair/2003/wiewiora2003jair-potentialbased/`
- 学习奖励预测器塑形: `https://ar5iv.labs.arxiv.org/html/2208.12525`

### 模型基 / 搜索
- MuZero（无规则学模型）: Schrittwieser et al. 2019 — `https://deepmind.google/blog/muzero-mastering-go-chess-shogi-and-atari-without-rules/`；PyTorch 多 GPU 复现 — `https://gitcode.com/gh_mirrors/mu/muzero-general`

### GPU 并行训练框架
- SampleFactory（PPO/APPO/self-play/PBT，GPU env）— `https://github.com/alex-petrenko/sample-factory`
- TorchRL（PyTorch 原生，PettingZoo/VMAS，集中 critic）— `https://pytorch.org/rl/`；多智能体教程 — `https://pytorch.org/rl/0.5/tutorials/multiagent_competitive_ddpg.html`
- PettingZoo（MARL 标准环境 API）— `https://pettingzoo.farama.org/`；SampleFactory 集成示例 — `https://github.com/facebookresearch/sol/blob/main/sf_examples/train_pettingzoo_env.py`
- CleanRL（单文件 PPO 轻量起步）— `https://github.com/vwxyzjn/cleanrl`

---

## 8. 风险与边界（诚实标注）

- **热度 ≠ 伤害**：热度奖励必须配引擎真值，否则 Agent 学"刷射界"。
- **吞吐是硬门槛**：路径 A 只够小规模验证；百万步训练必须路径 B/C（引擎张量化或原生扩展）。
- **动作空间结构化**：OrderBatch 的 JSON 结构是最大工程点；行为克隆预热几乎是必需的。
- **迷雾/非平稳**：双 Agent 自博弈非平稳（对手在变），需 self-play + 对手池（AlphaStar league / PBT）。
- **GPU 依赖**：本机/服务器（阿里云）当前无 GPU；训练机器需另配。
- **通用化**：ship-token + 规范网格 + 想定元数据可跨想定；跨"不同兵棋"则需要统一的格子/舰船本体抽象，本作地图几何可复用，规则抽象不可复用（规则留在引擎）。
