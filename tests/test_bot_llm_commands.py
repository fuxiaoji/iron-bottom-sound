"""Isolated real-engine LLM command integration with a deterministic fake client.

No provider, credential, production match, or network transport is used here.
"""
from copy import deepcopy
import json
from threading import Thread

import pytest

from iron_bottom_sound.bot.service import BattleService, ServiceError
from iron_bottom_sound.models import Side


ROOM = 'qqbot:123:GROUP'
ACTOR = 'qqbot:123:member:GROUP:OWNER'
PEER = 'qqbot:123:member:GROUP:PEER'
VIEWER = 'qqbot:123:member:GROUP:VIEWER'
C2C = 'qqbot:123:c2c:PRIVATE_USER'


class FakeClient:
    def __init__(self, response=None, hook=None):
        self.response = response if response is not None else {'report': '本方战况简报', 'advice': ['先查看当前阶段。'], 'model': 'fake-model'}
        self.hook = hook
        self.calls = []

    def generate(self, *, task, context, instruction=''):
        self.calls.append({'task': task, 'context': deepcopy(context), 'instruction': instruction})
        if self.hook:
            self.hook(task, context, instruction)
        return deepcopy(self.response)


@pytest.fixture
def service(tmp_path):
    value = BattleService(tmp_path / 'llm.sqlite')
    yield value
    value.close()


def create(service, *, mode='classic', opponent='pve', side='allies'):
    return service.create(ACTOR, ROOM, mode=mode, opponent=opponent, side=side, request_id='create')


def raw_state(service, match):
    return service.db.execute('SELECT state FROM bot_matches WHERE id=?', (match,)).fetchone()['state']


def run(service, value, client, *, task='report', actor=ACTOR, scope='group', request='llm-one', instruction=''):
    if task == 'orders' and not instruction:
        instruction = '请确认当前阶段；仅执行明确合法的本方命令。'
    return service.llm_run(value['match_id'], actor, ROOM, task=task, scope=scope,
                           instruction=instruction, request_id=request, llm=client)


def rejected(call):
    try:
        result = call()
    except ServiceError as error:
        return error
    assert result.get('submitted') is False
    return result


def binding(service, value):
    challenge = service.issue_identity_link(C2C, ROOM, value['match_id'], value['side'], 'binding')
    service.claim_identity_link(challenge['code'], ACTOR, ROOM)


def assert_bounded_context(context):
    assert isinstance(context, dict) and 'side' in context and 'phase' in context and 'observation' in context
    serialized = json.dumps(context, ensure_ascii=False)
    assert all(secret not in serialized for secret in (ACTOR, PEER, C2C, ROOM, 'WORLD_SECRET_PROBE', 'SEALED_ENEMY_SECRET'))
    banned = {'actor', 'actor_id', 'room', 'room_id', 'state', 'raw_game', 'raw_state',
              'rng', 'rng_state', 'random_state', 'submitted_orders', 'sealed_orders',
              'opponent_orders', 'seats', 'recognition_secret'}
    def visit(value):
        if isinstance(value, dict):
            assert not (set(value) & banned)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(context)


def assert_public_result(result):
    assert not ({'observation', 'orders', 'legal_actions', 'order_schema', 'actor_id', 'room_id'} & set(result))
    assert ACTOR not in json.dumps(result) and C2C not in json.dumps(result)


@pytest.mark.parametrize('mode', ['classic', 'formation'])
@pytest.mark.parametrize('side', ['allies', 'axis'])
def test_group_pve_report_uses_the_unique_human_view_and_never_changes_match(service, mode, side):
    value = create(service, mode=mode, side=side)
    before = raw_state(service, value['match_id'])
    client = FakeClient()
    result = run(service, value, client, actor=VIEWER)
    assert result['submitted'] is False and result['revision'] == 0
    assert result['phase'] == value['phase'] and result['opponent'] == 'pve'
    assert '本方战况简报' in result['text'] and raw_state(service, value['match_id']) == before
    assert len(client.calls) == 1 and client.calls[0]['context']['side'] == side
    assert_bounded_context(client.calls[0]['context'])
    assert_public_result(result)
    with service._transaction():
        _, state = service._load(value['match_id'], ROOM)
        allowed = {s.id for s in service.engine.observe(state.game_id, Side(side)).ships}
    observed = client.calls[0]['context']['observation'].get('ships', [])
    assert {s['id'] for s in observed} <= allowed


def test_pvp_group_report_intersects_views_and_drops_sealed_enemy_orders(service):
    value = create(service, mode='formation', opponent='pvp')
    service.join(value['match_id'], PEER, ROOM, request_id='join')
    legal = service.legal(value['match_id'], PEER, ROOM)
    formations = legal['actions'][0]['schema_hint']['suggested_formations']
    formations[0]['name'] = 'SEALED_ENEMY_SECRET'
    service.submit(value['match_id'], PEER, ROOM, {'formation_setup': formations}, 0, 'enemy-sealed')
    before = raw_state(service, value['match_id'])
    client = FakeClient()
    result = run(service, value, client, actor=VIEWER)
    assert result['submitted'] is False and raw_state(service, value['match_id']) == before
    context = client.calls[0]['context']
    assert_bounded_context(context)
    assert 'order_schema' not in context and 'legal_actions' not in context
    with service._transaction():
        _, state = service._load(value['match_id'], ROOM)
        from iron_bottom_sound.bot.public_view import public_observation
        allowed = {s.id for s in public_observation(service.engine, state).ships}
    assert {s['id'] for s in context['observation'].get('ships', [])} <= allowed
    assert_public_result(result)


def test_private_report_requires_an_owned_and_bound_seat(service):
    value = create(service)
    blocked = FakeClient()
    rejected(lambda: run(service, value, blocked, actor=C2C, scope='c2c'))
    assert blocked.calls == []
    binding(service, value)
    client = FakeClient()
    result = run(service, value, client, actor=C2C, scope='c2c', request='bound-report')
    assert result['submitted'] is False and len(client.calls) == 1
    assert_bounded_context(client.calls[0]['context'])


@pytest.mark.parametrize('mode', ['classic', 'formation'])
@pytest.mark.parametrize('scope', ['group', 'c2c'])
def test_valid_generated_orders_are_submitted_by_the_existing_engine(service, mode, scope, monkeypatch):
    value = create(service, mode=mode)
    orders = {'confirmation': {'ready': True}}
    if mode == 'formation':
        orders = {'formation_setup': service.legal(value['match_id'], ACTOR, ROOM)['actions'][0]['schema_hint']['suggested_formations']}
    actor = ACTOR
    if scope == 'c2c':
        binding(service, value)
        actor = C2C
    client = FakeClient({'orders': orders, 'clarification': '', 'model': 'fake-model'})
    suggest = service._suggest
    ai_sides = []
    def opponent_only(row, state, side):
        ai_sides.append(side.value)
        assert side.value == 'axis'
        return suggest(row, state, side)
    monkeypatch.setattr(service, '_suggest', opponent_only)
    result = run(service, value, client, task='orders', actor=actor, scope=scope, instruction='执行所选方案')
    assert result['submitted'] is True and result['revision'] == 1
    assert result['phase'] != value['phase'] and ai_sides == ['axis']
    context = client.calls[0]['context']
    assert 'order_schema' in context and 'legal_actions' in context
    assert_bounded_context(context)
    assert_public_result(result)


def test_group_spectator_cannot_order_for_either_seat(service):
    value = create(service)
    client = FakeClient({'orders': {'confirmation': {'ready': True}}, 'clarification': ''})
    rejected(lambda: run(service, value, client, task='orders', actor=VIEWER))
    assert client.calls == [] and service.status(value['match_id'], ACTOR, ROOM)['revision'] == 0


def test_ambiguous_instruction_returns_clarification_without_state_machine_fallback(service, monkeypatch):
    value = create(service)
    before = raw_state(service, value['match_id'])
    client = FakeClient({'orders': None, 'clarification': '请说明要由哪艘舰采取什么行动。'})
    def no_fallback(*args, **kwargs):
        pytest.fail('A clarification must never invoke a state-machine fallback')
    monkeypatch.setattr(service, '_suggest', no_fallback)
    result = run(service, value, client, task='orders', instruction='随便弄一下')
    assert result['submitted'] is False and '请说明' in result['text']
    assert raw_state(service, value['match_id']) == before


@pytest.mark.parametrize('orders', [
    {'_auto': True}, {'side': 'axis'}, {'phase': 'gunnery'}, {'unknown': []},
    {'movement': [{'ship_id': 'NOT_OWNED', 'plan': '1'}]}, [], 'not-an-order-object',
])
def test_unsafe_or_engine_rejected_orders_do_not_advance_or_silently_fill(service, orders):
    value = create(service)
    before = raw_state(service, value['match_id'])
    client = FakeClient({'orders': orders, 'clarification': ''})
    rejected(lambda: run(service, value, client, task='orders'))
    assert len(client.calls) == 1 and raw_state(service, value['match_id']) == before
    assert service.status(value['match_id'], ACTOR, ROOM)['revision'] == 0


@pytest.mark.parametrize('orders', [
    {},
    {'side': 'allies', 'phase': 'reinforcement'},
    {'movement': []},
    {'movement': [], 'gunnery': [], 'torpedoes': [], 'formation_setup': []},
    {'confirmation': {}},
    {'confirmation': None},
    {'confirmation': {'ready': False}},
    {'confirmation': {'ready': 1}},
    {'confirmation': {'ready': 'true'}},
    {'confirmation': {'ready': True, 'unknown_nested_field': 'PRIVATE_NESTED_PROBE'}},
])
def test_implicit_empty_confirmation_and_unknown_nested_fields_do_not_advance(service, orders):
    value = create(service)
    before = raw_state(service, value['match_id'])
    client = FakeClient({'orders': orders, 'clarification': ''})
    result = run(service, value, client, task='orders')
    assert result['submitted'] is False and len(client.calls) == 1
    assert raw_state(service, value['match_id']) == before
    assert service.status(value['match_id'], ACTOR, ROOM)['revision'] == 0
    assert 'PRIVATE_NESTED_PROBE' not in result['text']


def test_group_pvp_clarification_never_echoes_model_private_tactical_text(service):
    value = create(service, opponent='pvp')
    service.join(value['match_id'], PEER, ROOM, request_id='join')
    before = raw_state(service, value['match_id'])
    client = FakeClient({'orders': None, 'clarification': 'PRIVATE_TACTICAL_SENTINEL：本方隐藏战术与目标。'})
    result = run(service, value, client, task='orders', instruction='请按本方战术下令')
    assert result['submitted'] is False and '需要澄清' in result['text']
    assert 'PRIVATE_TACTICAL_SENTINEL' not in result['text'] and '本方隐藏战术' not in result['text']
    assert raw_state(service, value['match_id']) == before
    assert_public_result(result)


def test_generation_occurs_outside_the_transaction_and_service_lock(service):
    value = create(service)
    def check_unlocked(task, context, instruction):
        assert not service.db.in_transaction
        acquired = []
        def worker():
            ok = service.lock.acquire(timeout=0.5)
            acquired.append(ok)
            if ok:
                service.lock.release()
        thread = Thread(target=worker)
        thread.start()
        thread.join(timeout=2)
        assert not thread.is_alive() and acquired == [True]
    client = FakeClient(hook=check_unlocked)
    assert run(service, value, client)['submitted'] is False


@pytest.mark.parametrize('task', ['report', 'orders'])
def test_event_repetition_and_restart_reuse_one_generation_and_cached_result(service, tmp_path, task):
    value = create(service)
    client = FakeClient() if task == 'report' else FakeClient({'orders': {'confirmation': {'ready': True}}, 'clarification': ''})
    first = run(service, value, client, task=task)
    assert run(service, value, client, task=task) == first and len(client.calls) == 1
    second = BattleService(tmp_path / 'llm.sqlite')
    unused = FakeClient(hook=lambda *_: pytest.fail('A persisted result must not call the provider again'))
    try:
        assert run(second, value, unused, task=task) == first and unused.calls == []
    finally:
        second.close()


def test_reusing_event_with_different_instruction_does_not_call_again(service):
    value = create(service)
    client = FakeClient()
    run(service, value, client, instruction='第一份报告')
    rejected(lambda: run(service, value, client, instruction='更改后的报告'))
    assert len(client.calls) == 1


def test_cross_instance_pending_request_never_starts_another_generation(service, tmp_path):
    value = create(service)
    probes = []
    def pending_probe(task, context, instruction):
        second = BattleService(tmp_path / 'llm.sqlite')
        duplicate = FakeClient()
        try:
            rejected(lambda: run(second, value, duplicate))
            probes.append(len(duplicate.calls))
        finally:
            second.close()
    client = FakeClient(hook=pending_probe)
    result = run(service, value, client)
    assert result['submitted'] is False and probes == [0] and len(client.calls) == 1


def test_prepared_orders_resume_after_restart_without_regeneration(service, tmp_path, monkeypatch):
    class SimulatedCrash(BaseException):
        pass
    value = create(service)
    client = FakeClient({'orders': {'confirmation': {'ready': True}}, 'clarification': ''})
    def crash_before_submit(*args, **kwargs):
        raise SimulatedCrash()
    monkeypatch.setattr(service, 'submit', crash_before_submit)
    with pytest.raises(SimulatedCrash):
        run(service, value, client, task='orders')
    assert len(client.calls) == 1 and service.status(value['match_id'], ACTOR, ROOM)['revision'] == 0
    second = BattleService(tmp_path / 'llm.sqlite')
    unused = FakeClient(hook=lambda *_: pytest.fail('Prepared orders must resume without regenerating'))
    try:
        result = run(second, value, unused, task='orders')
        assert result['submitted'] is True and result['revision'] == 1 and unused.calls == []
        assert run(second, value, unused, task='orders') == result and unused.calls == []
    finally:
        second.close()


def test_state_changed_while_model_generates_is_rejected_without_a_second_advance(service):
    value = create(service)
    def other_progress(task, context, instruction):
        service.auto(value['match_id'], ACTOR, ROOM, 0, 'concurrent-player-progress')
    client = FakeClient({'orders': {'confirmation': {'ready': True}}, 'clarification': ''}, hook=other_progress)
    rejected(lambda: run(service, value, client, task='orders'))
    assert service.status(value['match_id'], ACTOR, ROOM)['revision'] == 1
    assert len(client.calls) == 1


def test_provider_failure_has_no_fallback_or_raw_error_disclosure_and_same_event_does_not_retry(service, monkeypatch):
    value = create(service)
    before = raw_state(service, value['match_id'])
    def fail_provider(*args):
        raise TimeoutError('PRIVATE_PROVIDER_RESPONSE_WITH_CREDENTIALS')
    client = FakeClient(hook=fail_provider)
    def no_fallback(*args, **kwargs):
        pytest.fail('Provider failure must not fall back to a state-machine order')
    monkeypatch.setattr(service, '_suggest', no_fallback)
    for _ in range(2):
        result = rejected(lambda: run(service, value, client, task='orders'))
        assert 'PRIVATE_PROVIDER_RESPONSE_WITH_CREDENTIALS' not in str(result)
    assert len(client.calls) == 1 and raw_state(service, value['match_id']) == before
