"""Trusted referee service against real isolated games, with no provider IO."""
from copy import deepcopy
import json
from threading import Thread

import httpx
import pytest

from iron_bottom_sound.bot.llm_client import BotLLMClient, BotLLMSettings
from iron_bottom_sound.bot.service import BattleService, ServiceError
from iron_bottom_sound.models import GameState, HexCoord, Phase, Side

ROOM = 'qqbot:123:GROUP'
ACTOR = 'qqbot:123:member:GROUP:OWNER'
PEER = 'qqbot:123:member:GROUP:PEER'
C2C = 'qqbot:123:c2c:PRIVATE_USER'
ADMINS = frozenset({ACTOR})


class FakeClient:
    def __init__(self, response, hook=None):
        self.response, self.hook, self.calls = response, hook, []

    def generate(self, *, task, context, instruction=''):
        self.calls.append(dict(task=task, context=deepcopy(context), instruction=instruction))
        if self.hook:
            self.hook()
        return deepcopy(self.response)


def plan(action='report', match=None, *, changes=None, create=None, steps=1, message='裁判公开说明'):
    return dict(action=action, match_id=match, create=create, changes=changes, steps=steps, message=message)


def create(service, *, mode='classic', opponent='pve', request='create', actor=ACTOR):
    return service.create(actor, ROOM, mode=mode, opponent=opponent, request_id=request)


def run(service, value, client, *, request='referee', instruction='请执行明确的裁判操作', actor=ACTOR, room=ROOM, scope='group', admins=ADMINS):
    match = value['match_id'] if isinstance(value, dict) else value
    return service.referee_run(match, actor_id=actor, room_id=room, instruction=instruction, scope=scope,
                               request_id=request, llm=client, admins=admins)


def state(service, value):
    match = value['match_id'] if isinstance(value, dict) else value
    row = service.db.execute('SELECT * FROM bot_matches WHERE id=?', (match,)).fetchone()
    return dict(row), GameState.model_validate_json(row['state'])


def own(service, value):
    return next(s for s in state(service, value)[1].ships.values() if s.side == Side.ALLIES and s.position is not None)


def patch(ship, **fields):
    return {'ships': [{'ship_id': ship, 'fields': fields}], 'game': {}}


def assert_public(result):
    text = json.dumps(result, ensure_ascii=False)
    assert all(secret not in text for secret in (ACTOR, PEER, ROOM, C2C, 'PRIVATE-MODEL-MUTATION'))
    assert not ({'orders', 'observation', 'seats', 'raw_state', 'rng_counter'} & set(result))


@pytest.fixture
def service(tmp_path):
    value = BattleService(tmp_path / 'referee.sqlite')
    yield value
    value.close()


@pytest.mark.parametrize('actor,room', [(PEER, ROOM), (C2C, ROOM), ('qqbot:999:member:GROUP:OWNER', ROOM),
                                        (ACTOR, 'qqbot:123:OTHER')])
def test_unauthorized_cannot_call_model_or_claim_request(service, actor, room):
    client = FakeClient(plan())
    with pytest.raises(ServiceError):
        run(service, None, client, actor=actor, room=room)
    assert client.calls == []
    assert service.db.execute('SELECT count(*) FROM bot_referee_calls').fetchone()[0] == 0


def test_bound_c2c_resolves_trusted_identity_and_model_io_holds_no_lock(service):
    value = create(service)
    token = service.issue_identity_link(C2C, ROOM, value['match_id'], 'allies', 'link')
    service.claim_identity_link(token['code'], ACTOR, ROOM)
    acquired = []
    def no_lock():
        assert not service.db.in_transaction
        def other_thread():
            locked = service.lock.acquire(timeout=1)
            acquired.append(locked)
            if locked:
                service.lock.release()
        worker = Thread(target=other_thread)
        worker.start()
        worker.join(2)
        assert acquired == [True]
    client = FakeClient(plan(match=value['match_id']), hook=no_lock)
    result = run(service, value, client, actor=C2C, scope='c2c')
    assert not result['mutated'] and client.calls[0]['task'] == 'referee'
    assert_public(result)


@pytest.mark.parametrize('mode', ['classic', 'formation'])
@pytest.mark.parametrize('opponent', ['pve', 'pvp'])
def test_real_create_fixed_admin_seat_and_persistent_exactly_once(tmp_path, mode, opponent):
    path = tmp_path / 'create.sqlite'
    first = BattleService(path)
    client = FakeClient(plan('create', create=dict(mode=mode, opponent=opponent, scenario_id='IBS-S-03', side='axis', seed=7),
                             message='PRIVATE-MODEL-MUTATION'))
    result = run(first, None, client)
    assert result['created'] and result['mutated'] and result['revision'] == 0
    row, game = state(first, result)
    assert json.loads(row['seats'])['axis'] == ACTOR and game.seed == 7
    assert row['mode'] == mode and row['opponent'] == opponent
    assert_public(result)
    first.close()
    second = BattleService(path)
    try:
        assert run(second, None, client) == result and len(client.calls) == 1
        assert second.db.execute('SELECT count(*) FROM bot_matches').fetchone()[0] == 1
    finally:
        second.close()


def test_real_client_mock_transport_metadata_connects_and_never_echoes_provider_internals(service):
    value = create(service)
    calls = []
    body = plan('advance', value['match_id'], message='PRIVATE-MODEL-MUTATION')
    def handle(request):
        calls.append(request)
        return httpx.Response(200, json={'choices':[{'finish_reason':'stop','message':{
            'role':'assistant','content':json.dumps(body), 'reasoning_content':'SECRET-REASONING'}}],
            'usage':{'prompt_tokens':5,'total_tokens':9,'prompt_cache_hit_tokens':2,'secret':'SECRET'}})
    client = BotLLMClient(BotLLMSettings(provider='deepseek', api_key='fixture-never-real'), transport=httpx.MockTransport(handle))
    result = run(service, value, client)
    assert result['mutated'] and result['revision'] == 1 and len(calls) == 1
    meta = json.loads(service.db.execute('SELECT meta FROM bot_referee_calls').fetchone()[0])
    assert meta['model'] == 'deepseek-flash' and meta['usage'] == {'prompt_tokens':5,'total_tokens':9,'prompt_cache_hit_tokens':2}
    assert 'SECRET' not in json.dumps(meta) and 'SECRET' not in json.dumps(result)
    assert_public(result)


@pytest.mark.parametrize('mode', ['classic', 'formation'])
@pytest.mark.parametrize('opponent', ['pve', 'pvp'])
def test_advance_real_both_sides_keeps_source_rules_and_one_snapshot(service, mode, opponent):
    value = create(service, mode=mode, opponent=opponent)
    if opponent == 'pvp':
        service.join(value['match_id'], PEER, ROOM, request_id='join')
    before_row, before = state(service, value)
    client = FakeClient(plan('advance', value['match_id'], steps=2, message='PRIVATE-MODEL-MUTATION'))
    result = run(service, value, client)
    assert result['mutated'] and result['revision'] == 2
    _, after = state(service, value)
    assert after.phase != before.phase
    assert after.rule_snapshot == before.rule_snapshot
    assert json.loads(before_row['seats']) == json.loads(state(service, value)[0]['seats'])
    snapshots = service.db.execute('SELECT * FROM bot_state_history WHERE match=?', (value['match_id'],)).fetchall()
    assert len(snapshots) == 1 and snapshots[0]['before_state'] == before_row['state']
    assert snapshots[0]['actor'] == ACTOR and snapshots[0]['operation'] == 'referee_advance'
    assert_public(result)


def test_advance_preserves_existing_pvp_sealed_orders(service):
    value = create(service, mode='formation', opponent='pvp')
    service.join(value['match_id'], PEER, ROOM, request_id='join')
    formations = service.legal(value['match_id'], PEER, ROOM)['actions'][0]['schema_hint']['suggested_formations']
    formations[0]['name'] = 'SEALED-ENEMY-SENTINEL'
    service.submit(value['match_id'], PEER, ROOM, {'formation_setup':formations}, 0, 'peer-seal')
    result = run(service, value, FakeClient(plan('advance', value['match_id'])))
    assert result['mutated']
    after = state(service, value)[1]
    assert any(v.name == 'SEALED-ENEMY-SENTINEL' for v in after.formations.values())


def test_advance_failure_rolls_back_all_steps_and_snapshot(service, monkeypatch):
    value = create(service)
    before = state(service, value)[0]['state']
    original = service._advance_decision
    calls = []
    def fault(game):
        calls.append(1)
        if len(calls) == 2:
            raise RuntimeError('PRIVATE-ENGINE-FAILURE')
        original(game)
    monkeypatch.setattr(service, '_advance_decision', fault)
    result = run(service, value, FakeClient(plan('advance', value['match_id'], steps=2)))
    assert not result['mutated'] and state(service, value)[0]['state'] == before
    assert service.db.execute('SELECT count(*) FROM bot_state_history').fetchone()[0] == 0
    assert 'PRIVATE-ENGINE' not in result['text']


@pytest.mark.parametrize('mode', ['classic', 'formation'])
@pytest.mark.parametrize('opponent', ['pve','pvp'])
def test_patch_real_position_label_heading_hull_fire_and_undo_restores_rng(service, mode, opponent):
    value = create(service, mode=mode, opponent=opponent)
    ship = own(service, value)
    before_row, before = state(service, value)
    client = FakeClient(plan('patch', value['match_id'], changes=patch(ship.id, position='P15', heading=3,
                             hull=ship.hull-1, fire_markers=2), message='PRIVATE-MODEL-MUTATION'))
    result = run(service, value, client, instruction=f'将{ship.name}修正到P15、向南，舰体减少1，火灾2')
    assert result['mutated'] and result['revision'] == 1
    after = state(service, value)[1].ships[ship.id]
    assert after.position.label == 'P15' and after.heading == 3 and after.hull == ship.hull-1 and after.fire_markers == 2
    undone = run(service, value, FakeClient(plan('undo', value['match_id'])), request='undo')
    assert undone['mutated'] and undone['revision'] == 2
    row, restored = state(service, value)
    assert restored.model_dump_json() == before.model_dump_json()
    assert restored.seed == before.seed and restored.rng_counter == before.rng_counter
    assert row['seats'] == before_row['seats']
    assert service.db.execute('SELECT consumed FROM bot_state_history').fetchone()[0] == 1
    assert run(service, value, FakeClient(plan('undo', value['match_id'])), request='undo') == undone
    unavailable = run(service, value, FakeClient(plan('undo', value['match_id'])), request='undo-again')
    assert not unavailable['mutated'] and '没有可撤销' in unavailable['text']


@pytest.mark.parametrize('fields', [
    {'heading':True}, {'hull':10**9}, {'current_speed':10**9}, {'position':{'q':1}},
    {'position':{'q':1,'r':1,'ignored':True}}, {'primary':{'ignored':True}}, {'name':'changed'},
    {'fire_source_attacker':'missing-id'}, {'formation_id':'missing-id'}, {'position':'Z99'},
])
def test_invalid_patch_is_strict_and_atomic(service, fields):
    value = create(service)
    ship = own(service, value)
    before = state(service, value)[0]['state']
    result = run(service, value, FakeClient(plan('patch', value['match_id'], changes=patch(ship.id, **fields))))
    assert not result['mutated'] and state(service, value)[0]['state'] == before
    assert service.db.execute('SELECT count(*) FROM bot_state_history').fetchone()[0] == 0


def test_patch_small_current_map_and_land_are_rejected(service):
    value = create(service)
    ship = own(service, value)
    with service._transaction():
        row, game = service._load(value['match_id'], ROOM)
        game.map_columns, game.map_rows = 5, 5
        game.land_hexes.add('B2')
        service._save(row, game)
    for i, label in enumerate(('P15','B2')):
        before = state(service, value)[0]['state']
        result = run(service, value, FakeClient(plan('patch', value['match_id'], changes=patch(ship.id, position=label))), request='bad-map-'+str(i))
        assert not result['mutated'] and state(service, value)[0]['state'] == before


@pytest.mark.parametrize('fields', [
    {'command_status':'withdrawn'}, {'formation_id':None}, {'reinforcement_turn':3},
    {'sunk':True}, {'sinking_turn':1}, {'sinking_drift_pending':True},
    {'withdrawal_edge':'north'}, {'position':None}, {'hull':0},
])
def test_lifecycle_changes_cannot_silently_break_linked_world_state(service, fields):
    value = create(service,mode='formation')
    ship = own(service,value)
    before = state(service,value)[0]['state']
    result = run(service,value,FakeClient(plan('patch',value['match_id'],changes=patch(ship.id,**fields))))
    assert not result['mutated'] and state(service,value)[0]['state'] == before
    assert any(word in result['text'] for word in ('生命周期','清空'))


@pytest.mark.parametrize('status,fields', [
    ('sunk',{'position':'P15'}), ('withdrawn',{'position':'P15'}), ('sunk',{'hull':2}),
])
def test_sunk_or_withdrawn_ship_cannot_be_moved_or_implicitly_revived(service,status,fields):
    value = create(service)
    ship = own(service,value)
    with service._transaction():
        row,game = service._load(value['match_id'],ROOM)
        if status == 'sunk':
            game.ships[ship.id].sunk, game.ships[ship.id].hull = True,0
        else:
            game.ships[ship.id].command_status = 'withdrawn'
        service._save(row,game)
    before = state(service,value)[0]['state']
    result = run(service,value,FakeClient(plan('patch',value['match_id'],changes=patch(ship.id,**fields))),
                 instruction=f'请直接修改{ship.name}的指定字段')
    assert not result['mutated'] and state(service,value)[0]['state'] == before
    assert '沉没' in result['text']


def test_phase_repair_clears_current_and_historical_sealed_batches(service):
    value = create(service)
    service.auto(value['match_id'], ACTOR, ROOM, 0, 'auto-before')
    _, before = state(service, value)
    assert before.sealed_orders
    result = run(service, value, FakeClient(plan('patch', value['match_id'], changes={'ships':[], 'game':{'phase':'reinforcement','turn':1}})))
    assert result['mutated']
    repaired = state(service, value)[1]
    assert repaired.phase == Phase.REINFORCEMENT and not repaired.submitted_orders and not repaired.sealed_orders


def test_nested_launcher_ammo_change_is_complete_and_bounded(service):
    value = create(service)
    ship = next(s for s in state(service,value)[1].ships.values() if s.side == Side.ALLIES and s.torpedo_launchers and s.torpedo)
    launcher = ship.torpedo_launchers[0]
    amount = max(0, launcher.loaded-1)
    changes = patch(ship.id, torpedo_launchers=[{'id':launcher.id,'loaded':amount}], torpedo={'ammo':ship.torpedo.ammo-launcher.loaded+amount})
    result = run(service, value, FakeClient(plan('patch', value['match_id'], changes=changes)))
    assert result['mutated']
    after = state(service,value)[1].ships[ship.id]
    assert after.torpedo.ammo == sum(v.loaded for v in after.torpedo_launchers)
    before = state(service,value)[0]['state']
    bad = patch(ship.id, torpedo_launchers=[{'id':launcher.id,'loaded':launcher.torpedoes+1}])
    result = run(service,value,FakeClient(plan('patch',value['match_id'],changes=bad)),request='bad-ammo')
    assert not result['mutated'] and state(service,value)[0]['state'] == before


def test_ordinary_submit_snapshot_then_undo_cannot_replay_old_event(service):
    value = create(service)
    before = state(service,value)[1]
    original = service.auto(value['match_id'], ACTOR, ROOM, 0, 'ordinary-event')
    assert original['revision'] == 1
    undo = run(service, value, FakeClient(plan('undo',value['match_id'])))
    assert undo['revision'] == 2
    assert state(service,value)[1].model_dump_json() == before.model_dump_json()
    assert service.auto(value['match_id'], ACTOR, ROOM, 0, 'ordinary-event') == original
    assert state(service,value)[0]['revision'] == 2
    with pytest.raises(ServiceError, match='版本'):
        service.auto(value['match_id'], ACTOR, ROOM, 0, 'new-old-event')


def test_undo_restores_rng_after_real_engine_random_resolution_and_replay_is_deterministic(service):
    value = create(service)
    service.auto(value['match_id'], ACTOR, ROOM, 0, 'rng-0')
    service.auto(value['match_id'], ACTOR, ROOM, 1, 'rng-1')
    before = state(service,value)[1]
    service.auto(value['match_id'], ACTOR, ROOM, 2, 'rng-2')
    resolved = state(service,value)[1]
    assert resolved.rng_counter > before.rng_counter
    result = run(service,value,FakeClient(plan('undo',value['match_id'])))
    assert result['revision'] == 4 and result['mutated']
    restored = state(service,value)[1]
    assert restored.model_dump_json() == before.model_dump_json()
    service.auto(value['match_id'], ACTOR, ROOM, 4, 'rng-replay')
    replay = state(service,value)[1]
    assert replay.model_dump_json() == resolved.model_dump_json()


def test_version_race_rejects_prepared_patch_without_second_mutation(service):
    value = create(service)
    ship = own(service,value)
    client = FakeClient(plan('patch',value['match_id'],changes=patch(ship.id,fire_markers=3)),
                        hook=lambda:service.auto(value['match_id'],ACTOR,ROOM,0,'racing-auto'))
    result = run(service,value,client)
    assert not result['mutated'] and state(service,value)[0]['revision'] == 1
    assert state(service,value)[1].ships[ship.id].fire_markers != 3
    assert '已变化' in result['text']


def test_prepared_restart_resumes_without_api_and_pending_cross_instance_never_reissues(tmp_path, monkeypatch):
    path = tmp_path / 'restart.sqlite'
    first = BattleService(path)
    value = create(first)
    client = FakeClient(plan('advance',value['match_id']))
    class Crash(BaseException):
        pass
    def crash(*args):
        raise Crash()
    monkeypatch.setattr(first,'_referee_apply',crash)
    with pytest.raises(Crash):
        run(first,value,client)
    assert first.db.execute('SELECT status FROM bot_referee_calls').fetchone()[0] == 'prepared'
    first.close()
    second = BattleService(path)
    try:
        result = run(second,value,client)
        assert result['mutated'] and result['revision'] == 1 and len(client.calls) == 1
        second.db.execute("UPDATE bot_referee_calls SET status='pending',result=NULL")
        second.db.commit()
        with pytest.raises(ServiceError) as caught:
            run(second,value,client)
        assert caught.value.code == 'referee_pending' and len(client.calls) == 1
    finally:
        second.close()


def test_create_commit_then_receipt_fault_stays_recoverable_and_does_not_claim_false_failure(service, monkeypatch):
    client = FakeClient(plan('create',create=dict(mode='classic',opponent='pve',scenario_id='IBS-S-03',side='allies',seed=1)))
    original = service._referee_finish
    calls = []
    def once(*args):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError('receipt crash')
        return original(*args)
    monkeypatch.setattr(service,'_referee_finish',once)
    with pytest.raises(ServiceError) as caught:
        run(service,None,client)
    assert caught.value.code == 'referee_recovery'
    assert service.db.execute('SELECT status FROM bot_referee_calls').fetchone()[0] == 'prepared'
    assert service.db.execute('SELECT count(*) FROM bot_matches').fetchone()[0] == 1
    restarted = BattleService(service.db.execute('PRAGMA database_list').fetchone()[2])
    try:
        result = run(restarted,None,client)
        assert result['created'] and result['mutated'] and len(client.calls) == 1
        assert restarted.db.execute('SELECT count(*) FROM bot_matches').fetchone()[0] == 1
    finally:
        restarted.close()


def test_concurrent_instance_pending_does_not_spend_or_apply_again(service):
    value = create(service)
    second = BattleService(service.db.execute('PRAGMA database_list').fetchone()[2])
    blocked = FakeClient(plan('advance',value['match_id']))
    def during_io():
        with pytest.raises(ServiceError) as caught:
            run(second,value,blocked)
        assert caught.value.code == 'referee_pending' and not blocked.calls
    try:
        client = FakeClient(plan('advance',value['match_id']),hook=during_io)
        result = run(service,value,client)
        assert result['mutated'] and result['revision']==1
        assert run(second,value,blocked)==result and not blocked.calls
    finally:
        second.close()


def test_invalid_create_never_echoes_model_chosen_scenario_or_creates_match(service):
    client = FakeClient(plan('create',create=dict(mode='classic',opponent='pve',
        scenario_id='PRIVATE-MODEL-MUTATION',side='allies',seed=1)))
    result = run(service,None,client)
    assert not result['created'] and not result['mutated']
    assert service.db.execute('SELECT count(*) FROM bot_matches').fetchone()[0] == 0
    assert_public(result)


def test_multiple_matches_cannot_be_guessed_and_other_room_target_cannot_be_loaded(service):
    one, two = create(service), create(service, request='create-two')
    result = run(service,None,FakeClient(plan('advance',one['match_id'])))
    assert not result['mutated'] and state(service,one)[0]['revision'] == 0 and state(service,two)[0]['revision'] == 0
    client = FakeClient(plan('advance',one['match_id']))
    with pytest.raises(ServiceError):
        run(service,one,client,actor='qqbot:123:member:OTHER:OWNER',room='qqbot:123:OTHER',
            admins=frozenset({'qqbot:123:member:OTHER:OWNER'}),request='other-room')
    assert not client.calls


def test_context_drops_hidden_world_and_sealed_orders_and_keeps_derived_heading_contract(service):
    value = create(service, mode='formation', opponent='pvp')
    service.join(value['match_id'],PEER,ROOM,request_id='join')
    legal = service.legal(value['match_id'],PEER,ROOM)
    orders = legal['actions'][0]['schema_hint']['suggested_formations']
    orders[0]['name'] = 'SEALED-ENEMY-SENTINEL'
    service.submit(value['match_id'],PEER,ROOM,{'formation_setup':orders},0,'seal')
    with service._transaction():
        row, game = service._load(value['match_id'],ROOM)
        enemy = next(s for s in game.ships.values() if s.side == Side.AXIS)
        enemy.name = 'HIDDEN-WORLD-SENTINEL'
        service._save(row,game)
    client = FakeClient(plan(match=value['match_id']))
    result = run(service,value,client)
    text = json.dumps(client.calls[0]['context'],ensure_ascii=False)
    assert all(s not in text for s in (ACTOR,PEER,ROOM,'HIDDEN-WORLD-SENTINEL','SEALED-ENEMY-SENTINEL'))
    assert 'rng_counter' not in text and 'sealed_orders' not in text and 'submitted_orders' not in text
    context = client.calls[0]['context']
    assert context['current']['view'] == 'shared'
    assert {k:v['name'] for k,v in context['referee_schema']['headings'].items()} == {
        '1':'东北','2':'东南','3':'南','4':'西南','5':'西北','6':'北'}
    assert_public(result)


def test_unknown_hidden_target_requires_explicit_user_reference_but_admin_can_repair_named_ship(service):
    value = create(service,opponent='pvp')
    game = state(service,value)[1]
    enemy = next(s for s in game.ships.values() if s.side == Side.AXIS)
    payload = plan('patch',value['match_id'],changes=patch(enemy.id,fire_markers=2))
    before = state(service,value)[0]['state']
    result = run(service,value,FakeClient(payload),instruction='仅解释当前局面，不要改动未知单位')
    assert not result['mutated'] and state(service,value)[0]['state'] == before
    client = FakeClient(payload)
    result = run(service,value,client,request='named',instruction=f'明确将{enemy.name}的火灾标记改为2')
    assert result['mutated'] and state(service,value)[1].ships[enemy.id].fire_markers == 2
    context = json.dumps(client.calls[0]['context'],ensure_ascii=False)
    assert enemy.id not in context and enemy.name not in context


def test_recent_summaries_are_bounded_own_room_and_do_not_persist_instruction(service):
    value = create(service)
    ship = own(service,value)
    for i in range(4):
        result = run(service,value,FakeClient(plan('patch',value['match_id'],changes=patch(ship.id,fire_markers=i))),
                     request=f'patch-{i}',instruction=f'PRIVATE-INSTRUCTION-{i}')
        assert result['mutated']
    other = FakeClient(plan(match=value['match_id']))
    run(service,value,other,actor=PEER,admins=frozenset({PEER}),request='peer-report')
    assert other.calls[0]['context']['recent_operations'] == []
    client = FakeClient(plan(match=value['match_id']))
    run(service,value,client,request='last-report')
    summaries = client.calls[0]['context']['recent_operations']
    assert len(summaries) == 3 and all(v['action']=='patch' for v in summaries)
    assert all(v['targets']==[{'ship':ship.id,'fields':['fire_markers']}] for v in summaries)
    dumped = '\n'.join(str(tuple(row)) for row in service.db.execute('SELECT meta,response,result FROM bot_referee_calls'))
    dumped += '\n'.join(str(tuple(row)) for row in service.db.execute('SELECT summary FROM bot_referee_audit'))
    assert 'PRIVATE-INSTRUCTION' not in dumped


@pytest.mark.parametrize('change', [
    {'extra':True}, {'steps':True}, {'steps':7}, {'action':'exec'}, {'changes':{}},
    {'usage':{'secret':'secret'}}, {'model':[]}, {'create':{'mode':'classic'}},
])
def test_invalid_structured_model_reply_never_changes_game(service, change):
    value = create(service)
    response = plan('advance',value['match_id']) | change
    before = state(service,value)[0]['state']
    result = run(service,value,FakeClient(response))
    assert not result['mutated'] and state(service,value)[0]['state'] == before
