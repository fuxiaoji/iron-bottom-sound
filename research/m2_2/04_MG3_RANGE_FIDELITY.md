# 04_MG3_RANGE_FIDELITY.md

Case: `IBS-S-EM-01` seed 1, turn 2, allied BB `IBS-U-USN-ERMA-IOWA` vs nearest
enemy `IBS-U-IJN-ERMA-SHIMAKAZE` (DD). CLOSE plan and OPEN plan built by the
frozen `plan_for_pose` rule.

**Reproduction of the registered arms: exact** — 2.556 vs 0.944 expected hits at
15 vs 17 hexes (M2.1-R2.1 doc records 2.56 vs 0.94, ratio 2.72x).

## M22-F4: the registered meter is not engine-realizable

| quantity | value |
|---|---|
| allied visibility (`state.visibility["allies"]`) | **13 hex** |
| axis visibility | 15 hex |
| optional rules | radar **OFF**, silhouettes OFF, squalls OFF |
| markers (searchlight / star shell) | none |
| CLOSE arm target distance | **15 hex** -> `_can_see = False` |
| OPEN arm target distance | **17 hex** -> `_can_see = False` |
| bearing primary mounts, CLOSE | P1,P2,P3,S-S1,S-S2,S-S3,S-S4,S-S5 |

The engine's gunnery resolution rejects a shot it cannot see
(`gunnery_rejected`, rule 8.1) and the order validator rejects a gunnery order
against an unseen target, so the 8 bearing mounts at 15 hexes can never fire.
The registered MG3 metric checks `_mount_can_bear` only; it has no `_can_see`
gate. MG3 was frozen during the M2.1-R2.1 repair, so it never received the
visibility fix that MG2 and MG4 received (see
`research/m2_1/FAILURES_AND_COUNTEREXAMPLES.md`, fidelity defects; and the
repaired meter `research/m2_1/scripts/mg/legal_fire2.py`).

The historical verdict `MG3_RANGE_CONTROL = VALID PASS` stands as recorded. What
M2.2 adds is the diagnosis: the effect it measured lies entirely outside the
engageable envelope of that state.

## Engine-real panels

| metric | gold | counter | random mean | current policy | intent compiler | beam |
|---|---|---|---|---|---|---|
| fleet margin | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | **+0.639** |
| pair margin | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

Both panels: `GOLD_GAP_NONPOSITIVE`. Moving the BB between 15 and 17 hexes
changes no legal fire at all. The beam's +0.639 comes from other ships in the
12-ship allied force bearing, not from the BB's range control.

## A note on what this does not say

It does not say range control has no value in the rules. The range-modifier
table is steep (M2.1-R2 MG3 and the MG1/MG2 results establish that the rules
price geometry). It says this case, as frozen, cannot measure the compiler: its
gold arm is not executable, and a fidelity ratio on a non-executable gold is
meaningless. A range-control case inside the 13-hex envelope would be a new
case, and building one would be a new pre-registration.
