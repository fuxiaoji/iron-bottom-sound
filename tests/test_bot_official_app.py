import time
import json

from fastapi.testclient import TestClient
import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from iron_bottom_sound.bot.app import create_app
from iron_bottom_sound.bot.qq_official import QQOfficialSettings
from iron_bottom_sound.bot.service import BattleService


def test_factory_mounts_official_callback_and_accepts_fixed_c2c_identity(tmp_path):
    service = BattleService(tmp_path / 'official.sqlite3')
    settings = QQOfficialSettings(app_id='1905878837', app_secret='a' * 32)
    app = create_app(service, identities={'private-token': 'qqbot:1905878837:c2c:user_openid'},
                     official_settings=settings)
    with TestClient(app) as client:
        response = client.post('/qq-official/events', json={
            'op': 13, 'd': {'plain_token': 'test_challenge', 'event_ts': str(int(time.time()))}})
        assert response.status_code == 200
        assert response.json()['plain_token'] == 'test_challenge'
        assert response.json()['signature']
        response = client.get('/v1/matches', params={'room_id': 'qqbot:1905878837:group'},
                              headers={'Authorization': 'Bearer private-token'})
        assert response.status_code == 200 and response.json() == []
    service.close()


@pytest.mark.parametrize('identity', [
    'qqbot:user_openid', 'qqbot:1905878837:member:user_openid',
    'qqbot:1905878837:c2c:', 'qqbot:wrong-app:c2c:user_openid',
])
def test_official_mcp_identity_requires_app_and_domain(tmp_path, identity):
    service = BattleService(tmp_path / 'invalid.sqlite3')
    try:
        with pytest.raises(ValueError):
            create_app(service, identities={'private-token': identity})
    finally:
        service.close()


def test_only_signed_discovery_persists_opaque_group_without_opening_match(tmp_path):
    service = BattleService(tmp_path / 'discovery.sqlite3')
    settings = QQOfficialSettings(app_id='1905878837', app_secret='a' * 32)
    sent = []

    def transport(request):
        if request.url.host == 'bots.qq.com':
            return httpx.Response(200, json={'access_token': 'test-access', 'expires_in': 7200})
        sent.append(json.loads(request.content))
        return httpx.Response(200, json={'id': 'platform-reply'})

    app = create_app(service, identities={}, official_settings=settings,
                     official_transport=httpx.MockTransport(transport))
    payload = {'op': 0, 't': 'GROUP_AT_MESSAGE_CREATE', 'd': {
        'id': 'signed-group-discovery', 'author': {'member_openid': 'member'},
        'group_openid': 'opaque_group', 'content': '帮助',
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}}
    body = json.dumps(payload).encode()
    stamp = str(int(time.time()))
    key = Ed25519PrivateKey.from_private_bytes(b'a' * 32)
    with TestClient(app) as client:
        assert client.post('/qq-official/events', content=body, headers={
            'X-Signature-Timestamp': stamp,
            'X-Signature-Ed25519': key.sign(stamp.encode() + body).hex()}).status_code == 200
        rows = service.db.execute('SELECT app_id,group_openid FROM bot_official_groups').fetchall()
        assert [tuple(row) for row in rows] == [('1905878837', 'opaque_group')]
        assert 'opaque_group' in sent[0]['content']
        assert service.db.execute('SELECT count(*) FROM bot_matches').fetchone()[0] == 0
        payload['d']['group_openid'] = 'forged_group'
        assert client.post('/qq-official/events', json=payload).status_code == 401
        assert service.db.execute('SELECT count(*) FROM bot_official_groups').fetchone()[0] == 1
    service.close()
