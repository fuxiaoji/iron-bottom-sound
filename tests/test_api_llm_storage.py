import hashlib
from urllib.parse import quote

from fastapi.testclient import TestClient

from iron_bottom_sound.api import app, engine as api_engine
from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.llm import DeterministicCommander
from iron_bottom_sound.models import OrderBatch, Phase, Side
from iron_bottom_sound.storage import GameRepository


def test_hotseat_api_requires_side_header() -> None:
    client = TestClient(app)
    created = client.post("/games", json={"scenario_id": "IBS-S-03", "seed": 5}).json()
    assert client.get(f"/games/{created['game_id']}/view").status_code == 400
    assert client.get(
        f"/games/{created['game_id']}/view", headers={"X-Player-Side": "axis"}
    ).status_code == 200


def test_api_supplies_editable_engine_validated_orders() -> None:
    client = TestClient(app)
    created = client.post("/games", json={"scenario_id": "IBS-S-03", "seed": 6}).json()
    game_id = created["game_id"]
    response = client.get(
        f"/games/{game_id}/suggested-orders", headers={"X-Player-Side": "axis"}
    )
    assert response.status_code == 200
    batch = OrderBatch.model_validate(response.json())
    assert batch.side == Side.AXIS
    assert batch.phase == Phase.REINFORCEMENT
    assert client.post(
        f"/games/{game_id}/orders",
        headers={"X-Player-Side": "axis"},
        json=batch.model_dump(mode="json"),
    ).status_code == 200


def test_tutorial_instructor_submits_only_after_player_without_leaking_orders() -> None:
    client = TestClient(app)
    created = client.post(
        "/games",
        json={"scenario_id": "IBS-S-03", "seed": 12, "options": {"mode": "tutorial"}},
    ).json()
    game_id = created["game_id"]
    premature = client.post(
        f"/games/{game_id}/tutorial-opponent", headers={"X-Player-Side": "axis"}
    )
    assert premature.status_code == 409
    player_batch = OrderBatch(side=Side.AXIS, phase=Phase.REINFORCEMENT)
    assert client.post(
        f"/games/{game_id}/orders",
        headers={"X-Player-Side": "axis"},
        json=player_batch.model_dump(mode="json"),
    ).status_code == 200
    response = client.post(
        f"/games/{game_id}/tutorial-opponent", headers={"X-Player-Side": "axis"}
    )
    assert response.status_code == 200
    assert response.json() == {"valid": True, "instructor_submitted": True}
    assert "orders" not in response.text
    assert client.post(
        f"/games/{game_id}/tutorial-opponent", headers={"X-Player-Side": "allies"}
    ).status_code == 403


def test_tutorial_api_reaches_second_turn_and_serves_canonical_counter() -> None:
    client = TestClient(app)
    asset = client.get(f"/assets/counters/{quote('德国-DD-卡尔加尔斯特.png')}")
    assert asset.status_code == 200
    assert asset.headers["content-type"] == "image/png"
    assert hashlib.sha256(asset.content).hexdigest() == (
        "918196c7a6450f13aed798a47f48dd90f659611c49f6677d343878c871714eb6"
    )

    created = client.post(
        "/games",
        json={"scenario_id": "IBS-S-03", "seed": 15, "options": {"mode": "tutorial"}},
    ).json()
    game_id = created["game_id"]
    order_phases = {"reinforcement", "movement_planning", "torpedo_planning", "gunnery"}
    for _ in range(20):
        view = client.get(
            f"/games/{game_id}/view", headers={"X-Player-Side": "axis"}
        ).json()
        if view["turn"] >= 2 or view["phase"] == "complete":
            break
        if view["phase"] in order_phases:
            batch = client.get(
                f"/games/{game_id}/suggested-orders",
                headers={"X-Player-Side": "axis"},
            ).json()
            assert client.post(
                f"/games/{game_id}/orders",
                headers={"X-Player-Side": "axis"},
                json=batch,
            ).status_code == 200
            assert client.post(
                f"/games/{game_id}/tutorial-opponent",
                headers={"X-Player-Side": "axis"},
            ).status_code == 200
        assert client.post(f"/games/{game_id}/advance").status_code == 200
    final_view = client.get(
        f"/games/{game_id}/view", headers={"X-Player-Side": "axis"}
    ).json()
    assert final_view["turn"] >= 2

    hotseat = client.post("/games", json={"scenario_id": "IBS-S-03", "seed": 13}).json()
    assert client.post(
        f"/games/{hotseat['game_id']}/tutorial-opponent",
        headers={"X-Player-Side": "axis"},
    ).status_code == 403


def test_api_hotseat_full_transport_and_persistence_surface() -> None:
    client = TestClient(app)
    assert client.get("/scenarios").status_code == 200
    assert client.post("/games", json={"scenario_id": "missing"}).status_code == 422
    assert client.get("/games/missing/view", headers={"X-Player-Side": "axis"}).status_code == 404

    created = client.post("/games", json={"scenario_id": "IBS-S-03", "seed": 8}).json()
    game_id = created["game_id"]
    assert client.get(
        f"/games/{game_id}/view", headers={"X-Player-Side": "invalid"}
    ).status_code == 400
    assert client.get(
        f"/games/{game_id}/legal-actions", headers={"X-Player-Side": "axis"}
    ).json()[0]["kind"] == "submit_phase_orders"
    assert client.post(f"/games/{game_id}/handoff").json()["clear_sensitive_state"] is True
    assert client.post(f"/games/{game_id}/advance").status_code == 409

    axis = OrderBatch(side=Side.AXIS, phase=Phase.REINFORCEMENT)
    assert client.post(
        f"/games/{game_id}/orders",
        headers={"X-Player-Side": "allies"},
        json=axis.model_dump(mode="json"),
    ).status_code == 403
    wrong_phase = OrderBatch(side=Side.AXIS, phase=Phase.GUNNERY)
    assert client.post(
        f"/games/{game_id}/orders",
        headers={"X-Player-Side": "axis"},
        json=wrong_phase.model_dump(mode="json"),
    ).status_code == 422

    for side in Side:
        batch = OrderBatch(side=side, phase=Phase.REINFORCEMENT)
        response = client.post(
            f"/games/{game_id}/orders",
            headers={"X-Player-Side": side.value},
            json=batch.model_dump(mode="json"),
        )
        assert response.status_code == 200
    assert response.json()["both_submitted"] is True
    assert client.post(f"/games/{game_id}/advance").status_code == 200
    assert client.get(
        f"/games/{game_id}/events?after=0", headers={"X-Player-Side": "axis"}
    ).json()

    api_engine.games.pop(game_id)
    restored = client.get(
        f"/games/{game_id}/view", headers={"X-Player-Side": "axis"}
    )
    assert restored.status_code == 200 and restored.json()["phase"] == "movement_planning"

    with client.websocket_connect(f"/games/{game_id}?side=axis") as socket:
        assert socket.receive_json()["side"] == "axis"
        socket.send_text("refresh")
        assert socket.receive_json()["game_id"] == game_id


def test_fake_llm_returns_engine_validated_conservative_plan() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 1)
    for side in Side:
        assert engine.submit_orders(state.game_id, OrderBatch(side=side, phase=Phase.REINFORCEMENT)).valid
    engine.advance(state.game_id)
    batch = DeterministicCommander().choose_orders(engine, state.game_id, Side.AXIS)
    assert engine.validate_orders(state.game_id, batch).valid


def test_sqlite_round_trip(tmp_path) -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 2)
    repository = GameRepository(tmp_path / "games.sqlite3")
    repository.save(state)
    restored = repository.load(state.game_id)
    assert restored.model_dump(mode="json") == state.model_dump(mode="json")
    assert repository.events(state.game_id)[0].type == "game_created"
    assert repository.game_ids() == [state.game_id]
    repository.close()
