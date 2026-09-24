# 00 · 基线冻结（IR-0）

**批次**：IBS Command Delay v2.3 — Integrity, Historical Routing, and Regression Repair
**冻结时间**：2026-09-24
**冻结提交**：`e3149c4f3c147c966efba49908fc960f3a439278`（分支 `research/m2-2-compiler-fidelity`）
**冻结标签**：`realistic-command-v1-frozen`（Classic / Realistic 语义仍以该标签为准）

## 1. 旧对局证据：保全，不移动、不覆盖

CD-13 二马剧本对局的全部证据**原地保留**在 `research/command_delay/battle_em01/`，
并按**复制**方式归档到本批次的 `raw/battle_em01/`（bundle 材料；该副本已在 `.gitignore` 中，
避免把 43 MB 重复内容再存进 git 历史）：

| 文件 | 字节 | sha256（前 16） |
|---|---|---|
| REPORT.md | 见 `baseline_manifest.json` | 见 `baseline_manifest.json` |
| battle_data.json | 35.0 MB | 同上 |
| calls.jsonl | 7.8 MB | 同上 |
| orders.jsonl / reports.jsonl / replay_verification.json / leak_scan.json / leak_self_test.json | 小 | 同上 |

> 完整哈希表在 `baseline_manifest.json` 的 `battle_evidence` 字段；同文件另记录了
> 三个被冻结源码面（engine.py / realistic_command.py / models.py）的 sha256 与黄金基线
> 的 8 行 digest，供 IR-8 的回归比对使用。

## 2. 冻结时的重演核验（重新执行，不是引用旧结论）

```
.venv/bin/python research/battle_video/replay_battle.py --battle battle_em01 --verify
→ verdict PASS，阶段快照 80，逐字段不一致 0
   使用记录指令批次 90/90；同时重放模型回复 60 条（编队）+ 22 条（舰队）
```

（该核验本身在 CD-13 期间**失败过一次**——只用 `orders.jsonl` 重演会在 T5 鱼雷结算分叉，
因为模型撰写的报文流量是战斗的一部分。修法是重放模型回复，见 `recorded_policies.py`。）

## 3. 本批次允许触碰与不允许触碰的边界

| 面 | 规则 |
|---|---|
| Classic 模式 | **不动**（黄金行 `classic_s01/s03/em01` 必须逐字节不变） |
| Realistic 模式既有语义 | **不动**（`realistic_s01/s03/em01/s03_seed9` 必须逐字节不变；FOLLOW_WAKE 行为冻结） |
| Command Delay 模式 | 本批次的修复对象（路由、因果信息、任务命令、上报、单位、事实出处） |
| 旧对局证据 | 只读；新证据写入 `battle_v2_3/`（IR-9） |
| 通信/委派代码 | 保持独立模块；`realistic_command.py` 只允许薄钩子（IR-8 审计） |
| 激励/契约实验 | **禁止启动**（PI 裁决） |

## 4. 交付

- `00_BASELINE_FREEZE.md`（本文件）
- `baseline_manifest.json`：提交号、分支、证据文件哈希、冻结源码面哈希、黄金基线 8 行摘要
- `raw/battle_em01/`：旧证据副本（不覆盖原件）
