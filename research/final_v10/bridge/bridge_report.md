# v10 Phase 2: rigid vs leader-follower bridge

Cells: 9 (6 pre-specified core + 3 pre-specified stress)
Commitment sign agreement: **9/9**
Kendall tau = 0.944, Spearman rho = 0.983
Median magnitude distortion: 8.1%
kappa*L_F vs |delta J| Spearman: 0.488
**VERDICT: ROBUST**

| cell | P6 rigid | P6 LF | match | kappa L_F | shape err | heading disp | field dev |
|---|---|---|---|---|---|---|---|
| crossing|0.8|1.0 | -7.422 | -7.050 | yes | 0.698 | 5.99 | 355.0 | 15.4% |
| head_on|0.8|1.0 | -9.447 | -9.532 | yes | 0.698 | 5.99 | 355.0 | 15.4% |
| parallel|1.2|1.0 | +4.883 | +7.454 | yes | 0.698 | 5.99 | 355.0 | 16.1% |
| parallel|0.8|1.0 | -6.018 | -6.507 | yes | 0.698 | 5.99 | 355.0 | 15.4% |
| head_on|1.2|1.0 | +7.304 | +9.673 | yes | 0.698 | 5.99 | 355.0 | 16.1% |
| crossing|1.2|1.2 | +8.940 | +9.825 | yes | 0.582 | 7.18 | 355.0 | 18.2% |
| crossing|1.0|1.2 | +2.086 | +1.234 | yes | 0.582 | 7.18 | 355.0 | 18.1% |
| crossing|1.2|1.0 | +6.425 | +6.292 | yes | 0.698 | 5.99 | 355.0 | 16.1% |
| crossing|0.8|0.8 | -8.659 | -8.812 | yes | 0.873 | 4.79 | 355.0 | 14.8% |