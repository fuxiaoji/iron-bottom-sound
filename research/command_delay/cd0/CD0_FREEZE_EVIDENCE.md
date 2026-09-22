# CD-0 冻结证据 · Command Delay Mode v2.2

## 1. 冻结对象与基线

| 项 | 值 |
|---|---|
| 冻结 tag | `realistic-command-v1-frozen` |
| 冻结 commit | `d432a975151651fa7d6746b2f92e66b1e09d8d4a`（该分支 HEAD） |
| 冻结文件面 | `backend/src/iron_bottom_sound/realistic_command.py`（IBS-R-RC-01…07）、`models.py` 的 `GameOptions.realistic_command` 语义、`Phase.FORMATION_SETUP` 流程 |
| 基线 harness | `research/command_delay/golden_replay.py` |
| 基线数据 | `research/command_delay/golden/*.json`（7 行矩阵）+ `GOLDEN_INDEX.json` |
| 基线构建日志 | `logs/cd0_golden_build.log` |
| 回归验证日志 | `logs/cd0_golden_check.log`（修复前）、`logs/cd0_golden_check_postfix.log`（修复后） |
| 哈希种子探针 | `logs/cd0_hash_seed_probe.log`（修复前）、`logs/cd0_hash_seed_probe_postfix.log`（修复后） |
| 探针 JSON | `audits/cd0_hash_seed_probe.json` |

基线矩阵（双向均为确定性状态机 AI，故整局是 `(想定, seed, options)` 的纯函数）：

| tag | 想定 | seed | 模式 | 事件数 |
|---|---|---|---|---|
| classic_s01 | IBS-S-01 | 20270830 | Classic | 586 |
| classic_s03 | IBS-S-03 | 3 | Classic | 213 |
| classic_em01 | IBS-S-EM-01 | 20270829 | Classic | 774 |
| realistic_s01 | IBS-S-01 | 20270830 | Realistic | 486 |
| realistic_s03 | IBS-S-03 | 3 | Realistic | 268 |
| realistic_em01 | IBS-S-EM-01 | 20270829 | Realistic | 1545 |
| realistic_s03_seed9 | IBS-S-03 | 9 | Realistic | 212 |

七行全部 `passed=True`（终局合法、无友军碰撞、无友军鱼雷命中）。

## 2. 冻结三面

每行记录三个互相独立的可观测面，任何一个漂移都判 FAIL：

1. `events` —— 裁决事件流（turn / phase / type / payload）。移动、炮击、损伤、指挥链任一裁决变化都会在此显现。
2. `orders` —— 每个 (turn, phase, side) 已封存订单批次的完整 JSON。即使某次改动恰好没改变骰点，只要**规划器**（编队展开、后舰航迹、脱队判定）变了也会被抓到。
3. `ships` / `formations` —— 终局逐舰 position/heading/hull/sunk/speed/command_status/formation_id 与编队指挥链。

`game_id` 每次 `Engine.reset` 都是新 UUID 且被 `game_created` 事件记录，因此在录制前做掩码（`<GAME_ID>`），否则任何基线都不可能复现。

## 3. 冻结投影比较法（为什么不是朴素字节 diff）

新增可选字段会改变 `model_dump(mode="json")` 的文本（例如 `GameOptions` 多一个布尔量，就会出现在每个 `game_created` 载荷里）。若用朴素字节 diff，这类**纯信封增长**会被误报成语义漂移；反之若放宽比较，又会漏掉真正的语义变化。

因此比较分两问：

- **冻结语义是否变化？** 由 `project(actual, frozen)` 回答：递归、逐元素、成对投影，只忽略**冻结时不存在的 dict 键**，列表长度必须相等，已存在键的值必须完全一致。因此嵌套载荷内部的变化无法被隐藏——被丢掉的只能是新键，绝不可能是旧键的新值。
- **数据模型是否增长？** 单独报告为 `envelope_keys_added` 路径集合，写入 `DATA_MODEL_DIFF.md` 供审查。

## 4. CD0-F1：冻结面上发现的既有非确定性缺陷

### 4.1 现象

基线首次构建时 `realistic_s01` 在不同 `PYTHONHASHSEED` 下产出两个不同的 trees 摘要：

```
realistic_s01  HS=0 → 917114fbb1dd
realistic_s01  HS=1 → 10679a78338d
realistic_s01  HS=2 → 10679a78338d
realistic_s01  HS=8 → 10679a78338d
```

其余 6 行在 HS∈{0,1,2,8} 下全部稳定；Classic 三行全部稳定。

### 4.2 定位

对 HS=0 与 HS=1 的两棵树做逐叶 diff，全文差异**只有 12 条**，全部形如：

```
events[352].payload.ship_ids[0]   HS0="IBS-U-USN-BUCHANAN"  HS1="IBS-U-USN-HELENA"
events[353].payload.ship_ids[0]   HS0="IBS-U-USN-HELENA"    HS1="IBS-U-USN-BUCHANAN"
```

即 `formation_emergency_stop`（真实模式：友舰航路解冲突）的两条事件**互换顺序**，涉及的两组舰集合完全相同，且 `ships` / `orders` / `rng_counter` / `n_events` 全部一致。

根因：`engine.py:3124` 以原生顺序遍历 `collision_sets`（`set[frozenset[str]]`），字符串哈希随机化即改变遍历顺序，进而改变事件发射顺序。

### 4.3 性质判定：这是**修复**，不是语义变更

同一函数内、同一变量的另一处循环（`engine.py:3144`，骰点友军碰撞路径）**已经**用 `sorted(collision_sets, key=lambda group: sorted(group))` 修过同类缺陷，仓库内还有专门的测试 `tests/test_tactical_ai.py::test_collision_resolution_is_deterministic_across_hash_seeds` 记录该 bug 的原始症状（"同 seed 跨进程战果分叉"）。也就是说：**哈希种子无关性是本仓库已经明文声明的契约**，而 3124 行是该契约的漏改孪生分支。命令延迟模式的验收标准第 10 条（每个消息事件与本地 agent 决策可复现/可审计）也要求它必须被修掉。

### 4.4 修复与验证

修复：`engine.py:3124` 改为与 3144 行同一规范排序键。

```
-                for collision_set in collision_sets:
+                for collision_set in sorted(collision_sets, key=lambda group: sorted(group)):
```

修复后：

| 检验 | 结果 |
|---|---|
| HS∈{0,1,2,8} 稳定性 | **PASS**，0 行不稳定（`logs/cd0_hash_seed_probe_postfix.log`） |
| `realistic_s01` 摘要 | `917114fbb1dd` —— **与修复前冻结基线逐字节相同** |
| 全部 7 行 golden 回归 | **PASS**（`logs/cd0_golden_check_postfix.log`） |
| 信封新增键 | 0（`envelope keys added: 0`，见 CD-0 结束时的工作树） |

**结论：修复改变了 0 个冻结值。** 规范排序键恰好与修复前代码在固定种子下产生的顺序一致，因此该行基线无需重建，冻结tag所指的语义与当前工作树完全一致，同时缺陷被永久消除。

## 5. 既有测试基线（修复前，冻结 commit + 仅新增 research 文件）

`logs/cd0_pytest_baseline.log`：3 项失败，全部为**既有失败**，与本次改动无关：

| 失败项 | 性质 | 说明 |
|---|---|---|
| `test_tactical_ai.py::test_collision_resolution_is_deterministic_across_hash_seeds` | **测试夹具缺陷** | 用 `sys.executable -c` 起子进程，未传 `PYTHONPATH=backend/src`，子进程 `ModuleNotFoundError: No module named 'iron_bottom_sound'` → 断言 `returncode == 0` 失败。测试从未真正跑到比较阶段 |
| `test_tactical_ai.py::test_ai_orders_deterministic_across_hash_seeds` | **测试夹具缺陷** | 同上，同一 `outcome()` 模式 |
| `test_api_llm_storage.py::test_tutorial_api_reaches_second_turn_and_serves_canonical_counter` | **素材哈希不符** | `/assets/counters/德国-DD-卡尔加尔斯特.png` 实测 `5c54f8aa…` ≠ 硬编码期望 `918196c7…`。属于素材二进制内容问题，与引擎无关 |

前两项必须在 CD-0 记录，因为它们是本项目"哈希种子无关性"契约**当前无法被自动验证**的原因；本次改用 `golden_replay.py --probe-hash-seeds`（显式传 `PYTHONPATH` 与环境变量）作为该契约的**有效**验证手段，并在 `logs/` 留下两份前后对照日志。该夹具缺陷不属本轮授权范围，未修，留待 PI 裁决（见 `BUG_AND_RERUN_LOG.md` CD0-F2）。

## 6. 待裁决项：编队数量上限 1–4（文档）vs 8（代码）

| 位置 | 陈述 |
|---|---|
| `docs/rules/realistic-command.md` §三 第 1 条（玩家可见规则） | "每方建立**一至四个**编队；每个编队至少两艘舰。" |
| `realistic_command.py:44` | `MAX_FORMATIONS_PER_SIDE = 8`，注释为"用户裁定：编队上限由 4 放开到 8" |
| `realistic_command.py:92-94` | 超出上限时把多余编队并入前一队（自动合并），而非报错 |

即：**代码实现的是用户裁定的 8，玩家规则文档仍写 4**。二者当前不会导致裁决错误（代码路径自洽、测试断言用 `MAX_FORMATIONS_PER_SIDE`），但玩家按文档只能建 4 队，而系统允许 8 队，属文档-实现不一致。

按 §一 授权顺序（想定特例 > 舰船记录/玩家辅助表 > 通用规则），并考虑到 8 是"用户裁定"而非规则推断，**本轮不改动任何一侧**（改代码会动冻结文件；改文档需要知道裁决是否仍然有效）。已在 `DATA_MODEL_DIFF.md` 与最终输出中列为 PI 裁决项 `CD0-Q1`。
