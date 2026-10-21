# 铁底湾的回响 IV

可审计的 Python 兵棋规则后端与 React/TypeScript Web UI。当前分支是阶段 1 的可运行基础，不代表所有规则已经完成四向闭环；真实状态见 `plan.md` 和 `docs/rules/coverage.csv`。

## 本地运行

Windows 可直接双击项目根目录 **`一键启动游戏.exe`**，启动完成后自动打开浏览器。它会调用当前 `scripts/start-game.ps1`，重复启动复用本项目服务，不删除存档或战报；失败时显示提示，并可打开 `tmp/runtime/launcher.log` 所在目录。请将 EXE 留在项目根目录，不要单独移动到桌面（可以创建快捷方式）。这是本地启动器，不是免 Python / Node.js / 前端依赖的完整游戏安装包；未做代码签名，Windows 可能显示未知发布者。

EXE 源码在 `scripts/launcher/GameLauncher.cs`，不需要下载打包工具。重新构建需使用不存在的输出路径：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build-launcher.ps1
# 已有 EXE 时另存新文件，避免覆盖正在使用的启动器：
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build-launcher.ps1 -OutputPath .\一键启动游戏-新版.exe
# 不打开浏览器 / 完整重启当前项目后端：
.\一键启动游戏.exe --no-browser
.\一键启动游戏.exe --restart-backend
```

Windows 一键启动（首次运行前需按下文安装 Python 与前端依赖）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-game.ps1
```

脚本会打开 `http://127.0.0.1:5173`，进度会保存到本地 SQLite。

启动器现在会验证端口归属并复用本项目服务；后端源码自动重载，不再混用旧引擎与新 AI。需要完整重启后端时运行 `powershell -ExecutionPolicy Bypass -File scripts/start-game.ps1 -RestartBackend`，或再次双击根目录 `start-game.bat`。启动/重启不会删除存档或战报。`http://127.0.0.1:8000/health` 返回 `ready` 才表示已加载当前后端源码；日志在 `tmp/runtime/backend-error.log`。

停止服务：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop-game.ps1
```

也可以分别启动后端和前端：

```powershell
python -m pip install -e ".[dev,corpus]"
python -m iron_bottom_sound
```

另开终端：

```powershell
cd frontend
pnpm install
pnpm dev
```

浏览器访问 `http://127.0.0.1:5173`。API 文档位于 `http://127.0.0.1:8000/docs`。

## 真实模式状态机 AI

2026-10-12 修复：所有状态机一旦决定使用某具鱼雷发射器，就发射该管当前全部剩余鱼雷；未选中的管仍可保留。整管候选先经过原引擎射界、发射时机及己方雷道安全筛选，再进入战术评分；不会为了清空鱼雷强行发射危险雷道。玩家和 LLM 仍可按原规则选择部分齐射，装填/损毁限制不变。以下强度统计是此次策略修复前的冻结版本，未重新测定整管齐射后的胜率。

另一个独立入口「命令延迟」已从 `command-delay-run` 合入当前新 AI 版本：在「我想直接开战」的指挥方式中选择，适用于想定 1、想定 3 和第二次马里亚纳海战。它保留任务式自然语言命令、通信队列与链路延迟、本地代理及每个编队的记忆，完整规则见 [命令延迟规则](docs/rules/command-delay.md)。该入口的编队采用 LLM 代理，不提供状态机对手；新建对局需填模型和本次会话密钥。服务器重启后密钥不保留，未恢复连接的存档由教条代理执行，并在代理记录中说明，不冒充 LLM 输出。经典、真实模式仍使用原来的状态机选择器。

真实与命令延迟可显式选择尾随或整队机动；默认仍为尾随。机动资格与重整纵队由引擎核验，不把横队/斜队假装成纵队。刷新后若本方已封存但对手执行失败，使用「本方已封存 · 重试对手并继续」，无需重复提交。

首页点击「我想直接开战」→「状态机 AI」，其下方即可选择「状态机对手类型」：协同舰队（推荐）、T 头猎手、雷击双翼、护航屏卫、分进合击，以及旧战术风格。选择新风格会自动启用真实模式；真实/经典往返记住各自的选择。剧本工坊使用同一选择器；不具备真实编队资格的自定义剧本会显示原因并禁用新风格，不再静默隐藏。

各风格共享按编队角色切换的搜索、接敌、抢 T 头、雷击、避雷、掩护与撤退状态机。移动先展开整个纵队，再做逐脉冲友军航路预约和下一回合首脉冲预防；雷击沿引擎提供的合法发射时机、雷道与齐射数量筛选，不向己方已封存航路发雷。只预测本方可见鱼雷，不读取敌方秘密订单或迷雾中的舰船。

强制直行、指挥中断、受损舰自主撤退或敌舰临时阻挡仍可能产生剩余风险；AI 在计划中记录风险，由既有引擎执行紧急避碰，不绕过损伤规则。旧对局不会自动更换已选对手；代码更新后请重启本地服务，再新建对局选择新风格。

离线行为验收（不读写玩家存档数据库）：

```powershell
python -m pytest tests/test_cooperative_formations.py
python scripts/evaluate_realistic_ai.py --profiles rc_coordinated rc_torpedo_wings --scenarios IBS-S-03 IBS-S-EM-01
# 91 舰大地图只做前两回合冒烟，不把它计作完整对局：
python scripts/evaluate_realistic_ai.py --profiles rc_coordinated --scenarios IBS-S-FM-01 --turn-limit 2
```

报告默认保存在 `artifacts/realistic-ai/evaluation.json`，记录订单合法性、实际发雷、友舰碰撞、误雷友舰、紧急停车、T 头改善、编队配合与确定性回放结果；这些是行为检查，不是官方胜率。

### 本轮继续：想定约束适配与独立验证（2026-10-11）

航速候选、精确路径、预览、编队共同航速和自主撤退现在通过同一引擎接口考虑萨沃岛未警戒直航及每回合提速上限。协同规划不再因初始提案无效而忽略其他合法路线；修复也适用于旧 AI，未改旧风格参数。己方整队不能炮击时先机动掩护，不以本回合无法执行的炮击火力鼓励接敌。

原页复核发现圣乔治角三艘必达增援被旧流程漏掉：现在按 IBS-S-05-R4 在第二回合入场计划前公开可用，正常提交三舰入场，不掷模拟成功骰。新旧双方使用同一修复后引擎；旧 S-05 报告仅反映修复前漏入场版本，不可当作原版全舰阵容结果。库拉湾“始终相邻”的逐脉冲含义、距离及受损撤退边界仍为 IBS-Q-022，概率增援阶段时序为 IBS-Q-023，未猜测或放宽。

开发种子 2401–2406 不计强度。另冻结三个问题想定各 30 个全新种子（S-02:3001–3030、S-05:3101–3130、S-10:3201–3230），沿原登记固定弱方，强方始终旧 balanced；新旧参数、72 个输入哈希与逐局 journal 一致。180 次尝试中 168 局合法终局/回放一致、80 个有效对；12 局库拉湾失败使 10 对整对排除。对本轮预注册的三个想定作 Holm 校正，不与旧 12 项报告合并。

| 固定弱方 | 旧 balanced 胜/负/平 | 新协同 胜/负/平 | 有效对 | 结论 |
|---|---:|---:|---:|---|
| 库拉湾 / 同盟 | 7/13/0 | 8/12/0 | 20 | 10 对无效，未验收 |
| 圣乔治角 / 轴心 | 5/7/18 | 4/12/14 | 30 | 未改善；得分率 46.7%→36.7% |
| 萨沃岛 / 同盟 | 12/18/0 | 26/4/0 | 30 | 胜率 40%→86.7%，Holm p=0.000183，显著改善 |

六种多编队自定义部署 ×5 新种子（3301–3305）×双方换边的另 60 局，对旧 adaptive 为 42 胜18负、70%；30 对中15正向、3负向、12中性，单侧配对符号检验 p=0.003769，达到预设门槛。各部署新方胜局分别7/5/7/5/9/9，不宣称每种部署单独显著。60 局全合法/回放一致，发雷1809次、友舰碰撞伤害和误雷友舰均0，仍有82舰次紧急停车；三个问题想定的168个合法局共发雷660次、上述友伤均0，紧急停车749舰次。

证据分别为 `constraint-holdout-180.json/.jsonl`、`constraint-fleet-holdout-60.json`；旧失败36局复测为31局合法终局/回放一致，其中萨沃岛19/19全修复，库拉湾12/17成功、5局仍因无合法撤退阻断（`constraint-former-failures-first.json`，这是开发排障，不是强度样本）。不宣称全部弱势想定已改善，也不将修复前后样本合并。

```powershell
# 必须使用新的输出文件名；历史证据禁止覆盖。
python scripts/benchmark_ai_constraints.py --mode holdout --pairs 30 --workers 8 --output artifacts/realistic-ai/constraint-new-run.json
python scripts/benchmark_ai_constraints.py --mode former-failures --workers 8 --output artifacts/realistic-ai/constraint-failure-new-run.json
```

### 强度评测：完整对局与双方换边

新版协同机动按局部战区选敌与搭档，整支纵队评估炮位射界、公开敌舰直航假设和己方航速下的受击风险；无公开部署区的自定义剧本按地图几何搜索，不读取隐藏敌舰。炮击采用引擎现有的舰队级目标分配。旧风格保留独立选靶与原有战术参数；共同的撤退、鱼雷及火力缓存优化另有逐项等价测试，受损编队恢复仅在原订单不合法时执行。

```powershell
# 调参集：不同于正式验证的部署与随机种子
python scripts/benchmark_realistic_strength.py --suite dev --workers 4 --output artifacts/realistic-ai/strength-dev.json
# 独立验证：6 个自定义部署 × 5 种子 × 双方换边 = 60 局
python scripts/benchmark_realistic_strength.py --suite holdout --workers 4 --output artifacts/realistic-ai/strength-holdout.json
# 历史想定及二马、91 舰午夜决战，完整运行到结束
python scripts/benchmark_realistic_strength.py --suite historical --seeds 19 --workers 4 --output artifacts/realistic-ai/strength-historical.json
# 直接读取本机自定义剧本定义，在隔离引擎中测试；数据库仅只读
python scripts/benchmark_realistic_strength.py --suite custom --custom-db backend/iron-bottom-sound.sqlite3 --custom-ids IBS-CUSTOM-21E8908FE969 IBS-CUSTOM-BIG-GRAND --seeds 211 223 227 229 233 239 241 251 257 263 --minimum-pairs 20 --workers 4 --progress --output artifacts/realistic-ai/strength-grand.json
```

最后一条的剧本 ID 须换成自己工坊中的实际 ID；两份剧本 × 10 种子可组成 20 个换边对，需在运行前明确指定 `--minimum-pairs 20`。默认门槛为至少 30 个完整换边对、胜 1 平 0.5 的平均得分 ≥60%、换边对单侧精确符号检验 p<0.05。按每个相同想定/种子的双方换边对检验，天然强势阵营双方各赢一局只计中性，不能冒充 AI 优势。非法、崩溃、未完赛或回放不一致会剔除整个对并使验收失败，不计作胜利。不同风格、旧对手与测试集分别报告，不混为一个胜率。

报告包含自定义定义、参数、源代码哈希、分想定胜负、真实鱼雷发射、友伤与失败原因；工作进程启动时检查代码版本，测试期间不要修改 AI 源码。穿甲表未覆盖的 >25 格射击不纳入本轮自动测试；当前生成场景能见度 ≤20、无雷达，详见规则开放问题 IBS-Q-021。

已知兼容边界：库拉湾 IBS-S-02 种子 19 的同盟方仍可因受损自主撤退与 IBS-S-02-R3（DD 必须保持与 CL 的邻接）冲突被订单校验拒绝；此换边对无效，不能作为优势证据，也没有通过删掉想定特例来绕过。真实模式共享避碰修复对新旧双方均生效；重叠冲突组按稳定顺序处理，已经停车的船不应使另一组中的友舰漏停。局部路线候选保留完整成员及原脱队决策，阶段内仅复用引擎生成的自主撤退命令，并以完整批次校验兜底。

2026-10-11 冻结 v5 版本，推荐「协同舰队」的完整换边结果（其他四种风格不能沿用此胜率）：

| 对照 | 完整局数 | 新 AI 胜 / 负 / 平 | 胜计 1、平计 0.5 的得分率 | 换边对单侧 p | 记录 |
|---|---:|---:|---:|---:|---|
| 两份本机 111 舰、30 回合自定义剧本，对旧 adaptive | 40 | 32 / 8 / 0 | 80.00% | 0.000916 | `artifacts/realistic-ai/strength-v5-grand.json` |
| 旧 adaptive，6 种多编队部署 | 60 | 50 / 10 / 0 | 83.33% | 0.000000954 | `artifacts/realistic-ai/strength-v5-holdout.json` |
| 旧 balanced，相同 6 种部署 | 60 | 42 / 18 / 0 | 70.00% | 0.000916 | `artifacts/realistic-ai/strength-v5-balanced-60.json` |
| 旧 brawl，相同 6 种部署 | 60 | 38 / 21 / 1 | 64.17% | 0.024521 | `artifacts/realistic-ai/strength-v5-brawl-60.json` |

三组通用对照均无无效对局，全部确定性回放一致；adaptive 是预设主要对照，balanced / brawl 为次要验证，后两者 p 未作多重检验校正，不能推出对所有旧风格、所有想定都更强。主要 60 局按随机种子聚合后的五个种子得分也均超过 50%（保守的种子级单侧符号 p=0.03125）；实际发雷 1,810 次、友舰碰撞伤害与误雷友舰均 0，仍有 135 舰次紧急停车。

两份实际大舰队定义均使用本机工坊原数据，不重新平衡战舰数值；库以 SQLite `mode=ro` 读取，比赛在隔离引擎内完成。16 编队普通地图剧本与 92×78 的 14 编队剧本各 **16 胜 4 负 / 20 局**，分层名义 p 分别为 0.015625 与 0.035156；合并 20 换边对的预设验收通过。按十个种子聚合为 8 个正向、2 个中性、0 个负向，保守的种子级符号 p=0.003906。40 局全部合法结束、回放一致，实际发雷 2,970 次、友舰碰撞伤害与误雷友舰均 0；仍有 8,611 舰次紧急停车，不代表拥挤航路下完全不受阻。正式版本源代码哈希、具体定义、胜负与风险细节都保存在报告内；失败及改进中的旧版本报告不与本次结果混算。

其他新风格以种子 157 在 6 部署换边，各 12 局合法结束且回放一致：T 头猎手 9 胜 3 负、雷击双翼 7 胜 5 负、护航屏卫 9 胜 3 负、分进合击 7 胜 5 负。均未达到 30 对与显著性门槛，只是补充检查；原始记录为 `strength-v5-rc_*.json`，不能把这些局混成「全新 AI」的总胜率。16 个内置想定共尝试 32 局，31 局合法结束；S-02 的无效换边对剔除后为 19 胜 6 负 5 平，整组兼容性验收仍不通过（`strength-v5-historical.json`）。

测试存储注意：本轮收尾发现旧 pytest API 夹具只隔离战报，没有隔离 `api.repository`，接口测试会向默认本地库新增测试对局。已改为每个测试使用其临时目录下的 SQLite，并新增真实 `/games` 端点的落库位置回归。联赛脚本始终只读剧本库；旧库中已写入的测试条目没有擅自批量清理，避免误删玩家记录。

### 固定弱势方：是否能救回旧失衡剧本

```powershell
# 12 个预先固定的剧本/弱势方 ×30 新种子 ×2 策略 =720 局尝试
python scripts/benchmark_weak_side.py --workers 10 --output artifacts/realistic-ai/weak-side-new-run.json
```

强势方一直是旧 balanced；弱势方分别使用旧 balanced、新 rc_coordinated，按同剧本/弱势方/开局种子配对。此实验不换边、不修改装备或胜利条件，不读取玩家数据库，也不调整 AI。十个剧本从旧 10 局参考中选择弱方，S-03/FM-01 另按旧日志的一边倒记录纳入；小样本参考只用于事先选方，不能作为真实弱势证据。S-03 当前 YAML 参考已是 6:4，保留用新旧基线复核历史印象。

主指标是引擎裁决的弱方胜率，平局不算胜；另报胜/负/平和胜1平0.5得分率。同种子并不意味着策略分化后每次掷骰还能一一相同。每剧本以「新胜旧不胜」对「旧胜新不胜」做单侧精确配对检验，对预注册全部 12 项作 Holm 校正；至少 30 个有效对、无无效局且校正 p<0.05、胜率增加才标记显著改善。非法、崩溃、回放不一致整对剔除，不能当战败或通过换种子补掉坏样本。尚未完成的报告不能作最终结论；原始逐局记录同步写入同名 `.jsonl`，输出存在时脚本拒绝覆盖。

2026-10-11 旧 v5 冻结版本（修复前历史结果）：**720 次尝试、684 局合法终局且回放一致、333 个有效同种子对**。36 局特例约束异常使 27 对无效，整对排除。AI、裁决和剧本均未调整，71 个冻结输入哈希一致；运行中断时 717 条已完成日志全部保留，仅补跑原登记中缺失的最后 3 局，没有换种子或重跑坏样本。证据：`artifacts/realistic-ai/weak-side-frozen-720.json` / `.jsonl`。

| 剧本 / 固定弱方 | 有效对 | 旧 balanced 胜 / 负 / 平 | 新协同舰队 胜 / 负 / 平 | Holm p | 结论 |
|---|---:|---:|---:|---:|---|
| 埃斯佩兰斯角 S-01 / 轴心 | 30 | 0 / 22 / 8 | 0 / 15 / 15 | 1 | 胜率不变，更多平局 |
| 库拉湾 S-02 / 同盟 | 18 | 2 / 15 / 1 | 8 / 9 / 1 | 0.175781 | 12 对无效，不作显著结论 |
| 通道行动 S-03 / 同盟 | 30 | 9 / 21 / 0 | 19 / 11 / 0 | 0.051758 | 改善大，但校正后未达门槛 |
| 塔萨法隆格 S-04 / 轴心 | 30 | 11 / 19 / 0 | 15 / 14 / 1 | 0.775391 | 未显著 |
| 圣乔治角 S-05 / 轴心 | 30 | 3 / 11 / 16 | 5 / 25 / 0 | 0.775391 | 未显著，得分率反而下降 |
| 第二次瓜达卡纳尔 S-06 / 轴心 | 30 | 9 / 21 / 0 | 17 / 13 / 0 | 0.172119 | 未显著 |
| 萨沃岛 S-10 / 同盟 | 15 | 3 / 12 / 0 | 14 / 1 / 0 | 0.005371 | 15 对无效，不作显著结论 |
| 奥古斯塔皇后湾 S-11 / 轴心 | 30 | 2 / 23 / 5 | 13 / 15 / 2 | 0.005371 | 显著：6.7% → 43.3% |
| 布干维尔 S-12 / 轴心 | 30 | 13 / 14 / 3 | 17 / 9 / 4 | 0.775391 | 未显著 |
| 霍腊纽 S-14 / 轴心 | 30 | 5 / 21 / 4 | 19 / 9 / 2 | 0.003113 | 显著：16.7% → 63.3% |
| 二马 EM-01 / 同盟 | 30 | 1 / 2 / 27 | 8 / 2 / 20 | 0.136719 | 未显著，多数仍是平局 |
| 91 舰午夜决战 FM-01 / 轴心 | 30 | 3 / 26 / 1 | 16 / 14 / 0 | 0.005371 | 显著：10.0% → 53.3% |

三项通过者在更保守的 12 倍 Bonferroni 校正下也均 p<0.006；不能因此宣称所有失衡剧本都能救回。尤其 S-05 虽多赢两局，但平局大幅变为败局，胜1平0.5得分率从 36.7% 降到 16.7%。S-02 的 DD–CL 邻接约束使旧/新分别异常 8/9 局；S-10 的每回合提速约束使旧/新分别异常 7/12 局，完整兼容性均未通过，剩余样本还可能存在选择偏差。以上仅是当前引擎已实现范围内的实测，不是官方胜率或所有想定特例已实现的声明。

## 验证

```powershell
python -m pytest --cov=iron_bottom_sound
python scripts/build_source_manifest.py
python skills/iron-bottom-sound-rules/scripts/build_rule_corpus.py
python skills/iron-bottom-sound-rules/scripts/query_rules.py "炮击"
```

前端生产构建：

```powershell
cd frontend
pnpm run build
```

## 资料与权威

- 想定特例高于舰船记录/玩家辅助表，后者高于通用规则。
- OCR 和全文检索只用于定位；表格与关键图必须回看原始页逐格核验。
- 未核实规则不得进入裁决核心，统一登记到 `docs/rules/open_questions.md`。
- 原始资料可能受版权保护；仓库应保持私有。

## QQ 机器人与 MCP

普通/编队模式、PVE/PVP、群 @ 创建与加入、私聊阶段命令、群公共图/双方受限视角图，以及两个 MCP agent 共用对局的配置见 [QQ / MCP 文档](docs/bot/README.md)。启动共享服务：

```sh
python -m pip install -e '.[bot]'
python -m uvicorn iron_bottom_sound.bot.app:create_app --factory --host 127.0.0.1 --port 3192 --env-file .env --workers 1
```
