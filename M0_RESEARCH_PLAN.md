# CCF-A 目标：多主线科研验证 M0 执行计划
## 面向 `fuxiaoji/iron-bottom-sound` 的本地 AI 实验迭代手册

**版本**：M0-v1  
**用途**：交给全新的本地执行 AI。  
**角色分工**：

- **科研总负责人 / PI（ChatGPT）**：提出研究问题、控制选题边界、设定验收门、审阅结果、决定主线与论文叙事。
- **本地执行 AI**：只负责审计仓库、实现研究用实验代码、运行实验、记录失败、生成图表、打包结果。**不得自行修改主研究问题，不得为了“做出正结果”改指标或挑数据。**
- **用户**：提供机器、仓库和必要授权；将 M0 结果包交回 PI 做下一轮决策。

---

# 0. 本阶段唯一目标

当前不是“把论文做完”，而是做 **M0 多主线可行性验证**。

M0 结束时必须回答：

1. 哪些方向在数学/算法上确实存在可测量的正信号？
2. 哪些方向在 Iron Bottom Sound 上确实能落地，而不只是 toy example？
3. 哪些方向的正结果经 confirmatory run 后仍成立？
4. 哪些方向虽然能做，但和 2025–2026 前沿过于接近，创新空间不足？
5. 哪一条主线值得进入正式论文阶段 M1？

本阶段**不以“写出漂亮论文”作为成功标准**，而以：

> **用尽可能小的成本，排除错误猜想，留下 1–2 条有硬证据的主线。**

最终由 PI 决定主线；本地 AI 只输出 `PASS / FAIL / AMBIGUOUS` 和证据。

---

# 1. 当前研究资产与不可丢失的优势

## 1.1 现有 OR 论文留下的研究资产

已有论文：

**Certified Budgeted Revision Scheduling Against Strategic Opponents**

真正应继续继承的是以下结构，而不是简单复刻“revision calendar”：

1. **Strategic opponent**：对手本身是优化者，而不是外生随机变量。
2. **Sealed commitments**：未执行命令可以被对手预先封存但对我方不可见。
3. **Public-state insufficiency**：同一公开历史可能对应不同隐藏未执行命令，从而产生不同 continuation game。
4. **Budgeted adaptation**：不是问“做什么”，而是问“什么时候值得重新决策/重新规划”。
5. **Certification**：不仅找一个解，而且尝试给出可独立检查的上下界或损失保证。
6. **Valid-object reuse**：已求出的对手可行响应在相关问题之间可能继续提供有效界。

旧工作已经暴露两个很重要的下一步问题：

- exact solve 随 horizon 增长非常快，必须走向 scalable AI / learning；
- 理论上更紧的 certificate 在旧实验中并未带来实际 pruning，所以新工作不能只“把旧 bound 再包装一次”。

## 1.2 Iron Bottom Sound 当前科研资产

本地 AI 必须先审计实际仓库，不得只依赖这份计划中的描述。重点确认：

- 权威规则引擎、合法动作与 `observe()` 过滤；
- 双方秘密/封存订单；
- replay / snapshots / event log；
- `state_export` / LLM 可读世界态；
- `TacticalCommander` 和各种 `TacticalProfile`；
- `AdaptiveTorpedoPlanner` 的 counterfactual route response；
- `bench.py` / `run_match` 自动对局；
- `rl/evolve.py`；
- `rl/psro.py` 与 meta-game / regret matching / best-response population；
- realistic-command 模式；
- 自定义 scenario 能力；
- 现有测试与 deterministic seed 机制。

**研究代码不得改变原规则裁决语义。**

---

# 2. M0 候选主线

本阶段同时验证四条主线。

## Track A — CARP
### Certified Adaptive Replanning under Hidden Commitments

核心问题：

> 在不完全信息、对手具有隐藏未执行承诺的博弈中，智能体能否在线决定“什么时候值得花一次昂贵 planning compute”，同时保证少规划造成的战略价值损失可控？

这是当前优先验证方向。

---

## Track B — CAIS
### Commitment-Aware Information State

核心问题：

> 公开 observation 是否因为隐藏 pending commitment 而产生严重 state aliasing？能否构造一个显式 commitment belief / refinement representation，使 continuation value 更接近 sufficient state？

这是高理论上限方向。

---

## Track C — CD-PSRO
### Certificate-Directed PSRO / Empirical Game Sampling

核心问题：

> PSRO/EGTA 的 simulation budget 能否不再平均撒在所有 payoff cells 上，而是由 equilibrium/certificate uncertainty 主动决定下一局应该模拟哪一对策略？

这是最快工程备线。

---

## Track D — DiagGame / B2-X
### Identifiable Strategic Test Synthesis

核心问题：

> 能否自动生成“最小战略对照实验”，以少量测试识别一个 agent 的具体 reasoning defect，而不是只生成“难游戏”？

这是 LLM/game evaluation 备线。

---

# 3. 总体执行规则

## 3.1 研究治理硬约束

本地 AI 必须遵守：

1. **先 `git status`，禁止覆盖用户工作。**
2. 不允许 `git reset --hard`、`git clean -fd`、覆盖未提交文件、静默 stash 用户改动。
3. 若当前工作树非干净：
   - 记录 `git status --short`；
   - 从当前 `HEAD` 新建独立 `git worktree` 或研究分支；
   - 原工作区保持不动。
4. 研究代码优先放：
   - `research/m0/`
   - 或独立 `research/m0-*` 分支。
5. 原规则引擎除 bug fix 外不改；如发现 bug：
   - 单独记录；
   - 单独 commit；
   - 必须重新运行所有受影响 baseline；
   - 不得把 bug fix 和研究算法混在一个 commit。
6. **禁止为得到正结果改变指标。**
7. Discovery 和 Confirmatory 数据必须分离。
8. 所有随机实验必须记录 seed。
9. 所有失败、超时、NaN、invalid game 都必须记录，不得删除。
10. 不使用未经同意的真人对局数据；M0 默认只用 simulator-generated data。
11. M0 不调用付费 LLM API。
12. M0 不训练大型模型；单个神经实验不得成为主要工程负担。
13. 任何 certificate 候选若发现一个反例，即标记 `INVALID`，不得通过 clipping/后处理掩盖违反。
14. 不做“跑很多参数只汇报最好一个”。所有调参轨迹留档。

## 3.2 M0 资源上限

默认上限：

- 总 Iron Bottom Sound 自动对局：**≤ 20,000 局**
- 单一实验最长墙钟：**2 小时**
- 单方向 discovery 最长：**约 12–18 小时机器时间**
- GPU：非必要；若用，单方向不超过约 4 GPU-hours
- LLM API：**0**
- 不允许因为性能问题重写整个引擎到 C++/CUDA
- 不允许 M0 阶段实现完整 PPO / DeepCFR / 世界模型

如果一个方向必须先做数周基础设施才能看到第一条曲线，优先判为 **工程风险过高**。

---

# 4. 总阶段安排

## P0 — 仓库审计与冻结
预计 0.5–1 天。

输出：

- `AUDIT.md`
- `BASELINE_STATUS.md`
- `git_info.txt`
- 当前测试结果
- 当前可用 scenario / policy / replay / snapshot / legal-action 接口清单
- 可直接复用模块地图
- 不能复用的缺口

### P0 必做测试

至少确认：

1. `run_match` 能 deterministic 复跑；
2. 同 seed + 同策略是否稳定；
3. 三个代表场景是否都能自动终局；
4. `rl/psro.py --smoke` 是否仍通过；
5. snapshots / event log 是否可以被研究代码只读使用；
6. 是否存在真正的 sealed/pending order 字段；
7. `AdaptiveTorpedoPlanner` 是否可以独立调用并返回 counterfactual response；
8. 当前策略集合来自哪里，禁止手工假定名称。

若基础设施本身损坏，先停在 P0，不进入科学实验。

---

## P1 — 共用 Exact Strategic Lab
预计 1–2 天。

Track A / B / D 共用一个小型、可完全枚举的实验环境。

目标不是造新游戏产品，而是建立一个：

> **可以得到真值的 strategic laboratory。**

### 4.1 必须实现的最小 DSL

放在：

`research/m0/common/exact_games/`

支持：

- 2-player zero-sum；
- horizon `T=2..6`；
- action size `b=2..3`；
- public observations；
- private information；
- opponent pending/sealed action blocks；
- focal pending action blocks；
- deterministic 或小型 chance node；
- path-dependent terminal payoff；
- exact enumeration；
- exact continuation value；
- exact best action；
- exact mixed strategy（需要时）；
- history → public observation；
- history → hidden commitment；
- clone / counterfactual continuation。

### 4.2 单元测试

至少包括：

- 一个完全 Markov 的 control game；
- 一个存在 public-state aliasing 的 `T=2` minimal witness；
- 一个 public observation 相同但 hidden pending commitment 不同、最优 continuation action 相反的例子；
- 一个 commitment 不影响 continuation 的 negative control；
- 一个 path-dependent payoff case。

### 4.3 数据生成

Discovery：

- 约 1,000–2,000 个游戏实例；
- T=3–5；
- b=2–3；
- 至少 3 种 payoff family；
- 至少 3 种 commitment pattern。

Confirmatory：

- 单独 generator seed；
- 300–500 个新游戏；
- 增加 T=5–6；
- 至少一个 discovery 中未见过的 payoff family 或 commitment-length 分布。

**训练/调参不能看到 confirmatory set。**

---

# 5. Track A：CARP 验证计划

# A0. 要验证的核心猜想

### H-A1
在 strategic opponent + sealed commitment 环境中：

> `always replan` 并非达到近似最优 value 所必需。

存在 adaptive gate，在显著减少 planning calls 的同时保留大部分战略价值。

### H-A2
是否应该 replan 与当前公开 observation 本身并不充分相关；引入 commitment-aware statistic 后可明显提升 gate quality。

### H-A3
可以构造一个**非空洞**的 loss certificate / upper bound，使其在 exact games 上始终覆盖真实 replanning loss，并显著紧于 trivial payoff-range bound。

---

# A1. 定义 planning/replanning

对每个 decision epoch：

- `REPLAN`：调用完整 continuation solver / expensive planner，基于当前信息重新生成后续计划；
- `CONTINUE`：继续执行上一次封存计划，不调用 planner。

定义：

\[
\Delta_t =
V_{\text{replan}}(h_t)-V_{\text{continue}}(h_t)
\]

在 exact lab 中，`\Delta_t` 必须能精确计算。

---

# A2. 第一组实验：是否存在值得学习的 replanning structure？

对 exact-game discovery pool 的所有 reachable decision states：

记录：

- public observation；
- hidden commitment（只作 oracle 标签，不作为普通 agent 输入）；
- 剩余 horizon；
- 当前计划；
- belief entropy（若可计算）；
- legal action count；
- payoff range；
- exact `V_replan`；
- exact `V_continue`；
- exact `Δ_t`。

先不训练模型。

画：

1. `Δ_t` 分布；
2. 不同 horizon 的 `Δ_t`；
3. 不同 commitment length 的 `Δ_t`；
4. public-observation 相同组内 `Δ_t` 方差；
5. replan top-K oracle frontier：
   - 如果只允许 K 次 planning；
   - oracle 把 budget 用在最大 `Δ_t` 的时点；
   - 与 periodic/random 的差距。

### A2 Kill Gate

如果：

- 绝大部分 `Δ_t≈0`；
- 或 periodic 已几乎等同 oracle；
- 或 hidden commitment 对 `Δ_t` 没有可测影响；

则 CARP 的研究动机很弱，标记 `A_WEAK`。

---

# A3. 第二组实验：最小 adaptive gate

目的不是发明网络，而是证明 research signal。

Baseline：

1. Always Plan
2. Never Plan
3. Fixed Periodic
4. Random-K
5. Uncertainty/entropy trigger
6. Myopic immediate-reward trigger
7. Oracle top-K（上界，不可部署）

Candidate gate：

- Logistic regression
- Gradient boosted trees
- 小型 MLP（二层即可）

输入版本：

- **A-public**：只有公开 observation feature；
- **A-history**：公开 history summary；
- **A-belief**：public + commitment belief statistic。

禁止一开始做 Transformer。

### 主要指标

规划节省率：

\[
Saving = 1-\frac{N_{\text{plan,candidate}}}{N_{\text{plan,always}}}
\]

价值保留率建议主指标：

\[
Retention =
\frac{V_{\text{candidate}}-V_{\text{never}}}
{V_{\text{always}}-V_{\text{never}}}
\]

另报：

- raw game value；
- regret vs always-plan；
- calls per episode；
- `Δ_t` prediction AUROC / calibration；
- value-vs-compute Pareto curve。

### A3 Discovery 正信号标准

至少出现一条非 oracle candidate：

- `Saving ≥ 30%`
- 且 `Retention ≥ 95%`

并且在不同 game families 都成立，而不是只靠一个 family。

这不是最终论文门，只是进入 A4 的门。

---

# A4. 第三组实验：certificate feasibility

## A4.1 候选界

本地 AI 可尝试以下三类，但不得声称有效，必须穷举验证：

### Bound-0：Trivial remaining-payoff range
仅作为下限 baseline，理论上应非常松。

### Bound-1：Local continuation deficit
对“继续当前 block”与“立即 replan”的局部 continuation difference 给上界。

### Bound-2：Compatible-history / path-consistent deficit
借鉴已有论文的 compatible-history 思路，但这里是**在线 adaptive gating**，不是旧的 fixed calendar。

本地 AI 的任务不是证明 theorem，而是：

1. 写清数学定义；
2. 在所有 exact small games 上 exhaustive check；
3. 自动搜索 counterexample；
4. 一旦违反，保留 counterexample；
5. 只有 0 violation 才进入下一步人工理论审查。

### 主要指标

- Validity violation count：必须为 0 才能继续；
- bound / true loss 比值；
- median tightness；
- 90/95 percentile tightness；
- trivial bound 相比候选 bound 的改善；
- certificate 是否经常为 vacuous。

### A4 Gate

“非空洞”最低要求：

- 0 observed violation；
- median `bound / true_loss` 不应大到完全无意义；
- 相对 trivial bound 有稳定收紧；
- 在真正 `Δ_t` 大的状态也不能全部失效。

如果 certificate 只能在 easy states 紧，在关键 states 全部 vacuous，则记 `A_CERT_WEAK`。

---

# A5. Iron Bottom Sound 最小迁移实验

M0 **不要求完整解决 IBS**。

优先使用：

- simulator-generated matches；
- `IBS-S-01`
- `IBS-S-03`
- `IBS-S-EM-01`（若仓库当前可用）

禁止使用真人对局数据。

### 实验目标

只回答：

> CARP 在真实复杂状态中有没有同样的“什么时候值得重算”信号？

优先级：

1. 鱼雷决策；
2. realistic-command 编队移动；
3. 炮击目标分配。

选择一个最容易做 counterfactual continuation 的子问题，不要三个都做。

### 如果完整 continuation clone 很难

允许构造 **IBS micro-scenario**：

- 从真实 scenario/snapshot 抽取一个局部状态；
- 保留引擎合法动作与裁决；
- 限制 1–2 个决策阶段；
- 对候选行动跑多 seed rollouts；
- 得到 empirical continuation value。

不得为 M0 重写整个 simulator。

### A 最终 PASS 条件

CARP 标记 `PASS` 至少要求：

1. exact lab 中存在清晰 compute-value frontier；
2. adaptive gate 在 confirmatory games 达到约：
   - `≥30%` planning saving；
   - `≥95%` normalized retention；
3. belief/history 至少有一个明显优于 snapshot-only；
4. certificate 候选在 exhaustive small games 中无反例且不完全 vacuous；
5. IBS micro-domain 至少复现“replanning value 随状态显著变化”的现象。

若 1–3 成立、4 不成立：

- 标记 `A_PASS_NO_CERT`
- 可保留为 adaptive planning 方向，但不能使用 “Certified” 作为主 claim。

---

# 6. Track B：CAIS 验证计划

# B0. 要验证的核心猜想

### H-B1
由于 hidden pending commitment：

\[
o(h)=o(h')
\]

并不意味着：

\[
Q^*(h,\cdot)\approx Q^*(h',\cdot)
\]

存在显著 public-state aliasing。

### H-B2
一个 commitment-aware belief representation 可显著减少 continuation ambiguity。

### H-B3
可以通过 counterexample-guided state refinement，用远少于完整 history 的状态维度达到接近 continuation-sufficient 的表示。

---

# B1. Exact aliasing census

在 exact-game pool 中对所有 reachable histories：

按 public observation 分组。

对每组计算：

\[
AliasGap(z)=
\max_{h,h':\phi(h)=\phi(h')}
\max_a
|Q^*(h,a)-Q^*(h',a)|
\]

同时计算：

- optimal-action disagreement rate；
- value disagreement；
- hidden commitment distribution；
- history length；
- commitment length。

输出：

- aliasing rate；
- AliasGap 分布；
- 最大 50 个 counterexamples。

### Negative control

对没有 pending commitment 的 Markov/control games 做同样实验。

如果 control 与 sealed games 的 aliasing 差不多，说明机制不特异，必须调查。

---

# B2. Representation ablation

比较：

### R0 Public Snapshot
仅当前公开 observation。

### R1 Finite History
最近 k 个 observation/action summary，`k=1,2,4`。

### R2 Recurrent Baseline
小 GRU/LSTM，可选，规模要小。

### R3 Commitment Belief
显式维护：

\[
b_t(c)=P(c_t=c\mid h_t)
\]

或它的低维统计量。

### R4 Oracle Hidden Commitment
直接给真实 hidden commitment。
只作 upper bound，不能作为可部署方法。

任务：

- continuation value prediction；
- best-action prediction；
- policy regret。

### 主要指标

- Q MSE / MAE；
- optimal-action accuracy；
- induced policy regret；
- worst-case / 95p continuation error；
- representation size；
- history compression ratio。

### B2 正信号

理想结构：

`R0 << R1/R2 < R3 ≈ R4`

尤其重要：

> R3 必须不仅比 snapshot 强，还要在相似参数量/输入预算下明显优于 generic history model。

否则“commitment-aware”没有贡献。

---

# B3. Counterexample-Guided State Refinement

实现最简 CEGIS-like prototype：

1. 初始 representation 只用 public state；
2. 在同一 representation cell 中搜索最大 `Q*` divergence 的 history pair；
3. 若 divergence > ε：
   - 保存 counterexample；
   - 找到一个可由 observation history 推断的 split feature；
   - refinement；
4. 重复直到：
   - 无 counterexample；
   - 或达到 size budget。

记录：

- 每轮 counterexample；
- state count；
- max continuation gap；
- policy regret；
- 与 full-history state count 的比值。

**禁止使用真实 hidden commitment 作为最终 split feature。**
它只能用于 oracle 分析和发现反例。

### B3 Gate

若 refinement：

- 用远少于 full history 的 states；
- 把 max/95p continuation gap 显著压低；
- 且策略 regret 同时下降；

则是强正结果。

---

# B4. Iron Bottom Sound aliasing probe

先审计仓库实际 sealed-order representation。

必须明确回答：

- 哪些字段是本方看不到的敌方 pending order？
- 它们在什么阶段跨 epoch 存在？
- 哪些 observation 完全相同但 future continuation 可不同？

优先做研究用 counterfactual clone：

- 相同 public state；
- 改变一个合法 hidden pending commitment；
- 不改变公开 observation；
- 从该 state forward resolve；
- 测 continuation value / best action 是否改变。

若没有安全的 clone 接口，先做 micro-scenario，不改生产引擎。

### B PASS 条件

至少要求：

1. exact games 出现稳定而非罕见的 aliasing；
2. R3 commitment belief 收回：
   - 至少 50% 的 R0→R4 regret gap；
3. counterexample refinement 比 full-history 表示明显更压缩；
4. IBS 中找到至少一类自然存在的 sealed-order counterexample。

若只在人工 toy witness 中出现，记 `B_TOY_ONLY`。

---

# 7. Track C：Certificate-Directed PSRO 验证计划

# C0. 核心猜想

已有 PSRO 的主要成本来自：

> 每个 empirical payoff cell 都需要大量 noisy simulator matches。

猜想：

> equilibrium value / exploitability 的不确定性主要由少数 payoff cells 主导；主动选择下一次 rollout 可以更快得到足够窄的 meta-game certificate。

---

# C1. 数据与策略池

数据全部由 Iron Bottom Sound simulator 生成。

本地 AI 必须从当前仓库动态读取实际策略集合，不硬编码旧名字。

候选来源：

- `PROFILES`
- `CHAMPIONS`
- PSRO 已注册策略
- torpedo doctrine profiles

选择：

- 6–12 个策略；
- 至少两个 scenario；
- 若 realistic scenario 性能允许，加入第三个。

M0 首版 utility 使用简单有界零和值：

- win = +1
- draw = 0
- loss = -1

不要一开始加入复杂 VP shaping。

invalid match 单独报告，不当作 loss 静默塞进 payoff。

---

# C2. 构建有置信区间的 payoff matrix

对每个 cell：

\[
M_{ij}\in[L_{ij},U_{ij}]
\]

首版优先使用容易验证的 simultaneous confidence bound：

- Hoeffding + union correction；
- 或 anytime-valid confidence sequence。

不要为了更紧先引入复杂统计方法。

用：

\[
v_L = v(L),\quad v_U=v(U)
\]

作为 zero-sum game value 的保守 bracket。

同时对当前 meta-strategy 计算 conservative best-response / exploitability interval。

必须写单元测试：

- 真矩阵已知的 synthetic normal-form games；
- interval shrinking 单调；
- 覆盖率 Monte Carlo 检查；
- widening 一个 cell 不得使总 uncertainty 错误变小。

---

# C3. Sampling Baselines

至少：

1. Uniform round-robin
2. Largest cell CI width
3. Variance-aware sampling
4. Current-support weighted width
5. Candidate：certificate sensitivity / estimated value-of-information

Candidate 可以先很简单：

> 试探如果 cell `(i,j)` 的 CI 缩窄一半，对 `v_U-v_L` 的最大可能改善是多少？

不需要一开始做神经 acquisition。

---

# C4. Primary endpoint

主要比较：

> 达到给定 meta-game uncertainty 阈值需要多少 simulator games。

例如：

\[
v_U-v_L \le 0.10
\]

并记录：

- 总 games；
- wall clock；
- matrix coverage；
- support coverage；
- exploitability UB；
- 不同 seeds 的方差。

画：

`certificate width vs number of simulated matches`

而不是只画胜率。

---

# C5. Confirmatory Gate

`C_PASS` 建议要求：

- 相比 uniform：
  - 达到相同 certificate width 的 simulator games 减少 **≥40%**
  - 或至少达到约 **2× sample efficiency** 的某个稳定区间；
- 在至少 2 个 scenario、5 个随机重复中方向一致；
- 不是因为漏采某些高方差 cell 导致错误自信；
- simultaneous coverage audit 无明显失败。

若有效但只节省 10–20%，标 `C_SMALL_EFFECT`。

---

# C6. Novelty Gate

即使实验通过，Track C 也不能自动升主线。

本地 AI 必须做 `C_LITERATURE_MATRIX.md`，至少核查：

- PSRO
- rectified / diverse PSRO variants
- JBR / experience reuse
- empirical game-theoretic analysis progressive sampling
- confidence-bound / adaptive payoff estimation
- population exploitability optimization

每篇写：

- 研究对象；
- 是否自适应选择 payoff cell；
- 是否给 equilibrium/exploitability certificate；
- 是否 joint population expansion；
- 与本方案重叠点。

若“certificate-directed adaptive cell sampling”已有高度同构工作，则 Track C 只能做备线/模块。

---

# 8. Track D：DiagGame / B2-X 验证计划

# D0. 核心猜想

不是“生成更难的游戏”。

真正要验证：

> 一个自动 experimental-design 系统，能否用比随机 benchmark 少得多的测试，识别 agent 的具体战略推理缺陷？

---

# D1. 构造已知 defect 的 agent zoo

Exact Strategic Lab 中实现：

1. **Optimal**
2. **Myopic**：只看即时收益或短 horizon
3. **No-Opponent-Model**
4. **No-Belief-Update**
5. **Commitment-Forgetful**
6. 可选 **Risk-Distorted**

这些 agent 的缺陷是人工定义的 ground truth。

必须保证它们不是简单“强弱排序”，而是不同机制缺陷。

---

# D2. Game DSL 参数

至少允许改变：

- horizon；
- hidden signal；
- commitment length；
- delayed reward；
- opponent response strength；
- risk/chance；
- action branching；
- information asymmetry。

定义 game complexity/edit distance。

---

# D3. 三类 test-selection 方法

Baseline：

1. Random generated games
2. Hardest-game / max-regret game
3. Max action-disagreement game

Candidate：

4. Information gain / mechanism identifiability
5. Minimal strategic contrast pair synthesis

Contrast pair 要求：

- 两个 game 参数尽可能接近；
- oracle optimal action 发生有意义变化；
- 某一个 defect agent 对关键变量不敏感。

---

# D4. 主要任务：agent type identification

给 evaluator 一个未知 agent type `Z`。

每轮选择一个 game `G_t`，观察 agent action。

目标：

> 用最少 queries 识别 Z。

指标：

- identification accuracy vs number of tests；
- tests to 90% posterior confidence；
- confusion matrix；
- robustness to ε-rational action noise；
- average edit distance / complexity；
- 失败模式可解释性。

---

# D5. PASS Gate

`D_PASS` 至少要求：

- 在 confirmatory unseen games / noisy agents 上：
  - 固定 test budget 下比 random 提升 ≥20 percentage points；
  - 或达到同等 identification accuracy 所需 tests 减少约 2×；
- 不只是识别“optimal vs bad”，而是真正区分至少 4 种 defect；
- minimal contrast pair 的改动确实小且可解释。

只有通过这个 gate，才允许下一阶段接真实 LLM。

M0 不跑 GPT/Claude API。

可选 local model pilot 只能作为 appendix-style signal，不决定 PASS/FAIL。

---

# 9. 四方向共享的 Confirmatory Protocol

Discovery 跑完后，先生成：

`DISCOVERY_FREEZE.md`

其中冻结：

- 每方向主假设；
- 最终 metrics；
- baseline；
- 阈值；
- generator parameters；
- confirmatory seeds；
- 不允许再调的超参。

然后才跑 confirmatory。

## Confirmatory 禁止事项

- 看到结果后换 primary metric；
- 删掉“不好看”的 scenario；
- 改 seed；
- 只报表现最好的模型；
- 把失败 replicate 当异常删掉；
- 临时改变 PASS threshold。

任何改动必须：

1. 标记为 `POST_HOC`；
2. 与 frozen primary analysis 分开。

---

# 10. 决策树

本地 AI 不做最终选题，只走如下门控并输出证据。

```text
START
  |
  +--> P0 仓库/基线可复现？
  |       |
  |       +-- NO --> STOP，先修基础设施
  |       |
  |       +-- YES
  |
  +--> P1 Exact Lab 正确？
          |
          +-- NO --> STOP，不允许继续
          |
          +-- YES
                |
                +--> Track A CARP
                |      |
                |      +-- compute-value signal 不存在 --> A_FAIL
                |      |
                |      +-- signal 存在
                |             |
                |             +-- adaptive gate confirm PASS?
                |                    |
                |                    +-- NO --> A_FAIL/AMBIG
                |                    |
                |                    +-- YES
                |                           |
                |                           +-- certificate 非空洞且无反例?
                |                                  |
                |                                  +-- YES --> A_PASS
                |                                  +-- NO  --> A_PASS_NO_CERT
                |
                +--> Track B CAIS
                |      |
                |      +-- aliasing 不显著 --> B_FAIL
                |      |
                |      +-- aliasing 显著
                |             |
                |             +-- belief/refinement 明显修复?
                |                    |
                |                    +-- YES + IBS例 --> B_PASS
                |                    +-- 仅toy --> B_TOY_ONLY
                |
                +--> Track C CD-PSRO
                |      |
                |      +-- sample efficiency < 40% improvement --> C_FAIL/SMALL
                |      |
                |      +-- >=40% 且 coverage 正确
                |             |
                |             +-- novelty matrix 安全 --> C_PASS
                |             +-- prior高度重合 --> C_EMPIRICAL_ONLY
                |
                +--> Track D DiagGame
                       |
                       +-- 无法识别机制类型 --> D_FAIL
                       |
                       +-- >=2x query efficiency / >=20pp accuracy
                              |
                              +-- minimal contrast 可解释 --> D_PASS
                              +-- 只是难度筛选 --> D_FAIL
```

---

# 11. 多方向都 PASS 时如何处理

**本地 AI 不自行合并论文。**

只生成 `DIRECTION_SCORECARD.md`，每方向报告：

- Effect size
- Confirmatory stability
- Theory opportunity
- Novelty risk
- Engineering cost
- Dependence on Iron Bottom Sound
- Generalization beyond IBS
- Required compute
- Closest prior work overlap
- Biggest unresolved risk

PI 再决定。

特别注意：

- A 与 B 若同时强，可以后续考虑：
  - A = 主问题；
  - B = information-state module。
- 但 M0 不允许主动 scope creep，把两条主线强行拼成一篇。

---

# 12. 数据来源清单

## 12.1 Iron Bottom Sound

只使用当前仓库生成：

- scenarios；
- simulator rollouts；
- snapshots；
- events；
- state export；
- AI-vs-AI matches；
- PSRO payoff samples。

优先 scenario：

- 当前仓库实际存在并可自动终局的 scenario；
- 预期包括 S-01、S-03、EM 类扩展，但必须以仓库审计为准。

## 12.2 Synthetic exact games

全部自行程序生成。

这是 A/B/D 的主要真值源。

## 12.3 Standard benchmark（M0 可选）

如环境安装顺利，可加入 OpenSpiel：

- Kuhn Poker
- Leduc Poker
- Goofspiel
- 一个 simultaneous-move 小游戏

目的只做 sanity/generalization，不允许因为 OpenSpiel 安装问题拖死 M0。

## 12.4 不使用

- 未授权人类对局；
- 付费 LLM API 数据；
- 网络上来源不清的数据集；
- 大规模预训练模型作为主要结果来源。

---

# 13. 文献核查任务

每方向必须有一个 `LITERATURE_MATRIX.md`。

优先核查：

### Adaptive planning / test-time compute
- *Learning When to Plan: Efficiently Allocating Test-Time Compute for LLM Agents* — arXiv:2509.03581

### Imperfect-information look-ahead / world model
- *LAMIR / Look-Ahead Reasoning with a Learned Model in Imperfect Information Games* — ICLR 2026
- *NashDreamer: Model-Based Reinforcement Learning for Zero-Sum Imperfect-Information Games* — arXiv:2609.01549

### Information-set representation
- *No-Regret Strategy Solving in Imperfect-Information Games via Pre-Trained Embedding* — AAAI 2026

### Strategic evaluation / game generation
- *GENSTRAT: Toward a Science of Strategic Reasoning in Large Language Models* — arXiv:2605.23238
- *Level-k Distinguishable Mechanisms for Evaluating Bounded Rationality in LLMs* — arXiv:2608.21296

### Game solving
- Deep / predictive discounted CFR 系列
- PSRO 与 empirical game-theoretic analysis
- progressive / adaptive simulation sampling

每篇只回答：

1. 它解决什么问题？
2. 它的 formal object 是什么？
3. 它是否已经做了我们的核心 claim？
4. 我们真正剩下的 novelty 是什么？
5. 如果 reviewer 引用它，最危险的质疑是什么？

---

# 14. 统一统计与图表要求

每个核心结果：

- 至少 5 个随机重复（若 exact deterministic 则说明无需）；
- 报 mean / median；
- 报标准差或 bootstrap CI；
- 画 individual seed points；
- 禁止只有 bar chart。

至少生成：

1. compute/value Pareto curve（A）
2. certificate tightness CDF/scatter（A）
3. alias gap distribution（B）
4. representation regret comparison（B）
5. certificate width vs simulation budget（C）
6. identification accuracy vs query budget（D）
7. 每方向失败/反例图至少一张

图必须由脚本自动生成。

---

# 15. 实验注册表

建立：

`research/m0/EXPERIMENT_REGISTRY.csv`

字段：

```text
experiment_id
track
hypothesis
status
commit
start_time
end_time
machine
seed_group
dataset_or_scenario
method
baseline
primary_metric
secondary_metrics
predeclared_threshold
result
pass_fail
artifact_path
notes
```

任何结果只有进入 registry 才能用于最终报告。

---

# 16. 结果包结构

最终给 PI 的压缩包：

`M0_STRATEGIC_AI_VALIDATION_BUNDLE.zip`

建议 ≤100–150MB。

必须包含：

```text
M0_STRATEGIC_AI_VALIDATION_BUNDLE/
│
├─ 00_README.md
├─ 01_EXECUTIVE_SUMMARY.md
├─ 02_AUDIT.md
├─ 03_DISCOVERY_FREEZE.md
├─ 04_DIRECTION_SCORECARD.md
├─ 05_DECISION_EVIDENCE.md
├─ EXPERIMENT_REGISTRY.csv
├─ CLAIM_EVIDENCE_MATRIX.csv
├─ FAILURES_AND_COUNTEREXAMPLES.md
├─ OPEN_QUESTIONS.md
├─ git_info.txt
├─ environment.txt
│
├─ track_A_carp/
│  ├─ HYPOTHESES.md
│  ├─ METHODS.md
│  ├─ RESULTS.md
│  ├─ metrics.csv
│  ├─ counterexamples/
│  └─ figures/
│
├─ track_B_cais/
│  ├─ HYPOTHESES.md
│  ├─ METHODS.md
│  ├─ RESULTS.md
│  ├─ alias_pairs.csv
│  ├─ counterexamples/
│  └─ figures/
│
├─ track_C_cdpsro/
│  ├─ HYPOTHESES.md
│  ├─ METHODS.md
│  ├─ RESULTS.md
│  ├─ payoff_summary.csv
│  ├─ coverage_audit.csv
│  └─ figures/
│
├─ track_D_diaggame/
│  ├─ HYPOTHESES.md
│  ├─ METHODS.md
│  ├─ RESULTS.md
│  ├─ synthesized_games.jsonl
│  ├─ identification.csv
│  └─ figures/
│
├─ literature/
│  ├─ A_LITERATURE_MATRIX.md
│  ├─ B_LITERATURE_MATRIX.md
│  ├─ C_LITERATURE_MATRIX.md
│  └─ D_LITERATURE_MATRIX.md
│
├─ code/
│  ├─ research_m0.patch
│  ├─ reproduce_smoke.ps1
│  ├─ reproduce_confirmatory.ps1
│  └─ TREE.txt
│
└─ raw_small/
   └─ 仅放关键的小型原始数据
```

---

# 17. 不要打包的内容

不要包含：

- `.venv`
- `node_modules`
- 完整 Git 仓库
- 数 GB 原始 replay
- 模型 cache
- API key
- 用户隐私数据
- 可重新生成的大型中间文件

大文件只在：

`DATA_MANIFEST.md`

记录：

- 路径；
- SHA256；
- 生成命令；
- 大小；
- 是否必须保留。

---

# 18. `01_EXECUTIVE_SUMMARY.md` 必须回答的 12 个问题

本地 AI 最终必须逐条回答：

1. P0 基础设施是否可信？
2. Track A 是否存在 compute-value tradeoff？
3. Track A 是否有 confirmatory adaptive replanning 正结果？
4. Track A certificate 是否发现反例？
5. Track B public-state aliasing 有多严重？
6. commitment belief 是否真正修复它？
7. Track C 自适应采样节省多少 simulator calls？
8. Track C confidence coverage 是否正确？
9. Track D 能否区分机制缺陷而非强弱？
10. 四方向各自最大的 reviewer attack 是什么？
11. 哪些结果是 discovery，哪些是 frozen confirmatory？
12. 哪些方向是 `PASS / FAIL / AMBIGUOUS`？为什么？

不要写宣传语。

---

# 19. `CLAIM_EVIDENCE_MATRIX.csv`

每个潜在论文 claim 一行：

```text
claim_id
track
claim_text
evidence_type
experiment_ids
supports_claim
counterevidence
scope_limit
status
```

例如：

```text
A-C1
A
Adaptive replanning reduces planning calls while retaining strategic value
confirmatory
A-CONF-001..005
yes
fails at horizon=6 high-noise family
exact synthetic games only
SUPPORTED_WITH_SCOPE
```

这会直接用于下一轮 PI 决策。

---

# 20. 本地 AI 主提示词

把下面整段作为新本地 AI 的第一条系统级任务说明。

---

## MASTER PROMPT

你现在是一个**科研执行工程师**，不是课题负责人。

项目：`fuxiaoji/iron-bottom-sound`

总体目标：为一篇以 CCF-A 为目标的 Game AI / multi-agent / imperfect-information research 工作做 **M0 多主线可行性验证**。

科研方向、假设、验收门由上级 PI 给定。你的职责是：

1. 审计当前仓库；
2. 保持原规则引擎语义不变；
3. 实现最小研究实验；
4. 运行可复现实验；
5. 主动寻找反例；
6. 如实记录正结果与负结果；
7. 最终打包证据供 PI 决策。

你**不允许**：

- 擅自改变研究主线；
- 为得到正结果改 primary metric；
- 删除失败 seed；
- 只展示最佳超参；
- 把 post-hoc 结果冒充预注册结果；
- 静默修改引擎裁决；
- 使用真人未授权数据；
- 调用付费 LLM API；
- reset/clean 用户工作区；
- 在没有 exact 验证时把 heuristic 称为 certificate；
- 在发现 certificate 反例后通过 clipping 等方式掩盖。

### 第一步

执行只读审计：

- `git status --short`
- 当前 HEAD / branch
- Python / Node / CUDA / CPU / RAM
- tests
- repository tree
- 可用 scenarios
- AI profiles
- PSRO status
- snapshots / replay / state export
- sealed/pending orders
- legal actions / observation APIs

如果工作树不干净，禁止覆盖。创建独立 research worktree/branch。

所有研究代码放在 `research/m0/`，除非必须调用现有模块。

完成 P0 后，写 `research/m0/AUDIT.md`。只有基础测试通过，才进入 P1。

### 科学纪律

每条主线采用：

`Hypothesis -> Minimal falsification experiment -> Discovery -> Freeze -> Confirmatory -> PASS/FAIL/AMBIGUOUS`

而不是：

`写大系统 -> 跑到有好结果为止`

遇到不符合预期的结果优先怀疑：

- 假设错误；
- metric 设计错误；
- data leakage；
- simulator bug；
- hidden confound；

不要第一反应调参。

完整执行计划见本目录的 M0 research plan。

最终输出 `M0_STRATEGIC_AI_VALIDATION_BUNDLE.zip`。

---

# 21. 分阶段提示词

## PROMPT P0 — 仓库审计

> 阅读整个 `research plan`。现在只执行 P0，不做任何新算法。审计当前仓库的科研基础设施：确定 deterministic replay、run_match、bench、PSRO、TacticalCommander、AdaptiveTorpedoPlanner、sealed/pending orders、observe/legal_actions、snapshots/events、自定义 scenario 的实际状态。运行最小 smoke tests。记录任何与计划描述不一致的地方。不要修改规则。完成后输出 `AUDIT.md`、`BASELINE_STATUS.md`、`TREE.txt` 和测试日志，并停止等待下一步。

---

## PROMPT P1 — Exact Strategic Lab

> 现在实现共用 Exact Strategic Lab，只服务 Track A/B/D。建立有限两人零和 extensive-form 小游戏 DSL，支持 public observation、private pending commitment、path-dependent payoff 和 exact continuation solve。先复现一个 public-state insufficiency 的最小 witness，再实现随机 game generator。所有 solver 结果必须能被 brute-force 交叉验证。生成 discovery/confirmatory 两套不同 seed 的 game families。完成后运行单元测试并停止，不进入四方向实验。

---

## PROMPT A — CARP

> 只执行 Track A。先在 Exact Lab 计算每个 decision state 的 exact replanning value `Δ_t`，不要先训练模型。验证 compute-value tradeoff 是否存在。若不存在，直接记录 A_FAIL。若存在，再实现 Always/Never/Periodic/Random/Entropy/Oracle baselines 和最小 adaptive gate。冻结 discovery 后跑 confirmatory。然后测试 candidate certificate，主动穷举搜索反例；发现反例立即保留并标 invalid，不得修饰。最后只做一个 Iron Bottom Sound micro-domain transfer，不得重写完整引擎。输出 Track A 的 HYPOTHESES/METHODS/RESULTS/figures/counterexamples，并停止。

---

## PROMPT B — CAIS

> 只执行 Track B。先做 public-observation aliasing census，比较 sealed-commitment games 与 Markov controls。然后比较 snapshot、finite-history、small recurrent、commitment-belief、oracle-hidden representation。主指标是 induced policy regret 和 continuation-value error，不以 representation accuracy 代替。若 commitment belief 没有明显优于 generic history baseline，标记为弱结果。随后实现最小 counterexample-guided state refinement，严禁将真实 hidden commitment 作为可部署 feature。最后在 Iron Bottom Sound 中寻找一个自然 sealed-order aliasing micro-case。输出完整反例与负结果。

---

## PROMPT C — CD-PSRO

> 只执行 Track C。复用当前 simulator 和策略池。先用 win/draw/loss 构建有 simultaneous confidence intervals 的 empirical payoff matrix，验证 coverage 后再实现 adaptive sampling。至少比较 uniform、largest-width、variance-aware、support-weighted 与 candidate certificate-sensitivity acquisition。主指标是达到固定 game-value/exploitability certificate width 所需 simulator games。必须做多 seed confirmatory 与 coverage audit。实验通过后再做 closest-prior literature matrix，判断是不是已有同构方法。不要因为代码里已有 PSRO 就默认该方向有论文创新。

---

## PROMPT D — DiagGame

> 只执行 Track D。不要调用真实 LLM。构造已知 latent defect 的策略 agent zoo：optimal、myopic、no-opponent-model、no-belief-update、commitment-forgetful 等。实现 procedural game generator，比较 random/hardest/disagreement/information-gain/minimal-contrast test selection。任务是用最少 queries 识别 agent type。若方法只能区分“强/弱”而不能区分机制缺陷，则判失败。confirmatory 加入 action noise。只有达到明显 query-efficiency 提升后，才保留为候选主线。

---

## PROMPT FINAL — 冻结与打包

> 四方向 discovery 完成后，先生成 `DISCOVERY_FREEZE.md`，冻结每方向的 primary metrics、阈值、confirmatory seeds 和算法版本。之后只运行 frozen confirmatory，不再调参。完成后生成方向 scorecard、claim-evidence matrix、failures/counterexamples、open questions。所有结论必须标记 PASS/FAIL/AMBIGUOUS，并说明证据范围。不要自行决定最终论文主线。将必要代码 patch、复现脚本、聚合数据、关键原始样本、图表、日志和环境信息打包为 `M0_STRATEGIC_AI_VALIDATION_BUNDLE.zip`，排除大 cache/venv/node_modules/API keys。

---

# 22. PI 回收结果后的下一轮决策

当 PI 收到结果包后，将按以下顺序审查：

1. **Correctness**
   - exact solver 是否正确；
   - simulator 是否被研究代码污染；
   - certificate 是否有反例；
   - confidence coverage 是否可信。

2. **Effect size**
   - 是否是真实、稳定、可重复的正结果；
   - 是否只靠一个 scenario/seed。

3. **Novelty**
   - 与最新工作实际差异；
   - 是否可以形成一个明确 formal problem。

4. **Generalization**
   - 是否脱离 Iron Bottom Sound 后仍成立。

5. **Paperability**
   - 是否可以在 6–10 页主文中形成单一清晰故事；
   - 是否需要不可承受的大规模训练。

6. **CCF-A readiness**
   - 是否有算法贡献；
   - 是否有 formal property；
   - 是否有标准 benchmark；
   - 是否有高复杂度 domain；
   - 是否有完整 ablation 与 failure analysis。

只有通过这一轮，才进入 M1 正式科研计划。

---

# 23. M0 的真正成功标准

M0 最理想的结果不是“四条都很好”。

理想结果是类似：

```text
A: PASS
   adaptive gate 省 42% planning calls，retention 97%
   candidate certificate exact small games 无反例
   IBS micro-case 有相同趋势

B: PASS / MODULE
   public-state aliasing 强
   commitment belief 收回 68% oracle gap
   适合作为 A 的状态模块，而非独立论文

C: SMALL_EFFECT
   仅节省 18% simulation，停止

D: FAIL
   只能区分强弱，不能稳定识别 defect，停止
```

或者完全不同。

**只要最终能用硬证据杀掉错误方向，M0 就是成功。**

M0 不允许得到：

> “四个方向都挺有希望，建议继续研究。”

这种结果等同于失败。

---

# 24. 给执行 AI 的最后一句话

你的工作不是证明 PI 的猜想是对的。

你的工作是：

> **尽可能快、尽可能严格地证明它们哪里错；只有经得住主动反驳和冻结复验的方向，才允许进入下一阶段。**
