# 铁底湾 RL 研究（本机 RTX 5070 初步实验）

与 `backend` 引擎解耦：只**读**用引擎接口（`run_match` / 只读观察助手），绝不改状态、
不改裁决、不复制规则常量（**引擎唯一裁决**纪律）。

> 📖 **训练原理讲解看 [DESIGN.md](DESIGN.md)**（基因组/适应度/交叉变异/冠军复评/验证，含参数表与流程图）。
> 本文档只给命令速查。

## 环境

```bash
export PYTHONPATH=backend/src          # bash
# PowerShell：$env:PYTHONPATH = "C:\Users\fwj\Documents\ChatGPT\铁底湾\backend\src"
```

## 当前阶段：遗传算法训练状态机 AI

BC 之前先把要被克隆的老师 `TacticalCommander` 的 `TacticalProfile` 权重进化出来。
**双想定都打**（S-03+S-01 共用主图，一套权重须双想定成立）。

### 训练（evolve.py）

```bash
# 中规模 5 代（推荐起步；双想定 × 3 对手 × 20 进程，约 1 小时）
python -X utf8 -m rl.evolve --scenario IBS-S-03,IBS-S-01 --gens 5 --pop 32 \
    --opponents balanced,fleet,brawl --games-per-opp 8 --workers 20 \
    --champion-candidates 4 --champion-games 24 \
    --out rl/results/ga-dual-med-v1 --seed 20260826

# 小规模冒烟（秒级）
python -X utf8 -m rl.evolve --gens 1 --pop 8 --games-per-opp 2 --workers -1 --out rl/results/ga-smoke
```

### 实时面板（watch.py）— 边跑边看风格 × 胜率

```bash
python -X utf8 -m rl.watch --out rl/results/ga-dual-med-v1          # 终端原地刷新
python -X utf8 -m rl.watch --out rl/results/ga-dual-med-v1 --once   # 只打一帧快照
```
列：`风格`（最近内置风格，`*`=已进化偏离）· `S-03`/`S-01`（真实胜率 0~1）· 进度/墙钟/ETA · 逐代 best(fitness)。

### 稳健性验证（verify.py）— fresh seed 防过拟合 + 绝对刻度

```bash
python -X utf8 -m rl.verify --profile rl/results/ga-dual-med-v1/champion-genome.json \
    --opponents balanced,fleet,line,brawl,torpedo,cautious --games 12 --workers 16 \
    --out rl/results/ga-dual-med-v1/verify-champion
```

输出三类指标：
- **相对**：逐槽胜率 / 均 VP 差 / 跨想定 combined（对"谁"打出来的）
- **绝对（锚在游戏规则）**：`目标达成率` = 达成剧本目标的局数占比（S-03 轴心=真击沉 2 艘
  英舰；盟军=真击沉/减速德舰），避免"默认兜底赢"被当成实力
- **绝对刻度**：`Elo vs balanced 锚点`（锚=1500，正=比手调均衡强），跨实验可累积比较

### 风格混战赛（style_tourney.py）— 看"想定 × 风格 × 阵营"

```bash
python -X utf8 -m rl.style_tourney --scenario IBS-S-01 \
    --champion rl/results/ga-dual-med-v1/champion-genome.json \
    --games 12 --workers 16 --out rl/results/style-tourney-s01
```
所有内置风格（+可选冠军）循环互殴：逐风格「轴心/盟军 胜率差分·真实胜率·平局率·均VP差」+
两两对阵矩阵 + 胜负原因分布。S-01 想定平局率高达 ~60%，必须看平局率/决定性率。

## 已上线游戏（2026-08-26）

- 全局进化冠军（`champions.py` `CHAMPIONS["evolved"]`，代码常量自包含）已接入
  **本地引擎**（`match.make_session`）+ **服务端**（`api.py ai-opponent`）+ **前端**
  （`App.tsx` `AI_PROFILES`，下拉分组「内置风格/进化冠军」+ 简介 + 胜率标注）。
- 胜率标注取自 `rl/results/style-tourney-final/style-summary.json`（双想定混战赛，
  288 局/风格）。**实测：进化冠军全体对打排倒数第二（−0.077）——价值在打法个性而非更强**。
  完整结论见 DESIGN.md §10。

## 产物（`--out` 目录，全部落盘保留）

- `games.jsonl`：**逐局**原始结果（流式写入，面板实时读）
- `gen-summary.csv` / `population-gen-N.json`：收敛曲线 / 每代全群体
- `best-*.json`：逐代最优（噪声尖峰，**仅对照**）
- **`champion-*.json`：交付**（冠军复评大量局数选出的稳健最优，BC 的老师）
- `hall-of-fame.json`：多样性存档

## 关键教训

小规模实测：best 训练 seed 上 8/8 全胜，fresh seed 一验并不优于手调 balanced——
**单局伯努利方差 ≈0.5**，局数太少必过拟合。→ 中规模加局数 + 冠军复评去噪。

## 规划中（BC/PPO 阶段）

- `env.py` 通用战局张量（34×27×通道，跨想定复用）
- `data.py` 并行 BC 数据采集（老师 = `champion-profile.json`）
- `model.py` 船-token Transformer + **空间旋转位置编码**（2D 轴向 RoPE）+ CNN 基线
- `train.py` BC：S-03 训 → S-01 测迁移 + PE 消融
- `train_ppo.py` 最小 PPO（火力热度势奖励）
