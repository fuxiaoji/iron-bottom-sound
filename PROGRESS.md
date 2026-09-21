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

失败留档：M22-F1（混合侧秩统计伪影）F2（搜索重复计炮）F3（`movement_candidates` 是合法计划空间的子集且 speed 须取 `movement_cost`）F4（MG3 度量缺能见度门）F5（MG4 gold 即全状态 argmax，F=1 平凡）F6（图 3 曾把 LEAD_TURN_ALLOWED 的结论挂到 CORRIDOR_BLOB 上）。B1 自然普查**未运行**（预注册以 B0 PASS 为门）。预算：~450 次引擎评估；0 付费 LLM；生产引擎零改动；未训练模型。包 `M2_2_TACTICAL_COMPILER_FIDELITY_BUNDLE.zip` sha256 `a2ccf6d8…`。

## 1.14 M2.2-R / B1E 探索性自然机会普查（分支 research/m2-2-compiler-fidelity）

2026-09-21：按 PI 四项裁决执行。预注册 `research/m2_2r/PRE_REGISTRATION_B1E.md`（EXPLORATORY / NOT USED TO OVERRIDE PRIOR GATES）先于测量冻结；历史 gate 原样保留（M2.1-R2.1 = FAIL_3_OF_5；M2.2 B0 = FAIL/BLOCKED_BY_METRIC_VALIDITY）。

- **A 溯源 = `RESEARCH_COMPILER_BUG`**：`intent_plans` 只在 research 脚本；production `TacticalCommander` 不做意图→航向编译（用引擎 `ship_gun_pressure` 扫描每个可达 (格,末航向)），缺陷类无生产路径。
- **B 修复**：冻结的 `mg_cases.py` **一字未改**（保证 `CURRENT_INTENT_PRE_FIX` 可复现），修复落在新模块 `REPAIRED_INTENT_BASELINE`（按本舰炮座弧表选航向，非价值函数、非搜索）。单测 (i)/(iii)/(iv) 通过；(ii)「恢复 gold 炮座数」为我自己过强的断言，**降级为报告值并披露**（2/3，pre-fix 1）——原因是 F18（同步移动使战前方位失效），不是放宽判据。
- **C MG1 双尺度**：pre-fix 意图在**两个尺度上都比不作为更差**（ΔL0 −0.056、炮座 2→1；ΔL1 −11.361）；修复后 **+0.667 L0（41% 相对）但 −5.833 L1** → `MECHANISM_SUCCESS_BUT_NEGATIVE_EXTERNALITY`；**只有联合搜索在两尺度都为正**（+0.472 L0 / +7.417 L1）。
- **D MG3-E = PASS**：EM-01 s1 t10，IOWA→KURAMA，两臂都可见且 8 门主炮可用，9 格 4.139 vs 12 格 2.528 命中（绝对差 1.611、相对 38.9%）；扫描 162 个状态并记录全部拒绝原因。旧 MG3 = `HISTORICAL_PROXY_PASS / EXECUTABLE_GOLD_INVALID`，不再计入可执行机制。
- **E MG4-P**：`PUBLIC_INFORMATION_GAP` 一词全阶段未使用。首次 per-route payoff 用二值 D 导致 `R_shared` 恒为 1（度量为动作空间覆盖率而非信念冲突，会造出假阳性；M22R-F2）→ 修为 graded D 并两种并列留档。**material regret 出现在 4/15 状态、跨 2 场景**（S-01 50%、EM-01 33%），冻结规则判 `TORPEDO_PARTIAL_OBSERVABILITY`；**但效应量单场景主导**（S-01 天花板 0.97/0.30，EM-01 仅 0.07/0.17），已作为结果的一部分披露。公开代理对照在两个方向上移动（0.200 vs 0.500 / 0.167 vs 0.000）→ **假设 B（观测缺口）未被分离**。
- **G 普查**：movement 52 状态 / 104 状态侧（S-01 32、S-03 32、EM-01 40），beam 按序号奇偶取单侧（n=49）；配额缺口 S-01 −4、S-03 −4，**`damaged` 层为空**（如实报告，不回填）。判定 **MOVEMENT = MIXED**——卡在冻结的「中位相对增益 ≥0.30」条款（实测 0.000），而机会率（0.375/0.235）与外部性结构都指向另一侧；且 `LOCAL_ONLY_MECHANISM` 明确**不成立**（beam 可用战术率 0.694、中位外部性 +0.861）。torpedo 15 状态六臂：**当前 AI 平均 RouteReduction = 0.000**（40% 状态开火却零约束），两个公开臂 ≈0.010，full-state 天花板 0.020–0.316。
- **最终判**：`B1E_VERDICT = TORPEDO_PARTIAL_OBSERVABILITY`（冻结首命中序），movement 分支 = MIXED。
- **失败留档 M22R-F1..F5**：判定条款引用不存在的第二机制行 / 二值 payoff 退化 / 桶标签丢弃中局状态 / 地图边缘 `neighbor()` 抛异常 / 空断言换真不变量。两次崩溃各损失约 30 分钟算力后改为 JSONL 逐条落盘。
- **预算**：约 5000 次引擎评估；0 付费 LLM；生产引擎零改动；未进入 RL/GNN/论文方法。包 `M2_2R_B1E_NATURAL_OPPORTUNITY_BUNDLE.zip` sha256 `302c9bf1…`（43 文件）。按指令停止。

## 1.15 M2.3 主线分歧裁决（分支 research/m2-2-compiler-fidelity）

2026-09-21：对两个候选做 cheap-kill。预注册 `research/m2_3/PRE_REGISTRATION_M23.md` 先于测量冻结；历史 gate 与旧普查原样保留（另加 M22R-F6 勘误：B1E 的 damaged 谓词是死代码 `hull_max`→`max_hull`）。

**JTC = FAIL**：`JTC_MULTI_INTENT = FAIL`（仅 I1 在两个场景达 ≥20%）；`JTC_JOINT_COORDINATION_EFFECT = FAIL`——在**同一** 35 个机会状态上 JOINT **1.048** < PER_SHIP_GREEDY **1.428** < RANDOM **1.831**；机制机会率上 greedy 在 8 个场景×意图格中有 5 个 ≥ joint。**关键混淆已写进判决本身（M23-F3）**：我的 cheap surrogate 逐舰可加，所以 greedy 是它的**精确最优解**，该臂结构上无法检验「协调」；真实交互项（集火加成/分火惩罚）不在 surrogate 里。故 FAIL 按冻结规则如实输出，并附「需以含交互项的 surrogate 重测」的建议，而不是就此判 JTC 死刑。

**BARD = FAIL**：14 个信息集（同公开历史、观测哈希与合法动作集在代码中强制一致并逐集记录）。真实隐藏集上冲突成立（11/14 有 best-action crossover、5/14 无 ε-good 共享动作），但 **size/diversity 匹配对照后 0.357 → 0.214**，且仅 S-01 一个场景存留 → `MATCHED_CONTROL = FAIL`；`PUBLIC_RECOVERY = FAIL`（最优公开规划器只恢复天花板的 0.611/0.226/0.086，当前 AI 全场景 0.000）。既非 ARTIFACT（池化 21.4% 过线）也非 INFORMATION_LIMIT_ONLY（≥2 场景未满足）。**结论：此前的 TORPEDO_PARTIAL_OBSERVABILITY 信号主要是假设集构造效应。**

**MAINLINE_CANDIDATE = NONE**（两条线都未过各自的冻结门槛；按 PI 规则不强行选）。

自查并修复的三处自身缺陷：M23-F1 匹配对照锚点错位（使 12/14 集恰为 0.000，本会误判 ARTIFACT；两次运行都留档）、M23-F2 跨不同状态集比较（违反 §4.2）、M23-F4 规划器计分口径不一致（出现 0.336 > 天花板 0.124 的不可比）。M23-F5 记录 BARD 落地前必须的三处管线修复（含 JTC 的退化基线准入规则）。预算约 3000 次引擎评估；0 付费 LLM；生产引擎零改动；未进入 RL/GNN/论文写作。包 `M2_3_MAINLINE_DISAMBIGUATION_BUNDLE.zip` sha256 `85d3e41f…`。按指令停止。

## 1.16 M2.4 JTC 交互感知最后机会门（分支 research/m2-2-compiler-fidelity）

2026-09-21：JTC 最后一次机制重测（预注册 `research/m2_4/PRE_REGISTRATION_M24.md` 先于测量）。历史 gate 与 M2.3 JTC=FAIL/BARD=FAIL 原样保留。

**Gate I 交互存在性 = PRESENT**：10 个预注册 pilot、150 个舰对，全部 engine-exact。median |φ|=0.000、**p90 0.556**、**max 4.139**、**28% 舰对 ≥0.05** —— 交互稀疏但真实；**精确可加模型**（用 engine-exact 的 q_i 求和）对精确联合值的预测一致性仅 **0.037**，即加性描述确实不足（这正是 M2.3 诊断的方向）。

**Gate II 等预算协调效应 = FAIL（六条判据全部不满足）**：主集 n=19（**尝试 53，34 个被静默丢弃**），**6 胜 / 9 平 / 4 负**、win rate **0.316**、中位增益 **+0.000**、bootstrap CI [+0.000,+0.111]；逐场景中位 S-01 0.000 / S-03 **+0.222** / EM-01 **−4.194**；**未胜过 sequential 精确坐标上升**（中位 0.000，CI [−0.722, 0.000]）；与等预算随机相比中位 −0.083。补充集 n=11，5/4/2，中位 0.000。

**结论：交互结构真实存在，但在该预算下把交互变成系统性队级收益的尝试失败**——这一轮不是 surrogate 伪影（臂有 engine-exact 的交互项、同一候选集、同一精确评估预算），因此按 PI 规则 `JTC_FINAL_STATUS = PERMANENTLY_KILL`，不再有第三次修 surrogate。`BARD_FINAL_STATUS = ARCHIVED`，`IBS_NEXT_ROLE = APPLICATION_BENCHMARK_ONLY`。

本轮自查并记录的自身缺陷：**M24-F1** 主集实际用了 M2.3 census 的全部唯一状态侧（53）而非冻结的 35 组合（超集，非挑拣，仍如实记录）；**M24-F2** 精确评估失败时 `RuntimeError` 被吞、状态静默丢弃（53→19、~30→11），正是红线 R3 警告的形态，已在每个面板表标出真实 n；**M24-F3** 主集意图标签退化（全为 I1，故 `P(Δ>0|RANGE/RAKING)` 不可算且未报）；**M24-F4** Gate I 通过后重读代码发现交互臂两处真 bug（φ 的 u_j 基点项错、模型只匹配首个探针），修复后 Gate II 从零重跑，Gate I 数字不受影响。0 碰撞事件、全部批次 `validate_orders` 通过。预算 Gate II 1973s；0 付费 LLM；生产引擎零改动；未进入 RL/GNN/Transformer/论文。包 `M2_4_JTC_INTERACTION_LAST_GATE.zip` sha256 `5781e81a…`（35 文件）。按指令停止。

## 1.17 整合交付包（M2.2→M2.4 弧线，供导师阅读）

2026-09-21：应要求产出**整合包**（不是四个阶段包的简单堆叠）：`research/M2_2_M2_4_ARC_INTEGRATED/` + 同名 zip（sha256 前 16 位 `0394d23613bbe9ee`，57 文件 1.9 MB）。内容 = 中文导读（研究链条 / 关键数字 / 冻结状态 / 仍成立的科研资产 / **自查缺陷表** / 未做与不主张 / 阅读顺序）+ 一页状态总表 + 17 份阶段文档（四阶段执行摘要、记分卡、预注册、failures）+ 17 张图 + 11 个顶层证据 JSON + 4 个阶段包 + 逐文件 sha256 的 MANIFEST.csv。副本已放 `~/Downloads/`。**注意**：包内明确写「本轮价值不在找到主线，而在用冻结协议排除两条候选并建立可复现测量基础设施」，并列出 9 处自查缺陷（含 M24-F2 静默丢状态），不主张论文级结论。

## 1.18 Phase A v3.0 主航线选择（新研究轴：BenchMARL/VMAS，分支 research/m2-2-compiler-fidelity）

2026-09-21：执行 A0（环境/策略/仪器锁定）并交付可审计 bundle。**未输出 SELECTED_MAINLINE**（PI 决定）。

- **A0.1 环境锁**：BenchMARL 1.5.2 + VMAS 1.5.2 + torch 2.8.0（py3.9.6）CPU；安装 112s（远低于 25% 预算线）。MPS 实测比 CPU **慢 2.1×**（导航 10 万帧 4m26s vs 2m03s）→ 冻结 CPU。
- **A0.2 基策**：MAPPO 3 seeds × 2 任务 × 600k 帧，**6/6 SUCCESS** 且检查点齐全；中位种子规则（非最好种子）。**任务切换**：`navigation` 500 回合干净成功率 **100% → SATURATED_GE_95PCT**，按冻结规则**在看 Track 结果之前**替换为 `vmas/sampling`（覆盖型协调，与 balance 共扶刚体结构不同），切换原因入 `logs/task_switch.log`；`balance` 存活（**87.6%**，均值 121.2±25.7）。
- **A0.3 干净基线 + 判据勘误**：**预注册的原生 success 判据在本版 VMAS 上不可用**——实测终止时四个 agent 距离 0.043/0.026/0.067/0.084 全部小于半径 0.1 且 `done()` 触发，而 `all_goal_reached`/`final_rew` 仍为 False。若照原判据走，一个真能完成任务的策略会被报成 **0% 成功**。改为**场景自身 `done()`**（导航=全部进入半径；平衡=done 且未落地）。此为仪器修正，发生在任何 Track 数字之前。
- **A0.4 正对照全 PASS**（无 MEASUREMENT_BLOCKER）：A 预算分配（敏感态 16 vs 不敏感 4；+8.9 vs 0.000）；B 已知边界（结构化/随机边界召回 **3.36×**(K=50)、**2.71×**(K=100)、1.11×@200）；C 单故障穷举修复（唯一最小 2 格窗口，单格修复无效）。
- **自身缺陷全部留档**（旧版一律 `INVALID_*`）：B1 toy A 预算集合使判据在构造上不可达、toy B 结构化探针反而劣于随机（含被否决的「弥漫式发现定义」）、toy C 同义反复；B2 注册器检查路径错把 6 个成功训练写成 REJECTED；B3 判据勘误；B5 我误启第二批训练（同调用内），2 分钟内杀掉并记录。
- **Track A/B/C = BLOCKED（未运行，非 FAIL）**：无任何 Track 数字，报告 KILL/PASS 即属编造；按计划 §10 以 BLOCKED + 原因记录，冻结设计、阈值、已验证仪器与已验证策略齐备可立即重跑。Track D = NOT_ACTIVATED（依赖 Track B）。
- 包 `PHASE_A_MAINLINE_SELECTION_BUNDLE.zip`（72 文件，109 KB，sha256 `12f0deb934967cf2…`，副本在 ~/Downloads）。0 付费 LLM；未训练 RL/GNN/Transformer（仅冻结基策所需 MAPPO）；未进入方法开发 Phase B。按指令停止。

## 1.19 Phase A v3.1（PI 续跑指令：A0 已接受，Track 未跑）

2026-09-21：按 v3.1 指令执行。`A0_STATUS = ACCEPTED_WITH_ERRATA`；任务对锁定 **VMAS/BALANCE + VMAS/SAMPLING**（navigation 因 100% 饱和在看 Track 前换出，唯一冻结后备 = WIND_FLOCKING）。

- **Sampling 训练完成**：3/3 seeds × 600k 帧，检查点齐全；验证回报 s0 172.66 / s1 196.96 / s2 进行中。**500 clean + 500 random 与四条件质量门仍在运行**（trained>random / bootstrap CI>0 / Cohen d≥0.5 / 错误率≤1%），**Q25/Q50/IQR 尚未产生，因此 Track B/C 语义不得先行套用**——我没有猜任何数字。
- **注册器已按指令硬化**：append-only CSV + 每 ≤10 单元 JSONL 检查点 + finally 块写唯一终态（SUCCESS / REJECTED_WITH_REASON / ERROR_WITH_TRACE，含异常类型/消息/trace 路径）+ 对账断言。当前对账 **261 = 259 SUCCESS + 0 REJECTED + 2 ERROR**，`reconciles = true`（2 个 ERROR 是我 Track A 试跑时的崩溃，已按红线保留而非抹掉）。
- **Track A 运行器已实现并试跑通过**（克隆式短回滚 + 冻结随机策略候选 + 分离搜索/评估 RNG + 0/4/16/64 预算 + 四种等预算分配 + oracle），**但 200 状态×2 任务的正式运行未在此窗口执行**（依赖 sampling 中位种子，由运行中的审计确定）。
- **Track B/C = NOT_RUN**（按 PI 口径：NOT_RUN ≠ BLOCKED）；Track D = NOT_ACTIVATED。
- 交付：`PHASE_A_MAINLINE_SELECTION_BUNDLE.zip`（93 文件，sha256 `a57d066d6e0ad03d…`），含 `history/A0_PARTIAL_CHECKPOINT/`（v3.0 包原文）、新增 `10_A0_ERRATA_AND_TASK_SWITCH.md`（E1 判据失效 / E2 注册器路径 / E3 三个坏仪器 / E4 误启批次 / E5 饱和换任务）与 `11_SAMPLING_POLICY_AUDIT.md`（协议、部分数字、明确标注未产生分位数）。未输出 SELECTED_MAINLINE；0 付费 LLM；未训练 RL/GNN/Transformer。

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
