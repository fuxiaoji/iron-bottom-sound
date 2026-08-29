import json
import time

import pytest

import rl.psro as psro
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


def test_corrected_invalid_result_clears_dashboard_error_and_keeps_unique_total(tmp_path) -> None:
    league = League(Config(out=str(tmp_path / "league"), rounds=0, workers=1))
    league._record_game("same-key", {
        "kind": "matrix", "ok": False, "error": "old failure", "elapsed_ms": 1,
    })
    assert league.state["last_error"] == "old failure"
    league._record_game("same-key", {
        "kind": "matrix", "ok": True, "error": None, "elapsed_ms": 1,
    })
    league._checkpoint()
    assert league.state["last_error"] is None
    assert len(league.state["games"]) == 1


def test_status_reports_live_heartbeat_and_stalled_progress(tmp_path) -> None:
    league = League(Config(out=str(tmp_path / "league"), rounds=0, workers=1))
    league.state["running_jobs"] = 3
    league.state["last_progress_at"] = time.time() - 301
    league._status()
    status = json.loads((tmp_path / "league" / "status.json").read_text(encoding="utf-8"))
    assert status["stalled"] is True
    assert status["running_jobs"] == 3
    assert status["progress_age_seconds"] >= 300
    assert time.time() - status["heartbeat"] < 5


def test_atomic_json_retries_transient_windows_permission_error(tmp_path, monkeypatch) -> None:
    target = tmp_path / "status.json"
    real_replace = psro.os.replace
    calls = 0

    def flaky_replace(source, destination):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise PermissionError(5, "temporarily locked")
        return real_replace(source, destination)

    monkeypatch.setattr(psro.os, "replace", flaky_replace)
    monkeypatch.setattr(psro.time, "sleep", lambda _seconds: None)
    psro._atomic_json(target, {"complete": True}, replace_attempts=3)
    assert calls == 3
    assert json.loads(target.read_text(encoding="utf-8")) == {"complete": True}


def test_status_projection_failure_does_not_abort_training(tmp_path, monkeypatch) -> None:
    league = League(Config(out=str(tmp_path / "league"), rounds=0, workers=1))
    real_atomic_json = psro._atomic_json

    def locked_status(path, data, **kwargs):
        if path == league.status_path:
            raise PermissionError(5, "dashboard reader holds destination")
        return real_atomic_json(path, data, **kwargs)

    monkeypatch.setattr(psro, "_atomic_json", locked_status)
    league._status()
    assert "PermissionError" in league.state["status_write_error"]

    monkeypatch.setattr(psro, "_atomic_json", real_atomic_json)
    league._status()
    status = json.loads(league.status_path.read_text(encoding="utf-8"))
    assert "PermissionError" in status["status_write_error"]
    assert "status_write_error" not in league.state


def test_all_training_jobs_use_versioned_realistic_ruleset(tmp_path) -> None:
    league = League(Config(out=str(tmp_path / "league"), rounds=0, workers=1))
    matrix_jobs = league._matrix_jobs()
    assert matrix_jobs
    assert all(key.startswith("realistic-v1|matrix|") for key, _job in matrix_jobs)
    assert all(job["ruleset"] == "realistic-v1" for _key, job in matrix_jobs)
    assert all(job["realistic_command"] is True for _key, job in matrix_jobs)
    assert {job["scenario"] for _key, job in matrix_jobs} == {
        "IBS-S-03", "IBS-S-01", "IBS-S-EM-01",
    }

    population = [{"id": 0, "profile": league.state["strategies"][0]["profile"]}]
    br_jobs = league._br_jobs(0, 0, population, [1.0] * len(league.state["strategies"]))
    assert br_jobs
    assert all(key.startswith("realistic-v1|br|") for key, _job in br_jobs)
    assert all(job["realistic_command"] is True for _key, job in br_jobs)
