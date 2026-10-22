"""Persistent, room-scoped C2C authorization by the existing group seat owner."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json

import pytest

from iron_bottom_sound.bot.service import BattleService, ServiceError


APP = '1905878837'
ROOM = f'qqbot:{APP}:groupA'
MEMBER = f'qqbot:{APP}:member:groupA:same-value'
OTHER = f'qqbot:{APP}:member:groupA:other-member'
C2C = f'qqbot:{APP}:c2c:same-value'


@pytest.fixture
def service(tmp_path):
    value = BattleService(tmp_path / 'identity.sqlite3')
    yield value
    value.close()


def match(service, *, owner=MEMBER, side='allies', request_id='create'):
    return service.create(owner, ROOM, opponent='pvp', side=side, request_id=request_id)


def issue(service, state, *, actor=C2C, side='allies', request_id='link'):
    return service.issue_identity_link(actor, ROOM, state['match_id'], side, request_id)


def bind(service, state, *, actor=C2C):
    challenge = issue(service, state, actor=actor)
    assert service.claim_identity_link(challenge['code'], MEMBER, ROOM) == {'linked': True}
    return challenge


def test_raw_equal_openids_have_distinct_domains_until_authorized(service):
    state = match(service)
    assert service.resolve_actor(C2C, ROOM) == C2C
    with pytest.raises(ServiceError) as error:
        service.status(state['match_id'], C2C, ROOM)
    assert error.value.code == 'forbidden'
    assert service.matches(C2C, ROOM) == []
    result = bind(service, state)
    assert len(result['code']) >= 32 and result['expires_in'] == 300
    assert service.resolve_actor(C2C, ROOM) == MEMBER
    assert service.status(state['match_id'], C2C, ROOM)['side'] == 'allies'
    assert service.resolve_actor('agent:blue', 'test') == 'agent:blue'
    assert service.resolve_actor('qq:123', 'qq:456') == 'qq:123'


def test_only_expected_authenticated_group_author_can_claim_and_errors_do_not_consume(service):
    state = match(service)
    challenge = issue(service, state)
    digest = hashlib.sha256(challenge['code'].encode()).hexdigest()
    saved = service.db.execute('SELECT * FROM bot_identity_challenges').fetchone()
    assert saved['codehash'] == digest and saved['codehash'] != challenge['code']
    assert saved['expected_member_actor'] == MEMBER
    for actor in (OTHER, C2C, 'agent:intruder'):
        with pytest.raises(ServiceError):
            service.claim_identity_link(challenge['code'], actor, ROOM)
        assert service.db.execute('SELECT consumed FROM bot_identity_challenges').fetchone()[0] == 0
        assert service.resolve_actor(C2C, ROOM) == C2C
    assert service.claim_identity_link(challenge['code'], MEMBER, ROOM) == {'linked': True}
    assert service.claim_identity_link(challenge['code'], MEMBER, ROOM) == {'linked': True}
    with pytest.raises(ServiceError):
        service.claim_identity_link(challenge['code'], OTHER, ROOM)


@pytest.mark.parametrize('actor,room', [
    (C2C, f'qqbot:other-app:groupA'),
    (MEMBER, f'qqbot:{APP}:groupB'),
    (MEMBER, 'qq:456'),
    (f'qqbot:{APP}:same-value', ROOM),
    (f'qqbot:{APP}:member:groupA:same-value:extra', ROOM),
    (f'qqbot:{APP}:c2c:', ROOM),
    (f'qqbot:{APP}:c2c:bad value', ROOM),
])
def test_official_identity_scope_and_shape_fail_closed(service, actor, room):
    with pytest.raises(ServiceError):
        service.resolve_actor(actor, room)


def test_challenge_cannot_cross_group_or_app_even_when_raw_ids_match(service):
    state = match(service)
    challenge = issue(service, state)
    for actor, room in [
        (f'qqbot:{APP}:member:groupB:same-value', f'qqbot:{APP}:groupB'),
        ('qqbot:other-app:member:groupA:same-value', 'qqbot:other-app:groupA'),
    ]:
        with pytest.raises(ServiceError):
            service.claim_identity_link(challenge['code'], actor, room)
    assert service.claim_identity_link(challenge['code'], MEMBER, ROOM) == {'linked': True}
    assert service.resolve_actor(C2C, f'qqbot:{APP}:groupB') == C2C
    assert service.resolve_actor('qqbot:other-app:c2c:same-value', 'qqbot:other-app:groupA') == 'qqbot:other-app:c2c:same-value'
    other_match = service.create(f'qqbot:{APP}:member:groupB:same-value', f'qqbot:{APP}:groupB',
                                 opponent='pvp', request_id='other-room')
    with pytest.raises(ServiceError):
        service.status(other_match['match_id'], C2C, f'qqbot:{APP}:groupB')


def test_issue_requires_c2c_and_an_existing_official_member_seat(service):
    state = match(service)
    for actor in (MEMBER, 'agent:blue', 'qq:123'):
        with pytest.raises(ServiceError):
            issue(service, state, actor=actor)
    for mid, side in [('missing', 'allies'), (state['match_id'], 'axis')]:
        with pytest.raises(ServiceError):
            service.issue_identity_link(C2C, ROOM, mid, side, 'bad-' + mid + side)
    for owner in ('agent:blue', C2C):
        created = match(service, owner=owner, request_id='non-member-' + owner)
        with pytest.raises(ServiceError):
            issue(service, created, request_id='reject-' + owner)
    with pytest.raises(ServiceError):
        issue(service, state, side='invented')


def test_expiry_does_not_consume_and_fresh_request_can_reissue(service, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr('iron_bottom_sound.bot.service.time.time', lambda: clock[0])
    state = match(service)
    challenge = issue(service, state)
    clock[0] += 300
    with pytest.raises(ServiceError) as error:
        service.claim_identity_link(challenge['code'], MEMBER, ROOM)
    assert error.value.code == 'identity_link_expired'
    assert service.db.execute('SELECT consumed FROM bot_identity_challenges').fetchone()[0] == 0
    assert service.resolve_actor(C2C, ROOM) == C2C
    fresh = issue(service, state, request_id='fresh')
    assert fresh['code'] != challenge['code']
    assert service.claim_identity_link(fresh['code'], MEMBER, ROOM) == {'linked': True}
    clock[0] += 1000
    assert service.claim_identity_link(fresh['code'], MEMBER, ROOM) == {'linked': True}


def test_challenge_issue_receipt_uses_original_c2c_actor_and_survives_restart(tmp_path):
    path = tmp_path / 'identity.sqlite3'
    first = BattleService(path)
    state = match(first, request_id='shared-rid')
    challenge = issue(first, state, request_id='shared-rid')
    first.close()
    second = BattleService(path)
    try:
        assert issue(second, state, request_id='shared-rid') == challenge
        second.claim_identity_link(challenge['code'], MEMBER, ROOM)
        assert issue(second, state, request_id='shared-rid') == challenge
        receipts = second.db.execute("SELECT actor FROM bot_receipts WHERE request='shared-rid' ORDER BY actor").fetchall()
        assert {row['actor'] for row in receipts} == {C2C, MEMBER}
    finally:
        second.close()
    third = BattleService(path)
    try:
        assert third.resolve_actor(C2C, ROOM) == MEMBER
        assert third.status(state['match_id'], C2C, ROOM)['side'] == 'allies'
        assert third.claim_identity_link(challenge['code'], MEMBER, ROOM) == {'linked': True}
    finally:
        third.close()


def test_link_conflict_cannot_overwrite_existing_room_alias(service):
    state = match(service)
    service.join(state['match_id'], OTHER, ROOM, 'join')
    allies = issue(service, state)
    axis = issue(service, state, side='axis', request_id='other-side')
    service.claim_identity_link(allies['code'], MEMBER, ROOM)
    with pytest.raises(ServiceError) as error:
        service.claim_identity_link(axis['code'], OTHER, ROOM)
    assert error.value.code == 'identity_link_conflict'
    assert service.resolve_actor(C2C, ROOM) == MEMBER
    assert service.db.execute('SELECT consumed FROM bot_identity_challenges WHERE codehash=?',
                              (hashlib.sha256(axis['code'].encode()).hexdigest(),)).fetchone()[0] == 0
    with pytest.raises(ServiceError) as error:
        issue(service, state, side='axis', request_id='new-other-side')
    assert error.value.code == 'identity_link_conflict'


def test_unexpired_challenge_limit_and_stable_receipt(service):
    state = match(service)
    issued = [issue(service, state, request_id=f'link-{n}') for n in range(8)]
    assert len({item['code'] for item in issued}) == 8
    assert issue(service, state, request_id='link-0') == issued[0]
    with pytest.raises(ServiceError) as error:
        issue(service, state, request_id='ninth')
    assert error.value.code == 'identity_link_limit'
    service.claim_identity_link(issued[0]['code'], MEMBER, ROOM)
    assert issue(service, state, request_id='now-available')['code']
    assert issue(service, state, actor=f'qqbot:{APP}:c2c:other-user', request_id='other')['code']


def test_two_instances_atomically_claim_same_code(tmp_path):
    path = tmp_path / 'shared.sqlite3'
    first, second = BattleService(path), BattleService(path)
    try:
        state = match(first)
        challenge = issue(first, state)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda service: service.claim_identity_link(challenge['code'], MEMBER, ROOM),
                                    (first, second)))
        assert results == [{'linked': True}, {'linked': True}]
        assert first.db.execute('SELECT count(*) FROM bot_identity_aliases').fetchone()[0] == 1
        assert second.db.execute('SELECT consumed FROM bot_identity_challenges').fetchone()[0] == 1
    finally:
        first.close()
        second.close()


def test_two_instances_cannot_race_binding_to_two_members(tmp_path):
    path = tmp_path / 'shared.sqlite3'
    first, second = BattleService(path), BattleService(path)
    try:
        state = match(first)
        first.join(state['match_id'], OTHER, ROOM, 'join')
        challenges = [issue(first, state), issue(first, state, side='axis', request_id='axis')]

        def attempt(args):
            service, code, actor = args
            try:
                service.claim_identity_link(code, actor, ROOM)
                return 'linked'
            except ServiceError as error:
                return error.code

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, [(first, challenges[0]['code'], MEMBER),
                                               (second, challenges[1]['code'], OTHER)]))
        assert sorted(results) == ['identity_link_conflict', 'linked']
        assert first.db.execute('SELECT count(*) FROM bot_identity_aliases').fetchone()[0] == 1
        assert first.db.execute('SELECT sum(consumed) FROM bot_identity_challenges').fetchone()[0] == 1
    finally:
        first.close()
        second.close()


def test_c2c_and_member_share_canonical_seat_and_mutation_receipts(service):
    state = match(service)
    service.join(state['match_id'], OTHER, ROOM, 'join')
    bind(service, state)
    mid = state['match_id']
    assert service.legal(mid, C2C, ROOM) == service.legal(mid, MEMBER, ROOM)
    assert service.screenshot(mid, C2C, ROOM).startswith(b'\x89PNG\r\n\x1a\n')
    orders = service.suggest(mid, C2C, ROOM)['orders']
    accepted = service.submit(mid, C2C, ROOM, orders, 0, 'mcp-submit')
    assert accepted['ready'] == ['allies'] and not accepted['advanced']
    assert service.submit(mid, MEMBER, ROOM, orders, 0, 'mcp-submit') == accepted
    assert service.auto(mid, OTHER, ROOM, 0, 'opponent')['revision'] == 1
    assert service.submit(mid, C2C, ROOM, orders, 0, 'mcp-submit') == accepted
    assert service.status(mid, C2C, ROOM)['revision'] == 1
    with pytest.raises(ServiceError):
        service.submit(mid, C2C, ROOM, {'invented': True}, 1, 'bad-payload')
    assert service.db.execute("SELECT count(*) FROM bot_receipts WHERE request='bad-payload'").fetchone()[0] == 0
    assert service.db.execute("SELECT actor FROM bot_receipts WHERE request='mcp-submit'").fetchone()[0] == MEMBER
    created = match(service, owner=C2C, request_id='c2c-create')
    seats = json.loads(service.db.execute('SELECT seats FROM bot_matches WHERE id=?', (created['match_id'],)).fetchone()[0])
    assert seats['allies'] == MEMBER and C2C not in seats.values()
    opposing = match(service, owner=OTHER, side='axis', request_id='other-create')
    joined = service.join(opposing['match_id'], C2C, ROOM, 'c2c-join')
    assert joined['side'] == 'allies'
    assert len(service.matches(C2C, ROOM)) == 3
