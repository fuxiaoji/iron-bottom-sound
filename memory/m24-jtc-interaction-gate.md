---
name: m24-jtc-interaction-gate
description: M2.4 最后机会门——交互结构真实（28% 舰对 |φ|≥0.05）但协调收益不成立（W/T/L 6/9/4，中位 0），JTC 永久 kill，BARD 归档
metadata:
  type: project
---

包 `research/m2_4/M2_4_JTC_INTERACTION_LAST_GATE.zip` sha256 `5781e81a…`。历史 gate 与 M2.3 判定原样保留。PI 批准的**唯一一次**重测，FAIL 即永久 kill（已按此执行）。

**判定**：`INTERACTION_STRUCTURE = PRESENT`、`JTC_INTERACTION_GATE = FAIL（六条全否）`、`JTC_FINAL_STATUS = PERMANENTLY_KILL`、`BARD_FINAL_STATUS = ARCHIVED`、`IBS_NEXT_ROLE = APPLICATION_BENCHMARK_ONLY`。

1. **交互真实存在**：10 pilot / 150 舰对全部 engine-exact，median |φ|=0.000、p90 0.556、max 4.139、**28% 舰对 ≥0.05**。且用 engine-exact 的 q_i 构成的**精确可加模型**对精确联合值一致性仅 **0.037** → 加性描述确实不足（不是代理粗糙）。**注意**：原冻结判据用 cheap surrogate 的一致性（0.175）会把「代理质量」与「存在交互」混淆，两种已并列报告。
2. **但协调收益不成立**：主集 19 个可评状态侧 **6 胜/9 平/4 负**、win rate 0.316、中位 **+0.000**；**打不过 sequential 精确坐标上升**（CI [−0.722,0.000]）、打不过等预算随机（中位 −0.083）。**最有信息量的结论：逐舰依次 + 精确接受就已拿走全部可得协调收益**，显式建模 φ_ij 不增值。
3. **kill 有信息量**：修 bug 后首个状态 beam−greedy = +0.972、S-03 中位 +0.222，符号直到整面板跑完前开放。

**必须记住的自身缺陷**：M24-F1 主集用了 census 全部唯一状态侧（53，超集）而非冻结 35 组合；**M24-F2 精确评估失败被 `RuntimeError` 吞、状态静默丢弃（53→19、~30→11）**——红线 R3 形态，已标真实 n；M24-F3 主集意图标签退化全 I1（条件概率只报可算项）；M24-F4 交互臂两处真 bug（φ 的 u_j 基点错、模型只匹配首个探针），Gate I 通过后重读代码发现并重跑 Gate II。

相关：[[m23-mainline-disambiguation]] [[m22r-b1e-census]] [[m22-compiler-fidelity]]
