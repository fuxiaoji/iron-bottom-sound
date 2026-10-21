"""One shared HTTP process for QQ ingress and identity-bound MCP clients."""

import asyncio
from contextlib import asynccontextmanager
import hmac
import json
import os
import re
from pathlib import Path
from typing import Annotated, Any, Literal

import httpx
from fastapi import Depends, FastAPI, Header, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field

from .service import BattleService, ServiceError


class StrictBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    room_id: str = Field(min_length=1, max_length=160)
    request_id: str = Field(min_length=1, max_length=240)


class CreateMatch(StrictBody):
    mode: Literal['classic', 'formation'] = 'classic'
    opponent: Literal['pve', 'pvp'] = 'pve'
    scenario_id: str = 'IBS-S-03'
    side: Literal['axis', 'allies'] = 'allies'
    seed: int = 1


class SubmitOrders(StrictBody):
    orders: dict[str, Any]
    expected_revision: int = Field(ge=0, strict=True)


class NotificationDelivery:
    """Durable at-least-once OneBot delivery; ack only accepted messages."""
    def __init__(self, service, settings, client=None):
        self.service, self.settings, self.client = service, settings, client
        self.lock = asyncio.Lock()

    async def flush(self):
        async with self.lock:
            # Scan beyond a page of revoked/failed recipients, then wrap so each
            # retained failure is retried. One unreachable player cannot block
            # the other seat or another group. No network happens under DB lock.
            cursor = 0
            while True:
                items = self.service.pending_notifications(after_id=cursor)
                if not items:
                    return
                for item in items:
                    cursor = item['id']
                    room = item['room_id']
                    if not room.startswith('qq:') or room[3:] not in self.settings.allowed_groups:
                        continue
                    actor = item.get('actor_id', '')
                    is_group = 'group_id' in item
                    if not is_group and (not actor.startswith('qq:') or not actor[3:].isdigit()):
                        continue
                    target = {'group_id': int(item['group_id'])} if is_group else {'user_id': int(actor[3:])}
                    text = item['summary']
                    chunks = [text[i:i + 1500] for i in range(0, len(text), 1500)] or ['']
                    payloads = [{**target, 'message': [
                        {'type': 'text', 'data': {'text': chunk}}]} for chunk in chunks]
                    payloads[-1]['message'].append(
                        {'type': 'image', 'data': {'file': 'base64://' + item['image']}})
                    url = self.settings.api_url.rstrip('/') + ('/send_group_msg' if is_group else '/send_private_msg')
                    headers = {'Authorization': f'Bearer {self.settings.token}'} if self.settings.token else {}
                    accepted = True
                    for payload in payloads:
                        try:
                            if self.client is None:
                                async with httpx.AsyncClient(follow_redirects=False, trust_env=False) as client:
                                    response = await client.post(url, json=payload, headers=headers, timeout=15)
                            else:
                                response = await self.client.post(url, json=payload, headers=headers, timeout=15, follow_redirects=False)
                            response.raise_for_status()
                            result = response.json()
                            if (not isinstance(result, dict) or result.get('status') != 'ok'
                                    or type(result.get('retcode')) is not int or result['retcode'] != 0):
                                accepted = False
                                break
                        except httpx.TransportError:
                            return
                        except (httpx.HTTPError, ValueError, AttributeError):
                            accepted = False
                            break
                    if not accepted:
                        continue
                    self.service.acknowledge_notification(item['id'])


def create_app(service: BattleService | None = None, *, identities: dict[str, str] | None = None,
               onebot_settings=None, onebot_client=None, notification_interval: float | None = 5,
               official_settings=None, official_client=None, official_transport=None) -> FastAPI:
    owned = service is None
    service = service or BattleService(Path(os.environ.get('IBS_BOT_DATABASE', 'backend/bot.sqlite3')))
    identities = identities if identities is not None else json.loads(os.environ.get('IBS_AGENT_IDENTITIES', '{}'))
    if not isinstance(identities, dict) or any(not isinstance(k, str) or not k or not k.isascii() or any(c.isspace() for c in k) or
            not isinstance(v, str) or not v.startswith(('qq:', 'agent:', 'qqbot:')) or not v.split(':', 1)[1] or
            (v.startswith('qqbot:') and not re.fullmatch(r'qqbot:[0-9]+:(?:c2c:[A-Za-z0-9_-]+|member:[A-Za-z0-9_-]+:[A-Za-z0-9_-]+)', v)) or
            (v.startswith('qq:') and (not v[3:].isascii() or not v[3:].isdigit() or v[3:].startswith('0'))) for k, v in identities.items()):
        raise ValueError('IBS_AGENT_IDENTITIES must map nonempty bearer tokens to valid qq:/agent:/qqbot: identities')
    if onebot_settings is None and os.environ.get('IBS_ONEBOT_SELF_ID'):
        from .onebot import BotSettings
        onebot_settings = BotSettings.from_env()
    notifier = NotificationDelivery(service, onebot_settings, onebot_client) if onebot_settings else None

    async def pump():
        while True:
            await notifier.flush()
            await asyncio.sleep(notification_interval)

    @asynccontextmanager
    async def lifespan(app):
        worker = asyncio.create_task(pump()) if notifier and notification_interval is not None else None
        try:
            yield
        finally:
            if worker:
                worker.cancel()
                try:
                    await worker
                except asyncio.CancelledError:
                    pass
            if owned:
                service.close()

    app = FastAPI(title='铁底湾 QQ / MCP', lifespan=lifespan)
    app.state.service, app.state.notifier = service, notifier

    @app.exception_handler(ServiceError)
    async def service_error(request: Request, exc: ServiceError):
        codes = {'forbidden': 403, 'not_found': 404, 'stale_revision': 409,
                 'already_ready': 409, 'idempotency_conflict': 409, 'unauthorized': 401}
        return JSONResponse(status_code=codes.get(exc.code, 400), content={'code': exc.code, 'message': exc.message})

    def actor(authorization: Annotated[str | None, Header()] = None):
        if authorization and authorization.startswith('Bearer '):
            token = authorization[7:]
            if not token.isascii() or any(c.isspace() for c in token):
                raise ServiceError('unauthorized', '需要有效的玩家令牌')
            for candidate, identity in identities.items():
                if hmac.compare_digest(token, candidate):
                    return identity
        raise ServiceError('unauthorized', '需要有效的玩家令牌')

    Player = Annotated[str, Depends(actor)]

    @app.get('/health')
    def health():
        return {'status': 'ok', 'engine': 'python', 'modes': ['classic', 'formation']}

    @app.get('/v1/scenarios')
    def scenarios(player: Player):
        return service.catalog()

    @app.get('/v1/matches')
    def matches(room_id: str, player: Player):
        return service.matches(player, room_id)

    @app.post('/v1/matches')
    def create(body: CreateMatch, player: Player):
        return service.create(actor_id=player, **body.model_dump())

    @app.post('/v1/matches/{match_id}/join')
    def join(match_id: str, body: StrictBody, player: Player):
        return service.join(match_id=match_id, actor_id=player, **body.model_dump())

    @app.get('/v1/matches/{match_id}/status')
    def status(match_id: str, room_id: str, player: Player):
        return service.status(match_id, player, room_id)

    @app.get('/v1/matches/{match_id}/legal')
    def legal(match_id: str, room_id: str, player: Player):
        return service.legal(match_id, player, room_id)

    @app.get('/v1/matches/{match_id}/suggest')
    def suggest(match_id: str, room_id: str, player: Player):
        return service.suggest(match_id, player, room_id)

    @app.get('/v1/matches/{match_id}/screenshot')
    def screenshot(match_id: str, room_id: str, player: Player):
        return Response(service.screenshot(match_id, player, room_id), media_type='image/png',
                        headers={'Cache-Control': 'no-store'})

    @app.post('/v1/matches/{match_id}/orders')
    def submit(match_id: str, body: SubmitOrders, player: Player):
        if '_auto' in body.orders:
            raise ServiceError('orders', '命令包含未知字段')
        return service.submit(match_id=match_id, actor_id=player, **body.model_dump())

    if onebot_settings:
        from .onebot import create_onebot_router
        app.include_router(create_onebot_router(service, onebot_settings, client=onebot_client))
    if official_settings is None and os.environ.get('IBS_QQ_APP_ID'):
        from .qq_official import QQOfficialSettings
        official_settings = QQOfficialSettings.from_env()
    if official_settings:
        from .qq_official import create_qq_official_router
        app.include_router(create_qq_official_router(
            service, official_settings, client=official_client, transport=official_transport))
    return app
