"""投影一导出端点 `GET /games/{id}/export`。

纯只读（不落盘）、X-Player-Side 必需、战争迷雾一致（帧+棋盘同源于 observe）。
"""

from fastapi.testclient import TestClient

from iron_bottom_sound.api import app, engine as api_engine
from iron_bottom_sound.models import HexCoord, Side


def _create(client: TestClient, seed: int = 11) -> str:
    created = client.post(
        "/games",
        json={"scenario_id": "IBS-S-03", "seed": seed, "options": {"mode": "llm"}},
    ).json()
    return created["game_id"]


def test_export_requires_player_side_and_404_unknown_game() -> None:
    client = TestClient(app)
    # 未知局优先 404（get_game 先于 header 校验，与其余端点一致）
    assert client.get("/games/UNKNOWN-123/export").status_code == 404
    assert client.get("/games/UNKNOWN-123/export", headers={"X-Player-Side": "axis"}).status_code == 404
    game_id = _create(client)
    # 已知局缺 X-Player-Side → 400
    assert client.get(f"/games/{game_id}/export").status_code == 400
    assert client.get(f"/games/{game_id}/export", headers={"X-Player-Side": "axis"}).status_code == 200


def test_export_returns_frame_and_board() -> None:
    client = TestClient(app)
    game_id = _create(client)
    response = client.get(f"/games/{game_id}/export", headers={"X-Player-Side": "axis"})
    assert response.status_code == 200
    payload = response.json()
    frame = payload["frame"]
    assert frame["side"] == "axis"
    for key in ("game", "turn", "phase", "sequence", "ships", "torpedoes", "markers", "wrecks", "recent_events"):
        assert key in frame
    board = payload["board"]
    assert board.splitlines()[0].split()[:3] == ["A", "B", "C"]
    assert "..=海" in board
    assert frame["game"] == game_id


def test_export_never_saves_state() -> None:
    client = TestClient(app)
    game_id = _create(client)
    state_before = api_engine.get(game_id).turn
    client.get(f"/games/{game_id}/export", headers={"X-Player-Side": "allies"})
    assert api_engine.get(game_id).turn == state_before


def test_export_fog_respects_visibility() -> None:
    client = TestClient(app)
    game_id = _create(client)
    state = api_engine.get(game_id)
    enemy = next(s for s in state.ships.values() if s.side == Side.ALLIES and not s.sunk and s.position)
    enemy.position = HexCoord(q=0, r=0)  # A1，距轴心 O14 20 格 > 视距 4
    axis_frame = client.get(
        f"/games/{game_id}/export", headers={"X-Player-Side": "axis"}
    ).json()["frame"]
    assert enemy.id not in {s["id"] for s in axis_frame["ships"]}
    allies_frame = client.get(
        f"/games/{game_id}/export", headers={"X-Player-Side": "allies"}
    ).json()["frame"]
    assert enemy.id in {s["id"] for s in allies_frame["ships"]}
