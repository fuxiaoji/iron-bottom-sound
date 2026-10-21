"""Capture real provider payloads; no external model or network is called."""
from copy import deepcopy
import json

import httpx
import pytest

from iron_bottom_sound.command_observation import formation_observation
from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.formation_llm import FormationLLMAgent, ProviderPolicy, build_prompt, compact_local_map
from iron_bottom_sound.llm import OpenAICompatibleCommander
from iron_bottom_sound.models import AIPlanSheet, GameOptions, HexCoord, OrderBatch, Phase, Side
from iron_bottom_sound.realistic_command import default_setup_orders


EXPECTED = [[], [4], [3, 6], [2, 5, 8], [2, 4, 6, 8], [1, 2, 4, 6, 8],
            [1, 2, 4, 6, 7, 8], [1, 2, 3, 4, 6, 7, 8], list(range(1, 9))]


def assert_lesson(lesson):
    assert lesson['version'] == 'greg-courter-8-v1'
    assert lesson['interval_count'] == 8 and lesson['source_pdf_page'] == 14
    assert lesson['applies_to'] == ['ships', 'torpedoes', 'contact_markers']
    assert [row['speed_or_total_mf'] for row in lesson['rows']] == list(range(9))
    assert [row['spend_one_mf_at'] for row in lesson['rows']] == EXPECTED
    assert lesson['worked_example']['launch_at_mf'] == 2
    assert lesson['worked_example']['launch_interval'] == 4
    assert lesson['worked_example']['first_turn_move_intervals'] == [5, 6, 7, 8]
    assert lesson['worked_example']['first_turn_hexes'] == 4
    assert 'MF不是节' in lesson['reading'] and '付费转向' in lesson['reading']
    assert 'launch_at_mf' in lesson['launch'] and '不补走' in lesson['launch']
    assert '尾随' in lesson['contact'] and '炮击阶段之后' in lesson['contact']


@pytest.mark.parametrize('night', [False, True])
def test_public_lesson_is_the_current_table_without_private_state(night):
    engine = IronBottomEngine()
    state = engine.reset('IBS-S-03', options=GameOptions(ruleset_version='night-v2' if night else 'legacy-v1'))
    before = state.model_dump(mode='json')
    lesson = engine.movement_timing_guidance(state)
    assert_lesson(lesson)
    assert state.model_dump(mode='json') == before
    enemy = next(s for s in state.ships.values() if s.side == Side.ALLIES)
    enemy.position = HexCoord.from_label('AA20')
    state.score[Side.ALLIES.value] = 999
    state.sealed_orders['secret-unrelated-key'] = {}
    assert engine.movement_timing_guidance(state) == lesson
    assert enemy.id not in json.dumps(lesson)


def test_prompt_table_is_generated_from_engine_not_a_second_copy():
    engine = IronBottomEngine()
    state = engine.reset('IBS-S-03')
    engine.rules.movement_impulses = deepcopy(engine.rules.movement_impulses)
    engine.rules.movement_impulses['rows'][1] = ['S', 'S', 'S', 'S', 'M', '-', '-', '-']
    assert engine.movement_timing_guidance(state)['rows'][1]['spend_one_mf_at'] == [5]


def test_legacy_lesson_cannot_teach_the_new_clock_to_an_old_game():
    engine = IronBottomEngine()
    state = engine.reset('IBS-S-03', movement_timing='legacy-mf-v1')
    lesson = engine.legal_actions(state.game_id, Side.AXIS)[0].schema_hint['movement_timing_guidance']
    assert lesson['version'] == 'legacy-mf-v1'
    assert '不套用' in lesson['instruction']
    assert 'rows' not in lesson and 'worked_example' not in lesson


@pytest.mark.parametrize('reject_first', [False, True])
def test_fleet_provider_receives_full_lesson_on_initial_and_retry_payloads(reject_first):
    engine = IronBottomEngine()
    state = engine.reset('IBS-S-03')
    captured = []
    plan = AIPlanSheet(turn=1, phase=state.phase, situation_summary='无增援', phase_goal='确认',
                      orders=OrderBatch(side=Side.AXIS, phase=state.phase).model_dump(mode='json'))
    def handler(request):
        captured.append(json.loads(request.content))
        content = '{}' if reject_first and len(captured) == 1 else plan.model_dump_json()
        return httpx.Response(200, json={'choices': [{'message': {'content': content}}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        commander = OpenAICompatibleCommander(api_key='test-placeholder', client=client)
        commander.choose_plan(engine, state.game_id, Side.AXIS)
    assert len(captured) == (2 if reject_first else 1)
    for payload in captured:
        assert 'movement_timing_guidance' in payload['messages'][0]['content']
        user = json.loads(payload['messages'][1]['content'])
        assert_lesson(user['legal_actions'][0]['schema_hint']['movement_timing_guidance'])


def local_observation():
    engine = IronBottomEngine()
    state = engine.reset('IBS-S-03', options=GameOptions(realistic_command=True, command_delay_mode=True))
    for side in Side:
        batch = OrderBatch(side=side, phase=Phase.FORMATION_SETUP,
                           formation_setup=default_setup_orders(state, side))
        assert engine.submit_orders(state.game_id, batch).valid
    engine.advance(state.game_id)
    formation = next(f for f in state.formations.values() if f.side == Side.AXIS)
    return engine, state, formation_observation(engine, state, Side.AXIS, formation.id)


def test_local_provider_allowlist_and_compaction_keep_lesson():
    engine, state, observation = local_observation()
    prompt = compact_local_map(build_prompt(observation))
    assert_lesson(prompt['movement_timing_guidance'])
    captured = []
    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={'choices': [{'message': {'content': '{}'}}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        policy = ProviderPolicy(endpoint='https://example.invalid/v1', model='stub', api_key='test-placeholder', client=client)
        policy(prompt)
    user = json.loads(captured[0]['messages'][1]['content'])
    assert_lesson(user['movement_timing_guidance'])
    assert 'movement_timing_guidance' in user['instruction']
    for forbidden in ['sealed_orders', 'torpedo_contact_snapshots', 'all_ships', 'score']:
        assert forbidden not in user


def test_local_correction_retry_preserves_lesson():
    _, _, observation = local_observation()
    seen = []
    def policy(prompt):
        seen.append(prompt)
        if len(seen) == 1:
            return json.dumps({'selected_movement_action_id': 'INVENTED'})
        return json.dumps({'selected_movement_action_id': None})
    agent = FormationLLMAgent(policy=policy)
    agent.act(observation)
    assert len(seen) == 2 and 'previous_response_rejected' in seen[1]
    assert_lesson(seen[1]['movement_timing_guidance'])
