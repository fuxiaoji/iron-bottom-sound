"""MCP adapter checks, including real official-SDK stdio subprocess sessions.

The HTTP fixture is an isolated protocol stub, not an engine-strength or QQ test.
"""
from __future__ import annotations

import asyncio
import base64
from contextlib import AsyncExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time

import httpx
import pytest

pytest.importorskip("mcp", reason="install the bot extra to test the official MCP adapter")
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.server.fastmcp.exceptions import ToolError

from iron_bottom_sound.bot.mcp_server import BotConnection, create_server


PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jS1kAAAAASUVORK5CYII="
)
TOOL_NAMES = {"ibs_scenarios", "ibs_matches", "ibs_create", "ibs_join", "ibs_status",
              "ibs_legal", "ibs_suggest", "ibs_submit", "ibs_screenshot"}


def content_json(result):
    if isinstance(result, dict):
        return result
    blocks = result.content if hasattr(result, "content") else result
    return json.loads(blocks[0].text)


def test_mcp_tools_expose_no_impersonation_arguments():
    async def check():
        server = create_server(BotConnection("http://localhost:3192", "private-test-token"))
        tools = await server.list_tools()
        assert {tool.name for tool in tools} == TOOL_NAMES
        for tool in tools:
            assert not {"actor", "user_id", "token", "identity", "agent_token"} & set(tool.inputSchema["properties"])
        submit = next(tool for tool in tools if tool.name == "ibs_submit")
        assert submit.inputSchema["properties"]["orders"]["type"] == "object"
        assert {"expected_revision", "request_id"} <= set(submit.inputSchema["required"])
        create = next(tool for tool in tools if tool.name == "ibs_create")
        assert create.inputSchema["properties"]["side"]["enum"] == ["axis", "allies"]

    asyncio.run(check())


def test_mcp_http_paths_payload_and_png():
    seen = []

    def handle(request):
        seen.append(request)
        assert request.headers["authorization"] == "Bearer fixed-token"
        if request.url.path.endswith("/screenshot"):
            return httpx.Response(200, content=PNG, headers={"content-type": "image/png"})
        return httpx.Response(200, json={"ok": True})

    async def check():
        server = create_server(BotConnection("http://localhost:3192", "fixed-token"),
                               transport=httpx.MockTransport(handle))
        args = {"room_id": "qq:42", "match_id": "demo"}
        for name in ("ibs_matches", "ibs_status", "ibs_legal", "ibs_suggest", "ibs_screenshot"):
            result = await server.call_tool(name, {"room_id": "qq:42"} if name == "ibs_matches" else args)
            if name == "ibs_screenshot":
                assert result[0].type == "image"
                assert result[0].mimeType == "image/png"
                assert base64.b64decode(result[0].data) == PNG
        await server.call_tool("ibs_scenarios", {})
        await server.call_tool("ibs_create", {
            "room_id": "qq:42", "mode": "formation", "opponent": "pvp", "scenario_id": "S-01",
            "side": "axis", "seed": 7, "request_id": "create-1",
        })
        await server.call_tool("ibs_join", {**args, "request_id": "join-1"})
        await server.call_tool("ibs_submit", {**args, "orders": {"moves": []},
                                               "expected_revision": 3, "request_id": "step-1"})

    asyncio.run(check())
    assert [request.url.path for request in seen] == [
        "/v1/matches", "/v1/matches/demo/status", "/v1/matches/demo/legal",
        "/v1/matches/demo/suggest", "/v1/matches/demo/screenshot", "/v1/scenarios",
        "/v1/matches", "/v1/matches/demo/join", "/v1/matches/demo/orders",
    ]
    assert all(request.url.params["room_id"] == "qq:42" for request in seen[:5])
    assert json.loads(seen[-1].content) == {
        "room_id": "qq:42", "orders": {"moves": []}, "expected_revision": 3, "request_id": "step-1",
    }
    assert "actor" not in json.loads(seen[-1].content)


@pytest.mark.parametrize("status", [401, 403, 409, 422, 500, 302])
def test_mcp_errors_do_not_expose_backend_body_or_credential(status):
    async def check():
        def handle(request):
            return httpx.Response(status, text="fixed-secret hidden-enemy-order", headers={"location": "https://other.invalid/"})
        server = create_server(BotConnection("http://localhost:3192", "fixed-secret"),
                               transport=httpx.MockTransport(handle))
        with pytest.raises(ToolError) as error:
            await server.call_tool("ibs_status", {"room_id": "42", "match_id": "demo"})
        assert "fixed-secret" not in str(error.value)
        assert "hidden-enemy-order" not in str(error.value)

    asyncio.run(check())


@pytest.mark.parametrize("status,code,guidance", [
    (409, "idempotency_conflict", "original exact payload"),
    (409, "stale_revision", "new decision with a new request_id"),
    (409, "already_ready", "Wait for the opposing seat"),
    (400, "waiting", "opposing identity join"),
    (400, "invalid_orders", "Read legal actions and order_schema"),
    (400, "ai_orders", "offline opponent generated invalid orders"),
    (400, "complete", "match is complete"),
    (400, "unknown-backend-code", "Invalid bot request"),
    (400, ["not-a-string"], "Invalid bot request"),
])
def test_mcp_domain_codes_give_static_corrective_guidance(status, code, guidance):
    async def check():
        def handle(request):
            return httpx.Response(status, json={"code": code, "message": "fixed-secret hidden-enemy-order"})
        server = create_server(BotConnection("http://localhost:3192", "fixed-secret"),
                               transport=httpx.MockTransport(handle))
        with pytest.raises(ToolError) as error:
            await server.call_tool("ibs_status", {"room_id": "42", "match_id": "demo"})
        assert guidance in str(error.value)
        assert "fixed-secret" not in str(error.value)
        assert "hidden-enemy-order" not in str(error.value)
        assert "unknown-backend-code" not in str(error.value)

    asyncio.run(check())


@pytest.mark.parametrize("kind", ["timeout", "connection", "json", "png"])
def test_mcp_bounds_transport_and_format_errors(kind):
    async def check():
        def handle(request):
            if kind == "timeout":
                raise httpx.ReadTimeout("fixed-secret", request=request)
            if kind == "connection":
                raise httpx.ConnectError("fixed-secret", request=request)
            return httpx.Response(200, text="fixed-secret", headers={"content-type": "text/html"})
        server = create_server(BotConnection("http://localhost:3192", "fixed-secret"),
                               transport=httpx.MockTransport(handle))
        with pytest.raises(ToolError) as error:
            await server.call_tool("ibs_screenshot" if kind == "png" else "ibs_status",
                                   {"room_id": "42", "match_id": "demo"})
        assert "fixed-secret" not in str(error.value)

    asyncio.run(check())


def test_mcp_connection_requires_fixed_secret(monkeypatch):
    monkeypatch.delenv("IBS_AGENT_TOKEN", raising=False)
    with pytest.raises(ValueError, match="IBS_AGENT_TOKEN"):
        BotConnection.from_env()
    monkeypatch.setenv("IBS_AGENT_TOKEN", "private-secret")
    monkeypatch.delenv("IBS_BOT_URL", raising=False)
    connection = BotConnection.from_env()
    assert connection.url == "http://127.0.0.1:3192"
    assert "private-secret" not in repr(connection)
    for url in ("https://user:password@host/", "https://host/?token=secret", "file:///tmp/foo"):
        with pytest.raises(ValueError):
            BotConnection(url, "secret")


def test_two_real_mcp_stdio_processes_share_http_service_and_fixed_identity(tmp_path):
    """A real tools/list/call handshake on two subprocesses, with no QQ sends."""
    receipts = []
    seats = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.respond()

        def do_POST(self):
            self.respond()

        def respond(self):
            token = self.headers.get("Authorization", "")
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            receipts.append((self.command, self.path, token, body))
            if token not in {"Bearer blue-test", "Bearer red-test"}:
                status, result = 401, {"detail": "private-secret"}
            elif self.path == "/v1/matches" and self.command == "POST":
                seats["axis"] = token
                status, result = 200, {"match_id": "shared-match", "revision": 0, "side": "axis"}
            elif self.path == "/v1/matches/shared-match/join":
                seats["allies"] = token
                status, result = 200, {"match_id": "shared-match", "revision": 0, "side": "allies"}
            elif "/screenshot?" in self.path:
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(PNG)))
                self.end_headers()
                self.wfile.write(PNG)
                return
            elif "/orders" in self.path:
                status, result = 200, {"accepted": True, "revision": 0}
            else:
                side = next((side for side, owner in seats.items() if owner == token), None)
                status, result = 200, {"match_id": "shared-match", "side": side, "revision": 0}
            payload = json.dumps(result).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()

    async def check():
        async with AsyncExitStack() as stack:
            sessions = []
            for token in ("blue-test", "red-test"):
                env = {**os.environ, "IBS_AGENT_TOKEN": token,
                       "IBS_BOT_URL": f"http://127.0.0.1:{http.server_port}",
                       "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "backend" / "src")}
                errlog = stack.enter_context((tmp_path / f"{token}.stderr").open("w+"))
                read, write = await stack.enter_async_context(stdio_client(StdioServerParameters(
                    command=sys.executable, args=["-m", "iron_bottom_sound.bot.mcp_server"], env=env,
                ), errlog=errlog))
                session = await stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                listed = await session.list_tools()
                assert {tool.name for tool in listed.tools} == TOOL_NAMES
                sessions.append(session)
            blue, red = sessions
            created = await blue.call_tool("ibs_create", {
                "room_id": "qq:42", "mode": "classic", "opponent": "pvp", "scenario_id": "S-01",
                "side": "axis", "seed": 1, "request_id": "create-1",
            })
            assert not created.isError
            assert content_json(created)["match_id"] == "shared-match"
            joined = await red.call_tool("ibs_join", {
                "room_id": "qq:42", "match_id": "shared-match", "request_id": "join-1",
            })
            assert not joined.isError
            for session, expected_side in ((blue, "axis"), (red, "allies")):
                args = {"room_id": "qq:42", "match_id": "shared-match"}
                observed = await session.call_tool("ibs_status", args)
                assert content_json(observed)["side"] == expected_side
                result = await session.call_tool("ibs_submit", {
                    **args, "orders": {"moves": []}, "expected_revision": 0,
                    "request_id": f"{expected_side}-step-1",
                })
                assert content_json(result)["accepted"] is True
                screenshot = await session.call_tool("ibs_screenshot", args)
                assert not screenshot.isError
                assert screenshot.content[0].type == "image"
                assert base64.b64decode(screenshot.content[0].data) == PNG

    try:
        asyncio.run(asyncio.wait_for(check(), timeout=120))
    finally:
        http.shutdown()
        http.server_close()
        thread.join(timeout=5)
    assert seats == {"axis": "Bearer blue-test", "allies": "Bearer red-test"}
    submitted = [item for item in receipts if "/orders" in item[1]]
    assert {item[2] for item in submitted} == set(seats.values())
    assert all("actor" not in item[3] and "token" not in item[3] for item in submitted)


@pytest.mark.parametrize("mode,phases", [("classic", 4), ("formation", 5)])
def test_mcp_duel_script_runs_two_sessions_through_real_engine(tmp_path, monkeypatch, mode, phases):
    """Official stdio -> real HTTP app -> isolated SQLite -> Python engine."""
    import uvicorn
    from iron_bottom_sound.bot.app import create_app
    from iron_bottom_sound.bot.service import BattleService

    monkeypatch.delenv("IBS_ONEBOT_SELF_ID", raising=False)
    service = BattleService(tmp_path / "bot.sqlite3")
    app = create_app(service, identities={"blue-test": "agent:blue", "red-test": "agent:red"})
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="critical"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "demo"
    try:
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(.02)
        assert server.started, "isolated HTTP app did not start"
        result = subprocess.run([
            sys.executable, str(root / "scripts" / "bot_mcp_duel.py"),
            "--room-id", "mcp-integration", "--url", f"http://127.0.0.1:{port}",
            "--mode", mode, "--phases", str(phases), "--output", str(output),
        ], cwd=root, env={**os.environ, "IBS_BLUE_TOKEN": "blue-test", "IBS_RED_TOKEN": "red-test"},
            capture_output=True, text=True, timeout=240)
        assert result.returncode == 0, result.stdout + result.stderr
        receipt = json.loads((output / "receipt.json").read_text())
        assert len(receipt["stages"]) == phases
        assert receipt["stages"][-1]["result"]["revision"] == phases
        assert receipt["stages"][-1]["result"]["turn"] == 2
        assert receipt["stages"][-1]["result"]["phase"] == "reinforcement"
        assert {stage["phase"] for stage in receipt["stages"]} >= {
            "reinforcement", "movement_planning", "torpedo_planning", "gunnery",
        }
        assert len(list(output.glob("*.png"))) == phases * 2
        for stage in receipt["stages"]:
            assert {seat["side"] for seat in stage["seats"]} == {"axis", "allies"}
            for seat in stage["seats"]:
                assert (output / seat["screenshot"]).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        text = (output / "receipt.json").read_text() + result.stdout + result.stderr
        assert "blue-test" not in text and "red-test" not in text
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
        if not thread.is_alive():
            service.close()
    assert not thread.is_alive(), "isolated HTTP app did not stop"
