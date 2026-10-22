"""Tencent official webhook protocol tests, using an offline HTTP transport."""
import base64
from datetime import datetime, timezone
import hashlib
import json
import logging
import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
import pytest

from iron_bottom_sound.bot.qq_official import ACK, API, TOKEN_URL, QQOfficialSettings, create_qq_official_router

SECRET = "official-test-secret"
PNG = b"\x89PNG\r\n\x1a\n" + b"map"


def signing_key(secret=SECRET):
    seed = secret.encode()
    while len(seed) < 32:
        seed += seed
    return Ed25519PrivateKey.from_private_bytes(seed[:32])


class DomainError(ValueError):
    code, message = "forbidden", "未绑定该席位"


class FakeService:
    def __init__(self):
        self.calls, self.receipts, self.mutations = [], {}, 0
        self.denied = False

    def snapshot(self, match="match1"):
        return {"match_id": match, "revision": 2, "phase": "movement_planning", "turn": 1,
                "mode": "classic", "opponent": "pvp", "ready": [], "started": True,
                "complete": False, "summary": "本方战况", "observation": {"secret": "OWN"},
                "enemy_orders": "NEVER_PUBLIC"}

    def mutate(self, op, **kwargs):
        self.calls.append((op, kwargs))
        rid = kwargs["request_id"]
        if rid not in self.receipts:
            self.mutations += 1
            self.receipts[rid] = self.snapshot(kwargs.get("match_id", "match1"))
        return self.receipts[rid]

    def catalog(self):
        self.calls.append(("catalog", {}))
        return [{"scenario_id": "IBS-S-03", "title": "公共想定", "private": "NEVER_PUBLIC"}]

    def create(self, **kwargs):
        return self.mutate("create", **kwargs)

    def join(self, match_id, **kwargs):
        return self.mutate("join", match_id=match_id, **kwargs)

    def submit(self, match_id, **kwargs):
        return self.mutate("submit", match_id=match_id, **kwargs)

    def auto(self, match_id, **kwargs):
        return self.mutate("auto", match_id=match_id, **kwargs)

    def status(self, match_id, **kwargs):
        self.calls.append(("status", {"match_id": match_id, **kwargs}))
        if self.denied:
            raise DomainError()
        return self.snapshot(match_id)

    def public_status(self, match_id, **kwargs):
        self.calls.append(("public_status", {"match_id": match_id, **kwargs}))
        return self.snapshot(match_id)

    def screenshot(self, match_id, **kwargs):
        self.calls.append(("screenshot", {"match_id": match_id, **kwargs}))
        if self.denied:
            raise DomainError()
        return PNG

    def public_screenshot(self, match_id, **kwargs):
        self.calls.append(("public_screenshot", {"match_id": match_id, **kwargs}))
        return PNG

    def legal(self, match_id, **kwargs):
        self.calls.append(("legal", {"match_id": match_id, **kwargs}))
        return {"match_id": match_id, "revision": 2, "actions": [{"ship_id": "ship1", "kind": "move"}]}

    def manual_actions(self, match_id, **kwargs):
        self.calls.append(("manual_actions", {"match_id": match_id, **kwargs}))
        if self.denied:
            raise DomainError()
        return {"text": "行动第1页 · ship1\n编号 move1：前进\n/选择 2 move1 " + match_id}

    def manual_draft(self, match_id, **kwargs):
        self.calls.append(("manual_draft", {"match_id": match_id, **kwargs}))
        return {"text": "草稿：尚未选择行动"}

    def manual_choose(self, match_id, **kwargs):
        self.calls.append(("manual_choose", {"match_id": match_id, **kwargs}))
        return {"text": "已加入草稿，尚未提交"}

    def manual_clear(self, match_id, **kwargs):
        self.calls.append(("manual_clear", {"match_id": match_id, **kwargs}))
        return {"text": "草稿已清空，未推进"}

    def manual_submit(self, match_id, **kwargs):
        return self.mutate("manual_submit", match_id=match_id, **kwargs)

    def suggest(self, match_id, **kwargs):
        self.calls.append(("suggest", {"match_id": match_id, **kwargs}))
        return {"revision": 2, "orders": {"movement": []}}

    def matches(self, **kwargs):
        self.calls.append(("matches", kwargs))
        return [self.snapshot()]

    def issue_identity_link(self, **kwargs):
        self.calls.append(("issue_identity_link", kwargs))
        return {"code": "PRIVATE_BINDING_CODE", "expires_in": 300}

    def claim_identity_link(self, code, **kwargs):
        self.calls.append(("claim_identity_link", {"code": code, **kwargs}))
        return {"linked": True, "c2c_actor": "PRIVATE_C2C_ID"}


@pytest.fixture
def bot():
    service, seen, control = FakeService(), [], {"fail_at": None, "bad_ack": False, "token_expiry": "7200"}

    def http(request):
        payload = json.loads(request.content)
        seen.append((str(request.url), payload, dict(request.headers)))
        if str(request.url) == TOKEN_URL:
            return httpx.Response(200, json={"access_token": "PRIVATE_ACCESS_TOKEN", "expires_in": control["token_expiry"]})
        assert request.headers["authorization"] == "QQBot PRIVATE_ACCESS_TOKEN"
        assert str(request.url).startswith(API)
        if request.url.path.endswith("/files"):
            return httpx.Response(200, json={"file_info": "PRIVATE_FILE_INFO", "ttl": 86400})
        count = sum(url.endswith("/messages") for url, _, _ in seen)
        if control["fail_at"] == count:
            return httpx.Response(200, json={"code": 22009, "message": "PRIVATE_API_ERROR"})
        return httpx.Response(200, json={} if control["bad_ack"] else {"id": "reply-" + str(count)})

    settings = QQOfficialSettings("12345", SECRET, frozenset({"GROUP"}))
    app = FastAPI()
    app.include_router(create_qq_official_router(service, settings, transport=httpx.MockTransport(http)))
    with TestClient(app) as client:
        yield client, service, seen, control


def event(content="帮助", *, private=False, message_id="message-one", sender="MEMBER", group="GROUP", age=0):
    data = {"id": message_id, "content": content,
            "timestamp": datetime.fromtimestamp(time.time() - age, timezone.utc).isoformat(),
            "author": {"user_openid" if private else "member_openid": sender}}
    if not private:
        data["group_openid"] = group
    return {"op": 0, "t": "C2C_MESSAGE_CREATE" if private else "GROUP_AT_MESSAGE_CREATE", "d": data}


def post(client, payload, *, signed=True, age=0, secret=SECRET):
    body = json.dumps(payload, ensure_ascii=False).encode()
    ts = str(int(time.time()) - age)
    headers = {"content-type": "application/json"}
    if signed:
        headers.update({"x-signature-timestamp": ts,
                        "x-signature-ed25519": signing_key(secret).sign(ts.encode() + body).hex()})
    return client.post("/qq-official/events", content=body, headers=headers)


def messages(seen):
    return [payload for url, payload, _ in seen if url.endswith("/messages")]


def test_official_documented_ed25519_key_derivation_vector():
    # Independent public-key vector from bot-docs sign.md. Its separate signature
    # example does not verify against its published body, so it is not reused.
    key = signing_key("naOC0ocQE3shWLAfffVLB1rhYPG7").public_key()
    expected = [215, 195, 98, 254, 120, 174, 248, 31, 242, 50, 135, 180, 147, 98, 139, 93,
                176, 42, 60, 79, 227, 11, 33, 94, 77, 25, 96, 155, 93, 118, 103, 58]
    assert list(key.public_bytes(Encoding.Raw, PublicFormat.Raw)) == expected


def test_unsigned_challenge_is_signed_without_business_or_network(bot):
    client, service, seen, _ = bot
    timestamp, plain = str(int(time.time())), "challenge_token-123"
    response = post(client, {"op": 13, "d": {"plain_token": plain, "event_ts": timestamp}}, signed=False)
    assert response.status_code == 200
    signing_key().public_key().verify(bytes.fromhex(response.json()["signature"]), (timestamp + plain).encode())
    assert service.calls == seen == []


@pytest.mark.parametrize("plain,age", [('{"op":0,"d":{}}', 0), ("token", 1000), ("", 0)])
def test_challenge_cannot_sign_business_json_or_stale_material(bot, plain, age):
    client, service, seen, _ = bot
    assert post(client, {"op": 13, "d": {"plain_token": plain, "event_ts": str(int(time.time()) - age)}}, signed=False).status_code == 400
    assert service.calls == seen == []


@pytest.mark.parametrize("kwargs", [{"signed": False}, {"secret": "wrong-secret"}, {"age": 400}, {"age": -400}])
def test_unsigned_wrong_and_replayed_business_never_runs(bot, kwargs):
    client, service, seen, _ = bot
    assert post(client, event("创建 普通 pvp"), **kwargs).status_code == 401
    assert service.calls == seen == []


def test_tampered_body_is_rejected(bot):
    client, service, seen, _ = bot
    ts, body = str(int(time.time())), json.dumps(event()).encode()
    sig = signing_key().sign(ts.encode() + body).hex()
    response = client.post("/qq-official/events", content=body + b" ",
                           headers={"x-signature-timestamp": ts, "x-signature-ed25519": sig})
    assert response.status_code == 401 and service.calls == seen == []


def test_create_reply_is_public_namespaced_and_bound_to_source_message(bot):
    client, service, seen, _ = bot
    payload = event("铁底湾 创建 编队 pvp IBS-S-03 日军")
    assert post(client, payload).json() == ACK
    create = service.calls[0]
    assert create[0] == "create"
    assert create[1]["actor_id"] == "qqbot:12345:member:GROUP:MEMBER"
    assert create[1]["room_id"] == "qqbot:12345:GROUP"
    assert create[1]["side"] == "axis" and create[1]["mode"] == "formation"
    sent = messages(seen)
    assert len(sent) == 1 and sent[0]["msg_id"] == payload["d"]["id"] and sent[0]["msg_seq"] == 1
    assert "NEVER_PUBLIC" not in sent[0]["content"] and "OWN" not in sent[0]["content"]
    assert seen[0][0] == TOKEN_URL and seen[0][1] == {"appId": "12345", "clientSecret": SECRET}


def test_unlisted_group_is_ignored(bot):
    client, service, seen, _ = bot
    assert post(client, event("创建 普通 pve", group="OTHER")).json() == ACK
    assert service.calls == seen == []


@pytest.mark.parametrize(('word', 'mode', 'opponent'), [
    ('编队pve', 'formation', 'pve'), ('编队PVP', 'formation', 'pvp'),
    ('普通PvE', 'classic', 'pve'), ('普通pvp', 'classic', 'pvp'),
])
def test_group_create_accepts_compact_mode_opponent(bot, word, mode, opponent):
    client, service, seen, _ = bot
    assert post(client, event('创建 ' + word + ' IBS-S-03 日军')).json() == ACK
    calls = [args for name, args in service.calls if name == 'create']
    assert len(calls) == 1
    assert (calls[0]['mode'], calls[0]['opponent'], calls[0]['side']) == (mode, opponent, 'axis')
    assert '对局 match1' in messages(seen)[0]['content']


def test_compact_create_still_requires_signed_authorized_group(bot):
    client, service, seen, _ = bot
    assert post(client, event('创建 编队pve'), signed=False).status_code == 401
    assert post(client, event('创建 编队pve', group='OTHER')).json() == ACK
    assert service.calls == seen == []


def test_rejected_create_logs_safe_category_without_acceptance(bot, caplog):
    client, service, seen, _ = bot
    with caplog.at_level(logging.INFO, logger='uvicorn.error'):
        assert post(client, event('创建 编队not-valid')).json() == ACK
    assert service.calls == []
    assert 'command_parameters_rejected' in caplog.text and 'create_accepted' not in caplog.text
    assert '编队not-valid' not in caplog.text and 'MEMBER' not in caplog.text


def test_empty_whitelist_only_discovers_signed_group_openid():
    service, seen = FakeService(), []

    def http(request):
        seen.append((str(request.url), json.loads(request.content), {}))
        return httpx.Response(200, json={"access_token": "token", "expires_in": 7200} if str(request.url) == TOKEN_URL else {"id": "r"})

    app = FastAPI()
    app.include_router(create_qq_official_router(service, QQOfficialSettings("12345", SECRET), transport=httpx.MockTransport(http)))
    with TestClient(app) as client:
        assert post(client, event("创建 普通 pve"), signed=False).status_code == 401
        assert post(client, event("创建 普通 pve")).json() == ACK
        assert post(client, event("铁底湾 帮助", private=True)).json() == ACK
    assert service.calls == []
    assert "群openid：GROUP" in messages(seen)[0]["content"]


def test_group_tactics_remain_private_and_public_image_uses_intersection(bot):
    client, service, seen, _ = bot
    post(client, event("态势 match1"))
    assert service.calls == []
    assert "私聊" in messages(seen)[0]["content"]
    seen.clear()
    post(client, event("战况 match1", message_id="public-map"))
    assert [c[0] for c in service.calls] == ["public_status", "public_screenshot"]
    upload = next(p for url, p, _ in seen if url.endswith("/files"))
    assert base64.b64decode(upload["file_data"]) == PNG
    assert upload["srv_send_msg"] is False and "url" not in upload
    assert [m["msg_seq"] for m in messages(seen)] == [1, 2]
    assert messages(seen)[1]["media"] == {"file_info": "PRIVATE_FILE_INFO"}


@pytest.mark.parametrize("command,op", [("自动 2", "auto"), ('提交 2 {"movement":[]}', "submit"), ("确认 2", "submit")])
def test_private_mutations_have_separate_c2c_identity_revision_and_png(bot, command, op):
    client, service, seen, _ = bot
    payload = event("铁底湾 GROUP match1 " + command, private=True)
    post(client, payload)
    post(client, payload)
    assert service.mutations == 1
    kwargs = next(c[1] for c in service.calls if c[0] == op)
    assert kwargs["actor_id"] == "qqbot:12345:c2c:MEMBER"
    assert kwargs["room_id"] == "qqbot:12345:GROUP" and kwargs["expected_revision"] == 2
    assert all(m["msg_id"] == payload["d"]["id"] for m in messages(seen))
    assert len(messages(seen)) == 2
    assert any(url.endswith("/users/MEMBER/files") for url, _, _ in seen)


def test_binding_is_c2c_issued_and_group_claimed_without_private_identity_disclosure(bot):
    client, service, seen, _ = bot
    post(client, event("铁底湾 GROUP match1 绑定 盟军", private=True))
    assert service.calls[0][0] == "issue_identity_link"
    assert service.calls[0][1]["actor_id"] == "qqbot:12345:c2c:MEMBER"
    assert service.calls[0][1]["side"] == "allies"
    assert "PRIVATE_BINDING_CODE" in messages(seen)[0]["content"]
    post(client, event("绑定 PRIVATE_BINDING_CODE", message_id="claim"))
    assert service.calls[1] == ("claim_identity_link", {"code": "PRIVATE_BINDING_CODE",
        "actor_id": "qqbot:12345:member:GROUP:MEMBER", "room_id": "qqbot:12345:GROUP"})
    assert "PRIVATE_C2C_ID" not in messages(seen)[1]["content"]


def test_unbound_private_seat_prompts_binding_without_image(bot):
    client, service, seen, _ = bot
    service.denied = True
    post(client, event("铁底湾 GROUP match1 态势", private=True))
    assert "先私聊" in messages(seen)[0]["content"] and "绑定" in messages(seen)[0]["content"]
    assert not any(url.endswith("/files") for url, _, _ in seen)


@pytest.mark.parametrize("command", ['提交 2 {"_auto":true}', "提交 2 []", "提交 -1 {}", "确认 2 extraneous", "自动"])
def test_bad_private_orders_do_not_mutate(bot, command):
    client, service, seen, _ = bot
    post(client, event("铁底湾 GROUP match1 " + command, private=True))
    assert service.calls == [] and service.mutations == 0
    assert len(messages(seen)) == 1


def test_long_json_is_lossless_within_limit_and_never_partially_sent_above_limit(bot):
    client, service, seen, _ = bot
    expected = {"orders": {"movement": ["舰艇1P2S3"] * 250}}
    service.suggest = lambda *args, **kwargs: expected
    post(client, event("铁底湾 GROUP match1 建议", private=True))
    assert len(messages(seen)) <= 5
    assert json.loads("".join(m["content"] for m in messages(seen))) == expected
    seen.clear()
    expected["orders"]["movement"] *= 10
    post(client, event("铁底湾 GROUP match1 建议", private=True, message_id="long"))
    assert len(messages(seen)) == 1
    notice = messages(seen)[0]["content"]
    assert "完整JSON未发送" in notice and "自动 版本号" in notice and "MCP" in notice
    assert "舰艇" not in notice


def test_api_failed_callback_retry_resumes_sequence_without_duplicate_mutation(bot, caplog):
    client, service, seen, control = bot
    control["fail_at"] = 2
    payload = event("铁底湾 GROUP match1 自动 2", private=True)
    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        assert post(client, payload).json() == ACK
        assert service.mutations == 1
        assert "result=delivery_failed" in caplog.text
        assert "result=delivered" not in caplog.text
        control["fail_at"] = None
        assert post(client, payload).json() == ACK
    assert service.mutations == 1
    assert [m["msg_seq"] for m in messages(seen)] == [1, 2, 2]
    assert "result=delivered" in caplog.text
    assert all(secret not in caplog.text for secret in [SECRET, "PRIVATE_ACCESS_TOKEN", "PRIVATE_FILE_INFO", "PRIVATE_API_ERROR", "MEMBER", "match1"])


def test_reusing_message_id_with_different_content_is_rejected(bot):
    client, service, seen, _ = bot
    payload = event("创建 普通 pvp")
    post(client, payload)
    payload["d"]["content"] = "创建 编队 pvp"
    assert post(client, payload).status_code == 409
    assert service.mutations == 1


def test_token_is_cached_and_invalid_reply_ack_never_marked_success(bot, caplog):
    client, _, seen, control = bot
    post(client, event())
    post(client, event(message_id="second"))
    assert sum(url == TOKEN_URL for url, _, _ in seen) == 1
    control["bad_ack"] = True
    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        post(client, event(message_id="bad-ack"))
    assert "result=delivery_failed" in caplog.text and "result=delivered" not in caplog.text


def test_group_and_c2c_reply_windows_are_enforced(bot):
    client, service, seen, _ = bot
    post(client, event("创建 普通 pvp", age=301))
    assert service.calls == seen == []
    post(client, event("铁底湾 GROUP match1 建议", private=True, age=301))
    assert service.calls[0][0] == "suggest"


def test_environment_and_client_configuration_fail_closed(monkeypatch):
    for name in ("IBS_QQ_APP_ID", "IBS_QQ_APP_SECRET", "IBS_QQ_ALLOWED_GROUPS"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValueError):
        QQOfficialSettings.from_env()
    monkeypatch.setenv("IBS_QQ_APP_ID", "12345")
    monkeypatch.setenv("IBS_QQ_APP_SECRET", SECRET)
    monkeypatch.setenv("IBS_QQ_ALLOWED_GROUPS", "GROUP, OTHER")
    settings = QQOfficialSettings.from_env()
    assert settings.allowed_groups == {"GROUP", "OTHER"} and SECRET not in repr(settings)
    with pytest.raises(ValueError, match="trust_env"):
        create_qq_official_router(FakeService(), settings, client=httpx.AsyncClient())
    with pytest.raises(ValueError):
        QQOfficialSettings("12345", SECRET, frozenset({"../../escape"}))
