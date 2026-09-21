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
| [m0-cheap-kill-findings.md](m0-cheap-kill-findings.md) | M0 四线结论（A_WEAK/B条件/C FAIL borderline/D FAIL）、实验室退化陷阱与 C0 门冲突 | project |
| [m1-g1-fail-b-toy-only.md](m1-g1-fail-b-toy-only.md) | M1 G1=FAIL（B_TOY_ONLY）：价值分歧普遍但决策混叠稀少；复活杠杆清单 | project |
| [m15-both-tracks-fail-none.md](m15-both-tracks-fail-none.md) | M1.5 双轨全灭（E1 不可预测/E2 无因果）——commitment 挖题线终结，需全系统重选题 | project |
| [m20-org-intel-reset-required.md](m20-org-intel-reset-required.md) | M2-0 组织智能三线全灭→RESET_REQUIRED；脚本化续局是系统性 regime 杀手 | project |
| [m21-platform-audit-partial.md](m21-platform-audit-partial.md) | M2.1 部分审计：规则 0 bug；同 seed≠CRN 实证；炮击层低杠杆；movement 因候选覆盖质疑未判定 | project |
| [m21r-gold-gate-fail.md](m21r-gold-gate-fail.md) | M2.1-R 测量修复完成但 Gold Gate FAIL（0/5）；G1 对抗下反号；开放=洗平 vs 编译器表达力 | project |
| [m21r2-mechanistic-decomposition.md](m21r2-mechanistic-decomposition.md) | M2.1-R2 机制分解：规则引擎陡峭定价几何（MG1/2/3 PASS）——问题定位在编译器与价值兑现层 | project |
| [m24-jtc-interaction-gate.md](m24-jtc-interaction-gate.md) | M2.4：交互真实（28% 舰对 |φ|≥0.05）但协调收益不成立（6胜/9平/4负）→ JTC 永久 kill，BARD 归档；含 M24-F1..F4 自查缺陷 | project |
| [m23-mainline-disambiguation.md](m23-mainline-disambiguation.md) | M2.3 裁决：JTC/BARD 双双 FAIL → MAINLINE=NONE；surrogate 可加性使联合臂无法检验协调；匹配对照把 BARD 效应砍半；M22R-F6 damaged 谓词勘误 | project |
| [m22r-b1e-census.md](m22r-b1e-census.md) | M2.2-R/B1E 自然普查：L0/L1 双尺度（intent 正局部/负外部性）、意图 bug=research-only、MG3-E PASS、graded vs binary per-route payoff 的陷阱、当前 AI 鱼雷 RR=0 | project |
| [m22-compiler-fidelity.md](m22-compiler-fidelity.md) | M2.2 编译器保真 FAIL（0/3）：机制值尺度改变符号（MG1 舰队 vs 舰对）、意图编译器把舷射转反、MG3 度量不可执行、MG4 走廊是全状态现象 | project |
| [m21r21-mechanistic-repair.md](m21r21-mechanistic-repair.md) | M2.1-R2.1 修复 F21/F22/F23：MG4 翻转 PASS（鱼雷走廊 28/29）；Crossing-T 定位到编译器占位 | project |

---

## 维护规则

1. **新增**：先查本索引是否已有覆盖同一事实的条目；有则**更新原文件**，不新建重复。
2. **纠错**：发现某条记忆已不成立（文件/函数/参数已变更）→ 改正文并在索引钩子里注明，或直接删除。
3. **不记录**：仓库已能自证的事实（代码结构、git 历史、`agent.md` 已写的规则）不重复记录；只记录**非显然**的、影响后续决策的事实。
4. **相关链接**：正文内用 `[[name]]` 链接相关记忆。
