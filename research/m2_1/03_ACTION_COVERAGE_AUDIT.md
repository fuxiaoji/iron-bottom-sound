# 03_ACTION_COVERAGE_AUDIT.md — P2

## Movement (classic) — FAIL for leverage purposes

Generated 8-16 validated joint batches per movement snapshot from: 5 policy
commanders, slower/faster scaling, port/starboard bias, dispersed, hold,
top-2-VP perturbations, 2 random legal. Diversity metrics computed
(endpoint/heading/speed divergence). **But** (user-raised, F8): all sources
are per-ship perturbations of the balanced plan; coordinated tactical plans
(broadside unmasking, T-crossing, range control, torpedo-corridor denial) are
absent. For measuring the platform's TRUE movement leverage this is
insufficient → **movement coverage FAIL pending enrichment**.

## Realistic movement — NOT SAMPLED (interrupted)
Formation-level actions only (policy proposals, leader-route perturbation,
spacing/speed variants); per plan §6.2 no follower bypass.

## Gunnery — PASS with caveat
Per state: 5 policy batches (measured identical — the auto-assigner is
consensus), hold, concentrate-highest-VP, finish-damaged, random-half. All
distinct at order level; validated. Caveat: the identical policy batches mean
effective diversity comes from the 4 hand-built variants.

## Torpedo — NOT SAMPLED (interrupted)

## Verdict
`ACTION_COVERAGE = FAIL` (movement). Not a platform flaw — a generator gap;
fix specified in 05_E0_SCRIPTED_LEVERAGE.md and FAILURES F8.
