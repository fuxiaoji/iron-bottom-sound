# 基准归档 · IBS-S-01 全配对 1260 局（含乱打 AI）

> 归档日期：2026-08-26。这是乱打 AI 加入后首次全配对基准的**正式归档**，来源 `tmp/bench-s01-r30/`（gitignored，运行临时区），此处为 git 跟踪副本。

## 运行配置

- 场景：`IBS-S-01`（埃斯佩兰斯角海战，7 回合，14 舰，想定一：胜利点差 <4 判平局）
- 局数：**42 对 × 30 局 = 1260**，完成 1260/1260，失败 0
- 参赛者：`balanced, fleet, line, brawl, torpedo, cautious, random`（random = 乱打 AI，全部合法选择均匀随机）
- 并行：workers=8，墙钟 858.5s
- 命令：`python -X utf8 -m iron_bottom_sound.bench --scenario IBS-S-01 --per-pair 30 --workers 8 --out tmp/bench-s01-r30`
- 引擎版本：本次提交（含三类卡死修复，见下）；`backend/src/iron_bottom_sound/bench.py` 可复跑

## 本次运行前的引擎修复（卡死根因，已入 engine.py）

1260 局首次运行 1246/1260 通过、14 局因「无合法机动指令」卡死，全部定位为**双约束互相矛盾**的强制转向死锁，修复后复跑 1260/1260 干净通过：

1. **双约束并存**：`forced_straight_turns` 与 `forced_circle_turns` 同时非零（状态机里 turn 被 straight 杀死、terminal 却要求 turned）→ `_resolve_special_damage` 命中新约束时清空对侧约束。
2. **不可机动 + 强制画圈**：`max_speed==0`（或损伤把速度下限顶过上限，`_legal_speed_range` 空区间）时强制画圈无法满足 → 空区间下限归 0 + 无法机动时允许原地驻留。
3. **贴图死角 + 强制画圈**：舰首朝向图外/陆地无法首进（`_advance_impossible`）→ 画圈门控豁免，允许合法原地驻留。

引擎不变量：**每艘在役舰必须存在 ≥1 条合法机动指令**；强制约束不可满足时失效、允许原地驻留（plan "0"）。

## 关键结论

- **增援**：检定成功恰好符合规格 210/1260（16.7%）；有舰入场 210 局，平均入场 1.24 舰（8 舰全入 120 局）。
- **平局率 47.8%**（602/1260）——想定一胜利点差 <4 即平局，AI 对局大量平局属引擎设定，非故障。
- **盟军总体占优**（决定性对局中盟军 484 vs 轴心 174）；风格合计胜率：brawl 36.7% > balanced 35.0% > torpedo 32.5% > fleet 28.3% > cautious 27.8% > line 20.6%。
- **乱打 AI 是对照组**：合计胜率仅 1.9%，且作为盟军时任意战术风格都能大胜它（如 balanced 24/1/5）——战术 AI 显著优于均匀随机，符合预期。

## 文件

| 文件 | 说明 |
|---|---|
| `bench-report.json` | 全量结构化结果（657KB）：逐对胜负、结局分布、增援统计 |
| `bench-report.md` | 人类可读报告：胜率表 + 组合矩阵 + 增援观察 + 结局分布 |
| `raw-games.jsonl` | 1260 局原始存档（460KB），逐行一局，可复放 |
| `run.log` | 运行进度日志 |

## 复跑

```bash
python -X utf8 -m iron_bottom_sound.bench --scenario IBS-S-01 --per-pair 30 --workers 8 --out tmp/bench-s01-r30
```
