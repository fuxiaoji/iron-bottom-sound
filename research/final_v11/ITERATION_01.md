# ITERATION 01 — v11 matched-horizon commitment

## 1. Current blocker
v10 的 $P_H=V_H-V_1$ 同时改变了承诺长度与评价时域，不能解释为
commitment value（v11 §1）。必须固定 $T$、只变重新规划频率。

## 2. Exact task
实现 matched-horizon receding planner，做 18 cells × h∈{1,2,3,6} 配对种子
Monte Carlo，给出 $C_h=V_T^{(h)}-V_T^{(1)}$ 与 95% CI，按预设 Gate 分类。

## 3. Mathematical definition
$T=6$ 固定；$r_t=\tfrac12[L(s_t)+L(s_{t+1})]$（梯形区间收益，动作必然影响
自身步的收益）；$h$ = 锁定期；$C_6=V_T^{(6)}-V_T^{(1)}$。
Receding 策略在每个重规划点解剩余时域开环博弈并**从完整均衡混合策略采样**
（不取 argmax、不截断 support）。

## 4. What is held fixed
模型（LF）、火力场、reward、$T=6$、动作网格 Grid-5、均衡求解器、terminal
规则、discount（=1）。

## 5. What changes
只有 replan interval $h$。

## 6. Files read
v11 计划；research/final_v10/*（v10 冻结）；research/formation/path_following.py。

## 7. Files changed
- research/formation/matched_horizon.py（**新建**：LeaderState、梯形区间收益、
  RemainingHorizonGame（向量化 + 跨 seed 缓存）、run_cadence、state_key）
- research/final_v11/commitment_matched/run_unit_tests_v11.py（**新建**，A–G）
- research/experiments/v11_commitment.py（**新建**：pilot/main/grid7/horizon/bridge）
- research/final_v11/v10_freeze/*（v10 冻结 + 术语改名表）
- **修复 path_following.py 与 matched_horizon.py 的 head 采样 bug**：
  在"当前 head 处"采样时索引被夹到 `len−2`，退回上一站点（末回合几何偏
  1 个站点）。v11 的 receding 采样会在 head 处采样故必须修；已回归验证
  **v10 结果完全不受影响**（v10 从不在 head 处采样，重跑 head_on|1.2|1.0
  与冻结值逐位一致）。

## 8. Pre-specified gate
CORE-STRONG：≥15/18 的 $C_6$ CI 不跨 0 且符号 = sign(ηr−1)，三几何双向，
Grid-7 anchors 无显著反向，cadence trend 合理。
CORE-CONDITIONAL：10–14 显著。REMOVE-CORE：多个显著反向（>2）。

## 9. Results
**REMOVE-CORE。** 18 cells / N=200 配对种子（CRN）：
- 10/18 的 $C_6$ CI 不跨 0；
- 其中**仅 4 个符号符合 sign(ηr−1)，6 个显著反向**（超过预设的"2 个以上
  强显著反向"阈值）；
- geometry 支持：head_on 1 正 0 负、parallel 0 正 1 负、crossing 2 正 0 负，
  呈零散而非系统的双向模式。

**对称控制诊断（决定性）**：在 ηr=ηv=1 的对称格上 $C_6$ 应≈0，实测
head_on +1.03 [−0.82,+2.99]（不显著）、crossing +6.14 [+4.88,+7.45]、
parallel −2.66 [−3.70,−1.61]。对 crossing 直接检验 payoff 反对称性：
$\max|J(p,q)+J(q,p)|=0.0000$、对角 $\max|J(p,p)|=0.0000$（**精确反对称**），
却仍给出显著非零 $C_6$ ⇒ 偏差来自**受限计划集均衡不等于全博弈均衡**
（receding 求解器在受限集上求均衡，其可被集外计划利用），属实现层面的
系统性偏差，量级 1–6，与主实验效应同阶。

## 10. Confidence interval / bounds
每格 $C_6$ 的配对 bootstrap 95% CI 见 main_18cells.csv。示例：
crossing|0.8|0.8 $C_6=+10.3$ [+8.6,+12.0]；crossing|1.2|1.0 $C_6=-7.4$
[−8.6,−6.3]；parallel|1.2|1.0 $C_6=-0.9$ [−2.7,+0.7]（不显著）。

## 11. Solver diagnostics
- 收敛敏感度：松容差（iters=3, gap=0.10）在对称格给出 V1=+3.88（偏差），
  收紧到 iters=15/gap=0.01 后 V1=+0.23±1.28、V6=+2.57±1.54（≈0）——
  默认已收紧。
- 跨 seed 缓存使边际成本降到 ~0.03 s/seed（预热 ~8 s/格-频率）。
- 单元测试 A–G 全过：stage reward 随动作变化 2.05（修正 v10 的
  pre-action payoff 隐患）；各 cadence 均执行恰好 6 步；h=6 与全开环解
  一致到 1e−9；h=1 逐步重解（R=6,5,4,3,2,1）；混合策略归一且 support 完整；
  同 seed 可复现。

## 12. Failures
- 主试验与对称控制均未通过 ⇒ **commitment 不能作为核心结论**。
- 受限均衡的实现偏差无法在预算内消除（需全空间均衡，不可行）。

## 13. Claim changes
- 旧 C5 / C5b / C5c（commitment-range comparative statics、LF-CORE-STRONG）
  → **REMOVE**（改称 open-loop engagement-horizon effect，仅作诊断）。
- 旧 "commitment premium / value of replanning" 措辞禁止使用。
- 保留：路径积分目标、闭环结构命题、能力单调、编队聚合、LF 表示鲁棒性
  （几何/场偏差部分）、延迟威胁机制（改写为 coverage×intensity 交互）、
  外部引擎边界。

## 14. Manuscript changes
标题删除 Commitment；Abstract 按 REMOVE 分支重写；Contributions 由 4 条
降为 3 条；commitment 章节改为 "Open-loop horizon effect（诊断）" +
"Matched-horizon replanning-cadence experiment（阴性/反向，含对称控制诊断）"；
reposition 降级；torpedo 改为 coverage×intensity 交互；engine 措辞统一；
tight-bound 数字按实测更正；heading dispersion bug 修正并在 changelog 声明
未进入任何 payoff。

## 15. Figure changes
Fig4 换成新的 $C_6$ 结果（含 CI 显著性编码 + 对称控制诊断面板）；
Fig7 的 rigid-vs-LF 面板改用 $C_6$（若 bridge 完成）；Fig5 caption 改为
"interaction of threat coverage and local intensity"。

## 16. KEEP / NARROW / REMOVE
REMOVE：commitment 作为核心贡献（含所有 premium 措辞）。
KEEP：路径积分表述、闭环简并+能力单调（含假设 (A1)(A2)）、LF 表示鲁棒性、
延迟威胁的 coverage×intensity×landscape 机制、external transfer boundary。
NARROW：reposition（表示依赖，仅诊断）。

## 17. Is Q2 readiness affected?
论文主线改为
`Path-integrated formation game + closed-loop structure + LF robustness +
delayed-threat response-space effects + external transfer boundary`，
仍具 Q2 竞争力；但不再有 commitment comparative statics 这一
numerical 卖点。

## 18. Next allowed task
按 §35/§43/§44 完成 REMOVE 分支的论文改写 + registry + advisor report +
stop gate + 打包。**不再发明新 commitment 定义。**
