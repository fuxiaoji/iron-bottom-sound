# FINAL_V9_ADVISOR_REPORT

回答 v9 §47 的十五个问题。**结论先行**：v8 的认证在数学上有两处缺陷
（受限值不能当全博弈下界；BR 搜索截断了对手混合策略），本轮用**精确有限
博弈**重做后，commitment 结论不但成立，而且比 v8 更强——18/18 认证中有
12 格界宽已 <5%（v8 无一格达标）。

---

## 1. Commitment 在 exact Grid-5 下多少 /18 被 sign-certified？

**18/18**，0 个认证反转。其中 **12/18 同时达到紧凑界**
$(U-L)/\max(1,|V|)<5\%$，其余 6 格为 sign-certified but value-loose
（已在论文与图表中区分标注）。每几何各 3 正 3 负。

## 2. Grid-7 refinement 是否保持 sign？

**是，18/18 符号一致，0 反转。** 动作网格从 $5^6=15{,}625$ 扩到
$7^6=117{,}649$ 条序列，符号全部保持；区间中点仅小幅移动
（例：−10.4→−11.1，+10.2→+10.2）。

## 3. 是否出现 certified reversal？

**没有。** Grid-5 与 Grid-7 均为 0 certified reversal。

## 4. Commitment 最终是 CORE-STRONG、CORE-CONDITIONAL 还是 REMOVE？

**CORE-STRONG**（v9 §14 冻结规则：Grid-5 ≥15/18 + 无反转 + Grid-7 无反转
+ 每几何双向支持，全部满足，且 Grid-7 跑满 18/18 而非 anchor 子集）。

论文中的限定措辞为 "**within the discretized formation game**"，未写成
连续博弈的精确结论。

## 5. Continuous heuristic result 与 exact discrete result 是否一致？

**符号 18/18 一致。** 旧 v8 连续启发式结果已**降级**为 robustness
experiment，论文明确说明其数值不是界、也不被当作界使用（v9 §15）。

## 6. Proposition 1 是否已修复 finite/infinite-horizon 逻辑？

**是。** 原稿把 $\gamma\in(0,1]$ 与压缩映射混用，现已拆成：
- **(i) 有限时域、任意 $\gamma\le1$**：由反向归纳证明，终端值满足
  $V_{H+1}(\mathcal S s)=-V_{H+1}(s)$ 即可逐层保持斜对称，不用压缩；
- **(ii) 无限时域、$0<\gamma<1$**：Bellman 算子为 $\gamma$-压缩，
  由压缩映射定理得唯一不动点 $L$。

同时补齐 **假设块 (A1)(A2)**（交换映射下阶段收益取负 + 动力学交换等变），
并明确写出由 (A1)(A2) 推出 $A_{uv}=-A_{vu}$。**未写 "identical ships
imply skew symmetry"。**

## 7. Torpedo claim 是否已统一？

**是。** 全文统一为
> response contraction depends jointly on coverage, local intensity, and
> the value landscape of alternative responses.

"thickness—not lethality"、"coverage beats damage"、"thickness monotonically
increases denial" 三处表述已删除；unmatched thickness sweep 仅作为
"contraction rises over the tested range" 报告，并紧随
matched-lethality 反例（21/28 concentrated 占优）。

## 8. Engine case-study wording 是否一致？

**是。** 全文统一为 external / rules-engine case study；"validation
substrate"、"high-fidelity validation"、"independent confirmation" 已清除；
"deterministic engine" 改为 "deterministic conditional on sealed orders and
random seed"。几何表述改为 "rank ordering preserved; strict sign agreement
in two of three"。

## 9. 六张主图分别做了哪些修改？

| 图 | 修改 |
|---|---|
| Fig 1 | 保留示意图（formation centre、两条编队、候选轨迹、延迟危险走廊；无历史地图） |
| Fig 2 | 保留三层逻辑（轨迹 / $L(t)$ / $J(t)$），明确 max L_A > max L_B 但 J_A(T) < J_B(T) |
| Fig 3 | **轴叙事修正**：横轴=速度不对称、纵轴=射程不对称；标题收窄为 "tested perturbations"；注释移出图面避免压色 |
| Fig 4 | **完全由 v9 exact 数据重画**：数值=认证区间中点；认证状态独立编码（蓝/红实边=认证正/负，灰 hatch=跨零，黑 X=Grid-5/7 不一致，空心圆=Grid-7 未跑） |
| Fig 5 | 明确 "thickness sweep (unmatched lethality)"，新增 matched-lethality 反例面板（21/28） |
| Fig 6 | 双面板（全幅 + 近零区），保留 $x=0,y=0$ 参考线，caption 报告 sign agreement / ρ / pairwise accuracy |

全部输出**矢量 PDF** + ≥300 dpi PNG；certification 不靠颜色单独区分。

## 10. 当前论文剩余 blocker 是否为 0？

**技术 blocker 为 0。** §45 Stop Gate 逐项核对通过（见文件末）。
剩两件非技术工程：目标期刊模板适配、arXiv v1 源码整理（等您指定期刊）。

## 11. 当前是否触发 STOP EXPERIMENT EXPANSION？

**是。** 触发。

## 12. 最终推荐标题？

保留现名（Commitment 为 CORE-STRONG）：

> **Maneuvering Formations in Directional Fields: Path-Integrated Exposure,
> Commitment, and Delayed Threats**
> —— 副题可加 *in Nonholonomic Adversarial Games*

（v9 §30 提供两个选项；因 commitment 为 CORE-STRONG，建议采用强调
formation 的那一版。）

## 13. 最终 3–4 条 Contributions？

1. **Formation-level path-integrated anisotropic interaction game** ——
   把编队几何机动从 snapshot 位置优化重构为对抗性累计轨迹优化，并证明
   peak-position 代理会改变策略排序。
2. **Closed-loop structural degeneracy 及其被测边界**（基于明确的
   player-exchange / skew-symmetry 条件）+ 速度能力单调性。
3. **Commitment–range comparative statics（CORE-STRONG）** —— 在冻结的
   离散开环博弈内，用穷举全空间最优响应得到有效平衡界，18/18 格认证、
   网格细化稳定。
4. **Delayed spatiotemporal threat 与近优响应集效应** ——
   coverage + intensity + response landscape 三者共同决定。

外部引擎结果**不列为核心贡献**，而是 external case study。

## 14. 哪些 negative results 被保留？

- **Engine transfer FAIL**（sign 75% / ρ=−0.08 / ordering 63%，匹配设计）；
- **matched-lethality 反例**（coverage 单独不足以决定 denial）；
- **free-disengagement 无保证**（最坏保持率 ≤0.07）；
- **plan library 不收敛**（25%/18%）；
- **continuous heuristic oracle 的局限**（点估计不是界）；
- **parallel 配置不具交换对称性**，故其对称控制格不预测零值（认证区间
  $[+0.06,+1.29]$）；
- **Grid-7 界宽普遍大于 Grid-5**（策略空间 7.5 倍），如实标注 loose。

## 15. arXiv v1 是否 ready？

**内容上 ready**（19 页、六图、三命题带完整证明、Related Work、
claim registry 无 PROVISIONAL、无 placeholder、一键复现通过）。
待办仅为模板适配与作者/单位信息（见 §10）。

---

## §45 Stop Gate 逐项核对

| 条件 | 状态 |
|---|---|
| Grid-5 18 cells exact certification | ✅ 18/18 |
| Grid-7 refinement（全部或 anchor） | ✅ 18/18（full） |
| Commitment 分类 | ✅ CORE-STRONG |
| Prop 1 $\gamma=1$ 问题修复 | ✅ 有限/无限时域拆分 |
| player-exchange symmetry 假设写清 | ✅ (A1)(A2) |
| terminal payoff claim 收窄 | ✅ symmetry-preserving 限定 |
| torpedo thickness claim 统一 | ✅ |
| "one third of rank information" 删除 | ✅ |
| engine 描述统一为 external case study | ✅ |
| doctrine 过强表述删除 | ✅ |
| Fig 3 轴叙事修正 | ✅ |
| Fig 4 用 exact 数据重画 | ✅ |
| Fig 5 matched-lethality 叙事修正 | ✅ |
| Fig 6 加 zoom / 改进缩放 | ✅ |
| 所有主图有 vector PDF | ✅ |
| Claim Registry 无 PROVISIONAL | ✅ 14 条 |
| Related Work 最接近工作补齐 | ✅ 四组 + 9 条新文献 |
| Abstract 与 registry 一致 | ✅ |
| Conclusion 与 registry 一致 | ✅ |
| reproduce_paper_v9.py 可运行 | ✅ |
| 无 placeholder | ✅ |
| 作者/单位信息进入投稿版 | ⏳ 待您提供 |

**STOP EXPERIMENT EXPANSION 已触发。**
