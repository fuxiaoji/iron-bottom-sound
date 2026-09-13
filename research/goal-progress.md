# 目标进度锚点

## 当前目标（v7.0 收口周期，2026-09-12）
✅ 完成。两个 MUST 实验按冻结规则判定完毕，论文 paper_v7 冻结，
STOP EXPERIMENT EXPANSION 生效。剩余仅 arXiv/投稿打包类工作。

## 最终判定
| 任务 | 判定 | 证据 |
|---|---|---|
| MUST-1 commitment | **PASS-STRONG** | sign(P_6)=sign(ηr−1) 18/18 格、3/3 几何；值 solver-relative（67% gap 门、K 值敏感已报告） |
| MUST-2 engine | **FAIL → case study** | sign 75%、ρ=−0.08、ordering 63%（六角离散化主导；B13 cross-policy ρ=1.00 保留为弱检查） |

## 论文
paper_v7/main.tex → main.pdf **13 页编译干净**。编队级 §2 形式化、
+5.14→policy-class gap、thickness 措辞清除、abstract/conclusion 与判定
同步、禁词清扫通过。

## 收尾清单
- [x] ITERATION_1.md / ITERATION_2.md（final_v7/）
- [x] claim_registry.yaml（9 条 claims，含 2 条 REMOVE）
- [x] must1_*（147 jobs + 聚合 + 报告）、must2_*（4800 局 + 门 + 报告）
- [x] 打包导师版（v7）
- [ ] arXiv v1 源码包 / venue 模板（用户指示后）

## 计数器
v7 周期 20/20 → 完毕。
