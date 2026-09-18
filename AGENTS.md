# Repository agent entrypoint

All contributors and coding agents must read and follow [agent.md](agent.md) before changing this repository. `agent.md` is the single authoritative project-governance document.

## 每轮会话的固定入口

1. [agent.md](agent.md) — 治理宪法（权威优先级、模块边界、会话纪律、子 agent 审计、红线）
2. [todo.md](todo.md) — 当前活动任务
3. [PROGRESS.md](PROGRESS.md) — 论文流水线 25 阶段台账与版本循环登记
4. [MEGA_PROMPT.md](MEGA_PROMPT.md) §2 + [RESTRICTS.yaml](RESTRICTS.yaml) — 阶段/门控/约束复习
5. [memory/MEMORY.md](memory/MEMORY.md) — 长期记忆索引

## 论文流水线相关文件

| 文件 | 用途 |
|---|---|
| [MEGA_PROMPT.md](MEGA_PROMPT.md) | 25 阶段流水线总纲（用户粘贴提示词文档化产物） |
| [docs/pipeline/STAGE_PROMPTS.md](docs/pipeline/STAGE_PROMPTS.md) | 阶段提示词注册表（原文照录） |
| [RESTRICTS.yaml](RESTRICTS.yaml) | 可机读约束清单（红线阈值 + 待确认槽位） |
| [plan.md](plan.md) | 批次级计划 |
| [havedone.md](havedone.md) | 只追加的完成记录（测试、证据、提交哈希） |
| [memory/](memory/) | 项目内长期记忆（正文 + 索引） |
