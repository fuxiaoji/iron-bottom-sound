# B3 assumption-breaking matrix

| case | max abs(V-L) | degeneracy |
|---|---|---|
| base_symmetric | 0.0 | held |
| speed_asymmetry_vB125 | 0.0 | held |
| speed_asymmetry_vB080 | 0.0 | held |
| range_asymmetry_B125_R080 | 13.99 | **BROKEN** |
| action_asymmetry_B5_R3 | 0.0 | held |
| firepower_asymmetry_B125 | 20.09 | **BROKEN** |
| full_asymmetry | 9.75 | **BROKEN** |
| terminal_payoff_finite_horizon_T30 | 0.0 | held |

## 结论
闭环简并是**作用对称性现象**：速度不对称、动作集不对称、有限时域终端收益
都不破坏 V≡L（精确保持）；只有作用强度本身的不对称（射程比、火力比≠1）
打破简并。火力不对称的破坏力强于射程不对称（20.1 vs 14.0）。

这精化了命题 1 的适用边界：运动学不对称无害，作用不对称才是解锁位置价值
的钥匙——与开环承诺博弈中任何方案不对称都产生位置价值形成互补图景。
