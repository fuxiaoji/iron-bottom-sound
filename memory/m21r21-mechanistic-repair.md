---
name: m21r21-mechanistic-repair
description: M2.1-R2.1 修复 F21/F22/F23——MG4 翻转为 PASS（鱼雷走廊剥夺 28/29 路线）；门 3/5 FAIL；Crossing-T 定位到编译器
metadata:
  type: project
---

2026-09-21，M2.1-R2.1（分支 `research/m2-1-platform-audit`）：修复三项测量缺陷后重判。**门 = 3/5 FAIL**（阈值不变，MG1/MG3 冻结）。

- **F21（PI 发现）已修**：旧 fire meter 对每个 (ship,target,mount) 三元组累加 → 重复计炮。重写为合法分配；同时修正引擎语义三处（`attackers` 集火加成 / `target_count` 分火惩罚 / 按 `mount.kind` 分组查表 / `_can_see` 能见度）。所有臂批次通过 validator。
- **MG4 = PASS（翻转）**：F22 时空段错位一格（`path[allowance]` 是回合起始格不是首个落点）+ F23 引擎 combo API 只给拦截瞄准（该状态 2 个相同 combo，无走廊自由度）。修复：288 个合法配置几何预选 + 实发长程设定（range 25）→ 覆盖受害者 **28/29** 条 T+1 路线，RouteReduction 0.966，**时空预测 vs 引擎 torpedo_contact 29/29 一致**。持久性探针 6/6 PASS（PI 引擎解读确认）。
- **MG2 = FAIL**：合法计量下交换比 1.56×（过）但纵向舷射占比 0.44<0.50（不过）→ CROSS 臂**没把本方摆到敌纵列前方**；PARALLEL 追击几何反而 0.89。定位为占位/编译器问题（Stage B 主题），非规则问题。
- **MG5 = FAIL（确认）**：合法计量下 DISPERSE 仍优（19.22 vs 13.19）；炮程 ≥ 舰队间距使局部优势不可表达。

**Why**：规则层杠杆现已有三项（炮位展开、距离控制、**鱼雷海域拒止**）经引擎原生 API 验证；Crossing-T 未证实的原因是"够不到舷射位置"。

**How to apply**：PI 放行 Stage B 时的第一问＝编译器能否把舰队摆进规则奖励的几何（T 头占位、舷射展开）。证据：`research/m2_1/05_REPAIRED_GOLD_GATE.md`；包 sha256 `2874b578…`。

相关：[[m21r2-mechanistic-decomposition]]、[[m21r-gold-gate-fail]]
