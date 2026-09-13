# ITERATION REPORT — 1 (v8 数值认证 + 论文工程周期)

## 1. Current paper main line
Formation-level path-integrated adversarial trajectory optimization:
directional formation field → path-integrated exposure → closed-loop
dynamic game (degeneracy + capability monotonicity) → formation
reachability/commitment → delayed threat → external engine case study.

## 2. Current task
T0 完整性审计 → T3 命题证明升级 → T4 Related Work → T5 可视化重构 →
T6 正文重写（本轮完成）；T1 认证运行中，T2/T7/T8 待 T1。

## 3. Exact hypothesis
(a) 18 个非对称 commitment cell 的 sign(P₆)=sign(ηr−1) 能否被
equilibrium-bound 区间认证（v8 §3.3）；(b) 论文能否在去除内部实验编号
后保持可追溯性与主张强度一致。

## 4. Mathematical object
- Formation: x_ik(t)=c_i(t)+R(ψ_i(t))p_ik；F_i=Σ_k K_ik；J=∫[P_{B→R}−λP_{R→B}]dt。
- Prop 1（简并）：successor-ℓ 矩阵斜对称 ⇒ val A=0 ⇒ T 为 γ-压缩且 L 为
  唯一不动点 ⇒ V*≡L。
- Prop 2（能力单调）：P(v̄1)⊆P(v̄2) ⇒ V(v̄2)≥V(v̄1)。
- Prop 3（编队聚合）：E_{i→j}=Σ_kΣ_m ∫K dt。
- T1 认证：L_H ≤ V*_H ≤ U_H，P_H∈[L_H−U_1, U_H−L_1]。

## 5. Files read
research/results/{e01,e02,b1..b13,final_v7}/*；paper_v7/main.tex；
research/geometry/{differential_game,committed_game,firepower_kernel}.py。

## 6. Files changed
- research/final_v8/audit/{provenance_manifest.json,source_of_truth.md,result_hashes.csv}
- research/experiments/t1_certification.py（新，增强 3-stage BR + 区间认证 + pass-2）
- research/final_v8/figures/{make_figures.py,make_fig3_data.py,fig3_grid.json,fig1/2/3/5/6.png}
- research/experiments/fig_helpers.py
- paper_v8/main.tex（新副本：Prop 1-3 全证明、Related Work、13 章重排、图 1/2/5/6、
  Abstract 模板重写、内部编码清扫）
- research/final_v8/paper_claim_registry.csv
- reproduce_paper.py（一键复现）
- research/final_v8/goal-progress.md

## 7. Solver / writing / visualization actions
- T1：Double Oracle，own-plan seeding 保证 BR≥L；BR 三阶段（Sobol 32 起点 +
  快速精修 → top-2 深度精修 × L-BFGS-B/Powell/Nelder-Mead → best-of-all）；
  对手混合截断 w≥0.05、cap 4；K∈{3,4,6}(+8)，H∈{1,6}。
- T5：6 张主图（Fig3 DP 网格 25 格；Fig1 用校准核画方向场；Fig2 用真实
  B2 rollout；Fig5 用 b10/b11 真实数据；Fig6 用 MUST-2 真实门值）。
- T6：section 重排为 13 章问题驱动结构；标题去编号；engine 措辞统一为
  case study；旧图 B4/B6 移除。

## 8. Pre-specified gate
T1（v8 §7/§8，冻结）：强收敛 (U−L)/max(1,|V|)<5%；允许 SIGN-CERTIFIED /
VALUE-NOT-TIGHT；分类 KEEP CORE ≥15/18 且无 certified reversal 且 K 细化不改
符号；NARROW 10–14；REMOVE 出现 certified reversal。

## 9. Results
T1 phase 1+2（106 runs）：**15/18 sign-certified、0 certified reversal**；
3 个未认证格全部为 ηr<1 且 rel_gap>100%（head_on ev=1.0/1.2，parallel
ev=1.0）—— 已触发 pass-2（8 轮 DO）收紧。已认证格符号 100% 符合
sign(ηr−1)。几何覆盖：crossing 6/6、parallel 5/6、head_on 4/6。
T3/T4/T5/T6 为文档与命题产出，无实验数值。

## 10. Convergence / certification
phase-1 tight 格 rel_gap 12%–82%；未认证格 101%–122%（界过松，正是
v8 §7 预期的 DO 迭代不足情形）。pass-2 目标 = 收紧这 3 格的上界。

## 11. Failure cases
- 3 格未认证（如实标注，交由 pass-2；若仍跨 0 则标 UNCERTIFIED）。
- 机器上并发 agent 进程与旧孤儿 worker 曾抢核（已清理，不影响结果）。
- 过程 bug：pass-2 写入的换行字面量损坏（已修，py_compile 通过）。

## 12. Claim changes
见 paper_claim_registry.csv：C5（commitment）由 PASS-STRONG 内部语言改为
equilibrium-bound 认证语言；C8 跨策略排序降为 NARROW；C9 匹配引擎
REMOVE（作为 validation）；C10/C11 保留 REMOVE。

## 13. Manuscript changes
Prop 1 完整证明 + Remark（斜对称条件范围）；Prop 2/3 证明；新增 Related
Work（四组 + 9 条文献）；13 章问题驱动结构；Abstract 按 v8 §26 模板重写；
内部编码从正文与标题清除；engine 定位统一。

## 14. Figure changes
新增 Fig1（问题示意）、Fig2（峰值 vs 积分）、Fig3（简并边界热图）、
Fig5（延迟威胁时空）、Fig6（引擎迁移四象限）；Fig4 待 T1 终值；
移除旧 fig_b4/fig_b6 正文位置（转 supplement 口径）。

## 15. KEEP / NARROW / REMOVE
- KEEP：C1 路径积分、C2 简并、C3 能力单调、C4 编队聚合、C6 延迟威胁、
  C7 无保证、C12 核校准。
- NARROW：C8 跨策略排序（仅 ordering）。
- REMOVE：C9（作为 validation）、C10（+5.14 feedback advantage）、
  C11（coverage beats damage）。
- C5：待 pass-2 定稿（≥15/18 ⇒ KEEP CORE）。

## 16. Next allowed task
T1 pass-2 收敛 → T2 claim 定稿 → 认证节重写 + Fig4 → T7 registry 定稿 +
禁词扫描 → T8 一键复现端到端 + §33 验收清单 + 打包。禁止新实验方向。

## 计数器
v8 周期 7/20。
