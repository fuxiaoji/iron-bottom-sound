"""Tournament accounting is paired; no duplicate, truncated or invalid wins."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest
from iron_bottom_sound import api

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
spec = importlib.util.spec_from_file_location("benchmark_realistic_strength", SCRIPTS / "benchmark_realistic_strength.py")
benchmark = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(SCRIPTS))
spec.loader.exec_module(benchmark)


def game(seed, side, winner, **changes):
    return {"scenario": "fixture", "profile": "rc_coordinated", "opponent": "adaptive",
            "seed": seed, "side": side, "winner": winner, "completed": True,
            "replay_equal": True, "failure": None, **changes}


def test_natural_faction_advantage_is_neutral_not_ai_strength():
    rows = [game(seed, side, "axis") for seed in range(30) for side in ("axis", "allies")]
    summary = benchmark.summarize(rows)
    assert summary["points_rate"] == .5
    assert summary["positive_pairs"] == summary["negative_pairs"] == 0
    assert summary["paired_one_sided_sign_p"] == 1
    assert not summary["strength_gate_pass"]


def test_api_test_repository_is_isolated_from_the_player_database(tmp_path):
    # Exercise the real endpoint: inspecting only the fixture's declared path
    # would miss an API handler accidentally retaining the old repository.
    from fastapi.testclient import TestClient
    from iron_bottom_sound.storage import GameRepository
    client = TestClient(api.app)
    created = client.post("/games", json={"scenario_id": "IBS-S-03", "seed": 5}).json()
    repository = GameRepository(tmp_path / "api-games.sqlite3")
    try:
        assert repository.game_ids() == [created["game_id"]]
    finally:
        repository.close()


def test_real_paired_advantage_passes_predeclared_gate():
    rows = [game(seed, side, side if seed < 25 else ("allies" if side == "axis" else "axis"))
            for seed in range(30) for side in ("axis", "allies")]
    summary = benchmark.summarize(rows)
    assert summary["wins"] == 50
    assert summary["paired_one_sided_sign_p"] < .001
    assert summary["strength_gate_pass"]


@pytest.mark.parametrize("changes", [{"completed": False}, {"replay_equal": False}, {"failure": "illegal"}])
def test_invalid_or_truncated_game_excludes_entire_pair(changes):
    summary = benchmark.summarize([game(1, "axis", "axis"), game(1, "allies", "allies", **changes)])
    assert summary["complete_pairs"] == 0
    assert summary["wins"] == 0
    assert summary["invalid_games"]
    assert not summary["strength_gate_pass"]


@pytest.mark.parametrize("layout", range(6))
@pytest.mark.parametrize("development", [False, True])
def test_generated_multi_formation_custom_scenarios_are_workshop_legal(layout, development):
    definition = benchmark.prepare(benchmark.fleet_scenario(layout, development))
    assert len(definition["ships"]) >= 24
    assert all(len(orders) >= 6 for orders in definition["formations"].values())
    assert definition["setup"]["engine_default_formations"]
