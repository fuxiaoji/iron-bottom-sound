---
name: m21r2-mechanistic-decomposition
description: M2.1-R2 机制分解定位成功——规则引擎对几何陡峭定价（MG1/2/3 PASS），失败在编译器与价值兑现层；MG4/MG5 失败分类
metadata:
  type: project
---

2026-09-21，M2.1-R2 Stage A（分支 `research/m2-1-platform-audit`）：**MECHANISTIC_GOLD_GATE = FAIL（3/5）**，但这是定位性成功：

- **规则引擎对几何陡峭定价**：MG1 broadside vs narrow = +92.9% 期望命中（同位置纯转向实验，两段式探针解决同时移动方位失效）；MG2 cross-T 净交换 1.68× 平行臂（64 对纵向修正）；MG3 BB 射程差 2 hex = 2.72× 期望命中。全部用引擎原生 API（_mount_can_bear/_target_aspect/_gunnery_modifiers/D66 积分）。
- **MG4 鱼雷走廊 = CASE_CONSTRUCTION_FAIL**：三种瞄准方案下 T+1 路由逐 13 位相同——鱼雷未存活到/未覆盖下一回合路由；需源码研究 `_resolve_torpedoes` 的持久性语义。
- **MG5 局部集中 = TACTICAL_ASSUMPTION_NOT_SUPPORTED**：炮程 8+ hex > 6 hex 集群间距，DISPERSE 边际反而更好（82.7 vs 56.6）。
- **关键规则事实**：首 MF 必须直航（无 cost-0 转向）；_target_aspect 是目标朝向属性（与射击方航向无关）；命中表是 D66（11-66）须用 d66_adjust 钳位积分。

**Why**：五轮实验（M0→M2.1-R2）首次把"游戏/编译器/尺子"三者分开。结论：规则丰富、编译器与价值兑现是瓶颈。

**How to apply**：PI 裁决方向：(1) 建真 intent-to-path 编译器（多回合机动形状、舰队形状目标）后重跑 Stage B；(2) 建能兑现位置价值的 Research Evaluation Policy 后跑 Stage C；(3) 或降级 IBS。已建成资产：micro.py 相位精确测量机器 + 5 个可复现微案例。证据：`research/m2_1/06_MECHANISTIC_GOLD_GATE.md`；包 sha256 `d2556f1b…`。

相关：[[m21r-gold-gate-fail]]、[[m21-platform-audit-partial]]、[[m20-org-intel-reset-required]]
