---
name: m23-mainline-disambiguation
description: M2.3 裁决——JTC = FAIL（含 surrogate 可加性混淆）、BARD = FAIL（匹配对照砍半效应）、MAINLINE_CANDIDATE = NONE；M22R-F6 damaged 谓词勘误
metadata:
  type: project
---

分支 `research/m2-2-compiler-fidelity`，预注册 `research/m2_3/PRE_REGISTRATION_M23.md`。包 `research/m2_3/M2_3_MAINLINE_DISAMBIGUATION_BUNDLE.zip` sha256 `85d3e41f…`。历史 gate 全部原样保留。

**`MAINLINE_CANDIDATE = NONE`（两条 cheap-kill 都没过）**：

1. **JTC = FAIL**：多意图条款只有 I1 在两个场景达 ≥20%；协调条款在**同一** 35 个机会状态上 JOINT 1.048 < GREEDY 1.428 < RANDOM 1.831。**混淆写进判决正文（M23-F3）**：cheap surrogate 逐舰可加 → 逐舰贪心是它的**精确最优解**，该臂结构上无法检验协调；真实交互项（`_gunnery_modifiers` 的集火加成/分火惩罚）不在 surrogate 里。重测需含交互项的 surrogate + 新预注册。
2. **BARD = FAIL**：14 个同公开历史信息集（观测哈希与合法动作集在代码中强制一致）。真实隐藏集上冲突成立（11/14 crossover、5/14 无 ε-good 共享动作），但 size/diversity 匹配对照把 material 率从 **0.357 砍到 0.214** 且只剩 S-01 一个场景；公开规划器仅恢复天花板的 0.611/0.226/0.086（当前 AI 全 0.000）。既非 ARTIFACT（池化 21.4% 过线）也非 INFORMATION_LIMIT_ONLY（≥2 场景未满足）。**结论：先前 TORPEDO_PARTIAL_OBSERVABILITY 主要是假设集构造效应。**
3. **M22R-F6 勘误**：B1E 的 damaged 层为空是谓词死代码（读 `hull_max`，模型字段是 `max_hull`），非指挥官行为；旧数字不受影响。且 PI 字面 damaged 判据**不具区分度**（池内 234/234 满足）。

三处自身缺陷已记录：M23-F1 匹配对照锚点错位（12/14 集恰为 0.000，本会误判 ARTIFACT）、M23-F2 跨状态集比较、M23-F4 规划器计分口径不一致；M23-F5 记 BARD 落地前必需的管线修复。相关：[[m22r-b1e-census]] [[m22-compiler-fidelity]]
