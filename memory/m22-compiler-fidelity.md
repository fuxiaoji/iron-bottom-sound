---
name: m22-compiler-fidelity
description: M2.2 战术编译器保真审计——冻结度量下舰队/舰对尺度结论相反；现有意图编译器把舷射意图转反；MG3 注册度量不可执行；MG4 走廊是全状态现象
metadata:
  type: project
---

分支 `research/m2-2-compiler-fidelity`。预注册 `research/m2_2/PRE_REGISTRATION_M22.md`（先于测量）。
**GOLD_COMPILER_GAP = FAIL（0/3；冻结度量下仅 1/3 可计算）**。历史判决逐字保留（MG1/MG3/MG4 = VALID PASS；门 3/5 FAIL）。

四条引擎真实的结论：

1. **机制值的尺度会改变符号（MG1）**。冻结的 `M_broad` 舰队级实现：手工舷射 gold −12.17、随机均值 −6.32、当前策略 −5.47、beam **+5.47**（分母非正 → 按预注册不可计算）。同一公式限制在该案例自身的舰对上：gold +1.89 > 随机 +1.44 > 当前 +1.36，SEARCH 保真度 **+0.876**、CURRENT_POLICY **−0.178** → 该案例在舰对尺度上**是**编译器缺口。展开舷射赢舰对、输舰队（M2.1-R"暴露对称"的单舰隔离版）。
2. **仓库自带意图编译器把舷射意图转反**：intent `BROADSIDE` → 焦点舰收到 `1S1P`（与**反向臂逐字符相同**，post_rel 5 / 1 炮位；gold 是 post_rel 1 / 3 炮位），舰对保真度 −2.53。表达式 `((b-1+1)%6)+1` 取错方向。**任何"发意图让 AI 编译"的组织结构都会继承这个反向转向。**
3. **MG3 注册度量不可执行（M22-F4）**：冻结 PASS 的 2.56 vs 0.94 在 15/17 格，该状态盟军能见度 **13 格**、radar 规则 **OFF** → 两臂 `_can_see=False`，引擎会 `gunnery_rejected`。引擎真实计量下两臂均 0.000。注册度量只查 `_mount_can_bear`；MG3 在 R2.1 被冻结，没拿到 MG2/MG4 的能见度修复。历史判决未改，只加诊断。
4. **MG4 鱼雷走廊是全状态现象**：gold RouteReduction 0.966 精确复现（时空接触 12/12 与引擎一致）。可部署公开搜索 **0.107**、当前 AI **0.000**（该状态 0 条鱼雷令）。公开目标**并列主导**：argmax 并列集 RR 跨 0.00–0.97，最优配置公开得分最低 → `PUBLIC_INFORMATION_GAP = CONFIRMED`。

**反例（常备）**：公开分与真实 RR 的 Spearman = +0.676，只报相关系数会得出"公开信号可排序"的错误结论——并列集分解才是证据。

`NATURAL_OPPORTUNITY_RATE = NOT_MEASURED`（B1 以 B0 PASS 为门，未运行）。失败留档 M22-F1..F5 见 `research/m2_2/FAILURES_AND_COUNTEREXAMPLES.md`。相关：[[m21r21-mechanistic-repair]] [[m21r2-mechanistic-decomposition]] [[m21r-gold-gate-fail]] [[m21-platform-audit-partial]]
