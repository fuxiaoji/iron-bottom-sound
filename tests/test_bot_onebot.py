"""Protocol-only QQ tests: no QQ login, live network or player database."""
import base64
import hashlib
import hmac
import json
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
import pytest

from iron_bottom_sound.bot.onebot import BotSettings, create_onebot_router


PNG = b"\x89PNG\r\n\x1a\n" + b"fake-png-payload"


class DomainError(ValueError):
    code = "forbidden"
    message = "你没有该对局席位"


class FakeService:
    def __init__(self):
        self.calls = []
        self.seen = set()
        self.mutations = 0
        self.denied = False

    def status(self, match_id, **kwargs):
        self.calls.append(("status", match_id, kwargs))
        if self.denied:
            raise DomainError()
        return {"match_id": match_id, "revision": 3, "turn": 1, "phase": "movement",
                "mode": "classic", "opponent": "pvp", "ready": ["allies"],
                "started": True, "complete": False, "summary": "private-summary",
                "observation": {"private": "OWN_ONLY"}, "enemy_orders": "SECRET"}

    def mutate(self, kind, kwargs):
        self.calls.append((kind, kwargs))
        key = kwargs["request_id"]
        if key not in self.seen:
            self.seen.add(key)
            self.mutations += 1
        return self.status(kwargs.get("match_id", "m1"))

    def create(self, **kwargs):
        return self.mutate("create", kwargs)

    def public_status(self, match_id, room_id):
        self.calls.append(("public_status", match_id, {"room_id": room_id}))
        if self.denied:
            raise DomainError()
        return {"match_id": match_id, "revision": 3, "turn": 1, "phase": "movement",
                "mode": "classic", "opponent": "pvp", "summary": "SECRET",
                "observation": {"private": "OWN_ONLY"}}

    def public_screenshot(self, match_id, room_id):
        self.calls.append(("public_screenshot", match_id, {"room_id": room_id}))
        return PNG

    def join(self, match_id, **kwargs):
        return self.mutate("join", {"match_id": match_id, **kwargs})

    def submit(self, match_id, **kwargs):
        if self.denied:
            raise DomainError()
        return self.mutate("submit", {"match_id": match_id, **kwargs})

    def auto(self, match_id, **kwargs):
        # The core caches the semantic auto request before generating suggestions.
        return self.mutate("auto", {"match_id": match_id, **kwargs})

    def catalog(self):
        return [{"scenario_id": "IBS-S-03", "title": "公开想定", "orders": "SECRET"}]

    def matches(self, **kwargs):
        self.calls.append(("matches", kwargs))
        return [self.status("m1")]

    def legal(self, match_id, **kwargs):
        self.status(match_id, **kwargs)
        return {"legal": ["move"]}

    def suggest(self, match_id, **kwargs):
        self.status(match_id, **kwargs)
        return {"orders": {"moves": []}}

    def screenshot(self, match_id, **kwargs):
        self.status(match_id, **kwargs)
        return PNG


@pytest.fixture
def bot():
    service, outgoing = FakeService(), []
    delivery = {"status": "ok", "retcode": 0, "data": {"message_id": 7}}

    def mock_send(request):
        outgoing.append((request, json.loads(request.content)))
        return httpx.Response(200, json=delivery)

    app = FastAPI()
    settings = BotSettings("999", "webhook-secret", "http://napcat.test:3000", "api-token", frozenset({"100"}))
    app.include_router(create_onebot_router(service, settings, transport=httpx.MockTransport(mock_send)))
    with TestClient(app) as client:
        yield client, service, outgoing, delivery


def event(command="状态 m1", *, private=False, mention=True, user=42, group=100, message_id=1):
    segments = [{"type": "text", "data": {"text": "铁底湾 " + command}}]
    if mention:
        segments.insert(0, {"type": "at", "data": {"qq": "999"}})
    return {"post_type": "message", "self_id": 999, "message_type": "private" if private else "group",
            "user_id": user, "group_id": group, "message_id": message_id, "message": segments}


def post(client, payload, *, secret="webhook-secret", signed=True):
    body = json.dumps(payload, ensure_ascii=False).encode()
    headers = {"content-type": "application/json"}
    if signed:
        headers["X-Signature"] = "sha1=" + hmac.new(secret.encode(), body, hashlib.sha1).hexdigest()
    return client.post("/onebot/events", content=body, headers=headers)


@pytest.mark.parametrize("signed,secret", [(False, "webhook-secret"), (True, "wrong")])
def test_requires_hmac(bot, signed, secret):
    client, service, outgoing, _ = bot
    assert post(client, event(), signed=signed, secret=secret).status_code == 403
    assert service.calls == outgoing == []


def test_wrong_bot_and_malformed_sender_rejected(bot):
    client, service, outgoing, _ = bot
    payload = event()
    payload["self_id"] = 998
    assert post(client, payload).status_code == 400
    payload = event(user=True)
    assert post(client, payload).status_code == 400
    assert service.calls == outgoing == []


@pytest.mark.parametrize("change", [{"mention": False}, {"user": 999}, {"group": 200}])
def test_ignores_chatter_self_and_non_whitelisted_groups(bot, change):
    client, service, outgoing, _ = bot
    assert post(client, event(**change)).json() == {"handled": False}
    assert service.calls == outgoing == []


def test_nonmessage_and_string_message_are_ignored(bot):
    client, service, outgoing, _ = bot
    payload = event()
    payload["post_type"] = "notice"
    assert not post(client, payload).json()["handled"]
    payload = event()
    payload["message"] = "[CQ:at,qq=999]铁底湾 状态 m1"
    assert not post(client, payload).json()["handled"]
    assert service.calls == outgoing == []


@pytest.mark.parametrize("text", ["帮助", "铁底湾帮助", "铁底湾 帮助", "铁底湾\u3000帮助", "铁底湾\n帮助"])
def test_group_mention_accepts_known_direct_command_and_prefix_separators(bot, text):
    client, service, outgoing, _ = bot
    payload = event()
    payload["message"][-1]["data"]["text"] = text
    assert post(client, payload).json() == {"handled": True}
    assert "QQ 指令" in outgoing[-1][1]["message"][0]["data"]["text"]
    assert service.calls == []


@pytest.mark.parametrize("text", ["列表", "创建 普通 pve", "加入 m1", "状态 m1", "战况 m1"])
def test_all_known_direct_group_commands_are_dispatched(bot, text):
    client, _, outgoing, _ = bot
    payload = event()
    payload["message"][-1]["data"]["text"] = text
    assert post(client, payload).json() == {"handled": True}
    assert outgoing[-1][1]["group_id"] == 100


@pytest.mark.parametrize("change", [{"mention": False}, {"group": 200}])
def test_direct_commands_still_require_real_mention_and_group_authorization(bot, change):
    client, service, outgoing, _ = bot
    payload = event(**change)
    payload["message"][-1]["data"]["text"] = "创建 普通 pve"
    assert post(client, payload).json() == {"handled": False}
    assert service.calls == outgoing == []


def test_private_still_requires_prefix_and_unknown_group_chatter_is_ignored(bot):
    client, service, outgoing, _ = bot
    for private, text in [(True, "100 m1 态势"), (False, "测试一下机器人")]:
        payload = event(private=private)
        payload["message"][-1]["data"]["text"] = text
        assert post(client, payload).json() == {"handled": False}
    assert service.calls == outgoing == []


def test_ingress_diagnostics_are_fixed_safe_labels(bot, caplog):
    client, service, outgoing, delivery = bot
    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        post(client, event("SECRET_MESSAGE_BODY", group=876543210))
        post(client, event(mention=False))
        payload = event()
        payload["message"] = [{"type": "SECRET_SEGMENT_TYPE", "data": {}}]
        post(client, payload)
        post(client, event(), secret="SECRET_INVALID_TOKEN")
        post(client, event("帮助"))
        delivery.update(status="failed", retcode=100)
        post(client, event("帮助"))
    logs = "\n".join(record.getMessage() for record in caplog.records if record.name == "uvicorn.error")
    assert all(value in logs for value in ["reason=group_denied", "reason=missing_mention", "reason=signature",
                                           "result=handled", "result=delivered", "reason=delivery_failed"])
    assert all(secret not in logs for secret in ["876543210", "qq:42", "SECRET", "webhook-secret", "api-token", "帮助"])
    assert "segments=other" in logs


def test_public_status_and_catalog_use_allowlist(bot):
    client, service, outgoing, _ = bot
    assert post(client, event()).status_code == 200
    request, payload = outgoing[-1]
    text = payload["message"][0]["data"]["text"]
    assert payload["group_id"] == 100
    assert request.url == "http://napcat.test:3000/send_group_msg"
    assert request.headers["authorization"] == "Bearer api-token"
    assert "movement" in text
    assert all(secret not in text for secret in ["private-summary", "OWN_ONLY", "SECRET", "observation"])
    assert service.calls[0] == ("public_status", "m1", {"room_id": "qq:100"})
    post(client, event("列表"))
    assert "公开想定" in outgoing[-1][1]["message"][0]["data"]["text"]
    assert "SECRET" not in json.dumps(outgoing[-1][1])


@pytest.mark.parametrize("command", ["态势 m1", "提交 m1 3 {}", "自动 m1 3", "建议 m1", "行动 m1"])
def test_group_tactics_never_read_or_submit(bot, command):
    client, service, outgoing, _ = bot
    post(client, event(command))
    assert service.calls == []
    assert "私聊" in outgoing[-1][1]["message"][0]["data"]["text"]


def test_create_trusted_identity_and_retry_idempotency_key(bot):
    client, service, outgoing, _ = bot
    payload = event("创建 编队 pvp IBS-S-03 日军")
    assert post(client, payload).status_code == post(client, payload).status_code == 200
    calls = [c[1] for c in service.calls if c[0] == "create"]
    assert service.mutations == 1
    assert calls[0] == calls[1]
    assert calls[0]["actor_id"] == "qq:42"
    assert calls[0]["room_id"] == "qq:100"
    assert calls[0]["mode"] == "formation" and calls[0]["side"] == "axis"
    assert "SECRET" not in json.dumps(outgoing[-1][1])


def test_join_and_matches(bot):
    client, service, outgoing, _ = bot
    post(client, event("加入 m1"))
    assert service.mutations == 1
    post(client, event("状态"))
    assert ("matches", {"actor_id": "qq:42", "room_id": "qq:100"}) in service.calls
    assert "OWN_ONLY" not in json.dumps(outgoing[-1][1])


def test_private_situation_contains_only_authorized_png(bot):
    client, service, outgoing, _ = bot
    assert post(client, event("100 m1 态势", private=True, mention=False)).status_code == 200
    request, payload = outgoing[-1]
    assert str(request.url).endswith("/send_private_msg")
    assert payload["user_id"] == 42
    assert payload["message"][1] == {"type": "image", "data": {"file": "base64://" + base64.b64encode(PNG).decode()}}
    assert all(c[2]["actor_id"] == "qq:42" and c[2]["room_id"] == "qq:100" for c in service.calls)


def test_group_spectators_get_public_map_only(bot):
    client, service, outgoing, _ = bot
    post(client, event("战况 m1", user=77))
    assert service.calls == [("public_status", "m1", {"room_id": "qq:100"}),
                             ("public_screenshot", "m1", {"room_id": "qq:100"})]
    message = outgoing[-1][1]["message"]
    assert message[1]["type"] == "image"
    assert "SECRET" not in message[0]["data"]["text"]
    assert "OWN_ONLY" not in message[0]["data"]["text"]
    service.calls.clear()
    post(client, event("态势 m1", user=77))
    assert not service.calls


@pytest.mark.parametrize("command", ["100 m1 提交 3 {\"moves\": []}", "100 m1 自动 3", "100 m1 确认 3"])
def test_private_mutation_revision_identity_and_image(bot, command):
    client, service, outgoing, _ = bot
    payload = event(command, private=True)
    post(client, payload)
    post(client, payload)
    calls = [c[1] for c in service.calls if c[0] in {"submit", "auto"}]
    assert service.mutations == 1
    assert calls[0]["expected_revision"] == 3
    assert calls[0]["actor_id"] == "qq:42" and calls[0]["room_id"] == "qq:100"
    assert outgoing[-1][1]["message"][1]["type"] == "image"
    if "自动" not in command:
        assert calls[0]["orders"] == ({} if "确认" in command else {"moves": []})


def test_public_domain_errors_do_not_leak_details(bot):
    client, service, outgoing, _ = bot
    service.denied = True
    post(client, event())
    assert "该对局席位" not in outgoing[-1][1]["message"][0]["data"]["text"]


@pytest.mark.parametrize("command", ["200 m1 态势", "100 m1 提交 3 []", "100 m1 提交 3 nope", "100 m1 确认 -1", "100 m1 自动 3 qq:9", "100 m1 提交 3 {} qq:9", '100 m1 提交 3 {"_auto":true}'])
def test_bad_private_context_and_orders_never_mutate(bot, command):
    client, service, outgoing, _ = bot
    assert post(client, event(command, private=True)).status_code == 200
    assert not service.calls
    assert outgoing[-1][1]["user_id"] == 42


def test_unauthorized_private_seat_does_not_render_png(bot):
    client, service, outgoing, _ = bot
    service.denied = True
    post(client, event("100 m1 态势", private=True))
    message = outgoing[-1][1]["message"]
    assert len(message) == 1 and "席位" in message[0]["data"]["text"]
    assert "base64://" not in json.dumps(message)


def test_delivery_failure_returns_failure_and_retry_reuses_mutation(bot):
    client, service, outgoing, delivery = bot
    delivery.update(status="failed", retcode=100)
    payload = event("创建 普通 pve")
    assert post(client, payload).status_code == 502
    delivery.update(status="ok", retcode=0)
    assert post(client, payload).status_code == 200
    assert service.mutations == 1


@pytest.mark.parametrize("command,method", [("行动", "legal"), ("建议", "suggest"), ("状态", "status")])
def test_long_private_json_is_split_losslessly_into_bounded_actions(bot, command, method):
    client, service, outgoing, _ = bot
    expected = {"orders": {"movement": [{"ship_id": "示例舰", "plan": "1P2S3"}] * 180}}
    setattr(service, method, lambda *args, **kwargs: expected)
    assert post(client, event(f"100 m1 {command}", private=True)).status_code == 200
    chunks = [segment["data"]["text"] for _, payload in outgoing for segment in payload["message"]]
    assert len(outgoing) > 2
    assert all(0 < len(text) <= 1500 for text in chunks)
    assert "".join(chunks) == json.dumps(expected, ensure_ascii=False, indent=2)
    assert json.loads("".join(chunks)) == expected
    assert all(payload["user_id"] == 42 for _, payload in outgoing)


def test_later_chunk_failure_fails_whole_request_and_retry_does_not_mutate_twice():
    service, outgoing = FakeService(), []
    original_status = service.status

    def long_status(*args, **kwargs):
        return {**original_status(*args, **kwargs), "summary": "战况连续文字" * 1100}

    service.status = long_status

    def mock_send(request):
        outgoing.append(json.loads(request.content))
        return httpx.Response(200, json={"status": "failed", "retcode": 100}
                              if len(outgoing) == 2 else {"status": "ok", "retcode": 0})

    app = FastAPI()
    settings = BotSettings("999", "webhook-secret", "http://napcat.test", allowed_groups=frozenset({"100"}))
    app.include_router(create_onebot_router(service, settings, transport=httpx.MockTransport(mock_send)))
    with TestClient(app) as client:
        payload = event("100 m1 提交 3 {}", private=True)
        assert post(client, payload).status_code == 502
        assert len(outgoing) == 2  # No image or further fragments after failed acknowledgment.
        assert post(client, payload).status_code == 200
    assert service.mutations == 1
    assert outgoing[0] == outgoing[2]  # At-least-once response replay starts from fragment one.
    replay = outgoing[2:]
    segments = [segment for payload in replay for segment in payload["message"]]
    assert segments[-1]["type"] == "image"
    text = "".join(segment["data"]["text"] for segment in segments if segment["type"] == "text")
    assert text.endswith("战况连续文字" * 1100)
    assert all(sum(len(segment["data"]["text"]) for segment in payload["message"]
                   if segment["type"] == "text") <= 1500 for payload in replay)


@pytest.mark.parametrize("result", [{"status": "ok", "retcode": False}, {"status": "ok"}, {"status": "async", "retcode": 0}])
def test_incomplete_or_non_success_ack_is_not_delivered(bot, result):
    client, _, _, delivery = bot
    delivery.clear()
    delivery.update(result)
    assert post(client, event()).status_code == 502


def test_mutations_without_message_id_rejected(bot):
    client, service, outgoing, _ = bot
    payload = event("创建 普通 pve")
    del payload["message_id"]
    post(client, payload)
    assert not service.calls


def test_required_configuration_fails_closed(monkeypatch):
    for key in ["IBS_ONEBOT_SELF_ID", "IBS_ONEBOT_SECRET", "IBS_ALLOWED_GROUPS"]:
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ValueError):
        BotSettings.from_env()
    for self_id, secret, groups in [("999", "", {"100"}), ("", "secret", {"100"}), ("999", "secret", set())]:
        with pytest.raises(ValueError):
            BotSettings(self_id, secret, allowed_groups=frozenset(groups))
    monkeypatch.setenv("IBS_ONEBOT_SELF_ID", "999")
    monkeypatch.setenv("IBS_ONEBOT_SECRET", "secret")
    monkeypatch.setenv("IBS_ALLOWED_GROUPS", "100, 200")
    assert BotSettings.from_env().allowed_groups == {"100", "200"}
    assert "secret" not in repr(BotSettings.from_env())


@pytest.mark.parametrize("url", ["file:///tmp/api", "https://u:pass@example.com", "https://example.com?token=x"])
def test_api_url_cannot_be_user_supplied_credentials_or_non_http(url):
    with pytest.raises(ValueError):
        BotSettings("999", "secret", url, allowed_groups=frozenset({"100"}))
