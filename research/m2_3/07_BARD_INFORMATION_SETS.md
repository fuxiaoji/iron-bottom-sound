# 07_BARD_INFORMATION_SETS.md

14 information sets (S-01 4, S-03 6, EM-01 4); rejections `few_valid_variants` 6,
`out_of_range` 4.

## Construction, and the verification the PI required

An information set is a turn's `MOVEMENT_PLANNING` state. The hidden commitment is
the opponent's **sealed movement plan**, which is unresolved at the torpedo
decision instant, so each variant is carried forward to `TORPEDO_PLANNING` and
**both** of the PI's identity requirements are checked in code and fail loudly:

1. the public observation/history hash (`eng.observe`, covering own ships, visible
   enemies, hulls, headings, speeds, tracks and markers) must be **identical**
   across variants — variants that differ are discarded and counted
   (`_hash_mismatch`);
2. the focal legal torpedo action set must be **identical** (compared as a sorted
   signature of launcher × MF × side × angle × setting × salvo) — mismatches are
   discarded and counted (`_action_mismatch`).

In the recorded run no variant was rejected by either check, which is the expected
result: sealed orders are hidden by construction. `observation_hash_identical` and
`action_set_identical` are recorded per set, and the hash prefix is stored.

Only then is each variant advanced to T+1 to obtain the route set that its sealed
plan produces — the quantity that differs across hidden states.

`K = 6` legal victim plans per set, taken in the engine's deterministic candidate
order (never chosen by outcome). Route counts per hidden state, victim positions,
and the full hidden-plan list are in `metrics/m23_bard.json`.
