# DRAFT figure QA record

2026-09-13. Destination: local experimental advisor/review packet, before manuscript writing. No target journal figure compliance is claimed.

All eight PNG figures were opened and inspected locally. All eight single-page vector PDFs were rendered using Poppler at 130 dpi for an additional visual check; rendered pages and a contact sheet are in qa/. Sixteen metadata checks (8 PNG via the requested scientific-visualization skill, minimum 300 dpi; 8 PDF via pdfinfo) completed successfully. Delivered PNGs were exported at 320 dpi. PDF metadata confirms one-page, unencrypted figures with no JavaScript.

|Figure|Evidence/encoding check|Visual result|
|---|---|---|
|A|Fixed head-on probe 0, epoch 0; before/after fields, projected headings, discrete three-endpoint reachability|Labels and separate markers readable; no continuous reachable-region claim; legend stays away from the data|
|B|Fixed opponent own-speed × own-policy factorial|Four value expressions, subtraction and fixed-opponent note readable|
|C|All five exploratory speeds, both fixed opponent classes, three geometries|Initial legend overlapped high points; final delivery wrapper moves legends above data; every reversal retained|
|D|All twelve endpoints, six shared physical contrasts, descriptive rho|Initial upper-left legend obscured one positive point; moved outside the plot on the right; all twelve points visible|
|E|Complete frozen forest table; numerical intervals, no sampling CIs|Five positive and seven negative marks visible, labels and zero line readable; intervals are narrower than points and source values retained|
|F|Six separate T=4 nested-speed interactions|Five positives and head-on/F negative retained; title states separate diagnostic|
|G|Both alpha curves and negative-correction fraction|Markers/line styles supplement color; no smoothing or exclusions; theoretical score is [0,1], plot shows lower [0,.5] portion with an explicit provenance note|
|H|Absolute M and numerical interval widths for twelve fixed IDs|Log axis and series distinctions readable; declared display floor 1e-16 is below the observed nonzero widths|

Only C/D legend layout changed after visual inspection. `v13_figures.py` remains frozen and unchanged; `v13_figures_delivery.py` records the layout correction. Data, signs, transformations, thresholds and source hashes were not changed. Final PDFs were re-rendered after the correction and checked against the PNGs. No clipping, missing labels or obscured data points were observed in the final figures.

The figures use redundant markers/line styles where relevant, textual legends, source tables and descriptions in FIGURE_MANIFEST.json. This local inspection is not a full accessibility certification or a journal production check. No decorative generated image is used as scientific evidence.
