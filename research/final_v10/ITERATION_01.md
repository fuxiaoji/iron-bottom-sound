# ITERATION 01 — v10 Leader–Follower 编队升级

## 1. Current task
实现 leader–follower 路径跟随编队、完成 8 项单元测试、9 格 rigid-vs-LF 桥接、
LF 精确认证（18 格 × Grid-5/Grid-7）、reposition 与 delayed-threat 代表性格
抽查，并把论文从"刚性编队"改写为"一般编队映射 + LF 主数值实例"。

## 2. Why this task is necessary
v9 的刚性编队是 $x_{ik}=c_i+R(\psi_i)p_{ik}$：整队像刚体一样旋转。急转弯时
后续舰会随领舰同时改变位置与航向，等价于不真实的横向扫动。真实纵队是
"领舰生成航迹、后续舰按固定沿航迹距离依次通过同一轨迹"。v10 回答：
**刚性编队的核心 comparative statics 在 path-following 动力学下是否成立？**

## 3. Formation model used
主模型 leader–follower（路径跟随）；rigid 保留为 baseline。IBS 引擎作为
external case study（其规则本身更接近轨迹跟随，未重跑）。

## 4. Mathematical definition
$x_{ik}(t)=\mathcal G_{ik}(\mathcal H_i(t))$（一般映射）；两个实例：
rigid $\mathcal G^R=c_i+R(\psi_i)p_{ik}$；
LF $\mathcal G^{LF}=\gamma_i(s_i-\ell_k)$，$\psi_{ik}=\arg\gamma_i'(s_i-\ell_k)$，
$\ell_k=(k-1)d$。数值上把每回合细分为 $n_{sub}=6$ 子步，站点间距 $v/n_{sub}$，
$M+q$ 索引保存站点 $q$，起始前向航迹由初始航向直线外推（避免后续舰叠在领舰上）。

## 5. Files read
v10 计划；research/final_v9/*（v9 冻结基线）；research/formation/ 旧接口；
research/experiments/t1_exact_discrete_certification.py（复用认证机械）。

## 6. Files changed
- research/formation/path_following.py（**新建**：LeaderPath、FormationGameLF、
  RigidLineAheadGame、batch_payoff_lf、make_lf_game 工厂）
- research/final_v10/formation_tests/run_unit_tests.py（**新建**，8 项测试）
- research/experiments/v10_bridge.py、v10_commitment_lf_exact.py、
  v10_sensitivity.py（**新建**）
- research/final_v10/figures/make_figures_v10.py（**新建**：Fig1 弯曲编队、
  Fig4 用 LF 数据、Fig7 表示鲁棒性）
- paper_v10/main.tex（**新建**：General Model → 一般映射；Naval → LF；
  rigid 降级为 baseline；新增 Formation Representation Robustness 节；
  层表；Related Work 增 leader–follower 类；Abstract 增一句）
- research/final_v10/claim_registry_v10.csv（新增 formation_model 字段）
- research/final_v10/v9_baseline/V9_FREEZE.{md,json}（v9 冻结，含哈希）

## 7. Pre-specified experiment design
桥接：6 核心格（3 几何 × ηr∈{0.8,1.2}，ηv=1.0）+ 3 预设 stress 格
（crossing/1.2/1.2、crossing/0.8/0.8、crossing/1.0/1.2），不得事后挑选。
认证：与 v9 完全相同的冻结网格（Grid-5 5^6、Grid-7 7^6）、完整混合策略、
穷举全空间 BR、H=1 完整矩阵精确解。敏感度：三类转向严重度 × 3 格；
威胁用 3 档覆盖 × 2 档强度的延迟威胁带。

## 8. Results
- **单元测试 8/8 通过**：直线等价（误差 0）、沿航迹间距（|Δd|≤0.0034）、
  等曲率圆弧（弦长 1.9966 vs 1.9955；航向展布 26.7° = ω·L/v，rigid 为 0）、
  无横向跳变（≤ v）、航向=切线（误差 0）、旋转/平移等变（1e-15）、
  编队次序保持、子步细化（6 vs 12 子步，J 变 1.5%）。
- **桥接：9/9 符号一致，Kendall τ=0.944（ρ=0.983），量级中位偏差 8.1%** →
  判定 **ROBUST**。几何差异真实存在：最大编队形状误差 7.18 hex、
  场偏差 15–18%，$\chi_F=\kappa L_F$ 0.58–0.87。
- **LF 精确认证：Grid-5 18/18 符号认证、0 反转；Grid-7 全 18 格 0 反转；
  每几何 3 正 3 负** → **LF-CORE-STRONG**。**rigid 与 LF 认证符号 18/18 一致**，
  逐格量级差约 8%。
- 敏感度：reposition 代价的趋势**表示依赖**（rigid 非单调、LF 随严重度递减）；
  延迟威胁机制中"薄威胁→零收缩"与"覆盖单独不改变收缩"两性质在两表示均成立，
  强度敏感度 LF 更平缓、rigid 更陡。

## 9. Rigid-vs-LF differences
- 位置：同一领舰航迹下，跟随模型与刚性模型的舰位差最大 7.18 hex。
- 场：归一化 L1 场偏差 15–18%。
- 代价：reposition 趋势改变（见上）；commitment 符号不变、量级差约 8%。

## 10. Numerical convergence
认证沿用 v9 机械：H=1 每格精确（LB=UB）；Grid-5/Grid-7 的 DO 迭代收敛，
逐格报告界宽与 gap。子步细化已做 dt 敏感性（1.5%）。

## 11. Sign / rank / magnitude changes
符号：**无变化**（桥接 9/9、认证 18/18）。秩：τ=0.944。量级：约 8%。

## 12. Claims affected
见 claim_registry_v10.csv：C5 改为 leader_follower 且 LF-CORE-STRONG；
新增 C5b（两表示符号一致）、C5c（桥接秩一致）、C14（reposition 趋势
表示依赖，NARROW）。C2/C3/C4 标注为 theory_general（不依赖编队表示）。

## 13. Manuscript sections updated
§3 General Formation Game（一般映射 + 两个实例）、§9 Naval Instantiation
（LF 主模型 + rigid baseline + 层表）、新增 §Formation Representation
Robustness、Related Work 增 leader–follower 类（+2 文献）、Abstract 增一句。

## 14. Figures updated
Fig1 改为弯曲纵队示意（领舰航迹 + 沿航迹偏移 + 各舰局部航向 + 火力场）；
Fig4 改用 LF 精确认证结果并标注 rigid 不一致符号；新增 Fig7（三面板：
形状对比 / χ_F 与误差 / P6 两表示散点）；全部矢量 PDF + 300dpi PNG。

## 15. KEEP / NARROW / REMOVE
- KEEP：C1–C4（理论/框架）、C5b/C5c（表示鲁棒性）、C5d、C6、C7、C12、C13。
- NARROW：C8（跨策略排序）、C14（reposition 趋势表示依赖）。
- REMOVE：C9（作为 validation）、C10（+5.14 feedback advantage）、
  C11（coverage beats damage）。
- C5：**LF-CORE-STRONG**。

## 16. Next allowed task
arXiv v1 打包 + 期刊模板适配（待目标期刊）。**STOP EXPERIMENT EXPANSION。**
