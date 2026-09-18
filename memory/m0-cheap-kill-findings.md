---
name: m0-cheap-kill-findings
description: 2026-09-18 M0 四线 cheap kill 结论（A_WEAK/B 条件通过/C FAIL borderline/D FAIL）、实验室两大退化陷阱、C0 门冲突——恢复 M0 工作前必读
metadata:
  type: project
---

M0 多主线验证（分支 `research/m0-validation`，基线 `7ab8ac4`）的 cheap kill 结论，产物在 `research/m0/`（CHEAP_KILL_REPORT.md 是入口）：

- **A (CARP) = WEAK**：Δ 信号真实且随 horizon 单调，但 28/74 局零 span、55% 节点 Δ<0.1、trivial 日程在 24% 可评估点已达门。救 A 需先找到"日历失败"的 regime。
- **B (CAIS) = PASS_TO_DISCOVERY（条件性）**：18/72 局 snapshot-policy regret>0（max 2.0），对照全 0。**两个致命实验室陷阱**：`alpha=0` → 信号与 θ 无关 → 可证无 aliasing（假"B_FAIL"）；`K=2,m=2` → 首步识别 θ。**度量陷阱**：计划原文的 AliasGap（值差）恒 0 = 假阴性，必须用 `min_a max_h[V−Q]`。**未做**：IBS 自然反例（B4）——不做则只能标 B_TOY_ONLY。
- **C (CD-PSRO) = FAIL（borderline 待 PI）**：S-03 势均局省 71%，S-01 一边倒局 0/5 到达。**门冲突 F12**：文本门"inconsistent→SMALL" vs 代码门"never-reached→FAIL"，未事后改判。support_weighted 永不产生证书（真实反例）。
- **D (DiagGame) = FAIL**：MYO≡OPT、NBU≡NOM 全 684 测试不可分；本实验室支付族不惩罚短视。greedy infogain 0/5（在不可分对上死锁）。

**Why**：这些结论与陷阱是恢复 M0 工作（discovery 或反驳性复核）时的第一手约束；重跑时若结果不同，先查是否踩了已记录的陷阱（F1/F2/F10/F11）。

**How to apply**：任何 M0 后续先读 `research/m0/CHEAP_KILL_REPORT.md` + `FAILURES_AND_COUNTEREXAMPLES.md`；B 线若推进，第一件事是 IBS 自然 sealed-order 反例；C 线若被 PI 复活，第一任务是刻画 near-tied rows 下 greedy 停滞的 regime。IBS 预算已用 2238/20000。

相关：[[paper-v14-state]]、[[pipeline-governance]]
