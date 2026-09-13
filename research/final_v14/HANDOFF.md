# v14 HANDOFF — resume on a larger machine

Written 2026-09-13. This file is the single entry point for continuing the v14
research line on another computer. It states the repository state, the exact
commands to resume, and the discipline that must not be broken.

---

## 1. Repository state

| item | value |
|---|---|
| remote | `https://github.com/fuxiaoji/iron-bottom-sound.git` (private) |
| branch | `codex/v14-budgeted-replanning` |
| commit at handoff | `09372a9` |
| engine baseline | deterministic conditional on sealed orders and seed |
| Python | 3.11+ with numpy / scipy / pandas / matplotlib; a `.venv` in the repo is used by every script |
| LaTeX | any TeX distribution with `pdflatex`, `natbib`, `booktabs`, `longtable` |

Everything needed is committed: theory, solver modules, tests, the frozen
design, the development-run outputs, the analysis/table/figure/result
generators, the paper working tree, and the reproduction entry point.

```bash
git clone https://github.com/fuxiaoji/iron-bottom-sound.git
cd iron-bottom-sound
git checkout codex/v14-budgeted-replanning
python -m venv .venv && . .venv/bin/activate
pip install -e "backend[dev]" numpy scipy pandas matplotlib
```

## 2. What v14 is

Direction: mathematical theory and operations research first, formation
gameplay as the application. The question is a budgeting one.

> With revisions rationed to a public calendar, how many revisions are needed
> to retain a given fraction of the fully flexible value, when should they
> occur, and can a computation certify the answer?

The controlling plan is `research/final_v14/MASTER_PLAN.md`; the item-by-item
ledger with status is `research/final_v14/PLAN_EXECUTION_LEDGER.md`. Read those
two first, then `PROGRESS.json`.

## 3. Current experimental state

Frozen design: 45 cells (`research/final_v14/DESIGN.json`, hash-checked by
`RUN_FREEZE.json`).

| phase | cells | jobs | status at handoff |
|---|---|---|---|
| development | 9 | 768 | **in progress** — 100 of 292 remaining jobs solved by the parallel dispatcher |
| test | 12 | 960 | not started |
| robustness | 18 | 1008 | not started |
| ablation | 9 | 144 | not started |

Solved jobs are skipped automatically, so resuming costs only the missing
work. `research/final_v14/DISPATCH_PROGRESS.json` and `PROGRESS.json` hold the
live counters; `research/final_v14/runs/<cell>/` holds the value files.

Two solvers exist and both are frozen:

* the official serial pipeline `research/experiments/v14_pipeline.py`
  (development → test → robustness → ablation → certificates → interval
  bounds → benchmarks → analysis), and
* a parallel dispatcher `research/experiments/v14_dispatch.py` that runs the
  **same** jobs through the **same** worker entry point with the **same**
  limits, only with several processes at once.

On the 16 GB machine used for development the dispatcher was memory-bounded,
not core-bounded: each solver process peaks near 0.55 GB, so six workers were
safe. On a larger machine raise `--workers` and `--memory-gb` together.

```bash
# resume the remaining development jobs, then the later phases
python -m research.experiments.v14_dispatch --phase development --workers 12 --memory-gb 24
python -m research.experiments.v14_dispatch --phase test        --workers 12 --memory-gb 24
python -m research.experiments.v14_dispatch --phase robustness  --workers 12 --memory-gb 24
python -m research.experiments.v14_dispatch --phase ablation    --workers 12 --memory-gb 24
```

```bash
# or run the official serial pipeline, which also produces the certificates,
# interval bounds and benchmarks after each phase
python -m research.experiments.v14_pipeline
```

Runtime guide from the measured per-job cost (14–30 s on the development
cells): development ≈ 0.5 h at 12 workers, test ≈ 1 h, ablation ≈ 10 min,
robustness ≈ 2–4 h (Grid-5 and Grid-7 cells are heavier). Certificates,
interval bounds and benchmarks add roughly one further hour.

## 4. Regenerating every product

After the phases finish:

```bash
python reproduce_v14.py                     # verify freeze -> analysis -> tables
                                            # -> figures -> PDF (no re-solving)
python reproduce_v14.py --run-phases        # also run the four solver phases
python reproduce_v14.py --check-only        # integrity checks only
```

`reproduce_v14.py` verifies that the frozen dependencies still hash to their
recorded values before doing anything, so it will refuse to produce outputs
from modified solver code. The individual stages are:

```bash
python research/final_v14/analysis_v14.py        # frontier, retention, summary
python research/final_v14/make_tables_v14.py     # four main tables
python research/final_v14/make_figures_v14.py    # eight main figures
python research/final_v14/make_results_v14.py    # results section from the CSVs
```

Every number in the results section is read from
`research/final_v14/analysis/*.csv`, so the prose cannot drift from the data.
Re-run `make_results_v14.py` after any new phase lands.

## 5. Discipline that must not be broken

1. **Do not change the frozen design.** `DESIGN.json`, the phase assignments,
   the tolerances and the parameter grid are frozen; `RUN_FREEZE.json` records
   the hashes and `reproduce_v14.py` enforces them. If a change is genuinely
   required, version it in a new design file and record why.
2. **One heavy runner at a time in the official pipeline.** The dispatcher is
   allowed to parallelise the same jobs; do not start a second *pipeline*.
3. **A resource limit is a result, not a failure to hide.** A job that hits
   its wall limit is written as `unresolved` with an interval from the global
   payoff minimum and maximum, and is reported that way.
4. **Negatives stay negative.** The range-commitment hypothesis from v12/v13
   is falsified and archived; do not revive it under a new name. The v11
   matched-horizon correction (which removed a commitment claim) is likewise
   archived and disclosed.
5. **No claim of CAS Q1/Q2 competitiveness from software tests alone.** The
   final quality assessment is a separate, explicit deliverable (P18).
6. **Do not invent metadata.** Author names, affiliations, funding and
   acknowledgements are left blank until the author supplies them.

## 6. What remains, by ledger item

| id | requirement | state at handoff | what finishes it |
|---|---|---|---|
| P08 | development, 9 physical / 18 conditions | 100 of 292 remaining jobs solved | `v14_dispatch --phase development` |
| P09 | frozen test, 12 physical / 24 conditions | not started | `--phase test`, then certificates and interval bounds |
| P10 | horizon and action-grid robustness | not started | `--phase robustness` |
| P11 | three one-factor ablations | not started | `--phase ablation` |
| P12 | certified retention budgets, policy replay | analysis code ready; needs P09 data | `make_results_v14.py` + `research/final_v14/recovery_v14.py` |
| P13 | fair algorithm comparison and losses | framework ready | `research/experiments/v14_benchmark.py` (cold and trace modes) |
| P14 | eight figures, four tables | **generators written**; five figures already render from partial data | `make_figures_v14.py`, then visual inspection |
| P15 | full English paper, proofs, supplement, Chinese note | model/theory/algorithm/methods/introduction/discussion/conclusion/results written; abstract and title in place; 14-page PDF builds clean | fill results after P09–P13, add the Chinese note, final proofread |
| P16 | two review rounds | round 1 revised and answered (`reviews/ROUND1_*`) | run round 2 after the results land |
| P17 | reproduction, manifests, environment | `reproduce_v14.py` + freeze verification in place | run once at the end, keep `reproduction_log.json` |
| P18 | journal positioning and candid quality assessment | literature positioning done; ranking check pending | verify scope and rankings against official sources, then write the assessment |

## 7. Skills that were used and are expected to continue

Vendored and provenance-pinned under `research/final_v12/skills/`
(`PROVENANCE.json` records the source repository, commit and SHA-256 for each):

* `scientific-critical-thinking` — design, assumptions, counterexamples
* `peer-review` — the two structured internal review rounds
* `scientific-visualization` — the eight figures (colourblind-safe, vector PDF
  plus 300 dpi PNG, explicit missing-data marks)
* `scientific-writing` — evidence-bound prose, consistency, full manuscript

They are developmental aids in the author's workspace, not independent peer
review and not a journal or ranking certification.

## 8. Copy-paste prompt for the AI on the new machine

> Continue the v14 research line in the repository
> `https://github.com/fuxiaoji/iron-bottom-sound.git`, branch
> `codex/v14-budgeted-replanning`. Work on a machine with more memory and
> cores than the 16 GB laptop used so far.
>
> Start by reading `research/final_v14/HANDOFF.md`,
> `research/final_v14/MASTER_PLAN.md` and
> `research/final_v14/PLAN_EXECUTION_LEDGER.md`, then `PROGRESS.json`.
>
> The destination is a complete paper: theory, certified algorithms, the
> frozen experimental design fully solved, eight figures, four tables, a
> full English manuscript with a proof appendix and a Chinese summary, two
> internal review rounds with responses, a reproduction package, and an
> honest journal-positioning and quality assessment. Do not stop at "the
> experiments ran"; the deliverable is the finished research package.
>
> Concretely:
> 1. Resume the frozen jobs, skipping everything already solved:
>    `python -m research.experiments.v14_dispatch --phase development
>    --workers 12 --memory-gb 24`, then the same for `test`, `robustness`
>    and `ablation`. Then run the official serial stages that produce the
>    certificates, interval bounds and benchmarks
>    (`research/experiments/v14_pipeline.py`) — or run the dispatcher and
>    then those stages individually. Never modify `DESIGN.json` or the
>    frozen tolerances; `reproduce_v14.py --check-only` must keep passing.
> 2. After each phase, regenerate every product:
>    `python research/final_v14/analysis_v14.py`,
>    `python research/final_v14/make_tables_v14.py`,
>    `python research/final_v14/make_figures_v14.py`,
>    `python research/final_v14/make_results_v14.py`. The results section is
>    generated from the analysis CSVs, so it can never drift from the data.
> 3. Finish P12 and P13 (certified retention budgets with policy replay, and
>    the fair algorithm comparison with complete enumeration, branch and
>    bound, and uniform / front-loaded / back-loaded / stepwise greedy at
>    equal model budget and precision, with preprocessing and optimization
>    costs separated).
> 4. Inspect all eight figures yourself and fix negative values, missing
>    data, units, fonts, colours and layout before they go into the paper.
> 5. Complete the manuscript: fill the results, tighten the proofs (every
>    theorem and proposition already has a proof; check quantifiers,
>    feasibility and the scope statements), add the Chinese summary, and
>    rebuild `paper_v14/main.pdf` and `paper_v14/supplement.pdf`.
> 6. Run the second internal review round with the `peer-review` skill on the
>    finished draft and write a response memo; keep round 1's record intact.
> 7. Run `python reproduce_v14.py` end to end and keep
>    `research/final_v14/reproduction_log.json`.
> 8. Write the final positioning and quality assessment: verify the target
>    journal's scope and the current official CAS ranking, state plainly what
>    the work achieves, what is unresolved, and whether the evidence supports
>    a Q1 or a Q2 submission. Do not certify a tier that the evidence does
>    not support, and do not revive the falsified range-commitment claim or
>    the withdrawn commitment claim.
>
> Keep the negatives: a resource limit is reported as an interval, a valid
> certificate is never presented as a tight one, and an ablation that
> overturns a pattern is reported as a boundary of the result.
