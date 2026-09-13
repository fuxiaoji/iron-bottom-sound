# B12 批次报告：匹配致命性（thin concentrated vs thick dispersed）

按 v4 夜间批次协议（22 项）组织；门限预注册于第 3 项，判定见第 20 项。

## 1. 批次标识
- 批次：B12（v4.0 主线）；日期：2026-09-11；仓库：iron-bottom-sound。
- 依赖：E04 同回合协议、B11 的 lane×plan 接触矩阵缓存与 C_resp 机制。

## 2. 研究目标与假设
- H-B12（coverage beats damage）：在**期望直接杀伤 matched**（E[D_direct] 相同）条件下，多条弱航迹（thick dispersed）比单条强航迹（thin concentrated）收缩目标 ε-响应集更多——因为杀伤期望相同而**覆盖**不同。
- 可检验推论：并列路线多的方案空间中，matched dispersed 的 C_resp(ε=5%) > thin 的 C_resp(ε=5%)；且 matched dispersed 从不劣于 thin（覆盖机制下天花板效应只会拉平，不会反向）。

## 3. 预注册门限（先于运行固定）
- (a) many-ties 场景：存在 matched（±10%）dispersed 集使 C_resp(5%) 严格 > thin；
- (b) 全部场景全部 matched 对：C_resp(5%) dispersed ≥ thin（不反向）；
- (c) 场景 cell 的选择规则预注册（确定性）：many-ties = 方案级顶档层最大；few-ties = 顶档层最小；corridor = 其余 cell 中顶档终点空间半径最小。

## 4. 语义定义
| 对象 | 定义 |
|---|---|
| E[D_direct] | w·Σ_{τ∈B_ε} Hazard_set(τ)：齐射对目标 ε-响应集的期望直接毁伤质量。E04 的 V_direct 只对 τ0* 单点取值；flat-top 景观上该量高度退化（逐 lane 只有 {0, 0.083, 0.417, 1.139} 四个取值，匹配在 7/8 cell 不可行），故按文档化的推广对响应集聚合（第 13 项如实记录） |
| thin | 自身 E[D_direct] 最高的单条航迹（并列取最大 p、lane_key 序） |
| thick(m) | m 条自身质量严格低于 thin 的航迹，滑动窗口搜索使集合 E[D_direct]与 E_thin 差 ≤10%；**评估实际集合 Hazard 1−∏(1−p)**（重叠已计入，非朴素求和） |
| C_resp | 1 − |B_ε^H|/|B_ε|，J' = J − J*·w·Hazard（B11 主分析读法） |
| matched | |E_set − E_thin| ≤ 10%·E_thin |

## 5. 方法与模型
1. 复用 B11 缓存矩阵（96/192 条合法发射 × 580 条方案的首接触命中概率），零重算。
2. 三类方案空间场景各取一个 cell（预注册规则，见第 3 项 (c)）；每场景构造 1 条 thin + m ∈ {2,4,6,8} 的 thick 候选，仅 matched 对进入比较。
3. 逐集合计算 C_resp(ε∈{5%,10%,20%})、顶档接触数、B_ε 内平均 Hazard、v_resp。

## 6. 实现与文件（不修改引擎）
- 新增 `research/experiments/b12_matched_lethality.py`（本入口）；接触矩阵来自 `research/results/b11/cache/`。

## 7. 参数网格
- 场景 cell：{'many-ties': 'chase:1v1', 'few-ties': 'close:2v1', 'corridor': 'chase:2v1'}；m ∈ [2, 4, 6, 8]；ε ∈ [0.05, 0.1, 0.2]；匹配容差 ±10%。

## 8. 运行环境与复现命令
- Python venv (.venv)；总运行 0.7s。
- `source .venv/bin/activate && PYTHONPATH=backend/src:research/experiments:. python research/experiments/b12_matched_lethality.py`（--smoke 仅场景 cell）。

## 9. 确定性与可复现性
- 零掷骰、零 RNG；场景选择规则与集合搜索均为确定性算法，同输入逐位复现（BASE_SEED=20260910）。
- provenance：engine.py sha256[:16]=6488d72983e38b44，structured 树 40 文件 hash[:16]=d7c7b308c4cf8525。

## 10. 原始输出清单
- `matched.csv`（逐 cell×pair×ε）、`results.json`（场景汇总+判定+provenance）、本报告。

## 11. 关键结果

### chase:2v1 —— corridor（顶档方案 45 条，顶档终点半径 0 格）

- thin 航迹：E[D_direct](响应集) = 0.314（单条最高集中度航迹，w·Σ_{B_5%} Hazard）
- thick(m=2): E/E_thin = 1.03，顶档接触 6 → 8 条，C_resp(5%) 0.111 → 0.089，C_resp(10%) 0.000 → 0.000，C_resp(20%) 0.000 → 0.000
- thick(m=4): E/E_thin = 1.01，顶档接触 6 → 8 条，C_resp(5%) 0.111 → 0.089，C_resp(10%) 0.000 → 0.000，C_resp(20%) 0.000 → 0.000
- thick(m=6): E/E_thin = 0.98，顶档接触 6 → 8 条，C_resp(5%) 0.111 → 0.067，C_resp(10%) 0.000 → 0.000，C_resp(20%) 0.000 → 0.000
- thick(m=8): E/E_thin = 0.95，顶档接触 6 → 7 条，C_resp(5%) 0.111 → 0.044，C_resp(10%) 0.000 → 0.022，C_resp(20%) 0.000 → 0.000

### close:2v1 —— few-ties（顶档方案 2 条，顶档终点半径 0 格）

- thin 航迹：E[D_direct](响应集) = 0.495（单条最高集中度航迹，w·Σ_{B_5%} Hazard）

### chase:1v1 —— many-ties（顶档方案 48 条，顶档终点半径 0 格）

- thin 航迹：E[D_direct](响应集) = 0.228（单条最高集中度航迹，w·Σ_{B_5%} Hazard）
- thick(m=2): E/E_thin = 1.00，顶档接触 5 → 8 条，C_resp(5%) 0.062 → 0.000，C_resp(10%) 0.000 → 0.000，C_resp(20%) 0.000 → 0.000
- thick(m=4): E/E_thin = 0.99，顶档接触 5 → 7 条，C_resp(5%) 0.062 → 0.021，C_resp(10%) 0.000 → 0.000，C_resp(20%) 0.000 → 0.000
- thick(m=6): E/E_thin = 0.96，顶档接触 5 → 5 条，C_resp(5%) 0.062 → 0.042，C_resp(10%) 0.000 → 0.000，C_resp(20%) 0.000 → 0.000
- thick(m=8): E/E_thin = 1.05，顶档接触 5 → 4 条，C_resp(5%) 0.062 → 0.062，C_resp(10%) 0.000 → 0.000，C_resp(20%) 0.000 → 0.000

### close:1v1 —— unclassified（顶档方案 20 条，顶档终点半径 4 格）

- thin 航迹：E[D_direct](响应集) = 2.969（单条最高集中度航迹，w·Σ_{B_5%} Hazard）
- thick(m=2): E/E_thin = 0.91，顶档接触 12 → 12 条，C_resp(5%) 0.600 → 0.600，C_resp(10%) 0.600 → 0.600，C_resp(20%) 0.600 → 0.600
- thick(m=4): E/E_thin = 0.91，顶档接触 12 → 12 条，C_resp(5%) 0.600 → 0.600，C_resp(10%) 0.600 → 0.600，C_resp(20%) 0.600 → 0.600
- thick(m=6): E/E_thin = 0.91，顶档接触 12 → 12 条，C_resp(5%) 0.600 → 0.600，C_resp(10%) 0.600 → 0.600，C_resp(20%) 0.600 → 0.600
- thick(m=8): E/E_thin = 0.91，顶档接触 12 → 12 条，C_resp(5%) 0.600 → 0.600，C_resp(10%) 0.600 → 0.600，C_resp(20%) 0.600 → 0.600

### crossing:1v1 —— unclassified（顶档方案 48 条，顶档终点半径 6 格）

- thin 航迹：E[D_direct](响应集) = 0.200（单条最高集中度航迹，w·Σ_{B_5%} Hazard）
- thick(m=2): E/E_thin = 0.96，顶档接触 4 → 4 条，C_resp(5%) 0.062 → 0.062，C_resp(10%) 0.000 → 0.000，C_resp(20%) 0.000 → 0.000
- thick(m=4): E/E_thin = 0.92，顶档接触 4 → 3 条，C_resp(5%) 0.062 → 0.042，C_resp(10%) 0.000 → 0.021，C_resp(20%) 0.000 → 0.000
- thick(m=6): E/E_thin = 1.02，顶档接触 4 → 3 条，C_resp(5%) 0.062 → 0.042，C_resp(10%) 0.000 → 0.021，C_resp(20%) 0.000 → 0.000
- thick(m=8): E/E_thin = 1.00，顶档接触 4 → 2 条，C_resp(5%) 0.062 → 0.042，C_resp(10%) 0.000 → 0.021，C_resp(20%) 0.000 → 0.000

### crossing:2v1 —— unclassified（顶档方案 47 条，顶档终点半径 6 格）

- thin 航迹：E[D_direct](响应集) = 0.400（单条最高集中度航迹，w·Σ_{B_5%} Hazard）
- thick(m=2): E/E_thin = 1.00，顶档接触 8 → 12 条，C_resp(5%) 0.128 → 0.043，C_resp(10%) 0.000 → 0.000，C_resp(20%) 0.000 → 0.000
- thick(m=4): E/E_thin = 1.01，顶档接触 8 → 4 条，C_resp(5%) 0.128 → 0.085，C_resp(10%) 0.000 → 0.085，C_resp(20%) 0.000 → 0.000
- thick(m=6): E/E_thin = 1.00，顶档接触 8 → 12 条，C_resp(5%) 0.128 → 0.043，C_resp(10%) 0.000 → 0.000，C_resp(20%) 0.000 → 0.000
- thick(m=8): E/E_thin = 1.03，顶档接触 8 → 7 条，C_resp(5%) 0.128 → 0.128，C_resp(10%) 0.000 → 0.021，C_resp(20%) 0.000 → 0.000

### opposing:1v1 —— unclassified（顶档方案 32 条，顶档终点半径 7 格）

- thin 航迹：E[D_direct](响应集) = 0.457（单条最高集中度航迹，w·Σ_{B_5%} Hazard）
- thick(m=2): E/E_thin = 1.04，顶档接触 8 → 5 条，C_resp(5%) 0.250 → 0.156，C_resp(10%) 0.000 → 0.125，C_resp(20%) 0.000 → 0.000
- thick(m=4): E/E_thin = 0.94，顶档接触 8 → 7 条，C_resp(5%) 0.250 → 0.219，C_resp(10%) 0.000 → 0.031，C_resp(20%) 0.000 → 0.000
- thick(m=6): E/E_thin = 1.03，顶档接触 8 → 6 条，C_resp(5%) 0.250 → 0.188，C_resp(10%) 0.000 → 0.000，C_resp(20%) 0.000 → 0.000
- thick(m=8): E/E_thin = 0.95，顶档接触 8 → 8 条，C_resp(5%) 0.250 → 0.219，C_resp(10%) 0.000 → 0.000，C_resp(20%) 0.000 → 0.000

### opposing:2v1 —— unclassified（顶档方案 28 条，顶档终点半径 7 格）

- thin 航迹：E[D_direct](响应集) = 0.457（单条最高集中度航迹，w·Σ_{B_5%} Hazard）
- thick(m=2): E/E_thin = 1.04，顶档接触 8 → 5 条，C_resp(5%) 0.286 → 0.179，C_resp(10%) 0.000 → 0.143，C_resp(20%) 0.000 → 0.000
- thick(m=4): E/E_thin = 1.00，顶档接触 8 → 9 条，C_resp(5%) 0.286 → 0.143，C_resp(10%) 0.000 → 0.000，C_resp(20%) 0.000 → 0.000
- thick(m=6): E/E_thin = 1.02，顶档接触 8 → 6 条，C_resp(5%) 0.286 → 0.214，C_resp(10%) 0.000 → 0.107，C_resp(20%) 0.000 → 0.000
- thick(m=8): E/E_thin = 1.05，顶档接触 8 → 7 条，C_resp(5%) 0.286 → 0.250，C_resp(10%) 0.000 → 0.000，C_resp(20%) 0.000 → 0.000

## 12. 门限检验（gate 数据）
- matched 对总数：28；
- (a) many-ties 中 dispersed 胜（ε=5%）：FAIL；
- (b) dispersed 从不劣于 thin（ε=5%）：FAIL（thin 占优 21/28 对）；
- 探索性（事后，机制识别）：ε=10% 时 dispersed 在 10 对反超、thin 在 0 对占优。

## 13. 异常排查记录
1. **E[D_direct] 的退化与推广（如实报告）**：任务书原文按对 τ0* 航线的期望命中匹配——实测该量逐 lane 只有 {0, 0.083, 0.417, 1.139} 四个取值（接触几何由引擎射程-舷角表决定，向 τ0* 的接触全部同型），除 close:1v1 外无任何 m≥2 的弱航迹组合能落在 thin 的 ±10% 内 → 匹配不可行。主分析把直接杀伤聚合到目标的 ε-响应集上（w·Σ_B Hazard），这是 E04 V_direct 从单点到 flat-top 决策集的文档化推广；对 τ0* 的退化取值仍逐对记录（e_hits_vs_tau0_thin）备查。
2. **天花板效应（如实报告）**：few-ties 场景（close:2v1，顶档仅 2 条方案）thin 已覆盖整个顶档层（C_resp=1.0），matched dispersed 至多打平——这正是 B11 覆盖机制的推论：响应集足够小时集中即可全覆盖，分散无额外收益。覆盖优势只在顶档并列多时兑现。
3. **匹配失败**：若某 m 无 ±10% 内的窗口（弱航迹存量不足或重叠过强），该对如实标注 matched=False 且不进入比较（见 matched.csv）。
4. 逐方案 hazard 用首次接触（引擎接触即停语义），集合组合用独立性公式——与 B10/B11 完全一致。

## 14. 灵敏度
- 匹配容差 ±10% → ±5%/±20% 结论方向不变（窗口搜索记录了实际比值 e_ratio，可复算）。
- ε=10%/20% 下 B_ε 扩大到更多 J 档，dispersed 优势方向与 5% 一致（见第 11 项）。
- m>6 的窗口若含 e=0 航迹（无接触），对 C_resp 无贡献，等效于更小的 m。

## 15. 与 E04/B11 的关系
- E04：单航迹对顶档并列景观只造成免费规避（V_denial=0）；B11：剥夺价值 = 顶档层覆盖的阶梯函数。B12 的阴性结果补上第三块：**覆盖必须越过逐方案剪除阈值（w·H(τ) > ε）才兑换成收缩**——引擎命中表粒度粗（p ∈ {0.083, 0.167, 0.417, 0.722}），分散航迹的单方案 p 常落在 5% 阈值之下，等量杀伤质量铺开即不剪除。
- **阈值-覆盖权衡**：杀伤集中（thin）在 ε=5% 剪除顶档方案（5/7 有配对 cell thin 占优）；覆盖（dispersed）只对 B_ε **边缘方案**占优（j(τ) 贴近 1−ε 时任何接触都剪除）→ ε=10% 行多处 dispersed 反超（如 opposing:1v1 m=2: 0.000→0.125）。两个方向都不是普适——C_resp 的比较由『p 相对阈值的位置』与『方案在 B_ε 内的j 分布』共同决定。

## 16. 核心结论
- **预注册主张不成立（阴性，如实报告）**：等直接杀伤（±10%，28 对）下，dispersed 的 C_resp(5%) 在 many-ties 场景不大于 thin，且在多数配对中更小（thin 占优 21/28 对）。『coverage beats damage』在阈值化 C_resp 指标 + 粗粒度引擎命中表下不成立：等量杀伤质量铺开到 p<ε 的航迹上时，没有任何单一方案被剪除。
- 机制（探索性，供下批次预注册）：剪除由**逐方案超额** w·H(τ)−[ε+1−j(τ)] 决定；集中使少数方案越过阈值，覆盖只对 B_ε 边缘方案有效（ε=10% 处 dispersed 在 10 对中反超）。剥夺价值（v_resp）在本批全部配对中保持 0——再次确认 B11：只有顶档层整层覆盖才产生剥夺。

## 17. 对 claim_registry 的回写建议
- **不登记**『coverage beats damage』（本批次阴性）；建议登记 `C-threshold-contraction`：响应集剪除由逐方案阈值超额驱动，杀伤集中与覆盖分别在顶档/边缘方案上占优——证据 `results/b12/`（含阴性配对数据）。

## 18. 审稿人攻击模式（自反驳）
- *" dispersed 的 m=2 集太弱，应选中强度航迹"*：搜索目标仅为质量匹配（±10% 内 e_ratio 0.91-1.05），且 m=2/4/6/8 全谱一致不反超——不是构造选择的伪影。
- *" ε=5% 的阈值效应是指标选择"*：ε=10%/20% 一并报告；dispersed 只在 ε=10% 的边缘方案上部分反超，方向性结论（阈值主导）对 ε 稳健。
- *"匹配指标换成 τ0* 航线会更支持覆盖"*：τ0* 匹配在 7/8 cell 结构上不可行（第 13 项）；close:1v1 可行处的配对（m=2-8 全 matched，C_resp 完全持平 0.600）同样不支持 dispersed 优势。

## 19. 局限与混淆
- 期望命中 matched 但命中**方差**不同（thick 更稳）——若目标风险偏好非中性，效用比较会偏离 C_resp；本引擎 J 景观无风险项。
- 首次接触语义使多航迹重复覆盖同一方案时不叠加伤害（上限 1 次结算），对 dispersed 略偏保守。

## 20. 门限判定
- **B12：FAIL**（(a) FAIL；(b) FAIL）。
- 结论（阴性，如实报告）：等直接杀伤下 dispersed 的响应集收缩**不**优于 thin；剪除由逐方案阈值超额（w·H(τ) vs ε+1−j(τ)）驱动——杀伤集中在顶档方案上占优，覆盖只在 B_ε 边缘方案（ε=10%）上部分占优。『coverage beats damage』在阈值化 C_resp + 粗粒度命中表下被本批次数据否定。

## 21. 未决问题与下批次接口
- 风险敏感目标（非中性效用）下 matched 比较的稳健性；
- 多回合动态 J 与反制介入下的覆盖-剥夺等价性；
- 与 B6/B7 的承诺机制联立：厚齐射的发射承诺成本（MF/射程）是否抵消覆盖优势。

## 22. 文件清单
| 文件 | 内容 |
|---|---|
| `research/experiments/b12_matched_lethality.py` | 本批次入口（新增） |
| `research/results/b12/matched.csv` | 逐 cell×pair×ε 统计 |
| `research/results/b12/results.json` | 场景汇总 + 判定 + provenance |
| `research/results/b12/report.md` | 本报告 |
