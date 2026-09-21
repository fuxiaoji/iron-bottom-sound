---
name: m22r-b1e-census
description: M2.2-R/B1E 自然机会普查——L0/L1 双尺度、意图 bug 溯源与修复、MG3-E PASS、MG4 可识别性（graded vs binary）、movement MIXED
metadata:
  type: project
---

分支 `research/m2-2-compiler-fidelity`。预注册 `research/m2_2r/PRE_REGISTRATION_B1E.md`（EXPLORATORY，不覆盖旧 gate；旧 gate 原样保留）。包 `research/m2_2r/M2_2R_B1E_NATURAL_OPPORTUNITY_BUNDLE.zip` sha256 `1ce46fa8…`。

**判定：`B1E_VERDICT = TORPEDO_PARTIAL_OBSERVABILITY`（冻结首命中序）；movement 分支 = MIXED。**

1. **意图 bug = `RESEARCH_COMPILER_BUG`**（调用图证据；production 用引擎 `ship_gun_pressure` 扫描航向，无意图→航向路径）。冻结的 `mg_cases.py` 一字未改，修复在新模块 `REPAIRED_INTENT_BASELINE`（按本舰炮座弧表选航向）。
2. **L0/L1 双尺度**（L1 = `FIRE_SEARCH own − enemy EH`）：pre-fix 意图在两尺度都差于不作为（−0.056 L0 / −11.361 L1）；修复后 **+0.667 L0 但 −5.833 L1** → `MECHANISM_SUCCESS_BUT_NEGATIVE_EXTERNALITY`；**只有 BEAM 双正**（+0.472 / +7.417）。普查同型：intent 臂负外部性率 12.9–16.5%，beam 2.0%，beam 可用战术率 0.694。
3. **MG3-E = PASS**（EM-01 s1 t10，9 vs 12 格，相对 38.9%，两臂皆可执行）；旧 MG3 = `HISTORICAL_PROXY_PASS / EXECUTABLE_GOLD_INVALID`。
4. **MG4-P 的关键教训**：per-route payoff 用二值 D 会让 `R_shared` 在「路线数 > 单动作覆盖」时恒为 1——测的是动作空间覆盖率，不是信念冲突，会造假阳性（M22R-F2）。必须用 graded D（路线自身轨迹被阻断比例）。graded 下 material 4/15 状态跨 2 场景，但**效应量单场景主导**，且**假设 B（观测缺口）未分离**：公开假设集在两个方向移动（0.200 vs 0.500；0.167 vs 0.000）。
5. **当前 AI 的鱼雷臂平均 RouteReduction = 0.000**（6/15 状态开火却零约束）；两个公开臂 ≈0.010；full-state 天花板 0.020–0.316。
6. **普查覆盖有结构缺口**：`damaged` 层为空、`late` 仅 16、配额缺 S-01 −4/S-03 −4（无 `mid` 桶 + 短想定），如实报告不回填。

失败 M22R-F1..F5 见 bundle 的 `FAILURES_AND_COUNTEREXAMPLES.md`。相关：[[m22-compiler-fidelity]] [[m21r21-mechanistic-repair]] [[m21r2-mechanistic-decomposition]]
