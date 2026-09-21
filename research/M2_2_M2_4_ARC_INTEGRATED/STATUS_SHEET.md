# 状态总表（一页版）

## 历史 gate（全部冻结，一处未改）

| 阶段 | 判定 |
|---|---|
| M2.1-R2.1 | `MECHANISTIC_GOLD_GATE = FAIL_3_OF_5` |
| M2.2 | `GOLD_COMPILER_GAP = FAIL / BLOCKED_BY_METRIC_VALIDITY` |
| M2.2-R | `B1E = TORPEDO_PARTIAL_OBSERVABILITY`；movement branch `= MIXED` |
| M2.3 | `JTC = FAIL`、`BARD = FAIL`、`MAINLINE_CANDIDATE = NONE` |

## 机制状态

| 机制 | 状态 | 关键数字 |
|---|---|---|
| MG1 舷射展开 | VALID PASS（规则层），局部可编译 | 同案例：舰队级 −12.17 / 舰对级 +1.89 |
| MG2 抢 T | FAIL（注册臂） | 纵向占比 0.44 < 0.50 |
| MG3 距离控制（旧） | `HISTORICAL_PROXY_PASS / EXECUTABLE_INVALID / SUPERSEDED_BY_MG3E` | 注册 2.56 vs 0.94 @15/17 格，engine-real 0.000 |
| **MG3-E 可执行距离** | **PASS** | 9 格 4.139 vs 12 格 2.528（38.9%），两臂皆可执行 |
| MG4 鱼雷走廊 | VALID PASS | RouteReduction 0.966，引擎接触 29/29 一致 |
| MG5 局部兵力优势 | FAIL（注册臂） | 平台交战尺度下不成立 |

## 本轮最终判定

```
INTERACTION_STRUCTURE = PRESENT      （28% 舰对 |phi| >= 0.05；p90 0.556；max 4.139）
JTC_INTERACTION_GATE  = FAIL         （六条判据全否：6胜/9平/4负，win 0.316，中位 +0.000）
JTC_FINAL_STATUS      = PERMANENTLY_KILL
BARD_FINAL_STATUS     = ARCHIVED
IBS_NEXT_ROLE         = APPLICATION_BENCHMARK_ONLY
```

## 关键对照数字

| 对照 | 数字 |
|---|---|
| 联合 beam vs 逐舰贪心（n=19） | 6 胜 / 9 平 / 4 负；中位 **+0.000**；CI [+0.000, +0.111] |
| 联合 beam vs 逐舰精确坐标上升 | 中位 +0.000；CI **[−0.722, +0.000]**（不占优） |
| 联合 beam vs 等预算随机 | 中位 **−0.083** |
| 逐场景中位 | S-01 0.000 · S-03 **+0.222** · EM-01 **−4.194** |
| BARD 真实集 vs 匹配对照 | material 率 **0.357 → 0.214**（仅 S-01 存留） |
| BARD 公开规划器 vs 天花板 | 0.611 / 0.226 / 0.086；当前 AI **0.000** |
| 当前 AI 鱼雷臂平均 RouteReduction | **0.000**（15 状态，6 个开火） |

## 自查缺陷（详见 README §5）

M22-F2 重复计炮 · M22-F6 图表结论错挂 · M22R-F6 `damaged` 谓词死代码 · M23-F1 对照锚点错位 · M23-F2 跨状态集比较 · M24-F1 主集超集 · M24-F2 状态静默丢弃 · M24-F3 意图标签退化 · M24-F4 交互臂两处 bug。
