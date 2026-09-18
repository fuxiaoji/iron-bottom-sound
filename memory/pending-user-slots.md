---
name: pending-user-slots
description: 阻塞论文流水线的待用户确认槽位清单，以及"在缺失时应当停下而不是编造"的判定
metadata:
  type: project
---

用户在 2026-09-18 的粘贴提示词中留下若干 `<...>` 槽位未填。这些槽位**决定流水线能否继续**，凡缺失处必须停下向用户索取，**不得用合理推测填充**（`RESTRICTS.yaml` §10 `pending_slots` 同步登记）。

| 编号 | 槽位 | 缺失导致无法做的事 |
|---|---|---|
| B-1 | `<目标会议名称>` | 无法选模板、无法定 Related Work 的组织方式与贡献叙述强度、阶段 9/16–23 无判定基准 |
| B-2 | `<截稿日期及时间>` | 无法做阶段 11 资源规划与动态缩放（种子数、步数上限） |
| B-3 | `<限制页数>` | 无法做阶段 17/19 的页数与字数防守 |
| B-4 | 会议 LaTeX 模板目录 `paper/<目标会议模板文件夹>/` | 阶段 22 无法导出投稿件 |
| B-5 | `<指定年份>`（文献年份下限） | 阶段 4/5/23 无法筛文献 |
| B-6 | `OPENAI_API_BASE/KEY`、`KAGGLE_API_TOKEN`、`TAVILY_API_KEY` | 阶段 4 真实 API 检索、阶段 12 部分实验无法运行 |
| B-7 | `<模型1..4>` 可选模型清单 | 阶段 10/13/14 的模型选型无依据 |
| B-8 | 占坑版摘要的位置与冻结状态 | 原文要求"应尽可能不修改"，但未给路径；现行候选是 `paper_v14/sections/abstract.tex`，**需用户确认是否为已提交的占坑版** |

**另有 6 个阶段在原文中只有名称、没有提示词模板**（8.5 `THEORETICAL_BOUNDS`、12 `EXPERIMENT_RUN`、13 `ITERATIVE_REFINE`、23 `CITATION_VERIFY`、24 `3RD_PARTY_REVIEW`、25 `REBUTTAL`）。这 6 个的模板同样需要用户补充，或由用户在知情下授权按 `MEGA_PROMPT.md` §2.2 的职责描述另行设计并登记进 `docs/pipeline/STAGE_PROMPTS.md`。完整性核对表见该文件附录。

**How to apply**：推进流水线前先查本表；命中任一未解槽位 → 停在对应阶段之前，把问题一并提给用户（而不是逐个来回问），并继续做**不依赖该槽位**的工作。

相关：[[paper-v14-state]]、[[pipeline-governance]]、[[agent-delegation-environment]]
