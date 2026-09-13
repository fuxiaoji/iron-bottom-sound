# OVERNIGHT FINAL REPORT (v5.0 + v6.0 credibility + commitment solver)

## 1. Executive Summary
v4 论文 11 页完成。v5 可信度修复完成。v6 两个 MUST 项目执行中：
- MUST-1 (Double Oracle + BR): 正在计算（100% CPU 已运行 45+ 分钟）
- MUST-2 (Matched Engine Validation): 协议已写，待 MUST-1 完成后跑
- B10 (延迟威胁) / B11 (响应集收缩): 完成
- B12 (匹配致命性): 完成（阴性）

## 2. v4 Paper Status
- paper_v4/main.pdf: 11 pages, compiles cleanly, all real data
- Overstrong language audit done (W3 fixes applied)
- B13 canonical results (PARTIAL) integrated
- Contributions restructured

## 3. Core Results Summary
| Result | Key Number | Batch |
|---|---|---|
| Kernel calibration | ρ=0.9912, nMAE 5.7% | E01/B1 |
| Path-integrated load-bearing | Kendall τ=0.14-0.62 | B2 |
| Degeneracy = interaction-symmetry | speed/action hold, range/firepower break | B3 |
| Speed-capability monotonicity | 8/8 cells, LP noise | B4 |
| Commitment-range | P_6 sign = sign(η_r−1), provisional | B7 |
| Torpedo denial null (low-hit) | ≡0 (216 samples), tiered landscape mechanism | E04 |
| Spatiotemporal hazard | 6-11% hot pulses, 40-42% future mass | B10 |
| Response contraction | 0.20→0.31 with k=1→6 | B11 |
| Engine validation | PARTIAL: ρ=1.00, sign varies by definition | B13 |
| Operating-speed effect | renamed from "speed paradox" | B4.2 |

## 4. Honest Negatives
| Negative | Mechanism |
|---|---|
| Low-hit torpedo denial ≡ 0 | Tiered landscape + 25.5 tied top routes |
| Library non-convergence | Discretisation is first-order uncertainty |
| B6 no viability guarantee | Decline-battle option |
| B12 coverage≠damage | Engine granularity limitation |
| E05 strict < gate | Shape features insufficient |

## 5. Two Blockers (v6.0 MUST items)
### MUST-1: Open-loop commitment solver
- Status: running (100% CPU, ~45+ min so far)
- Method: Double Oracle with continuous BR trajectory optimisation
- Gate: BR gap < 5% on representative cells

### MUST-2: Matched engine validation
- Status: protocol written, awaiting MUST-1 frozen predictions
- Design: 2×2 (fixed-vs-fixed + feedback-vs-feedback) + true feedback premium
- Minimum: 12 cells × 100 paired seeds with CRN

## 6. Claims Audit
| Claim | Status |
|---|---|
| Path-integrated exposure | KEEP (core) |
| Directional kernel | KEEP (foundational) |
| Closed-loop degeneracy | KEEP + NARROW |
| Speed-capability monotonicity | KEEP (proposition) |
| Delayed torpedo field | KEEP (core candidate) |
| Commitment-range | PROVISIONAL |
| Coverage beats damage | REMOVED |
| Feedback premium | NARROWED to policy-class gap |
| E05 graph PASS | NARROWED to specification-sensitive |
