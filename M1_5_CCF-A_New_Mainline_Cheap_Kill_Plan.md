# M1.5：CCF-A 新主线双轨 Cheap-Kill 计划
## Selective Opponent Reasoning vs. Strategic Influence Planning

**项目**：`fuxiaoji/iron-bottom-sound`  
**阶段**：M1.5 — 新主线快速筛选  
**目标**：在 3–5 天内，从两个新方向中筛出 1 条真正值得进入 CCF-A 论文阶段的主线；如果两条都失败，就停止围绕 hidden commitment 继续挖题。  
**执行角色**：
- **PI / 科研总负责人**：提出问题、设定门槛、审阅结果、决定最终主线。
- **本地 AI / 实验执行者**：实现实验、运行、记录失败、打包证据；不得自行改研究问题或降低门槛。
- **用户**：提供机器和仓库，将 checkpoint 交回 PI。

---

# 0. 背景：为什么重新开两条新线

M0/M1 已经帮助排除了四条原主线：

- A / CARP：replanning signal 存在，但简单 periodic baseline 已经很强；
- B / CAIS/B*：hidden commitment 确实改变未来，但在真实 IBS 中自然产生强 decision aliasing 的密度不足；
- C / CD-PSRO：一个 regime 节省很大，另一个 regime 发生 starvation/failure；
- D / DiagGame：当前 game family 对部分 latent defect 根本不可识别。

最重要的新现象：

> hidden commitment 经常改变未来 value，但多数时候并不迫使当前最佳 action 改变。

因此 M1.5 改为验证两个更贴近 Game AI / Multi-Agent AI 的方向：

1. **E1 — Selective Opponent Reasoning / Strategic Irrelevance**
2. **E2 — Strategic Influence Planning**

这两条都必须先做 cheap-kill，不允许直接上大模型或 RL。

---

# 1. Track E1 — Selective Opponent Reasoning
## Learning When Opponent Reasoning Matters

### 1.1 核心问题

在部分可观测对抗中，agent 不一定每一步都需要精确建模对手。

若多个可能 hidden commitments 下存在一个共同的安全行动，那么昂贵 opponent model / search 是浪费。

定义：

\[
\rho(s)=
\min_a
\max_{c\in\mathcal C(s)}
\left[V_c-Q_c(a)\right]
\]

其中：

- `s`：agent 当前可见信息状态；
- `c`：与该信息状态一致的可能隐藏 commitment；
- `V_c = max_a Q_c(a)`；
- `rho(s)`：不知道真实 hidden commitment 时，强行使用一个共享 action 的最小 worst-case regret。

解释：

- `rho(s) ≈ 0`：**对手具体隐藏计划暂时不重要**；
- `rho(s)` 大：**不知道对手会导致当前决策错误**。

目标不是“预测对手是什么”，而是：

> 先判断现在是否值得花算力预测对手。

---

# 2. E1 要验证的三个核心猜想

## H-E1.1：Strategic criticality 稀疏但重要

希望看到：

```text
大量状态 rho ≈ 0
少量状态 rho 很高
```

即：

> 大多数时候不用深度 opponent reasoning，少数时候不用会付出明显损失。

这是 Selective Reasoning 成立的必要条件。

---

## H-E1.2：criticality 可从 agent 可见信息预测

使用只允许 agent 看到的 features，预测：

```text
high-rho vs low-rho
```

如果完全不可预测，那么在线 gating 没有现实意义。

---

## H-E1.3：Selective reasoning 具有 compute-value 优势

比较：

- Always Reason
- Never Reason
- Random Budget
- Periodic
- Entropy / uncertainty trigger
- Generic planning trigger
- Ours: strategic-criticality gate

希望：

```text
显著减少 expensive reasoner calls
同时接近 Always Reason 的 game value
```

---

# 3. E1 数据来源

## 3.1 首先复用 M1 G1 数据

不要重新跑 35k rollouts。

读取现有：

- `M1_G1_CHECKPOINT`
- pair validation
- Q tables
- public observations
- hidden commitments
- strong cases
- control pairs

重新计算：

- absolute shared-action regret；
- normalized regret；
- stake；
- action disagreement；
- value divergence；
- confidence flag。

注意：

**不要继承旧 F6“candidate set 扩大只会让 R 下降”的错误单调性结论。**

---

## 3.2 Exact Strategic Lab

为 E1 增加一个可 exact solve 的 benchmark。

需要支持：

- hidden opponent type / commitment；
- cheap action；
- expensive opponent-aware solve；
- exact `rho(s)`；
- exact full-information best response。

用于验证：

> Selective reasoning 本身是否真的成立，而不被 IBS rollout noise 污染。

---

# 4. E1 Cheap Test 1：rho 分布

对已有 G1 pair/state 计算：

```text
rho_abs
rho_norm
stake
value_divergence
action_disagreement
```

必须画：

1. `rho_abs` histogram / CDF
2. `rho_norm` histogram / CDF
3. stake vs rho
4. value divergence vs rho
5. action disagreement vs rho
6. scenario-conditioned distributions

### E1-T1 PASS

至少满足：

- ≥50% 状态 `rho` 很低；
- ≥10% 状态有明显高 regret；
- 高-rho 状态的 absolute stake 不能全部接近 0；
- 不是 normalized-regret 分母过小造成的假高值。

建议高值门：

```text
absolute regret >= meaningful stake floor
AND normalized regret >= 0.10
```

stake floor 要根据数据分布预注册，不能看完结果再挑。

如果：
- 所有 rho 都低 → 无需 selective；
- 所有 rho 都高 → 应该 always reason；
- 高 rho 只由 tiny stake 产生 → 假信号；

则 `E1_FAIL_DISTRIBUTION`。

---

# 5. E1 Cheap Test 2：criticality prediction

只允许使用 agent 可见信息。

第一版 feature 可包括：

- visible enemy count；
- nearest enemy distance；
- relative bearing；
- torpedo-ready count；
- own damage；
- score margin；
- turn；
- phase；
- action count；
- public uncertainty proxy；
- formation geometry；
- public tactical pressure features。

禁止使用：

- hidden commitment；
- opponent private state；
- rollout-derived future value；
- rho 本身。

模型：

1. Logistic regression
2. Random Forest / XGBoost / LightGBM（三者选现成最方便的一种）
3. Small MLP

任务：

```text
predict high-rho
```

指标：

- AUROC
- AUPRC
- calibration
- recall at fixed compute budget
- false-negative rate on high-rho states

### E1-T2 PASS

至少有一种简单模型：

```text
AUROC >= 0.75
```

且在 20–30% reasoning budget 下：

```text
recall(high-rho) >= 70%
```

更重要：

false negatives 不能集中在最高 regret 状态。

如果复杂模型也只接近随机：

`E1_FAIL_PREDICTABILITY`。

---

# 6. E1 Cheap Test 3：Selective Reasoning simulation

先在 Exact Lab 做。

定义两个 agent：

### Cheap agent
不使用 hidden commitment，只执行 robust/default action。

### Expensive agent
调用 full opponent-aware solver。

Gate：

```text
if predicted_rho > tau:
    expensive_reasoner()
else:
    cheap_policy()
```

Baselines：

1. Always Reason
2. Never Reason
3. Random with same budget
4. Periodic
5. Entropy trigger
6. Generic value-uncertainty trigger
7. Oracle rho gate

主图：

```text
game value / regret
vs
expensive reasoner calls
```

### E1-T3 PASS

在 unseen exact games 上：

- expensive calls 减少 ≥40%
- relative value retention ≥95%
- 明显优于 random / periodic / entropy 在同 compute budget 下
- 与 oracle gate 有合理差距，不要求接近 oracle

如果只有：

```text
Ours ≈ entropy / periodic
```

则 `E1_WEAK`。

---

# 7. E1 Novelty Kill

在决定继续之前，必须查 closest prior：

- Learning When to Plan
- Value of Information in POMDP planning
- adaptive test-time compute
- selective search
- opponent modeling gates
- metareasoning / value of computation
- safe opponent exploitation
- information gathering in games

必须回答：

1. 我们是不是只把“什么时候规划”换成“什么时候建模对手”？
2. `rho(s)` 是否只是 VOI 的重写？
3. strategic opponent / hidden commitment 是否带来新的 formal structure？
4. 是否可以给出“共享安全 action 存在”的 certificate？
5. 是否能在 Game AI benchmark + IBS 上展示独特现象？

如果最接近工作已经直接做：

> action sensitivity / regret → decide whether to invoke opponent model

则 `E1_NOVELTY_FAIL`。

---

# 8. Track E2 — Strategic Influence Planning
## Counterfactual Planning by Changing the Opponent's Best Response

### 8.1 核心问题

传统 planner 评价动作时主要看：

```text
我直接造成多少伤害 / 得分
```

但战略动作的价值可能来自：

```text
迫使对方改变路线
迫使对方减速
破坏 formation
失去 firing position
失去 crossing-T
暴露于后续火力
```

因此：

> 一个看起来“没有直接收益”的动作，可能因为重塑 opponent best response 而非常有价值。

---

# 9. E2 核心 formal object

对动作 `a`：

\[
IV(a)
=
V\left(BR_{opp}^{without\ a}\right)
-
V\left(BR_{opp}^{with\ a}\right)
\]

实际实现可以拆成：

\[
Score(a)
=
DirectValue(a)
+
\lambda InfluenceValue(a)
\]

其中 `InfluenceValue` 衡量：

- opponent route changed；
- forced deviation；
- speed loss；
- loss of firing position；
- crossing-T loss；
- formation split；
- future exposure；
- local force-ratio change。

注意：

E2 的研究对象不是“让对手学习错误”。

而是：

> 当前动作改变物理/战略可行域，从而改变对手 rational best response。

---

# 10. E2 Cheap Test 1：现有 torpedo planner 是否真的存在 influence signal

复用：

`AdaptiveTorpedoPlanner`

读取其已有 counterfactual outputs：

- baseline route
- threatened route
- forced deviation
- speed loss
- fire-position loss
- crossing-T loss
- formation split
- local force ratio gain
- route_changed

采样：

- 至少 200 个真实 reachable torpedo states；
- ≥2 scenarios；
- 多种 TacticalProfile。

对每个状态比较候选 action：

### Direct-only
只按 expected hit / immediate damage 排序。

### Influence-only
只按 counterfactual strategic influence 排序。

### Hybrid
direct + influence。

统计：

```text
ranking disagreement
```

即：

> influence term 是否真的经常改变动作选择？

### E2-T1 PASS

至少：

- ≥20% 状态 influence 会改变 top action；
- 改变不是纯 heuristic artifact；
- ≥30 个强可解释案例。

如果 influence 几乎从不改变 top action：

`E2_FAIL_NO_SIGNAL`。

---

# 11. E2 Cheap Test 2：Counterfactual continuation

对 Direct-only 与 Hybrid 选择的 action 做真实 simulator continuation。

每个 state：

```text
Action_direct
Action_hybrid
```

相同随机种子做 CRN。

记录：

- immediate damage；
- 1-turn value；
- 2-turn value；
- terminal value；
- opponent route deviation；
- formation metrics。

重点：

> Hybrid 是否愿意牺牲短期直接收益，换来后续更好的战略状态？

### E2-T2 PASS

在至少两个 scenario：

- Hybrid terminal/2-turn value 稳定优于 Direct-only；
- effect size 有统计意义；
- 至少一部分收益来自“影响对手响应”而不是简单选中了更高伤害动作；
- OOD profile 不崩。

参考门：

```text
>=10% relative improvement in long-horizon value
```

或等价明显 effect。

如果只有 immediate heuristic score 更好，没有 rollout value 改善：

`E2_FAIL_HEURISTIC_ONLY`。

---

# 12. E2 Cheap Test 3：消融因果性

必须证明收益来自 influence，而不是 feature 堆叠。

做：

1. Direct-only
2. Direct + random influence features
3. Direct + shuffled influence labels
4. Direct + true influence
5. Oracle counterfactual influence（如可行）

如果：

```text
true influence ≈ shuffled/random
```

则 `E2_FAIL_CAUSALITY`。

---

# 13. E2 Novelty Kill

必须检查：

- opponent shaping
- strategic influence
- counterfactual planning
- adversarial planning
- opponent-aware MCTS
- Stackelberg / best-response shaping
- tactical area denial
- deception / feint planning

重点回答：

> 我们的“改变对手 best-response set”是不是已有 opponent-shaping 的平凡特例？

必须明确区分：

- learning-time opponent shaping；
- belief manipulation；
- policy exploitation；
- **single-decision physical strategic influence**。

如果分不清：

`E2_NOVELTY_FAIL`。

---

# 14. 双轨比较标准

E1/E2 cheap-kill 后制作：

`M1_5_DIRECTION_SCORECARD.md`

字段：

| Criterion | E1 | E2 |
|---|---:|---:|
| Natural signal | | |
| Effect size | | |
| Simple baseline gap | | |
| Generalization potential | | |
| Theory potential | | |
| Game-AI identity | | |
| Engineering cost | | |
| Compute cost | | |
| Closest-prior collision | | |
| IBS reuse | | |
| Standard benchmark portability | | |
| Biggest reviewer attack | | |

本地 AI 不做最终主线决定。

---

# 15. 双轨 Stop Rules

## E1 Kill

任意一条成立即可：

- rho 没有稀疏重尾结构；
- high-rho 只能靠 tiny-stake normalization；
- visible features 无法预测 criticality；
- selective gate 不优于 entropy/periodic/random；
- closest prior 已高度同构。

## E2 Kill

任意一条成立即可：

- influence 几乎不改变 top action；
- Hybrid rollout 不优于 Direct-only；
- 收益全部来自直接伤害；
- shuffled influence 也一样好；
- closest prior 高度同构。

---

# 16. 时间与资源预算

M1.5 总时长：

```text
3–5 天
```

建议：

### Day 1
E1 rho 分布 + E2 influence disagreement

### Day 2
E1 predictability + E2 rollout pilot

### Day 3
E1 Exact selective gate + E2 confirmatory micro-run

### Day 4–5
novelty review + repeat + checkpoint

资源：

- 主要本机；
- GPU 非必须；
- IBS 新增 rollout ≤15,000；
- LLM API = 0；
- 不训练大模型；
- 不租服务器；
- 不做 PPO/self-play。

---

# 17. 实验纪律

1. 先冻结每个 cheap test 的 metric 和 threshold。
2. 不根据结果改 success gate。
3. 任何 bug 修复必须记录。
4. 所有 negative results 保留。
5. 所有 post-hoc probe 标记 `POST_HOC`。
6. 不为了凑足案例继续扫 scenario。
7. 不把 heuristic score 当真实 value。
8. simulator continuation 与 heuristic 分开报告。
9. 不允许用 hidden/private feature 训练 E1 online gate。
10. E2 influence feature 必须可由合法 planner counterfactual 获得。

---

# 18. 最终 checkpoint

输出：

`M1_5_NEW_MAINLINE_CHECKPOINT.zip`

必须包含：

```text
00_EXECUTIVE_SUMMARY.md
01_E1_SELECTIVE_REASONING.md
02_E2_STRATEGIC_INFLUENCE.md
03_NOVELTY_MATRIX.md
04_DIRECTION_SCORECARD.md
FAILURES_AND_COUNTEREXAMPLES.md
EXPERIMENT_REGISTRY.csv
CLAIM_EVIDENCE_MATRIX.csv
metrics/
figures/
scripts/
logs/
git_info.txt
environment.txt
```

---

# 19. Executive Summary 必须输出

```text
E1_SIGNAL = PASS / FAIL
E1_PREDICTABILITY = PASS / FAIL
E1_COMPUTE_VALUE = PASS / FAIL
E1_NOVELTY = PASS / FAIL / AMBIGUOUS

E2_SIGNAL = PASS / FAIL
E2_LONG_HORIZON_VALUE = PASS / FAIL
E2_CAUSALITY = PASS / FAIL
E2_NOVELTY = PASS / FAIL / AMBIGUOUS

BEST_SUPPORTED_TRACK = E1 / E2 / NONE
SECONDARY_TRACK = E1 / E2 / NONE
```

禁止使用：

```text
promising
worth exploring
looks good
```

最终必须是明确证据。

---

# 20. 当前执行顺序

不要同时大跑。

顺序：

```text
E1-T1 rho distribution
↓
E2-T1 influence ranking disagreement
↓
如果某条立即 FAIL，就停止该条
↓
E1-T2 / E2-T2
↓
E1-T3 / E2-T3
↓
Novelty kill
↓
checkpoint
```

---

# 21. 最终科研原则

这次不是继续“救”原来的 hidden-commitment 论文。

我们现在问两个新的 AI 问题：

### E1
> 什么时候对手的隐藏信息根本不值得花算力推理？

### E2
> 怎样通过自己的行动改变对手未来最优回应，而不仅仅追求直接收益？

只有其中至少一条在**真实 simulator + 强 baseline + novelty review**下成立，才进入 CCF-A full-paper 阶段。

如果两条都失败：

> 停止围绕 hidden commitment / torpedo 继续挖，重新从整个 Iron Bottom Sound 系统做新一轮选题扫描。
