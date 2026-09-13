你现在接手 Iron Bottom Sound / Directional Formation Game 项目的 v13.1 实验阶段。

你的任务不是“把结果做正”，也不是继续救已经被 v12 否决的 range–Commitment 假设。你的任务是严格执行 `iron_bottom_sound_v13_1_mobility_flexibility_q1_plan.md`，检验一个新的、独立的假设：

    Mobility capability × Value of Adaptation

核心问题：
在完全固定对手速度、对手 policy class、range、geometry、horizon、formation model 和 payoff 的情况下，仅提高焦点玩家自己的 mobility，是否会提高“从 committed policy class 升级为 flexible/replanning policy class”的边际价值？

必须研究的主量不是旧 bilateral Commitment，也不是跨不同 opponent policy class 比较“快方 flexibility”和“慢方 flexibility”。

正式主量是：

    F_B(v | κ_R)
      = V(F, κ_R; v, v_R)
      - V(C, κ_R; v, v_R)

其中 κ_R ∈ {F, C} 固定。

主 interaction：

    M_B^{κ_R}
      = F_B(v_H | κ_R)
      - F_B(v_L | κ_R)

等价：

    M_B^{κ_R}
      =
      [V(F,κ_R;v_H)-V(C,κ_R;v_H)]
      -
      [V(F,κ_R;v_L)-V(C,κ_R;v_L)]

只有当 opponent speed 和 opponent policy class 在 high/low mobility comparison 中完全相同时，这个 interaction 才是有效的。

========================
一、首先冻结 v12
========================

你必须先创建：

    research/final_v13/v12_freeze/

记录并保留以下已知事实，不得覆盖或重解释：

1. v12 exact symmetric controls：
   3 geometries × 4 cadence 的 12 个博弈全部约为 0，
   最大量级约 2.4e-15。

2. sequence form 已与完整矩阵 / backward induction 小规模结果一致。

3. exact-history cache 与 cache-off 同种子一致。

4. old pose-only cache 在三个 geometry 中都触发非对称矩阵错误。
   old cache 永久禁止用于 scientific results。

5. geometric canonicalization 已把 strategy equivariance error 压到约 2e-15。

6. 原 range-based bilateral Commitment hypothesis 失败。

7. 6 exact range anchors：
   只有 head-on 两个符合原符号，
   parallel / crossing 反向。

8. 12 个冻结 held-out range points：
   仅 1/12 支持“range-disadvantaged flexibility is more valuable”，
   其余 11/12 反向。

9. flexibility non-negativity 和 decomposition identity 成立。

必须生成：

    V12_FROZEN_CONCLUSIONS.md

其中明确写：

    RANGE_COMMITMENT = FALSIFIED
    RANGE_FLEXIBILITY_VALUE_HYPOTHESIS = FALSIFIED
    SOLVER_CORE = VALIDATED
    OLD_POSE_CACHE = INVALID

不得试图用 v13 修改这些历史结论。

========================
二、不要重复 v12 solver audit
========================

v13 只运行 regression tests：

- T=1 matrix equivalence；
- T=2/3 backward-induction equivalence；
- 3 symmetric geometry；
- player swap；
- flexibility non-negativity；
- old pose cache absence check。

除非 regression failure，否则不要重复完整 v12 Monte Carlo audit。

========================
三、绝对禁止现在重写主论文
========================

当前只允许：

- experimental branch；
- experiment code；
- theorem scratchpad；
- literature notes；
- result reports；
- figures marked DRAFT。

必须保留：

    manuscript_q2_frozen/

作为 v11/v12 Q2 fallback。

只有 `V13_Q1_GATE.md` 最终给出：

    Q1-STRONG

或

    Q1-CONDITIONAL

才允许重写：

- title；
- abstract；
- contribution list；
- main manuscript narrative。

========================
四、Phase A：Exact Grid-3 Discovery
========================

固定：

    eta_r = 1
    v_opponent = 1.0
    T = 6
    formation = leader_follower
    action_grid = {-1, 0, +1}

geometry：

    head_on
    parallel
    crossing

focal own speed：

    {0.70, 0.85, 1.00, 1.15, 1.30}

每个 cell 必须完整计算：

    V_FF
    V_FC
    V_CF
    V_CC

并计算：

    F_blue_given_red_F = V_FF - V_CF
    F_blue_given_red_C = V_FC - V_CC

对 mirror / Red focal side 也必须计算。

必须检查：

    F >= 0

违反即 solver bug，不进入科学解释。

必须成对做 player-swap mirror：

    Blue fast / Red baseline
    Blue baseline / Red fast

验证：

    V_swap ≈ -V

以及 interaction 等变。

========================
五、Operating speed 与 capability 必须区分
========================

先检查当前 speed 参数到底是：

A. forced operating speed
    v(t) = v_op

还是：

B. speed capability
    v(t) ∈ [0, v_max]

如果是 A：

所有主结果暂时只能称：

    operating-speed × flexibility interaction

不能写：

    mobility capability × flexibility

如果计算允许，请增加低维 speed-control action，例如：

    v / v_max ∈ {0.75, 1.0}

或：

    {0.5, 0.75, 1.0}

把真正的：

    v_max capability expansion

作为 Q1 升级版本。

如果无法做到，必须在最终论文中明确限制。

========================
六、Phase B：Moving Favorable Geometry
========================

不要把 Crossing-T 硬编码进 reward。

所有 favorable geometry 都必须从现有 directional interaction kernel 自动导出。

定义 bounded relative-state domain D。

主 favorable set：

    G_0.9(t)
      = { z in D : L(z;t) >= 0.9 L*(t) }

robustness：

    alpha = 0.8

不要把单一 argmax 作为主机制指标，因为可能多峰/跳变。

必须至少计算：

1. directed nearest-set drift
2. centroid/medoid drift
3. Hausdorff distance（supplement robustness）
4. opponent heading change

推荐主 drift：

    D_t
      = median_{z in G_t} d(z, G_{t+1})

========================
七、Reachable Correction 与 Tracking Ability
========================

对焦点玩家，给定新的 favorable set：

    G_{t+1}

定义：

    d_before = d(s_t, G_{t+1})

在一个 replanning interval reachable set R_t 中：

    d_after_min
      = min_{s' in R_t} d(s', G_{t+1})

定义：

    reachable_correction
      = d_before - d_after_min

主 tracking score 使用 bounded 形式：

    Theta_t
      = R_t / (R_t + D_t + eps)

范围应在 [0,1]。

episode level：

    Theta_bar = median_t Theta_t

原始 ratio：

    R_t / (D_t + eps)

只放 robustness，不作为主机制指标。

========================
八、机制假设
========================

重点不是单纯 F 与 speed 的相关性。

需要检验：

    mobility increase
      -> tracking ability increase
      -> flexibility interaction M increase

计算：

    DeltaTheta
    M

并至少报告：

- Spearman(M, DeltaTheta)
- geometry-stratified scatter
- simple regression with geometry fixed effects

不要使用 ML。

========================
九、Discovery 完成后必须冻结 Confirmatory Design
========================

在运行新验证参数前，生成：

    research/final_v13/confirmatory_design/CONFIRMATORY_DESIGN.md

内容必须包含：

- hypotheses
- exact parameter grid
- primary endpoints
- solver tolerances
- exclusions
- robustness rules
- success gates
- git hash

写完后不可按结果修改。

推荐 held-out own-speed ratios：

    {0.75, 0.90, 1.10, 1.25}

opponent speed：

    1.0

eta_r：

    1.0

geometry：

    3 types

对手 policy class 分别固定：

    Red F
    Red C

Primary endpoints：

    M_B^F > 0
    M_B^C > 0

Mirror 只做 symmetry check，不计入独立 held-out count。

========================
十、Q1 Gate
========================

Q1-STRONG 推荐要求：

1. held-out primary interactions ≥10/12 同方向；
2. resolved cases ≤1 个 strong reversal；
3. 3 geometries 都有正支持；
4. exact Grid-3 与 Grid-5 同方向；
5. Grid-7 anchors 不系统翻转；
6. all symmetry / monotonicity regression tests pass；
7. solver error << measured interaction；
8. DeltaTheta 与 M 有强正机制关联；
9. turn-rate robustness 不推翻；
10. T=4/6/8 不推翻。

Q1-CONDITIONAL：

- 8–9/12；
- effect 主要存在 crossing / parallel；
- head-on weak；
- no multiple strong reversals。

FAIL：

- ≤7/12；
- 多个强反向；
- exact / finer grid 不一致；
- mechanism 不支持；
- effect 依赖 forced-speed artifact；
- solver residual 与 effect 同量级。

FAIL 后立即停止，回到 `manuscript_q2_frozen/` 投稿。

========================
十一、Refinement
========================

如果 exact Grid-3 支持：

1. Grid-5：
   {-1,-0.5,0,0.5,1}

2. Grid-7：
   仅 6 pre-specified anchors

3. turn-rate robustness：
   eta_omega ∈ {0.8,1.0,1.2}

4. horizon：
   T ∈ {4,6,8}
   仅 6 anchors

5. LF vs rigid：
   仅 6 anchors

所有结果必须保留反例。

========================
十二、理论任务
========================

必须整理三个层级：

A. 已经严格成立：
   policy-set monotonicity

B. 已经严格成立：
   bilateral decomposition

C. 新目标：
   increasing differences / complementarity

对固定 opponent κ_R：

    [V(F,κ_R;v_H)-V(C,κ_R;v_H)]
    >=
    [V(F,κ_R;v_L)-V(C,κ_R;v_L)]

不要强行证明完整 naval model。

优先构造 reduced tracking model：

    state = tracking error to moving favorable set
    disturbance = favorable-set drift
    control authority = mobility
    feedback = observe drift and adapt
    commitment = cannot react until next decision epoch

如果能在合理充分条件下证明 increasing differences：

    Delta_v Delta_F V >= 0

则作为 general theorem。

完整 LF formation game 只作为 numerical instantiation。

========================
十三、每轮报告
========================

每轮保存：

    research/final_v13/ITERATION_<n>.md

固定格式：

1. Phase
2. Scientific question
3. Pre-specified hypothesis
4. Focal player
5. Opponent conditions held fixed
6. Mobility variable changed
7. Policy variable changed
8. Exact / approximate solver
9. Regression tests
10. Results
11. Reversals
12. Mechanism metrics
13. Discovery or confirmatory
14. Claim implication
15. Q1 Gate implication
16. Next allowed action

========================
十四、最终报告
========================

生成：

    FINAL_V13_ADVISOR_REPORT.md
    V13_Q1_GATE.md

必须回答：

- 是否真正固定 opponent conditions？
- 是否避免退化成 old bilateral sign？
- operating speed 还是 capability？
- exact results 是否支持 M>0？
- held-out support count？
- geometry dependence？
- tracking mechanism？
- action-grid robustness？
- turn-rate robustness？
- horizon robustness？
- LF/rigid robustness？
- theorem status？
- Q1-STRONG / CONDITIONAL / FAIL？
- 是否允许重写论文？
- 是否按中科院一区目标选刊？
- 是否立即停止实验？

========================
十五、最重要的科学纪律
========================

真正成功不是：

    “快船的结果终于更漂亮。”

真正成功是：

    “在固定对手条件下，提高本方 mobility 会提高本方 adaptation rights 的边际价值，
     并且这一 interaction 可以由追踪移动 favorable geometry 的能力解释。”

如果 exact finite game、held-out tests、mechanism 和 robustness 同时支持这一点，才允许把它升级成中科院一区冲刺的核心贡献。
