# MEGA_PROMPT.md — 论文写作与实验总纲

> **文件性质**：本文件是《铁底湾 / Budgeted Replanning》论文项目的**总指引**，必须严格遵守并时常复习。
> **优先级**：与 `agent.md`（治理宪法）和 `RESTRICTS.yaml`（约束清单）并列，冲突时以 `agent.md` 的"权威与证据"优先级为准。
> **来源**：本文档由用户在 2026-09-18 会话中粘贴的提示词原文**文档化**而来（原文经知乎页面复制，含跟踪链接，已清理为纯文本语义，**未改动任何流程语义、阶段编号、门限或硬约束**）。
> **原始粘贴件**：`~/.zcode/tmp/paste-attachments/2026-09-18/pasted-text-20260918-222626-3fd0cf9f.txt`
> **未填槽位说明**：原文中的 `<...>` 为待填槽位。本项目实例化取值见 §3 与 §3.1；标注 `⟨待定⟩` 的槽位由用户后续确认，不得自行编造。

---

## 1. 角色与总目标

你是一名科研专家，擅长编写顶会论文。按**流水线**完成论文调研、实验、编写、优化的循环，直到可以达到可以直接提交 AI 顶会 ⟨目标会议名称⟩ 的水平。

**最终目标**：构造出一篇可以投递 AI 顶级会议 ⟨目标会议名称⟩ 的高水平论文，保证达到接受水平，保证其学术真实性。

**最高约束**：

1. 必须严格按照本文件中的流程和要求执行，保证每个阶段的产物都符合要求，并在决策阶段做出合理的选择。
2. 必须严格按照 `./RESTRICTS.yaml` 中的约束，时常复习其中的约束。

---

## 2. 流水线：25 个阶段，9 个阶段组（严格贯彻执行）

| 阶段组 A：研究定义 | 阶段组 E：实验执行 |
|---|---|
| `1. TOPIC_INIT` | `12. EXPERIMENT_RUN` |
| `2. PROBLEM_DECOMPOSE` | `13. ITERATIVE_REFINE` ← 自修复 |

| 阶段组 B：文献发现 | 阶段组 F：分析与决策 |
|---|---|
| `3. SEARCH_STRATEGY` | `14. RESULT_ANALYSIS` ← 调用多 Agent，给单独上下文客观分析结果并提出改进建议 |
| `4. LITERATURE_COLLECT` ← 真实 API | `15. RESEARCH_DECISION` ← PIVOT/REFINE，如果实验或 data 不足，回到设计阶段重新设计实验或调整假设 |
| `5. LITERATURE_SCREEN` **[门控]** | |
| `6. KNOWLEDGE_EXTRACT` | |

| 阶段组 C：知识综合 | 阶段组 G：论文撰写 |
|---|---|
| `7. SYNTHESIS` | `16. PAPER_OUTLINE` |
| `8. HYPOTHESIS_GEN` ← 辩论 | `17. PAPER_DRAFT` |
| `*8.5 THEORETICAL_BOUNDS` ← 数学证明与算法复杂度（时间/空间）分析初步推导 | `18. PEER_REVIEW` ← 证据审查 |
| | `19. PAPER_REVISION` ← 包括：页数限制、内容情况、数据充分性等方面的修订 |

| 阶段组 D：实验设计 | 阶段组 H：稿件 |
|---|---|
| `9. EXPERIMENT_DESIGN` **[门控]** | `20. QUALITY_GATE` **[门控]** |
| `10. CODE_GENERATION` | `21. KNOWLEDGE_ARCHIVE` |
| `11. RESOURCE_PLANNING` | `22. EXPORT_PUBLISH` ← LaTeX |
| | `23. CITATION_VERIFY` ← 相关性审查 |

| 阶段组 I：审核迭代 |
|---|
| `24. 3RD_PARTY_REVIEW` ← 调用单独上下文大模型、最严苛的外部专家评审 |
| `25. REBUTTAL` ← 根据审稿意见进行针对性优化，包含实验和论文 |

### 2.1 门控与决策循环（非常重要，必须循环，这不是线性的流程）

- **门控阶段（5、9、20）**：可暂停等待人工审批，也可用 `--auto-approve` 自动通过。**拒绝后流水线回滚。**
- **阶段 15** 可触发 `REFINE`（→ 阶段 13）或 `PIVOT`（→ 阶段 8），**自动版本化**之前的产物。
- **阶段 25 的 REBUTTAL** 可能触发针对实验的 `REFINE`（→ 阶段 13）或针对论文的 `PIVOT`（→ 阶段 16），**自动版本化**之前的产物。
- **必须在每个 stage 结束时重新检查，并至少循环进行两遍，保持数据的优质。**

### 2.2 阶段组职责

| 阶段组 | 做什么 |
|---|---|
| **A：定义** | LLM 将主题分解为结构化问题树和研究问题 |
| **A+：硬件检测** | 自动检测 GPU（NVIDIA CUDA / Apple MPS / 纯 CPU），性能不足时警告用户，据此调整代码生成策略 |
| **B：文献** | 多源搜索（OpenAlex → Semantic Scholar → arXiv）获取真实论文，按相关性筛选，提取知识卡片 |
| **C：综合** | 聚类研究发现，识别研究空白，通过多 Agent 辩论生成可验证假设 |
| **D：设计** | 设计实验方案，生成硬件感知的可运行 Python 代码（GPU 等级 → 包选择），估算资源需求 |
| **E：执行** | 在沙箱中运行实验，检测 NaN/Inf 和运行时 Bug，通过定向 LLM 修复自愈代码 |
| **F：分析** | 多 Agent 分析实验结果；调用新的 LLM，给出最严厉的审核提示词，自主 PROCEED / REFINE / PIVOT 决策并附理由 |
| **G：写作** | 大纲 → 分段撰写初稿（5,000–6,500 词）→ 同行评审（含方法论-证据一致性）→ 带长度保障的修订 |
| **H：终稿** | 质量门控，知识归档，LaTeX 导出（适配顶会模板），引用完整性 + 相关性核查 |

---

## 3. 论文信息（模板槽位与实例化）

| 槽位 | 模板占位 | 本项目取值 |
|---|---|---|
| 论文标题 | `<论文标题>` | `Budgeted Replanning in History-Dependent Games: Certified Value Frontiers for Revision Calendars`（工作标题，见 `paper_v14/main.tex`） |
| 论文摘要 | 参考 `<摘要对应文档路径>` 的 Abstract | 占坑版本已写好并提交，**应尽可能不修改**；对应 `paper_v14/sections/abstract.tex` |
| 目标会议 | `<目标会议名称>` | ⟨待定⟩ |
| 截稿日期 | `<截稿日期及时间>` | ⟨待定⟩ |
| 当前日期 | `<当前日期>`（开始任务时） | 2026-09-18 |
| 项目/开源实现 | `<项目名称>` | ⟨待定⟩（论文代码入口 `reproduce_v14.py`、研究层 `research/final_v14/`） |
| 资源 1–5 | `<资源N名称/描述/所在目录>` | 见 §3.1 |

### 3.1 项目源码 / 文档 / 示例库

> 原文要求：由于你并不熟悉该项目，应该**频繁地访问**源码库、文档库和示例库来理解设计细节和使用方法；也可以直接调用它们生成示例代码，或在实验中直接使用它们验证想法。
> **注意**：原文此处指的是本机 WSL 路径；本项目实际运行环境为 **macOS（darwin 25.3.0 arm64）**，路径已相应实例化。

| 资源 | 路径 |
|---|---|
| 论文实验代码 | `paper_v14/`（稿件）、`research/final_v14/`（研究层与冻结证据）、`reproduce_v14.py`（复现入口） |
| 引擎源码 | `backend/src/iron_bottom_sound/engine.py`（裁决入口）、`rl/`（强化学习环境）、`frontend/` |
| 项目文档库 | `docs/`（`architecture/`、`rules/`、`rl_reference.md`） |
| 项目示例库 | `tests/`（回归与端到端）、`benchmarks/`、`resources/`（原始与派生数据） |
| 流水线阶段提示词注册表 | `docs/pipeline/STAGE_PROMPTS.md` |
| 本总纲 | `MEGA_PROMPT.md`（本文件） |

**如何展示对核心技术的理解与应用能力**：

1. **方法部分**：详细描述核心技术（历史依赖博弈中的预算化重规划、完美回忆序列形式、认证价值前沿）的设计原则、核心机制和执行模型，并通过示例代码说明用法与优势。
2. **实验部分**：使用该技术实现实验设计，并与基线方法对比，展示在 ⟨指标1⟩、⟨指标2⟩ 等方面的提升。
3. **讨论部分**：分析局限性和未来改进方向，展示对这项技术的深入思考。

---

## 4. 文件夹结构（模板要求）

```text
/<项目名称>-paper
├── MEGA_PROMPT.md          # 本文件，论文写作和实验的总指引，必须严格遵守与复习
├── RESTRICTS.yaml          # 约束清单，一些约束和辅助规则，必须严格遵守与复习
├── code                    # 论文中实验相关的代码（规范放置，写好 readme），必须保证真实性和可复现性
├── data                    # 论文中实验需要输入的数据，必须保证真实性和可复现性
├── docs                    # 论文写作相关的文档
│   ├── <实验构想文档>.md      # 详细的实验设计方案，必须严格按照这个方案来执行实验
│   ├── <文献与问题文档>.md    # 相关工作的分析和审稿人可能提出的问题，必须在论文中做好防御
│   └── <整体构想文档>.md      # 论文的整体构想和大纲，必须按照这个大纲来撰写论文
├── paper
│   ├── <目标会议模板文件夹>   # <目标会议名称> 的 LaTeX 模板，必须使用这个模板来撰写论文
│   │   ├── README.md
│   │   ├── <会议缩写>.bib / .bst / .pdf / .sty / .tex
│   │   ├── fancyhdr.sty
│   │   ├── math_commands.tex
│   │   └── natbib.sty
│   └── mypaper             # 你撰写论文的地方，必须在这里撰写论文
│       ├── figures         # 论文中引用的图表，必须保证真实性和清晰度
│       ├── main.tex        # 论文主文件，必须使用 LaTeX 撰写，并按模板要求组织结构
│       └── sections        # 论文各部分（Introduction、Methodology 等），按 <整体构想文档>.md 的大纲撰写
├── plans                   # 每个阶段开始前的计划文件，必须在该阶段开始前创建
└── results                 # 论文中实验产生的数据/结果（规范化格式，如 JSON、CSV），必须保证真实性和可复现性
```

> 其他没有规定、但你认为有必要的文件夹或文件，可以根据需要创建，但必须保证内容与用途清晰，且不违反上述规定。

### 4.1 本项目实际结构映射（**不另建平行目录树**）

本项目已有既定仓库结构，**不做目录搬迁**；模板角色按下表映射到现有路径：

| 模板角色 | 本项目实际路径 |
|---|---|
| `MEGA_PROMPT.md` | `MEGA_PROMPT.md`（根） |
| `RESTRICTS.yaml` | `RESTRICTS.yaml`（根） |
| `code/` | `research/`（研究代码）、`reproduce_v14.py`（复现入口）、`backend/`、`rl/` |
| `data/` | `data/`（实验输入）、`resources/`（原始与派生规则/舰船/地图数据） |
| `docs/<实验构想文档>.md` | `research/final_v14/DESIGN.json`、`BENCHMARK_PROTOCOL.md`、`MASTER_PLAN.md` |
| `docs/<文献与问题文档>.md` | `research/final_v14/LITERATURE_POSITIONING.md`、`JOURNAL_POSITIONING.md` |
| `docs/<整体构想文档>.md` | `research/final_v14/THEORY.md`、`CLAIM_CHAIN.md` |
| `paper/<目标会议模板>/` | ⟨待定⟩（当前 `paper_v14/main.tex` 使用通用 `article` 类，尚未套用会议模板） |
| `paper/mypaper/` | `paper_v14/`（`main.tex` + `sections/` + `figures/` + `tables/` + `appendices/` + `references.bib`） |
| `plans/` | `plan.md`（批次计划）+ `PROGRESS.md`（流水线阶段台账）+ 本文件 §6 的留痕机制 |
| `results/` | `research/final_v*/`（冻结结果与审计）、`research/results/` |

---

## 5. 论文基本设计

- 有关论文的构想在 `docs/` 目录里的 md 文件中，**必须在开始所有任务前认真阅读它们，保证彻底理解论文思路，并写入**，并在过程中**不断复习**。
- 论文中应尽可能地展示对 ⟨项目名称/核心技术⟩ 的理解和应用能力（方法部分讲设计原则与机制、实验部分做对比、讨论部分谈局限与未来方向）。

---

## 6. 留痕与规划机制

### 6.1 `PROGRESS.md`

- **全程记录路线规划并标记已完成的步骤，注意循环验证。**
- 每个阶段结束后，**必须**在 `PROGRESS.md` 中记录产物摘要（如：生成的论文大纲、实验设计细节、分析结论等），并标记该阶段为"已完成"。
- 由于存在循环机制，`PROGRESS.md` 中的规划**不应是线性的**，而应在规划时就**标记可能的循环点**（如 `REFINE` 或 `PIVOT`），并在实际执行时根据需要跳转回之前的阶段进行调整。
- `PROGRESS.md` 还需记录每次循环的**版本号**（如 v1、v2、v3…），以及每次循环中产物的**变化点**（如：大纲结构调整、实验设计修改、分析结论更新等）。

### 6.2 各阶段计划文件

- 在**每个阶段开始前**，必须在计划目录下创建一个新的 md 文件，详细规划该阶段的任务和目标。
- 本项目计划载体：`plan.md`（批次级）与 `PROGRESS.md`（阶段级）；阶段计划如需独立文件，写入 `research/final_v14/` 对应阶段目录，避免在根目录堆叠。

---

## 7. 实验与文献要求

### 7.1 实验要求

- **真实性**：论文数据必须是亲自编写代码（或调用 `gh` / GitHub Copilot CLI）写出来的，具备 **100% 的数据真实性**。
- **数据充足性**：必须进行**足够量的实验，至少 10–15 轮不同条件**的实验，保证充分性与说服力。在所有检查中，都必须检查数据是否足以支撑结论。
- 必须**严格按照**实验构想文档中的方案执行，保证每个实验条件都得到充分测试，并在结果分析阶段进行合理的对比与解读。

### 7.2 文献要求

- 引用的文献必须**在网上真实查找到**，保证真实性，**不能编造数据或文献**。
- 保证论文年份在 ⟨指定年份⟩ 年之后，**优先引用顶会论文，数量至少 30 篇**。

### 7.3 论文写作要求

- **内容真实性（最重要）**：论文中所有内容细节都符合项目已有的设计和实现，**不能编造不存在的功能或特性**。应通过频繁访问源码库、文档库、示例库来验证理解，并准确描述设计原则、核心原语和执行模型。
- **数据真实性**：论文中所有实验数据必须真实，不能编造数据或结果。
- 必须使用 ⟨目标会议名称⟩ 的 LaTeX 模板撰写论文（模板位于 `paper/<目标会议模板文件夹>/`），按模板要求组织结构和格式，确保符合投稿规范。
- 在 `paper/mypaper/`（本项目为 `paper_v14/`）下撰写，主文件 `main.tex`，各章拆分为 `sections/*.tex`，通过 `\input{sections/introduction.tex}` 组织。
- 合理引用文献调研阶段找到的相关工作，引用格式符合 LaTeX 规范，在 `<会议缩写>.bib`（本项目 `references.bib`）中维护参考文献列表。

### 7.4 论文结构

标准计算机顶会论文结构：

| 部分 | 内容 |
|---|---|
| **Introduction** | 研究背景、问题定义、核心贡献、论文结构 |
| **Related Work** | 分析相关领域工作，突出创新点与差异性 |
| **Methodology** | 详细描述设计原理、核心机制和实现细节 |
| **Experiments** | 实验设计、结果和分析，验证假设与贡献 |
| **Discussion** | 实际应用意义、局限性和未来改进方向 |
| **Conclusion** | 总结工作，展望未来研究方向 |

不同 tex 放在不同文件，保证结构清晰、便于修改维护；参考文献与附录同样开新文件。

### 7.5 页数要求

- 正文部分**最多 ⟨限制页数⟩ 页**：即 Conclusion 结束的部分必须控制在 ⟨限制页数⟩ 页内。应尽量靠近该页数，但**不能超过**。
- **参考文献部分可以无限制添加额外页面**，因此找到的文献越多越好。
- **附录页面不计入正文页数限制**，可用尽可能多的附录页（参考文献之后），但审稿人不需要阅读附录。正文写不下的次要细节可放附录，**核心内容必须放在正文**。
- 可选的**可重现性声明**不计入页面限制，但应不超过 1 页 —— **本项目不写**。
- 可选的**致谢**部分不计入页面限制，但应不超过 1 页 —— **本项目不写**。

### 7.6 配图

- 论文配图部分，应在 tex 中用**注释**留下一段**严格的 prompt**，供后续交给 nano banana 2 绘图。
- **图表类**可以直接调用 Python 绘制，使用 matplotlib、seaborn 等库，保证清晰度与专业性。

---

## 8. 实验阶段：调用一切工具

### 8.1 大模型工具

原文声明在当前环境中配置了如下环境变量（本项目实际值见下，**密钥不得写入仓库**）：

```bash
export OPENAI_API_BASE="<大模型API基础路径>"
export OPENAI_API_KEY="<大模型API_KEY>"
export OPENAI_MODEL_NAME="<默认大模型名称>"   # 可选
export KAGGLE_API_TOKEN="<KAGGLE_TOKEN>"
export TAVILY_API_KEY="<TAVILY_KEY>"
```

- 实验中需要调用大模型工具的地方，都可直接调用该环境变量中配置的模型接口，保证实验的真实性与可复现性。
- 可选模型：⟨模型1⟩（综合最强）、⟨模型2⟩（稍弱版本）、⟨模型3⟩（最便宜最快，适合极简单任务或大量调用省成本）、⟨模型4⟩（可能适合代码生成相关实验）。
- **本项目现状**：`.env.example` 声明 `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL` / `DEEPSEEK_MODEL` / `IBS_DB_PATH`；`.env` 不入库（已在 `.gitignore`）。上表 OPENAI_*/KAGGLE/TAVILY 槽位在本机当前 shell 中**未设置**，使用前需先由用户提供。**不得伪造已配置的模型能力或实验结果。**

### 8.2 文献检索

- 可以用大模型检索，但**最推荐调用真实文献数据库 API**（如 OpenAlex、Semantic Scholar）获取文献资料，保证真实性与相关性。
- 若文献数据库达到上限，可从 arXiv 等开放资源爬取相关论文的标题与摘要，或使用 Google Scholar 检索。

### 8.3 写代码

- 可以调用命令行 Claude Code 工具写代码，或调用 GitHub Copilot CLI（`gh`）写代码；也可以自行生成代码或在本地环境编写，保证真实性与可复现性。

### 8.4 实验环境配置

- 可以安装任何需要的库（numpy、scipy、matplotlib、pandas、sklearn、torch 等），配置任何需要的环境（虚拟环境、docker 等），以保证顺利实验与撰写。
- **环境可逆性**：任何环境配置必须可逆，或在虚拟环境中完成，避免对系统环境造成不可逆影响。建议使用 `venv` 或 `conda` 管理 Python 环境，或使用 Docker 隔离。
- **环境记录**：必须在 `PROGRESS.md` 中记录每次环境配置的细节，包括安装的库（`requirements.txt`）、版本号、配置的环境变量等，以保证可复现性与透明度。
- **Git 版本控制**：代码和论文草稿都应放入 Git 仓库，并在每个阶段结束后提交一次，记录提交信息（如：完成了实验设计、完成了论文大纲等），便于追踪进展和回滚。

---

## 9. 核心纪律与强制附加约束（HARD CONSTRAINTS & ANTI-PATTERNS）

> 在执行上述所有流程时，必须将以下纪律作为**最高优先级**。**一旦触碰红线，必须立即中断当前阶段并自我修复。**

### 9.1 计算与资源守卫（针对阶段 D & E）

- **强制时间估算**：在运行任何主实验循环前，必须先运行 **1 个条件的小规模 Pilot**，在日志中打印 `TIME_ESTIMATE: Xs` 以推算总运行时间。
- **动态缩放规则**：
  - 如果实验条件 **> 100 组**：自动将随机种子（Seeds）次数降至 **3–5 次**（**严禁强跑 20 次**）。
  - 如果可用时间不足：限制每轮优化步数上限（如 **≤5,000 步**）。
- **优雅中断（Graceful Shutdown）**：代码必须包含 `time_guard` 逻辑，定期检查时间，在达到资源预算 **80%** 时强制停止并保存已收集的部分数据。

### 9.2 真实性代码红线（针对阶段 10 & 13）

- **反幻觉禁令**：**严禁**使用 `random.uniform()` 或类似随机数生成器来伪造下降的 Loss 曲线或实验结果。
- **真实数学逻辑**：必须使用 NumPy 矩阵运算实现真实的算法（如手动实现梯度计算或基于真实数据的交叉熵）。
- **真实收敛门控**：必须实现真实的收敛停止准则（如连续 N 次迭代 Objective 变化 < 1e-8）。**严禁**仅仅使用固定的 for 循环而不做收敛检查。
- **数值稳定性自愈（No Band-Aids）**：在 `ITERATIVE_REFINE` 时，如果遇到 NaN/Inf 或 RuntimeWarning，必须**追踪根源**（如：学习率过高、零除错误、未归一化），**严禁**单纯使用 `try-except` 或 `np.nan_to_num()` 来掩盖报错。

### 9.3 顶会级论文构写标准（针对阶段 G）

- 在这一阶段开始前，**必须重新复习 `RESTRICTS.yaml` 中的写作约束**，尤其是字数长度和质量约束，确保完全理解并准备在写作中贯彻执行。
- **Sushi, not Curry（聚焦原则）**：一篇好论文只有 **1–2 个核心创新点**（Novelty），其余部分保持极致的简洁和严谨。**不要堆砌毫无关联的模块。**
- **Figure 1 霸权**：必须在初稿前构思好"图 1"。图 1 必须能**独立传达**这篇论文的最核心贡献，并在 prompt 中为 Nano Banana 2 提供极为详尽的视觉元素描述。
- **强制消融实验（Ablations）**：论文中提到的任何"有效组件"，代码中必须包含且论文中必须报告"移除该组件"后的对比数据。**没有消融实验，直接拒绝进入下一步。**
- **强基线（Strong Baselines）**：基线模型必须经过与你提出的方法**同等精力的超参数调优**。
- **字数防卫**：严守长度底线（**Introduction 需 800–1000 字，Method 需 1000–1500 字**）。如果字数不足，只能通过增加实质性的"研究空白分析"或"技术细节"扩写，**严禁使用车轱辘话凑字数**。

### 9.4 证据与相关性红线审查（针对阶段 18 & 23）

- **一致性核查（Methodology-Evidence Consistency）**：必须将生成的论文 Draft 与 `results.json` 和实验 Log **逐行比对**。
- **红线**：如果论文声称跑了 10 种数据集，而 log 显示只有 2 种；如果论文宣称执行了 T-test，但代码中没有实现，**直接判定为 CRITICAL FABRICATION（重大伪造），强制退回实验阶段**。
- **文献保真**：提取的文献卡片必须保留原版的 `cite_key` 和 DOI。**拒绝对本领域毫无关联的论文**（哪怕它本身是高质量的顶会）。

### 9.5 环境与库兼容性规范（针对阶段 10）

- **沙盒依赖**：优先使用 Python stdlib、numpy、math、statistics。在非必要情况下（即纯算法创新时），**禁止强行引入庞大的深度学习框架**。
- **NumPy 2.x 强制兼容（CRITICAL）**：
  - 废弃 `np.trapz` → 强制使用 `np.trapezoid`
  - 废弃 `np.erfinv` → 强制使用 `scipy.special.erfinv`
  - 废弃 `np.bool`、`np.int`、`np.float` → 强制使用 Python 原生类型 `bool`、`int`、`float`
  - 废弃 `np.math` → 强制使用标准库 `math`

### 9.6 HARD TOPIC CONSTRAINT（硬主题约束块）

原文以 `blocks.topic_constraint` 形式给出的可复用约束块，**原文照录**：

```text
=== HARD TOPIC CONSTRAINT ===

The paper MUST be about: {topic}

PROHIBITED content (unless user explicitly specifies case-study mode):

- Do NOT treat environment setup, dependency installation, or infrastructure failures as a research contribution.
- Do NOT present debugging logs, system errors, or configuration issues as experimental findings.
- Do NOT drift to tangential topics not directly related to the stated topic.
- Every section MUST connect back to the core research question.
- The Abstract and Introduction MUST clearly state the research problem derived from: {topic}
- The Method section MUST describe a technical approach, not a workflow.
- The Results section MUST report quantitative outcomes of experiments, not environment status.

=== END CONSTRAINT ===
```

---

## 10. 阶段提示词注册表（原文照录）

原粘贴文本除流程描述外，还给出了**完整的阶段 LLM 提示词**（含 `system` / `user`、`max_tokens`、`json_mode` 等字段）。为避免本文件过长，原文 25 个阶段提示词 + 4 个 `sub_prompts` 已**逐字归档**至：

- **`docs/pipeline/STAGE_PROMPTS.md`** — 阶段提示词注册表（原文照录，未改写）

阶段索引：`topic_init`、`problem_decompose`、`search_strategy`、`literature_collect`、`literature_screen`、`knowledge_extract`、`synthesis`、`hypothesis_gen`、`experiment_design`、`code_generation`、`resource_planning`、`export_publish`、`knowledge_archive`、`paper_outline`、`paper_draft`、`paper_revision`、`peer_review`、`quality_gate`、`research_decision`、`result_analysis`；
子提示词：`code_repair`、`iterative_improve`、`iterative_repair`。

另有 3 个**关键门限与质量条款**内嵌于提示词中，执行时必须遵守：

| 条款 | 来源 | 内容 |
|---|---|---|
| 论文长度门限 | `paper_draft` / `paper_revision` / `peer_review` / `quality_gate` | 正文目标 **5000–6500 词**（约 9 页会议论文）；分节下限：Abstract 150–250、Introduction 800–1000、Related Work 600–800、Method 1000–1500、Experiments 800–1200、Results 600–800、Discussion 400–600、Limitations 200–300、Conclusion 200–300；**总词数 < 4000 视为严重不足** |
| 试验次数一致性 | `peer_review` | 论文声称的试验次数必须与实际运行次数一致；声称"100 次独立试验"而实际只跑 1 次 = **CRITICAL fabrication，必须修正** |
| 质量门阈值 | `quality_gate` / `literature_screen` | 按 `{quality_threshold}` 判定，verdict 与 required_actions 必须落盘 |

---

## 11. 本文件的使用方式

1. **每次会话开始**：先读 `agent.md` 与 `todo.md`，再复习本文件 §2（阶段与循环）与 `RESTRICTS.yaml`。
2. **每个阶段开始前**：在 `PROGRESS.md` 登记该阶段计划与可能的循环点。
3. **每个阶段结束后**：在 `PROGRESS.md` 记录产物摘要、版本号与变化点，并追加 `havedone.md`。
4. **每次循环（REFINE/PIVOT）**：登记版本号递增与受影响产物清单。
5. **投稿前**：对照 §9.3–9.6 与 §10 的门限做一次完整自查，任一红线未过则不得标记"可投稿"。
