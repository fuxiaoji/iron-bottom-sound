"""QQ Open Platform webhook and passive replies; no ordinary-account access.

Protocol sources: tencent-connect/bot-docs (sign.md, event-emit.md,
send-receive/send.md) and qqbot-nodejs/src/protocol/{transport,api}.
Business receipts live in BattleService. Reply progress is process-local: run
one webhook worker; a restart may replay a reply sequence, never a mutation.
"""
from __future__ import annotations

import asyncio
import base64
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
import logging
import os
import re
import time
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from starlette.concurrency import run_in_threadpool
import httpx

logger = logging.getLogger("uvicorn.error")
ACK = {"op": 12, "d": 0}
API = "https://api.sgroup.qq.com"
TOKEN_URL = "https://bots.qq.com/app/getAppAccessToken"
HELP = """铁底湾：帮助 / 列表 / 创建 普通|编队 pve|pvp [想定ID] [盟军|日军]
加入 对局ID / 状态 [对局ID] / 战况 对局ID（公共地图）
私聊：铁底湾 群openid 对局ID 态势|行动 [舰ID]|建议
私聊：铁底湾 群openid 对局ID 提交 版本 JSON对象 / 自动 版本 / 确认 版本
私聊绑定席位：铁底湾 群openid 对局ID 绑定 盟军|日军
随后本人在对应群@机器人：绑定 私聊获得的验证码
版本号来自态势。PVP另一席请主动查询更新；平台主动推送已停止。
私聊读取席位前必须完成可信身份绑定，不根据原始openid相同自动关联。"""
GROUP_COMMANDS = {"帮助", "列表", "创建", "加入", "状态", "战况", "绑定"}
TACTICAL = {"态势", "行动", "建议", "提交", "自动", "确认", "截图"}


def _openid(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise ValueError("无效openid")
    return value


@dataclass(frozen=True)
class QQOfficialSettings:
    app_id: str
    app_secret: str = field(repr=False)
    allowed_groups: frozenset[str] = field(default_factory=frozenset)
    signature_max_age: int = 300  # Local replay defense, not a claimed QQ limit.
    text_chunk_size: int = 1500  # Conservative application bound.

    def __post_init__(self):
        if not isinstance(self.app_id, str) or not re.fullmatch(r"[0-9]{1,32}", self.app_id):
            raise ValueError("缺少有效QQ机器人AppID")
        if not isinstance(self.app_secret, str) or not self.app_secret or not self.app_secret.isascii():
            raise ValueError("缺少有效QQ机器人AppSecret")
        object.__setattr__(self, "allowed_groups", frozenset(_openid(g) for g in self.allowed_groups))
        if not 1 <= self.signature_max_age <= 3600 or not 100 <= self.text_chunk_size <= 1500:
            raise ValueError("无效回调时间窗或文本分片设置")

    @classmethod
    def from_env(cls):
        return cls(os.environ.get("IBS_QQ_APP_ID", ""), os.environ.get("IBS_QQ_APP_SECRET", ""),
                   frozenset(g.strip() for g in os.environ.get("IBS_QQ_ALLOWED_GROUPS", "").split(",") if g.strip()))


class OfficialAPIError(RuntimeError):
    """Fixed-label transport failure; never carries response body or credentials."""


def _json(value):
    return json.dumps(value, ensure_ascii=False, indent=2)


def _public(value):
    keys = ("match_id", "revision", "turn", "phase", "mode", "opponent", "ready", "started", "complete")
    return _json({k: value[k] for k in keys if k in value})


def _log(scope, result):
    # Callers pass constants only, never platform IDs, text, headers or orders.
    logger.info("qq_official scope=%s result=%s", scope, result)


class _QQAPI:
    def __init__(self, settings):
        self.settings, self.token, self.expires = settings, "", 0.0
        self.lock = asyncio.Lock()

    async def access_token(self, client, force=False):
        async with self.lock:
            if not force and self.token and time.monotonic() < self.expires:
                return self.token
            try:
                response = await client.post(TOKEN_URL, json={"appId": self.settings.app_id,
                    "clientSecret": self.settings.app_secret}, timeout=15, follow_redirects=False)
                response.raise_for_status()
                data = response.json()
                if data.get("code", 0) != 0:
                    raise ValueError()
                token, lifetime = data.get("access_token"), int(data.get("expires_in", 0))
                if not isinstance(token, str) or not token or lifetime <= 0:
                    raise ValueError()
            except (httpx.HTTPError, ValueError, TypeError, AttributeError):
                raise OfficialAPIError("token_failed") from None
            self.token = token
            self.expires = time.monotonic() + lifetime - min(60, lifetime / 3)
            return token

    async def post(self, client, path, payload):
        for attempt in range(2):
            token = await self.access_token(client, force=bool(attempt))
            try:
                response = await client.post(API + path, json=payload,
                    headers={"Authorization": "QQBot " + token}, timeout=30, follow_redirects=False)
                if response.status_code == 401 and not attempt:
                    continue
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict) or data.get("code", 0) != 0 or data.get("retcode", 0) != 0:
                    raise ValueError()
                return data
            except (httpx.HTTPError, ValueError):
                raise OfficialAPIError("api_failed") from None
        raise OfficialAPIError("api_failed")


def create_qq_official_router(service, settings: QQOfficialSettings, *, client: httpx.AsyncClient | None = None,
                              transport: httpx.AsyncBaseTransport | None = None) -> APIRouter:
    """Mount POST /qq-official/events; supplied clients must disable environment proxies."""
    if client is not None and client.trust_env:
        raise ValueError("QQ官方HTTP客户端须trust_env=False")
    router, api = APIRouter(), _QQAPI(settings)
    seed = settings.app_secret.encode()
    while len(seed) < 32:
        seed += seed
    key = Ed25519PrivateKey.from_private_bytes(seed[:32])
    receipts: OrderedDict[str, dict] = OrderedDict()
    receipt_lock = asyncio.Lock()

    def commands(scope, data, actor, room, rid):
        text = data["content"].strip()
        # GROUP_AT_MESSAGE_CREATE itself is the signed mention gate.
        if scope == "group":
            text = re.sub(r"^(?:<@!?[^>\s]{1,128}>\s*)+", "", text)
        if text.startswith("铁底湾"):
            text = text[len("铁底湾"):].lstrip()
        elif scope == "c2c":
            return [("text", "私聊指令请以 铁底湾 开头。\n" + HELP)]
        if text in {"", "帮助"}:
            return [("text", HELP)]
        if scope == "group":
            parts = text.split()
            command, args = parts[0], parts[1:]
            if command in TACTICAL:
                return [("text", "本方态势和战术命令请私聊：铁底湾 群openid 对局ID 态势。")]
            if command not in GROUP_COMMANDS:
                return [("text", HELP)]
            if command == "列表":
                return [("text", _json([{k: v[k] for k in ("id", "scenario_id", "title", "name") if k in v}
                                         for v in service.catalog()]))]
            if command == "绑定" and len(args) == 1:
                value = service.claim_identity_link(args[0], actor_id=actor, room_id=room)
                return [("text", "席位私聊身份已绑定。" if value.get("linked") is True else "绑定未完成。")]
            if command == "创建":
                if not 2 <= len(args) <= 4 or args[0] not in {"普通", "编队"} or args[1].lower() not in {"pve", "pvp"}:
                    raise ValueError("用法：创建 普通|编队 pve|pvp [想定ID] [盟军|日军]")
                extra, side = args[2:], "allies"
                if extra and extra[-1] in {"盟军", "日军"}:
                    side = {"盟军": "allies", "日军": "axis"}[extra.pop()]
                if len(extra) > 1:
                    raise ValueError("创建参数过多")
                value = service.create(actor_id=actor, room_id=room,
                    mode={"普通": "classic", "编队": "formation"}[args[0]], opponent=args[1].lower(),
                    scenario_id=extra[0] if extra else "IBS-S-03", side=side, seed=1, request_id=rid)
                return [("text", _public(value) + f"\n私聊：铁底湾 {data['group_openid']} {value['match_id']} 态势")]
            if command == "加入" and len(args) == 1:
                return [("text", _public(service.join(args[0], actor_id=actor, room_id=room, request_id=rid)))]
            if command == "状态" and not args:
                return [("text", "\n".join(_public(v) for v in service.matches(actor_id=actor, room_id=room)) or "你尚未加入对局。")]
            if command in {"状态", "战况"} and len(args) == 1:
                result = [("text", _public(service.public_status(args[0], room_id=room)))]
                if command == "战况":
                    result.append(("image", service.public_screenshot(args[0], room_id=room)))
                return result
            raise ValueError("指令参数错误，请发送 帮助。")
        parts = text.split(maxsplit=3)
        if len(parts) < 3:
            raise ValueError("用法：铁底湾 群openid 对局ID 态势|行动|建议|提交 版本 JSON")
        group, match, command = _openid(parts[0]), parts[1], parts[2]
        if group not in settings.allowed_groups:
            raise ValueError("该群未获授权。")
        context = {"actor_id": actor, "room_id": "qqbot:" + settings.app_id + ":" + group}
        rest = parts[3] if len(parts) > 3 else ""
        if command == "绑定":
            if rest not in {"盟军", "日军"}:
                raise ValueError("绑定用法：铁底湾 群openid 对局ID 绑定 盟军|日军")
            value = service.issue_identity_link(match_id=match, **context,
                side={"盟军": "allies", "日军": "axis"}[rest], request_id=rid)
            return [("text", f"请在目标群由该席位本人@机器人发送：绑定 {value['code']}\n有效期{value['expires_in']}秒；绑定前不能读取该席位态势。")]

        def situation(value):
            return [("text", _public(value) + "\n" + str(value.get("summary", ""))),
                    ("image", service.screenshot(match, **context))]

        if command in {"态势", "截图"} and not rest:
            return situation(service.status(match, **context))
        if command == "行动":
            value = service.legal(match, **context)
            if rest:
                value = {k: value[k] for k in ("match_id", "revision", "phase") if k in value} | {
                    "selected_ship": rest, "actions": [a for a in value.get("actions", []) if a.get("ship_id") == rest]}
            return [("text", _json(value))]
        if command in {"建议", "状态"} and not rest:
            return [("text", _json((service.suggest if command == "建议" else service.status)(match, **context)))]
        if command not in {"提交", "自动", "确认"}:
            raise ValueError("未识别私聊指令。")
        args = rest.split(maxsplit=1)
        if not args or not re.fullmatch(r"[0-9]{1,10}", args[0]):
            raise ValueError("请先查看态势并提供非负版本号。")
        revision = int(args[0])
        if command in {"自动", "确认"}:
            if len(args) != 1:
                raise ValueError("自动/确认仅接受版本号。")
            value = service.auto(match, **context, expected_revision=revision, request_id=rid) if command == "自动" else service.submit(
                match, **context, orders={}, expected_revision=revision, request_id=rid)
        else:
            try:
                orders = json.loads(args[1]) if len(args) == 2 else None
            except (ValueError, RecursionError):
                raise ValueError("命令JSON格式错误。") from None
            if not isinstance(orders, dict) or "_auto" in orders:
                raise ValueError("命令须为JSON对象；自动方案请使用 自动 指令。")
            value = service.submit(match, **context, orders=orders, expected_revision=revision, request_id=rid)
        return situation(value)

    async def process(entry):
        scope, data = entry["scope"], entry["data"]
        try:
            if time.time() >= entry["deadline"]:
                _log(scope, "reply_expired")
                return
            if entry["parts"] is None:
                try:
                    if scope == "group" and not settings.allowed_groups:
                        parts = [("text", "此群尚未授权。管理员配置群openid：" + data["group_openid"])]
                    else:
                        parts = await run_in_threadpool(commands, scope, data, entry["actor"], entry["room"], entry["rid"])
                except Exception as exc:
                    if hasattr(exc, "code") and hasattr(exc, "message"):
                        detail = str(exc.message) if scope == "c2c" else "请求未接受，请核对席位、对局和阶段。"
                        if scope == "c2c" and exc.code == "forbidden":
                            detail += "\n请先私聊：铁底湾 群openid 对局ID 绑定 盟军|日军，再由该席位本人在对应群确认。"
                    elif isinstance(exc, ValueError):
                        detail = str(exc)
                    else:
                        _log(scope, "business_failed")
                        return
                    parts = [("text", detail)]
                compiled = []
                for kind, value in parts:
                    if kind == "text":
                        compiled += [(kind, value[i:i + settings.text_chunk_size]) for i in range(0, len(value), settings.text_chunk_size)]
                    else:
                        if not isinstance(value, bytes) or not value.startswith(b"\x89PNG\r\n\x1a\n") or len(value) > 5 * 1024 * 1024:
                            raise OfficialAPIError("invalid_png")
                        compiled.append((kind, value))
                if len(compiled) > 5:
                    compiled = [("text", "输出超过单次5条被动回复限额，完整JSON未发送。建议可改用 自动 版本号；或用MCP获取完整JSON、行动 舰ID 缩小查询。已执行的操作可重新查询状态。")]
                entry["parts"] = compiled

            async def deliver(http):
                path = "/v2/" + ("groups/" if scope == "group" else "users/") + entry["target"]
                while entry["sent"] < len(entry["parts"]):
                    if time.time() >= entry["deadline"]:
                        raise OfficialAPIError("reply_expired")
                    kind, value = entry["parts"][entry["sent"]]
                    payload = {"msg_id": data["id"], "msg_seq": entry["sent"] + 1}
                    if kind == "image":
                        media = await api.post(http, path + "/files", {"file_type": 1,
                            "file_data": base64.b64encode(value).decode(), "srv_send_msg": False})
                        if not isinstance(media.get("file_info"), str) or not media["file_info"]:
                            raise OfficialAPIError("upload_failed")
                        payload.update(msg_type=7, content=" ", media={"file_info": media["file_info"]})
                    else:
                        payload.update(msg_type=0, content=value)
                    result = await api.post(http, path + "/messages", payload)
                    if not isinstance(result.get("id"), str) or not result["id"]:
                        raise OfficialAPIError("reply_unacknowledged")
                    entry["sent"] += 1
                entry["complete"] = True
                _log(scope, "delivered")

            if client is not None:
                await deliver(client)
            else:
                async with httpx.AsyncClient(transport=transport, trust_env=False, follow_redirects=False) as owned:
                    await deliver(owned)
        except OfficialAPIError:
            _log(scope, "delivery_failed")
        except Exception:
            _log(scope, "internal_failed")
        finally:
            entry["busy"] = False

    @router.post("/qq-official/events")
    async def events(request: Request, background: BackgroundTasks):
        body = await request.body()
        if len(body) > 128_000:
            raise HTTPException(413, "event too large")
        try:
            event = json.loads(body)
            if not isinstance(event, dict):
                raise ValueError()
        except (ValueError, RecursionError):
            raise HTTPException(400, "invalid event") from None
        if event.get("op") == 13:
            # The platform's unsigned URL-validation handshake is not dispatch.
            data = event.get("d")
            if not isinstance(data, dict):
                raise HTTPException(400, "invalid challenge")
            plain, timestamp = data.get("plain_token"), data.get("event_ts")
            # Excluding JSON punctuation prevents the public challenge endpoint
            # from becoming an oracle for signing arbitrary business events.
            if (not isinstance(plain, str) or not re.fullmatch(r"[A-Za-z0-9._~+/=-]{1,256}", plain)
                    or not isinstance(timestamp, str) or not re.fullmatch(r"[0-9]{1,12}", timestamp)
                    or abs(time.time() - int(timestamp)) > settings.signature_max_age):
                raise HTTPException(400, "invalid challenge")
            _log("validation", "challenge_signed")
            return {"plain_token": plain, "signature": key.sign((timestamp + plain).encode()).hex()}
        timestamp = request.headers.get("x-signature-timestamp", "")
        signature = request.headers.get("x-signature-ed25519", "")
        try:
            if not re.fullmatch(r"[0-9]{1,12}", timestamp) or abs(time.time() - int(timestamp)) > settings.signature_max_age:
                raise ValueError()
            if not re.fullmatch(r"[0-9a-fA-F]{128}", signature):
                raise ValueError()
            key.public_key().verify(bytes.fromhex(signature), timestamp.encode() + body)
        except (ValueError, InvalidSignature):
            _log("unknown", "signature_rejected")
            raise HTTPException(401, "invalid signature or timestamp") from None
        event_type = event.get("t")
        if event.get("op") != 0 or event_type not in ("GROUP_AT_MESSAGE_CREATE", "C2C_MESSAGE_CREATE"):
            _log("other", "ignored")
            return ACK
        scope = "group" if event_type == "GROUP_AT_MESSAGE_CREATE" else "c2c"
        try:
            data = event["d"]
            sender = _openid(data["author"]["member_openid" if scope == "group" else "user_openid"])
            group = _openid(data["group_openid"]) if scope == "group" else ""
            if not isinstance(data["content"], str) or not isinstance(data["id"], str) or not 1 <= len(data["id"]) <= 512:
                raise ValueError()
            produced = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
            if produced.tzinfo is None:
                raise ValueError()
            deadline = produced.timestamp() + (300 if scope == "group" else 3600)
            if produced.timestamp() > time.time() + 30 or time.time() >= deadline:
                _log(scope, "message_expired")
                return ACK
        except (KeyError, ValueError, TypeError, AttributeError):
            _log(scope, "event_rejected")
            raise HTTPException(400, "invalid message event") from None
        if scope == "group" and settings.allowed_groups and group not in settings.allowed_groups:
            _log(scope, "group_denied")
            return ACK
        if scope == "group" and not settings.allowed_groups and hasattr(service, "record_official_group"):
            await run_in_threadpool(service.record_official_group, settings.app_id, group)
        if scope == "c2c" and not settings.allowed_groups:
            _log(scope, "not_configured")
            return ACK
        context = [settings.app_id, scope, sender, group, data["id"]]
        rid = "qq-official:" + hashlib.sha256(json.dumps(context).encode()).hexdigest()
        fingerprint = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
        async with receipt_lock:
            for name in list(receipts):
                if receipts[name]["deadline"] < time.time() and not receipts[name]["busy"]:
                    del receipts[name]
            entry = receipts.get(rid)
            if entry and entry["fingerprint"] != fingerprint:
                _log(scope, "replay_conflict")
                raise HTTPException(409, "message id reused with different content")
            if entry and (entry["busy"] or entry["complete"]):
                _log(scope, "duplicate_ignored")
                return ACK
            if entry is None:
                if len(receipts) >= 2048:
                    _log(scope, "capacity_rejected")
                    raise HTTPException(503, "callback capacity reached")
                actor = ("qqbot:" + settings.app_id + ":member:" + group + ":" + sender if scope == "group"
                         else "qqbot:" + settings.app_id + ":c2c:" + sender)
                entry = {"scope": scope, "data": data, "actor": actor,
                         "room": "qqbot:" + settings.app_id + ":" + group, "target": group if scope == "group" else sender,
                         "rid": rid, "fingerprint": fingerprint, "deadline": deadline,
                         "parts": None, "sent": 0, "complete": False}
                receipts[rid] = entry
            entry["busy"] = True
            background.add_task(process, entry)
        _log(scope, "accepted")
        return ACK

    return router
