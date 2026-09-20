# PRE_REGISTRATION.md — M2.1 thresholds, frozen before any leverage number

Written after P0/P1/P2 infrastructure work and before E0/E1/E2/E3 produced any
statistic. Primary leverage scale: **U1 (normalized material)**, with U0
alongside (plan §14).

## Leverage statistic

`Lambda9010(s) = Q90{Q_E(s,a)} − Q10{Q_E(s,a)}` over the state's validated
candidate actions; `L_range` and `top2 gap` reported alongside.

## Fixed thresholds

| label | rule (U1 scale) |
|---|---|
| low-leverage state | Lambda9010 < 0.05 |
| medium | 0.05 ≤ Lambda < 0.10 |
| high | Lambda ≥ 0.10 |
| pivotal | Lambda ≥ 0.20 with ≥2 evaluators and CI lower bound > 0 |
| HEALTHY_LEVERAGE | strong evaluator (E2/E3) + ≥2 scenarios + ≥30% states Lambda ≥ 0.10, rankings resolvable |
| SCRIPTED_FLATTENING | E0 high < 15% AND E2/E3 ≥ 30% at ≥0.10 AND median strong-evaluator Lambda ≥ 2× E0 AND U3 not low |
| PHASE_LOCALIZED | one phase ≥30% high, another clearly lower, ≥2 scenarios |
| SPARSE_PIVOTAL | median low AND ≥10% states ≥0.20 with 2-evaluator confirmation |
| LOW_LEVERAGE_PLATFORM | all evaluators low, <10% ≥0.10, terminal subset does not recover, with P0/P2 PASS |

## Fixed protocol

- snapshot caps (plan §7): classic 15 movement + 10 gunnery + 5 torpedo per
  scenario; realistic 10 movement + 5 gunnery; 15-20 disruption states reused
  from M2-0 locators; snapshot order = (scenario, profile-pair, seed, turn)
  deterministic, no hand-picking;
- R = 5 replicates (up to 20 if pilot variance demands — pre-declared);
- E1: exactly the 9 pre-registered profile pairs, Q_mix = unweighted mean;
- E2: local minimax on 24-30 diagnostic states, 4-6 focal x 4-6 opponent
  candidates, 1-ply; cost stop per plan §11;
- E3: adversarial = min over the 5-profile pool (fixed);
- bootstrap CI 1000 resamples; "resolvable" = CI lower bound > 0;
- MATCHED_INITIAL_SEEDS_ONLY: no CRN language anywhere (P1);
- terminal subset: S-03 all states to terminal (4 turns); S-01 5-state subset;
  EM-01 3-state subset (time-capped).

## Phase / layer definitions (fixed)

- MOVEMENT snapshot: phase == MOVEMENT_PLANNING; GUNNERY: phase == GUNNERY;
  TORPEDO: phase == TORPEDO_PLANNING.
- Realistic strata: formed / speed-crisis (any formation speed_decision or
  detach in previous turn) / pre-transfer (next event is transfer) /
  disruption (disruption_turn == current turn).
