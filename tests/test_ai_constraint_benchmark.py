"""Continuation experiments do not reuse development samples as holdout."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from benchmark_ai_constraints import register


def test_continuation_cases_keep_old_weak_sides_and_disjoint_new_seeds():
    cases = register("holdout", 30)
    assert [(case["id"], case["weak_side"]) for case in cases] == [
        ("IBS-S-02", "allies"), ("IBS-S-05", "axis"), ("IBS-S-10", "allies"),
    ]
    seeds = [seed for case in cases for seed in case["seeds"]]
    assert len(seeds) == len(set(seeds)) == 90
    assert min(seeds) == 3001 and max(seeds) == 3230
    assert all(len(case["seeds"]) == 30 for case in cases)
    development = {seed for case in register("development", 6) for seed in case["seeds"]}
    assert not development.intersection(seeds)


def test_development_is_explicitly_separate_from_three_case_holdout():
    cases = register("development", 6)
    assert len(cases) == 1 and cases[0]["id"] == "IBS-S-05"
    assert cases[0]["seeds"] == list(range(2401, 2407))
