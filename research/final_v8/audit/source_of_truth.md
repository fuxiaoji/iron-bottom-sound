# Source of Truth (T0 audit, 2026-09-12 11:34:16)

Every core number in paper_v7 traces to a structured result file:
provenance in `provenance_manifest.json`, hashes in `result_hashes.csv`.

- Claims mapped: 15; files hashed: 20; missing: none
- Engine: deterministic conditional on sealed orders and random seed
  (frozen commit fc77a65 per paper preamble).
- Canonical aggregate files:
  - e01/kernel_fits.json (kernel rho=0.9912, nMAE 5.7%)
  - b2..b13 report.md (B-batch canonical numbers)
  - final_v7/must1_aggregate.json (formation commitment: sign 18/18, conv 67%)
  - final_v7/must2_results.json (matched engine: sign 75%, rho -0.083, FAIL)
- Internal experiment codes (B*/MUST*) are repository bookkeeping; the
  manuscript narrative is problem-driven (v8 mandate).
