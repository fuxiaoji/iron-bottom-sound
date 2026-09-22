# 08_REPLAY_DETERMINISM_AUDIT.md

审计对象：命令延迟模式的所有状态转移、消息、优先级指令与自主动作是否在 seed/profile 下**确定性可复现**（验收 10、12）。

- 审计记录：`audits/audit_replay.json`、`audits/cd0_hash_seed_probe.json`、`audits/audit_freeze.json`
- 测试：六个命令延迟测试文件中各有一项跨 `PYTHONHASHSEED` 的确定性用例

## 1. 整局跨进程确定性

同一个完整命令延迟对局（IBS-S-01 / seed 20270830 / 确定性状态机 AI / 命令延迟模式）在四个不同的 `PYTHONHASHSEED` 下**分别起子进程**运行，对以下全部内容取摘要：

```text
事件流（turn/phase/type/payload，game_id 掩码）
本地代理决策（全部 19 条，含分支、方案、报告动作、调整）
通信台账（每条报文的 kind/medium/status/发出/送达回合）
链路状态与报告回合
终局逐舰（位置/航向/舰体/沉没）
rng_counter 与胜者
```

结果：

```json
{"hash_seeds": ["0","1","2","5"], "unique": 1, "verdict": "PASS"}
```

四个种子得到**同一个** sha256：`148028d10d2291be1aaad55f09852aca0286349bd04d3b1e54227ac4db7f707b`。因为整个局面是 `(想定, seed, options)` 的纯函数（引擎骰点由 `state.seed * 1_000_003 + state.rng_counter` 派生），跨进程一致等价于跨机器一致。

## 2. 分模块的哈希种子无关性

每个阶段都带一项跨种子的确定性测试，覆盖该阶段新增的全部决策面：

| 测试文件 | 断言内容 | 种子 |
|---|---|---|
| `test_command_delay_movement_style.py` | `MOVE_TOGETHER` 展开的逐舰 orders/plans/detach | 0, 1, 7 |
| `test_command_delay_communications.py` | 整局报文台账 + 订单确认 + 链路状态 | 0, 1, 5 |
| `test_command_delay_formation_agent.py` | 整局 agent 决策 + 逐回合炮击批次数 + 链路 | 0, 1, 6 |

加上 CD-0 的 7 行黄金基线（`--probe-hash-seeds 0,1,2,8`）当前为 `all_stable: True`、`n_unstable_rows: 0`。

## 3. CD0-F1：冻结面上发现的既有非确定性

基线首次构建时，`realistic_s01` 行在不同哈希种子下产出两个不同摘要：

```text
realistic_s01  HS=0 → 917114fbb1dd
realistic_s01  HS=1 → 10679a78338d      HS=2 → 10679a78338d      HS=8 → 10679a78338d
```

逐叶 diff 全文只有 12 条差异，全部是 `formation_emergency_stop` 事件 `payload.ship_ids` 的**顺序互换**（涉及的两组舰集合完全相同，`ships`/`orders`/`rng_counter`/`n_events` 一致）。

根因：`engine.py:3124` 以原生顺序遍历 `collision_sets`（`set[frozenset[str]]`），字符串哈希随机化即改变事件发射顺序。

性质判定：同一函数内同一变量的另一处循环（`engine.py:3144`，骰点友军碰撞路径）**已经**用 `sorted(collision_sets, key=lambda group: sorted(group))` 修过同类缺陷，仓库内还有专门的测试记录该 bug 的原始症状。哈希种子无关性是本仓库已明文声明的契约，3124 行是该契约的漏改孪生分支。

修复与验证：用同一规范排序键；修复后 `realistic_s01` 摘要仍为 `917114fbb1dd`，与**修复前**冻结基线逐字节相同——即**修复改变了 0 个冻结值**，同时 7 行全部哈希种子稳定。因此无需重建基线，冻结 tag 所指语义与当前工作树一致。

## 4. CD0-F2：既有确定性测试实际上从未运行

`tests/test_tactical_ai.py` 中的两项哈希种子测试用 `sys.executable -c "..."` 起子进程，但没有传 `PYTHONPATH`，子进程报 `ModuleNotFoundError: No module named 'iron_bottom_sound'`，断言 `returncode == 0` 失败——**比较阶段从未执行**。这就是"项目声称有该契约的自动验证，实际上没有"的原因。

处置：本轮**未修**该夹具（不在本任务授权范围），改用 `golden_replay.py --probe-hash-seeds`（显式传 `PYTHONPATH` 与环境变量）作为该契约的**有效**验证手段，并在 `logs/` 留下修复前后两份对照日志。该项列为 PI 裁决项。

## 5. 新增代码的确定性写法

新模块遵守同一约束：

- `formation_maneuver` 的全部成员遍历用 `formation.ship_ids` 顺序或 `sorted(key=...)`；
- `target_priority` 的候选遍历按 `(ship_id, target_id)` 排序，选择用显式评分键并在并列时以 plan 字符串与标签打破；
- `communications.queue` 的排序键为 `(优先级, 发出回合, 发出阶段序, message_id)`，完全有序；
- `command_delay.refresh_link_status` / `commit_sealed_style_transitions` / `link_summary` 都按排序后的 id 遍历；
- `research_hooks` 的导出按 `(turn, side, formation_id)` 排序。

因此"新功能不得引入哈希顺序依赖"这条约束不仅被测试覆盖，也写进了各模块的代码形态。
