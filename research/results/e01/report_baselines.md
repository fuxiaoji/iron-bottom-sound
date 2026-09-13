# E01b baselines, CIs, and transfer

- pooled full kernel: rho=0.9936 CI [0.9931, 0.9940]; isotropic rho=0.9524

| class | full rho [CI] | isotropic rho | nMAE full / iso |
|---|---|---|---|
| DD | 0.9913 [0.9901, 0.9922] | 0.9468 | 0.0616 / 0.1925 |
| CL | 0.9917 [0.9904, 0.9927] | 0.8991 | 0.0550 / 0.2432 |
| CA | 0.9908 [0.9894, 0.9918] | 0.9468 | 0.0577 / 0.1765 |
| BB | 0.9907 [0.9894, 0.9917] | 0.9607 | 0.0543 / 0.1418 |

## cross-pair transfer

| source fit -> target pair | Spearman | nMAE |
|---|---|---|
| CA-> DD | 0.9917 | 0.0599 |
| CA-> CL | 0.9916 | 0.0541 |
| CA-> BB | 0.9825 | 0.1556 |
| BB-> DD | 0.9917 | 0.0597 |
| BB-> CL | 0.9900 | 0.0830 |
| BB-> CA | 0.9894 | 0.0907 |
