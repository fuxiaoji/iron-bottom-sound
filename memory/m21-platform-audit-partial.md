---
name: m21-platform-audit-partial
description: M2.1 平台审计部分完成——规则无 bug；同 seed≠CRN（分支错位实证）；炮击层低杠杆；movement 层因专家覆盖性质疑未判定
metadata:
  type: project
---

2026-09-20，M2.1（分支 `research/m2-1-platform-audit`）按 PI 指示在 80/93 快照处停止打包：

- **规则引擎无 bug**（0 BUG/UNKNOWN）；非法移动 fallback=接口更严；编队上限 8-vs-4 记录在案。
- **RNG=MATCHED_INITIAL_SEEDS_ONLY**：每次掷骰独立 `Random(seed*1e6+counter)`；HOLD 45 vs FIRE 63 draws 实证分支即错位。**任何 IBS 实验都不能宣称 CRN**。
- **炮击层低杠杆**（唯一完成层）：中位 λ 0.000-0.018，零状态 ≥0.05；hold-vs-fire 有差异但目标分配无差异（5 profile 炮击批次全同）。
- **movement/torpedo 未测**。用户（游戏专家）指出候选集缺大师级联合机动（舷侧抢位/crossing T/鱼雷航道封锁/距离控制）——F8 记录了三个待检验掩盖机制：候选同质化、脚本续局洗平（E2/E3 检验）、horizon 太短。

**Why**：炮击低杠杆符合常识（自动分配器即共识+伤害小）；movement 是真正未解的问题，且在候选扩充前**任何"IBS 低杠杆"的平台结论都不成立**。

**How to apply**：复活此审计的顺序=扩候选（战术联合计划）→ E0 movement 重测 → E2/E3 洗平检验 → horizon 曲线 → 平台判定。证据：`research/m2_1/00_EXECUTIVE_SUMMARY.md`；包 sha256 `4977395c…`。

相关：[[m20-org-intel-reset-required]]、[[m1-g1-fail-b-toy-only]]
