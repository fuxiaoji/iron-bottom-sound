# 04 — Direction scorecard

| Criterion | E1 Selective Reasoning | E2 Strategic Influence |
|---|---|---|
| Natural signal | PASS (rho sparse, stake 0.333) | PASS (48.5% top-1 changes) |
| Effect size | n/a — gate unlearnable | ~0 (mean +0.02, 60% ties) |
| Simple baseline gap | negative (models <= chance) | negative (shuffled == true) |
| Generalization potential | untestable without a gate | none demonstrated |
| Theory potential | rho itself is clean; the gap is epistemic access | IV(a) definition fine; no measurable effect here |
| Game-AI identity | high (metareasoning) | high (opponent shaping) |
| Engineering cost | low | low |
| Compute cost | low | low-moderate |
| Closest-prior collision | VOI / Learning-When-to-Plan family (not fully reviewed — moot) | opponent shaping family (not fully reviewed — moot) |
| IBS reuse | complete (G1 data reused) | complete |
| Standard benchmark portability | plausible in POMDPs with readable criticality | unproven |
| Biggest reviewer attack | "your gate is a coin flip" (measured) | "your effect is noise" (measured) |
| Verdict | **FAIL (E1_FAIL_PREDICTABILITY)** | **FAIL (E2_FAIL_HEURISTIC_ONLY + E2_FAIL_CAUSALITY)** |
