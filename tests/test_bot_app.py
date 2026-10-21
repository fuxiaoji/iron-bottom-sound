import asyncio
import hashlib
import hmac
import json

from fastapi.testclient import TestClient
import httpx
import pytest

from iron_bottom_sound.bot.app import create_app
from iron_bottom_sound.bot.onebot import BotSettings
from iron_bottom_sound.bot.service import BattleService


@pytest.fixture
def api(tmp_path):
    service = BattleService(tmp_path / 'bot.sqlite3')
    app = create_app(service, identities={'blue-token': 'agent:blue', 'red-token': 'agent:red'})
    with TestClient(app) as client:
        yield service, client
    service.close()


def auth(token='blue-token'):
    return {'Authorization': 'Bearer ' + token}


def test_http_fixed_identity_schema_auth_and_png(api):
    service, client = api
    assert client.get('/health').json()['engine'] == 'python'
    assert client.get('/v1/scenarios').status_code == 401
    assert client.get('/v1/scenarios', headers=auth('wrong')).status_code == 401
    assert client.get('/v1/scenarios', headers=auth()).status_code == 200
    payload = dict(room_id='test', request_id='new', opponent='pvp')
    a = client.post('/v1/matches', headers=auth(), json={**payload, 'actor_id': 'agent:red'})
    assert a.status_code == 422
    a = client.post('/v1/matches', headers=auth(), json=payload)
    assert a.status_code == 200
    mid = a.json()['match_id']
    assert client.get(f'/v1/matches/{mid}/status', params={'room_id': 'test'}, headers=auth('red-token')).status_code == 403
    assert client.get(f'/v1/matches/{mid}/status', params={'room_id': 'other'}, headers=auth()).status_code == 404
    png = client.get(f'/v1/matches/{mid}/screenshot', params={'room_id': 'test'}, headers=auth())
    assert png.headers['content-type'] == 'image/png' and png.content.startswith(b'\x89PNG')
    assert png.headers['cache-control'] == 'no-store'
    assert client.post(f'/v1/matches/{mid}/join', headers=auth('red-token'), json={'room_id': 'test', 'request_id': 'join'}).status_code == 200
    suggested = client.get(f'/v1/matches/{mid}/suggest', headers=auth(), params={'room_id': 'test'}).json()
    body = dict(room_id='test', request_id='orders', expected_revision=0, orders=suggested['orders'])
    assert client.post(f'/v1/matches/{mid}/orders', headers=auth(), json={**body, 'expected_revision': True}).status_code == 422
    r = client.post(f'/v1/matches/{mid}/orders', headers=auth(), json=body)
    assert r.status_code == 200 and r.json()['ready'] == ['allies']
    assert client.post(f'/v1/matches/{mid}/orders', headers=auth(), json=body).json() == r.json()
    assert client.post(f'/v1/matches/{mid}/orders', headers=auth(), json={**body, 'request_id': 'again'}).status_code == 409


def signed(event, secret='bridge-secret'):
    data = json.dumps(event, ensure_ascii=False).encode()
    return data, {'X-Signature': 'sha1=' + hmac.new(secret.encode(), data, hashlib.sha1).hexdigest()}


def test_real_qq_group_create_dm_submit_and_durable_delivery(tmp_path):
    service = BattleService(tmp_path / 'bot.sqlite3')
    sent = []
    fail = [False]

    def receive(request):
        sent.append(json.loads(request.content))
        return httpx.Response(200, json={'status': 'failed' if fail[0] else 'ok', 'retcode': 1 if fail[0] else 0,
                                         'data': {'message_id': len(sent)}})

    outbound = httpx.AsyncClient(transport=httpx.MockTransport(receive))
    settings = BotSettings(self_id='999', secret='bridge-secret', token='action-token', allowed_groups=frozenset({'456'}))
    app = create_app(service, identities={'qq-agent-token': 'qq:123'}, onebot_settings=settings, onebot_client=outbound, notification_interval=None)
    with TestClient(app) as client:
        base = dict(self_id=999, post_type='message', message_type='group', user_id=123, group_id=456,
                    message_id=1, message=[{'type': 'at', 'data': {'qq': '999'}},
                    {'type': 'text', 'data': {'text': ' 铁底湾 创建 普通 pve'}}])
        data, headers = signed(base)
        assert client.post('/onebot/events', content=data, headers=headers).status_code == 200
        mid = service.matches('qq:123', 'qq:456')[0]['match_id']
        assert len(sent) == 1 and sent[0]['group_id'] == 456
        assert 'observation' not in json.dumps(sent)
        dm = dict(self_id=999, post_type='message', message_type='private', user_id=123, message_id=2,
                  message=[{'type': 'text', 'data': {'text': f'铁底湾 456 {mid} 自动 0'}}])
        data, headers = signed(dm)
        assert client.post('/onebot/events', content=data, headers=headers).status_code == 200
        assert service.status(mid, 'qq:123', 'qq:456')['revision'] == 1
        queue = service.pending_notifications()
        assert queue
        # Failed action delivery remains pending, then can recover without replaying gameplay.
        fail[0] = True
        client.portal.call(app.state.notifier.flush)
        assert service.pending_notifications() == queue
        fail[0] = False
        client.portal.call(app.state.notifier.flush)
        assert not service.pending_notifications()
        # Same QQ message after a phase change replays its mutation receipt.
        assert client.post('/onebot/events', content=data, headers=headers).status_code == 200
        assert service.status(mid, 'qq:123', 'qq:456')['revision'] == 1
        assert not service.pending_notifications()
        # An MCP identity mapped to the same QQ actor continues exactly that seat.
        state = client.get(f'/v1/matches/{mid}/status', params={'room_id': 'qq:456'}, headers=auth('qq-agent-token')).json()
        assert state['revision'] == 1 and state['side'] == 'allies'
        client.portal.call(outbound.aclose)
    service.close()


@pytest.mark.parametrize('identities', [{'非ASCII': 'agent:blue'}, {'a b': 'agent:blue'},
                                     {'ascii': 'qq:bad'}, {'ascii': 'qq:0123'}, {'ascii': 'agent:'}])
def test_invalid_identity_config_rejected(tmp_path, identities):
    service = BattleService(tmp_path / 'bot.sqlite3')
    with pytest.raises(ValueError):
        create_app(service, identities=identities)
    service.close()


def test_notifications_skip_revoked_page_and_failed_recipient(tmp_path):
    from iron_bottom_sound.bot.app import NotificationDelivery
    service = BattleService(tmp_path / 'bot.sqlite3')
    base = dict(match_id='public', revision=1, summary='public summary', image='cG5n')
    for _ in range(25):
        service.db.execute('INSERT INTO bot_outbox(payload) VALUES(?)',
                           (json.dumps(dict(base, room_id='qq:111', actor_id='qq:123')),))
    # First allowed recipient fails; the other seat and public group still receive.
    for target in ({'actor_id': 'qq:123'}, {'actor_id': 'qq:789'}, {'group_id': '456'}):
        service.db.execute('INSERT INTO bot_outbox(payload) VALUES(?)',
                           (json.dumps(dict(base, room_id='qq:456', **target)),))
    service.db.commit()
    sent = []
    def receive(request):
        data = json.loads(request.content)
        sent.append(data)
        bad = data.get('user_id') == 123
        return httpx.Response(200, json={'status': 'failed' if bad else 'ok', 'retcode': 1 if bad else 0})
    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(receive)) as client:
            settings = BotSettings('999', 'secret', allowed_groups=frozenset({'456'}))
            await NotificationDelivery(service, settings, client).flush()
    asyncio.run(check())
    assert len(sent) == 3
    assert sent[1]['user_id'] == 789 and sent[2]['group_id'] == 456
    assert service.db.execute('SELECT count(*) FROM bot_outbox WHERE delivered=0').fetchone()[0] == 26
    service.close()


def test_notification_long_text_acknowledges_only_complete_delivery(tmp_path):
    from iron_bottom_sound.bot.app import NotificationDelivery
    service = BattleService(tmp_path / 'bot.sqlite3')
    summary = '长战况' * 1200
    service.db.execute('INSERT INTO bot_outbox(payload) VALUES(?)',
        (json.dumps(dict(room_id='qq:456', actor_id='qq:123', summary=summary, image='cG5n')),))
    service.db.commit()
    sent = []
    def receive(request):
        data = json.loads(request.content);sent.append(data)
        return httpx.Response(200,json={'status':'ok','retcode':0})
    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(receive)) as client:
            await NotificationDelivery(service,BotSettings('999','secret',allowed_groups=frozenset({'456'})),client).flush()
    asyncio.run(check())
    text = ''.join(segment['data']['text'] for batch in sent for segment in batch['message'] if segment['type']=='text')
    assert text == summary and len(sent) == 3
    assert all(sum(len(segment['data']['text']) for segment in batch['message'] if segment['type']=='text') <= 1500 for batch in sent)
    assert sent[-1]['message'][-1]['type']=='image'
    assert not service.pending_notifications()
    service.close()
