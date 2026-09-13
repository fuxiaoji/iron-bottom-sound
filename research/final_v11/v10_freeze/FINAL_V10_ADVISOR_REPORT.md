# FINAL_V10_ADVISOR_REPORT（v10 计划 §50 二十问）

**结论先行**：leader–follower 升级没有推翻任何核心结论。commitment 比较静态
在路径跟随模型下再次通过精确认证（**LF-CORE-STRONG，18/18**），且与刚性基线
**符号 18/18 完全一致**。真正改变的是：rigid 从"主模型"降级为"小曲率基线"，
reposition 代价的趋势被证明是**表示依赖**的（已如实降级），论文的 General
Model 改为不绑定任何编队表示的一般映射。

---

## 1. LF 模型是否通过所有 unit tests？
**是，8/8。** 直线等价（误差 0）、沿航迹间距固定（≤0.0034 hex）、等曲率转弯
位于同一圆弧且航向展布 = ω·L/v（26.7°，rigid 会得 0）、无横向跳变（≤v）、
航向等于切线（误差 0）、旋转/平移等变（1e−15）、编队次序保持、子步细化
（6→12 子步 J 变 1.5%）。

## 2. rigid 和 LF 在 9-cell bridge 中有多少 Commitment sign 一致？
**9/9（100%）**，Kendall τ = 0.944、Spearman ρ = 0.983，量级中位偏差 8.1%。
判定 **ROBUST**。

## 3. 哪些 cell 差异最大？
量级上：`parallel|1.2|1.0`（P6 rigid +4.88 → LF +7.45）与
`head_on|1.2|1.0`（+7.30 → +9.67）最大；`crossing|1.2|1.0`（+6.43 → +6.29）
最小。几何差异最大的是 stress 格（形状误差 7.18 hex，χ_F=0.58）。

## 4. error 是否随 κL_F 增大？
方向正确但关系不强：κ_L_F 与 |ΔJ| 的 Spearman = 0.49（n=9）。真实几何误差
（形状误差、场偏差）随 χ_F 单调增大；payoff 层面的差异被抵消较多。论文
Fig7(b) 画出该散点，未包装成定律。

## 5. rigid 是否可以继续称 useful approximation？
**可以，但必须限定。** 它保留 comparative statics 的符号与秩序（9/9、τ=0.94、
认证 18/18 符号一致），因此是有效的结构性 baseline；但它的几何在 χ_F ≳ 0.6
时明显偏离，reposition 代价趋势会改变。论文措辞为
"analytically transparent, small-curvature approximation"。

## 6. LF exact Commitment 有多少 /18 sign-certified？
**18/18**，0 certified reversal；Grid-7 全 18 格同样 0 反转；每几何各 3 正 3 负。

## 7. Grid-7 refinement 是否稳定？
**稳定**：LF 在 Grid-7 上 18 格无反转，符号与 Grid-5 全部一致。

## 8. 是否存在 certified sign reversal？
**没有**（Grid-5 与 Grid-7 均为 0）。

## 9. Commitment 最终是 LF-CORE-STRONG / CONDITIONAL / REMOVE？
**LF-CORE-STRONG。**

## 10. B5 的 qualitative trend 是否保持？
**没有保持。** rigid 下 reposition 代价随转向严重度非单调（+0.28, −0.84,
+2.69），LF 下单调递减（−1.00, −0.96, −2.69）。按 v10 §26，正文只保留 LF
结果，rigid 曲线降为 baseline 注记；claim C14 标为 NARROW。

## 11. delayed-threat 主机制是否保持？
**保持（在关键性质上）。** 两表示均满足：薄+弱威胁 →（近）零收缩；
仅扩大覆盖（加宽威胁带）而不提高强度 → 收缩不变。差别在强度敏感度：
LF 平缓（0→0.87），rigid 更陡（0.11→0.33）。与 v9 的"coverage 单独不足、
机制 = coverage + intensity + landscape"一致。

## 12. 哪些旧 rigid 数值仍留正文？
单舰方向性核校准、path-integral 定义与偏好反转、两个结构命题（简并、能力
单调）、编队聚合、延迟威胁时空场概念、engine case study、Related Work。

## 13. 哪些旧 rigid 数值移动到 Supplement？
B5 的密集重定位网格（正文只留 LF 曲线与一句结论）、rigid 的 commitment
热图（正文用 LF，rigid 作为 Fig4 的不一致标记与 Supplement 面板）、
部分敏感度明细表。

## 14. 哪些结果被 LF 替代？
commitment 主图（Fig4）、Fig1 示意、编队几何类数值（形状/场偏差）、
reposition 代价主线。

## 15. Engine case study 是否无需重跑？
**无需。** IBS 引擎本身以规则方式实现编队与航迹跟随，比刚性更接近真实；
论文新增一句说明引擎研究同时允许编队形变/轨迹跟随，正是 v10 引入 LF 的
动机。未重跑，也未声称与 LF 定义完全一致。

## 16. 当前还有没有 scientific blocker？
**没有。** 内容层面可投稿；剩模板适配与作者信息。

## 17. 是否触发 STOP EXPERIMENT EXPANSION？
**触发。**

## 18. 最终标题？
> **Maneuvering Formations in Directional Fields: Path-Integrated Exposure,
> Commitment, and Delayed Threats**

（副题可加 *in Nonholonomic Adversarial Games*；commitment 为
LF-CORE-STRONG，标题保留 Commitment。）

## 19. 最终 Contributions？
1. **Formation-level path-integrated anisotropic interaction game** ——
   一般编队映射下的对抗性累计轨迹优化；瞬时/峰值几何不等于最优轨迹。
2. **Closed-loop structural degeneracy 及其被测边界** + 速度能力单调性
   （不依赖具体编队表示）。
3. **Commitment–range comparative statics（LF-CORE-STRONG）** ——
   冻结离散开环博弈内穷举全空间最优响应的有效平衡界，18/18 认证，
   网格细化稳定，且**在路径跟随与刚性两种编队表示下符号一致（18/18）**。
4. **Delayed spatiotemporal threat 与近优响应集效应** ——
   coverage + intensity + response landscape，单独覆盖不足。

leader–follower 本身**不列为算法贡献**，而是 fidelity / robustness 层。

## 20. arXiv 是否 ready？
内容 ready（22 页、Fig1–7、三命题完整证明、Related Work、registry 17 条无
PROVISIONAL、一键复现）。待办：期刊模板、作者/单位/通讯信息。

---

## v10 §47 Stop Gate 核对

| 条件 | 状态 |
|---|---|
| v9 baseline 冻结 | ✅（含哈希） |
| LF 实现完成 | ✅ |
| 8 项 unit tests 通过 | ✅ 8/8 |
| 9-cell bridge 完成 | ✅ ROBUST |
| κL_F sensitivity 完成 | ✅ Fig7(b) |
| LF exact Commitment 18 cells | ✅ 18/18 |
| Grid-7 refinement | ✅ 全 18 格 |
| Commitment 最终分类 | ✅ LF-CORE-STRONG |
| B5 代表性 sensitivity | ✅（趋势改为表示依赖，如实报告） |
| delayed-threat 代表性 sensitivity | ✅（关键性质保持） |
| theorem 未不必要重跑 | ✅ Prop 1–3 已是一般形式 |
| kernel 未不必要重跑 | ✅ |
| engine 未不必要重跑 | ✅ |
| General Model 改为 generic map | ✅ |
| Naval Instantiation 改为 LF | ✅ |
| rigid 明确降级为 baseline | ✅ |
| Figure 1 展示 bending formation | ✅ |
| Commitment Figure 使用 LF | ✅ |
| claim registry 标注 formation scope | ✅ formation_model 字段 |
| Abstract / Conclusion 同步 | ✅ |
| reproducibility pipeline 更新 | ✅ reproduce_paper_v10.py |

**STOP EXPERIMENT EXPANSION 已触发。**
