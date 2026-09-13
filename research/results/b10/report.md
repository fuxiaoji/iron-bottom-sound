# B10 批次报告：延迟鱼雷状态模型（z_t=(s_t,q_t) 与 H(x,t)）

按 v4 夜间批次协议（22 项）组织；门限预注册于第 3 项，判定见第 20 项。

## 1. 批次标识
- 批次：B10（v4.0 主线）；日期：2026-09-10/11；仓库：iron-bottom-sound。
- 依赖：E04 协议模块（routes/lane/scenarios/protocol，航迹时间线已与引擎 traversed_hexes 逐格核对）；E04 价值景观阶梯发现（results/e04/）。

## 2. 研究目标与假设
- H-B10（延迟状态场）：鱼雷是 delayed stateful field——过去发射、未来持续存在的时空威胁实体，与舰炮 instantaneous field 范畴不同；形式化为 z_t=(s_t,q_t)，并导出时空危险场 H(x,t)。
- 可检验推论：(a) 同一空间格在不同 impulse 进入时 H 不同；(b) 场的未来部分在发射时刻即被完全确定（无须攻击者后续决策）——瞬时武器机制上不可能。

## 3. 预注册门限（先于运行固定）
- (a) 全部 cell 的热格平均仅在全脉冲的 ≤30% 脉冲上危险（时间依赖的总体证据）；
- (b) 每个 cell 存在 route-based 例证：同一 hex 在 τ0* 接触脉冲 H>0，而另一条（尽量顶档并列的）方案在不同脉冲经过同一 hex 时 H=0；
- (c) 全部 cell 未来回合威胁质量占比 > 0（跨回合持续性）。

## 4. 语义定义
| 对象 | 定义 |
|---|---|
| s_t | 决策时刻 t 的世界快照（引擎 GameState，只读） |
| q_t | 已发射鱼雷航迹集合：每枚记录发射 (turn,impulse)/格/航向、速度周期、射程、齐射量、逐脉冲位置表、removed_at 过期脉冲 |
| H(x,t) | 1−∏k(1−p_k(x,t))，k 为在脉冲 t 占据格 x 的航迹；p_k 由 engine.torpedo_hit_probability 在该航迹接触几何处计算 |
| 参照目标约定 | broadside aspect（对目标最坏）+ 参照目标名义航速 → H 只依赖威胁状态本身；路线级 hazard（B11/B12）仍用逐方案精确 aspect |

## 5. 方法与模型
1. 复用 E04 同回合协议管线（沙箱 → 回合1 → 封存攻击者回合2直航计划 → TORPEDO_PLANNING）；发射机会 = 全部合法 (发射器,舷侧,角度,速度档,发射MF) 组合。
2. 每条合法发射经 build_lane（镜像引擎 impulse 环）展开为 TrackState → q_t；H(x,t) 在 horizon=6 回合的 (hex,turn,impulse) 网格上合成。
3. 时间依赖验证三层：逐 hex 热-脉冲结构统计；最大对比度 hex 的冷/热脉冲例证；route-based 同 hex 异脉冲例证（优先顶档并列方案）。
4. 延迟态量化：跨回合威胁质量占比、发射一回合后仍在水中的航迹占比、航迹寿命脉冲数分布；对照瞬时武器（未来威胁质量恒 0）。

## 6. 实现与文件（不修改引擎）
- 新增 `research/torpedo_denial/hazard_field.py`（TrackState/DelayedTorpedoState/HazardField；供 B11/B12 复用）。
- 兼容性修复：`lane.py::evaluate_contact` 适配引擎新签名 `_torpedo_modifier(state, attacker, target, distance)`（保留旧签名回退，E04 存档数字逐位复现：chase/1v1 tau0=R11 J=5.333 c_denial=0 已核对）。
- 新增 `research/experiments/b_common.py`（共享引导：规则快照纪律 + provenance + setup_cell）与本入口 `research/experiments/b10_hazard_field.py`。

## 7. 参数网格
- 4 几何（opposing/chase/crossing/close）× 2 舰队（1v1/2v1）= 8 cell；引擎管线确定性 → 每 cell 一次测量即可（无抽样，无 RNG）。

## 8. 运行环境与复现命令
- Python venv (.venv)；总运行 3.4s。
- `source .venv/bin/activate && PYTHONPATH=backend/src:research/experiments:. python research/experiments/b10_hazard_field.py`（--smoke 为 2 cell 冒烟）。

## 9. 确定性与可复现性
- 零掷骰、零 RNG；同 cell 重复运行逐位一致。
- provenance：engine.py sha256[:16]=6488d72983e38b44，structured 树 40 文件 hash[:16]=d7c7b308c4cf8525（本仓库存在并发再生产程，运行采用 E04 规则快照纪律隔离）。

## 10. 原始输出清单
- `field_stats.csv`（逐 cell 场统计）、`hex_examples.csv`（冷/热脉冲例证）、`hazard_slices.png`（H(x,t) 切片热图：固定 t 空间切面 + 固定 x 时间切面）、`time_dependence.json`（同格异时定量例证）、`results.json`。

## 11. 关键结果（逐 cell）
| cell | 航迹数 | 热格数 | 热格平均热脉冲 | 未来回合质量占比 | 一回合后存活航迹 | τ0*机会池 |
|---|---|---|---|---|---|---|
| chase:1v1 | 96 | 399 | 2.95 | 0.408 | 96 (100%) | 9 |
| chase:2v1 | 192 | 481 | 4.14 | 0.425 | 192 (100%) | 13 |
| close:1v1 | 96 | 399 | 2.95 | 0.408 | 96 (100%) | 6 |
| close:2v1 | 192 | 481 | 4.14 | 0.425 | 192 (100%) | 9 |
| crossing:1v1 | 96 | 399 | 2.95 | 0.408 | 96 (100%) | 6 |
| crossing:2v1 | 192 | 481 | 4.14 | 0.425 | 192 (100%) | 6 |
| opposing:1v1 | 96 | 399 | 2.95 | 0.408 | 96 (100%) | 5 |
| opposing:2v1 | 192 | 481 | 4.14 | 0.425 | 192 (100%) | 5 |

### 同格异时例证（定量）
- chase:1v1: hex T19 在脉冲 t2.i0 H=1.000，在脉冲 t2.i2 H=0.0
- chase:1v1: τ0* 在 t3.i2 于 T10 接触（路线级 P_hit=0.083，场值 0.160）；方案 `1PP1P1P1P`（顶档并列方案） J/J_ref=1.000 同格不同脉冲 H=0 → 同一空间格的进入时刻决定是否受威胁
- chase:2v1: hex W18 在脉冲 t2.i3 H=1.000，在脉冲 t2.i0 H=0.0
- chase:2v1: τ0* 在 t3.i2 于 T10 接触（路线级 P_hit=0.083，场值 0.230）；方案 `1PP1P1P1P`（顶档并列方案） J/J_ref=1.000 同格不同脉冲 H=0 → 同一空间格的进入时刻决定是否受威胁
- close:1v1: hex T19 在脉冲 t2.i0 H=1.000，在脉冲 t2.i2 H=0.0
- close:1v1: τ0* 在 t2.i2 于 T18 接触（路线级 P_hit=0.722，场值 1.000）；方案 `1P1PP2`（顶档并列方案） J/J_ref=1.000 同格不同脉冲 H=0 → 同一空间格的进入时刻决定是否受威胁
- close:2v1: hex W18 在脉冲 t2.i3 H=1.000，在脉冲 t2.i0 H=0.0
- close:2v1: τ0* 在 t2.i2 于 T17 接触（路线级 P_hit=0.722，场值 0.979）；方案 `1` J/J_ref=0.382 同格不同脉冲 H=0 → 同一空间格的进入时刻决定是否受威胁
- crossing:1v1: hex T19 在脉冲 t2.i0 H=1.000，在脉冲 t2.i2 H=0.0
- crossing:1v1: τ0* 在 t3.i3 于 T10 接触（路线级 P_hit=0.083，场值 0.160）；方案 `1P2P1P1P`（顶档并列方案） J/J_ref=1.000 同格不同脉冲 H=0 → 同一空间格的进入时刻决定是否受威胁
- crossing:2v1: hex W18 在脉冲 t2.i3 H=1.000，在脉冲 t2.i0 H=0.0
- crossing:2v1: τ0* 在 t3.i3 于 T10 接触（路线级 P_hit=0.083，场值 0.160）；方案 `1P2P1P1P`（顶档并列方案） J/J_ref=1.000 同格不同脉冲 H=0 → 同一空间格的进入时刻决定是否受威胁
- opposing:1v1: hex T19 在脉冲 t2.i0 H=1.000，在脉冲 t2.i2 H=0.0
- opposing:1v1: τ0* 在 t3.i1 于 V25 接触（路线级 P_hit=0.083，场值 0.160）；方案 `2S2S1P` J/J_ref=0.250 同格不同脉冲 H=0 → 同一空间格的进入时刻决定是否受威胁
- opposing:2v1: hex W18 在脉冲 t2.i3 H=1.000，在脉冲 t2.i0 H=0.0
- opposing:2v1: τ0* 在 t3.i1 于 V25 接触（路线级 P_hit=0.083，场值 0.160）；方案 `2S2S1P` J/J_ref=0.400 同格不同脉冲 H=0 → 同一空间格的进入时刻决定是否受威胁

## 12. 门限检验（gate 数据）
- (a) 逐 cell 热格平均热脉冲/全脉冲比：0.089, 0.125, 0.089, 0.125, 0.089, 0.125, 0.089, 0.125 → 全部 ≤ 0.30；
- (b) route-based 例证覆盖 8/8 cell；
- (c) 未来回合威胁质量占比范围 [0.408, 0.425]

## 13. 异常排查记录
1. **引擎 API 漂移**：引擎 `_torpedo_modifier` 自 E04 运行后新增 state 参数，protocol 冒烟抛 TypeError。已按研究层兼容修（lane.py 传 state + 旧签名回退），并以 E04 存档逐位复现核对（chase/1v1: tau0=R11, J=5.333, c_denial=0）。
2. **并发规则再生**：本仓库存在并发程再生 resources/derived/structured（场景 YAML 在本批次运行窗口内被改写）。首两轮 probe 出现过 opposing/1v1 τ0* 机会池瞬时为 0 的幻象；隔离复测为 5（与 E04 存档一致），确认为读取了半写入状态。全部批次改用 E04 的等待-快照纪律，provenance 指纹写入 results.json。
3. **场值与路线值差异**：H(x,t) 用 broadside 参照约定，同格的路线级 P_hit （真实 aspect）可低于场值——两者用途不同（场=威胁状态属性；路线=决策属性），例证中同时报告两个数。

## 14. 灵敏度
- 参照航速：modifier 含 target_speed 项，参照目标取 CA 名义航速；对 CA（5 MF）与 DD 直航场景该值为常数，不引入额外自由度。
- horizon=6 回合覆盖全部航迹寿命（射程 10-21 格、速度 5-8/回合），removed_at 前所有脉冲均在网格内。
- **场对几何不变（如实说明）**：H 只依赖威胁状态 q_t（攻击者初始阵位与封存直航计划在全部几何中相同），故 4 几何的场逐位相同（1v1: 96 航迹/399 热格；2v1: 192/481）——这是参照目标约定的直接推论，不是 bug；几何只通过 τ0* 路线进入 route-based 例证（逐 cell 机会池 5-13 条不同）与 B11/B12 的逐方案精确 aspect hazard。

## 15. 与 E04 的关系
- E04 的解析航迹时间线 = 单条航迹的 position-by-pulse；B10 把全体合法发射升格为显式状态 q_t 并合成场，是对 E04『时空航迹』主张（claim C-torpedo-null KEEP+EXTEND）的形式化扩展。
- E04 价值景观阶梯（8 档/顶档 25.5 并列）是 B11 响应集收缩机理的输入。

## 16. 核心结论
- 鱼雷威胁场在 (hex, turn, impulse) 网格上高度局部化：热格只在航迹通过的个别脉冲危险（同格异时 H: p vs 0），空间切片随脉冲移动（threat front），时间切片呈脉冲串——『同一格不同时刻进入』的后果定性不同。
- 延迟态属性量化：各 cell 41-42% 的威胁质量落在发射回合之后的回合，且在发射时即完全确定——这是与瞬时舰炮场的范畴差异（枪炮的未来威胁质量恒为 0，直到开火脉冲）。

## 17. 对 claim_registry 的回写建议
- `C-torpedo-null` 的 KEEP+EXTEND(B10/B11)：本批次交付 B10 部分——建议登记新主张 `C-delayed-stateful-field`：鱼雷发射构成延迟状态场（z_t 形式化 + 时间依赖例证 + 跨回合持续性），证据 `results/b10/`。

## 18. 审稿人攻击模式（自反驳）
- *"时间依赖是航迹模型的平凡推论"*：是——但正是需要逐格核对的平凡性（E04 已对引擎 traversed_hexes 验证）；本批次的科学内容是把『延迟状态』变成可检验的量化命题（门限 a/b/c），并给出 route-based 决策例证。
- *"broadside 参照约定使 H 偏高"*：H 的用途是威胁状态属性对比（同格异脉冲、跨回合质量），B11/B12 的决策量全部用逐方案精确 aspect；两个量在第 13.3 项同时报告、不混用。
- *"场景是人造沙箱"*：与 E04 同一协议同一几何族，机制结论不依赖具体初始条件（4 几何 × 2 舰队全部复现）。

## 19. 局限与混淆
- H 不含目标反制（鱼雷可被拦截/诱偏的规则若启用会压缩 q_t）；本引擎版本无此机制。
- 参照目标约定使场值偏离真实 aspect 命中率（已在第 4/13.3 项声明）。
- 单回合决策 + 直航延拓的响应模型（E04 决策 3） inherited by route 例证。

## 20. 门限判定
- **B10：PASS**（(a) PASS：热脉冲占比全部 ≤0.30；(b) PASS：route 例证 8/8；(c) PASS：未来质量占比 > 0）。
- 结论：torpedo = delayed stateful field 的三重证据（状态形式化 / 时间依赖 / 延迟持续性）成立。

## 21. 未决问题与下批次接口
- B11 直接消费 z_t/Hazard(τ)：响应集收缩 B_ε 与 C_resp；
- 多航迹场的联合分布（饱和/重复覆盖）→ B12 厚度匹配协议；
- 目标反制机制（若引擎未来加入）对 q_t 生命表的修正。

## 22. 文件清单
| 文件 | 内容 |
|---|---|
| `research/torpedo_denial/hazard_field.py` | z_t 状态模型 + H(x,t) 场（新增） |
| `research/experiments/b_common.py` | 共享引导（快照/provenance/setup_cell，新增） |
| `research/experiments/b10_hazard_field.py` | 本批次入口（新增） |
| `research/results/b10/field_stats.csv` | 逐 cell 场统计 |
| `research/results/b10/hex_examples.csv` | 冷/热脉冲例证 |
| `research/results/b10/hazard_slices.png` | H(x,t) 两族切片热图（固定 t 空间 + 固定 x 时间） |
| `research/results/b10/time_dependence.json` | 同格异时定量例证（逐 cell） |
| `research/results/b10/results.json` | 结构化结果 + gate 判定 + provenance |
| `research/results/b10/report.md` | 本报告 |
