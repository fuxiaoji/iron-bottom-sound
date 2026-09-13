# Iron Bottom Sound v13.1 — Mobility × Flexibility Q1 主线重构（基于已完成 v12）
## 中科院一区冲刺版本
### 先实验、后改稿；只有通过 Gate 才重写主论文

> **基准事实（来自已完成 v12）**
>
> 1. v12 已完成 solver audit：
>    - exact symmetric controls 在 3 geometry × 4 cadence 下全部约为 0；
>    - 最大数值误差约 \(2.4\times 10^{-15}\)；
>    - sequence form 与完整矩阵 / backward induction 小规模结果一致；
>    - 17 项针对性测试通过；
>    - `cache_off` 与 `exact_history` 同种子结果一致；
>    - old pose-only cache 在三种 geometry 中都触发非对称矩阵错误，已证明不可用于科学结果；
>    - geometric canonicalization 将 strategy equivariance error 压到约 \(2\times10^{-15}\)。
>
> 2. 原 range-based bilateral Commitment hypothesis 已被可靠否决：
>    - 6 个 exact anchors 中仅 head-on 两点符合原符号，parallel/crossing 反向；
>    - 12 个冻结 held-out range points 中仅 1/12 支持“range-disadvantaged side has larger flexibility value”，其余 11/12 反向；
>    - flexibility non-negativity 与 decomposition identity 均成立。
>
> 3. 因此：
>    - **不要继续救 range–Commitment 主线；**
>    - **不要重新跑 v12 solver audit；**
>    - v12 作为经过验证的数值基础和负结果保留；
>    - v13 只研究新的、独立的假设：
>
> \[
> \boxed{\text{Mobility capability} \times \text{Value of Adaptation}}
> \]
>
> 4. 本计划中的“一区/二区”默认指 **中科院分区**。最终选刊时再根据最新中科院分区、JCR、scope、审稿风格做实时核验。
>
> **总纪律：**
> - discovery 与 confirmatory 严格分离；
> - 不因结果方向更换参数；
> - 不删除反例；
> - 不在 confirmatory 前改 hypothesis；
> - 不在 Q1 Gate 通过前重写主论文；
> - v11/v12 稿件始终保留为 Q2 fallback branch。

---

# 0. v13.1 最大修改：不要再用“不同对手 policy class”比较快慢双方的 flexibility

原 v13 中若直接比较：

\[
F_{\rm fast}
\quad\text{vs}\quad
F_{\rm slow}
\]

但两者分别来自不同 opponent policy structure，例如：

\[
F_B=V_{FC}-V_{CC},
\]

\[
F_R=V_{FC}-V_{FF},
\]

则：

\[
F_R-F_B
=
V_{CC}-V_{FF},
\]

这正好又等价于旧 bilateral Commitment effect。

v12 已证明这种比较不能产生新的独立机制。

因此 v13.1 的主实验必须改成真正的 **factorial interaction**：

> **固定对手的速度和 policy class，只改变焦点玩家自己的 mobility 和自己的 flexibility。**

---

# 1. 正确的新主量：Conditional Own-Flexibility Value

设 Blue 为焦点玩家，Red 的速度 \(v_R\) 与 policy class \(\kappa_R\) 固定。

\[
\kappa_R\in\{F,C\}.
\]

定义：

\[
\boxed{
\mathcal F_B(v_B\mid \kappa_R,v_R)
=
V(F,\kappa_R;v_B,v_R)
-
V(C,\kappa_R;v_B,v_R)
}
\]

理论上，由 policy-set inclusion：

\[
\boxed{
\mathcal F_B\ge0.
}
\]

这个量只回答：

> 在对手完全不变时，本方多获得 replanning/adaptation 权到底值多少钱？

---

# 2. 两种条件化 flexibility value

## 2.1 Opponent committed

\[
\boxed{
\mathcal F_B^{C}
=
V_{FC}-V_{CC}
}
\]

## 2.2 Opponent flexible

\[
\boxed{
\mathcal F_B^{F}
=
V_{FF}-V_{CF}
}
\]

这两个量都必须分别研究。

这样可以回答：

> mobility × flexibility complementarity 是否只在对手 committed 时出现，还是在对手 flexible 时也存在？

---

# 3. 新核心假设 H1：Own Mobility–Flexibility Complementarity

固定：

- opponent speed；
- opponent range；
- opponent policy class；
- geometry；
- total horizon；
- formation model；
- payoff。

仅改变焦点玩家：

\[
v_B=v_L
\quad\text{or}\quad
v_H,
\]

以及：

\[
C\quad\text{or}\quad F.
\]

定义：

\[
\boxed{
M_B^{\kappa_R}
=
\mathcal F_B(v_H\mid\kappa_R)
-
\mathcal F_B(v_L\mid\kappa_R)
}
\]

等价写成 difference-in-differences：

\[
\boxed{
M_B^{\kappa_R}
=
[
V(F,\kappa_R;v_H)
-
V(C,\kappa_R;v_H)
]
-
[
V(F,\kappa_R;v_L)
-
V(C,\kappa_R;v_L)
]
}
\]

主假设：

\[
\boxed{
H1:
M_B^{\kappa_R}>0
}
\]

即：

> **更高 mobility 提高了本方获得 feedback/replanning 权的边际价值。**

这是 v13.1 的第一主量。

---

# 4. Player-swap 镜像

对 Red 做完全对称定义：

\[
\mathcal F_R(v_R\mid\kappa_B,v_B)
\]

以及：

\[
M_R^{\kappa_B}.
\]

必须通过 player-swap：

\[
M_B(s)
\approx
M_R(\mathcal Ss)
\]

到数值 tolerance。

最终不应该出现：

> Blue 天生比 Red 更依赖 flexibility。

---

# 5. Secondary hypothesis H2：Mutual Commitment Compresses Mobility Premium

这可以保留，但只能作为 **H1 的推论/解释性副结果**，不能作为主实验。

固定 Red 能力，比较 Blue 高/低 speed：

\[
S_F
=
V_{FF}(v_H)-V_{FF}(v_L),
\]

\[
S_C
=
V_{CF}(v_H)-V_{CF}(v_L).
\]

注意这里必须保持：

- Red policy 同为 \(F\) 时比较 \(S_F\)；
- Red policy 同为 \(F\)，Blue 自己从 F/C 变化对应 factorial；
- 不得混用不同对手 policy class。

若定义保持一致：

\[
\boxed{
S_F-S_C=M_B^{F}.
}
\]

同理可在 Red committed 条件下构造：

\[
S_{F|C}-S_{C|C}=M_B^{C}.
\]

所以 H2 不是独立假设，而是 H1 的另一个解释：

> 高 mobility 的收益在允许 adaptation 时更容易兑现。

---

# 6. v13.1 不再重复 v12 Solver Audit

v12 已经证明：

- exact symmetric value 归零；
- exact solver 与 brute force/normal form 小规模一致；
- old cache 错；
- exact-history cache 正确；
- symmetry canonicalization 正确。

因此 v13 只保留 **regression tests**：

每次核心代码改动自动运行：

1. 3 symmetric geometry；
2. T=1 matrix equivalence；
3. T=2/3 exact backward induction equivalence；
4. player-swap；
5. flexibility non-negativity；
6. old pose cache 禁止出现在 scientific config。

不得重新跑整套 v12 Monte Carlo audit。

---

# 7. Freeze v12

新建：

```text
research/final_v13/v12_freeze/
```

保存：

- exact control results；
- six exact range anchors；
- 12 held-out range points；
- v12 negative-result report；
- v12 solver tests；
- sequence-form validation；
- commit hash。

生成：

```text
V12_FROZEN_CONCLUSIONS.md
```

明确：

```text
RANGE_COMMITMENT = FALSIFIED
RANGE_FLEXIBILITY_VALUE_HYPOTHESIS = FALSIFIED
SOLVER_CORE = VALIDATED
OLD_POSE_CACHE = INVALID
```

v13 不得覆盖这些结论。

---

# 8. Phase A — Exact Grid-3 Mobility Discovery

使用已通过测试的 exact finite-game / sequence-form infrastructure。

固定：

\[
\eta_r=1.
\]

Red baseline speed：

\[
v_R=1.0.
\]

Blue focal speed：

\[
v_B
\in
\{0.70,0.85,1.00,1.15,1.30\}.
\]

geometry：

```text
head_on
parallel
crossing
```

T：

\[
T=6.
\]

action grid：

\[
\mathcal A_3=\{-1,0,1\}.
\]

---

# 9. Discovery 要完整计算 2×2 policy factorial

对于每个：

\[
(\text{geometry},v_B,v_R)
\]

计算：

\[
V_{FF},
V_{FC},
V_{CF},
V_{CC}.
\]

然后得到：

\[
\mathcal F_B^F=V_{FF}-V_{CF},
\]

\[
\mathcal F_B^C=V_{FC}-V_{CC}.
\]

再计算：

\[
M_B^F,
M_B^C.
\]

注意：

> 这里比较 high/low mobility 时 Red 的 speed 和 policy class 必须完全相同。

---

# 10. 镜像运行

所有 Blue-fast / Red-baseline 实验必须有 mirror：

```text
Blue baseline / Red fast
```

以及 slow 方向。

验证：

\[
V_{\text{swap}}
=
-V
\]

和对应 flexibility interaction 等变。

---

# 11. Discovery 参数只用于机制探索

Discovery 输出：

```text
geometry
v_blue
v_red
V_FF
V_FC
V_CF
V_CC
F_blue_given_red_F
F_blue_given_red_C
M_blue_given_red_F
M_blue_given_red_C
exact
```

此阶段允许看曲线，但：

\[
\boxed{\text{禁止宣布 confirmatory success}}
\]

---

# 12. 速度应该作为 capability expansion，而不是 forced operating speed

优先模型：

\[
v_B(t)\in[0,\bar v_B]
\]

其中：

\[
\bar v_B
\]

是最大速度 capability。

不要默认：

\[
v_B(t)=\bar v_B
\]

除非现有 action space 没有 speed control。

原因：

> 如果速度只是强迫更快航行，得到的是 operating-speed effect，不是 capability effect。

---

# 13. 如果当前模型只有固定速度

必须做两层区分：

## Main computational experiment

可先研究固定 operating speed：

\[
v=v_{\rm op}.
\]

但正式措辞必须叫：

```text
operating-speed × flexibility interaction
```

不能直接称：

```text
mobility capability complementarity
```

## Q1 upgrade

若计算可承受，应加入低维 speed-control action，例如：

\[
v/\bar v\in\{0.75,1.0\}
\]

或：

\[
\{0.5,0.75,1.0\}.
\]

然后真正研究：

\[
\bar v
\]

作为 capability set expansion。

如果做不到，论文必须明确限制。

---

# 14. Phase B — Moving Favorable Geometry Mechanism

用户原始机制：

> 敌方转向后，T 头/长期有利位置也随对手航向移动；高速方更能根据新信息重新追踪该区域。

这部分必须独立测量，不能只靠文字解释。

---

# 15. 不以单个 argmax 作为主机制指标

单一：

\[
x^\star=\arg\max L
\]

可能：

- 多峰；
- 跳变；
- 对网格敏感。

因此：

\[
x^\star
\]

只做可视化。

主机制使用 **favorable superlevel set**。

---

# 16. Favorable set 定义

在预先冻结的 bounded relative-state domain \(\mathcal D\) 中：

\[
\mathcal G_\alpha(t)
=
\{
z\in\mathcal D:
L(z;t)\ge
\alpha L^\star(t)
\}.
\]

主阈值：

\[
\alpha=0.90.
\]

robustness：

\[
\alpha=0.80.
\]

\(\mathcal D\) 必须由 interaction kernel 有效作用范围预先定义，不能按结果调整。

---

# 17. Drift 指标

主指标不要直接用 raw Hausdorff distance 作为唯一结果。

同时计算：

### A. Set-centroid / medoid drift
稳健描述整体移动。

### B. Directed nearest-set drift

从当前 favorable set 到下一 favorable set：

\[
D_t
=
\operatorname{median}_{z\in\mathcal G_t}
d(z,\mathcal G_{t+1}).
\]

### C. Hausdorff distance

作为 robustness。

### D. Angular change

\[
|\Delta\psi_{\rm opp}|.
\]

主机制建议用 B，Hausdorff 只做补充，避免少数边界点支配结果。

---

# 18. Reachable correction 的正确指标

给定当前焦点玩家 state：

\[
s_t
\]

以及下一时刻 favorable set：

\[
\mathcal G_{t+1},
\]

定义：

\[
d_{\rm before}
=
d(s_t,\mathcal G_{t+1}).
\]

一决策间隔 reachable set：

\[
\mathcal R_t(\bar v,\omega_{\max}).
\]

定义：

\[
d_{\rm after}^{\min}
=
\min_{s'\in\mathcal R_t}
d(s',\mathcal G_{t+1}).
\]

于是：

\[
\boxed{
R_t
=
d_{\rm before}
-
d_{\rm after}^{\min}
}
\]

代表：

> mobility 在一个 replanning interval 内最多可以把自己向新的 favorable set 拉近多少。

---

# 19. Tracking Ability 指标

不要直接用：

\[
R_t/D_t
\]

作为唯一指标，因为 \(D_t\approx0\) 会爆炸。

主指标改为 bounded：

\[
\boxed{
\Theta_t
=
\frac{R_t}
{R_t+D_t+\epsilon}
\in[0,1]
}
\]

解释：

- \(\Theta\approx0\)：有利区域跑得比你能修正得快；
- \(\Theta\approx1\)：自身修正能力足以跟踪 geometry drift。

原 ratio：

\[
R_t/(D_t+\epsilon)
\]

保留 Supplement robustness。

---

# 20. Mechanism outcome

episode level：

\[
\bar\Theta
=
\operatorname{median}_t\Theta_t.
\]

检验：

\[
\boxed{
\mathcal F
\text{ vs }
\bar\Theta
}
\]

至少：

- Spearman；
- geometry-stratified scatter；
- simple regression：
  \[
  \mathcal F
  =
  \beta_0+
  \beta_1\bar\Theta+
  \text{geometry FE}
  +\epsilon.
  \]

不要使用 ML。

---

# 21. Mechanism 的更强检验：Mediation-style ordering

如果：

\[
v_H>v_L
\]

同时：

\[
\bar\Theta_H>\bar\Theta_L
\]

且：

\[
\mathcal F_H>\mathcal F_L,
\]

记录：

\[
\Delta \Theta
\]

与：

\[
M=\Delta\mathcal F.
\]

检验：

\[
M
\]

是否随：

\[
\Delta\Theta
\]

增大。

这比单纯：

\[
F\sim\Theta
\]

更贴合 complementarity mechanism。

---

# 22. Phase C — Freeze Confirmatory Design

Discovery 完成后：

**不要立刻跑新点。**

先生成：

```text
research/final_v13/confirmatory_design/CONFIRMATORY_DESIGN.md
```

记录：

- hypotheses；
- parameter grid；
- primary outcome；
- exclusions；
- solver tolerances；
- success gate；
- git hash。

之后不可修改，除非版本化并明确记录原因。

---

# 23. Confirmatory 参数

推荐 focal own-speed values：

\[
v_B/v_R
\in
\{0.75,0.90,1.10,1.25\}.
\]

三种 geometry。

对手：

\[
v_R=1.
\]

range：

\[
\eta_r=1.
\]

优先检验：

\[
M_B^F
\]

和：

\[
M_B^C.
\]

形成 12 geometry × contrast 的核心 held-out comparisons。

Mirror swap 不计入独立样本数，只做 symmetry validation。

---

# 24. Primary confirmatory endpoint

不要把：

\[
F_{\rm fast}>F_{\rm slow}
\]

写成跨不同对手条件的比较。

正式 endpoint：

\[
\boxed{
M_B^{F}>0
}
\]

和：

\[
\boxed{
M_B^{C}>0
}
\]

其中每一个 interaction 都保证：

> opponent speed + opponent policy class 完全固定。

---

# 25. Success classification

## Q1-STRONG

要求：

1. primary held-out interactions ≥10/12 同方向；
2. resolved cases 不超过 1 个强反向；
3. 3 geometry 都有正支持；
4. \(M^F\) 和 \(M^C\) 至少一个为强一致，另一个不系统反向；
5. exact Grid-3 与 Grid-5 同方向；
6. Grid-7 anchors 不系统翻转；
7. mechanism：
   \[
   \rho(M,\Delta\Theta)>0.6
   \]
   或预冻结等价标准；
8. turn-rate robustness 不推翻；
9. horizon robustness 不推翻；
10. solver residual 远小于 effect。

---

## Q1-CONDITIONAL

- 8–9/12 同方向；
- 或 effect 主要存在 crossing/parallel；
- head-on 弱；
- 没有多个强反向。

可以写：

> mobility–adaptation complementarity is geometry-dependent.

---

## FAIL

- ≤7/12；
- 多个强反向；
- exact/finer grid 不一致；
- mechanism 不支持；
- speed effect 仅来自 forced operating-speed artifact。

触发：

\[
\boxed{\text{STOP; return to Q2 fallback manuscript}}
\]

---

# 26. Phase D — Grid-5 refinement

如果 Grid-3 discovery/confirmatory 支持：

使用：

\[
\mathcal A_5=
\{-1,-0.5,0,0.5,1\}.
\]

优先重跑 held-out 12 个核心 comparisons。

若 asymmetric information structure 的 exact Grid-5 太大：

- sequence-form column generation；
- extensive-form DO；
- 必须有 exploitability / duality-gap certificate。

不能返回旧 v11 那种 fixed-iteration heuristic。

---

# 27. Phase E — Grid-7 anchors

只做 6 个 pre-specified anchors：

```text
3 geometries
× 2 strong mobility contrasts
```

目的：

> action-resolution sign stability。

不做全 grid。

---

# 28. Phase F — Turn-rate / maneuverability robustness

因为用户的机制不是纯直线速度，而是：

> 能否追踪随对手转向移动的 favorable set。

固定 speed contrast，

改变：

\[
\omega_{\max}
\]

或 curvature bound。

至少：

\[
\eta_\omega\in\{0.8,1,1.2\}.
\]

6 anchors。

若 speed 和 turn-rate 都提高 flexibility value：

可以用：

\[
\boxed{\text{mobility–adaptation complementarity}}
\]

若只有 speed：

只写：

\[
\boxed{\text{speed–adaptation interaction}}
\]

---

# 29. Phase G — Horizon robustness

只做：

\[
T\in\{4,6,8\}
\]

的 6 anchors。

不要全 sweep。

重点：

\[
\operatorname{sign}(M)
\]

和 effect order。

---

# 30. Phase H — Leader–Follower vs Rigid

LF 为主。

Rigid 只做 6 anchors。

如果：

\[
M^{LF}
\]

和：

\[
M^{Rigid}
\]

同号：

> result robust to formation representation。

如果不同：

不要掩盖。

可解释：

> formation bending changes the ability to exploit replanning for tracking moving favorable geometry.

---

# 31. 理论模块 1：Policy-set monotonicity

保留 v12 已成立结果：

若：

\[
\Pi_B^C\subseteq\Pi_B^F,
\]

则：

\[
V(\Pi_B^F,\Pi_R)
\ge
V(\Pi_B^C,\Pi_R).
\]

---

# 32. 理论模块 2：Bilateral decomposition

保留：

\[
V_{CC}-V_{FF}
=
(V_{FC}-V_{FF})
-
(V_{FC}-V_{CC}).
\]

但把它作为：

> why bilateral Commitment has no fixed sign

而不是新主 empirical claim。

---

# 33. 理论模块 3：Increasing Differences / Complementarity

主理论目标：

对于固定 opponent structure \(\kappa_R\)：

\[
\boxed{
[
V(F,\kappa_R;v_H)-V(C,\kappa_R;v_H)
]
\ge
[
V(F,\kappa_R;v_L)-V(C,\kappa_R;v_L)
]
}
\]

这就是：

\[
M_B^{\kappa_R}\ge0.
\]

---

# 34. 不要企图直接证明完整 naval model 的全局 theorem

优先建立 reduced tracking model。

例如 state：

\[
e_t
=
\text{distance / tracking error to favorable set}.
\]

dynamics：

\[
e_{t+1}
=
\Phi(e_t,d_t,u_t;v),
\]

其中：

\[
d_t
\]

为 favorable-set drift。

假设：

1. higher mobility weakly enlarges feasible correction；
2. feedback can condition on realized drift；
3. commitment cannot；
4. stage payoff decreases with tracking error；
5. mobility expansion has increasing returns when control can react to drift。

证明 reduced-model：

\[
M\ge0.
\]

然后明确：

> full LF formation game is numerical instantiation, not directly covered by every sufficient condition.

这比强行证明完整海战 theorem 更可信。

---

# 35. Q1 方法学故事

若成功，真正的 Q1 story 不是：

> “快船更喜欢短 Commitment”。

而是：

\[
\boxed{
\text{Control authority and information are complements.}
}
\]

具体到本文：

\[
\boxed{
\text{Mobility}
\rightarrow
\text{better tracking of a moving favorable set}
\rightarrow
\text{higher marginal value of adaptation}
}
\]

这才是 abstract/general contribution。

---

# 36. 论文重写必须延后

**当前不要让本地 AI 同步重写主论文。**

只允许：

- 创建 v13 experimental branch；
- 写实验设计文档；
- 维护结果日志；
- 补文献笔记；
- 写 theorem scratchpad。

禁止覆盖：

```text
main manuscript
abstract
title
contribution list
```

直到：

```text
V13_Q1_GATE.md
```

明确为：

```text
Q1-STRONG
```

或：

```text
Q1-CONDITIONAL
```

---

# 37. Q2 fallback branch

保留：

```text
manuscript_q2_frozen/
```

基于 v11/v12：

- path-integrated exposure；
- structural closed-loop results；
- leader–follower model；
- delayed threat；
- honest negative range-Commitment result；
- external engine case study。

v13 FAIL 后直接回这里投稿。

---

# 38. 成功后论文结构

仅 Q1 Gate 通过后：

1. Introduction
2. Related Work
3. Directional Formation Game
4. Path-Integrated Geometry
5. Adaptation Rights and Information Structures
6. Mobility–Flexibility Complementarity
7. Tracking a Moving Favorable Set
8. Robustness and Boundaries
9. Delayed Threats
10. External Rules-engine Case Study
11. Discussion
12. Conclusion

---

# 39. 新核心图

## Fig A — Moving favorable set

敌方转向前后：

\[
\mathcal G_\alpha(t)
\to
\mathcal G_\alpha(t+1).
\]

叠加：

- slow reachable set；
- fast reachable set。

这是用户原始直觉的概念图。

## Fig B — 2×2 factorial

固定 opponent：

| own mobility | committed | flexible |
|---|---:|---:|
| low | \(V_{LC}\) | \(V_{LF}\) |
| high | \(V_{HC}\) | \(V_{HF}\) |

interaction：

\[
M=(V_{HF}-V_{HC})-(V_{LF}-V_{LC}).
\]

这张图比 FF/FC/CF/CC 更直接解释新主假设。

## Fig C — Exact mobility–flexibility curves

\[
v
\]

vs

\[
\mathcal F(v).
\]

## Fig D — Mechanism

\[
\Delta\Theta
\]

vs

\[
M.
\]

## Fig E — Held-out confirmatory forest plot

12 个预冻结 comparisons。

---

# 40. Related Work 重点更新

只新增真正服务新主线的文献：

- value of feedback / information；
- open-loop vs feedback dynamic games；
- mobility / pursuit-evasion speed asymmetry；
- moving-target tracking；
- receding/moving-horizon games；
- extensive-form zero-sum / sequence form；
- information-control complementarity / increasing differences。

不要增加无关海战史文献。

---

# 41. 最终 V13 Advisor Report 必须回答

1. v12 solver 是否保持 regression pass？
2. v13 是否完全没有使用 old pose cache？
3. 新 \(M_B^F,M_B^C\) 是否真正固定 opponent conditions？
4. discovery 中 \(\mathcal F(v)\) 是否随 own mobility 上升？
5. player-swap 是否成立？
6. held-out 12 comparisons 有多少 \(M>0\)？
7. 三种 geometry 是否都有支持？
8. exact Grid-3 / Grid-5 是否同方向？
9. Grid-7 anchors 是否稳定？
10. turn-rate robustness 是否支持“mobility”而非仅 speed？
11. favorable-set drift 是否稳定可测？
12. tracking ability \(\Theta\) 是否解释 \(M\)？
13. T=4/6/8 是否稳定？
14. LF / rigid 是否稳定？
15. 是否存在 multiple strong reversals？
16. Q1-STRONG / CONDITIONAL / FAIL？
17. 是否允许重写主论文？
18. 是否值得按中科院一区选刊？
19. 如果失败，是否立即切回 Q2 fallback？
20. 是否 STOP EXPERIMENT EXPANSION？

---

# 42. 最后原则

v12 已经证明一件非常重要的事：

\[
\boxed{
\text{“谁更需要 flexibility”不能通过换一个 bilateral decomposition 名字来救。}
}
\]

v13.1 必须研究一个真正新的 interaction：

\[
\boxed{
\text{同一玩家、同一对手、同一几何、同一 horizon，
只改变自己的 mobility 与自己的 adaptation rights。}
}
\]

如果：

\[
\boxed{
\text{Mobility increases the marginal value of adaptation}
}
\]

在：

- exact finite game；
- held-out tests；
- tracking mechanism；
- grid / horizon / turning robustness；

中同时成立，

这才是有资格替代旧 Commitment、用于冲击中科院一区的新核心贡献。
