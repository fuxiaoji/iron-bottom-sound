"""LLM 对手端点 `POST /games/{id}/llm-opponent`（llm 模式，玩家对侧 DeepSeek 下单）。

守卫顺序：404 → 403（非 llm mode）→ 400（缺 header）→ 503（用户/服务器均无密钥，
调用前）→ 409（玩家未提交）→ 幂等短路。返回 audits 公开子集，不返回私有订单。
测试用 monkeypatch 注入 stub 指挥官，绝不发真实 HTTP 请求。
"""

import os

from fastapi.testclient import TestClient

from iron_bottom_sound import api
from iron_bottom_sound.api import app
from iron_bottom_sound.models import LLMCallAudit, OrderBatch, Phase, Side


def _player_batch(side: Side, phase: Phase = Phase.REINFORCEMENT) -> OrderBatch:
    return OrderBatch(side=side, phase=phase)


class StubCommander:
    """choose_plan 返回预设 batch + audits，记录调用次数供幂等/不调用断言。"""

    def __init__(self, batch: OrderBatch, audits: list | None = None) -> None:
        self.batch = batch
        self.audits = audits or []
        self.calls = 0

    def choose_plan(self, engine, game_id, side):
        self.calls += 1
        return None, self.batch, self.audits


def _audit() -> LLMCallAudit:
    return LLMCallAudit(
        side=Side.ALLIES, turn=1, phase=Phase.REINFORCEMENT, attempt=1,
        model="deepseek-v4-flash", elapsed_ms=12, input_tokens=100, output_tokens=20,
        valid=True, reasoning_preview="选定南缘入口。",
    )


def _create(client: TestClient, mode: str, seed: int = 21) -> str:
    return client.post(
        "/games",
        json={"scenario_id": "IBS-S-03", "seed": seed, "options": {"mode": mode}},
    ).json()["game_id"]


def test_llm_opponent_403_outside_llm_mode(monkeypatch) -> None:
    client = TestClient(app)
    game_id = _create(client, "hotseat")
    response = client.post(
        f"/games/{game_id}/llm-opponent", headers={"X-Player-Side": "axis"}
    )
    assert response.status_code == 403
    assert "only in llm mode" in response.text


def test_llm_opponent_503_without_key_makes_no_call(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    client = TestClient(app)
    game_id = _create(client, "llm")
    calls: list = []
    monkeypatch.setattr(
        api, "llm_commander_factory",
        lambda timeout, thinking_enabled, api_key=None, config=None: calls.append(timeout),
    )
    response = client.post(
        f"/games/{game_id}/llm-opponent", headers={"X-Player-Side": "axis"}
    )
    assert response.status_code == 503
    assert "请先提供你自己的 LLM API 密钥" in response.text
    assert calls == []  # 密钥缺失时绝不发起任何 LLM 调用


def test_llm_opponent_409_before_player_submits(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only-placeholder")
    client = TestClient(app)
    game_id = _create(client, "llm")
    calls: list = []
    monkeypatch.setattr(
        api, "llm_commander_factory",
        lambda timeout, thinking_enabled, api_key=None, config=None: calls.append(1),
    )
    response = client.post(
        f"/games/{game_id}/llm-opponent", headers={"X-Player-Side": "axis"}
    )
    assert response.status_code == 409
    assert "Submit the player's orders first" in response.text
    assert calls == []


def test_llm_opponent_submits_opponent_and_returns_public_audits(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only-placeholder")
    client = TestClient(app)
    game_id = _create(client, "llm")
    stub = StubCommander(_player_batch(Side.ALLIES), audits=[_audit()])
    monkeypatch.setattr(
        api, "llm_commander_factory",
        lambda timeout, thinking_enabled, api_key=None, config=None: stub,
    )
    assert client.post(
        f"/games/{game_id}/orders",
        headers={"X-Player-Side": "axis"},
        json=_player_batch(Side.AXIS).model_dump(mode="json"),
    ).status_code == 200
    response = client.post(
        f"/games/{game_id}/llm-opponent", headers={"X-Player-Side": "axis"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True and body["ai_submitted"] is True
    assert body["audits"][0]["reasoning_preview"] == "选定南缘入口。"
    assert "elapsed_ms" in body["audits"][0] and "validation_errors" in body["audits"][0]
    assert "orders" not in response.text and "plan" not in response.text  # 不泄漏私有订单
    state = api.engine.get(game_id)
    assert Side.ALLIES.value in state.submitted_orders


def test_llm_opponent_uses_player_selected_zhipu_model_without_persisting_key(monkeypatch) -> None:
    client = TestClient(app)
    secret = "runtime-zhipu-placeholder"
    response = client.post("/games", json={
        "scenario_id": "IBS-S-03",
        "seed": 221,
        "options": {"mode": "llm"},
        "llm_api_key": secret,
        "llm_config": {
            "provider": "zhipu",
            "model": "glm-5.3-flash",
            "vision_enabled": True,
        },
    })
    assert response.status_code == 201
    game_id = response.json()["game_id"]
    stub = StubCommander(_player_batch(Side.ALLIES), audits=[_audit()])
    captured: dict = {}

    def factory(timeout, thinking_enabled, api_key=None, config=None):
        captured.update(api_key=api_key, config=config)
        return stub

    monkeypatch.setattr(api, "llm_commander_factory", factory)
    assert client.post(
        f"/games/{game_id}/orders",
        headers={"X-Player-Side": "axis"},
        json=_player_batch(Side.AXIS).model_dump(mode="json"),
    ).status_code == 200
    assert client.post(
        f"/games/{game_id}/llm-opponent", headers={"X-Player-Side": "axis"}
    ).status_code == 200
    assert captured["api_key"] == secret
    assert captured["config"].provider == "zhipu"
    assert captured["config"].model == "glm-5.3-flash"
    assert captured["config"].vision_enabled is True
    # Repository serialization contains GameState only, never runtime credentials/provider config.
    persisted = api.repository.load(game_id).model_dump_json()
    assert secret not in persisted and "glm-5.3-flash" not in persisted


def test_llm_opponent_idempotent_short_circuit(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only-placeholder")
    client = TestClient(app)
    game_id = _create(client, "llm")
    stub = StubCommander(_player_batch(Side.ALLIES), audits=[_audit()])
    monkeypatch.setattr(
        api, "llm_commander_factory",
        lambda timeout, thinking_enabled, api_key=None, config=None: stub,
    )
    client.post(
        f"/games/{game_id}/orders",
        headers={"X-Player-Side": "axis"},
        json=_player_batch(Side.AXIS).model_dump(mode="json"),
    )
    first = client.post(f"/games/{game_id}/llm-opponent", headers={"X-Player-Side": "axis"})
    assert first.status_code == 200 and stub.calls == 1
    again = client.post(
        f"/games/{game_id}/llm-opponent", headers={"X-Player-Side": "axis"}
    )
    assert again.status_code == 200
    assert again.json() == {"valid": True, "ai_submitted": True, "audits": []}
    assert stub.calls == 1  # 幂等短路，不再调 LLM


def test_llm_opponent_rejects_illegal_ai_orders_without_silent_fix(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only-placeholder")
    client = TestClient(app)
    game_id = _create(client, "llm")
    # 非法对侧订单：给盟军一艘不存在的舰下移动令（本阶段也不该有移动令）。
    illegal = _player_batch(Side.ALLIES)
    illegal.movement = [{"ship_id": "NO-SUCH-SHIP", "plan": "0"}]
    stub = StubCommander(illegal)
    monkeypatch.setattr(
        api, "llm_commander_factory",
        lambda timeout, thinking_enabled, api_key=None, config=None: stub,
    )
    client.post(
        f"/games/{game_id}/orders",
        headers={"X-Player-Side": "axis"},
        json=_player_batch(Side.AXIS).model_dump(mode="json"),
    )
    response = client.post(
        f"/games/{game_id}/llm-opponent", headers={"X-Player-Side": "axis"}
    )
    assert response.status_code == 409  # 引擎拒绝，不静默修复
    state = api.engine.get(game_id)
    assert Side.ALLIES.value not in state.submitted_orders
    # 换成合法空订单后双方齐备，可推进
    stub.batch = _player_batch(Side.ALLIES)
    assert client.post(
        f"/games/{game_id}/llm-opponent", headers={"X-Player-Side": "axis"}
    ).status_code == 200
    advance = client.post(f"/games/{game_id}/advance", headers={"X-Player-Side": "axis"})
    assert advance.status_code == 200
    assert advance.json()  # 引擎裁决事件正常返回
