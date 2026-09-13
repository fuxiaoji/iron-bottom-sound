# ITERATION REPORT — 2 (v7 收口周期 · 最终判定)

## 1. Current paper main line
Path-integrated anisotropic formation game（编队级对抗轨迹优化）
+ closed-loop structural degeneracy + delayed threat
+ **commitment comparative statics（PASS-STRONG，核心贡献）**
+ matched engine validation（FAIL → engine 定位为 case study）。

## 2. Current stage
STOP EXPERIMENT EXPANSION 已生效。论文冻结，进入 arXiv v1 / 投稿准备。

## 3. Research question
同 ITERATION_1（MUST-1 / MUST-2 两个收口问题）。

## 4. Hypothesis
MUST-1: H1/H2/H3（P_H 符号 = sign(ηr−1)）。
MUST-2: V_surr 与引擎 margin 的 sign/ranking 一致（≥80% / ρ≥0.60 / ≥75%）。

## 5. Formation-level mathematical definition
见 ITERATION_1 §5 与论文 §2（x_ik = c_i + R(ψ_i)p_ik；F_i = Σ_k K_ik；
J = Σ_t γ^t [P_{B→R} − λ P_{R→B}]）。

## 6. Files read
research/results/final_v7/{must1_report.md, must1_aggregate.json,
must1_jobs.jsonl, must2_report.md, must2_results.json}。

## 7. Files changed
- paper_v7/main.tex（§5-result、§9、Abstract、Conclusion、Contributions
  4/6、Discussion limitations vii/viii 全部按判定填充；13 页编译干净）
- research/results/final_v7/ITERATION_2.md（本文件）
- research/goal-progress.md

## 8. Solver / experiment design
MUST-1: Double Oracle（编队级，N=3 纵队聚合火力；K∈{2,3,4,6} 段常数转向；
multi-start 连续 BR + own-plan seeding；restricted-game 精确 LP）。
147 jobs = 27 格 × H∈{1,2,3,4,6} + 3 个 B7/B8 锚点格 × H∈{1,4,6} + K 细化。
MUST-2: 2×2 臂（F-F/R-R/R-F/F-R），3v3 对称编队场景，12 格（3 几何 ×
2 射程 × 2 初速）× 100 配对 CRN 种子 = 4800 局，0 中断。

## 9. Pre-specified gate
见 ITERATION_1 §9（冻结，未改动）。

## 10. Results
### MUST-1（commitment）
- **18/18（100%）非对称 H=6 格满足 sign(P_6)=sign(ηr−1)**；3/3 几何。
- ηr<1：P_6 ∈ [−11.8, −4.8]（9/9 为负）；ηr>1：P_6 ∈ [+3.4, +14.4]
  （9/9 为正）；纯对称格 P_6≈0（机器精度，简并保持）。
- 旧锚点复现 B7 量级：ηr=1.33 → P_6=+15.5；ηr=0.75 → P_6=−7.2。
- 收敛：67%（gap gate 或 3 轮滞止）；未达格以 approximate BR gap 如实
  报告（最大 gap/V 66%，值按 solver-relative 口径）。
- K 细化：值随 K 单调上升（K=3: +6.4 → K=6: +12.0）但符号不变 ——
  与 B8 library-sensitivity 教训一致。
- 新观察（冻结规则外）：纯速度不对称（ηr=1, ev≠1）也产生承诺值，
  更快方承诺更久多数几何受损 —— 与 B3 分类一致。

### MUST-2（engine）
- **VERDICT: FAIL**。sign 75%（3/4 有符号预测格；gate ≥80%）、
  Spearman ρ=−0.08（gate ≥0.60）、pairwise ordering 63%（gate ≥75%）。
- 失败模式：head_on/crossing 的镜像对称几何上 surrogate 预测精确 0
  （简并），而六角量化引擎给出 ±1..6 的显著 margin（离散化不对称
  主导模型级小边际）；parallel 有符号格 3/4 一致，一处大幅反转
  （r12v6：模型 +11.4 vs 引擎 −5.5）。
- 匹配反馈溢价不可靠：R-F>0 仅 5/12、F-R>0 仅 1/12 —— 再次确认
  +5.1 不得读作 replanning 价值。

## 11. Convergence diagnostics
MUST-1：gap/stag 门 67%；BR gap 在构造上 ≥0（own-plan seeding）；
matching-pennies LP 检验通过；K∈{2,3,6} 符号稳定。
MUST-2：4800/4800 完成零错误；bootstrap CI 10k 次重采样。

## 12. Effect sizes / CI
MUST-1：P_6 区间见上；代表例（head_on er=1.2 ev=1.0）：V_1=0 →
V_6=+11.97（gap/V=0.5% 收敛）。
MUST-2：全部 12 格 × 4 臂的 mean [95% bootstrap CI] 见
final_v7/must2_report.md 表。

## 13. Failure cases
- MUST-2 判定 FAIL 本身（如实上报，不修改引擎/定义救结果）。
- 过程事故（均已修复且不进入结果）：场景叠加 bug（双方编队同格，
  r0=0）导致首轮 4800 局作废重跑；restricted_lp 等式约束 bug；
  BR 参数顺序 bug；L-BFGS 劣局部最优（own-plan seeding 修复）。

## 14. Claim status
- commitment-range comparative statics：PROVISIONAL → **KEEP CORE
  （PASS-STRONG）**（编队级、去库化、符号 100% 稳定；值 solver-relative）。
- engine validation：**FAIL → case study only**；B13 cross-policy
  （ρ=1.00）保留为较弱外部检查；泛化 claim 已缩小。
- "+5.14 feedback advantage"：REMOVE（改为 policy-class gap）。
- "coverage beats damage"：REMOVE（机制=coverage+intensity+response
  landscape 三者 jointly）。
- formation-level wording：全文一致（§2 形式化 + 全文清扫）。

## 15. Does this change the main line?
主线不变（Path-integrated formation game + degeneracy + delayed threat）。
MUST-1 使 commitment 升为核心贡献；MUST-2 把 engine 章降为 case study
并缩小泛化 claim —— 与 v7 决策树 Main A + case-study 定位一致。

## 16. PASS / CONDITIONAL / FAIL
- commitment：**PASS-STRONG**（v7 4.9 冻结规则；K 值敏感性与 67% 收敛
  已作限制如实报告）。
- engine validation：**FAIL**（v7 5.6 冻结规则；→ case study）。

## 17. Next allowed task
无。STOP EXPERIMENT EXPANSION。剩余工作仅限：arXiv v1 打包、投稿格式
（venue 模板）、图表一键复现脚本核对。

## 18. Manuscript sections updated
§5-result（MUST-1 判定全文）、§9（MUST-2 判定全文）、Abstract（(3) 增强
+ 引擎句改写）、Conclusion（commitment 确认 + case-study 边界）、
Contributions 4/6、Discussion limitations (vii)(viii)。13 页编译干净
（0 未定义引用、禁词清扫通过）。

## 计数器
v7 周期 20/20 → 周期终点。判定完成，论文冻结。
