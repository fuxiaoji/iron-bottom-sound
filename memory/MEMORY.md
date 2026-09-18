# 项目长期记忆索引（Project Memory Index）

> **位置**：`iron-bottom-sound/memory/`（项目内，随 Git 版本化）
> **与 ZCode 用户级记忆的关系**：`~/.zcode/cli/memories/projects/seawar-*/memory/` 是**每次会话自动加载**的索引层；本目录是**持久、可共享、随仓库走**的正文层。写入规则：新事实写入本目录正文文件，并在本文件登记一行；同时在用户级记忆目录留一条指向本目录的指针，保证下次会话能自动找到。
> **写入格式**：每文件一个事实，带 frontmatter（`name` / `description` / `metadata.type`）。`type` ∈ `user` | `feedback` | `project` | `reference`。
> **红线**：不得写入密钥、令牌、私有推理或未经核验的结论。

---

## 索引

| 记忆 | 一句话钩子 | 类型 |
|---|---|---|
| [pipeline-governance.md](pipeline-governance.md) | 治理五件套的职责分工与读写时序（agent.md / todo.md / plan.md / havedone.md / PROGRESS.md） | project |
| [nature-skills-install.md](nature-skills-install.md) | nature-skills 安装位置、源 commit 与更新命令 | reference |
| [agent-delegation-environment.md](agent-delegation-environment.md) | 子 agent 可用工具面与模型路由现状（含 GLM 未配置的事实） | reference |
| [delegation-audit-policy.md](delegation-audit-policy.md) | 派发子 agent 的选型、并行与**产出审计**纪律 | feedback |
| [paper-v14-state.md](paper-v14-state.md) | v14 论文与研究线的当前真实状态（含未完成项） | project |
| [pending-user-slots.md](pending-user-slots.md) | 阻塞流水线的 8 个待用户确认槽位 | project |

---

## 维护规则

1. **新增**：先查本索引是否已有覆盖同一事实的条目；有则**更新原文件**，不新建重复。
2. **纠错**：发现某条记忆已不成立（文件/函数/参数已变更）→ 改正文并在索引钩子里注明，或直接删除。
3. **不记录**：仓库已能自证的事实（代码结构、git 历史、`agent.md` 已写的规则）不重复记录；只记录**非显然**的、影响后续决策的事实。
4. **相关链接**：正文内用 `[[name]]` 链接相关记忆。
