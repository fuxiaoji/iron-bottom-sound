# 05_JTC_EXTERNALITY.md

`Externality = ΔU − ΔM` per (state, intent, arm), pooled over both supplemental
panels.

| arm | arms-rows | mechanism-opportunity rate | team-beneficial rate | negative-externality rate |
|---|---|---|---|---|
| `REPAIRED_RESEARCH_INTENT` | 208 | 0.135 | 0.087 | **0.067** |
| `JOINT_BEAM_SEARCH` | 150 | 0.233 | 0.153 | **0.107** |
| `RANDOM_MATCHED_BUDGET` | 210 | 0.224 | 0.181 | **0.090** |
| `PER_SHIP_GREEDY` | 192 | 0.292 | 0.193 | **0.161** |

(pooled over both supplemental panels; per-scenario and per-intent cells are in `metrics/m23_verdicts.json`)

Per-scenario and per-intent negative-externality rates, conditional medians and
the full arm table are in `metrics/m23_verdicts.json` (`per_scenario_intent`).

## What the numbers say, including where they contradict the earlier narrative

- `PER_SHIP_GREEDY` has the **highest** negative-externality rate (0.161) and the
  highest mechanism-opportunity rate (0.292): stitching per-ship optima is the
  most locally successful strategy and the most team-costly one. This is the
  cleanest census-scale statement of the externality.
- `JOINT_BEAM_SEARCH` sits at 0.107 — **five times the 0.020 rate the B1E
  unconstrained beam recorded** in `research/m2_2r/`. The reason is structural: the
  JTC beam is lexicographically constrained to reach the intent, so it inherits the
  intent's externality cost instead of avoiding it.
- `REPAIRED_RESEARCH_INTENT` is the **lowest** of the four (0.067), which is the
  opposite of the M2.2/B1E panel where the repaired intent was the worst offender
  (0.165). The difference is the state set, and the honest reading is that the
  single-ship repaired intent is not intrinsically the most harmful arm — on this
  supplemental sample, greedy and the constrained beam are.
- `RANDOM_MATCHED_BUDGET` at 0.090 sits between them.

So the local-vs-team tension is confirmed at census scale, but the ranking of arms
is **not** stable across state sets, and I do not claim one. What the JTC
experiment cannot settle — because of M23-F3 — is whether a better joint compiler
could have both.
