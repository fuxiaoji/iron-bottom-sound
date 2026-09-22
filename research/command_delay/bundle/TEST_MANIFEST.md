# TEST_MANIFEST.md

命令延迟模式 v2.2 的测试清单与运行方式。

## 1. 新增测试文件（130 项）

| 文件 | 项数 | 覆盖 |
|---|---|---|
| `tests/test_command_delay_movement_style.py` | 20 | `MOVE_TOGETHER` 七项资格条件逐条、整队执行（同一记号序列、不复制格位）、斜队与 `geometry_kind`、`FOLLOW_WAKE` 拒绝与 `REFORM_COLUMN` 成功/失败、默认路径未变、跨哈希种子确定性 |
| `tests/test_command_delay_mode_shell.py` | 16 | 三入口互斥与 fail-closed、Classic/Realistic 无模式状态、权限表与舰队编队规则、逐阶段 tick、舰队视图精确性、编队视图作用域与禁止键 |
| `tests/test_command_delay_communications.py` | 25 | 传播为 0 与抽象标注、媒介延迟表、距离只选媒介、无概率定义、无来源概率被拒、队列优先级/容量/TTL、任务式命令结构校验、三类分支激活、端到端管线、草拟时刻快照、迟到订单不覆盖、跨哈希种子 |
| `tests/test_command_delay_formation_agent.py` | 18 | 决策模型无炮击字段、结构守卫、引擎拒绝原始炮击、指令只重排合法目标（含炮位一致性与真实翻转）、不可见目标回退、本地权重上界、教条的静默性、代理只在枚举动作内移动、纯函数、本地接触来源、失联分支、记账、端到端、跨哈希种子 |
| `tests/test_command_delay_formation_llm.py` | 16 | 提示词严格等于 §12 清单、不含规则公式、七类拒绝情形、重试、回退并保留审计、逐次尝试记录、录播重放、协议一致性 |
| `tests/test_command_delay_research_hooks.py` | 13 | 张量块宽度对齐 `TENSOR_SPEC`、策略观察无对方舰、`to_numpy` 形状、两种导出的 `POLICY_SAFE` 标记、文件往返、契约未确认不生效、权重不得凭空声明、账本不改决策、序列化往返 |
| `tests/test_command_delay_agents_and_memory.py` | 16 | **CD-10**：每编队独立记忆（有界、只含本地材料、渲染时自旧向新裁剪）、自然语言命令经链路发电并落入收件编队记忆、命令正文即代理所读、编队订单来自代理、ProviderPolicy 的请求与解析（stub 客户端，无网络）、无密钥时如实标注教条、每条决策都有可审记录、agent-log 端点不跨阵营 |
| `tests/test_command_delay_live_surface.py` | 6 | **交付评审补测**：API `/view` 逐次等于 `engine.observe(side)`（整局）、事件端点不返回对方私有事件、中立战报不含指挥链、被搭载编队恒为 DIRECT、`STALE` 即 `LOCAL_AUTONOMY`、链路被切断的编队仍自主打完一局 |

合计 **130** 项，全部 PASS。

## 2. 运行

```bash
cd iron-bottom-sound
.venv/bin/python -m pytest tests/test_command_delay_*.py -q -p no:warnings
```

## 3. 既有测试

```bash
.venv/bin/python -m pytest tests/test_realistic_command.py tests/test_realistic_rules_preview.py -q
# 38 passed —— Realistic 冻结面回归
```

全量套件结果见 `logs/full_pytest.log`，与改动前基线 `logs/cd0_pytest_baseline.log` 逐条对照。

## 4. 冻结与审计的可执行验证

| 命令 | 作用 | 当前结果 |
|---|---|---|
| `.venv/bin/python research/command_delay/golden_replay.py --check` | 7 行冻结回放 + 信封增长报告 | `GOLDEN_REPLAY = PASS`，0 漂移 |
| `... --probe-hash-seeds 0,1,2,8` | 冻结面的哈希种子稳定性 | `HASH_SEED_STABILITY = PASS`，0 行不稳定 |
| `.venv/bin/python research/command_delay/run_audits.py` | 8 项审计（冻结/机动/通信/命令/泄漏/炮击权限/重放/数据模型） | `AUDITS = PASS` |
| `.venv/bin/python research/command_delay/verify_live.py` | 实机验证：18 局完整对局矩阵、HTTP API 全流程、链路切断自主性、战报管线 | `LIVE_VERIFICATION = PASS` |

`run_audits.py` 的退出码非零即表示某项审计 FAIL，因此它同时是 bundle 的完整性闸门。

## 5. 审计产物清单（`audits/`）

| 文件 | 内容 |
|---|---|
| `audit_freeze.json` | 7 行结果、0 漂移、信封新增键、冻结文件改动清单 |
| `audit_movement_style.json` | 几何、共同航速区间、整队订单、不复制格位、越线拒绝、默认样式、`REFORM_COLUMN` 闸门方向 |
| `audit_communication.json` | 媒介抽象表、延迟样本、抽象标注、整局报文台账（状态/媒介/延迟/链路/报告年龄） |
| `audit_mission_order.json` | 结构字段齐备性、校验错误、三类分支、自主权次序、教条常量 |
| `audit_leakage.json` | 5 个采样回合的 10 条舰队视图 + 19 条编队视图、命令事件 `secret_side` 覆盖、Classic/Realistic 载荷检查 |
| `audit_gunnery_authority.json` | 决策字段、结构守卫、引擎拒绝原始炮击、54 条订单合法性复核、回退、本地权重上界 |
| `audit_replay.json` | 四个哈希种子的整局摘要 |
| `audit_data_model.json` | 新模型/枚举/字段、信封叶子键 |
| `cd0_hash_seed_probe.json` | 修复后的跨种子稳定性探针 |

## 6. 本轮未做的事（与测试有关）

- 未修 `tests/test_tactical_ai.py` 的两项夹具缺陷（见 `08_REPLAY_DETERMINISM_AUDIT.md` §4、`BUG_AND_RERUN_LOG.md` CD0-F2）。
- 未对 `test_api_llm_storage.py` 的计数器素材哈希做任何改动（素材问题，与引擎无关）。
- 未为不可玩的想定编造数据来"跑通"模式闸门测试。
