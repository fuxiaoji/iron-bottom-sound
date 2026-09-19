---
name: m1-g1-fail-b-toy-only
description: M1 G1 判定 FAIL（B_TOY_ONLY）——IBS 鱼雷窗口决策混叠真实但密度远低于门；若复活需 M2 级杠杆
metadata:
  type: project
---

2026-09-19，M1 主线 Decision-Sufficient State Learning 的 G1 硬门 **FAIL**（分支 `research/m1-decision-state`，提交 `27f23b2`）：G1_IBS_NATURALITY = FAIL，FINAL_M1_STATUS = B_TOY_ONLY，已按纪律停止（无 G2/神经网络/DSRL/PPO）。

关键数字：273 合法 pair（200 主 + 73 对照B）；15-rep CI-passing 20/22（主值/副值）；nontrivial 6/11（门 ≥25）；≥0.10 占 20%/36%（max 0.40/0.84）；对照 B 主值 22% 不低于主组。Control A 全部 bit-identical。

**核心科学发现**：隐藏承诺频繁改变**价值**（65/120 对 outcome 跨分支差 ≥0.2）但很少重排游戏自身候选集的**最优动作**——"value divergence ≠ decision aliasing"。置信与遗憾反相关（排名可分辨处恰有"两界皆稳"的鲁棒动作，如不发射）。

**Why**：若未来重访此主线，这些结论定义了起点：现象存在、可审计、但密度不足；瓶颈是脚本化续局 regime 与候选集，不是管线。

**How to apply**：复活杠杆（均未执行，M2 规模）：接触时刻最优续局 Q、全合法批次候选集、绑定想定胜利边际的值函数。证据：`research/m1/g1/G1_EXECUTIVE_SUMMARY.md`；包 sha256 `7f79f8ab…`。预算 ~35k/50k rollouts。

相关：[[m0-cheap-kill-findings]]、[[paper-v14-state]]
