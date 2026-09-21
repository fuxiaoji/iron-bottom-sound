# 05_B1E_MOVEMENT_CENSUS.md

## Design as executed (frozen in `PRE_REGISTRATION_B1E.md` §5)

52 natural movement states / 104 state-sides: S-01 32, S-03 32, EM-01 40. Every
cheap arm runs on both sides of a state; `BEAM_SEARCH_COMPILER` runs on one side
per state chosen by the state index parity (n = 49 state-sides: 16 / 16 / 17), a
rule that consults no arm's output.

## Coverage actually achieved — reported, not back-filled

| stratum | state-sides |
|---|---|
| `early` (turn ≤ 3) | 62 (+18 shared with `contact`) |
| `contact` (first ≥3-engagement turn) | 8 (+18 early, +4 late) |
| `late` (turn ≥ 8) | 12 (+4 contact) |
| **`damaged` (≥25 % hull lost)** | **0** |

Per-scenario quota shortfalls (frozen rule: reported as numbers, never filled):
**S-01 −4, S-03 −4, EM-01 0**, out of 20 source states each. Two causes, both
structural: S-01 and S-03 end at turns 7 and 4, so `late` is unreachable there;
and with only four labels and no `mid` bucket a mid-game state that is neither
early, the contact turn, damaged nor late carries **no** label and is dropped
from the pool (M22R-F3). **The `damaged` stratum is empty across the whole
census.** Any claim in this bundle about damaged-fleet behaviour would therefore
have no evidence behind it, and none is made.

> **ERRATUM (added in M2.3, M22R-F6).** The explanation originally given here —
> "the scripted balanced commanders do not produce ≥25 % hull loss inside the
> scanned windows" — is **wrong**. The `damaged` predicate was dead code: it read
> `getattr(s, "hull_max", s.hull)` while the model field is `max_hull`, so the
> fraction was identically 1.0. Measured after the fix, **S-01 18/18, S-03 9/9,
> EM-01 24/33** scanned states satisfy "≥1 surviving ship with `hull < max_hull`".
> The stratum was never empty; the label was. The 52-state selection and every
> rate in this file are **unaffected**, because `_hull_frac` only ever assigned a
> label and the picker consumes labels — a dead label changes no selection.

## Pooled results (all 104 state-sides, `metrics/b1e_movement_pooled.json`)

| arm | n | MECHANISM_OPPORTUNITY rate | USABLE_TACTICAL rate | negative-externality rate | median ΔL0 | median ΔL1 | median externality |
|---|---|---|---|---|---|---|---|
| BEAM_SEARCH_COMPILER | 49 | **0.245** | **0.694** | **0.020** | +0.000 | +0.972 | +0.861 |
| REPAIRED_INTENT_BASELINE | 103 | **0.301** | **0.388** | **0.165** | +0.000 | +0.000 | +0.000 |
| CURRENT_INTENT_PRE_FIX | 101 | **0.297** | **0.416** | **0.129** | +0.000 | +0.000 | +0.000 |
| RANDOM_LEGAL | 104 | **0.298** | **0.404** | **0.154** | +0.000 | +0.000 | +0.000 |


## Per scenario

| scenario | arm | mech opportunity | usable tactical | negative externality | median ΔL0 | median ΔL1 | median externality |
|---|---|---|---|---|---|---|---|
| S-01 | BEAM | **0.375** | 0.688 | **0.000** | +0.125 | **+2.792** | **+2.292** |
| S-01 | REPAIRED | 0.469 | 0.250 | 0.312 | +0.111 | −1.778 | −1.986 |
| S-01 | PRE_FIX | 0.484 | 0.290 | 0.258 | +0.111 | −2.139 | −2.222 |
| S-01 | RANDOM | 0.469 | 0.219 | 0.156 | +0.174 | +0.373 | −0.323 |
| S-03 | BEAM | 0.125 | 0.563 | 0.000 | 0.000 | +0.542 | +0.597 |
| S-03 | REPAIRED | 0.323 | 0.290 | 0.194 | −0.083 | −0.222 | −0.250 |
| S-03 | PRE_FIX | 0.323 | 0.323 | 0.161 | 0.000 | 0.000 | −0.111 |
| S-03 | RANDOM | 0.188 | 0.281 | 0.219 | −0.087 | 0.000 | +0.130 |
| EM-01 | BEAM | 0.235 | 0.471 | 0.059 | 0.000 | 0.000 | 0.000 |
| EM-01 | REPAIRED | 0.150 | 0.375 | 0.025 | 0.000 | 0.000 | 0.000 |
| EM-01 | PRE_FIX | 0.128 | 0.359 | 0.000 | 0.000 | 0.000 | 0.000 |
| EM-01 | RANDOM | 0.250 | 0.075 | 0.100 | 0.000 | 0.000 | 0.000 |

## The three opportunity definitions, kept apart

- `MECHANISM_OPPORTUNITY` (local, ≥0.05 abs and ≥25 % rel): present for **every**
  arm at **24.5–30.1 %** of state-sides pooled (beam 0.245, intent arms ~0.30). Local opportunity is common — it is not
  the scarce resource.
- `USABLE_TACTICAL_OPPORTUNITY` (team, ≥0.05 abs): **69.4 % for the beam**, 38.8 %
  (repaired), 41.6 % (pre-fix) and 40.4 % (random). The beam's team gain is ~1.7×
  as likely as any other arm's.
- `TEAM_BENEFICIAL_OPPORTUNITY` = local opportunity *and* ΔL1 > 0: this is where
  the arms separate. The beam's negative-externality rate is **2.0 %** pooled
  (0 % in S-01 and S-03); the other arms sit at 12.9–16.5 % and the repaired
  intent is the worst offender in S-01 (31.2 %).

## The finding that matters most

The intent arms gain locally and lose team utility; the joint search gains both.
In S-01 the repaired intent's median local gain is +0.111 while its median team
change is −1.778, and 31.2 % of its state-sides are
`MECHANISM_SUCCESS_BUT_NEGATIVE_EXTERNALITY`. The beam, on the same states, has
median ΔL1 **+2.792** and a 0 % negative-externality rate (pooled median ΔL1
+0.972, negative-externality rate 2.0 %). This reproduces, at
scale, exactly the pattern the MG1 dual-scale panel showed on one case: the
tactic is real, per-ship compilation of it is not the same thing as a tactic, and
only the joint search converts it.

Note also that `RANDOM_LEGAL` has a *higher* median ΔL0 than the beam in S-01
(+0.174 vs +0.125) while its median ΔL1 is 7× smaller (+0.373 vs +2.792). A
single-ship random perturbation frequently improves the focal pair and rarely
improves the fleet — the clearest illustration in this census of why L0 alone
must never be the target.

## Frozen verdict

```
MOVEMENT_VERDICT = MIXED
  >=2 scenarios with mechanism-opportunity rate >= 20%   : YES (S-01 0.375, EM-01 0.235)
  median SEARCH-over-CURRENT relative local gain >= 0.30 : NO  (0.000)
  random clearly worse (<= 0.5x median SEARCH gain)      : YES
  not driven by one scenario                            : YES
  LOCAL_ONLY_MECHANISM branch: usable rate < 0.10        : NO  (0.694)
                               median externality <= 0   : NO  (+0.861)
  MECHANISM_RARE / NO_NATURAL_GAP branches: max rate 0.375 >= 0.10 -> NO
```

The clause that blocks `NATURAL_COMPILER_GAP` is the **median** relative gain,
and the reason is visible in the distributions: the median state has *zero*
opportunity, so the median is 0 while 23–38 % of states carry material gains.
The rates and the medians answer different questions here, and both are reported;
the frozen rule keys on the median, so the rule returns MIXED rather than
NATURAL_COMPILER_GAP. This is a property of the pre-registered rule, not a
softening of it: the rule was written before these distributions were known and
is applied as written (see `09_NEXT_RESEARCH_DECISION.md` for the metric-design
follow-up).
