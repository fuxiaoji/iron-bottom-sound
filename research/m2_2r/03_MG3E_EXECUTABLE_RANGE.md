# 03_MG3E_EXECUTABLE_RANGE.md — Executable Range-Control Gold

Old MG3 status, frozen and quoted: `HISTORICAL_PROXY_PASS /
EXECUTABLE_GOLD_INVALID` (arms at 15/17 hex against allied visibility 13, radar
rule OFF, `_can_see = False` in both arms, real legal fire 0/0). It is no longer
counted as a confirmed executable mechanism. The old 3/5 gate is untouched.

## Selection, per the frozen rules

Rule 7 required scanning states in `(scenario, seed, turn)` order — **every**
movement-planning state, not only turn 2 — and taking the first that satisfies
rules 1–6, with no look at EH magnitude. The scan ran over the full turn range of
each game; because S-01/S-03/S-EM-01 end at turns 7/4/12, the scan covers turns
2..7, 1..4 and 2..12 respectively.

```
states checked            : 162
rejection reasons         : no_bb_on_side 144 · not_executable 15 · distance_rule 2 · accepted 1
verdict                   : MG3E = PASS
```

## The chosen case

| field | value |
|---|---|
| scenario / seed / turn | `IBS-S-EM-01` / 1 / **10** |
| side, focal | ALLIES, `IBS-U-USN-ERMA-IOWA` (BB) |
| target | `IBS-U-IJN-ERMA-KURAMA` |
| CLOSE arm | plan `1S2P`, **9 hex**, visible, 8 primary mounts bearing, own EH **4.139** |
| OPEN arm | plan `1P1P1P`, **12 hex**, visible, 8 primary mounts bearing, own EH **2.528** |
| enemy return fire | 1.500 (CLOSE) vs 0.694 (OPEN) |
| net EH | **2.639** vs **1.833** |

Gate, frozen before measurement:

```
executable in both arms : PASS (visible and >=1 mount bearing in both)
|Δ own EH| = 1.611 >= 0.05            : PASS
relative   = 0.389 >= 0.25            : PASS
relative on net EH = 0.305 (context)  : PASS
MG3E = PASS
```

Both distances sit **inside** the engageable envelope, which is exactly what the
old MG3 lacked: 9 and 12 hex against allied visibility 13, radar rule off, and
the engine's own `_can_see` true in both arms. All eight bearing mounts in both
arms are primary-battery mounts (`P1..P3`, `S-S1..S-S5` / `S-P1..S-P5`), so the
effect is a battery-wide range effect rather than a single-mount artefact.

Measurement used `FIRE_SEARCH` + engine-validated batches; every arm's movement
batch passed `validate_orders` and both arms were played through real
simultaneous movement to the post-movement / pre-fire instant.

## What this does and does not license

Range control is now an **executable, engine-real** mechanism at a measurable
distance pair within visibility, and Range may therefore enter the B1E census.
It does not revive the old MG3 verdict, it does not add a fifth confirmed
mechanism to any prior gate, and it makes no claim about the size of the range
effect in natural play — that is what the census would measure.
