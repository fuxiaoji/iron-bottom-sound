"""Short QQ commands must retain real persistent seat and revision checks."""
import base64
import json
import re

from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
import pytest

from iron_bottom_sound.bot.qq_official import QQOfficialSettings, create_qq_official_router
from iron_bottom_sound.bot.service import BattleService
from test_bot_qq_official import API, SECRET, TOKEN_URL, event, messages, post


@pytest.mark.parametrize("preset,mode", [("普通人机", "classic"), ("编队人机", "formation")])
def test_real_bound_short_commands_survive_restart_and_do_not_replay_phase(tmp_path, preset, mode):
    database = tmp_path / "shortcuts.sqlite3"
    seen = []

    def http(request):
        value = json.loads(request.content)
        seen.append((str(request.url), value, {}))
        if str(request.url) == TOKEN_URL:
            return httpx.Response(200, json={"access_token": "TEST", "expires_in": 7200})
        assert str(request.url).startswith(API)
        if request.url.path.endswith("/files"):
            png = base64.b64decode(value["file_data"])
            assert png.startswith(b"\x89PNG\r\n\x1a\n") and len(png) > 10000
            return httpx.Response(200, json={"file_info": "TEST_PNG"})
        return httpx.Response(200, json={"id": "reply-" + str(len(seen))})

    settings = QQOfficialSettings("12345", SECRET, frozenset({"GROUP"}))
    service = BattleService(database)

    def app_for(current):
        app = FastAPI()
        app.include_router(create_qq_official_router(current, settings, transport=httpx.MockTransport(http)))
        return app

    room, actor = "qqbot:12345:GROUP", "qqbot:12345:c2c:MEMBER"
    try:
        with TestClient(app_for(service)) as client:
            post(client, event("/" + preset, message_id="create"))
            row = service.db.execute("SELECT id,mode,revision FROM bot_matches").fetchone()
            match = row["id"]
            assert row["mode"] == mode and row["revision"] == 0
            seen.clear()
            post(client, event("/态势", private=True, message_id="unbound"))
            assert not any(url.endswith("/files") for url, _, _ in seen)
            assert "绑定" in messages(seen)[0]["content"]

            seen.clear()
            post(client, event(f"铁底湾 GROUP {match} 绑定 盟军", private=True, message_id="issue"))
            code = re.search(r"绑定 ([A-Za-z0-9_-]{32})", messages(seen)[0]["content"])[1]
            post(client, event("/绑定 " + code, message_id="claim"))
            seen.clear()
            post(client, event("/下一步", private=True, message_id="next"))
            assert f"/自动 0 {match}" in messages(seen)[0]["content"]
            post(client, event("/自动", private=True, message_id="preview"))
            assert service.status(match, actor, room)["revision"] == 0
            advance = event(f"/自动 0 {match}", private=True, message_id="advance")
            post(client, advance)
            post(client, advance)
            assert service.status(match, actor, room)["revision"] == 1
        service.close()
        service = BattleService(database)
        seen.clear()
        with TestClient(app_for(service)) as client:
            post(client, event("/态势", private=True, message_id="after-restart"))
            assert "版本1" in messages(seen)[0]["content"]
            assert any(url.endswith("/users/MEMBER/files") for url, _, _ in seen)
            post(client, advance)  # New router, persisted mutation receipt.
            assert service.status(match, actor, room)["revision"] == 1
    finally:
        service.close()
