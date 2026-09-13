# B0 审计 3/6：鱼雷时间语义（torpedo_time_semantics.md）

审计对象：`research/torpedo_denial/`（E04 完整协议）、
`research/experiments/e04_min_denial.py`（交叉检查）、
`research/experiments/e04c_salvo_sweep.py`。

## v4 B0 必查 6：torpedo 是否只做 spatial route overlap？

**完整协议（E04 主结果）：否——时空语义正确。**
- 每条航迹有解析 (turn, impulse) 时间线，镜像引擎脉冲环（船先动、雷后动、
  逐 impulse 同格接触、跨回合 allowance = cycle[(t−发射回合)%3]）；
- 接触判定是 (hex, impulse) 同格；且已与引擎真实裁决的
  `traversed_hexes` 前缀逐格核对（results.json: lane_model_verification.match=true）。
- Hazard 概率来自 `engine.torpedo_hit_probability(aspect, modifier)`，在接触
  几何处由引擎函数计算。

**交叉检查协议（E04-min）：部分时空。** 用路线逐脉冲格 + 直航延拓至拦截
回合的接近度近似；无解析脉冲环。定位：稳健性旁证，不作为主证据。

## v4 B0 必查 7：V_direct 是否用 post-best-response direct value？

**主协议：direct value 在 τ0*（无威胁基线）航路上计算**——即 pre-response
direct value。审计结论：这是故意的分解选择（直接价值定义在"威胁不存在时
目标会走的航线"上，剥离剥夺分量），但 v4 语义下应补充 post-response 变体：
威胁后目标走 τT*，直接命中应沿 τT* 评估（通常更低——目标已经避开）。
**处置：B10/B11 中同时报告 V_direct(τ0*) 与 V_direct(τT*)**；前者是威胁的
"标称杀伤"，后者是"实际可达杀伤"。当前论文只报前者，需在 v4 论文中补注。

## 其余审计点
- 鱼雷动力学：解析投影 + 引擎核对 ✓（B10.2 的六要素中，launch time/
  position/direction/speed/future-by-pulse/expiration 全有；概率/期望毁伤
  来自引擎表）✓
- B10.3 时空危险 H(x,t)：解析时间线支持"同一位置不同时间不同威胁" ✓
  （已由 lane_model_verification 证明时间轴正确）

## B0 Gate 判定
时空语义正确、模型核对过。**PASS**。B10/B11 在此之上做状态扩展 z=(s,q)
与响应集收缩计数即可，无需推倒。
