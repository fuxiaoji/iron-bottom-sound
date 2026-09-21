# 09_IBS_COMPATIBILITY_NOTE.md

**IBS was not used to make any Phase A track pass**, and no IBS result feeds any
Phase A number: Phase A ran entirely in VMAS/BenchMARL. This note is the
engineering compatibility audit the plan asks for, and it is written for whichever
track the PI eventually selects.

| candidate | IBS side | what IBS would have to expose | status |
|---|---|---|---|
| A adaptive planning | Classic primary, Realistic as stress test | a cloneable/replayable decision state plus a simulator that can be branched at a fixed horizon, and a *total* planning-budget accounting identical to the fixed allocations | already demonstrated in this repository: `research/m2_2r` and `research/m2_4` branch sealed states through the engine's own submit/advance path and count exact evaluations — the same accounting Track A needs |
| B/D boundary + resilience | Realistic likely valuable (command shocks/failures are semantically structured) | a perturbation API over (agent, time-window, modality, severity) without changing game rules, plus a hidden evaluation pool | partially demonstrated: observation/action/command perturbations are expressible as order-level changes, and the M2.4 information-set machinery already forks a state and verifies that the public observation is unchanged |
| C attribution | replay/counterfactual branch machinery | counterfactual replay of a *failed* episode with a single cell repaired, at a countable query budget | demonstrated at the mechanism level: the M2.4 `phi_ij` probes are exactly single-cell counterfactual repairs with exact evaluation counting |

No IBS performance result is claimed, and nothing here changes the game rules: the
existing research tree already reaches every operation through the engine's public
entry points (`validate_orders`, `submit_orders`, `advance`) with no rule edits.

## Where IBS would be weaker than VMAS

IBS is a two-sided wargame with an adversarial opponent, whereas Phase A's tracks
assume a cooperative task with a native success signal. An IBS transfer would have
to define success (e.g. objective completion) and would face opponent
nondeterminism inside the counterfactual repairs — a materially harder attribution
setting than the cooperative tasks used here. That is a property to be measured,
not assumed, and it is not measured in this window.
