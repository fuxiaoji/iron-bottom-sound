---
name: m21r-gold-gate-fail
description: M2.1-R 测量修复完成但 Gold Gate FAIL（0/5 分离，G1 在对抗下反号）——开放问题：脚本洗平 vs 候选编译器表达力
metadata:
  type: project
---

2026-09-20，M2.1-R（分支 `research/m2-1-platform-audit`）：PI 判定原 M2.1 E0 无效后执行测量修复。四项 PI 指定修复全部完成验证（U1 冻结定义+4 单测、sha256 派生 seed replicates、gunnery 双方 submit+seal、P0/T0/T1/T2/Terminal、显式 baseline）。另发现修复 F9（几何采样早一个相位）与 **F10 航向 off-by-one**（`((b-1)%6)+1 ≡ b` 使全部意图候选坍缩为同一批次）。

**Gold Gate = FAIL（0/5）**：5 个专家战术模式（抢舷侧/cross T/距离控制/鱼雷走廊/局部集中）在修复后 evaluator 下的 T2 分离只有 0.003-0.033（门 0.05）。**最有信息量的负结果：G1 unmask 在 E0 +0.011 但在 E3 对抗下 −0.015**——舷侧暴露是双刃剑，位置价值取决于对手是否惩罚它。E3 把 E0 差距压缩 2-4 倍。

**Why**：平台判定仍 UNRESOLVED，两个假说未分：(a) evaluator 家族（脚本+profile 池+局部 minimax）无法为需要多回合意图性利用的位置价值定价；(b) intent→plan 编译器（60° 量化+逐舰贪心）表达不了专家战术。

**How to apply**：若 PI 重开，顺序=真 intent-to-path 编译器（多回合机动形状）→ 重跑 gate → 才轮到 E0/E2/E3 mass census。F14 记录了意图词汇表混叠问题（CLOSE/PRESS/CONCENTRATE 编译为同一 batch）。证据：`research/m2_1/STRATEGIC_GOLD_CASES.md`；包 sha256 `d3c77d05…`。

相关：[[m21-platform-audit-partial]]、[[m20-org-intel-reset-required]]
