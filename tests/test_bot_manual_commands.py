"""Real-engine manual menus, persistence, permissions and transaction boundaries."""
import json

import pytest

from iron_bottom_sound.bot.service import BattleService, ServiceError


ACTOR, ROOM = 'agent:manual', 'manual:room'


@pytest.fixture
def service(tmp_path):
    instance = BattleService(tmp_path / 'manual.sqlite')
    yield instance
    instance.close()


def create(service, mode='classic', actor=ACTOR, room=ROOM, opponent='pve', request='create'):
    return service.create(actor, room, mode=mode, opponent=opponent, request_id=request)


def current_state(service, match):
    return service.db.execute('SELECT state FROM bot_matches WHERE id=?', (match,)).fetchone()['state']


def advance_to(service, value, phase):
    while value['phase'] != phase:
        value = service.auto(value['match_id'], ACTOR, ROOM, value['revision'], 'advance-' + str(value['revision']))
    return value


def catalog(service, value):
    with service._transaction():
        actor, row, state, side = service._manual_current(value['match_id'], ACTOR, ROOM)
        return service._manual_catalog(row, state, side)


@pytest.mark.parametrize('mode', ['classic', 'formation'])
def test_first_manual_phase_select_submit_and_persistent_retry(service, tmp_path, mode):
    value = create(service, mode)
    match = value['match_id']
    before = current_state(service, match)
    menu = service.manual_actions(match, ACTOR, ROOM)
    assert len(menu['text']) <= 1400 and menu['choices']
    assert '代表选项' in menu['text'] and '/选择 0 ' in menu['text']
    assert current_state(service, match) == before
    choice = menu['choices'][0]['choice_id']
    selected = service.manual_choose(match, ACTOR, ROOM, 0, choice, 'choose')
    assert selected['selection_count'] == 1 and current_state(service, match) == before
    assert service.manual_choose(match, ACTOR, ROOM, 0, choice, 'choose') == selected
    result = service.manual_submit(match, ACTOR, ROOM, 0, 'manual-submit')
    assert result['revision'] == 1 and result['advanced'] is True
    assert service.manual_draft(match, ACTOR, ROOM)['selection_count'] == 0
    with pytest.raises(ServiceError):
        service.manual_choose(match, ACTOR, ROOM, 0, choice, 'stale-choice')
    second = BattleService(tmp_path / 'manual.sqlite')
    try:
        assert second.manual_submit(match, ACTOR, ROOM, 0, 'manual-submit') == result
        assert second.manual_choose(match, ACTOR, ROOM, 0, choice, 'choose') == selected
        assert second.status(match, ACTOR, ROOM)['revision'] == 1
    finally:
        second.close()


def test_read_only_pagination_names_filter_and_stable_choice_ids(service):
    value = advance_to(service, create(service), 'movement_planning')
    match = value['match_id']
    before = current_state(service, match)
    page = service.manual_actions(match, ACTOR, ROOM)
    same = service.manual_actions(match, ACTOR, ROOM)
    assert page == same and page['pages'] > 1 and len(page['choices']) == 6
    assert '单位索引' in page['text'] and '下一页：/行动' in page['text']
    assert '/草稿 ' + match in page['text'] and '/提交 1 ' + match in page['text']
    first = page['choices'][0]
    filtered = service.manual_actions(match, ACTOR, ROOM, unit=first['unit_name'])
    assert filtered['unit'] == first['unit_id']
    assert all(c['unit_id'] == first['unit_id'] for c in filtered['choices'])
    second = service.manual_actions(match, ACTOR, ROOM, page=2, unit=first['unit_id'])
    assert not ({c['choice_id'] for c in filtered['choices']} & {c['choice_id'] for c in second['choices']})
    assert len(second['text']) <= 1400 and current_state(service, match) == before


@pytest.mark.parametrize('mode', ['classic', 'formation'])
def test_manual_movement_requires_own_explicit_selection_and_never_calls_human_ai(service, mode, monkeypatch):
    value = advance_to(service, create(service, mode), 'movement_planning')
    choices = catalog(service, value)
    units = {}
    for choice in choices:
        if choice['unit_id']:
            units.setdefault(choice['unit_id'], choice)
    assert units
    suggest = service._suggest
    sides = []
    def opponent_only(row, state, side):
        sides.append(side.value)
        assert side.value == 'axis'
        return suggest(row, state, side)
    monkeypatch.setattr(service, '_suggest', opponent_only)
    for index, choice in enumerate(units.values()):
        service.manual_choose(value['match_id'], ACTOR, ROOM, value['revision'], choice['choice_id'], 'pick-' + str(index))
    result = service.manual_submit(value['match_id'], ACTOR, ROOM, value['revision'], 'manual-move')
    assert result['phase'] == 'torpedo_planning' and result['revision'] == value['revision'] + 1
    assert sides == ['axis']


def test_replacing_same_unit_preserves_other_units_and_restart_draft(service, tmp_path):
    value = advance_to(service, create(service), 'movement_planning')
    choices = catalog(service, value)
    first, replacement = choices[0], next(c for c in choices[1:] if c['unit_id'] == choices[0]['unit_id'])
    other = next(c for c in choices if c['unit_id'] != first['unit_id'])
    for index, choice in enumerate((first, other, replacement)):
        service.manual_choose(value['match_id'], ACTOR, ROOM, value['revision'], choice['choice_id'], 'select-' + str(index))
    draft = service.manual_draft(value['match_id'], ACTOR, ROOM)
    assert draft['selection_count'] == 2
    ids = {c['choice_id'] for c in draft['selections']}
    assert ids == {replacement['choice_id'], other['choice_id']}
    second = BattleService(tmp_path / 'manual.sqlite')
    try:
        assert second.manual_draft(value['match_id'], ACTOR, ROOM) == draft
    finally:
        second.close()


def test_partial_movement_failure_keeps_match_rng_receipts_and_draft(service):
    value = advance_to(service, create(service), 'movement_planning')
    choice = service.manual_actions(value['match_id'], ACTOR, ROOM)['choices'][0]
    service.manual_choose(value['match_id'], ACTOR, ROOM, 1, choice['choice_id'], 'one-ship')
    before = current_state(service, value['match_id'])
    with pytest.raises(ServiceError) as error:
        service.manual_submit(value['match_id'], ACTOR, ROOM, 1, 'failed-submit')
    assert error.value.code == 'invalid_orders'
    assert current_state(service, value['match_id']) == before
    assert service.manual_draft(value['match_id'], ACTOR, ROOM)['selection_count'] == 1
    assert service.db.execute('SELECT count(*) FROM bot_receipts WHERE request=?', ('failed-submit',)).fetchone()[0] == 0


def test_empty_draft_cannot_silently_confirm_even_valid_empty_phase(service):
    value = create(service)
    with pytest.raises(ServiceError) as error:
        service.manual_submit(value['match_id'], ACTOR, ROOM, 0, 'no-explicit-choice')
    assert error.value.code == 'manual_empty' and service.status(value['match_id'], ACTOR, ROOM)['revision'] == 0


def test_clear_is_idempotent_and_duplicate_old_clear_does_not_erase_new_choice(service):
    value = create(service)
    choice = service.manual_actions(value['match_id'], ACTOR, ROOM)['choices'][0]
    service.manual_choose(value['match_id'], ACTOR, ROOM, 0, choice['choice_id'], 'choose1')
    cleared = service.manual_clear(value['match_id'], ACTOR, ROOM, 0, 'clear')
    assert cleared['selection_count'] == 0
    service.manual_choose(value['match_id'], ACTOR, ROOM, 0, choice['choice_id'], 'choose2')
    assert service.manual_clear(value['match_id'], ACTOR, ROOM, 0, 'clear') == cleared
    assert service.manual_draft(value['match_id'], ACTOR, ROOM)['selection_count'] == 1


@pytest.mark.parametrize('method', ['manual_choose', 'manual_clear'])
def test_stale_version_rejected_without_draft_write(service, method):
    value = create(service)
    args = [value['match_id'], ACTOR, ROOM, 3]
    if method == 'manual_choose':
        args.append('not-a-choice')
    args.append('stale')
    with pytest.raises(ServiceError) as error:
        getattr(service, method)(*args)
    assert error.value.code == 'stale_revision'
    assert service.db.execute('SELECT count(*) FROM bot_manual_drafts').fetchone()[0] == 0


def test_unknown_choice_and_foreign_seat_choice_are_rejected(service):
    value = create(service)
    for actor, room in [('agent:other', ROOM), (ACTOR, 'other:room')]:
        with pytest.raises(ServiceError):
            service.manual_actions(value['match_id'], actor, room)
    with pytest.raises(ServiceError) as error:
        service.manual_choose(value['match_id'], ACTOR, ROOM, 0, 'missing', 'bad-choice')
    assert error.value.code == 'manual_choice'
    other = create(service, actor='agent:other', request='other')
    foreign = service.manual_actions(other['match_id'], 'agent:other', ROOM)['choices'][0]['choice_id']
    with pytest.raises(ServiceError):
        service.manual_choose(value['match_id'], ACTOR, ROOM, 0, foreign, 'foreign-choice')


def test_official_alias_uses_canonical_seat_but_never_crosses_app_or_room(service):
    room, member, c2c = 'qqbot:123:GROUP', 'qqbot:123:member:GROUP:MEMBER', 'qqbot:123:c2c:USER'
    value = create(service, actor=member, room=room)
    with pytest.raises(ServiceError):
        service.manual_actions(value['match_id'], c2c, room)
    challenge = service.issue_identity_link(c2c, room, value['match_id'], 'allies', 'link')
    service.claim_identity_link(challenge['code'], member, room)
    choice = service.manual_actions(value['match_id'], c2c, room)['choices'][0]
    service.manual_choose(value['match_id'], c2c, room, 0, choice['choice_id'], 'c2c-choice')
    assert service.db.execute('SELECT actor FROM bot_manual_drafts').fetchone()[0] == member
    for actor, target in [('qqbot:other:c2c:USER', room), (c2c, 'qqbot:123:OTHER')]:
        with pytest.raises(ServiceError):
            service.manual_actions(value['match_id'], actor, target)


def test_gunnery_weapon_choices_merge_and_same_mount_replaces_only_itself(service):
    value = advance_to(service, create(service), 'gunnery')
    choices = [c for c in catalog(service, value) if c['slot'].startswith('gunnery:')]
    first = choices[0]
    same_mount = next(c for c in choices if c['slot'] == first['slot'] and c['choice_id'] != first['choice_id'])
    same_ship_other_mount = next(c for c in choices if c['unit_id'] == first['unit_id'] and c['slot'] != first['slot'])
    for index, choice in enumerate((first, same_ship_other_mount, same_mount)):
        service.manual_choose(value['match_id'], ACTOR, ROOM, value['revision'], choice['choice_id'], 'gun-' + str(index))
    draft = service.manual_draft(value['match_id'], ACTOR, ROOM)
    assert draft['selection_count'] == 2
    result = service.manual_submit(value['match_id'], ACTOR, ROOM, value['revision'], 'manual-gun')
    assert result['revision'] == value['revision'] + 1


def test_torpedo_representatives_use_visible_hints_and_choose_does_not_launch(service):
    value = advance_to(service, create(service), 'torpedo_planning')
    before = current_state(service, value['match_id'])
    choices = catalog(service, value)
    selected = next(c for c in choices if c['slot'].startswith('torpedoes:'))
    assert 'MF' in selected['label'] and '枚' in selected['label']
    service.manual_choose(value['match_id'], ACTOR, ROOM, value['revision'], selected['choice_id'], 'torpedo')
    assert current_state(service, value['match_id']) == before
    result = service.manual_submit(value['match_id'], ACTOR, ROOM, value['revision'], 'manual-torpedo')
    assert result['revision'] == value['revision'] + 1


def test_choosing_no_action_is_explicit_and_removes_previously_selected_weapons(service):
    value = advance_to(service, create(service), 'torpedo_planning')
    choices = catalog(service, value)
    launch = next(c for c in choices if c['slot'].startswith('torpedoes:'))
    empty = next(c for c in choices if c['slot'] == '_empty')
    service.manual_choose(value['match_id'], ACTOR, ROOM, value['revision'], launch['choice_id'], 'launch')
    service.manual_choose(value['match_id'], ACTOR, ROOM, value['revision'], empty['choice_id'], 'empty')
    draft = service.manual_draft(value['match_id'], ACTOR, ROOM)
    assert draft['selection_count'] == 1 and draft['selections'][0]['choice_id'] == empty['choice_id']


def test_menu_and_draft_return_human_choices_without_schema_or_order_payload(service):
    value = advance_to(service, create(service), 'movement_planning')
    menu = service.manual_actions(value['match_id'], ACTOR, ROOM)
    assert 'schema_hint' not in json.dumps(menu) and 'payload' not in json.dumps(menu)
    assert 'observation' not in json.dumps(menu)
    service.manual_choose(value['match_id'], ACTOR, ROOM, value['revision'], menu['choices'][0]['choice_id'], 'choose')
    draft = service.manual_draft(value['match_id'], ACTOR, ROOM)
    assert len(draft['text']) <= 1400 and 'payload' not in json.dumps(draft)


@pytest.mark.parametrize('page', [0, -1, True, '2', 100])
def test_invalid_pagination_does_not_change_match(service, page):
    value = create(service)
    before = current_state(service, value['match_id'])
    with pytest.raises(ServiceError):
        service.manual_actions(value['match_id'], ACTOR, ROOM, page=page)
    assert current_state(service, value['match_id']) == before


def test_submitted_pvp_seat_cannot_choose_or_clear(service):
    value = create(service, opponent='pvp')
    service.join(value['match_id'], 'agent:enemy', ROOM, request_id='join')
    service.submit(value['match_id'], ACTOR, ROOM, {}, 0, 'sealed')
    for function, args in [(service.manual_actions, ()), (service.manual_clear, (0, 'clear')),
                           (service.manual_choose, (0, 'choice', 'choose'))]:
        with pytest.raises(ServiceError) as error:
            function(value['match_id'], ACTOR, ROOM, *args)
        assert error.value.code == 'already_ready'


def test_draft_pagination_exposes_all_weapon_choices_and_keeps_footer(service):
    value = advance_to(service, create(service), 'gunnery')
    unique = {}
    for choice in catalog(service, value):
        if choice['slot'].startswith('gunnery:'):
            unique.setdefault(choice['slot'], choice)
    choices = list(unique.values())[:7]
    assert len(choices) == 7
    for index, choice in enumerate(choices):
        reply = service.manual_choose(value['match_id'], ACTOR, ROOM, value['revision'], choice['choice_id'], 'draft-' + str(index))
        assert choice['label'] in reply['text'] and '尚未提交' in reply['text']
    page1 = service.manual_draft(value['match_id'], ACTOR, ROOM)
    page2 = service.manual_draft(value['match_id'], ACTOR, ROOM, page=2)
    assert page1['selection_count'] == page2['selection_count'] == 7
    assert len(page1['selections']) == 6 and len(page2['selections']) == 1
    assert page1['pages'] == page2['pages'] == 2
    assert '/草稿 ' + value['match_id'] + ' 页2' in page1['text']
    for page in (page1, page2):
        assert len(page['text']) <= 1400
        assert page['text'].endswith(f"/清空 {value['revision']} {value['match_id']}")
    assert {c['choice_id'] for c in page1['selections'] + page2['selections']} == {c['choice_id'] for c in choices}


def test_candidate_clones_never_read_other_seats_pending_orders(service, monkeypatch):
    value = create(service, opponent='pvp')
    match = value['match_id']
    service.join(match, 'agent:enemy', ROOM, request_id='join')
    service.submit(match, ACTOR, ROOM, {}, 0, 'allies-ready')
    service.submit(match, 'agent:enemy', ROOM, {}, 0, 'enemy-ready')
    before = service.manual_actions(match, ACTOR, ROOM)
    enemy = service.suggest(match, 'agent:enemy', ROOM)['orders']
    service.submit(match, 'agent:enemy', ROOM, enemy, 1, 'enemy-sealed')
    assert json.loads(current_state(service, match))['submitted_orders']
    legal = service.engine.legal_actions
    validation = service.engine.validate_orders
    def safe_legal(game_id, side):
        assert service.engine.get(game_id).submitted_orders == {}
        return legal(game_id, side)
    def safe_validation(game_id, batch, *args, **kwargs):
        assert service.engine.get(game_id).submitted_orders == {}
        return validation(game_id, batch, *args, **kwargs)
    monkeypatch.setattr(service.engine, 'legal_actions', safe_legal)
    monkeypatch.setattr(service.engine, 'validate_orders', safe_validation)
    assert service.manual_actions(match, ACTOR, ROOM) == before


def test_unmapped_gunnery_target_is_not_echoed_or_selectable(service, monkeypatch):
    value = advance_to(service, create(service), 'gunnery')
    legal = service.engine.legal_actions
    def unmapped_target(game_id, side):
        actions = legal(game_id, side)
        hint = actions[0].schema_hint
        hint['gunnery_candidates'][0]['targets'].append({'target_id': 'PRIVATE_WORLD_ID', 'mount_ids': ['P1'], 'range': 1})
        return actions
    monkeypatch.setattr(service.engine, 'legal_actions', unmapped_target)
    assert 'PRIVATE_WORLD_ID' not in json.dumps(catalog(service, value))


def test_cross_instance_draft_change_between_read_and_submit_is_rejected(service, tmp_path, monkeypatch):
    value = create(service)
    match = value['match_id']
    choice = service.manual_actions(match, ACTOR, ROOM)['choices'][0]
    service.manual_choose(match, ACTOR, ROOM, 0, choice['choice_id'], 'choose-before-race')
    before = current_state(service, match)
    original_submit = service.submit
    def raced_submit(*args, **kwargs):
        assert kwargs.get('manual_guard')
        second = BattleService(tmp_path / 'manual.sqlite')
        try:
            second.manual_clear(match, ACTOR, ROOM, 0, 'other-writer-clear')
        finally:
            second.close()
        return original_submit(*args, **kwargs)
    monkeypatch.setattr(service, 'submit', raced_submit)
    with pytest.raises(ServiceError) as error:
        service.manual_submit(match, ACTOR, ROOM, 0, 'raced-manual-submit')
    assert error.value.code == 'manual_stale'
    assert current_state(service, match) == before
    assert service.manual_draft(match, ACTOR, ROOM)['selection_count'] == 0
    assert service.db.execute('SELECT count(*) FROM bot_receipts WHERE request=?', ('raced-manual-submit',)).fetchone()[0] == 0
