# M2-0：CCF-A 组织智能主线第一阶段验证计划
## Organizational Intelligence Validation for Iron Bottom Sound

**项目**：`fuxiaoji/iron-bottom-sound`  
**阶段目标**：第一阶段选题/可行性验证，而不是完成论文。  
**阶段结束标志**：至少一条主线达到 `MAINLINE_READY`，并形成一份冻结的 `POSITIVE_RESULT_BLUEPRINT.md`，明确“什么结果才算论文级正结果、算法应该怎么做、标准 benchmark 怎么补、主图是什么、最危险 reviewer attack 是什么”。若没有任何方向达到该标准，则输出 `RESET_REQUIRED`，不得为了保住方向降低门槛。  
**角色分工**：
- **PI / 科研总负责人（ChatGPT）**：研究问题、创新点、formal object、hard gate、正结果设计、最终主线选择；
- **本地 AI**：代码审计、实验实现、数据生成、统计、bug 记录、可复现打包；不得自行“优化创新点”或改变论文问题；
- **用户**：提供本地计算资源、把 checkpoint 打包交回 PI。

---

# 0. 研究重置后的核心判断

前一轮 hidden-commitment / torpedo 主线已经完成系统性 cheap-kill。下一轮不再围绕鱼雷、sealed commitment、PSRO 继续修补，而从整个平台重新寻找 **Multi-Agent Organization / Hierarchical Control** 问题。

当前平台真正有价值的结构是：

## 经典/普通模式
- `realistic_command=False`；
- AI 在移动层仍是逐舰控制；
- `TacticalCommander` 对各舰生成普通 `MovementOrder`；
- `w_formation`、`line_ahead` 只是评分偏好，不把多舰真正压缩为一个决策实体；
- 炮击/鱼雷也按舰/发射器提交订单。

## 真实模式
- `realistic_command=True`；
- 先进入 `formation_setup`；
- 每方形成若干编队，指定：
  - leader；
  - flagship；
  - reserve flagship；
  - succession order；
  - spacing；
  - heading；
- 移动只提交编队层 `FormationMovementOrder`，再由 `expand_movement_orders()` 展开为普通逐舰移动订单；
- 编队存在共同航速；
- 损伤导致速度不兼容时必须降速或永久脱队；
- 脱队舰进入自主撤退；
- flagship 丧失指挥能力会触发继承；
- 下一回合 command disruption；
- 无合法继承者时 formation dissolution；
- 炮击/鱼雷仍然主要保持逐舰/逐发射器粒度。

**重要审计点**：规则文档仍写“每方 1–4 个编队”，当前代码 `MAX_FORMATIONS_PER_SIDE=8`。M2-0 不修改生产规则；先把不一致写入审计。正式真实模式实验优先只使用 1–4 编队，避免研究结论依赖该未统一边界。

当前支持真实模式的正式想定：
- `IBS-S-01`
- `IBS-S-03`
- `IBS-S-EM-01`

其中 `IBS-S-EM-01` 当前项目版本为双方各 12 艘、共 24 艘，12 回合，是组织结构实验的首要压力测试场景。

---

# 1. 本阶段候选研究主线

## Track A — Dynamic Decision-Entity Abstraction（优先级最高）
### 暂定题目
**Learning Dynamic Decision-Entity Abstractions for Hierarchical Multi-Agent Control**

### 核心问题
在多智能体系统中，是否所有 agent 每一步都必须独立地产生动作？

给定当前存活 agent 集合：

\[
\mathcal N_t=\{1,\ldots,N_t\}
\]

学习一个随状态变化的 partition：

\[
\Pi_t=\{G_1,\ldots,G_{K_t}\}
\]

使每个 group 只产生一个 macro decision，再由合法 executor 展开为各 agent 的动作。

核心不是 role label，不是 communication group，而是：

\[
\boxed{\text{直接改变 action-producing decision entities 的数量}}
\]

定义研究对象：

\[
L(s,\Pi)=V_{\text{flat}}(s)-V_{\Pi}(s)
\]

称为 **team-abstraction loss / decision-entity abstraction regret**。

目标：

\[
\min_\Pi |\Pi|
\quad
\text{s.t.}\quad
L(s,\Pi)\le \epsilon
\]

直观解释：

> 尽可能把多个 agent 当成一个决策实体，但不能因为压缩控制粒度而显著损失价值。

### 与现有 MARL 方向必须区别
不是：
- role discovery；
- partner selection；
- communication graph；
- task decomposition；
- “同组 agent 仍各自产生 action”。

我们需要验证的是：

> **一个 group 是否真的只产生一个 macro decision，从而减少 policy factorization / action dimensions。**

---

## Track B — Failure-Aware Command Organization
### 暂定题目
**Failure-Aware Organizational Design for Hierarchical Multi-Agent Systems**

### 注意：本阶段不叫 Dynamic Reconfiguration
当前真实模式规则只允许开局设置 formation / flagship / reserve / succession，发生 flagship transfer 后按固定继承规则执行，不能任意在战斗中重新组建编队。

因此第一阶段只研究**合法的组织设计**：

> 开战前怎样安排编队、flagship、reserve 和 succession，使团队在战斗中遭遇“内生关键节点失效”时仍保持战斗能力？

这里的 failure 与普通随机 agent dropout 不同：

- 对手会主动攻击；
- 失败概率取决于位置、威胁、单位价值与对手策略；
- flagship loss 不仅删除一个 unit，还改变 command state；
- 会造成下一回合 command disruption；
- 极端情况下导致 formation dissolution。

核心问题：

\[
G_0 \rightarrow \text{battle} \rightarrow failure \rightarrow V
\]

学习/优化 initial command organization \(G_0\)。

---

## Track C — Phase-Adaptive Control Granularity
### 暂定题目
**Phase-Adaptive Granularity for Multi-Agent Control**

平台天然存在：
- movement：真实模式是 formation-level；
- gunnery：ship-level；
- torpedo：ship/launcher-level。

研究问题：

> 不同阶段、不同状态是否需要不同控制粒度？

例如：

```text
远距离航渡：3 个编队级 decision entities 足够
↓
接敌运动：5 个 groups
↓
近距交战：10–12 个 individual entities
↓
脱离：再次合并
```

本阶段把它当作独立猜想验证，但默认更可能成为 Track A 的模块，而非单独论文。

---

## Track D — Rule-Constrained Macro Executor
这不是论文主线，是 A/C 的必要基础设施。

目标：

\[
(\Pi, u_1,\ldots,u_K)
\rightarrow
\text{legal per-ship orders}
\]

必须保证：
- 不改生产引擎语义；
- 只通过正式 validator/submit boundary；
- deterministic；
- replayable；
- singleton group 与经典逐舰动作兼容；
- group macro action 失败时返回 invalid，不偷偷修复成另一个动作。

Track D 只判 `INFRA_PASS/FAIL`，不参与最终主线排名。

---

# 2. 为什么这几条有 CCF-A 价值，但也有严重碰撞风险

必须横向比较的近期工作至少包括：

1. **GRDC — AAAI 2026**  
   动态 interaction graph + role discovery + intra-role communication。
2. **Autonomous Partner Selection (APS) — AAAI 2026**  
   agent 动态选择合作伙伴/隐式 grouping。
3. **CD3T — AAAI 2026**  
   dynamic task decomposition / hierarchical MARL。
4. **DECOR — IJCAI 2026**  
   动态组合 behavioral traits 形成 roles。
5. **VO-MASD — IJCAI 2025**  
   dynamic subgroup discovery + multi-agent temporal skills。
6. **Empirical Study on Robustness and Resilience in Cooperative MARL — NeurIPS 2025**  
   82k+ experiments，研究不同 uncertainty / agent scope 下的 robustness/resilience。
7. 经典基线方向：
   - MAPPO
   - QMIX
   - HAPPO
   - hierarchical MARL / skills / macro-actions
   - coordination graphs

### Track A 的 novelty 必须最终回答
有没有已发表工作已经同时做到：

```text
state-dependent partition
+
one macro action per group
+
fewer action-producing decision entities
+
performance/complexity Pareto
+
dynamic split/merge
```

如果有高度同构工作，Track A 立即降级。

### Track B 的 novelty 必须最终回答
已有 robust MARL 通常模拟 observation/action noise、agent perturbation、agent failure。

我们的潜在差异必须是：

```text
failure is endogenous/adversarial
+
failure changes organizational command structure
+
command-node failure creates temporal control constraints
+
organization can be designed before battle
```

如果最终只是“agent dropout robustness”，Track B 失败。

---

# 3. M2-0 最终成功标准

本阶段结束只允许三类总结果：

## `MAINLINE_READY`
至少一条方向同时满足：
1. **Problem existence**：真实 IBS + exact lab 中都有明确非平凡信号；
2. **Effect size**：不是只比弱 baseline；
3. **Learnability / algorithmic leverage**：存在能学习/利用 oracle signal 的可观测结构；
4. **Generality**：不是只在一个想定成立；
5. **Novelty**：closest-prior matrix 没发现致命同构；
6. **Positive-result blueprint**：已经知道完整论文应该怎样产生正结果。

## `SIGNAL_ONLY`
现象存在，但：
- 方法不可学；
- 或泛化不够；
- 或 novelty 危险；
- 或只能当模块。

不得进入大规模训练。

## `RESET_REQUIRED`
所有主线失败，停止 Organizational Intelligence 这一轮选题。

---

# 4. 阶段总流程

```text
P0 Repo / Mode Audit
        ↓
P1 Shared Data + Exact Team Lab
        ↓
D0 Rule-Constrained Macro Executor
        ↓
A0/A1 Dynamic Team Abstraction Oracle
        ↓
A2 Merge-Safety Learnability
        ↓
B0 Natural Command-Failure Census
        ↓
B1 Hierarchy Sensitivity
        ↓
B2 Robust Organization Oracle
        ↓
C0 Phase-Granularity Census
        ↓
Novelty Gate
        ↓
Confirmatory Freeze
        ↓
Direction Scorecard
        ↓
POSITIVE_RESULT_BLUEPRINT
        ↓
PI 决定唯一主线
```

不得直接跳到 MAPPO / GNN / Transformer。

---

# 5. P0 — 仓库与模式语义审计

## P0.1 Git 安全

执行：

```bash
git status --short
git branch --show-current
git rev-parse HEAD
```

禁止：

```bash
git reset --hard
git clean -fd
```

建议新 branch/worktree：

```text
research/m2-0-organizational-intelligence
```

所有研究代码：

```text
research/m2_0/
```

生产模块原则上不改。

---

## P0.2 必须形成 `MODE_SEMANTICS_AUDIT.md`

逐项从当前 HEAD 核实：

### Classic
- movement action object；
- TacticalCommander 如何逐舰决策；
- legal action boundary；
- hidden info boundary；
- gunnery / torpedo granularity；
- profile 列表；
- scenario support。

### Realistic
- formation setup；
- leader / flagship / reserve；
- formation movement；
- shared speed；
- detach；
- autonomous withdrawal；
- command succession；
- command disruption；
- dissolution；
- gunnery / torpedo 粒度；
- enemy observation 是否隐藏 formation hierarchy。

### 必须明确写：
> 当前系统是 centralized side-level commander，不可直接宣称“每艘舰是一个 decentralized MARL agent”。

后续如果论文进入 MARL，需要研究 wrapper 明确定义：
- local observation \(o_i\)；
- group observation \(o_G\)；
- CTDE critic 可见 global state；
- execution policy 可见什么。

---

## P0.3 文档/代码不一致

记录：

```text
docs: formations <= 4
code: MAX_FORMATIONS_PER_SIDE = 8
```

M2-0：
- 不自动修改；
- 正式 realistic experiment 只使用 <=4 formations；
- research classic wrapper 不受该真实模式编队规则约束。

---

## P0.4 Baseline throughput

每个场景各做少量 pilot：

```text
classic TacticalCommander
realistic RealisticCommander
```

记录：
- sec/game；
- failure rate；
- turns；
- events；
- command succession count；
- detach count；
- dissolution count。

如果真实模式大量非法/无法终局，先停实验。

---

# 6. P1 — Shared IBS Snapshot Dataset

## 6.1 数据全部来自 simulator

禁止人工伪造主分析状态。

场景：

```text
IBS-S-01
IBS-S-03
IBS-S-EM-01
```

策略池首轮：

```text
balanced
fleet
line
brawl
cautious
```

鱼雷 doctrine 不是本轮研究重点，不需要为了多样性引入全部 adaptive specialists。

---

## 6.2 Discovery 数据生成

先做 pilot time estimate，再确定总量。

目标大致：

### Classic
每个 scenario：
- 30–50 completed matches；
- 覆盖不同 profile pair + side swap；
- 保存每个 movement planning snapshot。

### Realistic
每个 scenario：
- 50–100 completed matches；
- 重点 EM-01；
- 保存：
  - movement planning；
  - pre-gunnery；
  - post-damage；
  - command-transfer events；
  - detach events；
  - dissolution events。

不要一次硬跑满。

先：

```text
5 matches / scenario / mode
```

估计时间与事件率，再扩。

---

## 6.3 Snapshot 记录字段

至少：

```text
snapshot_id
scenario
seed
mode
axis_profile
allies_profile
side
turn
phase

public_observation
research_full_state_ref

alive_ships
ship_positions
headings
speeds
damage
fire
visible_enemy_summary

formation_membership
leader
flagship
reserve_flagship
succession_order
formation_status
command_status
disruption_turn

legal_action_summary
event_prefix_hash
replay_locator
```

研究 private/full-state 字段必须和可用于在线算法的 public fields 分开。

---

## 6.4 Train/discovery/confirmatory 拆分

一开始就预留：

```text
discovery seeds
confirmatory seeds
```

Confirmatory seeds 不得在 discovery 中查看主指标。

建议按 seed 哈希固定 70/30。

---

# 7. P1b — Exact Team-Abstraction Lab

目录：

```text
research/m2_0/exact_team_lab/
```

目的不是当论文主实验，而是验证 formal object 和代码正确性。

## 7.1 最小环境

- cooperative team；
- 3–6 heterogeneous agents；
- 2–4 actions/agent；
- horizon 2–5；
- state-dependent local task；
- speed/capability heterogeneity；
- optional agent damage/failure；
- exact enumeration。

必须可以 exact 计算：

\[
V^*_{\text{flat}}(s)
\]

以及给 partition \(\Pi\)：

\[
V^*_{\Pi}(s)
\]

和：

\[
L^*(s,\Pi)=V^*_{\text{flat}}(s)-V^*_{\Pi}(s)
\]

---

## 7.2 必须有四类单元案例

### Case 1 — Grouping lossless
两个 agent 永远应执行同一宏动作。

### Case 2 — Grouping harmful
两个 agent 当前需要不同动作。

### Case 3 — State-dependent split
前一状态可合并，后一状态因 damage / task divergence 必须拆。

### Case 4 — Failure-sensitive organization
不同 leader / command organization 在失败后 continuation 不同。

两种 exact 实现交叉核验或 exhaustive enumeration + independent DP。

---

# 8. D0 — ResearchGroupExecutor

这是 Track A/C 的基础。

## 8.1 不能直接拿“真实模式 vs 普通模式”当因果实验

原因：

真实模式不仅改变控制粒度，还新增：
- shared speed；
- permanent detach；
- command disruption；
- withdrawal；
- formation constraints。

因此：

```text
classic flat
vs
realistic formations
```

不是纯净的 team-abstraction 对照。

---

## 8.2 正确做法

在 **classic engine semantics** 上写研究 wrapper：

```text
ResearchGroupExecutor
```

输入：

```text
state
side
partition Pi
macro action per group
```

输出：

```text
ordinary per-ship MovementOrder
```

最终必须通过：

```text
engine.validate_orders
```

或正式 submit validation。

生产 engine 不改。

---

## 8.3 Partition 支持

允许 singleton：

```text
{ship1}
```

也允许 multi-ship：

```text
{ship1,ship2,ship3}
```

Group 只产生 **一个 macro decision**。

第一版 macro movement vocabulary 不求强：

```text
HOLD
STRAIGHT_SLOW
STRAIGHT_FAST
TURN_PORT_60
TURN_STARBOARD_60
TACTICAL_LEADER_PROPOSAL
```

具体合法速度/路径必须通过 engine preview/validator。

后舰 expansion 可复用“共享航迹”思想，但不能触发真实模式 command disruption/detach 等额外规则。

---

## 8.4 D0 验收

至少：
- singleton partition 与普通逐舰候选语义一致；
- 每个输出都经过正式 validator；
- deterministic；
- same seed repeat identical；
- invalid macro action 明确失败；
- 不 silent repair；
- production module zero semantic changes。

`D0=FAIL` 时 A/C 全停。

---

# 9. Track A — Dynamic Decision-Entity Abstraction

# A0：先回答“最佳 grouping 是否真的随状态变化？”

不要训练网络。

---

## 9.1 Candidate partitions

每个 movement snapshot 生成有限候选：

### P0 Flat
每舰 singleton。

### P1 Fixed
使用该场景默认/当前 formation membership 作为 grouping 模板。

### P2 Type
按 BB/CA/CL/DD 等类型分。

### P3 Speed-compatible
按合法速度区间兼容性聚类。

### P4 Spatial
按距离/航向邻近聚类。

### P5 Damage-aware
从 fixed/type 中把明显受损/速度不兼容舰拆出来。

### P6 Threat-aware
将面对不同局部敌情/方向压力的舰拆组。

### P7 Split/Merge Neighbors
对 fixed partition 做一步：
- split one group；
- merge two nearby compatible groups。

### P8 Random matched-K
与结构化 partition 相同 K 的随机分组，作为重要 control。

不要枚举 N=12 的全部 Bell partitions。

Exact Lab 中才全部枚举。

---

## 9.2 Partition value

第一阶段定义：

\[
V_H^{eval}(s,\Pi)
\]

不是声称真 \(V^*\)。

使用 simulator continuation：

- H = 1 turn 作为主 discovery；
- H = 2 turn 做关键状态复核；
- opponent 用固定 policy mixture；
- paired/common random numbers；
- 相同 rollout budget。

禁止使用 planner heuristic score 当主 value。

建议 utility：

1. terminal winner/value（能到终局时）；
2. VP margin normalized；
3. H-step combat value：

```text
VP swing
+ hull-value swing
+ sunk-value
```

但必须在 `VALUE_DEFINITION.md` 先冻结。

不能看结果后改 utility。

---

## 9.3 公平性

每个 partition：
- 相同 macro candidate budget；
- 相同 rollout reps；
- 相同 opponent profiles；
- 相同 future seeds。

同时报告两个成本：

```text
K = number of decision entities
candidate evaluations
wall-clock
```

---

## 9.4 关键指标

定义：

\[
K(\Pi)=|\Pi|
\]

\[
Saving(\Pi)=1-\frac{K(\Pi)}{N}
\]

近似 abstraction loss：

\[
L_H(s,\Pi)
=
V_H^{eval}(s,\Pi_{flat})
-
V_H^{eval}(s,\Pi)
\]

安全 grouping：

\[
L_H(s,\Pi)\le \epsilon
\]

Discovery 阶段建议：

```text
epsilon = 0.05 normalized value
```

必须在读取主结果前写入 pre-registration。

---

# 10. A1 — Oracle Signal Gate

对每个 snapshot 求候选集合里的：

```text
best partition
minimal-K safe partition
fixed partition
flat partition
```

必须画：

1. Value vs K Pareto；
2. minimal safe K distribution；
3. best partition type by state；
4. damage vs desired K；
5. enemy proximity vs desired K；
6. speed incompatibility vs desired K；
7. scenario-conditioned plots。

---

## 10.1 Track A PASS_TO_LEARNABILITY

至少满足：

### State dependence
≥30% movement snapshots：

```text
minimal-safe partition
```

与固定 formation partition 的 K 或 membership 明显不同。

### Compression
动态 candidate-oracle 在至少两个 scenario 中：

```text
median decision-entity reduction >=30%
```

同时：

```text
value retention >=95%
```

相对 flat evaluated baseline。

### Need for adaptation
固定 grouping 在 ≥20% snapshots：

```text
loss > 0.05
```

而某个动态候选 partition 能恢复其中至少一半。

### Structure beats random
相同 K 下，结构化 partition 明显优于 random matched-K。

如果只有：
- flat 永远最好；
- fixed 永远足够；
- best K 几乎恒定；
- random grouping 和结构 grouping 一样；

则 `A_FAIL_ORACLE`。

---

# 11. A2 — Merge-Safety Learnability

A1 通过后才做。

不要直接上 GNN/MAPPO。

将问题降成：

> 给两个当前 groups，是否可以安全 merge？

标签：

```text
SAFE_MERGE
UNSAFE_MERGE
```

由 A1 simulator oracle 给出。

---

## 11.1 只能使用 online-observable features

允许：

### group internal
- size；
- type composition；
- speed interval overlap；
- damage dispersion；
- heading dispersion；
- spatial diameter；
- formation alignment。

### between groups
- centroid distance；
- heading difference；
- relative speed；
- enemy-pressure difference；
- visible target overlap；
- local threat difference。

### state
- turn；
- phase；
- score margin；
- visible enemy density。

禁止：
- future rollout value；
- oracle partition；
- hidden enemy state；
- future damage；
- label leakage。

---

## 11.2 模型

只做：

1. logistic regression；
2. GBDT / LightGBM / XGBoost 任一；
3. small MLP。

---

## 11.3 泛化

必须：
- random seed holdout；
- scenario holdout；
- profile holdout。

主指标：
- AUROC；
- AUPRC；
- calibration；
- unsafe-merge false negative；
- regret mass in false negatives。

---

## 11.4 A2 PASS

建议：

```text
AUROC >= 0.75 discovery
scenario-holdout AUROC >= 0.65
```

并且最高 regret 的 unsafe merges 不集中在 false negatives。

若所有模型接近随机：

```text
A_SIGNAL_ONLY
```

不要进入 GNN。

---

# 12. Track B — Failure-Aware Command Organization

## B0：Natural command-failure census

真实模式运行。

重点事件：

```text
formation_command_transferred
command disruption
ship_detached
formation dissolved
flagship sunk
flagship captain killed
leader unavailable
```

---

## 12.1 数据

优先：

```text
IBS-S-EM-01
```

同时保留 S-01/S-03。

先 50 matches/scenario pilot。

若事件不足：
- 最多扩到 500 realistic matches 总量；
- 不无限刷直到有结果。

---

## 12.2 B0 PASS

至少满足其一：

### Natural
总 realistic matches 中：

```text
>=5% 出现 command-transfer/disruption
```

或：

### Event count
在预算内得到：

```text
>=30 independent command-disruption cases
```

且不是全部来自同一 seed/profile/scenario。

若自然发生几乎为零：

```text
B_FAIL_NATURALITY
```

---

# 13. B1 — Hierarchy Sensitivity

这一实验只先改变**不影响物理部署**的 command assignment：

固定：
- formation membership；
- ship order；
- leader；
- heading；
- spacing。

只改变：
- flagship；
- reserve flagship；
- succession order。

这样初始舰位完全一致。

---

## 13.1 可达性

每个 hierarchy variant 必须是 formation setup 阶段合法订单。

不能中途凭空改 hierarchy。

正确方式：

1. 从同一 scenario/seed 开始；
2. 提交不同合法 hierarchy；
3. 使用同样后续 action policy；
4. 在无 command failure 前物理轨迹应保持一致；
5. 发生同样 damage shock 后才分叉。

---

## 13.2 Shock 来源

优先使用真实自然 damage：

- 找到 pre-gunnery snapshot；
- 固定 engine RNG / paired seed；
- 某 candidate ship 在该分支真实被击沉或 captain killed；
- 在不同 hierarchy 下复现完全相同物理 damage；
- 比较 command consequences。

若为了覆盖率使用 controlled research intervention：
- 必须单独标 `INTERVENTIONAL`；
- 不可和 natural results 混为主结果；
- 必须使用真实 engine state field/event semantics；
- production engine 不改。

---

## 13.3 指标

\[
S_H(s)=
\max_G V_H(s,G)
-
\min_G V_H(s,G)
\]

其中 \(G\) 是不同合法 command hierarchy。

报告：
- next-turn legal action loss；
- speed/heading lock；
- formation integrity；
- H=1/2 turn value；
- terminal outcome（可行时）。

---

## 13.4 B1 PASS

至少：

```text
>=20% valid shock cases
hierarchy sensitivity >=0.05 normalized value
```

且 effect 在 ≥2 scenario/profile regimes 可见。

如果 hierarchy 只是 flavor、后续价值几乎不变：

```text
B_FAIL_SENSITIVITY
```

---

# 14. B2 — Robust Organization Oracle

仅 B0+B1 PASS 后执行。

候选 hierarchy：

1. current default；
2. random legal；
3. flagship=highest VP；
4. flagship=lowest exposure / robust unit proxy；
5. reserve=fastest compatible；
6. succession by survivability；
7. simple risk-aware exhaustive/oracle（小 formation）。

评价：

\[
ExpectedValue(G)
\]

和：

\[
PostShockLoss(G)
\]

---

## 14.1 B2 强信号

一个不读取 future shock 的 legal organization policy：

```text
post-shock value loss reduction >=10%
```

相对 default/random，

同时 nominal/no-shock value penalty：

```text
<=2%
```

若 robust organization 只有 oracle-with-future-info 才有效：

```text
B_ORACLE_ONLY
```

不能叫可行 AI 方法。

---

# 15. Track C — Phase-Adaptive Granularity

只在 D0 PASS 后做。

目标：

> 测量不同 phase 对 grouping 的容忍度是否本质不同。

---

## 15.1 Movement
直接使用 Track A partition evaluator。

## 15.2 Gunnery
设计最小 group macro：

```text
group shares primary target intent
```

各舰实际炮位仍由 engine 合法展开。

比较：
- individual target selection；
- group target intent。

## 15.3 Torpedo
只做最简单：

```text
group HOLD/FIRE intent
+
shared target/sector intent
```

不要复活旧 torpedo influence 研究。

---

## 15.4 C0 指标

每 phase：

```text
value loss vs decision entities
```

看：

\[
K^*_{movement}(s),
K^*_{gunnery}(s),
K^*_{torpedo}(s)
\]

是否系统不同。

---

## 15.5 C 结论标签

### `C_MODULE`
如果：
- movement 可大量压缩；
- combat 更需要细粒度；
- 结果稳定；

则把它作为 Track A 的核心模块/实验。

### `C_MAINLINE_CANDIDATE`
只有当：
- phase/state adaptive granularity 比任意 fixed granularity 明显强；
- 并且 novelty matrix 显示区别于 dynamic task decomposition / skills；

才允许独立候选。

默认不要把 C 强行独立成论文。

---

# 16. Novelty Gate

实验信号通过后必须完成：

```text
CLOSEST_PRIOR_MATRIX.csv
```

至少字段：

```text
paper
venue
year
problem
dynamic_grouping
role_learning
partner_selection
task_decomposition
one_macro_action_per_group
reduces_decision_entities
state_dependent_split_merge
performance_complexity_tradeoff
failure_model
organizational_failure
benchmark
strongest_overlap
remaining_novelty
hostile_reviewer_attack
```

---

## 16.1 必查论文

### Track A/C
- GRDC, AAAI 2026
- Autonomous Partner Selection, AAAI 2026
- CD3T, AAAI 2026
- DECOR, IJCAI 2026
- VO-MASD, IJCAI 2025
- coordination graph / action abstraction / macro-action literature
- hierarchical MARL / skill discovery
- dynamic coalition / subgroup formation

### Track B
- NeurIPS 2025 robustness/resilience study
- robust MARL
- agent failure / dropout
- fault-tolerant MARL
- dynamic leader election / role reassignment
- organizational design in multi-agent systems

---

## 16.2 强制搜索关键词

不能只读 PI 给的论文。

至少搜索：

```text
multi-agent action abstraction
agent abstraction reinforcement learning
dynamic team partition MARL
group macro action multi-agent
decision entity abstraction
dynamic coalition control MARL
state-dependent grouping macro-action
hierarchical multi-agent control granularity
agent failure command hierarchy reinforcement learning
leader failure multi-agent reinforcement learning
organizational resilience MARL
```

---

## 16.3 Fatal novelty criteria

Track A 若发现已有工作直接做到：

```text
state-dependent agent partition
+
one macro action per partition block
+
explicit reduction of decision variables
+
performance-complexity objective
```

则必须报告 `A_NOVELTY_RISK_HIGH`，等待 PI。

Track B 若最终与 generic agent-dropout robustness 无结构区别：

```text
B_NOVELTY_FAIL
```

---

# 17. Confirmatory Freeze

所有 discovery 完成后，只有 survivor 才进入 confirmatory。

生成：

```text
M2_0_DISCOVERY_FREEZE.md
```

冻结：

- snapshot dataset split；
- candidate partitions；
- macro vocabulary；
- value definition；
- H；
- rollout reps；
- epsilon；
- profiles；
- thresholds；
- model features；
- model hyperparameters；
- confirmatory seeds。

Freeze 后：
- 不改 primary metric；
- 不换 threshold；
- 不删坏 seed；
- post-hoc 必须标记。

---

# 18. 最终方向判定

本地 AI **不能替 PI 最终选主线**，但必须给硬证据标签。

---

## Track A 标签

```text
A_FAIL_ORACLE
A_SIGNAL_ONLY
A_NOVELTY_RISK
A_MAINLINE_READY
```

`A_MAINLINE_READY` 需要：

```text
A1 oracle PASS
A2 learnability PASS
>=2 scenarios
exact lab PASS
novelty no fatal collision
```

---

## Track B 标签

```text
B_FAIL_NATURALITY
B_FAIL_SENSITIVITY
B_ORACLE_ONLY
B_NOVELTY_RISK
B_MAINLINE_READY
```

---

## Track C 标签

```text
C_FAIL
C_MODULE
C_MAINLINE_CANDIDATE
```

---

# 19. 正确的“正结果方案”必须长什么样

阶段最后必须产生：

```text
POSITIVE_RESULT_BLUEPRINT.md
```

针对每个 surviving mainline 写清楚。

---

# 20. Track A 若通过：PI 预设的 full-paper 方法蓝图

工作名：

## **Decision-Entity Abstraction Network (DEAN)**

注意：本阶段不要实现完整 DEAN。

### 方法结构

1. **Agent encoder**
   \[
   h_i=f(o_i)
   \]

2. **Merge-safety / compatibility graph**
   \[
   p_{ij}=g(h_i,h_j,h_{global/local})
   \]

3. **Partition layer**
   根据 compatibility + complexity penalty 得到：
   \[
   \Pi_t
   \]

4. **Group policy**
   每个 group 只产生一个 macro action：
   \[
   u_G
   \]

5. **Rule-Constrained Executor**
   \[
   (G,u_G)\rightarrow\{a_i\}_{i\in G}
   \]
   并由环境 validator 保证合法。

6. **CTDE critic**
   训练可见 global state；
   执行时 actor 只用允许信息。

### 训练目标候选

\[
J=
J_{RL}
-\lambda_K \frac{K_t}{N_t}
-\lambda_R \hat L(s,\Pi_t)
\]

其中 merge-regret auxiliary 可由 M2-0 oracle labels warm-start。

### 论文主图
**Value / Win Rate vs Number of Decision Entities / Planning Cost**

必须比较：

```text
Flat MARL
Fixed formations
Type grouping
Spatial grouping
Role/group baselines
Dynamic grouping baseline
DEAN
Oracle partition
```

### 必须加标准 benchmark
Full paper 至少：
- one standard MARL benchmark（优先 SMACv2 或 VMAS 中适合 subgroup control 的 task）；
- Exact Team Lab；
- IBS。

### CCF-A 正结果最低形状
不是“胜率高 2%”。

而是：

```text
接近 flat-control value
+
明显更少 decision entities
+
state-dependent split/merge
+
OOD agent-count/scenario generalization
```

---

# 21. Track B 若通过：full-paper 方法蓝图

工作名：

## **Risk-Aware Command Organization (RACO)**

本阶段不要实现完整 RACO。

输入：
- unit capabilities；
- visible/known scenario threat；
- formation geometry；
- survivability proxies。

输出：
- formation membership（若研究范围允许）；
- flagship；
- reserve；
- succession order。

目标：

\[
\max_G
E[V(G)]
-\lambda E[\text{post-shock loss}]
\]

Full-paper 主结果必须表现为：

```text
nominal performance 不下降
+
command-node failure 后 recovery 更快
+
post-shock loss 更低
+
对不同 opponent / scenario 泛化
```

如果只能在手工 shock 上有效，而自然 failure 极少，不进入 CCF-A full paper。

---

# 22. 数据与计算预算

M2-0 目标是验证问题，不是训练最终 MARL。

建议预算：

- completed IBS matches：≤1,500；
- continuation branches：≤50,000；
- GPU：原则上 <20 GPU-hours；
- LLM API：0；
- 不租服务器；
- 不训练 full MAPPO / QMIX / GNN；
- 单个实验先 pilot，预计 >2h 必须写 `TIME_ESTIMATE.md` 再决定。

---

# 23. 必须画的图

## Shared
1. mode architecture diagram（classic vs realistic）
2. dataset coverage

## Track A
3. value-vs-K Pareto
4. minimal-safe-K distribution
5. fixed vs dynamic oracle
6. structured vs random matched-K
7. merge safety ROC/PR
8. state factors vs desired granularity

## Track B
9. natural disruption event rate
10. hierarchy sensitivity distribution
11. post-shock recovery curves
12. default vs robust organization

## Track C
13. phase-specific value-vs-K curves

失败结果也必须画。

---

# 24. Experiment Registry

`EXPERIMENT_REGISTRY.csv`

字段至少：

```text
experiment_id
track
gate
hypothesis
git_commit
scenario
mode
profile_pair
seed
snapshot_set
method
partition
value_definition
horizon
rollout_reps
primary_metric
result
verdict
artifact
notes
```

---

# 25. Claim-Evidence Matrix

`CLAIM_EVIDENCE_MATRIX.csv`

字段：

```text
claim_id
track
claim
evidence_type
experiment_ids
supporting_result
counterevidence
scope_limit
status
```

禁止只保存“成功实验”。

---

# 26. 失败与反例

`FAILURES_AND_COUNTEREXAMPLES.md`

必须记录：
- code bug；
- metric bug；
- invalid partition；
- legality failure；
- no-signal regime；
- baseline unexpectedly strong；
- counterexample；
- post-hoc probe；
- data leakage risk；
- rule/document mismatch。

修 bug 不删记录。

---

# 27. 最终交付包

文件名：

```text
M2_0_ORGANIZATIONAL_INTELLIGENCE_VALIDATION_BUNDLE.zip
```

建议 ≤150 MB。

必须包含：

```text
00_EXECUTIVE_SUMMARY.md
01_MODE_SEMANTICS_AUDIT.md
02_DATASET_AND_EXACT_LAB.md
03_TRACK_A_DYNAMIC_TEAM_ABSTRACTION.md
04_TRACK_B_COMMAND_ORGANIZATION.md
05_TRACK_C_PHASE_GRANULARITY.md
06_CLOSEST_PRIOR_REVIEW.md
07_DIRECTION_SCORECARD.md
08_POSITIVE_RESULT_BLUEPRINT.md
M2_0_DISCOVERY_FREEZE.md
EXPERIMENT_REGISTRY.csv
CLAIM_EVIDENCE_MATRIX.csv
FAILURES_AND_COUNTEREXAMPLES.md
VALUE_DEFINITION.md
DATA_MANIFEST.md
environment.txt
git_info.txt
figures/
metrics/
exact_team_lab/
code_patch/
logs/
```

不要打包：
- `.venv`
- `node_modules`
- `.git`
- 100MB+ 可再生 raw cache
- 模型 cache
- keys

大文件写：
```text
path
size
sha256
generation_command
```

---

# 28. `00_EXECUTIVE_SUMMARY.md` 必须回答

必须明确填写：

```text
P0_MODE_AUDIT = PASS / FAIL
D0_MACRO_EXECUTOR = PASS / FAIL

A_ORACLE_SIGNAL = PASS / FAIL
A_STATE_DEPENDENCE = PASS / FAIL
A_COMPRESSION_VALUE = PASS / FAIL
A_LEARNABILITY = PASS / FAIL
A_NOVELTY = PASS / FAIL / AMBIGUOUS
A_VERDICT = A_FAIL_ORACLE / A_SIGNAL_ONLY / A_NOVELTY_RISK / A_MAINLINE_READY

B_NATURALITY = PASS / FAIL
B_HIERARCHY_SENSITIVITY = PASS / FAIL
B_ROBUST_ORGANIZATION = PASS / FAIL / NOT_RUN
B_NOVELTY = PASS / FAIL / AMBIGUOUS
B_VERDICT = ...

C_PHASE_DIFFERENCE = PASS / FAIL
C_VERDICT = C_FAIL / C_MODULE / C_MAINLINE_CANDIDATE

BEST_EVIDENCE_TRACK =
SECOND_BEST_TRACK =
TRACKS_TO_KILL =
BIGGEST_UNRESOLVED_RISK =
```

不要用：
- promising
- encouraging
- likely useful

代替明确判定。

---

# 29. `07_DIRECTION_SCORECARD.md`

不要做主观星级排名。

只列证据：

| Criterion | Track A | Track B | Track C |
|---|---|---|---|
| exact-lab signal | | | |
| IBS natural signal | | | |
| state dependence | | | |
| effect size | | | |
| strong-baseline gap | | | |
| learnability | | | |
| cross-scenario | | | |
| standard benchmark portability | | | |
| engineering cost | | | |
| closest-prior overlap | | | |
| strongest counterevidence | | | |
| current verdict | | | |

PI 根据该表最终决定主线。

---

# 30. 阶段停止点

本地 AI 完成整个 M2-0 后停止。

**不要自行进入：**
- full MAPPO；
- QMIX；
- GNN grouping；
- DEAN；
- RACO；
- server rental；
- full benchmark training；
- paper drafting。

第一阶段的任务只有：

\[
\boxed{
\text{找到一个确实存在、可学、可泛化、没有致命 novelty 冲突的问题}
}
\]

并把它转换成：

\[
\boxed{
\text{一个明确的 full-paper 正结果设计}
}
\]

然后把 bundle 交给 PI 决策。

---

# 31. 本阶段最重要的科研纪律

1. **Normal vs Realistic 不得直接当作“flat vs hierarchy”的纯因果比较。**
   - 真实模式改变了规则约束，不只改变控制架构。
2. **不能把 centralized commander 直接称为 MARL。**
3. **Track A 的创新必须是 decision-entity/action factorization abstraction，不是 role/grouping 换名。**
4. **Track B 必须利用 command-node failure 改变组织状态这一结构，不能退化成 generic dropout robustness。**
5. **所有主结论以 simulator continuation/value 为准，不以 heuristic score 为准。**
6. **先 oracle gap，再学习算法。**
7. **如果 oracle 自己都没有优势，不训练 neural policy。**
8. **不为了“必须找到主线”降低 gate。**
