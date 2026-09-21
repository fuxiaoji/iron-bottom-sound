# code_patch

## Added (research only)

- `research/m2_2r/scripts/intent_compiler.py` — `REPAIRED_INTENT_BASELINE`
- `research/m2_2r/scripts/test_intent_compiler.py` — unit test
- `research/m2_2r/scripts/b1e.py` — census, MG3-E, identifiability risks
- `research/m2_2r/scripts/mg1_dual.py` — L0/L1 freeze
- `research/m2_2r/scripts/b1e_verdict.py` — frozen verdict mapping + figures

## Deliberately NOT changed

- `research/m2_1/scripts/mg/mg_cases.py` — holds the defective `intent_plans`;
  left byte-identical so `CURRENT_INTENT_PRE_FIX` stays reproducible. The repair
  lives in the new module instead.
- `backend/src/iron_bottom_sound/**` — production engine untouched: no rule
  edits, no AI edits, no constants changed. Every measurement goes through the
  engine's own public entry points (`validate_orders`, `submit_orders`,
  `advance`, `movement_candidates`, `movement_trajectory`, `movement_cost`,
  `_gunnery_modifiers`, `_mount_can_bear`, `_can_see`, `_relative_aspect`,
  `_bearing_between`, `torpedo_tactical_combos`, `_project_torpedo_path`,
  `ship_gun_pressure`).
- `research/m2_2/**` — the M2.2 bundle, its gates and metrics are read-only here.
