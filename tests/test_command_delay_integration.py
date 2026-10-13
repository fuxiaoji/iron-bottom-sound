"""Integration of the restored extension with cooperative AI and live reload."""
from __future__ import annotations

from fastapi.testclient import TestClient

from iron_bottom_sound import api, command_delay, target_priority
from iron_bottom_sound.models import (
    CommandDelayState, GameOptions, GameState, Phase, Side, TargetPriorityDirective,
)
from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.realistic_command import RealisticCommander
from iron_bottom_sound.tactical import PROFILES


def test_health_detects_an_old_loaded_revision(monkeypatch):
    client = TestClient(api.app)
    monkeypatch.setattr(api, '_loaded_revision', api.source_revision())
    assert client.get('/health').json()['status'] == 'ready'
    monkeypatch.setattr(api, 'source_revision', lambda: 'changed-source')
    response = client.get('/health')
    assert response.status_code == 503
    assert response.json()['status'] == 'restart_required'


def test_policies_are_scoped_to_game_and_side():
    first, second = object(), object()
    command_delay.clear_side_policies()
    try:
        command_delay.set_side_policy(Side.AXIS, first, 'first', game_id='a')
        command_delay.set_side_policy(Side.AXIS, second, 'second', game_id='b')
        assert command_delay.side_policy(Side.AXIS, 'a') == (first, 'first')
        assert command_delay.side_policy(Side.AXIS, 'b') == (second, 'second')
        assert command_delay.side_policy(Side.ALLIES, 'a')[0] is None
        assert command_delay.side_policy(Side.AXIS, 'imported-or-restarted')[0] is None
    finally:
        command_delay.clear_side_policies()


def test_classic_legacy_save_has_no_command_delay_state():
    engine = IronBottomEngine()
    old = engine.reset('IBS-S-03', 1, GameOptions()).model_dump(mode='json')
    old['options'].pop('command_delay_mode')
    old.pop('command_delay')
    state = GameState.model_validate(old)
    assert state.command_delay is None
    assert not state.options.command_delay_mode


def test_selector_cannot_read_the_opponents_priority(monkeypatch):
    engine = IronBottomEngine()
    state = engine.reset('IBS-S-03', 1, GameOptions(realistic_command=True))
    for side in Side:
        batch = RealisticCommander().choose_orders(engine, state.game_id, side)
        assert engine.submit_orders(state.game_id, batch).valid
    engine.advance(state.game_id)
    own = next(f.id for f in state.formations.values() if f.side == Side.AXIS)
    enemy = next(f.id for f in state.formations.values() if f.side == Side.ALLIES)
    state.command_delay = CommandDelayState(local_directives=[
        TargetPriorityDirective(formation_id=own, source='LOCAL_AGENT', target_class='DD', weight=.2),
        TargetPriorityDirective(formation_id=enemy, source='LOCAL_AGENT', target_class='CA', weight=.2),
    ])
    captured = []
    def selector(_engine, _state, _side, directives):
        captured.extend(directives)
        return []
    monkeypatch.setattr(target_priority, 'select_gunnery_orders', selector)
    target_priority.auto_gunnery(engine, state, Side.AXIS)
    assert captured and all(d.formation_id == own for d in captured)


def test_mode_gates_and_saved_game_metadata():
    client = TestClient(api.app)
    response = client.post('/games', json={'scenario_id': 'IBS-S-02', 'options': {
        'realistic_command': True, 'command_delay_mode': True}})
    assert response.status_code == 422
    response = client.post('/games', json={'scenario_id': 'IBS-S-03', 'options': {
        'realistic_command': True, 'command_delay_mode': True}})
    assert response.status_code == 201
    game = response.json()['game_id']
    entry = next(item for item in client.get('/games').json() if item['game_id'] == game)
    assert entry['command_delay_mode'] is True
    view = client.get(f'/games/{game}/view', headers={'X-Player-Side': 'axis'}).json()
    assert view['command_delay_mode'] and view['realistic_command']


def test_command_delay_opponent_uses_local_agents_not_global_llm(monkeypatch):
    client = TestClient(api.app)
    def forbidden(*args, **kwargs):
        raise AssertionError('fleet-wide model must never be called in Command Delay')
    monkeypatch.setattr(api, 'llm_commander_factory', forbidden)
    response = client.post('/games', json={'scenario_id': 'IBS-S-03', 'options': {
        'mode': 'llm', 'realistic_command': True, 'command_delay_mode': True}})
    game = response.json()['game_id']
    headers = {'X-Player-Side': 'axis'}
    batch = client.get(f'/games/{game}/suggested-orders?profile=rc_coordinated', headers=headers).json()
    assert client.post(f'/games/{game}/orders', json=batch, headers=headers).status_code == 200
    view = client.get(f'/games/{game}/view', headers=headers).json()
    assert view['own_orders_submitted'] and not view['both_orders_submitted']
    assert client.post(f'/games/{game}/llm-opponent', headers=headers).status_code == 200
    assert client.post(f'/games/{game}/llm-opponent', headers=headers).status_code == 200
    assert client.get(f'/games/{game}/view', headers=headers).json()['both_orders_submitted']
    assert client.post(f'/games/{game}/advance', headers=headers).status_code == 200
    state = api.get_game(game)
    state.phase = Phase.GUNNERY
    plan, batch, _ = RealisticCommander(profile=PROFILES['rc_coordinated']).choose_plan(api.engine, game, Side.AXIS)
    assert not batch.gunnery
    assert api.engine.submit_orders(game, batch).valid
    assert client.post(f'/games/{game}/llm-opponent', headers=headers).status_code == 200


def test_new_cooperative_profiles_still_work_in_realistic_mode():
    engine = IronBottomEngine()
    state = engine.reset('IBS-S-03', 17, GameOptions(realistic_command=True))
    for side in Side:
        assert engine.submit_orders(state.game_id, RealisticCommander().choose_orders(
            engine, state.game_id, side)).valid
    engine.advance(state.game_id)
    while state.phase != Phase.MOVEMENT_PLANNING:
        for side in Side:
            batch = RealisticCommander().choose_orders(engine, state.game_id, side)
            assert engine.submit_orders(state.game_id, batch).valid
        engine.advance(state.game_id)
    for profile in ('rc_coordinated', 'rc_t_hunter', 'rc_torpedo_wings', 'rc_screen', 'rc_pincer'):
        for side in Side:
            batch = RealisticCommander(profile=PROFILES[profile]).choose_orders(engine, state.game_id, side)
            assert engine.validate_orders(state.game_id, batch).valid
    assert state.command_delay is None


def test_command_delay_save_import_preserves_traffic_and_uses_fresh_identity():
    client = TestClient(api.app)
    headers = {'X-Player-Side': 'axis'}
    response = client.post('/games', json={'scenario_id': 'IBS-S-01', 'options': {
        'mode': 'llm', 'realistic_command': True, 'command_delay_mode': True}})
    game = response.json()['game_id']
    for side in Side:
        batch = RealisticCommander().choose_orders(api.engine, game, side)
        assert api.engine.submit_orders(game, batch).valid
    api.engine.advance(game)
    state = api.get_game(game)
    remote = next(f.id for f in state.formations.values()
                  if f.side == Side.AXIS and f.id != state.command_delay.authorities['axis'].fleet_formation_id)
    assert client.post(f'/games/{game}/command-delay/order', headers=headers,
                       json={'formation_id': remote, 'text': '保持接触，掩护主力'}).status_code == 200
    saved = client.get(f'/games/{game}/save').json()
    imported = client.post('/games/import', json=saved)
    assert imported.status_code == 201
    new_game = imported.json()['game_id']
    assert new_game != game and imported.json()['command_delay_mode']
    clone = api.get_game(new_game)
    assert clone.command_delay == state.command_delay
    assert command_delay.side_policy(Side.AXIS, new_game)[0] is None
    assert client.get(f'/games/{new_game}/replay/checkpoints').status_code == 200


def test_legacy_portable_save_checksum_is_checked_before_new_defaults():
    from iron_bottom_sound import savegame
    engine = IronBottomEngine()
    state = engine.reset('IBS-S-03', 1, GameOptions())
    api.repository.save(state)
    bundle = savegame.build_save_bundle(api.repository, state)
    for raw in [bundle['state']] + [item['state'] for item in bundle['snapshots']]:
        raw['options'].pop('command_delay_mode')
        raw.pop('command_delay')
    bundle['checksum'] = savegame._checksum(bundle)
    loaded, snapshots = savegame.validate_save_bundle(bundle)
    assert not loaded.options.command_delay_mode and loaded.command_delay is None
    assert snapshots
