"""POST_HOC rescue probe for Track D.  NOT part of the pre-declared experiment.

The pre-declared D0 run (identify.py) returned D_FAIL: MYO answered exactly like
OPT and NBU exactly like NOM on every test in the discovery pool, i.e. the
generator's payoff families do not punish myopia or missing lookahead under a
uniform model.

This probe asks a narrower question: is that inseparability STRUCTURAL, or an
artefact of the original family set?  It adds one payoff family ("setup") in
which an early commitment must be steered toward a final-turn target that only
lookahead can see, and re-measures separability and identification on a pool
built from that family alone.

Any result from here is labelled POST_HOC and does not count toward the
pre-declared D0 gate.  It exists so the PI can tell "mechanism unidentifiable in
principle" from "generator lacked the right structure".
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO / "research" / "m0"))

from exact_lab import ExactLab, GameSpec, enumerate_all_nodes  # noqa: E402
from d0_diaggame.zoo import ZOO, agent_answer, regret_of  # noqa: E402
from d0_diaggame.identify import run_identification  # noqa: E402

OUT = REPO / "research" / "m0" / "results"


def setup_payoff(spec, af, ao, t, cum_ao_next):
    """Final-turn-only payoff on a target only lookahead can steer toward:
    +1 if the focal's final action matches the opponent's ACCUMULATED action."""
    if t < spec.T - 1:
        return 0.0
    return 1.0 if af == (cum_ao_next % spec.b) else -1.0


def build_probe_specs():
    specs = []
    for T in (4, 5):
        for K in (3,):
            for L in (2, 3):
                if L > T:
                    continue
                for b in (3,):
                    specs.append(GameSpec(name=f"setup_T{T}b{b}K{K}L{L}",
                                          T=T, b=b, K=K, m=2, L=L,
                                          family="setup", seed=13, alpha=1))
    return specs


def main() -> int:
    # patch the family into the spec/payoff machinery via module-level hooks
    import exact_lab.core as core
    core.FAMILIES = core.FAMILIES + ("setup",)
    original = core.payoff

    def patched(spec, af, ao, t, cum_ao_next):
        if spec.family == "setup":
            return setup_payoff(spec, af, ao, t, cum_ao_next)
        return original(spec, af, ao, t, cum_ao_next)

    core.payoff = patched
    # zoo.py did `from exact_lab import payoff`, so patch its own binding too
    import d0_diaggame.zoo as zoo_mod
    zoo_mod.payoff = patched

    pool = []
    for spec in build_probe_specs():
        lab = ExactLab(spec)
        try:
            nodes = enumerate_all_nodes(spec)
        except RuntimeError:
            continue
        kept = 0
        for (t, af, rf, obs), belief in nodes:
            if rf <= 0 or t >= spec.T:
                continue
            answers = {z: agent_answer(z, spec, lab, (t, af, rf, obs), belief)
                       for z in ZOO}
            regrets = {z: regret_of(spec, lab, (t, af, rf, obs), belief,
                                    answers[z]) for z in ZOO}
            pool.append({"game": spec.name, "spec": spec, "lab": lab,
                         "node": (t, af, rf, obs), "belief": belief,
                         "answers": answers, "regrets": regrets})
            kept += 1
            if kept >= 15:
                break

    never_split = []
    for a in ZOO:
        for b in ZOO:
            if a < b:
                if not any(t["answers"][a] != t["answers"][b] for t in pool):
                    never_split.append((a, b))

    rows = []
    for true_type in ZOO:
        for method in ("random", "disagreement", "infogain"):
            seeds = range(5) if method == "random" else [0]
            for seed in seeds:
                rows.append(run_identification(pool, true_type, method, seed))

    agg = {}
    for method in ("random", "disagreement", "infogain"):
        tests = [r["tests"] for r in rows
                 if r["method"] == method and r["tests"] is not None]
        agg[method] = {"n_identified": len(tests),
                       "median_tests": statistics.median(tests) if tests else None}
    per_type = {}
    for z in ZOO:
        t = [r["tests"] for r in rows if r["true_type"] == z and r["tests"] is not None]
        per_type[z] = {"identified_runs": len(t),
                       "median_tests": statistics.median(t) if t else None}

    summary = {
        "LABEL": "POST_HOC rescue probe - does not count toward the pre-declared gate",
        "family": "setup (final-turn payoff on opponent's accumulated action)",
        "pool_size": len(pool),
        "inseparable_pairs": never_split,
        "methods": agg,
        "per_type": per_type,
        "interpretation": (
            "if MYO/NBU now separate, the pre-declared D_FAIL is "
            "family-limited (generator lacked structure), not a fundamental "
            "unidentifiability; if they still coincide, the defects as "
            "defined are not expressible in this action/commitment model"),
    }
    (OUT / "D0_posthoc_probe.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
