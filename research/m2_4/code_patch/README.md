# code_patch — M2.4

## Added (research only)

- `scripts/m24_jtc.py` — candidate pools shared by every method, engine-exact
  `U_exact`, the five methods at a common 24-evaluation budget, Gate I (`phi_ij`)
  and Gate II (equal-budget coordination) with paired bootstrap

## Nothing else changed

- `backend/src/iron_bottom_sound/**` — untouched; every measurement goes through
  `validate_orders` / `submit_orders` / `advance`, `movement_candidates`,
  `movement_trajectory`, `movement_cost`, `_gunnery_modifiers`, `_mount_can_bear`,
  `_can_see`, `_target_aspect`, and the repaired `FIRE_SEARCH` (visibility,
  mount-once, engine modifiers, concentration/split-fire terms, kind grouping,
  validated gunnery batch)
- frozen trees `research/m2_1`, `research/m2_2`, `research/m2_2r`, `research/m2_3`:
  read-only here, no edits, no re-runs
- no rule changes, no training, no RL/GNN/paper work
