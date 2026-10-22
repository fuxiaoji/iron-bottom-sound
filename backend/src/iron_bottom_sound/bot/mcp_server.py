"""Official MCP stdio adapter for one fixed identity on the shared bot service.

Run with ``python -m iron_bottom_sound.bot.mcp_server``.  Each process needs
IBS_AGENT_TOKEN; IBS_BOT_URL defaults to http://127.0.0.1:3192.  The HTTP service
owns games and persistence.  This adapter never opens a database or selects an
actor from tool arguments.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import os
from typing import Any, Literal
from urllib.parse import quote, urlsplit

import httpx
from mcp.server.fastmcp import FastMCP, Image
from mcp.server.fastmcp.exceptions import ToolError


@dataclass(frozen=True)
class BotConnection:
    url: str
    token: str = field(repr=False)

    def __post_init__(self) -> None:
        parts = urlsplit(self.url)
        if (parts.scheme not in {"http", "https"} or not parts.hostname
                or parts.username or parts.password or parts.query or parts.fragment):
            raise ValueError("IBS_BOT_URL must be an HTTP(S) service URL without credentials or query")
        if not self.token or any(char.isspace() for char in self.token):
            raise ValueError("IBS_AGENT_TOKEN is required and must not contain whitespace")

    @classmethod
    def from_env(cls) -> BotConnection:
        return cls(os.environ.get("IBS_BOT_URL", "http://127.0.0.1:3192").rstrip("/"),
                   os.environ.get("IBS_AGENT_TOKEN", ""))


def create_server(connection: BotConnection, *, transport: httpx.AsyncBaseTransport | None = None) -> FastMCP:
    """Build a server; transport injection is only for local adapter tests."""
    server = FastMCP(
        "iron-bottom-sound",
        instructions=("Each MCP process has one fixed service identity. Read status and legal "
                      "actions before submitting. PVP orders are sealed until both sides submit. "
                      "suggest returns deterministic engine choices, not an LLM decision."),
        log_level="WARNING",
    )

    async def request(method: str, path: str, *, params: dict | None = None,
                      body: dict | None = None, image: bool = False) -> Any:
        # No redirects: never forward the bearer credential to another origin.
        # Ignore proxy environment variables for this explicitly configured service.
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=5.0), follow_redirects=False,
                trust_env=False, transport=transport,
                headers={"Authorization": f"Bearer {connection.token}"},
            ) as client:
                response = await client.request(method, f"{connection.url.rstrip('/')}/v1/{path}",
                                                params=params, json=body)
        except httpx.TimeoutException:
            raise ToolError("Bot service timed out. Read status before retrying with the same request_id.") from None
        except httpx.HTTPError:
            raise ToolError("Bot service connection failed.") from None
        if not response.is_success:
            # Only known domain codes select static guidance. Never forward the
            # backend message: an exception body can include hidden state or secrets.
            domain_messages = {
                "stale_revision": "Phase revision changed. Read status and legal actions, then create a new decision with a new request_id.",
                "already_ready": "This seat already sealed orders for this phase. Wait for the opposing seat; read status before submitting again.",
                "idempotency_conflict": "This request_id belongs to a different payload. Replay its original exact payload, or use a new request_id for a new intent.",
                "waiting": "The PVP match needs another player. Have the opposing identity join, then read status.",
                "full": "The match has no open seat. Read your matches or create a new PVP match.",
                "complete": "The match is complete. Read status and screenshot, or create a new match.",
                "invalid_orders": "The engine rejected these orders. Read legal actions and order_schema, correct this seat's orders, then submit a new decision.",
                "orders": "OrderBatch fields, side, or phase do not match this seat. Read status and legal actions before correcting the payload.",
                "revision": "expected_revision must be a nonnegative integer from the current status.",
                "request_id": "Provide a nonempty request_id of at most 240 characters, stable for exact retries.",
                "ai_orders": "The offline opponent generated invalid orders. The match did not advance; report this service error before retrying.",
                "suggestion": "The offline commander could not generate suggestions. Read legal actions to choose orders or report this service error.",
                "phase_loop": "The engine failed to reach the next decision phase. The match did not advance; report this service error.",
                "scenario": "The scenario could not be created. List scenarios and select a supported scenario_id.",
                "options": "mode must be classic or formation, and opponent must be pve or pvp.",
                "side": "side must be axis or allies.",
                "room_limit": "The room reached its match limit. Ask the service administrator to archive completed matches.",
                "room": "Provide a nonempty room_id of at most 160 characters.",
                "identity": "The configured service identity is invalid. Ask the service administrator to correct its mapping.",
                "forbidden": "This fixed identity does not own a seat in that match.",
                "not_found": "That match does not exist in the specified room. Check both room_id and match_id.",
                "unauthorized": "Bot identity authentication failed. Correct this process's IBS_AGENT_TOKEN configuration.",
            }
            try:
                error_body = response.json()
            except ValueError:
                error_body = None
            code = error_body.get("code") if isinstance(error_body, dict) else None
            if isinstance(code, str) and code in domain_messages:
                raise ToolError(domain_messages[code])
            messages = {
                400: "Invalid bot request.", 401: "Bot identity authentication failed.",
                403: "This identity cannot access that room or match.",
                404: "Room, match, or endpoint not found.",
                409: "Match conflict. Read status and legal actions. Reuse request_id only when retrying the original exact payload.",
                422: "Invalid command or parameters. Read legal actions before resubmitting.",
                429: "Bot service rate limited the request.",
            }
            # Backend bodies and exception strings can contain credentials or hidden
            # state. Return a bounded, fixed message rather than an arbitrary body.
            raise ToolError(messages.get(response.status_code,
                            f"Bot service returned HTTP {response.status_code}."))
        if image:
            if (response.headers.get("content-type", "").split(";", 1)[0].strip() != "image/png"
                    or not response.content.startswith(b"\x89PNG\r\n\x1a\n")):
                raise ToolError("Bot service returned an invalid PNG screenshot.")
            return Image(data=response.content, format="png")
        try:
            return response.json()
        except ValueError:
            raise ToolError("Bot service returned invalid JSON.") from None

    def match_path(match_id: str, action: str) -> str:
        if not match_id or match_id in {".", ".."}:
            raise ToolError("A match_id is required.")
        return f"matches/{quote(match_id, safe='')}/{action}"

    @server.tool()
    async def ibs_scenarios() -> Any:
        """List available scenarios from the shared bot service."""
        return await request("GET", "scenarios")

    @server.tool()
    async def ibs_matches(room_id: str) -> Any:
        """List matches visible to this fixed identity in a room."""
        return await request("GET", "matches", params={"room_id": room_id})

    @server.tool()
    async def ibs_create(room_id: str, mode: Literal["classic", "formation"],
                         opponent: Literal["pve", "pvp"], scenario_id: str,
                         side: Literal["axis", "allies"], seed: int,
                         request_id: str) -> Any:
        """Create a match and occupy one side. Use a unique, stable request_id."""
        return await request("POST", "matches", body={
            "room_id": room_id, "mode": mode, "opponent": opponent,
            "scenario_id": scenario_id, "side": side, "seed": seed, "request_id": request_id,
        })

    @server.tool()
    async def ibs_join(room_id: str, match_id: str, request_id: str) -> Any:
        """Join the open opposing PVP seat using this process's fixed identity."""
        return await request("POST", match_path(match_id, "join"),
                             body={"room_id": room_id, "request_id": request_id})

    @server.tool()
    async def ibs_status(room_id: str, match_id: str) -> Any:
        """Read this identity's observation, phase, revision, and battle report."""
        return await request("GET", match_path(match_id, "status"), params={"room_id": room_id})

    @server.tool()
    async def ibs_legal(room_id: str, match_id: str) -> Any:
        """Read this identity's legal actions; contains no opposing sealed orders."""
        return await request("GET", match_path(match_id, "legal"), params={"room_id": room_id})

    @server.tool()
    async def ibs_suggest(room_id: str, match_id: str) -> Any:
        """Get deterministic engine suggestions, suitable for a transport demo."""
        return await request("GET", match_path(match_id, "suggest"), params={"room_id": room_id})

    @server.tool()
    async def ibs_submit(room_id: str, match_id: str, orders: dict[str, Any],
                         expected_revision: int, request_id: str) -> Any:
        """Submit an OrderBatch at the observed revision; PVP waits for both seats.

        On connection uncertainty, reuse the same request_id and exact payload.
        On a revision conflict, read status before making a new decision.
        """
        return await request("POST", match_path(match_id, "orders"), body={
            "room_id": room_id, "orders": orders, "expected_revision": expected_revision,
            "request_id": request_id,
        })

    @server.tool()
    async def ibs_screenshot(room_id: str, match_id: str) -> Image:
        """Return a PNG rendered only from this identity's permitted observation."""
        return await request("GET", match_path(match_id, "screenshot"),
                             params={"room_id": room_id}, image=True)

    return server


def main() -> None:
    try:
        connection = BotConnection.from_env()
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    create_server(connection).run(transport="stdio")


if __name__ == "__main__":
    main()
