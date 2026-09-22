# code_patch/

三份补丁，全部相对冻结 tag `realistic-command-v1-frozen`（commit `d432a975151651fa7d6746b2f92e66b1e09d8d4a`）。

| 文件 | 内容 | 规模 |
|---|---|---|
| `frozen_surface_touched.patch` | 被触及的**既有**文件：`models.py`、`realistic_command.py`、`engine.py` | +353 行（`realistic_command.py` 56、`models.py` 297、`engine.py` 41/−2） |
| `command_delay_v2_2_source_and_tests.patch` | 新增引擎模块（`backend/src/iron_bottom_sound/`）、玩家规则（`docs/rules/command-delay.md`）、测试（`tests/test_command_delay_*.py`） | 见文件头 |
| `research_harness.patch` | 研究层 harness：`golden_replay.py`、`run_audits.py`、审计 JSON、日志、CD-0 证据文档（不含 1.9 MB 的基线数据树） | 见文件头 |

应用：

```bash
git checkout realistic-command-v1-frozen
git apply --stat code_patch/frozen_surface_touched.patch
git apply       code_patch/frozen_surface_touched.patch
git apply       code_patch/command_delay_v2_2_source_and_tests.patch
git apply       code_patch/research_harness.patch
```

或直接使用已提交的分支（CD-0…CD-6 七个提交，见 `../COMMITS.md`）。

## 被触及的既有文件（逐处说明）

**`realistic_command.py`（冻结文件，+56 / −0，四处插入，全部受新模式/新样式保护）**

1. import 段：引入 `formation_maneuver` 的三个函数与 `FormationMovementStyle`。
2. `expand_movement_orders`：① `MOVE_TOGETHER` / `REFORM_COLUMN` 的**唯一**分派；② `FOLLOW_WAKE` 的声明几何闸门。
3. `after_movement`：一行 `commit_sealed_style_transitions(engine, state)`；无整队机动订单时立即返回。
4. `RealisticCommander.choose_plan`：① 命令延迟模式下 GUNNERY 只公布目标优先级；② 命令延迟模式下领舰方案取自本地代理。

**`engine.py`（+41 / −2）**

1. `advance()`：一个受 `command_delay_mode` 保护的钩子（`on_phase_advanced`）。
2. `validate_orders()` / `submit_orders()`：命令延迟模式下拒绝原始炮击批次，并由引擎选择器生成炮击。
3. CD0-F1 确定性修复：`collision_set` 遍历改为规范排序键（−1 行 +1 行；修复前后 7 行冻结摘要逐字节不变）。

**`models.py`（+297 / −0）**：纯新增枚举/模型/带默认值字段，见 `../DATA_MODEL_DIFF.md`。
