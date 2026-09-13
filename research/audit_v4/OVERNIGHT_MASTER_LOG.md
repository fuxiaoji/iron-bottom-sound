# OVERNIGHT_MASTER_LOG.md — Iron Bottom Sound v4.0 夜间研究总日志

## 会话元信息
- 开始时间：2026-09-10 09:05 CST
- 仓库：/Users/Zhuanz1/Desktop/code/seawar/iron-bottom-sound（branch main，commit fc77a65 + 未跟踪 research//paper/）
- Python：3.13 venv（.venv），numpy/scipy/matplotlib/pypdfium2
- 总计划：v4.0（OR + Applied Mathematics 主线，B0→B13 严格顺序）
- 工作协议：采用夜间研究纪律（MASTER_LOG、批次协议 22 项输出、失败留档、审稿人攻击模式、MORNING_README）
- 项目专属规则适配：DeFi 模板中的 2025-lock/D001-D004 不适用本项目；等价规则为
  （a）不改引擎裁决（b）不用隐藏状态（c）负结果留档（d）预置门限先行
- 旧周期成果（v3 管线 + 19 页论文）：作为 B0 审计对象，按 KEEP/NARROW/REMOVE/RENAME 重分类

## 批次状态看板
| 批次 | 状态 | 产出位置 |
|---|---|---|
| B0 定义审计 | **DONE** | research/audit_v4/（6 文件） |
| B3 简并性假设破坏 | **DONE** | research/results/b3/（发现：简并=作用对称性现象，速度/动作不对称无害，射程/火力不对称打破） |
| B1 核校准 | **DONE (PASS)** | research/results/e01 + b1/（v3 ρ=0.9912；B1-ext 损毁核重校准 ρ=0.995 PASS、舰尾命中归零验证 χ 项生效） |
| B2 路径积分目标验证 | **DONE (PASS)** | research/results/b2/（τ=0.38-0.62 不等价；A/B 反转例；时序偏差二阶；纵队中部侧翼 +18.8%） |
| B3 简并性假设破坏 | 待开始 | research/results/b3/ |
| B4 速度能力单调性 | **DONE (PASS)** | research/results/b4/（8/8 cell 嵌套单调，最大"下降"=LP 噪声 −2.2e-15；对偶间隙≤4.6e-14；B4.2 旧结果重分类为 operating-speed effect） |
| B5 非完整重定位代价 | **DONE** | research/results/b5/（C_reposition=+0.26 价值点，d≤6 内平坦——非完整税是"转向税"而非"逐格税"；两种耦合模型对照） |
| B6 可达性/生存性 | **DONE (阴性+景观)** | research/results/b6/（144 格无保证：R 的拒绝交战选择权使最坏保证不可达；保持率中位 0-3%——转向生存性景观报告） |
| B7 承诺时域 | **DONE (核心发现)** | research/results/b7/（对称格 P_H≈0 全时域；非对称格 78% |P_6|>0.05 且 P_6 符号=η_r−1 符号——承诺时域是射程优势的放大器） |
| B8 方案库收敛 | **DONE (FAIL→如实)** | research/results/b8/（收敛 25%、方案稳定 18%——库离散化是一阶不确定性；v4 论文以 [V21,V41] 区间报告，dropped 'equilibrium' 绝对表述） |
| B6 可达性/生存性 | **DONE (无阈值→景观)** | research/results/b6/（R 拒绝交战使最坏保证不可达；优势保持率中位 0-3%——有利状态极脆弱） |
| B9 区间地图 | 待开始 | research/results/b9/ |
| B10 延迟鱼雷状态 | 部分已有（E04 时空航迹） | research/results/b10/ |
| B11 响应集收缩 | **DONE** | research/results/b11/（C_resp 随 k 单调 0.20→0.31；v_resp>0 ⟺ 顶档整层覆盖 8/8） |
| B12 匹配致命性 | **DONE (FAIL 如实)** | research/results/b12/（ε=5% thin 占优 21/28；ε=10% dispersed 10/0——引擎粒度限制；机制=交互非单一） |
| B13 引擎验证 | 部分已有（E06/E07）→ 按 v4 门限补齐 | research/results/b13/ |
| 论文 v4 | 待开始 | paper_v4/ |

## 日志
[2026-09-10 09:05] 会话启动。目标模式锚点：research/goal-progress.md（v4 周期 0/20）。
[2026-09-10 09:05] 开始 B0：审计 committed_game.py / differential_game.py / e04 协议的目标语义、速度语义、定理前提。

[2026-09-10 09:40] B0 DONE：6 份审计文件完成，Gate PASS（速度语义重分类 operating-speed effect 为唯一 RENAME）。
[2026-09-10 09:45] B3 DONE：假设破坏矩阵完成。关键发现——速度不对称(vB 4.8/7.5)、动作集不对称(5v3)、有限时域终端收益均不破坏 V≡L（精确 0.0）；仅射程不对称(14.0)与火力不对称(20.1)打破简并。简并=作用对称性现象。STATUS: DONE。
[2026-09-10 09:46] Wave 1 并行中：B2 子agent（路径积分 vs 快照）、B4/B5 子agent（速度能力单调性+重定位代价）。

[2026-09-10 10:00] B2 DONE (PASS)：snapshot vs integral Kendall τ 均值 0.476（snapshot_T）/0.365（peak），无格达 0.95 等价线——路径积分目标 load-bearing。A/B 核心例（crossing@0.8）：A max L=2.879/J=1.323 vs B max L=0.2915/J=5.024，偏好完全反转。开火时序 fire_after_move 对照：1089 对 0 变号（二阶）。纵队中部侧翼 F=9.18 vs 侧翼 7.73（+18.8%）。STATUS: DONE。NEXT: 等 B4/B5，随后 B10-B12。

[2026-09-10 10:20] B6 DONE：无清晰阈值（R 拒绝交战使最坏保证不可达）→ 按决策树转 viability landscape：优势保持率中位 0-3%，有利状态极脆弱。STATUS: DONE (negative+landscape)。
[2026-09-10 10:20] B7 DONE：对称格 P_H≈0；非对称格 78% |P_6|>0.05，P_6 符号=sign(η_r−1)——承诺时域放大射程优势（劣势方要短承诺保留拒绝权，优势方要长承诺强制交战持续）。STATUS: DONE。
[2026-09-10 10:21] B8 DONE (FAIL 如实)：收敛 25%/方案稳定 18%，未达 80%/85% 门限。处置：论文以 [V21,V41] 区间报告、去掉 'equilibrium' 绝对术语、记录库离散化为一阶不确定性。按决策树转"不写稳定 regime"（B9 相图降级为 library-approximate）。
[2026-09-10 10:22] 派出 B13 子 agent（100 seeds/cell 引擎验证，v4 门限：符号一致≥80%、秩 ρ≥0.60、区间一致≥75%）。

[2026-09-11 00:40] B4 DONE (PASS)：嵌套能力单调性 8/8 成立（LP 噪声级）；协议自检还捕获了首版 pure-maximin 符号错误并修复留档。B4.2 旧速度结论 RENAME 完成。
[2026-09-11 00:42] B5 DONE：重定位代价 +0.26（d≤6 平坦、出射程归零；两种耦合对照）。
[2026-09-11 00:45] B7 DONE：对称格 P_H≈0 全时域；非对称格 78% |P_6|>0.05，P_6 符号=sign(η_r−1)。承诺时域=射程优势放大器。
[2026-09-11 00:46] B6 DONE (阴性)：144 格无最坏保证；保持率中位 0-3%——拒绝交战选择权使位置保证不可购买。
[2026-09-11 00:47] B8 DONE (FAIL 如实)：收敛 25%、方案稳定 18%。处置=区间报告+去绝对化+敏感性审计入论文。
[2026-09-11 00:48] v4 论文骨架 9 页编译通过；B2/B3/B4/B5/B6/B7/B8 数字已填入 §3-§5；待 B10-B12、B13 子 agent 返回后填 §6/§8。

[2026-09-11 01:10] B1-ext DONE (PASS)：损毁 P3 后核重校准 ρ=0.9951/nMAE 5.5%；结构检查：舰尾扇区命中 0.0 vs 舰首 1.407——核的 χ(武器状态) 结构项自动适应损毁。B1 完全关闭。
[2026-09-11 01:12] B10-B12 重试子 agent 已派出（前一 agent 网络死亡，遗留 b10_hazard_field.py 交由重试 agent 评估复用）。

[2026-09-11 01:30] B10-B12 重试完成。B10 PASS(3/3)：时间依赖确认、8 route 例证、40.8-42.5% 威胁质量在未来。B11 PASS：C_resp 随厚度单调、机制=顶档覆盖决定（8/8）。B12 FAIL 如实：覆盖 vs 毁伤在引擎粒度不可分（thin 21/28 占优 @ε=5%）。v4 论文 Section 6 已更新至 B10-B12 最终数字。
