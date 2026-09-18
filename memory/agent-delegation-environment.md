---
name: agent-delegation-environment
description: 本机可用作子 agent 的执行通道与模型路由现状（claude CLI 指向 DeepSeek；GLM 未配置；Agent 工具仅暴露固定 subagent_type）
metadata:
  type: reference
---

2026-09-18 实测的本机委派环境，**决定了"用 glm4.7 / glm4.6v 跑子 agent"目前能不能落地**：

**可用 CLI**：

- `claude` → `/opt/homebrew/bin/claude`，**可用**。其 `~/.claude/settings.json` 已把 `ANTHROPIC_BASE_URL` 指向 `https://api.deepseek.com/anthropic`，模型别名全部映射为 `Deepseek-v4-pro[1m]`。即：**`claude -p` 目前跑的是 DeepSeek，不是 Claude，也不是 GLM。**
- `gh` → `/opt/homebrew/bin/gh`，可用于 GitHub 操作与（按用户设定）Copilot CLI 写代码。
- **未安装**：`codex`、`gemini`、`ollama`。

**模型凭据现状**：

- 本机当前 shell **没有** `OPENAI_API_BASE` / `OPENAI_API_KEY` / `KAGGLE_API_TOKEN` / `TAVILY_API_KEY`（`MEGA_PROMPT.md` §8.1 声明的槽位）。
- 仓库只有 `.env.example`（声明 `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL` / `DEEPSEEK_MODEL` / `IBS_DB_PATH`），`.env` 不存在且已在 `.gitignore` 中。
- `~/.zcode/cli/config.json` **只有** `plugins` 一个键 —— 没有 `providers` / `models` / `agents` 配置。
- 因此**目前无法把子 agent 路由到 glm4.7 / glm4.6v**：既没有 GLM 端点的 base URL 与 key，也没有 ZCode 侧的模型映射配置。

**ZCode 内置 Agent 工具的实际能力面**：

- 只能指定 `subagent_type`：`general-purpose`（全工具）、`Explore`（只读检索）、`judge` / `document-skills:judge`（渲染件视觉验收）。
- **没有** per-call 的模型选择参数。子 agent 用哪个模型由会话/客户端配置决定，不由调用方指定。

**要真正启用 GLM 免费模型做子 agent，需要用户提供**（缺一不可）：

1. GLM 的 OpenAI 兼容 base URL 与 API key；
2. 若走 ZCode 原生子 agent，需要客户端侧的模型/提供商映射配置；
3. 若走 CLI 通道，需要一条独立的 wrapper（例如另建一个指向 GLM 端点的 `claude` 风格配置或用 `curl` 直连），**且不得把 key 写进仓库**。

相关：[[delegation-audit-policy]]、[[nature-skills-install]]、[[pending-user-slots]]
