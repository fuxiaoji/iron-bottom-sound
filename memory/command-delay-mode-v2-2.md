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

## CD-13：舰队级 agent、上报链路、预算翻倍与纪录片（2026-09-24）

**指挥链现在是两级**：舰队总指挥是独立 agent（`fleet_llm.py`，自己的提示词/解析器/记忆/思维链），
在 `on_phase_advanced` 里**先于**编队 agent 运行（`run_fleet_agent`），所以给本队的命令当面交办、
同一回合即生效；给其他编队的走电报（README 的延迟表不变）。分舰队每回合上报：引擎保底态势+目击，
外加 agent 亲笔的 `report_text`；上报按 **`reporting_formation_id`** 记账（信封写给舰队，
知识归给上报者）。确认/偏离/澄清都是真实报文。

**实现坑（都不是能从代码一眼看出的）**：

1. **舰队 agent 的提示词必须自己序列化**：`FleetProviderPolicy` 不能复用 `ProviderPolicy._payload`（它按编队白名单裁字段，会把舰队提示词裁成空壳）。另外 `build_fleet_prompt` 里的 pydantic 模型要让 `json.dumps` 能处理（`model_dump(mode="json")`），否则在**发请求时**才炸。
2. **总指挥必须能对自己所在编队下令**——我第一版把"本队"从 `addressable_formations` 里排除了，于是当面交办规则永远不可能触发（单元测试反而先过）。现在本队在名单里并标注"当面交办：即刻生效"。
3. **确认的匹配不能用 origin==destination**：报文 origin 是舰 id，destination 是编队 id；确认要按 `payload.order_id`（+ `acknowledged_by`）回写 `acknowledged_turn`。
4. **思考模型要留足输出预算**：glm-4.5-flash 在 `max_tokens=2000` 时会用推理吃光预算、返回 `content=""` + `finish_reason=length`，被解析器判为"只有推理"而重试——**约 19% 的调用这样浪费掉**。开到 4000 后本局零发生。
5. **传输失败必须是一次尝试，不是一场对局的结束**：网络错误曾让驱动直接崩掉整局。现在 agent 捕获异常记为失败尝试（回退教条），recorder 还会在**直连与环境代理之间交替重试一次**（本机 `open.bigmodel.cn` 解析到 198.18.0.0/15，透明代理会成片返回 503，约 30% 的调用中招但都可重试成功）。
6. **记忆截断方向曾经是反的**：`render_for_prompt` 超限时保留的是尾部，也就是把"当前命令 + 备忘"丢掉、留下最旧的历史——与它自己的注释和测试声称的相反（测试只是因为样本不够大才通过）。现在保头，测试也改成真的断言超限时命令与备忘仍在。
7. **黄金基线只覆盖了模式关闭的行**：既有 7 行全是 `command_delay_mode:false`，所以 CD-13 的改动零漂移；新语义另开一行 `cd_s01` 冻结（含报文台账、上报作者、记忆条数、as-substitutions）。**判据的可失败性**又一次成为要点（见 CD12-F5/F6/F7）。

**纪录片是"从记录生成"的**，不是剪出来的：`replay_battle.py` 先用 `orders.jsonl` 重演并核验（本局 90 个批次、24 舰、0 不一致），出三视角静帧；`build_timeline.py` 把解说词、屏显、节奏**全部由记录推导**（含每回合"看得见几艘 vs 海图上几艘"的信息差）；`tts_speak.py` 用固定音色的 ChatTTS 配音；Remotion 只负责包装层。**节奏按事件而非回合数**（安静回合合并成蒙太奇），否则同样一份记录会拍成 24 分钟。

## CD v2.3 修复批次（2026-09-24，IR-0…IR-9）

**两条必须记住的引擎事实**：
1. **TBS 射程是可达性阈值，不是延迟**：`TBS_DIRECT_RANGE_HEX = 73`（≈25 法定英里 @600yd/格）。
   v2.2 把**光学能见度**（13/15 hex）当射程用，于是 14–42 hex 的报文全被推上"转报再加密 +2"
   （本局 55 封全是美方，理由声称"不同密码体系"——模式里根本没有密码域概念）。
   **距离永远不换算成回合延迟**；延迟只来自 handling/encoding/relay/reencipher/queue/clarification。
2. **"长命令 +1"已删除**：长度体现为**信道槽位**（≤240 字 1 槽、≤600 字 2 槽、更长 3 槽），
   占不到槽位就在队列里等，延迟以 `queue` 分量出现。中继/再加密必须带 `route_nodes[]` 与理由。

**三个新的模式机制**：`RadioPolicy`（NORMAL/CONTACT_ONLY/SCHEDULED_WINDOW/STRICT_SILENCE，起草前判定）；
`KnowledgeItem` 知识账本（本地观测 / 投递报文，替代"编队可见兄弟报告位"的窗口）；
`MissionOrder` 持久化 + 修订线（NEW/AMEND/CANCEL/ACTIVATE_PREBRIEFED_BRANCH/NO_NEW_ORDER，重述不产生修订）。

**两个自己踩的坑**：① 当面交办路径**先折入投递、后盖送达回合** → `confirmed_turn` 恒为 None →
命令永不"生效"、去重与修订线全失效（IR-9 战报的命令修订表暴露：全是 rev=1）；
② 事件驱动上报必须先改**默认条令**（`mission_order_template` 里写着"每回合一份 sitrep"）。
