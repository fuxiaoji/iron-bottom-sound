from copy import deepcopy

import pytest

from iron_bottom_sound.engine import IronBottomEngine, ORDER_PHASES
from iron_bottom_sound.models import GameState, HexCoord, MovementOrder, OrderBatch, Phase, Side, TorpedoOrder, TorpedoTrack


SOURCE_INTERVALS = {0: (), 1: (4,), 2: (3, 6), 3: (2, 5, 8), 4: (2, 4, 6, 8),
                    5: (1, 2, 4, 6, 8), 6: (1, 2, 4, 6, 7, 8),
                    7: (1, 2, 3, 4, 6, 7, 8), 8: tuple(range(1, 9))}


def isolated(*, ship_start='O20', ship_heading=6, plan='0', fish_start='O15', fish_speed=8, friendly=False):
    engine = IronBottomEngine()
    state = engine.reset('IBS-S-03', seed=9)
    attacker = state.ships['IBS-U-KM-KARL-GALSTER']
    target = state.ships['IBS-U-RN-JAVELIN']
    for ship in state.ships.values():
        ship.position = None
    state.land_hexes.clear()
    attacker.position = HexCoord.from_label('C3')
    target.position = HexCoord.from_label(ship_start)
    target.heading = ship_heading
    if friendly:
        target.side = attacker.side
    state.sealed_orders[f'{state.turn}:{Phase.MOVEMENT_PLANNING.value}'] = {
        target.side.value: OrderBatch(side=target.side, phase=Phase.MOVEMENT_PLANNING,
                                     movement=[MovementOrder(ship_id=target.id, plan=plan)])}
    track = TorpedoTrack(id='pulse-test', side=attacker.side, launcher_ship_id=attacker.id,
                         torpedo_type=attacker.torpedo_type, position=HexCoord.from_label(fish_start),
                         heading=3, speed_cycle=(fish_speed,) * 3, range_remaining=30,
                         launched_turn=state.turn)
    state.torpedo_tracks = [track]
    return engine, state, attacker, target, track


@pytest.mark.parametrize('speed,expected', SOURCE_INTERVALS.items())
def test_source_schedule_and_actual_ship_and_torpedo_steps(speed, expected):
    engine, state, attacker, target, track = isolated(ship_start='C10', ship_heading=3,
                                                    plan=str(speed), fish_start='O10', fish_speed=speed)
    assert engine.movement_intervals(speed) == expected
    assert len(expected) == speed
    records = []
    original = engine._check_torpedo_contacts
    def record(current, **kwargs):
        original(current, **kwargs)
        records.append((kwargs.get('movement_interval', 0), target.position, track.position))
    engine._check_torpedo_contacts = record
    engine._resolve_movement(state)
    previous_ship, previous_fish = HexCoord.from_label('C10'), HexCoord.from_label('O10')
    ship_steps, fish_steps = [], []
    for interval, ship_position, fish_position in records:
        if ship_position != previous_ship:
            ship_steps.append(interval)
        if fish_position != previous_fish:
            fish_steps.append(interval)
        previous_ship, previous_fish = ship_position, fish_position
    assert tuple(ship_steps) == tuple(fish_steps) == expected
    assert [e.payload['movement_interval'] for e in state.events if e.type == 'movement_interval_resolved'] == list(range(1, 9))


def test_paid_120_degree_turn_spends_its_scheduled_mf_without_translation():
    engine = IronBottomEngine()
    start = HexCoord.from_label('O15')
    raw, _ = engine._movement_program(start, 3, engine.movement_commands(MovementOrder(ship_id='x', plan='1PP1')))
    timed = engine._interval_program(raw, start, 3)
    assert timed[0][0] == start
    assert timed[1][0] == timed[4][0] == start.neighbor(3)
    assert timed[1][1] == 3 and timed[4][1] == 1
    assert timed[7][0] == start.neighbor(3).neighbor(1)


def test_mid_turn_launch_uses_remaining_time_not_subtracted_launcher_mf():
    engine, state, attacker, target, _ = isolated()
    state.torpedo_tracks.clear()
    target.position = None
    attacker.position, attacker.heading = HexCoord.from_label('O10'), 3
    state.sealed_orders[f'{state.turn}:{Phase.MOVEMENT_PLANNING.value}'] = {
        attacker.side.value: OrderBatch(side=attacker.side, phase=Phase.MOVEMENT_PLANNING,
                                      movement=[MovementOrder(ship_id=attacker.id, plan='4')])}
    order = TorpedoOrder(ship_id=attacker.id, launcher_id='TT1', count=1, launch_at_mf=2,
                         launch_hex=HexCoord.from_label('O12'), launch_side='port', launch_angle='A', setting_index=0)
    state.sealed_orders[f'{state.turn}:{Phase.TORPEDO_PLANNING.value}'] = {
        attacker.side.value: OrderBatch(side=attacker.side, phase=Phase.TORPEDO_PLANNING, torpedoes=[order])}
    engine._resolve_movement(state)
    track = state.torpedo_tracks[0]
    assert track.distance_travelled == 4
    launch = next(event for event in state.events if event.type == 'torpedo_launched')
    assert launch.payload['movement_interval'] == 4
    assert launch.payload['first_turn_move_intervals'] == [5, 6, 7, 8]
    state.turn += 1
    engine._resolve_movement(state)
    assert track.distance_travelled == min(12, int(engine.rules.torpedoes[track.torpedo_type]['settings'][0]['range']))


@pytest.mark.parametrize('start,heading,plan,kind', [
    ('O16', 6, '8', 'edge_crossing'), ('O17', 6, '8', 'same_hex'),
    ('O16', 3, '8', None), ('O16', 6, '0', 'same_hex')])
def test_same_hex_crossing_following_and_stationary_target(start, heading, plan, kind):
    engine, state, _, target, track = isolated(ship_start=start, ship_heading=heading, plan=plan)
    engine._resolve_movement(state)
    if kind is None:
        assert not track.contact_ship_ids
    else:
        assert track.contact_ship_ids == [target.id]
        assert state.torpedo_contact_snapshots[track.id][target.id].kind == kind
        assert track.distance_travelled == 1


def test_ship_can_enter_a_torpedo_hex_after_the_torpedo_finished_its_moves():
    engine, state, _, target, track = isolated(plan='3', fish_speed=2)
    engine._resolve_movement(state)
    assert target.position == track.position == HexCoord.from_label('O17')
    assert state.torpedo_contact_snapshots[track.id][target.id].movement_interval == 8


def test_friendly_ship_is_a_contact_but_launcher_is_not():
    engine, state, _, target, track = isolated(ship_start='O16', friendly=True)
    engine._resolve_movement(state)
    assert track.contact_ship_ids == [target.id]
    state.torpedo_tracks.clear()
    track.contact_ship_ids.clear()
    track.launcher_ship_id = target.id
    track.position = target.position
    state.torpedo_tracks = [track]
    engine._check_torpedo_contacts(state)
    assert not track.contact_ship_ids


def test_last_range_hex_can_contact_and_whole_salvo_is_removed_even_on_miss():
    engine, state, _, target, track = isolated(ship_start='O16', fish_speed=1)
    track.range_remaining = 1
    engine._resolve_movement(state)
    assert track.range_remaining == 0 and track.contact_ship_ids == [target.id]
    assert track in state.torpedo_tracks
    engine._roll_2d6 = lambda _: (2, [1, 1])
    engine._resolve_torpedoes(state)
    assert not state.torpedo_tracks and not state.torpedo_contact_snapshots


def test_grounded_torpedo_does_not_hit_ship_entering_its_old_hex():
    engine, state, _, target, track = isolated(ship_start='O14', ship_heading=3, plan='1')
    state.land_hexes.add('O16')
    engine._resolve_movement(state)
    assert target.position == HexCoord.from_label('O15')
    assert not state.torpedo_tracks and not track.contact_ship_ids


def test_contact_freezes_heading_and_speed_before_later_movement_and_damage():
    engine, state, _, target, track = isolated(ship_start='O17', plan='1P1')
    engine._resolve_movement(state)
    snapshot = state.torpedo_contact_snapshots[track.id][target.id]
    assert snapshot.movement_interval == 2 and snapshot.heading == 6 and snapshot.speed == 2
    assert target.heading == 5 and target.position != track.position
    target.current_speed = 0
    engine._roll_2d6 = lambda _: (2, [1, 1])
    engine._resolve_torpedoes(state)
    attack = next(e for e in state.events if e.type == 'torpedo_attack')
    assert attack.payload['aspect'] == 'bow_stern' and attack.payload['hits'] == 0
    assert attack.dice.adjusted == 9
    assert not state.torpedo_contact_snapshots


@pytest.mark.parametrize('timing', ['legacy-mf-v1', 'greg-courter-8-v1'])
def test_seeded_command_log_replay_preserves_both_clocks(timing):
    engine = IronBottomEngine()
    state = engine.reset('IBS-S-03', seed=77, movement_timing=timing)
    while state.turn == 1:
        if state.phase in ORDER_PHASES:
            for side in Side:
                movement = [MovementOrder(ship_id=s.id, plan='0') for s in state.ships.values() if s.side == side and s.position]
                batch = OrderBatch(side=side, phase=state.phase,
                                   movement=movement if state.phase == Phase.MOVEMENT_PLANNING else [])
                assert engine.submit_orders(state.game_id, batch).valid
        engine.advance(state.game_id)
    assert engine.replay(state.events).model_dump(mode='json') == state.model_dump(mode='json')
    saved = state.model_dump(mode='json')
    if timing == 'legacy-mf-v1':
        saved.pop('movement_timing')
        saved.pop('torpedo_contact_snapshots')
        assert GameState.model_validate(saved).movement_timing == 'legacy-mf-v1'
        assert 'movement_timing' not in state.events[0].payload
    else:
        assert state.events[0].payload['movement_timing'] == timing


def test_assist_intercept_agrees_with_engine_at_an_edge_crossing():
    engine, state, attacker, target, track = isolated(ship_start='O16', plan='8')
    projected = engine._assist_intercept(state, attacker.torpedo_type, track.position, 3, 0, 0, target)
    engine._resolve_movement(state)
    assert projected[:2] == (track.position, track.distance_travelled)
    assert projected[2:] == (None, 0)


def test_contact_snapshots_are_internal_not_part_of_observation():
    engine, state, _, target, track = isolated(ship_start='O16')
    engine._resolve_movement(state)
    assert state.torpedo_contact_snapshots
    for side in Side:
        observation = engine.observe(state.game_id, side).model_dump(mode='json')
        assert 'torpedo_contact_snapshots' not in observation
        assert all('contact_snapshots' not in item for item in observation['torpedo_tracks'])


def test_state_machine_deconfliction_matches_different_speed_intervals():
    from iron_bottom_sound.tactical import TacticalCommander
    engine, state, attacker, target, _ = isolated(ship_start='O15', ship_heading=1, plan='1')
    attacker.position, attacker.heading = HexCoord.from_label('P15'), 5
    commander = TacticalCommander()
    left = MovementOrder(ship_id=target.id, plan='1')
    right = MovementOrder(ship_id=attacker.id, plan='2')
    assert commander._movement_conflicts(engine, state, target, left, [(attacker, right)])
    state.movement_timing = 'legacy-mf-v1'
    # Separate commander because the live branch caches paths within a decision.
    assert not TacticalCommander()._movement_conflicts(engine, state, target, left, [(attacker, right)])


def test_state_machine_timed_avoidance_distinguishes_overtake_from_following():
    from iron_bottom_sound.tactical import TacticalCommander
    engine, state, _, target, track = isolated(ship_start='O10', ship_heading=3, plan='4', fish_start='O8')
    path = engine.torpedo_clock_positions(state, track.position, track.heading, 8, 30)
    commander = TacticalCommander()
    assert commander._timed_torpedo_risk(engine, state, target, MovementOrder(ship_id=target.id, plan='4'), [path]) == 1
    assert commander._timed_torpedo_risk(engine, state, target, MovementOrder(ship_id=target.id, plan='8'), [path]) == 0


def test_forecast_has_no_prelaunch_track_and_expires_after_last_contact_slot():
    engine, state, _, _, _ = isolated()
    start = HexCoord.from_label('O10')
    path = engine.torpedo_clock_positions(state, start, 3, 8, 2, launch_interval=4)
    assert path[:4] == [None] * 4
    assert path[4:7] == [start, start.neighbor(3), start.neighbor(3).neighbor(3)]
    assert path[7:] == [None, None]


def test_timed_ai_context_does_not_use_hidden_enemy_torpedo():
    from iron_bottom_sound.tactical import TacticalCommander
    engine, state, attacker, target, track = isolated()
    state.options.optional_rules.blind_torpedoes = True
    track.hidden = True
    context = TacticalCommander()._build_movement_context(engine, state, target.side, [])
    assert context.visible_torpedo_paths == []
    state.options.optional_rules.blind_torpedoes = False
    track.hidden = False
    context = TacticalCommander()._build_movement_context(engine, state, target.side, [])
    assert len(context.visible_torpedo_paths) == 1
