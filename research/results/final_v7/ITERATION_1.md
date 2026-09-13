# ITERATION REPORT — 1 (v7 收口周期启动)

## 1. Current paper main line
Path-integrated anisotropic formation game (adversarial trajectory
optimisation for moving line-ahead formations) + closed-loop structural
degeneracy + delayed threat. Commitment 与 engine validation 的地位由
MUST-1 / MUST-2 结果决定（本轮正在跑）。

## 2. Current stage
写作主导 + 两个核心实验收尾。STOP-EXPANSION 纪律已生效：只跑 MUST-1 /
MUST-2，无任何新主线。

## 3. Research question
MUST-1: commitment–range comparative statics 是真实编队级结果，还是有限
人工 plan library 的离散化假象（B8 不收敛）？
MUST-2: 低维编队级 OR 模型的 sign / ranking / mechanism direction 能否在
更复杂的规则引擎中重现？

## 4. Hypothesis
MUST-1: H1 ηr=1 ⇒ P_H≈0；H2 ηr>1 ⇒ P_H>0；H3 ηr<1 ⇒ P_H<0。
MUST-2: surrogate 编队博弈值 V_surr 的符号与引擎 axis margin 符号一致
（≥80%），排序 ρ≥0.60，成对排序 ≥75%。

## 5. Formation-level mathematical definition
玩家 i = rigid line-ahead 编队（3 舰，间距 2 hex）：
  x_ik(t) = c_i(t) + R(ψ_i(t)) p_ik,  p_ik=(0,-ℓk)
整队火力聚合：F_i(x,t) = Σ_k K_ik；payoff 为路径积分目标
  J(τ_B,τ_R) = Σ_t γ^t [P_{B→R}(t) − λ P_{R→B}(t)], λ=1
策略 = 开环转向率表 τ_i（分段常数，K∈{3,4,6} 段），速度固定（v7 4.4
第一版）。

## 6. Files read
research/geometry/committed_game.py, firepower_kernel.py,
research/policies/geometry_policy.py, research/experiments/e06 (机制),
paper_v4/main.tex, OVERNIGHT_FINAL_REPORT.md。

## 7. Files changed
- research/experiments/must1_formation_do.py（新增，编队级 DO）
- research/experiments/must2_matched_engine.py（重写为 v7 规格）
- paper_v7/main.tex（新副本：编队化 §2、+5.14 改口径、3 处 optimal 措辞、
  fig:b5/prop:deg/sec:kernel 修复、MUST-2 节骨架）
- research/results/final_v7/claim_registry.yaml
- /tmp/progress.sh（进度条）

## 8. Solver / experiment design
MUST-1: Double Oracle——restricted payoff M_ij=J(τ_i,τ_j) 精确 LP 均衡；
连续 multi-start BR（own-plan seeding 保证 gap≥0）；27 格网格（3 几何 ×
ηr∈{0.8,1,1.2} × ηv∈{0.8,1,1.2}）+ 3 个 B7/B8 旧锚点格 + K 细化；
H∈{1,2,3,4,6}；147 jobs 并行（4 workers）。
MUST-2: 2×2 臂（F-F/R-R/R-F/F-R），3v3 编队场景（对称 ca-american-1942），
12 格（3 几何 × 2 射程 × 2 初速）× 100 配对 CRN 种子，4800 局（2 workers）。

## 9. Pre-specified gate
MUST-1: g = BR_B(π_R) − BR_R(π_B)（仅称 approximate BR gap）；
g/max(1,|V|)<5% 或连续 3 轮 |ΔV|/max(1,|V|)<2%；多起点；K 细化；
几何重复 ≥2/3；ηr≠1 格 ≥80% 符号稳定 ⇒ PASS-STRONG。
MUST-2: sign ≥80%、Spearman ρ≥0.60、pairwise ordering ≥75% ⇒ PASS；
sign ≥60% 且 ρ≥0.40 且 ordering ≥55% ⇒ PARTIAL；否则 FAIL。

## 10. Results
（运行中——ITERATION_2 填写）

## 11. Convergence diagnostics
（运行中）

## 12. Effect sizes / CI
（运行中）

## 13. Failure cases
- 首版 MUST-1（单舰级、旧 BR 符号、LP 等式约束把值变量卷入单纯形）发现
  三个数值 bug，全部修复并以 matching-pennies + 检验性插桩验证；
  own-plan seeding 使 approximate BR gap 在构造上 ≥0。
- MUST-2 首版几何错置（axis heading 误用 ally heading）+ gunnery 空批次
  （无人开炮）—— 修正后重跑。
- 旧单舰 MUST-1 与崩溃的 MUST-2 数据作废（未进入任何结果文件）。

## 14. Claim status
见 claim_registry.yaml：+5.14 "feedback advantage" REMOVE（改为
policy-class gap）；"coverage beats damage" REMOVE；commitment 与 engine
两条 PROVISIONAL 待 MUST 结果落地。

## 15. Does this change the main line?
否。主线（Path-integrated formation game + degeneracy + delayed threat）
不依赖 MUST 结果；MUST 只决定 commitment 章节定位与 engine 章节定位。

## 16. PASS / CONDITIONAL / FAIL
待定（MUST-1/MUST-2 运行中）。

## 17. Next allowed task
等待两个 MUST 完成 → 按 v7 4.9 / 5.6 冻结判定 → 更新论文 §5/§9、Abstract、
Conclusion → ITERATION_2 → 打包。禁止任何新实验方向。

## 18. Manuscript sections updated
§2 General Formation Model（编队形式化 x_ik、F_i=ΣK_ik）；
§1 contributions（编队口径 + commitment 改为"待 MUST-1 判定"）；
§8 +5.14 改口径（cross-policy comparison / policy-class gap）；
新增 §9 骨架 Matched External Engine Validation (MUST-2)；
3 处 "optimal" → best-response/object-of-optimisation；
fig:b5、prop:deg、sec:kernel 引用修复；编译通过（12 页）。

## 计数器
v7 周期 0/20 → 启动（本轮）。
