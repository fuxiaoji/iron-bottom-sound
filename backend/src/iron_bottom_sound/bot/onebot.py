"""Authenticated OneBot v11 ingress; all tactics stay in seat-authorized DMs."""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
import hashlib
import hmac
import json
import logging
import os
from typing import Any
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool
import httpx


HELP = """铁底湾 QQ 指令（群内须 @机器人，已知群指令可省略“铁底湾”前缀）：
铁底湾 帮助 / 列表
铁底湾 创建 普通|编队 pve|pvp [想定ID] [盟军|日军]
铁底湾 加入 对局ID / 状态 [对局ID]
铁底湾 战况 对局ID（群内查看双方共同可见的公共地图）
私聊机器人：铁底湾 群号 对局ID 态势|行动|建议
私聊提交：铁底湾 群号 对局ID 提交 版本号 JSON对象
私聊自动：铁底湾 群号 对局ID 自动 版本号
私聊确认：铁底湾 群号 对局ID 确认 版本号
态势含本方地图；行动列出合法行动；自动采用状态机建议；确认提交空命令并由引擎校验。
PVP双方密封提交，群聊仅公布阶段进度。"""
TACTICAL = {"态势", "行动", "建议", "提交", "自动", "确认", "截图"}
GROUP_COMMANDS = {"帮助", "创建", "列表", "加入", "状态", "战况"}
logger = logging.getLogger("uvicorn.error")


def _ingress_log(kind: str, result: str, reason: str, segments: str = "none", mention: bool = False) -> None:
    # Every argument is a fixed label or boolean, never message data or identities.
    logger.info("onebot_ingress type=%s result=%s reason=%s segments=%s mention_self=%s",
                kind, result, reason, segments, mention)


def _qq_id(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError("QQ号/群号必须为正整数")
    value = str(value)
    if not value.isascii() or not value.isdigit() or int(value) <= 0:
        raise ValueError("QQ号/群号必须为正整数")
    return str(int(value))


@dataclass(frozen=True)
class BotSettings:
    self_id: str
    secret: str = field(repr=False)
    api_url: str = "http://127.0.0.1:3000"
    token: str = field(default="", repr=False)
    allowed_groups: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        object.__setattr__(self, "self_id", _qq_id(self.self_id))
        object.__setattr__(self, "allowed_groups", frozenset(_qq_id(g) for g in self.allowed_groups))
        if not self.secret or not self.allowed_groups:
            raise ValueError("OneBot须配置SELF_ID、SECRET与非空ALLOWED_GROUPS白名单")
        url = urlsplit(self.api_url)
        if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("OneBot API须为固定HTTP(S)地址，不得内嵌凭据、查询或片段")

    @classmethod
    def from_env(cls) -> "BotSettings":
        return cls(
            self_id=os.environ.get("IBS_ONEBOT_SELF_ID", ""),
            secret=os.environ.get("IBS_ONEBOT_SECRET", ""),
            api_url=os.environ.get("IBS_ONEBOT_API_URL", "http://127.0.0.1:3000"),
            token=os.environ.get("IBS_ONEBOT_TOKEN", ""),
            allowed_groups=frozenset(g.strip() for g in os.environ.get("IBS_ALLOWED_GROUPS", "").split(",") if g.strip()),
        )


class DeliveryError(RuntimeError):
    """A response was not acknowledged by the configured OneBot API."""


def _text_segment(value: str) -> dict:
    return {"type": "text", "data": {"text": value}}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _public_status(status: dict) -> str:
    # Do not forward summary, observation, orders or arbitrary future fields.
    allowed = ("match_id", "revision", "turn", "phase", "mode", "opponent", "ready", "started", "complete")
    return "对局公开进度：\n" + _json({k: status[k] for k in allowed if k in status})


def create_onebot_router(service: Any, settings: BotSettings, *, client: httpx.AsyncClient | None = None,
                         transport: httpx.AsyncBaseTransport | None = None) -> APIRouter:
    """Mount on a FastAPI app. An injected client remains owned by its caller."""
    router = APIRouter()

    async def send(kind: str, target: str, message: list[dict]) -> None:
        # Bound each action's total text without truncating executable JSON.
        # Concatenating the text segments across actions restores the exact reply.
        batches, pending, text_length = [], [], 0
        for segment in message:
            if segment["type"] == "text":
                value = segment["data"]["text"]
                for start in range(0, len(value), 1500):
                    chunk = value[start:start + 1500]
                    if text_length + len(chunk) > 1500:
                        batches.append(pending)
                        pending, text_length = [], 0
                    pending.append(_text_segment(chunk))
                    text_length += len(chunk)
                    if text_length == 1500:
                        batches.append(pending)
                        pending, text_length = [], 0
            else:
                pending.append(segment)
                batches.append(pending)
                pending, text_length = [], 0
        if pending:
            batches.append(pending)
        headers = {"Authorization": f"Bearer {settings.token}"} if settings.token else {}
        url = settings.api_url.rstrip("/") + f"/send_{kind}_msg"

        async def deliver(api: httpx.AsyncClient) -> None:
            for batch in batches:
                payload = {"group_id" if kind == "group" else "user_id": int(target), "message": batch}
                response = await api.post(url, json=payload, headers=headers, timeout=15, follow_redirects=False)
                response.raise_for_status()
                result = response.json()
                if (not isinstance(result, dict) or result.get("status") != "ok"
                        or type(result.get("retcode")) is not int or result["retcode"] != 0):
                    raise DeliveryError("OneBot未确认消息发送成功")

        try:
            if client is not None:
                await deliver(client)
            else:
                async with httpx.AsyncClient(transport=transport, follow_redirects=False) as owned:
                    await deliver(owned)
        except (httpx.HTTPError, ValueError) as exc:
            raise DeliveryError("OneBot消息发送失败") from exc

    def request_id(event: dict, group: str, actor: str) -> str:
        mid = event.get("message_id")
        if isinstance(mid, bool) or not isinstance(mid, (int, str)) or not str(mid):
            raise ValueError("变更指令需要OneBot message_id")
        context = [settings.self_id, event["message_type"], group, actor, str(mid)]
        return "onebot:" + hashlib.sha256(json.dumps(context).encode()).hexdigest()

    def group_command(text: str, event: dict, group: str, actor: str) -> list[dict]:
        parts = text.split()
        command = parts[0] if parts else "帮助"
        args = parts[1:]
        room = "qq:" + group
        if command in TACTICAL:
            return [_text_segment("战术指令请私聊机器人：铁底湾 群号 对局ID 态势|行动|建议|提交 版本号 JSON。群内不公开本方态势与命令。")]
        if command == "帮助":
            return [_text_segment(HELP)]
        if command == "列表":
            catalog = service.catalog()
            return [_text_segment("可选想定：\n" + _json([
                {k: item[k] for k in ("id", "scenario_id", "name", "title") if k in item}
                for item in catalog
            ]))]
        if command == "创建":
            if len(args) < 2 or len(args) > 4 or args[0] not in {"普通", "编队"} or args[1].lower() not in {"pve", "pvp"}:
                raise ValueError("用法：铁底湾 创建 普通|编队 pve|pvp [想定ID] [盟军|日军]")
            extra = args[2:]
            side = "allies"
            if extra and extra[-1] in {"盟军", "日军"}:
                side = {"盟军": "allies", "日军": "axis"}[extra.pop()]
            if len(extra) > 1:
                raise ValueError("创建指令参数过多")
            result = service.create(actor_id=actor, room_id=room, mode={"普通": "classic", "编队": "formation"}[args[0]],
                                    opponent=args[1].lower(), scenario_id=extra[0] if extra else "IBS-S-03", side=side,
                                    seed=1, request_id=request_id(event, group, actor))
            return [_text_segment(_public_status(result) + f"\n私聊：铁底湾 {group} {result['match_id']} 态势")]
        if command == "加入" and len(args) == 1:
            return [_text_segment(_public_status(service.join(args[0], actor_id=actor, room_id=room,
                                                             request_id=request_id(event, group, actor))))]
        if command in {"状态", "战况"} and len(args) == 1:
            status = service.public_status(args[0], room_id=room)
            message = [_text_segment(_public_status(status))]
            if command == "战况":
                png = service.public_screenshot(args[0], room_id=room)
                if not isinstance(png, bytes) or not png.startswith(b"\x89PNG\r\n\x1a\n"):
                    raise ValueError("公共地图生成失败")
                message.append({"type": "image", "data": {"file": "base64://" + base64.b64encode(png).decode("ascii")}})
            return message
        if command == "状态" and not args:
            return [_text_segment("你的对局：\n" + "\n".join(_public_status(s) for s in service.matches(actor_id=actor, room_id=room)))]
        raise ValueError("未识别群指令。发送 @机器人 铁底湾 帮助 查看用法。")

    def private_command(text: str, event: dict, actor: str) -> list[dict]:
        if text in {"", "帮助"}:
            return [_text_segment(HELP)]
        parts = text.split(maxsplit=3)
        if len(parts) < 3:
            raise ValueError("私聊用法：铁底湾 群号 对局ID 态势|行动|建议|提交 版本号 JSON")
        group, match, command = _qq_id(parts[0]), parts[1], parts[2]
        if group not in settings.allowed_groups:
            raise ValueError("该群未获授权")
        context = {"actor_id": actor, "room_id": "qq:" + group}
        rest = parts[3] if len(parts) == 4 else ""
        def situation(status: dict) -> list[dict]:
            png = service.screenshot(match, **context)
            if not isinstance(png, bytes) or not png.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("地图生成失败")
            return [_text_segment(_public_status(status) + "\n" + str(status.get("summary", ""))),
                    {"type": "image", "data": {"file": "base64://" + base64.b64encode(png).decode("ascii")}}]

        if command in {"态势", "截图"} and not rest:
            return situation(service.status(match, **context))
        if command in {"行动", "建议", "状态"} and not rest:
            method = {"行动": service.legal, "建议": service.suggest, "状态": service.status}[command]
            return [_text_segment(_json(method(match, **context)))]
        if command not in {"提交", "自动", "确认"}:
            raise ValueError("未识别私聊指令。发送 铁底湾 帮助 查看用法。")
        revision_parts = rest.split(maxsplit=1)
        if not revision_parts or not revision_parts[0].isascii() or not revision_parts[0].isdigit():
            raise ValueError("必须指定非负版本号；请先查看态势")
        revision = int(revision_parts[0])
        rid = request_id(event, group, actor)
        if command == "提交":
            if len(revision_parts) != 2:
                raise ValueError("提交指令须包含JSON对象")
            try:
                orders = json.loads(revision_parts[1])
            except (ValueError, RecursionError) as exc:
                raise ValueError("命令JSON格式错误") from exc
            if not isinstance(orders, dict):
                raise ValueError("命令JSON必须是对象")
            if "_auto" in orders:
                raise ValueError("自动方案请使用 自动 版本号 指令")
        else:
            if len(revision_parts) != 1:
                raise ValueError("自动/确认仅接受版本号")
            if command == "自动":
                return situation(service.auto(match, **context, expected_revision=revision, request_id=rid))
            orders = {}
        return situation(service.submit(match, **context, orders=orders,
                                        expected_revision=revision, request_id=rid))

    @router.post("/onebot/events")
    async def events(request: Request) -> dict:
        body = await request.body()
        if len(body) > 128_000:
            _ingress_log("unknown", "rejected", "event_size")
            raise HTTPException(413, "event too large")
        signature = "sha1=" + hmac.new(settings.secret.encode(), body, hashlib.sha1).hexdigest()
        if not hmac.compare_digest(request.headers.get("x-signature", "").encode("utf-8"), signature.encode("ascii")):
            _ingress_log("unknown", "rejected", "signature")
            raise HTTPException(403, "invalid signature")
        try:
            event = json.loads(body)
            if not isinstance(event, dict) or _qq_id(event.get("self_id")) != settings.self_id:
                raise ValueError("invalid self_id")
        except (ValueError, TypeError, RecursionError) as exc:
            _ingress_log("unknown", "rejected", "event_structure")
            raise HTTPException(400, "invalid event") from exc
        kind = event.get("message_type")
        if event.get("post_type") != "message" or kind not in ("group", "private"):
            _ingress_log(kind if kind in ("group", "private") else "other", "ignored", "event_type")
            return {"handled": False}
        try:
            user = _qq_id(event.get("user_id"))
            group = _qq_id(event.get("group_id")) if kind == "group" else ""
        except ValueError as exc:
            _ingress_log(kind, "rejected", "sender_structure")
            raise HTTPException(400, "invalid sender") from exc
        if user == settings.self_id:
            _ingress_log(kind, "ignored", "self_event")
            return {"handled": False}
        if kind == "group" and group not in settings.allowed_groups:
            _ingress_log(kind, "ignored", "group_denied")
            return {"handled": False}
        segments = event.get("message")
        if not isinstance(segments, list) or any(not isinstance(s, dict) or not isinstance(s.get("data"), dict) for s in segments):
            _ingress_log(kind, "ignored", "segment_structure")
            return {"handled": False}
        segment_types = ",".join(sorted({s.get("type") if isinstance(s.get("type"), str) and s.get("type") in {"text", "at", "image", "reply", "face"}
                                         else "other" for s in segments})) or "none"
        mentioned = any(s.get("type") == "at" and str(s["data"].get("qq")) == settings.self_id for s in segments)
        if kind == "group" and not mentioned:
            _ingress_log(kind, "ignored", "missing_mention", segment_types)
            return {"handled": False}
        text = "".join(s["data"].get("text", "") for s in segments if s.get("type") == "text" and isinstance(s["data"].get("text"), str)).strip()
        if text.startswith("铁底湾"):
            command = text[len("铁底湾"):].lstrip()
        elif kind == "group" and text.split(maxsplit=1) and text.split(maxsplit=1)[0] in GROUP_COMMANDS:
            command = text
        else:
            _ingress_log(kind, "ignored", "unknown_command", segment_types, mentioned)
            return {"handled": False}
        actor = "qq:" + user
        reason = "command_accepted"
        try:
            message = await run_in_threadpool(group_command, command, event, group, actor) if kind == "group" else await run_in_threadpool(private_command, command, event, actor)
        except Exception as exc:
            # Only domain errors are converted to a user reply. Bugs remain failures.
            if hasattr(exc, "code") and hasattr(exc, "message"):
                detail = str(exc.message) if kind == "private" else "对局请求未接受，请核对席位、群号、对局ID和当前阶段。"
            elif isinstance(exc, ValueError):
                detail = str(exc)
            else:
                _ingress_log(kind, "failed", "internal_error", segment_types, mentioned)
                raise
            reason = "command_rejected"
            message = [_text_segment(f"请求失败：{detail}")]
        _ingress_log(kind, "handled", reason, segment_types, mentioned)
        try:
            await send(kind, group if kind == "group" else user, message)
        except DeliveryError as exc:
            _ingress_log(kind, "failed", "delivery_failed", segment_types, mentioned)
            raise HTTPException(502, "OneBot delivery failed; retry is safe for mutation IDs") from exc
        _ingress_log(kind, "delivered", reason, segment_types, mentioned)
        return {"handled": True}

    return router
