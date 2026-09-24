# todo.md — 活动任务清单

> **性质**：本文件是**滚动更新**的活动任务清单（不是完成记录，也不是阶段台账）。
> **职责划分**：
> - `todo.md`（本文件）= 现在要做/正在做/刚做完的**活动任务**；
> - `PROGRESS.md` = 25 阶段流水线的**阶段级**留痕与版本循环；
> - `plan.md` = **批次级**计划（每批次追加在顶部）；
> - `havedone.md` = **只追加**的完成记录（含测试、证据、提交哈希）。
> **规则**：任务完成后**不在此处保留长期历史** —— 把证据写入 `havedone.md` 与 `PROGRESS.md`，然后从活动区移走。

**最后更新**：2026-09-24

---

## 活动任务

**命令延迟交互层（v2.4 界面批次）：已完成**，证据见 `havedone.md` 2026-09-24 条。
- 修掉三个真实缺陷：前端读已删字段导致指挥链面板空白、顶栏按钮静默覆盖代理方案、
  运行中的 API 服务还是 v2.2 旧代码（该对局两封电报因此卡在「待发」）。
- 新增只读投递预判与模型接入接口（含舰队代理），重写两个面板并新增「打法说明」。
- **已接入智谱免费档 `glm-4.5-flash`（思考链开，3000 tokens）**：双方编队 + 同盟舰队代理；
  密钥只在服务进程内存，重启或新建命令延迟对局后需重新接入。看思考：顶栏「调试」开 →
  「编队代理记录（调试 · 含思考链）」。demo 对局 `4d9c33b1-e709-439e-8159-a9d66d4249f0`。
- 未做的事（如实记录）：**用户自己的对局尚未推进**（推进即触发 6–7 次模型往返，约 5 分钟），
  由用户决定何时按「交接」。

**CD-13（指挥链 + 二马剧本 LLM 对战 + 纪录片）：已完成**，证据见 `havedone.md` 2026-09-24 条。

- 交付物：`research/battle_video/out/documentary.mp4`（12.0 分钟 1080p30，另出 720p）、
  `research/command_delay/battle_em01/REPORT.md`（含配图）、`data/narration_script.md`、
  `data/subtitles.srt`、以及完整对局记录（calls/orders/reports/views）。
- 用户交付时的两个提醒：**视频不在 git 里**（212MB 超 GitHub 单文件上限；用
  `research/battle_video/make_documentary.sh battle_em01` 可一键重建）；**API key 曾在对话中出现，建议轮换**。

**已结案**：T-18（CD12-F3 确认不入台账）、T-19（CD12-F4 上报不接线）——本轮按 PI 指示实现：
确认写入 `acknowledged_turn`，上报由分舰队 agent 亲笔 + 引擎保底，且都成为真实报文。

## 待裁决（登记，未改语义）

**机动方案的两处引擎语义问题**（本轮只做标记与过滤，未改结算规则）：
1. **编队内同脉冲同格**：含原地 120° 的方案在显示路径被避开（"间距纵队传不下去"），但
   `expand_movement_orders` / `validate_orders` 接受它，结算时同队两舰同脉冲进同格 →
   `formation_emergency_stop` 整队急停。是否改为**拒绝**（让代理当场失败并重选）属冻结语义变更。
2. **跨编队航迹冲突**：两支编队的方案各自可行但在同一脉冲相交时，引擎仍按既有规则给其中一支减速；
   此时计划表显示的是调整后的方案，代理的原始选择只在记录里可见。

## 待办（按流水线强制顺序）

| # | 任务 | 关联阶段 | 依赖 | 状态 |
|---|---|---|---|---|
| T-4 | 向用户索取阻塞槽位：目标会议、截稿时间、页数上限、会议 LaTeX 模板、文献年份下限 | 全流水线 | 用户输入 | 待办 |
| T-5 | 核验现行稿件的分节实际词数 vs `RESTRICTS.yaml` §4 下限（`paper_v14/sections/*.tex`） | 17 | 无 | 待办 |
| T-6 | 对 `research/final_v14/` 逐条复核真实性红线（收敛门控 / 禁 `np.trapz` / 禁 `try-except` 掩盖 NaN / `TIME_ESTIMATE` pilot / `time_guard`） | 10、12、13 | 无 | 待办 |
| T-7 | 阶段 4–6 重建：真实 API 文献采集（≥30 篇）→ 门控筛选（保留 `cite_key`/DOI）→ 知识卡片 | 4、5、6 | T-4（年份下限）、API 凭据 | 待办 |
| T-8 | 阶段 14 独立上下文多 Agent 结果分析（含真实数值） | 14 | T-6 | 待办 |
| T-9 | 阶段 15 决策：`PROCEED` / `REFINE` / `PIVOT` 并登记 `PROGRESS.md` §0.1 循环表 | 15 | T-8 | 待办 |
| T-10 | 阶段 18 方法论-证据一致性逐行核查（draft vs log/results） | 18 | T-9 | 待办 |
| T-11 | 阶段 23 引用真实性与相关性双查（≥30 篇、年份下限） | 23 | T-7 | 待办 |
| T-13 | M2.2-R/B1E 已完成（判定 TORPEDO_PARTIAL_OBSERVABILITY + movement MIXED，包 `1ce46fa8…`） | — | 无 | 完成 |
| T-13b | M2.3 已完成：JTC = FAIL（含 M23-F3 surrogate 可加性混淆）、BARD = FAIL（匹配对照砍半效应）、MAINLINE_CANDIDATE = NONE，包 `85d3e41f…` | — | 无 | 完成 |
| T-13c | M2.4 已完成：INTERACTION_STRUCTURE=PRESENT 但 JTC_INTERACTION_GATE=FAIL（六条全否）→ **JTC 永久 kill**；BARD 归档；包 `5781e81a…` | — | 无 | 完成 |
| T-17 | 主线状态：JTC 与 BARD 均已 kill/归档，`IBS_NEXT_ROLE = APPLICATION_BENCHMARK_ONLY`。后续若继续，需 PI 给出新研究轴（现有确认资产：MG1/MG3-E/MG4 机制、B1E 双尺度外部性、BARD 指标集、永久 kill 的 JTC 结论） | — | 用户输入 | 阻塞 |
| T-14 | 等 PI 裁决：① torpedo partial observability 是否升为主线（建议先做 size/diversity-matched subset 对照分离假设 B）② MG3 是否改注为 superseded-by-MG3-E ③ 「编译整条线而非单舰」是否立题 ④ 后续 census 是否加 `mid` 桶与 range 臂（修 M22R-F1/F3） | — | 用户输入 | 阻塞 |
| T-15 | 技术债：`b1e.py` 的 Counter 序列化已修，但 `summarize` 仍是崩溃丢全量的结构（现靠 JSONL 恢复）；建议改为流式汇总 | — | 无 | 待办 |
| T-12 | 阶段 22 套用目标会议 LaTeX 模板并导出 | 22 | T-4 | 待办 |

## 已完成（本会话 2026-09-18，证据已归档至 `havedone.md`）

| # | 任务 | 证据 |
|---|---|---|
| D-1 | GitHub `Yuan1z0825/nature-skills`（43k★，commit `2375e0abdf42158ef149256f2c64b1f759a0d274`）安装到 `~/.zcode/skills/nature-*`；稳定 clone 于 `~/ai-skills/nature-skills`；同步脚本 `~/ai-skills/sync-nature-skills.sh` | 20 个技能目录，`SKILL.md` frontmatter 全部合法（20/20）；跨技能引用 `../../../nature-shared/core/*` 5/5 命中 |
| D-2 | 粘贴提示词文档化 | `MEGA_PROMPT.md`（26 KB）+ `docs/pipeline/STAGE_PROMPTS.md`（26 KB，24 个模板原文照录，6 个缺模板阶段已显式声明） |
| D-3 | `RESTRICTS.yaml` 建立 | 项目 `.venv` 解析通过；14 个顶层键；红线组 5 项；门控 `[5,9,20]`；最少循环 2 |
| D-4 | `agent.md` 扩展为治理宪法（原 4+5+4 条**逐字保留**，新增会话纪律/记忆制度/子 agent 审计/流水线纪律/红线 R1–R10） | `git show HEAD:agent.md` 比对：原 10 条关键条款 10/10 KEPT |
| D-5 | 项目内长期记忆库 `memory/`（索引 + 6 条正文）与 ZCode 自动加载层指针 | `memory/MEMORY.md` + 6 个正文文件 + `~/.zcode/.../memory/project-memory-and-governance-location.md` |
| D-6 | 工作区入口 `seawar/AGENTS.md`（cwd 在 seawar 时自动加载，路由到仓库治理文件） | 文件就位 |

---

## 规则

1. **不编造**：任务状态必须有可核查证据；未核验的历史产物标 ⟨待核⟩，不得直接标完成。
2. **不越门**：门控（阶段 5、9、20）未通过前，不得启动其下游阶段的"完成"标记。
3. **失败保留**：失败分支与未触发扩展项必须保持失败/未触发标记。
4. **闭环**：任务完成 → 证据写 `havedone.md` + 阶段台账写 `PROGRESS.md` → 从本文件活动区移除。
