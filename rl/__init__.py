"""铁底湾 RL 研究包（与 backend 引擎解耦，只读使用引擎接口）。

- DESIGN.md    训练设计文档（基因组/适应度/交叉变异/冠军复评/验证 + 参数表）
- evolve.py    遗传算法训练状态机 AI（TacticalProfile 权重，双想定）
- watch.py     实时面板：风格 × 双想定胜率（追读流式 games.jsonl）
- verify.py    全新 seed 稳健性验证（防过拟合，双想定）
- style_tourney.py  风格混战赛：内置风格（+冠军）互殴，逐风格×阵营 + 两两对阵
- env.py       （规划中）通用战局张量构建器
- data.py      （规划中）并行 BC 数据采集
- model.py     （规划中）船-token Transformer + 空间旋转位置编码 / CNN 基线
- train.py     （规划中）BC 训练 + 跨想定迁移 + PE 消融
- train_ppo.py （规划中）最小 PPO（火力热度奖励）

运行需 PYTHONPATH=backend/src（引擎在 backend/src/iron_bottom_sound）。
"""
