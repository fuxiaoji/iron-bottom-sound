"""User-authorized recognition extension: real boundary/privacy/replay checks.

Synthetic positions isolate sensing, rather than filling missing Savo deployment.
"""
from copy import deepcopy
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from iron_bottom_sound import api, night, recognition, ai_memory
from iron_bottom_sound.data import ROOT
from iron_bottom_sound.engine import IronBottomEngine, ORDER_PHASES
from iron_bottom_sound.models import (GameOptions, OptionalRules, Side, Phase, HexCoord,
    OrderBatch, GunneryOrder, SearchlightOrder, MarkerState)
from iron_bottom_sound.realistic_command import RealisticCommander
from iron_bottom_sound.tactical import TacticalCommander, PROFILES
from iron_bottom_sound.llm import OpenAICompatibleCommander
from iron_bottom_sound.savegame import build_save_bundle, validate_save_bundle, clone_imported_game
from iron_bottom_sound.storage import GameRepository


@pytest.fixture
def contact():
    engine = IronBottomEngine()
    state = engine.reset('IBS-S-03', seed=37, options=GameOptions(ruleset_version='night-v2',
        night_recognition=True, optional_rules=OptionalRules(radar=True, searchlights=True, star_shells=True, squalls=True)))
    own = next(s for s in state.ships.values() if s.side == Side.AXIS)
    enemy = next(s for s in state.ships.values() if s.side == Side.ALLIES)
    for ship in state.ships.values():
        ship.position = None
    own.position = HexCoord.from_label('M12')
    own.radar = True
    enemy.position = HexCoord(q=own.position.q+6, r=own.position.r)
    state.land_hexes.clear(); state.coast_hexes.clear(); state.radar_blocking_hexes.clear()
    state.visibility = {'axis':8, 'allies':8}
    state.phase = Phase.GUNNERY
    state.events[0].payload['initial_state'] = state.model_dump(mode='json', exclude={'events'})
    recognition.refresh(engine, state)
    return engine, state, own, enemy


def public_enemy(engine, state):
    return next(s for s in engine.observe(state.game_id, Side.AXIS).ships if s.side != Side.AXIS)


@pytest.mark.parametrize('distance,identified', [(2, True), (3, True), (4, False), (8, False)])
def test_near_recognition_boundary_and_generic_counter(contact, distance, identified):
    engine,state,own,enemy = contact
    enemy.position = HexCoord(q=own.position.q+distance,r=own.position.r)
    public = public_enemy(engine,state)
    assert public.identified == identified
    assert public.id.startswith('contact-') and enemy.id not in public.id
    if identified:
        assert (public.name,public.ship_type) == (enemy.name,enemy.ship_type)
    else:
        assert public.asset == '敌舰.png' and public.ship_type == 'UNKNOWN'
        assert enemy.name not in public.name and public.hull is None and public.belt_armor is None
        assert not public.gun_mounts and not public.torpedo_launchers


def test_whole_map_radar_never_identifies_and_same_counter(contact):
    engine,state,own,enemy = contact
    enemy.position = HexCoord.from_label('DD32')
    public = public_enemy(engine,state)
    assert public.asset == '敌舰.png' and not public.identified
    assert engine.observe(state.game_id,Side.AXIS).environment['contacts'][public.id] == 'radar'
    own.radar = False
    assert all(s.side == Side.AXIS for s in engine.observe(state.game_id,Side.AXIS).ships)


@pytest.mark.parametrize('distance,blocked', [(4,True),(5,False)])
def test_radar_land_exclusion_is_target_four_hexes(contact,distance,blocked):
    engine,state,own,enemy = contact
    enemy.position = HexCoord.from_label('DD32')
    state.land_hexes.add(HexCoord(q=enemy.position.q+distance,r=enemy.position.r).label)
    assert night.radar_contact(engine,state,own,enemy) != blocked


def test_island_between_and_rain_block_even_light_and_near_identification(contact):
    engine,state,own,enemy = contact
    enemy.position = HexCoord(q=own.position.q+3,r=own.position.r)
    state.land_hexes.add(HexCoord(q=own.position.q+1,r=own.position.r).label)
    assert not recognition.identified(engine,state,Side.AXIS,enemy)
    assert not night.radar_contact(engine,state,own,enemy)
    state.land_hexes.clear()
    state.markers = [MarkerState(id='rain',kind='squall',position=enemy.position),
                     MarkerState(id='lit',kind='searchlight',ship_id=own.id,target_ship_id=enemy.id,expires_turn=state.turn)]
    assert not recognition.identified(engine,state,Side.AXIS,enemy)
    assert all(s.side == Side.AXIS for s in engine.observe(state.game_id,Side.AXIS).ships)


@pytest.mark.parametrize('light', ['searchlight','star_shell'])
def test_light_identifies_only_after_effect_then_tracks_without_forgetting(contact,light):
    engine,state,own,enemy = contact
    token = public_enemy(engine,state).id
    if light == 'searchlight':
        batch = OrderBatch(side=Side.AXIS,searchlights=[SearchlightOrder(ship_id=own.id,target_id=token)])
        assert engine.validate_orders(state.game_id,batch).valid
        assert not public_enemy(engine,state).identified
        night.prepare_gunnery(engine,state,[recognition.decode_orders(engine,state,batch)])
    else:
        state.markers.append(MarkerState(id='star',kind='star_shell',position=enemy.position,expires_turn=state.turn))
        recognition.refresh(engine,state)
    public = public_enemy(engine,state)
    assert public.id == token and public.identified and public.name == enemy.name
    state.markers.clear()
    assert public_enemy(engine,state).identified  # continuous radar/optical track
    own.radar = False
    enemy.position = HexCoord.from_label('DD32')
    recognition.refresh(engine,state)
    own.radar = True
    assert not public_enemy(engine,state).identified  # new distant contact


def test_public_target_token_valid_raw_identity_refused_and_no_alias_leaks(contact):
    engine,state,own,enemy = contact
    token = public_enemy(engine,state).id
    batch = OrderBatch(side=Side.AXIS,searchlights=[SearchlightOrder(ship_id=own.id,target_id=token)])
    assert engine.submit_orders(state.game_id,batch).valid
    assert state.submitted_orders['axis'].searchlights[0].target_id == enemy.id
    del state.submitted_orders['axis']
    batch.searchlights[0].target_id = enemy.id
    assert not engine.validate_orders(state.game_id,batch).valid
    assert not engine.submit_orders(state.game_id,batch).valid
    text = engine.observe(state.game_id,Side.AXIS).model_dump_json()
    assert enemy.name not in text and enemy.id not in text and 'recognition_secret' not in text
    legal = json.dumps([a.model_dump(mode='json') for a in engine.legal_actions(state.game_id,Side.AXIS)],ensure_ascii=False)
    assert enemy.name not in legal and enemy.id not in legal and token in legal


def test_readonly_preview_and_heatmap_cannot_reveal_identity(contact,monkeypatch):
    engine,state,own,enemy = contact
    monkeypatch.setattr(api,'engine',engine)
    token = public_enemy(engine,state).id
    before = state.model_dump()
    client = TestClient(api.app)
    response = client.post(f'/games/{state.game_id}/night-preview',headers={'X-Player-Side':'axis'},json={
        'side':'axis','searchlights':[{'ship_id':own.id,'target_id':token}]})
    assert response.is_success,response.text
    assert token in response.text and enemy.id not in response.text and enemy.name not in response.text
    assert response.json()['light_counter'] == '光源.png' and response.json()['recognition_enabled']
    assert state.model_dump() == before
    assert not public_enemy(engine,state).identified
    heat = engine.field_of_fire_heatmap(state,Side.AXIS,ship_id=token)
    assert not heat['sides']['allies']['hexes'] and not heat['sides']['allies']['ships']


def test_event_time_identity_never_revealed_retroactively(contact):
    engine,state,own,enemy = contact
    event = engine._event(state,'gun_mount_attack',f'{enemy.name} 炮击 {own.name}：8英寸',
        payload={'attacker':enemy.id,'target':own.id,'caliber':8,'firepower':11,'mount_id':'P1',
                 'modifiers':{'caliber_target':2},'damage':{'hull':5}})
    enemy.position = HexCoord(q=own.position.q+2,r=own.position.r)
    assert public_enemy(engine,state).identified
    old = engine.public_events(state,Side.AXIS,[event])[0].model_dump_json()
    assert enemy.name not in old and enemy.id not in old and 'caliber' not in old and '8英寸' not in old
    assert 'P1' not in old and 'modifiers' not in old


@pytest.mark.parametrize('phase',[Phase.MOVEMENT_PLANNING,Phase.TORPEDO_PLANNING,Phase.GUNNERY])
def test_state_machine_plan_uses_contacts_without_hidden_capabilities(contact,phase):
    engine,state,own,enemy = contact
    state.phase = phase
    commander = TacticalCommander(PROFILES['balanced'])
    plan,batch,_ = commander.choose_plan(engine,state.game_id,Side.AXIS)
    assert engine.validate_orders(state.game_id,batch).valid
    text = plan.model_dump_json()
    assert enemy.id not in text and enemy.name not in text
    # Unknown class, armor, weapons and VP have no influence on the proposal.
    enemy.ship_type = 'BB'; enemy.vp = 1000; enemy.belt_armor = 30
    for m in enemy.gun_mounts:
        m.firepower = 100
    changed,_,_ = commander.choose_plan(engine,state.game_id,Side.AXIS)
    assert changed.orders == plan.orders


@pytest.mark.parametrize('realistic',[False,True])
def test_new_game_real_round_save_import_and_replay(realistic,tmp_path):
    engine = IronBottomEngine()
    state = engine.reset('IBS-S-03',seed=37,options=GameOptions(ruleset_version='night-v2',
        night_recognition=True,realistic_command=realistic,optional_rules=OptionalRules(searchlights=True,star_shells=True,radar=True)))
    commander = RealisticCommander()
    while state.turn == 1 and state.phase != Phase.COMPLETE:
        if state.phase in ORDER_PHASES:
            for side in Side:
                plan,batch,audits = commander.choose_plan(engine,state.game_id,side)
                assert engine.submit_orders(state.game_id,batch).valid
                ai_memory.accepted(engine,state,side,plan,batch,audits)
        engine.advance(state.game_id)
    assert engine.replay(state.events).model_dump() == state.model_dump()
    repo = GameRepository(tmp_path/'save.sqlite3'); repo.save(state)
    loaded,snapshots = validate_save_bundle(build_save_bundle(repo,state))
    cloned,snapshots = clone_imported_game(loaded,snapshots)
    engine.games[cloned.game_id] = cloned
    assert engine.replay(cloned.events).model_dump() == cloned.model_dump()
    assert recognition.contact_id(state,Side.AXIS,next(s.id for s in state.ships.values() if s.side == Side.ALLIES)) == recognition.contact_id(cloned,Side.AXIS,next(s.id for s in cloned.ships.values() if s.side == Side.ALLIES))
    repo.close()


def test_mock_model_prompt_contains_only_public_contacts_and_legal_actions(contact):
    engine,state,own,enemy = contact
    plan,batch,_ = TacticalCommander(PROFILES['balanced']).choose_plan(engine,state.game_id,Side.AXIS)
    calls = []
    def handler(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200,json={'choices':[{'message':{'content':plan.model_dump_json()}}]})
    commander = OpenAICompatibleCommander(api_key='fixture',client=httpx.Client(transport=httpx.MockTransport(handler)))
    _,chosen,_ = commander.choose_plan(engine,state.game_id,Side.AXIS)
    assert engine.validate_orders(state.game_id,chosen).valid
    prompt = json.dumps(calls,ensure_ascii=False)
    assert enemy.id not in prompt and enemy.name not in prompt and 'contact-' in prompt


def test_native_assets_and_historical_parameter_source_and_legacy_snapshot(contact):
    engine,state,own,enemy = contact
    config = recognition.data(state)
    assert config['status'] == 'user_historical_extension' and config['unlit_hexes'] == 3
    assert config['yards_per_hex'] == 600 and len(config['evidence']) == 2
    assert all('history.navy.mil' in item['url'] for item in config['evidence'])
    assets = {config['optical_counter'],config['radar_counter'],config['light_counter']}
    assets.update(a for nation in config['class_counters'].values() for a in nation.values())
    assert all((ROOT/'resources/originals/assets/images'/a).exists() for a in assets)
    old = engine.reset('IBS-S-03',options=GameOptions(ruleset_version='night-v2'))
    frozen = deepcopy(old.rule_snapshot)
    assert not recognition.enabled(old) and 'recognition_secret' not in old.scenario_state
    assert all(s.identified for s in engine.observe(old.game_id,Side.AXIS).ships)
    assert old.rule_snapshot == frozen


def test_new_api_defaults_on_old_options_missing_flag_stay_off(monkeypatch):
    engine=IronBottomEngine();monkeypatch.setattr(api,'engine',engine)
    response=TestClient(api.app).post('/games',json={'scenario_id':'IBS-S-03','options':{'realistic_command':False}})
    assert response.is_success,response.text
    assert engine.get(response.json()['game_id']).options.night_recognition
    assert not GameOptions.model_validate({'ruleset_version':'night-v2'}).night_recognition


def test_remembered_priority_cannot_enable_a_hidden_shot(contact):
    engine,state,own,enemy = contact
    from iron_bottom_sound.models import TargetPriorityDirective
    token = public_enemy(engine,state).id
    enemy.position=HexCoord.from_label('DD32');own.radar=False
    batch=OrderBatch(side=Side.AXIS,target_priorities=[TargetPriorityDirective(
        formation_id='remembered-formation',source='DOCTRINE',target_id=token,weight=.2)])
    assert recognition.decode_orders(engine,state,batch).target_priorities[0].target_id == enemy.id
    assert not any(c['targets'] for c in engine._gunnery_candidates(state,Side.AXIS))
    batch.searchlights=[SearchlightOrder(ship_id=own.id,target_id=token)]
    assert not engine.validate_orders(state.game_id,batch).valid


@pytest.mark.parametrize('identified',[False,True])
def test_observed_losses_keep_unknown_types_private_and_known_sunk_identity(contact,identified):
    engine,state,own,enemy = contact
    if identified:
        enemy.position=HexCoord(q=own.position.q+2,r=own.position.r)
    enemy.sunk=True
    engine._event(state,'ship_sunk',enemy.name+' 沉没',payload={'ship_id':enemy.id})
    enemy.position=None
    assert recognition.identified(engine,state,Side.AXIS,enemy) == identified
    loss=engine.observe(state.game_id,Side.AXIS).battle_losses['allies']
    assert loss['sunk_count'] == 1
    if identified:
        assert loss['sunk'][0]['name'] == enemy.name
    else:
        assert not loss['sunk'] and not loss['by_type']


def test_import_refuses_missing_contact_salt_instead_of_regenerating_ids(contact,tmp_path):
    engine,state,_,_=contact
    from iron_bottom_sound.savegame import _checksum
    repo=GameRepository(tmp_path/'tampered.sqlite3');repo.save(state)
    bundle=build_save_bundle(repo,state)
    del bundle['state']['scenario_state']['recognition_secret']
    bundle['checksum']=_checksum(bundle)
    with pytest.raises(ValueError,match='接触编号'):
        validate_save_bundle(bundle)
    repo.close()
