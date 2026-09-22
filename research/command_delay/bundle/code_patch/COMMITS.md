# COMMITS.md · CD-0 … CD-6 分阶段提交

全部提交位于分支 `research/m2-2-compiler-fidelity`，冻结 tag 之后。SHA 见下（`git log --oneline realistic-command-v1-frozen..HEAD`）。

| 阶段 | 提交标题 | 内容要点 |
|---|---|---|
| CD-0 | `feat(command-delay): CD-0 freeze — realistic-command-v1-frozen tag + golden replay baseline` | 冻结 tag、7 行黄金回放基线、跨哈希种子探针、CD0-F1 确定性修复（0 冻结漂移） |
| CD-1 | `feat(command-delay): CD-1 MOVE_TOGETHER additive formation movement style (IBS-R-RC-08)` | `formation_maneuver.py`、几何/轴线索状态、七项资格条件、`REFORM_COLUMN`、20 项测试 |
| CD-2 | `feat(command-delay): CD-2 Command Delay mode shell — isolation, authority, fleet/formation views` | 新选项、权限状态机、舰队/编队视图、API 入口、16 项测试 |
| CD-3 | `feat(command-delay): CD-3 MissionOrder, three contingency kinds, deterministic communications` | `communications/`、`delegation.py`、任务式命令与三类分支、CD3-F1 修复、25 项测试 |
| CD-4 | `feat(command-delay): CD-4 deterministic formation agent + gunnery authority boundary` | `target_priority.py`、`formation_agents.py`、权限边界与引擎侧炮击生成、18 项测试 |
| CD-5 | `feat(command-delay): CD-5 LLM formation adapter -- action ids only, no gunnery, audited` | `formation_llm.py`、严格解析、重试与回退、录播重放、16 项测试 |
| CD-6 | `feat(command-delay): CD-6 research hooks -- contracts, ledger, tensors, episode export` | `contracts.py`、`research_hooks.py`、版本化张量规格、策略安全与回放导出分离、13 项测试 |

每个提交都在提交前跑过：该阶段的测试 + CD-0 黄金回放（`GOLDEN_REPLAY = PASS`，0 漂移）。

## 复现

```bash
cd iron-bottom-sound
git log --oneline realistic-command-v1-frozen..HEAD     # 七个提交
git tag -l -n1 realistic-command-v1-frozen              # 冻结基线

.venv/bin/python research/command_delay/golden_replay.py --check
.venv/bin/python -m pytest tests/test_command_delay_*.py -q
.venv/bin/python research/command_delay/run_audits.py
```
