# 复现步骤（v2.3 批次）

全部命令在仓库根目录（`iron-bottom-sound/`）执行。

## 1. 冻结与审计

```bash
.venv/bin/python research/command_delay/golden_replay.py --check
.venv/bin/python research/command_delay/golden_replay.py --probe-hash-seeds 0,1,2,8
.venv/bin/python research/command_delay/run_audits.py          # 8 项，退出码即闸门
```

## 2. 本批次的测试

```bash
.venv/bin/python -m pytest tests/ -k command_delay -q
# 或只跑 v2.3 新增的八个文件
.venv/bin/python -m pytest tests/test_command_delay_*_v23.py -q
```

## 3. IR-1 路由审计（对旧对局记录重算）

```bash
.venv/bin/python research/command_delay/v2_3/ir1_route_audit.py
# 产出 raw/old_message_route_audit.csv 与 raw/ir1_route_audit_summary.json
```

## 4. IR-9 实机对局（需要 API key，约 1.5–2 小时）

```bash
ZHIPU_API_KEY=... .venv/bin/python research/command_delay/llm_battle.py \
  --scenario IBS-S-EM-01 --seed 19440619 --out battle_v2_3 \
  --model glm-4.5-flash --thinking --turn-cap 12
```

模型可用性先探测（免费档、是否接受 thinking 字段、是否返回严格 JSON）：

```bash
ZHIPU_API_KEY=... .venv/bin/python research/command_delay/probe_provider.py --models glm-4-flash,glm-4.5-flash
```

## 5. IR-9 的核验与战报

```bash
# 重演一致性（重放记录的模型回复）
.venv/bin/python research/battle_video/replay_battle.py --battle battle_v2_3 --verify
# 泄漏扫描 + 注入正对照
.venv/bin/python research/battle_video/scan_provider_battle.py --battle battle_v2_3
.venv/bin/python research/battle_video/scan_provider_battle.py --battle battle_v2_3 --self-test
# 战报 + 七项断言
.venv/bin/python research/command_delay/v2_3/ir9_battle_report.py --battle battle_v2_3
```

## 6. 环境注意

- 本机对 provider 的连接会被透明代理成片打断（TLS 重置 / 503）；驱动已按"同一决策内重试 +
  直连与环境代理交替"处理，失败逐条留档（`calls.jsonl` 的 `transport_error`）。
- 思维链模型（`glm-4.5-flash`）需要足够输出预算：`--thinking` 会把 `max_tokens` 默认提到 4000，
  否则推理会吃光预算、返回空 content（实测约占 19% 的调用）。
