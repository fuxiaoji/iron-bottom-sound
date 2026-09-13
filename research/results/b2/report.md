# B2 批次报告：Path-integrated Exposure Objective 验证（v4.0）

按 v4.0 夜间研究批次协议输出 22 项。执行日期：2026-09-10（夜间会话）。

---

## 1. 批次标识

- **批次**：B2 路径积分目标验证（B2.1 Snapshot vs Integral；B2.2 Fleet exposure heat map）
- **输入依赖**：E01 校准火力核（`research/results/e01/kernel_fits.json`，CA 类，ρ=0.9912）；
  `research/geometry/committed_game.py`（11 方案承诺机动库、LP 矩阵博弈解）。
- **代码变更**：仅 `committed_game.py::simulate/open_loop_minimax` 新增 `fire_after_move`
  参数（默认 False，行为逐位不变）；新建 `research/experiments/b2_path_integrated.py`。
  未触碰引擎与 E01 校准。

## 2. 研究问题

- **Q1**：对同一批 candidate trajectories（11×11 方案对 rollout），snapshot 目标
  （终点 L(s_T) 与峰值 max_t L(t)）与 path-integrated 目标 J=Σγ^t L(t) 是否给出
  等价的方案排序与 maximin 选择？
- **Q2**：计划书核心对照——是否存在轨迹 A：max_t L_A > max_t L_B（短暂 T 字头峰值）
  但 ∫L_A < ∫L_B（长期中等优势胜出）？即两类目标是否产生**相反的偏好序**？
- **Q3**：B0 审计发现的开火-机动时序偏移（代理先开火后机动 vs 引擎先机动后开火）
  对积分目标与方案选择有多大影响？
- **Q4**（B2.2）：两舰纵队侧面的暴露密度 F_B(x,t) 是否在纵队中部侧面稳定形成更高密度
  （不预设答案，由剖面数据回答）？

## 3. 假设（预注册）

- **H1**：snapshot 与 integral 排序**不等价**（若 Kendall τ≥0.95 则判"结构性等价"并如实报告）。
- **H2**：A/B 反例在真实方案对 rollout 中存在（若 9 格中均不存在，转合成轨迹搜索）。
- **H3**：snapshot 目标改变 maximin/minimax 方案选择或 LP 混合策略支撑。
- **H4**：纵队中部侧面密度高于两翼端部对应位置，且随队形移动该结构稳定（共动系中不变）。

## 4. 数学定义

- 每步火力差：L(t) = K_B(r,Δ_B,v_R,aspect_R) − K_R(r,Δ_R,v_B,aspect_B)，K 为 E01 核
  （KernelWrap，η_r=η_g=1）。
- **Path-integrated（论文主模型）**：J = Σ_{t=0}^{T−1} γ^t L(t)，γ=0.96，T=40。
- **Snapshot-terminal**：L(s_T) = L(T−1)（终点几何火力差）。
- **Snapshot-peak**：max_t L(t)（T 字头瞬时峰值）。
- 方案排序：B 方案按行最小值（worst case）升序；R 方案按列最大值升序；
  相关性用 Kendall τ / Spearman ρ（121 个 payoff 元素层面 + 11 方案 worst-case 层面）。
- 矩阵博弈：pure maximin = argmax_i min_j M_ij；minimax = argmin_j max_i M_ij；
  混合策略为精确 LP（`solve_matrix_game`），支撑集 = {i: x_i > 1e−9}，支撑重叠用 Jaccard。
- B2.2 暴露场：两舰纵队（舰长 3 格、每舰沿航向 4 段、段为点源、间距 6 格），
  F_B(x,t) = Σ_源 expected_hits(r_s(x), 0, v=4, aspect=broadside)（对速度 4 的中性
  靶侧舷姿态的点目标；r 截断到 [1,24]，与 KernelWrap.fire 完全一致；分扇区向量化，
  与逐点循环精确等价）。剖面去噪：中心滑动平均（k=5），原始值一并输出。

## 5. 实验设计

- **B2.1**：参数格 ηv∈{0.8,1.0,1.25} × 几何∈{head_on, parallel, crossing} = 9 格
  （≥6 达标）。每格对 11×11 方案对 rollout（r0=16，与 E02 基线格一致），同一批
  L(t) 序列分别用三个目标泛函成矩阵；做排序相关、maximin/minimax/LP 支撑对比；
  跨全部 9×121=1089 个 rollout 对搜索 A/B 反例（同格内配对，保证初始几何受控）；
  全部格再以 fire_after_move=True 重跑做时序对照。
- **B2.2**：t=0 静态场热图（0.5 格分辨率，[−28,28]²）；纵队以 1 格/步前进，
  t∈{0,6,12} 三帧（地球系）；共动系平移稳定性对照；三站位横向剖面
  （flank_aft x=−7.5 / center x=−3 / flank_fwd x=+1.5，y∈[0.5,24]）与
  纵向剖面（y=6，x∈[−24,24]），全部三帧、原始+去噪输出 CSV。

## 6. 参数

| 项 | 值 |
|---|---|
| 核 | CA（HELENA→CL），η_r=1.0，η_g=1.0（E02 基线格） |
| ηv | 0.80, 1.00, 1.25（vB=6ηv，vR=6） |
| 几何 | head_on (bearing 0, hB 0, hR 180)；parallel (90, 0, 0)；crossing (45, 0, 180) |
| r0, steps, γ | 16, 40, 0.96 |
| 方案库 | turn0/±30/±60/±90/±120/±180（前 3 回合转向后直航），11 个 |
| B2.2 | 航向 0°（+x），舰长 3 格，4 段/舰，2 舰，间距 6 格，1 格/步，帧 t=0/6/12 |

## 7. 种子与可复现性

全批次**无 RNG**（确定性 rollout、确定性 LP、确定性网格）——种子 = 无/确定性。
A/B 搜索为穷举（同格内 121 选 2 配对）。重跑脚本逐位复现。
环境：Python 3.13 venv，numpy/scipy/matplotlib；import 路径
`PYTHONPATH=backend/src:research/experiments:.`。

## 8. 验收标准（预置门限，先于运行写定）

1. 排名等价门限：任一 cell entry-level Kendall τ ≥ 0.95 → 报告"结构性等价"分支；
2. A/B 反例成立判据：peak_A > peak_B **且** J_A < J_B（ score = min(峰值差, 积分差)
   最大化选取；同格内配对）；
3. maximin 敏感性：报告 changed-cells 比例（无预设方向）；
4. B2.2 结构判据：center 剖面值 > 两翼端部站位（abeam 段），且三帧共动系偏差可忽略；
5. 兼容性判据：`fire_after_move=False` 必须逐位复现修改前参考值
   （REF1 parallel straight/straight = 0.0；REF2 crossing turn+90/straight @4.8kn =
   1.9100269276917112；REF3 crossing minimax value=0，B=turn+90，R=turn+90）。

## 9. 结果 B2.1——方案排名（Table 3 数据）

Entry-level（121 payoff/格，9 格 1089 元素）：

| 目标对 | τ 范围（逐格） | τ 均值 [bootstrap 95% CI, 9 格重采样] | pooled τ | pooled ρ |
|---|---|---|---|---|
| integral vs snapshot_T | 0.320 – 0.616 | 0.476 [0.404, 0.548] | 0.502 | 0.596 |
| integral vs snapshot_peak | 0.140 – 0.577 | 0.365 [0.281, 0.451] | 0.363 | 0.491 |

**没有任何格达到 τ≥0.95（最大 0.616）→ H1 成立：snapshot 与 integral 排序不等价，
"结构性等价"分支不触发。** 逐格明细见 `snapshot_vs_integral.csv`（Table 3）。

Worst-case 方案层面：snapshot_peak 的 B 方案 worst-case 向量在 **9/9 格完全退化**
（11 个方案并列同一值 0.0——初始接触时 L(0)=0，R 总存在惩罚方案使 L(t)≤0 ∀t，
故 max_t L 的 worst case 恒为 0）→ peak 目标在 maximin 意义下**无区分力**，
其 planB worst-case Kendall τ 全部无定义（NaN，如实记录）；"straight"被 argmax
选中的格全部是首索引并列截断的产物。snapshot_T 的 worst-case 向量在 5/9 格退化
（1 个唯一值），其余格 τ∈[0.715, 0.866]。

## 10. 结果 B2.1——maximin / minimax / LP 混合策略

| 对比 | snapshot_T | snapshot_peak |
|---|---|---|
| maximin 方案 B 改变 | 6/9 格 | 7/9 格（且 9/9 格为并列退化，选择无意义） |
| minimax 惩罚方案 R 改变 | 5/9 格 | 7/9 格 |
| LP 支撑集 Jaccard（vs integral） | 均值 0.372（最低 0.00） | 均值 0.290（最低 0.00） |
| 博弈值（integral → snapshot） | 见下 | 见下 |

- integral 博弈值逐格：[+1.025, +1.099, −0.000, −0.000, +0.017, −0.000, −1.388, −1.490, −0.221]
- snapshot_T 替换后：[+0.068, +0.060, +0.068, −0.000, −0.000, −0.000, −0.068, −0.061, −0.068]
- snapshot_peak 替换后：[+0.784, +0.337, +0.323, +0.697, +0.323, −0.000, +0.571, +0.329, +0.247]

结构性发现：**peak 目标的博弈值几乎处处非负**（8/9 格 >0）——峰值目标对劣势方
结构性乐观（忽略持续负暴露），把 −1.49 的劣势格变成 +0.33；snapshot_T 则把
量级压缩到 ±0.07 以内。两类 snapshot 都不能复现 integral 的值结构。

## 11. 结果 B2.1——A/B 核心对照例（真实 rollout 对，9/9 格均存在）

- **格**：crossing，ηv=0.8（fire_after_move=False）。
- **A（高峰值/低积分）**：B 方案 turn+180 vs R 方案 turn+30——t=1 L=−1.386
  （挨首轮），t=2 出现 **L=+2.879 的 T 字头尖峰**（frac_L>0 仅 3%），此后相互
  脱离，L≡0；**max_t L_A = 2.879**，**J_A = 1.323**（折扣后尖峰残值）。
- **B（稳态/高积分）**：B 方案 turn+30 vs R 方案 turn−30——t=4 起 37 步稳定
  L≈+0.2915（frac_L>0 = 93%）；**max_t L_B = 0.2915**，**J_B = 5.024**。
- **偏好序反转**：peak 目标下 A ≻ B（2.879 > 0.292）；integral 目标下 B ≻ A
  （5.024 > 1.323）；score = min(2.588, 3.700) = 2.588。L(t) 时间序列见
  `fig_b2_ab_timeseries.png`（左），数据在 `example_AB.json`。
- 该现象**不是孤例**：9/9 个参数格都存在满足不等式的真实 rollout 对
  （`example_AB.json: n_cells_with_real_pair = 9`），无需合成轨迹回退。
- 机制：peak 目标奖励一次性穿越 T 字头（此后脱离、归零），integral 目标奖励
  长期保持中等火力优势（稳态平行舷侧对射）——正是计划书设想的对照语义。

## 12. 结果——开火时序对照（B0 审计偏差修复）

| 量 | 值（9 格，False vs True 各 1089 对） |
|---|---|
| mean \|ΔJ\|（逐格均值） | 0.071 – 0.104（格均值 0.081） |
| max \|ΔJ\|（单对最大） | 0.282 – 0.794 |
| J 符号翻转比例 | **0/9 格**（1089 对中 0 对变号） |
| maximin 方案 B 因时序改变 | **0/9 格** |

结论：先开火 vs 先机动的一拍时序差对**积分数值**有二阶小量影响（均值约 0.08，
相对博弈值量级 1–1.5 约 5–8%），但在整个参数格上**不改变任何 payoff 符号、
不改变任何 maximin 选择**。B0 审计发现的时序偏差被定量界定为二阶；论文主结论
对开火时序稳健。默认参数保持 False（历史行为逐位复现，见第 8 项 REF 判据——全部通过）。

## 13. 结果 B2.2——纵队暴露密度场与 center/flank 剖面

- **静态场（t=0）**：`fleet_heatmap_t0.png`。场紧贴队形：abeam 方向最热；
  前方（+x，首向）因仅艏向扇面火力而塌缩最快。
- **动态三帧（t=0,6,12）**：`fleet_heatmap_frames.png`。共动系平移稳定性：
  max|ΔF| = 0.0（机器精度），Pearson = 1.000——**场是队形的刚体随动属性**。
- **center vs flank（abeam 脊线 y=6，去噪剖面）**：
  - F(center, x=−3) = **9.175** vs F(flank_aft, x=−7.5) = **7.725** 与
    F(flank_fwd, x=+1.5) = **7.725** → 中部 **+18.8%**；
  - 纵向剖面 argmax 恰在纵队中点 x=−3.0，三帧完全一致；
  - 更近处（y=2）：16.96 vs 13.63（**+24.5%**）；远处（y=12）：3.863 vs 3.866
    （差 <0.1%——远距上纵队退化为点源，中部优势消失）。
- **研究问题回答（Q4）**：**是（在本模型内）**——纵队中部侧面稳定形成更高暴露
  密度；优势随横向距离增大而衰减，在 y≈12 格外消失。剖面原始+去噪数据：
  `flank_profile.csv`（1434 行：3 站位×3 帧 lateral + 3 帧 longitudinal，raw+smooth）。

## 14. 不确定度 / CI

仿真为确定性（无随机种子可重复），频率派 CI 不适用于单格 payoff；
报告的不确定度： (a) 排名相关的 p 值（pooled τ 的 p < 1e−61，见 JSON）；(b) 9 格
重采样的 τ 均值 95% bootstrap CI（第 9 项表）；(c) LP 为精确解（无求解器随机性）。
B2.2 的数值不确定度来自核拟合残差（E01 nMAE 0.057），未在本批二次传播——列入第 22 项限制。

## 15. 收敛性

- 方案库规模：沿用 11 方案库（B8 将做库收敛），本批不重复验证，但 A/B 与退化
  结构均在库内穷举得到，不依赖采样。
- steps=40、γ=0.96 使 J 的截断尾项权重 ≤ 0.96^40 ≈ 0.195；脱离子弹格局中 L≡0
  使截断误差实际为零（第 11 项 A 轨迹 t≥3 全零）。E02 曾以同参数复现边界（E02b
  8/8 bootstrap），本批不改变该设置。

## 16. 失败案例 / 负结果（如实留档）

1. **snapshot_peak 的 maximin 完全退化**（9/9 格）：这不是"peak 目标偏好 straight"，
   而是所有方案并列 worst-case=0，argmax 首索引截断制造了假的"straight 选择"。
   任何基于 peak-worst-case 的方案推荐都无意义。
2. **planB/planR worst-case Kendall τ 大量为 NaN**（常数输入）：真实退化信号，
   非数据缺失；已用 n_unique 列（CSV）与 tie-structure 块（JSON）显式记录。
3. **fire_after_move 未改变任何 maximin 选择**（0/9）——预注册假设 H3 未涉及时序，
   该结果作为"时序偏差无害"的负结果留档（对论文是好消息，如实报告）。
4. 合成轨迹回退未触发（真实对 9/9 格存在）——回退代码保留在脚本中备查。

## 17. 是否支持主张

| 主张 | 判定 |
|---|---|
| 路径积分目标与 snapshot 目标产生实质不同的方案排序（τ≪0.95） | **支持** |
| 存在 peak/integral 偏好反转的真实 A/B 对照例 | **支持**（9/9 格，报告例 score=2.59） |
| snapshot 目标不能复现 integral 的 maximin/博弈值结构 | **支持**（peak 退化且乐观偏置；terminal 压平） |
| 论文采用 path-integrated 是 load-bearing 的建模选择而非无差别细节 | **支持** |
| 纵队中部侧面稳定高暴露（B2.2） | **支持**（模型内；+18.8% @y=6，随队形刚体稳定） |

## 18. 旧结论重分类（KEEP / NARROW / REMOVE / RENAME）

- **KEEP**：E02 全部 minimax/maximin 结论（fire_after_move 对照 0/9 改变，稳健）；
  论文主目标 J=Σγ^t L 保持正式模型。
- **NARROW**：E02 的 fire_adv_fraction 等 L 符号统计——只可作为描述统计，
  不得作为目标泛函引用（本批证明 peak 型目标退化）。
- **RENAME**：B0 审计第 3 条的 TacticalCommander "snapshot 评分者"对照——现在有
  定量支撑：snapshot 评分与积分评分排序相关仅 τ≈0.36–0.50，论文中该基线对比
  应表述为"**评分语义不同**（snapshot vs path-integrated），非单纯策略强弱"。
- **REMOVE**：无（本批未发现需要删除的旧结论）。

## 19. 批次判定

**PASS**。四条研究问题全部得到确定性回答，预注册验收 1–5 全部满足
（门限 1 以"不等价"方向触发并如实报告；门限 2 在 9/9 格成立；门限 5 逐位通过）。
无协议失败，无引擎改动。

## 20. 下一步

- **B3（简并性假设破坏）**：本批的 peak-退化机制（L(0)=0 平台 + 惩罚可压平全部 t）
  直接给出 B3 的破坏手段——引入位置项/终端项后重新检验退化是否消失；
- **B7（承诺时域）**：A 例的尖峰存活仅 1 步，提示承诺时域与目标语义有交互
  （T 短时 peak 与 integral 差异缩小），列入 B7 设计；
- **B8（方案库收敛）**：A/B 在 11 方案库内已出现；库加密后反转幅度（score）是否
  增大可作为库收敛的辅助指标；
- 论文侧：Table 3 直接采用 `snapshot_vs_integral.csv`；A/B 例作 Fig（已有成图）；
  B2.2 部分如进入论文，需先补 BB/DD 核的敏感性（本批仅 CA，见 22 项限制）。

## 21. 原始输出路径

| 文件 | 内容 |
|---|---|
| `research/results/b2/snapshot_vs_integral.json` | 9 格 × 2 时序 × 3 目标矩阵、排序相关、tie 结构、LP 支撑、汇总块 |
| `research/results/b2/snapshot_vs_integral.csv` | **Table 3**（18 行 × 20 列） |
| `research/results/b2/example_AB.json` | A/B 对照例（格、方案、峰值、积分、L 序列） |
| `research/results/b2/fig_b2_ab_timeseries.png` | A/B L(t) 时间序列 + pooled 排名散点 |
| `research/results/b2/fig_b2_ranking.png` | Table 3 条形图 + 交叉格方案排序对照 |
| `research/results/b2/fleet_heatmap_t0.png` | B2.2 静态暴露场（含站位/剖面线标注） |
| `research/results/b2/fleet_heatmap_frames.png` | t=0/6/12 三帧动态 |
| `research/results/b2/flank_profile.csv` | 剖面数据（lateral/longitudinal × 3 帧 × raw/smooth） |
| `research/results/b2/fleet_heatmap_summary.json` | B2.2 参数、共动稳定性、center/flank 数值 |
| `research/experiments/b2_path_integrated.py` | 可复现脚本（确定性，单文件运行） |

## 22. 协议偏离与自审（审稿人攻击模式）

1. **偏差（轻微）**：计划要求"至少 6 个参数格"，实际跑了 9 个（3×3 全因子）——
   超集，无偏离风险。
2. **限制（声明）**：B2.1 仅用 CA 核对称对决（η_r=η_g=1），与 E02 基线格一致但未
   扫 η_r/η_g；B2.2 仅 CA 核、仅 2 舰、仅 1 个间距（6 格）与 1 个航速（1 格/步）。
   纵队中部高密度是**几何+火力核弧面**的必然（多源叠加），换核类预计定性不变、
   定量会变；敏感性扫描留给后续批次，不在本批 CLAIM 范围。
3. **限制（声明）**：F_B 的目标定义为"速度 4 中性舷侧点靶"，是火力投送密度的
   上界型度量；真实目标朝向会引入位置相关 aspect 修正，不改变"中部更高"的定性
   结构（弧面扇区不随目标朝向改变）。
4. **自审-攻击 1**："A/B 例是挑出来的"——回复：9/9 格均存在真实对（JSON 有计数），
   报告例为 score 最大化确定性选取，非抽样。
5. **自审-攻击 2**："peak 退化是 r0=16 太远的伪影"——回复：L(0)=0 是因为 16 格
   超出有效射程（E02 同款初始条件）；只要初始接触在有效射程外，任何 snapshot-peak
   目标都有此退化。若初始即接敌（r0 小），peak 不再全 0，但 9 格中 crossing@1.0
   的 col-max 仍显示 peak 值域远窄于 integral——该敏感性可作后续单点补测。
6. **自审-攻击 3**："时序结论只在 9 格成立"——接受；已在第 12 项明确范围
   （9 格 × 121 对，0 变号 0 换方案），不外推到全部参数空间。
7. 引擎未改动；`git diff` 层面仅 `committed_game.py` 新增默认参数分支 + 新增
   B2 脚本/结果文件；E01 校准与 e02 结果文件未被触碰。
