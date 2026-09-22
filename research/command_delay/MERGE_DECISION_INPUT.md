# 分支合并裁决输入（PI）

## 1. 事实：两条分支互不包含

| 分支 | 最新提交 | 日期 | 有什么 |
|---|---|---|---|
| `research/m2-2-compiler-fidelity`（**当前工作分支**） | `173b574b` | 2026-09-22 | 命令延迟模式全部实现（CD-0…CD-10）、真实模式冻结基线、8 项审计 |
| `glm/data-entry-and-briefing`（**未合并**） | `62d03464` | 2026-09-11 | 想定 02–14 + FM-01、`class-cards.yaml`（4114 行）、想定简报弹窗、想定特殊规则、`sim_scenarios.py` |
| `main` / `origin/main` | `fc77a65e` | 2026-09-09 | 两条分支的公共祖先 |

**当前运行平台在 `research/m2-2-compiler-fidelity`**：只有想定 1/3/二马可玩，没有想定简报，没有全部剧本。你的记忆是准确的。

## 2. 实测：合并本身是干净的

在临时工作树 `/tmp/ibs-merge-trial`（分支 `trial/merge-data-entry`，**未触碰你的工作分支**）里已完整合并并提交 `318c942d`：

- 冲突仅 4 处，全部是"两边都在末尾追加"型：`StartScreen.tsx`（他们的「📄 剧本简报」按钮 + 我的三入口选择器，已保留两者）、`style.css`、`havedone.md`、`plan.md`。
- `engine.py` / `models.py` / `realistic_command.py` / `api.py` / `data.py` **全部自动合并**。
- 合并后 16 个想定全部可载入（含虚构的 FM-01）；真实模式覆盖范围由他们的分支扩展到新导入想定。

合并后的测试实测：

| 套件 | 结果 |
|---|---|
| `test_engine.py` | 78 passed |
| `test_scenario_special_rules.py`（他们的新文件） | 18 passed |
| `test_realistic_command.py`（我的冻结面回归） | 35 passed |
| `test_command_delay_movement_style.py` | 23 passed |
| `test_command_delay_mode_shell.py` | 15 passed, 1 skipped（原 1 项失败是我测试里写死了"S-02 不受支持"，合并后该前提失效——已改为从实时集合推导，见 `173b574b`） |

## 3. 关键结论：漂移来自他们的规则，不是来自合并

用 CD-0 冻结基线分别测"他们的分支单独"与"合并后"，漂移行**完全相同**：

| 基线行 | 他们分支单独 | 合并后 |
|---|---|---|
| `classic_s01` | DRIFT（`rng_counter`, `n_events`） | DRIFT |
| `classic_s03` | DRIFT（`rng_counter`） | DRIFT |
| `realistic_s01` | DRIFT（`rng_counter`, `n_events`） | DRIFT |
| `realistic_em01` | DRIFT | DRIFT |
| `classic_em01` / `realistic_s03` / `realistic_s03_seed9` | OK | OK |

即：**合并没有引入任何自己的漂移**；但他们的分支**不是纯数据录入**，它改了裁决：`penetration(..., period=...)`（按时期穿甲）、`_apply_turn_start_scenario_rules`（回合开始特例）、`_weather_blocked`、`_mark_alerted`、`_extra_fire_determination`、`_scenario_movement_violation`。这些会让骰点序列与事件数变化——**经典与真实两个模式的既有行为都变了**。

## 4. 需要你裁决的两项

**Q1｜采用哪条分支作为平台基线？**

- (a) 保持现状：命令延迟在 `research/m2-2-compiler-fidelity`，只有 3 个想定可玩。
- (b) 采用合并分支：16 个想定 + 想定简报 + 命令延迟，但**经典/真实模式的裁决按他们的规则改变**，因此 CD-0 冻结基线中对那 4 行必须**重新冻结**（记录为"由 data-entry 分支的规则变更导致"，并重新跑 8 项审计）。

我倾向 (b)（你要的正是全剧本 + 命令延迟在同一平台），但**重新冻结会改写我此前"0 漂移"的认证含义**，所以这一步需要你确认，不能由我单方面做。

**Q2｜若采用 (b)，是否接受裁决行为变更？** 若你希望"全剧本 + 命令延迟，但经典/真实裁决保持我冻结时的行为"，那就不是合并，而是要逐条审查他们的规则改动并把不想生效的部分回退——这是更大的工作，也需要你指定哪些改动保留。
