# V13.1 计划执行清单 — 实验阶段

用户最新范围：阅读两个 v13.1 文件，完成新实验，直到开写论文前。附件的研究假设作为待检验假设；其错误公式、循环充分条件和“失败即投稿”表述不能替代数学正确性、研究证据或用户的阶段边界。最新范围优先于旧 v12 完整写稿目标。

状态用语：“完成”指产物和检验已执行；“未触发”指失败分支禁止继续，不能宣称运行或通过；“范围外”指当前不允许写稿或投稿。最终数值和 Gate 以 FINAL_V13_ADVISOR_REPORT.md 与 V13_Q1_GATE.md 为准。

|计划节|事项|执行状态及证据|
|---:|---|---|
|0|不更换对手策略类来比较快慢 flexibility|完成；DISCOVERY_PROTOCOL.md、confirmatory_design/CONFIRMATORY_DESIGN.md|
|1|Conditional own-flexibility 主量|完成；四价值表及 conditional_flexibility 字段|
|2|对手 F/C 分别固定|完成；F^F=FF−CF，F^C=FC−CC|
|3|新 H1 互补假设|完成检验；失败，不将假设改成事实|
|4|player-swap 镜像|完成；所有主物理单元独立重建，NUMERICAL_AUDIT.json|
|5|H2 mobility-premium 解释|完成；THEOREM_SCRATCHPAD.md 证明 S_F−S_C=M；不增加独立端点|
|6|只做 solver regression|完成；REGRESSION_FINAL.log，30 项；未重跑 v12 完整 Monte Carlo|
|7|冻结 v12|完成；v12_freeze/、V12_FROZEN_CONCLUSIONS.md、429 文件原冻结清单|
|8|Exact Grid-3 discovery|完成；15 焦点物理单元及 15 镜像，discovery/|
|9|完整 2×2 factorial|完成；每单元 FF/FC/CF/CC，全部源数据保留|
|10|discovery 镜像运行|完成；独立物理交换与 parallel 转向反射映射|
|11|discovery 不替代确认|完成；探索结果独立标记，原验证设计不可变；实现修订单独披露|
|12|operating speed 与 capability 区分|完成；主模型是 forced speed，不误称 capability|
|13|固定速度主实验和可选能力升级|完成；T=4 绝对速度菜单严格嵌套，6 个单独 interaction；不加入主分母|
|14|moving favorable geometry|完成；冻结核导出集合，未硬编码 Crossing-T reward|
|15|不采用单一 argmax 主机制|完成；使用超水平集合，插图探针与时点事前固定|
|16|G_alpha 域和阈值|完成；相对位置/航向离散域、alpha=.9/.8、不正最大值规则预设|
|17|漂移指标|完成；directed median nearest-set、embedded centroid、symmetric Hausdorff、对手转向|
|18|reachable correction|完成；逐个合法单步终态比较，保留 signed R_raw 和负值标记|
|19|bounded Theta|完成且纠正原公式；R_plus/(R_plus+D+epsilon)，明确原 signed 形式不保证 [0,1]|
|20|mechanism outcome|完成；F 与 Theta 按对手类报告，27 单元完整探针与源数据|
|21|mediation-style ordering|完成诊断；DeltaTheta/M 相关、分层图、geometry/class/contrast FE；不主张因果中介|
|22|冻结确认设计|完成；原 FREEZE.json/设计 hash 不改，修订另存 IMPLEMENTATION_AMENDMENT_01.md 与 RERUN_FREEZE.json|
|23|held-out 参数|完成；.75/.90/1.10/1.25，各三几何、固定对手 1.0、固定 range|
|24|12 个 primary endpoints|完成；outer/inner ×三几何×两固定类；镜像不增加数量|
|25|成功分类|完成；FAIL，见 V13_Q1_GATE.md；不是期刊质量评分|
|26|Grid-5 refinement|未触发；基础 Gate 失败，停止扩展|
|27|Grid-7 六 anchors|未触发；不伪报稳定性|
|28|turn-rate robustness|未触发；不宣称一般 maneuverability 规律|
|29|T=4/6/8 robustness|未触发；独立 T=4 capability 不是同模型 horizon 验证|
|30|LF / rigid 六 anchors|未触发；不作跨编队模型稳健性结论|
|31|policy-set monotonicity 理论|完成；有限 minimax 嵌入论证与小规模数值检验|
|32|bilateral decomposition|完成；纯代数恒等式与非负项之差的无固定符号解释|
|33|increasing differences|完成 reduced theorem 与嵌套能力反例；完整模型的一般命题不成立/未获支持|
|34|不强证完整 naval theorem|完成；固定扰动、球约束、平方损失/reset 条件逐项写清；不用结论作假设|
|35|Q1 方法学叙事|成功前提未满足；范围外，不改写成一区主贡献|
|36|延后主论文|已遵守；本次未写主标题、摘要、贡献列表或正文|
|37|Q2 fallback|冻结完成；未获二区认证，有已知证明/叙事缺陷，不自动投稿|
|38|成功后论文结构|未触发且范围外；只保留附件方案，无新主论文|
|39|核心图 A–E|完成；外加 F 能力对照、G 指标诊断、H 数值分离，共八组 DRAFT PNG/PDF|
|40|related work|完成定向文献笔记；主原始来源与访问边界记录，新颖性不作认证|
|41|20 问最终导师报告|完成；FINAL_V13_ADVISOR_REPORT.md|
|42|科学纪律与停止|已执行；不改符号、不换分母、不补选参数，不写稿，不投稿|

主提示词 15 项对应：1→7；2→6；3→36–38；4→8–11；5→12–13；6→14–17；7→18–19；8→20–21；9→22–24；10→25；11→26–30；12→31–34；13→ITERATION_01/02/03.md；14→41；15→42。ITERATION_01 保留为原始历史记录，其修订前数值不作最终证据；ITERATION_02 记录失败和修正；ITERATION_03 记录最终结果与停止。

本计划包含三个已披露的必要数学/实现处理：有限速度菜单采用固定绝对速度以保证真正嵌套；bounded Theta 显式使用正部并保留 signed 指标；冻结后射界边界浮点错误通过一份独立实现修订处理并重算所有 v13。均未改变原 12 比较或按结果放宽 Gate。
