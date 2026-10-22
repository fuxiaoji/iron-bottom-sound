"""Signed QQ group/private LLM commands over the real isolated battle service."""
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
import pytest

from iron_bottom_sound.bot.qq_official import QQOfficialSettings, create_qq_official_router, TOKEN_URL
from iron_bottom_sound.bot.service import BattleService
from test_bot_qq_official import SECRET, event, messages, post

ROOM = 'qqbot:12345:GROUP'
OWNER = 'qqbot:12345:member:GROUP:MEMBER'


class Model:
    def __init__(self):
        self.calls = []
        self.orders = {'confirmation': {'ready': True}}

    def generate(self, *, task, context, instruction=''):
        self.calls.append(dict(task=task, context=context, instruction=instruction))
        if task == 'report':
            return {'report': '当前仅依据已发现敌情。', 'advice': ['先检查本阶段。']}
        return {'orders': self.orders, 'clarification': ''}


@pytest.fixture
def live(tmp_path):
    service = BattleService(tmp_path/'llm-qq.sqlite3')
    match = service.create(OWNER, ROOM, request_id='create')['match_id']
    model, seen = Model(), []
    def http(request):
        payload = json.loads(request.content)
        seen.append((str(request.url), payload, {}))
        if str(request.url) == TOKEN_URL:
            return httpx.Response(200, json={'access_token':'MOCK','expires_in':7200})
        if request.url.path.endswith('/files'):
            return httpx.Response(200, json={'file_info':'MOCK_PNG'})
        return httpx.Response(200, json={'id':'mock-reply'})
    def build():
        app = FastAPI()
        app.include_router(create_qq_official_router(service,
            QQOfficialSettings('12345',SECRET,frozenset({'GROUP'})),
            transport=httpx.MockTransport(http), llm_client=model))
        return TestClient(app)
    with build() as client:
        yield service, match, model, seen, client, build
    service.close()


@pytest.mark.parametrize('prefix', ['/参谋', '铁底湾 参谋', '<@!12345> /参谋'])
def test_group_report_is_readonly_public_and_works_without_private_binding(live, prefix):
    s, match, llm, seen, client, _ = live
    response = post(client, event(prefix+' 现在优先做什么？', sender='VIEWER'))
    assert response.status_code == 200
    assert len(llm.calls) == 1 and llm.calls[0]['task'] == 'report'
    assert llm.calls[0]['instruction'] == '现在优先做什么？'
    assert '未下达命令' in messages(seen)[0]['content']
    assert all('/groups/GROUP/' in url for url,_,_ in seen if url != TOKEN_URL)
    assert s.status(match,OWNER,ROOM)['revision'] == 0


def test_group_natural_order_executes_one_phase_and_returns_public_png(live):
    s, match, llm, seen, client, _ = live
    command = event('/下令 本阶段无增援，确认不行动',message_id='order')
    post(client,command)
    assert len(llm.calls) == 1 and llm.calls[0]['task'] == 'orders'
    assert llm.calls[0]['instruction'] == '本阶段无增援，确认不行动'
    assert s.status(match,OWNER,ROOM)['revision'] == 1
    assert '原引擎校验' in messages(seen)[0]['content']
    assert len(messages(seen)) == 2 and any(url.endswith('/files') for url,_,_ in seen)
    post(client,command)
    assert len(llm.calls) == 1 and s.status(match,OWNER,ROOM)['revision'] == 1


def test_router_restart_replays_persisted_result_without_second_api_or_phase(live):
    s, match, llm, seen, client, build = live
    command=event('/下令 '+match+' 本阶段确认不行动',message_id='restart-order')
    post(client,command)
    with build() as other:
        post(other,command)
    assert len(llm.calls) == 1 and s.status(match,OWNER,ROOM)['revision'] == 1


def test_group_spectator_cannot_order_or_call_model(live):
    s, match, llm, seen, client, _ = live
    post(client,event('/下令 '+match+' 随便开火',sender='VIEWER'))
    assert not llm.calls and not any(url.endswith('/files') for url,_,_ in seen)
    assert s.status(match,OWNER,ROOM)['revision'] == 0


@pytest.mark.parametrize('content', ['/下令', '/下令 '+('x'*1700)])
def test_missing_or_excess_instruction_does_not_call_model(live, content):
    s, match, llm, seen, client, _ = live
    post(client,event(content))
    assert not llm.calls and s.status(match,OWNER,ROOM)['revision'] == 0


def test_multiple_matches_require_explicit_id_before_model_or_orders(live):
    s, match, llm, seen, client, _ = live
    s.create(OWNER,ROOM,request_id='second')
    post(client,event('/下令 确认本阶段'))
    assert not llm.calls and '多个对局' in messages(seen)[0]['content']
    seen.clear()
    post(client,event('/参谋 '+match+' 请汇报',message_id='specific'))
    assert len(llm.calls) == 1 and llm.calls[0]['instruction'] == '请汇报'


def test_c2c_requires_binding_and_then_uses_original_seat(live):
    s, match, llm, seen, client, _ = live
    post(client,event('/参谋',private=True,message_id='unbound'))
    assert not llm.calls
    issue=s.issue_identity_link(actor_id='qqbot:12345:c2c:MEMBER',room_id=ROOM,match_id=match,side='allies')
    s.claim_identity_link(issue['code'],actor_id=OWNER,room_id=ROOM)
    seen.clear()
    post(client,event('/参谋 请分析',private=True,message_id='bound'))
    assert len(llm.calls) == 1 and llm.calls[0]['context']['side']=='allies'
    assert any(url.endswith('/users/MEMBER/messages') for url,_,_ in seen)


def test_bad_signature_or_unallowlisted_group_never_calls_model(live):
    s, match, llm, seen, client, _ = live
    assert post(client,event('/参谋'),signed=False).status_code == 401
    post(client,event('/参谋',group='OTHER',message_id='other-room'))
    assert not llm.calls


def test_pvp_group_order_never_echoes_private_model_or_order_fields(live):
    s, _, llm, seen, client, _ = live
    match=s.create(OWNER,ROOM,opponent='pvp',request_id='pvp')['match_id']
    s.join(match,'qqbot:12345:member:GROUP:OTHER',ROOM,request_id='join')
    llm.orders={'confirmation':{'ready':True}}
    post(client,event('/下令 '+match+' 确认不行动',message_id='pvp-order'))
    content=''.join(p['content'] for p in messages(seen) if p.get('content'))
    assert '本方订单已封存' in content
    assert 'observation' not in content and 'confirmation' not in content and 'gun_mounts' not in content
    assert s.status(match,OWNER,ROOM)['revision'] == 0
    assert s.status(match,OWNER,ROOM)['ready'] == ['allies']
