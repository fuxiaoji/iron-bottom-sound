---
name: command-delay-mode-v2-2
description: 命令延迟模式 v2.2 实施（CD-0…CD-7）的结构与关键坑：冻结投影比较、MOVE_TOGETHER 声明几何、通信抽象边界、炮击权限四道闸门、CD0-F1 哈希顺序缺陷
metadata:
  type: project
---

命令延迟模式 v2.2 已实施完毕（2026-09-22），入口与结构：

- 冻结 tag `realistic-command-v1-frozen`（commit `d432a975…`）；黄金回放 harness 是 `research/command_delay/golden_replay.py`，八项审计是 `research/command_delay/run_audits.py`（退出码非零即 FAIL）。**基线行在固定 `PYTHONHASHSEED` 的子进程中运行**，否则不可复现。
- 比较用**冻结投影**：只忽略冻结时不存在的 dict 键，已存在键的值必须逐字节一致。这不是洁癖——朴素字节 diff 会把"新增可选字段"误报成语义漂移（见 [[iron-bottom-sound-research]] 的引擎坑位清单）。
- 新模块：`formation_maneuver.py`（IBS-R-RC-08 `MOVE_TOGETHER`）、`command_delay.py`、`command_observation.py`、`communications/`、`delegation.py`、`target_priority.py`、`formation_agents.py`、`formation_llm.py`、`contracts.py`、`research_hooks.py`。

**Why**：这些坑都不是能从代码一眼看出的，而是实现中真实踩到并修掉的。

**How to apply**（改动本模式前先记住）：

1. **`FormationState.geometry_kind` 是声明状态，不是实时测量**。`FOLLOW_WAKE` 编队转向过程中本就会暂时不在一条线上；若用实时几何当闸门，冻结的 Realistic 行为会被破坏。它只在"本回合封存订单请求了整队机动/重整"时更新。
2. **炮击权限有四道闸门**，改动任一条都要保持其余三条：决策类型无炮击字段、`target_priority.validate_agent_decision_shape`、引擎拒绝原始炮击批次、`OrderBatch.target_priorities` 是唯一输入。审计会在每个 GUNNERY 阶段**当场**用当时候选集复核订单合法性——用终局棋盘判历史订单会得出全部非法的假结论。
3. **通信延迟只由媒介配置给出**（处理/编码/转报/队列），传播固定 0；距离只选媒介不换算延迟；任何丢包/错码概率无来源即拒绝执行。不要为了"更真实"塞进未标注来源的数值。
4. **报告与订单都按发出时间判新鲜度**（同回合按阶段序）：报文航程会交叉，到达顺序 ≠ 新鲜度顺序，否则旧报告会覆盖更新认知。
5. **命令延迟类事件必须带 `secret_side`**：初始化事件曾一次性泄漏双方指挥链。
6. **`engine.py` 里 `set[frozenset]` 的遍历是既有雷区**（CD0-F1）：同函数内骰点路径已修、友舰解冲突路径曾漏修。新增任何碰撞/分组逻辑都要用规范排序键。
7. 本地视图的接触必须来自**本编队自身舰只**的可见性；地平线取请求方自身视距（曾误取双方较小值）。

## CD-12：LLM 对 LLM 实机对战（2026-09-22）

- **可运行入口**：`research/command_delay/llm_vs_llm.py`（桥接驱动，`--battle DIR`）+ `.zcode/workflow-drafts/命令延迟模式-LLM-对战.dwf.ts`（ZCode 子代理服务循环）。战报：`research/command_delay/generate_battle_md.py`（→ `battle/REPORT.md`）；配图裁剪：`crop_battle_images.py`；泄露核验：`scan_battle_leakage.py`（`--self-test` 跑正对照）。
- **实机结论**：25 次子代理调用 0 超时；平局（axis 8 / allies 5）；**代理机动方案执行率 7/12**——5 个阵营回合的批次被引擎整批驳回后回退确定性指挥官（`cannot follow guide trail before advancing` / `speed N is outside member limits` / `cannot reverse 180 degrees` / `forced movement prevents formation following`）。**引用本局"多智能体协作"结论时必须带上这个折扣。**
- **命令延迟实证**：舰队总指挥 T3 写的命令经 TBS +1 回合，编队 T4 才读到；72 条报文里 55 条同回合、13 条跨回合、4 条停战时仍在队列。

**为什么这些坑要记住**：

1. **"不可能失败的检查"不是证据。** 旧泄漏判据是"提示词是否含未见过的敌方舰名"——IBS-S-01 双方自 T1 起全在光学距离内（轴心可见 9/9 美舰、同盟可见 5/5 日舰），该检查永不可能 FAIL；更糟的是它扫的 `agent_log` 里**没有 `prompt` 字段**，实际在扫空字典，却报了 PASS。**任何 PASS 都要先问"它在什么情况下会 FAIL"，并跑一次注入本局真实字符串的正对照。**
2. **文本泄露要看出处，不是身份。** 可判定的判据是：提示词里每个特征串都必须对读者有合法出处（自己编队更早回合 / 已投递给它的舰队命令）；敌方文字、友邻编队决策文字、任何晚于当时的回合文字都非法（第三条同时抓"敌方计划泄露"与"预知未来"）。
3. **跨阵营缺陷有两层**：命令批次层（`formation_orders` 未按阵营过滤 → 引擎每回合拒收，静默回退，代理方案从未执行）与优先级层（`gunnery_batch` 未过滤 `local_directives` → 一方火力权重进对手选择器）。**"引擎拒收"会把真正的 bug 伪装成"代理不听话"**——所以驱动必须把 rejection 记成 substitution 并在战报里披露执行率。
4. **两种"没接线"**（CD12-F3 确认不入台账、CD12-F4 报告动作不生成报文）都属于**改冻结模式语义**，会使黄金回放漂移，按纪律只登记待 PI 裁决，不自行改。

## 推送 GitHub 的一条硬约束（2026-09-23）

仓库是 **public**；历史里有 `.venv_phase_a/`（616 MB，`acfbb4f9` 误提交，含 203 MB 的 libtorch dylib）与 `research/m1_5/metrics/e2_t1_decisions.json`（124/83 MB），**直接 `git push` 必被 GitHub 拒**。

推送一律走 `scripts/push_to_github.sh`：临时克隆 + `filter-branch` 摘掉这两个路径再推，本地仓库不动。**远端那 79 个提交的 SHA 与本地不同**——所以别再指望 `git push` 本地分支能成功，也别拿本地 SHA 去 GitHub 上对；要对齐就用脚本的 `--dry-run` 看体积，或看脚本头部的说明。要真正把那两个大文件上库，得装 git-lfs（当前 `git lfs` 未安装）。
