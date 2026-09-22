# 01_FREEZE_REGRESSION_AUDIT.md

审计对象：Classic 与既有 Realistic 语义是否在 CD-1…CD-6 全部改动之后**仍未改变**。

## 1. 冻结基线

| 项 | 值 |
|---|---|
| 冻结 tag | `realistic-command-v1-frozen` |
| 冻结 commit | `d432a975151651fa7d6746b2f92e66b1e09d8d4a` |
| harness | `research/command_delay/golden_replay.py` |
| 基线数据 | `research/command_delay/golden/`（7 行 + `GOLDEN_INDEX.json`） |
| 审计记录 | `audits/audit_freeze.json`、`logs/audit_golden_check.log` |
| CD-0 详细证据 | `research/command_delay/cd0/CD0_FREEZE_EVIDENCE.md` |

基线矩阵（双向确定性状态机 AI，整局是 `(想定, seed, options)` 的纯函数）：

| tag | 模式 | 想定 | seed | 事件数 |
|---|---|---|---|---|
| classic_s01 | Classic | IBS-S-01 | 20270830 | 586 |
| classic_s03 | Classic | IBS-S-03 | 3 | 213 |
| classic_em01 | Classic | IBS-S-EM-01 | 20270829 | 774 |
| realistic_s01 | Realistic | IBS-S-01 | 20270830 | 486 |
| realistic_s03 | Realistic | IBS-S-03 | 3 | 268 |
| realistic_em01 | Realistic | IBS-S-EM-01 | 20270829 | 1545 |
| realistic_s03_seed9 | Realistic | IBS-S-03 | 9 | 212 |

## 2. 冻结三面与比较方法

每行冻结三个互相独立的可观测面：事件流（turn/phase/type/payload）、每个 (turn, phase, side) 已封存订单批次、终局逐舰与编队状态。

比较用**冻结投影**而非朴素字节 diff：递归、成对，只忽略冻结时不存在的 dict 键，列表长度必须相等，已存在键的值必须完全一致；新增键单独报告为 `envelope_keys_added`。这样两类问题被分离：

- **冻结语义是否变化** → 由投影回答（值变化、键消失、列表长度或顺序变化都是漂移）；
- **数据模型是否增长** → 单独报告（见 `DATA_MODEL_DIFF.md`）。

`game_id` 每局为新 UUID 且被 `game_created` 记录，录制前掩码为 `<GAME_ID>`，否则任何基线都不可能复现。

## 3. 结果

```
CLASSIC_REGRESSION       = PASS
REALISTIC_FROZEN_DEFAULT = PASS
```

7 行全部 `OK`，**0 漂移**（`audits/audit_freeze.json` → `n_drift: 0`）。每行 `passed=True`（终局合法、无友军碰撞、无友军鱼雷命中）。

## 4. 冻结面被改动的文件（全部为插入）

```
backend/src/iron_bottom_sound/realistic_command.py   +56 / -0
backend/src/iron_bottom_sound/models.py             +297 / -0
```

相对冻结 tag，整个改动集为 `8264 insertions(+), 2 deletions(-)`；两处删除是：

| 删除行 | 文件 | 说明 |
|---|---|---|
| `for collision_set in collision_sets:` | `engine.py` | CD0-F1 确定性修复（改为同一规范排序键）；修复后 7 行摘要**逐字节不变** |
| `elif state.phase == Phase.GUNNERY:` | `engine.py` | 改为 `... and not state.options.command_delay_mode:`，即加闸门；默认路径等价 |

`realistic_command.py` 的 4 处插入（全部受新模式/新样式保护，默认路径不进入）：

| 位置 | 内容 |
|---|---|
| import 段 | 引入 `formation_maneuver` 的三个函数与 `FormationMovementStyle` |
| `expand_movement_orders` | ① `MOVE_TOGETHER`/`REFORM_COLUMN` 的唯一分派；② `FOLLOW_WAKE` 的几何闸门（声明几何非 COLUMN 时要求先 `REFORM_COLUMN`） |
| `after_movement` | 一行 `commit_sealed_style_transitions(engine, state)`；无订单请求时立即返回、不触碰状态 |
| `RealisticCommander.choose_plan` | ① `command_delay_mode` 且 GUNNERY 时只公布目标优先级；② `command_delay_mode` 时领舰方案取自本地代理选择 |

最后一项的默认路径等价性由黄金回放证明：`blocked_reason`、`formation_emergency_stop`、`orders_submitted` 等载荷在所有 7 行都未变化。

## 5. `models.py` 的插入

新增 6 个 StrEnum、13 个模型、6 个既有模型的新字段（详见 `DATA_MODEL_DIFF.md`）。全部字段都有默认值，因此旧存档与旧调用逐位兼容；新增字段是唯一的信封增长来源（4 个叶子键）。
