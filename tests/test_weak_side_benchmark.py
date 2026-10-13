"""Fixed-side accounting must not convert draws, crashes or duplicates to wins."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("benchmark_weak_side", SCRIPTS / "benchmark_weak_side.py")
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


def case(name="fixture", count=30):
    return {"id": name, "weak_side": "axis", "seeds": list(range(count))}


def game(seed, arm, winner, **changes):
    return {"scenario": "fixture", "profile": "rc_coordinated" if arm == "new" else "balanced",
            "opponent": "balanced", "side": "axis", "seed": seed, "arm": arm,
            "winner": winner, "completed": True, "replay_equal": True, "failure": None, **changes}


def test_fixed_weak_side_improves_only_when_new_wins_more():
    rows = [game(seed, arm, "axis" if arm == "new" else "allies")
            for seed in range(30) for arm in ("baseline", "new")]
    summary = benchmark.summarize(rows, [case()])
    layer = summary["by_scenario"]["fixture"]
    assert layer["baseline"]["win_rate"] == 0
    assert layer["new"]["win_rate"] == 1
    assert layer["improved_pairs"] == 30
    assert layer["paired_one_sided_p"] == 2 ** -30
    assert layer["significant_improvement"]


def test_new_losses_to_draws_do_not_improve_primary_win_rate():
    rows = [game(seed, arm, None if arm == "new" else "allies")
            for seed in range(30) for arm in ("baseline", "new")]
    layer = benchmark.summarize(rows, [case()])["by_scenario"]["fixture"]
    assert layer["new"]["points_rate"] == .5
    assert layer["win_rate_change"] == 0
    assert layer["paired_one_sided_p"] == 1
    assert not layer["significant_improvement"]


def test_win_to_draw_is_worsening_and_same_faction_advantage_is_no_improvement():
    rows = [game(seed, arm, None if arm == "new" else "axis")
            for seed in range(30) for arm in ("baseline", "new")]
    layer = benchmark.summarize(rows, [case()])["by_scenario"]["fixture"]
    assert layer["worsened_pairs"] == 30 and layer["paired_one_sided_p"] == 1
    for row in rows:
        row["winner"] = "allies"
    layer = benchmark.summarize(rows, [case()])["by_scenario"]["fixture"]
    assert layer["unchanged_pairs"] == 30 and not layer["significant_improvement"]


@pytest.mark.parametrize("changes", [{"failure": "illegal"}, {"completed": False}, {"replay_equal": False}])
def test_invalid_game_excludes_whole_pair_and_blocks_compatibility(changes):
    rows = [game(seed, arm, "axis" if arm == "new" else "allies")
            for seed in range(30) for arm in ("baseline", "new")]
    rows[0].update(changes)
    layer = benchmark.summarize(rows, [case()])["by_scenario"]["fixture"]
    assert layer["valid_pairs"] == 29
    assert layer["new"]["wins"] == 29 and layer["baseline"]["losses"] == 29
    assert len(layer["invalid_games"]) == layer["invalid_pairs"] == 1
    assert not layer["significant_improvement"]


def test_missing_arms_or_small_samples_cannot_pass():
    summary = benchmark.summarize([game(0, "new", "axis")], [case()])
    assert summary["valid_pairs"] == 0
    assert not summary["completed_attempts"]
    rows = [game(seed, arm, "axis" if arm == "new" else "allies")
            for seed in range(10) for arm in ("baseline", "new")]
    layer = benchmark.summarize(rows, [case(count=10)])["by_scenario"]["fixture"]
    assert layer["paired_one_sided_p"] < .05 and not layer["significant_improvement"]


def test_unrun_scenarios_remain_in_holm_family():
    rows = [game(seed, arm, "axis" if arm == "new" else "allies")
            for seed in range(30) for arm in ("baseline", "new")]
    cases = [case()] + [case(f"unrun-{i}") for i in range(11)]
    layer = benchmark.summarize(rows, cases)["by_scenario"]["fixture"]
    assert layer["holm_p"] == 12 * 2 ** -30
    assert benchmark.holm_adjust({"a": .01, "b": .04, "c": .03, "d": .9}) == {
        "a": .04, "c": .09, "b": .09, "d": .9,
    }


@pytest.mark.parametrize("changes", [{}, {"side": "allies"}, {"seed": 999},
                                      {"opponent": "adaptive"}, {"profile": "balanced"}])
def test_duplicate_or_unregistered_games_rejected(changes):
    rows = [game(0, "new", "axis"), {**game(0, "new", "axis"), **changes}]
    with pytest.raises(ValueError):
        benchmark.summarize(rows, [case()])


def test_preregistered_weak_sides_and_seeds_are_frozen_disjoint():
    cases = benchmark.preregister()
    assert len(cases) == 12
    seeds = [seed for item in cases for seed in item["seeds"]]
    assert len(set(seeds)) == len(seeds) == 360
    by_id = {item["id"]: item for item in cases}
    assert by_id["IBS-S-FM-01"]["weak_side"] == "axis"
    assert by_id["IBS-S-03"]["weak_side"] == "allies"
    assert by_id["IBS-S-03"]["selection_caution"].startswith("S-03 current YAML is only axis 6:4")
    assert by_id["IBS-S-01"]["seeds"] == list(range(1001, 1031))


def recovery_module():
    recovery_spec = importlib.util.spec_from_file_location("resume_weak_side", SCRIPTS / "resume_weak_side.py")
    recovery = importlib.util.module_from_spec(recovery_spec)
    recovery_spec.loader.exec_module(recovery)
    return recovery


def test_recovery_reruns_only_missing_registered_games():
    recovery = recovery_module()
    metadata = {"cases": [case(count=3)], "source_hashes": {"core.py": "frozen"}}
    rows = [game(0, "baseline", "allies"), game(0, "new", "axis"), game(1, "baseline", "axis")]
    tasks = recovery.missing_tasks(rows, metadata)
    assert [(task[2], task[3]) for task in tasks] == [(1, "new"), (2, "baseline"), (2, "new")]
    assert all(task[1] == "axis" and task[4] == metadata["source_hashes"] for task in tasks)


def test_recovery_rejects_duplicate_journal_samples():
    recovery = recovery_module()
    row = game(0, "new", "axis")
    with pytest.raises(ValueError, match="Duplicate"):
        recovery.missing_tasks([row, row], {"cases": [case()], "source_hashes": {}})
