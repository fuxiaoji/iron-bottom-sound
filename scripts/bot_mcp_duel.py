#!/usr/bin/env python3
"""Two independent MCP sessions controlling seats on one shared HTTP service.

This is a deterministic transport/engine demo, not an autonomous LLM match.
Start the shared HTTP service separately. Set IBS_BLUE_TOKEN / IBS_RED_TOKEN
to two server-configured identities (including QQ seat owners when desired).
No model API is called and no QQ message is sent by this script.

Example:
  python scripts/bot_mcp_duel.py --room-id 123456 --mode formation --phases 4
"""
from __future__ import annotations

import argparse
import asyncio
import base64
from contextlib import AsyncExitStack
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def call(session, name, arguments):
    result = await session.call_tool(name, arguments)
    if result.isError:
        messages = " ".join(block.text for block in result.content if block.type == "text")
        raise RuntimeError(f"{name}: {messages}")
    return result


async def json_call(session, name, arguments):
    result = await call(session, name, arguments)
    text = next(block.text for block in result.content if block.type == "text")
    return json.loads(text)


async def run(args):
    tokens = [os.environ.get(key) for key in ("IBS_BLUE_TOKEN", "IBS_RED_TOKEN")]
    if not all(tokens) or tokens[0] == tokens[1]:
        raise RuntimeError("Set two distinct IBS_BLUE_TOKEN and IBS_RED_TOKEN identities before running.")
    args.output.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex
    receipt = {"demo": "deterministic engine choices; no autonomous LLM decisions",
               "room_id": args.room_id, "mode": args.mode, "run_id": run_id, "stages": []}
    receipt_path = args.output / "receipt.json"
    print("Deterministic MCP transport demo: two fixed identities, one shared service; no LLM calls.")
    async with AsyncExitStack() as stack:
        sessions = []
        for token in tokens:
            env = {"IBS_AGENT_TOKEN": token, "IBS_BOT_URL": args.url,
                   "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "backend" / "src")}
            read, write = await stack.enter_async_context(stdio_client(StdioServerParameters(
                command=sys.executable, args=["-m", "iron_bottom_sound.bot.mcp_server"], env=env,
            )))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            sessions.append(session)
        if args.match_id:
            match_id = args.match_id
        else:
            created = await json_call(sessions[0], "ibs_create", {
                "room_id": args.room_id, "mode": args.mode, "opponent": "pvp",
                "scenario_id": args.scenario, "side": "axis", "seed": args.seed,
                "request_id": f"{run_id}:create",
            })
            match_id = created["match_id"]
        await json_call(sessions[1], "ibs_join", {
            "room_id": args.room_id, "match_id": match_id, "request_id": f"{run_id}:join",
        })
        receipt["match_id"] = match_id
        common = {"room_id": args.room_id, "match_id": match_id}
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
        for index in range(args.phases):
            statuses = [await json_call(session, "ibs_status", common) for session in sessions]
            if statuses[0]["complete"]:
                print(f"Match {match_id} complete.")
                break
            if statuses[0]["revision"] != statuses[1]["revision"]:
                raise RuntimeError("The two seats observed different revisions; read status before resuming.")
            stage = {"revision": statuses[0]["revision"], "phase": statuses[0]["phase"],
                     "turn": statuses[0]["turn"], "seats": []}
            for session, status in zip(sessions, statuses):
                # Observe legal actions and screenshot through each fixed identity.
                await json_call(session, "ibs_legal", common)
                image = await call(session, "ibs_screenshot", common)
                block = next(item for item in image.content if item.type == "image")
                png = base64.b64decode(block.data, validate=True)
                filename = f"stage-{index:03d}-rev-{status['revision']}-{status['side']}.png"
                (args.output / filename).write_bytes(png)
                seat = {"side": status["side"], "screenshot": filename,
                        "sha256": hashlib.sha256(png).hexdigest(), "summary": status["summary"]}
                if status["side"] not in status["ready"]:
                    suggestion = await json_call(session, "ibs_suggest", common)
                    if suggestion["revision"] != status["revision"]:
                        raise RuntimeError("Phase changed during the demo; read status before resuming.")
                    request_id = f"{run_id}:{index}:{status['side']}"
                    accepted = await json_call(session, "ibs_submit", {
                        **common, "orders": suggestion["orders"],
                        "expected_revision": status["revision"], "request_id": request_id,
                    })
                    seat.update(request_id=request_id, result_revision=accepted["revision"])
                stage["seats"].append(seat)
            after = await json_call(sessions[0], "ibs_status", common)
            stage["result"] = {key: after[key] for key in ("revision", "phase", "turn", "complete", "summary")}
            receipt["stages"].append(stage)
            receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"{match_id}: turn {stage['turn']} {stage['phase']} r{stage['revision']} -> "
                  f"r{after['revision']} ({after['phase']})")
    print(f"Receipt and per-seat PNGs: {args.output.resolve()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--room-id", required=True)
    parser.add_argument("--url", default=os.environ.get("IBS_BOT_URL", "http://127.0.0.1:3192"))
    parser.add_argument("--mode", choices=("classic", "formation"), default="classic")
    parser.add_argument("--scenario", default="IBS-S-03")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--phases", type=int, default=4, help="Maximum decision phases to advance (default: 4)")
    parser.add_argument("--match-id", help="Use an existing match owned by these two identities")
    parser.add_argument("--output", type=Path, default=Path("artifacts") / "bot-mcp-duel" /
                        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    args = parser.parse_args()
    if args.phases < 1:
        parser.error("--phases must be positive")
    try:
        asyncio.run(run(args))
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None


if __name__ == "__main__":
    main()
