# ITERATION REPORT — 2 (v8 收口周期 · 最终判定)

## 1. Current paper main line
Formation-level path-integrated adversarial trajectory optimization：
directional formation field → path-integrated exposure → closed-loop
dynamic game（简并 + 能力单调）→ formation reachability / certified
commitment → delayed threat → external engine case study。

## 2. Current task
T1 认证 → T1b 镜像验证 → T2 claim 定稿 → T7/T8 冻结与打包（全部完成）。

## 3. Exact hypothesis
H1：commitment–range 比较静态能被 equilibrium-bound 区间认证；
H2：若认证成立，符号模式应同时被博弈自身的镜像反对称性确认。

## 4. Mathematical object
见 ITERATION_1 §4；新增认证区间 P_H∈[L_H−U_1, U_H−L_1]（式 (5)）。

## 5. Files read
research/final_v8/commitment/*（certification_runs.jsonl / results.csv /
summary.json / mirror_validation.csv）、fig3_grid.json、paper_claim_registry.csv。

## 6. Files changed
- research/experiments/t1_certification.py（增强 BR + 区间认证 + pass-2 + resume）
- research/experiments/t1b_mirror_validation.py（新）
- research/final_v8/commitment/{certification_*,mirror_validation*}.{csv,json,md}
- research/final_v8/figures/{make_figures.py,make_fig3_data.py,fig4,fig3_grid.json}
- research/final_v8/paper_claim_registry.csv（C5 定稿）
- paper_v8/main.tex（认证节、镜像表、Fig4、Abstract、Conclusion）
- reproduce_paper.py（修 cwd 冲突 + 下划线转义）

## 7. Solver / writing / visualization actions
T1：88+18 runs（H=6 K∈{3,4,6}+K8、H=1 基线、对称 sanity、pass-2 收紧）。
T1b：12 runs（6 镜像格 × (H=6, H=1)）。T5：六张主图全部完成。

## 8. Pre-specified gate
同 ITERATION_1（v8 §7/§8，冻结未改）。

## 9. Results
### T1（认证）
- **18/18 非对称 K=6 格符号认证，0 certified reversal**；每几何正负各 ≥3 格。
- 区间：ηr=0.8 → P₆ 认证负（最紧 [−0.22,+0.00]）；ηr=1.2 → 认证正
  （[+6.62,+14.58] 至 [+13.51,+15.35]）。
- K∈{3,4,6} 细化：符号不变（K 值敏感但符号稳定）。
- **裁定：KEEP CORE (STRONG)**（v8 §8 冻结规则）。

### T1b（镜像一致性）
- **6/6 符号翻转符合预测**。head-on 与 crossing 是严格反对称（配置在
  半转下自映射），parallel 配置本身非对称，作为一致性观察报告。
- head_on：ηr'=0.833 → P∈[−10.4,−5.3]；ηr'=1.25 → [+12.2,+26.0]。
  crossing：ηr'=0.833 → [−7.6,+0.3]（点估计负）；ηr'=1.25 → [+10.6,+12.6]。
  parallel：ηr'=0.833 → [−5.4,+1.1]；ηr'=1.25 → [+10.7,+12.6]。

## 10. Convergence / certification
全部格为 "sign-certified / value-not-tight"（无格达到 5% 界宽门；相对界宽
12%–101%）。**受限值存在可测量的正向偏差**：在可证为零值的对称配置
（head-on/crossing at ηr=ηv=1，种子矩阵精确斜对称）上，受限估计报出
至多 +5.6 —— 已在论文中量化并声明（负向认证因此保守；正向认证由镜像
检验独立确认）。

## 11. Failure cases
- 无 certified reversal；无数值失败。
- 诚实标注：3 格首轮未认证（界过松），pass-2 收紧后全部认证；
  parallel 镜像格之一（ηr'=0.833）区间跨 0（该几何无严格镜像预测）。
- 过程：T1 首轮被孤儿 worker 抢核（已清理）；reproduce_paper.py 两处
  接口错误（已修，端到端通过）。

## 12. Claim changes
registry 12 条、无 PROVISIONAL：KEEP 7、KEEP CORE 1（C5 commitment）、
NARROW 1（C8 跨策略排序）、REMOVE 3（C9 作为 validation、C10 +5.14
feedback advantage、C11 coverage beats damage）。

## 13. Manuscript changes
认证节全文重写（协议/结果/诚实限定/镜像检验/分类）；镜像表（真实区间）；
Fig4；Abstract 与 Conclusion 按 KEEP CORE + 边界重写；Reproducibility
指向一键入口。

## 14. Figure changes
Fig1–6 全部完成并插入；Fig4 标注 certified/uncertified（hatch）与
区间数值；标题不含内部实验编号。

## 15. KEEP / NARROW / REMOVE
见 §12；论文身份保持
"Formation-level Path-integrated Adversarial Trajectory Optimization"。

## 16. Next allowed task
无。**STOP EXPERIMENT EXPANSION**：进入 arXiv v1 / 期刊投稿准备。
