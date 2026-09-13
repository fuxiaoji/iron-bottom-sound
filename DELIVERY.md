# 交付说明（2026-09-10 凌晨科研冲刺）

## 交付物

| 交付物 | 位置 |
|---|---|
| 英文论文（19 页） | `paper/main.pdf`（源码 `paper/main.tex`） |
| 中文论文（17 页） | `paper/main_zh.pdf`（源码 `paper/main_zh.tex`，XeLaTeX + ctex） |
| 独立审稿意见存档 | `paper/review.md` |
| 科研层代码 | `research/`（见 `research/README.md` 索引） |
| 实验原始结果 | `research/results/e00 … e07`（每目录含 report.md + raw CSV/JSON + 图） |
| 进度锚点 | `research/goal-progress.md` |

## 一览（论文表 3 的完整版）

| 实验 | 门限 | 结果 |
|---|---|---|
| E00 引擎审计 | 零泄漏/零变异/确定性重放 | PASS |
| E01 火力核校准 | ρ≥0.90，nMAE≤15% | PASS（pooled ρ=0.9912，nMAE 5.7%；CI [0.9931,0.9940]） |
| E01b 基线+迁移 | 各向同性核对照；跨舰对迁移 | 方向性核 pooled ρ=0.9936 [0.9931,0.9940] vs 各向同性 0.9524（nMAE 3.2 倍差距）；迁移 ρ 0.982–0.992 |
| E02 承诺机动博弈 | 对称性/边界复现 | PASS（swap 误差 0.0；54 格相图；简并命题 V≡L 精确；8/8 bootstrap 重采样复现全部 maximin 计划） |
| E04 鱼雷 denial | 低命中 denial CI>0（≥3 几何） | **FAIL（如实）**：216 样本恒 0；机制=价值景观 8 档/顶档 25.5 并列；直击对照 0.92 [0.42,1.42] 显著 |
| E04c 齐扫规模 | （新增）厚度响应 | denial 立即饱和（2.0→2.5），direct 线性增长（2.6→8.6）；低命中层 k≤2 为 0、k=4 转 1.3 |
| E05 交战图（规范分析） | ΔR²≥+0.05 或 MAE−10% | **规范敏感**：plan-literal（可复现脚本 e05_spec_analysis.py）ΔR²=+0.108 [0.069,0.160]、MAE−17.5% [9.7,26.7] PASS；strict 口径 +0.033 未达 |
| E06 引擎验证（60 seeds/cell） | 翻译层竞争力 | PASS：vs straight +7.7/+5.2/+9.6 全显著；vs balanced 持平；head-on 对 line 显著让分（−1.73 [−3.23,−0.28]，纵队特化） |
| E07 历史定性（埃斯佩兰斯角，20 seeds） | 外部效度 | vs straight +12.2 [+6.5,+17.9] 显著；vs line +3.7 正趋势不显著；axis 全负与已知想定偏差一致 |
| E04c 齐扫规模（270 去重测量） | 厚度响应 | denial 单调凸增 2.0→2.0→3.3→5.0（k=6 时 100% 改航）；direct 线性 2.6→20.2；低命中层 0→0→+2.0→+4.0 |

## 质量流程
1. 独立审稿人子 agent：4 Major + 11 Minor，全部修订（含 E02 速度方向反转的硬伤更正）。
2. 视觉验收 judge：7 项修复全部完成。
3. 纪律：未改引擎裁决、零隐藏信息、无 doctrine 进目标函数、配对种子 + 95%CI、
   两个如实 FAIL（E04 低命中、E05 严格口径）带机制解释。

## 复现
```bash
source .venv/bin/activate
PYTHONPATH=backend/src:. python research/experiments/e00_engine_audit.py
PYTHONPATH=backend/src:. python research/experiments/e01_fire_kernel.py
# … 依 README.md 索引
cd paper && pdflatex main.tex
```

## 投稿建议
- 首选 Defence Technology（返修后 Likely）。
- 投稿前待办：实名作者信息；E04 几何×齐扫 2×2 因子实验；一个历史想定的定量对照升级。
