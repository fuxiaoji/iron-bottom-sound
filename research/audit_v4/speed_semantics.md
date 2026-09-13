# B0 审计 2/6：速度语义（speed_semantics.md）

审计对象：`committed_game.simulate(speedB = speed0B * vB / 6.0)`、
`e02_crossing_t_phase.py (vB = 6.0 * eta_v)`、
`geometry_policy (vB = ship.current_speed)`、
`differential_game（定速巡航近似）`。

## v4 B0 必查 4：speed ratio 是哪种语义？

**结论：现有全部 E02/E06 实验测的是 FIXED OPERATING SPEED（固定运行速度），
不是 max-speed capability。**

证据链：
1. `simulate` 中速度是常量参数：`speedB` 每步恒定，方案库只含航向指令，
   没有变速动作；
2. ηv 扫描改变的是该常量的数值（`vB = 6.0 * eta_v`），同时作用于平移速度
   与（作为目标航速修正传给核的）`speed0R` 参数位置——但开火目标航速实际
   传的是 `speed0R`（常量 6），即**射击命中修正不随 ηv 变化**（引擎对
   v≥4 的目标航速修正本来就为 0，语义一致）；
3. 转向模型与速度解耦：`hB += planB[t]` 不依赖 v（无 R_min(v) 耦合）——
   B5 的 realistic coupling 未建模；
4. 没有"增大 max speed 扩大控制集合"的嵌套结构（B4.1 的
   U(v̄1)⊆U(v̄2) 检验在此模型上无直接对应物）。

## 对已有结论的强制重分类（v4 B4.2）

| 旧结论（v3 论文） | v4 重分类 |
|---|---|
| "速度悖论：等射程下更快承诺方更差"（§5.4 发现 3、摘要、贡献 3） | **operating-speed effect**（运行速度效应）：在固定运行速度语义下成立。不得表述为 speed-capability effect |
| "速度通过可达战术集起作用" | 保留，但"可达集"指航向-时序可达性，非速度能力集 |

## B4 的正确打开方式（本周夜执行计划）
1. **B4.1 嵌套能力检验**：把速度做成能力参数 v̄（可选速度集
   {0..v̄}，方案含变速段），检验 U(v̄1)⊆U(v̄2) 下
   V(v̄2)≥V(v̄1) 是否数值成立；若出现下降，先查方案库/优化器/
   speed-turn 耦合，再谈语义。
2. **B4.2 固定运行速度**：现有结果重新标注为 operating-speed effect
   （机制：更早接敌+互火包线内更长通过+无位置项可兑现）。
3. **B5 耦合**：加入转向脉冲消耗推进（引擎真实语义：60° 转向脉冲不
   前进）后再测速度效应——这是引擎真实语义，当前代理缺失（B0 发现
   的第二处代理-引擎偏差）。

## B0 Gate 判定
速度语义**定义清楚但语义归类错误**（capability vs operating 混用）。
v3 论文速度结论必须 RENAME。**PASS（有条件）**：B4 按上述两条路线执行。
