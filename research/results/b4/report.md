# B4 批次报告：速度能力单调性（B4.1）+ 固定运行速度效应重分类（B4.2）

按 v4 夜间批次协议（22 项）组织；门限预注册于第 3 项，判定见第 20 项。

## 1. 批次标识
- 批次：B4（v4.0 主线）；日期：2026-09-10；仓库：iron-bottom-sound（main, commit fc77a65 + research/ 未跟踪）。
- 依赖：E01 核校准（`research/results/e01/kernel_fits.json`，CA 舰对，ρ=0.9912）；E02 相图（`research/results/e02/phase_diagram.csv`）；B0 速度语义审计（`research/audit_v4/speed_semantics.md`）。

## 2. 研究目标与假设
- H-B4.1（能力单调性）：把速度做成**能力参数** v̄（可选速度档集 U(v̄)={v∈{2,4,6}: v≤v̄}，嵌套 U(2)⊂U(4)⊂U(6)），开环 maximin 值满足 V(6) ≥ V(4) ≥ V(2)。
- H-B4.2（语义重分类）：v3/E02"速度悖论"是 FIXED OPERATING SPEED 语义的产物，必须 RENAME 为 operating-speed effect，与 B4.1 的 capability 语义并列对照。

## 3. 预注册门限（先于运行固定）
- B4.1 gate：全部 cell 嵌套下**无 V 下降**（容差 1e-8，LP 数值噪声水平）；若出现下降→执行排查协议（a 嵌套审计 b LP 对偶诊断 c 速度强制审计），**不得**称 speed paradox。
- B4.2 gate：e02 数据完整提取且语义标注无误（不重跑，符合批次纪律：确定性协议引用原记录）。

## 4. 语义定义（两套速度语义）
| | capability（B4.1，新） | operating speed（E02，旧） |
|---|---|---|
| 速度是谁选的 | 方案的一部分：plan=(航向序列, 速度档 v) | 实验者：常量参数 vB=6·ηv |
| 可选集 | U(v̄)={2}⊂{2,4}⊂{2,4,6} 嵌套 | 单点 {vB} |
| 能力增大意味着 | 可选速度集扩大（可仍选慢速） | 被迫全程更快 |
| 射击通道 | 与 E02 一致：核的目标航速参数=常量 6（引擎 v≥4 中性） | 同左 |
| 理论预期 | 嵌套行集矩阵博弈值单调不减（极小极大定理） | 无单调性保证（E02 实测递减） |

## 5. 方法与模型
- 方案库 = `make_maneuver_library()`（11 个承诺航向方案，不改）× 速度档 {2,4,6} → 33 个 (航向,速度) 方案；动态由 `committed_game.simulate` 原样执行（40 步，γ=0.96，r0=16）。
- 对每个 (geometry, ηr)：一次性算满 33×33 支付矩阵（对手能力固定 v̄_R=6），V(v̄) 用 `scipy.optimize.linprog`(HiGHS) 在行切片上解 LP；对偶侧独立解第二 LP 检验对偶间隙；记录均衡约束松弛量、支撑速度档、纯 maximin/minimax。
- 嵌套审计：低能力行块必须与高能力矩阵对应行**逐位相等**（simulate 确定性 → 位级可检）。

## 6. 实现与文件（不修改引擎与 committed_game.py）
- 新增 `research/geometry/speed_capability.py`（方案-速度库、嵌套切片 LP、对偶诊断、actual-speed 灵敏度孪生函数）。
- 新增 `research/experiments/b4_speed_monotonicity.py`（本批次入口）。

## 7. 参数网格
- 几何：head_on (bearing 0°, 0°/180°)、parallel (90°, 0°/0°)；ηr ∈ {0.75, 1.0, 1.33}；ηg=1；v̄_B ∈ {2,4,6}，v̄_R=6；步数 40，γ=0.96，r0=16。
- 灵敏度：射击通道改为传递实际目标航速（`simulate_actual_speed`），ηr=1.0，两几何。
- B4.2：引用 E02 的 ηv ∈ {0.8, 1.0, 1.25}（ηr=1.0）全部 3 几何。

## 8. 运行环境与复现命令
- Python 3.13 venv（.venv），numpy/scipy(HiGHS)/matplotlib。总运行 ~25 s。
- `source .venv/bin/activate && PYTHONPATH=backend/src:research/experiments:. python research/experiments/b4_speed_monotonicity.py`

## 9. 确定性与可复现性
- 支付矩阵无随机源；LP 对偶间隙全部 ≤ 4.6e-14；嵌套审计全部 bitexact（18/18 行块）。

## 10. 原始输出清单
- `b41_monotonicity.csv`（18 行 = 6 cell × 3 v̄，全诊断量）
- `b42_operating_speed_e02.csv`（E02 提取 9 行）、`b42_semantics_contrast.csv`（对照表）
- `fig_b41_monotonicity.png`、`fig_b42_semantics_contrast.png`、`results.json`

## 11. B4.1 关键结果（LP 值，行=cell，列=V(2)→V(4)→V(6)，Δ=V(6)−V(2)）
| cell | V(2) | V(4) | V(6) | ΔV 能力收益 |
|---|---|---|---|---|
| head_on ηr=0.75 | −3.1647 | −3.0945 | −3.0622 | **+0.1025** |
| head_on ηr=1.00 | −0.0 | −0.0 | −0.0 | 0（斜对称，见 13.2） |
| head_on ηr=1.33 | +2.9965 | +2.9965 | +2.9965 | 0（射程优势饱和） |
| parallel ηr=0.75 | −2.8523 | −2.8394 | −2.3905 | **+0.4617** |
| parallel ηr=1.00 | −0.5712 | −0.1346 | **+0.0004** | **+0.5716（变号）** |
| parallel ηr=1.33 | +2.6628 | +2.6853 | +2.7654 | +0.1026 |

## 12. 单调性检验（gate）
- 8/8 cell（6 主网格 + 2 灵敏度）单调性在 1e-8 容差内成立；最大单步"下降"= **−2.2e-15**（head_on ηr=1.33，v̄ 2→4，纯 LP 噪声，比容差低 7 个量级）；嵌套位级审计 18/18 通过；对偶间隙 ≤ 4.6e-14。
- 支撑分析：parallel ηr≤1.0 时 v̄=6 的均衡支撑混合多档速度（ηr=1 支撑= {2,4,6}），能力扩张被**真实使用**；ηr=1.33 时支撑只用 {2}（射程优势下机动价值饱和）。

## 13. 异常排查记录（按要求留档）
1. **V_pure 公式错误（已在 gate 评估前捕获）**：首版把 pure maximin 写成 `pay.max(axis=1).min()`（这是最小化侧的量，嵌套下不保证单调，冒烟测试出现 6.16→3.00 的"违反"）。修正为 `pay.min(axis=1).max()` 后单调。教训：嵌套单调性是定理，任何"违反"先查实现——本批次正好演示了该排查协议。
2. **对称 cell 零值**：head_on ηr=1.0 恒 V=−0.0。非 bug：镜像方案（turn+k ↔ turn−k，同速度档）使矩阵在行列置换下斜对称，值精确为 0（对偶间隙 0 证实）。因此 head_on 的能力区分度靠 ηr≠1 cell 提供。
3. **−2.2e-15 级"下降"**：head_on ηr=1.33 v̄2→4。LP 容差级噪声（对偶间隙 1.3e-15~4.6e-14），在预注册容差 1e-8 内，如实记录。
4. **速度强制审计**：方案钉死常速档，但 U(v̄) 恒含 v=2（无"必须用满"结构）；支撑档位（第 12 项）显示 LP 自主选择混合/不混合。

## 14. 灵敏度（射击通道=实际航速，ηr=1.0）
- head_on：−7.1040 → −0.0 → −0.0（单调；慢速档受引擎慢目标易命中修正惩罚，V(2) 大幅下降）
- parallel：−6.3371 → −0.1402 → −0.1402（单调）
- 结论：单调性 gate 对射击通道不敏感（定理保证），但能力**收益幅度**依赖通道；主网格采用与 E02 一致的常量-6 通道以隔离"纯运动学能力"。

## 15. B4.2 operating-speed effect（引用 E02，ηr=1.0）
| 几何 | ηv=0.8 | ηv=1.0 | ηv=1.25 |
|---|---|---|---|
| head_on | **+1.0252** | −0.0 | **−1.3878** |
| parallel | +1.0987 | +0.0173 | −1.4899 |
| crossing | −0.0 | −0.0 | −0.2209 |

## 16. 两语义对照（核心结论）
- operating 语义下，提高常速使值**下降**（head_on +1.03 → −1.39）：快船更早接敌、在互火包线内通过时间更长、位置收益无处兑现（承诺式开环无位置项可收）。
- capability 语义下，扩大可选速度集**从不损害**且常有正收益（最大 +0.572，parallel ηr=1，且变号）：均衡支撑显示最优解常混合慢速档（v=2 诱敌/拉距）与高速档（v=6 抢占）。
- 两者相容："更快更差"是**被迫全程快**的效应，不是**拥有速度选项**的效应。v3 论文"速度悖论"（claim C-speed-paradox）按 B0 审计正式 RENAME 为 operating-speed effect；speed-capability monotonicity 在本引擎代理上成立。

## 17. 对 claim_registry 的回写建议
- `C-speed-paradox` → action 已列 RENAME，本批次提供证据：`results/b4/{b41_monotonicity.csv, b42_semantics_contrast.csv}`。
- 新主张（登记建议）：`C-speed-capability-monotonicity`：嵌套速度能力集下开环 maximin 值单调不减（8/8 cell，最大违反 −2.2e-15 ≪ 1e-8 门限）；能力收益集中在对称射程/射程劣势几何。

## 18. 审稿人攻击模式（自反驳）
- *"单调是定理，实验平凡"*：是定理——这正是把它用作**实现正确性的 oracle**（嵌套审计+LP 对偶+支撑诊断）；科学内容在**能力收益 ΔV 的几何结构**（何时不为零、何时饱和），见第 11/12 项。
- *"速度档只有 3 个、方案恒速"*：预注册设计（v∈{2,4,6} 嵌套）；变速时序方案是 B7/B8 接口，本批次不外推。
- *"射击通道钉死常量 6 掩盖了慢速受罚"*：第 14 项灵敏度覆盖；两通道下单调性均成立。
- *"行切片 LP 的嵌套性可能被求解器路径破坏"*：位级嵌套审计 + 双侧 LP 对偶间隙 ≤ 4.6e-14 排除。

## 19. 局限与混淆
- 开环承诺代理（非引擎逐回合裁决）；转向-推进解耦（引擎 60° 转向脉冲不前进的耦合在 **B5** 处理）；能力收益幅度依赖 γ=0.96 折扣与 40 步视界；head_on ηr=1 cell 结构性零值无区分度。

## 20. 门限判定
- **B4.1：PASS**（8/8 cell 无超出 1e-8 的下降；嵌套 18/18 bitexact）→ *speed-capability monotonicity 成立*。
- **B4.2：PASS**（e02 完整重分类为 operating-speed effect，对照表落盘）。

## 21. 未决问题与下批次接口
- 变速时序方案（方案内速度可变）与 L(v̄) 方案库收敛（B8）；
- 转向耗推进耦合对 capability 收益的影响 → B5 耦合模型；
- head_on ηr=1 斜对称零值的假设边界 → B3 假设破坏清单可复用本批次的镜像方案论证。

## 22. 文件清单
| 文件 | 内容 |
|---|---|
| `research/geometry/speed_capability.py` | B4.1 模块（新增，不改编原代理） |
| `research/experiments/b4_speed_monotonicity.py` | 批次入口脚本 |
| `research/results/b4/b41_monotonicity.csv` | 主网格全诊断量 |
| `research/results/b4/b42_operating_speed_e02.csv` | E02 引用行 |
| `research/results/b4/b42_semantics_contrast.csv` | 两语义对照表 |
| `research/results/b4/fig_b41_monotonicity.png` | V(v̄) 曲线（3 ηr × 2 几何，LP+pure） |
| `research/results/b4/fig_b42_semantics_contrast.png` | operating vs capability 对照图 |
| `research/results/b4/results.json` | 结构化结果 + gate 判定 |
| `research/results/b4/report.md` | 本报告 |
