# B1-ext kernel calibration under mount damage

- damaged mount: P3 (stern primary, firepower 8) destroyed
- held-out Spearman: **0.9951** (gate >= 0.90)
- held-out nMAE: **0.0547** (gate <= 0.15)
- gate: **PASS**
- structural check: stern mean hits 0.000 vs bow 1.407 (stern must be lower after P3 loss)
- interpretation: the kernel's structural sector-firepower term picks up capability state chi automatically from mount.destroyed; no refitting of the arc structure is needed.
