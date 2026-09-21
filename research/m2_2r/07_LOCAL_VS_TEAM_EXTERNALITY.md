# 07_LOCAL_VS_TEAM_EXTERNALITY.md — the two scales, measured

`metrics/mg1_dual_scale.json` (frozen MG1 case, reproduction `true`).

| arm | L0 EH | mounts | ΔL0 | L1 U_team | ΔL1 | externality | flag |
|---|---|---|---|---|---|---|---|
| CURRENT_POLICY | 1.611 | 2 | — | −6.722 | — | — | baseline |
| CURRENT_INTENT_PRE_FIX | 1.556 | 1 | −0.056 | −18.083 | −11.361 | −11.306 | neither |
| REPAIRED_INTENT_BASELINE | 2.278 | 2 | **+0.667** | −12.556 | −5.833 | −6.500 | **MECHANISM_SUCCESS_BUT_NEGATIVE_EXTERNALITY** |
| RANDOM_LEGAL (mean 8) | 2.194 | 2.75 | +0.583 | −8.694 | −1.972 | −2.556 | — |
| BEAM_SEARCH_COMPILER | 2.083 | 3 | +0.472 | **+0.694** | **+7.417** | **+6.944** | — |

Opportunity flags under the frozen thresholds (≥0.05 absolute and ≥25 %
relative for L0; ≥0.05 absolute for L1):

- `CURRENT_INTENT_PRE_FIX`: no opportunity on either scale — the defective
  compiler is dominated by the deployed policy.
- `REPAIRED_INTENT_BASELINE`: `MECHANISM_OPPORTUNITY` true (ΔL0 0.667 = 41 %
  relative), `USABLE_TACTICAL_OPPORTUNITY` false, externality −6.500.
- `BEAM_SEARCH_COMPILER`: opportunity on both scales, positive externality
  +6.944.

## Interpretation

The single-ship intent, once compiled correctly, delivers what it promises
locally (+41 % on the focal pair, and it is the only arm whose L0 gain comes with
the intended arc richness) and costs the fleet 5.8 EH of margin. The joint
search is the only arm that converts the same mechanism into a team gain. That
is the quantitative form of the M2.1-R "exposure is symmetric" result, now split
into the two scales the PI asked for:

- it is **not** a compiler failure — the compiler now compiles the intent;
- it is **not** a rule-engine failure — the pair exchange improves;
- it is a property of the tactic: unmasking one ship's broadside and the
  consequent re-allocation of the whole line's fire.

`RANDOM_LEGAL` beating `REPAIRED_INTENT_BASELINE` on both scales is kept in the
table deliberately: a per-ship intent is not a tactic. In the B1E census the
`REPAIRED_INTENT_BASELINE` arm is a **baseline**, never a candidate method.
