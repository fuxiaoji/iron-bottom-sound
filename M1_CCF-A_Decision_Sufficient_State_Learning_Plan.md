# M1：以 CCF-A 为目标的主线验证计划
## Decision-Sufficient State Learning under Hidden Commitments

**项目**：`fuxiaoji/iron-bottom-sound`  
**阶段**：M1 — 主线生死验证  
**目标会议类型**：CCF-A AI 主会（优先考虑 AAAI / IJCAI 风格；若方法更偏 representation learning / world models，再考虑 NeurIPS / ICML 风格）  
**执行模式**：PI 负责方向、方法边界、判定标准；本地 AI 负责代码、实验、日志、打包。  
**当前主线**：Decision-Sufficient State Learning under Hidden Commitments  
**当前状态**：M0 已完成；A/C/D 不再并行推进，B* 进入 M1。  

---

# 0. 为什么现在选这条主线

M0 cheap-kill 的核心结果：

- A（adaptive replanning）存在信号，但固定 periodic 策略已经在相当一部分点达到原门槛，尚不足以支持“必须学习 when-to-plan”的强主张；
- B（commitment-aware state）出现了最明确的机制性正信号：
  - sealed games 中存在 snapshot-policy regret；
  - Markov/control 中该现象消失；
  - 仅看 value-gap 会产生假阴性；
  - `value-equivalent` 并不意味着 `decision-equivalent`；
- C（certificate-directed PSRO）在 near-tied regime 有很强节省，但在结构性优势 regime 出现严重 starvation/failure；
- D（DiagGame）在当前生成器中出现结构性不可辨识，继续投入不划算。

因此 M1 不再做“四线并行”，而集中验证：

> **一个 AI agent 是否可以学习一个 compact latent state，它不要求恢复整个隐藏世界，但必须保留所有会改变最优战略决策的信息。**

这比“做一个新的 game abstraction”更适合 CCF-A Game AI / Multi-agent / Representation Learning 投稿。

---

# 1. 论文目标形态

暂定题目：

**Learning Decision-Sufficient States for Strategic Agents under Hidden Commitments**

候选中文：

**隐藏承诺下战略智能体的决策充分状态学习**

理想论文结构：

1. **AI 问题**
   - agent 只能看到部分可观测历史；
   - 对手存在 pending / sealed commitment；
   - 当前 public snapshot 可能不足以支持正确决策。

2. **核心现象**
   - `value-equivalent != decision-equivalent`
   - 两个 history 可以拥有相同最优 value，但最优 action 不同。

3. **方法**
   - 从 history 学习 latent state；
   - latent 只保留 decision-relevant hidden information；
   - 不要求完整 hidden-state reconstruction。

4. **方法目标**
   - 降低 decision regret；
   - 降低 alias-pair regret；
   - 泛化到 unseen opponent / unseen commitment length / unseen scenario。

5. **理论支持**
   - 给出 commitment-sufficient statistic 的条件；
   - 证明或至少系统验证：
     `public state + belief over pending commitments`
     在特定条件下足以决定 continuation Q-values。

6. **实验**
   - Exact Strategic Lab；
   - 标准 imperfect-information benchmark；
   - Iron Bottom Sound；
   - 最终 M2 再考虑 online RL/self-play。

---

# 2. M1 的唯一目标

M1 不是写完论文，而是回答四个生死问题：

## G1 — Naturalness
Iron Bottom Sound 里是否真实存在自然、合法、可达的 commitment-induced decision aliasing？

## G2 — Generality
这个现象是否能在标准或公开可复现的 imperfect-information game benchmark 中复现，而不是 IBS 私有现象？

## G3 — Method
regret-guided / commitment-aware representation learning 是否真正优于 GRU / Transformer / generic history encoder？

## G4 — Novelty
与 public belief state、world-model latent、information abstraction/refinement、IIG representation 学习相比，是否存在足够清晰的 CCF-A 新颖性？

只有：

```text
G1 = PASS
G2 = PASS
G3 = PASS
G4 = PASS 或 STRONG_AMBIGUOUS
```

才进入 M2 full-paper。

任何硬门失败，都停止扩算力，先回 PI 决策。

---

# 3. M1 阶段总决策树

```text
START
 |
 v
G1：IBS 中存在自然 commitment-induced aliasing？
 |
 +-- NO --> B_TOY_ONLY --> STOP
 |
 +-- YES
       |
       v
G2：标准/公开 benchmark 中也可复现？
 |
 +-- NO --> DOMAIN_SPECIFIC_RISK --> STOP / REFRAME
 |
 +-- YES
       |
       v
G3：DSRL > 最强参数匹配 history baseline？
 |
 +-- NO --> METHOD_FAIL --> STOP
 |
 +-- YES
       |
       v
G4：closest-prior novelty 安全？
 |
 +-- NO --> NOVELTY_FAIL --> STOP / REFRAME
 |
 +-- YES
       |
       v
M1 PASS
 |
 v
M2 Full Paper
```

---

# 4. Gate 1：Iron Bottom Sound 自然反例

## 4.1 目标

寻找真实、合法、可达的 history pairs：

```text
public observation identical
own current state identical
own pending order identical
legal action set identical
opponent hidden pending commitment different
```

但：

```text
best action differs
or
shared-action regret > 0
```

定义：

\[
R(h_1,h_2)=
\min_a
\max\{
V^*(h_1)-Q^*(h_1,a),
V^*(h_2)-Q^*(h_2,a)
\}.
\]

M1 的第一硬门不是神经网络，而是这个现象在真实复杂环境中是否存在。

---

## 4.2 优先调查阶段

优先级：

### 1. Torpedo planning
重点检查：

```text
movement orders 已 sealed
↓
torpedo planning / tactical decision
↓
movement resolution
```

原因：

- hidden movement commitment 对未来 route 有直接影响；
- 现有 `AdaptiveTorpedoPlanner` 已有 opponent route / counterfactual response 逻辑；
- 最容易获得 decision-sensitive Q 差异。

### 2. Realistic-command formation planning
重点：

- lead formation commitment；
- formation speed；
- turning path；
- command interruption；
- forced continuation。

### 3. Gunnery
只有前两项信号不足时再做。

---

## 4.3 Pair 生成方式

禁止直接编辑成不可达 state。

允许：

1. 从真实 scenario 起点运行；
2. 让双方提交合法订单；
3. 在订单封存后 clone engine state；
4. 仅替换对手另一个**合法且可从同一公开 observation 产生**的 sealed commitment；
5. 确保替换前后：
   - public observation 完全一致；
   - own observation 完全一致；
   - own legal action set 完全一致；
6. forward simulate。

必须保存：

```text
pair_id
scenario
seed
turn
phase
public_observation_hash
own_state_hash
legal_action_hash
hidden_commitment_A
hidden_commitment_B
candidate_actions
Q_A
Q_B
V_A
V_B
shared_action_regret
normalized_regret
reachability_proof
```

---

## 4.4 Q-value 估计

优先级：

### Exact / deterministic
如果局部子问题可以完全枚举，优先 exact。

### Simulator rollouts
若不能 exact：

- 每 action × hidden commitment 做多 seed rollout；
- 使用同一对未来随机种子做 common-random-number pairing；
- 输出 mean / CI；
- 若 action ranking CI 重叠太多，该 pair 不进入主分析。

### Strong tactical oracle
已有 tactical planner 可作为 candidate generator，但不能把 heuristic score 当真值。

必须通过 simulator continuation 验证。

---

## 4.5 G1 PASS 标准

至少：

- ≥25 个 nontrivial pairs；
- ≥2 个 scenario；
- pair 全部真实可达；
- hidden commitment 是唯一关键变化；
- public observation hash / legal action hash 一致；
- ≥20% pairs：
  `normalized shared-action regret >= 0.10`
- 至少 5 个可人工审计的强反例；
- control pairs 基本不出现同等级 regret。

如果无法满足：

```text
G1_IBS_NATURALITY = FAIL
FINAL = B_TOY_ONLY
```

立即停止，不进入 G2/G3。

---

# 5. Gate 2：标准 Game AI benchmark

## 5.1 目标

证明问题不是：

> “Iron Bottom Sound 规则导致的一个特殊 bug/现象。”

而是一个一般性的 imperfect-information strategic-agent 问题。

---

## 5.2 首选平台

优先 OpenSpiel。

候选：

- Goofspiel with imperfect information
- Oshi-Zumo
- Liar's Dice
- Battleship
- Kuhn / Leduc 作为 non-commitment control

但必须先检查其真实 information-state semantics。

不要因为游戏“看起来像 simultaneous”就认为有 pending hidden commitment。

---

## 5.3 必做 feasibility audit

对每个 game：

1. current player 的 observation string / information state；
2. previous hidden action 是否已提交；
3. 对另一玩家是否不可见；
4. future transition 是否依赖该 hidden action；
5. 是否存在相同 observation、不同 hidden pending action；
6. 是否能形成 shared-action regret。

输出：

`OPEN_SPIEL_COMMITMENT_AUDIT.md`

---

## 5.4 如果标准游戏不足

允许增加一个公开、极小、可复现的：

`SealedCommitmentGame`

要求：

- OpenSpiel-compatible API；
- 规则简单；
- 不依赖 IBS；
- 2-player zero-sum；
- pending commitment 是核心机制；
- exact solve 可行；
- README 中给出完整规则。

这是 benchmark，而不是新产品。

---

## 5.5 G2 PASS 标准

必须至少形成：

```text
Exact Lab
+ 1 个公开/标准 commitment benchmark
+ 1 个 non-commitment control
+ Iron Bottom Sound
```

理想为：

```text
2 个 commitment benchmark + IBS
```

若只有：

```text
Exact Lab + IBS
```

则：

```text
G2_GENERALITY = FAIL or AMBIGUOUS
DOMAIN_SPECIFIC_RISK = HIGH
```

暂停并回 PI。

---

# 6. Gate 3：Representation Learning 方法

## 6.1 方法工作名

**DSRL — Decision-Sufficient Representation Learning**

暂不固定最终论文名。

---

## 6.2 输入与输出

输入 history：

\[
h_t=(o_1,a_1,o_2,a_2,\ldots,o_t)
\]

encoder：

\[
z_t=f_\theta(h_t)
\]

policy/Q head：

\[
\pi(a|z_t), \quad Q(z_t,a)
\]

我们不要求：

\[
z_t \approx X_t^{full-hidden-state}
\]

而要求：

> 对未来最优决策而言，两个 history 该合并时合并，该分开时分开。

---

# 7. Decision compatibility

对两个 histories：

\[
h_i,h_j
\]

定义：

\[
D_R(h_i,h_j)
=
\min_a
\max\{
V^*(h_i)-Q^*(h_i,a),
V^*(h_j)-Q^*(h_j,a)
\}.
\]

如果：

\[
D_R(h_i,h_j)\le \epsilon
\]

则称：

**decision-compatible**

否则：

**decision-incompatible**

这比：

- next-state similarity；
- value similarity；
- hidden-state similarity；

更接近真正的战略决策目标。

---

# 8. DSRL 第一版方法

不做复杂模型。

先做：

\[
L =
L_{\text{task}}
+
\lambda_R L_{\text{regret}}
+
\lambda_C L_{\text{commit}}
\]

## 8.1 Task loss

可选：

- Q regression；
- policy imitation；
- action ranking。

M1 优先 Q/policy supervision。

---

## 8.2 Regret-guided representation loss

对于 pair `(h_i,h_j)`：

### Compatible
拉近 latent：

\[
L^+ = ||z_i-z_j||^2
\]

### Incompatible
用 margin 拉远：

\[
L^- =
\max(0,m-||z_i-z_j||)^2
\]

权重可由：

\[
w_{ij}=clip(D_R(h_i,h_j),0,w_{max})
\]

控制。

---

## 8.3 Commitment auxiliary

预测：

- pending commitment distribution；
- commitment class；
- commitment-relevant statistic。

但 auxiliary 不是主任务。

必须验证：

```text
commitment prediction accuracy 高
```

是否真的对应：

```text
decision regret 低
```

不允许把 auxiliary accuracy 当论文主结果。

---

# 9. 2×2 核心消融

必须严格做：

| Variant | Regret loss | Commitment aux |
|---|---:|---:|
| Base | No | No |
| +Commit | No | Yes |
| +Regret | Yes | No |
| DSRL | Yes | Yes |

如果结果：

```text
+Commit ≈ DSRL
```

说明真正贡献可能只是 hidden commitment prediction。

如果：

```text
+Regret > +Commit
```

则更支持 Decision Sufficiency 叙事。

如果：

```text
GRU/Transformer ≈ DSRL
```

则方法失败。

---

# 10. 必须使用的 Baselines

## R0 Snapshot MLP
当前 snapshot，不用历史。

## R1 GRU
完整可观察 history。

## R2 Transformer
完整 history，参数量匹配。

## R3 Generic latent/world-model baseline
一个普通 latent predictive objective：
- next observation；
- reward；
- transition。

## R4 Belief baseline
在可 tractable 环境：
- public belief；
- particle belief；
- exact belief。

## R5 Oracle hidden commitment
直接输入真实 hidden commitment。

只作为 upper bound。

---

# 11. 公平性控制

必须尽可能匹配：

- latent dimension；
- parameter count；
- optimizer；
- training samples；
- training steps；
- seeds；
- policy/Q head；
- action mask。

每种方法至少 5 seeds。

不能出现：

```text
DSRL 5M parameters
GRU 300K parameters
```

然后称方法获胜。

---

# 12. 数据生成

## 12.1 Exact Lab

提供：

- exact Q*；
- exact V*；
- exact decision regret；
- exact commitment；
- exact alias pairs。

用途：

- debugging；
- method sanity；
- theorem sanity。

---

## 12.2 OpenSpiel

优先使用：

- exact solve；
- CFR；
- best response；
- 或强 teacher。

记录 teacher quality。

---

## 12.3 IBS

数据全部 simulator-generated。

禁止使用未经授权真人数据。

IBS dataset 每条：

```text
history
public observation
candidate actions
action mask
hidden commitment (research-only label)
Q estimate per action
Q uncertainty
best action
scenario
seed
phase
```

主训练中可使用 research-only commitment label 做 auxiliary；

正式 inference 禁止访问真实 hidden commitment。

---

# 13. M1 不先做 PPO

M1 先回答：

> representation 本身是否有价值。

所以先做：

- imitation / Q supervision；
- fixed teacher；
- offline evaluation。

只有 M1 PASS 才在 M2 加：

- PPO；
- recurrent PPO；
- self-play；
- population play；
- exploitability / BR；
- test-time planning。

这样避免“PPO 没调好”掩盖 representation 的真价值。

---

# 14. 主指标

## Primary 1 — Decision regret

\[
Regret(h)=V^*(h)-Q^*(h,\pi(z_h))
\]

或 simulator 估计版本。

---

## Primary 2 — Alias-pair regret

只在 commitment-induced alias pairs 上：

\[
R_{pair}
\]

这是最能验证主假设的指标。

---

## Secondary

- action accuracy；
- ranking accuracy；
- normalized return；
- win rate；
- exploitability（tractable game）；
- calibration；
- latent clustering；
- commitment prediction accuracy。

---

# 15. OOD 测试

必须包含至少 3 类：

1. unseen opponent policy；
2. unseen commitment length；
3. unseen horizon / scenario。

推荐再加：

4. noise / partial observation level；
5. action branching；
6. payoff shift。

---

# 16. G3 PASS 标准

相对于：

**最强参数匹配 history baseline**

而不是 snapshot baseline。

要求：

- confirmatory set 上：
  `>=20% relative reduction in decision regret`
- 至少 3 个 domain 方向一致；
- IBS 必须有正结果；
- 不能有核心 domain 出现 >10% 稳定退化；
- gain 不能全部来自 Exact Lab；
- alias-pair regret 上必须有明确提升。

如果：

```text
Snapshot << DSRL
GRU ≈ Transformer ≈ DSRL
```

则：

```text
G3_METHOD = FAIL
```

---

# 17. Gate 4：Novelty 与理论

## 17.1 Closest-prior matrix

必须检查：

- ReBeL / public belief state
- LAMIR
- NashDreamer
- Embedding CFR
- WEVA
- imperfect-information abstraction / refinement
- bisimulation / state abstraction
- predictive state representations
- POMDP belief compression
- representation learning for control
- opponent modeling / belief modeling

表格字段：

```text
paper
year
formal_problem
representation
training_objective
decision_regret
belief_used
pending_commitment_explicit
online_agent_state
theory
benchmark
strongest_overlap
our_remaining_novelty
reviewer_attack
```

---

# 18. 必须回答的两个 reviewer killer question

## Q1
为什么：

> `belief over pending commitment`

不是：

> public belief state 的平凡低维投影？

必须有结构条件或算法收益回答。

## Q2
为什么：

> regret-guided refinement / representation

不是：

> 传统 extensive-form game abstraction/refinement 换了个 neural encoder？

必须至少满足一个：

- online learned representation；
- trajectory-to-state mapping；
- scalable without full game-tree enumeration；
- commitment-specific bottleneck；
- generalization to unseen games/opponents；
- end-to-end acting agent improvement。

否则 novelty gate 不通过。

---

# 19. 理论目标：只做一个命题

设 hidden private variable：

\[
X_t
\]

pending commitment：

\[
C_t=g(X_t)
\]

如果未来：

- transition；
- payoff；
- opponent strategic response；

对 hidden history 的影响只通过 `C_t` 传递，

尝试建立：

\[
Z_t=
(S_t^{pub},P(C_t|h_t))
\]

为 decision-sufficient statistic：

\[
Q^*(h_t,a)=Q^*(Z_t,a).
\]

本地 AI 任务：

1. 写 assumptions；
2. Exact Lab exhaustive check；
3. 逐个删除 assumption；
4. 自动搜最小反例；
5. 输出 `THEOREM_SANITY.md`。

不要自行宣布“证明完成”。

---

# 20. Discovery / Confirmatory 纪律

## Discovery

允许：

- 调 λ；
- 调 margin；
- 选 latent dim；
- 修 bug；
- 找训练稳定区间。

全部记录。

## Freeze

生成：

`M1_DISCOVERY_FREEZE.md`

固定：

```text
model
params
latent_dim
losses
lambda
margin
optimizer
steps
data split
seed list
primary metrics
PASS threshold
```

## Confirmatory

使用：

- unseen seed；
- unseen game instances；
- unseen IBS scenario/rollout seeds；
- 至少一个 distribution shift。

冻结后不得再调。

所有 post-hoc 分析单独标记。

---

# 21. CCF-A 风格实验矩阵

最低要求：

| Domain | Snapshot | GRU | Transformer | Generic Latent | Belief | +Commit | +Regret | DSRL | Oracle |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Exact Lab | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Public benchmark 1 | ✓ | ✓ | ✓ | ✓ | ✓/if feasible | ✓ | ✓ | ✓ | ✓/if possible |
| Public benchmark 2/control | ✓ | ✓ | ✓ | ✓ | ✓/if feasible | ✓ | ✓ | ✓ | - |
| Iron Bottom Sound | ✓ | ✓ | ✓ | ✓ | approximate | ✓ | ✓ | ✓ | research-only |

M1 不必全部大规模训练，但结构必须完整。

---

# 22. M1 时间预算

建议：

## Week 1
G1 — IBS natural aliasing

## Week 2
G2 — benchmark + data pipeline

## Week 3
G3 discovery — baselines + DSRL

## Week 4
freeze + confirmatory + G4 novelty/theory

如果一个 gate 明确失败，立即停止，不补满 4 周。

---

# 23. 计算预算

M1 默认：

- 主要使用本地 RTX 5070；
- 不租服务器；
- 单模型 discovery < 4 GPU-hours；
- 总 GPU 预算目标 < 40 GPU-hours；
- IBS rollout < 50,000 局；
- LLM API = 0；
- 不训练大型 foundation model。

只有 M1 PASS 后，M2 才申请扩算力。

---

# 24. 实验注册

继续维护：

`research/m1/EXPERIMENT_REGISTRY.csv`

字段：

```text
experiment_id
gate
hypothesis
commit
data_version
model
params
seed
primary_metric
secondary_metrics
result
verdict
artifact
notes
```

---

# 25. 结果打包

最终：

`M1_DECISION_STATE_VALIDATION.zip`

必须包含：

```text
00_EXECUTIVE_SUMMARY.md
01_G1_IBS_ALIASING.md
02_G2_GENERALITY.md
03_G3_METHOD.md
04_G4_NOVELTY.md
THEOREM_SANITY.md
CLOSEST_PRIOR_MATRIX.csv
M1_DISCOVERY_FREEZE.md
DECISION_TREE_RESULT.md
EXPERIMENT_REGISTRY.csv
CLAIM_EVIDENCE_MATRIX.csv
FAILURES_AND_COUNTEREXAMPLES.md
IBS_ALIAS_PAIRS.jsonl
OPEN_SPIEL_COMMITMENT_AUDIT.md
metrics/
figures/
code/
logs/
environment.txt
git_info.txt
```

---

# 26. 每个 Gate 的 checkpoint

不要一次跑完整 M1。

## G1 后
输出：

`M1_G1_CHECKPOINT.zip`

等待 PI。

## G2 后
输出：

`M1_G2_CHECKPOINT.zip`

等待 PI。

## G3 discovery 后
输出：

`M1_G3_DISCOVERY_CHECKPOINT.zip`

等待 PI 决定是否 freeze。

## 最终
输出：

`M1_DECISION_STATE_VALIDATION.zip`

---

# 27. G1 checkpoint 必须包含

```text
G1_EXECUTIVE_SUMMARY.md
IBS_ALIAS_PAIRS.jsonl
PAIR_VALIDATION.csv
CONTROL_PAIRS.csv
Q_ESTIMATION_METHOD.md
REACHABILITY_AUDIT.md
FAILURES_AND_COUNTEREXAMPLES.md
figures/
scripts/
logs/
git_info.txt
environment.txt
```

---

# 28. G1 Executive Summary 必须回答

```text
How many valid alias pairs?
How many scenarios?
How many have normalized regret >= 0.10?
What is median/max regret?
Are public observations byte/structure identical?
Are legal action sets identical?
Are pairs naturally reachable?
What variable differs?
How reliable are Q estimates?
What do controls show?

G1_IBS_NATURALITY = PASS / FAIL
```

不允许使用“promising”。

---

# 29. 最重要的科研纪律

本阶段最危险的三种错误：

1. **把 public-state insufficiency 当成 novelty**
   - 不是。IIG/POMDP 已知。

2. **把 hidden commitment prediction accuracy 当成主要贡献**
   - 不是。我们的对象是 decision sufficiency。

3. **只比 snapshot MLP**
   - 不够。必须打赢强 history baseline。

---

# 30. 当前立即执行的任务

现在只执行：

\[
\boxed{\text{G1 — Iron Bottom Sound natural aliasing}}
\]

不要进入 G2。

不要训练 neural representation。

不要实现 PPO。

不要扩大 PSRO。

先回答：

> **在真实 IBS 中，hidden pending commitment 是否真的造成足够强、足够自然、足够频繁的 decision aliasing？**

如果答案是否定的，这条主线应立即停止。

如果答案是肯定的，再进入下一 gate。

