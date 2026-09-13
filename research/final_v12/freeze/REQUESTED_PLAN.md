# Iron Bottom Sound v12.0 — Commitment Revival / Q1 Attack Plan
## 最后一次允许的“Commitment 复活攻关”：先纠错，再重定义，再用精确博弈验证
### 适用基准：v11 matched-horizon 结果已经完成，当前 Commitment 被 REMOVE-CORE

> **目标不是“把结果做正”**。目标是回答：
>
> 1. v11 的负结果中，有多少来自求解器/缓存/均衡选择误差？
> 2. 即使求解器修正后，原来的“双方同时长期承诺”指标是否本来就不是一个应该有单调符号的对象？
> 3. 能否把 Commitment 重构成更一般、更理论化的 **value of flexibility / information-structure** 问题，并得到可证明、可精确求解、可外推的结果？
>
> 只有第 3 条成功，Commitment 才真正“复活”为论文核心，而且才有把论文从“扎实 Q2”向 Q1 冲击的意义。
>
> **纪律**：
> - 不允许换参数只为了让结果变正；
> - 不允许删除反向 cell；
> - 不允许继续使用未通过对称控制的 solver；
> - 不允许把 post-hoc 发现包装成 preregistered；
> - 新假设必须在新 confirmatory grid 运行前冻结；
> - 如果所有复活路线失败，永久删除 Commitment，不再继续救。

---

# 0. 为什么 v11 还不能被解释成“Commitment 已被证伪”

v11 修正了 v10 最大的问题：

\[
P_6=V_6-V_1
\]

同时改变评价 horizon 和承诺长度。

v11 改成固定：

\[
T=6
\]

只改变 replanning cadence：

\[
h\in\{1,2,3,6\},
\]

并定义：

\[
C_h=V_T^{(h)}-V_T^{(1)}.
\]

这个定义比 v10 正确。

但是 v11 的 symmetric control：

\[
\eta_r=\eta_v=1
\]

出现：

- head-on：约 \(+1.03\)，CI 跨 0；
- crossing：约 \(+6.14\)，CI 显著 \(>0\)；
- parallel：约 \(-2.66\)，CI 显著 \(<0\)。

在严格交换对称的零和初态下，同样的 policy structure 施加给双方时，理论上应有：

\[
V(h,h)=0
\]

（或数值误差量级接近 0）。

因此当前 v11 的非零 \(C_6\) 至少包含：

\[
\boxed{\text{algorithmic / equilibrium-selection bias}}
\]

而且量级与 asymmetric cells 的 effect 同阶。

所以当前正确状态是：

```text
Commitment claim in manuscript: REMOVE
Scientific status: INCONCLUSIVE pending solver audit
```

---

# 1. 目前代码中必须先修的两个具体问题

## 1.1 Leader–Follower cache key 不是完整状态

当前 cache key 主要包含：

- 领舰当前位置；
- 领舰当前 heading；
- 当前 head index。

但 Leader–Follower 后舰位置由过去一段航迹决定：

\[
x_k(t)=\gamma(s(t)-\ell_k).
\]

两条不同历史路径可能到达几乎相同的：

\[
(x_L,y_L,\psi_L)
\]

但后舰仍然处于不同位置/朝向。

所以：

\[
\boxed{\text{leader pose 不是 LF 模型的完整 Markov state}}
\]

当前跨 seed / 跨 epoch cache 可能错误复用 payoff arrays。

### 修复

新增：

```python
full_lf_state_fingerprint()
```

至少 hash：

- Blue 最近 \(L_F+\) margin 的 station buffer；
- Red 最近 \(L_F+\) margin 的 station buffer；
- head indices；
- speeds；
- spacing / n_ships；
- current remaining horizon R；
- action grid ID。

推荐：

```python
blake2b(
    np.ascontiguousarray(relevant_station_buffer).view(np.uint8)
)
```

不要再：

```text
round(x, 0.01)
round(y, 0.01)
round(psi, 0.1 deg)
```

作为科学结果 cache key。

### 三种模式必须同时实现

```text
cache_mode = off
cache_mode = exact_history
cache_mode = old_pose_key   # 只用于复现 v11
```

---

## 1.2 对称博弈的 equilibrium selection 没有强制交换对称

对于 skew-symmetric payoff matrix：

\[
A=-A^\top,
\]

value 为 0。

如果 \(x\) 是 row 的 maximin strategy，则它也是 column 的 minimax strategy。

但当前实现：

- row LP 单独求 \(x\)；
- column LP 单独求 \(y\)；
- LP 在多重 equilibrium 时可能返回不同 basic solution；
- Double Oracle 又分别把 Blue BR 和 Red BR 加到 X/Y；
- X 与 Y 可能逐渐分叉。

因此即使 full game 对称，**restricted solver 本身可能选择一个不交换等变的 policy mapping**。

这会导致 receding rollout 中：

\[
E[J]\neq0
\]

即便每个局部 matrix value 约为 0。

### 修复：Symmetry-Preserving DO

在 player-exchange symmetric state：

1. 使用共同策略集：
   \[
   X=Y=S.
   \]

2. restricted matrix 强制按同一策略排序构造。

3. 验证：
   \[
   \max|A+A^\top|<10^{-10}.
   \]

4. 只求一个 maximin mixture \(p\)。

5. 同时令：
   \[
   x=y=p.
   \]

6. 计算 Blue BR 与 Red BR。

7. 将两者的 union 全部加入同一个：
   \[
   S.
   \]

8. 下一轮继续保持：
   \[
   X=Y.
   \]

### 更一般的 swap-equivariant solver

定义 player swap：

\[
\mathcal S(s).
\]

实现 canonical orientation：

```text
canonical(s)
```

对：

\[
s,\mathcal S(s)
\]

只求解一次。

另一个状态的策略通过 player swap / action mirror 映射得到。

这样 solver 本身满足：

\[
\pi_B(s)
=
\mathcal M[\pi_R(\mathcal S s)].
\]

---

# 2. Double Oracle 必须从“固定迭代数”改成“收敛驱动”

v11 主实验：

```text
Grid-5: max 15 iterations
Grid-7: 6 iterations
```

不能作为最终 Q1 级结果的求解标准。

每个 remaining-horizon game 已经能够在完整有限策略空间上 exhaustive best-response，因此可以得到：

\[
LB\le V^\star\le UB.
\]

必须使用：

\[
g_{\rm rel}
=
\frac{UB-LB}{\max(1,|V|)}
\]

驱动停止。

## Audit 标准

对 symmetric control：

\[
g_{\rm rel}<0.5\%
\]

或 absolute：

\[
UB-LB<0.1
\]

取更严格者/根据 payoff scale 预冻结。

对主实验：

\[
g_{\rm rel}<1\%
\]

推荐。

最大迭代：

```text
200
```

如果仍未达到：

```text
SOLVER_NOT_CONVERGED
```

该 state 的 policy 不允许进入最终科学统计。

**不能到 iteration cap 后仍假装 equilibrium。**

---

# 3. 将“统计误差”和“求解器误差”分开

v11 的 bootstrap CI 只覆盖：

> mixed equilibrium sampling variance。

不覆盖：

> equilibrium approximation error。

v12 必须每个 replan epoch 报告：

\[
LB_t,\quad V_t,\quad UB_t,\quad g_t.
\]

然后构造保守的 episode solver-error budget。

最简单可以报告：

\[
E_{\rm solver}
=
\sum_t(UB_t-LB_t).
\]

如果：

\[
|C_6|
\le
E_{\rm solver}
\]

则该 cell 不允许称 sign-resolved。

最终一个 result 必须同时有：

```text
Monte Carlo CI
solver-error bound
```

而不是只看 CI。

---

# 4. Phase A — Commitment Solver Audit
## 这是所有“救 Commitment”实验之前的硬 Gate

只跑：

```text
eta_r = 1
eta_v = 1
geometry = head_on / parallel / crossing
T = 6
Grid-5
h = 1,2,3,6
```

---

## A1. Cache ablation

每个 symmetric geometry 跑：

```text
old_pose_key
exact_history
cache_off
```

固定相同 solver tolerance。

比较：

\[
C_h.
\]

### 判据

`exact_history` 与 `cache_off`：

\[
|\Delta C_h|<0.1
\]

或相对 tolerance。

如果 old cache 与新 cache 明显不同：

> v11 的一部分结果被 cache contamination 污染。

---

## A2. DO convergence sweep

对三个 symmetric cells：

```text
gap_tol ∈ {5%, 2%, 1%, 0.5%}
max_iters ∈ {15, 30, 60, 120, 200}
```

画：

\[
C_6
\quad vs\quad
g_{\rm rel}.
\]

真正想验证：

\[
g_{\rm rel}\to0
\Rightarrow
C_6\to0.
\]

---

## A3. Symmetry-preserving solver

比较：

```text
ordinary independent LP equilibrium
vs
symmetry-coupled equilibrium
```

要求三个 symmetric controls：

\[
|C_6|<0.25
\]

且 CI 包含 0。

最好：

\[
|C_6|<0.1.
\]

---

## A4. Metamorphic player-swap test

对随机生成的 100 个 reachable LF histories：

\[
J(s,\tau_B,\tau_R)
\]

和：

\[
J(\mathcal Ss,\mathcal M\tau_R,\mathcal M\tau_B)
\]

检查：

\[
J(\mathcal Ss,\ldots)
=
-J(s,\ldots).
\]

要求 max error：

\[
<10^{-8}
\]

或数值容差。

---

## A5. Vectorized vs scalar payoff

不是只测试初始 state。

从真实 rollout 中采 100 个 path-history states，

随机计划对：

\[
(\tau_B,\tau_R).
\]

比较：

```text
batch_interval_payoff
scalar_interval_payoff
```

要求：

\[
|J_{\rm batch}-J_{\rm scalar}|<10^{-8}
\]

或严格合理 tolerance。

---

# 5. Solver Audit Stop Gate

只有满足：

- [ ] cache_off ≈ exact_history；
- [ ] symmetric \(C_h\) 全部接近 0；
- [ ] swap metamorphic tests 全通过；
- [ ] vectorized/scalar 全通过；
- [ ] solver gap 达标；
- [ ] symmetry-coupled solver 不再产生明显 bias；

才允许继续。

如果仍然：

\[
|C_6^{sym}|\gtrsim1
\]

或者显著非零，

则：

\[
\boxed{\text{STOP Commitment permanently}}
\]

不再救。

---

# 6. Phase B — Exact Grid-3 Gold Standard
## 不依赖 Double Oracle / Monte Carlo 的小规模“真值实验”

即使 Phase A 通过，也需要一个完全不同算法的 gold standard。

使用：

\[
\mathcal A_3=\{-1,0,1\}.
\]

固定：

\[
T=6.
\]

总 joint action histories：

\[
(3\times3)^6
=
9^6
=
531441.
\]

这个规模可以做 exact backward induction / complete enumeration。

---

# 7. Same-cadence exact block game

对于：

\[
h\in\{1,2,3,6\},
\]

每个 block 开始时双方同时选择长度：

\[
\min(h,R)
\]

的 sealed plan。

执行 block 后观察状态，再进入下一 block。

定义 exact value：

\[
W_t^{(h)}(s).
\]

递推：

\[
W_t^{(h)}(s)
=
\operatorname{val}_{\tau_B,\tau_R}
\left[
R_h(s,\tau_B,\tau_R)
+
W_{t+h}^{(h)}(s')
\right].
\]

其中：

\[
R_h
\]

为该 block 的累计 interval payoff。

由于 T=6、Grid-3，小树可完整求解。

这样得到：

\[
\boxed{
V^{exact}_{h}
}
\]

不需要 Monte Carlo，不需要 restricted-set DO。

---

# 8. Exact Grid-3 首先做 3 个 symmetric controls

必须得到：

\[
V^{exact}_{h}=0
\]

到数值 tolerance：

\[
10^{-8}\sim10^{-6}.
\]

若 exact Grid-3 自己不为 0：

> 模型或 game-tree 实现仍有错误。

---

# 9. 然后做 6 个 asymmetric anchors

```text
3 geometries
× eta_r {0.8,1.2}
× eta_v = 1.0
```

计算：

\[
C_6^{exact}
=
V_{h=6}^{exact}
-
V_{h=1}^{exact}.
\]

---

# 10. 这里有两条分支

## Branch B1：原 range-sign pattern 回来

如果至少：

\[
5/6
\]

anchors 满足：

\[
\operatorname{sign}(C_6)
=
\operatorname{sign}(\eta_r-1)
\]

且对称 controls 精确归零：

> 说明 v11 负结果主要由 solver bias 造成。

进入 Phase C：

> 复活原 bilateral commitment comparative statics。

---

## Branch B2：exact Grid-3 仍然正负混杂

这时不要再救原简单规律。

但 Commitment 仍可以用**更强的理论框架复活**：

\[
\boxed{\text{Value of Flexibility / Adaptation Rights}}
\]

进入 Phase D。

---

# 11. 为什么“双方同时 commitment”本来就可能没有单调符号

v11 比较：

\[
V(6,6)-V(1,1).
\]

这里两个玩家**同时失去灵活性**。

从 Blue maximizer 的角度：

- Blue 失去 flexibility → 对 Blue 不利；
- Red 失去 flexibility → 对 Blue 有利。

所以净效应天然是两项的差：

\[
\boxed{
\text{benefit from opponent losing flexibility}
-
\text{cost of own lost flexibility}
}
\]

因此 sign 本来就可能正负变化。

这不是“Commitment 没有意义”。

恰恰说明旧指标把两种相反机制混在一起了。

---

# 12. Phase D — 把 Commitment 重构成“Value of Flexibility”
## 这是最推荐、最可能形成 Q1 级新贡献的路线

定义一般 value：

\[
V(\Pi_B,\Pi_R),
\]

其中：

\[
\Pi_i
\]

是玩家 \(i\) 允许使用的 policy class。

令：

\[
\Pi_i^F
\]

为 flexible / feedback-capable policy class，

\[
\Pi_i^C
\]

为 committed policy class。

满足：

\[
\Pi_i^C
\subseteq
\Pi_i^F.
\]

---

# 13. Proposition A — Own flexibility cannot hurt

Blue 为 maximizer：

\[
\boxed{
V(\Pi_B^F,\Pi_R)
\ge
V(\Pi_B^C,\Pi_R).
}
\]

定义 Blue flexibility value：

\[
\boxed{
F_B
=
V(\Pi_B^F,\Pi_R^C)
-
V(\Pi_B^C,\Pi_R^C)
\ge0.
}
\]

---

# 14. Proposition B — Opponent flexibility cannot help Blue

Red 为 minimizer：

\[
\boxed{
V(\Pi_B,\Pi_R^F)
\le
V(\Pi_B,\Pi_R^C).
}
\]

定义 Red flexibility value（从 Red 自身角度的收益）：

\[
\boxed{
F_R
=
V(\Pi_B^F,\Pi_R^C)
-
V(\Pi_B^F,\Pi_R^F)
\ge0.
}
\]

---

# 15. Proposition C — Bilateral commitment decomposition

定义：

\[
V_{FF}
=
V(\Pi_B^F,\Pi_R^F),
\]

\[
V_{FC}
=
V(\Pi_B^F,\Pi_R^C),
\]

\[
V_{CC}
=
V(\Pi_B^C,\Pi_R^C).
\]

则：

\[
F_B
=
V_{FC}-V_{CC},
\]

\[
F_R
=
V_{FC}-V_{FF}.
\]

所以旧 bilateral commitment effect：

\[
C_{\rm bilat}
=
V_{CC}-V_{FF}
\]

满足：

\[
\boxed{
C_{\rm bilat}
=
F_R-F_B.
}
\]

这非常重要。

它解释：

> 为什么 simultaneous commitment 没有必然单调 sign。

sign 完全取决于：

> 哪一方的 flexibility 更值钱。

---

# 16. Proposition D — Symmetric game cancellation

在 player-exchange symmetric zero-sum game 下：

\[
F_B=F_R.
\]

因此：

\[
\boxed{
C_{\rm bilat}=0.
}
\]

这会把 v11 的 symmetric control 从“一个额外检查”升级成**理论必需条件**。

---

# 17. 新的真正研究问题

不要再问：

> “长期射程优势方是不是喜欢 commitment？”

改成：

\[
\boxed{
\text{Capability asymmetry changes whose flexibility is more valuable?}
}
\]

通俗版本：

> 射程短的一方是不是更依赖临场反应？
>
> 射程长的一方是不是可以更早把路线锁死而损失较小？
>
> 双方都被迫提前写死命令时，最终谁更吃亏？

这是一个比旧问题更自然的 OR / dynamic-games 问题。

---

# 18. 新的主 comparative static

例如定义：

\[
\Delta_F
=
F_{\rm disadvantaged}
-
F_{\rm advantaged}.
\]

预设假设：

\[
\eta_r\neq1
\]

时，射程劣势方：

\[
F_{\rm disadvantaged}
\]

更大。

但这是**新假设**，必须：

1. 先根据理论冻结；
2. 不用旧 18 cells 宣称 confirmatory；
3. 在新的 held-out parameter grid 上验证。

---

# 19. 为什么需要 asymmetric information-structure game

为了分别得到 \(F_B,F_R\)，需要：

\[
V_{FF},V_{FC},V_{CF},V_{CC}.
\]

其中：

- \(FF\)：双方灵活；
- \(FC\)：Blue flexible，Red committed；
- \(CF\)：Blue committed，Red flexible；
- \(CC\)：双方 committed。

注意：

> sealed plan 的未来动作不能自动让对手看到。

因此 asymmetric cadence 不是普通 matrix game，而是**finite extensive-form game with information sets**。

这反而可能成为论文真正的方法学升级。

---

# 20. Phase E — Exact Extensive-Form Solver

原项目是 sealed-order discipline。

所以建立 finite extensive-form zero-sum game：

- 每个玩家只在自己的 replanning node 选择新 plan；
- 未执行的未来 sealed actions 对对方不可见；
- 已发生的状态变化可以观察；
- 玩家记得自己的过去选择；
- perfect recall。

对于 finite perfect-recall extensive-form game，可以采用 **sequence form**；经典结果表明 sequence form 对 perfect-recall extensive games 提供线性于 game tree 大小的表示，零和情形可以转化为 LP 求解。

## 首先实现 Grid-3

\[
\mathcal A_3=\{-1,0,1\}
\]

\[
T=6.
\]

计算：

\[
V_{FF},V_{FC},V_{CF},V_{CC}.
\]

---

# 21. Sequence-form 实现要点

同时行动可以转成：

1. Blue decision node；
2. Red decision node；
3. Red 的 information set 不知道 Blue 当前 sealed choice；

从而保持 simultaneity。

对 future sealed plan：

> opponent information set 必须隐藏尚未执行的 order suffix。

只暴露：

- 当前可观察 formation state；
- 已执行动作产生的状态；
- 按原模型允许观察的历史。

---

# 22. Sequence-form Unit Tests

## E1. One-stage equivalence

T=1 时：

sequence-form value = normal-form matrix LP value。

## E2. Fully committed equivalence

\[
CC
\]

必须与完整 open-loop matrix game一致。

## E3. Fully flexible Grid-3 small horizon

T=2/3 与 brute-force backward induction 一致。

## E4. Symmetry

在：

\[
\eta_r=\eta_v=1
\]

下：

\[
V_{FF}=V_{CC}=0,
\]

且：

\[
V_{FC}=-V_{CF}.
\]

## E5. Flexibility monotonicity

必须数值满足：

\[
F_B\ge0,\quad F_R\ge0
\]

到 tolerance。

如果违反：

> solver / information-set implementation 有错。

---

# 23. Exact flexibility experiment — Discovery set

先跑：

```text
3 geometries
× eta_r {0.8,1.2}
× eta_v = 1.0
```

得到：

\[
F_B,\quad F_R,\quad
\Delta_F.
\]

此阶段叫：

```text
mechanism discovery
```

不能直接声称 confirmatory。

---

# 24. Confirmatory held-out grid
## 防止“看到结果以后改假设”

在 discovery 数据出来前，冻结新验证集。

推荐：

```text
geometry ∈ {head_on, parallel, crossing}
eta_r ∈ {0.85, 1.15}
eta_v ∈ {0.9, 1.1}
```

共：

\[
12
\]

新 cells。

这些参数与旧主 grid 不同。

若资源允许，再加：

\[
\eta_r\in\{0.7,1.3\}
\]

作为 stress anchors。

---

# 25. 新主 hypothesis 的判定

如果 hypothesis：

> range-disadvantaged side has larger flexibility value

则对镜像 pair 检查：

\[
\Delta_F>0.
\]

## Q1-STRONG

- discovery 有清晰机制；
- held-out 12 cells ≥10/12 同方向；
- 95% CI / exact bounds 不跨 0；
- 3 geometry 均支持；
- Grid refinement 不翻转；
- rigid/LF 不改变主 sign；
- exact Grid-3 与 Grid-5 approximate 同方向。

## Q1-CONDITIONAL

- 8–9/12；
- 或只在某 geometry / speed regime 稳定。

仍可保留 Commitment，但论文不写 universal law。

## FAIL

- held-out 混乱；
- 多个显著反向。

永久放弃 Commitment 作为核心。

---

# 26. Grid-5 / Grid-7 如何扩展

完整 sequence-form Grid-5 可能过大。

所以采用两层验证：

## Exact core

Grid-3 / T=6 exact sequence form。

## Fine approximation

Grid-5：

- sequence-form column generation；
- 或 symmetry-preserving extensive-form Double Oracle；
- 必须有 exploitability / duality gap。

Grid-7：

只做 6 anchors。

最终措辞：

> exact on the coarse finite game, robust under finer action discretization.

不能说：

> exact continuous game。

---

# 27. 可选 Phase F — Exact expected receding-policy evaluation

即使暂时不完成 full asymmetric sequence form，也可以先消除 Monte Carlo 噪声。

当前 equilibrium support 通常较小。

对每个 replan state：

1. 求 equilibrium mixture；
2. 对 support 的所有 plan pairs 分支；
3. 权重：
   \[
   p_iq_j;
   \]
4. 执行 h 步；
5. 递归到下一 replanning state；
6. memoize full LF state。

这样可以得到：

\[
E[J]
\]

的 deterministic expectation。

用于：

- symmetric controls；
- 6 anchor cells；
- Grid-3 / Grid-5 对照。

Monte Carlo 只保留为 independent check。

---

# 28. 可选 Phase G — “Commitment frontier” 而不是单个 \(h=1\) vs \(h=6\)

如果 flexibility decomposition 成立，

研究：

\[
h\in\{1,2,3,6\}.
\]

定义 marginal adaptation value：

\[
M_{1\to2},
M_{2\to3},
M_{3\to6}.
\]

问：

> 第一份额外灵活性最值钱，还是临近完全反馈时最值钱？

这可以形成：

\[
\text{adaptation-value curve}.
\]

但只在主 flexibility hypothesis 已成功后做。

不是 blocker。

---

# 29. 对当前 v11 sign reversals 的诊断表

新实验必须解释旧结果。

为每个旧 18 cell 计算：

```text
old C6
cache-fixed C6
symmetry-fixed C6
converged-DO C6
exact Grid-3 sign (anchor only)
```

分类：

```text
CACHE_ARTIFACT
EQUILIBRIUM_SELECTION_ARTIFACT
DO_NONCONVERGENCE
REAL_SIGN_REVERSAL
UNRESOLVED
```

这会让论文非常可信。

---

# 30. 为什么这个方向比“继续调 v11”更强

旧问题：

\[
V(6,6)-V(1,1)
\]

问的是：

> 双方同时失去灵活性后 Blue 的净收益。

它混合两种相反效应。

新问题：

\[
F_B,\quad F_R
\]

直接问：

> 每一方的临场反应权到底值多少钱？

这是一个 policy-set / information-structure 问题。

它有：

- 一般理论命题；
- 明确 monotonicity；
- 对称性 theorem；
- extensive-form exact solver；
- naval case；
- held-out comparative statics。

这才是有机会让论文从 applied Q2 走向 Q1 的结构。

---

# 31. 论文重构方案（如果 Commitment 成功复活）

推荐标题候选：

### A
**The Value of Flexibility in Directional Formation Games: Path-Integrated Exposure, Commitment, and Delayed Threats**

### B
**Commitment and Adaptation in Directional Formation Games**

副标题/正文强调 naval instantiation。

### C（保守）
**Maneuvering Formations in Directional Fields: Path-Integrated Exposure, Adaptation, and Delayed Threats**

---

# 32. 新 Contributions

如果 Q1-STRONG：

1. **Path-integrated anisotropic formation game**，证明 snapshot positional surrogate 可改变 trajectory ranking。
2. **Closed-loop structural results**：exchange-symmetry degeneracy + speed-capability monotonicity。
3. **Commitment/flexibility theory**：nested policy classes、unilateral flexibility monotonicity、bilateral commitment decomposition、symmetric cancellation。
4. **Exact/controlled computation across information structures**：finite extensive-form / sequence-form solver + action-grid refinement。
5. **Delayed threat response-space mechanism** 作为 secondary contribution。
6. Naval rules engine 只做 external case study。

如果 Commitment 只是 CONDITIONAL：

Contributions 控制到 4 条，降低其强度。

---

# 33. Commitment 章节新的结构

## 5.1 Information structures and policy classes

定义：

\[
F/C.
\]

## 5.2 Value-of-flexibility propositions

正式证明 A–D。

## 5.3 Exact finite extensive-form computation

sequence form / exact Grid-3。

## 5.4 Capability asymmetry and flexibility value

\[
F_B,F_R,\Delta_F.
\]

## 5.5 Held-out confirmatory tests

新 12 cells。

## 5.6 Formation-model robustness

rigid vs LF。

## 5.7 External engine interpretation

只有结果足够稳再做少量 case study。

---

# 34. 可视化

## Figure Commitment-1

2×2 information structure square：

```text
          Red flexible    Red committed
Blue F       V_FF             V_FC
Blue C       V_CF             V_CC
```

箭头表示：

- Blue 获得 flexibility；
- Red 获得 flexibility。

旁边显示：

\[
F_B,\quad F_R,\quad C_{\rm bilat}=F_R-F_B.
\]

这是非常重要的解释图。

## Figure Commitment-2

三个 geometry：

x：

\[
\eta_r
\]

y：

\[
F_{\rm disadvantaged}-F_{\rm advantaged}.
\]

## Figure Commitment-3

old v11 bilateral \(C_6\) vs decomposed：

\[
F_R-F_B.
\]

展示 sign reversal 为什么出现。

## Supplement

solver convergence / symmetry audit。

---

# 35. 和现有论文其它模块的关系

Commitment 复活成功后，不要重新做：

- kernel calibration；
- path-integrated reversal；
- closed-loop theorem；
- speed monotonicity；
- delayed threat 全套；
- engine 全套。

只更新：

- Introduction；
- Related Work；
- Commitment；
- Discussion；
- Abstract；
- Conclusion；
- related figures。

---

# 36. Related Work 必须新增

至少加入：

1. open-loop vs feedback dynamic games；
2. moving/receding-horizon dynamic games；
3. commitment as restriction of future action sets；
4. value of information / information structures in zero-sum games；
5. finite extensive-form zero-sum games and sequence form。

核心参考方向：

- moving horizon dynamic games；
- sequence form for perfect-recall extensive games；
- dynamic commitment games；
- value of information in zero-sum games。

不要声称这些思想本身由本文首次提出。

本文 novelty 应定位为：

> applying and extending information-structure / flexibility ideas to nonholonomic directional formation games, with structural decomposition and controlled computational evidence.

---

# 37. 为什么这才有“冲 Q1”的可能

仅仅：

> 18 个 naval cells 出现漂亮 sign

不足以把论文自动变成 Q1。

Q1 潜力来自四件东西同时成立：

### 1. General question

从：

> 海战怎么转弯

升级为：

> **动态零和博弈里，未来适应权（flexibility）值多少钱？**

### 2. Theory

有：

\[
F_B\ge0,\quad F_R\ge0
\]

和：

\[
C_{\rm bilat}=F_R-F_B,
\]

以及 symmetry cancellation。

### 3. Rigorous computation

不是 heuristic planner，

而是：

> exact finite extensive-form / sequence-form core + finer-grid robustness。

### 4. Interpretable application

Leader–Follower naval formation 提供一个非平凡、方向性、非完整运动的应用环境。

这四者结合，才有更高档期刊的理由。

---

# 38. 最终决策树

```text
Phase A solver audit
|
|-- FAIL symmetric controls
|      -> PERMANENTLY DROP COMMITMENT
|
+-- PASS
       |
       v
Phase B exact Grid-3 same-cadence game
|
|-- original range-sign returns
|      -> Branch C: revive bilateral commitment
|
+-- sign remains mixed
       |
       v
Phase D/E value-of-flexibility + sequence form
|
|-- exact discovery + held-out confirmation succeed
|      -> COMMITMENT REVIVED as FLEXIBILITY THEORY
|
+-- fail
       -> PERMANENTLY DROP COMMITMENT
```

---

# 39. Branch C — 如果原简单 Commitment 真被 solver 修复救回来

若 exact Grid-3 6 anchors ≥5/6 支持原 sign：

1. 用修复后的 Grid-5 solver 跑旧 18 cells；
2. 全部 solver gaps 达标；
3. no cache approximation；
4. symmetric controls 归零；
5. Grid-7 6 anchors；
6. T=4/6/8 anchors；
7. 新 held-out 12 cells；
8. LF / rigid bridge。

### 强 Gate

旧 18：

\[
\ge15/18
\]

方向正确，

新 held-out：

\[
\ge10/12
\]

方向正确，

无多个显著 reversal。

否则不要保留 universal sign story。

---

# 40. 什么时候停止救

任何一个：

- 对称 control 在 exact / converged solver 仍不为 0；
- exact Grid-3 与 finer grid 系统翻转；
- held-out confirmation <8/12；
- flexibility monotonicity 被数值违反；
- sequence-form unit tests 失败且无法定位；
- effect 小于 solver bound；

则：

\[
\boxed{\text{Commitment permanently removed}}
\]

之后只做投稿。

---

# 41. 建议执行顺序

```text
R0 Freeze v11
R1 Fix LF cache state
R2 Add cache-off audit
R3 Add symmetry-coupled equilibrium selection
R4 Add swap-canonical solver
R5 Convert DO to gap-driven convergence
R6 Run symmetric solver audit
R7 Exact Grid-3 same-cadence DP
R8 6 asymmetric exact anchors
R9 Decide Branch C or D
R10 If D: prove flexibility propositions
R11 Build asymmetric information-structure extensive-form model
R12 Implement sequence-form Grid-3 solver
R13 Discovery 6 cells
R14 Freeze new confirmatory hypothesis/grid
R15 Run 12 held-out cells
R16 Grid-5 finer approximation
R17 Grid-7 anchors
R18 Update rigid/LF robustness
R19 Rewrite manuscript
R20 Claim registry audit
R21 Scientific freeze
```

---

# 42. 本地 AI 每轮报告格式

```text
# COMMITMENT REVIVAL ITERATION

1. Current phase
2. Exact scientific question
3. What is being held fixed
4. What implementation changed
5. Why the change is correctness-driven
6. Unit tests
7. Symmetry tests
8. Solver gap / exploitability
9. Exact vs approximate status
10. Results
11. Negative / reversal cases
12. Does this revive the old claim?
13. Does it support the flexibility reframing?
14. Claim status
15. Next allowed step
```

---

# 43. 最终导师报告必须回答

1. v11 symmetric bias 的主要来源是什么？
2. old cache 是否污染结果？
3. independent LP equilibrium selection 是否破坏 symmetry？
4. DO 15/6 iterations 是否不足？
5. 修复后 symmetric controls 是否归零？
6. exact Grid-3 的 bilateral commitment sign 是什么？
7. 原 range-sign hypothesis 是否复活？
8. 若没有，\(F_B,F_R\) 是否都满足理论 monotonicity？
9. bilateral effect 是否满足：
   \[
   C=F_R-F_B
   \]
   ？
10. 射程劣势方 flexibility value 是否更高？
11. held-out 12 cells 是否确认？
12. sequence-form solver 是否通过全部 unit tests？
13. Grid-5 / Grid-7 是否稳健？
14. LF / rigid 是否稳健？
15. Commitment 最终是：
   - REVIVED-STRONG
   - REVIVED-CONDITIONAL
   - PERMANENTLY-REMOVE
16. 论文是否因此有新的 Q1-level methodological story？
17. 是否停止所有新实验？

---

# 44. 最终科学纪律

“救回 Commitment”允许做的：

- 修 bug；
- 提高 solver 收敛；
- 使用 exact gold-standard；
- 更准确地定义 information structure；
- 将混合机制拆成可解释组成；
- 提出新的理论问题，并在新 held-out 数据上验证。

不允许做的：

- 换 cell；
- 换参数直到正；
- 删除反向结果；
- 只汇报最好的 geometry；
- 用 post-hoc pattern 冒充 pre-specified hypothesis；
- 把 approximate solver 当 exact；
- 对 failure 不报告。

真正成功不是：

> “结果终于变正。”

真正成功是：

\[
\boxed{
\text{Commitment 被重构成一个更一般、可证明、可精确计算的
value-of-flexibility 问题。}
}
