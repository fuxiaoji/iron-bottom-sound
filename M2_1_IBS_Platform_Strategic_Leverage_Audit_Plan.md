# M2.1 — Iron Bottom Sound 平台与战略决策杠杆审计
## Platform & Strategic-Leverage Audit

**项目**：`fuxiaoji/iron-bottom-sound`  
**阶段性质**：研究平台体检，不是新论文主线，不训练最终模型。  
**科研总负责人 / PI**：ChatGPT  
**本地 AI 角色**：实验执行工程师，只按本计划实现、运行、记录、打包。

## 0. 核心目标

前几轮研究反复出现“不同决策最后价值差很小”。本阶段只回答：究竟是游戏本身低杠杆、候选动作太弱、value/victory 太粗、scripted continuation 把优势洗平、只有少数 pivotal states 有高杠杆、杠杆集中在其它 phase，还是 realistic command events 才创造杠杆。

阶段结束后，PI 才决定：
- IBS 是否继续作为 CCF-A 方法论文核心 benchmark；
- 是否建立更强的 Research Evaluation Policy；
- B（Command Organization）是否值得复活；
- 是否转向炮击/目标分配；
- 或把 IBS 降为 application benchmark。

---

# 1. 规则语义：本阶段必须尊重

## 1.1 Classic / 原版

### 秘密计划 + 同时行动
- 双方先秘密制定移动计划；
- 鱼雷计划也在移动执行前秘密写下；
- 舰船同时移动；
- 移动结束后炮击；
- 炮击同时结算；
- 鱼雷命中在炮击后结算；
- 最后处理火灾与回合结束。

因此动作价值不能只看终点坐标，必须考虑同时移动、炮击几何、鱼雷延迟和持续损伤。

### 移动具有路径依赖
- 第 1 MF 必须直航；
- 每 MF 前进 1 格；
- 60° 转向不耗 MF，但受转向时序约束；
- 120° 转向耗 1 MF；
- 最大速度有三回合循环；
- 加速/减速受上一回合速度约束；
- BB/BC 减速限制更严格；
- 碰撞按同 MF 的同时轨迹判断。

候选动作必须是完整合法 movement plan，不能只比较终点格。

### 炮击高度依赖几何
移动会改变：
- visibility；
- firing arc；
- bow/stern longitudinal-fire modifier；
- target speed modifier；
- concentration of fire；
- burning modifier；
- MFC damage；
- line-of-fire obstruction / possible misfire；
- split-fire opportunities。

所以平台审计必须加入 **gunnery opportunity diagnostic**。

### 损伤具有长期影响
包括 hull、主副炮、MFC、radar、torpedo launcher、fire、rudder、bridge、speed、captain/commander 状态等。

### 鱼雷是延迟路径决策
鱼雷具有发射格、舷侧、方向、速度、最大航程、MF 同步推进与多回合装填。不能只用当前 expected-hit heuristic 代表长期价值。

---

## 1.2 Realistic Command

真实模式是项目扩展，不覆盖原版战斗规则。

### Formation setup
玩家规则要求：
- 每方 1–4 编队；
- 每队至少 2 艘；
- 所有初始舰和预定增援舰恰好属于一个编队；
- 指定 leader / flagship / reserve flagship / succession order / spacing / heading。

**审计要求**：当前代码曾出现 `MAX_FORMATIONS_PER_SIDE=8`，而玩家规则仍为 1–4。M2.1 必须核实当前 HEAD；不自动修复。正式规则敏感实验按 1–4 执行，除非 PI 后续裁定。

### Formation movement
- 每队只提交 leader route；
- followers 沿实际 guide trail 尾随；
- 全队仍受原版移动/地形/碰撞；
- 任一成员无法合法完成时，该编队航路不能提交。

### Shared-speed crisis
编队速度是所有成员合法速度区间的交集。损伤导致不兼容时必须全队降速或永久脱队。

### Command hierarchy
leader 与 flagship 不同。flagship 的 captain killed / sunk / exit 会触发 succession；每次 transfer 使下一回合 formation 不得转向，必须重复上一回合最终 heading 与实际 speed；无继承者时 formation dissolves。

### Combat remains individual
realistic mode 只改变 command/movement layer；gunnery 仍逐舰，torpedo 仍逐 launcher。

---

# 2. 新诊断量：Strategic Leverage

对状态 `s`、合法候选动作集合 `A(s)`、evaluator `E`：

\[
Q_E(s,a)=\mathbb{E}[U\mid s,a,E]
\]

IBS 中禁止写成 `Q*`，除非 exact solver 真求最优。

主指标：

\[
\Lambda^{90-10}_E(s)=Q_{0.90}\{Q_E(s,a)\}-Q_{0.10}\{Q_E(s,a)\}
\]

同时报告：

\[
\Lambda^{range}_E(s)=\max_aQ_E(s,a)-\min_aQ_E(s,a)
\]

以及 best-vs-second-best gap。

解释：
- `Lambda ≈ 0`：做对/做错差异很小；
- `Lambda` 大：该状态有真正决策杠杆。

90–10 分位作为主值，降低极端异常动作对 range 的支配。

---

# 3. 固定四层 value panel

## U0 — Authoritative scenario value
优先调用当前 engine 的官方 score / winner / threshold，不复制规则常量。

- **S-01**：7 回合 VP 制，领先至少 4 分才胜；首回合日方不得炮击；第 4 回合前日方不得鱼雷；美方 GF 减半。
- **S-03**：4 回合 threshold objective，核心是德方 DD 是否被击沉或减速到 `2-2-2`；官方 outcome 很离散。
- **EM-01**：项目版本 12 回合，damage-point scoring，25 分差获胜；hull、BB fire control/radar/primary mount/speed loss 都有计分，是 dense leverage audit 主场景。

## U1 — Normalized Material Value（诊断，不是官方胜负）
先冻结公式再运行。建议：

\[
M(s)=\frac{\sum_{enemy}VP_i\cdot damageFrac_i-\sum_{own}VP_i\cdot damageFrac_i}{\sum_{all}VP_i}
\]

- sunk = 1；
- hull fraction 为主项；
- 不擅自给炮塔/MFC/radar 加人工权重；
- 若当前代码已有统一 ship combat value，可审计后复用，但必须记录公式。

## U2 — Gunnery Opportunity（只做 diagnostic）
在 movement 后、gunnery 前，用只读 engine 语义计算：
- 合法可见目标；
- 每舰合法 target allocation 的 expected hits/threat；
- 双方 opportunity margin。

禁止把 TacticalCommander heuristic score 当 U2。

## U3 — Physical State Divergence（非价值）
比较动作分支在 end-of-turn 的：positions、headings、speeds、visibility graph、formation integrity、damage、legal-action counts。

若 U3 大但 U0/U1 leverage 小，提示 evaluator/continuation 可能“洗平”价值。

---

# 4. P0 — Rule-to-Engine Conformance Audit

在任何 leverage 主实验前完成：

`RULE_ENGINE_CONFORMANCE.md`

字段：

```text
rule_id_or_section
source_rule
engine_code_path
existing_test
probe_test
status
notes
```

status 只能：

```text
SOURCE_EXACT
PROJECT_EXTENSION
INTENTIONAL_INTERFACE_STRICTER
NOT_IMPLEMENTED
BUG
UNKNOWN
```

必须检查：
- phase order + S-01/EM-01 initial phase special cases；
- secret/sealed movement/torpedo planning；
- observation 不泄漏 opponent sealed order；
- simultaneous movement；
- first MF / 60° / 120° / acceleration / deceleration / BB-BC braking；
- collision；
- visibility / arcs / facing / speed modifier；
- obstruction / misfire；
- simultaneous gunnery damage；
- damage persistence；
- torpedo path / delay / reload / speed restrictions；
- S-01 / S-03 / EM-01 victory；
- realistic formation follow / shared speed / detach / succession / disruption / dissolution；
- realistic gunnery/torpedo 仍逐舰。

### 特别：非法移动语义
原版桌游规则中存在非法移动计划的 fallback；当前数字引擎可能在 submit 前 reject。必须明确当前实现。M2.1 只比较 validator 通过的合法动作。

若存在会影响主结果的 `BUG/UNKNOWN`：暂停 leverage，先给 PI blocker checkpoint。

---

# 5. P1 — RNG / Branching Audit

生成：`RNG_BRANCHING_AUDIT.md`

同 seed 不自动等于真正 CRN。若动作导致不同炮击数/碰撞数/鱼雷检定数/fire rolls，RNG draw sequence 可能错位。

测试：
1. 同 snapshot + 同 action + 同 seed 两次，必须 deterministic；
2. 同 snapshot + action A/B + 同 seed；
3. 记录 `rng_counter`、dice event sequence、roll count；
4. 判断 branch 后 RNG 是否事件对齐。

必须输出：

```text
RNG_PAIRING_STATUS =
  TRUE_EVENT_ALIGNED_CRN
  MATCHED_INITIAL_SEEDS_ONLY
  UNSAFE
```

若仅 matched-seed，后文禁止称 CRN。

---

# 6. P2 — Action Candidate Coverage Audit

低 leverage 可能只是候选动作太弱。先确认动作集覆盖真正不同的合法战术。

## 6.1 Classic movement
每 state 目标 8–12 个 unique validated joint batches。

来源：
- balanced / fleet / line / brawl / cautious 完整 joint proposals；
- slower legal batch；
- faster legal batch；
- port-biased；
- starboard-biased；
- dispersed；
- formation-preserving；
- 1–2 high-VP/front-line ship local perturbations；
- 至少 2 random legal joint batches。

所有计划必须来自 engine movement candidates/path/preview，最终 full side-level validator 通过。不得使用 hidden enemy info。

记录 action diversity：endpoint distance、heading divergence、speed divergence、plan edit distance。

## 6.2 Realistic movement
只比较合法 formation-level actions：
- RealisticCommander 多 profile proposals；
- leader-route perturbation；
- spacing/speed variants；
- 真实 speed crisis 时合法 reduce/detach。

不得绕过 formation constraint 控制 follower。

## 6.3 Gunnery
每 state 6–10 个合法完整 batches：
- current assist；
- concentrated expected-hit；
- high-VP target；
- finish damaged target；
- split fire；
- hold/minimal；
- random legal。

## 6.4 Torpedo
每 state 5–8：hold、current、direct、existing doctrine candidate、random legal。本轮只测 leverage，不研究 influence。

若动作集实际上高度同质：`ACTION_COVERAGE_FAIL`。

---

# 7. P3 — Snapshot Sampling

不得按“看起来有趣”手挑主样本。

## Classic main census
每 scenario：
- movement 15；
- gunnery 10；
- torpedo 5。

S-01 / S-03 / EM-01 共约 90 states，覆盖 early/contact/damaged/late/both sides。

## Realistic subset
每 scenario：
- movement 10；
- gunnery 5。

共最多 45 states。

额外从 M2-0 已有自然 command disruption cases 中抽 15–20 个 disruption/pre-disruption states。

优先复用既有 replay locator，不重刷海量对局。

---

# 8. E0 — Current Scripted Evaluator

控制组。

当前 candidate action 执行后：
- 后续使用正式 TacticalCommander / RealisticCommander；
- profile 预注册；
- matched seed set；
- 先完成到 end-of-current-turn；
- 关键 subset 再 H=1/H=2/terminal。

保存：

```text
state_id
phase
action_id
seed
U0
U1
U2
U3
events
rng_counter_delta
```

先 3-state pilot 估 variance/time。reps 从 5 起，最多 20。

---

# 9. Horizon Audit

- H0 = 当前完整回合结束；
- H1 = 下一个完整回合结束；
- H2 = 再下一个完整回合结束；
- S-03 尽量 terminal；
- S-01 代表 subset terminal；
- EM-01 小 subset terminal/固定剩余 horizon，先估时。

核心图：`Lambda(H0/H1/H2/terminal)`。

如果 leverage 随 horizon 快速趋零，提示 continuation attenuation；若短期低但长程高，提示原来 horizon 太短。

---

# 10. E1 — Diverse Continuation Policy Ensemble

目的：排除 balanced-vs-balanced 脚本特性。

预注册 9 个 continuation pairs：

```text
balanced-balanced
fleet-fleet
line-line
brawl-brawl
cautious-cautious
balanced-brawl
brawl-balanced
fleet-cautious
cautious-fleet
```

对 E0 每 scenario 分层抽 low / medium / high leverage 各 5 states 左右，总约 45 states。

定义：

\[
Q_{mix}(s,a)=average_{profile\ pairs}E[U|s,a]
\]

profile set 冻结后不改。

---

# 11. E2 — Local Minimax / Replanning Evaluator

本轮关键“强 evaluator”。不是 full MCTS，不是 RL。

对当前动作 `a_t`：
1. 执行到下一 focal decision point；
2. focal 生成 4–6 个合法候选；
3. opponent 生成 4–6 个合法候选；
4. 按真实 simultaneous/sequential phase 语义构造小 response matrix；
5. 计算短 horizon：

\[
V_{local}(s')\approx\max_{a_f}\min_{a_o}Q(s',a_f,a_o)
\]

随后可回到 scripted continuation。

禁止 evaluator policy 输入 opponent private/sealed info。

只能称 **local tactical minimax evaluator**，不得称 optimal。

只在约 24–30 diagnostic states 上跑。先 3-state pilot；若预计 >8 CPU-hours，先停并生成 `E2_COST_CHECKPOINT`。

---

# 12. E3 — Adversarial Profile Evaluator

current action 后：
- focal continuation 固定；
- opponent 在预注册 profile pool 中取最坏 expected value：balanced/fleet/line/brawl/cautious；
- 若已有可直接复现的 evolved，可以加入，但不得为本轮重训。

\[
Q_{adv}(s,a)=\min_{\pi_o\in P}E[U|s,a,\pi_o]
\]

作用：检测动作是否只对 balanced 有价值。

---

# 13. Continuation-Policy Attenuation

定义：

\[
A_{search}(s)=\Lambda_{E2}(s)-\Lambda_{E0}(s)
\]

并报告 ratio。

重点寻找：

```text
physical divergence high
E0 leverage low
E2/E3 leverage high
```

这是 scripted continuation “洗平”战略优势的关键证据模式。

---

# 14. Platform Health 判定

全部 threshold 在主结果前写入 `PRE_REGISTRATION.md`。

建议用 U1 normalized material 作为跨场景统一 leverage scale，同时 U0 官方结果并列报告。

## HEALTHY_LEVERAGE
强 evaluator 至少一个、≥2 scenarios、≥30% states 满足：

\[
\Lambda^{90-10}_{U1}\ge0.10
\]

且 action ranking 可分辨。

## SCRIPTED_FLATTENING
- E0 高 leverage states <15%；
- E2/E3 中 ≥30% states ≥0.10；
- strong evaluator median leverage ≥ E0 的 2 倍；
- U3 divergence 不低。

## PHASE_LOCALIZED
至少一个 phase ≥30% high-leverage，另一个主要 phase 明显低，并跨 ≥2 scenarios。

## SPARSE_PIVOTAL
median low，但 ≥10% states 满足：

\[
\Lambda_{U1}\ge0.20
\]

且至少两个 evaluator 确认、CI 可分辨。

## LOW_LEVERAGE_PLATFORM
E0/E1/E2/E3 都低，<10% states ≥0.10，terminal subset 也不恢复，且 rules/action coverage 均 PASS。

---

# 15. Scenario-specific interpretation

## S-01
7 turns VP，首回合日方无炮击、第 4 回合前日方无鱼雷、美方 GF 减半、存在概率增援。早期 movement 的 terminal effect 可能延迟，增援 RNG 会加大噪声。

## S-03
4 turns，胜负是“击沉/把德国 DD 降速到 2-2-2”的 threshold。官方 outcome 粗，必须并列 material + speed-to-threshold diagnostic。winner 不变不等于动作没价值。

## EM-01
12 turns + dense damage-point scoring，是主场景。若 EM-01 在强 evaluator 下仍长期 flat，才是严重平台警告。

---

# 16. Realistic-mode special audit

分层：
- normal formed；
- speed crisis；
- pre-command-transfer；
- command disruption。

分别测 movement leverage。

若只有 disruption states 高 leverage，说明 realistic mode 是 event-driven sparse-leverage environment。

---

# 17. B（Command Organization）复活门

B 当前状态：`SUSPENDED`。

只有 M2.1 同时满足以下条件才交 PI 复审：
1. command disruption/pre-disruption states 高 leverage；
2. E2/E3 强 evaluator 下 B1 sensitivity 仍存在；
3. 至少两个 scenario/regime 重现；
4. effect 不是静态 heuristic rule 的偶然符号；
5. 有迹象表明 pre-battle observable context 与 preferred hierarchy 有关系。

本轮不要训练 organization model。

若 1–3 都不满足：`B_PERMANENTLY_ARCHIVE`。

---

# 18. 必须做的统计

每 evaluator × scenario × phase：

```text
n_states
n_actions_per_state
valid_action_rate
Lambda90_10 median
Lambda90_10 p75/p90
fraction >=0.05
fraction >=0.10
fraction >=0.20
range leverage
top2 gap
bootstrap CI
U3 divergence
```

另报：
- rank correlation E0 vs E1/E2/E3；
- best-action agreement；
- low->high leverage transitions；
- high->low transitions。

---

# 19. 必须画的图

1. Lambda CDF by evaluator
2. Lambda by scenario
3. Lambda by phase
4. E0 vs E2 scatter
5. E0 vs E3 scatter
6. U3 divergence vs leverage
7. H0/H1/H2/terminal leverage curve
8. best-action agreement heatmap
9. S-03 official outcome vs speed-threshold diagnostic
10. realistic formed/speed-crisis/disruption leverage
11. ≥10 representative action-value tables

---

# 20. 代表案例

至少保存：
- **Case L**：物理差异大，但所有 evaluator value 都近似相同；
- **Case F**：E0 平坦，但 E2/E3 拉开；
- **Case P**：少数 pivotal state，多 evaluator 一致高 leverage；
- **Case G**：gunnery 高 leverage、movement 低（若存在）；
- **Case R**：realistic command disruption 高 leverage（若存在）。

每个案例保存 board/state summary、legal candidates、Q table、continuation profiles、event diff、rule explanation。

---

# 21. 停止规则

禁止：
- MAPPO/QMIX/GNN/Transformer；
- 新 paper method；
- 新 torpedo heuristic；
- 新 organization net；
- 修改 victory/rules；
- 为提高 leverage 人工制造主分析不可达 state。

允许：research-only evaluator、local search、diagnostic metrics、rule unit-test intervention。

---

# 22. 计算预算

先 pilot：
- E0 主 census ≤150 states；
- E1 ≤45；
- E2 ≤30；
- E3 ≤45；
- action candidates/state ≤12；
- reps 从 5 起，最多 20；
- 新增 full-match equivalent 尽量 ≤20,000；
- 0 付费 LLM；
- 不租服务器。

---

# 23. 最终结果包

文件：

`M2_1_PLATFORM_STRATEGIC_LEVERAGE_AUDIT.zip`

必须包含：

```text
00_EXECUTIVE_SUMMARY.md
01_RULE_ENGINE_CONFORMANCE.md
02_RNG_BRANCHING_AUDIT.md
03_ACTION_COVERAGE_AUDIT.md
04_SNAPSHOT_DATASET.md
05_E0_SCRIPTED_LEVERAGE.md
06_HORIZON_AUDIT.md
07_E1_POLICY_ENSEMBLE.md
08_E2_LOCAL_MINIMAX.md
09_E3_ADVERSARIAL_PROFILE.md
10_REALISTIC_MODE_LEVERAGE.md
11_PLATFORM_DIAGNOSIS.md
12_B_REASSESSMENT.md
VALUE_SEMANTICS.md
PRE_REGISTRATION.md
EXPERIMENT_REGISTRY.csv
CLAIM_EVIDENCE_MATRIX.csv
FAILURES_AND_COUNTEREXAMPLES.md
DATA_MANIFEST.md
git_info.txt
environment.txt
figures/
metrics/
cases/
code_patch/
logs/
```

不要打包 `.git`、`.venv`、node_modules、keys、大体积可再生 cache。

---

# 24. Executive Summary 必须硬判

```text
RULE_ENGINE_CONFORMANCE = PASS / FAIL / BLOCKED
RNG_PAIRING_STATUS = TRUE_EVENT_ALIGNED_CRN / MATCHED_INITIAL_SEEDS_ONLY / UNSAFE
ACTION_COVERAGE = PASS / FAIL

MOVEMENT_LEVERAGE = HIGH / SPARSE / LOW
GUNNERY_LEVERAGE = HIGH / SPARSE / LOW
TORPEDO_LEVERAGE = HIGH / SPARSE / LOW
REALISTIC_COMMAND_LEVERAGE = HIGH / SPARSE / LOW

SCRIPTED_CONTINUATION_ATTENUATION = YES / NO / AMBIGUOUS
HORIZON_MASKING = YES / NO / AMBIGUOUS
VICTORY_METRIC_MASKING = YES / NO / AMBIGUOUS

PLATFORM_DIAGNOSIS =
  HEALTHY_LEVERAGE /
  SCRIPTED_FLATTENING /
  PHASE_LOCALIZED /
  SPARSE_PIVOTAL /
  LOW_LEVERAGE_PLATFORM /
  MIXED

IBS_FUTURE_ROLE =
  CORE_METHOD_BENCHMARK /
  CORE_AFTER_NEW_EVALUATOR /
  PHASE_SPECIFIC_BENCHMARK /
  APPLICATION_BENCHMARK_ONLY

B_COMMAND_ORGANIZATION =
  REASSESS /
  KEEP_SUSPENDED /
  PERMANENTLY_ARCHIVE

NEXT_PI_DECISION_NEEDED =
```

禁止用 `promising/encouraging/probably` 代替结论。

---

# 25. PI 决策树

```text
RULE AUDIT FAIL
 -> 先修平台

ACTION COVERAGE FAIL
 -> 先修 candidate generator

STRONG EVALUATORS 也 LOW LEVERAGE
 -> IBS 降为 application benchmark
 -> 标准 MARL benchmark 作为主实验

E0 LOW，但 E2/E3 HIGH
 -> scripted continuation 是根因
 -> 建立冻结 Research Evaluation Policy
 -> 再复审 B / organization

某 PHASE 明显 HIGH
 -> 后续研究聚焦该 phase

SPARSE PIVOTAL
 -> 保留 IBS
 -> 下一轮再研究 pivotal decision structure

B states 在强 evaluator 下稳定高 leverage
 -> B 进入 PI 复审
```

**本阶段最重要的一句话：不要证明某个新方法好。先证明这个平台的“好动作”和“坏动作”在可信 evaluator 下真的能被区分。**
