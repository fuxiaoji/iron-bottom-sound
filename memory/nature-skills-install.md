---
name: nature-skills-install
description: nature-skills 科研技能包的安装位置、源 commit、跨技能引用约束与更新命令
metadata:
  type: reference
---

2026-09-18 安装 `Yuan1z0825/nature-skills`（GitHub，约 43k★，Apache-2.0）到本机。

- **稳定 clone**：`~/ai-skills/nature-skills`（保留 `.git`，源 commit `2375e0abdf42158ef149256f2c64b1f759a0d274`）
- **ZCode 用户技能目录**：`~/.zcode/skills/nature-*`（20 个目录，约 38 MB）
- **同步脚本**：`~/ai-skills/sync-nature-skills.sh`（`--pull` 先 `git pull` 再重新同步）
- **可触发技能（19）**：`nature-academic-search`、`nature-citation`、`nature-data`、`nature-downloader`、`nature-experiment-log`、`nature-figure`、`nature-image2ppt`、`nature-literature-pipeline`、`nature-paper-card`、`nature-paper-to-patent`、`nature-paper2ppt`、`nature-polishing`、`nature-reader`、`nature-ref-verifier`、`nature-response`、`nature-reviewer`、`nature-statistics`、`nature-writing`，以及 `nature-proposal-writer`（其 frontmatter `name:` 为 **`researchwrite`**，不是目录名）
- **支持包（1）**：`nature-shared` —— 本身不被当作独立触发技能，但**必须与其它技能同级存在**，否则引用断裂

**关键约束（决定安装方式）**：技能内部大量使用 `../../../nature-shared/core/*.md`、`../../../../nature-shared/journal-formats/*.md` 这类相对引用。因此**只能整目录复制 `skills/nature-*`，不能只复制 `SKILL.md`**。把每个 `skills/nature-*` 目录复制为 `~/.zcode/skills/nature-*` 后，`../nature-shared` 恰好解析到 `~/.zcode/skills/nature-shared/`，引用完整保留（已实测校验 `core/reader-workflow.md`、`core/terminology-ledger.md`、`core/main-text-discipline.md`、`journal-formats/nature.md`、`core/nature-abstract.md` 全部命中）。

**更新**：`~/ai-skills/sync-nature-skills.sh --pull`。

**已知非致命断裂**：`nature-paper-card/README.md` 指向 `../../docs/*tutorial*.md`，位于 clone 的 `docs/` 下，复制后失效——仅影响该 README 的教程链接，不影响技能执行。

相关：[[agent-delegation-environment]]
