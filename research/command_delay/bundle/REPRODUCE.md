# REPRODUCE.md

从零复跑本轮全部证据。所有命令在 `iron-bottom-sound/` 目录下执行，使用仓库自带 `.venv`。

## 0. 环境

```bash
cd iron-bottom-sound
.venv/bin/python -V        # 3.14.6（本仓库既有解释器）
.venv/bin/python -c "import pydantic, fastapi; print('deps ok')"
```

本阶段**不新增任何 Python 依赖**：新模块只用标准库与 pydantic。`research_hooks.to_numpy()` 按需引入 numpy（已存在），张量本身是普通嵌套列表。

## 1. 冻结基线（必须最先跑）

```bash
# 逐行核对 7 行 golden replay；同时报告信封新增键
.venv/bin/python research/command_delay/golden_replay.py --check

# 冻结面的跨哈希种子稳定性（0 行不稳定才算通过）
.venv/bin/python research/command_delay/golden_replay.py --probe-hash-seeds 0,1,2,8

# 若需从当前工作树重建基线（仅在明确要重新冻结时使用）
# .venv/bin/python research/command_delay/golden_replay.py --build
```

期望：`GOLDEN_REPLAY = PASS`、`HASH_SEED_STABILITY = PASS`。

## 2. 测试

```bash
# 本阶段新增的 108 项
.venv/bin/python -m pytest tests/test_command_delay_*.py -q -p no:warnings

# Realistic 冻结面回归
.venv/bin/python -m pytest tests/test_realistic_command.py tests/test_realistic_rules_preview.py -q

# 全量套件（结果与改动前基线逐条对照）
.venv/bin/python -m pytest -q -p no:warnings
```

## 3. 八项审计（可执行闸门）

```bash
.venv/bin/python research/command_delay/run_audits.py                  # 全部
.venv/bin/python research/command_delay/run_audits.py leakage gunnery  # 单项
```

退出码非零即表示某项 FAIL。审计是**测量**而非复述：它会真的驱动引擎跑完整对局，并在对局进行中采样。产物写入 `research/command_delay/audits/*.json`。

单项含义：

| 名称 | 测什么 |
|---|---|
| `freeze` | 7 行黄金回放 + 冻结文件改动清单 |
| `movement` | `MOVE_TOGETHER` 资格、整队执行、几何、默认路径 |
| `communication` | 媒介表、传播为 0、抽象标注、整局通信台账、无概率定义 |
| `mission_order` | 命令结构、三类分支、自主权次序 |
| `leakage` | 舰队/编队视图作用域（对局中采样 5 个回合）、命令事件 `secret_side` |
| `gunnery` | 权限边界四道闸门、54 条订单合法性复核、回退 |
| `replay` | 一局完整对局在 4 个哈希种子下的摘要一致 |
| `data_model` | 新模型/枚举/字段、信封叶子键 |

## 3b. 实机验证（对局矩阵 / API / 自主性 / 战报）

```bash
.venv/bin/python research/command_delay/verify_live.py
```

四个部分，退出码非零即失败：

1. **完整对局矩阵** —— 3 想定 × 3 seed × {命令延迟, 真实对照} = 18 局，全部要求到达 `COMPLETE`；
2. **HTTP API** —— 用 FastAPI `TestClient` 打完一整局，并逐次断言 `GET /view == engine.observe(side)`、模式门控 409/404、事件不越界；
3. **自主性** —— 完全切断某一个编队的链路（双向含报告），要求该编队仍自主决策、选出合法方案、整局打完；
4. **战报** —— 命令延迟模式下战报管线可用，且中立战报不含任何一方的指挥链。

对应固化测试：`.venv/bin/python -m pytest tests/test_command_delay_live_surface.py -q`

## 4. 手工检查点（不必跑，用于快速确认模式确实存在）

```bash
# 三入口互斥：命令延迟必须显式同时打开真实模式
.venv/bin/python -c "
import sys; sys.path.insert(0,'backend/src')
from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import GameOptions
try:
    IronBottomEngine().reset('IBS-S-03', 3, GameOptions(command_delay_mode=True))
except ValueError as e:
    print('OK fail-closed:', e)
"
```

```bash
# 编队代理不能提交炮击：引擎拒绝原始批次
.venv/bin/python -m pytest tests/test_command_delay_formation_agent.py -q -k gunnery -p no:warnings
```

## 5. 成本与边界

- **零付费 LLM 调用**：`formation_llm.py` 的策略是可注入的可调用对象，测试与审计全部使用 stub 与录播；新模块不 import 任何 provider 或网络库。
- **零模拟器预算消耗**：本阶段不使用 BenchMARL/VMAS 环境（那属于 Phase A 的另一条线）。
- 未开始任何科研实验；未实现 RL/GNN/Transformer。
