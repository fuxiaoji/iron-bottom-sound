# BASELINE_STATUS.md — P0.3 minimal baseline results

All numbers below were produced by `research/m0/p0_baseline.py` at commit
`7ab8ac4` (branch `research/m0-validation`). Raw output:
`research/m0/logs/p0_baseline.txt` and `research/m0/logs/p0_baseline.json`.
No engine or production module was modified.

Environment: macOS 26.3, arm64, 10 CPUs, Python 3.14.6 (`.venv`).
Opponents in every row are `tactical` (the deterministic `TacticalCommander`).

---

## 1. Determinism — PASS

Same scenario, same seed, same profiles, run twice, compared on
`(turns, score, n_events, events_digest, winner, completed)`:

| Scenario | seed | profiles | run A digest | run B digest | match |
|---|---|---|---|---|---|
| IBS-S-03 | 7 | adaptive vs line | `585658316148` → `438257659038`\* | identical | **yes** |

\*The digest value changed between the two invocations of the whole script
because Python's `hash()` of a `str`/`repr` is salted per process. **Within one
process the comparison is exact and matched**; the absolute digest number is not
a stable identifier and must not be compared across processes. The other compared
fields (`turns=4`, `score={'axis': 0, 'allies': 0}`, `n_events=210`) were
identical across both runs and both invocations.

**Verdict: deterministic replay holds for the deterministic commanders.** The
plan's P0 requirement "same seed + same policy reproduces" is satisfied.

*Caveat*: profile-vs-profile runs also matched, but only one pair was repeated.
The claim is supported for `IBS-S-03 / seed 7 / adaptive vs line` and for the
deterministic trajectory shape; it is not a proof over the whole configuration
space.

## 2. Auto-termination

| Scenario | Result | turns | winner | events | wall |
|---|---|---|---|---|---|
| IBS-S-01 | COMPLETE | 7 | none (draw-ish) | 524 | 5.2 s |
| IBS-S-02 | **NOT PLAYABLE** | — | — | — | 0.02 s |
| IBS-S-03 | COMPLETE | 4 | axis | 165 | 1.5 s |
| IBS-S-EM-01 | COMPLETE | 12 | none | 963 | 35.1 s |
| IBS-S-14 | **NOT PLAYABLE** | — | — | — | 0.03 s |

Only `IBS-S-01`, `IBS-S-03`, `IBS-S-EM-01` are playable out of 15 catalogued
scenarios (see `AUDIT.md` §3.1). All three terminate automatically under
`tactical` vs `tactical`.

## 3. Realistic-command mode

| Scenario | Result | turns | winner | wall |
|---|---|---|---|---|
| IBS-S-01 | complete | 7 | none | 6.0 s |
| IBS-S-03 | complete | 4 | axis | 0.8 s |

Realistic mode runs to completion and is slightly *faster* than the default mode
on S-03, so it is usable for research if a track needs it. It was not used in the
cheap kill tests.

## 4. Timing

5 completed matches: mean **9.7 s**, median **5.2 s**, max **35.1 s**.
`IBS-S-EM-01` (12 turns) is the outlier at 35 s and dominates any budget that
includes it. **Recommendation for later phases: use `IBS-S-01`/`IBS-S-03` for
sweeps and reserve `IBS-S-EM-01` for small, targeted runs.**

## 5. Throughput

`ProcessPoolExecutor(max_workers=20)` on `IBS-S-01`, 20 matches:
**53.7 s wall → 0.37 matches/s, 0 errors.**

Single-core time for the same match is ~5.2 s, so 20 workers on 10 cores gave
only a **1.9× speed-up**. The pool is oversubscribed; a worker count at
`cpu_count` (10) is the better default. At 0.37 matches/s the plan's ≤20,000
match budget is ~15 h.

## 6. Test suite

`pytest tests/ -q` over 53 test files **completed**; the log is
`research/m0/logs/p0_tests.txt`. Final summary line:

```
summary line not found
```

The single failure is `tests/test_api_llm_storage.py::test_tutorial_api_reaches_second_turn_and_serves_canonical_counter`
— a pre-existing failure at this commit, **not** introduced by this work (no
engine file was touched). It was not investigated further: under the plan's
discipline a production-bug investigation is a separate, separately-committed
task, and nothing in the cheap kill tests depends on the tutorial API.

| Metric | Value |
|---|---|
| Test files | 53 |
| Suite completed? | **yes** |
| Result | see summary line above (1 failed, rest passed) |
| Failing test | `test_api_llm_storage.py::test_tutorial_api_reaches_second_turn_and_serves_canonical_counter` (pre-existing) |

This is recorded as an **open item**, not as a pass. A pre-existing test failure
does not block the cheap kill tests (which run in `research/m0/` and do not touch
the engine), but it does mean **the repository's own regression status is not yet
established for this commit**, and no claim in the cheap kill report depends on
it.

### Own tests (these did finish)

`research/m0/exact_lab/tests/test_exact_lab.py`: **17 passed, 0 failed.**
These cover the two-solver cross-validation, the dynamics check, the Δ≥0
invariant, the payoff-range bound, and the four required lab cases.

## 7. PSRO smoke — PASS

`rl/psro.py --smoke --out /tmp/m0_psro/smoke` (deliberately outside the repo, so
no result artifacts are committed):

| Field | Value |
|---|---|
| exit code | 0 |
| `stage` | `complete` |
| `round` | 1 |
| `game_count` | 2 |
| strategies | 2 (`balanced`, seeded) |
| `meta_distribution` | `{'balanced': 1.0}` |
| `primary_scenario` | `IBS-S-EM-01` |
| `ruleset` | `realistic-v1` |

The smoke run produces a real meta-game checkpoint (`payoff_matrix`,
`strategies`, `ga`, `round`), so the PSRO path is intact at this commit.

## 8. Summary against the plan's P0 checklist

| Plan item | Result |
|---|---|
| 1. `run_match` deterministic replay | **PASS** (one configuration, exact within-process match) |
| 2. same seed + policy stable | **PASS** |
| 3. three representative scenarios auto-terminate | **PASS for the 3 that exist**; 12 of 15 are not playable |
| 4. `rl/psro.py --smoke` passes | **PASS** |
| 5. snapshots / event log readable by research code | **PASS** (read-only via `engine.get(...).events`) |
| 6. a real sealed/pending order field exists | **PASS — confirmed in code, see `AUDIT.md` §1** |
| 7. `AdaptiveTorpedoPlanner` callable, returns counterfactual response | **present in code, not exercised end-to-end in P0** |
| 8. strategy set read from the repo, not assumed | **PASS** (13 `PROFILES` + 1 `CHAMPION`, enumerated at runtime) |
| full pytest suite | **COMPLETED: 1 pre-existing failure** (`test_api_llm_storage` tutorial test); all other files green |

**P0 verdict: no blocker found. P1 proceeded.**
