"""用户自备 LLM 密钥 + 科研用途同意（落库 + Server酱通知）的 API 级测试。

覆盖：
- 开局注入 llm_api_key → 仅存进程内存 `_user_llm_keys`（绝不落库/落盘），
  llm-opponent 与战报叙事都优先用它。
- llm-opponent 请求体里的 api_key > 开局注入 > 服务器 env 回退。
- 完全无密钥 → 503（一切 LLM 调用前短路，绝不发请求）。
- research_consent 落库 research_consent 表；allow=False/未传 → 不通知；
  allow=True → 后台通知一次；落库/通知失败都不影响建局。
- Server酱 sender：URL/标题/正文正确、code==0 → True、非 0 码/异常 → False。

全部用 monkeypatch / MockTransport 风格替身，绝不发真实 HTTP。
"""

import os

import httpx
import pytest
from fastapi.testclient import TestClient

from iron_bottom_sound import api, notify
from iron_bottom_sound.api import app
from iron_bottom_sound.models import OrderBatch, Phase, Side
from iron_bottom_sound.storage import GameRepository


@pytest.fixture(autouse=True)
def _isolated_repo_keys_and_notify_env(tmp_path, monkeypatch):
    """每测试独立 DB + 清空用户密钥 + 拔掉通知/env，防跨测试泄漏。

    teardown 必须 close()：Windows 上 sqlite 连接会锁文件，否则 pytest
    清理 tmp_path 时 PermissionError。
    """
    temp_repo = GameRepository(tmp_path / "test.sqlite3")
    monkeypatch.setattr(api, "repository", temp_repo)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("IBS_NOTIFY_CHANNEL", raising=False)
    monkeypatch.delenv("IBS_NOTIFY_SERVERCHAN_KEY", raising=False)
    api._user_llm_keys.clear()
    yield
    api._user_llm_keys.clear()
    temp_repo.close()


class _StubCommander:
    def __init__(self, batch: OrderBatch) -> None:
        self.batch = batch
        self.calls = 0

    def choose_plan(self, engine, game_id, side):
        self.calls += 1
        return None, self.batch, []


def _create(
    client: TestClient,
    mode: str = "hotseat",
    *,
    llm_api_key: str | None = None,
    consent: dict | None = None,
    battle_report: bool = False,
    seed: int = 9001,
) -> str:
    body = {
        "scenario_id": "IBS-S-03",
        "seed": seed,
        "options": {"mode": mode, "battle_report": battle_report},
    }
    if llm_api_key is not None:
        body["llm_api_key"] = llm_api_key
    if consent is not None:
        body["research_consent"] = consent
    return client.post("/games", json=body).json()["game_id"]


def _submit(client: TestClient, game_id: str, side: Side) -> None:
    response = client.post(
        f"/games/{game_id}/orders",
        headers={"X-Player-Side": side.value},
        json=OrderBatch(side=side, phase=Phase.REINFORCEMENT).model_dump(mode="json"),
    )
    assert response.status_code == 200


def _capturing_factory(captured: dict, stub: _StubCommander):
    def factory(timeout, thinking_enabled, api_key=None, config=None):
        captured["api_key"] = api_key
        captured["config"] = config
        return stub
    return factory


# ── 用户自备 LLM 密钥：内存专用，绝不落盘 ─────────────────────────────

def test_create_game_stores_user_key_in_memory_only(monkeypatch) -> None:
    client = TestClient(app)
    game_id = _create(client, "llm", llm_api_key="sk-user-injected")
    assert api._user_llm_keys[game_id] == "sk-user-injected"
    # 密钥绝不进 SQLite（games.state_json / 任何表都查不到）
    blobs = api.repository.connection.execute(
        "SELECT state_json FROM games UNION ALL SELECT COALESCE(handle,'') FROM research_consent"
    ).fetchall()
    assert "sk-user-injected" not in str(blobs)
    assert api.repository.research_consents() == []


def test_llm_opponent_prefers_injected_key(monkeypatch) -> None:
    captured: dict = {}
    client = TestClient(app)
    game_id = _create(client, "llm", llm_api_key="sk-user-injected")
    stub = _StubCommander(OrderBatch(side=Side.ALLIES, phase=Phase.REINFORCEMENT))
    monkeypatch.setattr(api, "llm_commander_factory", _capturing_factory(captured, stub))
    _submit(client, game_id, Side.AXIS)
    response = client.post(f"/games/{game_id}/llm-opponent", headers={"X-Player-Side": "axis"})
    assert response.status_code == 200
    assert captured["api_key"] == "sk-user-injected"


def test_llm_opponent_request_key_beats_injected(monkeypatch) -> None:
    captured: dict = {}
    client = TestClient(app)
    game_id = _create(client, "llm", llm_api_key="sk-injected")
    stub = _StubCommander(OrderBatch(side=Side.ALLIES, phase=Phase.REINFORCEMENT))
    monkeypatch.setattr(api, "llm_commander_factory", _capturing_factory(captured, stub))
    _submit(client, game_id, Side.AXIS)
    response = client.post(
        f"/games/{game_id}/llm-opponent", headers={"X-Player-Side": "axis"},
        json={"api_key": "sk-per-request"},
    )
    assert response.status_code == 200
    assert captured["api_key"] == "sk-per-request"


def test_llm_opponent_uses_server_env_when_no_user_key(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "env-only")
    captured: dict = {}
    client = TestClient(app)
    game_id = _create(client, "llm")
    stub = _StubCommander(OrderBatch(side=Side.ALLIES, phase=Phase.REINFORCEMENT))
    monkeypatch.setattr(api, "llm_commander_factory", _capturing_factory(captured, stub))
    _submit(client, game_id, Side.AXIS)
    response = client.post(f"/games/{game_id}/llm-opponent", headers={"X-Player-Side": "axis"})
    assert response.status_code == 200
    # 无用户密钥时传给工厂的是 None，env 由 _resolve_api_key 在构造时兜底
    assert captured["api_key"] is None


def test_advance_narrative_uses_injected_key(monkeypatch) -> None:
    captured: dict = {}
    client = TestClient(app)
    # battle_report=True 才会走 advance 里的叙事路径
    game_id = _create(client, "hotseat", llm_api_key="sk-narrative", battle_report=True)
    monkeypatch.setattr(api, "capture_phase_snapshot", lambda *a, **k: None)  # 开局快照跳过
    monkeypatch.setattr(
        api, "capture_after_advance",
        lambda *a, commander=None, **k: captured.setdefault("commander", commander),
    )
    _submit(client, game_id, Side.AXIS)
    _submit(client, game_id, Side.ALLIES)
    response = client.post(f"/games/{game_id}/advance", headers={"X-Player-Side": "axis"})
    assert response.status_code == 200
    assert captured["commander"] is not None
    assert captured["commander"].api_key == "sk-narrative"


# ── 科研用途同意：落库 + 通知 ─────────────────────────────────────────

def test_research_consent_saved_and_notified(monkeypatch) -> None:
    notifications: list = []
    monkeypatch.setattr(
        api, "notify_research_consent",
        lambda game_id, allow, handle, scenario: notifications.append((game_id, allow, handle, scenario)),
    )
    client = TestClient(app)
    game_id = _create(client, consent={"allow": True, "handle": "老玩家"})
    rows = api.repository.research_consents()
    assert len(rows) == 1
    assert rows[0]["game_id"] == game_id
    assert rows[0]["allow"] == 1 and rows[0]["handle"] == "老玩家"
    assert rows[0]["scenario"] == "IBS-S-03"
    assert notifications == [(game_id, True, "老玩家", "IBS-S-03")]


def test_research_consent_declined_saved_but_not_notified(monkeypatch) -> None:
    notifications: list = []
    monkeypatch.setattr(api, "notify_research_consent", lambda *a, **k: notifications.append(a))
    client = TestClient(app)
    game_id = _create(client, consent={"allow": False, "handle": None})
    rows = api.repository.research_consents()
    assert len(rows) == 1 and rows[0]["game_id"] == game_id and rows[0]["allow"] == 0
    assert rows[0]["handle"] is None
    assert notifications == []


def test_no_consent_field_records_nothing(monkeypatch) -> None:
    notifications: list = []
    monkeypatch.setattr(api, "notify_research_consent", lambda *a, **k: notifications.append(a))
    client = TestClient(app)
    _create(client)
    assert api.repository.research_consents() == []
    assert notifications == []


def test_consent_save_failure_never_blocks_game_creation(monkeypatch) -> None:
    monkeypatch.setattr(
        api.repository, "save_research_consent",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db down")),
    )
    client = TestClient(app)
    response = client.post(
        "/games",
        json={"scenario_id": "IBS-S-03", "seed": 9002,
              "research_consent": {"allow": True, "handle": "x"}},
    )
    assert response.status_code == 201


# ── Server酱 sender ──────────────────────────────────────────────────

class _FakeClient:
    def __init__(self, captured: dict, *, code: int = 0, raise_on_post: bool = False) -> None:
        self.captured = captured
        self.code = code
        self.raise_on_post = raise_on_post

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def post(self, url: str, data=None):
        if self.raise_on_post:
            raise RuntimeError("network down")
        self.captured["url"] = url
        self.captured["data"] = data
        return _FakeResponse(self.code)


class _FakeResponse:
    def __init__(self, code: int) -> None:
        self.code = code

    def raise_for_status(self):
        pass

    def json(self):
        return {"code": self.code}


def test_serverchan_sender_builds_expected_request(monkeypatch) -> None:
    captured: dict = {}
    monkeypatch.setattr(notify.httpx, "Client", lambda **kw: _FakeClient(captured))
    monkeypatch.setenv("IBS_NOTIFY_CHANNEL", "serverchan")
    monkeypatch.setenv("IBS_NOTIFY_SERVERCHAN_KEY", "SCT-sendkey")
    result = notify.notify_research_consent("g-1", True, "老玩家", "IBS-S-03")
    assert result is True
    assert captured["url"] == "https://sctapi.ftqq.com/SCT-sendkey.send"
    data = captured["data"]
    assert data["title"] == "铁底湾：新的科研用途同意"
    assert "IBS-S-03" in data["desp"] and "g-1" in data["desp"]
    assert "已同意" in data["desp"] and "老玩家" in data["desp"]
    assert "密钥" not in data["desp"] and "订单" not in data["desp"]  # 不携带敏感/私有信息


def test_serverchan_nonzero_code_returns_false(monkeypatch) -> None:
    monkeypatch.setattr(notify.httpx, "Client", lambda **kw: _FakeClient({}, code=40001))
    monkeypatch.setenv("IBS_NOTIFY_CHANNEL", "serverchan")
    monkeypatch.setenv("IBS_NOTIFY_SERVERCHAN_KEY", "SCT-sendkey")
    assert notify.notify_research_consent("g-1", False, None, "IBS-S-03") is False


def test_serverchan_failure_is_swallowed(monkeypatch) -> None:
    monkeypatch.setattr(
        notify.httpx, "Client", lambda **kw: _FakeClient({}, raise_on_post=True)
    )
    monkeypatch.setenv("IBS_NOTIFY_CHANNEL", "serverchan")
    monkeypatch.setenv("IBS_NOTIFY_SERVERCHAN_KEY", "SCT-sendkey")
    assert notify.notify_research_consent("g-1", True, None, "IBS-S-03") is False


def test_notify_returns_false_when_channel_unset(monkeypatch) -> None:
    monkeypatch.delenv("IBS_NOTIFY_CHANNEL", raising=False)
    monkeypatch.delenv("IBS_NOTIFY_SERVERCHAN_KEY", raising=False)
    assert notify.notify_research_consent("g-1", True, None, "IBS-S-03") is False
