# v10: leader-follower exact commitment certification

Grids: ['5', '7']; H=1 exact on every cell: True
Grid-5 LF: 18/18 sign-certified, 0 reversals
Grid-7 LF: 18 cells, 0 reversals
Geometry support: {'head_on': {'pos': 3, 'neg': 3, 'n': 6}, 'parallel': {'pos': 3, 'neg': 3, 'n': 6}, 'crossing': {'pos': 3, 'neg': 3, 'n': 6}}
Rigid vs LF sign match (Grid-5): 18/18
**VERDICT: LF-CORE-STRONG**

| model | geometry | eta_r | eta_v | grid | LB | UB | P interval | sign | gap | status |
|---|---|---|---|---|---|---|---|---|---|---|
| lf | crossing | 0.8 | 0.8 | 5 | -10.458 | -8.702 | [-9.44, -7.69] | -1 | 18% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | crossing | 0.8 | 1.0 | 5 | -8.373 | -7.776 | [-7.36, -6.76] | -1 | 8% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | crossing | 0.8 | 1.2 | 5 | -6.646 | -6.399 | [-5.63, -5.38] | -1 | 4% | tight |
| lf | crossing | 1.2 | 0.8 | 5 | +5.321 | +6.110 | [+3.99, +4.78] | +1 | 14% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | crossing | 1.2 | 1.0 | 5 | +7.146 | +7.724 | [+5.81, +6.39] | +1 | 8% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | crossing | 1.2 | 1.2 | 5 | +9.753 | +10.953 | [+8.42, +9.62] | +1 | 12% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | head_on | 0.8 | 0.8 | 5 | -13.653 | -11.113 | [-12.46, -9.93] | -1 | 20% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | head_on | 0.8 | 1.0 | 5 | -12.584 | -9.066 | [-11.40, -7.88] | -1 | 32% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | head_on | 0.8 | 1.2 | 5 | -13.341 | -10.322 | [-12.15, -9.13] | -1 | 26% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | head_on | 1.2 | 0.8 | 5 | +9.834 | +12.731 | [+7.93, +10.83] | +1 | 25% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | head_on | 1.2 | 1.0 | 5 | +10.451 | +13.687 | [+8.55, +11.78] | +1 | 27% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | head_on | 1.2 | 1.2 | 5 | +7.383 | +10.068 | [+5.48, +8.16] | +1 | 31% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | parallel | 0.8 | 0.8 | 5 | -10.161 | -8.213 | [-9.82, -7.87] | -1 | 22% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | parallel | 0.8 | 1.0 | 5 | -9.475 | -5.995 | [-9.13, -5.65] | -1 | 48% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | parallel | 0.8 | 1.2 | 5 | -6.812 | -4.548 | [-6.47, -4.20] | -1 | 38% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | parallel | 1.2 | 0.8 | 5 | +7.156 | +9.686 | [+4.74, +7.27] | +1 | 30% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | parallel | 1.2 | 1.0 | 5 | +7.825 | +11.302 | [+5.41, +8.88] | +1 | 39% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | parallel | 1.2 | 1.2 | 5 | +8.797 | +12.148 | [+6.38, +9.73] | +1 | 32% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | crossing | 0.8 | 0.8 | 7 | -10.365 | -8.845 | [-9.35, -7.83] | -1 | 16% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | crossing | 0.8 | 1.0 | 7 | -8.680 | -7.172 | [-7.66, -6.16] | -1 | 20% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | crossing | 0.8 | 1.2 | 7 | -6.860 | -5.696 | [-5.84, -4.68] | -1 | 19% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | crossing | 1.2 | 0.8 | 7 | +4.693 | +6.598 | [+3.36, +5.26] | +1 | 32% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | crossing | 1.2 | 1.0 | 7 | +6.303 | +7.699 | [+4.97, +6.36] | +1 | 20% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | crossing | 1.2 | 1.2 | 7 | +9.177 | +11.547 | [+7.84, +10.21] | +1 | 23% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | head_on | 0.8 | 0.8 | 7 | -14.271 | -10.747 | [-13.08, -9.56] | -1 | 29% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | head_on | 0.8 | 1.0 | 7 | -13.684 | -9.068 | [-12.50, -7.88] | -1 | 42% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | head_on | 0.8 | 1.2 | 7 | -14.160 | -8.192 | [-12.97, -7.00] | -1 | 51% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | head_on | 1.2 | 0.8 | 7 | +8.867 | +15.123 | [+6.96, +13.22] | +1 | 53% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | head_on | 1.2 | 1.0 | 7 | +9.800 | +14.606 | [+7.90, +12.70] | +1 | 39% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | head_on | 1.2 | 1.2 | 7 | +5.957 | +13.024 | [+4.05, +11.12] | +1 | 71% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | parallel | 0.8 | 0.8 | 7 | -11.089 | -6.848 | [-10.75, -6.50] | -1 | 46% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | parallel | 0.8 | 1.0 | 7 | -8.491 | -4.369 | [-8.15, -4.03] | -1 | 61% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | parallel | 0.8 | 1.2 | 7 | -7.220 | -4.143 | [-6.88, -3.80] | -1 | 53% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | parallel | 1.2 | 0.8 | 7 | +6.302 | +9.652 | [+3.89, +7.24] | +1 | 40% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | parallel | 1.2 | 1.0 | 7 | +6.275 | +10.503 | [+3.86, +8.09] | +1 | 47% | SIGN-CERTIFIED/VALUE-LOOSE |
| lf | parallel | 1.2 | 1.2 | 7 | +7.276 | +15.125 | [+4.86, +12.71] | +1 | 78% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | crossing | 0.8 | 0.8 | 5 | -11.688 | -8.707 | [-10.67, -7.69] | -1 | 31% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | crossing | 0.8 | 1.0 | 5 | -9.212 | -7.014 | [-8.20, -6.00] | -1 | 26% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | crossing | 0.8 | 1.2 | 5 | -8.081 | -6.677 | [-7.06, -5.66] | -1 | 20% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | crossing | 1.2 | 0.8 | 5 | +4.417 | +7.380 | [+3.08, +6.04] | +1 | 46% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | crossing | 1.2 | 1.0 | 5 | +6.638 | +10.623 | [+5.30, +9.29] | +1 | 51% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | crossing | 1.2 | 1.2 | 5 | +8.215 | +11.850 | [+6.88, +10.51] | +1 | 38% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | head_on | 0.8 | 0.8 | 5 | -12.901 | -9.032 | [-11.71, -7.84] | -1 | 35% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | head_on | 0.8 | 1.0 | 5 | -12.045 | -9.040 | [-10.86, -7.85] | -1 | 28% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | head_on | 0.8 | 1.2 | 5 | -12.488 | -8.867 | [-11.30, -7.68] | -1 | 35% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | head_on | 1.2 | 0.8 | 5 | +7.240 | +11.082 | [+5.34, +9.18] | +1 | 41% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | head_on | 1.2 | 1.0 | 5 | +9.797 | +12.560 | [+7.89, +10.66] | +1 | 24% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | head_on | 1.2 | 1.2 | 5 | +9.877 | +12.947 | [+7.97, +11.04] | +1 | 28% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | parallel | 0.8 | 0.8 | 5 | -10.556 | -7.201 | [-10.21, -6.86] | -1 | 39% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | parallel | 0.8 | 1.0 | 5 | -7.807 | -4.071 | [-7.46, -3.73] | -1 | 54% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | parallel | 0.8 | 1.2 | 5 | -6.931 | -4.836 | [-6.59, -4.49] | -1 | 35% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | parallel | 1.2 | 0.8 | 5 | +5.242 | +10.100 | [+2.83, +7.68] | +1 | 59% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | parallel | 1.2 | 1.0 | 5 | +7.519 | +10.620 | [+5.10, +8.20] | +1 | 34% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | parallel | 1.2 | 1.2 | 5 | +8.551 | +11.527 | [+6.13, +9.11] | +1 | 30% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | crossing | 0.8 | 0.8 | 7 | -11.221 | -7.692 | [-10.20, -6.68] | -1 | 35% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | crossing | 0.8 | 1.0 | 7 | -10.090 | -6.653 | [-9.07, -5.64] | -1 | 42% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | crossing | 0.8 | 1.2 | 7 | -7.266 | -5.629 | [-6.25, -4.61] | -1 | 25% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | crossing | 1.2 | 0.8 | 7 | +4.734 | +7.315 | [+3.40, +5.98] | +1 | 40% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | crossing | 1.2 | 1.0 | 7 | +4.076 | +8.881 | [+2.74, +7.55] | +1 | 64% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | crossing | 1.2 | 1.2 | 7 | +7.195 | +12.614 | [+5.86, +11.28] | +1 | 55% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | head_on | 0.8 | 0.8 | 7 | -14.971 | -10.858 | [-13.78, -9.67] | -1 | 33% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | head_on | 0.8 | 1.0 | 7 | -14.465 | -7.482 | [-13.28, -6.29] | -1 | 65% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | head_on | 0.8 | 1.2 | 7 | -11.899 | -7.952 | [-10.71, -6.76] | -1 | 41% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | head_on | 1.2 | 0.8 | 7 | +5.469 | +11.533 | [+3.57, +9.63] | +1 | 70% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | head_on | 1.2 | 1.0 | 7 | +9.290 | +13.441 | [+7.39, +11.54] | +1 | 36% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | head_on | 1.2 | 1.2 | 7 | +9.011 | +13.890 | [+7.11, +11.99] | +1 | 40% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | parallel | 0.8 | 0.8 | 7 | -11.556 | -6.580 | [-11.21, -6.24] | -1 | 57% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | parallel | 0.8 | 1.0 | 7 | -7.912 | -4.158 | [-7.57, -3.81] | -1 | 58% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | parallel | 0.8 | 1.2 | 7 | -6.746 | -4.014 | [-6.40, -3.67] | -1 | 51% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | parallel | 1.2 | 0.8 | 7 | +5.925 | +10.790 | [+3.51, +8.37] | +1 | 59% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | parallel | 1.2 | 1.0 | 7 | +5.958 | +10.414 | [+3.54, +8.00] | +1 | 52% | SIGN-CERTIFIED/VALUE-LOOSE |
| rigid | parallel | 1.2 | 1.2 | 7 | +7.982 | +12.273 | [+5.57, +9.86] | +1 | 44% | SIGN-CERTIFIED/VALUE-LOOSE |