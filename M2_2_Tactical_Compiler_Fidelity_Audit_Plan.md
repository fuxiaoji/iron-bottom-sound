# M2.2 — Tactical Compiler Fidelity Audit
## 从“规则有战略价值”到“AI 能否把战略意图编译成合法联合行动”

**项目**：`fuxiaoji/iron-bottom-sound`  
**阶段性质**：新的探索性阶段，不修改 M2.1-R2.1 的预注册结论。  
**PI 判定**：

```text
M2.1-R2.1 MECHANISTIC_GOLD_GATE = FAIL (3/5)
```

保持原样，不改成 PASS。

但该 gate 的失败**不等于平台低杠杆**。目前已有三个独立、合法、引擎原生验证的强机制：

```text
MG1 BROADSIDE       = PASS
MG3 RANGE CONTROL   = PASS
MG4 TORPEDO CORRIDOR= PASS
```

所以新的问题已经变成：

> 这些规则层真实存在的战略杠杆，当前自动 AI / tactical compiler 能否在自然战局中发现并实现？

本阶段不再“救” MG2/MG5，不为了把 3/5 改成 4/5 继续找案例。

---

# 1. 旧结果如何冻结

## 1.1 冻结，不再改判

```text
MG1 = VALID PASS
MG3 = VALID PASS
MG4 = VALID PASS

MG2 = FAIL in its registered arm
MG5 = FAIL in its registered arm

MECHANISTIC_GOLD_GATE = FAIL (3/5)
```

## 1.2 解释边界

MG2 的结果只支持：

> 当前名为 CROSS_T 的自动 arm 没有真正占据足够的 raking geometry。

它**不支持**：

> Crossing-the-T 在规则中没有价值。

MG5 的结果只支持：

> IBS-S-01 seed 1 turn 3 的当前 CONCENTRATE arm 没有制造局部兵力优势，DISPERSE 的合法火力边际反而更高。

它**不支持**：

> 所有 IBS 状态都不存在局部兵力优势。

因此 M2.2 不再把 MG2/MG5 当作 platform-level negative。

---

# 2. 本阶段科研问题

只回答三个问题：

## Q1 — Natural Opportunity
在真实可达 snapshot 中，MG1/MG3/MG4 这三类机制是否经常存在可利用机会？

## Q2 — Compiler Gap
当机会存在时，当前 TacticalCommander / AdaptiveTorpedoPlanner / 现有 intent compiler 能拿到多少规则层可实现收益？

## Q3 — Search Recoverability
一个不训练神经网络、只使用规则合法 action + 有限搜索的 research planner，能否明显恢复这些收益？

如果答案是：

```text
Natural opportunity exists
+
current AI captures little
+
finite search recovers much
```

则：

```text
COMPILER_GAP_CONFIRMED
```

这才值得进入下一步算法创新。

---

# 3. 本阶段明确不做什么

禁止：

```text
MAPPO
QMIX
GNN
Transformer
LLM planner training
self-play training
新 torpedo heuristic 作为论文方法
修改生产规则
修改胜利条件
重新跑 MG2/MG5 以凑 4/5
```

本阶段只是“测量编译差距”。

---

# 4. 三类已验证机制

## M1 — Broadside / Firepower-Unmasking

规则层 Gold：

```text
MG1 +92.9% common-distance expected hits
```

自然状态目标：

> 是否存在合法 movement batch，可以显著增加下一炮击阶段的合法火力机会？

定义 post-movement pre-gunnery 机制值：

\[
M_{broad}(s,a)
=
EH^{legal}_{own}(s')
-
\lambda EH^{legal}_{enemy}(s')
\]

主报告同时保留：

```text
own legal EH
enemy legal EH
net legal EH
own bearing mounts
enemy bearing mounts
target aspect mix
```

默认 `lambda=1`，在主结果前冻结。

---

## M2 — Range Control

规则层 Gold：

```text
MG3: distance 15 vs 17 -> expected hits 2.56 vs 0.94
```

自然状态目标：

> movement 是否能把关键交战保持在己方有利距离，而不是单纯追近/拉远？

不得定义成：

```text
distance smaller = better
```

而应使用引擎原生合法炮击机会。

定义：

\[
M_{range}(s,a)
=
NetEH(s')
\]

并附：

```text
weighted engagement distance
penetration feasibility
torpedo-threat proximity
```

只有当不同 movement batch 的距离变化带来明显 `NetEH` 差异时，才叫 range opportunity。

---

## M3 — Torpedo Corridor / Action-Set Shaping

规则层 Gold：

```text
MG4:
29 legal routes
28 torpedo-contact routes
RouteReduction = 0.966
```

这里的核心不是 expected hit。

定义：

\[
RR(s,\tau)
=
1-\frac{|R^{safe}_{\tau}(s)|}{|R(s)|}
\]

其中：
- \(\tau\)：合法 torpedo launch configuration；
- \(R(s)\)：目标下一决策点的合法 movement routes；
- \(R^{safe}_{\tau}(s)\)：不与鱼雷时空轨迹接触的合法 routes。

同时计算：

```text
best-safe-route identity
best-safe-route tactical score
no-torpedo best-route tactical score
```

当前阶段只研究标准可见鱼雷：
`blind_torpedoes=False`。

---

# 5. 重要测量修正：Legal Fire Evaluator

M2.1-R2.1 的 repaired fire evaluator可继续使用，但必须明确：

> 当前 `team_legal_fire_v2` 是一个“合法的一目标/舰分配器”，不是全局最优炮击求解器。

原因：
- 每个 mount 最多使用一次：正确；
- batch 能通过 validator：正确；
- 但当前实现约束“一艘舰只选一个 target”，而规则/引擎可能允许不同 mount / 主副炮分火。

因此 M2.2 所有文档必须写：

```text
LEGAL_FIRE_HEURISTIC
```

不能写：

```text
OPTIMAL_LEGAL_FIRE
```

如果需要 research ceiling，再实现小规模 `FIRE_SEARCH_ORACLE`：
- 枚举/beam 合法 target/mount allocations；
- full validator；
- engine-exact modifiers；
- 不需要覆盖所有状态，只用于 10–20 个校准状态。

如果 `LEGAL_FIRE_HEURISTIC` 与 `FIRE_SEARCH_ORACLE` 排序高度一致，可继续用前者做大样本。

---

# 6. B0 — Gold Compiler Fidelity

先不要自然状态 census。

先让当前自动 compiler 回到三个已经确认的 Gold mechanism cases：

```text
MG1
MG3
MG4
```

## 6.1 对比方法

每个 Gold case 比较：

```text
MANUAL_GOLD
CURRENT_POLICY
CURRENT_INTENT_COMPILER
SEARCH_COMPILER
RANDOM_LEGAL
```

其中：

### MANUAL_GOLD
冻结 Gold case 中已经通过的合法动作。

### CURRENT_POLICY
当前 TacticalCommander / AdaptiveTorpedoPlanner 原生输出。

### CURRENT_INTENT_COMPILER
现有 `intents.py` / tactical intent 编译器。

### SEARCH_COMPILER
本阶段新增 research-only 有限搜索，只为测上限，不作为论文方法。

### RANDOM_LEGAL
同 action budget 的随机合法 baseline。

---

# 7. B0 fidelity 指标

对机制值 \(M\)：

\[
F(method)
=
\frac{M(method)-M(random)}
{M(manual\_gold)-M(random)}
\]

只在分母为正且 Gold gap 超过预注册最小值时计算。

同时报告绝对值，不能只报比率。

### 初步解释

```text
F >= 0.8  -> compiler 基本能实现 Gold
0.4–0.8   -> 部分实现
F < 0.4   -> 明显 compiler gap
```

这只是 Stage B 诊断，不是论文 success gate。

---

# 8. SEARCH_COMPILER：movement

目的：
证明“合法联合机动里存在更好的几何”，不是训练最终算法。

## 8.1 每舰候选

每个 ship 先通过 engine movement preview / candidate API 得到合法 plans。

限制每舰最多 K=8：
- current-policy plan；
- hold（若合法）；
- fast/slow；
- port/starboard extreme；
- 按 intent metric 单舰评分的 top plans。

## 8.2 Joint beam search

构造联合计划时：

```text
beam width = 64
```

若 EM-01 过慢，可降到 32，但必须预注册。

每加入一舰：
- 合并 joint batch；
- 用 full side-level validator；
- 非法立即丢弃；
- 用 cheap partial geometry score 排序保留 beam。

最终完整 batches 用真实：
- simultaneous movement；
- opponent frozen/sealed policy；
- post-movement pre-gunnery metric

重新评分。

不要用逐舰独立最优直接拼接当 oracle。

## 8.3 Search 不是“optimal”

统一命名：

```text
SEARCH_UPPER_BASELINE
```

或：

```text
BEAM_SEARCH_COMPILER
```

不得写 `oracle` / `optimal`，除 Exact Lab 外。

---

# 9. SEARCH_COMPILER：torpedo

不要再只使用 `torpedo_tactical_combos()` 的 intercept options。

在 TORPEDO_PLANNING：

枚举真实合法配置：

```text
launcher
× launch MF
× launch side
× launch angle
× speed/range setting
× salvo size
```

每个候选：
- `_project_torpedo_path`
- full `validate_orders`
- 只用公开信息构建目标未来 route set

## 9.1 PUBLIC corridor objective

不能读取敌方 sealed movement order。

从当前 observation 构造目标下一回合可行动作集合/可达区域。

定义：

```text
PUBLIC_ROUTE_REDUCTION
```

基于：
- 当前公开位置；
- 当前公开 heading/speed；
- 已知规则；
- 目标下一决策点的合法 route generator。

如果某些 future speed/damage 是隐藏信息：
只使用 observation 中可见值；
未知值按规则允许集合处理，不能偷看真实值。

## 9.2 RESEARCH_FULL_STATE ceiling

可以另外计算：

```text
FULL_STATE_ROUTE_REDUCTION
```

作为 research upper ceiling。

必须与 PUBLIC 分开报告。

差距回答：

> 编译难，还是信息限制难？

---

# 10. B0 Gate

三个 frozen Gold case 中至少 2 个满足：

```text
MANUAL_GOLD mechanism strong
SEARCH_COMPILER fidelity >= 0.70
CURRENT_POLICY fidelity <= 0.40
```

则：

```text
GOLD_COMPILER_GAP = PASS
```

如果 Search 也做不到 Manual Gold：

```text
SEARCH_COMPILER_FAIL
```

先修搜索，不进入自然状态。

如果 Current 已 >=0.8：

说明当前 AI 已能利用规则机制，compiler 不再是主要瓶颈。

---

# 11. B1 — Natural-State Opportunity Census

只有 B0 PASS 才执行。

## 11.1 数据

场景：

```text
IBS-S-01
IBS-S-03
IBS-S-EM-01
```

优先复用已有 replay pool。

每 scenario / side 分层抽：
- early movement；
- contact；
- damaged；
- late。

Movement：

```text
20 states / scenario
```

Torpedo：

```text
10 legal torpedo-planning states / scenario
```

总量约：
- 60 movement states；
- ≤30 torpedo states。

不按结果手挑。

---

# 12. B1 Movement Opportunity

每个 state 比较：

```text
CURRENT_POLICY
CURRENT_INTENT
BEAM_SEARCH_COMPILER
RANDOM_LEGAL
```

同时测：

```text
BroadsideOpportunity
RangeOpportunity
RakingDiagnostic
```

### Opportunity 定义

当 Search 相对 Current 有：

```text
>=25% relative mechanism gain
```

且 absolute gain 超过预注册最小值，
记为：

```text
OPPORTUNITY_PRESENT
```

避免 tiny denominator。

---

# 13. B1 Torpedo Opportunity

每个合法 torpedo state：

比较：

```text
CURRENT_ADAPTIVE_TORPEDO
INTERCEPT_ASSIST
PUBLIC_CORRIDOR_SEARCH
FULL_STATE_CORRIDOR_CEILING
HOLD
```

主要指标：

```text
route reduction
safe-route count
best safe route tactical score
number of enemy ships constrained
friendly-route risk
```

不能只看：
`expected_hits`。

---

# 14. Stage B 核心结果

必须得到下面四个量：

\[
P_{opp}
=
P(\text{natural state has exploitable mechanism opportunity})
\]

\[
F_{current}
=
\text{current AI mechanism fidelity}
\]

\[
F_{search}
=
\text{search compiler mechanism fidelity}
\]

\[
InfoGap
=
F_{full-state}-F_{public}
\]

这四个量决定下一步研究问题。

---

# 15. Stage B 判定

## COMPILER_GAP_CONFIRMED

要求：

1. 至少两类机制在至少两个 scenario 中有 natural opportunity；
2. natural opportunity rate >=20%；
3. Search 相对 Current 的机制增益明显：
   - median fidelity gain >=0.30
   或
   - Current 捕获 <40% 可实现 gain，而 Search 捕获 >=70%；
4. Random matched-budget 明显低于 Search；
5. 结果不是只来自一个 scenario。

解释：

> 平台规则有价值，自然状态中也有机会，但当前 AI 无法把战略意图编译成合法联合动作。

---

## MECHANISM_RARE

Gold 很强，但自然状态：

```text
opportunity rate <10%
```

解释：
机制真实，但不适合作为常规训练主信号。

---

## SEARCH_LIMITED

Natural opportunity 看起来存在，但：
`SEARCH_COMPILER` 也无法稳定恢复 Gold / natural gain。

先改善 research search，不进入学习算法。

---

## CURRENT_AI_ALREADY_STRONG

Current fidelity >=0.8 且与 Search 接近。

解释：
compiler 不是问题，应进入 value realization / opponent reasoning。

---

# 16. Crossing-T 如何处理

本阶段不再用旧 `CROSS_T` arm 判规则机制。

把它改成 supplemental compiler target：

## RAKING_GEOMETRY

Search objective：

```text
maximize:
  legal net EH
  + bow/stern selected-target fraction
subject to:
  own legal fire maintained
```

若 Search 能从自然状态得到：

```text
bow/stern fraction >=0.5
+
net EH >=1.25x current
```

则说明：

> T-head/raking position 是可编译的高价值 geometry。

如果 Search 都做不到：
不再把 crossing-T 当核心 benchmark。

---

# 17. Local Force 如何处理

MG5 不再重跑 Gold。

只作为自然状态 diagnostic。

定义 engagement graph：
- shooter -> legal selected target；
- edge weight = expected hits / GF。

观察是否自然出现：
- 某 movement action 让部分敌舰退出有效交战图；
- 自方有效参与节点保持。

如果自然 opportunity 稀少：
永久放弃 local-force 作为论文核心机制。

---

# 18. Stage C 仍然禁止提前进入

Stage B 只看：

```text
mechanism realization
```

不看最终胜率主张。

只有 `COMPILER_GAP_CONFIRMED` 后，PI 才决定是否进入：

```text
M2.3 Value Realization
```

届时再比较：

```text
E0 scripted
E2 local minimax
E3 adversarial
terminal
```

---

# 19. 必须输出的图

1. Gold fidelity bars: Manual / Current / Intent / Search / Random
2. Natural mechanism-gain CDF
3. Current vs Search scatter
4. Search fidelity by scenario
5. Broadside/range opportunity rate
6. Torpedo route-reduction distribution
7. Public vs full-state torpedo ceiling
8. Raking geometry scatter
9. Failure/counterexample gallery

---

# 20. 最终 bundle

```text
M2_2_TACTICAL_COMPILER_FIDELITY_BUNDLE.zip
```

必须包含：

```text
00_EXECUTIVE_SUMMARY.md
01_GOLD_COMPILER_FIDELITY.md
02_MOVEMENT_SEARCH_COMPILER.md
03_TORPEDO_CORRIDOR_COMPILER.md
04_NATURAL_OPPORTUNITY_CENSUS.md
05_PUBLIC_VS_FULLSTATE_GAP.md
06_RAKING_GEOMETRY_DIAGNOSTIC.md
07_COMPILER_GAP_DIAGNOSIS.md
PRE_REGISTRATION_M22.md
EXPERIMENT_REGISTRY.csv
CLAIM_EVIDENCE_MATRIX.csv
FAILURES_AND_COUNTEREXAMPLES.md
DATA_MANIFEST.md
metrics/
figures/
cases/
code_patch/
logs/
```

---

# 21. Executive Summary 硬判

```text
M21R21_GOLD_GATE = FAIL_3_OF_5   # 保留历史，不修改

MG1_RULE_LEVERAGE = CONFIRMED
MG3_RULE_LEVERAGE = CONFIRMED
MG4_RULE_LEVERAGE = CONFIRMED

GOLD_COMPILER_GAP =
PASS / FAIL / BLOCKED

BROAD_SIDE_NATURAL_OPPORTUNITY =
HIGH / SPARSE / LOW

RANGE_NATURAL_OPPORTUNITY =
HIGH / SPARSE / LOW

TORPEDO_CORRIDOR_NATURAL_OPPORTUNITY =
HIGH / SPARSE / LOW

SEARCH_RECOVERABILITY =
HIGH / MEDIUM / LOW

CURRENT_AI_FIDELITY =
HIGH / MEDIUM / LOW

PUBLIC_INFORMATION_GAP =
HIGH / MEDIUM / LOW

STAGE_B_DIAGNOSIS =
COMPILER_GAP_CONFIRMED /
MECHANISM_RARE /
SEARCH_LIMITED /
CURRENT_AI_ALREADY_STRONG /
MIXED

NEXT_PI_DECISION =
```

---

# 22. 核心纪律

1. 不改变 M2.1-R2.1 的 3/5 FAIL。
2. 不再修 MG2/MG5 凑门。
3. Gold 用于规则存在性；Natural Census 用于普遍性。
4. Search 是 research baseline，不叫 optimal。
5. Public 与 full-state 必须分离。
6. Torpedo 核心是 action-set shaping / route denial，不是 expected hit。
7. 所有 movement batches 走完整 validator。
8. 不训练模型。
9. Stage B 完成后停止交 PI。
