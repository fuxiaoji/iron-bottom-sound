# ITERATION 1 — v9 精确离散认证 + 论文修复

## 1. Current paper status
Formation-level path-integrated adversarial trajectory optimization；
commitment 认证由 v8 的**启发式 oracle 界**升级为 **v9 精确有限博弈界**。

## 2. Task executed
T1-exact 精确离散开环认证（Grid-5 / Grid-7）+ Prop 1 修复 + 措辞纪律
（v9 §18–26）+ 图表重做（§33–37）+ Table 3（§38）+ registry 重做（§39）+
一键复现（§41）。

## 3. Exact mathematical target
冻结动作网格：$\mathcal A_5=\{-1,-\frac12,0,\frac12,1\}$、
$\mathcal A_7=\{-1,-\frac23,-\frac13,0,\frac13,\frac23,1\}$，
$a=\omega/\bar\omega$，$\bar\omega=60^\circ$（引擎转向粒度）。
纯策略 = H=6 的完整转向序列：$|\Omega_5|=15\,625$、$|\Omega_7|=117\,649$。
有效界：$\underline V=\min_{\tau_R\in\Omega_m}\mathbb E_{x_R}J$、
$\overline V=\max_{\tau_B\in\Omega_m}\mathbb E_{y_R}J$，
$P_6\in[\underline V_6-\overline V_1,\overline V_6-\underline V_1]$。

## 4. Files read
v9 计划；research/final_v8/commitment/*（旧启发式结果，作对照保留）；
research/results/{e01,b10,b11,b12,b13,final_v7}/*。

## 5. Files changed
- research/experiments/t1_exact_discrete_certification.py（**新建**）
- research/final_v9/commitment_exact/{exact_grid5_results.csv,
  exact_grid7_results.csv, exact_grid*_sanity_results.csv,
  exact_certification_summary.json, exact_certification_report.md,
  double_oracle_trace.jsonl, exact_br_diagnostics.csv, grid_refinement.csv,
  exact_h1_baselines.json}
- research/final_v9/make_figures_v9.py（新建）、paper_claim_registry_v9.csv
- paper_v8/main.tex（Prop 1 完整重写、认证节重写、Abstract/Conclusion/
  Contributions、Table 3、Fig3–6 矢量替换、v9 §18–26 措辞）
- reproduce_paper_v9.py（新建）

## 6. Pre-specified design
DO 循环：解受限博弈 LP → 对**完整混合策略**做**穷举**全空间 BR →
得 LB/UB → 加入精确 argmin/argmax → 直到
$(\overline V-\underline V)/\max(1,|V_R|)<5\%$。
**全程无 mixture 截断、无 top-k、无重归一化**；H=1 用完整
$|\mathcal A_m|\times|\mathcal A_m|$ 矩阵精确解（LB₁=UB₁=V₁*）。
映射与网格在任何运行前冻结。

## 7. Result
- **Grid-5：18/18 非对称格符号认证，0 认证反转，12/18 达紧凑界（<5%）**；
  每几何各 3 正 3 负。
- **Grid-7：18 格全部完成，0 认证反转**；跨网格符号一致 **18/18**，
  区间中点稳定（如 −10.4→−11.1、+10.2→+10.2）。
- 量级符号方向符合机制：ηr=0.8 → 区间 $[-10.8,-10.2]$ 至 $[-5.7,-5.4]$；
  ηr=1.2 → $[+5.0,+5.2]$ 至 $[+8.7,+9.3]$。
- **对称控制格**：head_on 与 crossing 在 ηr=ηv=1 **精确为 0**
  （$\underline V=\overline V=-0.008$ / $-0.000$），离散博弈中复现 Prop 1 简并；
  parallel 配置非交换对称（两列同向并排），无零值预测，认证区间 $[+0.06,+1.29]$，
  如实报告而非当作简并失败。
- 判定：**CORE-STRONG（Grid-7 full）**。

## 8. Exact/heuristic status
认证路径 100% **exact**：全空间穷举 + 完整混合策略 + 有效界。
旧 v8 连续启发式结果**降级**为 robustness experiment（论文中明确说明
其数值不是界、也不被当界使用）；其符号与 exact 结果 18/18 一致。

## 9. Lower/upper bounds
见 §7 与 exact_grid{5,7}_results.csv 的 `lower_bound` / `upper_bound` /
`bound_width` / `relative_gap` 列。所有格满足
$\underline V\le V_R\le\overline V$（脚本内断言，违反即报错）。

## 10. Grid refinement status
Grid-5 → Grid-7：18/18 符号保持、0 反转。Grid-7 界宽普遍大于 Grid-5
（策略空间 7.5 倍、DO 迭代上限相同），已如实标注 loose。

## 11. Failures/anomalies
- 性能：首版标量受限矩阵填充导致每格 200–300s；改为缓存的向量化列/行后
  降到 15–17s（Grid-5）/135s（Grid-7）。核评估按 (扇区, 目标舷角) 分组
  向量化，与标量路径逐点一致（2e-15 / 0.0）。
- DO 早停 bug（append 后条件恒真）已修；种子集扩充为确定性结构化族。
- sanity 相首次运行覆盖了主相 CSV；已改为按 phase 命名输出并重跑主相。
- v8 的 `truncate_mix` 缺陷已彻底移除（v9 §5 要求），本脚本不存在截断路径。

## 12. Claim changes
registry 重做（14 条、无 PROVISIONAL）：KEEP 9、CORE-STRONG 1（C5）、
NARROW 1（C8 跨策略排序）、REMOVE 3（C9 作为 validation、C10 +5.14
feedback advantage、C11 coverage beats damage）。新增 C5b（对称控制格）、
C13（库不收敛）。字段含 mathematical_scope / bound_type /
exact_or_heuristic / grid。

## 13. Manuscript sections changed
§3 General Formation Game（Prop 3）、§4 Structural（Prop 1 重写为
finite-horizon 归纳 + infinite-horizon 压缩、假设块 (A1)(A2)、Prop 2）、
§6 Open-Loop Commitment（认证节按 exact 结果重写；Robustness 定位旧启发式）、
§9（terminal payoff 收窄）、§10（engine case-study 措辞、2/3 严格符号）、
Abstract / Contributions / Conclusion 同步。

## 14. Figures changed
Fig3 轴叙事修正（x=速度、y=射程）+ 标题收窄为 "tested perturbations"；
Fig4 **完全由 exact 结果重画**（certified 边框 / hatch / X / 空心圆编码）；
Fig5 标注 unmatched-lethality 并新增 matched-lethality 反例面板；
Fig6 改双面板（全幅 + 近零区），保留零参考线；全部输出**矢量 PDF** + 300dpi PNG。

## 15. KEEP / NARROW / REMOVE
Commitment = **CORE-STRONG**（within the discretized formation game）。
Engine = external case study（FAIL 保留）。Torpedo = coverage + intensity +
response landscape（thickness law 删除）。

## 16. Next allowed task
终稿润色 + arXiv v1 打包 + 期刊模板适配（等目标期刊）。
