# 04 — Track B: Failure-Aware Command Organization

## B0 natural census — PASS (overwhelming)

150 realistic matches (50/scenario, 5x5 profile cells), 150/150 completed.
Matches with command transfer/disruption: S-01 86%, S-03 16%, EM-01 **94%**;
overall **65.3%** (gate: >=5%) with **226** independent transfer cases (gate:
>=30) across 58 scenario x profile cells. EM-01 (24 ships, 12 turns) is the
organizational stress test the plan hoped for: 137 transfers, 446 detaches,
116 dissolutions in 50 matches.

## B1 hierarchy sensitivity — PASS

12 valid natural shock cases (same physical deployment; ONLY
flagship/reserve differ, both submitted as legal formation_setup orders; the
shock is the first natural `formation_command_transferred`):

- 3/12 cases (25%) have H=2 post-shock sensitivity >= 0.05 (gate >=20%);
- max sensitivity **0.767** (EM-01 s102: rev_flagship_g1 beats default by 0.77
  of normalized value);
- both scenarios present (S-01 max 0.20, EM-01 max 0.767).

Recorded honestly: 3 additional cases were dropped because the variant's
shock turn DIFFERED from default's (the hierarchy change itself shifted *when*
the first transfer happens) — this is a real hierarchy effect, not noise, and
it makes the paired analysis conservative. Median sensitivity is 0.000 (most
cases are insensitive), i.e. the effect is real but sparse — the same shape
as every other signal this project has measured.

## B2 robust organization — B_ORACLE_ONLY

7 organization variants x 36 scenario/seed cells, natural shocks, 5 CRN reps,
strict same-shock pairing:

| org | pairs | mean diff vs default | W/L/T |
|---|---|---|---|
| random0/1/2 | 27-31 | +0.04..+0.10 | mostly ties (16-24) |
| flagship_max_vp | 31 | +0.000 — **degenerate: identical to default** (31/31 exact ties; default flagship already max-VP) |
| flagship_low_exposure | 30 | **+0.118 but scenario-opposed**: EM-01 +0.252 (10W/3L/5T), S-01 **-0.083** (2W/5L/5T) |

The coded gate initially printed PASS off a 118,000,000x "relative improvement"
(default mean ~0: small-denominator artifact). Corrected in
`metrics/b2_robust_org.json` with reasoning: no non-future-reading organization
satisfies the >=10% post-shock reduction gate in BOTH scenarios. The one rule
that helps in the 24-ship scenario actively hurts in the 2-scenario S-01.
Verdict: **B_ORACLE_ONLY** — an effect exists (B1 proves it) but it is
scenario-opposed for every simple design rule tried; only an oracle with
future/regime knowledge would pick correctly, which the plan explicitly
excludes from being called a viable AI method.

## Novelty note (moot but recorded)

Track B's structural differentiator — endogenous, adversarially-produced
command-node failure that changes the organizational state and imposes
next-turn control constraints — IS distinct from generic agent dropout. But
with B_ORACLE_ONLY, there is no robust-design result to write about; the
novelty question is moot.
