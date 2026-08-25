"""通用人机大战端点 `POST /games/{id}/ai-opponent`。

玩家（X-Player-Side 任一侧）先提交本阶段订单，AI 侧按 body.profile 提交对侧订单；
不返回其私有订单、幂等、不限制 mode/阵营。订单仍由规则引擎 `submit_orders` 校验。
"""

from fastapi.testclient import TestClient

from iron_bottom_sound.api import app, engine as api_engine
from iron_bottom_sound.models import OrderBatch, Phase, Side


def player_batch(side: Side, phase: Phase) -> OrderBatch:
    return OrderBatch(side=side, phase=phase)


def test_vs_ai_game_stores_profile_and_ai_opponent_submits_only_after_player() -> None:
    client = TestClient(app)
    created = client.post(
        "/games",
        json={
            "scenario_id": "IBS-S-03", "seed": 5,
            "options": {"mode": "vs_ai", "ai_profile": "cautious"},
        },
    ).json()
    game_id = created["game_id"]
    state = api_engine.get(game_id)
    assert state.options.mode == "vs_ai"
    assert state.options.ai_profile == "cautious"

    # 玩家提交前 → 409
    premature = client.post(
        f"/games/{game_id}/ai-opponent", headers={"X-Player-Side": "axis"}
    )
    assert premature.status_code == 409

    # 玩家提交增援确认 → AI 提交对侧
    assert client.post(
        f"/games/{game_id}/orders",
        headers={"X-Player-Side": "axis"},
        json=player_batch(Side.AXIS, Phase.REINFORCEMENT).model_dump(mode="json"),
    ).status_code == 200
    response = client.post(
        f"/games/{game_id}/ai-opponent",
        headers={"X-Player-Side": "axis"},
        json={"profile": "cautious"},
    )
    assert response.status_code == 200
    assert response.json() == {"valid": True, "ai_submitted": True}
    assert "orders" not in response.text  # 不泄漏 AI 私有订单

    # 幂等：重复调用短路返回
    again = client.post(
        f"/games/{game_id}/ai-opponent",
        headers={"X-Player-Side": "axis"},
        json={"profile": "balanced"},
    )
    assert again.status_code == 200
    assert again.json() == {"valid": True, "ai_submitted": True}

    # 双方已提交 → 推进到移动计划
    assert client.post(
        f"/games/{game_id}/advance", headers={"X-Player-Side": "axis"}
    ).status_code == 200
    assert api_engine.get(game_id).phase == Phase.MOVEMENT_PLANNING


def test_ai_opponent_unknown_profile_is_422() -> None:
    client = TestClient(app)
    created = client.post(
        "/games",
        json={"scenario_id": "IBS-S-03", "seed": 6, "options": {"mode": "vs_ai"}},
    ).json()
    game_id = created["game_id"]
    assert client.post(
        f"/games/{game_id}/orders",
        headers={"X-Player-Side": "axis"},
        json=player_batch(Side.AXIS, Phase.REINFORCEMENT).model_dump(mode="json"),
    ).status_code == 200
    response = client.post(
        f"/games/{game_id}/ai-opponent",
        headers={"X-Player-Side": "axis"},
        json={"profile": "not-a-profile"},
    )
    assert response.status_code == 422


def test_ai_opponent_works_on_hotseat_game_generically() -> None:
    """通用端点不限定 mode/阵营：热座局也可让 AI 代打一方。"""
    client = TestClient(app)
    created = client.post("/games", json={"scenario_id": "IBS-S-03", "seed": 7}).json()
    game_id = created["game_id"]
    assert client.post(
        f"/games/{game_id}/orders",
        headers={"X-Player-Side": "allies"},
        json=player_batch(Side.ALLIES, Phase.REINFORCEMENT).model_dump(mode="json"),
    ).status_code == 200
    response = client.post(
        f"/games/{game_id}/ai-opponent",
        headers={"X-Player-Side": "allies"},
    )
    assert response.status_code == 200
    assert response.json() == {"valid": True, "ai_submitted": True}


def test_vs_ai_reaches_second_turn_on_either_player_side() -> None:
    """玩家选 axis 或 allies 都能推进到第 2 回合（无交接屏的人机大战闭环）。"""
    order_phases = {"reinforcement", "movement_planning", "torpedo_planning", "gunnery"}
    for player_side in ("axis", "allies"):
        client = TestClient(app)
        created = client.post(
            "/games",
            json={
                "scenario_id": "IBS-S-03", "seed": 11,
                "options": {"mode": "vs_ai", "ai_profile": "fleet"},
            },
        ).json()
        game_id = created["game_id"]
        for _ in range(24):
            view = client.get(
                f"/games/{game_id}/view", headers={"X-Player-Side": player_side}
            ).json()
            if view["turn"] >= 2 or view["phase"] == "complete":
                break
            if view["phase"] in order_phases:
                batch = client.get(
                    f"/games/{game_id}/suggested-orders",
                    headers={"X-Player-Side": player_side},
                ).json()
                assert client.post(
                    f"/games/{game_id}/orders",
                    headers={"X-Player-Side": player_side},
                    json=batch,
                ).status_code == 200
                assert client.post(
                    f"/games/{game_id}/ai-opponent",
                    headers={"X-Player-Side": player_side},
                ).status_code == 200
            assert client.post(
                f"/games/{game_id}/advance", headers={"X-Player-Side": player_side}
            ).status_code == 200
        final_view = client.get(
            f"/games/{game_id}/view", headers={"X-Player-Side": player_side}
        ).json()
        assert final_view["turn"] >= 2
