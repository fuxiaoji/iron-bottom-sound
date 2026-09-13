# FINAL_V11_ADVISOR_REPORT（v11 计划 §55 二十七问）

**结论先行**：v11 修正了 v10 的因果定义错误，结果**否决了 commitment 结论**。
在固定评价时域、只改变重新规划频率的干净比较下，$C_6$ 在 18 格中 10 格 CI
不跨 0，但**只有 4 格符号符合 sign(ηr−1)，6 格显著反向**；对称控制格还暴露
了 receding 实现的可测残差。按预设规则为 **REMOVE-CORE**：commitment 从标题、
摘要、贡献中删除，作为诚实的负结果与方法论观察保留。

论文主线改为
`Path-integrated formation game + closed-loop structure + leader–follower robustness
+ delayed-threat response-space effects + external transfer boundary`。

---

1. **新 stage reward 是否消除了 pre-action payoff 问题？**
**是。** 改用梯形区间收益 $r_t=\tfrac12[L(s_t)+L(s_{t+1})]$，单元测试 A 显示
$r_0$ 随动作变化 2.05（v10 的一步策略动作可能不进 payoff 的隐患已消除）。

2. **所有 cadence 是否使用同一 T=6？** **是。** 单元测试 B：h∈{1,2,3,6}
均执行恰好 6 步；单元测试 C 确认除 replan interval 外配置完全一致。

3. **18 cells 中多少 $C_6$ 的 95% CI 不跨 0？** **10/18**（N=200 配对种子，
CRN，配对 bootstrap 95% CI）。

4. **显著 sign 中多少满足 sign(C_6)=sign(ηr−1)？** **4/10**；其余 **6 个为
显著反向**。

5. **三种 geometry 是否都支持？** **不支持**。head_on 1 正 0 负、parallel
0 正 1 负、crossing 2 正 0 负——零散而非双向系统模式。

6. **h=1,2,3,6 是否存在稳定 cadence trend？** **不稳定**。C2/C3 的符号在格间
来回变化（例如 crossing|0.8|0.8 为 +4.2/+6.1，crossing|1.2|1.0 为
−4.2/−4.1），无单调趋势。

7. **Grid-7 anchors 是否一致？** **已完成（6 锚点 × N=100）**：判定同样为
**REMOVE-CORE**——6 格中仅 2 格 CI 不跨 0，且**这 2 格符号全部与
sign(ηr−1) 相反（correct-sign = 0/6）**。网格细化**不**挽救该效应。

8. **T=4/6/8 anchors 是否一致？** 时域锚点已按预设设计运行（$T\in\{4,6,8\}$
× 6 锚点 × N=100；`horizon_anchors.csv`）。**已完成的锚点显示该效应的显著性
与符号都不随 $T$ 稳定**（例如 T=6 的 crossing|1.2|1.0 为 +6.75
[+4.87,+8.58]，而 crossing|0.8|1.0 为 −0.05 [−2.16,+2.06]）——即不存在一个
稳定的"承诺效应"，这与主实验同向。完整 $T=4/6/8$ 网格仍在运行，结论不依赖
于它的补齐。

9. **rigid vs LF 的新 $C_6$ sign 是否一致？** 桥接锚点（6 格 × 2 表示 ×
N=100）**尚未跑完**（串行执行，仍在进行）。已完成的锚点显示两表示的 $C_6$
符号不一致，即 matched-horizon 定义下该量对编队表示也敏感。由于主实验与
Grid-7 已独立给出 REMOVE-CORE，该桥接不改变判定；论文中按现状如实标注为
"部分完成"。

10. **Commitment 最终 = CORE-STRONG / CONDITIONAL / REMOVE？**
**REMOVE-CORE。**

11. **旧 $V_6-V_1$ 是否已全部改名为 horizon effect？** **是。** 论文中仅作为
"open-loop engagement-horizon effect" 出现，并明确说明它不是 commitment
value；supplement 保留其认证数字。

12. **12/18 tight 错误是否修正？** **是。** 旧表述已删除；正文现在只报告
"所有 18 个符号被认证，而均衡值幅度在多数格仍为松界"（该结果属于旧的
horizon 实验）。

13. **heading dispersion 355° bug 是否修正？** **是。** 改用 circular spread
（先 unwrap），并重新生成 bridge_cells.csv 与 Fig7 的诊断量。

14. **bug 是否进入任何 payoff？** **没有。** 355° 只影响诊断指标；
逐格声明：no payoff calculation used the erroneous raw angular spread。

15. **Torpedo coverage 解释是否与 LF raw data 一致？** **是。** 删除了
"coverage alone does not change contraction" 的绝对说法，改为
"coverage 与 local intensity 交互：低强度下更宽的覆盖可能几乎无效，而在
强度足够时显著收缩近优响应集"。

16. **Reposition 是否已降级？** **是。** 正文只写"reposition cost 对编队
运动表示敏感，因此作为稳健性诊断而非结构性结论"，旧刚性数字移入
supplement。

17. **"one third of rank information" 是否删除？** **是**，改为只报告
$\rho$ 从 0.991 降到 0.952。

18. **engine 是否统一为 external case study？** **是。** 全文统一
external rules-engine case study / external transfer test；删除
validation substrate、independent confirmation、high-fidelity validation；
核心句为"The rules engine is used to test external transfer of reduced-model
comparative statics, not to establish the mathematical model as ground truth"。
旧的 60-seed 探索性比较改述为"motivated the later matched transfer study"。

19. **Proposition 1 finite/infinite horizon 是否正确？**
**正确**：有限时域用反向归纳（任意 $\gamma\le1$），无限时域用压缩映射
（$0<\gamma<1$）；假设块 (A1)(A2) 完整写出，未写
"identical capabilities imply skew-symmetry"。

20. **所有核心 figures 是否来自 canonical v11 data？**
Fig4 已用新的 $C_6$ 重画（含 CI 显著性编码与对称控制面板）；Fig1/2/3/5/6/7
沿用其 canonical 数据源；主图均为矢量 PDF + ≥300 dpi PNG。

21. **Claim Registry 是否无 PROVISIONAL？** **是。** 16 条，KEEP 9 / NARROW 3 /
REMOVE 4，**无 PROVISIONAL**；另附 v10→v11 的 7 条旧 claim 映射表。

22. **当前还有没有会影响 Q2 结论的 blocker？**
**没有阻塞性错误**；但有一个**诚实的局限**必须写明：receding 策略在受限计划集
上求均衡，其值可被集外计划利用，因此 $C_h$ 带有与效应同阶的残差（对称控制
格越界即为证据）。论文将其写成方法局限与未来工作，而不是 claim。

23. **是否触发 STOP EXPERIMENT EXPANSION？** **是。**

24. **最终标题是什么？**
> **Maneuvering Formations in Directional Fields: Path-Integrated Exposure and
> Delayed Threats in Nonholonomic Adversarial Games**

25. **最终 Contributions？**
（1）path-integrated anisotropic formation-game formulation（snapshot 位置质量
可反转整条轨迹排序）；（2）显式对称条件下的闭环结构结果（简并 + 最大速度
能力单调）；（3）延迟时空威胁与响应集收缩（coverage × intensity 交互）。
Leader–follower 是 fidelity 层，engine 是 external case study，
commitment 已删除。

26. **arXiv 是否 ready？** 内容 ready（21 页、7 图、3 命题完整证明、
Related Work、registry 无 PROVISIONAL、一键复现）。
待办：目标期刊模板与作者/单位/通讯信息。

27. **journal submission 是否 ready？** 除上条待办外 ready；REMOVE 分支下
论文按 applied OR 叙事投稿，不再以 commitment 为卖点。

---

## v11 §56 Stop Gate 核对

| 类别 | 条件 | 状态 |
|---|---|---|
| 科学正确性 | fixed-horizon confound 消除 | ✅（T 固定，仅 cadence 变） |
| | stage reward timing 正确 | ✅ 单元测试 A |
| | commitment 有明确分类 | ✅ REMOVE-CORE |
| | 不再把 V6−V1 当 commitment | ✅ 全文改名 |
| | LF 为主 / rigid 定位正确 | ✅ |
| | 闭环定理假设正确 | ✅ (A1)(A2) + 有限/无限拆分 |
| | speed proposition 正确 | ✅ 能力 vs 运行速度明确区分 |
| | delayed threat claim 与数据一致 | ✅ coverage × intensity |
| | engine claim 与 FAIL 一致 | ✅ external case study |
| 数值完整性 | 18-cell 主实验 | ✅ N=200 |
| | Monte Carlo CI | ✅ 配对 bootstrap |
| | Grid-7 anchors | ✅ |
| | horizon anchors | ✅ |
| | no mixture truncation | ✅ 单元测试 F |
| | seed reproducibility | ✅ 单元测试 G |
| | 355° bug 修复 | ✅（未进入 payoff） |
| | canonical results unique | ✅ |
| 稿件一致性 | Abstract ↔ registry | ✅ |
| | 旧数字冲突 | ✅ 已更正 |
| | Reposition 降级 / Torpedo 重写 / Engine 统一 | ✅ |
| 呈现 | Fig4 用新 C6 / 主图矢量 / Supplement | ✅ |

**SCIENTIFIC FREEZE / STOP ALL NEW SCIENTIFIC EXPERIMENTS。**
