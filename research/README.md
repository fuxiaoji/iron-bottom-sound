# Research Layer (科研层)

本目录是 iron-bottom-sound 规则引擎之上的科研层，按照
`../iron_bottom_sound_research_plan.md`（研究计划书）建设。
论文 `../paper/main.tex` 的全部数字与图由本目录脚本生成。

## 纪律（不可违反）

1. **引擎唯一裁决**：本层从不修改 `engine.py`、规则表、或任何参与对局的
   `GameState`。测量用途的沙箱状态变异只发生在从不进入裁决的离线场景中
   （E01 扫描、E00 审计）。
2. **零隐藏信息**：策略与论文指标只读公开接口。E00 审计在
   hidden_damage / blind_torpedoes 规则下验证快照零泄漏。
3. **无 doctrine 污染**：论文目标函数只有期望命中差；Crossing-the-T、
   formation-split 等战术从不写入目标或 reward。
4. **可复现**：全部实验 seeded（`research/common.derive_seed`）、配对比较
   共享初始条件；每个结果目录含 raw CSV/JSON + 生成脚本。

## 实验索引

| 脚本 | 内容 | 结果目录 | 状态 |
|---|---|---|---|
| `experiments/e00_engine_audit.py` | 确定性重放/泄漏/变异审计 | `results/e00/` | PASS |
| `experiments/e01_fire_kernel.py` | 火力核校准（Spearman/nMAE 门限） | `results/e01/` | PASS (ρ=0.991) |
| `experiments/e02_crossing_t_phase.py` | 承诺机动博弈相图 + 简并命题 | `results/e02/` | 完成 |
| `experiments/e04_torpedo_denial.py` | 鱼雷 direct/denial 分解（完整协议） | `results/e04/` | 完成如实 FAIL |
| `experiments/e04_min_denial.py` | 独立实现的稳健性交叉检查 | `results/e04min/` | 与完整协议结论一致 |
| `experiments/e05_engagement_graph.py` | 交战图预测力（预注册阴性） | `results/e05/` | 完成如实 FAIL→附录 |
| `experiments/e06_engine_validation.py` | 几何策略→引擎命令验证（配对局） | `results/e06/` | 完成 |

运行方式：`source .venv/bin/activate && PYTHONPATH=backend/src:.
python research/experiments/<脚本>`（e04/e05/e06 支持 `--smoke`/并行）。

## 依赖的引擎事实（踩坑记录，写代码前必读）

- D66 **低值=好**（roll 11 是命中表顶格），有利情形带**负**修正；
  `d66_adjust` 沿升序 D66 序列走，命中响应曲线 h(m) 随 m **递减**。
- `_bearing_between` 是连续屏幕角取最近六方向；odd-q 错位网格上**不等于**
  轴向行走方向索引（引擎注释：旧近似误判约四成目标）。
- `state.ships` 按 id 键控：攻防两侧用同名 ship id 会别名成同一对象。
- `submit_orders` 对无效批次**静默不存储**（返回 `ValidationResult`），
  到 `advance` 才报 "Both sides must submit"；驱动对局用
  每阶段 `submit_orders` + `advance`，并以返回值做回退。
- 想定标签行号在不同列奇偶下对应不同内部 r；几何布置一律用内部坐标。

## 结构

```
research/
├── common.py               # 沙箱想定注册、种子派生
├── adapters/ibs_observation.py   # 只读 ResearchSnapshot（E00 审计）
├── geometry/
│   ├── firepower_kernel.py # 方向性火力核 + 反演/删失回归校准（E01）
│   ├── differential_game.py# 降维 (r,αB,αR) 闭环博弈（简并命题演示）
│   └── committed_game.py   # 承诺机动 open-loop minimax（E02 主模型）
├── policies/geometry_policy.py   # 代理策略 → 引擎合法命令翻译层（M6）
├── torpedo_denial/         # E04 完整协议模块（routes/lane/scenarios/protocol）
├── experiments/            # 全部实验入口
├── results/                # 全部原始结果（csv/json/图/报告）
└── goal-progress.md        # 目标模式进度锚点
```
