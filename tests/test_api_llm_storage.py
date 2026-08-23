from fastapi.testclient import TestClient

from iron_bottom_sound.api import app
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
    repository.close()
