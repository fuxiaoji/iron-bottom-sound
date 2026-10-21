from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import json

from PIL import Image
import pytest

from iron_bottom_sound.bot.service import BattleService, ServiceError
from iron_bottom_sound.models import Side


@pytest.fixture
def service(tmp_path):
    s = BattleService(tmp_path / 'bot.sqlite3')
    yield s
    s.close()


def create(s, **kw):
    return s.create('agent:blue', 'test', request_id='create', **kw)


def submit_auto(s, status, actor, key):
    return s.auto(status['match_id'], actor, 'test', status['revision'], key)


@pytest.mark.parametrize('mode', ['classic', 'formation'])
@pytest.mark.parametrize('opponent', ['pve', 'pvp'])
def test_real_engine_both_modes_and_opponents(service, mode, opponent):
    state = create(service, mode=mode, opponent=opponent)
    mid = state['match_id']
    if opponent == 'pvp':
        service.join(mid, 'agent:red', 'test', request_id='join')
    phases = []
    for n in range(8):
        before = service.status(mid, 'agent:blue', 'test')
        if before['complete']:
            break
        phases.append(before['phase'])
        blue = service.suggest(mid, 'agent:blue', 'test')
        red = service.suggest(mid, 'agent:red', 'test') if opponent == 'pvp' else None
        result = service.submit(mid, 'agent:blue', 'test', blue['orders'], before['revision'], f'b{n}')
        if red:
            assert not result['advanced']
            assert result['revision'] == before['revision']
            result = service.submit(mid, 'agent:red', 'test', red['orders'], before['revision'], f'r{n}')
        assert result['advanced'] and result['revision'] == before['revision'] + 1
    assert {'movement_planning', 'torpedo_planning', 'gunnery'} <= set(phases)
    assert result['turn'] >= 2
    png = service.screenshot(mid, 'agent:blue', 'test')
    image = Image.open(BytesIO(png))
    assert image.format == 'PNG' and image.width > 1000


def test_idempotency_create_submit_auto_and_conflicting_payload(service):
    a = create(service)
    assert create(service) == a
    mid = a['match_id']
    b = submit_auto(service, a, 'agent:blue', 'auto1')
    assert submit_auto(service, a, 'agent:blue', 'auto1') == b
    assert service.status(mid, 'agent:blue', 'test')['revision'] == 1
    with pytest.raises(ServiceError, match='不同操作'):
        service.auto(mid, 'agent:blue', 'test', 1, 'auto1')
    with pytest.raises(ServiceError) as exc:
        service.auto(mid, 'agent:blue', 'test', 0, 'new-stale')
    assert exc.value.code == 'stale_revision'


def test_failed_orders_rollback_all_state_and_ai_and_receipts(service):
    a = create(service)
    mid = a['match_id']
    before = service.db.execute('SELECT state FROM bot_matches').fetchone()[0]
    with pytest.raises(ServiceError):
        service.submit(mid, 'agent:blue', 'test', {'movement': [{'ship_id': 'not-owned', 'plan': '1'}]}, 0, 'bad')
    assert service.db.execute('SELECT state FROM bot_matches').fetchone()[0] == before
    assert service.db.execute("SELECT count(*) FROM bot_receipts WHERE request='bad'").fetchone()[0] == 0
    assert not service.pending_notifications()
    assert submit_auto(service, a, 'agent:blue', 'good')['revision'] == 1


def test_waiting_seat_and_cross_room_and_cross_user_fail_closed(service):
    a = create(service, opponent='pvp')
    mid = a['match_id']
    with pytest.raises(ServiceError) as exc:
        submit_auto(service, a, 'agent:blue', 'waiting')
    assert exc.value.code == 'waiting'
    for method in (service.status, service.legal, service.suggest, service.screenshot):
        with pytest.raises(ServiceError):
            method(mid, 'agent:intruder', 'test')
        with pytest.raises(ServiceError):
            method(mid, 'agent:blue', 'wrong-room')
    with pytest.raises(ServiceError):
        service.join(mid, 'agent:red', 'wrong-room', request_id='join')
    service.join(mid, 'agent:red', 'test', request_id='join')
    with pytest.raises(ServiceError):
        service.join(mid, 'agent:third', 'test', request_id='join')


def test_opponent_sealed_plan_not_in_other_view(service):
    a = create(service, opponent='pvp')
    mid = a['match_id']
    service.join(mid, 'agent:red', 'test', request_id='join')
    before = service.suggest(mid, 'agent:red', 'test')
    submit_auto(service, a, 'agent:blue', 'ready')
    after = service.suggest(mid, 'agent:red', 'test')
    assert before == after
    red = service.status(mid, 'agent:red', 'test')
    assert all(e['payload'].get('secret_side') != 'allies' for e in red['observation']['recent_events'])
    with pytest.raises(ServiceError) as exc:
        service.auto(mid, 'agent:blue', 'test', 0, 'second')
    assert exc.value.code == 'already_ready'


def test_restart_preserves_sealed_orders_and_receipts(tmp_path):
    path = tmp_path / 'bot.sqlite3'
    s = BattleService(path)
    a = create(s, opponent='pvp')
    mid = a['match_id']
    s.join(mid, 'agent:red', 'test', request_id='join')
    first = submit_auto(s, a, 'agent:blue', 'sealed')
    s.close()
    resumed = BattleService(path)
    assert resumed.auto(mid, 'agent:blue', 'test', 0, 'sealed') == first
    state = resumed.status(mid, 'agent:red', 'test')
    assert state['ready'] == ['allies'] and state['revision'] == 0
    assert submit_auto(resumed, state, 'agent:red', 'finish')['revision'] == 1
    resumed.close()


def test_concurrent_duplicate_only_one_commit(service):
    a = create(service)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: submit_auto(service, a, 'agent:blue', 'same'), range(2)))
    assert results[0] == results[1]
    assert service.status(a['match_id'], 'agent:blue', 'test')['revision'] == 1


def test_seat_side_phase_and_unknown_fields_rejected(service):
    a = create(service)
    for payload in ({'side': 'axis'}, {'phase': 'gunnery'}, {'invented': True}):
        with pytest.raises(ServiceError):
            service.submit(a['match_id'], 'agent:blue', 'test', payload, 0, json.dumps(payload))


def test_outbox_is_atomic_persistent_and_only_for_qq_seats(tmp_path):
    path = tmp_path / 'bot.sqlite3'
    s = BattleService(path)
    a = s.create('qq:123', 'qq:456', request_id='new')
    s.auto(a['match_id'], 'qq:123', 'qq:456', 0, 'go')
    queue = s.pending_notifications()
    assert len(queue) == 2 and queue[0]['actor_id'] == 'qq:123'
    assert queue[1]['group_id'] == '456' and 'actor_id' not in queue[1]
    assert queue[0]['revision'] == 1 and queue[0]['image']
    s.close()
    s = BattleService(path)
    assert s.pending_notifications() == queue
    for item in queue:
        s.acknowledge_notification(item['id'])
    assert not s.pending_notifications()
    s.close()


def test_two_service_instances_serialize_same_sqlite(tmp_path):
    path = tmp_path / 'shared.sqlite3'
    first, second = BattleService(path), BattleService(path)
    a = create(first, opponent='pvp')
    mid = a['match_id']
    second.join(mid, 'agent:red', 'test', request_id='join')
    blue = first.suggest(mid, 'agent:blue', 'test')
    red = second.suggest(mid, 'agent:red', 'test')
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(s.submit, mid, actor, 'test', p['orders'], 0, key)
                   for s, actor, p, key in [(first, 'agent:blue', blue, 'b'), (second, 'agent:red', red, 'r')]]
        results = [f.result() for f in futures]
    assert sorted(r['advanced'] for r in results) == [False, True]
    assert first.status(mid, 'agent:blue', 'test')['revision'] == 1
    assert second.status(mid, 'agent:red', 'test')['revision'] == 1
    first.close()
    second.close()
