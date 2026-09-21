# 04_MG4_PUBLIC_IDENTIFIABILITY.md — MG4-P

Status vocabulary is the PI's: the only allowed labels are
`PUBLIC_PROXY_AMBIGUITY` and the three-way split **A** representation/objective
gap, **B** belief gap, **C** irreducible public insufficiency. The phrase
`PUBLIC_INFORMATION_GAP` is not used anywhere in this bundle.

## Frozen definitions, as executed

```
D(c,a)          per-route payoff of action a against hidden route c
V_c             = max_a D(c,a)
R_shared(h)     = min_a max_c [ V_c − D(c,a) ]      minimax shared-action regret
R_Bayes_UNIFORM = min_a mean_c [ V_c − D(c,a) ]
DIFFERENT_BEST  = the per-route argmax action is not the same for all c
material        iff R_shared >= 0.25 AND DIFFERENT_BEST
```

`C(h)` = the victim's engine-legal next-turn routes. These are exactly the hidden
states compatible with the shooter's public history: at the launch instant the
victim's next-turn route is committed-but-hidden, and every route in the set is
consistent with the victim's observed position, heading and speed.

## M22R-F2 — my first per-route payoff was degenerate, and how I caught it

The first implementation used `D_bin(c,a) = 1[route c is in contact with a]`. It
produced `R_shared = 1.000` in three states whose full-state ceilings were only
0.071–0.316. That exactness was the tell: with 14–40 compatible routes and one
launch per turn, no action can touch every route, so `R_shared` collapses to 1
whenever `|C(h)|` exceeds one action's reach — it was measuring **action-space
coverage**, not belief conflict. The frozen formula presupposes that `V_c` is
achievable per route, which the binary payoff violates.

Repair: `D_grad(c,a)` = the fraction of route c's own trajectory that action a
blocks, so `V_c` is per-route achievable. Both forms are kept in the record
(`risk_binary`, `R_shared`), and the binary form is reported as the counterexample
rather than deleted. The verdict uses the graded form.

A cross-check that the graded metric is not merely counting routes: EM-01 s1 t3
has **39 coverable of 40 routes** and `R_shared = 0.000` (one action is
simultaneously best for all of them), while S-01 s1 t2 has 28 coverable of 29 and
`R_shared = 0.500`. Route count does not determine the metric.

## Result

| scenario | states | material rate | median R_shared | median R_Bayes |
|---|---|---|---|---|
| IBS-S-01 | 4 | **0.500** | 0.583 | 0.128 |
| IBS-S-03 | 5 | 0.000 | 0.000 | 0.000 |
| IBS-S-EM-01 | 6 | **0.333** | 0.333 | 0.148 |
| pooled | 15 | 0.267 | 0.333 | — |

Material states (frozen thresholds): `R_shared` = 0.500, 0.667, 0.333, 0.333 with
full-state ceilings 0.97, 0.30, 0.07, 0.17 and 2–5 distinct best actions each.
The frozen rule (material in ≥20 % of states in ≥2 scenarios) is met, so

```
TORPEDO_VERDICT = TORPEDO_PARTIAL_OBSERVABILITY
```

with the caveat quantified below, which is part of the result rather than a
footnote: **the ≥2-scenario support is thin in effect size.** The two S-01
material states carry ceilings 0.97 and 0.30 (torpedoes matter), while the two
EM-01 states carry ceilings 0.07 and 0.17 (torpedoes barely matter there), and
S-03 contributes nothing. The strongest evidence for the phenomenon is
single-scenario.

## The public-proxy control, and why it does not settle hypothesis B

The PI's "Public-vs-FullState" comparison was run as a control by evaluating the
same formula on the route set the public actor itself hypothesises (straight-line
walk from the observed position, heading, speed):

| state | R_shared true routes | R_shared public hypotheses | reading |
|---|---|---|---|
| S-01 s1 t2 | 0.500 | 0.200 | public set **understates** the conflict |
| S-01 s1 t6 | n/a (no coverable route) | 0.000 | — |
| S-03 s2 t2 | 0.000 | **0.167** | public set **overstates** it |
| EM-01 s1 t4 | n/a | 0.200 | — |
| EM-01 s1 t10 | n/a | 0.333 | — |

The comparison moves in **both** directions, so it cannot separate the
observational component on its own: the public hypothesis set has a different
size and a different diversity from the true route set, and the metric responds
to both. What can be said honestly:

- the per-route commitment conflict measured on the **true** compatible set is
  material in 4 of 15 states across 2 scenarios — that is hypothesis-**C**-shaped
  evidence, since the set is genuinely hidden at the launch instant;
- a straight-line public proxy is **not** a faithful stand-in for it (it was
  optimistic in one state and pessimistic in another);
- a decisive separation of the observational component (hypothesis B) would need
  a size/diversity-matched control over subsets of `C(h)`. That control is **not**
  in the frozen design and was therefore not run. It is listed as the first
  follow-up in `09_NEXT_RESEARCH_DECISION.md`.

## Status

MG4 goes from `PUBLIC_PROXY_AMBIGUITY = CONFIRMED` to
`TORPEDO_PARTIAL_OBSERVABILITY = CONFIRMED (material commitment regret in 4/15
states, ≥2 scenarios, single-scenario-dominant effect size)`. Per the PI's
instruction this qualifies the topic for an independent CCF-A novelty review —
but it remains **`STRONG_RESEARCH_SEED`, not a main line**, until that review and
the matched control exist.
