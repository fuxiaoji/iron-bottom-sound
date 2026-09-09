from __future__ import annotations

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from iron_bottom_sound import api
from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import GameEvent, Side
from iron_bottom_sound.storage import GameRepository


@pytest.fixture
def save_client(tmp_path, monkeypatch):
    repository = GameRepository(tmp_path / "saves.sqlite3")
    game_engine = IronBottomEngine()
    monkeypatch.setattr(api, "repository", repository)
    monkeypatch.setattr(api, "engine", game_engine)
    yield TestClient(api.app), repository, game_engine
    repository.close()


def _create(client: TestClient) -> str:
    response = client.post(
        "/games",
        json={"scenario_id": "IBS-S-03", "seed": 904, "options": {"mode": "hotseat"}},
    )
    assert response.status_code == 201
    return response.json()["game_id"]


def test_save_download_import_clone_and_resume_listing(save_client) -> None:
    client, repository, game_engine = save_client
    game_id = _create(client)

    download = client.get(f"/games/{game_id}/save")
    assert download.status_code == 200
    assert download.headers["content-disposition"].endswith('.ibs-save.json"')
    bundle = download.json()
    assert bundle["format"] == "iron-bottom-sound-save"
    assert bundle["source_game_id"] == game_id
    assert bundle["checksum"].startswith("sha256:")
    assert bundle["state"]["options"].get("llm_api_key") is None

    def browser_numbers(value):
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, dict):
            return {key: browser_numbers(child) for key, child in value.items()}
        if isinstance(value, list):
            return [browser_numbers(child) for child in value]
        return value

    # JSON.parse -> JSON.stringify in browsers removes the `.0` from integral floats.
    imported_response = client.post("/games/import", json=browser_numbers(bundle))
    assert imported_response.status_code == 201, imported_response.text
    imported_id = imported_response.json()["game_id"]
    assert imported_id != game_id
    imported = repository.load(imported_id)
    original = repository.load(game_id)
    left = original.model_dump(mode="json")
    right = imported.model_dump(mode="json")
    left["game_id"] = right["game_id"]
    left["events"][0]["payload"]["game_id"] = right["game_id"]
    assert right == left
    assert game_engine.get(imported_id).game_id == imported_id

    cards = client.get("/games").json()
    imported_card = next(card for card in cards if card["game_id"] == imported_id)
    assert imported_card["scenario_title"] == imported.scenario_title
    assert imported_card["mode"] == "hotseat"
    assert "ships" not in imported_card and "submitted_orders" not in imported_card


def test_import_rejects_tampered_save(save_client) -> None:
    client, _, _ = save_client
    game_id = _create(client)
    bundle = client.get(f"/games/{game_id}/save").json()
    tampered = deepcopy(bundle)
    tampered["state"]["turn"] = 99
    response = client.post("/games/import", json=tampered)
    assert response.status_code == 422
    assert "校验和不匹配" in response.text


def test_replay_uses_saved_checkpoint_and_keeps_fog_of_war(save_client) -> None:
    client, repository, game_engine = save_client
    game_id = _create(client)
    state = game_engine.get(game_id)
    initial_sequence = state.events[-1].sequence
    expected_visible = {
        ship["id"]
        for ship in client.get(
            f"/games/{game_id}/view", headers={"X-Player-Side": Side.AXIS.value}
        ).json()["ships"]
    }

    # A later snapshot must not change the historical checkpoint.
    state.turn = 2
    state.events.append(
        GameEvent(
            sequence=initial_sequence + 1,
            turn=2,
            phase=state.phase,
            type="test_checkpoint",
            message="测试快照",
        )
    )
    repository.save(state)
    checkpoints = client.get(f"/games/{game_id}/replay/checkpoints").json()
    assert checkpoints[0]["sequence"] == initial_sequence

    replay = client.get(
        f"/games/{game_id}/replay?sequence={initial_sequence}",
        headers={"X-Player-Side": Side.AXIS.value},
    )
    assert replay.status_code == 200
    payload = replay.json()
    assert payload["checkpoint_sequence"] == initial_sequence
    assert payload["view"]["turn"] == 1
    # Replay must pass through the same side-filtered observe() projection.
    assert {ship["id"] for ship in payload["view"]["ships"]} == expected_visible
