# v9 T1: exact discretized open-loop commitment certification

Grids run: ['5', '7']   H=1 exact baselines: all exact
Grid-5: 18/18 sign-certified, 0 certified reversals
Grid-7: 18 cells, 0 certified reversals
Geometry support: {'head_on': {'pos': 3, 'neg': 3, 'n': 6}, 'parallel': {'pos': 3, 'neg': 3, 'n': 6}, 'crossing': {'pos': 3, 'neg': 3, 'n': 6}}
Symmetric sanity near zero: True
**VERDICT: CORE-STRONG (Grid-7 full)**

Bounds are exact for the frozen finite game: LB = exhaustive min over the full action space against the complete Blue mixture; UB = exhaustive max against the complete Red mixture. No mixture truncation is used anywhere.

| geometry | eta_r | eta_v | grid | LB | UB | P interval | cert | gap | status |
|---|---|---|---|---|---|---|---|---|---|
| head_on | 0.8 | 0.8 | 5 | -12.502 | -11.960 | [-10.789, -10.247] | Y | 4% | tight |
| head_on | 1.2 | 1.0 | 5 | +13.175 | +13.702 | [+9.962, +10.489] | Y | 4% | tight |
| head_on | 1.2 | 0.8 | 5 | +11.912 | +12.481 | [+8.700, +9.268] | Y | 5% | tight |
| head_on | 0.8 | 1.0 | 5 | -12.222 | -11.924 | [-10.509, -10.211] | Y | 2% | tight |
| head_on | 0.8 | 1.2 | 5 | -11.818 | -10.890 | [-10.105, -9.178] | Y | 8% | SIGN-CERTIFIED/VALUE-LOOSE |
| head_on | 1.2 | 1.2 | 5 | +13.242 | +13.868 | [+10.030, +10.656] | Y | 5% | tight |
| parallel | 0.8 | 0.8 | 5 | -9.722 | -7.662 | [-8.653, -6.593] | Y | 23% | SIGN-CERTIFIED/VALUE-LOOSE |
| parallel | 0.8 | 1.0 | 5 | -7.566 | -7.244 | [-6.497, -6.176] | Y | 4% | tight |
| parallel | 0.8 | 1.2 | 5 | -6.731 | -6.447 | [-5.662, -5.379] | Y | 4% | tight |
| parallel | 1.2 | 0.8 | 5 | +6.817 | +7.769 | [+5.482, +6.434] | Y | 13% | SIGN-CERTIFIED/VALUE-LOOSE |
| parallel | 1.2 | 1.0 | 5 | +7.864 | +8.792 | [+6.529, +7.457] | Y | 11% | SIGN-CERTIFIED/VALUE-LOOSE |
| crossing | 0.8 | 1.0 | 5 | -9.376 | -9.030 | [-8.360, -8.014] | Y | 4% | tight |
| parallel | 1.2 | 1.2 | 5 | +9.101 | +11.787 | [+7.766, +10.452] | Y | 28% | SIGN-CERTIFIED/VALUE-LOOSE |
| crossing | 0.8 | 0.8 | 5 | -9.583 | -9.108 | [-8.566, -8.092] | Y | 5% | SIGN-CERTIFIED/VALUE-LOOSE |
| crossing | 0.8 | 1.2 | 5 | -7.896 | -7.634 | [-6.880, -6.617] | Y | 3% | tight |
| crossing | 1.2 | 0.8 | 5 | +6.325 | +6.542 | [+4.990, +5.206] | Y | 3% | tight |
| crossing | 1.2 | 1.0 | 5 | +7.768 | +8.115 | [+6.433, +6.780] | Y | 4% | tight |
| crossing | 1.2 | 1.2 | 5 | +9.861 | +10.328 | [+8.526, +8.992] | Y | 5% | tight |
| head_on | 0.8 | 0.8 | 7 | -12.632 | -12.043 | [-10.919, -10.330] | Y | 5% | tight |
| head_on | 0.8 | 1.0 | 7 | -13.780 | -11.899 | [-12.067, -10.186] | Y | 15% | SIGN-CERTIFIED/VALUE-LOOSE |
| head_on | 0.8 | 1.2 | 7 | -11.359 | -9.515 | [-9.646, -7.802] | Y | 17% | SIGN-CERTIFIED/VALUE-LOOSE |
| head_on | 1.2 | 1.0 | 7 | +13.057 | +13.732 | [+9.845, +10.519] | Y | 5% | SIGN-CERTIFIED/VALUE-LOOSE |
| head_on | 1.2 | 0.8 | 7 | +11.498 | +12.609 | [+8.286, +9.396] | Y | 9% | SIGN-CERTIFIED/VALUE-LOOSE |
| head_on | 1.2 | 1.2 | 7 | +12.039 | +13.689 | [+8.826, +10.477] | Y | 13% | SIGN-CERTIFIED/VALUE-LOOSE |
| parallel | 0.8 | 0.8 | 7 | -9.286 | -7.930 | [-8.217, -6.862] | Y | 16% | SIGN-CERTIFIED/VALUE-LOOSE |
| parallel | 0.8 | 1.2 | 7 | -6.591 | -5.686 | [-5.523, -4.617] | Y | 15% | SIGN-CERTIFIED/VALUE-LOOSE |
| parallel | 0.8 | 1.0 | 7 | -7.673 | -6.246 | [-6.605, -5.177] | Y | 21% | SIGN-CERTIFIED/VALUE-LOOSE |
| parallel | 1.2 | 0.8 | 7 | +7.538 | +8.538 | [+6.203, +7.203] | Y | 13% | SIGN-CERTIFIED/VALUE-LOOSE |
| parallel | 1.2 | 1.0 | 7 | +8.053 | +9.895 | [+6.718, +8.560] | Y | 20% | SIGN-CERTIFIED/VALUE-LOOSE |
| parallel | 1.2 | 1.2 | 7 | +8.793 | +12.620 | [+7.458, +11.285] | Y | 39% | SIGN-CERTIFIED/VALUE-LOOSE |
| crossing | 0.8 | 0.8 | 7 | -9.788 | -8.185 | [-8.772, -7.169] | Y | 18% | SIGN-CERTIFIED/VALUE-LOOSE |
| crossing | 0.8 | 1.0 | 7 | -9.411 | -8.725 | [-8.394, -7.709] | Y | 8% | SIGN-CERTIFIED/VALUE-LOOSE |
| crossing | 0.8 | 1.2 | 7 | -8.188 | -6.434 | [-7.171, -5.418] | Y | 24% | SIGN-CERTIFIED/VALUE-LOOSE |
| crossing | 1.2 | 0.8 | 7 | +5.748 | +7.319 | [+4.413, +5.984] | Y | 24% | SIGN-CERTIFIED/VALUE-LOOSE |
| crossing | 1.2 | 1.0 | 7 | +7.649 | +9.245 | [+6.314, +7.910] | Y | 19% | SIGN-CERTIFIED/VALUE-LOOSE |
| crossing | 1.2 | 1.2 | 7 | +8.846 | +12.122 | [+7.511, +10.787] | Y | 32% | SIGN-CERTIFIED/VALUE-LOOSE |