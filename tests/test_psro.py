import json

import pytest

from rl.psro import Config, League, TrainingInterrupted, regret_matching


def test_regret_matching_solves_matching_pennies() -> None:
    mixture = regret_matching([[1.0, -1.0], [-1.0, 1.0]], iterations=3000)
    assert mixture == pytest.approx([0.5, 0.5], abs=0.03)


def test_league_checkpoint_is_resumable_and_dashboard_ready(tmp_path) -> None:
    root = tmp_path / "league"
    config = Config(out=str(root), rounds=0, population=2, generations=1, workers=1)
    league = League(config)
    league._record_game("synthetic", {
        "kind": "matrix", "utility": 1.0, "elapsed_ms": 20, "ok": True,
    })
    league.state["stage"] = "interrupted"
    league._checkpoint()
    assert (root / "dashboard.html").is_file()
    assert not (root / "checkpoint.json.tmp").exists()
    assert (root / "results.sqlite3").is_file()
    checkpoint = json.loads((root / "checkpoint.json").read_text(encoding="utf-8"))
    assert "games" not in checkpoint and checkpoint["game_count"] == 1
    status = json.loads((root / "status.json").read_text(encoding="utf-8"))
    assert status["stage"] == "interrupted"
    assert status["completed_games"] == 1

    resumed = League(config, resume=True)
    assert resumed.state["games"]["synthetic"]["utility"] == 1.0
    resumed.run()
    assert resumed.state["stage"] == "complete"


def test_requested_stop_is_resumable_not_failed(tmp_path) -> None:
    config = Config(out=str(tmp_path / "league"), rounds=1, population=1, generations=1)
    league = League(config)
    league.stop_requested = True
    with pytest.raises(TrainingInterrupted):
        league._run_jobs([("pending", {"kind": "matrix"})])
    assert league.state["stage"] == "interrupted"
    assert league.state["last_error"] is None

    resumed = League(config, resume=True)
    assert resumed.state["stage"] == "interrupted"
