---
name: paper-v14-state
description: v14 预算化重规划研究的当前真实状态——哪些已成稿、哪些在跑、哪些根本还没做
metadata:
  type: project
---

截至 2026-09-18，`iron-bottom-sound` 的论文线处于 **v14**，分支 `codex/v14-budgeted-replanning`（基线 commit `5572b73`，为 HANDOFF 提交）。

**已存在**：

- `paper_v14/`：`main.tex` + `sections/{abstract,introduction,model,theory,algorithm,methods,results,discussion,conclusion}.tex`、`references.bib`、`main.pdf`、`supplement.*`、`figures/`、`tables/`、`appendices/`、`qa/`。
- 工作标题：`Budgeted Replanning in History-Dependent Games: Certified Value Frontiers for Revision Calendars`。
- **`main.tex` 用的是通用 `\documentclass[11pt,a4paper]{article}`，尚未套用任何会议模板**（`\bibliographystyle{plainnat}`）。
- `research/final_v14/`：协议与冻结件（`MASTER_PLAN.md`、`DESIGN.json`、`BENCHMARK_PROTOCOL.md`、`THEORY.md`、`CLAIM_CHAIN.md`、`HISTORICAL_FREEZE.json`、`PILOT_FREEZE.json`、`RUN_FREEZE.json`、多个 `REGRESSION_*.log`、`DEVELOPMENT_AMENDMENT_01.md`、`PLAN_EXECUTION_LEDGER.md`、`WORK_STATUS.md`）。
- 复现入口 `reproduce_v14.py`（根目录另有 v9–v13 的历史入口）。

**尚在进行（不得宣称为已完成）**：

- 串行开发实验仍在跑；单独进程监控 8 GB 内存与 20 分钟普通任务限制。
- 冻结测试、稳健性、消融、证书、冷运行比较**尚未完成**。
- 完整稿件终稿与两轮内部审阅**尚未完成**。

**历史线的处置约定**：

- v12 稿件制作被用户以 v13.1 范围（"直到开写论文前"）暂停；v12 未获二区质量认证，其 fallback 稿件**不是**获认证稿件。
- v13.1 是一条**失败停止分支**：修订后主验证 5/12 正、7/12 强反向，`Gate=FAIL`，据此停止 Grid-5/7、转向率、horizon 和 rigid 扩展。**失败与未触发项必须保持失败标记**。
- 论文证明审计曾推翻 v11 的"全状态 V=L"推论，并给出满足其假设的反例与正确的交换奇对称证明。**旧的错误推论不得重新写回论文。**

**检查点**：在宣称任何 v14 结果成立前，先看 `research/final_v14/WORK_STATUS.md` 与 `PLAN_EXECUTION_LEDGER.md`；v14 的冻结哈希是否仍与 live 文件匹配是硬前提。

相关：[[pipeline-governance]]、[[pending-user-slots]]
