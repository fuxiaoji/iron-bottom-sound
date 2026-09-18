---
name: pipeline-governance
description: 论文流水线治理五件套（agent.md / todo.md / plan.md / havedone.md / PROGRESS.md）各自的职责与每轮会话的读写时序
metadata:
  type: project
---

2026-09-18 起，`iron-bottom-sound` 仓库的论文流水线按下述分工留痕，**不得把同一信息散落多处**：

| 文件 | 职责 | 写入方式 |
|---|---|---|
| `agent.md` | 治理宪法（权威优先级、模块边界、会话纪律、子 agent 审计、红线） | 稳定，规则变化时改写 |
| `MEGA_PROMPT.md` | 25 阶段流水线总纲（由用户粘贴提示词文档化而来） | 流程变化时改写 |
| `RESTRICTS.yaml` | 机器可读约束清单（含红线阈值与 `pending_slots`） | 约束增减时改写 |
| `todo.md` | **滚动**活动任务清单 | 每轮会话更新，完成后移出 |
| `PROGRESS.md` | 25 阶段**阶段级**台账 + 版本循环登记表 | 每阶段结束追加 |
| `plan.md` | **批次级**计划 | 每批次追加在顶部 |
| `havedone.md` | **只追加**完成记录（测试、证据、提交哈希） | 只追加，不改写 |
| `docs/pipeline/STAGE_PROMPTS.md` | 阶段提示词注册表（原文照录） | 提示词变化时改写 |
| `memory/`（本目录） | 长期记忆正文 + 索引 | 见 [[MEMORY]] |

**每轮会话的强制时序**：

1. 开始：读 `agent.md` → `todo.md` → `PROGRESS.md` 末尾状态；复习 `MEGA_PROMPT.md` §2 与 `RESTRICTS.yaml`。
2. 工作中：每完成一个阶段，在 `PROGRESS.md` 登记产物摘要、版本号与变化点。
3. 结束：证据写入 `havedone.md`，活动任务从 `todo.md` 移出，必要时更新 `memory/`。

**Why**：仓库此前已有 `plan.md`（129 KB）与 `havedone.md`（168 KB），若再引入职责重叠的第三份台账，历史会碎片化且互相矛盾。上述分工是**在既有文件基础上补足缺口**（阶段台账、约束清单、活动任务），而不是替换或另建平行体系。

**How to apply**：写任何记录前先自问"这条信息属于哪个文件"；若发现两条记录冲突，以 `agent.md` 的权威优先级裁定，并在 `PROGRESS.md` 登记冲突与裁定结果。

相关：[[paper-v14-state]]、[[pending-user-slots]]
