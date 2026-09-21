# PROGRESS.md — 论文流水线阶段台账

> **性质**：本文件是 25 阶段论文流水线的**留痕与规划载体**（`MEGA_PROMPT.md` §6.1）。
> **规则**：每个阶段结束必须在此登记产物摘要、版本号与变化点；规划**不是线性的**，必须在规划阶段就标出可能的循环点（REFINE / PIVOT）。
> **配套**：`agent.md`（治理宪法）、`MEGA_PROMPT.md`（总纲）、`RESTRICTS.yaml`（约束）、`plan.md`（批次计划）、`havedone.md`（完成记录）、`docs/pipeline/STAGE_PROMPTS.md`（阶段提示词）。

---

## 0. 状态图例

| 标记 | 含义 |
|---|---|
| ✅ | 已完成，且有可核查产物 |
| 🔄 | 进行中 |
| ⏸ | 阻塞（等待用户槽位 / 门控审批 / 外部资源） |
| ❌ | 失败或已按失败分支停止（**保留记录，不得改写为通过**） |
| ⬜ | 未开始 |
| ⟨待核⟩ | 有历史产物但未按本流水线重新核验，**不得直接标记 ✅** |

## 0.1 循环登记表

| 版本 | 触发阶段 | 循环类型 | 回到阶段 | 受影响产物 | 登记日期 |
|---|---|---|---|---|---|
| — | — | — | — | — | — |

> 每次 REFINE / PIVOT 必须在此追加一行。原文要求：**每个 stage 结束时重新检查，并至少循环进行两遍**。

---

## 1. 流水线建立（2026-09-18）

**本次会话产物**：

| 产物 | 路径 | 状态 |
|---|---|---|
| 治理宪法 | `agent.md`（重写扩展） | ✅ |
| 流水线总纲（提示词文档化） | `MEGA_PROMPT.md` | ✅ |
| 阶段提示词注册表（原文照录） | `docs/pipeline/STAGE_PROMPTS.md` | ✅ |
| 约束清单 | `RESTRICTS.yaml` | ✅ |
| 阶段台账 | `PROGRESS.md`（本文件） | ✅ |
| 活动任务清单 | `todo.md` | ✅ |
| 长期记忆库 | `memory/MEMORY.md` | ✅ |
| nature-skills 技能安装 | `~/.zcode/skills/nature-*`（源 commit `2375e0abdf42158ef149256f2c64b1f759a0d274`） | ✅ |

**来源留痕**：原始粘贴件 `~/.zcode/tmp/paste-attachments/2026-09-18/pasted-text-20260918-222626-3fd0cf9f.txt`。

**核验证据**：

| 检查项 | 结果 |
|---|---|
| `RESTRICTS.yaml` YAML 语法 | 通过（项目 `.venv` python3.14 `yaml.safe_load`，14 个顶层键） |
| `agent.md` 原条款保留 | 10/10 KEPT（对照 `git show HEAD:agent.md` 逐条比对） |
| nature-skills `SKILL.md` frontmatter | 20/20 合法 |
| nature-skills 跨技能引用解析 | 5/5 命中（`core/reader-workflow.md` 等） |
| 新建/改写文件 | 14 个 + 工作区入口 `seawar/AGENTS.md`，全部非空 |
| pytest / 实验 / 论文编译 | **未运行**（本批次为治理与工具批次，不产生科学结论） |

**已记录的环境事实（影响后续委派）**：本机 `claude` CLI 指向 DeepSeek 端点（非 Claude/GLM）；`codex`/`gemini`/`ollama` 未安装；GLM 端点与 key 未配置；ZCode 内置 Agent 工具无 per-call 模型选择参数。**因此"用 glm4.7/glm4.6v 跑子 agent"当前不具备执行条件**，详见 `memory/agent-delegation-environment.md`。

**环境记录**（`RESTRICTS.yaml` §6 `environment_recording` 要求）：

| 项 | 值 |
|---|---|
| 平台 | macOS（darwin 25.3.0 arm64） |
| 项目 Python 环境 | `.venv`（`python3.14`） |
| 本会话新增全局安装 | `~/ai-skills/nature-skills`（40 个 md 级技能资产，20 个可触发技能） |
| 全局技能目录变更 | `~/.zcode/skills/nature-*`（20 个目录，约 38 MB） |
| 系统包管理器变更 | 无（未使用 `--break-system-packages`） |
| 环境变量变更 | 无（未写入任何密钥） |

---

## 1.5 M0 多主线验证（独立于论文流水线，分支 research/m0-validation）

2026-09-18 完成 P0 审计 + P1 Exact Lab + A0/B0/C0/D0 cheap kill tests，止步于 checkpoint（M0 计划纪律：PI 审查前不进 discovery）。结论：**A=WEAK，B=PASS_TO_DISCOVERY（条件性，IBS 反例未做），C=FAIL（borderline F12 待 PI 裁定），D=FAIL**。证据入口 `research/m0/CHEAP_KILL_REPORT.md`；IBS 对局预算 2238/20000；生产模块零改动。详见 `havedone.md` 2026-09-18 M0 条目与 `memory/m0-cheap-kill-findings.md`。

## 1.6 M1 G1（分支 research/m1-decision-state）

2026-09-19 完成 G1（IBS 自然 commitment 决策混叠验证）：**G1_IBS_NATURALITY = FAIL → FINAL_M1_STATUS = B_TOY_ONLY**，按纪律停在 checkpoint（未进 G2/神经网络/DSRL/PPO）。现象真实可审计（10 强案例，max normalized regret 0.84 damage / 0.40 outcome，CI-passing）但自然密度 6-11 nontrivial pairs << 25；主值下对照不更低。证据入口 `research/m1/g1/G1_EXECUTIVE_SUMMARY.md`；包 `research/m1/M1_G1_CHECKPOINT.zip`。预算 ~35k/50k rollouts。

## 1.7 M1.5 新主线双轨 cheap-kill（分支 research/m1_5）

2026-09-19 完成 E1/E2 双轨验证：**E1 FAIL（E1_FAIL_PREDICTABILITY：可见特征 AUROC≤0.47，尽管 rho 稀疏且重大）**；**E2 FAIL（E2_FAIL_HEURISTIC_ONLY + E2_FAIL_CAUSALITY：48.5% 排名变化但续局 +0.02/60% 平局，true≈shuffled）**。**BEST_SUPPORTED_TRACK = NONE**。证据入口 `research/m1_5/00_EXECUTIVE_SUMMARY.md`；包 sha256 `23113572945faefc…`。预算 ~760/15000 rollouts。

## 1.8 M2-0 组织智能验证（分支 research/m2-0-organizational-intelligence）

2026-09-20 完成：基础设施全 PASS（模式审计/Exact Lab 双求解器/D0 宏执行器）；**A_FAIL_ORACLE**（flat 71% 并列最优、无压缩 gap）、**B_ORACLE_ONLY**（B0 65% 中断率、B1 max 0.767 但设计规则场景反向）、**C_MODULE**（场景主导）。**RESET_REQUIRED**：无 MAINLINE_READY；隐藏承诺/组织智能两轮选题均被 oracle-first cheap-kill 系统排除。证据入口 `research/m2_0/00_EXECUTIVE_SUMMARY.md`；包 sha256 `d539ab28…`。

## 1.9 M2.1 平台杠杆审计（分支 research/m2-1-platform-audit，PARTIAL）

2026-09-20：P0 PASS（0 BUG/UNKNOWN）；P1 **MATCHED_INITIAL_SEEDS_ONLY**（同 seed ≠ CRN，分支后 draw 数必错位）；E0 炮击层完成——**低杠杆**（无状态 ≥0.05，分配级差异≈0）；movement/torpedo/realistic 层未测完（PI 指示停止，80/93），且 movement 候选集被专家指出缺联合战术计划（F8）。平台判定 INCOMPLETE，包 sha256 `4977395c…`。PI 三选一：扩候选重测 movement / 上 E2-E3 测洗平假说 / 接受现状降级 IBS。

## 1.10 M2.1-R 测量修复 + Gold Gate（分支 research/m2-1-platform-audit）

2026-09-20：PI 判定原 E0 无效（gunnery 分支对手批次未提交）。四项修复完成并验证（U1 公式+单测、derived-seed replicates、双方 submit+seal、P0/T0/T1/T2/Terminal、显式 baseline），另修 F9/F10 两个自找 bug。5 个 Gold Cases 全部建成并评估：**GOLD_EVALUATOR_GATE = FAIL**（0/5 ≥0.05；最大 0.033；G1 在 E3 下反号）。按指令停止，未跑 mass census。包 sha256 `d3c77d05…`。开放问题：SCRIPTED_FLATTENING vs 候选编译器太粗——修复后的 harness 已可区分。

## 1.11 M2.1-R2 机制金分解（分支 research/m2-1-platform-audit）

2026-09-21 Stage A 完成：**MECHANISTIC_GOLD_GATE = FAIL（3/5）**——规则引擎对几何陡峭定价（MG1 +92.9% broadside / MG2 1.68× cross-T / MG3 2.72× 射程），MG4 案例构建失败、MG5 战术假设在平台尺度不成立。失败定位成功：问题在编译器与价值兑现层，不在规则引擎。按指令停止（Stage B/C 未进入）。包 sha256 `d2556f1b…`。

## 1.12 M2.1-R2.1 机制修复（分支 research/m2-1-platform-audit）

2026-09-21：修复 PI 指出的 F21（重复计炮）并自发现 F22（时空段错位）/F23（瞄准受限）。**MG4 由 FAIL 翻转为 PASS**（真实长程鱼雷走廊剥夺 28/29 条 T+1 路线，时空预测与引擎接触事件 29/29 一致）；MG2 转 FAIL（纵向占比 0.44<0.50）、MG5 确认 FAIL。门 **3/5 FAIL**（阈值未变）。Stage B/C 未进入。包 sha256 `2874b578…`。

## 1.13 M2.2 战术编译器保真审计（分支 research/m2-2-compiler-fidelity）

2026-09-21：对三个已确认机制（MG1 舷射 / MG3 距离控制 / MG4 鱼雷走廊）审计"当前 AI 能否把机制编译成合法联合行动"。预注册 `research/m2_2/PRE_REGISTRATION_M22.md`（命名纪律 / 机制值 / 保真度公式 / B0 门 / 搜索预算 / B1 门）先于测量冻结。

**GOLD_COMPILER_GAP = FAIL（0/3；按冻结度量仅 1/3 可计算）**。三个引擎真实结论：

1. **MG1 同一个冻结公式在两个尺度上给出相反答案**：舰队级 `M_broad` 下手工舷射 gold **−12.17**，比随机合法计划均值 **−6.32** 还差（gap −5.84，分母非正 → 按预注册条款不可计算）；限制在该案例自身的舰对尺度上，同公式给出 gold **+1.89** > 随机 **+1.44**，保真度翻为 GAP（SEARCH **+0.876** / CURRENT_POLICY **−0.178**）。展开舷射在舰对交换上赢、在舰队交换上输——M2.1-R"暴露对称"效应被隔离到单舰并精确复现。
2. **现有意图编译器把舰转向反了（MG1）**：被告知 intent `BROADSIDE` 时，仓库自带 `mg_cases.intent_plans` 给焦点舰发 **`1S1P`**——与反向臂**逐字符相同**，post_rel 5 / 1 炮位（gold 为 post_rel 1 / 3 炮位），舰对保真度 **−2.53**。缺陷表达式 `((b-1+1)%6)+1`，一行可复现。
3. **MG3 注册度量落在可交战包线之外（M22-F4）**：冻结 PASS 比较 15/17 格处期望命中 2.56/0.94（精确复现）。该状态盟军能见度 **13 格**、radar 可选规则 **OFF**，两臂 `_can_see` 均为 False——引擎会 `gunnery_rejected`。引擎真实计量下两臂均为 **0.000**，gold gap = 0。注册度量只查 `_mount_can_bear`、无 `_can_see` 门；MG3 在 R2.1 冻结故从未获得 MG2/MG4 拿到过的能见度修复。**历史判决逐字保留**，M2.2 只加诊断。
4. **鱼雷走廊是全状态现象（MG4）**：gold 精确复现（RouteReduction **0.966**、时空接触 12/12 与引擎一致、预测段与 R2.1 记录相同）。可部署的公开信息搜索 **0.107**、当前 AI **0.000**（该状态一条鱼雷令都不发）。公开目标是**并列主导**的：其 argmax 并列集内 RR 跨 0.00–0.97，而真正最优配置在公开目标上得分**最低**（overlap 1 / 最大 5）→ `PUBLIC_INFORMATION_GAP = CONFIRMED`。

失败留档：M22-F1（混合侧秩统计伪影）F2（搜索重复计炮）F3（`movement_candidates` 是合法计划空间的子集且 speed 须取 `movement_cost`）F4（MG3 度量缺能见度门）F5（MG4 gold 即全状态 argmax，F=1 平凡）。B1 自然普查**未运行**（预注册以 B0 PASS 为门）。预算：~450 次引擎评估；0 付费 LLM；生产引擎零改动；未训练模型。包 `M2_2_TACTICAL_COMPILER_FIDELITY_BUNDLE.zip` sha256 `b6531b37…`。

## 2. 阶段台账

> **重要**：阶段 1–11 在 2026-09-13 之前已有历史产物（v12/v13/v14 研究线），但这些产物是在本流水线成立**之前**产生的，其"是否符合本流水线的阶段定义与门控要求"**尚未按本流水线重新核验**，因此统一标记 ⟨待核⟩，不得直接升为 ✅。

### 阶段组 A：研究定义

| 阶段 | 状态 | 产物 | 备注 |
|---|---|---|---|
| 1 `TOPIC_INIT` | ⟨待核⟩ | `research/final_v14/MASTER_PLAN.md` | 历史 SMART 目标未按 `topic_init` 模板生成 |
| 2 `PROBLEM_DECOMPOSE` | ⟨待核⟩ | `research/final_v14/DESIGN.json` | 子问题树未按 `problem_decompose` 模板登记 |
| 3 `SEARCH_STRATEGY` | ⬜ | — | 历史检索策略未固化为 `search_plan_yaml` |
| 4 `LITERATURE_COLLECT` | ⏸ | `research/final_v14/LITERATURE_POSITIONING.md` | 需真实 API（OpenAlex/Semantic Scholar/arXiv）；**≥30 篇**要求待核 |
| 5 `LITERATURE_SCREEN` **[门控]** | ⏸ | — | 门控未过；需按 `literature_screen` 重新筛选并保留 `cite_key`/DOI |
| 6 `KNOWLEDGE_EXTRACT` | ⬜ | — | 需产出 `cards` JSON |
| 7 `SYNTHESIS` | ⬜ | — | 需产出聚类 + 研究空白 |
| 8 `HYPOTHESIS_GEN` | ⟨待核⟩ | `research/final_v14/CLAIM_CHAIN.md`、`THEORY.md` | 可证伪假设的 failure condition 未按模板登记 |
| 8.5 `THEORETICAL_BOUNDS` | ⟨待核⟩ | `research/final_v14/THEORY.md`、`INTERVAL_BOUND_PROTOCOL.md` | 有理论推导产物；原文未给模板 |

**可能的循环点**：阶段 5 门控若拒绝 → 回阶段 3/4 重做检索；阶段 8 辩论若无法给出可证伪假设 → 回阶段 7。

### 阶段组 D：实验设计

| 阶段 | 状态 | 产物 | 备注 |
|---|---|---|---|
| 9 `EXPERIMENT_DESIGN` **[门控]** | ⏸ | `research/final_v14/DESIGN.json`、`BENCHMARK_PROTOCOL.md`、`PILOT_FREEZE.json`、`RUN_FREEZE.json` | 设计已冻结；门控审批与 `compute_budget`/`ablations` 键完整性待核 |
| 10 `CODE_GENERATION` | ⟨待核⟩ | `research/final_v14/`、`reproduce_v14.py` | 需按 §3 真实性红线逐条复核（收敛门控、禁 `np.trapz`、禁 `try-except` 掩盖 NaN） |
| 11 `RESOURCE_PLANNING` | ⬜ | — | 缺 `schedule JSON`（`tasks`/`total_gpu_budget`） |

**可能的循环点**：阶段 9 门控若拒绝 → 回阶段 8 调整假设；阶段 10 生成代码不满足收敛门控 → 回阶段 9。

### 阶段组 E：实验执行

| 阶段 | 状态 | 产物 | 备注 |
|---|---|---|---|
| 12 `EXPERIMENT_RUN` | 🔄 | `research/final_v14/development.log`、`DISPATCH_PROGRESS.json`、`PLAN_EXECUTION_LEDGER.md` | 串行开发实验；**未完成** |
| 13 `ITERATIVE_REFINE` | 🔄 | `DEVELOPMENT_AMENDMENT_01.md`、`REGRESSION_*.log` | 已有一次修订归档；自修复需按 §3 红线（追根因，不得 `np.nan_to_num` 掩盖） |

**强制项检查**：`TIME_ESTIMATE:` pilot 记录、`time_guard` 80% 预算中断 → ⟨待核⟩。

### 阶段组 F：分析与决策

| 阶段 | 状态 | 产物 | 备注 |
|---|---|---|---|
| 14 `RESULT_ANALYSIS` | ⬜ | — | 需**独立上下文**多 Agent 客观分析（`result_analysis`）；现有 `analysis/` 未按模板产出 |
| 15 `RESEARCH_DECISION` | ⬜ | — | 需产出 `PROCEED` / `REFINE` / `PIVOT` + 理由 + 证据 |

**可能的循环点**：阶段 15 `REFINE` → 阶段 13；`PIVOT` → 阶段 8（并自动版本化）。

### 阶段组 G：论文撰写

| 阶段 | 状态 | 产物 | 备注 |
|---|---|---|---|
| 16 `PAPER_OUTLINE` | ⬜ | — | 需按 `paper_outline` 产出带 evidence links 的大纲 |
| 17 `PAPER_DRAFT` | 🔄 | `paper_v14/main.tex` + `sections/*.tex`、`main.pdf` | 已有英文稿；**是否满足 5000–6500 词与分节下限待核** |
| 18 `PEER_REVIEW` | ⬜ | `paper_v14/qa/` | 需按方法论-证据一致性逐行比对 draft 与 log/results |
| 19 `PAPER_REVISION` | ⬜ | — | 修订**只能加长不得缩短** |

### 阶段组 H：稿件

| 阶段 | 状态 | 产物 | 备注 |
|---|---|---|---|
| 20 `QUALITY_GATE` **[门控]** | ⬜ | — | 需 `score_1_to_10` + `verdict` + `required_actions` |
| 21 `KNOWLEDGE_ARCHIVE` | ⬜ | — | 需复现性回顾归档 |
| 22 `EXPORT_PUBLISH` | ⏸ | — | 需模板；当前 `paper_v14/main.tex` 用通用 `article` 类，**尚未套用会议模板** |
| 23 `CITATION_VERIFY` | ⬜ | `paper_v14/references.bib` | 需真实性 + 相关性双查；**≥30 篇**、年份下限待用户给槽位 |

### 阶段组 I：审核迭代

| 阶段 | 状态 | 产物 | 备注 |
|---|---|---|---|
| 24 `3RD_PARTY_REVIEW` | ⬜ | — | 必须用**独立上下文**模型 + 最严苛外部专家提示词 |
| 25 `REBUTTAL` | ⬜ | — | 可触发 `REFINE(→13)` 或 `PIVOT(→16)`，自动版本化 |

---

## 3. 阻塞项（等待用户输入，禁止自行编造）

| 编号 | 阻塞内容 | 影响阶段 | 需要的槽位 |
|---|---|---|---|
| B-1 | 目标会议未定 | 9、16–22、23 | `<目标会议名称>` |
| B-2 | 截稿日期未定 | 11（资源规划）、全局排期 | `<截稿日期及时间>` |
| B-3 | 正文页数上限未定 | 16、17、19、20 | `<限制页数>` |
| B-4 | 会议 LaTeX 模板未提供 | 22 `EXPORT_PUBLISH` | `paper/<目标会议模板文件夹>/` |
| B-5 | 文献年份下限未定 | 4、5、23 | `<指定年份>` |
| B-6 | 文献检索 API / Kaggle / Tavily 凭据未配置 | 4、12 | `OPENAI_API_BASE/KEY`、`KAGGLE_API_TOKEN`、`TAVILY_API_KEY` |
| B-7 | 可选模型清单未指定 | 10、13、14 | `<模型1..4>` |
| B-8 | 摘要在原文中要求"尽可能不修改" | 17、19 | 需确认占坑版摘要文件与冻结哈希 |

---

## 4. 下一步（按流水线强制顺序）

1. **解阻塞**：向用户索取 §3 的 B-1、B-2、B-3、B-4、B-5（B-6/B-7 可稍后）。
2. **补核验**：对 §2 中标记 ⟨待核⟩ 的阶段按本流水线模板重新核验，核验通过才升 ✅，不通过则登记为 REFINE 起点。
3. **推进阶段 14**（`RESULT_ANALYSIS`）：用独立上下文多 Agent 分析 `research/final_v14/` 的实跑数据，产出含真实数值的 markdown 报告。
4. **推进阶段 15 决策**：基于阶段 14 报告给出 `PROCEED` / `REFINE` / `PIVOT` 并登记 §0.1 循环表。
5. **阶段 17 长度核查**：统计现行 `paper_v14/sections/*.tex` 的实际词数，对照 `RESTRICTS.yaml` §4 的分节下限，缺则补实质内容。

> **纪律提醒**：在阶段 9 门控与阶段 5 门控未明确通过前，不得标记"可投稿"；任何未触发的扩展项（如失败的 Grid 扩展）必须保持失败标记，**不得报为通过**。
