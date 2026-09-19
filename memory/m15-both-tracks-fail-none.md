---
name: m15-both-tracks-fail-none
description: M1.5 双轨全灭（E1 不可预测 / E2 无因果效应）——hidden-commitment 挖题线终结，PI 需全系统重选题
metadata:
  type: project
---

2026-09-19，M1.5 验证两条新主线均被杀（分支 `research/m1_5`）：

- **E1 Selective Opponent Reasoning**：rho 分布完美（83-90% 低 / 10-17% 高且 stake 0.333 胜率）但**可见特征完全预测不了 criticality**（3 模型族 AUROC 0.37-0.47，假阴性含 76-100% 遗憾质量）。现象真实但认识论上封闭。
- **E2 Strategic Influence Planning**：影响特征在 48.5% 决策中改变 top-1（启发式层），但真实 CRN 续局 hybrid vs direct 仅 +0.02（60% 平局，S-01 恰为 0），且 **true influence ≈ shuffled influence**——启发式分歧是伪影。

**Why**：至此 M0（A/B/C/D）→ M1 G1（B_TOY_ONLY）→ M1.5（E1/E2 全灭）已系统性排除 hidden-commitment/torpedo 方向的全部主线变体。共同根因：脚本化续局下鱼雷决策极少 pivotal + 游戏自身评分机器不含可利用信号。

**How to apply**：PI 下一轮应按计划 §21 从整个 IBS 系统重新扫描选题（炮击/编队/指挥链/大图战役层等未挖区域），不再回到 commitment/torpedo。若重访 E1，先在 criticality 可读的域（exact lab 或有信念可观测性的 benchmark）验证方法，再谈 IBS 迁移。

证据：`research/m1_5/00_EXECUTIVE_SUMMARY.md`；包 sha256 `23113572945faefc…`。相关：[[m1-g1-fail-b-toy-only]]、[[m0-cheap-kill-findings]]
